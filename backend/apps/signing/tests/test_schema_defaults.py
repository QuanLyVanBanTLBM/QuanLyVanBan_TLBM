"""Database contract tests for signing defaults, enums and updated_at behavior."""

from importlib import import_module
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.db import connection, transaction
from django.db.models.fields import NOT_PROVIDED
from django.test import TestCase
from django.utils import timezone

from signing.models import (
    SigningAttempt,
    SigningAuditLog,
    SigningChangeMessage,
    SigningChangeThread,
    SigningKey,
    SigningKeyUnlock,
    SigningManifest,
    SigningNotification,
    SigningProcess,
    SigningProcessStep,
    SigningProcessStepSigner,
    SigningRequest,
    SigningRequestStep,
    SigningRequestStepSigner,
    SigningSignature,
)


class SigningSchemaDefaultsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="issue168_c2b_schema_defaults", password="test-only"
        )

    def test_model_database_defaults_exist_in_catalog(self):
        models = (
            SigningAttempt,
            SigningAuditLog,
            SigningChangeMessage,
            SigningChangeThread,
            SigningKey,
            SigningKeyUnlock,
            SigningManifest,
            SigningNotification,
            SigningProcess,
            SigningProcessStep,
            SigningProcessStepSigner,
            SigningRequest,
            SigningRequestStep,
            SigningRequestStepSigner,
            SigningSignature,
        )
        with connection.cursor() as cursor:
            for model in models:
                for field in model._meta.local_fields:
                    if field.db_default is NOT_PROVIDED:
                        continue
                    cursor.execute(
                        "SELECT pg_get_expr(default_value.adbin, default_value.adrelid) "
                        "FROM pg_class AS pg_table "
                        "JOIN pg_namespace AS table_namespace ON table_namespace.oid = pg_table.relnamespace "
                        "JOIN pg_attribute AS attribute ON attribute.attrelid = pg_table.oid "
                        "LEFT JOIN pg_attrdef AS default_value "
                        "ON default_value.adrelid = pg_table.oid AND default_value.adnum = attribute.attnum "
                        "WHERE table_namespace.nspname = 'public' AND pg_table.relname = %s "
                        "AND attribute.attname = %s AND attribute.attnum > 0 AND NOT attribute.attisdropped",
                        [model._meta.db_table, field.column],
                    )
                    row = cursor.fetchone()
                    self.assertIsNotNone(row, f"Missing catalog column {model._meta.db_table}.{field.column}")
                    self.assertIsNotNone(row[0], f"Missing DB default {model._meta.db_table}.{field.column}")

    def test_raw_inserts_use_document_kind_and_canonical_defaults(self):
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO signing_process (ma_quy_trinh, ten_quy_trinh, pham_vi, nguoi_tao_id) "
                "VALUES (%s, %s, %s, %s) "
                "RETURNING id, mo_ta, phien_ban, trang_thai, created_at, updated_at",
                ["C2B-DEFAULTS", "Schema defaults", "CONG_TY", self.user.pk],
            )
            process_id, description, version, state, created_at, updated_at = cursor.fetchone()
            self.assertEqual((description, version, state), ("", 1, "NHAP"))
            self.assertGreater(created_at.year, 2000)
            self.assertGreater(updated_at.year, 2000)

            cursor.execute(
                "INSERT INTO signing_request "
                "(document_type, document_id, quy_trinh_id, phien_ban_quy_trinh, nguoi_tao_id) "
                "VALUES (%s, %s, %s, %s, %s) "
                "RETURNING trang_thai, ly_do_tu_choi, ly_do_huy, ghi_chu, created_at, updated_at",
                ["vanbandi", 89001, process_id, 1, self.user.pk],
            )
            request_state, rejected, cancelled, note, request_created, request_updated = cursor.fetchone()
            self.assertEqual((request_state, rejected, cancelled, note), ("NHAP", "", "", ""))
            self.assertGreater(request_created.year, 2000)
            self.assertGreater(request_updated.year, 2000)

            cursor.execute(
                "INSERT INTO signing_key "
                "(nguoi_so_huu_id, ma_khoa, dau_van_tay, khoa_cong_khai, ngay_hieu_luc) "
                "VALUES (%s, %s, %s, %s, %s) "
                "RETURNING id, thuat_toan, trang_thai, ghi_chu, created_at",
                [self.user.pk, "C2B-KEY", "C2B-FINGERPRINT", "public-key", timezone.now()],
            )
            key_id, algorithm, key_state, key_note, key_created = cursor.fetchone()
            self.assertEqual((algorithm, key_state, key_note), ("Ed25519", "CHO_KICH_HOAT", ""))
            self.assertGreater(key_created.year, 2000)

            cursor.execute(
                "INSERT INTO signing_key_unlock "
                "(khoa_id, ma_bam_xac_minh_pin, khoa_bi_mat_ma_hoa, tham_so_kdf) "
                "VALUES (%s, %s, %s, %s::jsonb) RETURNING so_lan_sai, created_at, updated_at",
                [key_id, "verifier", "encrypted-share", "{}"],
            )
            failed_attempts, unlock_created, unlock_updated = cursor.fetchone()
            self.assertEqual(failed_attempts, 0)
            self.assertGreater(unlock_created.year, 2000)
            self.assertGreater(unlock_updated.year, 2000)

            cursor.execute(
                "UPDATE signing_key_unlock SET updated_at = %s WHERE khoa_id = %s RETURNING updated_at",
                ["2000-01-01T00:00:00+00:00", key_id],
            )
            self.assertGreater(cursor.fetchone()[0].year, 2000)

            cursor.execute(
                "SELECT format_type(attribute.atttypid, attribute.atttypmod) "
                "FROM pg_attribute AS attribute "
                "WHERE attribute.attrelid = 'public.signing_request'::regclass "
                "AND attribute.attname = 'document_type'"
            )
            self.assertEqual(cursor.fetchone()[0], "document_kind")

    def test_enum_catalog_and_adopted_schema_path_are_idempotent(self):
        migration = import_module("signing.migrations.0012_db_defaults_document_kind")
        schema_editor = SimpleNamespace(connection=connection)

        with connection.cursor() as cursor:
            for name, expected_labels in migration.SIGNING_ENUMS.items():
                cursor.execute(
                    "SELECT enum.enumlabel FROM pg_type AS typ "
                    "JOIN pg_namespace AS namespace ON namespace.oid = typ.typnamespace "
                    "JOIN pg_enum AS enum ON enum.enumtypid = typ.oid "
                    "WHERE namespace.nspname = 'public' AND typ.typname = %s "
                    "ORDER BY enum.enumsortorder",
                    [name],
                )
                self.assertEqual(tuple(row[0] for row in cursor.fetchall()), expected_labels, name)

            cursor.execute(
                "SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'signing_kieuky')"
            )
            self.assertFalse(cursor.fetchone()[0])

        migration.ensure_signing_enums_and_document_kind(None, schema_editor)
        migration.ensure_signing_key_unlock_updated_at_trigger(None, schema_editor)

    def test_noncanonical_enum_labels_are_rejected_without_rewrite(self):
        migration = import_module("signing.migrations.0012_db_defaults_document_kind")
        schema_editor = SimpleNamespace(connection=connection)

        with self.assertRaisesRegex(RuntimeError, r"Canonical enum signing_scope differs"):
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute("ALTER TYPE public.signing_scope RENAME TO signing_scope_probe_old")
                    cursor.execute("CREATE TYPE public.signing_scope AS ENUM ('NOT_CANONICAL')")
                migration.ensure_signing_enums_and_document_kind(None, schema_editor)

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT enum.enumlabel FROM pg_type AS typ "
                "JOIN pg_namespace AS ns ON ns.oid = typ.typnamespace "
                "JOIN pg_enum AS enum ON enum.enumtypid = typ.oid "
                "WHERE ns.nspname = 'public' AND typ.typname = 'signing_scope' "
                "ORDER BY enum.enumsortorder"
            )
            self.assertEqual(tuple(row[0] for row in cursor.fetchall()), ("DEPARTMENT", "COMPANY"))

    def test_noncanonical_key_unlock_trigger_is_rejected_without_rewrite(self):
        migration = import_module("signing.migrations.0012_db_defaults_document_kind")
        schema_editor = SimpleNamespace(connection=connection)

        with self.assertRaisesRegex(RuntimeError, r"Existing signing_key_unlock updated_at trigger is not canonical"):
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(
                        "ALTER TABLE public.signing_key_unlock "
                        "DISABLE TRIGGER trg_signing_key_unlock_updated_at"
                    )
                migration.ensure_signing_key_unlock_updated_at_trigger(None, schema_editor)

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT trg.tgenabled FROM pg_trigger AS trg "
                "JOIN pg_class AS pg_table ON pg_table.oid = trg.tgrelid "
                "WHERE pg_table.oid = 'public.signing_key_unlock'::regclass "
                "AND trg.tgname = 'trg_signing_key_unlock_updated_at'"
            )
            self.assertEqual(cursor.fetchone()[0], "O")

    def test_conditional_key_unlock_trigger_is_rejected_without_rewrite(self):
        migration = import_module("signing.migrations.0012_db_defaults_document_kind")
        schema_editor = SimpleNamespace(connection=connection)

        with self.assertRaisesRegex(RuntimeError, r"Existing signing_key_unlock updated_at trigger is not canonical"):
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(
                        "DROP TRIGGER trg_signing_key_unlock_updated_at ON public.signing_key_unlock"
                    )
                    cursor.execute(
                        "CREATE TRIGGER trg_signing_key_unlock_updated_at "
                        "BEFORE UPDATE ON public.signing_key_unlock FOR EACH ROW "
                        "WHEN (NEW.so_lan_sai >= 0) EXECUTE FUNCTION public.set_updated_at()"
                    )
                migration.ensure_signing_key_unlock_updated_at_trigger(None, schema_editor)

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT trg.tgqual IS NULL FROM pg_trigger AS trg "
                "JOIN pg_class AS pg_table ON pg_table.oid = trg.tgrelid "
                "WHERE pg_table.oid = 'public.signing_key_unlock'::regclass "
                "AND trg.tgname = 'trg_signing_key_unlock_updated_at'"
            )
            self.assertTrue(cursor.fetchone()[0])

    def test_supported_document_kind_values_convert_without_row_loss(self):
        with connection.cursor() as cursor:
            cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
            cursor.execute(
                "ALTER TABLE public.signing_request ALTER COLUMN document_type TYPE varchar(20) "
                "USING document_type::text"
            )
            cursor.execute(
                "INSERT INTO signing_process (ma_quy_trinh, ten_quy_trinh, pham_vi, nguoi_tao_id) "
                "VALUES (%s, %s, %s, %s) RETURNING id",
                ["C2B-CONVERT", "Legacy document type", "CONG_TY", self.user.pk],
            )
            process_id = cursor.fetchone()[0]
            cursor.execute(
                "INSERT INTO signing_request "
                "(document_type, document_id, quy_trinh_id, phien_ban_quy_trinh, nguoi_tao_id) "
                "VALUES ('vanbandi', %s, %s, 1, %s) RETURNING id",
                [89003, process_id, self.user.pk],
            )
            request_id = cursor.fetchone()[0]
            cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")

        migration = import_module("signing.migrations.0012_db_defaults_document_kind")
        migration.ensure_signing_enums_and_document_kind(None, SimpleNamespace(connection=connection))

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT format_type(attribute.atttypid, attribute.atttypmod), request.document_type "
                "FROM pg_attribute AS attribute "
                "JOIN public.signing_request AS request ON request.id = %s "
                "WHERE attribute.attrelid = 'public.signing_request'::regclass "
                "AND attribute.attname = 'document_type'",
                [request_id],
            )
            self.assertEqual(cursor.fetchone(), ("document_kind", "vanbandi"))

    def test_invalid_document_kind_fails_before_type_conversion(self):
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO signing_process (ma_quy_trinh, ten_quy_trinh, pham_vi, nguoi_tao_id) "
                "VALUES (%s, %s, %s, %s) RETURNING id",
                ["C2B-INVALID-KIND", "Invalid kind preflight", "CONG_TY", self.user.pk],
            )
            process_id = cursor.fetchone()[0]
            cursor.execute(
                "INSERT INTO signing_request "
                "(document_type, document_id, quy_trinh_id, phien_ban_quy_trinh, nguoi_tao_id) "
                "VALUES ('vanbandi', %s, %s, 1, %s) RETURNING id",
                [89002, process_id, self.user.pk],
            )
            request_id = cursor.fetchone()[0]

        migration = import_module("signing.migrations.0012_db_defaults_document_kind")
        schema_editor = SimpleNamespace(connection=connection)
        with transaction.atomic():
            with connection.cursor() as cursor:
                # TestCase keeps a transaction open; flush deferred FK events before DDL.
                cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
                cursor.execute(
                    "ALTER TABLE public.signing_request ALTER COLUMN document_type TYPE varchar(20) "
                    "USING document_type::text"
                )
                cursor.execute(
                    "UPDATE public.signing_request SET document_type = 'unsupported' WHERE id = %s",
                    [request_id],
                )

            with self.assertRaisesRegex(RuntimeError, r"1 row\(s\) contain an unsupported value"):
                migration.ensure_signing_enums_and_document_kind(None, schema_editor)

            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT format_type(attribute.atttypid, attribute.atttypmod), document_type "
                    "FROM pg_attribute AS attribute "
                    "JOIN public.signing_request AS request ON request.id = %s "
                    "WHERE attribute.attrelid = 'public.signing_request'::regclass "
                    "AND attribute.attname = 'document_type'",
                    [request_id],
                )
                self.assertEqual(cursor.fetchone(), ("character varying(20)", "unsupported"))
