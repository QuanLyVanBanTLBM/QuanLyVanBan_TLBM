"""
Nguồn đọc ảnh chữ ký phía máy chủ (#459): ký bắt buộc có ảnh, snapshot lấy từ máy chủ, ảnh trình duyệt gửi kèm bị
bỏ qua, cờ có ảnh/preview/snapshot dùng chung một nguồn, Nhóm 7 được ưu tiên hơn ảnh của Trình ký.
"""

import hashlib
import io
from unittest import mock

from pypdf import PdfReader

from signing import crypto
from signing.models import SigningProcessStepSigner, SigningRequestStepSigner, SigningSignature
from signing.storage import get_storage
from signing.tich_hop import to_chuc

from .helpers import dat_anh_chu_ky
from .test_hanh_dong_ky_phase8 import ky_so
from .test_hoan_tat_phase10 import HoanTatBase
from .test_hoan_thien_80 import anh_png
from .test_trinh_ky_phase7 import BASE, pdf_mau, tep_pdf


def png_mau(mau):
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGBA", (60, 20), mau).save(buf, format="PNG")
    return buf.getvalue()


class KyCanAnhMayChuTests(HoanTatBase):
    def test_signing_without_server_image_is_rejected_and_not_recorded(self):
        from signing.models import SigningUserSignature

        SigningUserSignature.objects.filter(nguoi_dung=self.ky1).delete()
        r = self.ky(self.ky1)
        self.assertEqual((r.status_code, r.data["code"]), (400, "chua_co_anh_chu_ky"), getattr(r, "data", None))
        self.assertEqual(SigningSignature.objects.count(), 0)
        self.assertEqual(SigningRequestStepSigner.objects.get(nguoi_ky=self.ky1).trang_thai, "CHO_KY")
        dat_anh_chu_ky(self.ky1)
        self.assertEqual(self.ky(self.ky1).status_code, 200)  # tải ảnh lên rồi ký lại được

    def test_snapshot_comes_from_server_and_browser_image_is_ignored(self):
        anh_server = png_mau((200, 0, 0, 255))
        dat_anh_chu_ky(self.ky1, anh_server)
        import base64

        r = self.ky(self.ky1, anh_chu_ky=base64.b64encode(anh_png()).decode())  # ảnh trình duyệt gửi kèm
        self.assertEqual(r.status_code, 200, r.data)
        ck = SigningSignature.objects.get(buoc_ky__nguoi_ky=self.ky1)
        self.assertTrue(ck.vi_tri_anh_chu_ky.startswith("anh_chu_ky/"))
        self.assertEqual(ck.ma_bam_anh_chu_ky, hashlib.sha256(anh_server).hexdigest())
        self.assertEqual(crypto.sha256_hex(get_storage().read_bytes(ck.vi_tri_anh_chu_ky)), ck.ma_bam_anh_chu_ky)
        anh_r = self.c.get(f"{BASE}/{self.pk}/anh-chu-ky/{ck.pk}/")
        self.assertEqual((anh_r.status_code, anh_r["Content-Type"], anh_r.content), (200, "image/png", anh_server))

    def test_image_from_user_out_of_turn_is_not_stored(self):
        r = self.ky(self.ky3)  # cấp 3 chưa mở
        self.assertGreaterEqual(r.status_code, 400)
        self.assertEqual(SigningSignature.objects.count(), 0)


class NguonDocAnhTests(HoanTatBase):
    URL = "/api/v1/signing"

    def test_flag_preview_and_snapshot_share_one_source(self):
        client = self.client_cua(self.ky1)
        self.assertTrue(client.get(f"{self.URL}/toi/").data["co_anh_chu_ky"])
        self.assertEqual(client.get(f"{self.URL}/anh-chu-ky-ca-nhan/tep/").content, to_chuc.anh_chu_ky(self.ky1))

    def test_group7_image_takes_priority_over_signing_image(self):
        anh_nhom_7 = png_mau((0, 160, 0, 255))
        with mock.patch.object(to_chuc, "_anh_tu_ho_so_nhom_7", return_value=anh_nhom_7):
            self.assertEqual(to_chuc.anh_chu_ky(self.ky1), anh_nhom_7)
            self.assertEqual(self.client_cua(self.ky1).get(f"{self.URL}/anh-chu-ky-ca-nhan/tep/").content, anh_nhom_7)
            r = self.ky(self.ky1)
            self.assertEqual(r.status_code, 200, r.data)
            ck = SigningSignature.objects.get(buoc_ky__nguoi_ky=self.ky1)
            self.assertEqual(ck.ma_bam_anh_chu_ky, hashlib.sha256(anh_nhom_7).hexdigest())

    def test_signing_image_used_when_group7_has_none(self):
        self.assertIsNotNone(to_chuc.anh_chu_ky(self.ky1))
        with mock.patch.object(to_chuc, "_anh_tu_ho_so_nhom_7", return_value=None):
            self.assertIsNotNone(to_chuc.anh_chu_ky(self.ky1))

    def test_user_without_any_image(self):
        nguoi = self.la
        self.assertFalse(to_chuc.co_anh_chu_ky(nguoi))
        self.assertIsNone(to_chuc.anh_chu_ky(nguoi))

    def test_invalid_stored_image_is_treated_as_missing(self):
        dat_anh_chu_ky(self.la, b"khong-phai-png")
        self.assertTrue(to_chuc.co_anh_chu_ky(self.la))  # có bản ghi
        self.assertIsNone(to_chuc.anh_chu_ky(self.la))  # nhưng không dùng được để ký


class TepHoanTatCoAnhMayChuTests(HoanTatBase):
    """Ảnh phía máy chủ được chốt vào bằng chứng và nhúng vào tệp hoàn tất ở đúng khung."""

    def setUp(self):
        super().setUp()
        tep = pdf_mau(2)
        self.pk = self.tao_nhap(tep=tep_pdf(tep)).data["id"]
        ch = {n.nguoi_ky_id: n.pk for n in SigningProcessStepSigner.objects.filter(
            buoc_quy_trinh__quy_trinh=self.process)}
        khung = {"toa_do_x": "55", "toa_do_y": "70", "chieu_rong_khung": "35", "chieu_cao_khung": "15"}
        self.gui(self.pk, khoa="anh", vi_tri_ky={str(ch[self.ky1.pk]): {"trang_ky": 1, **khung},
                                                 str(ch[self.ky2.pk]): {"trang_ky": 1, **khung, "toa_do_y": "50"},
                                                 str(ch[self.ky3.pk]): {"trang_ky": 2, **khung}})
        self.hash = hashlib.sha256(tep).hexdigest()

    def ky_tep(self, user):
        private, _ = self.khoa[user.pk]
        return self.ky(user, hash_tai_lieu=self.hash, chu_ky_so=ky_so(private, self.hash))

    def test_image_is_in_evidence_and_final_pdf(self):
        self.assertEqual(self.ky_tep(self.ky1).status_code, 200)
        self.assertEqual(self.ky_tep(self.ky2).status_code, 200)
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.ky_tep(self.ky3).status_code, 200)
        bc = self.c.get(f"{BASE}/{self.pk}/bang-chung/").data
        self.assertTrue(bc["xac_minh"]["hop_le"])
        self.assertEqual([c["anh_chu_ky_khop"] for c in bc["xac_minh"]["chu_ky"]], [True, True, True])
        pdf = PdfReader(io.BytesIO(self.c.get(f"{BASE}/{self.pk}/tep-hoan-tat/").content))
        self.assertIn("/XObject", str(pdf.pages[0]["/Resources"]))
        self.assertIn("/XObject", str(pdf.pages[1]["/Resources"]))
