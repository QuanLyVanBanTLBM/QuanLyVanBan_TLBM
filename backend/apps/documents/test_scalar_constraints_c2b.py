from importlib import import_module
from types import SimpleNamespace
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.test import SimpleTestCase, TestCase

from documents.models import DocumentViewLog, VanBanDen, VanBanDi


class DocumentScalarValidatorTests(SimpleTestCase):
    def test_nonnegative_model_validators_remain_after_integer_field_changes(self):
        fields = (
            (VanBanDen, "nam"),
            (VanBanDen, "so_thu_tu"),
            (VanBanDi, "nam"),
            (VanBanDi, "so_thu_tu"),
            (DocumentViewLog, "document_id"),
        )
        for model, field_name in fields:
            with self.subTest(model=model.__name__, field=field_name):
                field = model._meta.get_field(field_name)
                with self.assertRaises(ValidationError):
                    field.run_validators(-1)


class DocumentReplacementLinkPreflightTests(SimpleTestCase):
    def test_invalid_links_refuse_before_any_ddl_and_report_counts_only(self):
        migration = import_module("documents.migrations.0011_reconcile_scalar_checks")
        cursor = _CountCursor([2, 1])
        editor = _SchemaEditor(cursor)

        with self.assertRaisesRegex(RuntimeError, r"documents_vanbanden: 2, documents_vanbandi: 1"):
            migration.preflight_document_constraints(None, editor)

        self.assertEqual(len(cursor.statements), 2)
        self.assertTrue(all(statement.startswith("SELECT count(*)") for statement in cursor.statements))
        self.assertNotIn("so_hieu", " ".join(cursor.statements))

    def test_wrong_boolean_precedence_and_changed_literal_are_not_canonical(self):
        migration = import_module("documents.migrations.0011_reconcile_scalar_checks")
        canonical = migration.EXPECTED_LINK_CHECK
        wrong_precedence = (
            "((hieu_luc <> 'HET_VA_THAY_THE'::hieu_luc_status) OR "
            "(link_thay_the IS NOT NULL)) AND (btrim((link_thay_the)::text) <> ''::text)"
        )
        wrong_literal = canonical.replace("'HET_VA_THAY_THE'", "'het_va_thay_the'")

        self.assertEqual(migration._normalize_link_check(canonical), canonical)
        self.assertNotEqual(migration._normalize_link_check(wrong_precedence), canonical)
        self.assertNotEqual(migration._normalize_link_check(wrong_literal), canonical)


class DocumentReplacementLinkDatabaseTests(TestCase):
    def test_release_ddl_and_migration_generated_checks_are_accepted(self):
        migration = import_module("documents.migrations.0011_reconcile_scalar_checks")
        expressions = (
            "hieu_luc <> 'HET_VA_THAY_THE' OR "
            "(link_thay_the IS NOT NULL AND BTRIM(link_thay_the) <> '')",
            "(hieu_luc <> 'HET_VA_THAY_THE') OR "
            "(link_thay_the IS NOT NULL AND btrim(link_thay_the) <> '')",
        )

        with connection.cursor() as cursor:
            for expression in expressions:
                table = f"issue168_link_probe_{uuid4().hex}"
                cursor.execute(
                    f"CREATE TEMP TABLE {table} "
                    "(hieu_luc hieu_luc_status NOT NULL, link_thay_the varchar(500))"
                )
                cursor.execute(
                    f"ALTER TABLE {table} ADD CONSTRAINT probe_check CHECK ({expression})"
                )
                cursor.execute(
                    "SELECT pg_get_expr(conbin, conrelid) FROM pg_constraint "
                    "WHERE conrelid = %s::regclass AND conname = 'probe_check'",
                    [f"pg_temp.{table}"],
                )
                self.assertEqual(
                    migration._normalize_link_check(cursor.fetchone()[0]),
                    migration.EXPECTED_LINK_CHECK,
                )

    def test_canonical_migration_constraints_pass_preflight(self):
        migration = import_module("documents.migrations.0011_reconcile_scalar_checks")

        migration.preflight_document_constraints(None, SimpleNamespace(connection=connection))

    def test_wrong_precedence_constraint_refuses_before_schema_data_or_history_changes(self):
        migration = import_module("documents.migrations.0011_reconcile_scalar_checks")
        document = VanBanDen.objects.create(
            nam=2097,
            so_hieu=f"C2B-PREFLIGHT-{uuid4().hex[:12]}",
            so_thu_tu=900000 + uuid4().int % 900000,
            trich_yeu="Preflight precedence probe",
            hieu_luc="CON_HIEU_LUC",
            link_thay_the="",
        )
        constraint = "chk_vanbanden_link_thay_the"
        with connection.cursor() as cursor:
            cursor.execute(
                f"ALTER TABLE documents_vanbanden DROP CONSTRAINT {constraint}"
            )
            cursor.execute(
                f"ALTER TABLE documents_vanbanden ADD CONSTRAINT {constraint} "
                "CHECK ((hieu_luc <> 'HET_VA_THAY_THE' OR link_thay_the IS NOT NULL) "
                "AND btrim(link_thay_the) <> '') NOT VALID"
            )
            cursor.execute(
                "SELECT (hieu_luc <> 'HET_VA_THAY_THE' OR "
                "(link_thay_the IS NOT NULL AND btrim(link_thay_the) <> '')), "
                "((hieu_luc <> 'HET_VA_THAY_THE' OR link_thay_the IS NOT NULL) "
                "AND btrim(link_thay_the) <> '') "
                "FROM documents_vanbanden WHERE id = %s",
                [document.pk],
            )
            self.assertEqual(cursor.fetchone(), (True, False))

        def snapshot():
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT conname, pg_get_expr(conbin, conrelid), convalidated "
                    "FROM pg_constraint WHERE conrelid = 'documents_vanbanden'::regclass "
                    "AND conname = %s",
                    [constraint],
                )
                schema = cursor.fetchone()
                cursor.execute(
                    "SELECT id, hieu_luc, link_thay_the FROM documents_vanbanden WHERE id = %s",
                    [document.pk],
                )
                data = cursor.fetchone()
                cursor.execute(
                    "SELECT app, name, applied FROM django_migrations "
                    "WHERE app = 'documents' ORDER BY name"
                )
                history = cursor.fetchall()
            return schema, data, history

        before = snapshot()
        queries = []

        def capture(execute, sql, params, many, context):
            queries.append(sql)
            return execute(sql, params, many, context)

        with connection.execute_wrapper(capture):
            with self.assertRaisesRegex(RuntimeError, "unexpected definition"):
                migration.preflight_document_constraints(
                    None, SimpleNamespace(connection=connection)
                )

        self.assertEqual(len(queries), 3)
        self.assertTrue(all(query.lstrip().upper().startswith("SELECT") for query in queries))
        self.assertTrue(all(query.lstrip().upper().startswith("SELECT COUNT(*)") for query in queries[:2]))
        self.assertEqual(snapshot(), before)

    def test_missing_incoming_replacement_link_is_rejected(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                VanBanDen.objects.create(
                    nam=2097,
                    so_hieu=f"C2B-DEN-{uuid4().hex[:12]}",
                    so_thu_tu=900000 + uuid4().int % 900000,
                    trich_yeu="Database constraint probe",
                    hieu_luc="HET_VA_THAY_THE",
                    link_thay_the=None,
                )

    def test_whitespace_only_outgoing_replacement_link_is_rejected(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                VanBanDi.objects.create(
                    nam=2097,
                    so_hieu=f"C2B-DI-{uuid4().hex[:12]}",
                    so_thu_tu=900000 + uuid4().int % 900000,
                    trich_yeu="Database constraint probe",
                    hieu_luc="HET_VA_THAY_THE",
                    link_thay_the="   ",
                )

    def test_generated_positive_database_checks_are_removed(self):
        old_checks = (
            ("documents_vanbanden", "documents_vanbanden_nam_check"),
            ("documents_vanbanden", "documents_vanbanden_so_thu_tu_check"),
            ("documents_vanbandi", "documents_vanbandi_nam_check"),
            ("documents_vanbandi", "documents_vanbandi_so_thu_tu_check"),
            ("documents_view_log", "documents_view_log_document_id_check"),
        )
        with connection.cursor() as cursor:
            for table, constraint in old_checks:
                with self.subTest(table=table, constraint=constraint):
                    cursor.execute(
                        "SELECT count(*) FROM pg_constraint "
                        "WHERE conrelid = %s::regclass AND conname = %s AND contype = 'c'",
                        [table, constraint],
                    )
                    self.assertEqual(cursor.fetchone()[0], 0)


class _CountCursor:
    def __init__(self, counts):
        self.counts = iter(counts)
        self.statements = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, statement, _params=None):
        self.statements.append(statement)

    def fetchone(self):
        return (next(self.counts),)


class _Connection:
    vendor = "postgresql"

    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self):
        return self._cursor


class _SchemaEditor:
    def __init__(self, cursor):
        self.connection = _Connection(cursor)
