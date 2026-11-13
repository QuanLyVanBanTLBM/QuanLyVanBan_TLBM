import logging
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
            logger.info("Deleted vector for %s:%s (not visible or deleted)", source_type, document_id)
            return False

        if not is_ai_configured():
            logger.info("AI chưa được cấu hình (thiếu OPENAI_API_KEY), bỏ qua lập chỉ mục vector cho %s:%s", source_type, document_id)
            return False

        key = index_sql_document(record)
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
