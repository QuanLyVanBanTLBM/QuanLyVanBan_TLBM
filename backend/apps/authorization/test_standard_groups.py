"""
Năm nhóm chuẩn của DDL (VT, CV, TP, BGD, ADMIN) không đổi tên, không xóa; nhóm ADMIN luôn giữ quyền quản lý
nhóm quyền; kiểm quyền diễn ra trước khi tra bản ghi để không dò được id nhóm.
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

ROLE_CODENAMES = ["view_nhomquyen", "add_nhomquyen", "change_nhomquyen", "delete_nhomquyen"]


def permission_ids(*codenames):
    return list(Permission.objects.filter(codename__in=codenames).values_list("id", flat=True))


class StandardRoleProtectionTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.manager = User.objects.create_user(username="rbac_prot_mgr", password="Test@12345")
        self.manager.user_permissions.add(*Permission.objects.filter(codename__in=ROLE_CODENAMES))
        self.viewer = User.objects.create_user(username="rbac_prot_view", password="Test@12345")
        self.viewer.user_permissions.add(Permission.objects.get(codename="view_nhomquyen"))
        self.no_perm = User.objects.create_user(username="rbac_prot_none", password="Test@12345")

        self.client = APIClient()
        self.client.force_authenticate(user=self.manager)
        self.viewer_client = APIClient()
        self.viewer_client.force_authenticate(user=self.viewer)
        self.noperm_client = APIClient()
        self.noperm_client.force_authenticate(user=self.no_perm)

        self.vt = Group.objects.get(name="Văn thư")
        self.admin_group = Group.objects.get(name="Quản trị hệ thống")

    def test_standard_group_cannot_be_deleted(self):
        response = self.client.delete(f"/api/roles/{self.vt.id}/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"], "roles.messages.groupProtected")
        self.assertTrue(Group.objects.filter(pk=self.vt.pk).exists())

    def test_admin_group_cannot_be_deleted_even_without_members(self):
        self.admin_group.user_set.clear()
        self.assertFalse(self.admin_group.user_set.exists())
        response = self.client.delete(f"/api/roles/{self.admin_group.id}/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(Group.objects.filter(pk=self.admin_group.pk).exists())

    def test_standard_group_cannot_be_renamed(self):
        response = self.client.patch(f"/api/roles/{self.vt.id}/", {"name": "Tên khác"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["name"], ["roles.messages.groupProtected"])
        self.vt.refresh_from_db()
        self.assertEqual(self.vt.name, "Văn thư")

    def test_standard_group_can_be_saved_with_same_name_and_new_permissions(self):
        ids = permission_ids("view_donvi", "export_donvi")
        response = self.client.put(
            f"/api/roles/{self.vt.id}/", {"name": "Văn thư", "permission_ids": ids}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(set(self.vt.permissions.values_list("id", flat=True)), set(ids))

    def test_admin_group_must_keep_role_management_permissions(self):
        before = self.admin_group.permissions.count()
        response = self.client.put(
            f"/api/roles/{self.admin_group.id}/permissions/",
            {"permission_ids": permission_ids("view_donvi")},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["permission_ids"], ["roles.messages.adminPermissionsRequired"])
        self.assertEqual(self.admin_group.permissions.count(), before)

        # Cập nhật qua PUT /roles/{id}/ cũng bị chặn như nhau.
        response = self.client.put(
            f"/api/roles/{self.admin_group.id}/",
            {"name": "Quản trị hệ thống", "permission_ids": permission_ids("view_donvi")},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.admin_group.permissions.count(), before)

    def test_admin_group_accepts_permissions_that_include_role_management(self):
        ids = permission_ids(*ROLE_CODENAMES, "view_donvi")
        response = self.client.put(
            f"/api/roles/{self.admin_group.id}/permissions/", {"permission_ids": ids}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(set(self.admin_group.permissions.values_list("id", flat=True)), set(ids))

    def test_other_standard_groups_may_drop_role_management_permissions(self):
        response = self.client.put(
            f"/api/roles/{self.vt.id}/permissions/",
            {"permission_ids": permission_ids("view_donvi")},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_custom_group_can_still_be_renamed_and_deleted(self):
        group = Group.objects.create(name="Nhóm tự tạo")
        response = self.client.patch(f"/api/roles/{group.id}/", {"name": "Nhóm tự tạo 2"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.client.delete(f"/api/roles/{group.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_permission_is_checked_before_lookup_so_ids_cannot_be_probed(self):
        missing = "/api/roles/999999/"
        existing = f"/api/roles/{self.vt.id}/"
        for url in (missing, existing):
            self.assertEqual(self.noperm_client.get(url).status_code, status.HTTP_403_FORBIDDEN)
            self.assertEqual(
                self.noperm_client.put(url, {"name": "x"}, format="json").status_code, status.HTTP_403_FORBIDDEN
            )
            self.assertEqual(
                self.noperm_client.patch(url, {"name": "x"}, format="json").status_code, status.HTTP_403_FORBIDDEN
            )
            self.assertEqual(self.noperm_client.delete(url).status_code, status.HTTP_403_FORBIDDEN)
        # Chỉ có quyền xem: xem id không tồn tại là 404, nhưng sửa/xóa vẫn 403.
        self.assertEqual(self.viewer_client.get(missing).status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            self.viewer_client.put(missing, {"name": "x"}, format="json").status_code, status.HTTP_403_FORBIDDEN
        )
        self.assertEqual(self.viewer_client.delete(missing).status_code, status.HTTP_403_FORBIDDEN)
        # Người đủ quyền vẫn nhận 404 đúng nghĩa.
        self.assertEqual(self.client.delete(missing).status_code, status.HTTP_404_NOT_FOUND)
