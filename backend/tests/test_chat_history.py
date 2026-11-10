import unittest

from backend.services.rag_service import (
    build_retrieval_query,
    format_chat_history,
    is_follow_up_question,
    normalize_chat_history,
)

class RagRegressionTests(unittest.TestCase):
    def test_is_follow_up_question_detects_short_follow_up(self):
        assert is_follow_up_question("giải thích thêm đi")
        assert is_follow_up_question("còn phần đó thì sao")
        assert not is_follow_up_question(
            "Hệ thống RAG sử dụng những công nghệ gì trong dự án này?"
        )


    def test_build_retrieval_query_uses_history_for_follow_up(self):
        history = [
            {"role": "user", "content": "RAG dùng công nghệ gì?"},
            {"role": "assistant", "content": "Dùng LlamaIndex, ChromaDB và Gemini."},
        ]

        query = build_retrieval_query("giải thích thêm phần embedding", history)

        assert "RAG dùng công nghệ gì?" in query
        assert "giải thích thêm phần embedding" in query


    def test_format_chat_history_keeps_recent_turns_only(self):
        history = [
            {"role": "user", "content": "Câu 1"},
            {"role": "assistant", "content": "Trả lời 1"},
            {"role": "user", "content": "Câu 2"},
            {"role": "assistant", "content": "Trả lời 2"},
            {"role": "user", "content": "Câu 3"},
            {"role": "assistant", "content": "Trả lời 3"},
            {"role": "user", "content": "Câu 4"},
            {"role": "assistant", "content": "Trả lời 4"},
            {"role": "user", "content": "Câu 5"},
            {"role": "assistant", "content": "Trả lời 5"},
        ]

        normalized = normalize_chat_history(history)
        formatted = format_chat_history(normalized)

        assert "Câu 1" not in formatted
        assert "Câu 5" in formatted
        assert "Người dùng:" in formatted
        assert "Trợ lý:" in formatted
