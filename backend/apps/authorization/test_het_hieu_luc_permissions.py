"""Quyền xem/xử lý văn bản hết hiệu lực: có trong DB dựng bằng migration, đúng nhóm, khớp release_DDL.sql."""
import importlib
import re
from pathlib import Path

from django.apps import apps as django_apps
from django.conf import settings
from django.contrib.auth.models import Permission
from django.db import connection
from django.test import TestCase

migration = importlib.import_module("authorization.migrations.0016_het_hieu_luc_permissions")
DDL_PATH = Path(settings.BASE_DIR).parent / "docs" / "common" / "database" / "release_DDL.sql"
EXPECTED_GROUPS = {
    "view_het_hieu_luc_vanbanden": ["ADMIN", "VT"],
    "view_het_hieu_luc_vanbandi": ["ADMIN", "VT"],
    "manage_het_hieu_luc_vanbanden": ["ADMIN"],
    "manage_het_hieu_luc_vanbandi": ["ADMIN"],
}


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


def module_of(codename):
    with connection.cursor() as cursor:
        cursor.execute("SELECT name, module_ten FROM auth_permission WHERE codename = %s", [codename])
        return cursor.fetchone()


class HetHieuLucPermissionTest(TestCase):
    def test_permissions_exist_with_labels_and_modules(self):
        self.assertEqual(module_of("view_het_hieu_luc_vanbanden"), ("Xem văn bản đến hết hiệu lực", "Văn bản đến"))
        self.assertEqual(module_of("view_het_hieu_luc_vanbandi"), ("Xem văn bản đi hết hiệu lực", "Văn bản đi"))
        self.assertEqual(
            module_of("manage_het_hieu_luc_vanbanden"), ("Xử lý (sửa, xóa) văn bản đến hết hiệu lực", "Văn bản đến")
        )
        self.assertEqual(
            module_of("manage_het_hieu_luc_vanbandi"), ("Xử lý (sửa, xóa) văn bản đi hết hiệu lực", "Văn bản đi")
        )

    def test_granted_to_expected_groups_only(self):
        for codename, groups in EXPECTED_GROUPS.items():
            self.assertEqual(groups_with(codename), groups, codename)

    def test_migration_is_idempotent(self):
        migration.add_permissions(django_apps, SchemaEditorStub())
        migration.add_permissions(django_apps, SchemaEditorStub())
        self.assertEqual(Permission.objects.filter(codename__in=EXPECTED_GROUPS).count(), 4)
        for codename, groups in EXPECTED_GROUPS.items():
            self.assertEqual(groups_with(codename), groups, codename)

    def test_migration_matches_expected_groups(self):
        self.assertEqual(migration.GROUP_CODES, EXPECTED_GROUPS)

    def test_release_ddl_seeds_the_same_permissions_and_clerk_mapping(self):
        ddl = DDL_PATH.read_text(encoding="utf-8")
        for name, codename, module in migration.PERMISSIONS:
            self.assertRegex(ddl, rf"'{re.escape(name)}',\s*'{codename}',\s*'{re.escape(module)}'")
        clerk_block = ddl[ddl.index("g.ma_nhom_quyen = 'VT'"):]
        clerk_block = clerk_block[: clerk_block.index(";")]
        for codename, groups in EXPECTED_GROUPS.items():
            self.assertEqual(f"'{codename}'" in clerk_block, "VT" in groups, codename)
