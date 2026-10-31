"""
Ảnh chữ ký PNG do trình duyệt gửi kèm yêu cầu ký (#420): snapshot lưu đúng, mã băm khớp, API trả ảnh, tệp hoàn tất
nhúng ảnh; ảnh sai định dạng hoặc quá lớn bị từ chối và không ký; không gửi ảnh thì giữ hành vi cũ.
"""

import base64
import hashlib
import io
from unittest import mock

from pypdf import PdfReader

from signing import anh_chu_ky as anh_ck
from signing import crypto
from signing.models import SigningRequestStepSigner, SigningProcessStepSigner, SigningSignature
from signing.storage import get_storage

from .test_hanh_dong_ky_phase8 import ky_so
from .test_hoan_tat_phase10 import HoanTatBase
from .test_hoan_thien_80 import anh_png
from .test_trinh_ky_phase7 import BASE, pdf_mau, tep_pdf


def b64(du_lieu):
    return base64.b64encode(du_lieu).decode()


def png_kich_thuoc(rong, cao):
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGBA", (rong, cao), (0, 0, 0, 0)).save(buf, format="PNG")
    return buf.getvalue()


class GiaiMaAnhTests(HoanTatBase):
    def test_accepts_base64_and_data_url(self):
        anh = anh_png()
        self.assertEqual(anh_ck.giai_ma_anh(b64(anh)), anh)
        self.assertEqual(anh_ck.giai_ma_anh("data:image/png;base64," + b64(anh)), anh)

    def test_rejects_wrong_format_size_and_dimensions(self):
        from PIL import Image

        jpeg = io.BytesIO()
        Image.new("RGB", (10, 10)).save(jpeg, format="JPEG")
        cases = [
            b64(jpeg.getvalue()),  # không phải PNG
            "data:image/jpeg;base64," + b64(anh_png()),  # data URL không phải PNG
            "***không phải base64***",
            b64(anh_ck.CHU_KY_PNG + b"\x00" * (anh_ck.ANH_TOI_DA + 1)),  # quá 2 MB
            b64(png_kich_thuoc(anh_ck.CANH_TOI_DA + 1, 2)),  # cạnh quá lớn
            b64(anh_png()[:-12]),  # PNG bị cắt (mất IEND)
        ]
        for gia_tri in cases:
            with self.subTest(gia_tri=gia_tri[:30]), self.assertRaises(anh_ck.AnhChuKyKhongHop):
                anh_ck.giai_ma_anh(gia_tri)


class KyKemAnhTests(HoanTatBase):
    """Luồng ký qua API với ảnh chữ ký trong body; hồ sơ mặc định không có vị trí khung."""

    def test_signing_with_image_stores_verified_snapshot(self):
        anh = anh_png()
        r = self.ky(self.ky1, anh_chu_ky="data:image/png;base64," + b64(anh))
        self.assertEqual(r.status_code, 200, r.data)
        ck = SigningSignature.objects.get(buoc_ky__nguoi_ky=self.ky1)
        self.assertTrue(ck.vi_tri_anh_chu_ky.startswith("anh_chu_ky/"))
        self.assertEqual(ck.ma_bam_anh_chu_ky, hashlib.sha256(anh).hexdigest())
        self.assertEqual(crypto.sha256_hex(get_storage().read_bytes(ck.vi_tri_anh_chu_ky)), ck.ma_bam_anh_chu_ky)
        nk = [n for c in r.data["luot_trinh"][0]["cap_ky"] for n in c["nguoi_ky"] if n["chu_ky"]]
        self.assertTrue(nk[0]["chu_ky"]["co_anh_chu_ky"])
        self.assertNotIn(b64(anh), str(r.data))  # phản hồi không trả lại nội dung ảnh
        anh_r = self.c.get(f"{BASE}/{self.pk}/anh-chu-ky/{ck.pk}/")
        self.assertEqual((anh_r.status_code, anh_r["Content-Type"], anh_r.content), (200, "image/png", anh))

    def test_without_image_keeps_previous_behaviour(self):
        r = self.ky(self.ky1)
        self.assertEqual(r.status_code, 200, r.data)
        ck = SigningSignature.objects.get(buoc_ky__nguoi_ky=self.ky1)
        self.assertEqual((ck.vi_tri_anh_chu_ky, ck.ma_bam_anh_chu_ky), ("", ""))
        nk = [n for c in r.data["luot_trinh"][0]["cap_ky"] for n in c["nguoi_ky"] if n["chu_ky"]]
        self.assertFalse(nk[0]["chu_ky"]["co_anh_chu_ky"])
        blank = self.ky(self.ky2, anh_chu_ky="")
        self.assertEqual(blank.status_code, 200, blank.data)
        self.assertEqual(SigningSignature.objects.get(buoc_ky__nguoi_ky=self.ky2).vi_tri_anh_chu_ky, "")

    def test_invalid_image_returns_400_and_does_not_sign(self):
        for gia_tri in (b64(b"GIF89a....."), b64(png_kich_thuoc(anh_ck.CANH_TOI_DA + 1, 2)), "***",
                        b64(anh_ck.CHU_KY_PNG + b"\x00" * (anh_ck.ANH_TOI_DA + 1))):
            with self.subTest(gia_tri=gia_tri[:20]):
                r = self.ky(self.ky1, anh_chu_ky=gia_tri)
                self.assertEqual(r.status_code, 400, getattr(r, "data", None))
        self.assertEqual(SigningSignature.objects.count(), 0)
        self.assertEqual(SigningRequestStepSigner.objects.get(nguoi_ky=self.ky1).trang_thai, "CHO_KY")
        self.assertEqual(self.ky(self.ky1).status_code, 200)  # ký lại không ảnh vẫn được

    def test_image_from_user_out_of_turn_is_not_stored(self):
        r = self.ky(self.ky3, anh_chu_ky=b64(anh_png()))  # cấp 3 chưa mở
        self.assertGreaterEqual(r.status_code, 400)
        self.assertEqual(SigningSignature.objects.count(), 0)

    @mock.patch("signing.tich_hop.to_chuc.anh_chu_ky", return_value=png_kich_thuoc(5, 5))
    def test_server_side_image_takes_priority(self, _anh):
        r = self.ky(self.ky1, anh_chu_ky=b64(anh_png()))
        self.assertEqual(r.status_code, 200, r.data)
        ck = SigningSignature.objects.get(buoc_ky__nguoi_ky=self.ky1)
        self.assertEqual(ck.ma_bam_anh_chu_ky, hashlib.sha256(png_kich_thuoc(5, 5)).hexdigest())


class TepHoanTatCoAnhTests(HoanTatBase):
    """Ảnh gửi lúc ký được chốt vào bằng chứng và nhúng vào tệp hoàn tất ở đúng khung."""

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

    def ky_tep(self, user, **body):
        private, _ = self.khoa[user.pk]
        return self.ky(user, hash_tai_lieu=self.hash, chu_ky_so=ky_so(private, self.hash), **body)

    def test_image_is_in_evidence_and_final_pdf(self):
        anh = b64(anh_png())
        self.assertEqual(self.ky_tep(self.ky1, anh_chu_ky=anh).status_code, 200)
        self.assertEqual(self.ky_tep(self.ky2).status_code, 200)  # không ảnh: khối chữ
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.ky_tep(self.ky3, anh_chu_ky=anh).status_code, 200)
        bc = self.c.get(f"{BASE}/{self.pk}/bang-chung/").data
        self.assertTrue(bc["xac_minh"]["hop_le"])
        self.assertEqual([c["anh_chu_ky_khop"] for c in bc["xac_minh"]["chu_ky"]], [True, None, True])
        pdf = PdfReader(io.BytesIO(self.c.get(f"{BASE}/{self.pk}/tep-hoan-tat/").content))
        self.assertIn("/XObject", str(pdf.pages[0]["/Resources"]))
        self.assertIn("/XObject", str(pdf.pages[1]["/Resources"]))
