"""Quy tắc Phòng ban từ QA 14/10: N2 thứ tự khối, N3 trùng tên đơn vị cùng khối, N4 SĐT +84."""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.db.models import Max
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from organizations.models import DonVi, KhoiKhuVuc

REGIONS = "/api/organizations/regions/"
UNITS = "/api/organizations/units/"


def next_unit_priority():
    return (DonVi.objects.aggregate(m=Max("stt_uu_tien"))["m"] or 0) + 1


class PhongBanRulesTest(TestCase):
    def setUp(self):
        self.block = KhoiKhuVuc.objects.create(ten="Khối Một", thu_tu_hien_thi=1)
        self.other_block = KhoiKhuVuc.objects.create(ten="Khối Hai", thu_tu_hien_thi=2)
        self.unit = DonVi.objects.create(khoi=self.block, stt_uu_tien=next_unit_priority(), ten="Lãnh đạo khối")
        user = get_user_model().objects.create_user(username="pb_admin", password="x", don_vi=self.unit)
        user.user_permissions.add(
            *Permission.objects.filter(codename__in=["view_donvi", "add_donvi", "change_donvi", "delete_donvi"])
        )
        self.client = APIClient()
        self.client.force_authenticate(user=user)

    # N2
    def test_new_region_without_display_order_goes_last_not_first(self):
        last_order = KhoiKhuVuc.objects.aggregate(m=Max("thu_tu_hien_thi"))["m"]
        response = self.client.post(REGIONS, {"ten": "Khối Mới"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["thu_tu_hien_thi"], last_order + 1)
        listed = [r["ten"] for r in self.client.get(f"{REGIONS}?all=true").data]
        self.assertEqual(listed[-1], "Khối Mới")

    def test_region_display_order_can_be_set_and_changed(self):
        created = self.client.post(REGIONS, {"ten": "Khối Đầu", "thu_tu_hien_thi": 0}, format="json")
        self.assertEqual(created.data["thu_tu_hien_thi"], 0)
        self.assertEqual(self.client.get(f"{REGIONS}?all=true").data[0]["ten"], "Khối Đầu")
        moved = self.client.patch(f"{REGIONS}{created.data['id']}/", {"thu_tu_hien_thi": 999}, format="json")
        self.assertEqual(moved.status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.get(f"{REGIONS}?all=true").data[-1]["ten"], "Khối Đầu")

    # N3
    def test_duplicate_unit_name_in_same_block_is_rejected(self):
        for name in ("Lãnh đạo khối", "  lãnh ĐẠO khối  "):
            response = self.client.post(UNITS, {"khoi": self.block.id, "ten": name}, format="json")
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(response.data["ten"], ["organizations.messages.unitNameExists"])
        self.assertEqual(DonVi.objects.filter(khoi=self.block).count(), 1)

    def test_same_unit_name_in_another_block_is_allowed(self):
        response = self.client.post(UNITS, {"khoi": self.other_block.id, "ten": "Lãnh đạo khối"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_editing_a_unit_keeps_its_own_name_but_cannot_take_a_sibling_name(self):
        sibling = DonVi.objects.create(khoi=self.block, stt_uu_tien=next_unit_priority(), ten="Ban Kế toán")
        own = self.client.patch(f"{UNITS}{self.unit.id}/", {"ten": "Lãnh đạo khối", "email": "ld@example.com"}, format="json")
        self.assertEqual(own.status_code, status.HTTP_200_OK)
        taken = self.client.patch(f"{UNITS}{sibling.id}/", {"ten": "lãnh đạo khối"}, format="json")
        self.assertEqual(taken.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(taken.data["ten"], ["organizations.messages.unitNameExists"])

    def test_moving_a_unit_into_a_block_with_the_same_name_is_rejected(self):
        moving = DonVi.objects.create(khoi=self.other_block, stt_uu_tien=next_unit_priority(), ten="Lãnh đạo khối")
        response = self.client.patch(f"{UNITS}{moving.id}/", {"khoi": self.block.id}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["ten"], ["organizations.messages.unitNameExists"])

    # N4
    def test_unit_phone_accepts_0_and_plus84_and_keeps_input(self):
        for phone in ("0912345678", "+84912345678", "+84 28 3823 9219", "028.3823.9219"):
            response = self.client.patch(f"{UNITS}{self.unit.id}/", {"dien_thoai": phone}, format="json")
            self.assertEqual(response.status_code, status.HTTP_200_OK, phone)
            self.assertEqual(response.data["dien_thoai"], phone)

    def test_unit_phone_rejects_invalid_numbers(self):
        for phone in ("84912345678", "+8412345678", "0112345678", "+840912345678", "abc"):
            response = self.client.patch(f"{UNITS}{self.unit.id}/", {"dien_thoai": phone}, format="json")
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, phone)
            self.assertEqual(response.data["dien_thoai"], ["organizations.messages.phoneInvalid"])

    def test_model_validation_uses_the_same_phone_rule(self):
        self.unit.dien_thoai = "+84912345678"
        self.unit.save()
        self.unit.dien_thoai = "84912345678"
        with self.assertRaises(ValidationError):
            self.unit.save()
