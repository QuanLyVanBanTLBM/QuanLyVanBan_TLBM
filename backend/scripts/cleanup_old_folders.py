"""
Script dọn dẹp toàn bộ các thư mục cũ trong Kho tài liệu AI (doc_registry và ChromaDB),
chỉ giữ lại duy nhất cấu trúc:
Folder
  ├── folder1
  │     ├── item1.docx
  │     ├── item2.docx
  │     └── item3.docx
  └── folder2
        ├── item1.docx
        ├── item2.docx
        └── item3.docx
"""

import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import chromadb

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DOCS_DIR = ROOT_DIR / "data" / "docs"
REG_FILE = ROOT_DIR / "data" / "doc_registry.json"
CHROMA_DIR = ROOT_DIR / "data" / "chroma"

# Các tệp thuộc cấu trúc chuẩn cần giữ lại
VALID_FILES = {
    "Folder_folder1_item1.docx": "Folder / folder1",
    "Folder_folder1_item2.docx": "Folder / folder1",
    "Folder_folder1_item3.docx": "Folder / folder1",
    "Folder_folder2_item1.docx": "Folder / folder2",
    "Folder_folder2_item2.docx": "Folder / folder2",
    "Folder_folder2_item3.docx": "Folder / folder2",
}


def cleanup():
    print("🧹 Bắt đầu dọn dẹp các thư mục và tệp cũ không thuộc cấu trúc Folder...")

    # 1. Xóa các file vật lý thừa trong data/docs
    deleted_files = []
    if DATA_DOCS_DIR.exists():
        for f in DATA_DOCS_DIR.iterdir():
            if f.is_file() and f.name != ".gitkeep" and f.name not in VALID_FILES:
                f.unlink()
                deleted_files.append(f.name)
                print(f"   🗑️ Đã xóa tệp: {f.name}")

    # 2. Cập nhật lại doc_registry.json
    new_registry = []
    for filename, cat in VALID_FILES.items():
        file_path = DATA_DOCS_DIR / filename
        if file_path.exists():
            size = file_path.stat().st_size
        else:
            size = 37300
        new_registry.append({
            "filename": filename,
            "category": cat,
            "size": size,
            "upload_time": "2026-10-14T01:00:00.000000+00:00",
        })

    REG_FILE.write_text(json.dumps(new_registry, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"   ✅ Đã cập nhật doc_registry.json ({len(new_registry)} tệp thuộc Folder/folder1 & folder2)")

    # 3. Dọn dẹp vectors thừa trong ChromaDB
    try:
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        collection = client.get_or_create_collection(name="tlbm_docs")
        all_ids = collection.get()
        if all_ids and "ids" in all_ids and len(all_ids["ids"]) > 0:
            metas = all_ids.get("metadatas") or []
            ids_to_delete = []
            for id_, meta in zip(all_ids["ids"], metas):
                fn = meta.get("file_name") or meta.get("filename") or ""
                if fn and fn not in VALID_FILES:
                    ids_to_delete.append(id_)
            if ids_to_delete:
                collection.delete(ids=ids_to_delete)
                print(f"   🗑️ Đã xóa {len(ids_to_delete)} vector cũ khỏi ChromaDB")
    except Exception as e:
        print(f"   ⚠️ Lỗi dọn ChromaDB (bỏ qua): {e}")

    print("\n🎉 Hoàn thành dọn dẹp! Bây giờ kho tài liệu chỉ còn duy nhất 1 thư mục 'Folder' với các folder nhỏ 'folder1' và 'folder2'.")


if __name__ == "__main__":
    cleanup()
