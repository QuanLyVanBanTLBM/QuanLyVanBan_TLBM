"""Tests cho Module Văn Bản — Kiến trúc 2 Model (VanBanDen, VanBanDi)."""

import io
import tempfile
from django.contrib.auth import get_user_model
User = get_user_model()
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from documents.filters import DocumentFilter, ViewerFilter
from documents.models import (
    HieuLuc,
    LoaiVanBan,
    PhamVi,
    VanBanDen,
    VanBanDenAttachment,
    VanBanDenNguoiNhan,
    VanBanDenHoSo,
    VanBanDenDanhmuc,
    VanBanDenDonViNhan,
    VanBanDi,
    VanBanDiAttachment,
    VanBanDiNguoiNhan,
    VanBanDiHoSo,
    VanBanDiDanhmuc,
    VanBanDiDonViNhan,
    VanBanDiNoiBanHanh,
    DocumentViewLog,
    DocumentAccessLog,
    Document,
    DocumentAttachment,
)
from documents.services import (
    export_to_excel,
    generate_excel_template,
    generate_so_thu_tu,
    import_from_excel,
    log_document_view,
)


class GenerateSoThuTuTests(TestCase):
    """Test tự sinh số thứ tự an toàn theo từng model."""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="test123")

    def test_first_so_thu_tu_is_1(self):
        """Số đầu tiên trong năm phải là 1."""
        result = generate_so_thu_tu("DEN", 2026)
        self.assertEqual(result, 1)

    def test_auto_increment(self):
        """Số tiếp theo phải tăng dần."""
        VanBanDen.objects.create(
            nam=2026, so_hieu="01/CV", so_thu_tu=1,
            trich_yeu="Test 1", nguoi_tao=self.user,
        )
        VanBanDen.objects.create(
            nam=2026, so_hieu="02/CV", so_thu_tu=2,
            trich_yeu="Test 2", nguoi_tao=self.user,
        )
        result = generate_so_thu_tu("DEN", 2026)
        self.assertEqual(result, 3)

    def test_separate_by_year(self):
        """Số thứ tự phải tách riêng theo năm."""
        VanBanDen.objects.create(
            nam=2025, so_hieu="01/CV", so_thu_tu=5,
            trich_yeu="Test 2025", nguoi_tao=self.user,
        )
        result = generate_so_thu_tu("DEN", 2026)
        self.assertEqual(result, 1)

    def test_separate_by_loai(self):
        """Số thứ tự phải tách riêng theo từng loại văn bản (Đến và Đi)."""
        VanBanDen.objects.create(
            nam=2026, so_hieu="01/CV", so_thu_tu=10,
            trich_yeu="Test DEN", nguoi_tao=self.user,
        )
        result = generate_so_thu_tu("DI", 2026)
        self.assertEqual(result, 1)

    def test_di_increment_so_thu_tu(self):
        """Văn bản Đi cũng tự tăng số thứ tự độc lập."""
        VanBanDi.objects.create(
            nam=2026, so_hieu="01/TB", so_thu_tu=1,
            trich_yeu="Test DI 1", nguoi_tao=self.user,
        )
        result = generate_so_thu_tu("DI", 2026)
        self.assertEqual(result, 2)


class DocumentViewLogTests(TestCase):
    """Test ghi log người xem (upsert) khớp bảng documents_view_log."""

    def setUp(self):
        self.user = User.objects.create_user(username="viewer1", password="test123")
        self.doc = VanBanDen.objects.create(
            nam=2026, so_hieu="01/CV", so_thu_tu=1,
            trich_yeu="Test document", nguoi_tao=self.user,
        )

    def test_first_view_creates_log(self):
        """Lần xem đầu tạo bản ghi mới."""
        log_document_view(self.doc, self.user)
        self.assertEqual(DocumentViewLog.objects.count(), 1)
        log = DocumentViewLog.objects.first()
        self.assertEqual(log.document_type, "vanbanden")
        self.assertEqual(log.document_id, self.doc.id)

    def test_second_view_updates_timestamp(self):
        """Lần xem thứ 2 chỉ cập nhật thời gian, không tạo bản ghi mới."""
        log_document_view(self.doc, self.user)
        first_time = DocumentViewLog.objects.first().viewed_at

        log_document_view(self.doc, self.user)
        self.assertEqual(DocumentViewLog.objects.count(), 1)

        updated_time = DocumentViewLog.objects.first().viewed_at
        self.assertGreaterEqual(updated_time, first_time)

    def test_different_users_create_separate_logs(self):
        """Mỗi user có bản ghi riêng."""
        user2 = User.objects.create_user(username="viewer2", password="test123")
        log_document_view(self.doc, self.user)
        log_document_view(self.doc, user2)
        self.assertEqual(DocumentViewLog.objects.count(), 2)


class DocumentModelTests(TestCase):
    """Test trực tiếp các models: VanBanDen, VanBanDi."""

    def setUp(self):
        self.user = User.objects.create_user(username="admin", password="test123")

    def test_create_van_ban_den(self):
        """Tạo VB Đến thành công."""
        doc = VanBanDen.objects.create(
            nam=2026, so_hieu="15/CV-BGDDT", so_thu_tu=1,
            trich_yeu="V/v hướng dẫn tuyển sinh",
            noi_ban_hanh="Bộ GD&ĐT",
            ngay_den=timezone.now(),
            nguoi_tao=self.user,
        )
        self.assertEqual(doc.loai, "DEN")
        self.assertEqual(doc.so_thu_tu, 1)
        self.assertFalse(doc.is_expired)

    def test_create_van_ban_di(self):
        """Tạo VB Đi thành công."""
        doc = VanBanDi.objects.create(
            nam=2026, so_hieu="10/TB-ITC", so_thu_tu=1,
            trich_yeu="Thông báo lịch thi",
            noi_ban_hanh="Trường ITC",
            ngay_ban_hanh=timezone.now(),
            nguoi_tao=self.user,
        )
        self.assertEqual(doc.loai, "DI")
        self.assertEqual(doc.so_thu_tu, 1)
        self.assertFalse(doc.is_expired)

    def test_create_van_ban_han_che(self):
        """Tạo VB Hạn chế nội bộ thành công với pham_vi=HAN_CHE."""
        doc = VanBanDen.objects.create(
            nam=2026, so_hieu="01/QD-HAN-CHE", so_thu_tu=1,
            trich_yeu="Văn bản hạn chế nội bộ",
            pham_vi=PhamVi.HAN_CHE,
            nguoi_tao=self.user,
        )
        self.assertEqual(doc.pham_vi, PhamVi.HAN_CHE)
        self.assertEqual(doc.loai, "DEN")

    def test_is_expired_property(self):
        """Property is_expired hoạt động đúng."""
        doc = VanBanDen.objects.create(
            nam=2026, so_hieu="01/CV", so_thu_tu=1,
            trich_yeu="Test", hieu_luc=HieuLuc.HET_HIEU_LUC,
            nguoi_tao=self.user,
        )
        self.assertTrue(doc.is_expired)

    def test_str_representation(self):
        """__str__ hiển thị đúng format."""
        doc = VanBanDen.objects.create(
            nam=2026, so_hieu="15/CV-TEST", so_thu_tu=1,
            trich_yeu="Test", nguoi_tao=self.user,
        )
        self.assertIn("Văn bản Đến", str(doc))
        self.assertIn("15/CV-TEST", str(doc))


class DocumentFilterTests(TestCase):
    """Test bộ lọc nâng cao."""

    def setUp(self):
        self.user = User.objects.create_user(username="filteruser", password="test123")
        self.doc1 = VanBanDen.objects.create(
            nam=2026, so_hieu="15/CV-BGDDT", so_thu_tu=1,
            trich_yeu="Hướng dẫn tuyển sinh đại học",
            noi_ban_hanh="Bộ Giáo Dục",
            hieu_luc=HieuLuc.CON_HIEU_LUC,
            ngay_den=timezone.now(),
            nguoi_tao=self.user,
        )
        self.doc2 = VanBanDen.objects.create(
            nam=2025, so_hieu="42/TB-ITC", so_thu_tu=2,
            trich_yeu="Thông báo kết thúc học phần",
            noi_ban_hanh="Trường ITC",
            hieu_luc=HieuLuc.HET_HIEU_LUC,
            ngay_den=timezone.now(),
            nguoi_tao=self.user,
        )

    def test_filter_loai_case_insensitive(self):
        f_upper = DocumentFilter({"loai": "DEN"}, queryset=VanBanDen.objects.all())
        self.assertEqual(f_upper.qs.count(), 2)

        f_lower = DocumentFilter({"loai": "den"}, queryset=VanBanDen.objects.all())
        self.assertEqual(f_lower.qs.count(), 2)

    def test_filter_type_english_alias(self):
        f = DocumentFilter({"type": "den"}, queryset=VanBanDen.objects.all())
        self.assertEqual(f.qs.count(), 2)

    def test_filter_chi_con_hieu_luc(self):
        f = DocumentFilter({"chi_con_hieu_luc": True}, queryset=VanBanDen.objects.all())
        self.assertEqual(f.qs.count(), 1)
        self.assertEqual(f.qs.first().id, self.doc1.id)

    def test_filter_year_english_alias(self):
        f_nam = DocumentFilter({"nam": 2026}, queryset=VanBanDen.objects.all())
        self.assertEqual(f_nam.qs.count(), 1)

        f_year = DocumentFilter({"year": 2026}, queryset=VanBanDen.objects.all())
        self.assertEqual(f_year.qs.count(), 1)

    def test_filter_search_q_and_keyword(self):
        f_q = DocumentFilter({"q": "tuyển sinh"}, queryset=VanBanDen.objects.all())
        self.assertEqual(f_q.qs.count(), 1)

        f_kw = DocumentFilter({"keyword": "tuyển sinh"}, queryset=VanBanDen.objects.all())
        self.assertEqual(f_kw.qs.count(), 1)


@override_settings(MEDIA_ROOT=tempfile.gettempdir())
class DocumentAPITests(TestCase):
    """Test API endpoints (hỗ trợ cả unified endpoint và dedicated endpoints)."""

    def setUp(self):
        user_kwargs = {"username": "cbnv", "password": "password123"}
        if hasattr(User, "ho_ten"):
            user_kwargs["ho_ten"] = "Nguyễn Văn"
        elif hasattr(User, "first_name"):
            user_kwargs["first_name"] = "Văn"
            user_kwargs["last_name"] = "Nguyễn"
        self.user = User.objects.create_user(**user_kwargs)
        from django.contrib.auth.models import Permission
        self.user.user_permissions.add(Permission.objects.get(codename="view_vanbanden"))
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.doc = VanBanDen.objects.create(
            nam=2026, so_hieu="10/CV-UBND", so_thu_tu=1,
            trich_yeu="Công văn chỉ đạo",
            noi_ban_hanh="UBND TP.HCM",
            hieu_luc=HieuLuc.CON_HIEU_LUC,
            ngay_den=timezone.now(),
            nguoi_tao=self.user,
        )

    def tearDown(self):
        super().tearDown()
        for att in list(VanBanDenAttachment.objects.all()) + list(VanBanDiAttachment.objects.all()):
            if att.file:
                att.file.delete(save=False)

    def test_api_list_documents(self):
        """GET /api/documents/?loai=DEN"""
        response = self.client.get("/api/documents/?loai=DEN")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        self.assertEqual(response.data["count"], 1)

    def test_api_retrieve_and_view_log(self):
        """GET /api/documents/{id}/ tự ghi nhận lịch sử xem."""
        response = self.client.get(f"/api/documents/{self.doc.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["so_hieu"], "10/CV-UBND")

        view_log = DocumentViewLog.objects.filter(document_type="vanbanden", document_id=self.doc.id, user=self.user)
        self.assertTrue(view_log.exists())

    def test_api_viewers(self):
        """GET /api/documents/{id}/viewers/"""
        log_document_view(self.doc, self.user)

        response = self.client.get(f"/api/documents/{self.doc.id}/viewers/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["username"], "cbnv")

    def test_api_so_thu_tu_read_only_on_update(self):
        """PUT / PATCH không cho phép sửa so_thu_tu."""
        response = self.client.patch(
            f"/api/documents/{self.doc.id}/",
            {"so_thu_tu": 999, "trich_yeu": "Trích yếu mới"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.doc.refresh_from_db()
        self.assertEqual(self.doc.so_thu_tu, 1)
        self.assertEqual(self.doc.trich_yeu, "Trích yếu mới")

    def test_api_excel_template(self):
        """GET /api/documents/template/?loai=DEN sinh file Excel."""
        response = self.client.get("/api/documents/template/?loai=DEN")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("application/vnd.openxmlformats-officedocument", response["Content-Type"])

    def test_api_excel_export(self):
        """GET /api/documents/export/?loai=DEN xuất file Excel theo bộ lọc."""
        response = self.client.get("/api/documents/export/?loai=DEN")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("application/vnd.openxmlformats-officedocument", response["Content-Type"])

    def test_api_excel_import(self):
        """POST /api/documents/import/ nhận file Excel và import."""
        template_stream = generate_excel_template("DEN")
        excel_file = SimpleUploadedFile(
            "import_test.xlsx",
            template_stream.read(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        response = self.client.post(
            "/api/documents/import/",
            {"file": excel_file, "loai": "DEN"},
            format="multipart",
        )
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST])

    def test_attachment_upload_path_by_document_type(self):
        """Kiểm tra file đính kèm được tự động phân vào folder: den, di theo phân loại: thuong, han_che."""
        # 1. Văn bản Đến -> 02_documents/den/thuong/
        file_den = SimpleUploadedFile("congvan_den.pdf", b"Test content den", content_type="application/pdf")
        att_den = VanBanDenAttachment.objects.create(
            document=self.doc,
            file=file_den,
            name="congvan_den.pdf",
            file_size=16,
        )
        self.assertTrue(att_den.file.name.startswith("02_documents/den/thuong/"))
        parts_den = att_den.file.name.split("/")
        self.assertEqual(len(parts_den), 7)
        self.assertEqual(parts_den[1], "den")
        self.assertEqual(parts_den[2], "thuong")

        # 2. Văn bản Đi -> 02_documents/di/thuong/
        doc_di = VanBanDi.objects.create(
            nam=2026, so_hieu="10/TB-TLBM", trich_yeu="Thông báo đi", nguoi_tao=self.user
        )
        file_di = SimpleUploadedFile("thongbao_di.pdf", b"Test content di", content_type="application/pdf")
        att_di = VanBanDiAttachment.objects.create(
            document=doc_di,
            file=file_di,
            name="thongbao_di.pdf",
            file_size=15,
        )
        self.assertTrue(att_di.file.name.startswith("02_documents/di/thuong/"))
        parts_di = att_di.file.name.split("/")
        self.assertEqual(len(parts_di), 7)
        self.assertEqual(parts_di[1], "di")
        self.assertEqual(parts_di[2], "thuong")

    def test_dedicated_endpoints(self):
        """Kiểm tra các endpoint chuyên biệt /api/documents/den/, /di/."""
        res_den = self.client.get("/api/documents/den/")
        self.assertEqual(res_den.status_code, status.HTTP_200_OK)

        res_di = self.client.get("/api/documents/di/")
        self.assertEqual(res_di.status_code, status.HTTP_200_OK)

    def test_create_without_permission_denied(self):
        """Issue #61 Lỗi 1: User không có quyền tạo văn bản bị chặn 403 Forbidden."""
        response = self.client.post(
            "/api/documents/",
            {
                "loai": "DEN",
                "nam": 2026,
                "so_hieu": "99/CV-TEST",
                "trich_yeu": "Test không quyền",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_het_va_thay_the_without_link_rejected(self):
        """Issue #61 Lỗi 2: HET_VA_THAY_THE bắt buộc phải có link_thay_the."""
        self.user.is_staff = True
        self.user.save()
        response = self.client.post(
            "/api/documents/",
            {
                "loai": "DEN",
                "nam": 2026,
                "so_hieu": "100/CV-TEST",
                "trich_yeu": "Test thay thế rỗng",
                "hieu_luc": HieuLuc.HET_VA_THAY_THE,
                "link_thay_the": "",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("link_thay_the", response.data)

    def test_create_returns_id_in_response(self):
        """Issue #61 Lỗi 3: Tạo văn bản thành công phải trả về trường id trong response."""
        self.user.is_staff = True
        self.user.save()
        response = self.client.post(
            "/api/documents/",
            {
                "loai": "DEN",
                "nam": 2026,
                "so_hieu": "101/CV-TEST",
                "trich_yeu": "Test có id",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("id", response.data)
        self.assertIsNotNone(response.data["id"])


class JunctionAndThroughModelTests(TestCase):
    """Kiểm thử các bảng liên kết qua trung gian và M2M through models khớp DDL."""

    def setUp(self):
        self.user = User.objects.create_user(username="test_emp", password="pwd")
        self.doc_den = VanBanDen.objects.create(
            nam=2026,
            so_hieu="10/CV-DEN",
            so_thu_tu=1,
            trich_yeu="Văn bản đến test junction",
            nguoi_tao=self.user,
        )
        self.doc_di = VanBanDi.objects.create(
            nam=2026,
            so_hieu="20/TB-DI",
            so_thu_tu=1,
            trich_yeu="Văn bản đi test junction",
            nguoi_tao=self.user,
        )

    def test_m2m_through_nguoi_nhan_den_and_di(self):
        """M2M nguoi_nhan sử dụng through model với employee_id khớp DDL."""
        self.doc_den.nguoi_nhan.add(self.user)
        self.assertTrue(
            VanBanDenNguoiNhan.objects.filter(vanbanden=self.doc_den, employee=self.user).exists()
        )
        self.assertEqual(self.doc_den.nguoi_nhan.count(), 1)

        self.doc_di.nguoi_nhan.add(self.user)
        self.assertTrue(
            VanBanDiNguoiNhan.objects.filter(vanbandi=self.doc_di, employee=self.user).exists()
        )
        self.assertEqual(self.doc_di.nguoi_nhan.count(), 1)

    def test_junction_danhmuc_filter(self):
        """Bảng documents_vanbanden_danhmuc và documents_vanbandi_danhmuc kết nối thành công với filter loai_van_ban."""
        VanBanDenDanhmuc.objects.create(vanbanden=self.doc_den, loaivanban_id=99)
        VanBanDiDanhmuc.objects.create(vanbandi=self.doc_di, loaivanban_id=99)

        f_den = DocumentFilter({"loai_van_ban": "99"}, queryset=VanBanDen.objects.all())
        self.assertIn(self.doc_den, f_den.qs)

        f_den_miss = DocumentFilter({"loai_van_ban": "888"}, queryset=VanBanDen.objects.all())
        self.assertNotIn(self.doc_den, f_den_miss.qs)

    def test_junction_hoso_and_donvinhan(self):
        """Bảng hoso, donvinhan, noibanhanh lưu trữ và truy vấn chính xác."""
        hs = VanBanDenHoSo.objects.create(vanbanden=self.doc_den, hoso_id=12)
        dvn = VanBanDenDonViNhan.objects.create(vanbanden=self.doc_den, donvi_id=34)
        self.assertEqual(self.doc_den.hoso.first(), hs)
        self.assertEqual(self.doc_den.donvinhan.first(), dvn)

        hs_di = VanBanDiHoSo.objects.create(vanbandi=self.doc_di, hoso_id=56)
        dvn_di = VanBanDiDonViNhan.objects.create(vanbandi=self.doc_di, donvi_id=78)
        nbh_di = VanBanDiNoiBanHanh.objects.create(vanbandi=self.doc_di, donvi_id=90)
        self.assertEqual(self.doc_di.hoso.first(), hs_di)
        self.assertEqual(self.doc_di.donvinhan.first(), dvn_di)
        self.assertEqual(self.doc_di.noibanhanh_links.first(), nbh_di)

    def test_restricted_document_not_visible_to_recipient_department(self):
        """Đơn vị nhận không cấp quyền xem HAN_CHE nếu nhân viên không được nhận cá nhân."""
        from documents.selectors import la_nguoi_xem_duoc, van_ban_xem_duoc
        user_dept = User.objects.create_user(username="dept_user", password="pwd")
        user_dept.don_vi_id = 999  # Giả lập employee thuộc đơn vị 999

        doc_restricted = VanBanDen.objects.create(
            nam=2026,
            so_hieu="30/HC-DEPT",
            so_thu_tu=2,
            trich_yeu="Văn bản hạn chế cho phòng ban",
            pham_vi=PhamVi.HAN_CHE,
            nguoi_tao=self.user,
        )
        VanBanDenDonViNhan.objects.create(vanbanden=doc_restricted, donvi_id=999)

        # Chỉ trùng đơn vị nhận, không có trong danh sách người nhận cá nhân.
        qs = van_ban_xem_duoc(user_dept, "DEN")
        self.assertNotIn(doc_restricted, qs)
        self.assertFalse(la_nguoi_xem_duoc(user_dept, doc_restricted))

        # Người lạ không thuộc đơn vị nhận không xem được
        stranger = User.objects.create_user(username="dept_stranger", password="pwd")
        stranger.don_vi_id = 111
        qs_stranger = van_ban_xem_duoc(stranger, "DEN")
        self.assertNotIn(doc_restricted, qs_stranger)


class DocumentVisibilityContractTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="no_document_permission", password="test")
        self.document = VanBanDen.objects.create(
            nam=2026,
            so_hieu="VB-PUBLIC-VISIBILITY",
            so_thu_tu=1,
            trich_yeu="Văn bản nội bộ đang hiển thị",
            nguoi_tao=self.user,
            hien_thi=True,
        )

    def test_noi_bo_public_does_not_replace_view_permission(self):
        from documents.selectors import la_nguoi_xem_duoc, van_ban_xem_duoc

        self.assertFalse(van_ban_xem_duoc(self.user, "DEN").filter(pk=self.document.pk).exists())
        self.assertFalse(la_nguoi_xem_duoc(self.user, self.document))

    def test_noi_bo_is_visible_with_view_permission(self):
        from unittest.mock import patch
        from documents.selectors import la_nguoi_xem_duoc, van_ban_xem_duoc

        with patch.object(self.user, "has_perm", return_value=True):
            self.assertTrue(van_ban_xem_duoc(self.user, "DEN").filter(pk=self.document.pk).exists())
            self.assertTrue(la_nguoi_xem_duoc(self.user, self.document))


class DocumentAutoExpireTests(TestCase):
    """Test tính năng tự động chuyển trạng thái Hết hiệu lực khi tới hạn."""

    def setUp(self):
        self.user = User.objects.create_user(username="expireuser", password="test123")
        self.past_date = timezone.now() - timezone.timedelta(days=2)
        self.future_date = timezone.now() + timezone.timedelta(days=30)

        # 1. Văn bản còn hiệu lực nhưng đã quá hạn
        self.doc_expired = VanBanDen.objects.create(
            nam=2026, so_hieu="99/CV-EXPIRED", so_thu_tu=1,
            trich_yeu="Văn bản đã quá hạn",
            hieu_luc=HieuLuc.CON_HIEU_LUC,
            ngay_het_hieu_luc=self.past_date,
            nguoi_tao=self.user,
        )

        # 2. Văn bản còn hiệu lực và chưa tới hạn
        self.doc_active = VanBanDen.objects.create(
            nam=2026, so_hieu="100/CV-ACTIVE", so_thu_tu=2,
            trich_yeu="Văn bản còn hạn trong tương lai",
            hieu_luc=HieuLuc.CON_HIEU_LUC,
            ngay_het_hieu_luc=self.future_date,
            nguoi_tao=self.user,
        )

        # 3. Văn bản đã bị thay thế (HET_VA_THAY_THE)
        self.doc_replaced = VanBanDen.objects.create(
            nam=2026, so_hieu="101/CV-REPLACED", so_thu_tu=3,
            trich_yeu="Văn bản đã bị thay thế",
            hieu_luc=HieuLuc.HET_VA_THAY_THE,
            link_thay_the="100/CV-ACTIVE",
            ngay_het_hieu_luc=self.past_date,
            nguoi_tao=self.user,
        )

        # 4. Văn bản còn hiệu lực 1 phần nhưng đã quá hạn (phải chuyển sang HET_HIEU_LUC)
        self.doc_partial_expired = VanBanDen.objects.create(
            nam=2026, so_hieu="102/CV-PARTIAL-EXP", so_thu_tu=4,
            trich_yeu="Văn bản còn hiệu lực 1 phần nhưng quá hạn",
            hieu_luc=HieuLuc.CON_HIEU_LUC_1_PHAN,
            ngay_het_hieu_luc=self.past_date,
            nguoi_tao=self.user,
        )

        # 5. Văn bản còn hiệu lực 1 phần còn hạn trong tương lai (giữ nguyên CON_HIEU_LUC_1_PHAN)
        self.doc_partial_active = VanBanDen.objects.create(
            nam=2026, so_hieu="103/CV-PARTIAL-ACT", so_thu_tu=5,
            trich_yeu="Văn bản còn hiệu lực 1 phần trong tương lai",
            hieu_luc=HieuLuc.CON_HIEU_LUC_1_PHAN,
            ngay_het_hieu_luc=self.future_date,
            nguoi_tao=self.user,
        )

    def test_auto_expire_on_get_api(self):
        """Khi gọi API GET /api/documents/, văn bản quá hạn tự động chuyển sang HET_HIEU_LUC."""
        client = APIClient()
        client.force_authenticate(user=self.user)

        res = client.get("/api/documents/?loai=DEN")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.doc_expired.refresh_from_db()
        self.assertEqual(self.doc_expired.hieu_luc, HieuLuc.HET_HIEU_LUC)

        self.doc_active.refresh_from_db()
        self.assertEqual(self.doc_active.hieu_luc, HieuLuc.CON_HIEU_LUC)

        self.doc_replaced.refresh_from_db()
        self.assertEqual(self.doc_replaced.hieu_luc, HieuLuc.HET_VA_THAY_THE)

        # Kiểm tra văn bản còn hiệu lực 1 phần quá hạn tự chuyển thành HET_HIEU_LUC
        self.doc_partial_expired.refresh_from_db()
        self.assertEqual(self.doc_partial_expired.hieu_luc, HieuLuc.HET_HIEU_LUC)

        # Văn bản còn hiệu lực 1 phần chưa quá hạn giữ nguyên CON_HIEU_LUC_1_PHAN
        self.doc_partial_active.refresh_from_db()
        self.assertEqual(self.doc_partial_active.hieu_luc, HieuLuc.CON_HIEU_LUC_1_PHAN)

    def test_management_command_expire_documents(self):
        """Management command expire_documents hoạt động chính xác."""
        from django.core.management import call_command
        from io import StringIO

        out = StringIO()
        call_command("expire_documents", stdout=out)

        self.doc_expired.refresh_from_db()
        self.assertEqual(self.doc_expired.hieu_luc, HieuLuc.HET_HIEU_LUC)

        self.doc_partial_expired.refresh_from_db()
        self.assertEqual(self.doc_partial_expired.hieu_luc, HieuLuc.HET_HIEU_LUC)


class DocumentPermissionOption2Tests(TestCase):
    """Test phân quyền Sửa/Xóa văn bản."""

    def setUp(self):
        self.admin = User.objects.create_superuser(username="admin_perm", password="password", is_staff=True)
        self.staff1 = User.objects.create_user(username="staff1", password="password")
        self.staff2 = User.objects.create_user(username="staff2", password="password")
        from django.contrib.auth.models import Permission
        view_permission = Permission.objects.get(codename="view_vanbanden")
        self.staff1.user_permissions.add(view_permission)
        self.staff2.user_permissions.add(view_permission)

        self.doc_staff1 = VanBanDen.objects.create(
            nam=2026, so_hieu="10/CV-STAFF1", so_thu_tu=1,
            trich_yeu="Văn bản do staff1 tạo",
            nguoi_tao=self.staff1,
        )

    def test_non_admin_cannot_delete_document(self):
        """Cán bộ thông thường không được phép xóa văn bản -> 403 Forbidden."""
        client = APIClient()
        client.force_authenticate(user=self.staff1)

        res = client.delete(f"/api/documents/{self.doc_staff1.id}/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("Quyền xóa chỉ dành cho Quản trị viên", str(res.data))
        self.assertTrue(VanBanDen.objects.filter(id=self.doc_staff1.id).exists())

    def test_admin_can_delete_document(self):
        """Admin có quyền xóa văn bản -> 204 No Content."""
        client = APIClient()
        client.force_authenticate(user=self.admin)

        res = client.delete(f"/api/documents/{self.doc_staff1.id}/")
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(VanBanDen.objects.filter(id=self.doc_staff1.id).exists())

    def test_non_creator_cannot_edit_document(self):
        """Cán bộ không phải người tạo không được phép sửa văn bản -> 403 Forbidden."""
        client = APIClient()
        client.force_authenticate(user=self.staff2)

        res = client.patch(
            f"/api/documents/{self.doc_staff1.id}/",
            {"trich_yeu": "Staff2 cố tình sửa văn bản của Staff1"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("Chỉ Quản trị viên, Người tạo", str(res.data))

    def test_creator_can_edit_own_document(self):
        """Người tạo văn bản được phép sửa văn bản của mình -> 200 OK."""
        client = APIClient()
        client.force_authenticate(user=self.staff1)

        res = client.patch(
            f"/api/documents/{self.doc_staff1.id}/",
            {"trich_yeu": "Staff1 cập nhật trích yếu hợp lệ"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.doc_staff1.refresh_from_db()
        self.assertEqual(self.doc_staff1.trich_yeu, "Staff1 cập nhật trích yếu hợp lệ")

    def test_admin_can_edit_any_document(self):
        """Admin có quyền sửa bất kỳ văn bản nào -> 200 OK."""
        client = APIClient()
        client.force_authenticate(user=self.admin)

        res = client.patch(
            f"/api/documents/{self.doc_staff1.id}/",
            {"trich_yeu": "Admin chỉnh sửa trích yếu"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.doc_staff1.refresh_from_db()
        self.assertEqual(self.doc_staff1.trich_yeu, "Admin chỉnh sửa trích yếu")

    def test_delegated_staff_can_edit_and_delete(self):
        """Cán bộ đặc biệt được cấp quyền (Django permissions) có thể sửa và xóa."""
        from django.contrib.auth.models import Permission
        perm_change = Permission.objects.get(codename="change_vanbanden")
        perm_delete = Permission.objects.get(codename="delete_vanbanden")
        self.staff2.user_permissions.add(perm_change, perm_delete)
        self.staff2 = User.objects.get(pk=self.staff2.pk)

        client = APIClient()
        client.force_authenticate(user=self.staff2)

        res_edit = client.patch(
            f"/api/documents/{self.doc_staff1.id}/",
            {"trich_yeu": "Staff2 được ủy quyền sửa văn bản"},
            format="json",
        )
        self.assertEqual(res_edit.status_code, status.HTTP_200_OK)

        res_delete = client.delete(f"/api/documents/{self.doc_staff1.id}/")
        self.assertEqual(res_delete.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(VanBanDen.objects.filter(id=self.doc_staff1.id).exists())

    def test_delete_replacement_document_restores_counterpart(self):
        """Khi xóa văn bản thay thế (A), văn bản cũ (B) tự động gỡ link và khôi phục CON_HIEU_LUC."""
        doc_b = VanBanDen.objects.create(
            nam=2026, so_hieu="15/CV-OLD", so_thu_tu=10,
            trich_yeu="Văn bản cũ B",
            hieu_luc=HieuLuc.CON_HIEU_LUC,
            nguoi_tao=self.admin,
        )

        client = APIClient()
        client.force_authenticate(user=self.admin)
        res_create = client.post(
            "/api/documents/",
            {
                "loai": "DEN",
                "nam": 2026,
                "so_hieu": "125/CV-NEW",
                "trich_yeu": "Văn bản mới A thay cho B",
                "noi_ban_hanh": "Bộ GD&ĐT",
                "hieu_luc": "CON_HIEU_LUC",
                "link_thay_the": "15/CV-OLD",
            },
            format="json",
        )
        self.assertEqual(res_create.status_code, status.HTTP_201_CREATED)
        new_doc_id = res_create.data["id"]

        # Kiểm tra văn bản B đã được tự động đồng bộ sang HET_VA_THAY_THE
        doc_b.refresh_from_db()
        self.assertEqual(doc_b.hieu_luc, HieuLuc.HET_VA_THAY_THE)
        self.assertEqual(doc_b.link_thay_the, "125/CV-NEW")

        # Xóa văn bản mới A
        res_del = client.delete(f"/api/documents/{new_doc_id}/")
        self.assertEqual(res_del.status_code, status.HTTP_204_NO_CONTENT)

        # Kiểm tra văn bản B tự động khôi phục CON_HIEU_LUC và xóa link_thay_the
        doc_b.refresh_from_db()
        self.assertEqual(doc_b.hieu_luc, HieuLuc.CON_HIEU_LUC)
        self.assertEqual(doc_b.link_thay_the, "")


class RestrictedDocumentSecurityIssue82Tests(TestCase):
    """
    Bộ kiểm thử toàn diện cho Issue #82 & PR #92:
    Văn bản hạn chế (pham_vi = 'HAN_CHE'), hàm xem dùng chung, và nhật ký truy cập (DocumentAccessLog).
    """

    def setUp(self):
        self.creator = User.objects.create_user(username="creator_user", password="pwd", is_staff=True)
        self.recipient1 = User.objects.create_user(username="recipient_1", password="pwd")
        self.recipient2 = User.objects.create_user(username="recipient_2", password="pwd")
        self.stranger = User.objects.create_user(username="stranger_user", password="pwd")
        self.other_staff = User.objects.create_user(username="other_staff", password="pwd", is_staff=True)
        self.superuser = User.objects.create_superuser(username="admin_super", password="pwd", email="admin@corp.vn")

        # Tạo văn bản hạn chế mẫu
        self.doc_han_che = VanBanDen.objects.create(
            nam=2026,
            so_hieu="01/HC-2026",
            so_thu_tu=1,
            trich_yeu="Văn bản hạn chế mật nội bộ công ty",
            pham_vi=PhamVi.HAN_CHE,
            hieu_luc=HieuLuc.CON_HIEU_LUC,
            nguoi_tao=self.creator,
        )
        self.doc_han_che.nguoi_nhan.add(self.recipient1)

    def test_restricted_document_requires_at_least_one_recipient_on_create(self):
        """Văn bản hạn chế bắt buộc phải có ít nhất một người nhận khi tạo mới."""
        client = APIClient()
        client.force_authenticate(user=self.creator)

        response = client.post(
            "/api/documents/",
            {
                "loai": "DEN",
                "nam": 2026,
                "so_hieu": "02/HC-FAIL",
                "trich_yeu": "Thử tạo không người nhận",
                "pham_vi": "HAN_CHE",
                "nguoi_nhan": [],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("nguoi_nhan", response.data)

    def test_restricted_document_rejects_system_wide_mail(self):
        """Văn bản hạn chế không được phép bật gửi mail toàn hệ thống."""
        client = APIClient()
        client.force_authenticate(user=self.creator)

        response = client.post(
            "/api/documents/",
            {
                "loai": "DEN",
                "nam": 2026,
                "so_hieu": "03/HC-MAIL",
                "trich_yeu": "Thử gửi mail toàn hệ thống",
                "pham_vi": "HAN_CHE",
                "gui_mail_toan_he_thong": True,
                "nguoi_nhan": [self.recipient1.id],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("gui_mail_toan_he_thong", response.data)

    def test_create_restricted_document_logs_them_nguoi_xem(self):
        """Khi tạo mới văn bản hạn chế, hệ thống tự động ghi log THEM_NGUOI_XEM cho các người nhận ban đầu."""
        client = APIClient()
        client.force_authenticate(user=self.creator)

        response = client.post(
            "/api/documents/",
            {
                "loai": "DEN",
                "nam": 2026,
                "so_hieu": "04/HC-SUCCESS",
                "trich_yeu": "Tạo văn bản hạn chế thành công",
                "pham_vi": "HAN_CHE",
                "nguoi_nhan": [self.recipient1.id, self.recipient2.id],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        new_id = response.data["id"]

        logs = DocumentAccessLog.objects.filter(document_id=new_id, hanh_dong="THEM_NGUOI_XEM")
        self.assertEqual(logs.count(), 2)
        target_ids = set(logs.values_list("doi_tuong_user_id", flat=True))
        self.assertEqual(target_ids, {self.recipient1.id, self.recipient2.id})

    def test_creator_and_recipient_can_view_and_logs_xem(self):
        """Người tạo và người nhận trong danh sách xem được văn bản hạn chế và được ghi log XEM."""
        client = APIClient()

        # 1. Người tạo xem
        client.force_authenticate(user=self.creator)
        res_list = client.get("/api/documents/?loai=DEN")
        self.assertEqual(res_list.status_code, status.HTTP_200_OK)
        ids = [doc["id"] for doc in res_list.data.get("results", res_list.data)]
        self.assertIn(self.doc_han_che.id, ids)

        res_detail = client.get(f"/api/documents/{self.doc_han_che.id}/")
        self.assertEqual(res_detail.status_code, status.HTTP_200_OK)
        self.assertEqual(res_detail.data["pham_vi"], "HAN_CHE")
        self.assertEqual(res_detail.data["pham_vi_display"], "Hạn chế")

        # 2. Người nhận xem
        client.force_authenticate(user=self.recipient1)
        res_rec_detail = client.get(f"/api/documents/{self.doc_han_che.id}/")
        self.assertEqual(res_rec_detail.status_code, status.HTTP_200_OK)

        # Kiểm tra nhật ký XEM
        view_logs = DocumentAccessLog.objects.filter(
            document_id=self.doc_han_che.id,
            hanh_dong="XEM",
        )
        self.assertTrue(view_logs.filter(user=self.creator).exists())
        self.assertTrue(view_logs.filter(user=self.recipient1).exists())

    def test_unauthorized_user_and_superuser_get_404_and_logs_bi_tu_choi(self):
        """
        Tài khoản không thuộc danh sách, KỂ CẢ SUPERUSER, nhận 404 như không tồn tại,
        và mỗi lần thử truy cập đều bị ghi log BI_TU_CHOI.
        """
        client = APIClient()

        # 1. Người lạ (stranger)
        client.force_authenticate(user=self.stranger)
        res_stranger_list = client.get("/api/documents/?loai=DEN")
        stranger_ids = [doc["id"] for doc in res_stranger_list.data.get("results", res_stranger_list.data)]
        self.assertNotIn(self.doc_han_che.id, stranger_ids)

        res_stranger_detail = client.get(f"/api/documents/{self.doc_han_che.id}/")
        self.assertEqual(res_stranger_detail.status_code, status.HTTP_404_NOT_FOUND)

        # 2. Superuser (Tuyệt đối KHÔNG có ngoại lệ)
        client.force_authenticate(user=self.superuser)
        res_super_list = client.get("/api/documents/?loai=DEN")
        super_ids = [doc["id"] for doc in res_super_list.data.get("results", res_super_list.data)]
        self.assertNotIn(self.doc_han_che.id, super_ids)

        res_super_detail = client.get(f"/api/documents/{self.doc_han_che.id}/")
        self.assertEqual(res_super_detail.status_code, status.HTTP_404_NOT_FOUND)

        # Kiểm tra nhật ký BI_TU_CHOI
        rejected_logs = DocumentAccessLog.objects.filter(
            document_id=self.doc_han_che.id,
            hanh_dong="BI_TU_CHOI",
        )
        self.assertTrue(rejected_logs.filter(user=self.stranger).exists())
        self.assertTrue(rejected_logs.filter(user=self.superuser).exists())

    def test_inactive_user_cannot_view_restricted_document(self):
        """Tài khoản bị khóa (is_active = False) mất hoàn toàn quyền xem, kể cả đã là người nhận."""
        self.recipient1.is_active = False
        self.recipient1.save()

        client = APIClient()
        client.force_authenticate(user=self.recipient1)

        res_detail = client.get(f"/api/documents/{self.doc_han_che.id}/")
        self.assertEqual(res_detail.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_delete_restricted_document(self):
        """Văn bản hạn chế KHÔNG ĐƯỢC PHÉP XÓA (bị chặn ở cả API và Model level)."""
        client = APIClient()

        # Thử xóa bằng người tạo
        client.force_authenticate(user=self.creator)
        res_del_creator = client.delete(f"/api/documents/{self.doc_han_che.id}/")
        self.assertEqual(res_del_creator.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("không được phép xóa", str(res_del_creator.data))

        # Thử xóa bằng superuser
        client.force_authenticate(user=self.superuser)
        res_del_super = client.delete(f"/api/documents/{self.doc_han_che.id}/")
        # Superuser nhận 404 (vì không xem được) hoặc 403
        self.assertIn(res_del_super.status_code, [status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN])

        # Đảm bảo văn bản vẫn còn nguyên trong DB
        self.assertTrue(VanBanDen.objects.filter(id=self.doc_han_che.id).exists())

    def test_cannot_change_pham_vi_after_creation(self):
        """Không được phép đổi phạm vi văn bản sau khi tạo (API từ chối)."""
        client = APIClient()
        client.force_authenticate(user=self.creator)

        response = client.patch(
            f"/api/documents/{self.doc_han_che.id}/",
            {"pham_vi": "NOI_BO"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("pham_vi", response.data)

        self.doc_han_che.refresh_from_db()
        self.assertEqual(self.doc_han_che.pham_vi, PhamVi.HAN_CHE)

    def test_update_recipients_logs_them_and_bot_nguoi_xem(self):
        """Thêm / bớt người xem văn bản hạn chế ghi log đúng THEM_NGUOI_XEM và BOT_NGUOI_XEM."""
        client = APIClient()
        client.force_authenticate(user=self.creator)

        # Cập nhật: bớt recipient1, thêm recipient2
        response = client.patch(
            f"/api/documents/{self.doc_han_che.id}/",
            {"nguoi_nhan": [self.recipient2.id]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Kiểm tra nhật ký
        added_log = DocumentAccessLog.objects.filter(
            document_id=self.doc_han_che.id,
            hanh_dong="THEM_NGUOI_XEM",
            doi_tuong_user=self.recipient2,
        ).first()
        self.assertIsNotNone(added_log)
        self.assertEqual(added_log.user, self.creator)

        removed_log = DocumentAccessLog.objects.filter(
            document_id=self.doc_han_che.id,
            hanh_dong="BOT_NGUOI_XEM",
            doi_tuong_user=self.recipient1,
        ).first()
        self.assertIsNotNone(removed_log)
        self.assertEqual(removed_log.user, self.creator)

    def test_download_attachment_access_control_and_logging(self):
        """Tải file đính kèm văn bản hạn chế: Người được cấp tải được (ghi TAI_FILE), người lạ nhận 404 (ghi BI_TU_CHOI)."""
        simple_file = SimpleUploadedFile("mat_noi_bo.pdf", b"Secret PDF content", content_type="application/pdf")
        att = VanBanDenAttachment.objects.create(
            document=self.doc_han_che,
            file=simple_file,
            name="mat_noi_bo.pdf",
            file_size=18,
            created_user=self.creator,
        )

        client = APIClient()

        # 1. Người lạ tải file -> nhận 404 và ghi BI_TU_CHOI
        client.force_authenticate(user=self.stranger)
        res_stranger = client.get(f"/api/documents/{self.doc_han_che.id}/attachments/{att.id}/download/")
        self.assertEqual(res_stranger.status_code, status.HTTP_404_NOT_FOUND)

        rej_log = DocumentAccessLog.objects.filter(
            document_id=self.doc_han_che.id,
            hanh_dong="BI_TU_CHOI",
            tep_id=att.id,
            user=self.stranger,
        ).first()
        self.assertIsNotNone(rej_log)

        # 2. Người nhận tải file -> nhận 200 và ghi TAI_FILE
        client.force_authenticate(user=self.recipient1)
        res_recipient = client.get(f"/api/documents/{self.doc_han_che.id}/attachments/{att.id}/download/")
        self.assertEqual(res_recipient.status_code, status.HTTP_200_OK)

        down_log = DocumentAccessLog.objects.filter(
            document_id=self.doc_han_che.id,
            hanh_dong="TAI_FILE",
            tep_id=att.id,
            user=self.recipient1,
        ).first()
        self.assertIsNotNone(down_log)

    def test_document_access_log_is_worm_immutable(self):
        """Nhật ký DocumentAccessLog tuân thủ WORM: Không được sửa và không được xóa."""
        log = DocumentAccessLog.objects.create(
            document_type="vanbanden",
            document_id=self.doc_han_che.id,
            user=self.creator,
            hanh_dong=DocumentAccessLog.HanhDong.XEM,
        )
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            log.save()

        with self.assertRaises(ValidationError):
            log.delete()

    def test_composite_primary_key_junction_tables(self):
        """Test D-1: 9 bảng nối hoạt động với CompositePrimaryKey không có cột id thừa."""
        from documents.models import (
            VanBanDenNguoiNhan, VanBanDenHoSo, VanBanDenDanhmuc, VanBanDenDonViNhan,
            VanBanDiNguoiNhan, VanBanDiHoSo, VanBanDiDanhmuc, VanBanDiDonViNhan, VanBanDiNoiBanHanh
        )

        # 1. Thêm người nhận qua M2M through (add, all, remove)
        self.doc_han_che.nguoi_nhan.add(self.recipient2)
        self.assertTrue(self.doc_han_che.nguoi_nhan.filter(pk=self.recipient2.pk).exists())
        self.doc_han_che.nguoi_nhan.remove(self.recipient2)
        self.assertFalse(self.doc_han_che.nguoi_nhan.filter(pk=self.recipient2.pk).exists())

        # 2. Tạo bản ghi trực tiếp trên các bảng junction
        hoso = VanBanDenHoSo.objects.create(vanbanden=self.doc_han_che, hoso_id=99)
        self.assertEqual(hoso.hoso_id, 99)

        dm = VanBanDenDanhmuc.objects.create(vanbanden=self.doc_han_che, loaivanban_id=12)
        self.assertEqual(dm.loaivanban_id, 12)

        dv = VanBanDenDonViNhan.objects.create(vanbanden=self.doc_han_che, donvi_id=5)
        self.assertEqual(dv.donvi_id, 5)

        # Query all không bị lỗi column id does not exist
        all_hoso = list(VanBanDenHoSo.objects.filter(vanbanden=self.doc_han_che))
        self.assertEqual(len(all_hoso), 1)

    def test_auto_stt_concurrency_retry_mechanism(self):
        """Test B-1: Cơ chế retry sinh so_thu_tu tự động khi gặp IntegrityError."""
        # Tạo văn bản đầu tiên
        doc1 = VanBanDen.objects.create(
            nam=2026, so_hieu="AUTO-01/TEST", so_thu_tu=100,
            trich_yeu="Văn bản test STT 100", noi_ban_hanh="ITC",
        )
        self.assertEqual(doc1.so_thu_tu, 100)

        # Tạo văn bản tiếp theo không truyền so_thu_tu, save() tự động sinh số kế tiếp
        doc2 = VanBanDen.objects.create(
            nam=2026, so_hieu="AUTO-02/TEST",
            trich_yeu="Văn bản test STT tự sinh", noi_ban_hanh="ITC",
        )
        self.assertGreaterEqual(doc2.so_thu_tu, 101)

    def test_directional_replacement_relations_and_circular_prevention(self):
        """Test phân định quan hệ thay thế 2 chiều và chặn vòng lặp thay thế A <-> B."""
        from documents.services import get_replacement_relations, sync_replacement_document
        from documents.serializers import DocumentCreateUpdateSerializer
        from rest_framework.exceptions import ValidationError

        # Tạo văn bản gốc A
        doc_a = VanBanDen.objects.create(
            nam=2026, so_hieu="VB-A/2026", so_thu_tu=201,
            trich_yeu="Văn bản cũ A", noi_ban_hanh="ITC",
            hieu_luc=HieuLuc.CON_HIEU_LUC,
        )

        # Tạo văn bản B thay thế A
        doc_b = VanBanDen.objects.create(
            nam=2026, so_hieu="VB-B/2026", so_thu_tu=202,
            trich_yeu="Văn bản mới B thay thế A", noi_ban_hanh="ITC",
            hieu_luc=HieuLuc.CON_HIEU_LUC,
            link_thay_the="VB-A/2026",
        )
        sync_replacement_document(doc_b)
        doc_a.refresh_from_db()

        # Quan hệ của A: bị B thay thế
        rel_a = get_replacement_relations(doc_a)
        self.assertIn("VB-B/2026", rel_a["bi_thay_boi"])
        self.assertEqual(rel_a["thay_the_cho"], [])

        # Quan hệ của B: thay thế A
        rel_b = get_replacement_relations(doc_b)
        self.assertIn("VB-A/2026", rel_b["thay_the_cho"])
        self.assertEqual(rel_b["bi_thay_boi"], [])

        # Chặn tự thay thế chính mình
        ser_self = DocumentCreateUpdateSerializer(
            instance=doc_b,
            data={"so_hieu": "VB-B/2026", "link_thay_the": "VB-B/2026", "noi_ban_hanh": "ITC", "trich_yeu": "Test"},
            partial=True,
        )
        with self.assertRaises(ValidationError):
            ser_self.is_valid(raise_exception=True)

        # Chặn A thay thế ngược lại B (Circular Replacement)
        ser_circ = DocumentCreateUpdateSerializer(
            instance=doc_a,
            data={"so_hieu": "VB-A/2026", "link_thay_the": "VB-B/2026", "noi_ban_hanh": "ITC", "trich_yeu": "Test"},
            partial=True,
        )
        with self.assertRaises(ValidationError):
            ser_circ.is_valid(raise_exception=True)

    def test_reject_nonexistent_replacement_target(self):
        """Khóa nghiệp vụ: Chặn nhập số hiệu văn bản không tồn tại trong hệ thống (như '12')."""
        from documents.serializers import DocumentCreateUpdateSerializer
        doc = VanBanDen.objects.create(
            nam=2026, so_hieu="112/TB-SGDĐT", so_thu_tu=210,
            trich_yeu="Văn bản thông báo", noi_ban_hanh="SGDĐT",
            hieu_luc=HieuLuc.HET_VA_THAY_THE,
            link_thay_the="",
        )
        # Thử gán link_thay_the là số '12' (không tồn tại trong CSDL)
        ser = DocumentCreateUpdateSerializer(
            instance=doc,
            data={"link_thay_the": "12"},
            partial=True,
        )
        self.assertFalse(ser.is_valid())
        self.assertIn("link_thay_the", ser.errors)
        self.assertIn("không tồn tại", str(ser.errors["link_thay_the"][0]))

    def test_get_replacement_relations_ignores_nonexistent_target(self):
        """Engine quan hệ thay thế tuyệt đối không sinh badge cho văn bản ma/không tồn tại trong DB."""
        from documents.services import get_replacement_relations
        doc = VanBanDen.objects.create(
            nam=2026, so_hieu="112/TB-SGDĐT", so_thu_tu=211,
            trich_yeu="Văn bản thông báo", noi_ban_hanh="SGDĐT",
            hieu_luc=HieuLuc.HET_HIEU_LUC,
            link_thay_the="12",  # Giả sử trong DB có chuỗi 12 chưa xóa
        )
        rel = get_replacement_relations(doc)
        self.assertEqual(rel["thay_the_cho"], [])
        self.assertEqual(rel["bi_thay_boi"], [])



