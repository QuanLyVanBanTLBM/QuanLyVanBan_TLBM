"""
Nhật ký xem văn bản chỉ ADMIN và BGD xem được (release_DDL.sql [RLOG]): seed không còn view_read_log_*
ở VT và TP, TLBGD/KT/BGD/ADMIN giữ nguyên; migration 0010 gỡ trên DB đã seed từ trước, chạy lại không đổi
thêm gì, và reverse gán lại đúng ba lượt.
"""
from importlib import import_module

from django.contrib.auth.models import Group, Permission
from django.db import connection
from django.test import TestCase

from authorization.models import GroupInfo
from authorization.rbac_seed import GROUP_PERMISSIONS, SUPPLEMENTARY_GROUP_PERMISSIONS

migration = import_module("authorization.migrations.0010_remove_read_log_from_vt_tp")

READ_LOG = ("view_read_log_vanbanden", "view_read_log_vanbandi")


class SchemaEditorStub:
    connection = connection


def group_of(code):
    return Group.objects.get(pk=GroupInfo.objects.get(ma_nhom_quyen=code).pk)


def has(code, codename):
    return group_of(code).permissions.filter(codename=codename).exists()


class ReadLogPermissionTest(TestCase):
    def test_seed_removes_read_log_from_vt_and_tp(self):
        for codename in READ_LOG:
            self.assertNotIn(codename, GROUP_PERMISSIONS["Văn thư"])
            self.assertNotIn(codename, GROUP_PERMISSIONS["Trưởng phòng"])
        self.assertEqual(len(GROUP_PERMISSIONS["Văn thư"]), 28)
        self.assertEqual(len(GROUP_PERMISSIONS["Trưởng phòng"]), 25)

    def test_seed_keeps_read_log_for_bgd_admin_tlbgd_kt(self):
        for codename in READ_LOG:
            self.assertIn(codename, GROUP_PERMISSIONS["Ban Giám đốc"])
            self.assertTrue(has("ADMIN", codename))
            self.assertIn(codename, SUPPLEMENTARY_GROUP_PERMISSIONS["TLBGD"])
            self.assertIn(codename, SUPPLEMENTARY_GROUP_PERMISSIONS["KT"])

    def test_database_after_migrate_matches_seed(self):
        for codename in READ_LOG:
            self.assertFalse(has("VT", codename))
            self.assertFalse(has("TP", codename))
            self.assertTrue(has("BGD", codename))
            self.assertTrue(has("ADMIN", codename))

    def test_migration_removes_existing_grants_once(self):
        for code, codenames in (("VT", READ_LOG), ("TP", READ_LOG[:1])):
            for codename in codenames:
                group_of(code).permissions.add(Permission.objects.get(codename=codename))
        bgd_before = group_of("BGD").permissions.count()

        migration.remove_read_log(None, SchemaEditorStub)
        migration.remove_read_log(None, SchemaEditorStub)

        for codename in READ_LOG:
            self.assertFalse(has("VT", codename))
            self.assertFalse(has("TP", codename))
        self.assertEqual(group_of("BGD").permissions.count(), bgd_before)

    def test_reverse_regrants_exactly_three_rows(self):
        vt_before = group_of("VT").permissions.count()
        tp_before = group_of("TP").permissions.count()

        migration.restore_read_log(None, SchemaEditorStub)
        migration.restore_read_log(None, SchemaEditorStub)

        self.assertEqual(group_of("VT").permissions.count(), vt_before + 2)
        self.assertEqual(group_of("TP").permissions.count(), tp_before + 1)
        self.assertTrue(has("TP", "view_read_log_vanbanden"))
        self.assertFalse(has("TP", "view_read_log_vanbandi"))
