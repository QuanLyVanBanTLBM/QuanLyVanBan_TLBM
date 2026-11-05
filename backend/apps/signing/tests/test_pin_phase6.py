"""PIN ký 6 chữ số và private key mã hóa phía máy chủ."""

import base64
import os
import threading
import unittest
from datetime import timedelta
from unittest import mock

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from signing import crypto, enums
from signing.errors import ConflictError, SigningError
from signing.models import SigningAuditLog, SigningKey, SigningKeyUnlock
from signing.services import keys as key_service
from signing.services import pin as pin_service

User = get_user_model()
BASE = "/api/v1/signing"
PIN = "123456"
PEPPER_TEST = "test-only-signing-key-pepper"


def kdf_moi():
    return {
        "thuat_toan": pin_service.KDF_THUAT_TOAN,
        **pin_service.KDF_SAN,
        "salt": base64.b64encode(os.urandom(pin_service.KDF_SALT_BYTES)).decode("ascii"),
    }


def khoa_cho(user, ma="K1"):
    private = Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    key = key_service.dang_ky(
        user,
        ma_khoa=ma,
        khoa_cong_khai=base64.b64encode(public).decode("ascii"),
        ngay_hieu_luc=timezone.now(),
    )
    challenge = key_service.thach_thuc_so_huu(key)
    proof = base64.b64encode(private.sign(challenge.encode())).decode("ascii")
    key_service.xac_minh_so_huu(key, user, challenge, proof)
    private_pkcs8 = private.private_bytes(
        serialization.Encoding.DER,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    return key, private_pkcs8


def khoa_hoat_dong(user, ma="K1", pin=PIN):
    key, private_pkcs8 = khoa_cho(user, ma)
    unlock = pin_service.dat_pin(key, user, pin, base64.b64encode(private_pkcs8).decode("ascii"), kdf_moi())
    key_service.kich_hoat(key, user)
    key.refresh_from_db()
    return key, private_pkcs8, unlock


def hanh_dong(key):
    return list(SigningAuditLog.objects.filter(loai_doi_tuong="signing_key", ma_doi_tuong=key.pk)
                .order_by("id").values_list("hanh_dong", flat=True))


@override_settings(SIGNING_PIN_SECRET="test-only-pin-secret", SIGNING_KEY_PEPPER=PEPPER_TEST)
class PinBase(TestCase):
    def setUp(self):
        self.u1 = User.objects.create_user("u1")
        self.u2 = User.objects.create_user("u2")
        self.key, self.private_pkcs8, self.unlock = khoa_hoat_dong(self.u1)
        self.pin = PIN

    def sai(self, lan=1):
        loi = None
        for _ in range(lan):
            with self.assertRaises(SigningError) as ctx:
                pin_service.mo_khoa_ky(self.key, self.u1, "999999")
            loi = ctx.exception
        self.unlock.refresh_from_db()
        return loi


class DatPinTests(PinBase):
    def test_set_pin_encrypts_matching_private_key_and_stores_no_plaintext(self):
        self.assertEqual(self.unlock.khoa_id, self.key.pk)
        self.assertEqual(len(self.unlock.ma_bam_xac_minh_pin), 64)
        self.assertEqual(self.unlock.tham_so_kdf["thuat_toan"], "argon2id")
        self.assertNotIn(base64.b64encode(self.private_pkcs8).decode("ascii"), self.unlock.khoa_bi_mat_ma_hoa)
        self.assertNotIn(self.pin, self.unlock.ma_bam_xac_minh_pin)
        self.assertIn("DAT_PIN", hanh_dong(self.key))

    def test_cannot_set_pin_twice(self):
        with self.assertRaises(ConflictError) as ctx:
            pin_service.dat_pin(
                self.key, self.u1, self.pin, base64.b64encode(self.private_pkcs8).decode("ascii"), kdf_moi(),
            )
        self.assertEqual(ctx.exception.get_codes(), "pin_da_dat")

    def test_rejects_invalid_pin_private_key_and_kdf(self):
        key, private_pkcs8 = khoa_cho(self.u2, "K2")
        encoded_private = base64.b64encode(private_pkcs8).decode("ascii")
        for invalid_pin in ("12345", "1234567", "12a456", ""):
            with self.subTest(pin=invalid_pin), self.assertRaises(SigningError) as ctx:
                pin_service.dat_pin(key, self.u2, invalid_pin, encoded_private, kdf_moi())
            self.assertEqual(ctx.exception.get_codes(), "pin_khong_hop_le")

        wrong_private = Ed25519PrivateKey.generate().private_bytes(
            serialization.Encoding.DER, serialization.PrivateFormat.PKCS8, serialization.NoEncryption(),
        )
        with self.assertRaises(SigningError) as ctx:
            pin_service.dat_pin(key, self.u2, PIN, base64.b64encode(wrong_private).decode("ascii"), kdf_moi())
        self.assertEqual(ctx.exception.get_codes(), "khoa_bi_mat_khong_hop_le")

        for bad_kdf in ({**kdf_moi(), "m": 1024}, {**kdf_moi(), "phien_ban": 1}, {"salt": "bad"}):
            with self.subTest(kdf=bad_kdf), self.assertRaises(SigningError) as ctx:
                pin_service.dat_pin(key, self.u2, PIN, encoded_private, bad_kdf)
            self.assertEqual(ctx.exception.get_codes(), "tham_so_kdf_khong_hop_le")
        self.assertFalse(SigningKeyUnlock.objects.filter(khoa=key).exists())

    def test_only_owner_can_set_pin_and_revoked_key_is_rejected(self):
        key, private_pkcs8 = khoa_cho(self.u2, "K2")
        encoded_private = base64.b64encode(private_pkcs8).decode("ascii")
        with self.assertRaises(SigningError) as ctx:
            pin_service.dat_pin(key, self.u1, PIN, encoded_private, kdf_moi())
        self.assertEqual(ctx.exception.status_code, 403)

        key_service.thu_hoi(key, self.u2, "Khóa không còn sử dụng")
        with self.assertRaises(ConflictError) as ctx:
            pin_service.dat_pin(key, self.u2, PIN, encoded_private, kdf_moi())
        self.assertEqual(ctx.exception.get_codes(), "khoa_khong_dung_trang_thai")

    def test_key_cannot_activate_before_pin_is_set(self):
        key, _ = khoa_cho(self.u2, "K2")
        with self.assertRaises(ConflictError) as ctx:
            key_service.kich_hoat(key, self.u2)
        self.assertEqual(ctx.exception.get_codes(), "pin_chua_dat")

    def test_pending_key_can_set_pin_before_activation(self):
        key, private_pkcs8 = khoa_cho(self.u2, "K2")
        unlock = pin_service.dat_pin(key, self.u2, PIN, base64.b64encode(private_pkcs8).decode("ascii"), kdf_moi())
        self.assertEqual((unlock.khoa_id, key.trang_thai), (key.pk, enums.TrangThaiKhoa.CHO_KICH_HOAT))


class MoKhoaKyTests(PinBase):
    def test_correct_pin_returns_same_private_key_only_to_service(self):
        private_pkcs8 = pin_service.mo_khoa_ky(self.key, self.u1, self.pin)
        self.assertEqual(private_pkcs8, self.private_pkcs8)
        self.assertIn("MO_KHOA_KY", hanh_dong(self.key))

    def test_wrong_pin_counts_and_success_resets_counter(self):
        loi = self.sai(3)
        self.assertEqual(loi.get_codes(), "pin_khong_dung")
        self.assertEqual(loi.fields["so_lan_con_lai"], [12])
        self.assertEqual(self.unlock.so_lan_sai, 3)
        pin_service.mo_khoa_ky(self.key, self.u1, self.pin)
        self.unlock.refresh_from_db()
        self.assertEqual(self.unlock.so_lan_sai, 0)
        self.assertEqual(hanh_dong(self.key).count("PIN_SAI"), 3)

    def test_fifteen_wrong_attempts_are_rate_limited(self):
        loi = self.sai(15)
        self.assertEqual((loi.get_codes(), loi.fields["so_lan_con_lai"]), ("pin_khong_dung", [0]))
        self.assertEqual(self.unlock.so_lan_sai, 15)
        with self.assertRaises(SigningError) as ctx:
            pin_service.mo_khoa_ky(self.key, self.u1, self.pin)
        self.assertEqual((ctx.exception.get_codes(), ctx.exception.status_code), ("pin_het_luot_trong_ngay", 429))

    def test_limit_resets_next_day(self):
        self.sai(15)
        next_day = timezone.now() + timedelta(days=1, minutes=1)
        with mock.patch.object(pin_service.timezone, "now", return_value=next_day):
            private_pkcs8 = pin_service.mo_khoa_ky(self.key, self.u1, self.pin)
        self.assertEqual(private_pkcs8, self.private_pkcs8)
        self.unlock.refresh_from_db()
        self.assertEqual(self.unlock.so_lan_sai, 0)

    def test_unreadable_ciphertext_returns_clear_error_without_counting_wrong_pin(self):
        SigningKeyUnlock.objects.filter(pk=self.unlock.pk).update(khoa_bi_mat_ma_hoa="tampered")
        with self.assertRaises(SigningError) as ctx:
            pin_service.mo_khoa_ky(self.key, self.u1, self.pin)
        self.assertEqual(ctx.exception.get_codes(), "khoa_bi_mat_khong_doc_duoc")
        self.unlock.refresh_from_db()
        self.assertEqual(self.unlock.so_lan_sai, 0)

    def test_only_owner_and_active_key_can_sign(self):
        with self.assertRaises(SigningError) as ctx:
            pin_service.mo_khoa_ky(self.key, self.u2, self.pin)
        self.assertEqual(ctx.exception.status_code, 403)

        key, private_pkcs8 = khoa_cho(self.u2, "K2")
        pin_service.dat_pin(key, self.u2, PIN, base64.b64encode(private_pkcs8).decode("ascii"), kdf_moi())
        with self.assertRaises(ConflictError) as ctx:
            pin_service.mo_khoa_ky(key, self.u2, PIN)
        self.assertEqual(ctx.exception.get_codes(), "khoa_khong_dung_trang_thai")


class DoiPinTests(PinBase):
    def test_change_pin_preserves_same_private_key(self):
        ciphertext_cu = self.unlock.khoa_bi_mat_ma_hoa
        verifier_cu = self.unlock.ma_bam_xac_minh_pin
        moi = "654321"
        unlock = pin_service.doi_pin(self.key, self.u1, self.pin, moi, kdf_moi())
        self.assertNotEqual(unlock.khoa_bi_mat_ma_hoa, ciphertext_cu)
        self.assertNotEqual(unlock.ma_bam_xac_minh_pin, verifier_cu)
        self.assertEqual(pin_service.mo_khoa_ky(self.key, self.u1, moi), self.private_pkcs8)
        with self.assertRaises(SigningError):
            pin_service.mo_khoa_ky(self.key, self.u1, self.pin)
        self.assertIn("DOI_PIN", hanh_dong(self.key))

    def test_change_pin_requires_new_salt_and_preserves_state_on_failure(self):
        ciphertext_cu = self.unlock.khoa_bi_mat_ma_hoa
        with self.assertRaises(SigningError) as ctx:
            pin_service.doi_pin(self.key, self.u1, self.pin, "654321", self.unlock.tham_so_kdf)
        self.assertEqual(ctx.exception.get_codes(), "salt_trung_salt_cu")
        self.unlock.refresh_from_db()
        self.assertEqual(self.unlock.khoa_bi_mat_ma_hoa, ciphertext_cu)
        self.assertEqual(pin_service.mo_khoa_ky(self.key, self.u1, self.pin), self.private_pkcs8)

    def test_wrong_old_pin_counts_and_new_pin_must_differ(self):
        with self.assertRaises(SigningError) as ctx:
            pin_service.doi_pin(self.key, self.u1, "999999", "654321", kdf_moi())
        self.assertEqual(ctx.exception.get_codes(), "pin_khong_dung")
        self.unlock.refresh_from_db()
        self.assertEqual(self.unlock.so_lan_sai, 1)
        with self.assertRaises(SigningError) as ctx:
            pin_service.doi_pin(self.key, self.u1, self.pin, self.pin, kdf_moi())
        self.assertEqual(ctx.exception.get_codes(), "pin_moi_trung_pin_cu")


@override_settings(SIGNING_PIN_SECRET="test-only-pin-secret", SIGNING_KEY_PEPPER=PEPPER_TEST)
class PinApiTests(PinBase):
    def setUp(self):
        super().setUp()
        from .helpers import cap_quyen

        cap_quyen(self.u1, "sign_trinhky")
        cap_quyen(self.u2, "sign_trinhky")
        self.c1, self.c2 = APIClient(), APIClient()
        self.c1.force_authenticate(self.u1)
        self.c2.force_authenticate(self.u2)

    def test_set_and_change_pin_endpoints_return_no_private_material(self):
        key, private_pkcs8 = khoa_cho(self.u2, "K2")
        private_b64 = base64.b64encode(private_pkcs8).decode("ascii")
        first_kdf = kdf_moi()
        response = self.c2.post(f"{BASE}/khoa/{key.pk}/dat-pin/", {
            "pin": PIN, "khoa_bi_mat_pkcs8": private_b64, "tham_so_kdf": first_kdf,
        }, format="json", secure=True)
        self.assertEqual((response.status_code, response.data), (201, {"khoa": key.pk, "da_dat_pin": True}))
        self.assertEqual(response["Cache-Control"], "no-store")

        key_service.kich_hoat(key, self.u2)
        response = self.c2.post(f"{BASE}/khoa/{key.pk}/doi-pin/", {
            "pin_cu": PIN, "pin_moi": "654321", "tham_so_kdf": kdf_moi(),
        }, format="json", secure=True)
        self.assertEqual((response.status_code, response.data), (200, {"khoa": key.pk, "da_dat_pin": True}))
        self.assertEqual(response["Cache-Control"], "no-store")
        self.assertNotIn("private", response.content.decode().lower())
        self.assertNotIn(private_b64, response.content.decode())
        self.assertEqual(pin_service.mo_khoa_ky(key, self.u2, "654321"), private_pkcs8)

    def test_pin_endpoints_require_permission_and_hide_other_users_keys(self):
        key, private_pkcs8 = khoa_cho(self.u2, "K2")
        u3 = User.objects.create_user("u3")
        client = APIClient()
        client.force_authenticate(u3)
        response = client.post(f"{BASE}/khoa/{key.pk}/dat-pin/", {
            "pin": PIN, "khoa_bi_mat_pkcs8": base64.b64encode(private_pkcs8).decode("ascii"),
            "tham_so_kdf": kdf_moi(),
        }, format="json", secure=True)
        self.assertEqual((response.status_code, response.data["code"]), (403, "khong_co_quyen"))

        response = self.c1.post(f"{BASE}/khoa/{key.pk}/dat-pin/", {}, format="json", secure=True)
        self.assertEqual(response.status_code, 404)

    @override_settings(DEBUG=False, SIGNING_KEY_PEPPER="")
    def test_production_without_pepper_returns_503_without_storing_pin(self):
        key, private_pkcs8 = khoa_cho(self.u2, "K2")
        with self.assertLogs("signing.services.pin", level="ERROR"):
            response = self.c2.post(f"{BASE}/khoa/{key.pk}/dat-pin/", {
                "pin": PIN, "khoa_bi_mat_pkcs8": base64.b64encode(private_pkcs8).decode("ascii"),
                "tham_so_kdf": kdf_moi(),
            }, format="json", secure=True)
        self.assertEqual((response.status_code, response.data["code"]), (503, "chua_cau_hinh_pepper_khoa_ky"))
        self.assertFalse(SigningKeyUnlock.objects.filter(khoa=key).exists())


@unittest.skipUnless(connection.vendor == "postgresql", "Cần PostgreSQL để kiểm tra khóa dòng đồng thời")
@override_settings(SIGNING_PIN_SECRET="test-only-pin-secret", SIGNING_KEY_PEPPER=PEPPER_TEST)
class PinConcurrencyTests(TransactionTestCase):
    def test_concurrent_wrong_attempts_are_counted_exactly(self):
        user = User.objects.create_user("u1")
        key, _, _ = khoa_hoat_dong(user)

        def thu_sai():
            try:
                pin_service.mo_khoa_ky(key, user, "999999")
            except SigningError:
                pass
            finally:
                connection.close()

        threads = [threading.Thread(target=thu_sai) for _ in range(4)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(SigningKeyUnlock.objects.get(khoa=key).so_lan_sai, 4)


class PinCryptoTests(TestCase):
    def test_private_key_ciphertext_is_bound_to_key_and_pepper(self):
        pepper = b"pepper-a"
        salt = os.urandom(16)
        aes_key = crypto.derive_signing_key_encryption_key(pepper, salt)
        aad = b"tlbm-signing-private-key-v1:1:fingerprint"
        token = crypto.encrypt_signing_private_key(b"private-key", aes_key, aad)
        self.assertEqual(crypto.decrypt_signing_private_key(token, aes_key, aad), b"private-key")

        with self.assertRaises(ValueError):
            crypto.decrypt_signing_private_key(token, aes_key, aad + b"-other-key")
        wrong_key = crypto.derive_signing_key_encryption_key(b"pepper-b", salt)
        with self.assertRaises(ValueError):
            crypto.decrypt_signing_private_key(token, wrong_key, aad)
