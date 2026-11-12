from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient


class AuthorizationAPITest(TestCase):
    """
    Test suite cho Issue #21 (RBAC): CRUD nhóm quyền (Group) và danh sách quyền (Permission).
    """

    def setUp(self):
        User = get_user_model()
        self.view_perm = Permission.objects.get(codename="view_nhomquyen")
        self.add_perm = Permission.objects.get(codename="add_nhomquyen")
        self.change_perm = Permission.objects.get(codename="change_nhomquyen")
        self.delete_perm = Permission.objects.get(codename="delete_nhomquyen")

        self.admin_user = User.objects.create_user(username="rbac_admin", password="Test@12345")
        self.admin_user.user_permissions.add(
            self.view_perm, self.add_perm, self.change_perm, self.delete_perm
        )

        self.view_only_user = User.objects.create_user(username="rbac_viewer", password="Test@12345")
        self.view_only_user.user_permissions.add(self.view_perm)

        self.no_perm_user = User.objects.create_user(username="rbac_noperm", password="Test@12345")

        self.admin_client = APIClient()
        self.admin_client.force_authenticate(user=self.admin_user)

        self.viewer_client = APIClient()
        self.viewer_client.force_authenticate(user=self.view_only_user)

        self.noperm_client = APIClient()
        self.noperm_client.force_authenticate(user=self.no_perm_user)

        self.anon_client = APIClient()

        self.some_permission = Permission.objects.get(codename="view_donvi")
        self.group = Group.objects.create(name="Test Role Alpha")
        self.group.permissions.add(self.view_perm)

    # ── Unauthenticated ──────────────────────────────────────────────
    def test_list_groups_unauthenticated_401(self):
        response = self.anon_client.get("/api/roles/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_permission_list_unauthenticated_401(self):
        response = self.anon_client.get("/api/permissions/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # ── List ─────────────────────────────────────────────────────────
    def test_list_groups_requires_view_permission_403(self):
        response = self.noperm_client.get("/api/roles/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["detail"], "roles.messages.permissionDenied")

    def test_list_groups_200(self):
        response = self.viewer_client.get("/api/roles/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("count", response.data)
        self.assertIn("results", response.data)
        names = [g["name"] for g in response.data["results"]]
        self.assertIn("Test Role Alpha", names)

    def test_list_groups_search(self):
        Group.objects.create(name="Another Group Beta")
        response = self.viewer_client.get("/api/roles/?search=Alpha")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [g["name"] for g in response.data["results"]]
        self.assertIn("Test Role Alpha", names)
        self.assertNotIn("Another Group Beta", names)

    def test_list_groups_pagination(self):
        for i in range(15):
            Group.objects.create(name=f"Bulk Group {i}")
        response = self.viewer_client.get("/api/roles/?page=1")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 10)
        self.assertIsNotNone(response.data["next"])

    def test_list_groups_all_param_returns_array(self):
        response = self.viewer_client.get("/api/roles/?all=true")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)

    def test_list_groups_includes_user_and_permission_count(self):
        self.admin_user.groups.add(self.group)
        response = self.viewer_client.get("/api/roles/?search=Alpha")
        row = response.data["results"][0]
        self.assertEqual(row["user_count"], 1)
        self.assertEqual(row["permission_count"], 1)

    # ── Create ───────────────────────────────────────────────────────
    def test_create_group_requires_add_permission_403(self):
        response = self.viewer_client.post("/api/roles/", {"name": "Nope"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_group_201(self):
        response = self.admin_client.post(
            "/api/roles/", {"name": "New Role", "permission_ids": [self.view_perm.id]}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "New Role")
        self.assertTrue(Group.objects.filter(name="New Role").exists())

    def test_create_group_empty_name_400(self):
        response = self.admin_client.post("/api/roles/", {"name": "   "}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("roles.messages.nameRequired", response.data["name"])

    def test_create_group_duplicate_name_400(self):
        response = self.admin_client.post(
            "/api/roles/", {"name": "test role alpha"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("roles.messages.nameExists", response.data["name"])

    def test_create_group_invalid_permission_id_400(self):
        response = self.admin_client.post(
            "/api/roles/", {"name": "Bad Perm Role", "permission_ids": [999999]}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ── Detail / Retrieve ─────────────────────────────────────────────
    def test_get_group_detail_200(self):
        response = self.viewer_client.get(f"/api/roles/{self.group.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Test Role Alpha")
        self.assertIn(self.view_perm.id, response.data["permission_ids"])

    def test_get_group_notfound_404(self):
        response = self.viewer_client.get("/api/roles/999999/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["detail"], "roles.messages.groupNotFound")

    def test_get_group_requires_view_permission_403(self):
        response = self.noperm_client.get(f"/api/roles/{self.group.id}/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ── Update ───────────────────────────────────────────────────────
    def test_update_group_requires_change_permission_403(self):
        response = self.viewer_client.put(
            f"/api/roles/{self.group.id}/", {"name": "Changed"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_group_name_200(self):
        response = self.admin_client.put(
            f"/api/roles/{self.group.id}/", {"name": "Renamed Role"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.group.refresh_from_db()
        self.assertEqual(self.group.name, "Renamed Role")

    def test_update_group_permissions_200(self):
        response = self.admin_client.put(
            f"/api/roles/{self.group.id}/",
            {"name": "Test Role Alpha", "permission_ids": [self.add_perm.id, self.change_perm.id]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.group.refresh_from_db()
        perm_ids = set(self.group.permissions.values_list("id", flat=True))
        self.assertEqual(perm_ids, {self.add_perm.id, self.change_perm.id})

    def test_update_group_clear_permissions(self):
        response = self.admin_client.put(
            f"/api/roles/{self.group.id}/",
            {"name": "Test Role Alpha", "permission_ids": []},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.group.refresh_from_db()
        self.assertEqual(self.group.permissions.count(), 0)

    def test_update_group_duplicate_name_400(self):
        Group.objects.create(name="Existing Other")
        response = self.admin_client.put(
            f"/api/roles/{self.group.id}/", {"name": "existing other"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_group_notfound_404(self):
        response = self.admin_client.put(
            "/api/roles/999999/", {"name": "X"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # ── Delete ───────────────────────────────────────────────────────
    def test_delete_group_requires_delete_permission_403(self):
        response = self.viewer_client.delete(f"/api/roles/{self.group.id}/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_group_204(self):
        response = self.admin_client.delete(f"/api/roles/{self.group.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Group.objects.filter(id=self.group.id).exists())

    def test_delete_group_with_users_400(self):
        self.admin_user.groups.add(self.group)
        response = self.admin_client.delete(f"/api/roles/{self.group.id}/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"], "roles.messages.groupHasUsers")
        self.assertTrue(Group.objects.filter(id=self.group.id).exists())

    def test_delete_group_notfound_404(self):
        response = self.admin_client.delete("/api/roles/999999/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # ── Permissions list ───────────────────────────────────────────────
    def test_permission_list_requires_view_permission_403(self):
        response = self.noperm_client.get("/api/permissions/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_permission_list_200(self):
        response = self.viewer_client.get("/api/permissions/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertGreater(len(response.data), 0)
        sample = response.data[0]
        self.assertIn("codename", sample)
        self.assertIn("module_ten", sample)
        self.assertNotIn("content_type", sample)

    def test_permission_list_matches_ddl_seed(self):
        """69 quyền chuẩn của DDL base + 8 quyền bổ sung (77, đã bỏ văn bản mật), gom theo module_ten tiếng Việt."""
        response = self.viewer_client.get("/api/permissions/")
        codenames = {p["codename"] for p in response.data}
        self.assertGreaterEqual(len(codenames), 77)
        self.assertIn("export_donvi", codenames)
        self.assertIn("view_nhomquyen", codenames)
        by_codename = {p["codename"]: p for p in response.data}
        self.assertEqual(by_codename["view_donvi"]["module_ten"], "Đơn vị, phòng ban")

    def test_group_list_exposes_ma_nhom_quyen(self):
        response = self.viewer_client.get("/api/roles/?all=true")
        by_name = {g["name"]: g for g in response.data}
        self.assertEqual(by_name["Quản trị hệ thống"]["ma_nhom_quyen"], "ADMIN")
        self.assertIsNone(by_name["Test Role Alpha"]["ma_nhom_quyen"])


class RolePermissionsEndpointTest(TestCase):
    """Issue #21: PATCH nhóm, PUT /roles/{id}/permissions/, GET /auth/me/permissions/ và helper require_permission."""

    def setUp(self):
        User = get_user_model()
        self.view_perm = Permission.objects.get(codename="view_nhomquyen")
        self.change_perm = Permission.objects.get(codename="change_nhomquyen")
        self.target_perm = Permission.objects.get(codename="view_donvi")
        self.other_perm = Permission.objects.get(codename="export_donvi")

        self.manager = User.objects.create_user(username="rbac_mgr", password="Test@12345")
        self.manager.user_permissions.add(self.view_perm, self.change_perm)
        self.viewer = User.objects.create_user(username="rbac_view2", password="Test@12345")
        self.viewer.user_permissions.add(self.view_perm)

        self.manager_client = APIClient()
        self.manager_client.force_authenticate(user=self.manager)
        self.viewer_client = APIClient()
        self.viewer_client.force_authenticate(user=self.viewer)
        self.anon_client = APIClient()

        self.group = Group.objects.create(name="Role Target")

    def test_patch_group_name_only_keeps_permissions(self):
        self.group.permissions.add(self.target_perm)
        response = self.manager_client.patch(f"/api/roles/{self.group.id}/", {"name": "Role Renamed"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.group.refresh_from_db()
        self.assertEqual(self.group.name, "Role Renamed")
        self.assertEqual(list(self.group.permissions.values_list("codename", flat=True)), ["view_donvi"])

    def test_patch_group_requires_change_permission_403(self):
        response = self.viewer_client.patch(f"/api/roles/{self.group.id}/", {"name": "X"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_put_permissions_replaces_set(self):
        self.group.permissions.add(self.target_perm)
        response = self.manager_client.put(
            f"/api/roles/{self.group.id}/permissions/", {"permission_ids": [self.other_perm.id]}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["permission_ids"], [self.other_perm.id])
        self.assertEqual(list(self.group.permissions.values_list("codename", flat=True)), ["export_donvi"])

    def test_put_permissions_empty_list_clears_all(self):
        self.group.permissions.add(self.target_perm)
        response = self.manager_client.put(
            f"/api/roles/{self.group.id}/permissions/", {"permission_ids": []}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.group.permissions.count(), 0)

    def test_put_permissions_unknown_id_400(self):
        response = self.manager_client.put(
            f"/api/roles/{self.group.id}/permissions/", {"permission_ids": [999999]}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_put_permissions_missing_field_400(self):
        response = self.manager_client.put(f"/api/roles/{self.group.id}/permissions/", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_put_permissions_group_not_found_404(self):
        response = self.manager_client.put("/api/roles/999999/permissions/", {"permission_ids": []}, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_put_permissions_unauthenticated_401(self):
        response = self.anon_client.put(f"/api/roles/{self.group.id}/permissions/", {"permission_ids": []}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_put_permissions_requires_change_permission_403(self):
        response = self.viewer_client.put(
            f"/api/roles/{self.group.id}/permissions/", {"permission_ids": [self.target_perm.id]}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.group.permissions.count(), 0)

    def test_my_permissions_unauthenticated_401(self):
        response = self.anon_client.get("/api/auth/me/permissions/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_my_permissions_lists_direct_and_group_codenames(self):
        self.group.permissions.add(self.target_perm)
        self.viewer.groups.add(self.group)
        response = self.viewer_client.get("/api/auth/me/permissions/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["is_superuser"])
        self.assertEqual(response.data["permissions"], sorted(["view_nhomquyen", "view_donvi"]))

    def test_my_permissions_superuser_gets_all(self):
        User = get_user_model()
        root = User.objects.create_superuser(username="rbac_root", password="Test@12345", email="root@example.com")
        client = APIClient()
        client.force_authenticate(user=root)
        response = client.get("/api/auth/me/permissions/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["is_superuser"])
        self.assertEqual(len(response.data["permissions"]), Permission.objects.count())

    def test_my_permissions_inactive_user_gets_none(self):
        self.viewer.groups.add(self.group)
        self.group.permissions.add(self.target_perm)
        self.assertIn("view_donvi", self.viewer.get_all_permissions())
        self.viewer.is_active = False
        self.viewer.save()
        self.viewer = get_user_model().objects.get(pk=self.viewer.pk)
        self.assertEqual(self.viewer.get_all_permissions(), set())


class RequirePermissionHelperTest(TestCase):
    """Helper dùng chung require_permission: 403 khi thiếu quyền, cho qua khi đủ quyền hoặc superuser."""

    def setUp(self):
        from rest_framework.test import APIRequestFactory

        self.factory = APIRequestFactory()
        User = get_user_model()
        self.user = User.objects.create_user(username="helper_user", password="Test@12345")
        self.root = User.objects.create_superuser(username="helper_root", password="Test@12345", email="r@example.com")

    def _check(self, user, codename):
        from authorization.permissions import require_permission

        request = self.factory.get("/")
        request.user = user
        return require_permission(codename)().has_permission(request, None)

    def test_denied_without_permission(self):
        self.assertFalse(self._check(self.user, "view_donvi"))

    def test_allowed_with_direct_permission(self):
        self.user.user_permissions.add(Permission.objects.get(codename="view_donvi"))
        self.user = get_user_model().objects.get(pk=self.user.pk)
        self.assertTrue(self._check(self.user, "view_donvi"))

    def test_superuser_allowed_for_any_codename(self):
        self.assertTrue(self._check(self.root, "anything_at_all"))

    def test_anonymous_denied(self):
        from django.contrib.auth.models import AnonymousUser

        self.assertFalse(self._check(AnonymousUser(), "view_donvi"))

    def test_denied_message_is_i18n_key(self):
        from authorization.permissions import require_permission

        self.assertEqual(require_permission("view_donvi").message, "roles.messages.permissionDenied")
