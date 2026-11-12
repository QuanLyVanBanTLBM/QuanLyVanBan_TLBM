from django.test import TestCase
from llama_index.core.schema import Document
from llama_index.core.vector_stores import MetadataFilter, MetadataFilters

from backend.services.pgvector_store import (
    PgVectorCollection,
    _VI_ACCENT_DST,
    _VI_ACCENT_SRC,
    insert_documents,
    keyword_search,
    similarity_search,
)


class _StubEmbedding:
    def get_text_embedding_batch(self, texts, show_progress=False):
        return [[1.0] + [0.0] * 3071 for _ in texts]

    def get_query_embedding(self, text):
        return [1.0] + [0.0] * 3071


class PgVectorStoreTests(TestCase):
    def test_insert_get_and_similarity_search_decode_json_metadata(self):
        filename = "pgvector-store-test.txt"
        document = Document(
            text="PostgreSQL vector search smoke test",
            metadata={"file_name": filename, "source_class": "ai_knowledge_base"},
        )

        ids = insert_documents([document], _StubEmbedding())
        collection = PgVectorCollection()
        stored = collection.get(ids=ids)
        results = similarity_search(
            "vector search",
            _StubEmbedding(),
            filters=MetadataFilters(filters=[MetadataFilter(key="file_name", value=filename)]),
        )

        self.assertEqual(stored["metadatas"][0]["file_name"], filename)
        self.assertEqual(results[0].node.text, document.text)
        self.assertEqual(results[0].node.metadata["file_name"], filename)

        collection.delete(ids=ids)
        self.assertEqual(collection.count(where={"file_name": filename}), 0)

    def test_keyword_search_matches_unaccented_text_and_respects_filters(self):
        self.assertEqual(len(_VI_ACCENT_SRC), len(_VI_ACCENT_DST))
        allowed_file = "HuynhVuongThanhNha_CV_unit.pdf"
        blocked_file = "TaiLieuMat_unit.pdf"
        docs = [
            Document(
                text="2. TEAM PROJECT: AI DOCUMENT CHATBOT by HUYNH VUONG THANH NHA",
                metadata={"file_name": allowed_file, "source_class": "ai_knowledge_base"},
            ),
            Document(
                text="2. TEAM PROJECT: RESTRICTED PROJECT",
                metadata={"file_name": blocked_file, "source_class": "official_document", "sql_doc_key": "vanbanden:99"},
            ),
        ]
        ids = insert_documents(docs, _StubEmbedding())
        try:
            hits = keyword_search(
                ["nha", "du", "an", "2"],
                filters=MetadataFilters(filters=[MetadataFilter(key="source_class", value="ai_knowledge_base")]),
            )
            self.assertTrue(hits)
            self.assertTrue(all(hit.node.metadata["file_name"] == allowed_file for hit in hits))
            self.assertIn("AI DOCUMENT CHATBOT", hits[0].node.text)
        finally:
            PgVectorCollection().delete(ids=ids)
