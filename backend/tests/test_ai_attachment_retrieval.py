import hashlib
import os
import tempfile
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock, patch

from backend.services.pgvector_store import _compile_where_dict
from backend.services.rag_service import (
    _authorized_fallback_nodes,
    _fallback_query_filter,
    _is_document_overview_query,
    _local_attachment_digest,
    _read_authorized_attachment_pages,
    _rerank_hybrid_nodes,
    build_answer_prompt,
    extract_target_from_question,
    read_document_pages,
    read_pdf_pages_with_pdfplumber,
)


class AttachmentRetrievalTests(unittest.TestCase):
    def test_fallback_query_filters_unauthorized_documents_in_postgres_results(self):
        rows = {
            "documents": ["restricted"] * 12 + ["allowed"],
            "metadatas": [{"file_name": "same.pdf", "sql_doc_key": "vanbanden:2"}] * 12
            + [{"file_name": "same.pdf", "sql_doc_key": "vanbanden:1"}],
        }
        query_filter = _fallback_query_filter("same.pdf", {"vanbanden:1"})
        self.assertEqual(query_filter["$and"][0], {"file_name": "same.pdf"})
        nodes = _authorized_fallback_nodes(rows, {"vanbanden:1"})
        self.assertEqual([node.text for node in nodes], ["allowed"])
        self.assertEqual(_authorized_fallback_nodes(rows, set()), [])

    def test_fallback_filters_permissions_before_limit(self):
        rows = {
            "documents": ["restricted"] * 12 + ["allowed"],
            "metadatas": [{"sql_doc_key": "vanbanden:2"}] * 12
            + [{"sql_doc_key": "vanbanden:1"}],
        }
        nodes = _authorized_fallback_nodes(rows, {"vanbanden:1"})
        self.assertEqual([node.text for node in nodes], ["allowed"])
        self.assertEqual(_authorized_fallback_nodes(rows, set()), [])

    def test_hash_cache_hits_and_invalidates_after_change(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "attachment.pdf"
            path.write_bytes(b"first")
            _local_attachment_digest.cache_clear()

            def signature():
                stat = os.stat(path)
                return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)

            first_signature = signature()
            first = _local_attachment_digest(str(path), first_signature)
            self.assertEqual(_local_attachment_digest(str(path), first_signature), first)
            self.assertEqual(_local_attachment_digest.cache_info().hits, 1)
            path.write_bytes(b"second content")
            second = _local_attachment_digest(str(path), signature())
            self.assertEqual(second, hashlib.sha256(b"second content").hexdigest())
            self.assertNotEqual(first, second)

    def test_doc_reader_returns_extracted_text(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "attachment.doc"
            path.write_bytes(b"document bytes")
            mock_module = ModuleType("legacy_doc")
            mock_module.extract_text = MagicMock(return_value=SimpleNamespace(text="Nội dung văn bản"))
            with patch.dict("sys.modules", {"legacy_doc": mock_module}):
                pages = read_document_pages(path)
            mock_module.extract_text.assert_called_once_with(b"document bytes")
            self.assertEqual(pages[0]["text"], "Nội dung văn bản")

    def test_authorized_attachment_pages_uses_shutil_and_reads_text(self):
        with tempfile.TemporaryDirectory() as directory:
            src_path = Path(directory) / "note.txt"
            src_path.write_text("Nội dung tệp đính kèm hợp lệ", encoding="utf-8")
            sha = hashlib.sha256(src_path.read_bytes()).hexdigest()
            record = {"source_id": 10}
            fingerprints = [
                {
                    "attachment": {"id": 101, "name": "note.txt", "path": "note.txt"},
                    "suffix": ".txt",
                    "sha256": sha,
                }
            ]
            fake_storage = SimpleNamespace(open=lambda key, mode="rb": src_path.open("rb"))
            with patch("document_storage.get_document_storage", return_value=fake_storage):
                pages, pending = _read_authorized_attachment_pages(record, fingerprints)
            self.assertFalse(pending)
            self.assertEqual(len(pages), 1)
            self.assertIn("Nội dung tệp đính kèm hợp lệ", pages[0]["text"])

    def test_compile_where_dict_handles_fallback_query_filter_operators(self):
        where_dict = _fallback_query_filter("same.pdf", {"vanbanden:1", "vanbandi:2"})
        sql_fragment, params = _compile_where_dict(where_dict)
        self.assertIn("AND", sql_fragment)
        self.assertIn("OR", sql_fragment)
        self.assertIn("= ANY(%s)", sql_fragment)
        self.assertTrue(any('"file_name": "same.pdf"' in str(p) for p in params))
        self.assertTrue(any('"source_class": "ai_knowledge_base"' in str(p) for p in params))
        self.assertTrue(any(isinstance(p, list) and set(p) == {"vanbanden:1", "vanbandi:2"} for p in params))

    def test_read_docx_extracts_paragraphs_and_tables(self):
        from docx import Document
        from backend.services.rag_service import read_docx

        with tempfile.TemporaryDirectory() as directory:
            doc_path = Path(directory) / "table_sample.docx"
            doc = Document()
            doc.add_paragraph("Đoạn mở đầu")
            table = doc.add_table(rows=2, cols=2)
            table.cell(0, 0).text = "Cột A"
            table.cell(0, 1).text = "Cột B"
            table.cell(1, 0).text = "Giá trị 1"
            table.cell(1, 1).text = "Giá trị 2"
            doc.save(str(doc_path))
            extracted = read_docx(doc_path)
            self.assertIn("Đoạn mở đầu", extracted)
            self.assertIn("Cột A | Cột B", extracted)
            self.assertIn("Giá trị 1 | Giá trị 2", extracted)

    def test_authorized_fallback_nodes_preserves_order_and_keyword_relevance_for_large_docs(self):
        docs = [f"Section body {i}" for i in range(1, 15)]
        docs[11] = "2. TEAM PROJECT: AI DOCUMENT CHATBOT"
        metas = [
            {"file_name": "cv.pdf", "source_class": "ai_knowledge_base", "section": 1, "chunk_id": f"1-{i}"}
            for i in range(1, 15)
        ]
        nodes = _authorized_fallback_nodes({"documents": docs, "metadatas": metas}, None, question="Dự án thứ 2 là gì")
        self.assertEqual(len(nodes), 10)
        chunk_ids = [node.metadata["chunk_id"] for node in nodes]
        self.assertIn("1-12", chunk_ids)
        self.assertEqual(chunk_ids, sorted(chunk_ids, key=lambda cid: int(cid.split("-")[1])))

    def test_rerank_hybrid_nodes_prefers_numbered_item_and_matching_filename(self):
        dense = [
            SimpleNamespace(
                text="Mức 3 (Mật): Yêu cầu 2FA",
                metadata={"file_name": "Folder_folder2_item1.docx", "chunk_id": "1-3"},
                score=0.34,
            )
        ]
        kw = [
            SimpleNamespace(
                text="3. TEAM PROJECT: DOCUMENT MANAGEMENT SYSTEM",
                metadata={"file_name": "HuynhVuongThanhNha_CV (1).pdf", "chunk_id": "1-13"},
                score=0.45,
            )
        ]
        ranked = _rerank_hybrid_nodes(dense, kw, "Dự án thứ 3 của Nhã là gì")
        self.assertEqual(ranked[0].node.metadata["file_name"], "HuynhVuongThanhNha_CV (1).pdf")

    def test_attachment_pages_preserve_sql_display_name_and_extract_stem_target(self):
        with tempfile.TemporaryDirectory() as directory:
            src_path = Path(directory) / "phuluc.txt"
            src_path.write_text("Nội dung phụ lục đính kèm", encoding="utf-8")
            sha = hashlib.sha256(src_path.read_bytes()).hexdigest()
            record = {"source_id": 15, "display_name": "Quy chế 01/QC"}
            fingerprints = [
                {"attachment": {"id": 5, "name": "phuluc.txt", "path": "phuluc.txt"}, "suffix": ".txt", "sha256": sha}
            ]
            fake_storage = SimpleNamespace(open=lambda key, mode="rb": src_path.open("rb"))
            with patch("document_storage.get_document_storage", return_value=fake_storage):
                pages, _pending = _read_authorized_attachment_pages(record, fingerprints)
            self.assertEqual(pages[0]["metadata"]["file_name"], "Quy chế 01/QC")
            self.assertEqual(pages[0]["metadata"]["attachment_name"], "phuluc.txt")

        with patch(
            "backend.services.rag_service._get_scoped_indexed_filenames",
            return_value=["HuynhVuongThanhNha_CV (1).pdf", "Folder_folder1_item1.docx"],
        ):
            self.assertEqual(
                extract_target_from_question("Tóm tắt HuynhVuongThanhNha_CV giúp tôi"),
                "HuynhVuongThanhNha_CV (1).pdf",
            )

    def test_is_document_overview_query_detection(self):
        # Overview / general inquiries about documents
        self.assertTrue(_is_document_overview_query("Thông Tin chung"))
        self.assertTrue(_is_document_overview_query("thông tin"))
        self.assertTrue(_is_document_overview_query("Tổng quan"))
        self.assertTrue(_is_document_overview_query("Tóm tắt nội dung"))
        self.assertTrue(_is_document_overview_query("Tài liệu này nói gì"))
        self.assertTrue(_is_document_overview_query("Cho tôi biết nội dung chính của tài liệu"))
        self.assertTrue(_is_document_overview_query("general information"))
        self.assertTrue(_is_document_overview_query("overview"))

        # Specific questions should NOT be treated as overview queries
        self.assertFalse(_is_document_overview_query("Số hiệu văn bản 123/QĐ-BCT ban hành ngày nào?"))
        self.assertFalse(_is_document_overview_query("Ai là người ký quyết định này?"))

    def test_build_answer_prompt_contains_overview_directives_for_pinned_doc(self):
        prompt_vi = build_answer_prompt(
            question="Thông Tin chung",
            context="Nội dung tóm tắt tài liệu môn học IE402",
            history=None,
            target_filename="IE402.pdf",
            language="vi",
        )
        self.assertIn("IE402.pdf", prompt_vi)
        self.assertIn("thông tin chung", prompt_vi.lower())
        self.assertIn("tổng quan", prompt_vi.lower())

        prompt_en = build_answer_prompt(
            question="General information",
            context="Summary of course IE402",
            history=None,
            target_filename="IE402.pdf",
            language="en",
        )
        self.assertIn("IE402.pdf", prompt_en)
        self.assertIn("general information", prompt_en.lower())

    def test_read_pdf_pages_falls_back_to_pypdf_when_pdfplumber_empty(self):
        with tempfile.TemporaryDirectory() as directory:
            fake_pdf = Path(directory) / "test.pdf"
            fake_pdf.write_bytes(b"%PDF-1.4 dummy")

            with patch("pdfplumber.open", side_effect=Exception("pdfplumber corrupted stream")):
                mock_pypdf_reader = MagicMock()
                mock_pypdf_reader.pages = [MagicMock(extract_text=lambda: "Nội dung trích xuất từ pypdf")]
                with patch("pypdf.PdfReader", return_value=mock_pypdf_reader):
                    pages = read_pdf_pages_with_pdfplumber(fake_pdf)
                    self.assertEqual(len(pages), 1)
                    self.assertEqual(pages[0]["text"], "Nội dung trích xuất từ pypdf")
                    self.assertEqual(pages[0]["reader"], "pypdf")

    def test_rrf_hybrid_reranking_matches_admin_code_and_acronym_without_accents(self):
        from backend.services.rag_service import _extract_hybrid_keywords

        kw_list = _extract_hybrid_keywords("Nội dung quyết định số 123/QĐ-UBND về phân công phòng HC-NS")
        self.assertIn("123/qd-ubnd", kw_list)
        self.assertIn("hcns", kw_list)

        # Truy vấn gõ không dấu + viết tắt liền "quyet dinh 123 phong hcns"
        dense = [
            SimpleNamespace(
                text="Quyết định số 124/QĐ-UBND về việc khen thưởng cuối năm cho các đơn vị.",
                metadata={"file_name": "QD_124_UBND.pdf", "doc_code": "124/QĐ-UBND", "chunk_id": "1-1"},
                score=0.72,
            ),
            SimpleNamespace(
                text="Quyết định số 123/QĐ-UBND phân công nhiệm vụ Phòng Hành chính - Nhân sự (HC-NS).",
                metadata={"file_name": "QD_123_UBND.pdf", "doc_code": "123/QĐ-UBND", "chunk_id": "1-1"},
                score=0.61,
            ),
        ]
        keyword = [
            SimpleNamespace(
                text="Quyết định số 123/QĐ-UBND phân công nhiệm vụ Phòng Hành chính - Nhân sự (HC-NS).",
                metadata={"file_name": "QD_123_UBND.pdf", "doc_code": "123/QĐ-UBND", "chunk_id": "1-1"},
                score=0.65,
            ),
        ]
        ranked = _rerank_hybrid_nodes(dense, keyword, "quyet dinh 123 phong hcns")
        self.assertEqual(ranked[0].node.metadata["file_name"], "QD_123_UBND.pdf")
        self.assertGreater(ranked[0].node.metadata.get("rrf_score", 0), 0.03)

    def test_build_answer_prompt_supports_multi_document_comparison(self):
        prompt_vi = build_answer_prompt(
            question="So sánh điểm khác biệt chính giữa các văn bản này",
            context="[1] QD_01.pdf\nNội dung 1\n\n[2] QD_02.pdf\nNội dung 2",
            history=None,
            target_filenames=["QD_01.pdf", "QD_02.pdf"],
            language="vi",
        )
        self.assertIn("GHIM ĐỒNG THỜI NHIỀU TÀI LIỆU", prompt_vi)
        self.assertIn("QD_01.pdf", prompt_vi)
        self.assertIn("QD_02.pdf", prompt_vi)

    def test_secretary_system_prompt_and_soft_fallback_context_builder(self):
        from backend.services.rag_service import (
            SECRETARY_SYSTEM_PROMPT,
            SOFT_FALLBACK_NOTE_VI,
            _is_drafting_or_action_query,
            build_flexible_context_and_prompt,
        )

        self.assertIn("Kho Tài Liệu & Biểu Mẫu", SECRETARY_SYSTEM_PROMPT)
        self.assertTrue(_is_drafting_or_action_query("Soạn giúp tôi email thông báo lịch họp giao ban"))
        self.assertTrue(_is_drafting_or_action_query("Tóm tắt các bước lập tờ trình xin phê duyệt kinh phí"))

        # Low-score nodes below SOURCE_SCORE_THRESHOLD trigger Soft Fallback with sources == []
        low_score_node = SimpleNamespace(
            node=SimpleNamespace(
                metadata={"file_name": "Tap_tin_nhieu.pdf", "page_label": "1"},
                get_content=lambda: "Nội dung rời rạc điểm thấp",
            ),
            score=0.12,
        )
        ctx = build_flexible_context_and_prompt(
            question="Soạn giúp tôi email đôn đốc các phòng ban nộp báo cáo tháng",
            sources=[],
            history=[],
            clean_filenames=None,
            language="vi",
            raw_nodes=[low_score_node],
        )
        self.assertTrue(ctx["soft_fallback"])
        self.assertEqual(ctx["sources"], [])
        self.assertIn(SOFT_FALLBACK_NOTE_VI, ctx["prompt"])
        self.assertIn("Kính gửi", ctx["prompt"])
        self.assertIn("Nội dung chính", ctx["prompt"])
        self.assertIn("Đề xuất / Kiến nghị", ctx["prompt"])

    def test_ask_document_and_stream_soft_fallback_without_pinned_doc(self):
        import json
        from backend.services.rag_service import (
            SOFT_FALLBACK_NOTE_VI,
            ask_document,
            ask_document_stream,
        )

        mock_llm = MagicMock()
        mock_llm.complete.return_value = (
            "1. **Kính gửi**: Trưởng các phòng ban, đơn vị trực thuộc.\n"
            "2. **Nội dung chính**: Đề nghị các đơn vị hoàn thiện và gửi báo cáo công tác định kỳ trước 16h00.\n"
            "3. **Đề xuất / Kiến nghị**: Vui lòng tham khảo biểu mẫu chuẩn tại Kho Tài Liệu & Biểu Mẫu."
        )
        mock_chunk = SimpleNamespace(delta=mock_llm.complete.return_value)
        mock_llm.stream_complete.return_value = [mock_chunk]

        mock_retriever = MagicMock()
        mock_retriever.retrieve.return_value = []
        mock_index = MagicMock()
        mock_index.as_retriever.return_value = mock_retriever

        with patch("backend.services.ai_access.has_permission_codename", return_value=True), patch(
            "backend.services.sql_document_source.is_postgres_source", return_value=True
        ), patch(
            "backend.services.sql_document_source.accessible_document_keys", return_value={"vanbanden:1"}
        ), patch(
            "backend.services.business_knowledge.match_business_sources", return_value=[]
        ), patch("backend.services.rag_service.setup_llamaindex"), patch(
            "backend.services.rag_service.get_index", return_value=mock_index
        ), patch("backend.services.faq_response_cache.get_cached_answer", return_value=None), patch(
            "backend.services.rag_service.Settings"
        ) as mock_settings:
            mock_settings.llm = mock_llm
            result = ask_document(
                "Soạn giúp tôi email đôn đốc báo cáo định kỳ",
                user=SimpleNamespace(is_authenticated=True, id=1),
                filename=None,
                language="vi",
            )
            self.assertEqual(result["sources"], [])
            self.assertIn(SOFT_FALLBACK_NOTE_VI, result["answer"])
            self.assertIn("Kính gửi", result["answer"])
            self.assertIn("Nội dung chính", result["answer"])
            self.assertIn("Đề xuất / Kiến nghị", result["answer"])
            self.assertNotIn("Tôi không tìm thấy thông tin phù hợp", result["answer"])

            stream_events = list(
                ask_document_stream(
                    "Soạn giúp tôi email đôn đốc báo cáo định kỳ",
                    user=SimpleNamespace(is_authenticated=True, id=1),
                    filename=None,
                    language="vi",
                )
            )
            sources_event = next(ev for ev in stream_events if ev.startswith("event: sources"))
            done_event = next(ev for ev in stream_events if ev.startswith("event: done"))
            sources_payload = json.loads(sources_event.split("data: ", 1)[1].strip())
            done_payload = json.loads(done_event.split("data: ", 1)[1].strip())
            self.assertEqual(sources_payload, [])
            self.assertIn(SOFT_FALLBACK_NOTE_VI, done_payload["answer"])
            self.assertIn("Kính gửi", done_payload["answer"])

    def test_chat_api_view_returns_200_when_no_pinned_document(self):
        import json
        from django.test import RequestFactory
        from backend.api.views import _answer_chat
        from backend.services.rag_service import SOFT_FALLBACK_NOTE_VI

        rf = RequestFactory()
        payload = {
            "question": "Tóm tắt các bước lập tờ trình xin phê duyệt kế hoạch công tác",
            "history": [],
            "filename": None,
            "language": "vi",
        }
        request = rf.post(
            "/api/ai/chat",
            data=json.dumps(payload),
            content_type="application/json",
        )
        request.user = SimpleNamespace(is_authenticated=True, is_superuser=True, id=1, username="admin")

        mock_retriever = MagicMock()
        mock_retriever.retrieve.return_value = []
        mock_index = MagicMock()
        mock_index.as_retriever.return_value = mock_retriever

        with patch("backend.api.views._require_ai_access", return_value=None), patch(
            "backend.api.views.resolve_employee_id", return_value=1
        ), patch("backend.services.ai_access.has_permission_codename", return_value=True), patch(
            "backend.services.sql_document_source.is_postgres_source", return_value=True
        ), patch(
            "backend.services.sql_document_source.accessible_document_keys", return_value=set()
        ), patch(
            "backend.services.business_knowledge.match_business_sources", return_value=[]
        ), patch("backend.services.rag_service.setup_llamaindex"), patch(
            "backend.services.rag_service.get_index", return_value=mock_index
        ), patch("backend.services.faq_response_cache.get_cached_answer", return_value=None), patch(
            "backend.services.rag_service.Settings"
        ) as mock_settings:
            mock_settings.llm = MagicMock()
            response = _answer_chat(request, payload=payload)
            self.assertEqual(response.status_code, 200)
            body = json.loads(response.content.decode("utf-8"))
            self.assertEqual(body["sources"], [])
            self.assertIn(SOFT_FALLBACK_NOTE_VI, body["answer"])
            self.assertIn("Kính gửi", body["answer"])
            self.assertIn("Kho Tài Liệu & Biểu Mẫu", body["answer"])

    def test_detect_drafting_intent_and_prompt_enhancement_for_admin_templates(self):
        from backend.services.rag_service import (
            _detect_drafting_intent,
            build_answer_prompt,
            build_drafting_prompt_enhancement,
            build_secretary_fallback_answer,
        )

        # 1. Kiểm tra nhận diện đúng từng phân loại: Email công vụ, Công văn, Tờ trình / Đề xuất
        self.assertEqual(
            _detect_drafting_intent("Soạn giúp tôi email đôn đốc nộp báo cáo"),
            "email",
        )
        self.assertEqual(
            _detect_drafting_intent("Soạn công văn đôn đốc các đơn vị thực hiện báo cáo quý"),
            "cong_van",
        )
        self.assertEqual(
            _detect_drafting_intent("Viết giúp tờ trình đề xuất phê duyệt kinh phí đào tạo"),
            "to_trinh",
        )
        self.assertIsNone(
            _detect_drafting_intent("Quyết định số 123/QĐ-UBND ban hành ngày nào?")
        )

        # 2. Kiểm tra build_drafting_prompt_enhancement tạo đúng cấu trúc chuẩn
        email_enhancement = build_drafting_prompt_enhancement("Soạn giúp tôi email đôn đốc nộp báo cáo")
        self.assertIn("MẪU EMAIL CÔNG VỤ CHUẨN HÀNH CHÍNH", email_enhancement)
        self.assertIn("Tiêu đề Email (Subject)", email_enhancement)
        self.assertIn("Kính gửi", email_enhancement)
        self.assertIn("Nội dung chính", email_enhancement)
        self.assertIn("Chữ ký chuẩn (Signature)", email_enhancement)

        cong_van_enhancement = build_drafting_prompt_enhancement("Soạn công văn phúc đáp Sở Nội vụ")
        self.assertIn("MẪU CÔNG VĂN HÀNH CHÍNH CHUẨN", cong_van_enhancement)
        self.assertIn("CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM", cong_van_enhancement)
        self.assertIn("THỦ TRƯỞNG CƠ QUAN / ĐƠN VỊ", cong_van_enhancement)

        to_trinh_enhancement = build_drafting_prompt_enhancement("Lập tờ trình đề xuất mua sắm thiết bị")
        self.assertIn("MẪU TỜ TRÌNH / ĐỀ XUẤT PHÊ DUYỆT CHUẨN CÔNG SỞ", to_trinh_enhancement)
        self.assertIn("Căn cứ pháp lý & Sự cần thiết", to_trinh_enhancement)
        self.assertIn("Ý KIẾN PHÊ DUYỆT CỦA LÃNH ĐẠO", to_trinh_enhancement)

        # 3. Kiểm tra tích hợp vào system instruction của build_answer_prompt và kết quả trả về
        prompt = build_answer_prompt(
            question="Soạn giúp tôi email đôn đốc nộp báo cáo",
            context="",
            history=[],
            language="vi",
            soft_fallback=True,
        )
        self.assertIn("MẪU EMAIL CÔNG VỤ CHUẨN HÀNH CHÍNH", prompt)
        self.assertIn("Chữ ký chuẩn (Signature)", prompt)

        fallback_reply = build_secretary_fallback_answer(
            "Soạn giúp tôi email đôn đốc nộp báo cáo",
            language="vi",
        )
        self.assertIn("Tiêu đề / Chủ đề", fallback_reply)
        self.assertIn("Kính gửi", fallback_reply)
        self.assertIn("Nội dung chính", fallback_reply)
        self.assertIn("Chữ ký chuẩn & Nơi nhận", fallback_reply)
        self.assertIn("Trân trọng cảm ơn", fallback_reply)
        self.assertIn("(/resources)", fallback_reply)

    def test_unpinned_drafting_and_advisory_filter_out_noisy_keyword_sources(self):
        from backend.services.rag_service import ask_document

        # Mô phỏng node nhiễu chỉ khớp lỏng lẻo từ khóa phổ thông ("đề nghị", "phối hợp")
        noisy_kw_node = SimpleNamespace(
            text="Công văn 15/CV-ĐT về việc đề nghị phối hợp tổ chức hoạt động học tập thực tế cho sinh viên.",
            metadata={"file_name": "15_CV_DT.pdf", "doc_code": "15/CV-ĐT", "chunk_id": "1-2"},
            score=0.35,
        )
        ranked = _rerank_hybrid_nodes([], [noisy_kw_node], "Soạn giúp tôi email đôn đốc các phòng ban nộp báo cáo tháng")
        self.assertLess(ranked[0].score, 0.30)

        mock_retriever = MagicMock()
        mock_retriever.retrieve.return_value = [noisy_kw_node]
        mock_index = MagicMock()
        mock_index.as_retriever.return_value = mock_retriever

        with patch("backend.services.ai_access.has_permission_codename", return_value=True), patch(
            "backend.services.sql_document_source.is_postgres_source", return_value=True
        ), patch(
            "backend.services.sql_document_source.accessible_document_keys", return_value={"vanbandi:15"}
        ), patch(
            "backend.services.business_knowledge.match_business_sources", return_value=[]
        ), patch("backend.services.rag_service.setup_llamaindex"), patch(
            "backend.services.rag_service.get_index", return_value=mock_index
        ), patch("backend.services.faq_response_cache.get_cached_answer", return_value=None), patch(
            "backend.services.rag_service.Settings"
        ) as mock_settings:
            mock_settings.llm = MagicMock()
            result = ask_document(
                "Soạn giúp tôi email đôn đốc các phòng ban nộp báo cáo tháng",
                user=SimpleNamespace(is_authenticated=True, id=1),
                filename=None,
                language="vi",
            )
            self.assertEqual(result["sources"], [])
            self.assertIn("(/resources)", result["answer"])

    def test_detect_drafting_intent_rejects_unrelated_topics(self):
        from backend.services.rag_service import (
            _detect_drafting_intent,
            _is_drafting_or_action_query,
        )

        unrelated_queries = [
            "Cách nấu phở bò ngon?",
            "Viết code Python sắp xếp mảng",
            "Mẫu xe máy đẹp",
            "1 + 1 bằng mấy?",
            "Đề xuất thực đơn ăn kiêng",
            "Tóm tắt các bước nấu phở",
            "Draft a poem about rain",
        ]
        for query in unrelated_queries:
            self.assertIsNone(_detect_drafting_intent(query), msg=f"Unexpected drafting intent for: {query}")
            self.assertFalse(_is_drafting_or_action_query(query))

        self.assertEqual(
            _detect_drafting_intent("Soạn giúp tôi email đôn đốc các phòng ban nộp báo cáo tháng"),
            "email",
        )
        self.assertEqual(_detect_drafting_intent("Tóm tắt các bước lập tờ trình"), "to_trinh")
        self.assertEqual(_detect_drafting_intent("Soạn công văn đề nghị phối hợp"), "cong_van")
        self.assertEqual(_detect_drafting_intent("Lập biên bản cuộc họp giao ban"), "general_draft")
        self.assertEqual(_detect_drafting_intent("Xin mẫu báo cáo tổng kết quý"), "general_draft")

    def test_build_flexible_context_and_prompt_disables_soft_fallback_for_unrelated_and_pinned_misses(self):
        from backend.services.rag_service import build_flexible_context_and_prompt

        for query in (
            "Cách nấu phở bò ngon?",
            "Viết code Python sắp xếp mảng",
            "1 + 1 bằng mấy?",
        ):
            bundle = build_flexible_context_and_prompt(
                question=query,
                sources=[],
                clean_filenames=[],
                language="vi",
            )
            self.assertFalse(bundle["soft_fallback"])
            self.assertEqual(bundle["sources"], [])
            self.assertEqual(bundle["prompt"], "")

        pinned_miss = build_flexible_context_and_prompt(
            question="Soạn giúp tôi email đôn đốc",
            sources=[],
            clean_filenames=["quyet_dinh.pdf"],
            language="vi",
        )
        self.assertFalse(pinned_miss["soft_fallback"])
        self.assertEqual(pinned_miss["sources"], [])
        self.assertEqual(pinned_miss["prompt"], "")

    def test_finalize_secretary_answer_preserves_refusal_for_non_drafting_queries(self):
        from backend.services.rag_service import (
            NO_ANSWER_VI,
            SOFT_FALLBACK_NOTE_VI,
            _finalize_secretary_answer,
        )

        final_answer, is_refusal = _finalize_secretary_answer(
            raw_answer=NO_ANSWER_VI,
            question="Cách nấu phở bò ngon?",
            language="vi",
            soft_fallback=True,
            context_note=SOFT_FALLBACK_NOTE_VI,
            no_ans=NO_ANSWER_VI,
        )
        self.assertTrue(is_refusal)
        self.assertEqual(final_answer, NO_ANSWER_VI)

    def test_ask_document_and_stream_reject_unrelated_questions_immediately(self):
        import json
        from types import SimpleNamespace
        from unittest.mock import MagicMock, patch
        from backend.services.rag_service import (
            ask_document,
            ask_document_stream,
            build_contextual_no_answer,
            is_no_answer,
        )

        mock_retriever = MagicMock()
        mock_retriever.retrieve.return_value = []
        mock_index = MagicMock()
        mock_index.as_retriever.return_value = mock_retriever
        mock_settings = MagicMock()
        mock_settings.llm = MagicMock()
        user = SimpleNamespace(is_authenticated=True, is_active=True, is_superuser=True, id=1)

        with (
            patch("backend.services.rag_service.is_ai_configured", return_value=True),
            patch("backend.services.rag_service.setup_llamaindex"),
            patch("backend.services.rag_service.sync_documents_if_needed"),
            patch("backend.services.rag_service.get_index", return_value=mock_index),
            patch("backend.services.rag_service.Settings", mock_settings),
            patch("backend.services.sql_document_source.is_postgres_source", return_value=False),
            patch("backend.services.business_knowledge.match_business_sources", return_value=[]),
            patch("backend.services.faq_response_cache.get_cached_answer", return_value=None),
        ):
            for query in (
                "Cách nấu phở bò ngon?",
                "Viết code Python sắp xếp mảng",
                "1 + 1 bằng mấy?",
            ):
                expected = build_contextual_no_answer(question=query, language="vi")
                result = ask_document(query, user=user, filename=None, language="vi")
                self.assertEqual(result["answer"], expected)
                self.assertNotIn("Xin lỗi", result["answer"])
                self.assertIn("ngoài phạm vi", result["answer"])
                self.assertTrue(is_no_answer(result["answer"]))
                self.assertEqual(result["sources"], [])

                raw_sse = "".join(ask_document_stream(query, user=user, filename=None, language="vi"))
                done_payload = None
                sources_events = []
                for frame in raw_sse.strip().split("\n\n"):
                    lines = frame.strip().splitlines()
                    if len(lines) >= 2 and lines[0].startswith("event:") and lines[1].startswith("data:"):
                        ev = lines[0].split("event:", 1)[1].strip()
                        data = json.loads(lines[1].split("data:", 1)[1].strip())
                        if ev == "sources":
                            sources_events.append(data)
                        elif ev == "done":
                            done_payload = data
                self.assertIsNotNone(done_payload)
                self.assertEqual(done_payload["answer"], expected)
                self.assertEqual(done_payload["sources"], [])
                self.assertTrue(all(ev == [] for ev in sources_events))

            mock_settings.llm.complete.assert_not_called()
            mock_settings.llm.stream_complete.assert_not_called()

    def test_ask_document_and_stream_clear_sources_when_llm_refuses_pinned_or_matched_chunks(self):
        import json
        from types import SimpleNamespace
        from unittest.mock import MagicMock, patch
        from backend.services.rag_service import (
            LLM_REFUSAL_SENTINEL_VI,
            ask_document,
            ask_document_stream,
            build_contextual_no_answer,
            is_no_answer,
        )

        matched_node = SimpleNamespace(
            score=0.92,
            text="Quyết định ban hành quy chế quản lý văn bản và công tác văn thư lưu trữ nội bộ.",
            metadata={
                "file_name": "quyet_dinh.pdf",
                "page": 1,
                "chunk_id": "c1",
                "parent_context": "Quyết định ban hành quy chế quản lý văn bản và công tác văn thư lưu trữ nội bộ.",
                "source_class": "ai_knowledge_base",
            },
        )
        mock_retriever = MagicMock()
        mock_retriever.retrieve.return_value = [matched_node]
        mock_index = MagicMock()
        mock_index.as_retriever.return_value = mock_retriever
        mock_collection = SimpleNamespace(list_filenames=lambda allowed_keys=None: ["quyet_dinh.pdf"])
        mock_settings = MagicMock()
        mock_settings.llm = MagicMock()
        mock_settings.llm.complete.return_value = SimpleNamespace(text=LLM_REFUSAL_SENTINEL_VI)
        mock_settings.llm.stream_complete.return_value = [
            SimpleNamespace(delta=LLM_REFUSAL_SENTINEL_VI[:12]),
            SimpleNamespace(delta=LLM_REFUSAL_SENTINEL_VI[12:]),
        ]
        user = SimpleNamespace(is_authenticated=True, is_active=True, is_superuser=True, id=1)

        with (
            patch("backend.services.rag_service.is_ai_configured", return_value=True),
            patch("backend.services.rag_service.setup_llamaindex"),
            patch("backend.services.rag_service.sync_documents_if_needed"),
            patch("backend.services.rag_service.get_index", return_value=mock_index),
            patch("backend.services.rag_service.get_vector_collection", return_value=mock_collection),
            patch("backend.services.rag_service.Settings", mock_settings),
            patch("backend.services.sql_document_source.is_postgres_source", return_value=False),
            patch("backend.services.business_knowledge.match_business_sources", return_value=[]),
            patch("backend.services.faq_response_cache.get_cached_answer", return_value=None),
        ):
            expected = build_contextual_no_answer(
                question="Cách nấu phở bò ngon?",
                language="vi",
                clean_filenames=["quyet_dinh.pdf"],
            )
            result = ask_document(
                "Cách nấu phở bò ngon?",
                user=user,
                filename="quyet_dinh.pdf",
                language="vi",
            )
            self.assertEqual(result["answer"], expected)
            self.assertNotIn("Xin lỗi", result["answer"])
            self.assertTrue(is_no_answer(result["answer"]))
            self.assertEqual(result["sources"], [])

            raw_sse = "".join(
                ask_document_stream(
                    "Cách nấu phở bò ngon?",
                    user=user,
                    filename="quyet_dinh.pdf",
                    language="vi",
                )
            )
            sources_events = []
            done_payload = None
            for frame in raw_sse.strip().split("\n\n"):
                lines = frame.strip().splitlines()
                if len(lines) >= 2 and lines[0].startswith("event:") and lines[1].startswith("data:"):
                    ev = lines[0].split("event:", 1)[1].strip()
                    data = json.loads(lines[1].split("data:", 1)[1].strip())
                    if ev == "sources":
                        sources_events.append(data)
                    elif ev == "done":
                        done_payload = data

            self.assertIsNotNone(done_payload)
            self.assertEqual(done_payload["answer"], expected)
            self.assertEqual(done_payload["sources"], [])
            self.assertGreaterEqual(len(sources_events), 1)
            self.assertEqual(sources_events[-1], [])

    def test_validate_upload_allows_legacy_doc_extension(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from backend.api.views import _validate_upload

        self.assertEqual(_validate_upload(SimpleUploadedFile("legacy.doc", b"abc")), "")

    def test_domain_ocr_and_classify_prompts_follow_nd30_and_qlvb_categories(self):
        from backend.services.rag_service import VISION_OCR_PROMPT, classify_document

        self.assertIn("Quốc hiệu", VISION_OCR_PROMPT)
        self.assertIn("Số, ký hiệu văn bản", VISION_OCR_PROMPT)
        self.assertIn("Trích yếu", VISION_OCR_PROMPT)
        self.assertIn("Nghị định 30/2020/NĐ-CP", VISION_OCR_PROMPT)

        mock_llm = MagicMock()
        mock_llm.complete.return_value = "Quyết định"
        with patch("backend.services.rag_service.Settings") as mock_settings:
            mock_settings.llm = mock_llm
            result = classify_document("Quyết định số 12/QĐ-UBND ban hành quy chế nội bộ")

        self.assertEqual(result, "Quyết định")
        prompt_sent = mock_llm.complete.call_args[0][0]
        self.assertIn("Quyết định", prompt_sent)
        self.assertIn("Công văn", prompt_sent)
        self.assertNotIn("Vật lý", prompt_sent)
        self.assertNotIn("Hóa học", prompt_sent)

    def test_extract_targets_matches_doc_code_without_hardcoded_demo_folder(self):
        from backend.services.rag_service import extract_targets_from_question

        with patch(
            "backend.services.rag_service._get_scoped_indexed_filenames",
            return_value=["123_QD_UBND_quy_che.pdf", "45_CV_VP_bao_cao.pdf"],
        ):
            self.assertEqual(
                extract_targets_from_question("Cho tôi xem quyết định số 123/QĐ-UBND"),
                ["123_QD_UBND_quy_che.pdf"],
            )
            self.assertEqual(
                extract_targets_from_question("Thư mục 1, item 1 nói gì"),
                [],
            )

    def test_unpinned_drafting_gates_noisy_low_dense_hybrid_hits_to_soft_fallback(self):
        from backend.services.rag_service import SOFT_FALLBACK_NOTE_VI, ask_document

        noisy_dense_node = SimpleNamespace(
            text="Công văn 09/CV-KH đề nghị phối hợp báo cáo tiến độ dự án quý I.",
            metadata={
                "file_name": "09_CV_KH.pdf",
                "doc_code": "09/CV-KH",
                "chunk_id": "1-1",
                "parent_context": "Công văn 09/CV-KH đề nghị phối hợp báo cáo tiến độ dự án quý I.",
            },
            score=0.45,
        )
        noisy_kw_node = SimpleNamespace(
            text="Công văn 09/CV-KH đề nghị phối hợp báo cáo tiến độ dự án quý I.",
            metadata={
                "file_name": "09_CV_KH.pdf",
                "doc_code": "09/CV-KH",
                "chunk_id": "1-1",
                "parent_context": "Công văn 09/CV-KH đề nghị phối hợp báo cáo tiến độ dự án quý I.",
            },
            score=0.80,
        )
        ranked = _rerank_hybrid_nodes(
            [noisy_dense_node],
            [noisy_kw_node],
            "Soạn công văn đôn đốc nộp báo cáo tháng",
        )
        self.assertAlmostEqual(ranked[0].node.metadata["dense_score"], 0.45)

        mock_retriever = MagicMock()
        mock_retriever.retrieve.return_value = [ranked[0]]
        mock_index = MagicMock()
        mock_index.as_retriever.return_value = mock_retriever
        mock_llm = MagicMock()
        mock_llm.complete.return_value = (
            "1. **Tiêu đề / Chủ đề:** Công văn đôn đốc nộp báo cáo tháng\n"
            "2. **Kính gửi:** Các phòng ban chuyên môn."
        )

        with (
            patch("backend.services.ai_access.has_permission_codename", return_value=True),
            patch("backend.services.sql_document_source.is_postgres_source", return_value=True),
            patch("backend.services.sql_document_source.accessible_document_keys", return_value={"vanbandi:9"}),
            patch("backend.services.business_knowledge.match_business_sources", return_value=[]),
            patch("backend.services.rag_service.setup_llamaindex"),
            patch("backend.services.rag_service.get_index", return_value=mock_index),
            patch("backend.services.faq_response_cache.get_cached_answer", return_value=None),
            patch("backend.services.rag_service.Settings") as mock_settings,
        ):
            mock_settings.llm = mock_llm
            result = ask_document(
                "Soạn công văn đôn đốc nộp báo cáo tháng",
                user=SimpleNamespace(is_authenticated=True, id=1),
                filename=None,
                language="vi",
            )

        self.assertEqual(result["sources"], [])
        self.assertIn(SOFT_FALLBACK_NOTE_VI, result["answer"])
        prompt_sent = mock_llm.complete.call_args[0][0]
        self.assertIn(SOFT_FALLBACK_NOTE_VI, prompt_sent)
        self.assertIn("(/resources)", prompt_sent)
        self.assertNotIn("09_CV_KH.pdf", prompt_sent)

    def test_hieu_luc_lifecycle_propagates_across_prefix_context_sources_and_prompts(self):
        from backend.services.rag_service import (
            SECRETARY_SYSTEM_PROMPT,
            SECRETARY_SYSTEM_PROMPT_EN,
            build_context_from_sources,
            build_contextual_prefix,
            public_sources,
        )

        prefix = build_contextual_prefix(
            file_name="01/QC — Quy chế cũ",
            hieu_luc="HET_HIEU_LUC",
            ngay_het_hieu_luc="2025-12-31",
            page=1,
        )
        self.assertIn("Hết hiệu lực", prefix)
        self.assertIn("2025-12-31", prefix)

        sources = [
            {
                "file_name": "01/QC — Quy chế cũ",
                "context": "Nội dung điều 1",
                "hieu_luc": "HET_HIEU_LUC",
                "ngay_het_hieu_luc": "2025-12-31",
            },
            {
                "file_name": "02/QD — Quy chế sửa đổi",
                "context": "Nội dung điều 2",
                "hieu_luc": "CON_HIEU_LUC_1_PHAN",
                "ngay_het_hieu_luc": "2026-06-30",
            },
        ]
        rendered_ctx = build_context_from_sources(sources)
        self.assertIn("[CẢNH BÁO: VĂN BẢN ĐÃ HẾT HIỆU LỰC - hết hạn: 2025-12-31]", rendered_ctx)
        self.assertIn("[LƯU Ý: VĂN BẢN CÒN HIỆU LỰC MỘT PHẦN - hết hạn: 2026-06-30]", rendered_ctx)

        exported = public_sources(sources)
        self.assertEqual(exported[0]["hieu_luc"], "HET_HIEU_LUC")
        self.assertEqual(exported[0]["ngay_het_hieu_luc"], "2025-12-31")
        self.assertEqual(exported[1]["hieu_luc"], "CON_HIEU_LUC_1_PHAN")
        self.assertIn("Kiểm soát hiệu lực văn bản", SECRETARY_SYSTEM_PROMPT)
        self.assertIn("Document Validity Control", SECRETARY_SYSTEM_PROMPT_EN)

    def test_sync_documents_prunes_orphan_kb_vectors_and_clears_faq_cache(self):
        from backend.services.rag_service import sync_documents_if_needed

        mock_collection = MagicMock()
        mock_collection.indexed_filenames.return_value = {"kept.pdf", "orphan.gif"}
        mock_cursor = MagicMock()
        mock_cursor.__enter__.return_value = mock_cursor
        mock_cursor.__exit__.return_value = False

        with (
            patch("django.db.connection.cursor", return_value=mock_cursor),
            patch("backend.services.rag_service.get_vector_collection", return_value=mock_collection),
            patch("backend.services.document_service.load_registry", return_value=[{"filename": "kept.pdf", "category": "Quyết định"}]),
            patch("backend.services.faq_response_cache.clear_faq_cache") as mock_clear_cache,
        ):
            sync_documents_if_needed()

        mock_collection.delete.assert_called_once_with(
            where={"$and": [{"file_name": "orphan.gif"}, {"sql_doc_key": {"$exists": False}}]}
        )
        mock_clear_cache.assert_called_once_with()

    def test_authorized_attachment_strips_media_url_prefix_before_reading_storage(self):
        import io
        import os
        import tempfile
        from pathlib import Path
        from types import SimpleNamespace
        from unittest.mock import patch
        from backend.services.rag_service import (
            _authorized_attachment_fingerprints,
            _normalize_storage_relpath,
            _read_authorized_attachment_pages,
        )

        with tempfile.TemporaryDirectory() as tmp_root:
            rel_file = Path(tmp_root) / "mau-van-ban" / "2026" / "11" / "ebanking.docx"
            rel_file.parent.mkdir(parents=True, exist_ok=True)
            rel_file.write_bytes(b"fake-docx-bytes")

            fake_storage = SimpleNamespace(
                base_url="/media/",
                path=lambda name: str(Path(tmp_root) / name),
                open=lambda name, mode="rb": open(Path(tmp_root) / name, mode),
            )
            self.assertEqual(
                _normalize_storage_relpath("/media/mau-van-ban/2026/11/ebanking.docx", fake_storage),
                "mau-van-ban/2026/11/ebanking.docx",
            )
            self.assertEqual(
                _normalize_storage_relpath(
                    "https://staging-quanlyvanban.bhbl.vn/media/mau-van-ban/2026/11/ebanking.docx",
                    fake_storage,
                ),
                "mau-van-ban/2026/11/ebanking.docx",
            )

            record = {
                "source_id": 15,
                "display_name": "QTEBANKING — Quy trình Bảo Long Banking",
                "attachments": [
                    {
                        "id": 99,
                        "name": "Quy trình Ebanking_BPC_rev_31.07.26.docx",
                        "path": "/media/mau-van-ban/2026/11/ebanking.docx",
                    }
                ],
            }
            with (
                patch("document_storage.get_document_storage", return_value=fake_storage),
                patch(
                    "backend.services.rag_service.read_document_pages",
                    return_value=[{"page": 1, "text": "BLBanking là hệ thống thanh toán điện tử.", "reader": "docx"}],
                ),
            ):
                fps = _authorized_attachment_fingerprints(record)
                self.assertEqual(len(fps), 1)
                self.assertTrue(fps[0]["sha256"])
                pages, pending = _read_authorized_attachment_pages(record, fps)

            self.assertFalse(pending)
            self.assertEqual(len(pages), 1)
            self.assertIn("BLBanking là hệ thống thanh toán điện tử.", pages[0]["text"])

    def test_metadata_only_pinned_target_expands_safely_within_authorized_scope(self):
        from types import SimpleNamespace
        from unittest.mock import MagicMock, patch
        from backend.services.rag_service import (
            build_contextual_no_answer,
            prepare_ask_document,
        )

        pinned_label = "QTEBANKING — Quy trình Bảo Long Banking"
        proc_filename = "Quy trình Ebanking_BPC_rev_31.07.26.docx"

        meta_only_node = SimpleNamespace(
            score=0.45,
            text="Số hiệu: QTEBANKING\nTrích yếu: Quy trình Bảo Long Banking\nHiệu lực: Còn hiệu lực",
            metadata={
                "file_name": pinned_label,
                "reader": "ai-sql-view",
                "chunk_id": "1-1",
                "sql_doc_key": "tailieu:10",
                "sql_doc_type": "tailieu",
                "sql_doc_id": 10,
                "parent_context": "Số hiệu: QTEBANKING\nTrích yếu: Quy trình Bảo Long Banking",
            },
        )
        ebanking_body_node = SimpleNamespace(
            score=0.78,
            text="BLBanking (Bảo Long Banking) là nền tảng ngân hàng số nội bộ hỗ trợ tra cứu và đối soát thu hộ.",
            metadata={
                "file_name": proc_filename,
                "reader": "docx",
                "page": 1,
                "chunk_id": "1-1",
                "source_class": "ai_knowledge_base",
                "parent_context": "BLBanking (Bảo Long Banking) là nền tảng ngân hàng số nội bộ hỗ trợ tra cứu và đối soát thu hộ.",
            },
        )
        unauthorized_body_node = SimpleNamespace(
            score=0.95,
            text="BLBanking mật dành cho tài khoản không có quyền.",
            metadata={
                "file_name": "Mat_BLBanking.docx",
                "reader": "docx",
                "page": 1,
                "chunk_id": "1-1",
                "sql_doc_key": "tailieu:999",
                "parent_context": "BLBanking mật dành cho tài khoản không có quyền.",
            },
        )

        def _retrieve_side_effect(query):
            # Initial filtered retrieval gets metadata-only chunk; supplemental retrieval gets authorized + unauthorized candidates
            return [meta_only_node, unauthorized_body_node, ebanking_body_node]

        mock_retriever = MagicMock()
        mock_retriever.retrieve.side_effect = _retrieve_side_effect
        mock_index = MagicMock()
        mock_index.as_retriever.return_value = mock_retriever
        mock_collection = SimpleNamespace(
            list_filenames=lambda allowed_keys=None: [pinned_label, proc_filename],
            get=lambda where=None, include=None: {
                "ids": ["1"],
                "documents": [meta_only_node.text],
                "metadatas": [meta_only_node.metadata],
            },
        )
        user = SimpleNamespace(is_authenticated=True, is_active=True, is_superuser=False, id=7)

        # Case 1: Metadata-only pinned doc expands safely to authorized ebanking procedure file
        with (
            patch("backend.services.ai_access.has_permission_codename", return_value=True),
            patch("backend.services.rag_service.setup_llamaindex"),
            patch("backend.services.rag_service.get_index", return_value=mock_index),
            patch("backend.services.rag_service.get_vector_collection", return_value=mock_collection),
            patch("backend.services.sql_document_source.is_postgres_source", return_value=True),
            patch("backend.services.sql_document_source.accessible_document_keys", return_value={"tailieu:10"}),
            patch("backend.services.business_knowledge.match_business_sources", return_value=[]),
            patch("backend.services.faq_response_cache.get_cached_answer", return_value=None),
        ):
            prep_type, payload = prepare_ask_document(
                question="banking là gì",
                user=user,
                employee_id=7,
                filename=pinned_label,
                language="vi",
            )

        self.assertEqual(prep_type, "prompt")
        returned_files = [s["file_name"] for s in payload["sources"]]
        self.assertIn(proc_filename, returned_files)
        self.assertNotIn("Mat_BLBanking.docx", returned_files)

        # Case 2: Metadata-only pinned doc with NO matching supplemental file returns Reason 2 immediately
        mock_retriever.retrieve.side_effect = None
        mock_retriever.retrieve.return_value = [meta_only_node]
        with (
            patch("backend.services.ai_access.has_permission_codename", return_value=True),
            patch("backend.services.rag_service.setup_llamaindex"),
            patch("backend.services.rag_service.get_index", return_value=mock_index),
            patch("backend.services.rag_service.get_vector_collection", return_value=mock_collection),
            patch("backend.services.sql_document_source.is_postgres_source", return_value=True),
            patch("backend.services.sql_document_source.accessible_document_keys", return_value={"tailieu:10"}),
            patch("backend.services.business_knowledge.match_business_sources", return_value=[]),
            patch("backend.services.faq_response_cache.get_cached_answer", return_value=None),
        ):
            prep_empty, payload_empty = prepare_ask_document(
                question="banking có thể làm gì",
                user=user,
                employee_id=7,
                filename=pinned_label,
                language="vi",
            )
            prep_meta, payload_meta = prepare_ask_document(
                question="Số hiệu và hiệu lực của tài liệu này là gì?",
                user=user,
                employee_id=7,
                filename=pinned_label,
                language="vi",
            )

        self.assertEqual(prep_empty, "immediate")
        self.assertEqual(
            payload_empty["answer"],
            build_contextual_no_answer(
                question="banking có thể làm gì",
                language="vi",
                clean_filenames=[pinned_label],
                metadata_only=True,
            ),
        )
        self.assertEqual(prep_meta, "prompt")
        self.assertEqual(payload_meta["sources"][0]["file_name"], pinned_label)




