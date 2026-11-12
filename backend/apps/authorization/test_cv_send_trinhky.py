"""
Issue #226: nhóm Chuyên viên có send_trinhky (release_DDL.sql [CVTK]); migration 0007 gán bổ sung
trên DB đã seed từ trước và gỡ đúng lượt này khi rollback.
"""
from importlib import import_module

from django.contrib.auth.models import Group, Permission
from django.db import connection
from django.test import TestCase

from authorization.rbac_seed import GROUP_PERMISSIONS

grant_cv = import_module("authorization.migrations.0007_grant_cv_send_trinhky")


class SchemaEditorStub:
    connection = connection


class ChuyenVienSendTrinhKyTest(TestCase):
    def setUp(self):
        self.cv = Group.objects.get(name="Chuyên viên")
        self.perm = Permission.objects.get(codename="send_trinhky")

    def test_seed_grants_send_trinhky_to_cv(self):
        self.assertIn("send_trinhky", GROUP_PERMISSIONS["Chuyên viên"])
        self.assertEqual(len(GROUP_PERMISSIONS["Chuyên viên"]), 21)

    def test_database_after_migrate_matches_ddl(self):
        self.assertTrue(self.cv.permissions.filter(pk=self.perm.pk).exists())
        self.assertEqual(self.cv.permissions.count(), 21)

    def test_migration_grants_missing_permission_once(self):
        self.cv.permissions.remove(self.perm)

        grant_cv.grant_cv_send_trinhky(None, SchemaEditorStub)
        grant_cv.grant_cv_send_trinhky(None, SchemaEditorStub)

        self.assertEqual(self.cv.permissions.filter(pk=self.perm.pk).count(), 1)
        self.assertEqual(self.cv.permissions.count(), 21)

    def test_reverse_revokes_only_cv_grant(self):
        tp = Group.objects.get(name="Trưởng phòng")

        grant_cv.revoke_cv_send_trinhky(None, SchemaEditorStub)

        self.assertFalse(self.cv.permissions.filter(pk=self.perm.pk).exists())
        self.assertEqual(self.cv.permissions.count(), 20)
        self.assertTrue(tp.permissions.filter(pk=self.perm.pk).exists())
