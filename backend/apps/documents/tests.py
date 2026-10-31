"""Tests cho Module Văn Bản — Kiến trúc 2 Model (VanBanDen, VanBanDi)."""

import atexit
import io
import shutil
import tempfile
from pathlib import Path
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
try:
    from organizations.models import DonVi
except ImportError:
    DonVi = None

try:
    from records.models import HoSo, LoaiVanBan as RecordLoaiVanBan
except ImportError:
    HoSo = None
    RecordLoaiVanBan = None

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
    VanBanMat,
    VanBanMatAttachment,
    VanBanMatNguoiNhan,
    VanBanMatHoSo,
    VanBanMatDanhmuc,
    VanBanMatDonViNhan,
    VanBanMatNoiBanHanh,
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

User = get_user_model()

TEMP_STORAGE_ROOT = tempfile.mkdtemp(prefix="documents-tests-")
atexit.register(shutil.rmtree, TEMP_STORAGE_ROOT, ignore_errors=True)


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
        self.user = User.objects.create_user(username="documents_admin_test", password="test123")

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


@override_settings(DOCUMENT_STORAGE_ROOT=TEMP_STORAGE_ROOT)
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
        """GET /api/documents/export/?loai=DEN xuất file Excel theo bộ lọc (khi có quyền)."""
        self.user.is_staff = True
        self.user.save()
        response = self.client.get("/api/documents/export/?loai=DEN")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("application/vnd.openxmlformats-officedocument", response["Content-Type"])

    def test_api_excel_export_without_permission_denied(self):
        """GET /api/documents/export/?loai=DEN trả về 403 nếu không có quyền export."""
        self.user.is_staff = False
        self.user.save()
        response = self.client.get("/api/documents/export/?loai=DEN")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_api_excel_import(self):
        """POST /api/documents/import/ nhận file Excel và import (khi có quyền)."""
        self.user.is_staff = True
        self.user.save()
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

    def test_api_excel_import_without_permission_denied(self):
        """POST /api/documents/import/ trả về 403 nếu không có quyền import."""
        self.user.is_staff = False
        self.user.save()
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
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_attachment_upload_path_by_document_type(self):
        """Kiểm tra file đính kèm được tự động phân vào folder: den, di theo phân loại: thuong, han_che."""
        # 1. Văn bản Đến -> van-ban-den/YYYY/MM/DD/<uuid>.pdf
        file_den = SimpleUploadedFile("congvan_den.pdf", b"Test content den", content_type="application/pdf")
        att_den = VanBanDenAttachment.objects.create(
            document=self.doc,
            file=file_den,
            name="congvan_den.pdf",
            file_size=16,
        )
        today = timezone.localdate()
        self.assertRegex(att_den.file.name, rf"^van-ban-den/(?:noi-bo/)?{today:%Y/%m/%d}/[0-9a-f]{{32}}\.pdf$")
        self.assertEqual((Path(TEMP_STORAGE_ROOT) / att_den.file.name).read_bytes(), b"Test content den")
        self.assertEqual(att_den.file.url, f"/media/{att_den.file.name}")
        self.assertEqual(att_den.name, "congvan_den.pdf")

        # 2. Văn bản Đi -> van-ban-di/YYYY/MM/DD/<uuid>.pdf
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
        self.assertRegex(att_di.file.name, rf"^van-ban-di/(?:noi-bo/)?{today:%Y/%m/%d}/[0-9a-f]{{32}}\.pdf$")
        self.assertTrue((Path(TEMP_STORAGE_ROOT) / att_di.file.name).is_file())

    def test_create_with_attachment_stores_in_shared_tree_and_downloads(self):
        self.user.is_staff = True
        self.user.save()
        response = self.client.post(
            "/api/documents/",
            {
                "loai": "DEN", "nam": 2026, "so_hieu": "55/CV-TEST", "trich_yeu": "Có tệp",
                "files": SimpleUploadedFile("Công văn.PDF", b"%PDF-1.4 noi dung", content_type="application/pdf"),
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        att = VanBanDenAttachment.objects.get(document_id=response.data["id"])
        self.assertEqual(att.name, "Công văn.PDF")
        self.assertRegex(att.file.name, r"^van-ban-den/(?:noi-bo/)?\d{4}/\d{2}/\d{2}/[0-9a-f]{32}\.pdf$")
        download = self.client.get(f"/api/documents/{att.document_id}/attachments/{att.id}/download/")
        self.assertEqual(download.status_code, status.HTTP_200_OK)
        self.assertEqual(download.content, b"%PDF-1.4 noi dung")

    def test_create_rejects_disallowed_extension_without_creating_document(self):
        self.user.is_staff = True
        self.user.save()
        before = VanBanDen.objects.count()
        response = self.client.post(
            "/api/documents/",
            {
                "loai": "DEN", "nam": 2026, "so_hieu": "56/CV-TEST", "trich_yeu": "Tệp sai định dạng",
                "files": SimpleUploadedFile("chay.exe", b"MZ", content_type="application/octet-stream"),
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(VanBanDen.objects.count(), before)
        self.assertFalse(VanBanDenAttachment.objects.exists())

    def test_download_missing_file_returns_404(self):
        att = VanBanDenAttachment.objects.create(document=self.doc, file="van-ban-den/2026/01/01/khong-con.pdf", name="a.pdf")
        response = self.client.get(f"/api/documents/{self.doc.id}/attachments/{att.id}/download/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

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
        hoso = HoSo.objects.get(is_he_thong=True)
        category = RecordLoaiVanBan.objects.create(ho_so=hoso, ten_loai="Loại văn bản junction")
        VanBanDenDanhmuc.objects.create(vanbanden=self.doc_den, loaivanban_id=category.pk)
        VanBanDiDanhmuc.objects.create(vanbandi=self.doc_di, loaivanban_id=category.pk)

        f_den = DocumentFilter({"loai_van_ban": str(category.pk)}, queryset=VanBanDen.objects.all())
        self.assertIn(self.doc_den, f_den.qs)

        f_den_miss = DocumentFilter({"loai_van_ban": "888"}, queryset=VanBanDen.objects.all())
        self.assertNotIn(self.doc_den, f_den_miss.qs)

    def test_junction_hoso_and_donvinhan(self):
        """Bảng hoso, donvinhan, noibanhanh lưu trữ và truy vấn chính xác."""
        hoso_id = HoSo.objects.get(is_he_thong=True).pk
        donvi_id = DonVi.objects.order_by("id").first().pk
        hs = VanBanDenHoSo.objects.create(vanbanden=self.doc_den, hoso_id=hoso_id)
        dvn = VanBanDenDonViNhan.objects.create(vanbanden=self.doc_den, donvi_id=donvi_id)
        self.assertEqual(self.doc_den.hoso.first(), hs)
        self.assertEqual(self.doc_den.donvinhan.first(), dvn)

        hs_di = VanBanDiHoSo.objects.create(vanbandi=self.doc_di, hoso_id=hoso_id)
        dvn_di = VanBanDiDonViNhan.objects.create(vanbandi=self.doc_di, donvi_id=donvi_id)
        nbh_di = VanBanDiNoiBanHanh.objects.create(vanbandi=self.doc_di, donvi_id=donvi_id)
        self.assertEqual(self.doc_di.hoso.first(), hs_di)
        self.assertEqual(self.doc_di.donvinhan.first(), dvn_di)
        self.assertEqual(self.doc_di.noibanhanh_links.first(), nbh_di)

    def test_restricted_document_visible_to_recipient_department(self):
        """Văn bản hạn chế xem được bởi CBNV thuộc đơn vị nhận (donvinhan)."""
        from documents.selectors import van_ban_xem_duoc
        department, other_department = list(DonVi.objects.order_by("id")[:2])
        user_dept = User.objects.create_user(username="dept_user", password="pwd")
        user_dept.don_vi_id = department.pk

        doc_restricted = VanBanDen.objects.create(
            nam=2026,
            so_hieu="30/HC-DEPT",
            so_thu_tu=2,
            trich_yeu="Văn bản hạn chế cho phòng ban",
            pham_vi=PhamVi.HAN_CHE,
            nguoi_tao=self.user,
        )
        VanBanDenDonViNhan.objects.create(vanbanden=doc_restricted, donvi_id=department.pk)

        # CBNV thuộc đơn vị nhận xem được
        qs = van_ban_xem_duoc(user_dept, "DEN")
        self.assertIn(doc_restricted, qs)

        # Người lạ không thuộc đơn vị nhận không xem được
        stranger = User.objects.create_user(username="dept_stranger", password="pwd")
        stranger.don_vi_id = other_department.pk
        qs_stranger = van_ban_xem_duoc(stranger, "DEN")
        self.assertNotIn(doc_restricted, qs_stranger)


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

        self.doc_staff1 = VanBanDen.objects.create(
            nam=2026, so_hieu="10/CV-STAFF1", so_thu_tu=1,
            trich_yeu="Văn bản do staff1 tạo",
            nguoi_tao=self.staff1,
        )

    def test_non_admin_cannot_delete_document(self):
        """Cán bộ không phải người tạo không được phép xóa văn bản -> 403 Forbidden."""
        client = APIClient()
        client.force_authenticate(user=self.staff2)

        res = client.delete(f"/api/documents/{self.doc_staff1.id}/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(VanBanDen.objects.filter(id=self.doc_staff1.id).exists())

    def test_creator_can_delete_own_active_document(self):
        """Người tạo có quyền xóa văn bản còn hiệu lực do mình tạo -> 204 No Content."""
        client = APIClient()
        client.force_authenticate(user=self.staff1)

        res = client.delete(f"/api/documents/{self.doc_staff1.id}/")
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(VanBanDen.objects.filter(id=self.doc_staff1.id).exists())

    def test_creator_cannot_delete_expired_document(self):
        """Người tạo không được phép xóa văn bản đã hết hiệu lực (chỉ Admin mới được xóa) -> 403 Forbidden."""
        doc_exp = VanBanDen.objects.create(
            nam=2026, so_hieu="11/CV-STAFF1-EXP", so_thu_tu=2,
            trich_yeu="Văn bản hết hạn",
            hieu_luc=HieuLuc.HET_HIEU_LUC,
            nguoi_tao=self.staff1,
        )
        client = APIClient()
        client.force_authenticate(user=self.staff1)

        res = client.delete(f"/api/documents/{doc_exp.id}/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(VanBanDen.objects.filter(id=doc_exp.id).exists())

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

        # Kiểm tra văn bản B đã được tự động đồng bộ sang CON_HIEU_LUC_1_PHAN (Phương án A)
        doc_b.refresh_from_db()
        self.assertIn(doc_b.hieu_luc, (HieuLuc.CON_HIEU_LUC_1_PHAN, HieuLuc.HET_HIEU_LUC, HieuLuc.HET_VA_THAY_THE))
        self.assertIn("125/CV-NEW", doc_b.link_thay_the)

        # Xóa văn bản mới A
        res_del = client.delete(f"/api/documents/{new_doc_id}/")
        self.assertEqual(res_del.status_code, status.HTTP_204_NO_CONTENT)

        # Kiểm tra văn bản B tự động khôi phục CON_HIEU_LUC và xóa link_thay_the
        doc_b.refresh_from_db()
        self.assertEqual(doc_b.hieu_luc, HieuLuc.CON_HIEU_LUC)
        self.assertEqual(doc_b.link_thay_the, "")


@override_settings(DOCUMENT_STORAGE_ROOT=TEMP_STORAGE_ROOT)
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
        hoso_id = HoSo.objects.get(is_he_thong=True).pk
        category = RecordLoaiVanBan.objects.create(ho_so_id=hoso_id, ten_loai="Loại văn bản bảo mật")
        donvi_id = DonVi.objects.order_by("id").first().pk
        hoso = VanBanDenHoSo.objects.create(vanbanden=self.doc_han_che, hoso_id=hoso_id)
        self.assertEqual(hoso.hoso_id, hoso_id)

        dm = VanBanDenDanhmuc.objects.create(vanbanden=self.doc_han_che, loaivanban_id=category.pk)
        self.assertEqual(dm.loaivanban_id, category.pk)

        dv = VanBanDenDonViNhan.objects.create(vanbanden=self.doc_han_che, donvi_id=donvi_id)
        self.assertEqual(dv.donvi_id, donvi_id)

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

        # Cho phép người điều chỉnh cập nhật văn bản bị thay thế ở trạng thái CON_HIEU_LUC_1_PHAN (Phương án A)
        ser_allow_partial = DocumentCreateUpdateSerializer(
            instance=doc_a,
            data={"so_hieu": "VB-A/2026", "link_thay_the": "VB-B/2026", "hieu_luc": HieuLuc.CON_HIEU_LUC_1_PHAN, "noi_ban_hanh": "ITC", "trich_yeu": "Cập nhật bình thường"},
            partial=True,
        )
        self.assertTrue(ser_allow_partial.is_valid())

    def test_reject_nonexistent_replacement_target(self):
        """Khóa nghiệp vụ: Chặn nhập số hiệu văn bản không tồn tại trong hệ thống (như '12')."""
        from documents.serializers import DocumentCreateUpdateSerializer
        doc = VanBanDen.objects.create(
            nam=2026, so_hieu="112/TB-SGDĐT", so_thu_tu=210,
            trich_yeu="Văn bản thông báo", noi_ban_hanh="SGDĐT",
            hieu_luc=HieuLuc.CON_HIEU_LUC,
            link_thay_the="",
        )
        # Thử gán link_thay_the là số '12' (không tồn tại trong CSDL)
        ser = DocumentCreateUpdateSerializer(
            instance=doc,
            data={"hieu_luc": HieuLuc.HET_VA_THAY_THE, "link_thay_the": "12"},
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


class DocumentPhamViFilterTests(TestCase):
    """
    Test suite kiểm tra bộ lọc pham_vi (HAN_CHE / NOI_BO) theo contract điều hướng của Nhóm 3 (PR #131).
    Đảm bảo:
    - Lọc đúng pham_vi=HAN_CHE và pham_vi=NOI_BO cho cả Văn bản Đến và Đi.
    - Bảo mật RBAC tuyệt đối: Chỉ người tạo/người nhận/đơn vị nhận mới thấy văn bản HAN_CHE.
    - Người không có quyền (stranger) khi gọi pham_vi=HAN_CHE nhận count = 0, không lộ metadata.
    - Phân trang (pagination) và count tính toán chính xác trên tập đã lọc.
    """

    def setUp(self):
        self.creator = User.objects.create_user(username="creator_pv", password="pwd", is_staff=True)
        self.recipient = User.objects.create_user(username="recipient_pv", password="pwd")
        self.stranger = User.objects.create_user(username="stranger_pv", password="pwd")

        # Văn bản đến: 1 nội bộ, 1 hạn chế
        self.doc_den_noibo = VanBanDen.objects.create(
            nam=2026, so_hieu="01/NB-DEN", so_thu_tu=1,
            trich_yeu="Văn bản đến nội bộ thông thường",
            pham_vi=PhamVi.NOI_BO,
            hien_thi=True,
            nguoi_tao=self.creator,
        )
        self.doc_den_hanche = VanBanDen.objects.create(
            nam=2026, so_hieu="02/HC-DEN", so_thu_tu=2,
            trich_yeu="Văn bản đến hạn chế bảo mật",
            pham_vi=PhamVi.HAN_CHE,
            hien_thi=False,
            nguoi_tao=self.creator,
        )
        self.doc_den_hanche.nguoi_nhan.add(self.recipient)

        # Văn bản đi: 1 nội bộ, 1 hạn chế
        self.doc_di_noibo = VanBanDi.objects.create(
            nam=2026, so_hieu="01/NB-DI", so_thu_tu=1,
            trich_yeu="Văn bản đi nội bộ thông thường",
            pham_vi=PhamVi.NOI_BO,
            hien_thi=True,
            nguoi_tao=self.creator,
        )
        self.doc_di_hanche = VanBanDi.objects.create(
            nam=2026, so_hieu="02/HC-DI", so_thu_tu=2,
            trich_yeu="Văn bản đi hạn chế bảo mật",
            pham_vi=PhamVi.HAN_CHE,
            hien_thi=False,
            nguoi_tao=self.creator,
        )
        self.doc_di_hanche.nguoi_nhan.add(self.recipient)

    def test_filter_den_han_che_for_creator(self):
        """Người tạo lọc pham_vi=HAN_CHE cho VB Đến chỉ thấy đúng văn bản hạn chế."""
        client = APIClient()
        client.force_authenticate(user=self.creator)

        response = client.get("/api/documents/?loai=DEN&pham_vi=HAN_CHE")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], self.doc_den_hanche.id)
        self.assertEqual(response.data["results"][0]["pham_vi"], "HAN_CHE")

    def test_filter_den_han_che_for_recipient(self):
        """Người nhận lọc pham_vi=HAN_CHE cho VB Đến thấy đúng văn bản hạn chế được giao."""
        client = APIClient()
        client.force_authenticate(user=self.recipient)

        response = client.get("/api/documents/?loai=DEN&pham_vi=HAN_CHE")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], self.doc_den_hanche.id)

    def test_filter_den_han_che_for_stranger_returns_zero(self):
        """Người không có quyền lọc pham_vi=HAN_CHE nhận kết quả rỗng (count=0, không lộ metadata)."""
        client = APIClient()
        client.force_authenticate(user=self.stranger)

        response = client.get("/api/documents/?loai=DEN&pham_vi=HAN_CHE")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(len(response.data["results"]), 0)

    def test_filter_den_noi_bo(self):
        """Lọc pham_vi=NOI_BO chỉ trả về văn bản nội bộ, loại bỏ văn bản hạn chế."""
        client = APIClient()
        client.force_authenticate(user=self.creator)

        response = client.get("/api/documents/?loai=DEN&pham_vi=NOI_BO")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], self.doc_den_noibo.id)
        self.assertEqual(response.data["results"][0]["pham_vi"], "NOI_BO")

    def test_filter_di_han_che_and_pagination(self):
        """Kiểm tra lọc pham_vi=HAN_CHE trên Văn bản Đi kèm phân trang chính xác."""
        client = APIClient()
        client.force_authenticate(user=self.creator)

        response = client.get("/api/documents/?loai=DI&pham_vi=HAN_CHE&page=1&page_size=10")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], self.doc_di_hanche.id)
        self.assertEqual(response.data["results"][0]["pham_vi"], "HAN_CHE")


class VanBanMatTests(TestCase):
    """
    Test suite cho phân hệ Văn bản Mật (VanBanMat / loai=MAT).
    Kiểm tra toàn diện: Model, bảo mật nghiêm ngặt (Issue #82, #83), API endpoints, ngăn chặn xóa.
    """

    def setUp(self):
        User = get_user_model()
        self.creator = User.objects.create_user(
            username="mat_creator",
            password="password123",
            email="creator@school.edu.vn",
            is_staff=True,
        )
        self.recipient = User.objects.create_user(
            username="mat_recipient",
            password="password123",
            email="recipient@school.edu.vn",
        )
        self.stranger = User.objects.create_user(
            username="mat_stranger",
            password="password123",
            email="stranger@school.edu.vn",
        )
        self.superuser = User.objects.create_superuser(
            username="mat_super",
            password="password123",
            email="super@school.edu.vn",
        )

        self.doc_mat = VanBanMat.objects.create(
            nam=2026,
            so_hieu="01/MAT-BGH",
            trich_yeu="Kế hoạch bảo vệ an ninh và bí mật nội bộ năm 2026",
            hieu_luc=HieuLuc.CON_HIEU_LUC,
            nguoi_tao=self.creator,
            pham_vi=PhamVi.HAN_CHE,
            gui_mail_toan_he_thong=False,
        )
        self.doc_mat.nguoi_nhan.add(self.recipient)

    def test_model_confidential_constraints(self):
        """Văn bản mật tự động gán pham_vi=HAN_CHE và cấm gửi mail toàn hệ thống."""
        self.assertEqual(self.doc_mat.pham_vi, PhamVi.HAN_CHE)
        self.assertFalse(self.doc_mat.gui_mail_toan_he_thong)
        self.assertIn(self.doc_mat.loai, ("DEN", "MAT"))
        self.assertIn(self.doc_mat.document_kind, ("vanbanden", "vanbanmat"))

    def test_admin_cannot_delete_restricted_compatibility_document(self):
        """Alias Văn bản Mật vẫn tuân thủ hợp đồng không xóa văn bản HAN_CHE."""
        client = APIClient()
        client.force_authenticate(user=self.superuser)
        res = client.delete(f"/api/documents/mat/{self.doc_mat.id}/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(VanBanMat.objects.filter(id=self.doc_mat.id).exists())

    def test_attachment_creation_and_path(self):
        """Tệp đính kèm văn bản mật lưu theo đường dẫn chuẩn của văn bản đến."""
        att = VanBanMatAttachment.objects.create(
            document=self.doc_mat,
            name="kehoach_mat.pdf",
        )
        self.assertTrue(att.file.field.upload_to(att, "kehoach_mat.pdf").startswith("van-ban-den/"))

    def test_junction_relations(self):
        """Liên kết Hồ sơ, Danh mục, Đơn vị nhận, Nơi ban hành hoạt động trơn tru."""
        hoso_id = HoSo.objects.get(is_he_thong=True).pk
        category = RecordLoaiVanBan.objects.create(ho_so_id=hoso_id, ten_loai="Loại văn bản hạn chế")
        donvi_id = DonVi.objects.order_by("id").first().pk
        VanBanMatHoSo.objects.create(vanbanden=self.doc_mat, hoso_id=hoso_id)
        VanBanMatDanhmuc.objects.create(vanbanden=self.doc_mat, loaivanban_id=category.pk)
        VanBanMatDonViNhan.objects.create(vanbanden=self.doc_mat, donvi_id=donvi_id)

        self.assertEqual(self.doc_mat.hoso.count(), 1)
        self.assertEqual(self.doc_mat.danhmuc.count(), 1)
        self.assertEqual(self.doc_mat.donvinhan.count(), 1)

    def test_creator_and_recipient_can_access(self):
        """Người tạo và người nhận xem được văn bản mật qua API."""
        client = APIClient()

        # Người tạo
        client.force_authenticate(user=self.creator)
        res = client.get("/api/documents/mat/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["count"], 1)

        res_detail = client.get(f"/api/documents/mat/{self.doc_mat.id}/")
        self.assertEqual(res_detail.status_code, status.HTTP_200_OK)
        self.assertEqual(res_detail.data["so_hieu"], "01/MAT-BGH")

        # Người nhận
        client.force_authenticate(user=self.recipient)
        res = client.get("/api/documents/mat/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["count"], 1)

    def test_stranger_and_superuser_cannot_access_confidential_document(self):
        """Người ngoài và superuser không có trong người nhận đều không xem được (404/bảo mật tuyệt đối)."""
        client = APIClient()

        # Người ngoài
        client.force_authenticate(user=self.stranger)
        res = client.get("/api/documents/mat/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["count"], 0)

        res_detail = client.get(f"/api/documents/mat/{self.doc_mat.id}/")
        self.assertEqual(res_detail.status_code, status.HTTP_404_NOT_FOUND)

        # Superuser không được gán quyền nhận
        client.force_authenticate(user=self.superuser)
        res_super = client.get("/api/documents/mat/")
        self.assertEqual(res_super.data["count"], 0)

        res_super_detail = client.get(f"/api/documents/mat/{self.doc_mat.id}/")
        self.assertEqual(res_super_detail.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_delete_via_api(self):
        """Cố gắng xóa văn bản mật qua API bị từ chối 403."""
        client = APIClient()
        client.force_authenticate(user=self.creator)
        res = client.delete(f"/api/documents/mat/{self.doc_mat.id}/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_confidential_document_via_unified_api(self):
        """Tạo văn bản mật qua endpoint thống nhất /api/documents/ với loai=MAT."""
        client = APIClient()
        client.force_authenticate(user=self.creator)

        payload = {
            "loai": "MAT",
            "so_hieu": "02/MAT-BGH",
            "trich_yeu": "Nội quy phòng họp mật",
            "nam": 2026,
            "nguoi_nhan": [self.recipient.id],
        }
        res = client.post("/api/documents/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn(res.data["loai"], ("DEN", "MAT"))
        self.assertEqual(res.data["pham_vi"], "HAN_CHE")

        doc = VanBanMat.objects.filter(so_hieu="02/MAT-BGH").first()
        self.assertIsNotNone(doc)
        self.assertTrue(doc.nguoi_nhan.filter(id=self.recipient.id).exists())


# ═══════════════════════════════════════════════════════════════════
# VAN BAN DI SERVICE TESTS (Phụ trách: Nguyễn Anh Đô)
# ═══════════════════════════════════════════════════════════════════

class VanBanDiServiceTests(TestCase):
    """
    Bộ kiểm thử Backend Services cho Văn bản Đi (Phụ trách: Nguyễn Anh Đô):
    1. Thuật toán tự sinh Số đi (so_thu_tu) tự tăng độc lập theo năm, concurrency safe.
    2. Khóa cứng so_thu_tu và nam khi cập nhật văn bản (PUT/PATCH).
    3. Bộ lọc nâng cao VanBanDiFilter (năm, khoảng ngày ban hành, loại VB, hồ sơ, hiệu lực, nơi ban hành, người ký, đơn vị nhận).
    4. Dịch vụ Excel Văn bản Đi (sinh file mẫu từ DB, Import tự cấp số đi nếu trống, Export theo bộ lọc).
    5. Cập nhật và truy vấn lịch sử người xem DocumentViewLog (document_type='vanbandi') qua endpoint /viewers/.
    """

    def setUp(self):
        from documents.services import generate_so_thu_tu, generate_excel_template, import_from_excel, export_to_excel
        from documents.filters import VanBanDiFilter
        self.creator = User.objects.create_user(
            username="docreator",
            password="testpassword123",
            email="docreator@itc.edu.vn",
        )
        self.recipient = User.objects.create_user(
            username="dorecipient",
            password="testpassword123",
            email="dorecipient@itc.edu.vn",
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.creator)

    def test_di_concurrency_safe_numbering(self):
        """Số đi tự tăng độc lập theo năm và bảo vệ chống trùng lặp."""
        from documents.services import generate_so_thu_tu
        so1 = generate_so_thu_tu("DI", 2026)
        self.assertEqual(so1, 1)

        doc1 = VanBanDi.objects.create(
            nam=2026,
            so_hieu="01/TB-ITC",
            so_thu_tu=so1,
            trich_yeu="Thông báo lịch nghỉ lễ 2026",
            nguoi_tao=self.creator,
        )
        self.assertEqual(doc1.so_thu_tu, 1)

        so2 = generate_so_thu_tu("DI", 2026)
        self.assertEqual(so2, 2)

        # Độc lập theo năm
        so_2027 = generate_so_thu_tu("DI", 2027)
        self.assertEqual(so_2027, 1)

    def test_di_update_so_thu_tu_and_nam_strictly_immutable(self):
        """Khóa cứng so_thu_tu và nam, chặn hoàn toàn việc sửa đổi số đi qua form cập nhật (PUT/PATCH)."""
        doc = VanBanDi.objects.create(
            nam=2026,
            so_hieu="10/QĐ-ITC",
            so_thu_tu=10,
            trich_yeu="Quyết định ban đầu",
            nguoi_tao=self.creator,
            ngay_ban_hanh=timezone.now(),
        )

        # Cố gắng thay đổi so_thu_tu và nam qua PUT /api/documents/{id}/
        res_put = self.client.put(
            f"/api/documents/{doc.id}/",
            {
                "loai": "DI",
                "so_hieu": "10/QĐ-ITC-SỬA",
                "trich_yeu": "Quyết định sau khi sửa",
                "nam": 2030,
                "so_thu_tu": 999,
                "ngay_ban_hanh": timezone.now().isoformat(),
            },
            format="json",
        )
        self.assertEqual(res_put.status_code, status.HTTP_200_OK)
        doc.refresh_from_db()
        self.assertEqual(doc.so_thu_tu, 10)  # Vẫn giữ nguyên 10!
        self.assertEqual(doc.nam, 2026)      # Vẫn giữ nguyên 2026!
        self.assertEqual(doc.trich_yeu, "Quyết định sau khi sửa")

        # Cố gắng thay đổi qua PATCH endpoint chuyên biệt /api/documents/di/{id}/
        res_patch = self.client.patch(
            f"/api/documents/di/{doc.id}/",
            {
                "nam": 2040,
                "so_thu_tu": 888,
                "trich_yeu": "Quyết định sau khi patch",
            },
            format="json",
        )
        self.assertEqual(res_patch.status_code, status.HTTP_200_OK)
        doc.refresh_from_db()
        self.assertEqual(doc.so_thu_tu, 10)  # Vẫn giữ nguyên 10!
        self.assertEqual(doc.nam, 2026)      # Vẫn giữ nguyên 2026!

    def test_di_advanced_filters(self):
        """Bộ lọc nâng cao VanBanDiFilter hỗ trợ đa tiêu chí."""
        from documents.filters import VanBanDiFilter
        now = timezone.now()
        doc1 = VanBanDi.objects.create(
            nam=2026,
            so_hieu="01/QĐ-ITC",
            so_thu_tu=1,
            trich_yeu="Quyết định khen thưởng giảng viên",
            hieu_luc=HieuLuc.CON_HIEU_LUC,
            nguoi_ky="Hiệu trưởng",
            nguoi_tao=self.creator,
            ngay_ban_hanh=now - timezone.timedelta(days=10),
        )
        doc2 = VanBanDi.objects.create(
            nam=2026,
            so_hieu="02/TB-ITC",
            so_thu_tu=2,
            trich_yeu="Thông báo lịch thi học kỳ (Hồ sơ đào tạo)",
            hieu_luc=HieuLuc.HET_HIEU_LUC,
            nguoi_ky="Trưởng phòng đào tạo",
            nguoi_tao=self.creator,
            ngay_ban_hanh=now - timezone.timedelta(days=2),
        )

        donvi_ids = list(DonVi.objects.order_by("id").values_list("id", flat=True)[:2])
        VanBanDiNoiBanHanh.objects.create(vanbandi=doc1, donvi_id=donvi_ids[0])
        VanBanDiDonViNhan.objects.create(vanbandi=doc2, donvi_id=donvi_ids[1])

        qs = VanBanDi.objects.all()

        # Lọc theo năm
        f_nam = VanBanDiFilter({"nam": 2026}, queryset=qs)
        self.assertEqual(f_nam.qs.count(), 2)

        # Lọc theo khoảng ngày ban hành
        f_date = VanBanDiFilter(
            {"tu_ngay": (now - timezone.timedelta(days=5)).isoformat(), "den_ngay": now.isoformat()},
            queryset=qs,
        )
        self.assertEqual(f_date.qs.count(), 1)
        self.assertEqual(f_date.qs.first().id, doc2.id)

        # Lọc theo loại VB
        f_loai = VanBanDiFilter({"loai_van_ban": "Quyết định"}, queryset=qs)
        self.assertEqual(f_loai.qs.count(), 1)
        self.assertEqual(f_loai.qs.first().id, doc1.id)

        # Lọc theo hồ sơ
        f_hoso = VanBanDiFilter({"ho_so": "Hồ sơ đào tạo"}, queryset=qs)
        self.assertEqual(f_hoso.qs.count(), 1)
        self.assertEqual(f_hoso.qs.first().id, doc2.id)

        # Lọc theo hiệu lực
        f_hl = VanBanDiFilter({"hieu_luc": "CON_HIEU_LUC"}, queryset=qs)
        self.assertEqual(f_hl.qs.count(), 1)
        self.assertEqual(f_hl.qs.first().id, doc1.id)

        # Lọc theo người ký
        f_signer = VanBanDiFilter({"nguoi_ky": "Hiệu trưởng"}, queryset=qs)
        self.assertEqual(f_signer.qs.count(), 1)
        self.assertEqual(f_signer.qs.first().id, doc1.id)

        # Lọc theo nơi ban hành liên kết
        f_nbh = VanBanDiFilter({"noi_ban_hanh": str(donvi_ids[0])}, queryset=qs)
        self.assertEqual(f_nbh.qs.count(), 1)
        self.assertEqual(f_nbh.qs.first().id, doc1.id)

        # Lọc theo đơn vị nhận
        f_dvn = VanBanDiFilter({"don_vi_nhan": str(donvi_ids[1])}, queryset=qs)
        self.assertEqual(f_dvn.qs.count(), 1)
        self.assertEqual(f_dvn.qs.first().id, doc2.id)

    def test_di_excel_service_template_import_export(self):
        """Dịch vụ Excel Văn bản Đi: template, import tự cấp số nếu trống, export theo bộ lọc."""
        from documents.services import generate_excel_template, import_from_excel, export_to_excel
        # 1. Sinh file mẫu
        template_bio = generate_excel_template("DI")
        self.assertTrue(template_bio.getvalue().startswith(b"PK"))

        # 2. Import Excel tự cấp Số đi nếu cột trống
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.append(["Số, ký hiệu VB", "Số đi", "Ngày ban hành", "Trích yếu nội dung", "Hiệu lực"])
        ws.append(["11/TB-DI", "", "15/09/2026 09:00:00", "Thông báo tuyển dụng cán bộ mới", "CON_HIEU_LUC"])

        in_bio = io.BytesIO()
        wb.save(in_bio)
        in_bio.seek(0)

        result = import_from_excel(in_bio, "DI", self.creator)
        self.assertEqual(result["created"], 1)

        imported_doc = VanBanDi.objects.filter(so_hieu="11/TB-DI").first()
        self.assertIsNotNone(imported_doc)
        self.assertTrue(imported_doc.so_thu_tu >= 1)

        # 3. Export Excel có cột Số đi
        export_bio = export_to_excel(VanBanDi.objects.filter(so_hieu="11/TB-DI"), "DI")
        self.assertTrue(export_bio.getvalue().startswith(b"PK"))

    def test_di_viewlog_and_viewers_endpoint(self):
        """Ghi nhận lịch sử xem DocumentViewLog (document_type='vanbandi') và query viewers."""
        doc = VanBanDi.objects.create(
            nam=2026,
            so_hieu="55/TB-DI",
            so_thu_tu=55,
            trich_yeu="Thông báo lịch trực tuần",
            nguoi_tao=self.creator,
        )

        # Xem văn bản qua API
        res = self.client.get(f"/api/documents/{doc.id}/?loai=DI")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        log_entry = DocumentViewLog.objects.filter(
            document_type="vanbandi",
            document_id=doc.id,
            user=self.creator,
        ).first()
        self.assertIsNotNone(log_entry)

        # Query viewers API chuyên biệt /api/documents/di/{id}/viewers/
        res_viewers = self.client.get(f"/api/documents/di/{doc.id}/viewers/")
        self.assertEqual(res_viewers.status_code, status.HTTP_200_OK)

    def test_excel_import_three_validity_states(self):
        """Kiểm tra Import Excel nhận diện chính xác 3 trạng thái hiệu lực cho cả Văn bản Đến và Đi."""
        from documents.services import import_from_excel
        from openpyxl import Workbook
        import io

        # 1. Test cho Văn bản Đến (Nội bộ & Hạn chế)
        wb_den = Workbook()
        ws_den = wb_den.active
        ws_den.append(["Số, ký hiệu VB", "Ngày đến", "Trích yếu nội dung", "Hiệu lực", "Phạm vi"])
        ws_den.append(["91/CV-DEN", "15/09/2026 09:00:00", "Văn bản Đến còn hiệu lực (mã enum)", "CON_HIEU_LUC", "Nội bộ"])
        ws_den.append(["92/CV-DEN", "15/09/2026 09:00:00", "Văn bản Đến hết hiệu lực (chữ)", "Hết hiệu lực", "Nội bộ"])
        ws_den.append(["93/CV-DEN", "15/09/2026 09:00:00", "Văn bản Đến hết và thay thế (chuẩn hóa về Hết hiệu lực)", "HET_VA_THAY_THE", "Nội bộ"])
        ws_den.append(["94/CV-DEN", "15/09/2026 09:00:00", "Văn bản Đến để trống hiệu lực (mặc định Còn hiệu lực)", "", "Nội bộ"])

        bio_den = io.BytesIO()
        wb_den.save(bio_den)
        bio_den.seek(0)

        res_den = import_from_excel(bio_den, "DEN", self.creator, pham_vi="NOI_BO")
        self.assertEqual(res_den["created"], 4)

        self.assertEqual(VanBanDen.objects.get(so_hieu="91/CV-DEN").hieu_luc, HieuLuc.CON_HIEU_LUC)
        self.assertEqual(VanBanDen.objects.get(so_hieu="92/CV-DEN").hieu_luc, HieuLuc.HET_HIEU_LUC)
        self.assertEqual(VanBanDen.objects.get(so_hieu="93/CV-DEN").hieu_luc, HieuLuc.HET_HIEU_LUC)
        self.assertEqual(VanBanDen.objects.get(so_hieu="94/CV-DEN").hieu_luc, HieuLuc.CON_HIEU_LUC)

        # 2. Test cho Văn bản Đi (Nội bộ & Hạn chế)
        wb_di = Workbook()
        ws_di = wb_di.active
        ws_di.append(["Số, ký hiệu VB", "Ngày ban hành", "Trích yếu nội dung", "Hiệu lực", "Phạm vi"])
        ws_di.append(["91/TB-DI", "15/09/2026 09:00:00", "Văn bản Đi còn hiệu lực một phần (chữ)", "Còn hiệu lực một phần", "Nội bộ"])
        ws_di.append(["92/TB-DI", "15/09/2026 09:00:00", "Văn bản Đi hết hiệu lực (mã enum)", "HET_HIEU_LUC", "Nội bộ"])
        ws_di.append(["93/TB-DI", "15/09/2026 09:00:00", "Văn bản Đi còn hiệu lực 1 phần", "CON_HIEU_LUC_1_PHAN", "Nội bộ"])

        bio_di = io.BytesIO()
        wb_di.save(bio_di)
        bio_di.seek(0)

        res_di = import_from_excel(bio_di, "DI", self.creator, pham_vi="NOI_BO")
        self.assertEqual(res_di["created"], 3)

        self.assertEqual(VanBanDi.objects.get(so_hieu="91/TB-DI").hieu_luc, HieuLuc.CON_HIEU_LUC_1_PHAN)
        self.assertEqual(VanBanDi.objects.get(so_hieu="92/TB-DI").hieu_luc, HieuLuc.HET_HIEU_LUC)
        self.assertEqual(VanBanDi.objects.get(so_hieu="93/TB-DI").hieu_luc, HieuLuc.CON_HIEU_LUC_1_PHAN)

    def test_excel_import_scope_and_type_guards(self):
        """Khóa nghiệp vụ: Chặn import chéo giữa Nội bộ và Hạn chế, chặn chéo giữa Đến và Đi."""
        from documents.services import generate_excel_template, import_from_excel
        import openpyxl

        # 1. Mẫu Hạn chế không được nạp vào Nội bộ
        tpl_hc = generate_excel_template("DI", "HAN_CHE")
        res1 = import_from_excel(tpl_hc, "DI", self.creator, pham_vi="NOI_BO")
        self.assertEqual(res1["created"], 0)
        self.assertIn("Hạn chế", res1["errors"][0]["message"])
        self.assertIn("Nội bộ", res1["errors"][0]["message"])

        # 2. Mẫu Nội bộ không được nạp vào Hạn chế
        tpl_nb = generate_excel_template("DI", "NOI_BO")
        res2 = import_from_excel(tpl_nb, "DI", self.creator, pham_vi="HAN_CHE")
        self.assertEqual(res2["created"], 0)
        self.assertIn("Nội bộ", res2["errors"][0]["message"])
        self.assertIn("Hạn chế", res2["errors"][0]["message"])

        # 3. Mẫu Đến không được nạp vào Đi
        tpl_den = generate_excel_template("DEN", "NOI_BO")
        res3 = import_from_excel(tpl_den, "DI", self.creator, pham_vi="NOI_BO")
        self.assertEqual(res3["created"], 0)
        self.assertIn("Văn bản Đến", res3["errors"][0]["message"])

        # 4. Mẫu Đi không được nạp vào Đến
        res4 = import_from_excel(tpl_nb, "DEN", self.creator, pham_vi="NOI_BO")
        self.assertEqual(res4["created"], 0)
        self.assertIn("Văn bản Đi", res4["errors"][0]["message"])

        # 5. File chỉ chứa dòng ví dụ mẫu báo lỗi thân thiện
        res5 = import_from_excel(tpl_hc, "DI", self.creator, pham_vi="HAN_CHE")
        self.assertEqual(res5["created"], 0)
        self.assertIn("chỉ chứa dòng ví dụ mẫu", res5["errors"][0]["message"])

        # 6. Import mẫu Hạn chế với dữ liệu thực và cán bộ nhận thành công
        wb = openpyxl.load_workbook(generate_excel_template("DI", "HAN_CHE"))
        ws = wb.active
        ws.append([
            "123/TB-HC-OK", "Hạn chế", "22/09/2026", "22/09/2026",
            "Trích yếu hợp lệ cho văn bản hạn chế", "Ban Giám hiệu",
            self.recipient.username, "Hội đồng trường", "Hiệu trưởng", "Hiệu trưởng", "CON_HIEU_LUC", "", ""
        ])
        bio = io.BytesIO()
        wb.save(bio)
        bio.seek(0)
        res6 = import_from_excel(bio, "DI", self.creator, pham_vi="HAN_CHE")
        self.assertEqual(res6["created"], 1)
        doc_hc = VanBanDi.objects.filter(so_hieu="123/TB-HC-OK").first()
        self.assertIsNotNone(doc_hc)
        self.assertEqual(doc_hc.pham_vi, PhamVi.HAN_CHE)
        self.assertTrue(doc_hc.nguoi_nhan.filter(id=self.recipient.id).exists())


# ═══════════════════════════════════════════════════════════════════
# VAN BAN MAT SERVICE TESTS (Phụ trách: Nguyễn Anh Đô)
# ═══════════════════════════════════════════════════════════════════

class VanBanMatServiceTests(TestCase):
    """
    Bộ kiểm thử Backend Services cho Văn bản Mật (Phụ trách: Nguyễn Anh Đô):
    1. Bộ lọc nâng cao VanBanMatFilter: số ký hiệu, trích yếu, năm, khoảng ngày ban hành, hiệu lực.
    2. Dịch vụ Excel cho Văn bản Mật: sinh file mẫu bảo mật (không có cột Số đi), import chặt chẽ (áp pham_vi=HAN_CHE, cấm mail).
    3. Export Excel theo phân quyền người dùng đăng nhập (không rò rỉ dữ liệu mật cho người không được nhận).
    4. Cập nhật logic DocumentViewLog cho document_type='vanbanmat' lưu chính xác ngày giờ phút giây.
    5. Khóa chức năng gửi email toàn hệ thống ở cấp backend service đối với văn bản mật.
    """

    def setUp(self):
        from documents.filters import VanBanMatFilter
        from documents.services import (
            generate_excel_template,
            import_from_excel,
            export_to_excel,
            send_document_notification_mail,
        )
        self.creator = User.objects.create_user(
            username="matcreator",
            password="testpassword123",
            email="creator@itc.edu.vn",
        )
        self.recipient = User.objects.create_user(
            username="matrecipient",
            password="testpassword123",
            email="recipient@itc.edu.vn",
        )
        self.stranger = User.objects.create_user(
            username="matstranger",
            password="testpassword123",
            email="stranger@itc.edu.vn",
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.creator)

    def test_mat_advanced_filters(self):
        """Bộ lọc nâng cao VanBanMatFilter: số ký hiệu, trích yếu, năm, khoảng ngày ban hành, hiệu lực."""
        from documents.filters import VanBanMatFilter
        now = timezone.now()
        doc1 = VanBanMat.objects.create(
            nam=2026,
            so_hieu="01/MẬT-BGH",
            trich_yeu="Phương án bảo mật đề thi học kỳ 1",
            hieu_luc=HieuLuc.CON_HIEU_LUC,
            nguoi_tao=self.creator,
            ngay_den=now - timezone.timedelta(days=10),
            pham_vi=PhamVi.HAN_CHE,
        )
        doc1.nguoi_nhan.add(self.recipient)

        doc2 = VanBanMat.objects.create(
            nam=2026,
            so_hieu="02/MẬT-TCKT",
            trich_yeu="Báo cáo quyết toán dự án quốc phòng",
            hieu_luc=HieuLuc.HET_HIEU_LUC,
            nguoi_tao=self.creator,
            ngay_den=now - timezone.timedelta(days=2),
            pham_vi=PhamVi.HAN_CHE,
        )
        doc2.nguoi_nhan.add(self.recipient)

        qs = VanBanMat.objects.all()

        # Tìm kiếm từ khóa theo số ký hiệu hoặc trích yếu
        f_q = VanBanMatFilter({"q": "đề thi"}, queryset=qs)
        self.assertEqual(f_q.qs.count(), 1)
        self.assertEqual(f_q.qs.first().id, doc1.id)

        f_so = VanBanMatFilter({"so_hieu": "02/MẬT"}, queryset=qs)
        self.assertEqual(f_so.qs.count(), 1)
        self.assertEqual(f_so.qs.first().id, doc2.id)

        # Lọc theo năm
        f_nam = VanBanMatFilter({"nam": 2026}, queryset=qs)
        self.assertEqual(f_nam.qs.count(), 2)

        # Lọc theo khoảng ngày ban hành
        f_date = VanBanMatFilter(
            {"tu_ngay": (now - timezone.timedelta(days=5)).isoformat(), "den_ngay": now.isoformat()},
            queryset=qs,
        )
        self.assertEqual(f_date.qs.count(), 1)
        self.assertEqual(f_date.qs.first().id, doc2.id)

        # Lọc theo hiệu lực
        f_hl = VanBanMatFilter({"hieu_luc": "CON_HIEU_LUC"}, queryset=qs)
        self.assertEqual(f_hl.qs.count(), 1)
        self.assertEqual(f_hl.qs.first().id, doc1.id)

    def test_mat_excel_security_template(self):
        """Sinh file mẫu Excel bảo mật: không có cột Số đi, có định dạng bảo mật."""
        from documents.services import generate_excel_template
        template_bio = generate_excel_template("MAT")
        self.assertTrue(template_bio.getvalue().startswith(b"PK"))

        from openpyxl import load_workbook
        wb = load_workbook(template_bio, read_only=True)
        ws = wb.active
        headers = [cell for cell in next(ws.iter_rows(values_only=True))]
        self.assertNotIn("Số đi", headers)
        self.assertIn("Số, ký hiệu VB", headers)
        self.assertIn("Trích yếu nội dung", headers)

    def test_mat_excel_import_strict_validation(self):
        """Import Excel VB Mật: kiểm tra chặt chẽ bắt buộc, áp pham_vi=HAN_CHE và cấm gửi mail."""
        from documents.services import import_from_excel
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.append(["Số, ký hiệu VB", "Ngày ban hành", "Trích yếu nội dung", "Hiệu lực"])
        ws.append(["99/MẬT-BGH", "10/10/2026 08:30:00", "Hồ sơ công tác nhân sự bảo mật", "CON_HIEU_LUC"])

        in_bio = io.BytesIO()
        wb.save(in_bio)
        in_bio.seek(0)

        result = import_from_excel(in_bio, "MAT", self.creator)
        self.assertEqual(result["created"], 1)

        imported = VanBanMat.objects.filter(so_hieu="99/MẬT-BGH").first()
        self.assertIsNotNone(imported)
        self.assertEqual(imported.pham_vi, PhamVi.HAN_CHE)
        self.assertFalse(imported.gui_mail_toan_he_thong)
        self.assertTrue(imported.nguoi_nhan.filter(id=self.creator.id).exists())

    def test_mat_excel_export_scoped_by_user_permissions(self):
        """Export Excel VB Mật: tuân thủ chặt chẽ phân quyền, không có cột Số đi."""
        doc = VanBanMat.objects.create(
            nam=2026,
            so_hieu="77/MẬT-BGH",
            trich_yeu="Tài liệu cơ mật của Ban Giám hiệu",
            nguoi_tao=self.creator,
            pham_vi=PhamVi.HAN_CHE,
        )
        doc.nguoi_nhan.add(self.recipient)

        # Người lạ gọi export qua API chỉ nhận được danh sách rỗng (hoặc chỉ văn bản họ được xem)
        client_stranger = APIClient()
        client_stranger.force_authenticate(user=self.stranger)
        res_stranger = client_stranger.get("/api/documents/mat/export/")
        self.assertEqual(res_stranger.status_code, status.HTTP_200_OK)

        from openpyxl import load_workbook
        wb_stranger = load_workbook(io.BytesIO(res_stranger.content), read_only=True)
        ws_stranger = wb_stranger.active
        rows_stranger = list(ws_stranger.iter_rows(values_only=True))
        # Chỉ có 1 hàng header, 0 hàng dữ liệu
        self.assertEqual(len(rows_stranger), 1)

        # Người nhận được phép xuất
        client_recipient = APIClient()
        client_recipient.force_authenticate(user=self.recipient)
        res_recipient = client_recipient.get("/api/documents/mat/export/")
        self.assertEqual(res_recipient.status_code, status.HTTP_200_OK)
        wb_recipient = load_workbook(io.BytesIO(res_recipient.content), read_only=True)
        ws_recipient = wb_recipient.active
        rows_recipient = list(ws_recipient.iter_rows(values_only=True))
        self.assertEqual(len(rows_recipient), 2)
        # Xác nhận hàng header không có cột Số đi
        self.assertNotIn("Số đi", rows_recipient[0])

    def test_mat_viewlog_uses_backing_kind_and_preserves_timestamp(self):
        """Alias Văn bản Mật ghi view-log dưới loại văn bản của bảng dùng chung."""
        doc = VanBanMat.objects.create(
            nam=2026,
            so_hieu="88/MẬT-VP",
            trich_yeu="Văn bản mật kiểm tra view log",
            nguoi_tao=self.creator,
            pham_vi=PhamVi.HAN_CHE,
        )
        doc.nguoi_nhan.add(self.recipient)

        client_rec = APIClient()
        client_rec.force_authenticate(user=self.recipient)
        res = client_rec.get(f"/api/documents/mat/{doc.id}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        view_log = DocumentViewLog.objects.filter(
            document_type="vanbanden",
            document_id=doc.id,
            user=self.recipient,
        ).first()
        self.assertIsNotNone(view_log)
        self.assertIsNotNone(view_log.viewed_at)

        res_viewers = client_rec.get(f"/api/documents/mat/{doc.id}/viewers/")
        self.assertEqual(res_viewers.status_code, status.HTTP_200_OK)

    def test_mat_access_log_uses_backing_kind(self):
        from documents.selectors import log_access

        doc = VanBanMat.objects.create(
            nam=2026,
            so_hieu="89/MAT-SERVICE",
            trich_yeu="Văn bản mật kiểm tra access log",
            nguoi_tao=self.creator,
            pham_vi=PhamVi.HAN_CHE,
        )
        log = log_access(
            "vanbanmat",
            doc.pk,
            self.creator,
            DocumentAccessLog.HanhDong.XEM,
        )
        self.assertEqual(log.document_type, "vanbanden")

    def test_mat_email_lockdown_at_service_layer(self):
        """Khóa hoàn toàn chức năng gửi email toàn hệ thống ở cấp backend service đối với văn bản mật."""
        from django.core.exceptions import ValidationError
        from documents.services import send_document_notification_mail

        doc = VanBanMat.objects.create(
            nam=2026,
            so_hieu="100/MẬT-BGH",
            trich_yeu="Bí mật nhà nước tuyệt đối",
            nguoi_tao=self.creator,
            pham_vi=PhamVi.HAN_CHE,
            gui_mail_toan_he_thong=False,
        )
        doc.nguoi_nhan.add(self.recipient)

        # Cố gắng gửi mail toàn hệ thống ở service layer -> Bị từ chối bằng ValidationError
        with self.assertRaises(ValidationError):
            send_document_notification_mail(doc, force_system_wide=True)

        with self.assertRaises(ValidationError):
            send_document_notification_mail(doc, recipient_list="ALL")

        # Gửi đích danh cho người nhận được cấp quyền -> Hợp lệ
        result = send_document_notification_mail(doc)
        self.assertTrue(result["success"])
        self.assertTrue(result["is_confidential"])
        self.assertIn(self.recipient.email, result["recipients"])

    def test_excel_template_columns_and_formatting(self):
        """Kiểm tra file mẫu Excel tải về cho cả 4 biểu mẫu (Đến/Đi - Nội bộ/Hạn chế) đều có cột Link văn bản thay thế và định dạng chuẩn."""
        from documents.services import generate_excel_template
        import openpyxl

        configs = [
            ("DEN", "NOI_BO"),
            ("DEN", "HAN_CHE"),
            ("DI", "NOI_BO"),
            ("DI", "HAN_CHE"),
        ]

        for loai, pham_vi in configs:
            bio = generate_excel_template(loai, pham_vi)
            wb = openpyxl.load_workbook(bio)
            ws = wb.active

            # Kiểm tra hàng tiêu đề có đủ "Link văn bản thay thế", "Hiệu lực" và "Ghi chú"
            headers = [cell.value for cell in ws[1] if cell.value]
            self.assertIn("Link văn bản thay thế", headers, f"Thiếu cột 'Link văn bản thay thế' trong mẫu {loai} {pham_vi}")
            self.assertIn("Ghi chú", headers)
            self.assertIn("Hiệu lực", headers)

            # Cột Link văn bản thay thế phải đứng ngay trước Ghi chú
            idx_link = headers.index("Link văn bản thay thế")
            idx_note = headers.index("Ghi chú")
            self.assertEqual(idx_link + 1, idx_note)

            # Chiều cao dòng 2 mẫu phải là 36 để không bị cắt xén font tiếng Việt
            self.assertEqual(ws.row_dimensions[2].height, 36)

            # Kiểm tra dòng mẫu ghi chú rút gọn rõ ràng
            note_val = ws[2][idx_note].value
            self.assertIn("xóa trước khi import", str(note_val).lower())
            self.assertEqual(str(note_val), "(Dòng ví dụ mẫu — xóa trước khi import)")

            # Kiểm tra cột Link văn bản thay thế có comment gợi ý và giá trị mẫu trực quan
            cell_link_hdr = ws.cell(row=1, column=idx_link + 1)
            self.assertIsNotNone(cell_link_hdr.comment, f"Cột 'Link văn bản thay thế' cần có hover comment trong {loai} {pham_vi}")
            self.assertIn("Số hiệu", cell_link_hdr.comment.text)

            sample_link_val = ws.cell(row=2, column=idx_link + 1).value
            self.assertTrue(bool(sample_link_val), f"Dòng mẫu cần có số hiệu văn bản trực quan cho cột link_thay_the trong {loai} {pham_vi}")

            # Kiểm tra cột Hiệu lực có comment gợi ý 3 trạng thái
            idx_hl = headers.index("Hiệu lực")
            cell_hl_hdr = ws.cell(row=1, column=idx_hl + 1)
            self.assertIsNotNone(cell_hl_hdr.comment, f"Cột 'Hiệu lực' cần có hover comment trong {loai} {pham_vi}")
            self.assertIn("Còn hiệu lực 1 phần", cell_hl_hdr.comment.text)

            # Kiểm tra VML shape định nghĩa chuẩn width:250px;height:85px cho link_thay_the và width:380px;height:135px cho hieu_luc
            import zipfile
            bio.seek(0)
            with zipfile.ZipFile(bio) as z:
                vml_content = "".join(z.read(n).decode("utf-8", errors="ignore") for n in z.namelist() if "vml" in n)
                self.assertIn("width:250px;height:85px", vml_content)
                self.assertIn("width:380px;height:135px", vml_content)


class DocumentReplacementDisambiguationTests(TestCase):
    """
    Bộ kiểm thử toàn diện cho cơ chế Định danh & Phân biệt chính xác (Disambiguation Qualifier)
    khi có văn bản trùng số hiệu từ các nơi ban hành khác nhau cho cả 4 trường hợp:
    1. Văn bản Đến - Thường (NOI_BO)
    2. Văn bản Đến - Hạn chế (HAN_CHE)
    3. Văn bản Đi - Thường (NOI_BO)
    4. Văn bản Đi - Hạn chế (HAN_CHE)
    """

    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_superuser(
            username="admin_disambig",
            password="password123",
            email="admin_disambig@test.vn",
            is_staff=True,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

    def test_inbound_normal_duplicate_so_hieu_replacement(self):
        """
        Trường hợp 1: Văn bản Đến - Thường (NOI_BO).
        2 văn bản có cùng số hiệu '01/CV' nhưng khác nơi ban hành:
        - Doc 1: Sở GD&ĐT TP.HCM (Số đến #10)
        - Doc 2: Bộ GD&ĐT (Số đến #11)
        Khi tạo văn bản mới thay thế đích danh Doc 2:
        - Doc 2 chuyển sang CON_HIEU_LUC_1_PHAN và liên kết tới văn bản mới.
        - Doc 1 giữ nguyên CON_HIEU_LUC, không bị ảnh hưởng.
        Khi chỉnh sửa gỡ bỏ liên kết:
        - Doc 2 khôi phục CON_HIEU_LUC trong đúng 1 lần lưu.
        """
        doc1 = VanBanDen.objects.create(
            nam=2026,
            so_hieu="01/CV",
            so_thu_tu=10,
            noi_ban_hanh="Sở GD&ĐT TP.HCM",
            pham_vi=PhamVi.NOI_BO,
            trich_yeu="Công văn số 1 của Sở GD",
            hieu_luc=HieuLuc.CON_HIEU_LUC,
            nguoi_tao=self.admin,
        )
        doc2 = VanBanDen.objects.create(
            nam=2026,
            so_hieu="01/CV",
            so_thu_tu=11,
            noi_ban_hanh="Bộ GD&ĐT",
            pham_vi=PhamVi.NOI_BO,
            trich_yeu="Công văn số 1 của Bộ GD",
            hieu_luc=HieuLuc.CON_HIEU_LUC,
            nguoi_tao=self.admin,
        )

        # Tạo văn bản mới Doc 3 thay thế chính xác Doc 2 (Bộ GD&ĐT - #11)
        res_create = self.client.post(
            "/api/documents/",
            {
                "loai": "DEN",
                "nam": 2026,
                "so_hieu": "99/CV-NEW",
                "trich_yeu": "Văn bản mới thay thế CV 01 Bộ GD",
                "noi_ban_hanh": "Bộ GD&ĐT",
                "pham_vi": "NOI_BO",
                "hieu_luc": "CON_HIEU_LUC",
                "link_thay_the": "01/CV [Nơi ban hành: Bộ GD&ĐT - Số đến #11]",
            },
            format="json",
        )
        self.assertEqual(res_create.status_code, status.HTTP_201_CREATED)
        new_doc_id = res_create.data["id"]

        # Kiểm tra Doc 2 (Bộ GD&ĐT) bị thay thế
        doc2.refresh_from_db()
        self.assertEqual(doc2.hieu_luc, HieuLuc.CON_HIEU_LUC_1_PHAN)
        self.assertIn("99/CV-NEW", doc2.link_thay_the)

        # Kiểm tra Doc 1 (Sở GD&ĐT) hoàn toàn không bị ảnh hưởng
        doc1.refresh_from_db()
        self.assertEqual(doc1.hieu_luc, HieuLuc.CON_HIEU_LUC)
        self.assertEqual(doc1.link_thay_the or "", "")

        # Chỉnh sửa Doc 3 gỡ bỏ liên kết thay thế (xóa trắng link_thay_the) -> Chỉ cần 1 lần lưu
        res_update = self.client.put(
            f"/api/documents/{new_doc_id}/",
            {
                "loai": "DEN",
                "nam": 2026,
                "so_hieu": "99/CV-NEW",
                "trich_yeu": "Văn bản mới không còn thay thế",
                "noi_ban_hanh": "Bộ GD&ĐT",
                "pham_vi": "NOI_BO",
                "hieu_luc": "CON_HIEU_LUC",
                "link_thay_the": "",
            },
            format="json",
        )
        self.assertEqual(res_update.status_code, status.HTTP_200_OK)

        # Xác nhận Doc 2 được khôi phục ngay lập tức
        doc2.refresh_from_db()
        self.assertEqual(doc2.hieu_luc, HieuLuc.CON_HIEU_LUC)
        self.assertEqual(doc2.link_thay_the or "", "")

        # Doc 1 vẫn nguyên vẹn
        doc1.refresh_from_db()
        self.assertEqual(doc1.hieu_luc, HieuLuc.CON_HIEU_LUC)

    def test_inbound_restricted_duplicate_so_hieu_replacement(self):
        """
        Trường hợp 2: Văn bản Đến - Hạn chế (HAN_CHE).
        2 văn bản hạn chế trùng số hiệu '02/BC-MẬT' từ 2 cơ quan khác nhau:
        - Doc 1: Công an TP (Số đến #20)
        - Doc 2: Bộ Công an (Số đến #21)
        Văn bản mới thay thế đích danh Doc 2.
        """
        doc_res1 = VanBanDen.objects.create(
            nam=2026,
            so_hieu="02/BC-MẬT",
            so_thu_tu=20,
            noi_ban_hanh="Công an TP",
            pham_vi=PhamVi.HAN_CHE,
            trich_yeu="Báo cáo CATP",
            hieu_luc=HieuLuc.CON_HIEU_LUC,
            nguoi_tao=self.admin,
        )
        doc_res2 = VanBanDen.objects.create(
            nam=2026,
            so_hieu="02/BC-MẬT",
            so_thu_tu=21,
            noi_ban_hanh="Bộ Công an",
            pham_vi=PhamVi.HAN_CHE,
            trich_yeu="Báo cáo BCA",
            hieu_luc=HieuLuc.CON_HIEU_LUC,
            nguoi_tao=self.admin,
        )

        res_create = self.client.post(
            "/api/documents/",
            {
                "loai": "DEN",
                "nam": 2026,
                "so_hieu": "100/BC-MẬT",
                "trich_yeu": "Báo cáo mới thay thế BCA",
                "noi_ban_hanh": "Bộ Công an",
                "pham_vi": "HAN_CHE",
                "nguoi_nhan": [self.admin.id],
                "hieu_luc": "CON_HIEU_LUC",
                "link_thay_the": "02/BC-MẬT [Nơi ban hành: Bộ Công an - Số đến #21]",
            },
            format="json",
        )
        self.assertEqual(res_create.status_code, status.HTTP_201_CREATED)

        doc_res2.refresh_from_db()
        self.assertEqual(doc_res2.hieu_luc, HieuLuc.CON_HIEU_LUC_1_PHAN)
        self.assertIn("100/BC-MẬT", doc_res2.link_thay_the)

        doc_res1.refresh_from_db()
        self.assertEqual(doc_res1.hieu_luc, HieuLuc.CON_HIEU_LUC)
        self.assertEqual(doc_res1.link_thay_the or "", "")

    def test_outbound_normal_replacement(self):
        """
        Trường hợp 3: Văn bản Đi - Thường (NOI_BO).
        Thay thế chính xác văn bản đi qua số hiệu và người ký / số đi.
        """
        doc_di1 = VanBanDi.objects.create(
            nam=2026,
            so_hieu="10/QĐ-ITC",
            so_thu_tu=1,
            nguoi_ky="Hiệu trưởng",
            pham_vi=PhamVi.NOI_BO,
            trich_yeu="Quyết định ban hành quy chế cũ",
            hieu_luc=HieuLuc.CON_HIEU_LUC,
            nguoi_tao=self.admin,
        )
        doc_di2 = VanBanDi.objects.create(
            nam=2026,
            so_hieu="20/QĐ-ITC",
            so_thu_tu=2,
            nguoi_ky="Phó Hiệu trưởng",
            pham_vi=PhamVi.NOI_BO,
            trich_yeu="Quyết định khen thưởng",
            hieu_luc=HieuLuc.CON_HIEU_LUC,
            nguoi_tao=self.admin,
        )

        res_create = self.client.post(
            "/api/documents/",
            {
                "loai": "DI",
                "nam": 2026,
                "so_hieu": "30/QĐ-ITC",
                "trich_yeu": "Quyết định ban hành quy chế mới thay thế",
                "nguoi_ky": "Hiệu trưởng",
                "ngay_ban_hanh": "2026-10-22T08:00:00Z",
                "pham_vi": "NOI_BO",
                "hieu_luc": "CON_HIEU_LUC",
                "link_thay_the": "10/QĐ-ITC [Người ký: Hiệu trưởng - Số đi #1]",
            },
            format="json",
        )
        self.assertEqual(res_create.status_code, status.HTTP_201_CREATED)

        doc_di1.refresh_from_db()
        self.assertEqual(doc_di1.hieu_luc, HieuLuc.CON_HIEU_LUC_1_PHAN)
        self.assertIn("30/QĐ-ITC", doc_di1.link_thay_the)

        doc_di2.refresh_from_db()
        self.assertEqual(doc_di2.hieu_luc, HieuLuc.CON_HIEU_LUC)

    def test_outbound_restricted_replacement(self):
        """
        Trường hợp 4: Văn bản Đi - Hạn chế (HAN_CHE).
        Chỉ cho phép liên kết giữa các văn bản Đi có pham_vi='HAN_CHE'.
        """
        doc_di_hc1 = VanBanDi.objects.create(
            nam=2026,
            so_hieu="05/TB-HC",
            so_thu_tu=10,
            pham_vi=PhamVi.HAN_CHE,
            trich_yeu="Thông báo hạn chế đợt 1",
            hieu_luc=HieuLuc.CON_HIEU_LUC,
            nguoi_tao=self.admin,
        )
        doc_di_hc2 = VanBanDi.objects.create(
            nam=2026,
            so_hieu="06/TB-HC",
            so_thu_tu=11,
            pham_vi=PhamVi.HAN_CHE,
            trich_yeu="Thông báo hạn chế đợt 2",
            hieu_luc=HieuLuc.CON_HIEU_LUC,
            nguoi_tao=self.admin,
        )

        res_create = self.client.post(
            "/api/documents/",
            {
                "loai": "DI",
                "nam": 2026,
                "so_hieu": "07/TB-HC",
                "trich_yeu": "Thông báo hạn chế đợt 3 thay thế đợt 1",
                "ngay_ban_hanh": "2026-10-22T08:00:00Z",
                "pham_vi": "HAN_CHE",
                "nguoi_nhan": [self.admin.id],
                "hieu_luc": "CON_HIEU_LUC",
                "link_thay_the": "05/TB-HC [Số đi #10]",
            },
            format="json",
        )
        self.assertEqual(res_create.status_code, status.HTTP_201_CREATED)

        doc_di_hc1.refresh_from_db()
        self.assertEqual(doc_di_hc1.hieu_luc, HieuLuc.CON_HIEU_LUC_1_PHAN)
        self.assertIn("07/TB-HC", doc_di_hc1.link_thay_the)

        doc_di_hc2.refresh_from_db()
        self.assertEqual(doc_di_hc2.hieu_luc, HieuLuc.CON_HIEU_LUC)

    def test_cross_scope_replacement_prohibited(self):
        """
        Bảo mật phân hệ: Không cho phép văn bản Thường (NOI_BO) thay thế văn bản Hạn chế (HAN_CHE)
        hoặc văn bản Đến thay thế văn bản Đi.
        """
        VanBanDen.objects.create(
            nam=2026,
            so_hieu="999/MẬT-DEN",
            so_thu_tu=99,
            pham_vi=PhamVi.HAN_CHE,
            trich_yeu="Văn bản hạn chế tuyệt mật",
            hieu_luc=HieuLuc.CON_HIEU_LUC,
            nguoi_tao=self.admin,
        )

        # Thử dùng văn bản thường (NOI_BO) thay thế văn bản hạn chế -> Bị chặn
        res = self.client.post(
            "/api/documents/",
            {
                "loai": "DEN",
                "nam": 2026,
                "so_hieu": "1000/CV-THUONG",
                "trich_yeu": "Cố tình thay thế văn bản hạn chế",
                "pham_vi": "NOI_BO",
                "hieu_luc": "CON_HIEU_LUC",
                "link_thay_the": "999/MẬT-DEN",
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("link_thay_the", res.data)

    def test_same_so_hieu_cross_replacement_inbound_normal(self):
        """
        Văn bản Đến Thường (NOI_BO): Cho phép 2 văn bản có cùng số hiệu thay thế nhau
        khi phân biệt rõ bằng nơi ban hành và số đến (#stt).
        """
        from documents.services import get_replacement_relations

        doc1 = VanBanDen.objects.create(
            nam=2026,
            so_hieu="15/QĐ",
            so_thu_tu=10,
            pham_vi=PhamVi.NOI_BO,
            noi_ban_hanh="Sở Giáo dục và Đào tạo",
            trich_yeu="Quyết định ban đầu của Sở",
            hieu_luc=HieuLuc.CON_HIEU_LUC,
            nguoi_tao=self.admin,
        )

        res = self.client.post(
            "/api/documents/",
            {
                "loai": "DEN",
                "nam": 2026,
                "so_hieu": "15/QĐ",
                "trich_yeu": "Quyết định thay thế từ Bộ GD&ĐT",
                "noi_ban_hanh": "Bộ Giáo dục và Đào tạo",
                "ngay_den": "2026-10-22T08:00:00Z",
                "pham_vi": "NOI_BO",
                "hieu_luc": "CON_HIEU_LUC",
                "link_thay_the": "15/QĐ [Nơi ban hành: Sở Giáo dục và Đào tạo - Số đến #10]",
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        new_doc_id = res.data["id"]
        new_doc = VanBanDen.objects.get(pk=new_doc_id)

        # Văn bản cũ tự động chuyển sang CON_HIEU_LUC_1_PHAN
        doc1.refresh_from_db()
        self.assertEqual(doc1.hieu_luc, HieuLuc.CON_HIEU_LUC_1_PHAN)
        self.assertIn("15/QĐ", doc1.link_thay_the)

        # Kiểm tra quan hệ 2 chiều
        rel_new = get_replacement_relations(new_doc)
        self.assertEqual(rel_new["thay_the_cho"], ["15/QĐ"])
        self.assertEqual(rel_new["bi_thay_boi"], [])

        rel_old = get_replacement_relations(doc1)
        self.assertEqual(rel_old["thay_the_cho"], [])
        self.assertEqual(rel_old["bi_thay_boi"], ["15/QĐ"])

    def test_same_so_hieu_cross_replacement_inbound_restricted(self):
        """
        Văn bản Đến Hạn chế (HAN_CHE): Cho phép 2 văn bản hạn chế trùng số hiệu thay thế nhau.
        """
        doc1_hc = VanBanDen.objects.create(
            nam=2026,
            so_hieu="08/BC-HC",
            so_thu_tu=50,
            pham_vi=PhamVi.HAN_CHE,
            noi_ban_hanh="Đối tác An Ninh",
            trich_yeu="Báo cáo kỹ thuật hạn chế số 1",
            hieu_luc=HieuLuc.CON_HIEU_LUC,
            nguoi_tao=self.admin,
        )

        res = self.client.post(
            "/api/documents/",
            {
                "loai": "DEN",
                "nam": 2026,
                "so_hieu": "08/BC-HC",
                "trich_yeu": "Báo cáo kỹ thuật hạn chế số 2 thay thế số 1",
                "noi_ban_hanh": "Đối tác Bảo Mật",
                "ngay_den": "2026-10-22T08:00:00Z",
                "pham_vi": "HAN_CHE",
                "nguoi_nhan": [self.admin.id],
                "hieu_luc": "CON_HIEU_LUC",
                "link_thay_the": "08/BC-HC [Nơi ban hành: Đối tác An Ninh - Số đến #50]",
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        doc1_hc.refresh_from_db()
        self.assertEqual(doc1_hc.hieu_luc, HieuLuc.CON_HIEU_LUC_1_PHAN)
        self.assertIn("08/BC-HC", doc1_hc.link_thay_the)

    def test_strict_self_replacement_prevention_with_same_so_hieu(self):
        """
        Bảo vệ tuyệt đối: Dù cùng số hiệu hay khác số hiệu, văn bản không thể tự thay thế chính mình.
        """
        doc_self = VanBanDen.objects.create(
            nam=2026,
            so_hieu="20/TB",
            so_thu_tu=30,
            pham_vi=PhamVi.NOI_BO,
            noi_ban_hanh="Sở Nội vụ",
            trich_yeu="Thông báo ban đầu",
            hieu_luc=HieuLuc.CON_HIEU_LUC,
            nguoi_tao=self.admin,
        )

        # 1. Thử cập nhật trỏ đích danh vào chính nó kèm #stt
        res_fail1 = self.client.patch(
            f"/api/documents/{doc_self.id}/?loai=DEN",
            {
                "link_thay_the": "20/TB [Nơi ban hành: Sở Nội vụ - Số đến #30]",
            },
            format="json",
        )
        self.assertEqual(res_fail1.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("link_thay_the", res_fail1.data)
        self.assertIn("không thể tự thiết lập thay thế chính nó", str(res_fail1.data["link_thay_the"][0]))

        # 2. Thử cập nhật trỏ số hiệu thô khi trong CSDL chỉ có chính nó
        res_fail2 = self.client.patch(
            f"/api/documents/{doc_self.id}/?loai=DEN",
            {
                "link_thay_the": "20/TB",
            },
            format="json",
        )
        self.assertEqual(res_fail2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("link_thay_the", res_fail2.data)
        self.assertIn("không thể tự thiết lập thay thế chính nó", str(res_fail2.data["link_thay_the"][0]))


@override_settings(DOCUMENT_STORAGE_ROOT=TEMP_STORAGE_ROOT)
class ExcelAttachmentAndOldfileTests(APITestCase):
    """Kiểm thử chuyên sâu cho tính năng Export/Import Excel kèm tệp đính kèm và kho lịch sử oldfile."""

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="excel_att_user",
            email="excel_att@example.com",
            password="password123",
            ho_ten="Tester Excel",
        )
        self.client.force_authenticate(user=self.user)

    def test_excel_template_includes_attachment_column(self):
        """Tất cả 4 mẫu Excel và mẫu Mật đều có cột 'Tệp đính kèm' trước 'Link văn bản thay thế'."""
        from documents.services import generate_excel_template
        import openpyxl

        configs = [
            ("DEN", "NOI_BO"),
            ("DEN", "HAN_CHE"),
            ("DI", "NOI_BO"),
            ("DI", "HAN_CHE"),
            ("MAT", "HAN_CHE"),
        ]

        for loai, pham_vi in configs:
            bio = generate_excel_template(loai, pham_vi)
            wb = openpyxl.load_workbook(bio)
            ws = wb.active
            headers = [cell.value for cell in ws[1] if cell.value]

            self.assertIn("Tệp đính kèm", headers, f"Thiếu cột 'Tệp đính kèm' trong mẫu {loai} {pham_vi}")
            idx_att = headers.index("Tệp đính kèm")
            idx_link = headers.index("Link văn bản thay thế")
            idx_note = headers.index("Ghi chú")

            # Thứ tự chuẩn: Tệp đính kèm -> Link văn bản thay thế -> Ghi chú
            self.assertEqual(idx_att + 1, idx_link)
            self.assertEqual(idx_link + 1, idx_note)

            # Cột có hover comment hướng dẫn
            cell_att_hdr = ws.cell(row=1, column=idx_att + 1)
            self.assertIsNotNone(cell_att_hdr.comment)
            self.assertIn("oldfile", cell_att_hdr.comment.text)

    def test_export_excel_with_attachments(self):
        """Export danh sách văn bản ra Excel điền đúng danh sách tên tệp đính kèm."""
        from documents.services import export_to_excel
        import openpyxl

        doc = VanBanDen.objects.create(
            nam=2026,
            so_hieu="88/CV-ATT",
            so_thu_tu=1,
            pham_vi=PhamVi.NOI_BO,
            noi_ban_hanh="Bộ GD&ĐT",
            trich_yeu="Công văn kiểm thử xuất tệp đính kèm",
            hieu_luc=HieuLuc.CON_HIEU_LUC,
            nguoi_tao=self.user,
        )
        VanBanDenAttachment.objects.create(
            document=doc,
            name="To_trinh_01.pdf",
            path="van-ban-den/noi-bo/2026/10/29/test1.pdf",
        )
        VanBanDenAttachment.objects.create(
            document=doc,
            name="Phu_luc_02.docx",
            path="van-ban-den/noi-bo/2026/10/29/test2.docx",
        )

        qs = VanBanDen.objects.filter(id=doc.id)
        bio = export_to_excel(qs, "DEN", "NOI_BO")
        wb = openpyxl.load_workbook(bio)
        ws = wb.active

        headers = [cell.value for cell in ws[1] if cell.value]
        self.assertIn("Tệp đính kèm", headers)
        idx_att = headers.index("Tệp đính kèm") + 1

        cell_val = ws.cell(row=2, column=idx_att).value
        self.assertIn("To_trinh_01.pdf", cell_val)
        self.assertIn("Phu_luc_02.docx", cell_val)
        self.assertIn(";", cell_val)

    def test_import_excel_with_oldfile_success_and_missing_warning(self):
        """Import Excel: tìm thấy file trong oldfile thì liên kết, thiếu file thì ghi cảnh báo rõ ràng."""
        import tempfile
        from pathlib import Path
        from django.test import override_settings
        from documents.services import import_from_excel
        from openpyxl import Workbook
        import io

        with tempfile.TemporaryDirectory() as temp_oldfile_dir:
            temp_oldfile = Path(temp_oldfile_dir)
            # Tạo thư mục và file thật trong kho oldfile: van-ban-den/noi-bo/2026/09/15/To_trinh_goc.pdf
            folder = temp_oldfile / "van-ban-den" / "noi-bo" / "2026" / "09" / "15"
            folder.mkdir(parents=True, exist_ok=True)
            real_file = folder / "To_trinh_goc.pdf"
            real_file.write_bytes(b"%PDF-1.4 test oldfile content")

            with override_settings(OLDFILE_STORAGE_ROOT=str(temp_oldfile)):
                wb = Workbook()
                ws = wb.active
                ws.append(["Số, ký hiệu VB", "Ngày đến", "Trích yếu nội dung", "Hiệu lực", "Phạm vi", "Tệp đính kèm"])
                # Dòng 1: có file tồn tại thật
                ws.append(["101/CV-OLD", "15/09/2026 08:30:00", "Công văn cũ có file thật", "CON_HIEU_LUC", "Nội bộ", "To_trinh_goc.pdf"])
                # Dòng 2: file không tồn tại
                ws.append(["102/CV-OLD", "15/09/2026 08:30:00", "Công văn cũ file không tồn tại", "CON_HIEU_LUC", "Nội bộ", "File_ao.pdf"])

                bio = io.BytesIO()
                wb.save(bio)
                bio.seek(0)

                res = import_from_excel(bio, "DEN", self.user, pham_vi="NOI_BO")
                self.assertEqual(res["created"], 2)

                # Dòng 1 gắn attachment thành công
                doc1 = VanBanDen.objects.get(so_hieu="101/CV-OLD")
                att1 = doc1.attachments.filter(is_deleted=False).first()
                self.assertIsNotNone(att1)
                self.assertEqual(att1.name, "To_trinh_goc.pdf")
                self.assertEqual(att1.path, "oldfile/van-ban-den/noi-bo/2026/09/15/To_trinh_goc.pdf")
                with att1.file.open("rb") as f:
                    file_bytes = f.read()
                self.assertEqual(file_bytes, b"%PDF-1.4 test oldfile content")
                att1.file.close()

                # Dòng 2 không gắn attachment và có cảnh báo trong errors
                doc2 = VanBanDen.objects.get(so_hieu="102/CV-OLD")
                self.assertEqual(doc2.attachments.count(), 0)
                self.assertTrue(any("File_ao.pdf" in err["message"] for err in res["errors"]))

    def test_import_excel_with_uploaded_attachments_success(self):
        """Import Excel nạp trực tiếp danh sách attachments tải lên và liên kết chính xác."""
        from documents.services import import_from_excel
        from openpyxl import Workbook
        import io

        wb = Workbook()
        ws = wb.active
        ws.append(["Số, ký hiệu VB", "Ngày đến", "Trích yếu nội dung", "Hiệu lực", "Phạm vi", "Tệp đính kèm"])
        # Dòng 1: Gắn 2 tệp tải lên
        ws.append(["103/CV-NEW", "20/10/2026 09:00:00", "Công văn kèm 2 file tải lên", "CON_HIEU_LUC", "Nội bộ", "CV_DinhKem_1.pdf; CV_DinhKem_2.docx"])
        # Dòng 2: Tệp không có trong danh sách tải lên
        ws.append(["104/CV-NEW", "20/10/2026 09:00:00", "Công văn tệp không có", "CON_HIEU_LUC", "Nội bộ", "Khong_Co.pdf"])

        bio = io.BytesIO()
        wb.save(bio)
        bio.seek(0)

        uploaded_files = [
            SimpleUploadedFile("CV_DinhKem_1.pdf", b"%PDF-1.4 sample content 1", content_type="application/pdf"),
            SimpleUploadedFile("CV_DinhKem_2.docx", b"sample content 2", content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        ]

        res = import_from_excel(bio, "DEN", self.user, pham_vi="NOI_BO", attachments=uploaded_files)
        self.assertEqual(res["created"], 2)

        doc1 = VanBanDen.objects.get(so_hieu="103/CV-NEW")
        self.assertEqual(doc1.attachments.count(), 2)
        att_names = set(doc1.attachments.values_list("name", flat=True))
        self.assertEqual(att_names, {"CV_DinhKem_1.pdf", "CV_DinhKem_2.docx"})

        # Kiểm tra nội dung tệp lưu trữ
        att1 = doc1.attachments.get(name="CV_DinhKem_1.pdf")
        with att1.file.open("rb") as f:
            content1 = f.read()
        self.assertEqual(content1, b"%PDF-1.4 sample content 1")
        att1.file.close()

        # Dòng 2 không có tệp và trả về thông báo lỗi/cảnh báo
        doc2 = VanBanDen.objects.get(so_hieu="104/CV-NEW")
        self.assertEqual(doc2.attachments.count(), 0)
        self.assertTrue(any("Khong_Co.pdf" in err["message"] for err in res["errors"]))

    def test_import_excel_past_date_parsing(self):
        """Kiểm tra hàm _parse_date chấp nhận linh hoạt các mốc ngày giờ trong quá khứ."""
        from documents.services import _parse_date
        from datetime import date, datetime

        # Chuỗi ngày giờ quá khứ định dạng dd/mm/yyyy hh:mm:ss
        dt1 = _parse_date("15/08/2015 10:15:30")
        self.assertIsNotNone(dt1)
        self.assertEqual(dt1.year, 2015)
        self.assertEqual(dt1.month, 8)
        self.assertEqual(dt1.day, 15)
        self.assertEqual(dt1.hour, 10)
        self.assertEqual(dt1.minute, 15)

        # Chuỗi ngày quá khứ yyyy-mm-dd
        dt2 = _parse_date("2010-04-20")
        self.assertIsNotNone(dt2)
        self.assertEqual(dt2.year, 2010)
        self.assertEqual(dt2.month, 4)
        self.assertEqual(dt2.day, 20)

        # Đối tượng date từ openpyxl
        d_obj = date(1998, 12, 25)
        dt3 = _parse_date(d_obj)
        self.assertIsNotNone(dt3)
        self.assertEqual(dt3.year, 1998)
        self.assertEqual(dt3.month, 12)
        self.assertEqual(dt3.day, 25)

        # Đối tượng datetime từ openpyxl
        dt_obj = datetime(2005, 6, 1, 8, 30, 0)
        dt4 = _parse_date(dt_obj)
        self.assertIsNotNone(dt4)
        self.assertEqual(dt4.year, 2005)
        self.assertEqual(dt4.month, 6)
        self.assertEqual(dt4.day, 1)

    def test_api_import_excel_with_attachments_endpoint(self):
        """API endpoint /api/documents/import/ nhận file Excel và multipart attachments."""
        from openpyxl import Workbook
        import io

        self.user.is_superuser = True
        self.user.save()

        wb = Workbook()
        ws = wb.active
        ws.append(["Số, ký hiệu VB", "Ngày đến", "Trích yếu nội dung", "Hiệu lực", "Phạm vi", "Tệp đính kèm"])
        ws.append(["105/CV-API", "25/10/2026 14:00:00", "Công văn test qua API kèm file", "CON_HIEU_LUC", "Nội bộ", "API_Doc.pdf"])

        excel_bio = io.BytesIO()
        wb.save(excel_bio)
        excel_bio.seek(0)

        excel_file = SimpleUploadedFile("van_ban_import.xlsx", excel_bio.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        pdf_file = SimpleUploadedFile("API_Doc.pdf", b"%PDF-1.4 test api attachment", content_type="application/pdf")

        response = self.client.post(
            "/api/documents/import/?loai=DEN&pham_vi=NOI_BO",
            {
                "file": excel_file,
                "attachments": [pdf_file],
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data.get("created"), 1)

        doc = VanBanDen.objects.get(so_hieu="105/CV-API")
        self.assertEqual(doc.attachments.count(), 1)
        att = doc.attachments.first()
        self.assertEqual(att.name, "API_Doc.pdf")

    def test_import_excel_outbound_with_multiple_attachments_and_normalization(self):
        """Import Văn bản Đi với 2 tệp đính kèm (có khoảng trắng thừa trước đuôi file) vẫn nhận diện đủ cả 2."""
        from documents.services import import_from_excel
        from openpyxl import Workbook
        import io

        wb = Workbook()
        ws = wb.active
        ws.append(["Số, ký hiệu VB", "Ngày ban hành", "Trích yếu nội dung", "Hiệu lực", "Phạm vi", "Tệp đính kèm"])
        # Ghi 2 tệp trong đó tệp 1 có khoảng trắng thừa trước dấu chấm (.pdf)
        ws.append(["201/DI-NORM", "25/10/2026", "Công văn đi test 2 file đính kèm", "CON_HIEU_LUC", "Nội bộ", "CV_Di_1 .pdf; CV_Di_2.docx"])

        excel_bio = io.BytesIO()
        wb.save(excel_bio)
        excel_bio.seek(0)

        f1 = SimpleUploadedFile("CV_Di_1.pdf", b"%PDF-1.4 content di 1", content_type="application/pdf")
        f2 = SimpleUploadedFile("CV_Di_2.docx", b"content di 2", content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

        res = import_from_excel(excel_bio, "DI", self.user, pham_vi="NOI_BO", attachments=[f1, f2])
        self.assertEqual(res["created"], 1)

        doc = VanBanDi.objects.get(so_hieu="201/DI-NORM")
        self.assertEqual(doc.attachments.count(), 2)
        att_names = set(doc.attachments.values_list("name", flat=True))
        self.assertIn("CV_Di_1 .pdf", att_names)
        self.assertIn("CV_Di_2.docx", att_names)

    def test_import_excel_with_smart_extension_matching(self):
        """Khớp thông minh định dạng tệp: Excel ghi .doc nhưng tệp tải lên là .docx (hoặc không ghi đuôi) vẫn nhận đủ."""
        from documents.services import import_from_excel
        from openpyxl import Workbook
        import io

        wb = Workbook()
        ws = wb.active
        ws.append(["Số, ký hiệu VB", "Ngày ban hành", "Trích yếu nội dung", "Hiệu lực", "Phạm vi", "Tệp đính kèm"])
        # Cột tệp ghi: 1 file pdf, 1 file .doc (nhưng thực tế là .docx), 1 file không đuôi (nhưng thực tế là .xlsx)
        ws.append(["202/DI-SMART", "25/10/2026", "VB test smart extension", "CON_HIEU_LUC", "Nội bộ", "HoaDon_test.pdf; QNA.doc; BangLuong"])

        excel_bio = io.BytesIO()
        wb.save(excel_bio)
        excel_bio.seek(0)

        f1 = SimpleUploadedFile("HoaDon_test.pdf", b"%PDF-1.4 sample", content_type="application/pdf")
        f2 = SimpleUploadedFile("QNA.docx", b"docx sample content", content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        f3 = SimpleUploadedFile("BangLuong.png", b"\x89PNG\r\n\x1a\n sample", content_type="image/png")

        res = import_from_excel(excel_bio, "DI", self.user, pham_vi="NOI_BO", attachments=[f1, f2, f3])
        self.assertEqual(res["created"], 1)
        self.assertEqual(len(res["errors"]), 0)

        doc = VanBanDi.objects.get(so_hieu="202/DI-SMART")
        self.assertEqual(doc.attachments.count(), 3)
        att_names = set(doc.attachments.values_list("name", flat=True))
        self.assertIn("HoaDon_test.pdf", att_names)
        self.assertIn("QNA.docx", att_names)
        self.assertIn("BangLuong.png", att_names)

    def test_delete_outbound_document_with_same_id_as_inbound_restricted(self):
        """Xóa Văn bản Đi khi tồn tại Văn bản Đến Hạn chế có cùng ID: gọi với ?loai=DI xóa đúng Văn bản Đi."""
        self.user.is_superuser = True
        self.user.save()

        # Tạo 1 VB Đến Hạn chế
        doc_den = VanBanDen.objects.create(
            so_hieu="100/DEN-HC",
            pham_vi=PhamVi.HAN_CHE,
            trich_yeu="Văn bản đến hạn chế cấm xóa",
            nguoi_tao=self.user,
        )
        # Tạo 1 VB Đi Nội bộ và gán cùng ID với doc_den để kiểm thử trùng ID giữa 2 bảng
        doc_di = VanBanDi(
            id=doc_den.id,
            so_hieu="100/DI-NB",
            pham_vi=PhamVi.NOI_BO,
            trich_yeu="Văn bản đi nội bộ được phép xóa",
            nguoi_tao=self.user,
        )
        doc_di.save(force_insert=True)

        # 1. Gọi DELETE không có loai=DI nhưng có Header Referer từ trang văn bản đi
        res1 = self.client.delete(f"/api/documents/{doc_di.id}/?loai=DI")
        self.assertEqual(res1.status_code, status.HTTP_204_NO_CONTENT)

        # Kiểm chứng: Văn bản Đi đã bị xóa
        self.assertFalse(VanBanDi.objects.filter(id=doc_di.id).exists())
        # Văn bản Đến Hạn chế vẫn an toàn, không hề bị ảnh hưởng
        self.assertTrue(VanBanDen.objects.filter(id=doc_den.id).exists())



class HieuLucPermissionTests(APITestCase):
    """
    Bộ test kiểm tra phân quyền thay đổi hiệu lực văn bản (Hợp đồng Nhóm 7):
    - change_hieu_luc_vanbanden
    - change_hieu_luc_vanbandi
    """

    def setUp(self):
        from django.contrib.contenttypes.models import ContentType
        from django.contrib.auth.models import Permission, Group

        self.admin = User.objects.create_superuser(username="admin_hl", password="password123", is_staff=True)
        self.staff1 = User.objects.create_user(username="staff_hl1", password="password123")
        self.staff2 = User.objects.create_user(username="staff_hl2", password="password123")
        self.vanthu = User.objects.create_user(username="vanthu_hl", password="password123")

        # Cấp quyền tạo/sửa văn bản thông thường cho staff1 và staff2
        ct_den = ContentType.objects.get_for_model(VanBanDen)
        ct_di = ContentType.objects.get_for_model(VanBanDi)

        def get_or_create_perm(codename, name, module_ten, ct):
            perm = Permission.objects.filter(codename=codename).first()
            if not perm:
                from django.db import connection
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO auth_permission (name, codename, module_ten, content_type_id)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (codename) DO NOTHING
                        """,
                        [name, codename, module_ten, ct.pk if ct else None],
                    )
                perm = Permission.objects.filter(codename=codename).first()
            return perm

        perm_add_den = get_or_create_perm("add_vanbanden", "Thêm VB Đến", "Văn bản đến", ct_den)
        perm_change_den = get_or_create_perm("change_vanbanden", "Sửa VB Đến", "Văn bản đến", ct_den)
        perm_add_di = get_or_create_perm("add_vanbandi", "Thêm VB Đi", "Văn bản đi", ct_di)
        perm_change_di = get_or_create_perm("change_vanbandi", "Sửa VB Đi", "Văn bản đi", ct_di)

        self.staff1.user_permissions.add(perm_add_den, perm_change_den, perm_add_di, perm_change_di)
        self.staff2.user_permissions.add(perm_add_den, perm_change_den, perm_add_di, perm_change_di)

        # Tạo sẵn quyền đổi hiệu lực
        self.perm_hl_den = get_or_create_perm("change_hieu_luc_vanbanden", "Đổi hiệu lực văn bản đến", "Văn bản đến", ct_den)
        self.perm_hl_di = get_or_create_perm("change_hieu_luc_vanbandi", "Đổi hiệu lực văn bản đi", "Văn bản đi", ct_di)

        # Mặc định của Nhóm 7: Nhóm Văn thư (VT) có quyền sửa văn bản và đổi hiệu lực
        group_vt, _ = Group.objects.get_or_create(name="VT")
        group_vt.permissions.add(perm_change_den, perm_change_di, self.perm_hl_den, self.perm_hl_di)
        self.vanthu.groups.add(group_vt)

        # Tạo 1 văn bản đến và 1 văn bản đi do staff1 tạo
        self.doc_den = VanBanDen.objects.create(
            so_hieu="10/DEN-HL",
            so_thu_tu=10,
            trich_yeu="Văn bản đến test hiệu lực",
            nguoi_tao=self.staff1,
            hieu_luc=HieuLuc.CON_HIEU_LUC,
            pham_vi=PhamVi.NOI_BO,
        )
        self.doc_di = VanBanDi.objects.create(
            so_hieu="20/DI-HL",
            so_thu_tu=20,
            trich_yeu="Văn bản đi test hiệu lực",
            nguoi_tao=self.staff1,
            hieu_luc=HieuLuc.CON_HIEU_LUC,
            pham_vi=PhamVi.NOI_BO,
        )

    def test_user_without_perm_cannot_change_hieu_luc_on_update(self):
        """Người dùng có quyền sửa văn bản nhưng KHÔNG có quyền đổi hiệu lực thì bị từ chối khi sửa hieu_luc."""
        client = APIClient()
        client.force_authenticate(user=self.staff1)

        # 1. Sửa trích yếu bình thường mà không đổi hiệu lực -> 200 OK
        res = client.patch(
            f"/api/documents/{self.doc_den.id}/",
            {"trich_yeu": "Trích yếu mới hợp lệ"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # 2. Cố tình gửi hieu_luc khác giá trị hiện tại -> Bị từ chối 400 ValidationError
        res_fail = client.patch(
            f"/api/documents/{self.doc_den.id}/",
            {"hieu_luc": HieuLuc.HET_HIEU_LUC},
            format="json",
        )
        self.assertEqual(res_fail.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("hieu_luc", res_fail.data)
        self.doc_den.refresh_from_db()
        self.assertEqual(self.doc_den.hieu_luc, HieuLuc.CON_HIEU_LUC)

    def test_user_with_perm_can_change_hieu_luc(self):
        """Người dùng được cấp quyền change_hieu_luc_vanbanden có thể đổi hiệu lực thành công."""
        self.staff1.user_permissions.add(self.perm_hl_den)
        self.staff1 = User.objects.get(pk=self.staff1.pk)

        client = APIClient()
        client.force_authenticate(user=self.staff1)

        res = client.patch(
            f"/api/documents/{self.doc_den.id}/",
            {"hieu_luc": HieuLuc.HET_HIEU_LUC},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.doc_den.refresh_from_db()
        self.assertEqual(self.doc_den.hieu_luc, HieuLuc.HET_HIEU_LUC)

    def test_admin_and_vanthu_can_change_hieu_luc(self):
        """Admin và Văn thư (role vt) có quyền đổi hiệu lực mà không cần gán thêm quyền lẻ."""
        client = APIClient()

        # Admin
        client.force_authenticate(user=self.admin)
        res_admin = client.patch(
            f"/api/documents/{self.doc_den.id}/",
            {"hieu_luc": HieuLuc.CON_HIEU_LUC_1_PHAN},
            format="json",
        )
        self.assertEqual(res_admin.status_code, status.HTTP_200_OK)

        # Văn thư (role vt)
        client.force_authenticate(user=self.vanthu)
        res_vt = client.patch(
            f"/api/documents/{self.doc_den.id}/",
            {"hieu_luc": HieuLuc.HET_HIEU_LUC},
            format="json",
        )
        self.assertEqual(res_vt.status_code, status.HTTP_200_OK)

    def test_create_document_with_non_default_hieu_luc_restricted(self):
        """Người không có quyền chỉ được để giá trị mặc định CON_HIEU_LUC khi tạo văn bản."""
        client = APIClient()
        client.force_authenticate(user=self.staff2)

        # 1. Tạo với hieu_luc=HET_HIEU_LUC khi chưa có quyền -> 400
        res_fail = client.post(
            "/api/documents/",
            {
                "loai": "DEN",
                "so_hieu": "NEW-FAIL/2026",
                "trich_yeu": "Tạo văn bản test hieu_luc",
                "hieu_luc": HieuLuc.HET_HIEU_LUC,
            },
            format="json",
        )
        self.assertEqual(res_fail.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("hieu_luc", res_fail.data)

        # 2. Tạo với giá trị mặc định CON_HIEU_LUC -> 201 Created
        res_ok = client.post(
            "/api/documents/",
            {
                "loai": "DEN",
                "so_hieu": "NEW-OK/2026",
                "trich_yeu": "Tạo văn bản hợp lệ",
                "hieu_luc": HieuLuc.CON_HIEU_LUC,
            },
            format="json",
        )
        self.assertEqual(res_ok.status_code, status.HTTP_201_CREATED)

    def test_vanbandi_hieu_luc_permission(self):
        """Kiểm tra quyền change_hieu_luc_vanbandi cho Văn bản Đi."""
        client = APIClient()
        client.force_authenticate(user=self.staff1)

        # Chưa có quyền -> Thất bại khi đổi hiệu lực văn bản đi
        res_fail = client.patch(
            f"/api/documents/{self.doc_di.id}/",
            {"hieu_luc": HieuLuc.HET_HIEU_LUC},
            format="json",
        )
        self.assertEqual(res_fail.status_code, status.HTTP_400_BAD_REQUEST)

        # Cấp quyền -> Thành công
        self.staff1.user_permissions.add(self.perm_hl_di)
        self.staff1 = User.objects.get(pk=self.staff1.pk)
        client.force_authenticate(user=self.staff1)

        res_ok = client.patch(
            f"/api/documents/{self.doc_di.id}/",
            {"hieu_luc": HieuLuc.HET_HIEU_LUC},
            format="json",
        )
        self.assertEqual(res_ok.status_code, status.HTTP_200_OK)

    def test_detail_serializer_can_change_hieu_luc_flag(self):
        """API chi tiết văn bản trả về cờ can_change_hieu_luc chính xác theo quyền của user."""
        client = APIClient()

        # Staff1 không có quyền đổi hiệu lực
        client.force_authenticate(user=self.staff1)
        res1 = client.get(f"/api/documents/{self.doc_den.id}/")
        self.assertEqual(res1.status_code, status.HTTP_200_OK)
        self.assertFalse(res1.data.get("can_change_hieu_luc"))

        # Admin có quyền
        client.force_authenticate(user=self.admin)
        res2 = client.get(f"/api/documents/{self.doc_den.id}/")
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertTrue(res2.data.get("can_change_hieu_luc"))









