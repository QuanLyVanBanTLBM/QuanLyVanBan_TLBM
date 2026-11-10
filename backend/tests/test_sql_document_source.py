import os
import runpy
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.conf import settings
from django.db import connections
from django.test import TestCase

from backend.services.sql_document_source import (
    SqlDocumentAccessError,
    accessible_documents,
    verify_sql_schema,
)


User = get_user_model()


def grant_codename(user, codename):
    user.user_permissions.add(Permission.objects.get(codename=codename))


class FakeCursor:
    def __init__(self, columns=(), rows=(), fetchone_row=None):
        self.description = [(column,) for column in columns]
        self.rows = rows
        self.fetchone_row = fetchone_row
        self.executed = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, query, params=None):
        self.executed.append((query, params))

    def fetchall(self):
        return self.rows

    def fetchone(self):
        return self.fetchone_row


class FakeReadonlyConnection:
    def __init__(self, cursors):
        self.cursors = iter(cursors)
        self.used_cursors = []

    def cursor(self):
        cursor = next(self.cursors)
        self.used_cursors.append(cursor)
        return cursor


class FakeConnections:
    def __init__(self, readonly):
        self.databases = {"readonly": {}}
        self.readonly = readonly

    def __getitem__(self, alias):
        if alias != "readonly":
            raise AssertionError(f"Unexpected database alias: {alias}")
        return self.readonly


class SqlDocumentSourceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="sql_ai", password="test-password")
        grant_codename(self.user, "use_aiassistant")

    @patch("backend.services.sql_document_source.is_postgres_source", return_value=True)
    def test_missing_ai_permission_fails_before_database_access(self, _is_postgres):
        self.user.user_permissions.clear()
        with self.assertRaises(SqlDocumentAccessError):
            accessible_documents(self.user)

    @patch("backend.services.sql_document_source.is_postgres_source", return_value=True)
    def test_reads_only_permitted_view_and_never_selects_attachment_columns(self, _is_postgres):
        grant_codename(self.user, "view_vanbanden")
        role_cursor = FakeCursor(fetchone_row=("qlvb_readonly", True, False, False))
        cursor = FakeCursor(
            columns=("source_type", "source_id", "so_hieu", "trich_yeu"),
            rows=(("vanbanden", 8, "01/AI", "Thông báo nội bộ"),),
        )
        readonly = FakeReadonlyConnection([role_cursor, cursor])
        db_connections = FakeConnections(readonly)
        with (
            patch("backend.services.sql_document_source.connections", db_connections),
            patch("backend.services.sql_document_source.transaction.atomic", return_value=nullcontext()),
        ):
            rows = accessible_documents(self.user)

        self.assertEqual([row["source_type"] for row in rows], ["vanbanden"])
        sql = cursor.executed[0][0]
        self.assertIn("transaction_read_only", role_cursor.executed[0][0])
        self.assertIn("pg_class", role_cursor.executed[0][0])
        self.assertIn("FROM ai_vanbanden", sql)
        self.assertNotIn("file_dinh_kem", sql)
        self.assertNotIn("documents_vanbanden ", sql)
        self.assertNotIn("vanbanmat", sql)

    @patch("backend.services.sql_document_source.is_postgres_source", return_value=True)
    def test_rejects_wrong_or_privileged_database_role_before_reading_a_view(self, _is_postgres):
        grant_codename(self.user, "view_vanbanden")
        role_cursor = FakeCursor(fetchone_row=("postgres", True, True, True))
        readonly = FakeReadonlyConnection([role_cursor])
        db_connections = FakeConnections(readonly)
        with (
            patch("backend.services.sql_document_source.connections", db_connections),
            patch("backend.services.sql_document_source.transaction.atomic", return_value=nullcontext()),
        ):
            with self.assertRaisesRegex(SqlDocumentAccessError, "qlvb_readonly"):
                accessible_documents(self.user)

        self.assertEqual(len(readonly.used_cursors), 1)
        self.assertIn("FROM pg_roles", role_cursor.executed[0][0])

    @patch("backend.services.sql_document_source.is_postgres_source", return_value=True)
    def test_tailieu_requires_host_employee_identity_and_sets_transaction_local_context(self, _is_postgres):
        grant_codename(self.user, "view_tailieu")
        with self.assertRaisesRegex(SqlDocumentAccessError, "mã nhân viên"):
            accessible_documents(self.user)

        role_cursor = FakeCursor(fetchone_row=("qlvb_readonly", True, False, False))
        identity_cursor = FakeCursor()
        view_cursor = FakeCursor(
            columns=("source_type", "source_id", "so_hieu", "trich_yeu"),
            rows=(("tailieu", 12, "TL-12", "Quy chế nội bộ"),),
        )
        readonly = FakeReadonlyConnection([role_cursor, identity_cursor, view_cursor])
        db_connections = FakeConnections(readonly)
        with (
            patch("backend.services.sql_document_source.connections", db_connections),
            patch("backend.services.sql_document_source.transaction.atomic", return_value=nullcontext()),
        ):
            rows = accessible_documents(self.user, employee_id=42)

        self.assertEqual([row["source_type"] for row in rows], ["tailieu"])
        self.assertIn("set_config('qlvb.employee_id'", identity_cursor.executed[0][0])
        self.assertEqual(identity_cursor.executed[0][1], ["42"])
        self.assertIn("FROM ai_tailieu", view_cursor.executed[0][0])
        self.assertNotIn("records_chitiettailieu ", view_cursor.executed[0][0])
        self.assertNotIn("file_dinh_kem", view_cursor.executed[0][0])

    @patch("backend.services.sql_document_source.is_postgres_source", return_value=False)
    def test_schema_verification_is_skipped_for_non_postgres_connection(self, _is_postgres):
        self.assertEqual(verify_sql_schema()["status"], "skipped")


class ReadonlyAliasSettingsTests(TestCase):
    settings_path = Path(settings.BASE_DIR) / "config" / "settings.py"

    def load_settings(self, **env):
        base = {"DJANGO_SECRET_KEY": "test-only", "DB_NAME": "qlvb_x", "DB_HOST": "db-host", "DB_PORT": "6543"}
        with patch.dict(os.environ, {**base, **env}, clear=False), patch("dotenv.load_dotenv"):
            for name in ("DB_READONLY_USER", "DB_READONLY_PASSWORD", "DB_READONLY_NAME", "DB_READONLY_HOST", "DB_READONLY_PORT"):
                if name not in env:
                    os.environ.pop(name, None)
            return runpy.run_path(str(self.settings_path))["DATABASES"]

    def test_alias_is_absent_without_readonly_user_and_never_reuses_default_user(self):
        databases = self.load_settings(DB_USER="app_user", DB_PASSWORD="app_secret")
        self.assertNotIn("readonly", databases)

    def test_alias_uses_dedicated_role_with_read_only_session_and_default_fallbacks(self):
        databases = self.load_settings(DB_USER="app_user", DB_READONLY_USER="ro_user", DB_READONLY_PASSWORD="ro_secret")
        readonly = databases["readonly"]
        self.assertEqual(readonly["USER"], "ro_user")
        self.assertEqual(readonly["PASSWORD"], "ro_secret")
        self.assertEqual((readonly["NAME"], readonly["HOST"], readonly["PORT"]), ("qlvb_x", "db-host", "6543"))
        self.assertEqual(readonly["OPTIONS"]["options"], "-c default_transaction_read_only=on")

    def test_readonly_overrides_take_precedence(self):
        databases = self.load_settings(DB_READONLY_USER="ro_user", DB_READONLY_NAME="other", DB_READONLY_HOST="ro-host", DB_READONLY_PORT="7000")
        readonly = databases["readonly"]
        self.assertEqual((readonly["NAME"], readonly["HOST"], readonly["PORT"]), ("other", "ro-host", "7000"))

    def test_ai_sql_fails_closed_when_alias_is_not_configured(self):
        user = User.objects.create_user(username="ai_no_ro", password="test-password")
        grant_codename(user, "use_aiassistant")
        grant_codename(user, "view_vanbanden")
        with patch.dict(connections.databases, clear=False) as databases:
            databases.pop("readonly", None)
            with self.assertRaises(SqlDocumentAccessError):
                accessible_documents(user)
            self.assertEqual(verify_sql_schema()["status"], "mismatch")

