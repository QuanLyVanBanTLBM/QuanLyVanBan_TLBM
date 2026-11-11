import hashlib
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from backend.services.pgvector_store import _compile_where_dict
from backend.services.rag_service import (
    _authorized_fallback_nodes,
    _fallback_query_filter,
    _local_attachment_digest,
    _read_authorized_attachment_pages,
    read_document_pages,
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
            with patch("legacy_doc.extract_text", return_value=SimpleNamespace(text="Nội dung văn bản")) as extract:
                pages = read_document_pages(path)
            extract.assert_called_once_with(b"document bytes")
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

