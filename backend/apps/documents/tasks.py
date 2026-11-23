import logging
from pathlib import Path
from django.db import OperationalError

try:
    from celery import shared_task
except ImportError:  # pragma: no cover
    def shared_task(*_args, **_kwargs):
        def decorator(func):
            func.delay = func
            return func
        return decorator

logger = logging.getLogger(__name__)


@shared_task(
    name="sync_sql_document_vectors",
    autoretry_for=(OperationalError,),
    retry_backoff=True,
    retry_backoff_max=60,
    retry_jitter=True,
    max_retries=3,
    ignore_result=True,
)
def sync_sql_document_vectors(source_type: str, document_id: int):
    """Celery task to index or remove vectors for a given SQL document in vector store."""
    from backend.services.faq_response_cache import clear_faq_cache
    from backend.services.rag_service import (
        delete_sql_document_vectors,
        index_sql_document,
        is_ai_configured,
    )
    from backend.services.sql_document_source import get_document_record_for_index

    try:
        record = get_document_record_for_index(source_type, document_id)
        if record is None:
            delete_sql_document_vectors(source_type, document_id)
            clear_faq_cache()
            logger.info("Deleted vector for %s:%s (not visible or deleted)", source_type, document_id)
            return False

        if not is_ai_configured():
            logger.info("AI chưa được cấu hình (thiếu OPENAI_API_KEY), bỏ qua lập chỉ mục vector cho %s:%s", source_type, document_id)
            return False

        key = index_sql_document(record)
        if key is not None:
            clear_faq_cache()
        logger.info("Successfully indexed vector for %s (key=%s)", f"{source_type}:{document_id}", key)
        return key is not None
    except OperationalError:
        raise
    except Exception as error:
        logger.warning("Could not sync vector for %s:%s: %s", source_type, document_id, error)
        return False


@shared_task(
    name="sync_registered_ai_documents",
    autoretry_for=(OperationalError,),
    retry_backoff=True,
    retry_backoff_max=60,
    retry_jitter=True,
    max_retries=3,
    ignore_result=True,
)
def sync_registered_ai_documents():
    """Celery task to synchronize registered AI knowledge-base documents outside the chat path."""
    from backend.services.rag_service import is_ai_configured, sync_documents_if_needed

    try:
        if not is_ai_configured():
            logger.info("AI chưa được cấu hình (thiếu OPENAI_API_KEY), bỏ qua đồng bộ tài liệu registry.")
            return False
        sync_documents_if_needed()
        return True
    except OperationalError:
        raise
    except Exception as error:
        logger.warning("Could not sync registered AI documents: %s", error)
        return False


@shared_task(
    name="index_uploaded_ai_document",
    autoretry_for=(OperationalError,),
    retry_backoff=True,
    retry_backoff_max=60,
    retry_jitter=True,
    max_retries=3,
    ignore_result=True,
)
def index_uploaded_ai_document(job_id: str, staged_path: str, filename: str, replace_existing: bool = True):
    """Celery task wrapping staged AI upload indexing for multi-worker deployments."""
    from backend.api.views import _run_index_job

    _run_index_job(job_id, Path(staged_path), filename, replace_existing)


@shared_task(
    name="sync_all_ai_documents",
    autoretry_for=(OperationalError,),
    retry_backoff=True,
    retry_backoff_max=60,
    retry_jitter=True,
    max_retries=3,
    ignore_result=True,
)
def sync_all_ai_documents(job_id: str | None = None):
    """Synchronize registered KB files (including orphan pruning) and eligible SQL documents."""
    from backend.api.views import _set_job
    from backend.services.faq_response_cache import clear_faq_cache
    from backend.services.rag_service import index_sql_document, is_ai_configured, sync_documents_if_needed
    from backend.services.sql_document_source import get_all_document_records_for_index

    if job_id:
        _set_job(job_id, status="processing", message="Đang đồng bộ kho tri thức & văn bản AI...")

    summary = {"kb_synced": False, "sql_total": 0, "sql_indexed": 0, "sql_skipped": 0, "sql_errors": 0}
    try:
        if is_ai_configured():
            sync_documents_if_needed()
            summary["kb_synced"] = True
            records = get_all_document_records_for_index()
            summary["sql_total"] = len(records)
            for rec in records:
                try:
                    key = index_sql_document(rec)
                    if key:
                        summary["sql_indexed"] += 1
                    else:
                        summary["sql_skipped"] += 1
                except Exception as exc:
                    summary["sql_errors"] += 1
                    logger.warning(
                        "Failed to sync SQL document %s:%s: %s",
                        rec.get("source_type"),
                        rec.get("source_id"),
                        exc,
                    )
            clear_faq_cache()
        if job_id:
            _set_job(
                job_id,
                status="done",
                message="Đồng bộ kho tri thức AI hoàn tất.",
                result=summary,
                error=None,
            )
    except Exception as exc:
        logger.exception("Full AI knowledge sync failed")
        if job_id:
            _set_job(
                job_id,
                status="error",
                message="Không thể hoàn tất đồng bộ AI lúc này.",
                error=type(exc).__name__,
            )
    return summary
