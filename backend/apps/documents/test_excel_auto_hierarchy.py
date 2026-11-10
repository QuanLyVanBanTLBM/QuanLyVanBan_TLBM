import io
import openpyxl
from django.test import TestCase
from django.contrib.auth import get_user_model
from documents.models import (
    VanBanDen,
    VanBanDi,
    PhamVi,
    LoaiVanBan,
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

User = get_user_model()


class ExcelAutoHierarchyAndValidationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="vanthu_test",
            password="password123",
            email="vanthu@test.com",
            is_staff=True,
            is_superuser=True,
        )
        ensure_standard_hoso_and_doc_types()

    def test_01_all_four_templates_contain_new_columns_and_comments(self):
        """4 biểu mẫu Excel đều có đủ 2 cột 'Danh mục hồ sơ' và 'Loại văn bản' kèm tooltip comment."""
        templates_to_test = [
            ("DEN", "NOI_BO", "Mẫu VB Đến - Nội bộ"),
            ("DEN", "HAN_CHE", "Mẫu VB Đến - Hạn chế"),
            ("DI", "NOI_BO", "Mẫu VB Đi - Nội bộ"),
            ("DI", "HAN_CHE", "Mẫu VB Đi - Hạn chế"),
        ]

        for loai, pham_vi, expected_title in templates_to_test:
            bio = generate_excel_template(loai, pham_vi)
            wb = openpyxl.load_workbook(bio)
            ws = wb.active

            self.assertEqual(ws.title, expected_title)
            headers = [cell.value for cell in ws[1] if cell.value]

            self.assertIn("Danh mục hồ sơ", headers, f"Thiếu cột 'Danh mục hồ sơ' trong template {loai}-{pham_vi}")
            self.assertIn("Loại văn bản", headers, f"Thiếu cột 'Loại văn bản' trong template {loai}-{pham_vi}")

            # Kiểm tra tooltip comment cho 2 cột mới
            hoso_col_idx = headers.index("Danh mục hồ sơ") + 1
            loaivb_col_idx = headers.index("Loại văn bản") + 1

            cell_hoso = ws.cell(row=1, column=hoso_col_idx)
            cell_loaivb = ws.cell(row=1, column=loaivb_col_idx)

            self.assertIsNotNone(cell_hoso.comment, f"Cột 'Danh mục hồ sơ' thiếu comment trong {loai}-{pham_vi}")
            self.assertIn("BẮT BUỘC", cell_hoso.comment.text)

            self.assertIsNotNone(cell_loaivb.comment, f"Cột 'Loại văn bản' thiếu comment trong {loai}-{pham_vi}")
            self.assertIn("BẮT BUỘC", cell_loaivb.comment.text)

    def test_02_block_import_when_danh_muc_ho_so_or_loai_van_ban_missing(self):
        """Chặn toàn bộ file (created: 0) nếu bất kỳ dòng nào thiếu Danh mục hồ sơ hoặc Loại văn bản."""
        # 1. Thiếu Danh mục hồ sơ ở dòng 2
        wb = openpyxl.load_workbook(generate_excel_template("DEN", "NOI_BO"))
        ws = wb.active
        # Dòng 2 có loại văn bản nhưng thiếu danh mục hồ sơ
        ws.append([
            "101/DEN-TEST", "Nội bộ", "15/10/2026 09:00:00", "15/10/2026",
            "Trích yếu hợp lệ", "", "Công văn", "Bộ GD&ĐT", "Nguyễn Văn A", "Cục trưởng",
            "CON_HIEU_LUC", "", "", "",
        ])
        bio = io.BytesIO()
        wb.save(bio)
        bio.seek(0)

        res = import_from_excel(bio, "DEN", self.user, pham_vi="NOI_BO")
        self.assertEqual(res["created"], 0, "Phải chặn toàn bộ file nếu thiếu Danh mục hồ sơ")
        self.assertTrue(any("Danh mục hồ sơ" in e["message"] for e in res["errors"]))
        self.assertFalse(VanBanDen.objects.filter(so_hieu="101/DEN-TEST").exists())

        # 2. Thiếu Loại văn bản ở dòng 2
        wb2 = openpyxl.load_workbook(generate_excel_template("DI", "NOI_BO"))
        ws2 = wb2.active
        ws2.append([
            "102/DI-TEST", "Nội bộ", "15/10/2026", "15/10/2026",
            "Trích yếu hợp lệ", "Hồ sơ Quản trị", "", "Bộ GD&ĐT", "UBND Tỉnh", "Trần Văn B", "Chủ tịch",
            "CON_HIEU_LUC", "", "", "",
        ])
        bio2 = io.BytesIO()
        wb2.save(bio2)
        bio2.seek(0)

        res2 = import_from_excel(bio2, "DI", self.user, pham_vi="NOI_BO")
        self.assertEqual(res2["created"], 0, "Phải chặn toàn bộ file nếu thiếu Loại văn bản")
        self.assertTrue(any("Loại văn bản" in e["message"] for e in res2["errors"]))
        self.assertFalse(VanBanDi.objects.filter(so_hieu="102/DI-TEST").exists())

        # 3. Thiếu cả hai ở dòng 2
        wb3 = openpyxl.load_workbook(generate_excel_template("DI", "HAN_CHE"))
        ws3 = wb3.active
        ws3.append([
            "103/DI-HC-TEST", "Hạn chế", "15/10/2026", "15/10/2026",
            "Trích yếu hợp lệ", "", "", "Bộ GD&ĐT", self.user.username, "UBND Tỉnh", "Trần Văn B", "Chủ tịch",
            "CON_HIEU_LUC", "", "", "",
        ])
        bio3 = io.BytesIO()
        wb3.save(bio3)
        bio3.seek(0)

        res3 = import_from_excel(bio3, "DI", self.user, pham_vi="HAN_CHE")
        self.assertEqual(res3["created"], 0, "Phải chặn toàn bộ file nếu thiếu cả 2 trường bắt buộc")
        self.assertTrue(any("Danh mục hồ sơ, Loại văn bản" in e["message"] for e in res3["errors"]))

    def test_03_allow_optional_fields_empty(self):
        """Các trường tùy chọn (Tệp đính kèm, Link thay thế, Ghi chú, Nơi ban hành,...) để trống vẫn import thành công."""
        wb = openpyxl.load_workbook(generate_excel_template("DEN", "NOI_BO"))
        ws = wb.active
        # Điền đầy đủ số hiệu, trích yếu, hồ sơ, loại vb. Để trống toàn bộ các cột tùy chọn phía sau.
        ws.append([
            "201/DEN-OPTIONAL", "Nội bộ", "15/10/2026 09:00:00", "15/10/2026",
            "Trích yếu kiểm tra trường tùy chọn", "Hồ sơ Tiếp nhận", "Công văn", "", "", "",
            "CON_HIEU_LUC", "", "", "",
        ])
        bio = io.BytesIO()
        wb.save(bio)
        bio.seek(0)

        res = import_from_excel(bio, "DEN", self.user, pham_vi="NOI_BO")
        self.assertEqual(res["created"], 1)
        doc = VanBanDen.objects.filter(so_hieu="201/DEN-OPTIONAL").first()
        self.assertIsNotNone(doc)

    def test_04_auto_hierarchy_level_1_then_level_2(self):
        """Cơ chế tự động phân cấp 1 rồi mới tới 2:
        - Hồ sơ chưa có -> Tự tạo mới an toàn.
        - Loại văn bản con được tạo hoặc khớp CHÍNH XÁC trực thuộc Hồ sơ Cấp 1.
        - Khóa chặt quan hệ cha - con, không lấy Loại VB của hồ sơ khác."""
        # Tạo trước Hồ sơ A đã có Loại văn bản "Báo cáo"
        hoso_a = HoSo.objects.create(
            ten_ho_so="Hồ sơ Phòng Đào Tạo",
            so_ky_hieu="HS-PDT",
            nguoi_lap=self.user,
        )
        lvb_a = RecordLoaiVanBan.objects.create(
            ho_so=hoso_a,
            ten_loai="Báo cáo",
        )

        # Import 1 văn bản đi vào Hồ sơ mới "Hồ sơ Khảo Thí" cũng có Loại VB tên "Báo cáo"
        wb = openpyxl.load_workbook(generate_excel_template("DI", "NOI_BO"))
        ws = wb.active
        ws.append([
            "301/DI-HIERARCHY", "Nội bộ", "20/10/2026", "20/10/2026",
            "Báo cáo kết quả khảo thí", "Hồ sơ Khảo Thí", "Báo cáo", "Phòng KT", "Toàn trường", "Hiệu trưởng", "Hiệu trưởng",
            "CON_HIEU_LUC", "", "", "",
        ])
        bio = io.BytesIO()
        wb.save(bio)
        bio.seek(0)

        res = import_from_excel(bio, "DI", self.user, pham_vi="NOI_BO")
        self.assertEqual(res["created"], 1)

        doc = VanBanDi.objects.get(so_hieu="301/DI-HIERARCHY")

        # 1. Kiểm tra Hồ sơ mới được tự tạo đúng
        hoso_b = HoSo.objects.filter(ten_ho_so="Hồ sơ Khảo Thí").first()
        self.assertIsNotNone(hoso_b)
        self.assertNotEqual(hoso_b.id, hoso_a.id)

        # 2. Kiểm tra junction VanBanDiHoSo
        di_hoso = VanBanDiHoSo.objects.filter(vanbandi=doc).first()
        self.assertIsNotNone(di_hoso)
        self.assertEqual(di_hoso.hoso_id, hoso_b.id)

        # 3. Kiểm tra junction VanBanDiDanhmuc
        di_danhmuc = VanBanDiDanhmuc.objects.filter(vanbandi=doc).first()
        self.assertIsNotNone(di_danhmuc)

        # 4. CỰC KỲ QUAN TRỌNG: Loại văn bản được liên kết PHẢI thuộc Hồ sơ B (hoso_b), TUYỆT ĐỐI KHÔNG phải lvb_a của hoso_a!
        lvb_assigned = RecordLoaiVanBan.objects.get(pk=di_danhmuc.loaivanban_id)
        self.assertEqual(lvb_assigned.ten_loai, "Báo cáo")
        self.assertEqual(lvb_assigned.ho_so_id, hoso_b.id, "Loại văn bản phải trực thuộc đúng Hồ sơ Cấp 1 vừa import")
        self.assertNotEqual(lvb_assigned.id, lvb_a.id, "Tuyệt đối không lấy nhầm loại văn bản của hồ sơ khác")

    def test_05_match_existing_hoso_and_doc_type(self):
        """Nếu Hồ sơ và Loại văn bản đã có sẵn thì khớp chính xác mà không tạo trùng lặp."""
        hoso = HoSo.objects.create(
            ten_ho_so="Hồ sơ Khen Thưởng",
            so_ky_hieu="HS-KT",
            nguoi_lap=self.user,
        )
        lvb = RecordLoaiVanBan.objects.create(
            ho_so=hoso,
            ten_loai="Quyết định",
        )

        initial_hoso_count = HoSo.objects.count()
        initial_lvb_count = RecordLoaiVanBan.objects.count()

        wb = openpyxl.load_workbook(generate_excel_template("DI", "NOI_BO"))
        ws = wb.active
        ws.append([
            "401/DI-MATCH", "Nội bộ", "25/10/2026", "25/10/2026",
            "Quyết định khen thưởng", "Hồ sơ Khen Thưởng", "Quyết định", "BGH", "Toàn trường", "Hiệu trưởng", "Hiệu trưởng",
            "CON_HIEU_LUC", "", "", "",
        ])
        bio = io.BytesIO()
        wb.save(bio)
        bio.seek(0)

        res = import_from_excel(bio, "DI", self.user, pham_vi="NOI_BO")
        self.assertEqual(res["created"], 1)

        # Số lượng hồ sơ và loại VB không được tăng thêm
        self.assertEqual(HoSo.objects.count(), initial_hoso_count)
        self.assertEqual(RecordLoaiVanBan.objects.count(), initial_lvb_count)

        doc = VanBanDi.objects.get(so_hieu="401/DI-MATCH")
        self.assertTrue(VanBanDiHoSo.objects.filter(vanbandi=doc, hoso_id=hoso.id).exists())
        self.assertTrue(VanBanDiDanhmuc.objects.filter(vanbandi=doc, loaivanban_id=lvb.id).exists())

    def test_06_export_contains_danh_muc_ho_so_and_loai_van_ban(self):
        """Export Excel xuất đúng Danh mục hồ sơ và Loại văn bản từ junction tables."""
        hoso = HoSo.objects.create(
            ten_ho_so="Hồ sơ Lưu Trữ 2026",
            so_ky_hieu="HS-LT26",
            nguoi_lap=self.user,
        )
        lvb = RecordLoaiVanBan.objects.create(
            ho_so=hoso,
            ten_loai="Chỉ thị",
        )

        doc = VanBanDen.objects.create(
            nam=2026,
            so_hieu="501/DEN-EXP",
            trich_yeu="Chỉ thị về phòng chống thiên tai",
            nguoi_tao=self.user,
        )
        VanBanDenHoSo.objects.create(vanbanden=doc, hoso_id=hoso.id)
        VanBanDenDanhmuc.objects.create(vanbanden=doc, loaivanban_id=lvb.id)

        export_bio = export_to_excel(VanBanDen.objects.filter(pk=doc.id), "DEN")
        wb = openpyxl.load_workbook(export_bio)
        ws = wb.active

        headers = [cell.value for cell in ws[1] if cell.value]
        self.assertIn("Danh mục hồ sơ", headers)
        self.assertIn("Loại văn bản", headers)

        hoso_col_idx = headers.index("Danh mục hồ sơ") + 1
        loaivb_col_idx = headers.index("Loại văn bản") + 1

        exported_hoso_val = ws.cell(row=2, column=hoso_col_idx).value
        exported_loaivb_val = ws.cell(row=2, column=loaivb_col_idx).value

        self.assertEqual(exported_hoso_val, "Hồ sơ Lưu Trữ 2026")
        self.assertEqual(exported_loaivb_val, "Chỉ thị")

    def test_07_user_without_add_hoso_permission_blocked_when_importing_new_hoso(self):
        """Cán bộ thiếu quyền records.add_hoso sẽ bị chặn toàn bộ file nếu import hồ sơ mới chưa có trong CSDL."""
        chuyenvien = User.objects.create_user(
            username="chuyenvien_normal",
            password="password123",
            email="cv@test.com",
            is_staff=False,
            is_superuser=False,
        )

        wb = openpyxl.load_workbook(generate_excel_template("DEN", "NOI_BO"))
        ws = wb.active
        ws.append([
            "701/DEN-NO-PERM", "Nội bộ", "28/10/2026 09:00:00", "28/10/2026",
            "Công văn chứa hồ sơ chưa từng tồn tại", "Hồ sơ Bí Mật Tự Phát 999", "Công văn", "Bộ GD&ĐT",
            "Nguyễn Văn X", "Chuyên viên", "CON_HIEU_LUC", "", "", "",
        ])
        bio = io.BytesIO()
        wb.save(bio)
        bio.seek(0)

        res = import_from_excel(bio, "DEN", chuyenvien, pham_vi="NOI_BO")
        self.assertEqual(res["created"], 0, "Chuyên viên không có quyền add_hoso phải bị chặn toàn bộ file")
        self.assertTrue(any("không có quyền tạo mới hồ sơ" in e["message"] for e in res["errors"]))
        self.assertFalse(HoSo.objects.filter(ten_ho_so="Hồ sơ Bí Mật Tự Phát 999").exists())
        self.assertFalse(VanBanDen.objects.filter(so_hieu="701/DEN-NO-PERM").exists())

    def test_08_user_without_add_hoso_permission_can_import_existing_hoso(self):
        """Cán bộ thiếu quyền records.add_hoso vẫn import thành công nếu sử dụng hồ sơ ĐÃ CÓ SẴN."""
        chuyenvien = User.objects.create_user(
            username="chuyenvien_existing",
            password="password123",
            email="cv_existing@test.com",
            is_staff=False,
            is_superuser=False,
        )

        # Sử dụng hồ sơ chuẩn "Hồ sơ Hành chính - Quản trị" đã có sẵn
        wb = openpyxl.load_workbook(generate_excel_template("DEN", "NOI_BO"))
        ws = wb.active
        ws.append([
            "801/DEN-EXISTING-HS", "Nội bộ", "29/10/2026 09:00:00", "29/10/2026",
            "Công văn nhập vào hồ sơ có sẵn", "Hồ sơ Hành chính - Quản trị", "Công văn", "Bộ GD&ĐT",
            "Nguyễn Văn Y", "Chuyên viên", "CON_HIEU_LUC", "", "", "",
        ])
        bio = io.BytesIO()
        wb.save(bio)
        bio.seek(0)

        res = import_from_excel(bio, "DEN", chuyenvien, pham_vi="NOI_BO")
        self.assertEqual(res["created"], 1, "Chuyên viên dùng hồ sơ có sẵn phải import thành công")
        doc = VanBanDen.objects.filter(so_hieu="801/DEN-EXISTING-HS").first()
        self.assertIsNotNone(doc)
        hs = HoSo.objects.filter(ten_ho_so="Hồ sơ Hành chính - Quản trị").first()
        self.assertTrue(VanBanDenHoSo.objects.filter(vanbanden=doc, hoso_id=hs.id).exists())

    def test_09_user_with_add_hoso_permission_can_auto_create_new_hoso(self):
        """Cán bộ được cấp quyền records.add_hoso (hoặc Văn thư/Admin) tự động tạo mới hồ sơ khi import."""
        from django.contrib.auth.models import Permission

        canbo_with_perm = User.objects.create_user(
            username="canbo_has_perm",
            password="password123",
            email="cb_perm@test.com",
            is_staff=False,
            is_superuser=False,
        )
        perm = Permission.objects.filter(codename="add_hoso").first()
        if perm:
            canbo_with_perm.user_permissions.add(perm)

        wb = openpyxl.load_workbook(generate_excel_template("DI", "NOI_BO"))
        ws = wb.active
        ws.append([
            "901/DI-NEW-HS-OK", "Nội bộ", "30/10/2026", "30/10/2026",
            "Quyết định thành lập ban dự án", "Hồ sơ Dự Án Chuyển Đổi Số 2026", "Quyết định", "BGH",
            "Toàn trường", "Hiệu trưởng", "Hiệu trưởng", "CON_HIEU_LUC", "", "", "",
        ])
        bio = io.BytesIO()
        wb.save(bio)
        bio.seek(0)

        res = import_from_excel(bio, "DI", canbo_with_perm, pham_vi="NOI_BO")
        self.assertEqual(res["created"], 1)

        new_hs = HoSo.objects.filter(ten_ho_so="Hồ sơ Dự Án Chuyển Đổi Số 2026").first()
        self.assertIsNotNone(new_hs)
        doc = VanBanDi.objects.filter(so_hieu="901/DI-NEW-HS-OK").first()
        self.assertTrue(VanBanDiHoSo.objects.filter(vanbandi=doc, hoso_id=new_hs.id).exists())
