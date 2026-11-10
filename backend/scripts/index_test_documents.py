"""Lập chỉ mục (Index) các tài liệu mẫu vào Vector Database ChromaDB

để Trợ lý AI có thể trả lời ngay lập tức khi người dùng đặt câu hỏi.
"""

import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.services.rag_service import index_document

DOCS = [
    ("Quy_Che_Bao_Mat_Thong_Tin_TLBM.docx", "Bảo mật & Lưu trữ"),
    ("Quy_Trinh_Ky_So_Va_Trinh_Ky_Van_Ban.docx", "Quy trình Trình ký"),
    ("Chinh_Sach_Phuc_Loi_Va_Nghi_Phep_2026.docx", "Nhân sự & Phúc lợi"),
    ("Huong_Dan_Van_Hanh_He_Thong_Va_Tro_Ly_AI.docx", "Kỹ thuật CNTT"),
]

def main():
    docs_dir = ROOT_DIR / "data" / "docs"
    print("=" * 70)
    print("🚀 BẮT ĐẦU LẬP CHỈ MỤC (INDEXING) CÁC TÀI LIỆU VÀO CHROMADB")
    print("=" * 70)

    for filename, category in DOCS:
        file_path = docs_dir / filename
        if not file_path.exists():
            print(f"⚠️  Không tìm thấy: {filename}")
            continue

        print(f"\n📄 Đang lập chỉ mục: {filename}...")
        try:
            result = index_document(file_path, category=category)
            print(f"   ✅ Thành công! Số chunks thứ cấp: {result.get('document_count')}")
            print(f"   🏷️  Danh mục: {result.get('category')}")
        except Exception as e:
            print(f"   ❌ Lỗi: {e}")

    print("\n" + "=" * 70)
    print("🎉 HOÀN TẤT LẬP CHỈ MỤC! CON AI ĐÃ SẴN SÀNG TRẢ LỜI CÁC CÂU HỎI.")
    print("=" * 70)

if __name__ == "__main__":
    main()
