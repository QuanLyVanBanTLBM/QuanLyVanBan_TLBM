import importlib
import unittest

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.db import connection
from django.test import TestCase

migration = importlib.import_module("authorization.migrations.0005_align_rbac_structure_with_ddl")


@unittest.skipUnless(connection.vendor == "postgresql", "Cấu trúc theo DDL chỉ kiểm trên PostgreSQL")
class RbacStructureMatchesDdlTests(TestCase):
    def test_key_columns_and_sequences_are_bigint(self):
        with connection.cursor() as cursor:
            for table, column in migration.BIGINT_COLUMNS:
                self.assertEqual(migration._column_info(cursor, table, column)[0], "bigint", f"{table}.{column}")
            for table in ("auth_group", "auth_permission"):
                cursor.execute("SELECT pg_get_serial_sequence(%s, 'id')", [table])
                sequence_name = cursor.fetchone()[0]
                self.assertIsNotNone(sequence_name)
                cursor.execute(
                    "SELECT format_type(seqtypid, NULL) FROM pg_sequence WHERE seqrelid = %s::regclass",
                    [sequence_name],
                )
                self.assertEqual(cursor.fetchone()[0], "bigint", f"{table}.id sequence")

    def test_required_uniques_exist_and_content_type_unique_is_removed(self):
        with connection.cursor() as cursor:
            permission_unique = [row[1] for row in migration._constraints(cursor, "auth_permission", "u")]
            group_unique = [row[1] for row in migration._constraints(cursor, "auth_group", "u")]
        self.assertIn(["codename"], permission_unique)
        self.assertIn(["ma_nhom_quyen"], group_unique)
        self.assertNotIn(["content_type_id", "codename"], permission_unique)

    def test_permission_has_no_content_type_fk(self):
        with connection.cursor() as cursor:
            constraints = migration._constraints(cursor, "auth_permission", "f")
        self.assertFalse(any("content_type_id" in row[1] for row in constraints))

    def test_link_foreign_keys_cascade_on_delete(self):
        with connection.cursor() as cursor:
            for table, column, referenced in migration.CASCADE_FOREIGN_KEYS:
                matches = [row for row in migration._constraints(cursor, table, "f") if row[1] == [column]]
                self.assertEqual(len(matches), 1, f"{table}.{column}")
                self.assertIn("ON DELETE CASCADE", matches[0][2], f"{table}.{column}")
                self.assertEqual(matches[0][4].split(".")[-1].strip('"'), referenced)
                self.assertEqual(matches[0][5], ["id"])

    def test_missing_link_foreign_key_is_recreated(self):
        table = "auth_group_permissions"
        column = "group_id"
        with connection.cursor() as cursor:
            cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
            constraint_name = next(
                row[0] for row in migration._constraints(cursor, table, "f") if row[1] == [column]
            )
            cursor.execute(
                f"ALTER TABLE {connection.ops.quote_name(table)} "
                f"DROP CONSTRAINT {connection.ops.quote_name(constraint_name)}"
            )

        with connection.schema_editor() as schema_editor:
            migration.align_structure(None, schema_editor)

        with connection.cursor() as cursor:
            matches = [row for row in migration._constraints(cursor, table, "f") if row[1] == [column]]
        self.assertEqual(len(matches), 1)
        self.assertIn("ON DELETE CASCADE", matches[0][2])

    def test_orphaned_auth_link_fails_closed_without_deleting_rows(self):
        employee = get_user_model().objects.create_user(
            username="c1b_rbac_orphan", password="unused", ho_ten="C1B RBAC orphan"
        )
        orphan_group_id = 9223372036854770000
        with connection.cursor() as cursor:
            cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
            constraint_name = next(
                row[0]
                for row in migration._constraints(cursor, "accounts_employee_groups", "f")
                if row[1] == ["group_id"]
            )
            cursor.execute(
                f"ALTER TABLE accounts_employee_groups DROP CONSTRAINT {connection.ops.quote_name(constraint_name)}"
            )
            cursor.execute(
                "INSERT INTO accounts_employee_groups (employee_id, group_id) VALUES (%s, %s)",
                [employee.pk, orphan_group_id],
            )

        with connection.schema_editor() as schema_editor:
            with self.assertRaisesRegex(RuntimeError, r"accounts_employee_groups.group_id.*1 orphan"):
                migration.align_structure(None, schema_editor)

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT count(*) FROM accounts_employee_groups WHERE employee_id = %s AND group_id = %s",
                [employee.pk, orphan_group_id],
            )
            self.assertEqual(cursor.fetchone()[0], 1)

    def test_raw_sql_deletes_cascade_all_rbac_links(self):
        permission = Permission.objects.get(codename="view_donvi")
        group = Group.objects.create(name="C1B RBAC source group")
        surviving_group = Group.objects.create(name="C1B RBAC surviving group")
        employee = get_user_model().objects.create_user(
            username="c1b_rbac_fk", password="unused", ho_ten="C1B RBAC"
        )
        group.permissions.add(permission)
        surviving_group.permissions.add(permission)
        employee.groups.add(group)
        employee.user_permissions.add(permission)

        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM auth_group WHERE id = %s", [group.pk])
            cursor.execute("SELECT count(*) FROM auth_group_permissions WHERE group_id = %s", [group.pk])
            self.assertEqual(cursor.fetchone()[0], 0)
            cursor.execute("SELECT count(*) FROM accounts_employee_groups WHERE group_id = %s", [group.pk])
            self.assertEqual(cursor.fetchone()[0], 0)

            cursor.execute("DELETE FROM auth_permission WHERE id = %s", [permission.pk])
            cursor.execute("SELECT count(*) FROM auth_group_permissions WHERE permission_id = %s", [permission.pk])
            self.assertEqual(cursor.fetchone()[0], 0)
            cursor.execute(
                "SELECT count(*) FROM accounts_employee_user_permissions WHERE permission_id = %s", [permission.pk]
            )
            self.assertEqual(cursor.fetchone()[0], 0)

        employee.refresh_from_db()
        another_permission = Permission.objects.get(codename="change_donvi")
        employee.user_permissions.add(another_permission)
        employee_id = employee.pk
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM accounts_employee WHERE id = %s", [employee_id])
            cursor.execute(
                "SELECT count(*) FROM accounts_employee_user_permissions WHERE employee_id = %s", [employee_id]
            )
            self.assertEqual(cursor.fetchone()[0], 0)

    def test_existing_custom_rbac_values_are_not_rewritten(self):
        group = Group.objects.create(name="C1B custom group name")
        permission = Permission.objects.get(codename="view_donvi")
        employee = get_user_model().objects.create_user(
            username="c1b_rbac_custom", password="unused", ho_ten="C1B RBAC custom"
        )
        group.permissions.add(permission)
        employee.groups.add(group)
        employee.user_permissions.add(permission)
        with connection.cursor() as cursor:
            cursor.execute("UPDATE auth_group SET ma_nhom_quyen = %s WHERE id = %s", ["C1B-CUSTOM", group.pk])
            cursor.execute("UPDATE auth_permission SET name = %s WHERE id = %s", ["Tên quyền tùy chỉnh", permission.pk])
            cursor.execute("SELECT id, name, ma_nhom_quyen FROM auth_group WHERE id = %s", [group.pk])
            group_row = cursor.fetchone()
            cursor.execute("SELECT id, name FROM auth_permission WHERE id = %s", [permission.pk])
            permission_row = cursor.fetchone()
            cursor.execute(
                "SELECT id FROM auth_group_permissions WHERE group_id = %s AND permission_id = %s",
                [group.pk, permission.pk],
            )
            group_permission_id = cursor.fetchone()[0]
            cursor.execute(
                "SELECT id FROM accounts_employee_groups WHERE employee_id = %s AND group_id = %s",
                [employee.pk, group.pk],
            )
            employee_group_id = cursor.fetchone()[0]
            cursor.execute(
                "SELECT id FROM accounts_employee_user_permissions WHERE employee_id = %s AND permission_id = %s",
                [employee.pk, permission.pk],
            )
            employee_permission_id = cursor.fetchone()[0]
            before = (group_row, permission_row, group_permission_id, employee_group_id, employee_permission_id)
            cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")

        with connection.schema_editor() as schema_editor:
            migration.align_structure(None, schema_editor)
            migration.align_structure(None, schema_editor)

        with connection.cursor() as cursor:
            cursor.execute("SELECT id, name, ma_nhom_quyen FROM auth_group WHERE id = %s", [group.pk])
            group_row = cursor.fetchone()
            cursor.execute("SELECT id, name FROM auth_permission WHERE id = %s", [permission.pk])
            permission_row = cursor.fetchone()
            cursor.execute(
                "SELECT id FROM auth_group_permissions WHERE group_id = %s AND permission_id = %s",
                [group.pk, permission.pk],
            )
            group_permission_id = cursor.fetchone()[0]
            cursor.execute(
                "SELECT id FROM accounts_employee_groups WHERE employee_id = %s AND group_id = %s",
                [employee.pk, group.pk],
            )
            employee_group_id = cursor.fetchone()[0]
            cursor.execute(
                "SELECT id FROM accounts_employee_user_permissions WHERE employee_id = %s AND permission_id = %s",
                [employee.pk, permission.pk],
            )
            employee_permission_id = cursor.fetchone()[0]
            after = (group_row, permission_row, group_permission_id, employee_group_id, employee_permission_id)
        self.assertEqual(before, after)

    def test_duplicate_codenames_fail_closed_without_deleting_rows(self):
        duplicate_codename = "c1b_duplicate_probe"
        with connection.cursor() as cursor:
            unique_constraints = [
                row for row in migration._constraints(cursor, "auth_permission", "u") if row[1] == ["codename"]
            ]
            self.assertEqual(len(unique_constraints), 1)
            cursor.execute(
                f"ALTER TABLE auth_permission DROP CONSTRAINT {connection.ops.quote_name(unique_constraints[0][0])}"
            )
            cursor.execute(
                "INSERT INTO auth_permission (name, codename, module_ten) VALUES (%s, %s, %s), (%s, %s, %s)",
                ["one", duplicate_codename, "test", "two", duplicate_codename, "test"],
            )

        with connection.schema_editor() as schema_editor:
            with self.assertRaisesRegex(RuntimeError, r"auth_permission.codename has 1 duplicate group"):
                migration.align_structure(None, schema_editor)

        with connection.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM auth_permission WHERE codename = %s", [duplicate_codename])
            self.assertEqual(cursor.fetchone()[0], 2)

    def test_duplicate_group_codes_fail_closed_without_deleting_rows(self):
        duplicate_code = "C1B-DUPLICATE"
        with connection.cursor() as cursor:
            unique_constraints = [
                row for row in migration._constraints(cursor, "auth_group", "u") if row[1] == ["ma_nhom_quyen"]
            ]
            self.assertEqual(len(unique_constraints), 1)
            cursor.execute(
                f"ALTER TABLE auth_group DROP CONSTRAINT {connection.ops.quote_name(unique_constraints[0][0])}"
            )
            cursor.execute(
                "INSERT INTO auth_group (name, ma_nhom_quyen) VALUES (%s, %s), (%s, %s)",
                ["C1B duplicate group one", duplicate_code, "C1B duplicate group two", duplicate_code],
            )

        with connection.schema_editor() as schema_editor:
            with self.assertRaisesRegex(RuntimeError, r"auth_group.ma_nhom_quyen has 1 duplicate group"):
                migration.align_structure(None, schema_editor)

        with connection.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM auth_group WHERE ma_nhom_quyen = %s", [duplicate_code])
            self.assertEqual(cursor.fetchone()[0], 2)

