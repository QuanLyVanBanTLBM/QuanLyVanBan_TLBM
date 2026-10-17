"""FK employee_id của bảng sinh nhật phải có ON DELETE CASCADE ở mức DB như release_DDL.sql."""
import importlib
import unittest
from datetime import date

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase

from birthdays.models import BirthdayEmailLog, BirthdayWish
from organizations.models import DonVi, KhoiKhuVuc

migration = importlib.import_module("birthdays.migrations.0003_employee_fk_cascade_ddl")


@unittest.skipUnless(connection.vendor == "postgresql", "Cấu trúc theo DDL chỉ kiểm trên PostgreSQL")
class BirthdayForeignKeyMatchesDdlTests(TestCase):
    def test_employee_fk_cascades_in_database(self):
        with connection.cursor() as cursor:
            for table, column, referenced in migration.CASCADE_FOREIGN_KEYS:
                matches = [d for _, columns, d in migration.foreign_keys(cursor, table) if columns == [column]]
                self.assertEqual(len(matches), 1, table)
                self.assertIn("ON DELETE CASCADE", matches[0], table)
                self.assertIn(f"REFERENCES {referenced}(id)", matches[0], table)

    def test_deleting_employee_with_raw_sql_removes_wish_and_email_log(self):
        unit = DonVi.objects.create(khoi=KhoiKhuVuc.objects.create(ten="Khối FK"), stt_uu_tien=1, ten="Đơn vị FK")
        employee = get_user_model().objects.create_user(username="fk_sinh_nhat", password="x", don_vi=unit)
        BirthdayWish.objects.create(employee=employee, sender_name="Người gửi", message="Chúc mừng")
        BirthdayEmailLog.objects.create(
            employee=employee, sent_date=date(2026, 5, 20), recipient_email="fk@example.test", subject="Chúc mừng"
        )
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM accounts_employee WHERE id = %s", [employee.id])
            cursor.execute("SELECT count(*) FROM birthdays_birthdaywish WHERE employee_id = %s", [employee.id])
            self.assertEqual(cursor.fetchone()[0], 0)
            cursor.execute("SELECT count(*) FROM birthdays_birthdayemaillog WHERE employee_id = %s", [employee.id])
            self.assertEqual(cursor.fetchone()[0], 0)

    def test_migration_is_idempotent(self):
        with connection.schema_editor() as schema_editor:
            migration.cascade_employee_fk(None, schema_editor)
            migration.cascade_employee_fk(None, schema_editor)
