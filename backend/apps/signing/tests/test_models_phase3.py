from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from signing import enums
from signing.errors import ImmutableEvidenceError
from signing.models import (
    SigningAttempt, SigningAuditLog, SigningKey, SigningManifest, SigningNotification,
    SigningProcess, SigningProcessStep, SigningProcessStepSigner, SigningRequest,
    SigningRequestStep, SigningRequestStepSigner, SigningSignature,
)

User = get_user_model()

H1, H2 = "a" * 64, "b" * 64


class Base(TestCase):
    def setUp(self):
        self.u1 = User.objects.create_user("u1")
        self.u2 = User.objects.create_user("u2")
        self.process = SigningProcess.objects.create(
            ma_quy_trinh="QT", ten_quy_trinh="QT", pham_vi=enums.PhamViQuyTrinh.CONG_TY, create_by=self.u1,
        )
        self.pstep = SigningProcessStep.objects.create(quy_trinh=self.process, cap_ky=1, ten_cap_ky="C1", thu_tu=1)
        self.request = self.make_request()
        self.attempt = self.make_attempt(self.request)
        self.step = SigningRequestStep.objects.create(
            luot_trinh=self.attempt, buoc_quy_trinh=self.pstep, cap_ky=1, ten_cap_ky="C1", thu_tu=1
        )
        self.signer = SigningRequestStepSigner.objects.create(
            buoc_ky=self.step, nguoi_ky=self.u1, ten_nguoi_ky="U1", vai_tro_ky=enums.VaiTroKy.KY_CHINH
        )
        self.key = SigningKey.objects.create(
            nguoi_so_huu=self.u1, ma_khoa="k", dau_van_tay=H1, khoa_cong_khai="x", ngay_hieu_luc=timezone.now()
        )

    def make_request(self, **kw):
        data = dict(
            document_type=enums.LoaiVanBan.VAN_BAN_DI, van_ban_id=1, quy_trinh=self.process, phien_ban_quy_trinh=1,
            muc_do="THUONG", create_by=self.u1,
        )
        data.update(kw)
        return SigningRequest.objects.create(**data)

    def make_attempt(self, request, so_luot=1, **kw):
        data = dict(
            trinh_ky=request, so_luot=so_luot, vi_tri_luu_tep="a.pdf", ma_bam_tai_lieu=H1, create_by=self.u1
        )
        data.update(kw)
        return SigningAttempt.objects.create(**data)

    def make_signature(self):
        return SigningSignature.objects.create(
            luot_trinh=self.attempt, buoc_ky=self.signer, khoa_ky=self.key, hash_tai_lieu=H1,
            thuat_toan="Ed25519", chu_ky_so="c2ln",
        )


class ProcessStepSignerTests(Base):
    def test_exactly_one_of_person_or_position(self):
        SigningProcessStepSigner.objects.create(buoc_quy_trinh=self.pstep, nguoi_ky=self.u1, thu_tu=1)
        SigningProcessStepSigner.objects.create(buoc_quy_trinh=self.pstep, chuc_vu_id=5, thu_tu=2)
        with self.assertRaises(IntegrityError), transaction.atomic():
            SigningProcessStepSigner.objects.create(buoc_quy_trinh=self.pstep, thu_tu=3)
        with self.assertRaises(IntegrityError), transaction.atomic():
            SigningProcessStepSigner.objects.create(
                buoc_quy_trinh=self.pstep, nguoi_ky=self.u1, chuc_vu_id=5, thu_tu=4
            )


class RequestAttemptTests(Base):
    def test_signing_only_accepts_outgoing_documents(self):
        # Phase 6c: bỏ cách thức ký toàn yêu cầu; trình ký chỉ nhận văn bản đi.
        # So đúng danh sách cột để phát hiện cả cột thừa lẫn cột thiếu so với DDL.
        self.assertEqual(enums.LoaiVanBan.values, ["vanbandi"])
        self.assertEqual(sorted(f.name for f in SigningProcess._meta.concrete_fields), [
            "cau_hinh_nhac_han", "create_by", "created_at", "don_vi_ap_dung_id", "id", "ma_quy_trinh", "mo_ta",
            "pham_vi", "phien_ban", "ten_quy_trinh", "trang_thai", "update_at", "update_by",
        ])
        self.assertEqual(sorted(f.name for f in SigningRequest._meta.concrete_fields), [
            "create_by", "created_at", "document_type", "ghi_chu", "han_chot", "ho_so_goc", "id", "ly_do_huy",
            "ly_do_tu_choi", "ma_bam_tai_lieu", "muc_do", "ngay_gui", "ngay_hoan_thanh", "ngay_huy",
            "ngay_tu_choi", "phien_ban_quy_trinh", "phien_ban_van_ban", "quy_trinh", "trang_thai",
            "update_at", "update_by", "van_ban_id", "vi_tri_luu_tep",
        ])
        for loai in ("vanbanden", "vanbanmat"):
            yeu_cau = SigningRequest(document_type=loai, van_ban_id=1, quy_trinh=self.process,
                                     phien_ban_quy_trinh=1, muc_do="THUONG", create_by=self.u1)
            with self.assertRaises(ValidationError) as ctx:
                yeu_cau.full_clean()
            self.assertIn("document_type", ctx.exception.message_dict)

    def test_document_type_has_no_default(self):
        field = SigningRequest._meta.get_field("document_type")
        self.assertFalse(field.has_default())

    def test_draft_request_allows_missing_file_fields(self):
        r = self.make_request(van_ban_id=2)
        self.assertIsNone(r.ma_bam_tai_lieu)

    def test_request_hash_must_be_sha256(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.make_request(van_ban_id=3, ma_bam_tai_lieu="ZZ")
        self.make_request(van_ban_id=4, ma_bam_tai_lieu=H1)

    def test_attempt_unique_number_per_request(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.make_attempt(self.request, so_luot=1)
        self.make_attempt(self.request, so_luot=2)
        self.make_attempt(self.make_request(van_ban_id=9), so_luot=1)

    def test_attempt_requires_valid_hash(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.make_attempt(self.request, so_luot=5, ma_bam_tai_lieu="short")

    def test_attempt_idempotency_key_unique(self):
        self.make_attempt(self.request, so_luot=2, khoa_chong_trung="k")
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.make_attempt(self.request, so_luot=3, khoa_chong_trung="k")
        # nhiều lượt không có khóa vẫn hợp lệ
        self.make_attempt(self.request, so_luot=4)
        self.make_attempt(self.request, so_luot=5)

    def test_sent_attempt_cannot_be_deleted(self):
        draft = self.make_attempt(self.request, so_luot=2)
        sent = self.make_attempt(self.request, so_luot=3, trang_thai=enums.TrangThaiLuotTrinh.CHO_KY)
        with self.assertRaises(ImmutableEvidenceError):
            sent.delete()
        draft.delete()

    def test_request_cannot_be_deleted_when_attempt_exists(self):
        from django.db.models import ProtectedError
        with self.assertRaises(ProtectedError):
            self.request.delete()

    def test_request_step_unique_order(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            SigningRequestStep.objects.create(
                luot_trinh=self.attempt, buoc_quy_trinh=self.pstep, cap_ky=2, ten_cap_ky="C2", thu_tu=1
            )

    def test_signer_unique_in_step_and_delegation_reason(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            SigningRequestStepSigner.objects.create(
                buoc_ky=self.step, nguoi_ky=self.u1, ten_nguoi_ky="U1", vai_tro_ky=enums.VaiTroKy.KY_NHAY
            )
        with self.assertRaises(IntegrityError), transaction.atomic():
            SigningRequestStepSigner.objects.create(
                buoc_ky=self.step, nguoi_ky=self.u2, ten_nguoi_ky="U2", vai_tro_ky=enums.VaiTroKy.KY_NHAY,
                uy_quyen_tu=self.u1, ly_do_uy_quyen="",
            )
        SigningRequestStepSigner.objects.create(
            buoc_ky=self.step, nguoi_ky=self.u2, ten_nguoi_ky="U2", vai_tro_ky=enums.VaiTroKy.KY_NHAY,
            uy_quyen_tu=self.u1, ly_do_uy_quyen="Đi công tác",
        )


class SignatureImmutabilityTests(Base):
    def test_signature_hash_must_be_sha256(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            SigningSignature.objects.create(
                luot_trinh=self.attempt, buoc_ky=self.signer, khoa_ky=self.key, hash_tai_lieu="x",
                thuat_toan="Ed25519", chu_ky_so="c2ln",
            )

    def test_core_fields_cannot_change_but_verification_can(self):
        sig = self.make_signature()
        sig.chu_ky_so = "khac"
        with self.assertRaises(ImmutableEvidenceError):
            sig.save()
        sig = SigningSignature.objects.get(pk=sig.pk)
        sig.trang_thai_xac_minh = enums.TrangThaiXacMinh.KHONG_HOP_LE
        sig.thoi_diem_xac_minh = timezone.now()
        sig.save()
        self.assertEqual(
            SigningSignature.objects.get(pk=sig.pk).trang_thai_xac_minh, enums.TrangThaiXacMinh.KHONG_HOP_LE
        )

    def test_delete_blocked(self):
        sig = self.make_signature()
        with self.assertRaises(ImmutableEvidenceError):
            sig.delete()
        with self.assertRaises(ImmutableEvidenceError):
            SigningSignature.objects.filter(pk=sig.pk).delete()

    def test_bulk_update_only_verification_fields(self):
        sig = self.make_signature()
        SigningSignature.objects.filter(pk=sig.pk).update(trang_thai_xac_minh=enums.TrangThaiXacMinh.HOP_LE)
        with self.assertRaises(ImmutableEvidenceError):
            SigningSignature.objects.filter(pk=sig.pk).update(chu_ky_so="khac")

    def test_multiple_signatures_per_signer_allowed(self):
        self.make_signature()
        self.make_signature()
        self.assertEqual(self.signer.chu_ky_set.count(), 2)


class ManifestImmutabilityTests(Base):
    def make_manifest(self, **kw):
        data = dict(
            luot_trinh=self.attempt, noi_dung_chuan_hoa={"v": 1}, ma_bam_bang_chung=H2, create_by=self.u1
        )
        data.update(kw)
        return SigningManifest.objects.create(**data)

    def test_draft_manifest_editable_and_deletable(self):
        m = self.make_manifest()
        m.vi_tri_luu = "m.json"
        m.save()
        m.delete()

    def test_final_manifest_cannot_change_or_delete(self):
        m = self.make_manifest(trang_thai=enums.TrangThaiManifest.DA_CHOT, thoi_diem_chot=timezone.now())
        m.vi_tri_luu = "m.json"
        with self.assertRaises(ImmutableEvidenceError):
            m.save()
        with self.assertRaises(ImmutableEvidenceError):
            m.delete()
        with self.assertRaises(ImmutableEvidenceError):
            SigningManifest.objects.filter(pk=m.pk).update(vi_tri_luu="x")
        with self.assertRaises(ImmutableEvidenceError):
            SigningManifest.objects.filter(pk=m.pk).delete()

    def test_manifest_hash_must_be_sha256(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.make_manifest(ma_bam_bang_chung="bad")

    def test_attempt_with_manifest_cannot_be_deleted(self):
        attempt = self.make_attempt(self.request, so_luot=2)
        SigningManifest.objects.create(
            luot_trinh=attempt, noi_dung_chuan_hoa={}, ma_bam_bang_chung=H2, create_by=self.u1
        )
        with self.assertRaises(ImmutableEvidenceError):
            attempt.delete()


class AuditLogTests(Base):
    def log(self, **kw):
        data = dict(
            loai_doi_tuong="signing_key", ma_doi_tuong=1, nguoi_thuc_hien=self.u1, hanh_dong="TAO_KHOA"
        )
        data.update(kw)
        return SigningAuditLog.objects.create(**data)

    def test_append_only(self):
        entry = self.log()
        entry.chi_tiet = "sua"
        with self.assertRaises(ImmutableEvidenceError):
            entry.save()
        with self.assertRaises(ImmutableEvidenceError):
            entry.delete()
        with self.assertRaises(ImmutableEvidenceError):
            SigningAuditLog.objects.all().update(chi_tiet="x")
        with self.assertRaises(ImmutableEvidenceError):
            SigningAuditLog.objects.all().delete()

    def test_ip_may_be_null_without_default(self):
        self.assertIsNone(self.log().dia_chi_ip)

    def test_signing_flow_event_requires_request(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.log(loai_doi_tuong="signing_signature")
        self.log(loai_doi_tuong="signing_signature", trinh_ky=self.request)

    def test_related_evidence_protected_from_delete(self):
        from django.db.models import ProtectedError
        self.log(loai_doi_tuong="signing_request", trinh_ky=self.request)
        with self.assertRaises(ProtectedError):
            self.u1.delete()


class ChangeThreadAndNotificationTests(Base):
    def test_thread_protected_when_attempt_deleted(self):
        from signing.models import SigningChangeThread, SigningChangeMessage
        from django.db.models import ProtectedError
        attempt = self.make_attempt(self.request, so_luot=2)
        thread = SigningChangeThread.objects.create(
            luot_trinh=attempt, nguoi_yeu_cau=self.u2, tieu_de="Sửa", ly_do="Sai số liệu"
        )
        SigningChangeMessage.objects.create(yeu_cau_sua=thread, nguoi_viet=self.u2, noi_dung="Nội dung")
        with self.assertRaises(ProtectedError):
            attempt.delete()

    def test_notification_dedup_key_unique(self):
        def notify(key):
            return SigningNotification.objects.create(
                trinh_ky=self.request, nguoi_nhan=self.u1, kenh=enums.KenhThongBao.IN_APP,
                loai_thong_bao="DEN_LUOT_KY", khoa_chong_gui_trung=key,
            )
        n = notify("k1")
        self.assertEqual(n.trang_thai, enums.TrangThaiThongBao.CHO_GUI)
        self.assertEqual(n.so_lan_gui_lai, 0)
        with self.assertRaises(IntegrityError), transaction.atomic():
            notify("k1")
