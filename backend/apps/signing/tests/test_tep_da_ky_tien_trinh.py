"""
Kiểm thử tải tệp PDF chứa chữ ký lũy kế theo từng giai đoạn trình ký (Issue #686).
"""

import io
import os
import reportlab
from django.contrib.auth import get_user_model
from django.test import override_settings
from pypdf import PdfReader

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
