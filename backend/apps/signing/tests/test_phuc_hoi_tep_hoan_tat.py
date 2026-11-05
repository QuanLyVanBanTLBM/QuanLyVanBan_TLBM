"""Phân loại lỗi dựng PDF hoàn tất và phục hồi lượt kẹt (#497, phân vùng 4 của #447)."""

import os
from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.test import override_settings
from django.utils import timezone

from signing.models import SigningAttempt, SigningAuditLog
from signing.services import tep_hoan_tat

from .test_hoan_tat_phase10 import BASE, PHONG_TEST, HoanTatBase

PHONG_KHONG_CO = os.path.join(os.path.dirname(PHONG_TEST), "khong-co.ttf")


class PhanLoaiLoiTests(HoanTatBase):
    def test_classification_of_error_codes(self):
        for ma in ("tep_goc_khong_khop", "anh_chu_ky_khong_khop", "tep_goc_bi_ma_hoa", "chua_co_bang_chung"):
            self.assertTrue(tep_hoan_tat.la_loi_vinh_vien(ma), ma)
        for ma in ("thieu_phong_chu", "loi_luu_tep", "tep_goc_khong_doc_duoc", "anh_chu_ky_khong_doc_duoc",
                   "loi_khong_xac_dinh", ""):
            self.assertFalse(tep_hoan_tat.la_loi_vinh_vien(ma), ma)

    def test_permanent_error_is_flagged_in_audit_and_manual_retry_refused(self):
        luot = SigningAttempt.objects.get(trinh_ky_id=self.pk)
        from signing.storage import get_storage

        with open(get_storage()._resolve(luot.vi_tri_luu_tep), "ab") as f:
            f.write(b"% bi sua\n")
        luot = self.ky_het()
        self.assertEqual(luot.loi_tep_hoan_tat, "tep_goc_khong_khop")
        nhat_ky = SigningAuditLog.objects.get(luot_trinh=luot, hanh_dong="LOI_TAO_TEP_HOAN_TAT")
        self.assertEqual(nhat_ky.du_lieu_kem_theo, {"loi": "tep_goc_khong_khop", "vinh_vien": True})
        r = self.tao_lai(self.tao)
        self.assertEqual((r.status_code, r.data["code"]), (409, "loi_tep_vinh_vien"))
        self.assertEqual(SigningAttempt.objects.get(pk=luot.pk).loi_tep_hoan_tat, "tep_goc_khong_khop")

    @override_settings(SIGNING_PDF_FONT=PHONG_KHONG_CO)
    def test_temporary_error_is_flagged_and_manual_retry_still_allowed(self):
        luot = self.ky_het()
        nhat_ky = SigningAuditLog.objects.get(luot_trinh=luot, hanh_dong="LOI_TAO_TEP_HOAN_TAT")
        self.assertEqual(nhat_ky.du_lieu_kem_theo, {"loi": "thieu_phong_chu", "vinh_vien": False})
        with override_settings(SIGNING_PDF_FONT=PHONG_TEST):
            self.assertEqual(self.tao_lai(self.tao).status_code, 200)


class PhucHoiTests(HoanTatBase):
    def _luot_loi_tam(self):
        with override_settings(SIGNING_PDF_FONT=PHONG_KHONG_CO):
            luot = self.ky_het()
        self.assertEqual((luot.trang_thai_tep_hoan_tat, luot.loi_tep_hoan_tat), ("LOI", "thieu_phong_chu"))
        return luot

    def test_candidates_cover_stale_processing_and_temporary_errors_only(self):
        luot = self._luot_loi_tam()
        self.assertEqual([x.pk for x in tep_hoan_tat.luot_can_phuc_hoi()], [luot.pk])
        SigningAttempt.objects.filter(pk=luot.pk).update(loi_tep_hoan_tat="tep_goc_khong_khop")
        self.assertEqual(tep_hoan_tat.luot_can_phuc_hoi(), [])  # lỗi vĩnh viễn: bỏ qua
        SigningAttempt.objects.filter(pk=luot.pk).update(
            trang_thai_tep_hoan_tat="DANG_XU_LY", loi_tep_hoan_tat="", update_at=timezone.now())
        self.assertEqual(tep_hoan_tat.luot_can_phuc_hoi(), [])  # đang xử lý, chưa quá hạn
        SigningAttempt.objects.filter(pk=luot.pk).update(update_at=timezone.now() - timedelta(minutes=11))
        self.assertEqual([x.pk for x in tep_hoan_tat.luot_can_phuc_hoi()], [luot.pk])

    def test_recovery_rebuilds_file_after_temporary_error_and_audits(self):
        luot = self._luot_loi_tam()
        with override_settings(SIGNING_PDF_FONT=PHONG_TEST):
            ket_qua = tep_hoan_tat.phuc_hoi_tep_hoan_tat()
        self.assertEqual(ket_qua, [(luot.pk, "LOI", "THANH_CONG")])
        luot.refresh_from_db()
        self.assertEqual((luot.trang_thai_tep_hoan_tat, luot.loi_tep_hoan_tat), ("THANH_CONG", ""))
        self.assertTrue(luot.ma_bam_tep_hoan_tat)
        nhat_ky = SigningAuditLog.objects.get(luot_trinh=luot, hanh_dong="PHUC_HOI_TEP_HOAN_TAT")
        self.assertEqual(nhat_ky.nguoi_thuc_hien_id, self.ky3.pk)  # người ký cuối
        self.assertEqual(self.c.get(f"{BASE}/{self.pk}/tep-hoan-tat/").status_code, 200)
        with override_settings(SIGNING_PDF_FONT=PHONG_TEST):
            self.assertEqual(tep_hoan_tat.phuc_hoi_tep_hoan_tat(), [])  # idempotent

    def test_recovery_unsticks_stale_processing(self):
        luot = self.ky_het()
        SigningAttempt.objects.filter(pk=luot.pk).update(
            trang_thai_tep_hoan_tat="DANG_XU_LY", ma_bam_tep_hoan_tat="", vi_tri_tep_hoan_tat="",
            update_at=timezone.now() - timedelta(minutes=30))
        with override_settings(SIGNING_PDF_FONT=PHONG_TEST):
            ket_qua = tep_hoan_tat.phuc_hoi_tep_hoan_tat()
        self.assertEqual(ket_qua, [(luot.pk, "DANG_XU_LY", "THANH_CONG")])

    def test_command_lists_by_default_and_runs_with_flag(self):
        luot = self._luot_loi_tam()
        ra = StringIO()
        call_command("phuc_hoi_tep_hoan_tat", stdout=ra)
        self.assertIn(f"Cần phục hồi: lượt {luot.pk}", ra.getvalue())
        self.assertIn("Tổng 1 lượt cần phục hồi.", ra.getvalue())
        self.assertEqual(SigningAttempt.objects.get(pk=luot.pk).trang_thai_tep_hoan_tat, "LOI")  # chưa đổi gì
        ra = StringIO()
        with override_settings(SIGNING_PDF_FONT=PHONG_TEST):
            call_command("phuc_hoi_tep_hoan_tat", "--chay", stdout=ra)
        self.assertIn(f"Lượt {luot.pk}: LOI -> THANH_CONG", ra.getvalue())
        self.assertEqual(SigningAttempt.objects.get(pk=luot.pk).trang_thai_tep_hoan_tat, "THANH_CONG")
