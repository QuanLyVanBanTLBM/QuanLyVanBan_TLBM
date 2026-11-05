"""Đặt lại PIN bằng email và giữ nguyên khóa ký phía máy chủ."""

import base64
import os
import re
from datetime import timedelta
from unittest import mock

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from signing import crypto, enums
from signing.errors import SigningError
from signing.models import SigningAuditLog, SigningKey, SigningKeyUnlock, SigningPinResetCode
from signing.services import keys as key_service
from signing.services import pin as pin_service
from signing.services import pin_reset

User = get_user_model()
BASE = "/api/v1/signing/dat-lai-pin"
PIN_CU = "123456"
PIN_MOI = "654321"
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
CAI_DAT_KIEM_THU = override_settings(
    SIGNING_EMAIL_BACKEND=EMAIL_BACKEND,
    SIGNING_PIN_SECRET="pin-reset-test-secret",
    SIGNING_KEY_PEPPER="pin-reset-test-pepper",
)


def ma_trong_thu():
    return re.search(r"\b(\d{6})\b", mail.outbox[-1].body).group(1)


def tao_khoa_hoat_dong(user, ma_khoa="K1"):
    """Tạo khóa test thật, đặt PIN và trả private key PKCS#8 ban đầu."""
    private_key = Ed25519PrivateKey.generate()
    public_raw = private_key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw,
    )
    key = key_service.dang_ky(
        user,
        ma_khoa=ma_khoa,
        khoa_cong_khai=base64.b64encode(public_raw).decode("ascii"),
        ngay_hieu_luc=timezone.now(),
    )
    challenge = key_service.thach_thuc_so_huu(key)
    signature = base64.b64encode(private_key.sign(challenge.encode())).decode("ascii")
    key_service.xac_minh_so_huu(key, user, challenge, signature)

    private_pkcs8 = private_key.private_bytes(
        serialization.Encoding.DER,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    tham_so_kdf = {
        "thuat_toan": pin_service.KDF_THUAT_TOAN,
        **pin_service.KDF_SAN,
        "salt": base64.b64encode(os.urandom(pin_service.KDF_SALT_BYTES)).decode("ascii"),
    }
    unlock = pin_service.dat_pin(
        key, user, PIN_CU, base64.b64encode(private_pkcs8).decode("ascii"), tham_so_kdf,
    )
    key_service.kich_hoat(key, user)
    key.refresh_from_db()
    return key, private_pkcs8, unlock


@CAI_DAT_KIEM_THU
class DatLaiPinTests(TestCase):
    def setUp(self):
        self.u1 = User.objects.create_user("u1", email="u1@example.test")
        self.key, self.private_pkcs8, self.unlock = tao_khoa_hoat_dong(self.u1)
        self.public_key = self.key.khoa_cong_khai
        self.ciphertext = self.unlock.khoa_bi_mat_ma_hoa
        self.verifier = self.unlock.ma_bam_xac_minh_pin
        mail.outbox.clear()

    def _yeu_cau_ma(self):
        pin_reset.yeu_cau_ma(self.u1)
        return ma_trong_thu()

    def _xac_nhan_that_bai_khong_doi_trang_thai(self):
        self.unlock.refresh_from_db()
        self.key.refresh_from_db()
        ban_ghi = SigningPinResetCode.objects.get()
        self.assertEqual(self.unlock.ma_bam_xac_minh_pin, self.verifier)
        self.assertEqual(self.unlock.khoa_bi_mat_ma_hoa, self.ciphertext)
        self.assertIsNone(ban_ghi.da_dung_luc)
        self.assertEqual(ban_ghi.so_lan_sai, 0)
        self.assertEqual(self.key.trang_thai, enums.TrangThaiKhoa.HOAT_DONG)
        self.assertEqual(self.key.khoa_cong_khai, self.public_key)

    def test_request_sends_code_by_email_and_stores_hash_bound_to_active_key(self):
        het_han = pin_reset.yeu_cau_ma(self.u1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["u1@example.test"])
        ma = ma_trong_thu()
        ban_ghi = SigningPinResetCode.objects.get()
        self.assertNotIn(ma, ban_ghi.ma_bam)
        self.assertEqual(ban_ghi.khoa_id, self.key.pk)
        self.assertEqual(ban_ghi.het_han, het_han)
        self.assertTrue(timedelta(minutes=9) < het_han - timezone.now() <= timedelta(minutes=10))
        self.assertTrue(SigningAuditLog.objects.filter(hanh_dong="YEU_CAU_MA_DAT_LAI_PIN").exists())

    def test_correct_code_changes_pin_and_user_can_sign_with_same_key(self):
        ma = self._yeu_cau_ma()
        khoa_id = pin_reset.xac_nhan_ma(self.u1, ma, PIN_MOI)
        self.assertEqual(khoa_id, self.key.pk)

        with self.assertRaises(SigningError) as ctx:
            pin_service.mo_khoa_ky(self.key, self.u1, PIN_CU)
        self.assertEqual(ctx.exception.get_codes(), "pin_khong_dung")
        private_after_reset = pin_service.mo_khoa_ky(self.key, self.u1, PIN_MOI)
        signature = crypto.sign_with_private_key(private_after_reset, b"document to sign")
        self.assertTrue(crypto.verify_signature(self.public_key, b"document to sign", signature))
        self.assertEqual(private_after_reset, self.private_pkcs8)

        self.key.refresh_from_db()
        self.unlock.refresh_from_db()
        code = SigningPinResetCode.objects.get()
        self.assertEqual(self.key.trang_thai, enums.TrangThaiKhoa.HOAT_DONG)
        self.assertEqual(self.key.khoa_cong_khai, self.public_key)
        self.assertEqual(self.unlock.khoa_bi_mat_ma_hoa, self.ciphertext)
        self.assertNotEqual(self.unlock.ma_bam_xac_minh_pin, self.verifier)
        self.assertIsNotNone(code.da_dung_luc)
        self.assertTrue(SigningAuditLog.objects.filter(hanh_dong="DAT_LAI_PIN_QUA_EMAIL").exists())

        with self.assertRaises(SigningError) as ctx:
            pin_reset.xac_nhan_ma(self.u1, ma, PIN_MOI)
        self.assertEqual(ctx.exception.get_codes(), "ma_het_han_hoac_khong_co")

    def test_changed_pepper_fails_without_consuming_code_or_changing_pin(self):
        ma = self._yeu_cau_ma()
        with override_settings(SIGNING_KEY_PEPPER="a-different-pepper"):
            with self.assertRaises(SigningError) as ctx:
                pin_reset.xac_nhan_ma(self.u1, ma, PIN_MOI)
        self.assertEqual((ctx.exception.get_codes(), ctx.exception.status_code), ("khoa_bi_mat_khong_doc_duoc", 409))
        self._xac_nhan_that_bai_khong_doi_trang_thai()

        # Khôi phục đúng cấu hình pepper cho phép người dùng thử lại mã còn hạn.
        self.assertEqual(pin_reset.xac_nhan_ma(self.u1, ma, PIN_MOI), self.key.pk)
        self.assertEqual(pin_service.mo_khoa_ky(self.key, self.u1, PIN_MOI), self.private_pkcs8)

    def test_corrupt_ciphertext_does_not_report_recovery_success(self):
        self.unlock.khoa_bi_mat_ma_hoa = "not-base64-ciphertext"
        self.unlock.save(update_fields=["khoa_bi_mat_ma_hoa"])
        ma = self._yeu_cau_ma()

        with self.assertRaises(SigningError) as ctx:
            pin_reset.xac_nhan_ma(self.u1, ma, PIN_MOI)

        self.assertEqual(ctx.exception.get_codes(), "khoa_bi_mat_khong_doc_duoc")
        self.unlock.refresh_from_db()
        self.key.refresh_from_db()
        code = SigningPinResetCode.objects.get()
        self.assertEqual(self.unlock.ma_bam_xac_minh_pin, self.verifier)
        self.assertEqual(self.unlock.khoa_bi_mat_ma_hoa, "not-base64-ciphertext")
        self.assertIsNone(code.da_dung_luc)
        self.assertEqual(self.key.trang_thai, enums.TrangThaiKhoa.HOAT_DONG)

    def test_decrypted_key_must_match_registered_public_key(self):
        wrong_private = Ed25519PrivateKey.generate().private_bytes(
            serialization.Encoding.DER,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
        self.unlock.khoa_bi_mat_ma_hoa = pin_service._ma_hoa_khoa(
            wrong_private, self.key, self.unlock.tham_so_kdf, pin_service._pepper_khoa_ky(),
        )
        self.unlock.save(update_fields=["khoa_bi_mat_ma_hoa"])
        ma = self._yeu_cau_ma()

        with self.assertRaises(SigningError) as ctx:
            pin_reset.xac_nhan_ma(self.u1, ma, PIN_MOI)

        self.assertEqual(ctx.exception.get_codes(), "khoa_bi_mat_khong_doc_duoc")
        self.unlock.refresh_from_db()
        self.assertEqual(self.unlock.ma_bam_xac_minh_pin, self.verifier)
        self.assertIsNone(SigningPinResetCode.objects.get().da_dung_luc)

    def test_request_requires_an_active_key_with_pin(self):
        user = User.objects.create_user("without-key", email="without-key@example.test")
        with self.assertRaises(SigningError) as ctx:
            pin_reset.yeu_cau_ma(user)
        self.assertEqual(ctx.exception.get_codes(), "pin_chua_dat")
        self.assertFalse(SigningPinResetCode.objects.exists())
        self.assertEqual(mail.outbox, [])

    def test_resend_requires_two_minutes_and_invalidates_previous_code(self):
        ma_cu = self._yeu_cau_ma()
        with self.assertRaises(SigningError) as ctx:
            pin_reset.yeu_cau_ma(self.u1)
        self.assertEqual((ctx.exception.get_codes(), ctx.exception.status_code), ("gui_ma_qua_nhanh", 429))
        self.assertEqual(len(mail.outbox), 1)

        SigningPinResetCode.objects.update(created_at=timezone.now() - timedelta(minutes=3))
        pin_reset.yeu_cau_ma(self.u1)
        ma_moi = ma_trong_thu()
        if ma_cu != ma_moi:
            with self.assertRaises(SigningError) as ctx:
                pin_reset.xac_nhan_ma(self.u1, ma_cu, PIN_MOI)
            self.assertEqual(ctx.exception.get_codes(), "ma_khong_dung")
        self.assertEqual(pin_reset.xac_nhan_ma(self.u1, ma_moi, PIN_MOI), self.key.pk)

    def test_five_wrong_codes_cancel_the_code_without_changing_pin(self):
        ma = self._yeu_cau_ma()
        sai = "000000" if ma != "000000" else "111111"
        for lan in range(4):
            with self.assertRaises(SigningError) as ctx:
                pin_reset.xac_nhan_ma(self.u1, sai, PIN_MOI)
            self.assertEqual(ctx.exception.get_codes(), "ma_khong_dung")
            self.assertEqual(ctx.exception.fields["so_lan_con_lai"], [4 - lan])
        with self.assertRaises(SigningError) as ctx:
            pin_reset.xac_nhan_ma(self.u1, sai, PIN_MOI)
        self.assertEqual(ctx.exception.get_codes(), "ma_bi_huy")
        with self.assertRaises(SigningError) as ctx:
            pin_reset.xac_nhan_ma(self.u1, ma, PIN_MOI)
        self.assertEqual(ctx.exception.get_codes(), "ma_het_han_hoac_khong_co")
        self.unlock.refresh_from_db()
        self.assertEqual(self.unlock.ma_bam_xac_minh_pin, self.verifier)

    def test_expired_code_and_bad_format(self):
        ma = self._yeu_cau_ma()
        for sai in ("12345", "abcdef", ""):
            with self.assertRaises(SigningError) as ctx:
                pin_reset.xac_nhan_ma(self.u1, sai, PIN_MOI)
            self.assertEqual(ctx.exception.get_codes(), "ma_khong_hop_le")
        self.assertEqual(SigningPinResetCode.objects.get().so_lan_sai, 0)
        SigningPinResetCode.objects.update(het_han=timezone.now() - timedelta(seconds=1))
        with self.assertRaises(SigningError) as ctx:
            pin_reset.xac_nhan_ma(self.u1, ma, PIN_MOI)
        self.assertEqual(ctx.exception.get_codes(), "ma_het_han_hoac_khong_co")

    def test_no_email_and_inactive_account_rejected(self):
        user = User.objects.create_user("no-email")
        with self.assertRaises(SigningError) as ctx:
            pin_reset.yeu_cau_ma(user)
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
        user = User.objects.create_user("u2", email="u2@example.test")
        key2, _, _ = tao_khoa_hoat_dong(user, ma_khoa="K2")
        ma_u1 = self._yeu_cau_ma()
        with self.assertRaises(SigningError) as ctx:
            pin_reset.xac_nhan_ma(user, ma_u1, PIN_MOI)
        self.assertEqual(ctx.exception.get_codes(), "ma_het_han_hoac_khong_co")
        key2.refresh_from_db()
        self.assertEqual(key2.trang_thai, enums.TrangThaiKhoa.HOAT_DONG)


@CAI_DAT_KIEM_THU
class DatLaiPinApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("u1", email="u1@example.test")
        self.key, self.private_pkcs8, _ = tao_khoa_hoat_dong(self.user)
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        mail.outbox.clear()

    def test_flow_works_without_sign_permission_and_keeps_same_key(self):
        response = self.client.post(f"{BASE}/yeu-cau/", {}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["gian_cach_giay"], 120)

        response = self.client.post(
            f"{BASE}/xac-nhan/", {"ma": ma_trong_thu(), "pin_moi": PIN_MOI}, format="json", secure=True,
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data, {"da_dat_lai_pin": True, "khoa": self.key.pk})
        self.assertEqual(response["Cache-Control"], "no-store")
        self.assertEqual(SigningKey.objects.get(pk=self.key.pk).trang_thai, enums.TrangThaiKhoa.HOAT_DONG)
        private_after_reset = pin_service.mo_khoa_ky(self.key, self.user, PIN_MOI)
        self.assertEqual(private_after_reset, self.private_pkcs8)

    def test_unreadable_key_returns_api_error_and_keeps_code_retryable(self):
        self.client.post(f"{BASE}/yeu-cau/", {}, format="json")
        ma = ma_trong_thu()
        unlock = SigningKeyUnlock.objects.get(khoa=self.key)
        verifier = unlock.ma_bam_xac_minh_pin
        data = {"ma": ma, "pin_moi": PIN_MOI}

        with override_settings(SIGNING_KEY_PEPPER="a-different-pepper"):
            response = self.client.post(f"{BASE}/xac-nhan/", data, format="json", secure=True)

        self.assertEqual((response.status_code, response.data["code"]), (409, "khoa_bi_mat_khong_doc_duoc"))
        unlock.refresh_from_db()
        self.assertEqual(unlock.ma_bam_xac_minh_pin, verifier)
        self.assertIsNone(SigningPinResetCode.objects.get().da_dung_luc)

        response = self.client.post(f"{BASE}/xac-nhan/", data, format="json", secure=True)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(pin_service.mo_khoa_ky(self.key, self.user, PIN_MOI), self.private_pkcs8)

    def test_error_codes_over_http(self):
        self.client.post(f"{BASE}/yeu-cau/", {}, format="json")
        response = self.client.post(f"{BASE}/yeu-cau/", {}, format="json")
        self.assertEqual((response.status_code, response.data["code"]), (429, "gui_ma_qua_nhanh"))

        response = self.client.post(
            f"{BASE}/xac-nhan/", {"ma": "abc", "pin_moi": PIN_MOI}, format="json", secure=True,
        )
        self.assertEqual((response.status_code, response.data["code"]), (400, "du_lieu_khong_hop_le"))
        response = self.client.post(f"{BASE}/xac-nhan/", {}, format="json", secure=True)
        self.assertEqual(response.status_code, 400)
        anonymous = APIClient()
        self.assertIn(anonymous.post(f"{BASE}/yeu-cau/", {}, format="json").status_code, (401, 403))
