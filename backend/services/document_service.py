import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from backend.config import DOCS_DIR, DOC_REGISTRY_PATH


def stage_upload_file(file) -> tuple[Path, str, bool]:
    """Write an upload outside the visible document list until indexing succeeds."""
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    staging_dir = DOCS_DIR / ".staging"
    staging_dir.mkdir(parents=True, exist_ok=True)
    filename = Path(file.name).name
    final_path = DOCS_DIR / filename
    descriptor, temporary_name = tempfile.mkstemp(
        prefix="upload-", suffix=Path(filename).suffix, dir=staging_dir
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as buffer:
            for chunk in file.chunks():
                buffer.write(chunk)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise
    return temporary_path, filename, final_path.exists()


def commit_staged_upload(staged_path: Path, filename: str) -> Path:
    final_path = DOCS_DIR / Path(filename).name
    final_path.parent.mkdir(parents=True, exist_ok=True)
    staged_path.replace(final_path)
    return final_path


def discard_staged_upload(staged_path: Path) -> None:
    staged_path.unlink(missing_ok=True)


# ── Registry CRUD ──────────────────────────────────────────────


def load_registry() -> list[dict]:
    """Đọc doc_registry.json, trả về list entries."""
    if not DOC_REGISTRY_PATH.exists():
        return []

    try:
        data = json.loads(DOC_REGISTRY_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def save_registry(entries: list[dict]):
    """Ghi list entries vào doc_registry.json."""
    DOC_REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    DOC_REGISTRY_PATH.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def add_to_registry(filename: str, category: str, size: int):
    """Thêm 1 document entry vào registry."""
    entries = load_registry()

    # Xóa entry cũ nếu trùng filename (re-upload)
    entries = [e for e in entries if e.get("filename") != filename]

    entries.append({
        "filename": filename,
        "category": category,
        "size": size,
        "upload_time": datetime.now(timezone.utc).isoformat(),
    })

    save_registry(entries)


def update_category_in_registry(filename: str, category: str):
    """Cập nhật category cho một document trong registry."""
    entries = load_registry()
    
    for entry in entries:
        if entry.get("filename") == filename:
            entry["category"] = category
            break
    
    save_registry(entries)


def remove_from_registry(filename: str) -> bool:
    """Xóa 1 entry theo filename."""
    entries = load_registry()
    initial_len = len(entries)
    entries = [e for e in entries if e.get("filename") != filename]
    if len(entries) < initial_len:
        save_registry(entries)
        return True
    return False


def clear_registry():
    """Xóa toàn bộ registry."""
    if DOC_REGISTRY_PATH.exists():
        DOC_REGISTRY_PATH.unlink()


# ── Document Management ───────────────────────────────────────


def list_documents():
    """Trả về danh sách tài liệu kèm category từ registry."""
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    registry = load_registry()
    registry_map = {e["filename"]: e for e in registry}

    documents = []

    for item in DOCS_DIR.iterdir():
        if not item.is_file() or item.name == ".gitkeep":
            continue

        reg_entry = registry_map.get(item.name, {})

        documents.append({
            "filename": item.name,
            "path": str(item),
            "size": item.stat().st_size,
            "category": reg_entry.get("category", "Chưa phân loại"),
            "upload_time": reg_entry.get("upload_time"),
        })

    return documents


def list_categories():
    """Trả về danh sách các chủ đề hiện có và số tài liệu mỗi chủ đề."""
    documents = list_documents()
    category_counts = {}

    for doc in documents:
        cat = doc["category"]
        category_counts[cat] = category_counts.get(cat, 0) + 1

    return [
        {"name": name, "count": count}
        for name, count in sorted(category_counts.items())
    ]


def clear_documents():
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    for item in DOCS_DIR.iterdir():
        if item.is_dir() and item.name == ".staging":
            for staged_file in item.iterdir():
                if staged_file.is_file():
                    staged_file.unlink()
            item.rmdir()
        if item.is_file() and item.name != ".gitkeep":
            item.unlink()

    clear_registry()


def delete_document_file(filename: str) -> bool:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    safe_name = Path(filename).name
    file_path = DOCS_DIR / safe_name
    file_existed = file_path.exists() and file_path.is_file()

    if file_existed and safe_name != ".gitkeep":
        file_path.unlink()

    reg_existed = remove_from_registry(safe_name)

    return file_existed or reg_existed
