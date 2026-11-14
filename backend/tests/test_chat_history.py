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
            {"role": "assistant", "content": "Dùng LlamaIndex, PostgreSQL pgvector và OpenAI gpt-6-luna."},
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

    def test_long_elliptical_follow_up_detection_and_conversational_rewriting(self):
        # Các câu hỏi nối tiếp dài > 6 từ thường gặp trong thực tế (Tình huống 4)
        assert is_follow_up_question("Áp dụng cho nhân sự thử việc không?")
        assert is_follow_up_question("Vậy trường hợp làm việc trên 5 năm thì sao?")
        assert is_follow_up_question("Đối với phòng hành chính nhân sự thì như thế nào?")

        history = [
            {"role": "user", "content": "Quy định nghỉ phép năm 2026 thế nào?"},
            {
                "role": "assistant",
                "content": "Theo Quyết định 45/QĐ-TLBM (Điều 4), nhân viên chính thức có 12 ngày phép/năm.",
            },
            {"role": "user", "content": "Vậy trường hợp làm việc trên 5 năm thì sao?"},
            {
                "role": "assistant",
                "content": "Theo Khoản 2 Điều 4 Quyết định 45/QĐ-TLBM, cứ đủ 5 năm thâm niên được cộng thêm 1 ngày phép.",
            },
        ]

        rewritten = build_retrieval_query("Áp dụng cho nhân sự thử việc không?", history)
        assert "Quy định nghỉ phép năm 2026 thế nào?" in rewritten
        assert "45/QĐ-TLBM" in rewritten
        assert "Áp dụng cho nhân sự thử việc không?" in rewritten
