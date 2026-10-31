import io
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from signing.models import SigningUserSignature
from signing.tich_hop import to_chuc

from .helpers import cap_quyen
from .test_trinh_ky_phase7 import TrinhKyBase

User = get_user_model()
BASE = "/api/v1/signing/anh-chu-ky-ca-nhan"


def _anh_png_bytes(size=(80, 30), color=(0, 0, 200, 255)):
    buf = io.BytesIO()
    Image.new("RGBA", size, color).save(buf, format="PNG")
    return buf.getvalue()


class AnhChuKyCaNhanApiTests(TrinhKyBase):
    """Kiểm thử API quản lý ảnh chữ ký cá nhân (Issue #424)."""

    def setUp(self):
        super().setUp()
        self.u = User.objects.create_user("user_ky_1")
        cap_quyen(self.u, "sign_trinhky", "view_trinhky")
        self.client_u = self.client_cua(self.u)

    def test_chua_co_anh_chu_ky(self):
        res = self.client_u.get(f"{BASE}/")
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.data["co_anh"])

        res_tep = self.client_u.get(f"{BASE}/tep/")
        self.assertEqual(res_tep.status_code, 404)
        self.assertEqual(res_tep.data["code"], "chua_co_anh_chu_ky")

        # Kiểm tra API /toi/
        toi_res = self.client_u.get("/api/v1/signing/toi/")
        self.assertFalse(toi_res.data["co_anh_chu_ky"])

    def test_upload_anh_multipart(self):
        png = _anh_png_bytes()
        f = SimpleUploadedFile("chuky.png", png, content_type="image/png")
        res = self.client_u.post(f"{BASE}/", {"tep": f}, format="multipart")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.data["co_anh"])
        self.assertTrue(res.data["ma_bam"])
        self.assertEqual(res.data["dung_luong_bytes"], len(png))

        # Kiểm tra database
        sig = SigningUserSignature.objects.filter(nguoi_dung=self.u).first()
        self.assertIsNotNone(sig)
        self.assertEqual(sig.ma_bam, res.data["ma_bam"])

        # Kiểm tra tải tệp
        tep_res = self.client_u.get(f"{BASE}/tep/")
        self.assertEqual(tep_res.status_code, 200)
        self.assertEqual(tep_res["Content-Type"], "image/png")
        self.assertEqual(tep_res.content, png)

        # Kiểm tra API /toi/
        toi_res = self.client_u.get("/api/v1/signing/toi/")
        self.assertTrue(toi_res.data["co_anh_chu_ky"])

        # Kiểm tra to_chuc.anh_chu_ky
        self.assertEqual(to_chuc.anh_chu_ky(self.u), png)

    def test_upload_anh_base64(self):
        png = _anh_png_bytes()
        import base64
        b64 = "data:image/png;base64," + base64.b64encode(png).decode("ascii")
        res = self.client_u.post(f"{BASE}/", {"du_lieu_base64": b64}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.data["co_anh"])

        # to_chuc.anh_chu_ky đọc được
        self.assertEqual(to_chuc.anh_chu_ky(self.u), png)

    def test_tu_choi_dinh_dang_khong_phai_png(self):
        fake_jpg = b"\xff\xd8\xff\xe0" + b"0" * 100
        f = SimpleUploadedFile("chuky.jpg", fake_jpg, content_type="image/jpeg")
        res = self.client_u.post(f"{BASE}/", {"tep": f}, format="multipart")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data["code"], "dinh_dang_khong_hop_le")

    def test_xoa_anh_chu_ky(self):
        png = _anh_png_bytes()
        f = SimpleUploadedFile("chuky.png", png, content_type="image/png")
        self.client_u.post(f"{BASE}/", {"tep": f}, format="multipart")
        self.assertTrue(SigningUserSignature.objects.filter(nguoi_dung=self.u).exists())

        res_del = self.client_u.delete(f"{BASE}/")
        self.assertEqual(res_del.status_code, 204)
        self.assertFalse(SigningUserSignature.objects.filter(nguoi_dung=self.u).exists())
        self.assertIsNone(to_chuc.anh_chu_ky(self.u))
