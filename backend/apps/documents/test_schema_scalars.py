"""Database contract tests for document scalar defaults and updated_at behavior."""

from importlib import import_module
from types import SimpleNamespace

from django.db import connection, transaction
from django.test import TestCase
from django.utils import timezone

from accounts.models import Employee
from documents.models import VanBanDen


class DocumentSchemaScalarTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = Employee.objects.create_user(username="schema_scalar_user", password="pw")

    @staticmethod
    def _replacement_link_check_state():
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT pg_get_constraintdef(oid), convalidated FROM pg_constraint "
                "WHERE conrelid = 'documents_vanbanden'::regclass "
                "AND conname = 'chk_vanbanden_link_thay_the'"
            )
            return cursor.fetchone()

    @staticmethod
    def _view_definition(name):
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_get_viewdef(to_regclass(%s), true)", [f"public.{name}"])
            return cursor.fetchone()[0]

    def test_raw_insert_defaults_and_updated_at_trigger(self):
        with connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO documents_vanbanden
                       (nam, so_hieu, so_thu_tu, ngay_den, trich_yeu, hieu_luc, nguoi_tao_id)
                   VALUES (%s, %s, %s, %s, %s, %s::hieu_luc_status, %s)
                   RETURNING id, pham_vi, hien_thi, gui_mail_toan_he_thong, created_at, updated_at""",
                [2094, "SCALAR-DEN-1", 1, timezone.now(), "Raw SQL document", "CON_HIEU_LUC", self.user.pk],
            )
            document_id, pham_vi, hien_thi, gui_mail, created_at, updated_at = cursor.fetchone()

            self.assertEqual((pham_vi, hien_thi, gui_mail), ("NOI_BO", True, False))
            self.assertGreater(created_at.year, 2000)
            self.assertGreater(updated_at.year, 2000)

            cursor.execute(
                """UPDATE documents_vanbanden
                   SET updated_at = %s, trich_yeu = %s
                   WHERE id = %s RETURNING updated_at""",
                ["2000-01-01T00:00:00+00:00", "Trigger updated this row", document_id],
            )
            triggered_at = cursor.fetchone()[0]
            self.assertGreater(triggered_at.year, 2000)

            cursor.execute(
                """INSERT INTO documents_vanbanden_attachment (document_id, name, path)
                   VALUES (%s, %s, %s) RETURNING is_deleted, created_at""",
                [document_id, "raw.pdf", "raw.pdf"],
            )
            is_deleted, attachment_created_at = cursor.fetchone()
            self.assertFalse(is_deleted)
            self.assertGreater(attachment_created_at.year, 2000)

            cursor.execute(
                """INSERT INTO documents_access_log
                       (document_type, document_id, user_id, hanh_dong)
                   VALUES ('vanbanden', %s, %s, 'XEM') RETURNING created_at""",
                [document_id, self.user.pk],
            )
            self.assertGreater(cursor.fetchone()[0].year, 2000)

            cursor.execute(
                """INSERT INTO documents_vanbandi
                       (nam, so_hieu, so_thu_tu, ngay_ban_hanh, ngay_van_ban,
                        trich_yeu, hieu_luc, nguoi_tao_id)
                   VALUES (%s, %s, %s, %s, %s, %s, %s::hieu_luc_status, %s)
                   RETURNING id""",
                [2094, "SCALAR-DI-1", 1, timezone.now(), timezone.now(),
                 "Raw SQL outgoing document", "CON_HIEU_LUC", self.user.pk],
            )
            outgoing_id = cursor.fetchone()[0]
            cursor.execute(
                """UPDATE documents_vanbandi SET updated_at = %s
                   WHERE id = %s RETURNING updated_at""",
                ["2000-01-01T00:00:00+00:00", outgoing_id],
            )
            self.assertGreater(cursor.fetchone()[0].year, 2000)

            cursor.execute(
                """SELECT pg_get_indexdef(index_class.oid)
                   FROM pg_class index_class
                   JOIN pg_namespace namespace ON namespace.oid = index_class.relnamespace
                   WHERE namespace.nspname = 'public' AND index_class.relname = 'idx_viewlog_document'"""
            )
            self.assertIn("(document_type, document_id)", cursor.fetchone()[0])

        scalar_migration = import_module("documents.migrations.0009_schema_scalars")
        scalar_migration.install_schema_scalars(None, SimpleNamespace(connection=connection))

    def test_invalid_enum_value_fails_preflight_before_conversion(self):
        scalar_migration = import_module("documents.migrations.0009_schema_scalars")
        document = VanBanDen.objects.create(
            nam=2093,
            so_hieu="SCALAR-DEN-2",
            so_thu_tu=1,
            trich_yeu="Invalid enum preflight probe",
            nguoi_tao=self.user,
        )
        view_definition = self._view_definition("ai_vanbanden")
        link_check_state = self._replacement_link_check_state()
        self.assertIsNotNone(view_definition)
        self.assertIsNotNone(link_check_state)

        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("DROP VIEW IF EXISTS ai_vanbanden")
                cursor.execute(
                    "ALTER TABLE documents_vanbanden "
                    "DROP CONSTRAINT chk_vanbanden_link_thay_the"
                )
                cursor.execute(
                    "ALTER TABLE documents_vanbanden ALTER COLUMN hieu_luc TYPE varchar(20) "
                    "USING hieu_luc::text"
                )
                cursor.execute(
                    "UPDATE documents_vanbanden SET hieu_luc = 'INVALID' WHERE id = %s",
                    [document.pk],
                )

            with self.assertRaisesRegex(RuntimeError, r"documents_vanbanden\.hieu_luc: 1"):
                scalar_migration.install_schema_scalars(
                    None, SimpleNamespace(connection=connection)
                )

            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT format_type(att.atttypid, att.atttypmod) "
                    "FROM pg_attribute att "
                    "WHERE att.attrelid = 'documents_vanbanden'::regclass "
                    "AND att.attname = 'hieu_luc'"
                )
                self.assertEqual(cursor.fetchone()[0], "character varying(20)")
                cursor.execute(
                    "SELECT hieu_luc FROM documents_vanbanden WHERE id = %s",
                    [document.pk],
                )
                self.assertEqual(cursor.fetchone()[0], "INVALID")
            transaction.set_rollback(True)

        with connection.cursor() as cursor:
            cursor.execute("SELECT to_regclass('public.ai_vanbanden')")
            self.assertIsNotNone(cursor.fetchone()[0])
        self.assertEqual(self._view_definition("ai_vanbanden"), view_definition)
        self.assertEqual(self._replacement_link_check_state(), link_check_state)

    def test_dependent_view_blocks_enum_conversion_preflight(self):
        scalar_migration = import_module("documents.migrations.0009_schema_scalars")
        view_definition = self._view_definition("ai_vanbanden")
        link_check_state = self._replacement_link_check_state()
        self.assertIsNotNone(view_definition)
        self.assertIsNotNone(link_check_state)

        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("DROP VIEW IF EXISTS ai_vanbanden")
                cursor.execute(
                    "ALTER TABLE documents_vanbanden "
                    "DROP CONSTRAINT chk_vanbanden_link_thay_the"
                )
                cursor.execute(
                    "ALTER TABLE documents_vanbanden ALTER COLUMN hieu_luc TYPE varchar(20) "
                    "USING hieu_luc::text"
                )
                cursor.execute(
                    "CREATE VIEW issue168_c2a_enum_dependency AS "
                    "SELECT hieu_luc FROM documents_vanbanden"
                )

            with self.assertRaisesRegex(RuntimeError, "view phụ thuộc"):
                scalar_migration.install_schema_scalars(
                    None, SimpleNamespace(connection=connection)
                )
            transaction.set_rollback(True)

        with connection.cursor() as cursor:
            cursor.execute("SELECT to_regclass('public.ai_vanbanden')")
            self.assertIsNotNone(cursor.fetchone()[0])
            cursor.execute("SELECT to_regclass('public.issue168_c2a_enum_dependency')")
            self.assertIsNone(cursor.fetchone()[0])
        self.assertEqual(self._view_definition("ai_vanbanden"), view_definition)
        self.assertEqual(self._replacement_link_check_state(), link_check_state)
