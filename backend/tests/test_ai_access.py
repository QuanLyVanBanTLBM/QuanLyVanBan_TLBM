import json
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from rest_framework.test import APIClient, APIRequestFactory, force_authenticate

from authorization.models import GroupInfo
from backend.api.views import document_file
from backend.services.ai_access import has_permission_codename, is_ai_admin, resolve_employee_id

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

    def test_ai_admin_is_system_admin_only(self):
        self.assertFalse(is_ai_admin(self.no_perm))
        self.assertFalse(is_ai_admin(self.ai_user))
        self.assertTrue(is_ai_admin(self.superuser))

    def test_ai_admin_grants_admin_group_and_denies_other_groups(self):
        other_group = Group.objects.create(name="ai_non_admin_group")
        admin_group = Group.objects.get(pk=GroupInfo.objects.get(ma_nhom_quyen="ADMIN").pk)

        staff_user = User.objects.create_user(username="ai_staff_group", password="test-password")
        staff_user.groups.add(other_group)
        admin_group_user = User.objects.create_user(username="ai_admin_group", password="test-password")
        admin_group_user.groups.add(admin_group)

        self.assertFalse(is_ai_admin(staff_user))
        self.assertTrue(is_ai_admin(admin_group_user))

    def test_chat_requires_authentication(self):
        response = self.client.post("/api/ai/chat", {"question": "Tìm văn bản"}, format="json")
        self.assertEqual(response.status_code, 401)

    def test_chat_requires_use_aiassistant_permission(self):
        self.client.force_authenticate(self.no_perm)
        response = self.client.post("/api/ai/chat", {"question": "Tìm văn bản"}, format="json")
        self.assertEqual(response.status_code, 403)

    def test_chat_denies_before_validating_body(self):
        self.client.force_authenticate(self.no_perm)
        for body in ({}, {"question": ""}, {"question": "x" * 5000}, {"question": "ok", "history": "sai"}):
            response = self.client.post("/api/ai/chat", body, format="json")
            self.assertEqual(response.status_code, 403, body)

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
        payload = response.json()
        self.assertIn("configured", payload)
        self.assertIsInstance(payload["configured"], bool)
        self.assertNotIn("api_key_masked", payload)
        self.assertNotIn("has_api_key", payload)

    def test_superuser_can_read_ai_settings(self):
        self.client.force_authenticate(self.superuser)
        response = self.client.get("/api/ai/settings")
        self.assertEqual(response.status_code, 200)
        self.assertIn("api_key_masked", response.json())
        self.assertEqual(response.json()["provider"], "openai")
        self.assertEqual(
            response.json()["model_options"]["openai"]["llm_models"],
            ["gpt-6-luna", "gpt-4o-mini", "gpt-4o"],
        )

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

    def test_chat_passes_language_to_ask_document(self):
        self.client.force_authenticate(self.ai_user)
        ask = MagicMock(return_value={"answer": "ok"})
        fake_rag = SimpleNamespace(ask_document=ask)
        with patch.dict(sys.modules, {"backend.services.rag_service": fake_rag}):
            response = self.client.post(
                "/api/ai/chat",
                {"question": "Hello", "language": "en"},
                format="json",
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ask.call_args.kwargs["language"], "en")
        self.assertEqual(response.json()["language"], "en")

    def test_openai_settings_use_bearer_auth_and_supported_models(self):
        self.client.force_authenticate(self.superuser)
        fake_rag = SimpleNamespace(setup_llamaindex=MagicMock())
        response_body = {
            "data": [
                {"id": "gpt-6-luna"},
                {"id": "text-embedding-3-small"},
                {"id": "text-embedding-3-large"},
            ]
        }
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(response_body).encode()
        mock_response.__enter__.return_value = mock_response

        with tempfile.TemporaryDirectory() as temp_dir:
            (Path(temp_dir) / "backend").mkdir()
            with (
                patch.dict(sys.modules, {"backend.services.rag_service": fake_rag}),
                patch("backend.services.rag_service", fake_rag, create=True),
                patch.dict("os.environ", {}, clear=False),
                patch("backend.api.views.config.OPENAI_API_KEY", "", create=True),
                patch("backend.api.views.urllib.request.urlopen", return_value=mock_response) as urlopen,
                patch.multiple(
                    "backend.api.views.config",
                    MODEL_PROVIDER="openai",
                    BASE_DIR=Path(temp_dir),
                    DATA_DIR=Path(temp_dir) / "data",
                    LLM_MODEL="gpt-6-luna",
                    EMBED_MODEL="text-embedding-3-large",
                    VISION_MODEL="gpt-6-luna",
                ),
            ):
                response = self.client.post(
                    "/api/ai/settings",
                    {
                        "provider": "openai",
                        "api_key": "test-openai-key",
                        "llm_model": "gpt-6-luna",
                    },
                    format="json",
                )

        self.assertEqual(response.status_code, 200)
        request = urlopen.call_args.args[0]
        self.assertEqual(request.get_header("Authorization"), "Bearer test-openai-key")

    def test_switch_from_legacy_gemini_config_to_openai_succeeds(self):
        self.client.force_authenticate(self.superuser)
        fake_rag = SimpleNamespace(
            setup_llamaindex=MagicMock(),
            sync_documents_if_needed=MagicMock(),
        )
        response_body = {
            "data": [
                {"id": "gpt-6-luna"},
                {"id": "text-embedding-3-large"},
            ]
        }
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(response_body).encode()
        mock_response.__enter__.return_value = mock_response

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            (temp_path / "backend").mkdir()
            (temp_path / "data").mkdir()
            with (
                patch.dict(sys.modules, {"backend.services.rag_service": fake_rag}),
                patch("backend.services.rag_service", fake_rag, create=True),
                patch.dict("os.environ", {}, clear=False),
                patch("backend.api.views.config.OPENAI_API_KEY", "", create=True),
                patch("backend.api.views.urllib.request.urlopen", return_value=mock_response),
                patch.multiple(
                    "backend.api.views.config",
                    MODEL_PROVIDER="gemini",
                    BASE_DIR=temp_path,
                    DATA_DIR=temp_path / "data",
                    LLM_MODEL="gemini-3.8-flash",
                    EMBED_MODEL="models/gemini-embedding-001",
                    VISION_MODEL="gemini-3.8-flash",
                ),
            ):
                response = self.client.post(
                    "/api/ai/settings",
                    {
                        "provider": "openai",
                        "api_key": "sk-mock-key-1234567890",
                        "llm_model": "gpt-6-luna",
                    },
                    format="json",
                )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["provider"], "openai")
        self.assertEqual(response.json()["llm_model"], "gpt-6-luna")

    def test_documents_and_categories_pass_resolved_employee_id(self):
        self.client.force_authenticate(self.ai_user)
        mock_accessible = MagicMock(
            return_value=[
                {
                    "source_type": "tailieu",
                    "source_id": 10,
                    "display_name": "01/TL — Quy trình nội bộ",
                    "updated_at": None,
                }
            ]
        )
        with (
            patch("api.views.list_documents", return_value=[]),
            patch("api.views.list_categories", return_value=[]),
            patch("backend.api.views.list_documents", return_value=[]),
            patch("backend.api.views.list_categories", return_value=[]),
            patch("backend.services.sql_document_source.is_postgres_source", return_value=True),
            patch("backend.services.sql_document_source.accessible_documents", mock_accessible),
        ):
            docs_resp = self.client.get("/api/ai/documents")
            cats_resp = self.client.get("/api/ai/categories")

        self.assertEqual(docs_resp.status_code, 200)
        self.assertEqual(len(docs_resp.json()["documents"]), 1)
        self.assertTrue(docs_resp.json()["documents"][0]["is_managed"])
        self.assertEqual(cats_resp.status_code, 200)
        self.assertEqual(mock_accessible.call_count, 2)
        for call in mock_accessible.call_args_list:
            self.assertEqual(call.kwargs["employee_id"], self.ai_user.pk)

    def test_reclassify_rejects_path_traversal(self):
        self.client.force_authenticate(self.superuser)
        response = self.client.post("/api/ai/reclassify/..%2Fsecret.txt")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Tên tệp không hợp lệ.")

    def test_preview_and_reclassify_hide_raw_exception_details(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            docs_dir = Path(temp_dir)
            sample_file = docs_dir / "tài liệu mẫu.docx"
            sample_file.write_bytes(b"not-a-valid-docx")

            self.client.force_authenticate(self.ai_user)
            with (
                patch("backend.config.DOCS_DIR", docs_dir),
                patch("backend.services.rag_service.read_docx", side_effect=RuntimeError("SECRET_STACK_TRACE")),
            ):
                preview_resp = self.client.get("/api/ai/documents/t%C3%A0i%20li%E1%BB%87u%20m%E1%BA%ABu.docx/preview")
            self.assertEqual(preview_resp.status_code, 500)
            self.assertNotIn("SECRET_STACK_TRACE", preview_resp.json()["detail"])

            self.client.force_authenticate(self.superuser)
            with (
                patch("api.views.list_documents", return_value=[{"filename": "tài liệu mẫu.docx", "path": str(sample_file)}]),
                patch("backend.api.views.list_documents", return_value=[{"filename": "tài liệu mẫu.docx", "path": str(sample_file)}]),
                patch("backend.services.rag_service.setup_llamaindex", side_effect=RuntimeError("SECRET_RECLASSIFY_ERR")),
            ):
                reclassify_resp = self.client.post("/api/ai/reclassify/t%C3%A0i%20li%E1%BB%87u%20m%E1%BA%ABu.docx")
            self.assertEqual(reclassify_resp.status_code, 500)
            self.assertNotIn("SECRET_RECLASSIFY_ERR", reclassify_resp.json()["detail"])

    def test_document_file_uses_rfc5987_content_disposition(self):
        factory = APIRequestFactory()
        with tempfile.TemporaryDirectory() as temp_dir:
            docs_dir = Path(temp_dir)
            sample_file = docs_dir / "tài liệu mẫu.txt"
            sample_file.write_text("hello", encoding="utf-8")

            request = factory.get("/api/ai/documents/t%C3%A0i%20li%E1%BB%87u%20m%E1%BA%ABu.txt/file")
            force_authenticate(request, user=self.ai_user)
            with patch("backend.config.DOCS_DIR", docs_dir):
                response = document_file(request, "tài liệu mẫu.txt")
            try:
                self.assertEqual(response.status_code, 200)
                disposition = response.headers.get("Content-Disposition", "")
                self.assertIn("inline;", disposition)
                self.assertIn("filename*=UTF-8''t%C3%A0i%20li%E1%BB%87u%20m%E1%BA%ABu.txt", disposition)
            finally:
                for closer in list(getattr(response, "_resource_closers", ())):
                    closer()
                response._resource_closers.clear()

    def test_sync_status_endpoint_requires_admin_and_returns_schedule_telemetry(self):
        self.client.force_authenticate(self.ai_user)
        self.assertEqual(self.client.get("/api/ai/sync/status").status_code, 403)
        self.assertEqual(self.client.post("/api/ai/sync", {}, format="json").status_code, 404)

        self.client.force_authenticate(self.superuser)
        mock_collection = MagicMock()
        mock_collection.indexed_filenames.return_value = {"kept.pdf", "orphan.gif"}
        fake_schema = {"status": "ok", "checked_views": 6, "missing_views": [], "missing_columns": {}}

        with (
            patch("api.views.list_documents", return_value=[{"filename": "kept.pdf"}]),
            patch("backend.api.views.list_documents", return_value=[{"filename": "kept.pdf"}]),
            patch("backend.services.rag_service.get_vector_collection", return_value=mock_collection),
            patch("backend.services.sql_document_source.is_postgres_source", return_value=False),
            patch("backend.services.sql_document_source.verify_sql_schema", return_value=fake_schema),
        ):
            status_resp = self.client.get("/api/ai/sync/status")

        self.assertEqual(status_resp.status_code, 200)
        status_body = status_resp.json()
        self.assertEqual(status_body["kb_registered"], 1)
        self.assertEqual(status_body["kb_indexed"], 2)
        self.assertEqual(status_body["kb_orphans"], 1)
        self.assertEqual(status_body["kb_orphan_names"], ["orphan.gif"])
        self.assertEqual(status_body["schema"]["status"], "ok")
        self.assertEqual(status_body["schedule"]["enabled"], True)
        self.assertEqual(status_body["schedule"]["task"], "sync_all_ai_documents")
        self.assertEqual(status_body["schedule"]["time"], "02:00")
        self.assertEqual(status_body["schedule"]["cron"], "0 2 * * *")
        self.assertTrue(status_body["schedule"]["next_run_at"])

    def test_documents_endpoint_filters_restricted_and_hidden_official_docs_and_exposes_validity(self):
        from documents.models import HieuLuc, PhamVi, VanBanDen

        self.client.force_authenticate(self.ai_user)
        internal_den = VanBanDen.objects.create(
            nam=2099,
            so_hieu="10/CV-NOIBO",
            so_thu_tu=30001,
            trich_yeu="Văn bản nội bộ",
            pham_vi=PhamVi.NOI_BO,
            hien_thi=True,
            hieu_luc=HieuLuc.CON_HIEU_LUC_1_PHAN,
        )
        restricted_den = VanBanDen.objects.create(
            nam=2099,
            so_hieu="11/CV-HANCHE",
            so_thu_tu=30002,
            trich_yeu="Văn bản hạn chế",
            pham_vi=PhamVi.HAN_CHE,
            hien_thi=True,
            hieu_luc=HieuLuc.CON_HIEU_LUC,
        )
        hidden_den = VanBanDen.objects.create(
            nam=2099,
            so_hieu="12/CV-AN",
            so_thu_tu=30003,
            trich_yeu="Văn bản ẩn",
            pham_vi=PhamVi.NOI_BO,
            hien_thi=False,
            hieu_luc=HieuLuc.CON_HIEU_LUC,
        )

        mock_records = [
            {
                "source_type": "vanbanden",
                "source_id": internal_den.pk,
                "display_name": "10/CV-NOIBO — Văn bản nội bộ",
                "so_hieu": "10/CV-NOIBO",
                "hieu_luc": HieuLuc.CON_HIEU_LUC_1_PHAN,
                "ngay_het_hieu_luc": None,
                "updated_at": None,
            },
            {
                "source_type": "vanbanden",
                "source_id": restricted_den.pk,
                "display_name": "11/CV-HANCHE — Văn bản hạn chế",
                "so_hieu": "11/CV-HANCHE",
                "hieu_luc": HieuLuc.CON_HIEU_LUC,
                "ngay_het_hieu_luc": None,
                "updated_at": None,
            },
            {
                "source_type": "vanbanden",
                "source_id": hidden_den.pk,
                "display_name": "12/CV-AN — Văn bản ẩn",
                "so_hieu": "12/CV-AN",
                "hieu_luc": HieuLuc.CON_HIEU_LUC,
                "ngay_het_hieu_luc": None,
                "updated_at": None,
            },
        ]

        with (
            patch("api.views.list_documents", return_value=[]),
            patch("backend.api.views.list_documents", return_value=[]),
            patch("backend.services.sql_document_source.is_postgres_source", return_value=True),
            patch("backend.services.sql_document_source.accessible_documents", return_value=mock_records),
        ):
            resp = self.client.get("/api/ai/documents")

        self.assertEqual(resp.status_code, 200)
        docs = resp.json()["documents"]
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0]["source_id"], internal_den.pk)
        self.assertEqual(docs[0]["so_hieu"], "10/CV-NOIBO")
        self.assertEqual(docs[0]["hieu_luc"], HieuLuc.CON_HIEU_LUC_1_PHAN)
        self.assertIsNone(docs[0]["ngay_het_hieu_luc"])
