from io import StringIO
from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

from django.core.management import call_command
from django.test import SimpleTestCase, TestCase

from documents.signals import (
    _trigger_sync,
    handle_tailieu_change,
    handle_vanbanden_attachment_change,
    handle_vanbanden_change,
    handle_vanbandi_attachment_change,
    handle_vanbandi_change,
)
from documents.tasks import sync_registered_ai_documents, sync_sql_document_vectors
from backend.services.rag_service import ask_document, delete_sql_document_vectors, is_ai_configured
from backend.services.sql_document_source import (
    get_all_document_records_for_index,
    get_document_record_for_index,
)


class CeleryIndexingTaskTests(SimpleTestCase):
    @patch("backend.services.rag_service.is_ai_configured", return_value=True)
    @patch("backend.services.rag_service.index_sql_document", return_value="vanbanden:1")
    @patch(
        "backend.services.sql_document_source.get_document_record_for_index",
        return_value={
            "source_type": "vanbanden",
            "source_id": 1,
            "display_name": "VB Đến 1",
            "attachments": [],
        },
    )
    def test_sync_sql_document_vectors_success(self, mock_get_rec, mock_index, _mock_cfg):
        result = sync_sql_document_vectors("vanbanden", 1)
        mock_get_rec.assert_called_once_with("vanbanden", 1)
        mock_index.assert_called_once()
        self.assertTrue(result)

    @patch("backend.services.rag_service.is_ai_configured", return_value=False)
    @patch("backend.services.rag_service.index_sql_document")
    @patch(
        "backend.services.sql_document_source.get_document_record_for_index",
        return_value={
            "source_type": "vanbanden",
            "source_id": 1,
            "display_name": "VB Đến 1",
            "attachments": [],
        },
    )
    def test_sync_sql_document_vectors_skips_when_ai_not_configured(self, mock_get_rec, mock_index, _mock_cfg):
        result = sync_sql_document_vectors("vanbanden", 1)
        mock_get_rec.assert_called_once_with("vanbanden", 1)
        mock_index.assert_not_called()
        self.assertFalse(result)

    @patch("backend.services.rag_service.delete_sql_document_vectors")
    @patch("backend.services.sql_document_source.get_document_record_for_index", return_value=None)
    def test_sync_sql_document_vectors_deletes_when_missing(self, mock_get_rec, mock_delete):
        result = sync_sql_document_vectors("vanbanden", 99)
        mock_get_rec.assert_called_once_with("vanbanden", 99)
        mock_delete.assert_called_once_with("vanbanden", 99)
        self.assertFalse(result)

    @patch("backend.services.rag_service.get_vector_collection")
    def test_delete_sql_document_vectors(self, mock_get_collection):
        mock_col = MagicMock()
        mock_get_collection.return_value = mock_col
        delete_sql_document_vectors("vanbanden", 42)
        mock_col.delete.assert_called_once_with(where={"sql_doc_key": "vanbanden:42"})

    @patch("backend.services.rag_service.sync_documents_if_needed")
    @patch("backend.services.rag_service.is_ai_configured", return_value=True)
    def test_sync_registered_ai_documents_task_runs_when_configured(self, _mock_cfg, mock_sync):
        self.assertTrue(sync_registered_ai_documents())
        mock_sync.assert_called_once_with()

    @patch("backend.services.rag_service.sync_documents_if_needed")
    @patch("backend.services.rag_service.is_ai_configured", return_value=False)
    def test_sync_registered_ai_documents_task_skips_when_unconfigured(self, _mock_cfg, mock_sync):
        self.assertFalse(sync_registered_ai_documents())
        mock_sync.assert_not_called()


class AskDocumentNoSyncIndexingTests(SimpleTestCase):
    @patch("backend.services.rag_service.sync_documents_if_needed")
    @patch("backend.services.rag_service.Settings")
    @patch("backend.services.rag_service.get_index")
    @patch("backend.services.rag_service.setup_llamaindex")
    @patch("backend.services.business_knowledge.match_business_sources", return_value=[])
    @patch("backend.services.rag_service.index_sql_document")
    @patch("backend.services.sql_document_source.accessible_document_keys")
    @patch("backend.services.sql_document_source.is_postgres_source", return_value=True)
    def test_ask_document_does_not_call_index_sql_document_or_sync_registry(
        self,
        mock_is_pg,
        mock_accessible_keys,
        mock_index_sql,
        _match_biz,
        _setup,
        mock_get_index,
        mock_settings,
        mock_sync_docs,
    ):
        mock_accessible_keys.return_value = {"vanbanden:1", "vanbandi:2", "tailieu:3"}
        mock_retriever = MagicMock()
        mock_retriever.retrieve.return_value = []
        mock_get_index.return_value.as_retriever.return_value = mock_retriever

        result = ask_document("Thủ tục trình ký như thế nào?")
        # Crucial checks: neither index_sql_document nor sync_documents_if_needed may run in chat!
        mock_index_sql.assert_not_called()
        mock_sync_docs.assert_not_called()
        mock_accessible_keys.assert_called_once()
        self.assertIn("answer", result)

        # Verify filters passed to retriever include allowed_keys
        call_kwargs = mock_get_index.return_value.as_retriever.call_args[1]
        filters = call_kwargs.get("filters")
        self.assertIsNotNone(filters)
        sql_filter = next(
            (f for f in filters.filters if getattr(f, "key", None) == "sql_doc_key"),
            None,
        )
        self.assertIsNotNone(sql_filter)
        self.assertEqual(set(sql_filter.value), {"vanbanden:1", "vanbandi:2", "tailieu:3"})


class DocumentSignalsTests(TestCase):
    @patch("documents.tasks.sync_sql_document_vectors.delay")
    def test_signals_trigger_celery_task_on_commit(self, mock_delay):
        with self.captureOnCommitCallbacks(execute=True):
            instance = SimpleNamespace(pk=10)
            handle_vanbanden_change(None, instance)
        mock_delay.assert_called_once_with("vanbanden", 10)

    @patch("documents.tasks.sync_sql_document_vectors.delay")
    def test_attachment_signals_trigger_celery_task_on_commit(self, mock_delay):
        with self.captureOnCommitCallbacks(execute=True):
            instance = SimpleNamespace(document_id=20)
            handle_vanbanden_attachment_change(None, instance)
        mock_delay.assert_called_once_with("vanbanden", 20)

    @patch("documents.tasks.sync_sql_document_vectors.delay")
    def test_vanbandi_signals_trigger_celery_task(self, mock_delay):
        with self.captureOnCommitCallbacks(execute=True):
            instance = SimpleNamespace(pk=30)
            handle_vanbandi_change(None, instance)
        mock_delay.assert_called_once_with("vanbandi", 30)

    @patch("documents.tasks.sync_sql_document_vectors.delay")
    def test_tailieu_signals_trigger_celery_task(self, mock_delay):
        with self.captureOnCommitCallbacks(execute=True):
            instance = SimpleNamespace(pk=40)
            handle_tailieu_change(None, instance)
        mock_delay.assert_called_once_with("tailieu", 40)


class ReindexCommandTests(SimpleTestCase):
    @patch("backend.services.rag_service.index_sql_document", side_effect=["vanbanden:1", None])
    @patch(
        "backend.services.sql_document_source.get_all_document_records_for_index",
        return_value=[
            {"source_type": "vanbanden", "source_id": 1},
            {"source_type": "vanbandi", "source_id": 2},
        ],
    )
    @patch("backend.services.rag_service.get_vector_collection")
    def test_reindex_command_execution(self, mock_get_col, mock_get_all, mock_index):
        mock_col = MagicMock()
        mock_get_col.return_value = mock_col

        out = StringIO()
        call_command("reindex_ai_documents", "--clear", stdout=out)
        output = out.getvalue()

        mock_col.delete.assert_called_once_with(where={"source_class": "official_document"})
        mock_get_all.assert_called_once_with(source_type=None)
        self.assertEqual(mock_index.call_count, 2)
        self.assertIn("Hoàn thành lập chỉ mục: 1 thành công, 1 bỏ qua, 0 lỗi.", output)


class SqlDocumentSourceHelperTests(SimpleTestCase):
    @patch("backend.services.sql_document_source.is_postgres_source", return_value=False)
    def test_get_document_record_for_index_non_pg(self, _is_pg):
        self.assertIsNone(get_document_record_for_index("vanbanden", 1))
        self.assertEqual(get_all_document_records_for_index(), [])

    @patch("backend.services.sql_document_source.is_postgres_source", return_value=True)
    def test_get_document_record_for_index_invalid_args(self, _is_pg):
        self.assertIsNone(get_document_record_for_index("unknown_type", 1))
        self.assertIsNone(get_document_record_for_index("vanbanden", "abc"))
