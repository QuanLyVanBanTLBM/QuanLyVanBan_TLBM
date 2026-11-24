"""
Issue #846: chỉ nhóm ADMIN được giữ view/add/change/delete_nhomquyen. Nhóm khác giữ change_nhomquyen thì người trong nhóm
tự sửa được tập quyền của nhóm mình (leo thang đặc quyền). Cả 3 đường ghi quyền của nhóm đều chặn, kể cả superuser;
migration 0020 gỡ các lượt gán sẵn có khỏi nhóm khác ADMIN và khỏi quyền gán thẳng cho người dùng, chạy lại không đổi thêm.
"""
from importlib import import_module

from django.apps import apps as django_apps
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.db import connection
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from authorization.models import GroupInfo
from authorization.rbac_seed import (
    EXTRA_GROUP_PERMISSIONS,
    GROUP_PERMISSIONS,
    GROUPS,
    SUPPLEMENTARY_GROUP_PERMISSIONS,
)

migration = import_module("authorization.migrations.0020_chi_admin_giu_quyen_nhom_quyen")

ROLE_CODENAMES = {"view_nhomquyen", "add_nhomquyen", "change_nhomquyen", "delete_nhomquyen"}
ERROR_KEY = "roles.messages.roleManagementAdminOnly"


class SchemaEditorStub:
    connection = connection
    quote_name = staticmethod(connection.ops.quote_name)


def ids(*codenames):
    return list(Permission.objects.filter(codename__in=codenames).values_list("id", flat=True))


def group_of(code):
    return Group.objects.get(pk=GroupInfo.objects.get(ma_nhom_quyen=code).pk)


def codenames_of(group):
    return set(group.permissions.values_list("codename", flat=True))


class RoleManagementAdminOnlyApiTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.manager = User.objects.create_user(username="nq846_mgr", password="Test@12345")
        self.manager.user_permissions.add(*Permission.objects.filter(codename__in=ROLE_CODENAMES))
        self.client = APIClient()
        self.client.force_authenticate(user=self.manager)
        self.tp = group_of("TP")
        self.admin_group = group_of("ADMIN")
        self.tp_before = codenames_of(self.tp)

    def assert_rejected(self, response):
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["permission_ids"], [ERROR_KEY])

    def test_permissions_endpoint_rejects_role_management_for_non_admin_group(self):
        for codename in sorted(ROLE_CODENAMES):
            response = self.client.put(
                f"/api/roles/{self.tp.pk}/permissions/", {"permission_ids": ids("view_donvi", codename)}, format="json"
            )
            self.assert_rejected(response)
        self.assertEqual(codenames_of(self.tp), self.tp_before)

    def test_put_and_patch_reject_role_management_for_non_admin_group(self):
        payload = {"name": self.tp.name, "permission_ids": ids("view_donvi", "change_nhomquyen")}
        self.assert_rejected(self.client.put(f"/api/roles/{self.tp.pk}/", payload, format="json"))
        self.assert_rejected(self.client.patch(f"/api/roles/{self.tp.pk}/", payload, format="json"))
        self.assertEqual(codenames_of(self.tp), self.tp_before)

    def test_create_rejects_role_management_permissions(self):
        response = self.client.post(
            "/api/roles/", {"name": "Nhóm 846", "permission_ids": ids("change_nhomquyen")}, format="json"
        )
        self.assert_rejected(response)
        self.assertFalse(Group.objects.filter(name="Nhóm 846").exists())

    def test_superuser_cannot_grant_role_management_to_non_admin_group(self):
        root = get_user_model().objects.create_superuser(username="nq846_root", password="Test@12345")
        client = APIClient()
        client.force_authenticate(user=root)
        response = client.put(
            f"/api/roles/{self.tp.pk}/permissions/", {"permission_ids": ids("change_nhomquyen")}, format="json"
        )
        self.assert_rejected(response)

    def test_non_admin_group_still_saves_other_permissions(self):
        response = self.client.put(
            f"/api/roles/{self.tp.pk}/permissions/", {"permission_ids": ids("view_donvi", "export_donvi")}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(codenames_of(self.tp), {"view_donvi", "export_donvi"})

    def test_admin_group_keeps_role_management_and_all_permissions(self):
        all_ids = list(Permission.objects.values_list("id", flat=True))
        response = self.client.put(
            f"/api/roles/{self.admin_group.pk}/permissions/", {"permission_ids": all_ids}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(ROLE_CODENAMES <= codenames_of(self.admin_group))


class RoleManagementSeedTest(TestCase):
    def test_seed_grants_role_management_only_to_admin(self):
        admin_name = dict((code, name) for name, code in GROUPS)["ADMIN"]
        seeded = {**GROUP_PERMISSIONS, **SUPPLEMENTARY_GROUP_PERMISSIONS}
        for group, codenames in seeded.items():
            if group != admin_name:
                self.assertFalse(ROLE_CODENAMES & set(codenames), group)
        self.assertEqual(set(EXTRA_GROUP_PERMISSIONS), {admin_name})


class RoleManagementMigrationTest(TestCase):
    def test_migration_removes_role_management_from_every_non_admin_group(self):
        tp = group_of("TP")
        vt = group_of("VT")
        custom = Group.objects.create(name="Nhóm 846 tự tạo")
        admin_group = group_of("ADMIN")
        role_perms = Permission.objects.filter(codename__in=ROLE_CODENAMES)
        for group in (tp, vt, custom):
            group.permissions.add(*role_perms)
        custom.permissions.add(Permission.objects.get(codename="view_donvi"))
        tp_other = codenames_of(tp) - ROLE_CODENAMES
        # Quyền gán thẳng cho người dùng cũng được RbacBackend cộng vào, nên phải gỡ theo
        user = get_user_model().objects.create_user(username="nq846_direct", password="Test@12345")
        user.user_permissions.add(*role_perms, Permission.objects.get(codename="view_donvi"))

        migration.remove_role_management_from_non_admin(django_apps, SchemaEditorStub)
        migration.remove_role_management_from_non_admin(django_apps, SchemaEditorStub)

        self.assertEqual(codenames_of(tp), tp_other)
        self.assertFalse(ROLE_CODENAMES & codenames_of(vt))
        self.assertEqual(codenames_of(custom), {"view_donvi"})
        self.assertTrue(ROLE_CODENAMES <= codenames_of(admin_group))
        self.assertEqual(set(user.user_permissions.values_list("codename", flat=True)), {"view_donvi"})


class RoleManagementUserLevelGrantTest(TestCase):
    def test_direct_grant_no_longer_lets_non_admin_edit_roles_after_migration(self):
        tp = group_of("TP")
        user = get_user_model().objects.create_user(username="nq846_tp_direct", password="Test@12345")
        user.groups.add(tp)
        user.user_permissions.add(Permission.objects.get(codename="change_nhomquyen"))
        tp_before = codenames_of(tp)

        migration.remove_role_management_from_non_admin(django_apps, SchemaEditorStub)

        user = get_user_model().objects.get(pk=user.pk)
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.put(
            f"/api/roles/{tp.pk}/permissions/", {"permission_ids": ids("view_donvi", "export_donvi")}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(codenames_of(tp), tp_before)
