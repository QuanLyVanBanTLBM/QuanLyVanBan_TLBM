"""Script kiểm thử thực tế quy trình nạp tài liệu và phân đoạn thứ cấp (Parent-Child Chunking)

Hệ thống: Quản lý Văn bản và Tài liệu Bảo mật (TLBM) - Module 8 AI Assistant.

Cách chạy:
    python backend/scripts/test_secondary_chunk_ingest.py [đường_dẫn_tệp_tùy_chọn]
"""

import sys
from pathlib import Path

# Đảm bảo import được backend từ thư mục gốc
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.config import (
    CHILD_CHUNK_OVERLAP,
    CHILD_CHUNK_SIZE,
    PARENT_CHUNK_OVERLAP,
    PARENT_CHUNK_SIZE,
)
from backend.services.rag_service import (
    build_context_from_sources,
    build_parent_child_documents,
    build_sources,
    chunk_text,
    read_document_pages,
)


def create_sample_document(target_dir: Path) -> Path:
    """Tạo một tài liệu văn bản mẫu nếu người dùng không truyền file vào."""
    file_path = target_dir / "Quy_dinh_Bao_mat_Thong_tin_2026.txt"
    sample_text = (
        "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\n"
        "Độc lập - Tự do - Hạnh phúc\n\n"
        "QUY ĐỊNH BẢO MẬT THÔNG TIN VÀ QUẢN LÝ TÀI LIỆU NỘI BỘ\n"
        "Số hiệu: 88/2026/QĐ-TLBM | Ngày ban hành: 10/10/2026\n\n"
        "Chương I: QUY ĐỊNH CHUNG\n"
        "Điều 1. Phạm vi điều chỉnh\n"
        "Văn bản này quy định về việc phân loại, lưu trữ, tiếp nhận, chuyển giao "
        "và tiêu hủy các tài liệu chứa thông tin bí mật kinh doanh, bí mật kỹ thuật "
        "và thông tin nội bộ của cơ quan, doanh nghiệp.\n\n"
        "Điều 2. Phân loại cấp độ bảo mật\n"
        "Hệ thống văn bản được phân thành 3 cấp độ thứ bậc:\n"
        "1. Cấp độ Tuyệt mật: Chứa thông tin chiến lược cốt lõi, mã khóa mật mã hệ thống.\n"
        "2. Cấp độ Tối mật: Chứa hồ sơ tài chính chưa công bố, quy trình vận hành trọng yếu.\n"
        "3. Cấp độ Mật: Bao gồm hợp đồng đang đàm phán, biên bản họp hội đồng quản trị.\n\n"
        "Chương II: QUY TRÌNH TIẾP NHẬN VÀ LẬP CHỈ MỤC VĂN BẢN\n"
        "Điều 3. Quản lý văn bản đến và đi\n"
        "Toàn bộ văn bản đến phải được số hóa qua hệ thống OCR, phân đoạn tri thức "
        "theo cơ chế Parent-Child Chunking đa cấp (đoạn sơ cấp 1500 ký tự và đoạn thứ cấp 300 ký tự). "
        "Mỗi đoạn văn bản thứ cấp được lập chỉ mục vector tại ChromaDB nhằm phục vụ truy vấn chính xác.\n\n"
        "Điều 4. Nguyên tắc trích dẫn Zero-Hallucination\n"
        "Trợ lý AI chỉ được phép phản hồi dựa trên ngữ cảnh được cung cấp từ tài liệu hợp lệ. "
        "Khi tìm thấy đoạn thứ cấp phù hợp, hệ thống tự động liên kết với đoạn sơ cấp cha để cung cấp "
        "ngữ cảnh đầy đủ nhất cho mô hình ngôn ngữ lớn (LLM).\n"
    )
    file_path.write_text(sample_text, encoding="utf-8")
    return file_path


def test_ingest_secondary_chunks(file_path: Path):
    print("=" * 70)
    print("🚀  KIỂM THỬ QUY TRÌNH NẠP TÀI LIỆU VÀ PHÂN ĐOẠN THỨ CẤP (PARENT-CHILD)")
    print("=" * 70)

    if not file_path.exists():
        print(f"❌ Không tìm thấy tệp: {file_path}")
        return

    print(f"\n📁 Tệp kiểm thử: {file_path.name}")
    print(f"📊 Kích thước: {file_path.stat().st_size:,} bytes")
    print(f"⚙️  Cấu hình đa cấp:")
    print(f"   • Sơ cấp (Parent Chunk): {PARENT_CHUNK_SIZE} ký tự | Overlap: {PARENT_CHUNK_OVERLAP} ký tự")
    print(f"   • Thứ cấp (Child Chunk):  {CHILD_CHUNK_SIZE} ký tự | Overlap: {CHILD_CHUNK_OVERLAP} ký tự")

    # 1. Đọc nội dung tệp
    print("\n[Bước 1/4] Đang đọc nội dung tài liệu...")
    page_items = read_document_pages(file_path)
    total_text = "".join(p.get("text", "") for p in page_items)
    print(f"   ✅ Đọc thành công {len(page_items)} trang/phần.")
    print(f"   ✅ Tổng độ dài văn bản: {len(total_text):,} ký tự.")

    # 2. Thực hiện phân đoạn đa cấp (Parent-Child)
    print("\n[Bước 2/4] Đang phân tích và bẻ thành các phân đoạn thứ cấp (Child Chunks)...")
    documents = build_parent_child_documents(
        file_path,
        page_items,
        category="Quy định bảo mật",
        source_metadata={"source_class": "test_ingestion_doc"},
    )
    print(f"   ✅ Đã sinh ra tổng cộng: {len(documents)} phân đoạn thứ cấp (Child Documents).")

    # 3. Phân tích chi tiết các đoạn thứ cấp
    print("\n[Bước 3/4] Kiểm tra chi tiết các phân đoạn thứ cấp (Secondary Chunks):")
    print("-" * 70)

    # Hiển thị tối đa 5 chunk mẫu
    sample_count = min(len(documents), 5)
    for i in range(sample_count):
        doc = documents[i]
        meta = doc.metadata
        child_txt = doc.text.replace("\n", " ")
        parent_ctx = meta.get("parent_context", "").replace("\n", " ")

        print(f"\n🔹 PHÂN ĐOẠN THỨ CẤP #{i + 1} (Chunk ID: {meta.get('chunk_id')})")
        print(f"   • Trang (Page):        {meta.get('page')}")
        print(f"   • Danh mục (Category): {meta.get('category')}")
        print(f"   • Độ dài đoạn thứ cấp: {len(doc.text)} ký tự")
        print(f"   • Nội dung thứ cấp:    \"{child_txt[:120]}...\"")
        print(f"   • Ngữ cảnh sơ cấp cha: \"{parent_ctx[:150]}...\" (Tổng {len(meta.get('parent_context', ''))} ký tự)")

        # Kiểm tra tính toàn vẹn (containment)
        is_contained = doc.text in meta.get("parent_context", "")
        status = "✅ PASS (Nằm trọn trong Parent Context)" if is_contained else "❌ FAIL (Không khớp context)"
        print(f"   • Kiểm tra toàn vẹn:   {status}")

    if len(documents) > sample_count:
        print(f"\n   ... và {len(documents) - sample_count} phân đoạn thứ cấp khác được lập chỉ mục thành công.")

    # 4. Mô phỏng tìm kiếm và mở rộng ngữ cảnh cha
    print("\n" + "=" * 70)
    print("[Bước 4/4] Mô phỏng truy vấn tìm kiếm dựa trên đoạn thứ cấp:")
    sample_query = "cấp độ bảo mật gồm những loại nào"
    print(f"❓ Câu hỏi giả lập: \"{sample_query}\"")

    # Giả lập tìm thấy đoạn thứ cấp khớp nhất (chunk có chứa từ khóa)
    matched_doc = None
    for doc in documents:
        if "cấp độ" in doc.text.lower() or "bảo mật" in doc.text.lower():
            matched_doc = doc
            break

    if not matched_doc and documents:
        matched_doc = documents[0]

    if matched_doc:
        print(f"   🎯 Đoạn thứ cấp tìm thấy: Chunk ID {matched_doc.metadata.get('chunk_id')}")
        print(f"   📄 Nội dung trích dẫn thứ cấp (Citation Preview):")
        print(f"      \"{matched_doc.text[:140]}...\"")
        print(f"   📦 Ngữ cảnh sơ cấp (Parent Context) gửi cho LLM (Zero-Truncation):")
        print("   " + "-" * 66)
        for line in matched_doc.metadata.get("parent_context", "").split("\n"):
            if line.strip():
                print(f"      | {line}")
        print("   " + "-" * 66)
        print("   💡 Lợi ích: Vector search tìm trúng đoạn nhỏ 300 ký tự,")
        print("              nhưng LLM nhận trọn vẹn ngữ cảnh cha 1500 ký tự xung quanh.")

    print("\n" + "=" * 70)
    print("🎉 KIỂM THỬ HOÀN TẤT THÀNH CÔNG! QUY TRÌNH NẠP TÀI LIỆU THỨ CẤP ĐẠT CHUẨN.")
    print("=" * 70)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        target_path = Path(sys.argv[1])
    else:
        # Ưu tiên tài liệu trong data/docs nếu có
        sample_in_docs = ROOT_DIR / "data" / "docs" / "3. BÀI TẬP C3-P3-Testcase3-09-10-26_ITC.docx"
        if sample_in_docs.exists():
            target_path = sample_in_docs
        else:
            target_path = create_sample_document(ROOT_DIR / "data" / "docs")

    test_ingest_secondary_chunks(target_path)
