"""
DDL Phase 7 Trình ký (PR #111, Issue #80): nhóm Trưởng phòng có manage_signing_process,
tổng 197 lượt gán quyền khớp DDL, và migration 0004 gán bổ sung trên DB đã seed từ trước.
"""
from importlib import import_module

from django.contrib.auth.models import Group, Permission
from django.db import connection
from django.test import TestCase

from authorization.rbac_seed import EXTRA_GROUP_PERMISSIONS, GROUP_PERMISSIONS

grant_tp = import_module("authorization.migrations.0004_grant_tp_manage_signing_process")


class SchemaEditorStub:
    connection = connection


class TruongPhongSigningProcessTest(TestCase):
    def test_seed_grants_manage_signing_process_to_tp(self):
        self.assertIn("manage_signing_process", GROUP_PERMISSIONS["Trưởng phòng"])

    def test_seed_has_197_group_permission_rows(self):
        groups = {}
        for mapping in (GROUP_PERMISSIONS, EXTRA_GROUP_PERMISSIONS):
            for group_name, codenames in mapping.items():
                groups.setdefault(group_name, set()).update(codenames)
        self.assertEqual(sum(len(codenames) for codenames in groups.values()), 197)
        self.assertEqual(len(groups["Trưởng phòng"]), 28)

    def test_database_after_migrate_matches_ddl(self):
        tp = Group.objects.get(name="Trưởng phòng")
        self.assertTrue(tp.permissions.filter(codename="manage_signing_process").exists())
        self.assertEqual(tp.permissions.count(), 29)

    def test_migration_grants_missing_permission_once(self):
        tp = Group.objects.get(name="Trưởng phòng")
        perm = Permission.objects.get(codename="manage_signing_process")
        tp.permissions.remove(perm)

        grant_tp.grant_tp_manage_signing_process(None, SchemaEditorStub)
        grant_tp.grant_tp_manage_signing_process(None, SchemaEditorStub)

        self.assertEqual(tp.permissions.filter(pk=perm.pk).count(), 1)
        self.assertEqual(tp.permissions.count(), 29)
