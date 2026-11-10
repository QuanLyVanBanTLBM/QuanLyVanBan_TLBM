"""
Script khởi tạo dữ liệu mẫu cho Mô hình Thư mục nhiều cấp (Hierarchical Folders)
Cấu trúc tạo mẫu:
Cấp 1: Tài liệu
  └── Cấp 2: Lập trình
        ├── Cấp 3: Python
        │     └── Cấp 4: Bài tập
        │           └── File: baitap.pdf, huongdan.docx
        └── Cấp 3: Java
              └── File: java_core.pdf
  └── Cấp 2: Cơ sở dữ liệu
        ├── Cấp 3: PostgreSQL
        └── Cấp 3: Redis
Cấp 1: Hành chính & Quy định
  └── Cấp 2: Quy chế công ty
"""

import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from documents.models import Folder, FolderFile


def seed_folders():
    print("🌱 Đang khởi tạo dữ liệu cấu trúc Thư mục nhiều cấp...")

    # Cấp 1: Tài liệu
    root_tailieu, _ = Folder.objects.get_or_create(
        name="Tài liệu",
        parent=None,
        defaults={"description": "Thư mục gốc chứa tài liệu kỹ thuật và đào tạo", "order": 1},
    )
    print(f"✅ Tạo Cấp 1: {root_tailieu.name} (depth={root_tailieu.depth}, path={root_tailieu.path})")

    # Cấp 2: Lập trình
    c2_laptrinh, _ = Folder.objects.get_or_create(
        name="Lập trình",
        parent=root_tailieu,
        defaults={"description": "Tài liệu ngôn ngữ và kỹ thuật lập trình", "order": 1},
    )
    print(f"  ✅ Tạo Cấp 2: {c2_laptrinh.name} (depth={c2_laptrinh.depth}, path={c2_laptrinh.path})")

    # Cấp 3: Python
    c3_python, _ = Folder.objects.get_or_create(
        name="Python",
        parent=c2_laptrinh,
        defaults={"description": "Ngôn ngữ lập trình Python, Django, FastApi", "order": 1},
    )
    print(f"    ✅ Tạo Cấp 3: {c3_python.name} (depth={c3_python.depth}, path={c3_python.path})")

    # Cấp 4: Bài tập
    c4_baitap, _ = Folder.objects.get_or_create(
        name="Bài tập",
        parent=c3_python,
        defaults={"description": "Bộ bài tập thực hành Python nâng cao", "order": 1},
    )
    print(f"      ✅ Tạo Cấp 4: {c4_baitap.name} (depth={c4_baitap.depth}, path={c4_baitap.path})")

    # Tệp trong Cấp 4
    file1, _ = FolderFile.objects.get_or_create(
        folder=c4_baitap,
        file_name="baitap.pdf",
        defaults={
            "file_size": 2048576,
            "file_type": "pdf",
            "file_path": "media/folder_files/baitap.pdf",
            "description": "Bài tập Python cơ bản và nâng cao",
        },
    )
    file2, _ = FolderFile.objects.get_or_create(
        folder=c4_baitap,
        file_name="huongdan.docx",
        defaults={
            "file_size": 1024000,
            "file_type": "docx",
            "file_path": "media/folder_files/huongdan.docx",
            "description": "Hướng dẫn nộp bài và chấm điểm",
        },
    )
    print(f"        📄 Thêm tệp: {file1.file_name}, {file2.file_name}")

    # Cấp 3: Java
    c3_java, _ = Folder.objects.get_or_create(
        name="Java",
        parent=c2_laptrinh,
        defaults={"description": "Java Core, Spring Boot", "order": 2},
    )
    FolderFile.objects.get_or_create(
        folder=c3_java,
        file_name="java_core.pdf",
        defaults={"file_size": 3145728, "file_type": "pdf", "description": "Giáo trình Java cơ bản"},
    )
    print(f"    ✅ Tạo Cấp 3: {c3_java.name} (depth={c3_java.depth}, path={c3_java.path})")

    # Cấp 2: Cơ sở dữ liệu
    c2_csdl, _ = Folder.objects.get_or_create(
        name="Cơ sở dữ liệu",
        parent=root_tailieu,
        defaults={"description": "SQL & NoSQL databases", "order": 2},
    )
    print(f"  ✅ Tạo Cấp 2: {c2_csdl.name} (depth={c2_csdl.depth}, path={c2_csdl.path})")

    # Cấp 3: PostgreSQL & Redis
    c3_pg, _ = Folder.objects.get_or_create(name="PostgreSQL", parent=c2_csdl, defaults={"order": 1})
    c3_redis, _ = Folder.objects.get_or_create(name="Redis", parent=c2_csdl, defaults={"order": 2})
    print(f"    ✅ Tạo Cấp 3: {c3_pg.name}, {c3_redis.name}")

    # Cấp 1 thứ 2: Hành chính
    root_hc, _ = Folder.objects.get_or_create(
        name="Hành chính & Quy định",
        parent=None,
        defaults={"description": "Văn bản nội bộ và quy chế công ty", "order": 2},
    )
    c2_qc, _ = Folder.objects.get_or_create(name="Quy chế công ty", parent=root_hc, defaults={"order": 1})
    print(f"✅ Tạo Cấp 1: {root_hc.name} -> Cấp 2: {c2_qc.name}")

    print("\n🎉 Hoàn thành khởi tạo dữ liệu cây thư mục nhiều cấp!")


if __name__ == "__main__":
    seed_folders()
