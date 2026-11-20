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
    handle_vanbandi_noibanhanh_change,
)
from documents.services import check_and_update_expired_documents
from documents.tasks import sync_registered_ai_documents, sync_sql_document_vectors
from backend.services.rag_service import ask_document, delete_sql_document_vectors, is_ai_configured
from backend.services.sql_document_source import (
    get_all_document_records_for_index,
    get_document_record_for_index,
)


class CeleryIndexingTaskTests(SimpleTestCase):
    @patch("backend.services.faq_response_cache.clear_faq_cache")
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
    def test_sync_sql_document_vectors_success(self, mock_get_rec, mock_index, _mock_cfg, mock_clear_cache):
        result = sync_sql_document_vectors("vanbanden", 1)
        mock_get_rec.assert_called_once_with("vanbanden", 1)
        mock_index.assert_called_once()
        mock_clear_cache.assert_called_once_with()
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

    @patch("backend.services.faq_response_cache.clear_faq_cache")
    @patch("backend.services.rag_service.delete_sql_document_vectors")
    @patch("backend.services.sql_document_source.get_document_record_for_index", return_value=None)
    def test_sync_sql_document_vectors_deletes_when_missing(self, mock_get_rec, mock_delete, mock_clear_cache):
        result = sync_sql_document_vectors("vanbanden", 99)
        mock_get_rec.assert_called_once_with("vanbanden", 99)
        mock_delete.assert_called_once_with("vanbanden", 99)
        mock_clear_cache.assert_called_once_with()
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

    @patch("documents.tasks.sync_sql_document_vectors.delay")
    def test_vanbandi_noibanhanh_signal_triggers_celery_task(self, mock_delay):
        with self.captureOnCommitCallbacks(execute=True):
            instance = SimpleNamespace(vanbandi_id=55)
            handle_vanbandi_noibanhanh_change(None, instance)
        mock_delay.assert_called_once_with("vanbandi", 55)

    def test_check_and_update_expired_documents_triggers_vector_resync(self):
        from datetime import timedelta
        from django.utils import timezone
        from documents.models import HieuLuc, PhamVi, VanBanDen, VanBanDi

        past_dt = timezone.now() - timedelta(days=2)
        den = VanBanDen.objects.create(
            nam=2099,
            so_hieu="91/CV-EXPIRE-DEN",
            so_thu_tu=31001,
            trich_yeu="Văn bản đến sắp hết hạn",
            pham_vi=PhamVi.NOI_BO,
            hien_thi=True,
            hieu_luc=HieuLuc.CON_HIEU_LUC,
            ngay_het_hieu_luc=past_dt,
        )
        di = VanBanDi.objects.create(
            nam=2099,
            so_hieu="92/CV-EXPIRE-DI",
            so_thu_tu=31002,
            trich_yeu="Văn bản đi sắp hết hạn",
            pham_vi=PhamVi.NOI_BO,
            hien_thi=True,
            hieu_luc=HieuLuc.CON_HIEU_LUC_1_PHAN,
            ngay_het_hieu_luc=past_dt,
        )

        with patch("documents.signals._trigger_sync") as mock_trigger:
            updated = check_and_update_expired_documents()

        self.assertGreaterEqual(updated, 2)
        den.refresh_from_db()
        di.refresh_from_db()
        self.assertEqual(den.hieu_luc, HieuLuc.HET_HIEU_LUC)
        self.assertEqual(di.hieu_luc, HieuLuc.HET_HIEU_LUC)
        self.assertIn(call("vanbanden", den.pk), mock_trigger.call_args_list)
        self.assertIn(call("vanbandi", di.pk), mock_trigger.call_args_list)


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


class TestEnvironmentGuardTests(SimpleTestCase):
    def test_is_ai_configured_returns_false_under_manage_py_test(self):
        with (
            patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test-should-not-fire"}, clear=False),
            patch("backend.services.ai_settings_service.get_active_ai_settings", return_value={"openai_api_key": "sk-test-should-not-fire"}),
        ):
            self.assertFalse(is_ai_configured())

    def test_is_ai_configured_returns_false_under_inline_discover_runner(self):
        with (
            patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test-should-not-fire"}, clear=False),
            patch("sys.argv", ["-"]),
            patch("backend.services.ai_settings_service.get_active_ai_settings", return_value={"openai_api_key": "sk-test-should-not-fire"}),
        ):
            self.assertFalse(is_ai_configured())


class AiSyncScheduleTests(SimpleTestCase):
    def test_default_schedule_info_and_next_run_rollover(self):
        from datetime import datetime
        from zoneinfo import ZoneInfo

        from backend.services.ai_sync_schedule import get_ai_sync_schedule_info

        tz = ZoneInfo("Asia/Ho_Chi_Minh")
        with patch.dict("os.environ", {}, clear=False):
            before = get_ai_sync_schedule_info(now=datetime(2026, 11, 20, 1, 30, tzinfo=tz))
            after = get_ai_sync_schedule_info(now=datetime(2026, 11, 20, 2, 30, tzinfo=tz))

        self.assertTrue(before["enabled"])
        self.assertEqual(before["mode"], "event_and_scheduled")
        self.assertEqual(before["task"], "sync_all_ai_documents")
        self.assertEqual(before["time"], "02:00")
        self.assertEqual(before["cron"], "0 2 * * *")
        self.assertEqual(before["next_run_at"], "2026-11-20T02:00:00+07:00")
        self.assertEqual(after["next_run_at"], "2026-11-21T02:00:00+07:00")

    def test_custom_env_and_disabled_schedule(self):
        from backend.services.ai_sync_schedule import (
            AI_SYNC_BEAT_ENTRY,
            build_ai_beat_schedule,
            get_ai_sync_schedule_info,
        )

        with patch.dict(
            "os.environ",
            {
                "AI_SYNC_SCHEDULE_ENABLED": "true",
                "AI_SYNC_SCHEDULE_HOUR": "4",
                "AI_SYNC_SCHEDULE_MINUTE": "30",
            },
            clear=False,
        ):
            info = get_ai_sync_schedule_info()
            beat = build_ai_beat_schedule()

        self.assertEqual(info["time"], "04:30")
        self.assertEqual(info["cron"], "30 4 * * *")
        self.assertIn(AI_SYNC_BEAT_ENTRY, beat)
        self.assertEqual(beat[AI_SYNC_BEAT_ENTRY]["task"], "sync_all_ai_documents")
        self.assertEqual(beat[AI_SYNC_BEAT_ENTRY]["schedule"].hour, {4})
        self.assertEqual(beat[AI_SYNC_BEAT_ENTRY]["schedule"].minute, {30})

        with patch.dict("os.environ", {"AI_SYNC_SCHEDULE_ENABLED": "false"}, clear=False):
            disabled_info = get_ai_sync_schedule_info()
            self.assertFalse(disabled_info["enabled"])
            self.assertEqual(disabled_info["mode"], "event_only")
            self.assertIsNone(disabled_info["next_run_at"])
            self.assertEqual(build_ai_beat_schedule(), {})

    def test_celery_app_registers_periodic_ai_sync(self):
        from backend.config.celery import app as celery_app
        from backend.services.ai_sync_schedule import AI_SYNC_BEAT_ENTRY

        schedule = celery_app.conf.beat_schedule or {}
        self.assertIn(AI_SYNC_BEAT_ENTRY, schedule)
        self.assertEqual(schedule[AI_SYNC_BEAT_ENTRY]["task"], "sync_all_ai_documents")
