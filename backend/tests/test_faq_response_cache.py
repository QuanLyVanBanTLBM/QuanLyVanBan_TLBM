from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase, TestCase
from llama_index.core.schema import Document, NodeWithScore, TextNode

from backend.services.ai_logging import end_trace, start_trace
from backend.services.pgvector_store import PgVectorCollection, insert_documents
from backend.services.faq_response_cache import (
    cache_key,
    clear_faq_cache,
    get_cached_answer,
    request_is_cacheable,
    set_cached_answer,
    sources_are_shareable,
)


class FaqResponseCacheTests(TestCase):
    def setUp(self):
        clear_faq_cache()

    def tearDown(self):
        clear_faq_cache()

    def test_key_normalizes_case_and_whitespace_but_separates_language(self):
        self.assertEqual(cache_key("  Quy   trình nghỉ lễ? "), cache_key("quy trình NGHỈ LỄ?"))
        self.assertNotEqual(cache_key("xin nghỉ", "vi"), cache_key("xin nghỉ", "en"))

    def test_request_with_personal_context_is_not_cacheable(self):
        self.assertTrue(request_is_cacheable("Lịch nghỉ lễ là gì?"))
        self.assertFalse(request_is_cacheable("Lịch nghỉ lễ là gì?", history=[{"role": "user"}]))
        self.assertFalse(request_is_cacheable("Quy trình?", filename="quy-trinh.pdf"))
        self.assertFalse(request_is_cacheable("Quy trình?", category="nội bộ"))
        self.assertFalse(request_is_cacheable("Xin chào", conversational=True))

    def test_only_shared_sources_can_seed_cross_user_entries(self):
        self.assertTrue(sources_are_shareable([{"source_type": "business_spec"}]))
        self.assertTrue(sources_are_shareable([{"source_class": "ai_knowledge_base", "category": "Quy trình nội bộ"}]))
        self.assertFalse(sources_are_shareable([{"source_class": "official_document"}]))
        self.assertFalse(sources_are_shareable([{"source_class": "ai_knowledge_base", "category": "Tài liệu hạn chế"}]))
        self.assertFalse(sources_are_shareable([]))
        self.assertFalse(set_cached_answer(
            "Hồ sơ cá nhân?", "vi", "Thông tin riêng",
            [{"source_class": "official_document"}],
        ))

    def test_cached_payload_round_trips_and_respects_entry_limit(self):
        self.assertTrue(set_cached_answer(
            "Câu hỏi phổ biến?", "vi", "Câu trả lời",
            [{"file_name": "Quy trình", "source_type": "business_spec"}],
        ))
        self.assertEqual(
            get_cached_answer(" câu hỏi   phổ biến? ", "vi"),
            {"answer": "Câu trả lời", "sources": [{"file_name": "Quy trình", "source_type": "business_spec"}]},
        )
        with patch("backend.services.faq_response_cache.MAX_ENTRY_BYTES", 8):
            self.assertFalse(set_cached_answer("Câu hỏi quá dài?", "vi", "Câu trả lời dài", []))
        self.assertIsNone(get_cached_answer("Câu hỏi quá dài?", "vi"))

    def test_lru_keeps_entry_count_bounded(self):
        with patch("backend.services.faq_response_cache.MAX_ENTRIES", 2):
            set_cached_answer("Một?", "vi", "A", [{"source_type": "business_spec"}])
            set_cached_answer("Hai?", "vi", "B", [{"source_type": "business_spec"}])
            get_cached_answer("Một?", "vi")
            set_cached_answer("Ba?", "vi", "C", [{"source_type": "business_spec"}])

        self.assertIsNone(get_cached_answer("Hai?", "vi"))
        self.assertEqual(get_cached_answer("Một?", "vi")["answer"], "A")
        self.assertEqual(get_cached_answer("Ba?", "vi")["answer"], "C")

    def test_lru_keeps_total_payload_bytes_bounded(self):
        with patch("backend.services.faq_response_cache.MAX_TOTAL_BYTES", 300):
            set_cached_answer("Một?", "vi", "A" * 100, [{"source_type": "business_spec"}])
            set_cached_answer("Hai?", "vi", "B" * 100, [{"source_type": "business_spec"}])

        self.assertIsNone(get_cached_answer("Một?", "vi"))
        self.assertEqual(get_cached_answer("Hai?", "vi")["answer"], "B" * 100)

    def test_shared_answer_is_reused_and_trace_records_cache_hit(self):
        from backend.services import rag_service

        filename = "faq-cache-shared-test.txt"
        document = Document(
            text="Lịch nghỉ lễ được thông báo theo quy trình nhân sự.",
            metadata={
                "file_name": filename,
                "category": "Quy trình nội bộ",
                "source_class": "ai_knowledge_base",
            },
        )
        ids = insert_documents([document], _StubEmbedding())
        node = NodeWithScore(
            node=TextNode(
                text="Lịch nghỉ lễ được thông báo theo quy trình nhân sự.",
                metadata={
                    "file_name": filename,
                    "category": "Quy trình nội bộ",
                    "source_class": "ai_knowledge_base",
                    "page": 1,
                },
            ),
            score=0.95,
        )
        retriever = Mock()
        retriever.retrieve.return_value = [node]
        index = Mock()
        index.as_retriever.return_value = retriever
        complete = Mock(return_value="Lịch nghỉ lễ do nhân sự thông báo.")
        fake_settings = SimpleNamespace(llm=SimpleNamespace(complete=complete))

        trace, token = start_trace()
        try:
            with (
                patch.object(rag_service, "is_inappropriate_message", return_value=False),
                patch.object(rag_service, "resolve_target_filename", return_value=None),
                patch.object(rag_service, "extract_target_from_question", return_value=None),
                patch.object(rag_service, "sync_documents_if_needed"),
                patch.object(rag_service, "setup_llamaindex"),
                patch.object(rag_service, "get_index", return_value=index),
                patch.object(rag_service, "Settings", fake_settings),
                patch("backend.services.sql_document_source.is_postgres_source", return_value=False),
                patch("backend.services.business_knowledge.match_business_sources", return_value=[]),
            ):
                first = rag_service.ask_document("Lịch nghỉ lễ như thế nào?")
                self.assertFalse(trace.fields["cache_hit"])
                second = rag_service.ask_document("  LỊCH nghỉ lễ như thế nào?  ")
        finally:
            end_trace(token)

        self.assertEqual(first, second)
        self.assertTrue(trace.fields["cache_hit"])
        self.assertEqual(complete.call_count, 1)
        PgVectorCollection().delete(ids=ids)

    def test_cache_hit_is_rejected_when_shared_source_becomes_restricted(self):
        filename = "faq-cache-scope-test.txt"
        document = Document(
            text="Quy trình xử lý hồ sơ dùng chung trong đơn vị.",
            metadata={
                "file_name": filename,
                "category": "Quy trình nội bộ",
                "source_class": "ai_knowledge_base",
            },
        )
        ids = insert_documents([document], _StubEmbedding())
        scope = [{
            "file_name": filename,
            "category": "Quy trình nội bộ",
            "source_class": "ai_knowledge_base",
        }]
        set_cached_answer("Quy trình hồ sơ là gì?", "vi", "Câu trả lời", [], eligible_sources=scope)
        self.assertIsNotNone(get_cached_answer("Quy trình hồ sơ là gì?", "vi"))

        collection = PgVectorCollection()
        metadata = collection.get(ids=ids)["metadatas"]
        metadata[0]["category"] = "Hạn chế"
        collection.update(ids=ids, metadatas=metadata)

        self.assertIsNone(get_cached_answer("Quy trình hồ sơ là gì?", "vi"))
        collection.delete(ids=ids)

    def test_cache_does_not_bypass_permission_or_sql_source_check(self):
        from backend.services import rag_service
        from backend.services.sql_document_source import SqlDocumentAccessError

        set_cached_answer(
            "Quy trình chung là gì?", "vi", "Câu trả lời đã cache",
            [{"file_name": "Quy trình", "source_type": "business_spec"}],
        )
        unauth_user = SimpleNamespace(is_authenticated=True, is_active=True, is_superuser=False)
        with patch("backend.services.ai_access.has_permission_codename", return_value=False):
            with self.assertRaises(SqlDocumentAccessError) as ctx:
                rag_service.ask_document("Quy trình chung là gì?", user=unauth_user, employee_id=1)
            self.assertEqual(ctx.exception.ai_reason, "no_ai_permission")

        auth_user = SimpleNamespace(is_authenticated=True, is_active=True, is_superuser=True)
        with (
            patch("backend.services.sql_document_source.is_postgres_source", return_value=True),
            patch(
                "backend.services.sql_document_source.accessible_document_keys",
                side_effect=SqlDocumentAccessError("No employee", ai_reason="employee_unresolved"),
            ),
        ):
            with self.assertRaises(SqlDocumentAccessError) as ctx:
                rag_service.ask_document("Quy trình chung là gì?", user=auth_user, employee_id=None)
            self.assertEqual(ctx.exception.ai_reason, "employee_unresolved")


class _StubEmbedding:
    def get_text_embedding_batch(self, texts, show_progress=False):
        return [[1.0] + [0.0] * 3071 for _ in texts]


class FaqCachePermissionAndBatchTests(SimpleTestCase):
    def setUp(self):
        clear_faq_cache()

    def tearDown(self):
        clear_faq_cache()

    def test_cache_does_not_bypass_permission_or_sql_source_check(self):
        from backend.services import rag_service
        from backend.services.sql_document_source import SqlDocumentAccessError

        set_cached_answer(
            "Quy trình chung là gì?", "vi", "Câu trả lời đã cache",
            [{"file_name": "Quy trình", "source_type": "business_spec"}],
        )
        unauth_user = SimpleNamespace(is_authenticated=True, is_active=True, is_superuser=False)
        with patch("backend.services.ai_access.has_permission_codename", return_value=False):
            with self.assertRaises(SqlDocumentAccessError) as ctx:
                rag_service.ask_document("Quy trình chung là gì?", user=unauth_user, employee_id=1)
            self.assertEqual(ctx.exception.ai_reason, "no_ai_permission")

        auth_user = SimpleNamespace(is_authenticated=True, is_active=True, is_superuser=True)
        with (
            patch("backend.services.sql_document_source.is_postgres_source", return_value=True),
            patch(
                "backend.services.sql_document_source.accessible_document_keys",
                side_effect=SqlDocumentAccessError("No employee", ai_reason="employee_unresolved"),
            ),
        ):
            with self.assertRaises(SqlDocumentAccessError) as ctx:
                rag_service.ask_document("Quy trình chung là gì?", user=auth_user, employee_id=None)
            self.assertEqual(ctx.exception.ai_reason, "employee_unresolved")

    def test_scope_sources_validation_uses_single_batched_query(self):
        from backend.services.faq_response_cache import _scope_sources_are_current

        fake_cursor = Mock()
        fake_cursor.fetchall.return_value = [
            ("doc1.pdf", "ai_knowledge_base", "Quy trình"),
            ("doc2.pdf", "ai_knowledge_base", "Hướng dẫn"),
        ]
        fake_conn = Mock()
        fake_conn.cursor.return_value.__enter__ = Mock(return_value=fake_cursor)
        fake_conn.cursor.return_value.__exit__ = Mock(return_value=False)

        scope = [
            {"file_name": "doc1.pdf", "category": "Quy trình"},
            {"file_name": "doc2.pdf", "category": "Hướng dẫn"},
        ]
        with patch("django.db.connection", fake_conn):
            self.assertTrue(_scope_sources_are_current(scope))

        self.assertEqual(fake_cursor.execute.call_count, 1)
        sql, params = fake_cursor.execute.call_args.args
        self.assertIn("ANY(%s)", sql)
        self.assertEqual(params, [["doc1.pdf", "doc2.pdf"]])
