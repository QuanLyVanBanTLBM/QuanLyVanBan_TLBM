"""Đặt lại PIN bằng mã xác thực gửi qua email (issue #478, phân vùng 1 của #447)."""

import re
from datetime import timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from signing import enums
from signing.errors import SigningError
from signing.models import SigningAuditLog, SigningKey, SigningPinResetCode
from signing.services import pin_reset

from .test_hanh_dong_ky_phase8 import khoa_hoat_dong as khoa_hoat_dong_moi
from .test_pin_phase6 import BI_MAT_KIEM_THU, khoa_hoat_dong

User = get_user_model()
BASE = "/api/v1/signing/dat-lai-pin"
EMAIL_KIEM_THU = override_settings(SIGNING_EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")


def ma_trong_thu():
    return re.search(r"\b(\d{6})\b", mail.outbox[-1].body).group(1)


@BI_MAT_KIEM_THU
@EMAIL_KIEM_THU
class DatLaiPinTests(TestCase):
    def setUp(self):
        self.u1 = User.objects.create_user("u1", email="u1@example.test")
        self.key = khoa_hoat_dong(self.u1)
        mail.outbox.clear()

    def sai(self, lan=1):
        loi = None
        for _ in range(lan):
            with self.assertRaises(SigningError) as ctx:
                pin_reset.xac_nhan_ma(self.u1, "000000" if ma_trong_thu() != "000000" else "111111")
            loi = ctx.exception
        return loi

    def test_request_sends_code_by_email_and_stores_only_hash(self):
        het_han = pin_reset.yeu_cau_ma(self.u1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["u1@example.test"])
        ma = ma_trong_thu()
        ban_ghi = SigningPinResetCode.objects.get()
        self.assertNotIn(ma, ban_ghi.ma_bam)
        self.assertEqual(ban_ghi.het_han, het_han)
        self.assertTrue(timedelta(minutes=9) < het_han - timezone.now() <= timedelta(minutes=10))
        self.assertTrue(SigningAuditLog.objects.filter(hanh_dong="YEU_CAU_MA_DAT_LAI_PIN").exists())

    def test_correct_code_revokes_current_key_and_is_single_use(self):
        pin_reset.yeu_cau_ma(self.u1)
        ma = ma_trong_thu()
        self.assertEqual(pin_reset.xac_nhan_ma(self.u1, ma), 1)
        self.key.refresh_from_db()
        self.assertEqual(self.key.trang_thai, enums.TrangThaiKhoa.THU_HOI)
        self.assertIsNotNone(self.key.ngay_thu_hoi)
        self.assertEqual(SigningAuditLog.objects.filter(hanh_dong="DAT_LAI_PIN_THU_HOI_KHOA").count(), 1)
        with self.assertRaises(SigningError) as ctx:
            pin_reset.xac_nhan_ma(self.u1, ma)
        self.assertEqual(ctx.exception.get_codes(), "ma_het_han_hoac_khong_co")

    def test_after_reset_user_can_register_and_activate_a_new_key(self):
        """Nối bước đặt lại PIN (thu hồi khóa hiện tại) với bước tạo khóa mới (#487)."""
        from signing.services import keys as key_service

        pin_reset.yeu_cau_ma(self.u1)
        pin_reset.xac_nhan_ma(self.u1, ma_trong_thu())
        self.key.refresh_from_db()
        self.assertEqual(self.key.trang_thai, enums.TrangThaiKhoa.THU_HOI)
        # Không còn khóa hoạt động nên kích hoạt khóa mới không vướng `da_co_khoa_hoat_dong`
        _, khoa_moi = khoa_hoat_dong_moi(self.u1, "K-MOI-1")
        self.assertEqual(khoa_moi.trang_thai, enums.TrangThaiKhoa.HOAT_DONG)
        self.assertEqual(
            SigningKey.objects.filter(nguoi_so_huu=self.u1, trang_thai=enums.TrangThaiKhoa.HOAT_DONG).count(), 1)
        with self.assertRaises(SigningError) as ctx:  # khóa đã thu hồi không kích hoạt lại được khi đã có khóa mới
            key_service.kich_hoat(self.key, self.u1)
        self.assertEqual(ctx.exception.get_codes(), "da_co_khoa_hoat_dong")

    def test_account_without_keys_still_confirms(self):
        u2 = User.objects.create_user("u2", email="u2@example.test")
        pin_reset.yeu_cau_ma(u2)
        self.assertEqual(pin_reset.xac_nhan_ma(u2, ma_trong_thu()), 0)

    def test_resend_requires_two_minutes_and_invalidates_previous_code(self):
        pin_reset.yeu_cau_ma(self.u1)
        ma_cu = ma_trong_thu()
        with self.assertRaises(SigningError) as ctx:
            pin_reset.yeu_cau_ma(self.u1)
        self.assertEqual((ctx.exception.get_codes(), ctx.exception.status_code), ("gui_ma_qua_nhanh", 429))
        self.assertEqual(len(mail.outbox), 1)
        SigningPinResetCode.objects.update(created_at=timezone.now() - timedelta(minutes=3))
        pin_reset.yeu_cau_ma(self.u1)
        ma_moi = ma_trong_thu()
        if ma_cu != ma_moi:  # hai mã trùng nhau với xác suất 1 phần triệu
            with self.assertRaises(SigningError) as ctx:
                pin_reset.xac_nhan_ma(self.u1, ma_cu)
            self.assertEqual(ctx.exception.get_codes(), "ma_khong_dung")
        self.assertEqual(pin_reset.xac_nhan_ma(self.u1, ma_moi), 1)

    def test_five_wrong_codes_cancel_the_code(self):
        pin_reset.yeu_cau_ma(self.u1)
        ma = ma_trong_thu()
        sai = "000000" if ma != "000000" else "111111"
        for lan in range(4):
            with self.assertRaises(SigningError) as ctx:
                pin_reset.xac_nhan_ma(self.u1, sai)
            self.assertEqual(ctx.exception.get_codes(), "ma_khong_dung")
            self.assertEqual(ctx.exception.fields["so_lan_con_lai"], [4 - lan])
        with self.assertRaises(SigningError) as ctx:
            pin_reset.xac_nhan_ma(self.u1, sai)
        self.assertEqual(ctx.exception.get_codes(), "ma_bi_huy")
        with self.assertRaises(SigningError) as ctx:  # mã đúng cũng không dùng được sau khi bị hủy
            pin_reset.xac_nhan_ma(self.u1, ma)
        self.assertEqual(ctx.exception.get_codes(), "ma_het_han_hoac_khong_co")
        self.key.refresh_from_db()
        self.assertEqual(self.key.trang_thai, enums.TrangThaiKhoa.HOAT_DONG)

    def test_expired_code_and_bad_format(self):
        pin_reset.yeu_cau_ma(self.u1)
        ma = ma_trong_thu()
        for sai in ("12345", "abcdef", ""):
            with self.assertRaises(SigningError) as ctx:
                pin_reset.xac_nhan_ma(self.u1, sai)
            self.assertEqual(ctx.exception.get_codes(), "ma_khong_hop_le")
        self.assertEqual(SigningPinResetCode.objects.get().so_lan_sai, 0)
        SigningPinResetCode.objects.update(het_han=timezone.now() - timedelta(seconds=1))
        with self.assertRaises(SigningError) as ctx:
            pin_reset.xac_nhan_ma(self.u1, ma)
        self.assertEqual(ctx.exception.get_codes(), "ma_het_han_hoac_khong_co")

    def test_no_email_and_inactive_account_rejected(self):
        u2 = User.objects.create_user("u2")
        with self.assertRaises(SigningError) as ctx:
            pin_reset.yeu_cau_ma(u2)
        self.assertEqual((ctx.exception.get_codes(), ctx.exception.status_code), ("tai_khoan_chua_co_email", 400))
        self.u1.is_active = False
        self.u1.save(update_fields=["is_active"])
        with self.assertRaises(SigningError) as ctx:
            pin_reset.yeu_cau_ma(self.u1)
        self.assertEqual(ctx.exception.get_codes(), "tai_khoan_khong_hoat_dong")
        self.assertFalse(SigningPinResetCode.objects.exists())

    def test_email_failure_rolls_back_so_user_can_retry_immediately(self):
        with mock.patch.object(pin_reset, "_gui_email", side_effect=OSError("smtp")):
            with self.assertRaises(SigningError) as ctx:
                pin_reset.yeu_cau_ma(self.u1)
        self.assertEqual((ctx.exception.get_codes(), ctx.exception.status_code), ("gui_email_that_bai", 503))
        self.assertFalse(SigningPinResetCode.objects.exists())
        pin_reset.yeu_cau_ma(self.u1)
        self.assertEqual(len(mail.outbox), 1)

    def test_codes_are_per_account(self):
        u2 = User.objects.create_user("u2", email="u2@example.test")
        key2 = khoa_hoat_dong(u2, ma="K2")
        pin_reset.yeu_cau_ma(self.u1)
        ma_u1 = ma_trong_thu()
        with self.assertRaises(SigningError):
            pin_reset.xac_nhan_ma(u2, ma_u1)
        key2.refresh_from_db()
        self.assertEqual(key2.trang_thai, enums.TrangThaiKhoa.HOAT_DONG)


@BI_MAT_KIEM_THU
@EMAIL_KIEM_THU
class DatLaiPinApiTests(TestCase):
    def setUp(self):
        self.u1 = User.objects.create_user("u1", email="u1@example.test")  # không cấp quyền ký
        self.key = khoa_hoat_dong(self.u1)
        self.client = APIClient()
        self.client.force_authenticate(self.u1)
        mail.outbox.clear()

    def test_flow_works_without_sign_permission(self):
        r = self.client.post(f"{BASE}/yeu-cau/", {}, format="json")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data["gian_cach_giay"], 120)
        r = self.client.post(f"{BASE}/xac-nhan/", {"ma": ma_trong_thu()}, format="json")
        self.assertEqual((r.status_code, r.data), (200, {"so_khoa_thu_hoi": 1}))
        self.assertEqual(SigningKey.objects.get(pk=self.key.pk).trang_thai, enums.TrangThaiKhoa.THU_HOI)

    def test_error_codes_over_http(self):
        self.client.post(f"{BASE}/yeu-cau/", {}, format="json")
        r = self.client.post(f"{BASE}/yeu-cau/", {}, format="json")
        self.assertEqual((r.status_code, r.data["code"]), (429, "gui_ma_qua_nhanh"))
        r = self.client.post(f"{BASE}/xac-nhan/", {"ma": "abc"}, format="json")
        self.assertEqual((r.status_code, r.data["code"]), (400, "ma_khong_hop_le"))
        r = self.client.post(f"{BASE}/xac-nhan/", {}, format="json")
        self.assertEqual(r.status_code, 400)
        anonymous = APIClient()
        self.assertIn(anonymous.post(f"{BASE}/yeu-cau/", {}, format="json").status_code, (401, 403))
