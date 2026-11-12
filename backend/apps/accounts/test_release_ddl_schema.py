"""Schema tạo từ migration phải khớp release_DDL.sql: accounts_employee, accounts_position, organizations_khoi, organizations_donvi."""

from unittest import skipUnless

from django.db import connection
from django.test import TestCase


def _column(table, column):
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT udt_name, character_maximum_length, is_nullable, column_default FROM information_schema.columns "
            "WHERE table_schema = current_schema() AND table_name = %s AND column_name = %s",
            [table, column],
        )
        return cursor.fetchone()


def _indexes(table):
    with connection.cursor() as cursor:
        cursor.execute("SELECT indexname FROM pg_indexes WHERE schemaname = current_schema() AND tablename = %s", [table])
        return {row[0] for row in cursor.fetchall()}


def _constraints(table):
    with connection.cursor() as cursor:
        cursor.execute("SELECT conname, contype FROM pg_constraint WHERE conrelid = %s::regclass", [table])
        return dict(cursor.fetchall())


@skipUnless(connection.vendor == "postgresql", "Kiểu ENUM và tên ràng buộc chỉ kiểm trên PostgreSQL")
class ReleaseDdlSchemaTests(TestCase):
    def test_employee_columns(self):
        self.assertEqual(_column("accounts_employee", "trang_thai"),
                         ("employee_work_status", None, "NO", "'LAM_VIEC'::employee_work_status"))
        self.assertEqual(_column("accounts_employee", "password")[:3], ("varchar", 255, "NO"))
        for column in ("chuc_danh", "sdt", "ghi_chu"):
            self.assertEqual(_column("accounts_employee", column)[2], "YES", column)
        for column, default in (("is_active", "true"), ("is_staff", "false"), ("is_superuser", "false"),
                                ("is_public", "true"), ("created_at", "now()"), ("updated_at", "now()")):
            self.assertEqual(_column("accounts_employee", column)[3], default, column)

    def test_employee_indexes_and_m2m_names(self):
        self.assertTrue({"idx_employee_donvi", "idx_employee_chucvu", "idx_employee_is_active"}
                        <= _indexes("accounts_employee"))
        self.assertIn("uq_employee_group", _constraints("accounts_employee_groups"))
        self.assertIn("uq_employee_permission", _constraints("accounts_employee_user_permissions"))

    def test_position_columns(self):
        self.assertEqual(_column("accounts_position", "note")[2], "YES")
        self.assertEqual(_column("accounts_position", "is_public")[3], "true")
        self.assertNotIn("c", _constraints("accounts_position").values())

    def test_organization_columns(self):
        self.assertEqual(_column("organizations_donvi", "dia_chi")[:3], ("varchar", 255, "YES"))
        for column in ("dien_thoai", "email", "ghi_chu"):
            self.assertEqual(_column("organizations_donvi", column)[2], "YES", column)
        self.assertEqual(_column("organizations_khoi", "thu_tu_hien_thi")[3], "0")
        self.assertIn("idx_donvi_khoi", _indexes("organizations_donvi"))
        khoi = _constraints("organizations_khoi")
        self.assertEqual(khoi, {"organizations_khoi_pkey": "p"})
        self.assertNotIn("c", _constraints("organizations_donvi").values())

    def test_password_reset_audit_schema(self):
        self.assertEqual(_column("accounts_password_reset_audit", "actor_id")[2], "YES")
        self.assertEqual(_column("accounts_password_reset_audit", "target_id")[2], "YES")
        self.assertEqual(_column("accounts_password_reset_audit", "actor_username")[:3], ("varchar", 150, "NO"))
        self.assertEqual(_column("accounts_password_reset_audit", "target_username")[:3], ("varchar", 150, "NO"))
        self.assertEqual(_column("accounts_password_reset_audit", "reason_code")[:3], ("varchar", 32, "NO"))
        self.assertEqual(_column("accounts_password_reset_audit", "reason_detail")[:3], ("varchar", 500, "YES"))
        self.assertEqual(_column("accounts_password_reset_audit", "created_at")[3], "now()")
        constraints = _constraints("accounts_password_reset_audit")
        self.assertEqual(list(constraints.values()).count("f"), 2)
        self.assertEqual(list(constraints.values()).count("c"), 2)
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT a.attname, c.confdeltype, c.condeferrable, c.condeferred "
                "FROM pg_constraint c "
                "JOIN unnest(c.conkey) WITH ORDINALITY AS key(attnum, ord) ON TRUE "
                "JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = key.attnum "
                "WHERE c.conrelid = 'accounts_password_reset_audit'::regclass AND c.contype = 'f'"
            )
            foreign_keys = {column: (delete_action, deferrable, deferred) for column, delete_action, deferrable, deferred in cursor.fetchall()}
        self.assertEqual(foreign_keys, {"actor_id": ("a", True, True), "target_id": ("a", True, True)})
        self.assertTrue(
            {
                "idx_pwd_reset_target_time",
                "idx_pwd_reset_actor_time",
            }
            <= _indexes("accounts_password_reset_audit")
        )
