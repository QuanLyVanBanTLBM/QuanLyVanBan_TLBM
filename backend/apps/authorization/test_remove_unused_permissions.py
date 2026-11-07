"""
Migration 0018 gỡ 3 mã quyền không có chức năng dùng (release_DDL.sql [GQVC]): seed, DDL và DB sau migrate
không còn các mã này; migration xóa được quyền cùng lượt gán cho nhóm và người dùng, chạy lại không lỗi.
"""
import re
from importlib import import_module
from pathlib import Path

from django.apps import apps as django_apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.db import connection
from django.test import TestCase

from authorization.rbac_seed import EXTRA_GROUP_PERMISSIONS, EXTRA_PERMISSIONS, GROUP_PERMISSIONS, PERMISSIONS

migration = import_module("authorization.migrations.0018_remove_unused_permissions")
REMOVED = {"toggle_status_hoso", "manage_documents_hoso", "send_wish_sinhnhat"}
DDL_PATH = Path(settings.BASE_DIR).parent / "docs" / "common" / "database" / "release_DDL.sql"
ROLES_DIR = Path(settings.BASE_DIR).parent / "frontend" / "src" / "i18n" / "roles"


class SchemaEditorStub:
    connection = connection

    @staticmethod
    def quote_name(name):
        return connection.ops.quote_name(name)


class RemoveUnusedPermissionsTest(TestCase):
    def test_seed_has_no_removed_codenames(self):
        codenames = {codename for _, codename, _ in [*PERMISSIONS, *EXTRA_PERMISSIONS]}
        self.assertFalse(codenames & REMOVED)
        for mapping in (GROUP_PERMISSIONS, EXTRA_GROUP_PERMISSIONS):
            for group_codenames in mapping.values():
                self.assertFalse(set(group_codenames) & REMOVED)

    def test_release_ddl_and_labels_have_no_removed_codenames(self):
        ddl = DDL_PATH.read_text(encoding="utf-8")
        # Chú thích đầu file và mục lịch sử [VTQ] vẫn nhắc tên mã; chỉ kiểm các dòng giá trị SQL.
        sql_literals = set(re.findall(r"^\s+'(\w+)',?\s*$", ddl, flags=re.MULTILINE))
        self.assertFalse(sql_literals & REMOVED)
        for name in ("vi.json", "en.json"):
            text = (ROLES_DIR / name).read_text(encoding="utf-8")
            for code in REMOVED:
                self.assertNotIn(f'"{code}"', text)

    def test_database_after_migrate_has_no_removed_codenames(self):
        self.assertFalse(Permission.objects.filter(codename__in=REMOVED).exists())

    def test_migration_removes_permissions_with_group_and_user_grants_and_is_idempotent(self):
        with connection.cursor() as cursor:
            for codename in REMOVED:
                cursor.execute(
                    "INSERT INTO auth_permission (name, codename, module_ten) VALUES (%s, %s, %s)",
                    [codename, codename, "Thử"],
                )
        permissions = Permission.objects.filter(codename__in=REMOVED)
        self.assertEqual(permissions.count(), 3)
        Group.objects.get(name="Văn thư").permissions.add(*permissions)
        user = get_user_model().objects.create_user(username="gqvc_user", password="Test@12345")
        user.user_permissions.add(*permissions)
        kept = Group.objects.get(name="Văn thư").permissions.exclude(codename__in=REMOVED).count()

        migration.remove_unused_permissions(django_apps, SchemaEditorStub())
        migration.remove_unused_permissions(django_apps, SchemaEditorStub())

        self.assertFalse(Permission.objects.filter(codename__in=REMOVED).exists())
        self.assertFalse(user.user_permissions.filter(codename__in=REMOVED).exists())
        self.assertEqual(Group.objects.get(name="Văn thư").permissions.count(), kept)
