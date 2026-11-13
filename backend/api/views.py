import os
import json
import logging
import threading
import uuid
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote

from django.conf import settings
from django.core.cache import cache
from django.db import DatabaseError, connection
from django.http import FileResponse, JsonResponse, StreamingHttpResponse
from django.views.decorators.http import require_GET
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

import backend.config as config
from backend.services.ai_access import has_permission_codename, is_ai_admin, resolve_employee_id
from backend.services.document_service import (
    add_to_registry,
    clear_documents,
    commit_staged_upload,
    discard_staged_upload,
    delete_document_file,
    list_categories,
    list_documents,
    stage_upload_file,
    update_category_in_registry,
)
from backend.services.ai_logging import (
    end_trace,
    log_exception,
    log_summary,
    mark_error,
    set_fields,
    start_trace,
)
from backend.services.sql_document_source import SqlDocumentAccessError
from backend.services.ai_model_config import MODEL_CONFIG
from backend.services.ai_settings_service import get_active_ai_settings, save_ai_settings

_jobs = {}
_jobs_lock = threading.Lock()
_upload_lock = threading.Lock()
logger = logging.getLogger(__name__)
MAX_CHAT_QUESTION_LENGTH = 4000


def _json_body(request):
    try:
        return request.data
    except Exception:
        return None


def _error(message, status=400, code=None):
    payload = {"detail": message}
    if code:
        payload["code"] = code
    return JsonResponse(payload, status=status)


def _require_ai_access(request):
    if not has_permission_codename(request.user, "use_aiassistant"):
        return _error("Tài khoản chưa được cấp quyền sử dụng trợ lý AI.", 403)
    return None


def _require_ai_admin(request):
    if not is_ai_admin(request.user):
        return _error("Chỉ quản trị viên được phép thực hiện thao tác này.", 403)
    return None


def _job_cache_key(job_id):
    return f"ai:upload_job:{job_id}"


def _set_job(job_id, **values):
    with _jobs_lock:
        current = dict(_jobs.get(job_id) or {})
        current.update(values)
        current["updated_at"] = datetime.now(timezone.utc).isoformat()
        _jobs[job_id] = current
    try:
        cache.set(_job_cache_key(job_id), current, timeout=3600)
    except Exception:
        logger.debug("Upload job cache write unavailable for job_id=%s", job_id)


def _get_job(job_id):
    with _jobs_lock:
        if job_id in _jobs:
            return dict(_jobs[job_id])
    try:
        cached = cache.get(_job_cache_key(job_id))
        if cached:
            return dict(cached)
    except Exception:
        logger.debug("Upload job cache read unavailable for job_id=%s", job_id)
    return {}


def _run_index_job(job_id, staged_path, filename, replace_existing=True):
    try:
        from backend.services.rag_service import index_document

        _set_job(job_id, status="processing", message="Đang lập chỉ mục tài liệu...")
        with _upload_lock:
            existing_path = config.DOCS_DIR / filename
            if existing_path.is_file() and not replace_existing:
                discard_staged_upload(staged_path)
                _set_job(
                    job_id,
                    status="error",
                    message="Tài liệu trùng tên đã tồn tại. Vui lòng xác nhận ghi đè trước khi tải lên.",
                    error="duplicate_filename",
                )
                return
            result = index_document(staged_path, source_metadata={"file_name": filename})
            category = result.get("category", "Chưa phân loại")
            final_path = commit_staged_upload(staged_path, filename)
            add_to_registry(filename, category, final_path.stat().st_size)
        _set_job(job_id, status="done", message="Tải lên và lập chỉ mục thành công.", category=category, result=result, error=None)
    except Exception:
        logger.exception("AI document indexing failed for filename=%s", filename)
        discard_staged_upload(staged_path)
        _set_job(job_id, status="error", message="Không thể lập chỉ mục tài liệu. Tệp chưa được thêm vào kho.", error="indexing_failed")


def root(request):
    return JsonResponse({"message": "Quản lý Văn bản TLBM API đang hoạt động", "stack": ["Django", "React", "LlamaIndex", "PostgreSQL pgvector"]})


@require_GET
def readiness(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except DatabaseError:
        return JsonResponse({"status": "not_ready"}, status=503)
    return JsonResponse({"status": "ready", "release": settings.RELEASE_ID})


def ai_health(request):
    return JsonResponse({"status": "ok"})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def chat(request):
    payload = _json_body(request)
    if isinstance(payload, dict) and payload.get("stream") is True:
        return _stream_response(request, payload=payload)

    trace, token = start_trace(user_id=request.user.pk)
    status = 500
    try:
        response = _answer_chat(request, payload=payload)
        status = response.status_code
        return response
    finally:
        log_summary(trace, status)
        end_trace(token)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def chat_stream(request):
    return _stream_response(request)


def _stream_response(request, payload=None):
    if request.method != "POST":
        return _error("Phương thức không được hỗ trợ.", 405)
    denied = _require_ai_access(request)
    if denied:
        trace, token = start_trace(user_id=request.user.pk)
        mark_error("permission", "no_ai_permission")
        log_summary(trace, 403)
        end_trace(token)
        return denied

    if payload is None:
        payload = _json_body(request)
    if not isinstance(payload, dict):
        return _error("Dữ liệu gửi lên không hợp lệ.")
    question = payload.get("question")
    history = payload.get("history", [])
    category = payload.get("category")
    filename = payload.get("filename")
    filenames = payload.get("filenames")
    if isinstance(filename, list) and not filenames:
        filenames = filename
        filename = None
    if filename and not isinstance(filename, str):
        filename = None
    elif filename:
        filename = filename.strip()
    clean_filenames = (
        [f.strip() for f in filenames if isinstance(f, str) and f.strip()][:10]
        if isinstance(filenames, list)
        else None
    )
    if not isinstance(question, str) or not question.strip():
        return _error("Câu hỏi không được để trống.")
    if len(question) > MAX_CHAT_QUESTION_LENGTH:
        return _error("Câu hỏi không được vượt quá 4000 ký tự.")
    if not isinstance(history, list):
        return _error("Lịch sử hội thoại không hợp lệ.")
    safe_history = [
        item for item in history[-8:]
        if isinstance(item, dict) and item.get("role") in {"user", "assistant"} and isinstance(item.get("content"), str)
    ]

    employee_id = resolve_employee_id(request)
    language = payload.get("language")
    if not language or not isinstance(language, str):
        accept_lang = request.headers.get("Accept-Language", "")
        language = "en" if "en" in accept_lang.lower() else "vi"
    else:
        language = "en" if language.lower().startswith("en") else "vi"

    def event_stream_generator():
        trace, token = start_trace(user_id=request.user.pk)
        set_fields(
            employee_resolved=employee_id is not None,
            question_chars=len(question),
            history_items=len(safe_history),
            has_filename=bool(filename or clean_filenames),
            has_category=bool(category),
            stream=True,
        )
        status = 200
        try:
            from backend.services.rag_service import ask_document_stream
            for event_chunk in ask_document_stream(
                question.strip(),
                history=safe_history,
                category=category if isinstance(category, str) else None,
                user=request.user,
                employee_id=employee_id,
                filename=filename,
                language=language,
                filenames=clean_filenames,
            ):
                yield event_chunk
        except GeneratorExit:
            status = 499
            set_fields(client_aborted=True)
            raise
        except SqlDocumentAccessError as error:
            status = 503
            mark_error("ask_document_stream", error.ai_reason)
            log_exception()
            yield f"event: error\ndata: {json.dumps({'error': 'Không thể truy cập nguồn dữ liệu AI lúc này.'}, ensure_ascii=False)}\n\n"
        except Exception as error:
            status = 502
            mark_error("ask_document_stream", type(error).__name__)
            log_exception()
            yield f"event: error\ndata: {json.dumps({'error': 'Không thể xử lý yêu cầu lúc này. Vui lòng thử lại sau.'}, ensure_ascii=False)}\n\n"
        finally:
            log_summary(trace, status)
            end_trace(token)

    response = StreamingHttpResponse(
        event_stream_generator(),
        content_type="text/event-stream; charset=utf-8",
    )
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response


def _answer_chat(request, payload=None):
    if request.method != "POST":
        return _error("Phương thức không được hỗ trợ.", 405)
    denied = _require_ai_access(request)
    if denied:
        mark_error("permission", "no_ai_permission")
        return denied
    if payload is None:
        payload = _json_body(request)
    if not isinstance(payload, dict):
        return _error("Dữ liệu gửi lên không hợp lệ.")
    question = payload.get("question")
    history = payload.get("history", [])
    category = payload.get("category")
    filename = payload.get("filename")
    filenames = payload.get("filenames")
    if isinstance(filename, list) and not filenames:
        filenames = filename
        filename = None
    if filename and not isinstance(filename, str):
        filename = None
    elif filename:
        filename = filename.strip()
    clean_filenames = (
        [f.strip() for f in filenames if isinstance(f, str) and f.strip()][:10]
        if isinstance(filenames, list)
        else None
    )
    if not isinstance(question, str) or not question.strip():
        return _error("Câu hỏi không được để trống.")
    if len(question) > MAX_CHAT_QUESTION_LENGTH:
        return _error("Câu hỏi không được vượt quá 4000 ký tự.")
    if not isinstance(history, list):
        return _error("Lịch sử hội thoại không hợp lệ.")
    safe_history = [item for item in history[-8:] if isinstance(item, dict) and item.get("role") in {"user", "assistant"} and isinstance(item.get("content"), str)]
    try:
        from backend.services.rag_service import ask_document

        # Employee identity is supplied by host auth or resolved through trusted username mapping
        employee_id = resolve_employee_id(request)
        set_fields(
            employee_resolved=employee_id is not None,
            question_chars=len(question),
            history_items=len(safe_history),
            has_filename=bool(filename or clean_filenames),
            has_category=bool(category),
        )
        language = payload.get("language")
        if not language or not isinstance(language, str):
            accept_lang = request.headers.get("Accept-Language", "")
            language = "en" if "en" in accept_lang.lower() else "vi"
        else:
            language = "en" if language.lower().startswith("en") else "vi"

        result = ask_document(
            question.strip(), history=safe_history,
            category=category if isinstance(category, str) else None,
            user=request.user,
            employee_id=employee_id,
            filename=filename,
            language=language,
            filenames=clean_filenames,
        )
        return JsonResponse({
            "question": question.strip(),
            "category": category or None,
            "filename": filename or (clean_filenames[0] if clean_filenames and len(clean_filenames) == 1 else None),
            "filenames": clean_filenames or ([filename] if filename else None),
            "language": language,
            **result,
        })
    except SqlDocumentAccessError as error:
        mark_error("ask_document", error.ai_reason)
        log_exception()
        return _error("Không thể truy cập nguồn dữ liệu AI lúc này.", 503)
    except Exception as error:
        mark_error("ask_document", type(error).__name__)
        log_exception()
        return _error("Không thể xử lý yêu cầu lúc này. Vui lòng thử lại sau.", 502)


def _validate_upload(upload):
    if not upload or not getattr(upload, "name", ""):
        return "File không hợp lệ."
    if not upload.name.lower().endswith(config.ALLOWED_EXTENSIONS):
        return f"Định dạng không được hỗ trợ. Cho phép: {', '.join(config.ALLOWED_EXTENSIONS)}"
    if upload.size > 50 * 1024 * 1024:
        return "Dung lượng tệp không được vượt quá 50 MB."
    return ""


def _validate_upload_replacement(request, upload):
    filename = Path(upload.name).name
    existing_path = config.DOCS_DIR / filename
    replace_existing = str(request.data.get("replace_existing", "")).lower() == "true"
    if existing_path.is_file() and not replace_existing:
        return _error(
            "A document with this filename already exists. Confirm replacement before uploading.",
            409,
            "duplicate_filename",
        )
    return None


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def upload_async(request):
    denied = _require_ai_admin(request)
    if denied:
        return denied
    upload = request.FILES.get("file")
    error = _validate_upload(upload)
    if error:
        return _error(error)
    replacement_error = _validate_upload_replacement(request, upload)
    if replacement_error:
        return replacement_error
    replace_existing = str(request.data.get("replace_existing", "")).lower() == "true"
    staged_path, filename, is_reupload = stage_upload_file(upload)
    job_id = str(uuid.uuid4())
    _set_job(job_id, status="queued", message="Đang chờ xử lý...", filename=filename, category=None, result=None, error=None, started_at=datetime.now(timezone.utc).isoformat())
    threading.Thread(
        target=_run_index_job,
        args=(job_id, staged_path, filename, replace_existing),
        daemon=True,
    ).start()
    return JsonResponse({"job_id": job_id, "filename": filename, "reupload": is_reupload, "message": "Đã nhận tệp, đang lập chỉ mục...", "poll_url": f"/api/ai/upload/progress/{job_id}"}, status=202)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def upload_progress(request, job_id):
    denied = _require_ai_admin(request)
    if denied:
        return denied
    job = _get_job(job_id)
    return JsonResponse(job or {"detail": "Không tìm thấy tiến trình tải lên."}, status=200 if job else 404)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def upload_sync(request):
    denied = _require_ai_admin(request)
    if denied:
        return denied
    upload = request.FILES.get("file")
    error = _validate_upload(upload)
    if error:
        return _error(error)
    replacement_error = _validate_upload_replacement(request, upload)
    if replacement_error:
        return replacement_error
    replace_existing = str(request.data.get("replace_existing", "")).lower() == "true"
    staged_path, filename, is_reupload = stage_upload_file(upload)
    try:
        from backend.services.rag_service import index_document

        with _upload_lock:
            existing_path = config.DOCS_DIR / filename
            if existing_path.is_file() and not replace_existing:
                discard_staged_upload(staged_path)
                return _error(
                    "A document with this filename already exists. Confirm replacement before uploading.",
                    409,
                    "duplicate_filename",
                )
            result = index_document(staged_path, source_metadata={"file_name": filename})
            category = result.get("category", "Chưa phân loại")
            final_path = commit_staged_upload(staged_path, filename)
            add_to_registry(filename, category, final_path.stat().st_size)
        return JsonResponse({"message": "Tải lên và lập chỉ mục thành công.", "filename": filename, "category": category, "reupload": is_reupload, "indexed": result})
    except Exception:
        logger.exception("Synchronous AI document indexing failed for filename=%s", filename)
        discard_staged_upload(staged_path)
        return _error("Không thể lập chỉ mục tài liệu. Tệp chưa được thêm vào kho.", 500)


@api_view(["GET", "DELETE"])
@permission_classes([IsAuthenticated])
def documents(request, filename=None):
    if request.method == "GET":
        denied = _require_ai_access(request)
        if denied:
            return denied
        public_documents = [
            {
                "filename": item["filename"],
                "size": item.get("size"),
                "category": item.get("category"),
                "upload_time": item.get("upload_time"),
            }
            for item in list_documents()
        ]
        return JsonResponse({"documents": public_documents})
    denied = _require_ai_admin(request)
    if denied:
        return denied
    if request.method == "DELETE":
        payload = _json_body(request)
        if not isinstance(payload, dict) or payload.get("confirmation") != "DELETE":
            return _error("Cần xác nhận bằng cách nhập DELETE.", 400)
        from backend.services.rag_service import clear_vector_database

        with _upload_lock:
            clear_vector_database()
            clear_documents()
        return JsonResponse({"message": "Đã xóa tài liệu và dữ liệu chỉ mục."})
    return _error("Phương thức không được hỗ trợ.", 405)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def categories(request):
    denied = _require_ai_access(request)
    if denied:
        return denied
    return JsonResponse({"categories": list_categories()})


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def document_detail(request, filename):
    denied = _require_ai_admin(request)
    if denied:
        return denied
    safe_name = Path(unquote(filename)).name
    if safe_name != unquote(filename):
        return _error("Tên tệp không hợp lệ.", 400)
    if request.method != "DELETE":
        return _error("Phương thức không được hỗ trợ.", 405)
    try:
        from backend.services.rag_service import delete_document_vectors

        delete_document_vectors(safe_name)
    except Exception:
        logger.exception("AI document vector deletion failed for filename=%s", safe_name)
        return _error("Không thể xóa tài liệu khỏi kho lúc này.", 503)
    existed = delete_document_file(safe_name)
    return JsonResponse({"message": f"Đã xóa tài liệu '{safe_name}'." if existed else f"Không tìm thấy tài liệu '{safe_name}'.", "deleted": existed})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def document_file(request, filename):
    denied = _require_ai_access(request)
    if denied:
        return denied
    safe_name = Path(unquote(filename)).name
    if safe_name != unquote(filename):
        return _error("Tên tệp không hợp lệ.", 400)
    file_path = config.DOCS_DIR / safe_name
    if not file_path.is_file():
        return _error(f"Không tìm thấy tài liệu '{safe_name}'.", 404)
    media_types = {
        ".pdf": "application/pdf",
        ".txt": "text/plain; charset=utf-8",
        ".md": "text/markdown; charset=utf-8",
        ".markdown": "text/markdown; charset=utf-8",
        ".csv": "text/csv; charset=utf-8",
        ".json": "application/json; charset=utf-8",
        ".xml": "application/xml; charset=utf-8",
        ".html": "text/html; charset=utf-8",
        ".htm": "text/html; charset=utf-8",
        ".doc": "application/msword",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
        ".tiff": "image/tiff",
        ".tif": "image/tiff",
        ".gif": "image/gif",
    }
    response = FileResponse(file_path.open("rb"), content_type=media_types.get(file_path.suffix.lower(), "application/octet-stream"), filename=safe_name)
    response["Content-Disposition"] = f'inline; filename="{safe_name}"'
    return response


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def preview_document(request, filename):
    denied = _require_ai_access(request)
    if denied:
        return denied
    safe_name = Path(unquote(filename)).name
    file_path = config.DOCS_DIR / safe_name
    if safe_name != unquote(filename) or not file_path.is_file():
        return _error("Không tìm thấy tài liệu.", 404)
    suffix = file_path.suffix.lower()
    image_extensions = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif", ".gif"}
    text_extract_extensions = {".doc", ".csv", ".pptx", ".md", ".markdown", ".html", ".htm", ".json", ".xml"}
    if suffix == ".pdf":
        return JsonResponse({"filename": safe_name, "file_type": "PDF", "render_mode": "pdf", "file_url": f"/api/ai/documents/{safe_name}/file"})
    if suffix in image_extensions:
        return JsonResponse({"filename": safe_name, "file_type": suffix[1:].upper(), "render_mode": "image", "file_url": f"/api/ai/documents/{safe_name}/file"})
    if suffix == ".docx":
        try:
            from backend.services.rag_service import read_docx

            full_text = read_docx(file_path)
            lines = full_text.splitlines()
            pages = [{"page": index // 60 + 1, "text": "\n".join(lines[index:index + 60])} for index in range(0, max(1, len(lines)), 60)]
        except Exception as exc:
            return _error(f"Không đọc được DOCX: {exc}", 500)
    elif suffix == ".txt":
        try:
            full_text = file_path.read_text(encoding="utf-8", errors="replace")
            lines = full_text.splitlines()
            pages = (
                [{"page": index // 60 + 1, "text": "\n".join(lines[index:index + 60])} for index in range(0, len(lines), 60)]
                if len(lines) > 60
                else [{"page": 1, "text": full_text}]
            )
        except OSError as exc:
            return _error(f"Không đọc được TXT: {exc}", 500)
    elif suffix in text_extract_extensions:
        try:
            from backend.services.rag_service import read_document_pages

            extracted = read_document_pages(file_path) or []
            pages = [
                {"page": page.get("page") or idx + 1, "text": page.get("text", "")}
                for idx, page in enumerate(extracted)
                if page.get("text", "").strip()
            ]
            if not pages:
                pages = [{"page": 1, "text": ""}]
            full_text = "\n\n".join(page["text"] for page in pages if page["text"])
        except Exception as exc:
            return _error(f"Không đọc được {suffix[1:].upper()}: {exc}", 500)
    else:
        return _error(f"Không hỗ trợ xem trước định dạng '{suffix}'.", 400)
    return JsonResponse({"filename": safe_name, "file_type": suffix[1:].upper(), "render_mode": "text", "total_pages": len(pages), "pages": pages, "full_text": full_text})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def reclassify(request, filename):
    denied = _require_ai_admin(request)
    if denied:
        return denied
    safe_name = Path(unquote(filename)).name
    doc = next((item for item in list_documents() if item["filename"] == safe_name), None)
    if not doc:
        return _error("Không tìm thấy tài liệu.", 404)
    try:
        from backend.services.rag_service import (
            classify_document,
            read_document_pages,
            setup_llamaindex,
            update_document_category_vectors,
        )

        setup_llamaindex()
        pages = read_document_pages(Path(doc["path"]))
        text = "\n\n".join(page["text"] for page in pages if page["text"].strip())
        if len(text.strip()) < 20:
            return _error("Không đọc được nội dung tài liệu.")
        category = classify_document(text)
        update_category_in_registry(safe_name, category)
        updated = update_document_category_vectors(safe_name, category)
        return JsonResponse({"message": "Đã phân loại lại tài liệu.", "filename": safe_name, "category": category, "updated_vectors": updated})
    except Exception as exc:
        return _error(f"Lỗi phân loại: {exc}", 500)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def ai_settings(request):
    if request.method == "GET":
        denied = _require_ai_access(request)
        if denied:
            return denied
        active = get_active_ai_settings()
        provider = "openai"
        provider_cfg = MODEL_CONFIG[provider]
        llm = active.get("llm_model") or provider_cfg["default_llm"]
        embed = active.get("embed_model") or provider_cfg["embed_model"]
        vision = active.get("vision_model") or llm

        model_options = {
            name: {"llm_models": list(values["llm_models"]), "embed_model": values["embed_model"]}
            for name, values in MODEL_CONFIG.items()
        }
        info = {
            "status": "ok",
            "provider": provider,
            "llm_model": llm,
            "embed_model": embed,
            "vision_model": vision,
        }
        if not is_ai_admin(request.user):
            return JsonResponse(info)

        openai_k = (active.get("openai_api_key") or getattr(config, "OPENAI_API_KEY", "") or os.getenv("OPENAI_API_KEY", "")).strip()
        masked_key = f"{openai_k[:6]}...{openai_k[-4:]}" if len(openai_k) > 10 else ("********" if openai_k else "")
        return JsonResponse({
            **info,
            "has_api_key": bool(openai_k),
            "api_key_masked": masked_key,
            "api_keys": {"openai": bool(openai_k)},
            "api_key_masked_by_provider": {"openai": masked_key},
            "model_options": model_options,
        })

    denied = _require_ai_admin(request)
    if denied:
        return denied
    if request.method != "POST":
        return _error("Phương thức không được hỗ trợ.", 405)
    payload = _json_body(request)
    if not isinstance(payload, dict):
        return _error("Cấu hình không hợp lệ.")
    provider = str(payload.get("provider", "")).lower().strip()
    if provider not in MODEL_CONFIG:
        return _error("Provider được hỗ trợ là 'openai'.", code="provider_not_supported")

    active = get_active_ai_settings()
    existing_key = active.get("openai_api_key") or getattr(config, "OPENAI_API_KEY", "") or os.getenv("OPENAI_API_KEY", "")
    key = str(payload.get("api_key") or existing_key).strip()
    if not key:
        return _error(f"Vui lòng cung cấp API key {provider.upper()}.", code="api_key_required")
    if "\n" in key or "\r" in key:
        return _error("API key không hợp lệ.", code="invalid_api_key")

    provider_config = MODEL_CONFIG[provider]
    llm = str(payload.get("llm_model") or provider_config["default_llm"]).strip()
    if llm not in provider_config["llm_models"]:
        return _error("Mô hình LLM không nằm trong danh sách được hỗ trợ.", code="model_not_supported")
    embed = provider_config["embed_model"]

    # Collection is isolated per provider (smart_documents vs smart_documents_openai),
    # preventing dimension mismatch errors when switching providers.

    check = urllib.request.Request("https://api.openai.com/v1/models", headers={"Authorization": f"Bearer {key}"})
    try:
        with urllib.request.urlopen(check, timeout=10) as response:
            catalog = json.loads(response.read().decode("utf-8"))
        available_models = {item.get("id") for item in catalog.get("data", [])}
        embedding_available = embed in available_models
        if llm not in available_models:
            return _error("API key không có quyền sử dụng mô hình đã chọn.", 400, "model_access_denied")
        if not embedding_available:
            return _error("API key không có quyền sử dụng mô hình embedding mặc định của provider.", 400, "embedding_access_denied")
    except urllib.error.HTTPError as exc:
        logger.warning("AI provider credentials rejected provider=%s status=%s", provider, exc.code)
        return _error("Không thể xác thực API key với nhà cung cấp.", 400, "invalid_api_key")
    except (urllib.error.URLError, TimeoutError, ValueError, KeyError):
        logger.exception("AI provider model catalog check failed provider=%s", provider)
        return _error("Không thể kết nối nhà cung cấp để xác thực cấu hình.", 503, "provider_unavailable")

    vision = llm
    updates = {
        "provider": provider,
        "MODEL_PROVIDER": provider,
        "openai_api_key": key,
        "OPENAI_API_KEY": key,
        "llm_model": llm,
        "LLM_MODEL": llm,
        "embed_model": embed,
        "EMBED_MODEL": embed,
        "vision_model": vision,
        "VISION_MODEL": vision,
    }
    save_ai_settings(updates)

    from backend.services import rag_service

    for name, value in updates.items():
        setattr(rag_service, name, value)
    rag_service.setup_llamaindex()

    if hasattr(rag_service, "sync_documents_if_needed"):
        try:
            rag_service.sync_documents_if_needed()
        except Exception:
            logger.exception("Failed to auto-sync documents for provider %s", provider)

    return JsonResponse({
        "success": True,
        "message": f"Đã cập nhật cấu hình {provider.upper()}.",
        "provider": provider,
        "llm_model": llm,
        "embed_model": embed,
        "api_key_masked": f"{key[:6]}...{key[-4:]}" if len(key) > 10 else "********",
    })
