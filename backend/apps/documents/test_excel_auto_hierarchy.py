import io
import openpyxl
from datetime import datetime
from django.db import models
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from documents.models import (
    VanBanDen,
    VanBanDi,
    PhamVi,
    LoaiVanBan,
    HieuLuc,
    VanBanDenHoSo,
    VanBanDenDanhmuc,
    VanBanDiHoSo,
    VanBanDiDanhmuc,
)
from documents.services import (
    generate_excel_template,
    import_from_excel,
    export_to_excel,
    ensure_hoso_and_doc_type,
    ensure_standard_hoso_and_doc_types,
)
from records.models import HoSo, LoaiVanBan as RecordLoaiVanBan
from organizations.models import DonVi, KhoiKhuVuc
from accounts.models import Employee, EmployeeAssignment, Position

User = get_user_model()


class ExcelAutoHierarchyAndValidationTests(TestCase):
    def setUp(self):
        # Thiết lập cơ cấu tổ chức chuẩn
        khoi = KhoiKhuVuc.objects.first()
        if not khoi:
            khoi = KhoiKhuVuc.objects.create(ten="KHỐI CÔNG NGHỆ THÔNG TIN")

        self.dv_cntt = DonVi.objects.filter(ten="Ban công nghệ thông tin").first()
        if not self.dv_cntt:
            max_stt = (DonVi.objects.aggregate(m=models.Max("stt_uu_tien"))["m"] or 0) + 1
            self.dv_cntt = DonVi.objects.create(khoi=khoi, ten="Ban công nghệ thông tin", stt_uu_tien=max_stt)

        self.dv_hcth = DonVi.objects.filter(ten="Ban hành chính quản trị").first() or DonVi.objects.filter(ten__icontains="hành chính").first()
        if not self.dv_hcth:
            max_stt = (DonVi.objects.aggregate(m=models.Max("stt_uu_tien"))["m"] or 0) + 1
            self.dv_hcth = DonVi.objects.create(khoi=khoi, ten="Ban hành chính quản trị", stt_uu_tien=max_stt)

        self.dv_bgd = DonVi.objects.filter(ten="Ban tổng giám đốc").first() or DonVi.objects.filter(ten__icontains="tổng giám đốc").first()
        if not self.dv_bgd:
            max_stt = (DonVi.objects.aggregate(m=models.Max("stt_uu_tien"))["m"] or 0) + 1
            self.dv_bgd = DonVi.objects.create(khoi=khoi, ten="Ban tổng giám đốc", stt_uu_tien=max_stt)

        # Thiết lập Cán bộ chuẩn
        self.admin = User.objects.filter(username="admin").first()
        if not self.admin:
            self.admin = User.objects.create_user(
                username="admin",
                password="password123",
                email="admin@test.com",
                ho_ten="Quản trị hệ thống",
                don_vi=self.dv_cntt,
                is_staff=True,
                is_superuser=True,
            )
        else:
            self.admin.don_vi = self.dv_cntt
            self.admin.save(update_fields=["don_vi"])

        self.cb_cntt = User.objects.filter(username="chuyenvien_cntt").first()
        if not self.cb_cntt:
            self.cb_cntt = User.objects.create_user(
                username="chuyenvien_cntt",
                password="password123",
                email="cv_cntt@test.com",
                ho_ten="Nguyễn Văn CNTT",
                don_vi=self.dv_cntt,
            )
        else:
            self.cb_cntt.don_vi = self.dv_cntt
            self.cb_cntt.save(update_fields=["don_vi"])

        self.cb_hcth = User.objects.filter(username="vanthu_hcth").first()
        if not self.cb_hcth:
            self.cb_hcth = User.objects.create_user(
                username="vanthu_hcth",
                password="password123",
                email="vt_hcth@test.com",
                ho_ten="Trần Thị Văn Thư",
                don_vi=self.dv_hcth,
            )

        # Cán bộ kiêm nhiệm (thuộc dv_cntt nhưng kiêm nhiệm thêm dv_bgd)
        self.cb_kiem_nhiem = User.objects.filter(username="cb_kiemnhiem").first()
        if not self.cb_kiem_nhiem:
            self.cb_kiem_nhiem = User.objects.create_user(
                username="cb_kiemnhiem",
                password="password123",
                email="kn@test.com",
                ho_ten="Lê Kiêm Nhiệm",
                don_vi=self.dv_cntt,
            )
        pos = Position.objects.first()
        EmployeeAssignment.objects.filter(employee=self.cb_kiem_nhiem, don_vi=self.dv_bgd).delete()
        EmployeeAssignment.objects.create(
            employee=self.cb_kiem_nhiem,
            don_vi=self.dv_bgd,
            chuc_vu=pos,
        )

        # Tạo sẵn danh mục hồ sơ và loại văn bản chuẩn
        ensure_standard_hoso_and_doc_types()

        self.hs_hcqt = HoSo.objects.filter(so_ky_hieu="HS-HCQT").first()
        if not self.hs_hcqt:
            self.hs_hcqt = HoSo.objects.create(
                ten_ho_so="Hồ sơ Hành chính - Quản trị",
                so_ky_hieu="HS-HCQT",
                nguoi_lap=self.admin,
            )
        self.lvb_congvan, _ = RecordLoaiVanBan.objects.get_or_create(
            ho_so=self.hs_hcqt,
            ten_loai="Công văn",
        )
        self.lvb_thongbao, _ = RecordLoaiVanBan.objects.get_or_create(
            ho_so=self.hs_hcqt,
            ten_loai="Thông báo",
        )

    def test_01_all_four_templates_contain_18_columns_and_comments(self):
        """Cả 4 biểu mẫu Excel đều có đủ đúng 18 cột (cột đầu là Năm) kèm tooltip comment phân biệt theo phạm vi."""
        templates_to_test = [
            ("DEN", "NOI_BO", "Mẫu VB Đến - Nội bộ"),
            ("DEN", "HAN_CHE", "Mẫu VB Đến - Hạn chế"),
            ("DI", "NOI_BO", "Mẫu VB Đi - Nội bộ"),
            ("DI", "HAN_CHE", "Mẫu VB Đi - Hạn chế"),
        ]

        expected_cols = [
            "Năm",
            "Số, ký hiệu VB",
            "Phạm vi",
            "Trích yếu nội dung",
            "Danh mục hồ sơ (Số ký hiệu)",
            "Loại văn bản",
            "Nơi ban hành",
            "Đơn vị nhận / chủ trì",
            "Cán bộ nhận / xử lý",
            "Người ký",
            "Chức vụ",
            "Hiệu lực",
            "Ngày hết hiệu lực",
            "Tệp đính kèm",
            "Link văn bản thay thế",
            "Ghi chú",
        ]

        for loai, pham_vi, expected_title in templates_to_test:
            bio = generate_excel_template(loai, pham_vi)
            wb = openpyxl.load_workbook(bio)
            ws = wb.active

            self.assertEqual(ws.title, expected_title)
            headers = [cell.value for cell in ws[1] if cell.value]

            self.assertEqual(len(headers), 18, f"Template {loai}-{pham_vi} phải có đúng 18 cột (thực tế: {len(headers)})")
            self.assertEqual(headers[0], "Năm", f"Cột đầu tiên của {loai}-{pham_vi} phải là 'Năm'")
            self.assertEqual(headers[1], "Số, ký hiệu VB", f"Cột thứ 2 của {loai}-{pham_vi} phải là 'Số, ký hiệu VB'")

            for col in expected_cols:
                self.assertIn(col, headers, f"Thiếu cột '{col}' trong template {loai}-{pham_vi}")

            # Kiểm tra tooltip comment cho các cột quan trọng
            for col_name in [
                "Năm",
                "Danh mục hồ sơ (Số ký hiệu)",
                "Loại văn bản",
                "Đơn vị nhận / chủ trì",
                "Cán bộ nhận / xử lý",
                "Người ký",
                "Chức vụ",
                "Tệp đính kèm",
                "Ngày hết hiệu lực",
            ]:
                col_idx = headers.index(col_name) + 1
                cell = ws.cell(row=1, column=col_idx)
                self.assertIsNotNone(cell.comment, f"Cột '{col_name}' thiếu tooltip comment trong {loai}-{pham_vi}")

            dv_comment = ws.cell(row=1, column=headers.index("Đơn vị nhận / chủ trì") + 1).comment.text
            cb_comment = ws.cell(row=1, column=headers.index("Cán bộ nhận / xử lý") + 1).comment.text
            if pham_vi == "NOI_BO":
                self.assertIn("TÙY CHỌN", dv_comment)
                self.assertIn("TÙY CHỌN", cb_comment)
            else:
                self.assertIn("BẮT BUỘC", dv_comment)
                self.assertIn("BẮT BUỘC", cb_comment)

    def test_02_block_import_when_mandatory_fields_missing(self):
        """Chặn toàn bộ file (created: 0) nếu bất kỳ ô bắt buộc nào bị để trống."""
        # Test thiếu Tệp đính kèm
        wb = openpyxl.load_workbook(generate_excel_template("DEN", "NOI_BO"))
        ws = wb.active
        ws.append([
            2026, "101/CV-TEST", "Nội bộ", "15/10/2026 08:30:00", "15/10/2026",
            "Trích yếu công văn đến", "HS-HCQT", "Công văn", "Bộ GD&ĐT",
            "Ban công nghệ thông tin", "chuyenvien_cntt", "Nguyễn Văn Ký", "Trưởng ban",
            "Còn hiệu lực", "", "", "", "",  # Tệp đính kèm để trống (cột 16)
        ])
        bio = io.BytesIO()
        wb.save(bio)
        bio.seek(0)

        res = import_from_excel(bio, "DEN", self.admin, pham_vi="NOI_BO")
        self.assertEqual(res["created"], 0, "Bắt buộc phải chặn import khi thiếu tệp đính kèm")
        self.assertTrue(any("Tệp đính kèm" in e["message"] for e in res["errors"]))

        # Test thiếu Người ký và Chức vụ
        wb2 = openpyxl.load_workbook(generate_excel_template("DI", "NOI_BO"))
        ws2 = wb2.active
        ws2.append([
            2026, "102/DI-TEST", "Nội bộ", "16/10/2026", "16/10/2026",
            "Trích yếu công văn đi", "HS-HCQT", "Công văn", "Ban công nghệ thông tin",
            "Phòng Hành chính - Tổng hợp", "vanthu_hcth", "", "",  # Người ký, Chức vụ trống
            "Còn hiệu lực", "", "tap_tin.pdf", "", "",
        ])
        bio2 = io.BytesIO()
        wb2.save(bio2)
        bio2.seek(0)

        res2 = import_from_excel(bio2, "DI", self.admin, pham_vi="NOI_BO")
        self.assertEqual(res2["created"], 0, "Bắt buộc phải chặn import khi thiếu Người ký / Chức vụ")
        self.assertTrue(any("Người ký" in e["message"] for e in res2["errors"]))

    def test_03_allow_three_optional_fields_empty(self):
        """Các trường tùy chọn (Năm, Ngày hết hiệu lực, Link thay thế, Ghi chú) được phép để trống."""
        wb = openpyxl.load_workbook(generate_excel_template("DEN", "NOI_BO"))
        ws = wb.active
        ws.append([
            "", "201/CV-VALID", "Nội bộ", "15/10/2026 08:30:00", "15/10/2026",
            "Trích yếu công văn đầy đủ trường", "HS-HCQT", "Công văn", "Bộ GD&ĐT",
            "Ban công nghệ thông tin", "chuyenvien_cntt", "Nguyễn Văn Ký", "Trưởng ban",
            "Còn hiệu lực", "", "Cong_van_201.pdf", "", "",  # Để trống Năm, ngày hết hạn, link thay thế, ghi chú
        ])
        bio = io.BytesIO()
        wb.save(bio)
        bio.seek(0)

        res = import_from_excel(bio, "DEN", self.admin, pham_vi="NOI_BO")
        self.assertEqual(res["created"], 1, "Để trống các trường tùy chọn hợp lệ phải import thành công")
        doc = VanBanDen.objects.filter(so_hieu="201/CV-VALID").first()
        self.assertIsNotNone(doc)
        self.assertEqual(doc.nam, timezone.localtime(timezone.now()).year)
        self.assertIsNone(doc.ngay_het_hieu_luc)
        self.assertEqual(doc.link_thay_the, "")
        self.assertEqual(doc.ghi_chu, "")
        self.assertEqual(doc.nguoi_ky, "Nguyễn Văn Ký")
        self.assertEqual(doc.chuc_vu, "Trưởng ban")

    def test_04_strict_hierarchy_pair_1_hoso_and_doc_type(self):
        """Cặp 1: Danh mục hồ sơ (Số ký hiệu) -> Loại văn bản: Phải tồn tại và đúng hồ sơ."""
        # 1. Hồ sơ không tồn tại trong hệ thống
        wb = openpyxl.load_workbook(generate_excel_template("DEN", "NOI_BO"))
        ws = wb.active
        ws.append([
            2026, "301/CV-ERR-HS", "Nội bộ", "15/10/2026 08:30:00", "15/10/2026",
            "Trích yếu test", "HS-KHONG-TON-TAI", "Công văn", "Bộ GD&ĐT",
            "Ban công nghệ thông tin", "chuyenvien_cntt", "Nguyễn Văn A", "Giám đốc",
            "Còn hiệu lực", "", "file.pdf", "", "",
        ])
        bio = io.BytesIO()
        wb.save(bio)
        bio.seek(0)

        res = import_from_excel(bio, "DEN", self.admin, pham_vi="NOI_BO")
        self.assertEqual(res["created"], 0)
        self.assertTrue(any("không tồn tại trong hệ thống" in e["message"] for e in res["errors"]))

        # 2. Loại văn bản không trực thuộc hồ sơ đã chọn
        wb2 = openpyxl.load_workbook(generate_excel_template("DEN", "NOI_BO"))
        ws2 = wb2.active
        ws2.append([
            2026, "302/CV-ERR-LVB", "Nội bộ", "15/10/2026 08:30:00", "15/10/2026",
            "Trích yếu test", "HS-HCQT", "Loại Văn Bản Ma Quái", "Bộ GD&ĐT",
            "Ban công nghệ thông tin", "chuyenvien_cntt", "Nguyễn Văn A", "Giám đốc",
            "Còn hiệu lực", "", "file.pdf", "", "",
        ])
        bio2 = io.BytesIO()
        wb2.save(bio2)
        bio2.seek(0)

        res2 = import_from_excel(bio2, "DEN", self.admin, pham_vi="NOI_BO")
        self.assertEqual(res2["created"], 0)
        self.assertTrue(any("không tồn tại trong Danh mục hồ sơ" in e["message"] for e in res2["errors"]))

    def test_05_strict_hierarchy_pair_2_don_vi_and_can_bo(self):
        """Cặp 2: Đơn vị nhận -> Cán bộ xử lý: Phải tồn tại và cán bộ phải thuộc biên chế hoặc kiêm nhiệm của đơn vị."""
        # 1. Đơn vị nhận không tồn tại
        wb = openpyxl.load_workbook(generate_excel_template("DI", "NOI_BO"))
        ws = wb.active
        ws.append([
            2026, "401/DI-ERR-DV", "Nội bộ", "15/10/2026", "15/10/2026",
            "Trích yếu", "HS-HCQT", "Công văn", "Ban công nghệ thông tin",
            "Phòng Ban Ảo Không Tồn Tại", "chuyenvien_cntt", "Lê Văn Ký", "Hiệu trưởng",
            "Còn hiệu lực", "", "tep.pdf", "", "",
        ])
        bio = io.BytesIO()
        wb.save(bio)
        bio.seek(0)

        res = import_from_excel(bio, "DI", self.admin, pham_vi="NOI_BO")
        self.assertEqual(res["created"], 0)
        self.assertTrue(any("không tồn tại trong cơ cấu tổ chức" in e["message"] for e in res["errors"]))

        # 2. Cán bộ không tồn tại
        wb2 = openpyxl.load_workbook(generate_excel_template("DI", "NOI_BO"))
        ws2 = wb2.active
        ws2.append([
            2026, "402/DI-ERR-CB", "Nội bộ", "15/10/2026", "15/10/2026",
            "Trích yếu", "HS-HCQT", "Công văn", "Ban công nghệ thông tin",
            "Ban công nghệ thông tin", "user_khong_ton_tai_999", "Lê Văn Ký", "Hiệu trưởng",
            "Còn hiệu lực", "", "tep.pdf", "", "",
        ])
        bio2 = io.BytesIO()
        wb2.save(bio2)
        bio2.seek(0)

        res2 = import_from_excel(bio2, "DI", self.admin, pham_vi="NOI_BO")
        self.assertEqual(res2["created"], 0)
        self.assertTrue(any("không tồn tại trong hệ thống" in e["message"] for e in res2["errors"]))

        # 3. Cán bộ thuộc đơn vị khác (chuyenvien_cntt không thuộc dv_hcth)
        wb3 = openpyxl.load_workbook(generate_excel_template("DI", "NOI_BO"))
        ws3 = wb3.active
        ws3.append([
            2026, "403/DI-ERR-WRONG-DEPT", "Nội bộ", "15/10/2026", "15/10/2026",
            "Trích yếu", "HS-HCQT", "Công văn", "Ban công nghệ thông tin",
            self.dv_hcth.ten, "chuyenvien_cntt", "Lê Văn Ký", "Hiệu trưởng",
            "Còn hiệu lực", "", "tep.pdf", "", "",
        ])
        bio3 = io.BytesIO()
        wb3.save(bio3)
        bio3.seek(0)

        res3 = import_from_excel(bio3, "DI", self.admin, pham_vi="NOI_BO")
        self.assertEqual(res3["created"], 0)
        self.assertTrue(any("không thuộc biên chế hoặc kiêm nhiệm" in e["message"] for e in res3["errors"]))

        # 4. Cán bộ kiêm nhiệm của đơn vị -> Hợp lệ và Thành công
        wb4 = openpyxl.load_workbook(generate_excel_template("DI", "NOI_BO"))
        ws4 = wb4.active
        ws4.append([
            2026, "404/DI-OK-ASSIGNMENT", "Nội bộ", "15/10/2026", "15/10/2026",
            "Trích yếu", "HS-HCQT", "Công văn", "Ban công nghệ thông tin",
            self.dv_bgd.ten, "cb_kiemnhiem", "Lê Văn Ký", "Hiệu trưởng",
            "Còn hiệu lực", "", "tep.pdf", "", "",
        ])
        bio4 = io.BytesIO()
        wb4.save(bio4)
        bio4.seek(0)

        res4 = import_from_excel(bio4, "DI", self.admin, pham_vi="NOI_BO")
        self.assertEqual(res4["created"], 1, "Cán bộ có EmployeeAssignment tại đơn vị phải import thành công")
        doc4 = VanBanDi.objects.filter(so_hieu="404/DI-OK-ASSIGNMENT").first()
        self.assertTrue(doc4.nguoi_nhan.filter(username="cb_kiemnhiem").exists())

    def test_06_replacement_link_validation(self):
        """Link thay thế: Bắt buộc văn bản bị thay thế phải có sẵn, cùng phân hệ và cùng phạm vi."""
        # Tạo sẵn 1 VB Đến - Nội bộ
        doc_den_noibo = VanBanDen.objects.create(
            so_hieu="OLD-DEN-NB-01",
            trich_yeu="Văn bản cũ đến nội bộ",
            pham_vi=PhamVi.NOI_BO,
            hieu_luc=HieuLuc.CON_HIEU_LUC,
            nguoi_ky="Trưởng ban A",
            chuc_vu="Trưởng ban",
        )

        # 1. Số hiệu thay thế không tồn tại
        wb = openpyxl.load_workbook(generate_excel_template("DEN", "NOI_BO"))
        ws = wb.active
        ws.append([
            2026, "501/DEN-TEST", "Nội bộ", "15/10/2026 08:30:00", "15/10/2026",
            "Văn bản mới", "HS-HCQT", "Công văn", "Bộ GD&ĐT",
            "Ban công nghệ thông tin", "chuyenvien_cntt", "Nguyễn Văn Ký", "Trưởng ban",
            "Còn hiệu lực", "", "file.pdf", "SO-HIEU-KHONG-TON-TAI", "",
        ])
        bio = io.BytesIO()
        wb.save(bio)
        bio.seek(0)

        res = import_from_excel(bio, "DEN", self.admin, pham_vi="NOI_BO")
        self.assertEqual(res["created"], 0)
        self.assertTrue(any("không tồn tại trong hệ thống" in e["message"] for e in res["errors"]))

        # 2. Số hiệu thay thế tồn tại ở phân hệ khác (Import Đi nhưng link đến VB Đến)
        wb2 = openpyxl.load_workbook(generate_excel_template("DI", "NOI_BO"))
        ws2 = wb2.active
        ws2.append([
            2026, "502/DI-TEST", "Nội bộ", "15/10/2026", "15/10/2026",
            "Văn bản mới", "HS-HCQT", "Công văn", "Ban công nghệ thông tin",
            "Phòng Hành chính - Tổng hợp", "vanthu_hcth", "Lê Văn Ký", "Hiệu trưởng",
            "Còn hiệu lực", "", "file.pdf", "OLD-DEN-NB-01", "",
        ])
        bio2 = io.BytesIO()
        wb2.save(bio2)
        bio2.seek(0)

        res2 = import_from_excel(bio2, "DI", self.admin, pham_vi="NOI_BO")
        self.assertEqual(res2["created"], 0)
        self.assertTrue(any("không cùng phân hệ" in e["message"] for e in res2["errors"]))

        # 3. Số hiệu thay thế cùng phân hệ Đến và cùng phạm vi Nội bộ -> Thành công
        wb3 = openpyxl.load_workbook(generate_excel_template("DEN", "NOI_BO"))
        ws3 = wb3.active
        ws3.append([
            2026, "503/DEN-OK", "Nội bộ", "15/10/2026 08:30:00", "15/10/2026",
            "Văn bản mới thay thế", "HS-HCQT", "Công văn", "Bộ GD&ĐT",
            "Ban công nghệ thông tin", "chuyenvien_cntt", "Nguyễn Văn Ký", "Trưởng ban",
            "Còn hiệu lực", "", "file.pdf", "OLD-DEN-NB-01", "",
        ])
        bio3 = io.BytesIO()
        wb3.save(bio3)
        bio3.seek(0)

        res3 = import_from_excel(bio3, "DEN", self.admin, pham_vi="NOI_BO")
        self.assertEqual(res3["created"], 1)
        doc3 = VanBanDen.objects.filter(so_hieu="503/DEN-OK").first()
        self.assertEqual(doc3.link_thay_the, "OLD-DEN-NB-01")

    def test_07_ngay_het_hieu_luc_field_handling(self):
        """Cột Ngày hết hiệu lực: Nếu nhập thì phải lưu vào CSDL; nếu sai format thì chặn."""
        # 1. Sai định dạng ngày
        wb = openpyxl.load_workbook(generate_excel_template("DEN", "NOI_BO"))
        ws = wb.active
        ws.append([
            2026, "601/DEN-DATE-ERR", "Nội bộ", "15/10/2026 08:30:00", "15/10/2026",
            "Trích yếu test", "HS-HCQT", "Công văn", "Bộ GD&ĐT",
            "Ban công nghệ thông tin", "chuyenvien_cntt", "Nguyễn Văn Ký", "Trưởng ban",
            "Còn hiệu lực", "ngay-khong-hop-le", "file.pdf", "", "",
        ])
        bio = io.BytesIO()
        wb.save(bio)
        bio.seek(0)

        res = import_from_excel(bio, "DEN", self.admin, pham_vi="NOI_BO")
        self.assertEqual(res["created"], 0)
        self.assertTrue(any("Ngày hết hiệu lực" in e["message"] for e in res["errors"]))

        # 2. Hợp lệ định dạng ngày DD/MM/YYYY
        wb2 = openpyxl.load_workbook(generate_excel_template("DEN", "NOI_BO"))
        ws2 = wb2.active
        ws2.append([
            2026, "602/DEN-DATE-OK", "Nội bộ", "15/10/2026 08:30:00", "15/10/2026",
            "Trích yếu test", "HS-HCQT", "Công văn", "Bộ GD&ĐT",
            "Ban công nghệ thông tin", "chuyenvien_cntt", "Nguyễn Văn Ký", "Trưởng ban",
            "Còn hiệu lực", "31/12/2026", "file.pdf", "", "",
        ])
        bio2 = io.BytesIO()
        wb2.save(bio2)
        bio2.seek(0)

        res2 = import_from_excel(bio2, "DEN", self.admin, pham_vi="NOI_BO")
        self.assertEqual(res2["created"], 1)
        doc2 = VanBanDen.objects.filter(so_hieu="602/DEN-DATE-OK").first()
        self.assertIsNotNone(doc2.ngay_het_hieu_luc)
        local_dt = timezone.localtime(doc2.ngay_het_hieu_luc)
        self.assertEqual(local_dt.strftime("%d/%m/%Y"), "31/12/2026")

    def test_08_export_contains_all_18_columns(self):
        """Export ra Excel chứa đủ 18 cột dữ liệu (+ STT, Số đến), bao gồm Năm, ngày hết hiệu lực, đơn vị nhận, cán bộ nhận."""
        doc = VanBanDen.objects.create(
            nam=2024,
            so_hieu="701/DEN-EXPORT",
            trich_yeu="Văn bản kiểm tra export",
            pham_vi=PhamVi.NOI_BO,
            hieu_luc=HieuLuc.CON_HIEU_LUC,
            ngay_het_hieu_luc=timezone.make_aware(datetime(2026, 12, 31, 0, 0)),
            nguoi_ky="Nguyễn Văn Ký",
            chuc_vu="Trưởng ban",
        )
        VanBanDenHoSo.objects.create(vanbanden=doc, hoso_id=self.hs_hcqt.id)
        VanBanDenDanhmuc.objects.create(vanbanden=doc, loaivanban_id=self.lvb_congvan.id)
        from documents.models import VanBanDenDonViNhan
        VanBanDenDonViNhan.objects.create(vanbanden=doc, donvi_id=self.dv_cntt.id)
        doc.nguoi_nhan.add(self.cb_cntt)

        qs = VanBanDen.objects.filter(pk=doc.pk)
        bio = export_to_excel(qs, "DEN", pham_vi="NOI_BO")

        wb = openpyxl.load_workbook(bio)
        ws = wb.active

        headers = [cell.value for cell in ws[1] if cell.value]
        self.assertIn("STT", headers)
        self.assertIn("Số đến", headers)
        self.assertIn("Năm", headers)
        self.assertIn("Ngày hết hiệu lực", headers)
        self.assertIn("Đơn vị nhận / chủ trì", headers)
        self.assertIn("Cán bộ nhận / xử lý", headers)
        self.assertEqual(len(headers), 20)

        nam_col_idx = headers.index("Năm") + 1
        het_col_idx = headers.index("Ngày hết hiệu lực") + 1
        dv_col_idx = headers.index("Đơn vị nhận / chủ trì") + 1
        cb_col_idx = headers.index("Cán bộ nhận / xử lý") + 1

        self.assertEqual(str(ws.cell(row=2, column=nam_col_idx).value), "2024")
        val_het = ws.cell(row=2, column=het_col_idx).value
        val_dv = ws.cell(row=2, column=dv_col_idx).value
        val_cb = ws.cell(row=2, column=cb_col_idx).value

        self.assertEqual(val_het, "31/12/2026")
        self.assertIn("Ban công nghệ thông tin", str(val_dv))
        self.assertIn("chuyenvien_cntt", str(val_cb))

    def test_09_no_auto_creation_of_unregistered_entities(self):
        """Không tự tiện tạo mới bất kỳ thực thể nào (Hồ sơ, Loại VB, Đơn vị, Cán bộ) khi import."""
        wb = openpyxl.load_workbook(generate_excel_template("DEN", "NOI_BO"))
        ws = wb.active
        ws.append([
            2026, "801/DEN-UNREGISTERED", "Nội bộ", "15/10/2026 08:30:00", "15/10/2026",
            "Trích yếu test", "HS-CHUA-DANG-KY", "Loại Chưa Đăng Ký", "Bộ GD&ĐT",
            "Đơn Vị Chưa Đăng Ký", "canbo_chua_dang_ky", "Nguyễn Văn Ký", "Trưởng ban",
            "Còn hiệu lực", "", "file.pdf", "", "",
        ])
        bio = io.BytesIO()
        wb.save(bio)
        bio.seek(0)

        res = import_from_excel(bio, "DEN", self.admin, pham_vi="NOI_BO")
        self.assertEqual(res["created"], 0)
        self.assertFalse(HoSo.objects.filter(so_ky_hieu="HS-CHUA-DANG-KY").exists())
        self.assertFalse(RecordLoaiVanBan.objects.filter(ten_loai="Loại Chưa Đăng Ký").exists())
        self.assertFalse(DonVi.objects.filter(ten="Đơn Vị Chưa Đăng Ký").exists())
        self.assertFalse(User.objects.filter(username="canbo_chua_dang_ky").exists())

    def _to_stream(self, wb):
        bio = io.BytesIO()
        wb.save(bio)
        bio.seek(0)
        return bio

    def test_10_noibo_optional_recipients_vs_hanche_mandatory(self):
        """VB Nội bộ (Đến & Đi) cho phép bỏ trống đơn vị/cán bộ hoặc chỉ chọn đơn vị; VB Hạn chế vẫn bắt buộc cả hai."""
        from documents.models import VanBanDenDonViNhan, VanBanDiDonViNhan

        # 1. Nội bộ Đến & Đi: để trống cả Đơn vị nhận lẫn Cán bộ xử lý -> Thành công
        for loai, model in (("DEN", VanBanDen), ("DI", VanBanDi)):
            wb = openpyxl.load_workbook(generate_excel_template(loai, "NOI_BO"))
            date_val = "15/10/2026 08:30:00" if loai == "DEN" else "15/10/2026"
            so_hieu = f"901/{loai}-NB-EMPTY"
            wb.active.append([
                2026, so_hieu, "Nội bộ", date_val, "15/10/2026",
                "VB nội bộ toàn cơ quan không chỉ định đích danh", "HS-HCQT", "Công văn", "Ban Giám hiệu",
                "", "", "Nguyễn Văn Ký", "Trưởng ban",
                "Còn hiệu lực", "", "file_empty.pdf", "", "",
            ])
            res = import_from_excel(self._to_stream(wb), loai, self.admin, pham_vi="NOI_BO")
            self.assertEqual(res["created"], 1, (loai, res))
            doc = model.objects.get(so_hieu=so_hieu)
            self.assertEqual(doc.donvinhan.count(), 0)
            self.assertEqual(doc.nguoi_nhan.count(), 0)

        # 2. Nội bộ Đến & Đi: có Đơn vị nhận, bỏ trống Cán bộ xử lý -> Thành công
        for loai, model, link_model in (
            ("DEN", VanBanDen, VanBanDenDonViNhan),
            ("DI", VanBanDi, VanBanDiDonViNhan),
        ):
            wb = openpyxl.load_workbook(generate_excel_template(loai, "NOI_BO"))
            date_val = "15/10/2026 08:30:00" if loai == "DEN" else "15/10/2026"
            so_hieu = f"902/{loai}-NB-UNIT-ONLY"
            wb.active.append([
                2026, so_hieu, "Nội bộ", date_val, "15/10/2026",
                "VB nội bộ chỉ chọn đơn vị", "HS-HCQT", "Công văn", "Ban Giám hiệu",
                self.dv_cntt.ten, "", "Nguyễn Văn Ký", "Trưởng ban",
                "Còn hiệu lực", "", "file_unit.pdf", "", "",
            ])
            res = import_from_excel(self._to_stream(wb), loai, self.admin, pham_vi="NOI_BO")
            self.assertEqual(res["created"], 1, (loai, res))
            doc = model.objects.get(so_hieu=so_hieu)
            self.assertEqual(link_model.objects.filter(**{("vanbandi" if loai == "DI" else "vanbanden"): doc}).count(), 1)
            self.assertEqual(doc.nguoi_nhan.count(), 0)

        # 3. Nội bộ: bỏ trống Đơn vị nhận NHƯNG nhập Cán bộ xử lý -> Bị chặn Fail-Fast
        for loai in ("DEN", "DI"):
            wb = openpyxl.load_workbook(generate_excel_template(loai, "NOI_BO"))
            date_val = "15/10/2026 08:30:00" if loai == "DEN" else "15/10/2026"
            wb.active.append([
                2026, f"903/{loai}-NB-STAFF-NO-UNIT", "Nội bộ", date_val, "15/10/2026",
                "Sai phân cấp 2 tầng", "HS-HCQT", "Công văn", "Ban Giám hiệu",
                "", "chuyenvien_cntt", "Nguyễn Văn Ký", "Trưởng ban",
                "Còn hiệu lực", "", "file.pdf", "", "",
            ])
            res = import_from_excel(self._to_stream(wb), loai, self.admin, pham_vi="NOI_BO")
            self.assertEqual(res["created"], 0, (loai, res))
            self.assertTrue(any("Đơn vị nhận" in e["message"] for e in res["errors"]))

        # 4. Hạn chế (Đến & Đi): thiếu Đơn vị nhận hoặc thiếu Cán bộ xử lý đều bị chặn
        for loai in ("DEN", "DI"):
            for dv_val, cb_val in (("", ""), (self.dv_cntt.ten, ""), ("", "chuyenvien_cntt")):
                wb = openpyxl.load_workbook(generate_excel_template(loai, "HAN_CHE"))
                date_val = "15/10/2026 08:30:00" if loai == "DEN" else "15/10/2026"
                wb.active.append([
                    2026, f"904/{loai}-HC-MISSING", "Hạn chế", date_val, "15/10/2026",
                    "Hạn chế thiếu người/đơn vị nhận", "HS-HCQT", "Công văn", "Ban Giám hiệu",
                    dv_val, cb_val, "Nguyễn Văn Ký", "Trưởng ban",
                    "Còn hiệu lực", "", "file.pdf", "", "",
                ])
                res = import_from_excel(self._to_stream(wb), loai, self.admin, pham_vi="HAN_CHE")
                self.assertEqual(res["created"], 0, (loai, dv_val, cb_val, res))

    def test_11_multi_unit_and_multi_staff_comma_and_semicolon(self):
        """Hỗ trợ nhập nhiều Đơn vị nhận và nhiều Cán bộ xử lý phân tách bằng dấu ',' hoặc ';'."""
        from documents.models import VanBanDenDonViNhan, VanBanDiDonViNhan

        for loai, model, link_model, field_key in (
            ("DEN", VanBanDen, VanBanDenDonViNhan, "vanbanden"),
            ("DI", VanBanDi, VanBanDiDonViNhan, "vanbandi"),
        ):
            wb = openpyxl.load_workbook(generate_excel_template(loai, "NOI_BO"))
            date_val = "15/10/2026 08:30:00" if loai == "DEN" else "15/10/2026"
            so_hieu = f"910/{loai}-MULTI-OK"
            wb.active.append([
                2026, so_hieu, "Nội bộ", date_val, "15/10/2026",
                "Phối hợp nhiều phòng ban và cán bộ", "HS-HCQT", "Công văn", "Ban Giám hiệu",
                f"{self.dv_cntt.ten}; {self.dv_hcth.ten}",
                "chuyenvien_cntt, vanthu_hcth; cb_kiemnhiem",
                "Nguyễn Văn Ký", "Trưởng ban",
                "Còn hiệu lực", "", "multi.pdf", "", "",
            ])
            res = import_from_excel(self._to_stream(wb), loai, self.admin, pham_vi="NOI_BO")
            self.assertEqual(res["created"], 1, (loai, res))
            doc = model.objects.get(so_hieu=so_hieu)
            linked_dv_ids = set(link_model.objects.filter(**{field_key: doc}).values_list("donvi_id", flat=True))
            self.assertEqual(linked_dv_ids, {self.dv_cntt.id, self.dv_hcth.id})
            self.assertEqual(
                set(doc.nguoi_nhan.values_list("username", flat=True)),
                {"chuyenvien_cntt", "vanthu_hcth", "cb_kiemnhiem"},
            )

        # Chặn nếu 1 trong nhiều đơn vị không tồn tại hoặc 1 cán bộ không thuộc đơn vị nào trong danh sách
        wb_err_dv = openpyxl.load_workbook(generate_excel_template("DEN", "NOI_BO"))
        wb_err_dv.active.append([
            2026, "911/DEN-MULTI-BAD-DV", "Nội bộ", "15/10/2026 08:30:00", "15/10/2026",
            "Thiếu 1 đơn vị", "HS-HCQT", "Công văn", "Ban Giám hiệu",
            f"{self.dv_cntt.ten}, Đơn Vị Không Tồn Tại", "chuyenvien_cntt",
            "Nguyễn Văn Ký", "Trưởng ban", "Còn hiệu lực", "", "multi.pdf", "", "",
        ])
        res_bad_dv = import_from_excel(self._to_stream(wb_err_dv), "DEN", self.admin, pham_vi="NOI_BO")
        self.assertEqual(res_bad_dv["created"], 0)
        self.assertTrue(any("Đơn Vị Không Tồn Tại" in e["message"] for e in res_bad_dv["errors"]))

        wb_err_cb = openpyxl.load_workbook(generate_excel_template("DEN", "NOI_BO"))
        wb_err_cb.active.append([
            2026, "912/DEN-MULTI-BAD-CB", "Nội bộ", "15/10/2026 08:30:00", "15/10/2026",
            "Cán bộ thuộc đơn vị khác", "HS-HCQT", "Công văn", "Ban Giám hiệu",
            f"{self.dv_hcth.ten}; {self.dv_bgd.ten}", "vanthu_hcth, chuyenvien_cntt",
            "Nguyễn Văn Ký", "Trưởng ban", "Còn hiệu lực", "", "multi.pdf", "", "",
        ])
        res_bad_cb = import_from_excel(self._to_stream(wb_err_cb), "DEN", self.admin, pham_vi="NOI_BO")
        self.assertEqual(res_bad_cb["created"], 0)
        self.assertTrue(any("chuyenvien_cntt" in e["message"] for e in res_bad_cb["errors"]))

    def test_12_year_column_arbitrary_years_and_years_endpoint_sync(self):
        """Import cột Năm hỗ trợ mọi năm dương hợp lệ (1890, 2024, 2150), đánh số riêng từng năm và cập nhật /years/."""
        from rest_framework.test import APIClient

        # 1. File hợp lệ gồm: năm lịch sử 1890, năm cũ 2024 (2 dòng), năm tương lai 2150, và ô trống -> năm hiện tại
        wb = openpyxl.load_workbook(generate_excel_template("DEN", "NOI_BO"))
        ws = wb.active
        ws.append([
            1890, "OLD/1890", "Nội bộ", "01/05/1890 08:00:00", "01/05/1890",
            "Tài liệu lịch sử 1890", "HS-HCQT", "Công văn", "Cơ quan cũ",
            "", "", "Người ký A", "Giám đốc", "Còn hiệu lực", "", "old_1890.pdf", "", "",
        ])
        ws.append([
            "2024", "2024/01", "Nội bộ", "10/03/2024 08:00:00", "10/03/2024",
            "Văn bản năm 2024 số 1", "HS-HCQT", "Công văn", "Bộ GD&ĐT",
            "", "", "Người ký B", "Trưởng ban", "Còn hiệu lực", "", "y2024_1.pdf", "", "",
        ])
        ws.append([
            2024.0, "2024/02", "Nội bộ", "12/03/2024 08:00:00", "12/03/2024",
            "Văn bản năm 2024 số 2", "HS-HCQT", "Công văn", "Bộ GD&ĐT",
            "", "", "Người ký B", "Trưởng ban", "Còn hiệu lực", "", "y2024_2.pdf", "", "",
        ])
        ws.append([
            2150, "FUT/2150", "Nội bộ", "01/01/2026 08:00:00", "01/01/2026",
            "Văn bản vượt 2100", "HS-HCQT", "Công văn", "Bộ GD&ĐT",
            "", "", "Người ký C", "Trưởng ban", "Còn hiệu lực", "", "fut_2150.pdf", "", "",
        ])
        ws.append([
            "", "NOW/AUTO", "Nội bộ", "15/09/2020 08:00:00", "15/09/2020",
            "Để trống cột Năm tự lấy năm hiện tại", "HS-HCQT", "Công văn", "Bộ GD&ĐT",
            "", "", "Người ký D", "Trưởng ban", "Còn hiệu lực", "", "now_auto.pdf", "", "",
        ])

        res = import_from_excel(self._to_stream(wb), "DEN", self.admin, pham_vi="NOI_BO")
        self.assertEqual(res["created"], 5, res)

        cur_year = timezone.localtime(timezone.now()).year
        doc_1890 = VanBanDen.objects.get(so_hieu="OLD/1890")
        doc_2024_1 = VanBanDen.objects.get(so_hieu="2024/01")
        doc_2024_2 = VanBanDen.objects.get(so_hieu="2024/02")
        doc_2150 = VanBanDen.objects.get(so_hieu="FUT/2150")
        doc_now = VanBanDen.objects.get(so_hieu="NOW/AUTO")

        self.assertEqual(doc_1890.nam, 1890)
        self.assertEqual(doc_1890.so_thu_tu, 1)
        self.assertEqual(doc_2024_1.nam, 2024)
        self.assertEqual(doc_2024_1.so_thu_tu, 1)
        self.assertEqual(doc_2024_2.nam, 2024)
        self.assertEqual(doc_2024_2.so_thu_tu, 2)
        self.assertEqual(doc_2150.nam, 2150)
        self.assertEqual(doc_2150.so_thu_tu, 1)
        self.assertEqual(doc_now.nam, cur_year)

        # Kiểm tra endpoint /api/documents/years/?loai=DEN trả đầy đủ các năm vừa import
        client = APIClient()
        client.force_authenticate(user=self.admin)
        years_res = client.get("/api/documents/years/?loai=DEN")
        self.assertEqual(years_res.status_code, 200)
        self.assertEqual(years_res.data, sorted({1890, 2024, 2150, cur_year}, reverse=True))

        # 2. Chặn Fail-Fast nếu cột Năm sai định dạng hoặc vượt ngưỡng SmallIntegerField
        for bad_year in ("khong-phai-nam", 0, -2020, 2024.5, 40000):
            wb_bad = openpyxl.load_workbook(generate_excel_template("DI", "NOI_BO"))
            wb_bad.active.append([
                bad_year, f"BAD/{bad_year}", "Nội bộ", "15/10/2026", "15/10/2026",
                "Năm lỗi", "HS-HCQT", "Công văn", "Ban Giám hiệu",
                "", "", "Lê Văn Ký", "Hiệu trưởng", "Còn hiệu lực", "", "bad.pdf", "", "",
            ])
            res_bad = import_from_excel(self._to_stream(wb_bad), "DI", self.admin, pham_vi="NOI_BO")
            self.assertEqual(res_bad["created"], 0, (bad_year, res_bad))
            self.assertTrue(any("Năm" in e["message"] for e in res_bad["errors"]), (bad_year, res_bad))
