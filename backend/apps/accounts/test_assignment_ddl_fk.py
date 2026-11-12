"""FK employee_id của accounts_employee_assignment phải có ON DELETE CASCADE ở mức DB như release_DDL.sql."""
import importlib
import unittest

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase

from accounts.models import EmployeeAssignment, Position
from organizations.models import DonVi, KhoiKhuVuc

migration = importlib.import_module("accounts.migrations.0011_employeeassignment_fk_cascade_ddl")


@unittest.skipUnless(connection.vendor == "postgresql", "Cấu trúc theo DDL chỉ kiểm trên PostgreSQL")
class AssignmentForeignKeyMatchesDdlTests(TestCase):
    def test_employee_fk_cascades_in_database(self):
        with connection.cursor() as cursor:
            for table, column, referenced in migration.CASCADE_FOREIGN_KEYS:
                matches = [d for _, columns, d in migration.foreign_keys(cursor, table) if columns == [column]]
                self.assertEqual(len(matches), 1, table)
                self.assertIn("ON DELETE CASCADE", matches[0], table)
                self.assertIn(f"REFERENCES {referenced}(id)", matches[0], table)

    def test_deleting_employee_with_raw_sql_removes_assignment(self):
        unit = DonVi.objects.first()
        if not unit:
            khoi = KhoiKhuVuc.objects.create(ten="Khối FK Test", thu_tu_hien_thi=999)
            unit = DonVi.objects.create(khoi=khoi, stt_uu_tien=999, ten="Đơn vị FK Test")
        pos = Position.objects.first()
        if not pos:
            pos = Position.objects.create(name="Chức vụ FK Test", display_order=999)
        employee = get_user_model().objects.create_user(username="fk_assignment", password="x", don_vi=unit)
        EmployeeAssignment.objects.create(employee=employee, don_vi=unit, chuc_vu=pos)
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM accounts_employee WHERE id = %s", [employee.id])
            cursor.execute("SELECT count(*) FROM accounts_employee_assignment WHERE employee_id = %s", [employee.id])
            self.assertEqual(cursor.fetchone()[0], 0)

    def test_migration_is_idempotent(self):
        with connection.schema_editor() as schema_editor:
            migration.cascade_employee_fk(None, schema_editor)
            migration.cascade_employee_fk(None, schema_editor)
