import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import unittest

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
    make_source_preview,
    parent_for_child,
    read_document_pages,
)

class RagRegressionTests(unittest.TestCase):
    def test_chunk_text_uses_overlap(self):
        text = "a" * 700

        chunks = chunk_text(text, chunk_size=300, overlap=50)

        assert len(chunks) == 3
        assert chunks[0]["start"] == 0
        assert chunks[1]["start"] == 250
        assert chunks[2]["start"] == 500


    def test_parent_child_documents_keep_source_metadata(self):
        page_items = [{
            "text": (
                "Phần mở đầu nói về hệ thống hỏi đáp tài liệu. "
                "Phần phương pháp mô tả parent child chunking và citation theo trang. "
            ) * 20,
            "page": 2,
            "reader": "pdfplumber",
        }]

        documents = build_parent_child_documents(Path("baitap.pdf"), page_items)
        first_doc = documents[0]

        assert documents
        assert first_doc.metadata["file_name"] == "baitap.pdf"
        assert first_doc.metadata["page"] == 2
        assert first_doc.metadata["parent_context"]
        assert first_doc.metadata["child_text"] == first_doc.text


    def test_source_preview_prefers_question_keyword(self):
        text = (
            "Đoạn đầu chỉ giới thiệu tài liệu. "
            "Hệ thống sử dụng parent child chunking để tìm đoạn nhỏ và gửi ngữ cảnh lớn cho LLM. "
            "Đoạn cuối nói về giao diện."
        )

        preview = make_source_preview(text, "parent child chunking hoạt động thế nào?")

        assert "parent child chunking" in preview


    def test_ingest_multipage_document_creates_secondary_chunks(self):
        """Kiểm tra khi nạp tài liệu nhiều trang, hệ thống tách đúng các phân đoạn thứ cấp (child chunks)

        gắn liền với từng trang và định danh chunk_id chuẩn xác.
        """
        page_items = [
            {
                "text": "Trang 1: Quyết định số 123/QĐ-TLBM về ban hành Quy chế bảo mật thông tin nội bộ doanh nghiệp.",
                "page": 1,
                "reader": "pdfplumber",
            },
            {
                "text": (
                    "Trang 2: Điều 1. Phạm vi điều chỉnh. Quy chế này quy định việc quản lý, lưu trữ và luân chuyển tài liệu mật. "
                    "Điều 2. Đối tượng áp dụng. Toàn thể cán bộ, nhân viên thuộc các phòng ban đều phải chấp hành nghiêm túc."
                ) * 5,
                "page": 2,
                "reader": "pdfplumber",
            },
            {
                "text": "Trang 3: Điều 3. Hiệu lực thi hành. Quyết định có hiệu lực kể từ ngày ký ban hành.",
                "page": 3,
                "reader": "pdfplumber",
            },
        ]

        documents = build_parent_child_documents(
            Path("Quyet_dinh_123.pdf"),
            page_items,
            category="Quy định nội bộ",
            source_metadata={"source_class": "ai_knowledge_base"},
        )

        assert len(documents) >= 3

        # Kiểm tra metadata từng phân đoạn thứ cấp
        pages_found = {doc.metadata.get("page") for doc in documents}
        assert pages_found == {1, 2, 3}

        # Mỗi phân đoạn thứ cấp đều có chunk_id định dạng {section}-{child_index}
        for doc in documents:
            assert "-" in doc.metadata["chunk_id"]
            assert doc.metadata["category"] == "Quy định nội bộ"
            assert doc.metadata["file_name"] == "Quyet_dinh_123.pdf"
            assert doc.metadata["source_class"] == "ai_knowledge_base"
            assert doc.metadata["child_text"] == doc.text
            # Đảm bảo child chunk nằm trong parent context
            assert doc.metadata["child_text"] in doc.metadata["parent_context"]


    def test_secondary_chunks_containment_and_boundaries(self):
        """Kiểm tra với tài liệu dài vượt ngưỡng kích thước Parent Chunk (1500 ký tự),

        các phân đoạn thứ cấp (Child Chunk - 300 ký tự) luôn nằm gọn trong Parent Context tương ứng.
        """
        paragraph_template = (
            "Quy trình xử lý văn bản đến và đi tại cơ quan: "
            "Bước 1 là tiếp nhận văn bản, kiểm tra tính toàn vẹn của con dấu và chữ ký số. "
            "Bước 2 là phân loại độ mật: Tuyệt mật, Tối mật hoặc Mật theo đúng danh mục được phê duyệt. "
            "Bước 3 là số hóa và cập nhật vào phần mềm quản trị tài liệu nội bộ. "
        )
        long_document_text = paragraph_template * 15  # ~3000 ký tự, vượt 1500 ký tự

        page_items = [{"text": long_document_text, "page": 1, "reader": "docx"}]
        documents = build_parent_child_documents(Path("quy_trinh.docx"), page_items)

        assert len(documents) > 5  # Phải sinh ra nhiều child chunks

        for doc in documents:
            # Kiểm tra kích thước đoạn thứ cấp không vượt quá giới hạn
            assert len(doc.text) <= CHILD_CHUNK_SIZE
            # Kiểm tra ngữ cảnh sơ cấp (Parent context) có kích thước hợp lệ
            assert len(doc.metadata["parent_context"]) <= PARENT_CHUNK_SIZE
            # Kiểm tra đoạn thứ cấp là tập con của ngữ cảnh sơ cấp
            assert doc.text in doc.metadata["parent_context"]


    def test_ingest_real_file_on_disk(self):
        """Kiểm tra quy trình bỏ file tài liệu thực tế từ ổ đĩa vào hệ thống:

        Đọc tệp tin văn bản -> trích xuất nội dung -> bẻ chunk thứ cấp -> kiểm tra metadata.
        """
        sample_content = (
            "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\n"
            "Độc lập - Tự do - Hạnh phúc\n\n"
            "QUY CHẾ QUẢN LÝ TÀI LIỆU VÀ VĂN BẢN ĐIỆN TỬ\n"
            "Điều 1. Nguyên tắc quản lý\n"
            "Tất cả văn bản điện tử phải được lưu trữ tập trung, mã hóa bảo mật và phân quyền truy cập.\n"
            "Điều 2. Quy trình ký số\n"
            "Văn bản phát hành bắt buộc phải có chữ ký số hợp lệ của người có thẩm quyền.\n"
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            test_file = Path(tmp_dir) / "Quy_che_mau.txt"
            test_file.write_text(sample_content, encoding="utf-8")

            # 1. Đọc nội dung file
            pages = read_document_pages(test_file)
            assert len(pages) == 1
            assert pages[0]["reader"] == "txt"
            assert "QUY CHẾ QUẢN LÝ TÀI LIỆU" in pages[0]["text"]

            # 2. Bỏ tài liệu vào bộ chuyển đổi đa cấp (Parent-Child)
            docs = build_parent_child_documents(test_file, pages, category="Hành chính")

            assert len(docs) >= 1
            first_doc = docs[0]
            assert first_doc.metadata["file_name"] == "Quy_che_mau.txt"
            assert first_doc.metadata["category"] == "Hành chính"
            assert "QUY CHẾ QUẢN LÝ TÀI LIỆU" in first_doc.metadata["parent_context"]


    def test_retrieval_and_context_reconstruction_from_secondary_chunks(self):
        """Kiểm tra khi truy vấn: Tìm kiếm trúng đoạn thứ cấp (Child Chunk)

        nhưng hệ thống tự động trích xuất ngữ cảnh sơ cấp (Parent Context) để gửi cho LLM.
        """
        child_text = "Bước 2 là phân loại độ mật: Tuyệt mật, Tối mật hoặc Mật theo đúng danh mục."
        parent_context = (
            "QUY TRÌNH XỬ LÝ TÀI LIỆU BẢO MẬT:\n"
            "Bước 1: Tiếp nhận và vào sổ công văn mật.\n"
            "Bước 2 là phân loại độ mật: Tuyệt mật, Tối mật hoặc Mật theo đúng danh mục.\n"
            "Bước 3: Bàn giao trực tiếp cho người nhận, có ký nhận sổ theo dõi."
        )

        # Giả lập node trả về từ Vector Store (PostgreSQL pgvector)
        mock_node = MagicMock()
        mock_node.score = 0.88
        mock_node.text = child_text
        mock_node.metadata = {
            "file_name": "Quy_trinh_bao_mat.pdf",
            "page": 5,
            "section": 2,
            "chunk_id": "2-1",
            "category": "Bảo mật",
            "child_text": child_text,
            "parent_context": parent_context,
        }

        # 1. Trích xuất danh sách nguồn trích dẫn (sources)
        sources = build_sources([mock_node], "độ mật gồm những loại nào?")

        assert len(sources) == 1
        source = sources[0]
        assert source["file_name"] == "Quy_trinh_bao_mat.pdf"
        assert source["page"] == 5
        assert source["chunk_id"] == "2-1"
        assert source["score"] == 0.88
        # Preview phải trích xuất từ đoạn thứ cấp
        assert "độ mật" in source["preview"]
        # Context lưu trữ trong source phải là toàn bộ parent context
        assert "Bước 1: Tiếp nhận" in source["context"]
        assert "Bước 3: Bàn giao" in source["context"]

        # 2. Tạo context hoàn chỉnh cho LLM
        llm_context = build_context_from_sources(sources)

        assert "[1] Quy_trinh_bao_mat.pdf" in llm_context
        assert "QUY TRÌNH XỬ LÝ TÀI LIỆU BẢO MẬT" in llm_context
        assert "Bước 3: Bàn giao trực tiếp" in llm_context

    def test_structure_aware_chunking_and_contextual_retrieval_metadata(self):
        """Kiểm tra cắt chunk theo cấu trúc hành chính (Điều/Khoản) và gắn tiền tố ngữ cảnh (Contextual Retrieval)."""
        legal_text = (
            "ỦY BAN NHÂN DÂN THÀNH PHỐ\n"
            "Số: 123/QĐ-UBND\n"
            "QUYẾT ĐỊNH Về việc phân công nhiệm vụ phòng HC-NS\n"
            "Điều 1. Phạm vi điều chỉnh và đối tượng áp dụng\n"
            "Quyết định này quy định chức năng, nhiệm vụ và quyền hạn của Phòng Hành chính - Nhân sự (HC-NS) "
            "trong công tác quản lý văn bản mật và lưu trữ hồ sơ nội bộ.\n"
            "Điều 2. Nhiệm vụ cụ thể của bộ phận văn thư bảo mật\n"
            "1. Tiếp nhận, đăng ký và kiểm tra tính hợp lệ của toàn bộ văn bản đến có đóng dấu độ mật.\n"
            "2. Thực hiện phân phối văn bản đến đúng cá nhân có thẩm quyền xử lý trong vòng 02 giờ làm việc.\n"
            "Điều 3. Trách nhiệm thi hành và hiệu lực\n"
            "Các trưởng phòng ban và toàn thể cán bộ nhân viên chịu trách nhiệm thi hành Quyết định này."
        )
        page_items = [{"text": legal_text, "page": 1, "reader": "pdfplumber"}]
        docs = build_parent_child_documents(
            Path("QD_123_UBND.pdf"),
            page_items,
            category="Quyết định hành chính",
        )

        assert len(docs) >= 2
        for doc in docs:
            assert doc.metadata.get("doc_code") == "123/QĐ-UBND"
            prefix = doc.metadata.get("contextual_prefix") or ""
            assert "QD_123_UBND.pdf" in prefix
            assert "123/QĐ-UBND" in prefix
            assert "Quyết định hành chính" in prefix
            assert doc.metadata["child_text"] == doc.text
            assert doc.text in doc.metadata["parent_context"]

        headings = [doc.metadata.get("structural_heading") for doc in docs if doc.metadata.get("structural_heading")]
        assert any("Điều" in h for h in headings)

    def test_multi_document_sources_round_robin_and_balanced_context(self):
        """Kiểm tra ghim đồng thời nhiều tài liệu: phân bổ đều nguồn (round-robin) và cân bằng context."""
        nodes = []
        for i in range(1, 5):
            n1 = MagicMock()
            n1.score = 0.95 - i * 0.01
            n1.text = f"Nội dung điều {i} của văn bản A quy định chi tiết quy trình kiểm soát."
            n1.metadata = {
                "file_name": "Van_ban_A.pdf",
                "page": i,
                "chunk_id": f"1-{i}",
                "child_text": n1.text,
                "parent_context": n1.text,
            }
            nodes.append(n1)

        for i in range(1, 3):
            n2 = MagicMock()
            n2.score = 0.75 - i * 0.01
            n2.text = f"Nội dung điều {i} của văn bản B quy định chế tài xử lý vi phạm."
            n2.metadata = {
                "file_name": "Van_ban_B.pdf",
                "page": i,
                "chunk_id": f"1-{i}",
                "child_text": n2.text,
                "parent_context": n2.text,
            }
            nodes.append(n2)

        pinned = ["Van_ban_A.pdf", "Van_ban_B.pdf"]
        sources = build_sources(nodes, "So sánh điểm khác biệt giữa hai văn bản", target_filenames=pinned)
        file_names_in_sources = [s["file_name"] for s in sources]

        assert "Van_ban_A.pdf" in file_names_in_sources
        assert "Van_ban_B.pdf" in file_names_in_sources
        # Hai vị trí đầu tiên phải đại diện cho cả 2 tài liệu nhờ round-robin
        assert set(file_names_in_sources[:2]) == {"Van_ban_A.pdf", "Van_ban_B.pdf"}

        context = build_context_from_sources(sources)
        assert "[1] Van_ban_A.pdf" in context
        assert "[2] Van_ban_B.pdf" in context
