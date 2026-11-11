"""Tạo cấu trúc thư mục phân cấp đúng chuẩn theo hình:

Folder (Thư mục gốc)
  ├── folder1 (Thư mục con cấp 1)
  │     ├── item1 (Tệp 1)
  │     ├── item2 (Tệp 2)
  │     └── item3 (Tệp 3)
  └── folder2 (Thư mục con cấp 2)
        ├── item1 (Tệp 1)
        ├── item2 (Tệp 2)
        └── item3 (Tệp 3)

Đồng thời lập chỉ mục (index) toàn bộ vào Vector Database ChromaDB
để Trợ lý AI có thể tra cứu và trích dẫn theo đúng cấu trúc phân cấp.
"""

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

from backend.services.rag_service import index_document

# Thư mục gốc đúng tên "Folder"
FOLDER_ROOT = ROOT_DIR / "Folder"

DATA_ITEMS = {
    "folder1": {
        "description": "Nghiệp vụ Quản lý Văn bản và Điều hành",
        "category": "Nghiệp vụ Văn bản",
        "items": {
            "item1": {
                "title": "QUY ĐỊNH XỬ LÝ VĂN BẢN ĐẾN (ITEM 1 - FOLDER 1)",
                "so_hieu": "01/2026/QĐ-VBĐ",
                "content": (
                    "Điều 1. Tiếp nhận và đăng ký văn bản đến\n"
                    "Mọi văn bản gửi đến cơ quan phải được tiếp nhận tại Bộ phận Văn thư, kiểm tra phong bì, "
                    "con dấu hoặc chữ ký số. Sau khi kiểm tra tính toàn vẹn, văn thư tiến hành số hóa (quét OCR), "
                    "vào sổ đăng ký văn bản đến trên phần mềm TLBM và cấp số đến trong vòng tối đa 02 giờ làm việc.\n\n"
                    "Điều 2. Trình và phân phối văn bản đến\n"
                    "Văn bản đến phải được chuyển cho Lãnh đạo cơ quan xem xét, phân phối trong ngày làm việc. "
                    "Đối với văn bản Hỏa tốc, thời gian chuyển giao không quá 15 phút. "
                    "Đơn vị chủ trì có trách nhiệm xử lý dứt điểm theo đúng thời hạn được giao."
                ),
            },
            "item2": {
                "title": "QUY TRÌNH PHÁT HÀNH VĂN BẢN ĐI (ITEM 2 - FOLDER 1)",
                "so_hieu": "02/2026/QĐ-VBĐI",
                "content": (
                    "Điều 1. Kiểm tra thể thức trước khi phát hành\n"
                    "Văn thư cơ quan có trách nhiệm kiểm tra thể thức văn bản theo Nghị định 30/2020/NĐ-CP, "
                    "kiểm tra chữ ký số của người có thẩm quyền. Văn bản chưa đủ điều kiện thể thức sẽ bị từ chối phát hành.\n\n"
                    "Điều 2. Cấp số và phát hành điện tử\n"
                    "Văn bản đi được cấp số tự động theo từng danh mục loại văn bản (Quyết định, Công văn, Tờ trình, Thông báo). "
                    "Văn bản điện tử được phát hành qua Trục liên thông văn bản quốc gia hoặc gửi trực tiếp qua email công vụ "
                    "ngay trong ngày làm việc sau khi hoàn tất ký số."
                ),
            },
            "item3": {
                "title": "QUY CHẾ LƯU TRỮ HỒ SƠ TÀI LIỆU (ITEM 3 - FOLDER 1)",
                "so_hieu": "03/2026/QC-LT",
                "content": (
                    "Điều 1. Thời hạn bảo quản hồ sơ văn bản\n"
                    "Thời hạn bảo quản hồ sơ được quy định cụ thể như sau:\n"
                    "1. Hồ sơ lưu trữ vĩnh viễn: Nghị quyết, quyết định về cơ cấu tổ chức, nhân sự cấp cao, chiến lược phát triển.\n"
                    "2. Hồ sơ lưu trữ 20 năm: Hợp đồng kinh tế lớn, báo cáo tài chính năm đã kiểm toán.\n"
                    "3. Hồ sơ lưu trữ 10 năm: Văn bản hành chính thông thường, báo cáo quý, kế hoạch công tác định kỳ.\n"
                    "4. Hồ sơ lưu trữ 05 năm: Phiếu đề xuất, giấy giới thiệu, công văn trao đổi sự vụ.\n\n"
                    "Điều 2. Nộp lưu hồ sơ vào Lưu trữ cơ quan\n"
                    "Trong thời hạn 01 năm kể từ ngày công việc kết thúc, các đơn vị phải hoàn tất việc lập hồ sơ "
                    "và bàn giao hồ sơ tài liệu vào Lưu trữ cơ quan theo đúng mục lục hồ sơ."
                ),
            },
        },
    },
    "folder2": {
        "description": "Bảo mật Thông tin và Phân quyền Hệ thống",
        "category": "Bảo mật & Phân quyền",
        "items": {
            "item1": {
                "title": "TIÊU CHUẨN AN TOÀN BẢO MẬT TLBM (ITEM 1 - FOLDER 2)",
                "so_hieu": "04/2026/TC-BM",
                "content": (
                    "Điều 1. Phân loại mức độ nhạy cảm của dữ liệu\n"
                    "Hệ thống TLBM áp dụng 3 mức độ bảo vệ nghiêm ngặt:\n"
                    "- Mức 1 (Tuyệt mật): Dữ liệu mã hóa toàn bộ ổ đĩa với thuật toán AES-256 bit và quản lý khóa KMS.\n"
                    "- Mức 2 (Tối mật): Chỉ cho phép truy cập từ mạng nội bộ (VPN chuyên dụng), cấm tải về thiết bị cá nhân.\n"
                    "- Mức 3 (Mật): Yêu cầu xác thực 2 yếu tố (2FA) và ghi nhật ký truy cập (Audit Log) đầy đủ.\n\n"
                    "Điều 2. Phòng chống lộ lọt thông tin\n"
                    "Mọi tệp tài liệu xuất ra khỏi hệ thống đều được tự động chèn Watermark số nhận diện (Tên người dùng, IP, Thời gian xuất). "
                    "Hệ thống tự động khóa tài khoản sau 5 lần nhập sai mã PIN hoặc mật khẩu."
                ),
            },
            "item2": {
                "title": "QUY ĐỊNH PHÂN QUYỀN TRUY CẬP RBAC (ITEM 2 - FOLDER 2)",
                "so_hieu": "05/2026/QĐ-RBAC",
                "content": (
                    "Điều 1. Các nhóm quyền chính trong hệ thống\n"
                    "1. Nhóm Quản trị viên (ADMIN): Toàn quyền cấu hình hệ thống, quản lý tài khoản, cấu hình AI và xem log bảo mật.\n"
                    "2. Nhóm Lãnh đạo đơn vị (LEAD): Quyền xem xét, phê duyệt và ký số tất cả văn bản thuộc thẩm quyền.\n"
                    "3. Nhóm Trưởng phòng (TP): Quyền ký nháy, phân công xử lý văn bản cho chuyên viên trong phòng ban.\n"
                    "4. Nhóm Chuyên viên (CV): Quyền soạn thảo văn bản, lập hồ sơ và sử dụng Trợ lý ảo AI tra cứu tài liệu.\n"
                    "5. Nhóm Văn thư (VT): Quyền tiếp nhận văn bản đến, vào sổ văn bản đi và đóng dấu số điện tử.\n\n"
                    "Điều 2. Quyền sử dụng Trợ lý AI (use_aiassistant)\n"
                    "Người dùng bắt buộc phải được cấp quyền `use_aiassistant` mới có thể trò chuyện và hỏi đáp với AI Chatbox."
                ),
            },
            "item3": {
                "title": "QUY TRÌNH ỨNG PHÓ SỰ CỐ AN NINH (ITEM 3 - FOLDER 2)",
                "so_hieu": "06/2026/QT-SC",
                "content": (
                    "Điều 1. Các cấp độ sự cố an ninh mạng\n"
                    "- Cấp độ Khẩn cấp: Hệ thống bị tấn công từ chối dịch vụ (DDoS) hoặc rò rỉ cơ sở dữ liệu mật. "
                    "Thời gian phản ứng và kích hoạt kịch bản cô lập hệ thống không quá 15 phút.\n"
                    "- Cấp độ Nghiêm trọng: Phát hiện mã độc trong mạng nội bộ hoặc nghi ngờ tài khoản quản trị bị chiếm đoạt. "
                    "Thời gian xử lý không quá 02 giờ.\n\n"
                    "Điều 2. Kế hoạch khôi phục sau sự cố (Disaster Recovery)\n"
                    "Trung tâm dữ liệu luôn duy trì bản sao lưu nóng (Hot Standby) đồng bộ theo thời gian thực. "
                    "Thời gian phục hồi dịch vụ tối đa (RTO) là 30 phút và mức tổn thất dữ liệu tối đa (RPO) là 05 phút."
                ),
            },
        },
    },
}


def build_docx(title: str, so_hieu: str, content: str, out_path: Path):
    doc = docx.Document()
    sections = doc.sections
    for s in sections:
        s.top_margin = Inches(0.79)
        s.bottom_margin = Inches(0.79)
        s.left_margin = Inches(1.18)
        s.right_margin = Inches(0.79)

    # Header
    hp = doc.add_paragraph()
    hp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r1 = hp.add_run("CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nĐộc lập - Tự do - Hạnh phúc\n-----------------------")
    r1.bold = True
    r1.font.size = Pt(13)

    # Title
    tp = doc.add_paragraph()
    tp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r2 = tp.add_run(f"\n{title}\n")
    r2.bold = True
    r2.font.size = Pt(14)
    r2.font.color.rgb = RGBColor(16, 44, 87)

    # Số hiệu
    sp = doc.add_paragraph()
    sp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r3 = sp.add_run(f"Số hiệu: {so_hieu} | Ngày ban hành: 11/10/2026\n\n")
    r3.italic = True
    r3.font.size = Pt(11)

    # Content
    cp = doc.add_paragraph()
    cp.paragraph_format.line_spacing = 1.25
    r4 = cp.add_run(content)
    r4.font.size = Pt(12)

    doc.save(str(out_path))


def build_txt(title: str, so_hieu: str, content: str, out_path: Path):
    text = (
        "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\n"
        "Độc lập - Tự do - Hạnh phúc\n"
        "-----------------------\n\n"
        f"{title}\n"
        f"Số hiệu: {so_hieu} | Ngày ban hành: 11/10/2026\n\n"
        f"{content}\n"
    )
    out_path.write_text(text, encoding="utf-8")


def main():
    print("=" * 70)
    print("📂  TẠO CẤU TRÚC THƯ MỤC CÂY PHÂN CẤP CHUẨN: Folder -> folder1, folder2 -> item1, item2, item3")
    print("=" * 70)

    FOLDER_ROOT.mkdir(parents=True, exist_ok=True)
    data_docs_dir = ROOT_DIR / "data" / "docs"
    data_docs_dir.mkdir(parents=True, exist_ok=True)

    # Đọc registry hiện tại
    reg_file = ROOT_DIR / "data" / "doc_registry.json"
    registry = []
    if reg_file.exists():
        try:
            registry = json.loads(reg_file.read_text(encoding="utf-8"))
        except Exception:
            registry = []
    reg_names = {e["filename"] for e in registry}

    all_indexed = []

    for folder_name, folder_info in DATA_ITEMS.items():
        sub_dir = FOLDER_ROOT / folder_name
        sub_dir.mkdir(parents=True, exist_ok=True)
        print(f"\n📁 Thư mục con: Folder/{folder_name}/ ({folder_info['description']})")

        for item_name, item_info in folder_info["items"].items():
            docx_path = sub_dir / f"{item_name}.docx"
            txt_path = sub_dir / f"{item_name}.txt"

            build_docx(item_info["title"], item_info["so_hieu"], item_info["content"], docx_path)
            build_txt(item_info["title"], item_info["so_hieu"], item_info["content"], txt_path)

            print(f"   📄 Tệp: {item_name}.docx ({docx_path.stat().st_size:,} bytes) & {item_name}.txt")

            # Đồng thời chuẩn bị tệp trong data/docs để index
            safe_index_name = f"Folder_{folder_name}_{item_name}.docx"
            dest_index_file = data_docs_dir / safe_index_name
            shutil.copy2(docx_path, dest_index_file)

            if safe_index_name not in reg_names:
                registry.append({
                    "filename": safe_index_name,
                    "category": folder_info["category"],
                    "size": dest_index_file.stat().st_size,
                    "upload_time": datetime.now(timezone.utc).isoformat(),
                })
                reg_names.add(safe_index_name)

            all_indexed.append((dest_index_file, folder_info["category"], folder_name, item_name))

    reg_file.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")

    # Đồng bộ vào Database Django (bảng documents_folder và documents_folder_file)
    try:
        import os
        import django
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
        backend_dir = ROOT_DIR / "backend"
        if str(backend_dir) not in sys.path:
            sys.path.insert(0, str(backend_dir))
        django.setup()
        from documents.models import Folder, FolderFile

        # Thư mục gốc "Folder"
        db_root, _ = Folder.objects.get_or_create(
            name="Folder",
            parent=None,
            defaults={"description": "Thư mục gốc lưu trữ phân cấp hệ thống", "order": 0},
        )
        for f_name, f_info in DATA_ITEMS.items():
            db_sub, _ = Folder.objects.get_or_create(
                name=f_name,
                parent=db_root,
                defaults={"description": f_info["description"]},
            )
            for i_name, i_info in f_info["items"].items():
                for ext in ["docx", "txt"]:
                    full_fn = f"{i_name}.{ext}"
                    FolderFile.objects.get_or_create(
                        folder=db_sub,
                        file_name=full_fn,
                        defaults={
                            "file_type": ext,
                            "file_path": f"Folder/{f_name}/{full_fn}",
                            "description": i_info["title"],
                        },
                    )
        print("\n   🗄️ Đã đồng bộ cấu trúc Thư mục và Tệp vào cơ sở dữ liệu Django!")
    except Exception as db_err:
        print(f"\n   ⚠️ Không thể đồng bộ Django DB: {db_err}")

    print("\n" + "=" * 70)
    print("🚀  LẬP CHỈ MỤC (INDEXING) CẢ 6 TỆP VÀO VECTOR STORE CHROMADB...")
    print("=" * 70)

    for doc_path, cat, f_name, i_name in all_indexed:
        print(f"   ⚙️ Đang index Folder/{f_name}/{i_name}.docx ...")
        try:
            res = index_document(
                doc_path,
                category=cat,
                source_metadata={
                    "parent_folder": "Folder",
                    "sub_folder": f_name,
                    "item_name": i_name,
                    "display_name": f"Folder/{f_name}/{i_name}.docx",
                },
            )
            print(f"      ✅ Thành công ({res.get('document_count')} child chunks, Category: {cat})")
        except Exception as e:
            print(f"      ❌ Lỗi: {e}")

    print("\n" + "=" * 70)
    print("🎉 HOÀN TẤT 100%! CẤU TRÚC CÂY THƯ MỤC VÀ TÀI LIỆU ĐÃ SẴN SÀNG.")
    print("=" * 70)


if __name__ == "__main__":
    main()
