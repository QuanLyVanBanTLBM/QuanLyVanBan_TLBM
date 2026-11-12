"""Quyền xuất danh bạ Phòng ban (export_donvi): gán ADMIN, BGD, TP; khớp release_DDL.sql; API xuất theo quyền."""
import importlib
from pathlib import Path

from django.apps import apps as django_apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from rest_framework.test import APIClient

migration = importlib.import_module("authorization.migrations.0012_grant_export_donvi_tp_bgd")
DDL_PATH = Path(settings.BASE_DIR).parent / "docs" / "common" / "database" / "release_DDL.sql"


class SchemaEditorStub:
    connection = connection


def groups_with(codename):
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT g.ma_nhom_quyen FROM auth_group_permissions gp "
            "JOIN auth_group g ON g.id = gp.group_id JOIN auth_permission p ON p.id = gp.permission_id "
            "WHERE p.codename = %s ORDER BY g.ma_nhom_quyen",
            [codename],
        )
        return [row[0] for row in cursor.fetchall()]


class ExportDonViGrantTest(TestCase):
    def test_granted_to_admin_bgd_and_tp_only(self):
        self.assertEqual(groups_with("export_donvi"), ["ADMIN", "BGD", "TP"])

    def test_same_groups_as_export_cbnv(self):
        self.assertEqual(groups_with("export_donvi"), groups_with("export_cbnv"))

    def test_migration_is_idempotent_and_reversible(self):
        migration.grant_export_donvi(django_apps, SchemaEditorStub())
        migration.grant_export_donvi(django_apps, SchemaEditorStub())
        self.assertEqual(groups_with("export_donvi"), ["ADMIN", "BGD", "TP"])
        migration.revoke_export_donvi(django_apps, SchemaEditorStub())
        self.assertEqual(groups_with("export_donvi"), ["ADMIN"])
        migration.grant_export_donvi(django_apps, SchemaEditorStub())
        self.assertEqual(groups_with("export_donvi"), ["ADMIN", "BGD", "TP"])

    def test_release_ddl_grants_tp_and_bgd(self):
        ddl = DDL_PATH.read_text(encoding="utf-8")
        for code in ("TP", "BGD"):
            block = ddl[ddl.index(f"g.ma_nhom_quyen = '{code}'"):]
            block = block[: block.index(";")]
            self.assertIn("'export_donvi'", block, code)
        for code in ("VT", "CV"):
            block = ddl[ddl.index(f"g.ma_nhom_quyen = '{code}'"):]
            block = block[: block.index(";")]
            self.assertNotIn("'export_donvi'", block, code)

    def test_export_api_allows_tp_and_denies_cv(self):
        User = get_user_model()
        from django.contrib.auth.models import Group

        for code, name, expected in (
            ("TP", "Trưởng phòng", 200),
            ("BGD", "Ban Giám đốc", 200),
            ("CV", "Chuyên viên", 403),
            ("VT", "Văn thư", 403),
        ):
            user = User.objects.create_user(
                username=f"exp_{code}", email=f"exp_{code}@donvi.gov.vn", password="TestOnly12345",
            )
            user.groups.add(Group.objects.get(name=name))
            client = APIClient()
            client.force_authenticate(user=user)
            response = client.get("/api/organizations/units/export/")
            self.assertEqual(response.status_code, expected, code)
