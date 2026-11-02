"""Khóa ký quá hạn chuyển HET_HAN khi đọc hoặc dùng khóa, không cần tác vụ định kỳ (#488)."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone

from signing import enums
from signing.models import SigningAuditLog, SigningKey, SigningSignature
from signing.services import keys as key_service

from .test_hanh_dong_ky_phase8 import KyBase

User = get_user_model()
URL_KHOA = "/api/v1/signing/khoa/"


class KhoaHetHanTests(KyBase):
    def _dat_het_han(self, key, giay=1):
        SigningKey.objects.filter(pk=key.pk).update(ngay_het_han=timezone.now() - timedelta(seconds=giay))

    def test_chuyen_het_han_ghi_nhat_ky_va_idempotent(self):
        _, key = self.khoa[self.ky1.pk]
        self._dat_het_han(key)
        self.assertEqual(key_service.chuyen_het_han(self.ky1), 1)
        key.refresh_from_db()
        self.assertEqual(key.trang_thai, enums.TrangThaiKhoa.HET_HAN)
        nhat_ky = SigningAuditLog.objects.filter(loai_doi_tuong="signing_key", ma_doi_tuong=key.pk,
                                                 hanh_dong="HET_HAN_KHOA")
        self.assertEqual(nhat_ky.count(), 1)
        self.assertEqual(key_service.chuyen_het_han(self.ky1), 0)
        self.assertEqual(nhat_ky.count(), 1)

    def test_khoa_con_han_hoac_khong_han_khong_bi_chuyen(self):
        _, key = self.khoa[self.ky1.pk]
        SigningKey.objects.filter(pk=key.pk).update(ngay_het_han=timezone.now() + timedelta(days=1))
        self.assertEqual(key_service.chuyen_het_han(self.ky1), 0)
        SigningKey.objects.filter(pk=key.pk).update(ngay_het_han=None)
        self.assertEqual(key_service.chuyen_het_han(self.ky1), 0)
        key.refresh_from_db()
        self.assertEqual(key.trang_thai, enums.TrangThaiKhoa.HOAT_DONG)

    def test_chi_chuyen_khoa_cua_chu_so_huu(self):
        _, key1 = self.khoa[self.ky1.pk]
        _, key2 = self.khoa[self.ky2.pk]
        self._dat_het_han(key1)
        self._dat_het_han(key2)
        self.assertEqual(key_service.chuyen_het_han(self.ky1), 1)
        key2.refresh_from_db()
        self.assertEqual(key2.trang_thai, enums.TrangThaiKhoa.HOAT_DONG)

    def test_ky_bang_khoa_het_han_bi_tu_choi_va_trang_thai_duoc_luu(self):
        _, key = self.khoa[self.ky1.pk]
        self._dat_het_han(key)
        r = self.ky(self.ky1)
        self.assertEqual((r.status_code, r.data["code"]), (400, "khoa_ky_khong_hoat_dong"))
        key.refresh_from_db()
        self.assertEqual(key.trang_thai, enums.TrangThaiKhoa.HET_HAN)
        self.assertFalse(SigningSignature.objects.exists())

    def test_doc_danh_sach_khoa_cap_nhat_trang_thai(self):
        _, key = self.khoa[self.ky1.pk]
        self._dat_het_han(key)
        r = self.client_cua(User.objects.get(pk=self.ky1.pk)).get(URL_KHOA)
        self.assertEqual(r.status_code, 200)
        key.refresh_from_db()
        self.assertEqual(key.trang_thai, enums.TrangThaiKhoa.HET_HAN)
