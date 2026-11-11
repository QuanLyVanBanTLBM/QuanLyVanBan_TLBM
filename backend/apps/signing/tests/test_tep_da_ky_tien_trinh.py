"""
Kiểm thử tải tệp PDF chứa chữ ký lũy kế theo từng giai đoạn trình ký (Issue #686).
"""

import io
import os
import reportlab
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, override_settings
from pypdf import PdfReader

from ..pdf_hoan_tat import dung_tep_da_ky_tien_trinh, dung_tep_hoan_tat, go_net_dut_trong_vung

from .helpers import cap_quyen
from .test_hanh_dong_ky_phase8 import KyBase
from .test_trinh_ky_phase7 import BASE, PDF

User = get_user_model()
PHONG_TEST = os.path.join(os.path.dirname(reportlab.__file__), "fonts", "Vera.ttf")


@override_settings(SIGNING_PDF_FONT=PHONG_TEST)
class TepDaKyTienTrinhTests(KyBase):
    def test_chua_co_chu_ky_tra_ve_tep_goc(self):
        """Khi chưa có cấp nào ký, endpoint trả về tệp gốc nguyên bản."""
        r = self.c.get(f"{BASE}/{self.pk}/tep-da-ky/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "application/pdf")
        self.assertEqual(r.content, PDF)
        self.assertIn(f"trinh-ky-{self.pk}.pdf", r["Content-Disposition"])

    def test_cap_1_ky_xong_tep_da_ky_chi_chua_chu_ky_cap_1(self):
        """Khi Cấp 1 ký xong (hồ sơ vẫn CHO_DUYET), tệp tải về có chữ ký Cấp 1, các cấp sau để trống."""
        self.ky(self.ky1)

        # Kiểm tra qua endpoint /tep-da-ky/
        r = self.c.get(f"{BASE}/{self.pk}/tep-da-ky/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "application/pdf")
        self.assertIn(f"trinh-ky-{self.pk}-da-ky.pdf", r["Content-Disposition"])

        pdf = PdfReader(io.BytesIO(r.content))
        text = "".join(p.extract_text() for p in pdf.pages).upper()
        self.assertIn("KE_TOAN", text)
        self.assertNotIn("PHAP_CHE", text)
        self.assertNotIn("GIAM_DOC", text)

        # Kiểm tra qua endpoint /tep/?da_ky=1
        r_param = self.c.get(f"{BASE}/{self.pk}/tep/", {"da_ky": "1"})
        self.assertEqual(r_param.status_code, 200)
        self.assertIn(f"trinh-ky-{self.pk}-da-ky.pdf", r_param["Content-Disposition"])

        # Kiểm tra /tep/ gốc không có param vẫn giữ nguyên tệp gốc để khớp mã băm tài liệu khóa
        r_goc = self.c.get(f"{BASE}/{self.pk}/tep/")
        self.assertEqual(r_goc.status_code, 200)
        self.assertEqual(r_goc.content, PDF)

    def test_cap_2_ky_xong_tep_da_ky_chua_ca_hai_cap(self):
        """Khi Cấp 2 ký xong, tệp tải về có cả chữ ký Cấp 1 và Cấp 2, Cấp 3 vẫn để trống."""
        self.ky(self.ky1)
        self.ky(self.ky2)

        r = self.c.get(f"{BASE}/{self.pk}/tep-da-ky/")
        self.assertEqual(r.status_code, 200)

        pdf = PdfReader(io.BytesIO(r.content))
        text = "".join(p.extract_text() for p in pdf.pages).upper()
        self.assertIn("KE_TOAN", text)
        self.assertIn("PHAP_CHE", text)
        self.assertNotIn("GIAM_DOC", text)

    def test_hoan_thanh_tra_ve_tep_hoan_tat_day_du(self):
        """Khi tất cả các cấp ký xong, endpoint trả về tệp hoàn tất có đầy đủ tất cả chữ ký."""
        self.ky(self.ky1)
        self.ky(self.ky2)
        with self.captureOnCommitCallbacks(execute=True):
            self.ky(self.ky3)

        r = self.c.get(f"{BASE}/{self.pk}/tep-da-ky/")
        self.assertEqual(r.status_code, 200)

        pdf = PdfReader(io.BytesIO(r.content))
        text = "".join(p.extract_text() for p in pdf.pages).upper()
        self.assertIn("KE_TOAN", text)
        self.assertIn("PHAP_CHE", text)
        self.assertIn("GIAM_DOC", text)

    def test_nguoi_ngoai_khong_xem_duoc_tep_da_ky(self):
        """Người dùng không có quyền xem hồ sơ nhận 404."""
        nguoi_ngoai = User.objects.create_user(username="nguoi_la_686", password="123")
        client_la = self.client_cua(nguoi_ngoai)
        r = client_la.get(f"{BASE}/{self.pk}/tep-da-ky/")
        self.assertEqual(r.status_code, 404)

    def test_khung_ky_co_lop_nen_trang_che_placeholder(self):
        """Khung ký khi dán lên PDF có vẽ hình chữ nhật màu trắng lót bên dưới để che placeholder."""
        self.ky(self.ky1)
        r = self.c.get(f"{BASE}/{self.pk}/tep-da-ky/")
        self.assertEqual(r.status_code, 200)

        pdf = PdfReader(io.BytesIO(r.content))
        # Kiểm tra nội dung trang có lệnh tô màu trắng RGB (1 1 1 rg) và lệnh vẽ chữ nhật tô đầy (re f / re f*)
        noi_dung_trang = pdf.pages[0].get_contents()
        raw_stream = noi_dung_trang.get_data().decode("latin1", errors="ignore")
        # ReportLab tô màu trắng bằng '1 1 1 rg' hoặc '1 g' trước lệnh 're f'
        self.assertTrue("1 1 1 rg" in raw_stream or "1 g" in raw_stream)


def _pdf_khung_net_dut_lon():
    """PDF 1 trang: tiêu đề, hai khung nét đứt lớn hơn khung ký, một khung liền và một khung nét đứt ngoài vùng ký."""
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(595, 842))
    c.drawString(50, 800, "TIEU DE GIU NGUYEN")
    c.setDash(4, 3)
    c.rect(100, 500, 210, 120)
    c.rect(330, 500, 210, 120)
    c.setDash()
    c.rect(50, 300, 100, 50)
    c.setDash(2, 2)
    c.rect(50, 100, 100, 50)
    c.save()
    return buf.getvalue()


def _vi_tri(x, y):
    return {"trang_ky": 1, "toa_do_x": str(x), "toa_do_y": str(y), "chieu_rong_khung": "22", "chieu_cao_khung": "9"}


def _lenh_trang(pdf_bytes):
    from pypdf.generic import ContentStream

    trang = PdfReader(io.BytesIO(pdf_bytes)).pages[0]
    cs = ContentStream(trang.get_contents(), trang.pdf)
    return [(bytes(op).decode("latin1"), [float(x) for x in ts] if op == b"re" else None) for ts, op in cs.operations]


@override_settings(SIGNING_PDF_FONT=PHONG_TEST)
class GoNetDutKhungKyTests(SimpleTestCase):
    """Nét đứt placeholder trong tệp gốc bị gỡ ở bản sinh ra, kể cả ô của người ký chưa ký (Issue #712)."""

    def _noi_dung(self, co_chu_ky_cap_1=True):
        ck = {"id": 1, "ngay_ky": "2026-01-01T00:00:00Z"} if co_chu_ky_cap_1 else None
        return {
            "nhan_dien": "Bản duyệt nội bộ", "ho_so": {"id": 1}, "luot_trinh": {"so_luot": 1, "id": 1},
            "cap_ky": [{"nguoi_ky": [
                {"ten_nguoi_ky": "Nguoi Ky Mot", "vi_tri": _vi_tri(20, 26), "chu_ky": ck},
                {"ten_nguoi_ky": "Nguoi Ky Hai", "vi_tri": _vi_tri(60, 26), "chu_ky": None},
            ]}],
        }

    def test_tien_trinh_go_net_dut_o_da_ky_va_chua_ky(self):
        goc = _pdf_khung_net_dut_lon()
        ra = dung_tep_da_ky_tien_trinh(goc, self._noi_dung())
        lenh = [op for op, _ in _lenh_trang(ra)]
        # hai khung nét đứt lớn không còn lệnh tô nét; khung liền và khung nét đứt ngoài vùng ký giữ nguyên `S`
        self.assertEqual(lenh.count("S"), 2)
        self.assertIn("TIEU DE GIU NGUYEN", PdfReader(io.BytesIO(ra)).pages[0].extract_text())

    def test_tep_goc_khong_bi_sua(self):
        goc = _pdf_khung_net_dut_lon()
        ban_sao = bytes(goc)
        dung_tep_da_ky_tien_trinh(goc, self._noi_dung())
        self.assertEqual(goc, ban_sao)
        self.assertEqual([op for op, _ in _lenh_trang(goc)].count("S"), 4)

    def test_tep_hoan_tat_go_net_dut(self):
        goc = _pdf_khung_net_dut_lon()
        noi_dung = self._noi_dung()
        noi_dung["ho_so"].update({"quy_trinh": {"ma": "QT", "ten": "Quy trình", "phien_ban": 1},
                                  "nguoi_tao": {"ten": "Người trình"}, "van_ban": None, "van_ban_id": None})
        noi_dung["luot_trinh"].update({"thoi_diem_gui": "2026-01-01T00:00:00Z",
                                       "thoi_diem_hoan_thanh": "2026-01-02T00:00:00Z", "ma_bam_tai_lieu": "0" * 64})
        noi_dung["cap_ky"][0].update({"cap_ky": 1, "ten_cap_ky": "Cấp 1"})
        for n in noi_dung["cap_ky"][0]["nguoi_ky"]:
            n.update({"vai_tro_ky": "KY_CHINH", "chu_ky": {"id": 2, "ngay_ky": "2026-01-01T00:00:00Z"}})
        ra = dung_tep_hoan_tat(goc, noi_dung, "0" * 64)
        self.assertEqual([op for op, _ in _lenh_trang(ra)].count("S"), 2)

    def test_net_dut_ngoai_vung_ky_va_vien_trang_duoc_giu(self):
        from reportlab.pdfgen import canvas

        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=(595, 842))
        c.setDash(4, 3)
        c.rect(5, 5, 585, 832)  # viền trang bao trùm khung ký
        c.save()
        trang = PdfReader(io.BytesIO(buf.getvalue())).pages[0]
        so = go_net_dut_trong_vung(trang, [(100.0, 500.0, 300.0, 600.0)])
        self.assertEqual(so, 0)
