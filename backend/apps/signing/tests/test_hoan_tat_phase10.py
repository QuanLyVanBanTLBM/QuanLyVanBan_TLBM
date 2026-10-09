"""
Lõi Phase 10 (#80 mục D): chốt bằng chứng khi cấp cuối ký đủ, sinh tệp PDF hoàn tất (bản duyệt nội bộ, chưa
phát hành), trạng thái đang xử lý/lỗi/thành công, thử lại không cần ký lại, tải tệp và xác minh có kiểm quyền.
"""

import io
import json
import os
from datetime import timedelta

import reportlab
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone
from pypdf import PdfReader

from signing import crypto
from signing.models import SigningAttempt, SigningAuditLog, SigningManifest, SigningSignature
from signing.services.bang_chung import ma_hoa_chuan
from signing.storage import get_storage

from .helpers import cap_quyen
from .test_hanh_dong_ky_phase8 import HASH, KyBase
from .test_trinh_ky_phase7 import BASE, PDF, tep_pdf

User = get_user_model()
# Phông có sẵn trong reportlab để test không phụ thuộc phông hệ thống (không đủ dấu, chỉ dùng cho test)
PHONG_TEST = os.path.join(os.path.dirname(reportlab.__file__), "fonts", "Vera.ttf")


@override_settings(SIGNING_PDF_FONT=PHONG_TEST)
class HoanTatBase(KyBase):
    def ky_het(self):
        self.ky(self.ky1)
        self.ky(self.ky2)
        with self.captureOnCommitCallbacks(execute=True):
            r = self.ky(self.ky3)
        self.assertEqual(r.status_code, 200, r.data)
        return SigningAttempt.objects.get(trinh_ky_id=self.pk)

    def chi_tiet(self, client=None):
        return (client or self.c).get(f"{BASE}/{self.pk}/").data["luot_trinh"][0]

    def tao_lai(self, user):
        return self.client_cua(User.objects.get(pk=user.pk)).post(f"{BASE}/{self.pk}/tao-lai-tep-hoan-tat/")


class TepHoanTatTests(HoanTatBase):
    def test_completion_locks_manifest_and_builds_internal_approval_pdf(self):
        luot = self.ky_het()
        self.assertEqual((luot.trang_thai, luot.trang_thai_tep_hoan_tat), ("HOAN_THANH", "THANH_CONG"))
        manifest = SigningManifest.objects.get(luot_trinh=luot)
        self.assertEqual(manifest.trang_thai, "DA_CHOT")
        self.assertEqual(crypto.sha256_hex(ma_hoa_chuan(manifest.noi_dung_chuan_hoa)), manifest.ma_bam_bang_chung)
        noi_dung = manifest.noi_dung_chuan_hoa
        self.assertEqual(noi_dung["luot_trinh"]["ma_bam_tai_lieu"], HASH)
        self.assertEqual(noi_dung["ho_so"]["van_ban"], {"so_hieu": "10/QD", "trich_yeu": "Mua sắm"})
        chu_ky = [n["chu_ky"] for c in noi_dung["cap_ky"] for n in c["nguoi_ky"]]
        self.assertEqual(len(chu_ky), 3)
        self.assertEqual({c["id"] for c in chu_ky}, set(SigningSignature.objects.values_list("id", flat=True)))

        d = self.chi_tiet()
        self.assertEqual((d["trang_thai_tep_hoan_tat"], d["ma_bam_bang_chung"]),
                         ("THANH_CONG", manifest.ma_bam_bang_chung))
        r = self.c.get(f"{BASE}/{self.pk}/tep-hoan-tat/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual((r["Cache-Control"], r["Content-Type"]), ("no-store", "application/pdf"))
        self.assertEqual(crypto.sha256_hex(r.content), luot.ma_bam_tep_hoan_tat)
        pdf = PdfReader(io.BytesIO(r.content))
        self.assertGreaterEqual(len(pdf.pages), len(PdfReader(io.BytesIO(PDF)).pages) + 1)  # gốc + trang phê duyệt
        dinh_kem = pdf.attachments[f"bang-chung-{luot.pk}.json"][0]
        self.assertEqual(json.loads(dinh_kem), noi_dung)
        self.assertEqual(pdf.metadata["/Subject"], noi_dung["nhan_dien"])
        self.assertEqual(crypto.sha256_hex(get_storage().read_bytes(luot.vi_tri_luu_tep)), HASH)  # tệp gốc không đổi
        hanh_dong = list(SigningAuditLog.objects.filter(trinh_ky_id=self.pk).values_list("hanh_dong", flat=True))
        self.assertEqual(hanh_dong[-3:], ["HOAN_THANH_TRINH_KY", "CHOT_BANG_CHUNG", "TAO_TEP_HOAN_TAT"])

    def test_evidence_endpoint_verifies_and_detects_tampered_original(self):
        luot = self.ky_het()
        r = self.c.get(f"{BASE}/{self.pk}/bang-chung/")
        self.assertEqual(r.status_code, 200)
        xm = r.data["xac_minh"]
        self.assertTrue(xm["hop_le"])
        self.assertEqual((xm["ma_bam_bang_chung_khop"], xm["tep_goc_khop"], xm["tep_hoan_tat_khop"]),
                         (True, True, True))
        self.assertTrue(all(c["hop_le"] for c in xm["chu_ky"]))
        self.assertEqual(self.client_cua(self.la).get(f"{BASE}/{self.pk}/bang-chung/").status_code, 404)
        with open(get_storage()._resolve(luot.vi_tri_luu_tep), "ab") as f:
            f.write(b"% sua len\n")
        xm = self.c.get(f"{BASE}/{self.pk}/bang-chung/").data["xac_minh"]
        self.assertEqual((xm["tep_goc_khop"], xm["hop_le"]), (False, False))

    def test_not_ready_before_completion(self):
        self.assertEqual(self.c.get(f"{BASE}/{self.pk}/tep-hoan-tat/").data["code"], "tep_hoan_tat_chua_san_sang")
        self.assertEqual(self.c.get(f"{BASE}/{self.pk}/bang-chung/").data["code"], "chua_co_bang_chung")
        self.assertEqual(self.tao_lai(self.tao).data["code"], "ho_so_chua_hoan_thanh")
        self.assertIsNone(self.chi_tiet()["trang_thai_tep_hoan_tat"])

    def test_tampered_result_file_is_refused(self):
        luot = self.ky_het()
        with open(get_storage()._resolve(luot.vi_tri_tep_hoan_tat), "ab") as f:
            f.write(b"x")
        r = self.c.get(f"{BASE}/{self.pk}/tep-hoan-tat/")
        self.assertEqual((r.status_code, r.data["code"]), (409, "tep_hoan_tat_bi_thay_doi"))

    def test_signers_and_auditor_can_download_outsider_cannot(self):
        self.ky_het()
        self.assertEqual(self.client_cua(self.ky3).get(f"{BASE}/{self.pk}/tep-hoan-tat/").status_code, 200)
        cap_quyen(self.la, "view_signing_audit")
        self.assertEqual(self.client_cua(User.objects.get(pk=self.la.pk)).get(
            f"{BASE}/{self.pk}/tep-hoan-tat/").status_code, 200)
        self.assertEqual(self.client_cua(User.objects.create_user("x")).get(
            f"{BASE}/{self.pk}/tep-hoan-tat/").status_code, 404)


class LoiVaThuLaiTests(HoanTatBase):
    @override_settings(SIGNING_PDF_FONT=os.path.join(os.path.dirname(PHONG_TEST), "khong-co.ttf"))
    def test_failure_keeps_signatures_then_retry_without_resigning(self):
        luot = self.ky_het()
        self.assertEqual((luot.trang_thai, luot.trang_thai_tep_hoan_tat, luot.loi_tep_hoan_tat),
                         ("HOAN_THANH", "LOI", "thieu_phong_chu"))
        self.assertEqual(SigningManifest.objects.filter(luot_trinh=luot).count(), 1)  # bằng chứng vẫn chốt
        self.assertEqual(self.c.get(f"{BASE}/{self.pk}/tep-hoan-tat/").status_code, 409)
        self.assertEqual(self.tao_lai(self.ky1).status_code, 403)  # người ký không phải người tạo/kiểm toán
        with override_settings(SIGNING_PDF_FONT=PHONG_TEST):
            r = self.tao_lai(self.tao)
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data["luot_trinh"][0]["trang_thai_tep_hoan_tat"], "THANH_CONG")
        ma_bam = SigningAttempt.objects.get(pk=luot.pk).ma_bam_tep_hoan_tat
        with override_settings(SIGNING_PDF_FONT=PHONG_TEST):
            self.tao_lai(self.tao)  # đã thành công: không sinh bản thứ hai
        self.assertEqual(SigningAttempt.objects.get(pk=luot.pk).ma_bam_tep_hoan_tat, ma_bam)
        self.assertEqual(SigningSignature.objects.count(), 3)
        hanh_dong = list(SigningAuditLog.objects.filter(trinh_ky_id=self.pk).values_list("hanh_dong", flat=True))
        self.assertEqual(hanh_dong[-3:], ["LOI_TAO_TEP_HOAN_TAT", "TAO_LAI_TEP_HOAN_TAT", "TAO_TEP_HOAN_TAT"])

    def test_retry_blocked_while_processing_allowed_when_stale(self):
        luot = self.ky_het()
        SigningAttempt.objects.filter(pk=luot.pk).update(trang_thai_tep_hoan_tat="DANG_XU_LY",
                                                         update_at=timezone.now())
        cap_quyen(self.la, "view_signing_audit")
        r = self.tao_lai(self.la)
        self.assertEqual((r.status_code, r.data["code"]), (409, "dang_tao_tep_hoan_tat"))
        SigningAttempt.objects.filter(pk=luot.pk).update(update_at=timezone.now() - timedelta(minutes=11))
        self.assertEqual(self.tao_lai(self.la).status_code, 200)  # kiểm toán thử lại khi tiến trình cũ treo
        self.assertEqual(SigningAttempt.objects.get(pk=luot.pk).trang_thai_tep_hoan_tat, "THANH_CONG")

    def test_changed_original_file_marks_error(self):
        luot = SigningAttempt.objects.get(trinh_ky_id=self.pk)
        with open(get_storage()._resolve(luot.vi_tri_luu_tep), "ab") as f:
            f.write(b"% bi sua\n")
        luot = self.ky_het()
        self.assertEqual((luot.trang_thai_tep_hoan_tat, luot.loi_tep_hoan_tat), ("LOI", "tep_goc_khong_khop"))


class TaiLenPdfTests(HoanTatBase):
    def test_unreadable_or_pageless_pdf_rejected_at_upload(self):
        r = self.c.post(f"{BASE}/", {"document_type": "vanbandi", "van_ban_id": 10, "quy_trinh": self.process.pk,
                                     "muc_do": "THUONG", "tep": tep_pdf(b"%PDF-1.4 hong")}, format="multipart")
        self.assertEqual((r.status_code, r.data["code"]), (400, "tep_khong_phai_pdf"))
