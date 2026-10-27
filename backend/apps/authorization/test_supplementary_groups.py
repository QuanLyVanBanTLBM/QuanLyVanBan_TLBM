"""
Issue #228: hai nhóm chuẩn bổ sung TLBGD (Trợ lý Ban Giám đốc) và KT (Kiểm toán) có đúng tập quyền cộng thêm,
được bảo vệ như nhóm chuẩn, và migration 0007 bổ sung idempotent trên DB đã có dữ liệu.
"""
from importlib import import_module

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.db import connection
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from authorization.models import GroupInfo
from authorization.rbac_seed import SUPPLEMENTARY_GROUP_PERMISSIONS, SUPPLEMENTARY_GROUPS

migration = import_module("authorization.migrations.0008_supplementary_groups_tlbgd_kt")


class SchemaEditorStub:
    connection = connection


def codenames_of(code):
    group = Group.objects.get(pk=GroupInfo.objects.get(ma_nhom_quyen=code).pk)
    return set(group.permissions.values_list("codename", flat=True))


class SupplementaryGroupsTest(TestCase):
    def test_groups_exist_with_exact_permissions(self):
        for name, code in SUPPLEMENTARY_GROUPS:
            self.assertEqual(GroupInfo.objects.get(ma_nhom_quyen=code).name, name)
            self.assertEqual(codenames_of(code), set(SUPPLEMENTARY_GROUP_PERMISSIONS[code]))

    def test_groups_do_not_grant_leadership_actions(self):
        granted = codenames_of("TLBGD") | codenames_of("KT")
        for codename in ("sign_trinhky", "cancel_trinhky", "delegate_trinhky", "manage_signing_process",
                         "approve_congviec"):
            self.assertNotIn(codename, granted)

    def test_migration_copy_matches_seed(self):
        self.assertEqual(migration.GROUPS, SUPPLEMENTARY_GROUPS)
        self.assertEqual(migration.GROUP_PERMISSIONS, SUPPLEMENTARY_GROUP_PERMISSIONS)

    def test_migration_is_idempotent_and_restores_missing_grant(self):
        kt = Group.objects.get(pk=GroupInfo.objects.get(ma_nhom_quyen="KT").pk)
        kt.permissions.remove(Permission.objects.get(codename="view_signing_audit"))
        migration.add_supplementary_groups(None, SchemaEditorStub)
        migration.add_supplementary_groups(None, SchemaEditorStub)
        self.assertEqual(GroupInfo.objects.filter(ma_nhom_quyen="KT").count(), 1)
        self.assertEqual(codenames_of("KT"), set(SUPPLEMENTARY_GROUP_PERMISSIONS["KT"]))

    def test_migration_adopts_custom_group_with_same_name(self):
        Group.objects.get(pk=GroupInfo.objects.get(ma_nhom_quyen="TLBGD").pk).delete()
        custom = Group.objects.create(name="Trợ lý Ban Giám đốc")
        migration.add_supplementary_groups(None, SchemaEditorStub)
        self.assertEqual(GroupInfo.objects.get(pk=custom.pk).ma_nhom_quyen, "TLBGD")
        self.assertEqual(codenames_of("TLBGD"), set(SUPPLEMENTARY_GROUP_PERMISSIONS["TLBGD"]))


class SupplementaryGroupProtectionTest(TestCase):
    def setUp(self):
        manager = get_user_model().objects.create_user(username="nqbs_mgr", password="Test@12345")
        manager.user_permissions.add(*Permission.objects.filter(
            codename__in=["view_nhomquyen", "change_nhomquyen", "delete_nhomquyen"]))
        self.client = APIClient()
        self.client.force_authenticate(user=manager)

    def test_supplementary_groups_cannot_be_renamed_or_deleted(self):
        for name, code in SUPPLEMENTARY_GROUPS:
            group_id = GroupInfo.objects.get(ma_nhom_quyen=code).pk
            response = self.client.patch(f"/api/roles/{group_id}/", {"name": "Tên khác"}, format="json")
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            response = self.client.delete(f"/api/roles/{group_id}/")
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(Group.objects.get(pk=group_id).name, name)
