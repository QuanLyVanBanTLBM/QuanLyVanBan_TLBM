"""
Chức vụ: STT không vượt trần INTEGER của DDL; cập nhật thiếu is_public không đổi cờ công khai.
"""
from rest_framework import status

from accounts.models import Position
from accounts.test_positions import IMPORT_URL, LIST_URL, PositionBaseTestCase, detail_url, make_xlsx

LIMIT = 2147483647


class PositionHardeningTests(PositionBaseTestCase):
    def test_stt_above_limit_rejected_with_message_key(self):
        res = self.client_for["pos_manager"].post(
            LIST_URL, {"name": "Quá lớn", "display_order": LIMIT + 1}, format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.json()["display_order"], ["positions.messages.sttTooLarge"])
        self.assertFalse(self.others().exists())

    def test_stt_at_limit_is_accepted_and_auto_numbering_keeps_working(self):
        client = self.client_for["pos_manager"]
        first_available = Position.get_next_display_order()
        res = client.post(LIST_URL, {"name": "Sát trần", "display_order": LIMIT}, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        res = client.post(LIST_URL, {"name": "Tự cấp"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.json()["display_order"], first_available)

    def test_next_display_order_takes_smallest_free_number_when_max_is_at_limit(self):
        first_available = Position.get_next_display_order()
        for stt in (first_available, first_available + 2, LIMIT):
            Position.objects.create(display_order=stt, name=f"P{stt}")
        self.assertEqual(Position.get_next_display_order(), first_available + 1)

    def test_put_without_is_public_keeps_internal_position_internal(self):
        position = Position.objects.create(
            display_order=Position.get_next_display_order(),
            name="Nội bộ",
            is_public=False,
        )
        res = self.client_for["pos_manager"].put(
            detail_url(position.pk), {"name": "Nội bộ mới"}, format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        position.refresh_from_db()
        self.assertEqual(position.name, "Nội bộ mới")
        self.assertFalse(position.is_public)

    def test_create_without_is_public_defaults_to_public(self):
        res = self.client_for["pos_manager"].post(LIST_URL, {"name": "Mặc định"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(res.json()["is_public"])

    def test_import_reports_stt_above_limit_per_row_instead_of_failing(self):
        upload = make_xlsx([[LIMIT + 1, "Quá lớn", "Có", ""], [None, "Hợp lệ", "Có", ""]])
        res = self.client_for["pos_manager"].post(IMPORT_URL, {"file": upload}, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        body = res.json()
        self.assertEqual(body["imported"], 1)
        self.assertEqual(body["failed"], 1)
        self.assertEqual(body["errors"][0]["code"], "positions.messages.sttTooLarge")
        self.assertEqual(body["errors"][0]["field"], "display_order")

    def test_import_blank_stt_uses_free_number_when_max_is_at_limit(self):
        first_available = Position.get_next_display_order()
        Position.objects.create(display_order=LIMIT, name="Sát trần")
        upload = make_xlsx([[None, "Dòng tự cấp", "Có", ""]])
        res = self.client_for["pos_manager"].post(IMPORT_URL, {"file": upload}, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.json()["imported"], 1)
        self.assertEqual(Position.objects.get(name="Dòng tự cấp").display_order, first_available)
