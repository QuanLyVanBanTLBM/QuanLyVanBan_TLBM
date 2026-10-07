from unittest.mock import patch

from django.contrib.auth.models import Permission, User
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import StaffProfile
from backend.services.ai_access import has_permission_codename, is_ai_admin


def grant_codename(user, codename):
    content_type = ContentType.objects.get_for_model(User)
    permission, _ = Permission.objects.get_or_create(
        content_type=content_type,
        codename=codename,
        defaults={"name": codename},
    )
    user.user_permissions.add(permission)


class AIAccessTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(username="ai_staff", password="test-password")
        self.admin = User.objects.create_user(username="ai_admin", password="test-password")
        StaffProfile.objects.create(
            user=self.admin,
            full_name="AI Admin",
            role="admin",
        )
        self.client = APIClient()

    def test_permission_codenames_support_direct_and_group_grants(self):
        self.assertFalse(has_permission_codename(self.staff, "use_aiassistant"))
        grant_codename(self.staff, "use_aiassistant")
        self.assertTrue(has_permission_codename(self.staff, "use_aiassistant"))

    def test_admin_role_is_shared_by_management_endpoints(self):
        self.assertFalse(is_ai_admin(self.staff))
        self.assertTrue(is_ai_admin(self.admin))

    def test_chat_requires_authentication(self):
        response = self.client.post("/chat", {"question": "Tìm văn bản"}, format="json")
        self.assertEqual(response.status_code, 401)

    def test_chat_requires_use_aiassistant_permission(self):
        self.client.force_authenticate(self.staff)
        response = self.client.post("/chat", {"question": "Tìm văn bản"}, format="json")
        self.assertEqual(response.status_code, 403)

    def test_categories_require_ai_permission(self):
        grant_codename(self.staff, "use_aiassistant")
        self.client.force_authenticate(self.staff)
        with patch("backend.api.views.list_categories", return_value=[]):
            response = self.client.get("/categories")
        self.assertEqual(response.status_code, 200)

    def test_document_management_is_admin_only(self):
        self.client.force_authenticate(self.staff)
        response = self.client.get("/documents")
        self.assertEqual(response.status_code, 403)

    def test_admin_can_read_ai_settings(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get("/settings/ai")
        self.assertEqual(response.status_code, 200)
