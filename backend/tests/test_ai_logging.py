import sys
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIClient

from backend.services import ai_logging
from backend.services.ai_logging import (
    add_count,
    ai_stage,
    end_trace,
    format_summary,
    log_summary,
    mark_error,
    set_fields,
    start_trace,
)
from backend.services.sql_document_source import (
    SqlDocumentAccessError,
    _assert_readonly_connection,
    _employee_id_value,
    accessible_documents,
)

User = get_user_model()


def grant_codename(user, codename):
    user.user_permissions.add(Permission.objects.get(codename=codename))


class FakeCursor:
    def __init__(self, fetchone_row=None):
        self.fetchone_row = fetchone_row

    def execute(self, _query, _params=None):
        return None

    def fetchone(self):
        return self.fetchone_row


class AiTraceTests(SimpleTestCase):
    def test_first_error_stage_is_kept_and_later_errors_are_ignored(self):
        trace, token = start_trace(user_id=7)
        try:
            with self.assertRaises(ValueError):
                with ai_stage("sql_index"):
                    raise ValueError("boom")
            with self.assertRaises(SqlDocumentAccessError):
                with ai_stage("sql_source"):
                    raise SqlDocumentAccessError("x", ai_reason="readonly_alias_missing")
        finally:
            end_trace(token)
        self.assertEqual(trace.error_stage, "sql_index")
        self.assertEqual(trace.error_reason, "ValueError")
        self.assertIn("sql_source", trace.stages)

    def test_ai_reason_becomes_error_reason(self):
        trace, token = start_trace()
        try:
            with self.assertRaises(SqlDocumentAccessError):
                with ai_stage("sql_source"):
                    raise SqlDocumentAccessError("x", ai_reason="readonly_alias_missing")
        finally:
            end_trace(token)
        self.assertEqual(trace.error_stage, "sql_source")
        self.assertEqual(trace.error_reason, "readonly_alias_missing")

    def test_helpers_do_nothing_without_active_trace(self):
        set_fields(question_chars=3)
        add_count("sql_reindexed")
        mark_error("retrieval", "ValueError")
        with ai_stage("llm"):
            pass
        self.assertIsNone(ai_logging._current_trace.get())

    def test_add_count_accumulates_and_summary_omits_content(self):
        trace, token = start_trace(user_id=3)
        try:
            add_count("sql_reindexed")
            add_count("sql_reindexed", 2)
            set_fields(question_chars=12, answer_mode="llm")
        finally:
            end_trace(token)
        summary = format_summary(trace, 200)
        self.assertIn("sql_reindexed=3", summary)
        self.assertIn("question_chars=12", summary)
        self.assertIn("answer_mode=llm", summary)
        self.assertIn("status=200", summary)
        self.assertNotIn("error_stage", summary)

    def test_summary_level_follows_status(self):
        trace, token = start_trace()
        try:
            with self.assertLogs("qlvb.ai", level="ERROR") as logs:
                log_summary(trace, 503)
        finally:
            end_trace(token)
        self.assertIn("status=503", logs.output[0])


class SqlDocumentReasonTests(SimpleTestCase):
    def test_missing_employee_id_has_reason(self):
        with self.assertRaises(SqlDocumentAccessError) as ctx:
            _employee_id_value(None)
        self.assertEqual(ctx.exception.ai_reason, "employee_unresolved")

    def test_invalid_employee_id_has_reason(self):
        for value in ("abc", 0):
            with self.assertRaises(SqlDocumentAccessError) as ctx:
                _employee_id_value(value)
            self.assertEqual(ctx.exception.ai_reason, "employee_id_invalid")

    def test_role_mismatch_has_reason(self):
        with self.assertRaises(SqlDocumentAccessError) as ctx:
            _assert_readonly_connection(FakeCursor(fetchone_row=("postgres", True, False, False)))
        self.assertEqual(ctx.exception.ai_reason, "readonly_role_mismatch")

    @patch("backend.services.sql_document_source.is_postgres_source", return_value=True)
    @patch("backend.services.sql_document_source.has_permission_codename", return_value=True)
    @patch(
        "backend.services.sql_document_source.van_ban_xem_duoc",
        return_value=SimpleNamespace(values_list=lambda *_a, **_k: []),
    )
    def test_missing_readonly_alias_has_reason(self, _van_ban, _perm, _is_pg):
        fake_connections = SimpleNamespace(databases={})
        with patch("backend.services.sql_document_source.connections", fake_connections):
            with self.assertRaises(SqlDocumentAccessError) as ctx:
                accessible_documents(SimpleNamespace(), employee_id=1)
        self.assertEqual(ctx.exception.ai_reason, "readonly_alias_missing")


class AiChatLogViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="ai_log_user", password="test-password")
        grant_codename(self.user, "use_aiassistant")
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    @patch("api.views.resolve_employee_id", return_value=None)
    def test_sql_source_failure_logs_stage_and_reason(self, _resolve):
        def failing_ask(*_args, **_kwargs):
            with ai_stage("sql_source"):
                raise SqlDocumentAccessError("x", ai_reason="readonly_alias_missing")

        fake_rag = SimpleNamespace(ask_document=failing_ask)
        with patch.dict(sys.modules, {"backend.services.rag_service": fake_rag}):
            with self.assertLogs("qlvb.ai", level="ERROR") as logs:
                response = self.client.post("/api/ai/chat", {"question": "Tìm văn bản"}, format="json")
        self.assertEqual(response.status_code, 503)
        summaries = [line for line in logs.output if "ai_chat request_id=" in line and "status=503" in line]
        self.assertEqual(len(summaries), 1)
        self.assertIn("error_stage=sql_source", summaries[0])
        self.assertIn("error_reason=readonly_alias_missing", summaries[0])
        self.assertIn("employee_resolved=False", summaries[0])
        self.assertIn("question_chars=", summaries[0])
        self.assertNotIn("Tìm văn bản", summaries[0])

    @patch("api.views.resolve_employee_id", return_value=None)
    def test_missing_employee_mapping_is_localized_in_real_chain(self, _resolve):
        with self.assertLogs("qlvb.ai", level="ERROR") as logs:
            response = self.client.post(
                "/api/ai/chat", {"question": "Quy trình xin nghỉ phép của đơn vị là gì?"}, format="json"
            )
        self.assertEqual(response.status_code, 503)
        summary = next(line for line in logs.output if "ai_chat request_id=" in line and "status=503" in line)
        self.assertIn("error_stage=sql_source", summary)
        self.assertIn("error_reason=employee_unresolved", summary)

    def test_permission_denial_is_logged_with_reason(self):
        other = User.objects.create_user(username="ai_log_no_perm", password="test-password")
        self.client.force_authenticate(other)
        with self.assertLogs("qlvb.ai", level="WARNING") as logs:
            response = self.client.post("/api/ai/chat", {"question": "Tìm văn bản"}, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertTrue(any(
            "status=403" in line and "error_stage=permission" in line and "error_reason=no_ai_permission" in line
            for line in logs.output
        ))

    def test_successful_answer_logs_answer_mode(self):
        def ok_ask(*_args, **_kwargs):
            set_fields(answer_mode="llm", sources=2)
            return {"answer": "ok", "sources": []}

        fake_rag = SimpleNamespace(ask_document=ok_ask)
        with patch.dict(sys.modules, {"backend.services.rag_service": fake_rag}):
            with self.assertLogs("qlvb.ai", level="INFO") as logs:
                response = self.client.post("/api/ai/chat", {"question": "Hello"}, format="json")
        self.assertEqual(response.status_code, 200)
        summary = next(line for line in logs.output if "status=200" in line)
        self.assertIn("answer_mode=llm", summary)
        self.assertIn("sources=2", summary)
        self.assertNotIn("error_stage", summary)
