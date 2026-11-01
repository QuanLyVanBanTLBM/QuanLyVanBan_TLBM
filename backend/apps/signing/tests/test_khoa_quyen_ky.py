"""Khóa tạm thời quyền ký của tài khoản do quản trị viên đặt (issue #449, phân vùng 3 của #447)."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.utils import timezone

from signing.errors import ConflictError, SigningError
from signing.models import SigningAuditLog, SigningRightLock
from signing.services import quyen_ky

from .helpers import cap_quyen
from .test_hanh_dong_ky_phase8 import KyBase

User = get_user_model()


class KhoaQuyenKyDichVuTests(KyBase):
    def setUp(self):
        super().setUp()
        self.quan_tri = User.objects.create_user("quan_tri")
        cap_quyen(self.quan_tri, "manage_signing_process")

    def khoa_quyen(self, nguoi=None, thoi_han="8_gio", ly_do="Nghi ngờ lộ thông tin ký"):
        return quyen_ky.khoa_quyen((nguoi or self.ky1).pk, self.quan_tri, ly_do=ly_do, thoi_han=thoi_han)

    def test_lock_sets_expiry_and_writes_audit(self):
        khoa = self.khoa_quyen(thoi_han="8_gio")
        self.assertAlmostEqual((khoa.khoa_den - khoa.khoa_tu).total_seconds(), 8 * 3600, delta=1)
        nhat_ky = SigningAuditLog.objects.get(hanh_dong="KHOA_QUYEN_KY")
        self.assertEqual((nhat_ky.nguoi_thuc_hien_id, nhat_ky.ma_doi_tuong, nhat_ky.chi_tiet),
                         (self.quan_tri.pk, khoa.pk, "Nghi ngờ lộ thông tin ký"))
        self.assertEqual(nhat_ky.du_lieu_kem_theo["nguoi_bi_khoa_id"], self.ky1.pk)

    def test_lock_until_unlocked_has_no_expiry(self):
        self.assertIsNone(self.khoa_quyen(thoi_han=quyen_ky.DEN_KHI_BAT_LAI).khoa_den)

    def test_invalid_duration_and_missing_reason_rejected(self):
        with self.assertRaises(SigningError) as ctx:
            self.khoa_quyen(thoi_han="2_gio")
        self.assertEqual(ctx.exception.get_codes(), "thoi_han_khoa_khong_hop_le")
        with self.assertRaises(SigningError) as ctx:
            self.khoa_quyen(ly_do="   ")
        self.assertEqual(ctx.exception.get_codes(), "thieu_ly_do_khoa_quyen_ky")
        self.assertFalse(SigningRightLock.objects.exists())

    def test_only_admin_can_lock_and_not_self(self):
        with self.assertRaises(SigningError) as ctx:
            quyen_ky.khoa_quyen(self.ky2.pk, self.ky1, ly_do="x", thoi_han="1_gio")
        self.assertEqual(ctx.exception.status_code, 403)
        with self.assertRaises(SigningError) as ctx:
            quyen_ky.khoa_quyen(self.quan_tri.pk, self.quan_tri, ly_do="x", thoi_han="1_gio")
        self.assertEqual(ctx.exception.get_codes(), "khong_the_khoa_chinh_minh")

    def test_double_lock_conflicts_until_expired(self):
        khoa = self.khoa_quyen()
        with self.assertRaises(ConflictError):
            self.khoa_quyen()
        SigningRightLock.objects.filter(pk=khoa.pk).update(
            khoa_tu=timezone.now() - timedelta(hours=9), khoa_den=timezone.now() - timedelta(hours=1))
        moi = self.khoa_quyen()
        khoa.refresh_from_db()
        self.assertEqual(khoa.bat_lai_luc, khoa.khoa_den)  # hết hạn tự nhiên, không có người bật lại
        self.assertIsNone(khoa.nguoi_bat_lai_id)
        self.assertIsNone(moi.bat_lai_luc)

    def test_signing_blocked_while_locked_and_allowed_after_unlock(self):
        self.khoa_quyen(thoi_han=quyen_ky.DEN_KHI_BAT_LAI)
        r = self.ky(self.ky1)
        self.assertEqual((r.status_code, r.data["code"]), (403, "quyen_ky_bi_khoa"))
        quyen_ky.bat_lai_quyen(self.ky1.pk, self.quan_tri, ly_do="Đã xác minh danh tính")
        r = self.ky(self.ky1)
        self.assertEqual(r.status_code, 200, r.data)

    def test_expired_lock_does_not_block_signing(self):
        khoa = self.khoa_quyen(thoi_han="1_gio")
        SigningRightLock.objects.filter(pk=khoa.pk).update(
            khoa_tu=timezone.now() - timedelta(hours=2), khoa_den=timezone.now() - timedelta(hours=1))
        self.assertIsNone(quyen_ky.khoa_dang_hieu_luc(self.ky1))
        self.assertEqual(self.ky(self.ky1).status_code, 200)

    def test_unlock_requires_reason_admin_and_active_lock(self):
        with self.assertRaises(ConflictError):
            quyen_ky.bat_lai_quyen(self.ky1.pk, self.quan_tri, ly_do="Đã xử lý")
        self.khoa_quyen()
        with self.assertRaises(SigningError) as ctx:
            quyen_ky.bat_lai_quyen(self.ky1.pk, self.quan_tri, ly_do=" ")
        self.assertEqual(ctx.exception.get_codes(), "thieu_ly_do_bat_lai_quyen_ky")
        with self.assertRaises(SigningError) as ctx:
            quyen_ky.bat_lai_quyen(self.ky1.pk, self.ky2, ly_do="Đã xử lý")
        self.assertEqual(ctx.exception.status_code, 403)
        khoa = quyen_ky.bat_lai_quyen(self.ky1.pk, self.quan_tri, ly_do="Đã xử lý")
        self.assertEqual((khoa.nguoi_bat_lai_id, khoa.ly_do_bat_lai), (self.quan_tri.pk, "Đã xử lý"))
        self.assertIsNone(quyen_ky.khoa_dang_hieu_luc(self.ky1))
        self.assertTrue(SigningAuditLog.objects.filter(hanh_dong="BAT_LAI_QUYEN_KY", chi_tiet="Đã xử lý").exists())

    def test_can_lock_again_after_unlock(self):
        self.khoa_quyen()
        quyen_ky.bat_lai_quyen(self.ky1.pk, self.quan_tri, ly_do="Đã xử lý")
        self.khoa_quyen()
        self.assertEqual(SigningRightLock.objects.filter(nguoi_bi_khoa=self.ky1).count(), 2)

    def test_database_rejects_second_open_lock_and_blank_reason(self):
        self.khoa_quyen()
        with self.assertRaises(IntegrityError), transaction.atomic():
            SigningRightLock.objects.create(nguoi_bi_khoa=self.ky1, nguoi_khoa=self.quan_tri, ly_do_khoa="x")
        with self.assertRaises(IntegrityError), transaction.atomic():
            SigningRightLock.objects.create(nguoi_bi_khoa=self.ky2, nguoi_khoa=self.quan_tri, ly_do_khoa="  ")
