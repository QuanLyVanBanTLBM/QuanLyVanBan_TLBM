import json
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.http import StreamingHttpResponse
from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIClient

from backend.services.rag_service import format_sse

User = get_user_model()


def grant_codename(user, codename):
    user.user_permissions.add(Permission.objects.get(codename=codename))


class MockStreamChunk:
    def __init__(self, delta):
        self.delta = delta


class AIStreamingTests(TestCase):
    def setUp(self):
        self.no_perm = User.objects.create_user(username="stream_no_perm", password="password123")
        self.ai_user = User.objects.create_user(username="stream_user", password="password123")
        grant_codename(self.ai_user, "use_aiassistant")
        self.client = APIClient()

    def test_stream_requires_authentication(self):
        response = self.client.post("/api/ai/chat/stream", {"question": "Hello"}, format="json")
        self.assertEqual(response.status_code, 401)

    def test_stream_requires_use_aiassistant_permission(self):
        self.client.force_authenticate(user=self.no_perm)
        response = self.client.post("/api/ai/chat/stream", {"question": "Hello"}, format="json")
        self.assertEqual(response.status_code, 403)

    def test_stream_validates_empty_question(self):
        self.client.force_authenticate(user=self.ai_user)
        response = self.client.post("/api/ai/chat/stream", {"question": ""}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Câu hỏi không được để trống.", response.json().get("detail", ""))

    def test_stream_validates_too_long_question(self):
        self.client.force_authenticate(user=self.ai_user)
        response = self.client.post("/api/ai/chat/stream", {"question": "x" * 4001}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("4000 ký tự", response.json().get("detail", ""))

    @patch("backend.services.rag_service.Settings")
    @patch("backend.services.rag_service.setup_llamaindex")
    @patch("backend.services.rag_service.get_index")
    @patch("backend.services.business_knowledge.match_business_sources", return_value=[])
    @patch("backend.services.sql_document_source.accessible_documents", return_value=[])
    @patch("backend.services.sql_document_source.is_postgres_source", return_value=False)
    def test_chat_stream_returns_sse_response_with_correct_headers(
        self,
        _mock_pg,
        _mock_accessible,
        _mock_match,
        mock_get_index,
        _mock_setup,
        mock_settings,
    ):
        mock_retriever = MagicMock()
        mock_retriever.retrieve.return_value = []
        mock_get_index.return_value.as_retriever.return_value = mock_retriever

        self.client.force_authenticate(user=self.ai_user)
        response = self.client.post(
            "/api/ai/chat/stream",
            {"question": "Quy trình xin nghỉ phép như thế nào?"},
            format="json",
        )

        self.assertIsInstance(response, StreamingHttpResponse)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("Content-Type"), "text/event-stream; charset=utf-8")
        self.assertEqual(response.headers.get("Cache-Control"), "no-cache")
        self.assertEqual(response.headers.get("X-Accel-Buffering"), "no")

    @patch("backend.services.rag_service.Settings")
    @patch("backend.services.rag_service.setup_llamaindex")
    @patch("backend.services.rag_service.get_index")
    @patch("backend.services.rag_service.build_sources")
    @patch("backend.services.rag_service.build_context_from_sources", return_value="Ngữ cảnh văn bản")
    @patch("backend.services.business_knowledge.match_business_sources", return_value=[])
    @patch("backend.services.sql_document_source.accessible_documents", return_value=[])
    @patch("backend.services.sql_document_source.is_postgres_source", return_value=False)
    def test_chat_stream_emits_sources_delta_done_events(
        self,
        _mock_pg,
        _mock_accessible,
        _mock_match,
        _mock_context,
        mock_build_sources,
        mock_get_index,
        _mock_setup,
        mock_settings,
    ):
        mock_retriever = MagicMock()
        mock_retriever.retrieve.return_value = [MagicMock()]
        mock_get_index.return_value.as_retriever.return_value = mock_retriever
        mock_build_sources.return_value = [
            {
                "index": 1,
                "file_name": "qd_01.pdf",
                "page": 1,
                "section": None,
                "chunk_id": "c1",
                "category": None,
                "score": 0.95,
                "preview": "Quyết định 01",
                "context": "Nội dung quyết định",
            }
        ]

        mock_settings.llm.stream_complete.return_value = [
            MockStreamChunk("Theo "),
            MockStreamChunk("quy định, "),
            MockStreamChunk("cán bộ được nghỉ phép."),
        ]

        self.client.force_authenticate(user=self.ai_user)
        response = self.client.post(
            "/api/ai/chat/stream",
            {"question": "Quy trình nghỉ phép?"},
            format="json",
        )

        raw_events = list(response.streaming_content)
        joined_content = b"".join(raw_events).decode("utf-8")

        self.assertIn("event: sources", joined_content)
        self.assertIn("event: delta", joined_content)
        self.assertIn("event: done", joined_content)
        self.assertIn("cán bộ được nghỉ phép.", joined_content)

    @patch("backend.services.rag_service.Settings")
    @patch("backend.services.rag_service.setup_llamaindex")
    @patch("backend.services.rag_service.get_index")
    @patch("backend.services.business_knowledge.match_business_sources", return_value=[])
    @patch("backend.services.sql_document_source.accessible_documents", return_value=[])
    @patch("backend.services.sql_document_source.is_postgres_source", return_value=False)
    def test_chat_delegates_to_stream_when_flag_present(
        self,
        _mock_pg,
        _mock_accessible,
        _mock_match,
        mock_get_index,
        _mock_setup,
        mock_settings,
    ):
        mock_retriever = MagicMock()
        mock_retriever.retrieve.return_value = []
        mock_get_index.return_value.as_retriever.return_value = mock_retriever

        self.client.force_authenticate(user=self.ai_user)
        response = self.client.post(
            "/api/ai/chat",
            {"question": "Tra cứu tài liệu", "stream": True},
            format="json",
        )

        self.assertIsInstance(response, StreamingHttpResponse)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("Content-Type"), "text/event-stream; charset=utf-8")


class FormatSseUnitTests(SimpleTestCase):
    def test_format_sse_encodes_json(self):
        frame = format_sse("delta", {"text": "Xin chào"})
        self.assertEqual(frame, 'event: delta\ndata: {"text": "Xin chào"}\n\n')

    def test_format_sse_handles_list(self):
        frame = format_sse("sources", [{"name": "VB1"}])
        self.assertEqual(frame, 'event: sources\ndata: [{"name": "VB1"}]\n\n')
