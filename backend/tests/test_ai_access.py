import json
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

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
        response = self.client.post("/api/ai/chat", {"question": "Tìm văn bản"}, format="json")
        self.assertEqual(response.status_code, 401)

    def test_chat_requires_use_aiassistant_permission(self):
        self.client.force_authenticate(self.no_perm)
        response = self.client.post("/api/ai/chat", {"question": "Tìm văn bản"}, format="json")
        self.assertEqual(response.status_code, 403)

    def test_categories_require_ai_permission(self):
        self.client.force_authenticate(self.no_perm)
        self.assertEqual(self.client.get("/api/ai/categories").status_code, 403)
        self.client.force_authenticate(self.ai_user)
        with patch("backend.api.views.list_categories", return_value=[]):
            response = self.client.get("/api/ai/categories")
        self.assertEqual(response.status_code, 200)

    def test_document_list_requires_ai_permission(self):
        self.client.force_authenticate(self.no_perm)
        self.assertEqual(self.client.get("/api/ai/documents").status_code, 403)
        self.client.force_authenticate(self.ai_user)
        with patch("backend.api.views.list_documents", return_value=[]):
            self.assertEqual(self.client.get("/api/ai/documents").status_code, 200)

    def test_management_endpoints_are_superuser_only(self):
        for user in (self.no_perm, self.ai_user):
            self.client.force_authenticate(user)
            self.assertEqual(self.client.delete("/api/ai/documents").status_code, 403)
            self.assertEqual(self.client.delete("/api/ai/documents/a.pdf").status_code, 403)
            self.assertEqual(self.client.post("/api/ai/settings", {"provider": "gemini"}, format="json").status_code, 403)

    def test_ai_user_reads_settings_without_api_key_info(self):
        self.client.force_authenticate(self.no_perm)
        self.assertEqual(self.client.get("/api/ai/settings").status_code, 403)
        self.client.force_authenticate(self.ai_user)
        response = self.client.get("/api/ai/settings")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("api_key_masked", response.json())
        self.assertNotIn("has_api_key", response.json())

    def test_superuser_can_read_ai_settings(self):
        self.client.force_authenticate(self.superuser)
        response = self.client.get("/api/ai/settings")
        self.assertEqual(response.status_code, 200)
        self.assertIn("api_key_masked", response.json())

    def test_chat_passes_authenticated_employee_id_not_request_body(self):
        self.client.force_authenticate(self.ai_user)
        ask = MagicMock(return_value={"answer": "ok"})
        fake_rag = SimpleNamespace(ask_document=ask)
        with patch.dict(sys.modules, {"backend.services.rag_service": fake_rag}):
            response = self.client.post(
                "/api/ai/chat",
                {"question": "Tìm văn bản", "employee_id": self.superuser.pk},
                format="json",
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ask.call_args.kwargs["employee_id"], self.ai_user.pk)

    def test_openai_settings_use_bearer_auth_and_supported_models(self):
        self.client.force_authenticate(self.superuser)
        fake_rag = SimpleNamespace(setup_llamaindex=MagicMock())
        response_body = {
            "data": [
                {"id": "gpt-4o-mini"},
                {"id": "text-embedding-3-small"},
            ]
        }
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(response_body).encode()
        mock_response.__enter__.return_value = mock_response

        with tempfile.TemporaryDirectory() as temp_dir:
            (Path(temp_dir) / "backend").mkdir()
            with (
                patch.dict(sys.modules, {"backend.services.rag_service": fake_rag}),
                patch("backend.services.rag_service", fake_rag),
                patch.dict("os.environ", {}, clear=False),
                patch("backend.api.views.config.OPENAI_API_KEY", "", create=True),
                patch("backend.api.views.urllib.request.urlopen", return_value=mock_response) as urlopen,
                patch.multiple(
                    "backend.api.views.config",
                    MODEL_PROVIDER="openai",
                    BASE_DIR=Path(temp_dir),
                    LLM_MODEL="gemini-3.8-flash",
                    EMBED_MODEL="models/gemini-embedding-001",
                    VISION_MODEL="gemini-3.8-flash",
                ),
            ):
                response = self.client.post(
                    "/api/ai/settings",
                    {
                        "provider": "openai",
                        "api_key": "test-openai-key",
                        "llm_model": "gpt-4o-mini",
                    },
                    format="json",
                )

        self.assertEqual(response.status_code, 200)
        request = urlopen.call_args.args[0]
        self.assertEqual(request.get_header("Authorization"), "Bearer test-openai-key")
