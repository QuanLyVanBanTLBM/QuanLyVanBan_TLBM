"""Quyền `view_all_trinhky`: có trong seed, gán đúng ba nhóm VT, BGD, ADMIN; migration 0013 idempotent."""
from importlib import import_module

from django.contrib.auth.models import Group, Permission
from django.db import connection
from django.test import TestCase

from authorization.models import GroupInfo
from authorization.rbac_seed import GROUP_PERMISSIONS, GROUPS, PERMISSIONS

migration = import_module("authorization.migrations.0013_add_view_all_trinhky_permission")
CODENAME = "view_all_trinhky"


class SchemaEditorStub:
    connection = connection


def nhom_co_quyen():
    return set(
        GroupInfo.objects.filter(pk__in=Group.objects.filter(permissions__codename=CODENAME).values("pk"))
        .values_list("ma_nhom_quyen", flat=True)
    )


class ViewAllTrinhKyPermissionTest(TestCase):
    def test_permission_exists_in_signing_module(self):
        permission = Permission.objects.get(codename=CODENAME)
        self.assertEqual(permission.name, "Xem tất cả hồ sơ trình ký")

    def test_granted_only_to_vt_bgd_admin(self):
        self.assertEqual(nhom_co_quyen(), {"VT", "BGD", "ADMIN"})
        self.assertEqual(
            {name for name, perms in GROUP_PERMISSIONS.items() if CODENAME in perms} | {"Quản trị hệ thống"},
            {ten for ten, ma in GROUPS if ma in ("VT", "BGD", "ADMIN")},
        )
        for ma in ("CV", "TP"):
            self.assertNotIn(ma, nhom_co_quyen())

    def test_vt_does_not_gain_audit_permission(self):
        vt = Group.objects.get(pk=GroupInfo.objects.get(ma_nhom_quyen="VT").pk)
        self.assertFalse(vt.permissions.filter(codename="view_signing_audit").exists())

    def test_migration_is_idempotent_and_restores_grants(self):
        vt = Group.objects.get(pk=GroupInfo.objects.get(ma_nhom_quyen="VT").pk)
        vt.permissions.remove(Permission.objects.get(codename=CODENAME))
        migration.add_view_all_trinhky(None, SchemaEditorStub)
        migration.add_view_all_trinhky(None, SchemaEditorStub)
        self.assertEqual(nhom_co_quyen(), {"VT", "BGD", "ADMIN"})
        self.assertEqual(Permission.objects.filter(codename=CODENAME).count(), 1)

    def test_migration_reverse_removes_permission(self):
        migration.remove_view_all_trinhky(None, SchemaEditorStub)
        self.assertFalse(Permission.objects.filter(codename=CODENAME).exists())
        migration.add_view_all_trinhky(None, SchemaEditorStub)
        self.assertEqual(nhom_co_quyen(), {"VT", "BGD", "ADMIN"})
