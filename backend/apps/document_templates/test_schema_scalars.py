"""Database contract tests for document-template scalar defaults and guards."""

from datetime import date
from importlib import import_module
from types import SimpleNamespace

from django.db import connection, transaction
from django.test import TestCase

from accounts.models import Employee
from document_templates.models import DanhMucTaiLieu, TaiLieuChiTiet


class DocumentTemplateSchemaScalarTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = Employee.objects.create_user(username="template_schema_scalar_user", password="pw")
        cls.category = DanhMucTaiLieu.objects.create(
            stt_uu_tien=0,
            ten_tai_lieu="Danh mục scalar test",
            nguoi_lap=cls.user,
        )

    def test_raw_insert_defaults_and_updated_at_triggers(self):
        with connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO records_tailieu (stt_uu_tien, ten_tai_lieu, nguoi_lap_id)
                   VALUES (%s, %s, %s) RETURNING id, created_at, updated_at""",
                [31000, "Raw SQL category", self.user.pk],
            )
            category_id, category_created_at, category_updated_at = cursor.fetchone()
            self.assertGreater(category_created_at.year, 2000)
            self.assertGreater(category_updated_at.year, 2000)

            cursor.execute(
                """INSERT INTO records_loaitailieu (dm_tai_lieu, ten_loai)
                   VALUES (%s, %s) RETURNING id, is_public, created_at, updated_at""",
                [category_id, "Raw SQL type"],
            )
            type_id, is_public, type_created_at, type_updated_at = cursor.fetchone()
            self.assertTrue(is_public)
            self.assertGreater(type_created_at.year, 2000)
            self.assertGreater(type_updated_at.year, 2000)

            cursor.execute(
                """INSERT INTO records_chitiettailieu
                       (dm_tai_lieu, tieu_de, ngay_dang, hieu_luc, hien_thi)
                   VALUES (%s, %s, %s, %s::hieu_luc_status, %s::chitiettailieu_hienthi)
                   RETURNING id, created_at, updated_at""",
                [category_id, "Raw SQL detail", date(2026, 1, 1), "CON_HIEU_LUC", "TAT_CA"],
            )
            detail_id, detail_created_at, detail_updated_at = cursor.fetchone()
            self.assertGreater(detail_created_at.year, 2000)
            self.assertGreater(detail_updated_at.year, 2000)

            cursor.execute(
                """INSERT INTO records_chitiettailieu_attachment (document_id, name, path)
                   VALUES (%s, %s, %s) RETURNING is_deleted, created_at""",
                [detail_id, "raw.pdf", "raw.pdf"],
            )
            is_deleted, attachment_created_at = cursor.fetchone()
            self.assertFalse(is_deleted)
            self.assertGreater(attachment_created_at.year, 2000)

            for table, row_id in (
                ("records_tailieu", category_id),
                ("records_loaitailieu", type_id),
                ("records_chitiettailieu", detail_id),
            ):
                cursor.execute(
                    f"UPDATE {table} SET updated_at = %s WHERE id = %s RETURNING updated_at",
                    ["2000-01-01T00:00:00+00:00", row_id],
                )
                self.assertGreater(cursor.fetchone()[0].year, 2000)

    def test_null_category_owner_fails_before_schema_or_data_change(self):
        migration = import_module("document_templates.migrations.0004_schema_scalars")
        category = DanhMucTaiLieu.objects.create(
            stt_uu_tien=0,
            ten_tai_lieu="Null owner preflight probe",
            nguoi_lap=self.user,
        )

        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
                cursor.execute(
                    "ALTER TABLE records_tailieu ALTER COLUMN nguoi_lap_id DROP NOT NULL"
                )
                cursor.execute(
                    "UPDATE records_tailieu SET nguoi_lap_id = NULL WHERE id = %s",
                    [category.pk],
                )

            with self.assertRaisesRegex(RuntimeError, r"records_tailieu\.nguoi_lap_id: 1"):
                migration.install_schema_scalars(None, SimpleNamespace(connection=connection))

            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT att.attnotnull FROM pg_attribute att "
                    "WHERE att.attrelid = 'records_tailieu'::regclass AND att.attname = 'nguoi_lap_id'"
                )
                self.assertFalse(cursor.fetchone()[0])
                cursor.execute(
                    "SELECT nguoi_lap_id FROM records_tailieu WHERE id = %s",
                    [category.pk],
                )
                self.assertIsNone(cursor.fetchone()[0])
            transaction.set_rollback(True)


    def test_invalid_enum_value_fails_before_conversion(self):
        migration = import_module("document_templates.migrations.0004_schema_scalars")
        detail = TaiLieuChiTiet.objects.create(
            dm_tai_lieu=self.category,
            tieu_de="Invalid enum preflight probe",
            ngay_dang=date(2026, 1, 2),
        )

        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("DROP VIEW IF EXISTS ai_tailieu")
                cursor.execute(
                    "ALTER TABLE records_chitiettailieu ALTER COLUMN hieu_luc TYPE varchar(30) "
                    "USING hieu_luc::text"
                )
                cursor.execute(
                    "UPDATE records_chitiettailieu SET hieu_luc = 'INVALID' WHERE id = %s",
                    [detail.pk],
                )

            with self.assertRaisesRegex(
                RuntimeError, r"records_chitiettailieu\.hieu_luc: 1"
            ):
                migration.install_schema_scalars(None, SimpleNamespace(connection=connection))

            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT format_type(att.atttypid, att.atttypmod) "
                    "FROM pg_attribute att "
                    "WHERE att.attrelid = 'records_chitiettailieu'::regclass "
                    "AND att.attname = 'hieu_luc'"
                )
                self.assertEqual(cursor.fetchone()[0], "character varying(30)")
                cursor.execute(
                    "SELECT hieu_luc FROM records_chitiettailieu WHERE id = %s",
                    [detail.pk],
                )
                self.assertEqual(cursor.fetchone()[0], "INVALID")
            transaction.set_rollback(True)

        with connection.cursor() as cursor:
            cursor.execute("SELECT to_regclass('public.ai_tailieu')")
            self.assertIsNotNone(cursor.fetchone()[0])

    def test_wrong_preexisting_enum_definition_fails_before_conversion(self):
        migration = import_module("document_templates.migrations.0004_schema_scalars")
        detail = TaiLieuChiTiet.objects.create(
            dm_tai_lieu=self.category,
            tieu_de="Wrong enum definition probe",
            ngay_dang=date(2026, 1, 3),
        )

        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("DROP VIEW IF EXISTS ai_tailieu")
                cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
                cursor.execute(
                    "ALTER TABLE records_chitiettailieu ALTER COLUMN hien_thi TYPE varchar(30) "
                    "USING hien_thi::text"
                )
                cursor.execute(
                    "ALTER TYPE chitiettailieu_hienthi RENAME TO issue168_old_hienthi_enum"
                )
                cursor.execute(
                    "CREATE TYPE public.chitiettailieu_hienthi AS ENUM ('TAT_CA')"
                )

            with self.assertRaisesRegex(RuntimeError, "nhãn không khớp DDL"):
                migration.install_schema_scalars(None, SimpleNamespace(connection=connection))

            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT format_type(att.atttypid, att.atttypmod) "
                    "FROM pg_attribute att "
                    "WHERE att.attrelid = 'records_chitiettailieu'::regclass "
                    "AND att.attname = 'hien_thi'"
                )
                self.assertEqual(cursor.fetchone()[0], "character varying(30)")
                cursor.execute(
                    "SELECT enumlabel FROM pg_enum "
                    "WHERE enumtypid = 'chitiettailieu_hienthi'::regtype "
                    "ORDER BY enumsortorder"
                )
                self.assertEqual(cursor.fetchall(), [("TAT_CA",)])
                cursor.execute(
                    "SELECT hien_thi FROM records_chitiettailieu WHERE id = %s",
                    [detail.pk],
                )
                self.assertEqual(cursor.fetchone()[0], "TAT_CA")
            transaction.set_rollback(True)

        with connection.cursor() as cursor:
            cursor.execute("SELECT to_regclass('public.ai_tailieu')")
            self.assertIsNotNone(cursor.fetchone()[0])


class DocumentTemplateSchemaMigrationIdempotenceTests(TestCase):
    def test_both_schema_installers_are_idempotent(self):
        documents = import_module("documents.migrations.0009_schema_scalars")
        templates = import_module("document_templates.migrations.0004_schema_scalars")

        documents.install_schema_scalars(None, SimpleNamespace(connection=connection))
        documents.install_schema_scalars(None, SimpleNamespace(connection=connection))
        templates.install_schema_scalars(None, SimpleNamespace(connection=connection))
        templates.install_schema_scalars(None, SimpleNamespace(connection=connection))

        with connection.cursor() as cursor:
            for table, trigger_name in (
                ("documents_vanbanden", "trg_vanbanden_updated_at"),
                ("documents_vanbandi", "trg_vanbandi_updated_at"),
                ("records_tailieu", "trg_tailieu_updated_at"),
                ("records_loaitailieu", "trg_loaitailieu_updated_at"),
                ("records_chitiettailieu", "trg_chitiettailieu_updated_at"),
            ):
                cursor.execute(
                    "SELECT COUNT(*) FROM pg_trigger trigger "
                    "JOIN pg_class relation ON relation.oid = trigger.tgrelid "
                    "WHERE relation.relname = %s AND trigger.tgname = %s "
                    "AND NOT trigger.tgisinternal",
                    [table, trigger_name],
                )
                self.assertEqual(cursor.fetchone()[0], 1)
