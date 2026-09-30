from django.contrib.auth.models import Group, Permission, User
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient


class AuthorizationAPITest(TestCase):
    """
    Test suite cho Issue #21 (RBAC): CRUD nhóm quyền (Group) và danh sách quyền (Permission).
    """

    def setUp(self):
        self.view_perm = Permission.objects.get(content_type__app_label="auth", codename="view_group")
        self.add_perm = Permission.objects.get(content_type__app_label="auth", codename="add_group")
        self.change_perm = Permission.objects.get(content_type__app_label="auth", codename="change_group")
        self.delete_perm = Permission.objects.get(content_type__app_label="auth", codename="delete_group")

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

        self.some_permission = Permission.objects.filter(content_type__app_label="auth").first()
        self.group = Group.objects.create(name="Test Role Alpha")
        self.group.permissions.add(self.view_perm)

    # ── Unauthenticated ──────────────────────────────────────────────
    def test_list_groups_unauthenticated_401(self):
        response = self.anon_client.get("/api/authorization/groups/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_permission_list_unauthenticated_401(self):
        response = self.anon_client.get("/api/authorization/permissions/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # ── List ─────────────────────────────────────────────────────────
    def test_list_groups_requires_view_permission_403(self):
        response = self.noperm_client.get("/api/authorization/groups/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["detail"], "roles.messages.permissionDenied")

    def test_list_groups_200(self):
        response = self.viewer_client.get("/api/authorization/groups/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("count", response.data)
        self.assertIn("results", response.data)
        names = [g["name"] for g in response.data["results"]]
        self.assertIn("Test Role Alpha", names)

    def test_list_groups_search(self):
        Group.objects.create(name="Another Group Beta")
        response = self.viewer_client.get("/api/authorization/groups/?search=Alpha")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [g["name"] for g in response.data["results"]]
        self.assertIn("Test Role Alpha", names)
        self.assertNotIn("Another Group Beta", names)

    def test_list_groups_pagination(self):
        for i in range(15):
            Group.objects.create(name=f"Bulk Group {i}")
        response = self.viewer_client.get("/api/authorization/groups/?page=1")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 10)
        self.assertIsNotNone(response.data["next"])

    def test_list_groups_all_param_returns_array(self):
        response = self.viewer_client.get("/api/authorization/groups/?all=true")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)

    def test_list_groups_includes_user_and_permission_count(self):
        self.admin_user.groups.add(self.group)
        response = self.viewer_client.get("/api/authorization/groups/?search=Alpha")
        row = response.data["results"][0]
        self.assertEqual(row["user_count"], 1)
        self.assertEqual(row["permission_count"], 1)

    # ── Create ───────────────────────────────────────────────────────
    def test_create_group_requires_add_permission_403(self):
        response = self.viewer_client.post("/api/authorization/groups/", {"name": "Nope"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_group_201(self):
        response = self.admin_client.post(
            "/api/authorization/groups/", {"name": "New Role", "permission_ids": [self.view_perm.id]}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "New Role")
        self.assertTrue(Group.objects.filter(name="New Role").exists())

    def test_create_group_empty_name_400(self):
        response = self.admin_client.post("/api/authorization/groups/", {"name": "   "}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("roles.messages.nameRequired", response.data["name"])

    def test_create_group_duplicate_name_400(self):
        response = self.admin_client.post(
            "/api/authorization/groups/", {"name": "test role alpha"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("roles.messages.nameExists", response.data["name"])

    def test_create_group_invalid_permission_id_400(self):
        response = self.admin_client.post(
            "/api/authorization/groups/", {"name": "Bad Perm Role", "permission_ids": [999999]}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ── Detail / Retrieve ─────────────────────────────────────────────
    def test_get_group_detail_200(self):
        response = self.viewer_client.get(f"/api/authorization/groups/{self.group.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Test Role Alpha")
        self.assertIn(self.view_perm.id, response.data["permission_ids"])

    def test_get_group_notfound_404(self):
        response = self.viewer_client.get("/api/authorization/groups/999999/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["detail"], "roles.messages.groupNotFound")

    def test_get_group_requires_view_permission_403(self):
        response = self.noperm_client.get(f"/api/authorization/groups/{self.group.id}/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ── Update ───────────────────────────────────────────────────────
    def test_update_group_requires_change_permission_403(self):
        response = self.viewer_client.put(
            f"/api/authorization/groups/{self.group.id}/", {"name": "Changed"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_group_name_200(self):
        response = self.admin_client.put(
            f"/api/authorization/groups/{self.group.id}/", {"name": "Renamed Role"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.group.refresh_from_db()
        self.assertEqual(self.group.name, "Renamed Role")

    def test_update_group_permissions_200(self):
        response = self.admin_client.put(
            f"/api/authorization/groups/{self.group.id}/",
            {"name": "Test Role Alpha", "permission_ids": [self.add_perm.id, self.change_perm.id]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.group.refresh_from_db()
        perm_ids = set(self.group.permissions.values_list("id", flat=True))
        self.assertEqual(perm_ids, {self.add_perm.id, self.change_perm.id})

    def test_update_group_clear_permissions(self):
        response = self.admin_client.put(
            f"/api/authorization/groups/{self.group.id}/",
            {"name": "Test Role Alpha", "permission_ids": []},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.group.refresh_from_db()
        self.assertEqual(self.group.permissions.count(), 0)

    def test_update_group_duplicate_name_400(self):
        Group.objects.create(name="Existing Other")
        response = self.admin_client.put(
            f"/api/authorization/groups/{self.group.id}/", {"name": "existing other"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_group_notfound_404(self):
        response = self.admin_client.put(
            "/api/authorization/groups/999999/", {"name": "X"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # ── Delete ───────────────────────────────────────────────────────
    def test_delete_group_requires_delete_permission_403(self):
        response = self.viewer_client.delete(f"/api/authorization/groups/{self.group.id}/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_group_204(self):
        response = self.admin_client.delete(f"/api/authorization/groups/{self.group.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Group.objects.filter(id=self.group.id).exists())

    def test_delete_group_with_users_400(self):
        self.admin_user.groups.add(self.group)
        response = self.admin_client.delete(f"/api/authorization/groups/{self.group.id}/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"], "roles.messages.groupHasUsers")
        self.assertTrue(Group.objects.filter(id=self.group.id).exists())

    def test_delete_group_notfound_404(self):
        response = self.admin_client.delete("/api/authorization/groups/999999/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # ── Permissions list ───────────────────────────────────────────────
    def test_permission_list_requires_view_permission_403(self):
        response = self.noperm_client.get("/api/authorization/permissions/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_permission_list_200(self):
        response = self.viewer_client.get("/api/authorization/permissions/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertGreater(len(response.data), 0)
        sample = response.data[0]
        self.assertIn("codename", sample)
        self.assertIn("content_type", sample)
        self.assertIn("app_label", sample["content_type"])
