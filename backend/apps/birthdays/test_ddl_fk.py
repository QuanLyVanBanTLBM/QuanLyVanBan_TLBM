import importlib
import unittest
from datetime import date

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase

from birthdays.models import BirthdayEmailLog, BirthdayWish
from organizations.models import DonVi, KhoiKhuVuc

migration = importlib.import_module("birthdays.migrations.0003_employee_fk_cascade_ddl")


def _next_unit_priority():
    return (DonVi.objects.order_by("-stt_uu_tien").values_list("stt_uu_tien", flat=True).first() or 0) + 1


@unittest.skipUnless(connection.vendor == "postgresql", "Cấu trúc theo DDL chỉ kiểm trên PostgreSQL")
class BirthdayForeignKeyMatchesDdlTests(TestCase):
    def test_employee_foreign_keys_cascade_on_delete(self):
        with connection.cursor() as cursor:
            for table, column, referenced in migration.CASCADE_FOREIGN_KEYS:
                matches = [row for row in migration._constraints(cursor, table) if row[1] == [column]]
                self.assertEqual(len(matches), 1, f"{table}.{column}")
                self.assertIn("ON DELETE CASCADE", matches[0][2], f"{table}.{column}")
                self.assertEqual(matches[0][4].split(".")[-1].strip('"'), referenced)

    def test_raw_sql_employee_delete_removes_wishes_and_email_logs(self):
        unit = DonVi.objects.create(
            khoi=KhoiKhuVuc.objects.create(ten="C1B khối sinh nhật"),
            stt_uu_tien=_next_unit_priority(),
            ten="C1B đơn vị",
        )
        employee = get_user_model().objects.create_user(username="c1b_birthday_fk", password="unused", don_vi=unit)
        BirthdayWish.objects.create(employee=employee, sender_name="Người gửi", message="Lời chúc")
        BirthdayEmailLog.objects.create(
            employee=employee,
            sent_date=date(2026, 5, 20),
            recipient_email="c1b@example.test",
            subject="Lời chúc",
        )

        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM accounts_employee WHERE id = %s", [employee.pk])
            cursor.execute("SELECT count(*) FROM birthdays_birthdaywish WHERE employee_id = %s", [employee.pk])
            self.assertEqual(cursor.fetchone()[0], 0)
            cursor.execute("SELECT count(*) FROM birthdays_birthdayemaillog WHERE employee_id = %s", [employee.pk])
            self.assertEqual(cursor.fetchone()[0], 0)

    def test_orphaned_employee_reference_fails_closed(self):
        unit = DonVi.objects.create(
            khoi=KhoiKhuVuc.objects.create(ten="C1B khối orphan"),
            stt_uu_tien=_next_unit_priority(),
            ten="C1B đơn vị orphan",
        )
        employee = get_user_model().objects.create_user(username="c1b_birthday_orphan", password="unused", don_vi=unit)
        wish = BirthdayWish.objects.create(employee=employee, sender_name="Người gửi", message="Lời chúc")
        with connection.cursor() as cursor:
            cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
            fk = next(row[0] for row in migration._constraints(cursor, "birthdays_birthdaywish") if row[1] == ["employee_id"])
            cursor.execute(
                f"ALTER TABLE birthdays_birthdaywish DROP CONSTRAINT {connection.ops.quote_name(fk)}"
            )
            cursor.execute("UPDATE birthdays_birthdaywish SET employee_id = %s WHERE id = %s", [9223372036854770000, wish.pk])

        with connection.schema_editor() as schema_editor:
            with self.assertRaisesRegex(RuntimeError, r"birthdays_birthdaywish.employee_id.*1 orphan"):
                migration.cascade_employee_fk(None, schema_editor)

        with connection.cursor() as cursor:
            cursor.execute("SELECT employee_id FROM birthdays_birthdaywish WHERE id = %s", [wish.pk])
            self.assertEqual(cursor.fetchone()[0], 9223372036854770000)

    def test_migration_is_idempotent(self):
        with connection.schema_editor() as schema_editor:
            migration.cascade_employee_fk(None, schema_editor)
            migration.cascade_employee_fk(None, schema_editor)
