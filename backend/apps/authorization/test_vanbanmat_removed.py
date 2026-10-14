"""
DDL base bỏ văn bản mật (PR #81, Issue #83): seed còn đúng 77 quyền, không còn *_vanbanmat,
và migration 0003 gỡ được quyền văn bản mật trên DB đã seed từ trước.
"""
from importlib import import_module

from django.apps import apps as django_apps
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.db import connection
from django.test import TestCase

from authorization.rbac_seed import EXTRA_PERMISSIONS, GROUP_PERMISSIONS, PERMISSIONS

remove_vanbanmat = import_module("authorization.migrations.0003_remove_vanbanmat_permissions")


class SchemaEditorStub:
    connection = connection

    @staticmethod
    def quote_name(name):
        return connection.ops.quote_name(name)


class VanBanMatRemovedTest(TestCase):
    def test_seed_has_77_permissions_without_vanbanmat(self):
        codenames = {codename for _, codename, _ in [*PERMISSIONS, *EXTRA_PERMISSIONS]}
        self.assertEqual(len(codenames), 77)
        self.assertFalse([c for c in codenames if "vanbanmat" in c])
        for group_codenames in GROUP_PERMISSIONS.values():
            self.assertFalse([c for c in group_codenames if "vanbanmat" in c])

    def test_database_after_migrate_has_no_vanbanmat(self):
        self.assertFalse(Permission.objects.filter(codename__contains="vanbanmat").exists())
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM auth_permission WHERE module_ten <> ''")
            # Legacy 77 permissions remain; E2EE adds creation only, never a read override.
            self.assertEqual(cursor.fetchone()[0], 78)
        self.assertTrue(Permission.objects.filter(codename="create_confidential_document").exists())

    def test_migration_removes_existing_vanbanmat_permissions_and_grants(self):
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO auth_permission (name, codename, module_ten) VALUES (%s, %s, %s)",
                ["Xem văn bản mật", "view_vanbanmat", "Văn bản mật"],
            )
        permission = Permission.objects.get(codename="view_vanbanmat")
        Group.objects.get(name="Văn thư").permissions.add(permission)
        user = get_user_model().objects.create_user(username="vbm_user", password="Test@12345")
        user.user_permissions.add(permission)

        # SQLite không cho mở schema_editor trong transaction của TestCase; hàm chỉ cần connection và quote_name.
        remove_vanbanmat.remove_vanbanmat_permissions(django_apps, SchemaEditorStub())

        self.assertFalse(Permission.objects.filter(codename="view_vanbanmat").exists())
        self.assertFalse(Group.objects.get(name="Văn thư").permissions.filter(codename="view_vanbanmat").exists())
        self.assertFalse(user.user_permissions.filter(codename="view_vanbanmat").exists())
