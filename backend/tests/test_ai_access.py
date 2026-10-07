from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from rest_framework.test import APIClient

from backend.services.ai_access import has_permission_codename, is_ai_admin

User = get_user_model()


def grant_codename(user, codename):
    user.user_permissions.add(Permission.objects.get(codename=codename))


class AIAccessTests(TestCase):
    def setUp(self):
        self.no_perm = User.objects.create_user(username="ai_no_perm", password="test-password")
        self.ai_user = User.objects.create_user(username="ai_user", password="test-password")
        grant_codename(self.ai_user, "use_aiassistant")
        self.superuser = User.objects.create_superuser(username="ai_super", password="test-password")
        self.client = APIClient()

    def test_permission_codename_follows_rbac(self):
        self.assertFalse(has_permission_codename(self.no_perm, "use_aiassistant"))
        self.assertTrue(has_permission_codename(self.ai_user, "use_aiassistant"))
        self.assertTrue(has_permission_codename(self.superuser, "use_aiassistant"))

    def test_locked_account_is_denied(self):
        self.ai_user.is_active = False
        self.assertFalse(has_permission_codename(self.ai_user, "use_aiassistant"))
        self.superuser.is_active = False
        self.assertFalse(has_permission_codename(self.superuser, "use_aiassistant"))
        self.assertFalse(is_ai_admin(self.superuser))

    def test_ai_admin_is_superuser_only(self):
        self.assertFalse(is_ai_admin(self.no_perm))
        self.assertFalse(is_ai_admin(self.ai_user))
        self.assertTrue(is_ai_admin(self.superuser))

    def test_chat_requires_authentication(self):
        response = self.client.post("/api/chat", {"question": "Tìm văn bản"}, format="json")
        self.assertEqual(response.status_code, 401)

    def test_chat_requires_use_aiassistant_permission(self):
        self.client.force_authenticate(self.no_perm)
        response = self.client.post("/api/chat", {"question": "Tìm văn bản"}, format="json")
        self.assertEqual(response.status_code, 403)

    def test_categories_require_ai_permission(self):
        self.client.force_authenticate(self.no_perm)
        self.assertEqual(self.client.get("/api/categories").status_code, 403)
        self.client.force_authenticate(self.ai_user)
        with patch("backend.api.views.list_categories", return_value=[]):
            response = self.client.get("/api/categories")
        self.assertEqual(response.status_code, 200)

    def test_management_endpoints_are_superuser_only(self):
        for user in (self.no_perm, self.ai_user):
            self.client.force_authenticate(user)
            self.assertEqual(self.client.get("/api/documents").status_code, 403)
            self.assertEqual(self.client.get("/api/settings/ai").status_code, 403)

    def test_superuser_can_read_ai_settings(self):
        self.client.force_authenticate(self.superuser)
        self.assertEqual(self.client.get("/api/settings/ai").status_code, 200)
