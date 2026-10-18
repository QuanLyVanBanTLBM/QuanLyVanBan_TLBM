"""Cấu trúc bảng phân quyền do migration tạo ra phải khớp release_DDL.sql (mục 14, 15)."""
import importlib
import unittest

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.db import connection
from django.test import TestCase

migration = importlib.import_module("authorization.migrations.0005_align_rbac_structure_with_ddl")


def _constraints(table, kind):
    with connection.cursor() as cursor:
        return migration._constraints(cursor, table, kind)


@unittest.skipUnless(connection.vendor == "postgresql", "Cấu trúc theo DDL chỉ kiểm trên PostgreSQL")
class RbacStructureMatchesDdlTests(TestCase):
    def test_key_columns_are_bigint(self):
        with connection.cursor() as cursor:
            for table, column in migration.BIGINT_COLUMNS:
                data_type, _ = migration._column_info(cursor, table, column)
                self.assertEqual(data_type, "bigint", f"{table}.{column}")

    def test_unique_codename_and_ma_nhom_quyen_are_constraints(self):
        permission_unique = [columns for _, columns, _ in _constraints("auth_permission", "u")]
        group_unique = [columns for _, columns, _ in _constraints("auth_group", "u")]
        self.assertIn(["codename"], permission_unique)
        self.assertIn(["ma_nhom_quyen"], group_unique)
        # DDL không có unique (content_type_id, codename)
        self.assertNotIn(["codename", "content_type_id"], permission_unique)

    def test_permission_has_no_content_type_fk(self):
        self.assertEqual([columns for _, columns, _ in _constraints("auth_permission", "f")], [])

    def test_link_tables_cascade_on_delete_in_database(self):
        for table, column, referenced in migration.CASCADE_FOREIGN_KEYS:
            matches = [d for _, columns, d in _constraints(table, "f") if columns == [column]]
            self.assertEqual(len(matches), 1, f"{table}.{column}")
            self.assertIn("ON DELETE CASCADE", matches[0], f"{table}.{column}")
            self.assertIn(f"REFERENCES {referenced}(id)", matches[0], f"{table}.{column}")

    def test_deleting_group_and_permission_with_raw_sql_removes_links(self):
        group = Group.objects.create(name="Nhóm kiểm cấu trúc")
        permission = Permission.objects.get(codename="view_donvi")
        group.permissions.add(permission)
        employee = get_user_model().objects.create_user(
            username="cau_truc_ddl", email="cau_truc_ddl@example.test", password="Pass12345", ho_ten="Cấu trúc DDL"
        )
        employee.groups.add(group)
        employee.user_permissions.add(permission)

        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM auth_group WHERE id = %s", [group.id])
            cursor.execute("SELECT count(*) FROM auth_group_permissions WHERE group_id = %s", [group.id])
            self.assertEqual(cursor.fetchone()[0], 0)
            cursor.execute("SELECT count(*) FROM accounts_employee_groups WHERE group_id = %s", [group.id])
            self.assertEqual(cursor.fetchone()[0], 0)
            cursor.execute("DELETE FROM accounts_employee WHERE id = %s", [employee.id])
            cursor.execute("SELECT count(*) FROM accounts_employee_user_permissions WHERE employee_id = %s", [employee.id])
            self.assertEqual(cursor.fetchone()[0], 0)

    def test_migration_is_idempotent(self):
        with connection.schema_editor() as schema_editor:
            migration.align_structure(None, schema_editor)
            migration.align_structure(None, schema_editor)
            migration.align_permission_names(None, schema_editor)


class PermissionNamesMatchDdlTests(TestCase):
    def test_permission_names_follow_ddl(self):
        for codename, expected in migration.DDL_PERMISSION_NAMES.items():
            self.assertEqual(Permission.objects.get(codename=codename).name, expected, codename)

    def test_seed_uses_the_same_names(self):
        from authorization.rbac_seed import EXTRA_PERMISSIONS

        seeded = {codename: name for name, codename, _ in EXTRA_PERMISSIONS}
        for codename, expected in migration.DDL_PERMISSION_NAMES.items():
            self.assertEqual(seeded[codename], expected, codename)
