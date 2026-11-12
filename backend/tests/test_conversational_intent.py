import unittest

from backend.services.rag_service import is_conversational_or_emotional


class ConversationalIntentTests(unittest.TestCase):
    def test_conversational_and_rag_routing_cases(self):
        test_cases = [
            ("xin chào", True),
            ("Chào bạn nhé!", True),
            ("Hello trợ lý", True),
            ("Hôm nay mệt mỏi quá bạn ơi", True),
            ("Tôi buồn quá", True),
            ("Vừa xong việc, vui quá xá!", True),
            ("Haha bạn hài hước thật đấy", True),
            ("Cảm ơn bạn nhiều nha", True),
            ("Bạn là ai thế?", True),
            ("Kể chuyện cười đi bạn", True),
            ("Hôm nay trời đẹp ghê", True),
            ("Buồn ngủ quá rồi", True),
            ("Quy trình tiếp nhận văn bản đến như thế nào?", False),
            ("Chào bạn, quy trình xử lý văn bản đến ra sao?", False),
            ("What documents do they need?", False),
            ("Văn bản tuyệt mật gồm những loại nào?", False),
            ("Thời hạn lưu trữ hồ sơ công việc là bao lâu?", False),
            ("Tìm cho tôi hợp đồng số 12", False),
            ("Ai là người ký quyết định này?", False),
            ("Hướng dẫn ký số văn bản đi", False),
        ]
        for query, expected in test_cases:
            with self.subTest(query=query):
                self.assertEqual(is_conversational_or_emotional(query), expected)

