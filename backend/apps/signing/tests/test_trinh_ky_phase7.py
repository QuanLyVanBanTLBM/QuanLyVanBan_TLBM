"""
Phase 7 (#80): hồ sơ trình ký, lượt trình, snapshot người ký, gửi/hủy/trình lại.
Văn bản đi của Nhóm 2 chưa có code: thay `_doc_van_ban_di` bằng dữ liệu giả trong test.
"""

import hashlib
import io
import shutil
import tempfile
from datetime import timedelta
from types import SimpleNamespace
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import Position
from signing import enums
from signing.models import SigningAttempt, SigningAuditLog, SigningRequest
from signing.services import process as process_service
from signing.services import trinh_ky as trinh_ky_service
from signing.storage import get_storage
from signing.tich_hop.van_ban import VanBanDi

from .helpers import cap_quyen, tao_chuc_vu

User = get_user_model()
BASE = "/api/v1/signing/trinh-ky"


def pdf_mau(so_trang=1):
    """PDF hợp lệ tối thiểu (trang A4 trống, bảng xref đúng offset) để upload và dựng tệp hoàn tất."""
    kids = " ".join(f"{3 + i} 0 R" for i in range(so_trang))
    doi_tuong = [b"<</Type/Catalog/Pages 2 0 R>>", f"<</Type/Pages/Kids[{kids}]/Count {so_trang}>>".encode()]
    doi_tuong += [b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 595 842]>>"] * so_trang
    out, vi_tri = bytearray(b"%PDF-1.4\n"), []
    for i, noi_dung in enumerate(doi_tuong, start=1):
        vi_tri.append(len(out))
        out += f"{i} 0 obj\n".encode() + noi_dung + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(doi_tuong) + 1}\n0000000000 65535 f \n".encode()
    out += b"".join(f"{v:010d} 00000 n \n".encode() for v in vi_tri)
    out += f"trailer\n<</Size {len(doi_tuong) + 1}/Root 1 0 R>>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)


PDF = pdf_mau()
DOC_TEP_DINH_KEM_PDF = trinh_ky_service.doc_tep_dinh_kem_pdf


def tep_dinh_kem_gia_lap(nguoi, van_ban_id, tep_dinh_kem_id):
    trinh_ky_service.kiem_tra_van_ban_trinh_ky(nguoi, enums.LoaiVanBan.VAN_BAN_DI, van_ban_id)
    return PDF, 1
VAN_BAN = {
    10: VanBanDi(id=10, pham_vi="NOI_BO", nguoi_tao_id=None, so_hieu="10/QD", trich_yeu="Mua sắm"),
    11: VanBanDi(id=11, pham_vi="HAN_CHE", nguoi_tao_id=None, so_hieu="11/QD", trich_yeu="Hạn chế"),
    12: VanBanDi(id=12, pham_vi="NOI_BO", hien_thi=False, nguoi_tao_id=None, so_hieu="12/QD", trich_yeu="Không công khai"),
}
# Văn bản thường khác: mỗi văn bản chỉ có một hồ sơ đang mở, test cần nhiều hồ sơ thì mỗi hồ sơ một văn bản
VAN_BAN.update({i: VanBanDi(id=i, pham_vi="NOI_BO", nguoi_tao_id=None, so_hieu=f"{i}/QD", trich_yeu="Văn bản thử")
                for i in range(20, 60)})


def tep_pdf(noi_dung=PDF, ten="du-thao.pdf"):
    return SimpleUploadedFile(ten, noi_dung, content_type="application/pdf")


class TrinhKyBase(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.thu_muc = tempfile.mkdtemp()
        cls._cai_dat = override_settings(SIGNING_DOCUMENT_ROOT=cls.thu_muc)
        cls._cai_dat.enable()
        cls._van_ban = mock.patch("signing.tich_hop.van_ban._doc_van_ban_di", side_effect=VAN_BAN.get)
        cls._van_ban.start()
        cls._tep_dinh_kem = mock.patch("signing.services.trinh_ky.doc_tep_dinh_kem_pdf",
                                     side_effect=tep_dinh_kem_gia_lap)
        cls._tep_dinh_kem.start()

    @classmethod
    def tearDownClass(cls):
        cls._van_ban.stop()
        cls._tep_dinh_kem.stop()
        cls._cai_dat.disable()
        shutil.rmtree(cls.thu_muc, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.tao = User.objects.create_user("chuyen_vien")
        self.ky1 = User.objects.create_user("ke_toan")
        self.ky2 = User.objects.create_user("phap_che")
        self.ky3 = User.objects.create_user("giam_doc")
        self.la = User.objects.create_user("nguoi_ngoai")
        self.position = Position.objects.create(
            display_order=Position.get_next_display_order(), name="Trưởng phòng"
        )
        cap_quyen(self.tao, "add_trinhky", "send_trinhky", "view_vanbandi")
        cap_quyen(self.ky1, "sign_trinhky")
        cap_quyen(self.ky2, "sign_trinhky")
        cap_quyen(self.ky3, "sign_trinhky")
        self._van_ban_tiep = iter([10, *range(20, 60)])
        self.process = self.tao_quy_trinh()
        self.c = self.client_cua(self.tao)

    def client_cua(self, user):
        client = APIClient()
        client.force_authenticate(user)
        return client

    def tao_quy_trinh(self, ma="QT", cap_ky=None):
        cap_ky = cap_ky or [
            {"cap_ky": 1, "ten_cap_ky": "Kiểm tra", "thu_tu": 1, "nguoi_ky": [
                {"nguoi_ky": self.ky1, "thu_tu": 1},
                {"nguoi_ky": self.ky2, "thu_tu": 2},
            ]},
            {"cap_ky": 2, "ten_cap_ky": "Duyệt", "thu_tu": 2, "so_gio_xu_ly": 24,
             "nguoi_ky": [{"nguoi_ky": self.ky3, "thu_tu": 1}]},
        ]
        quy_trinh = process_service.tao_quy_trinh(
            self.tao, ma_quy_trinh=ma, ten_quy_trinh="Duyệt tờ trình", pham_vi=enums.PhamViQuyTrinh.CONG_TY,
            cap_ky=cap_ky,
        )
        return process_service.kich_hoat(quy_trinh, self.tao)

    def tao_nhap(self, client=None, **kw):
        """Tạo nháp qua API; mặc định chọn PDF đính kèm trên văn bản đi."""
        if "van_ban_id" in kw:
            van_ban_id = kw["van_ban_id"]
        elif "tep" in kw:
            van_ban_id = None
        else:
            van_ban_id = next(self._van_ban_tiep)
        if van_ban_id in ("", None):
            data = {"quy_trinh": self.process.pk, "trich_yeu_van_ban": "Tài liệu thử", "tep": tep_pdf()}
        else:
            data = {"document_type": "vanbandi", "van_ban_id": van_ban_id,
                    "quy_trinh": self.process.pk, "tep_dinh_kem_id": 1}
        data.update({key: value for key, value in kw.items() if value is not None})
        return (client or self.c).post(f"{BASE}/", data, format="multipart")

    def gui(self, pk, client=None, khoa="k1", **body):
        return (client or self.c).post(f"{BASE}/{pk}/gui/", body, format="json", HTTP_IDEMPOTENCY_KEY=khoa)

    def ho_so_da_gui(self):
        r = self.tao_nhap()
        self.assertEqual(r.status_code, 201, r.data)
        r = self.gui(r.data["id"], khoa=f"gui-{r.data['id']}")  # mỗi hồ sơ một khóa chống trùng
        self.assertEqual(r.status_code, 200, r.data)
        return r.data


class TaoNhapTests(TrinhKyBase):
    def test_create_draft_stores_pdf_and_server_hash(self):
        r = self.tao_nhap(ghi_chu="Trình duyệt mua sắm")
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual((r.data["trang_thai"], r.data["phien_ban_van_ban"]), ("NHAP", "1"))
        self.assertEqual(r.data["ma_bam_tai_lieu"], hashlib.sha256(PDF).hexdigest())
        self.assertNotIn("vi_tri_luu_tep", r.data)
        ho_so = SigningRequest.objects.get(pk=r.data["id"])
        self.assertEqual(get_storage().read_bytes(ho_so.vi_tri_luu_tep), PDF)
        self.assertEqual(r.data["lich_su"][0]["hanh_dong"], "TAO_TRINH_KY")

    def test_rejections(self):
        cases = [
            ({"van_ban_id": 11}, 400, "van_ban_han_che_khong_trinh_ky"),
            ({"van_ban_id": 99}, 404, "khong_tim_thay_van_ban"),
            ({"document_type": "vanbanden"}, 400, "du_lieu_khong_hop_le"),
            ({"han_chot": (timezone.now() - timedelta(hours=1)).isoformat()}, 400, "han_chot_khong_hop_le"),
        ]
        for kw, ma_http, code in cases:
            r = self.tao_nhap(**kw)
            self.assertEqual((r.status_code, r.data["code"]), (ma_http, code), kw)
        r = self.c.post(f"{BASE}/", {"quy_trinh": self.process.pk, "trich_yeu_van_ban": "Dự thảo",
                                     "tep": tep_pdf(b"khong phai pdf")}, format="multipart")
        self.assertEqual((r.status_code, r.data["code"]), (400, "tep_khong_phai_pdf"))
        self.assertFalse(SigningRequest.objects.exists())

    def test_file_size_limit(self):
        with mock.patch.object(trinh_ky_service, "TEP_TOI_DA", len(PDF) - 1):
            r = self.c.post(f"{BASE}/", {"quy_trinh": self.process.pk,
                                         "trich_yeu_van_ban": "Dự thảo", "tep": tep_pdf()}, format="multipart")
        self.assertEqual((r.status_code, r.data["code"]), (400, "tep_qua_lon"))

    def test_registered_document_requires_its_own_pdf_attachment(self):
        r = self.c.post(f"{BASE}/", {"document_type": "vanbandi", "van_ban_id": 10,
                                     "quy_trinh": self.process.pk}, format="multipart")
        self.assertEqual(r.status_code, 400)
        self.assertIn("tep_dinh_kem_id", r.data["fields"])
        r = self.tao_nhap(van_ban_id=10, tep=tep_pdf())
        self.assertEqual(r.status_code, 400)
        self.assertIn("tep", r.data["fields"])

    def test_registered_document_attachment_is_copied_as_immutable_signing_source(self):
        class StoredFile:
            size = len(PDF)

            def open(self, mode):
                self.mode = mode
                return io.BytesIO(PDF)

        attachment = SimpleNamespace(name="signed-source.pdf", file=StoredFile())
        with mock.patch("documents.models.VanBanDiAttachment.objects.filter") as query, \
                mock.patch("signing.services.trinh_ky.doc_tep_dinh_kem_pdf", wraps=DOC_TEP_DINH_KEM_PDF):
            query.return_value.first.return_value = attachment
            r = self.tao_nhap()
        self.assertEqual(r.status_code, 201, r.data)
        query.assert_called_once_with(document_id=10, pk=1, is_deleted=False)
        ho_so = SigningRequest.objects.get(pk=r.data["id"])
        self.assertEqual(get_storage().read_bytes(ho_so.vi_tri_luu_tep), PDF)
        self.assertEqual(ho_so.ma_bam_tai_lieu, hashlib.sha256(PDF).hexdigest())

    def test_registered_attachment_must_be_pdf_and_belong_to_selected_document(self):
        class StoredFile:
            size = len(PDF)

            def open(self, mode):
                return io.BytesIO(PDF)

        cases = [
            (SimpleNamespace(name="word.docx", file=StoredFile()), "tep_khong_phai_pdf"),
            (SimpleNamespace(name="missing.pdf", file=None), "khong_tim_thay_tep_dinh_kem"),
        ]
        for attachment, code in cases:
            with mock.patch("documents.models.VanBanDiAttachment.objects.filter") as query, \
                    mock.patch("signing.services.trinh_ky.doc_tep_dinh_kem_pdf", wraps=DOC_TEP_DINH_KEM_PDF):
                query.return_value.first.return_value = attachment
                r = self.tao_nhap()
            self.assertEqual(r.data["code"], code)
        with mock.patch("documents.models.VanBanDiAttachment.objects.filter") as query, \
                mock.patch("signing.services.trinh_ky.doc_tep_dinh_kem_pdf", wraps=DOC_TEP_DINH_KEM_PDF):
            query.return_value.first.return_value = None  # wrong document ID or soft-deleted attachment
            r = self.tao_nhap()
        self.assertEqual((r.status_code, r.data["code"]), (404, "khong_tim_thay_tep_dinh_kem"))


class LienKetVanBanDiTests(TrinhKyBase):
    def tao_da_hoan_tat(self, *, co_tep=True):
        r = self.tao_nhap(van_ban_id=None, trich_yeu_van_ban="Kế hoạch thử")
        self.assertEqual(r.status_code, 201, r.data)
        ho_so = SigningRequest.objects.get(pk=r.data["id"])
        luot = SigningAttempt.objects.create(
            trinh_ky=ho_so, so_luot=1, phien_ban_van_ban=ho_so.phien_ban_van_ban,
            vi_tri_luu_tep=ho_so.vi_tri_luu_tep, ma_bam_tai_lieu=ho_so.ma_bam_tai_lieu,
            trang_thai=enums.TrangThaiLuotTrinh.HOAN_THANH, thoi_diem_hoan_thanh=timezone.now(),
            create_by=self.tao,
        )
        ho_so.trang_thai = enums.TrangThaiYeuCau.HOAN_THANH
        ho_so.ngay_hoan_thanh = timezone.now()
        ho_so.save(update_fields=["trang_thai", "ngay_hoan_thanh", "update_at"])
        if co_tep:
            luot.vi_tri_tep_hoan_tat, luot.ma_bam_tep_hoan_tat = trinh_ky_service.luu_du_lieu_pdf(PDF)
            luot.trang_thai_tep_hoan_tat = enums.TrangThaiTepHoanTat.THANH_CONG
            luot.save(update_fields=["vi_tri_tep_hoan_tat", "ma_bam_tep_hoan_tat", "trang_thai_tep_hoan_tat", "update_at"])
        return ho_so.pk

    def lien_ket(self, pk, van_ban_id=10, client=None):
        return (client or self.c).post(f"{BASE}/{pk}/lien-ket-van-ban-di/", {"van_ban_id": van_ban_id},
                                       format="json")

    def test_creator_links_completed_draft_and_audit_records_target(self):
        pk = self.tao_da_hoan_tat()
        r = self.lien_ket(pk)
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual((r.data["document_type"], r.data["van_ban_id"]), ("vanbandi", 10))
        self.assertEqual((r.data["so_hieu_van_ban"], r.data["trich_yeu_van_ban"]), ("", ""))
        log = SigningAuditLog.objects.get(trinh_ky_id=pk, hanh_dong="LIEN_KET_VAN_BAN_DI")
        self.assertEqual(log.du_lieu_kem_theo["van_ban_id"], 10)
        self.assertEqual(log.chi_tiet, "#10 · 10/QD")
        r = self.lien_ket(pk)
        self.assertEqual((r.status_code, r.data["code"]), (409, "ho_so_da_lien_ket_van_ban"))

    def test_completed_drafts_cannot_link_to_an_outgoing_document_twice(self):
        self.assertEqual(self.lien_ket(self.tao_da_hoan_tat()).status_code, 200)

        second = self.tao_da_hoan_tat()
        r = self.lien_ket(second)

        self.assertEqual((r.status_code, r.data["code"]), (409, "van_ban_da_co_ho_so_hoan_tat"))
        self.assertIsNone(SigningRequest.objects.get(pk=second).van_ban_id)

    def test_link_waits_for_approval_and_successful_final_pdf(self):
        pk = self.tao_nhap(van_ban_id=None, trich_yeu_van_ban="Kế hoạch thử").data["id"]
        r = self.lien_ket(pk)
        self.assertEqual((r.status_code, r.data["code"]), (409, "ho_so_chua_hoan_tat"))
        pk = self.tao_da_hoan_tat(co_tep=False)
        r = self.lien_ket(pk)
        self.assertEqual((r.status_code, r.data["code"]), (409, "tep_hoan_tat_chua_san_sang"))

    def test_link_requires_creator_and_visible_nonrestricted_outgoing_document(self):
        pk = self.tao_da_hoan_tat()
        cap_quyen(self.la, "view_signing_audit")
        r = self.lien_ket(pk, client=self.client_cua(User.objects.get(pk=self.la.pk)))
        self.assertEqual((r.status_code, r.data["code"]), (403, "khong_co_quyen"))
        self.tao.user_permissions.clear()
        self.c = self.client_cua(User.objects.get(pk=self.tao.pk))
        for van_ban_id, http_status, code in (
            (11, 400, "van_ban_han_che_khong_trinh_ky"),
            (12, 404, "khong_tim_thay_van_ban"),
        ):
            r = self.lien_ket(pk, van_ban_id=van_ban_id)
            self.assertEqual((r.status_code, r.data.get("code")), (http_status, code), r.data)
        self.assertIsNone(SigningRequest.objects.get(pk=pk).van_ban_id)

    def test_process_must_be_active(self):
        nhap = process_service.nhan_ban(self.process, self.tao)  # bản 2 còn NHAP
        r = self.tao_nhap(quy_trinh=nhap.pk)
        self.assertEqual((r.status_code, r.data["code"]), (409, "quy_trinh_khong_hoat_dong"))

    def test_requires_add_permission_and_document_visibility(self):
        r = self.tao_nhap(client=self.client_cua(self.la))
        self.assertEqual((r.status_code, r.data["code"]), (403, "khong_co_quyen"))
        cap_quyen(self.la, "add_trinhky")  # có quyền tạo nhưng không xem được văn bản (nội bộ, không công khai)
        la = User.objects.get(pk=self.la.pk)
        r = self.tao_nhap(client=self.client_cua(la), van_ban_id=12)
        self.assertEqual((r.status_code, r.data["code"]), (404, "khong_tim_thay_van_ban"))

    def test_create_without_muc_do_returns_201_and_no_muc_do_in_response(self):
        r = self.tao_nhap()
        self.assertEqual(r.status_code, 201, r.data)
        self.assertNotIn("muc_do", r.data)

    def test_edit_draft_replaces_file_and_bumps_version(self):
        pk = self.tao_nhap().data["id"]
        moi = PDF + b"% ban sua\n"
        r = self.c.patch(f"{BASE}/{pk}/", {"ghi_chu": "Bản sửa", "tep": tep_pdf(moi)}, format="multipart")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual((r.data["ghi_chu"], r.data["phien_ban_van_ban"]), ("Bản sửa", "2"))
        self.assertEqual(r.data["ma_bam_tai_lieu"], hashlib.sha256(moi).hexdigest())
        self.gui(pk)
        r = self.c.patch(f"{BASE}/{pk}/", {"ghi_chu": "x"}, format="multipart")
        self.assertEqual((r.status_code, r.data["code"]), (409, "ho_so_khong_o_trang_thai_nhap"))


class GuiTests(TrinhKyBase):
    def test_send_locks_file_snapshots_signers_and_opens_first_level(self):
        r = self.tao_nhap(han_chot=(timezone.now() + timedelta(days=3)).isoformat())
        r = self.gui(r.data["id"])
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data["trang_thai"], "CHO_KY")
        luot = r.data["luot_trinh"][0]
        self.assertEqual((luot["so_luot"], luot["trang_thai"]), (1, "CHO_KY"))
        self.assertEqual(luot["ma_bam_tai_lieu"], hashlib.sha256(PDF).hexdigest())
        cap1, cap2 = luot["cap_ky"]
        self.assertEqual((cap1["trang_thai"], cap2["trang_thai"]), ("DANG_KY", "CHUA_MO"))
        mo = {n["ten_nguoi_ky"]: n["thoi_diem_mo"] is not None for n in cap1["nguoi_ky"]}
        self.assertEqual(mo, {"ke_toan": True, "phap_che": True})
        self.assertTrue(all(n["thoi_diem_mo"] is None for n in cap2["nguoi_ky"]))
        self.assertIsNotNone(cap1["han_xu_ly"])
        self.assertEqual({d["ten_nguoi_ky"] for d in r.data["dang_cho"]}, {"ke_toan", "phap_che"})

    def test_level_deadline_uses_hours_or_splits_remaining_time(self):
        cap1 = {"cap_ky": 1, "ten_cap_ky": "C1", "thu_tu": 1, "so_gio_xu_ly": 8,
                "nguoi_ky": [{"nguoi_ky": self.ky1, "thu_tu": 1}]}
        cap2 = {"cap_ky": 2, "ten_cap_ky": "C2", "thu_tu": 2, "nguoi_ky": [{"nguoi_ky": self.ky3, "thu_tu": 1}]}
        self.process = self.tao_quy_trinh("QT8", [cap1, cap2])
        luot = SigningAttempt.objects.get(trinh_ky_id=self.ho_so_da_gui()["id"])
        dau = luot.cap_ky_set.get(thu_tu=1)
        self.assertEqual(dau.han_xu_ly - dau.thoi_diem_mo, timedelta(hours=8))
        self.process = self.tao_quy_trinh("QTH", [{**cap1, "so_gio_xu_ly": None}, cap2])
        han = timezone.now() + timedelta(hours=10)
        pk = self.tao_nhap(han_chot=han.isoformat()).data["id"]
        self.gui(pk, khoa="k2")
        dau = SigningAttempt.objects.get(trinh_ky_id=pk).cap_ky_set.get(thu_tu=1)
        self.assertAlmostEqual((dau.han_xu_ly - dau.thoi_diem_mo).total_seconds(), 5 * 3600, delta=5)

    def test_send_requires_key_permission_and_creator(self):
        pk = self.tao_nhap().data["id"]
        r = self.c.post(f"{BASE}/{pk}/gui/", {}, format="json")
        self.assertEqual((r.status_code, r.data["code"]), (400, "thieu_khoa_chong_trung"))
        cap_quyen(self.la, "send_trinhky", "view_signing_audit")  # thấy hồ sơ nhưng không phải người tạo
        r = self.gui(pk, client=self.client_cua(User.objects.get(pk=self.la.pk)))
        self.assertEqual((r.status_code, r.data["code"]), (403, "khong_co_quyen"))
        tao2 = User.objects.create_user("chi_tao")
        cap_quyen(tao2, "add_trinhky", "view_vanbandi")
        pk2 = self.tao_nhap(client=self.client_cua(tao2)).data["id"]
        r = self.gui(pk2, client=self.client_cua(User.objects.get(pk=tao2.pk)))
        self.assertEqual((r.status_code, r.data["fields"]), (403, {"quyen": ["send_trinhky"]}))

    def test_duplicate_send_is_idempotent(self):
        pk = self.tao_nhap().data["id"]
        self.assertEqual(self.gui(pk, khoa="lap").status_code, 200)
        self.assertEqual(self.gui(pk, khoa="lap").status_code, 200)
        self.assertEqual(SigningAttempt.objects.filter(trinh_ky_id=pk).count(), 1)
        r = self.gui(pk, khoa="khac")
        self.assertEqual((r.status_code, r.data["code"]), (409, "ho_so_khong_o_trang_thai_nhap"))
        self.assertEqual(SigningAuditLog.objects.filter(trinh_ky_id=pk, hanh_dong="GUI_TRINH_KY").count(), 1)

    def test_inactive_signer_blocks_send(self):
        self.ky3.is_active = False
        self.ky3.save()
        pk = self.tao_nhap().data["id"]
        r = self.gui(pk)
        self.assertEqual((r.status_code, r.data["code"]), (400, "khong_xac_dinh_duoc_nguoi_ky"))
        self.assertEqual(r.data["fields"]["nguoi_ky"][0]["loai"], "nguoi_ky_khong_hoat_dong")
        self.assertEqual(SigningRequest.objects.get(pk=pk).trang_thai, "NHAP")

    def test_signer_by_position_zero_one_or_many_candidates(self):
        self.process = self.tao_quy_trinh("QTCV", [{"cap_ky": 1, "ten_cap_ky": "Trưởng phòng", "thu_tu": 1,
                                                   "nguoi_ky": [{"chuc_vu_id": self.position.pk, "thu_tu": 1}]}])
        tim = "signing.tich_hop.to_chuc.tim_ung_vien_theo_chuc_vu"
        pk = self.tao_nhap().data["id"]
        with mock.patch(tim, return_value=[]):
            r = self.gui(pk, khoa="a")
        self.assertEqual(r.data["fields"]["nguoi_ky"][0]["loai"], "khong_co_ung_vien")
        with mock.patch(tim, return_value=[self.ky1, self.ky2]):
            r = self.gui(pk, khoa="b")
            self.assertEqual((r.status_code, r.data["code"]), (400, "can_chon_nguoi_ky"))
            van_de = r.data["fields"]["nguoi_ky"][0]
            self.assertEqual([u["id"] for u in van_de["ung_vien"]], [self.ky1.pk, self.ky2.pk])
            r = self.gui(pk, khoa="c", chon_nguoi_ky={str(van_de["cau_hinh"]): self.la.pk})  # ngoài danh sách
            self.assertEqual(r.data["code"], "can_chon_nguoi_ky")
            r = self.gui(pk, khoa="d", chon_nguoi_ky={str(van_de["cau_hinh"]): self.ky2.pk})
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data["luot_trinh"][0]["cap_ky"][0]["nguoi_ky"][0]["nguoi_ky"], self.ky2.pk)
        self.assertEqual(r.data["luot_trinh"][0]["cap_ky"][0]["nguoi_ky"][0]["ten_nguoi_ky"], "phap_che")

    def test_same_person_twice_in_level_rejected(self):
        self.process = self.tao_quy_trinh("QTT", [{"cap_ky": 1, "ten_cap_ky": "C", "thu_tu": 1, "nguoi_ky": [
            {"nguoi_ky": self.ky1, "thu_tu": 1}, {"chuc_vu_id": self.position.pk, "thu_tu": 2}]}])
        pk = self.tao_nhap().data["id"]
        with mock.patch("signing.tich_hop.to_chuc.tim_ung_vien_theo_chuc_vu", return_value=[self.ky1]):
            r = self.gui(pk)
        self.assertEqual(r.data["fields"]["nguoi_ky"][0]["loai"], "nguoi_ky_trung_trong_cap")

    def test_document_rechecked_on_send(self):
        pk = self.tao_nhap().data["id"]
        SigningRequest.objects.filter(pk=pk).update(van_ban_id=11)  # văn bản thành HAN_CHE
        r = self.gui(pk)
        self.assertEqual((r.status_code, r.data["code"]), (400, "van_ban_han_che_khong_trinh_ky"))


class XemTests(TrinhKyBase):
    def test_visibility_and_inboxes(self):
        pk = self.ho_so_da_gui()["id"]
        c1, c2, c3, la = (self.client_cua(u) for u in (self.ky1, self.ky2, self.ky3, self.la))
        self.assertEqual([h["id"] for h in c1.get(f"{BASE}/?hop=can_toi_ky").data["results"]], [pk])
        self.assertEqual([h["id"] for h in c2.get(f"{BASE}/?hop=can_toi_ky").data["results"]], [pk])
        self.assertEqual(c3.get(f"{BASE}/?hop=can_toi_ky").data["results"], [])  # cấp sau chưa mở
        self.assertEqual(c3.get(f"{BASE}/{pk}/").status_code, 200)  # người ký của hồ sơ xem được
        self.assertEqual([h["id"] for h in self.c.get(f"{BASE}/?hop=toi_gui").data["results"]], [pk])
        r = la.get(f"{BASE}/{pk}/")
        self.assertEqual((r.status_code, r.data["code"]), (404, "khong_tim_thay"))
        self.assertEqual(la.get(f"{BASE}/").data["results"], [])
        self.assertEqual(la.get(f"{BASE}/{pk}/tep/").status_code, 404)
        cap_quyen(self.la, "view_signing_audit")
        kiem_toan = self.client_cua(User.objects.get(pk=self.la.pk))
        self.assertEqual(kiem_toan.get(f"{BASE}/{pk}/").status_code, 200)

    def test_download_locked_file(self):
        pk = self.ho_so_da_gui()["id"]
        r = self.client_cua(self.ky1).get(f"{BASE}/{pk}/tep/")
        self.assertEqual((r.status_code, r["Content-Type"], r.content), (200, "application/pdf", PDF))
        self.assertEqual(r["Cache-Control"], "no-store")


class HuyTrinhLaiTests(TrinhKyBase):
    def huy(self, pk, client=None, khoa="h1", **body):
        return (client or self.c).post(f"{BASE}/{pk}/huy/", body, format="json", HTTP_IDEMPOTENCY_KEY=khoa)

    def test_creator_cancels_sent_request(self):
        pk = self.ho_so_da_gui()["id"]
        r = self.huy(pk, ly_do="Đổi nội dung")
        self.assertEqual((r.status_code, r.data["trang_thai"]), (200, "HUY"))
        self.assertEqual(r.data["luot_trinh"][0]["trang_thai"], "HUY")
        self.assertEqual(self.client_cua(self.ky1).get(f"{BASE}/?hop=can_toi_ky").data["results"], [])
        self.assertEqual(self.huy(pk).status_code, 200)  # lặp cùng khóa
        r = self.huy(pk, khoa="h2")
        self.assertEqual((r.status_code, r.data["code"]), (409, "ho_so_da_ket_thuc"))

    def test_cancel_key_reused_on_another_request_is_rejected_not_silently_ignored(self):
        pk1 = self.ho_so_da_gui()["id"]
        pk2 = self.ho_so_da_gui()["id"]
        self.assertEqual(self.huy(pk1, khoa="cung-khoa").status_code, 200)
        r = self.huy(pk2, khoa="cung-khoa")
        self.assertEqual((r.status_code, r.data["code"]), (409, "khoa_chong_trung_da_dung"))
        self.assertEqual(SigningRequest.objects.get(pk=pk2).trang_thai, "CHO_KY")  # không báo "đã hủy" giả

    def test_admin_cancel_needs_permission_and_reason(self):
        pk = self.ho_so_da_gui()["id"]
        r = self.huy(pk, client=self.client_cua(self.ky1))
        self.assertEqual((r.status_code, r.data["code"]), (403, "khong_co_quyen"))
        cap_quyen(self.ky1, "cancel_trinhky")
        quan_tri = self.client_cua(User.objects.get(pk=self.ky1.pk))
        r = self.huy(pk, client=quan_tri, khoa="q1")
        self.assertEqual((r.status_code, r.data["code"]), (400, "thieu_ly_do"))
        r = self.huy(pk, client=quan_tri, khoa="q2", ly_do="Sai quy trình")
        self.assertEqual(r.status_code, 200)
        log = SigningAuditLog.objects.get(trinh_ky_id=pk, hanh_dong="HUY_TRINH_KY")
        self.assertTrue(log.du_lieu_kem_theo["huy_thay"])

    def test_resubmit_after_rejection_creates_linked_draft(self):
        pk = self.ho_so_da_gui()["id"]
        r = self.c.post(f"{BASE}/{pk}/trinh-lai/", {}, format="json", HTTP_IDEMPOTENCY_KEY="t1")
        self.assertEqual((r.status_code, r.data["code"]), (409, "chi_trinh_lai_ho_so_bi_tu_choi"))
        SigningRequest.objects.filter(pk=pk).update(trang_thai=enums.TrangThaiYeuCau.TU_CHOI)
        moi_ban = process_service.nhan_ban(self.process, self.tao)
        process_service.kich_hoat(moi_ban, self.tao)  # bản 1 ngừng, bản 2 hoạt động
        r = self.c.post(f"{BASE}/{pk}/trinh-lai/", {}, format="json", HTTP_IDEMPOTENCY_KEY="t2")
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual((r.data["trang_thai"], r.data["ho_so_goc"]), ("NHAP", pk))
        self.assertEqual((r.data["quy_trinh"], r.data["phien_ban_quy_trinh"]), (moi_ban.pk, 2))
        self.assertEqual(r.data["ma_bam_tai_lieu"], hashlib.sha256(PDF).hexdigest())
        self.assertEqual(SigningRequest.objects.get(pk=pk).trang_thai, "TU_CHOI")  # hồ sơ gốc giữ nguyên
        lap = self.c.post(f"{BASE}/{pk}/trinh-lai/", {}, format="json", HTTP_IDEMPOTENCY_KEY="t2")
        self.assertEqual(lap.data["id"], r.data["id"])
        self.assertEqual(SigningRequest.objects.filter(ho_so_goc_id=pk).count(), 1)
