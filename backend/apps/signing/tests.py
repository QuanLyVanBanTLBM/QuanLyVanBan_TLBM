"""
Kiểm thử mô hình dữ liệu phân hệ Trình ký (plan mục 5.2 – 5.3).

Chạy: python manage.py test signing
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import TestCase
from django.utils import timezone

from signing.models import (
    BangChungTrangThai,
    BatBienError,
    KhoaKyTrangThai,
    KieuKy,
    PhamVi,
    SigningAttempt,
    SigningAuditLog,
    SigningKey,
    SigningManifest,
    SigningNotification,
    SigningProcess,
    SigningProcessStep,
    SigningProcessStepSigner,
    SigningRequest,
    SigningRequestStep,
    SigningRequestStepSigner,
    SigningSignature,
    VaiTroKy,
    XacMinhTrangThai,
)

User = get_user_model()
HASH_A = "a" * 64
HASH_B = "b" * 64


class SigningModelBase(TestCase):
    def setUp(self):
        self.nguoi_tao = User.objects.create_user("nguoi_tao", password="x")
        self.nguoi_ky = User.objects.create_user("nguoi_ky", password="x")
        self.nguoi_ky_2 = User.objects.create_user("nguoi_ky_2", password="x")

        self.quy_trinh = SigningProcess.objects.create(
            ma_quy_trinh="QT-01", ten_quy_trinh="Tờ trình nội bộ", pham_vi=PhamVi.CONG_TY,
            kieu_ky_mac_dinh=KieuKy.TUAN_TU, create_by=self.nguoi_tao,
        )
        self.cap = SigningProcessStep.objects.create(quy_trinh=self.quy_trinh, cap_ky=1, ten_cap_ky="Rà soát",
                                                     thu_tu=1)
        self.trinh_ky = SigningRequest.objects.create(
            van_ban_id=1, quy_trinh=self.quy_trinh, phien_ban_quy_trinh=1, muc_do="THUONG",
            kieu_ky=KieuKy.TUAN_TU, create_by=self.nguoi_tao,
        )
        self.luot = SigningAttempt.objects.create(
            trinh_ky=self.trinh_ky, so_luot=1, vi_tri_luu_tep="05_signing/tai-lieu.pdf", ma_bam_tai_lieu=HASH_A,
            create_by=self.nguoi_tao,
        )
        self.cap_luot = SigningRequestStep.objects.create(
            luot_trinh=self.luot, buoc_quy_trinh=self.cap, cap_ky=1, ten_cap_ky="Rà soát", thu_tu=1,
        )
        self.nguoi_ky_luot = SigningRequestStepSigner.objects.create(
            buoc_ky=self.cap_luot, nguoi_ky=self.nguoi_ky, ten_nguoi_ky="Người Ký", vai_tro_ky=VaiTroKy.KY_CHINH,
        )

    def tao_khoa(self, nguoi=None, trang_thai=KhoaKyTrangThai.HOAT_DONG, ma="K1"):
        return SigningKey.objects.create(
            nguoi_so_huu=nguoi or self.nguoi_ky, ma_khoa=ma, dau_van_tay=ma.ljust(64, "0"),
            khoa_cong_khai="PUBLIC", trang_thai=trang_thai, ngay_hieu_luc=timezone.now(),
            thoi_diem_xac_minh_so_huu=timezone.now() if trang_thai == KhoaKyTrangThai.HOAT_DONG else None,
        )

    def tao_chu_ky(self, **kwargs):
        data = dict(luot_trinh=self.luot, buoc_ky=self.nguoi_ky_luot, hash_tai_lieu=HASH_A, thuat_toan="Ed25519",
                    chu_ky_so="c2lnbmF0dXJl", ngay_ky=timezone.now())
        data.update(kwargs)
        if "khoa_ky" not in data:
            data["khoa_ky"] = self.tao_khoa()
        return SigningSignature.objects.create(**data)


class DefaultsAndUniqueTests(SigningModelBase):
    def test_default_values_follow_plan(self):
        self.assertEqual(self.quy_trinh.trang_thai, "NHAP")
        self.assertEqual(self.trinh_ky.trang_thai, "NHAP")
        self.assertEqual(self.luot.trang_thai, "NHAP")
        self.assertEqual(self.cap_luot.trang_thai, "CHUA_MO")
        self.assertEqual(self.nguoi_ky_luot.trang_thai, "CHO_KY")
        self.assertTrue(self.nguoi_ky_luot.chan_ky_chinh)
        self.assertTrue(self.cap.dang_ap_dung)

    def test_unique_process_version(self):
        with self.assertRaises(IntegrityError):
            SigningProcess.objects.create(
                ma_quy_trinh="QT-01", phien_ban=1, ten_quy_trinh="Trùng", pham_vi=PhamVi.CONG_TY,
                kieu_ky_mac_dinh=KieuKy.TUAN_TU, create_by=self.nguoi_tao,
            )

    def test_unique_step_order_in_process(self):
        with self.assertRaises(IntegrityError):
            SigningProcessStep.objects.create(quy_trinh=self.quy_trinh, cap_ky=2, ten_cap_ky="Trùng", thu_tu=1)

    def test_unique_attempt_number(self):
        with self.assertRaises(IntegrityError):
            SigningAttempt.objects.create(trinh_ky=self.trinh_ky, so_luot=1, vi_tri_luu_tep="x",
                                          ma_bam_tai_lieu=HASH_B, create_by=self.nguoi_tao)

    def test_unique_signer_in_step(self):
        with self.assertRaises(IntegrityError):
            SigningRequestStepSigner.objects.create(buoc_ky=self.cap_luot, nguoi_ky=self.nguoi_ky,
                                                    ten_nguoi_ky="Trùng", vai_tro_ky=VaiTroKy.KY_NHAY)

    def test_attempt_hash_must_be_sha256(self):
        with self.assertRaises(IntegrityError):
            SigningAttempt.objects.create(trinh_ky=self.trinh_ky, so_luot=2, vi_tri_luu_tep="x",
                                          ma_bam_tai_lieu="khong-phai-sha256", create_by=self.nguoi_tao)


class BusinessConstraintTests(SigningModelBase):
    def test_config_signer_needs_exactly_one_target(self):
        with transaction.atomic(), self.assertRaises(IntegrityError):
            SigningProcessStepSigner.objects.create(buoc_quy_trinh=self.cap, thu_tu=1)
        with transaction.atomic(), self.assertRaises(IntegrityError):
            SigningProcessStepSigner.objects.create(buoc_quy_trinh=self.cap, thu_tu=1, nguoi_ky=self.nguoi_ky,
                                                    chuc_vu_id=5)
        SigningProcessStepSigner.objects.create(buoc_quy_trinh=self.cap, thu_tu=1, nguoi_ky=self.nguoi_ky)
        SigningProcessStepSigner.objects.create(buoc_quy_trinh=self.cap, thu_tu=2, chuc_vu_id=5)

    def test_delegation_requires_reason(self):
        self.nguoi_ky_luot.uy_quyen_tu = self.nguoi_ky_2
        with transaction.atomic(), self.assertRaises(IntegrityError):
            self.nguoi_ky_luot.save()
        self.nguoi_ky_luot.ly_do_uy_quyen = "Đi công tác"
        self.nguoi_ky_luot.save()

    def test_previous_attempt_must_belong_to_same_request(self):
        khac = SigningRequest.objects.create(
            van_ban_id=2, quy_trinh=self.quy_trinh, phien_ban_quy_trinh=1, muc_do="THUONG",
            kieu_ky=KieuKy.TUAN_TU, create_by=self.nguoi_tao,
        )
        luot = SigningAttempt(trinh_ky=khac, so_luot=1, vi_tri_luu_tep="x", ma_bam_tai_lieu=HASH_B,
                              create_by=self.nguoi_tao, luot_truoc=self.luot)
        with self.assertRaises(ValidationError):
            luot.full_clean()

    def test_current_signature_must_belong_to_signer(self):
        khac = SigningRequestStepSigner.objects.create(buoc_ky=self.cap_luot, nguoi_ky=self.nguoi_ky_2,
                                                       ten_nguoi_ky="Người 2", vai_tro_ky=VaiTroKy.KY_NHAY)
        chu_ky = self.tao_chu_ky(buoc_ky=khac)
        self.nguoi_ky_luot.chu_ky_hien_hanh = chu_ky
        with self.assertRaises(ValidationError):
            self.nguoi_ky_luot.full_clean()

    def test_signer_can_sign_again_after_revoke(self):
        """buoc_ky không unique: ký lại sau thu hồi tạo dòng chữ ký mới."""
        self.tao_chu_ky(khoa_ky=self.tao_khoa(ma="K-A", trang_thai=KhoaKyTrangThai.DA_XOAY_VONG))
        self.tao_chu_ky(khoa_ky=self.tao_khoa(ma="K-B", trang_thai=KhoaKyTrangThai.DA_XOAY_VONG))
        self.assertEqual(self.nguoi_ky_luot.chu_ky_set.count(), 2)


class SigningKeyTests(SigningModelBase):
    def test_only_one_active_key_per_owner(self):
        self.tao_khoa(ma="K1")
        with transaction.atomic(), self.assertRaises(IntegrityError):
            self.tao_khoa(ma="K2")
        self.tao_khoa(ma="K3", trang_thai=KhoaKyTrangThai.DA_XOAY_VONG)
        self.tao_khoa(nguoi=self.nguoi_ky_2, ma="K4")

    def test_active_key_requires_possession_proof(self):
        with self.assertRaises(IntegrityError):
            SigningKey.objects.create(
                nguoi_so_huu=self.nguoi_ky, ma_khoa="K9", dau_van_tay="9" * 64, khoa_cong_khai="PUBLIC",
                trang_thai=KhoaKyTrangThai.HOAT_DONG, ngay_hieu_luc=timezone.now(),
            )

    def test_new_key_defaults_to_pending(self):
        khoa = SigningKey.objects.create(nguoi_so_huu=self.nguoi_ky, ma_khoa="K7", dau_van_tay="7" * 64,
                                         khoa_cong_khai="PUBLIC", ngay_hieu_luc=timezone.now())
        self.assertEqual(khoa.trang_thai, "CHO_KICH_HOAT")
        self.assertEqual(khoa.thuat_toan, "Ed25519")


class ImmutabilityTests(SigningModelBase):
    def test_signature_content_cannot_change_or_be_deleted(self):
        chu_ky = self.tao_chu_ky()
        self.assertEqual(chu_ky.trang_thai_xac_minh, XacMinhTrangThai.HOP_LE)
        chu_ky.chu_ky_so = "gia-mao"
        with self.assertRaises(BatBienError):
            chu_ky.save()
        with self.assertRaises(BatBienError):
            chu_ky.delete()
        # Chỉ được cập nhật kết quả xác minh lại
        chu_ky.refresh_from_db()
        chu_ky.trang_thai_xac_minh = XacMinhTrangThai.KHONG_HOP_LE
        chu_ky.thoi_diem_xac_minh = timezone.now()
        chu_ky.save(update_fields=["trang_thai_xac_minh", "thoi_diem_xac_minh"])

    def test_audit_log_is_append_only(self):
        with transaction.atomic(), self.assertRaises(IntegrityError):
            SigningAuditLog.objects.create(loai_doi_tuong="signing_attempt", ma_doi_tuong=self.luot.id,
                                           nguoi_thuc_hien=self.nguoi_tao, hanh_dong="gui")
        # Sự kiện ngoài luồng ký (ví dụ khóa ký) không cần trinh_ky
        log = SigningAuditLog.objects.create(loai_doi_tuong="signing_key", ma_doi_tuong=1,
                                             nguoi_thuc_hien=self.nguoi_ky, hanh_dong="xoay_vong")
        log.chi_tiet = "sửa"
        with self.assertRaises(BatBienError):
            log.save()
        with self.assertRaises(BatBienError):
            log.delete()

    def test_finalized_manifest_is_locked(self):
        bang_chung = SigningManifest.objects.create(luot_trinh=self.luot, noi_dung_chuan_hoa={"v": 1},
                                                    ma_bam_bang_chung=HASH_B, create_by=self.nguoi_tao)
        bang_chung.vi_tri_luu = "cho-phep-khi-nhap"
        bang_chung.save()
        bang_chung.trang_thai = BangChungTrangThai.DA_CHOT
        bang_chung.thoi_diem_chot = timezone.now()
        bang_chung.save()
        bang_chung.vi_tri_luu = "sua-sau-khi-chot"
        with self.assertRaises(BatBienError):
            bang_chung.save()
        with self.assertRaises(BatBienError):
            bang_chung.delete()

    def test_submitted_history_is_protected_from_delete(self):
        with self.assertRaises(ProtectedError):
            self.trinh_ky.delete()
        with self.assertRaises(ProtectedError):
            self.luot.delete()


class NotificationTests(SigningModelBase):
    def test_dedupe_key_is_unique(self):
        data = dict(trinh_ky=self.trinh_ky, nguoi_nhan=self.nguoi_ky, kenh="EMAIL", loai_thong_bao="DEN_LUOT_KY",
                    khoa_chong_gui_trung="req-1:signer-1:den-luot-ky",
                    hen_gio_gui=timezone.now() + timedelta(hours=1))
        tb = SigningNotification.objects.create(**data)
        self.assertEqual((tb.trang_thai, tb.so_lan_gui_lai), ("CHO_GUI", 0))
        with self.assertRaises(IntegrityError):
            SigningNotification.objects.create(**data)
