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

