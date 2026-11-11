import hashlib
import os
import tempfile
import unittest
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import chromadb

from backend.services.rag_service import (
    _authorized_fallback_nodes,
    _fallback_query_filter,
    _local_attachment_digest,
    read_document_pages,
)


class AttachmentRetrievalTests(unittest.TestCase):
    def test_fallback_query_filters_unauthorized_documents_in_chroma(self):
        client = chromadb.EphemeralClient()
        collection = client.create_collection("ai-test-" + uuid.uuid4().hex)
        collection.add(
            ids=[str(i) for i in range(13)],
            embeddings=[[1.0, 0.0]] * 13,
            documents=["restricted"] * 12 + ["allowed"],
            metadatas=[{"file_name": "same.pdf", "sql_doc_key": "vanbanden:2"}] * 12
            + [{"file_name": "same.pdf", "sql_doc_key": "vanbanden:1"}],
        )
        rows = collection.get(
            where=_fallback_query_filter("same.pdf", {"vanbanden:1"}),
            include=["documents", "metadatas"],
        )
        self.assertEqual(rows["documents"], ["allowed"])
        self.assertEqual(_authorized_fallback_nodes(rows, {"vanbanden:1"})[0].text, "allowed")
        self.assertEqual(collection.get(where=_fallback_query_filter("same.pdf", set()))["ids"], [])

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

