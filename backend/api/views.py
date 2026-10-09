import os
import threading
import uuid
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote

from django.http import FileResponse, JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

import backend.config as config
from backend.services.ai_access import has_permission_codename, is_ai_admin, resolve_employee_id
from backend.services.document_service import (
    add_to_registry,
    clear_documents,
    delete_document_file,
    list_categories,
    list_documents,
    save_upload_file,
    update_category_in_registry,
)
from backend.services.sql_document_source import SqlDocumentAccessError
_jobs = {}
_jobs_lock = threading.Lock()


def _json_body(request):
    try:
        return request.data
    except Exception:
        return None


def _error(message, status=400):
    return JsonResponse({"detail": message}, status=status)


def _require_ai_access(request):
    if not has_permission_codename(request.user, "use_aiassistant"):
        return _error("Tài khoản chưa được cấp quyền sử dụng trợ lý AI.", 403)
    return None


def _require_ai_admin(request):
    if not is_ai_admin(request.user):
        return _error("Chỉ quản trị viên được phép thực hiện thao tác này.", 403)
    return None


def _set_job(job_id, **values):
    with _jobs_lock:
        _jobs.setdefault(job_id, {}).update(values)
        _jobs[job_id]["updated_at"] = datetime.now(timezone.utc).isoformat()


def _run_index_job(job_id, saved_path, filename):
    try:
        from backend.services.rag_service import index_document

        _set_job(job_id, status="processing", message="Đang đọc và phân tích tài liệu...")
        result = index_document(saved_path)
        category = result.get("category", "Chưa phân loại")
        _set_job(job_id, status="processing", message="Đang lưu thông tin tài liệu...")
        add_to_registry(filename, category, saved_path.stat().st_size)
        _set_job(job_id, status="done", message="Tải lên và lập chỉ mục thành công.", category=category, result=result, error=None)
    except Exception as exc:
        _set_job(job_id, status="error", message=f"Lỗi xử lý tài liệu: {exc}", error=str(exc))


def root(request):
    return JsonResponse({"message": "Quản lý Văn bản TLBM API đang hoạt động", "stack": ["Django", "React", "LlamaIndex", "ChromaDB"]})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def ai_health(request):
    has_key = bool(config.GEMINI_API_KEY) if config.MODEL_PROVIDER == "gemini" else bool(os.getenv("OPENAI_API_KEY"))
    return JsonResponse({"status": "ok", "provider": config.MODEL_PROVIDER, "llm_model": config.LLM_MODEL, "llm_available": has_key, "embed_model": config.EMBED_MODEL, "embed_available": has_key, "available_models": [config.LLM_MODEL, config.EMBED_MODEL]})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def chat(request):
    if request.method != "POST":
        return _error("Phương thức không được hỗ trợ.", 405)
    payload = _json_body(request)
    if not isinstance(payload, dict):
        return _error("Dữ liệu gửi lên không hợp lệ.")
    question = payload.get("question")
    history = payload.get("history", [])
    category = payload.get("category")
    if not isinstance(question, str) or not question.strip():
        return _error("Câu hỏi không được để trống.")
    if len(question) > 4000:
        return _error("Câu hỏi không được vượt quá 4000 ký tự.")
    if not isinstance(history, list):
        return _error("Lịch sử hội thoại không hợp lệ.")
    denied = _require_ai_access(request)
    if denied:
        return denied
    safe_history = [item for item in history[-8:] if isinstance(item, dict) and item.get("role") in {"user", "assistant"} and isinstance(item.get("content"), str)]
    try:
        from backend.services.rag_service import ask_document

        # Employee identity is supplied by host auth or resolved through trusted username mapping
        employee_id = resolve_employee_id(request)
        result = ask_document(
            question.strip(), history=safe_history,
            category=category if isinstance(category, str) else None,
            user=request.user,
            employee_id=employee_id,
        )
        return JsonResponse({"question": question.strip(), "category": category or None, **result})
    except SqlDocumentAccessError as exc:
        status = 401 if "danh tính" in str(exc).lower() or "đăng nhập" in str(exc).lower() else 403
        return _error(str(exc), status)
    except Exception as exc:
        return _error(f"Không thể xử lý câu hỏi: {exc}", 502)


def _validate_upload(upload):
    if not upload or not getattr(upload, "name", ""):
        return "File không hợp lệ."
    if not upload.name.lower().endswith(config.ALLOWED_EXTENSIONS):
        return f"Định dạng không được hỗ trợ. Cho phép: {', '.join(config.ALLOWED_EXTENSIONS)}"
    if upload.size > 50 * 1024 * 1024:
        return "Dung lượng tệp không được vượt quá 50 MB."
    return ""


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def upload_async(request):
    denied = _require_ai_admin(request)
    if denied:
        return denied
    if request.method != "POST":
        return _error("Phương thức không được hỗ trợ.", 405)
    upload = request.FILES.get("file")
    error = _validate_upload(upload)
    if error:
        return _error(error)
    saved_path, _ = save_upload_file(upload)
    job_id = str(uuid.uuid4())
    _set_job(job_id, status="queued", message="Đang chờ xử lý...", filename=upload.name, category=None, result=None, error=None, started_at=datetime.now(timezone.utc).isoformat())
    threading.Thread(target=_run_index_job, args=(job_id, saved_path, upload.name), daemon=True).start()
    return JsonResponse({"job_id": job_id, "filename": upload.name, "reupload": False, "message": "Đã nhận tệp, đang lập chỉ mục...", "poll_url": f"/upload/progress/{job_id}"}, status=202)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def upload_progress(request, job_id):
    denied = _require_ai_admin(request)
    if denied:
        return denied
    with _jobs_lock:
        job = dict(_jobs.get(job_id, {}))
    return JsonResponse(job or {"detail": f"Không tìm thấy job '{job_id}'"}, status=200 if job else 404)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def upload_sync(request):
    denied = _require_ai_admin(request)
    if denied:
        return denied
    if request.method != "POST":
        return _error("Phương thức không được hỗ trợ.", 405)
    upload = request.FILES.get("file")
    error = _validate_upload(upload)
    if error:
        return _error(error)
    saved_path, is_reupload = save_upload_file(upload)
    try:
        from backend.services.rag_service import index_document

        result = index_document(saved_path)
        category = result.get("category", "Chưa phân loại")
        add_to_registry(upload.name, category, saved_path.stat().st_size)
        return JsonResponse({"message": "Tải lên và lập chỉ mục thành công.", "filename": upload.name, "saved_path": str(saved_path), "category": category, "reupload": is_reupload, "indexed": result})
    except Exception as exc:
        return _error(f"Lỗi xử lý tài liệu: {exc}", 500)


@api_view(["GET", "DELETE"])
@permission_classes([IsAuthenticated])
def documents(request, filename=None):
    denied = _require_ai_admin(request)
    if denied:
        return denied
    if request.method == "GET":
        return JsonResponse({"documents": list_documents()})
    if request.method == "DELETE":
        from backend.services.rag_service import clear_vector_database

        clear_documents()
        clear_vector_database()
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
    existed = delete_document_file(safe_name)
    if existed:
        try:
            from backend.services.rag_service import delete_document_vectors

            delete_document_vectors(safe_name)
        except Exception as exc:
            print(f"Không xóa được vector cho {safe_name}: {exc}")
    return JsonResponse({"message": f"Đã xóa tài liệu '{safe_name}'." if existed else f"Không tìm thấy tài liệu '{safe_name}'.", "deleted": existed})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def document_file(request, filename):
    denied = _require_ai_admin(request)
    if denied:
        return denied
    safe_name = Path(unquote(filename)).name
    if safe_name != unquote(filename):
        return _error("Tên tệp không hợp lệ.", 400)
    file_path = config.DOCS_DIR / safe_name
    if not file_path.is_file():
        return _error(f"Không tìm thấy tài liệu '{safe_name}'.", 404)
    media_types = {".pdf": "application/pdf", ".txt": "text/plain; charset=utf-8", ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
    response = FileResponse(file_path.open("rb"), content_type=media_types.get(file_path.suffix.lower(), "application/octet-stream"), filename=safe_name)
    response["Content-Disposition"] = f'inline; filename="{safe_name}"'
    return response


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def preview_document(request, filename):
    denied = _require_ai_admin(request)
    if denied:
        return denied
    safe_name = Path(unquote(filename)).name
    file_path = config.DOCS_DIR / safe_name
    if safe_name != unquote(filename) or not file_path.is_file():
        return _error("Không tìm thấy tài liệu.", 404)
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        return JsonResponse({"filename": safe_name, "file_type": "PDF", "render_mode": "pdf", "file_url": f"/documents/{safe_name}/file"})
    if suffix == ".docx":
        try:
            from docx import Document
            lines = [paragraph.text for paragraph in Document(str(file_path)).paragraphs]
            full_text = "\n".join(lines)
            pages = [{"page": index // 60 + 1, "text": "\n".join(lines[index:index + 60])} for index in range(0, len(lines), 60)]
        except Exception as exc:
            return _error(f"Không đọc được DOCX: {exc}", 500)
    elif suffix == ".txt":
        try:
            full_text = file_path.read_text(encoding="utf-8", errors="replace")
            pages = [{"page": 1, "text": full_text}]
        except OSError as exc:
            return _error(f"Không đọc được TXT: {exc}", 500)
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
    denied = _require_ai_admin(request)
    if denied:
        return denied
    if request.method == "GET":
        key = config.GEMINI_API_KEY if config.MODEL_PROVIDER == "gemini" else os.getenv("OPENAI_API_KEY", "")
        masked = f"{key[:6]}...{key[-4:]}" if len(key) > 10 else ("********" if key else "")
        return JsonResponse({"status": "ok", "provider": config.MODEL_PROVIDER, "has_api_key": bool(key), "api_key_masked": masked, "llm_model": config.LLM_MODEL, "embed_model": config.EMBED_MODEL, "vision_model": config.VISION_MODEL})
    if request.method != "POST":
        return _error("Phương thức không được hỗ trợ.", 405)
    payload = _json_body(request)
    if not isinstance(payload, dict):
        return _error("Cấu hình không hợp lệ.")
    provider = str(payload.get("provider", "")).lower().strip()
    if provider not in {"gemini", "openai"}:
        return _error("Provider phải là 'gemini' hoặc 'openai'.")
    key = str(payload.get("api_key") or (config.GEMINI_API_KEY if provider == "gemini" else os.getenv("OPENAI_API_KEY", ""))).strip()
    if not key:
        return _error(f"Vui lòng cung cấp API key {provider.upper()}.")
    if provider == "gemini":
        check = urllib.request.Request(
            f"https://generativelanguage.googleapis.com/v1beta/models?key={key}",
            headers={"x-goog-api-key": key},
        )
        defaults = ("gemini-3.8-flash", "models/gemini-embedding-001")
    else:
        check = urllib.request.Request("https://api.openai.com/v1/models", headers={"Authorization": f"Bearer {key}"})
        defaults = ("gpt-4o-mini", "text-embedding-3-small")
    try:
        with urllib.request.urlopen(check, timeout=10) as response:
            valid = response.status == 200
        message = "API key không hợp lệ."
    except urllib.error.HTTPError as exc:
        valid, message = False, f"API key không hợp lệ (HTTP {exc.code})."
    except (urllib.error.URLError, TimeoutError) as exc:
        valid, message = False, f"Không thể xác thực API key: {exc}"
    if not valid:
        return _error(message)
    llm = str(payload.get("llm_model") or defaults[0]).strip()
    embed = str(payload.get("embed_model") or defaults[1]).strip()
    vision = str(payload.get("vision_model") or llm).strip()
    updates = {"MODEL_PROVIDER": provider, f"{'GEMINI' if provider == 'gemini' else 'OPENAI'}_API_KEY": key, "LLM_MODEL": llm, "EMBED_MODEL": embed, "VISION_MODEL": vision}
    for name, value in updates.items():
        os.environ[name] = value
        setattr(config, name, value)
    target_env_paths = [config.BASE_DIR / "backend" / ".env"]
    root_env = config.BASE_DIR / ".env"
    if root_env.exists():
        target_env_paths.append(root_env)
    for env_path in target_env_paths:
        lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
        seen = set()
        output = []
        for line in lines:
            name = line.split("=", 1)[0].strip() if "=" in line else ""
            if name in updates:
                output.append(f"{name}={updates[name]}")
                seen.add(name)
            else:
                output.append(line)
        output.extend(f"{name}={value}" for name, value in updates.items() if name not in seen)
        env_path.write_text("\n".join(output) + "\n", encoding="utf-8")
    from backend.services.rag_service import setup_llamaindex

    setup_llamaindex()
    return JsonResponse({"success": True, "message": f"Đã cập nhật cấu hình {provider.upper()}.", "provider": provider, "llm_model": llm, "embed_model": embed, "api_key_masked": f"{key[:6]}...{key[-4:]}" if len(key) > 10 else "********"})
