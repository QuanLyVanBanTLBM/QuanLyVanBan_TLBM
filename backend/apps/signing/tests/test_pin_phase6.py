"""
Phase 6 — bảo vệ khóa ký bằng PIN (signing-backend-plan.md mục 3.4, bảng signing_key_unlock).
"""

import base64
import os
import threading
import unittest
from datetime import timedelta

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from django.contrib.auth.models import User
from django.db import connection
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from signing import crypto, enums
from signing.errors import ConflictError, SigningError
from signing.models import SigningAuditLog, SigningKey, SigningKeyUnlock
from signing.services import keys as key_service
from signing.services import pin as pin_service

BASE = "/api/v1/signing"
KDF = {"thuat_toan": "argon2id", "m": 65536, "t": 3, "p": 1, "phien_ban": 1}


def xac_minh():
    """Verifier giả lập (32 byte, Base64) — trong thực tế do trình duyệt dẫn xuất từ PIN."""
    return base64.b64encode(os.urandom(32)).decode()


def khoa_hoat_dong(user, ma="K1", kich_hoat=True):
    private = Ed25519PrivateKey.generate()
    raw = private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    key = key_service.dang_ky(user, ma_khoa=ma, khoa_cong_khai=base64.b64encode(raw).decode(),
                              ngay_hieu_luc=timezone.now())
    chu_ky = base64.b64encode(private.sign(key_service.thach_thuc_so_huu(key).encode())).decode()
    key_service.xac_minh_so_huu(key, user, chu_ky)
    if kich_hoat:
        key_service.kich_hoat(key, user)
    key.refresh_from_db()
    return key


def hanh_dong(key):
    return list(SigningAuditLog.objects.filter(loai_doi_tuong="signing_key", ma_doi_tuong=key.pk)
                .order_by("id").values_list("hanh_dong", flat=True))


class PinBase(TestCase):
    def setUp(self):
        self.u1 = User.objects.create_user("u1", password="p")
        self.u2 = User.objects.create_user("u2", password="p")
        self.key = khoa_hoat_dong(self.u1)
        self.pin = xac_minh()
        self.unlock, self.k_srv = pin_service.dat_pin(self.key, self.u1, self.pin, KDF)

    def sai(self, lan=1):
        loi = None
        for _ in range(lan):
            with self.assertRaises(SigningError) as ctx:
                pin_service.mo_khoa_ky(self.key, self.u1, xac_minh())
            loi = ctx.exception
        self.unlock.refresh_from_db()
        return loi


class DatPinTests(PinBase):
    def test_set_pin_returns_server_share_and_stores_no_secret_in_clear(self):
        self.assertEqual(len(self.k_srv), 32)
        self.assertEqual(self.unlock.tham_so_kdf, KDF)
        self.assertEqual(self.unlock.so_lan_sai, 0)
        luu = self.unlock.ma_bam_xac_minh_pin + self.unlock.manh_bi_mat_ma_hoa
        self.assertNotIn(self.pin, luu)  # không lưu verifier dạng gốc
        self.assertNotIn(base64.b64encode(self.k_srv).decode(), luu)  # k_srv được mã hóa
        self.assertIn("DAT_PIN", hanh_dong(self.key))

    def test_cannot_set_pin_twice(self):
        with self.assertRaises(ConflictError) as ctx:
            pin_service.dat_pin(self.key, self.u1, xac_minh(), KDF)
        self.assertEqual(ctx.exception.get_codes(), "pin_da_dat")

    def test_rejects_bad_verifier_and_weak_kdf(self):
        key2 = khoa_hoat_dong(self.u2, ma="K2")
        for sai in ("khong-phai-base64", base64.b64encode(b"ngan").decode(), ""):
            with self.assertRaises(SigningError) as ctx:
                pin_service.dat_pin(key2, self.u2, sai, KDF)
            self.assertEqual(ctx.exception.get_codes(), "xac_minh_pin_khong_hop_le")
        for kdf, ma in (({**KDF, "m": 1024}, "tham_so_kdf_duoi_muc_san"),
                        ({**KDF, "t": 1}, "tham_so_kdf_duoi_muc_san"),
                        ({**KDF, "thuat_toan": "pbkdf2"}, "tham_so_kdf_khong_hop_le"),
                        ({**KDF, "muoi": "x"}, "tham_so_kdf_khong_hop_le"),
                        ({**KDF, "m": "65536"}, "tham_so_kdf_khong_hop_le")):
            with self.assertRaises(SigningError) as ctx:
                pin_service.dat_pin(key2, self.u2, xac_minh(), kdf)
            self.assertEqual(ctx.exception.get_codes(), ma)
        self.assertFalse(SigningKeyUnlock.objects.filter(khoa=key2).exists())

    def test_only_owner_and_valid_key_state(self):
        key2 = khoa_hoat_dong(self.u2, ma="K2")
        with self.assertRaises(SigningError) as ctx:
            pin_service.dat_pin(key2, self.u1, xac_minh(), KDF)
        self.assertEqual(ctx.exception.status_code, 403)
        key_service.thu_hoi(key2, self.u2, "Mất thiết bị")
        with self.assertRaises(ConflictError):
            pin_service.dat_pin(key2, self.u2, xac_minh(), KDF)

    def test_pending_key_can_set_pin(self):
        key3 = khoa_hoat_dong(self.u2, ma="K3", kich_hoat=False)
        unlock, _ = pin_service.dat_pin(key3, self.u2, xac_minh(), KDF)
        self.assertEqual(unlock.khoa_id, key3.pk)


class MoKhoaKyTests(PinBase):
    def test_correct_pin_returns_same_server_share(self):
        unlock, manh = pin_service.mo_khoa_ky(self.key, self.u1, self.pin)
        self.assertEqual(manh, self.k_srv)
        self.assertIn("MO_KHOA_KY", hanh_dong(self.key))

    def test_wrong_pin_counts_and_success_resets(self):
        loi = self.sai(3)
        self.assertEqual(loi.get_codes(), "pin_khong_dung")
        self.assertEqual(loi.fields["so_lan_con_lai"], [2])
        self.assertEqual(self.unlock.so_lan_sai, 3)
        pin_service.mo_khoa_ky(self.key, self.u1, self.pin)
        self.unlock.refresh_from_db()
        self.assertEqual(self.unlock.so_lan_sai, 0)
        self.assertEqual(hanh_dong(self.key).count("PIN_SAI"), 3)

    def test_five_wrong_locks_fifteen_minutes(self):
        loi = self.sai(5)
        self.assertEqual((loi.get_codes(), loi.status_code), ("pin_tam_khoa", 423))
        con_lai = self.unlock.khoa_den - timezone.now()
        self.assertTrue(timedelta(minutes=14) < con_lai <= timedelta(minutes=15))
        # Đang khóa: PIN đúng cũng bị chặn và không làm tăng bộ đếm
        with self.assertRaises(SigningError) as ctx:
            pin_service.mo_khoa_ky(self.key, self.u1, self.pin)
        self.assertEqual(ctx.exception.get_codes(), "pin_tam_khoa")
        self.unlock.refresh_from_db()
        self.assertEqual(self.unlock.so_lan_sai, 5)
        self.assertIn("PIN_KHOA", hanh_dong(self.key))
        # Hết thời gian khóa: PIN đúng mở được và đặt lại bộ đếm
        SigningKeyUnlock.objects.filter(pk=self.unlock.pk).update(khoa_den=timezone.now() - timedelta(seconds=1))
        _, manh = pin_service.mo_khoa_ky(self.key, self.u1, self.pin)
        self.assertEqual(manh, self.k_srv)

    def test_ten_wrong_hard_lock(self):
        self.sai(5)
        SigningKeyUnlock.objects.filter(pk=self.unlock.pk).update(khoa_den=timezone.now() - timedelta(seconds=1))
        loi = self.sai(4)
        self.assertEqual(loi.fields["so_lan_con_lai"], [1])
        loi = self.sai(1)
        self.assertEqual((loi.get_codes(), loi.status_code), ("pin_khoa_cung", 423))
        self.assertEqual(self.unlock.so_lan_sai, 10)
        with self.assertRaises(SigningError) as ctx:
            pin_service.mo_khoa_ky(self.key, self.u1, self.pin)
        self.assertEqual(ctx.exception.get_codes(), "pin_khoa_cung")
        self.assertEqual(hanh_dong(self.key).count("PIN_KHOA"), 2)

    def test_only_active_key_and_owner(self):
        with self.assertRaises(SigningError) as ctx:
            pin_service.mo_khoa_ky(self.key, self.u2, self.pin)
        self.assertEqual(ctx.exception.status_code, 403)
        key3 = khoa_hoat_dong(self.u2, ma="K3", kich_hoat=False)
        pin3 = xac_minh()
        pin_service.dat_pin(key3, self.u2, pin3, KDF)
        with self.assertRaises(ConflictError):
            pin_service.mo_khoa_ky(key3, self.u2, pin3)
        self.assertEqual(SigningKeyUnlock.objects.get(khoa=key3).so_lan_sai, 0)

    def test_pin_not_set(self):
        key2 = khoa_hoat_dong(self.u2, ma="K2")
        with self.assertRaises(ConflictError) as ctx:
            pin_service.mo_khoa_ky(key2, self.u2, xac_minh())
        self.assertEqual(ctx.exception.get_codes(), "pin_chua_dat")

    def test_database_leak_alone_cannot_verify_pin(self):
        """Bí mật máy chủ khác -> HMAC và bản mã k_srv trong CSDL không dùng được."""
        with override_settings(SIGNING_PIN_SECRET="bi-mat-khac"):
            with self.assertRaises(SigningError) as ctx:
                pin_service.mo_khoa_ky(self.key, self.u1, self.pin)
        self.assertEqual(ctx.exception.get_codes(), "pin_khong_dung")


class DoiPinTests(PinBase):
    def test_change_pin_keeps_server_share(self):
        moi = xac_minh()
        _, manh = pin_service.doi_pin(self.key, self.u1, self.pin, moi, {**KDF, "phien_ban": 2})
        self.assertEqual(manh, self.k_srv)
        self.unlock.refresh_from_db()
        self.assertEqual(self.unlock.tham_so_kdf["phien_ban"], 2)
        with self.assertRaises(SigningError):
            pin_service.mo_khoa_ky(self.key, self.u1, self.pin)  # PIN cũ hết hiệu lực
        _, manh = pin_service.mo_khoa_ky(self.key, self.u1, moi)
        self.assertEqual(manh, self.k_srv)
        self.assertIn("DOI_PIN", hanh_dong(self.key))

    def test_wrong_old_pin_counts_and_same_pin_rejected(self):
        with self.assertRaises(SigningError) as ctx:
            pin_service.doi_pin(self.key, self.u1, xac_minh(), xac_minh(), KDF)
        self.assertEqual(ctx.exception.get_codes(), "pin_khong_dung")
        self.unlock.refresh_from_db()
        self.assertEqual(self.unlock.so_lan_sai, 1)
        with self.assertRaises(SigningError) as ctx:
            pin_service.doi_pin(self.key, self.u1, self.pin, self.pin, KDF)
        self.assertEqual(ctx.exception.get_codes(), "pin_moi_trung_pin_cu")


class PinApiTests(PinBase):
    def setUp(self):
        super().setUp()
        self.c1, self.c2 = APIClient(), APIClient()
        self.c1.force_authenticate(self.u1)
        self.c2.force_authenticate(self.u2)

    def test_unlock_endpoint_and_response_content(self):
        r = self.c1.post(f"{BASE}/khoa/{self.key.pk}/mo-khoa-ky/", {"xac_minh_pin": self.pin}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r["Cache-Control"], "no-store")
        self.assertEqual(base64.b64decode(r.data["manh_bi_mat"]), self.k_srv)
        self.assertEqual(set(r.data), {"khoa", "manh_bi_mat", "tham_so_kdf"})  # không trả PIN, hash, bản bọc
        r = self.c1.get(f"{BASE}/khoa/")
        self.assertTrue(r.data[0]["da_dat_pin"])
        self.assertNotIn("ma_bam_xac_minh_pin", r.content.decode())

    def test_wrong_and_locked_responses(self):
        r = self.c1.post(f"{BASE}/khoa/{self.key.pk}/mo-khoa-ky/", {"xac_minh_pin": xac_minh()}, format="json")
        self.assertEqual((r.status_code, r.data["code"]), (400, "pin_khong_dung"))
        for _ in range(4):
            r = self.c1.post(f"{BASE}/khoa/{self.key.pk}/mo-khoa-ky/", {"xac_minh_pin": xac_minh()}, format="json")
        self.assertEqual((r.status_code, r.data["code"]), (423, "pin_tam_khoa"))

    def test_set_and_change_pin_endpoints(self):
        key2 = khoa_hoat_dong(self.u2, ma="K2")
        pin2 = xac_minh()
        r = self.c2.post(f"{BASE}/khoa/{key2.pk}/dat-pin/", {"xac_minh_pin": pin2, "tham_so_kdf": KDF}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        r = self.c2.post(f"{BASE}/khoa/{key2.pk}/doi-pin/",
                         {"xac_minh_pin_cu": pin2, "xac_minh_pin_moi": xac_minh(), "tham_so_kdf": KDF}, format="json")
        self.assertEqual(r.status_code, 200, r.content)

    def test_other_users_key_not_found(self):
        r = self.c2.post(f"{BASE}/khoa/{self.key.pk}/mo-khoa-ky/", {"xac_minh_pin": self.pin}, format="json")
        self.assertEqual(r.status_code, 404)
        self.assertEqual(APIClient().post(f"{BASE}/khoa/{self.key.pk}/mo-khoa-ky/", {}).status_code, 401)


@unittest.skipUnless(connection.vendor == "postgresql", "Cần PostgreSQL để kiểm tra khóa dòng đồng thời")
class PinConcurrencyTests(TransactionTestCase):
    def test_concurrent_wrong_attempts_counted_exactly(self):
        user = User.objects.create_user("u1", password="p")
        key = khoa_hoat_dong(user)
        pin_service.dat_pin(key, user, xac_minh(), KDF)

        def thu_sai():
            try:
                pin_service.mo_khoa_ky(key, user, xac_minh())
            except SigningError:
                pass
            finally:
                connection.close()

        luong = [threading.Thread(target=thu_sai) for _ in range(4)]
        for t in luong:
            t.start()
        for t in luong:
            t.join()
        self.assertEqual(SigningKeyUnlock.objects.get(khoa=key).so_lan_sai, 4)


class PinCryptoTests(TestCase):
    def test_server_share_bound_to_key(self):
        enc = crypto.derive_subkey(b"bi-mat", "server-share")
        token = crypto.encrypt_server_share(b"x" * 32, enc, b"signing_key:1:abc")
        self.assertEqual(crypto.decrypt_server_share(token, enc, b"signing_key:1:abc"), b"x" * 32)
        with self.assertRaises(ValueError):
            crypto.decrypt_server_share(token, enc, b"signing_key:2:abc")
        self.assertNotEqual(crypto.derive_subkey(b"bi-mat", "server-share"),
                            crypto.derive_subkey(b"bi-mat", "pin-verifier"))
