"""
Test suite xác thực toàn bộ 11 bản sửa lỗi Backend (8 lỗ hổng bảo mật/logic mới phát hiện + 3 lỗi từ Sheet).
"""

from datetime import timedelta
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from documents.models import (
    HieuLuc,
    LoaiVanBan,
    PhamVi,
    VanBanDen,
    VanBanDi,
    Folder,
    FolderFile,
)
from documents.services import cleanup_replacement_links_on_delete
from organizations.models import DonVi, KhoiKhuVuc
from records.models import HoSo, LoaiVanBan as RecordLoaiVanBan

User = get_user_model()


class BackendFixesSecurityAndLogicTests(TestCase):
    def setUp(self):
        user_kwargs = {"username": "normal_user", "password": "password123"}
        if hasattr(User, "ho_ten"):
            user_kwargs["ho_ten"] = "Normal User"
        self.user = User.objects.create_user(**user_kwargs)

        other_kwargs = {"username": "other_user", "password": "password123"}
        if hasattr(User, "ho_ten"):
            other_kwargs["ho_ten"] = "Other User"
        self.other_user = User.objects.create_user(**other_kwargs)

        admin_kwargs = {"username": "admin_user", "password": "password123", "is_staff": True, "is_superuser": True}
        if hasattr(User, "ho_ten"):
            admin_kwargs["ho_ten"] = "Admin User"
        self.admin_user = User.objects.create_user(**admin_kwargs)

        self.client = APIClient()

    # ─────────────────────────────────────────────────────────────
    # 1. Path Traversal & File Uploads Protection
    # ─────────────────────────────────────────────────────────────
    def test_path_traversal_blocked_in_folder_file_download(self):
        """P0: Chặn Path Traversal trong FolderFileViewSet.download."""
        self.client.force_authenticate(user=self.user)
        folder = Folder.objects.create(name="Thư mục test", created_by=self.user)
        malicious_file = FolderFile.objects.create(
            folder=folder,
            file_name="traversal.txt",
            file_path="../../etc/passwd",
            file_size=10,
            uploaded_by=self.user,
        )
        res = self.client.get(f"/api/folder-files/{malicious_file.id}/download/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("Path Traversal", res.data.get("detail", ""))

    def test_folder_files_disallowed_extension_rejected(self):
        """P2: File upload trong FolderViewSet.files phải kiểm tra định dạng cho phép."""
        self.client.force_authenticate(user=self.user)
        folder = Folder.objects.create(name="Folder Ext Test", created_by=self.user)
        res = self.client.post(
            f"/api/folders/{folder.id}/files/",
            {"file_name": "virus.exe", "file_size": 100},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("không được phép", res.data.get("detail", ""))

    def test_folder_delete_and_move_permissions(self):
        """P2: User thường không được xóa hoặc di chuyển thư mục của người khác."""
        folder_a = Folder.objects.create(name="Folder A", created_by=self.user)
        folder_dest = Folder.objects.create(name="Folder Dest", created_by=self.user)

        # Other user cố xóa -> 403
        self.client.force_authenticate(user=self.other_user)
        res = self.client.delete(f"/api/folders/{folder_a.id}/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        # Other user cố di chuyển -> 403
        res = self.client.patch(f"/api/folders/{folder_a.id}/move/", {"target_parent_id": folder_dest.id}, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        # Admin có quyền xóa -> 204
        self.client.force_authenticate(user=self.admin_user)
        res = self.client.delete(f"/api/folders/{folder_a.id}/")
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

    # ─────────────────────────────────────────────────────────────
    # 2. Dedicated ViewSets RBAC & IDOR Protection
    # ─────────────────────────────────────────────────────────────
    def test_dedicated_viewsets_permission_checks(self):
        """P1: Chặn IDOR và thiếu kiểm tra quyền trên VanBanDenViewSet & VanBanDiViewSet."""
        doc_den = VanBanDen.objects.create(
            nam=2026,
            so_hieu="01/CV-TEST",
            so_thu_tu=1,
            trich_yeu="Văn bản đến test",
            nguoi_tao=self.admin_user,
        )
        doc_di = VanBanDi.objects.create(
            nam=2026,
            so_hieu="01/TB-TEST",
            so_thu_tu=1,
            trich_yeu="Văn bản đi test",
            ngay_ban_hanh=timezone.now(),
            nguoi_tao=self.admin_user,
        )

        # User thường không có quyền chỉnh sửa văn bản của admin
        self.client.force_authenticate(user=self.user)
        res = self.client.patch(f"/api/documents/den/{doc_den.id}/", {"trich_yeu": "Sửa lén"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        res = self.client.patch(f"/api/documents/di/{doc_di.id}/", {"trich_yeu": "Sửa lén"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        # User thường không có quyền tạo văn bản
        res = self.client.post(f"/api/documents/den/", {"so_hieu": "99/DEN", "trich_yeu": "Tạo lén"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        res = self.client.post(f"/api/documents/di/", {"so_hieu": "99/DI", "trich_yeu": "Tạo lén", "ngay_ban_hanh": timezone.now().isoformat()}, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    # ─────────────────────────────────────────────────────────────
    # 3. Expiration Date Earlier Than Issue Date Logic Flaw
    # ─────────────────────────────────────────────────────────────
    def test_expiration_earlier_than_issue_date_rejected(self):
        """P2: Ngày hết hiệu lực không được nhỏ hơn ngày ban hành / ngày đến."""
        self.client.force_authenticate(user=self.admin_user)
        now = timezone.now()
        yesterday = now - timedelta(days=2)

        res = self.client.post(
            "/api/documents/",
            {
                "loai": "DEN",
                "nam": 2026,
                "so_hieu": "100/CV-EXP",
                "trich_yeu": "Test hạn hiệu lực",
                "ngay_den": now.isoformat(),
                "ngay_het_hieu_luc": yesterday.isoformat(),
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("ngay_het_hieu_luc", res.data)

    # ─────────────────────────────────────────────────────────────
    # 4. Sheet Issues: Relations danh_muc_ho_so, ten_loai_van_ban, noi_ban_hanh
    # ─────────────────────────────────────────────────────────────
    def test_danh_muc_ho_so_and_ten_loai_van_ban_persisted(self):
        """Lỗi Sheet Dòng 15: Lưu và truy xuất danh_muc_ho_so & ten_loai_van_ban."""
        self.client.force_authenticate(user=self.admin_user)
        hs = HoSo.objects.create(
            stt_uu_tien=8888,
            so_ky_hieu="HS-UNIQUE-88",
            ten_ho_so="Hồ sơ quản lý nhân sự",
            nguoi_lap=self.admin_user,
        )
        lvb = RecordLoaiVanBan.objects.create(
            ho_so=hs,
            ten_loai="Quyết định bổ nhiệm",
        )

        res = self.client.post(
            "/api/documents/",
            {
                "loai": "DEN",
                "nam": 2026,
                "so_hieu": "200/QD-TEST",
                "trich_yeu": "Quyết định thử nghiệm",
                "danh_muc_ho_so": hs.ten_ho_so,
                "ten_loai_van_ban": lvb.ten_loai,
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        doc_id = res.data["id"]

        # Kiểm tra API Detail trả về đúng tên hồ sơ và loại văn bản từ quan hệ
        res_detail = self.client.get(f"/api/documents/{doc_id}/")
        self.assertEqual(res_detail.status_code, status.HTTP_200_OK)
        self.assertEqual(res_detail.data["danh_muc_ho_so"], "Hồ sơ quản lý nhân sự")
        self.assertEqual(res_detail.data["ten_loai_van_ban"], "Quyết định bổ nhiệm")

    def test_vanbandi_noi_ban_hanh_persisted_and_filtered(self):
        """Lỗi Sheet Dòng 14: Lưu và truy xuất noi_ban_hanh cho Văn bản Đi."""
        self.client.force_authenticate(user=self.admin_user)
        khoi = KhoiKhuVuc.objects.first() or KhoiKhuVuc.objects.create(ten="Khối 1")
        don_vi = DonVi.objects.create(
            khoi=khoi,
            stt_uu_tien=8888,
            ten="Phòng Đào tạo - Khảo thí",
        )

        now = timezone.now()
        res = self.client.post(
            "/api/documents/",
            {
                "loai": "DI",
                "nam": 2026,
                "so_hieu": "300/TB-PDT",
                "trich_yeu": "Thông báo thi tốt nghiệp",
                "ngay_ban_hanh": now.isoformat(),
                "noi_ban_hanh": don_vi.ten,
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        doc_id = res.data["id"]

        # Kiểm tra detail trả về nơi ban hành
        res_detail = self.client.get(f"/api/documents/{doc_id}/")
        self.assertEqual(res_detail.status_code, status.HTTP_200_OK)
        self.assertEqual(res_detail.data["noi_ban_hanh"], "Phòng Đào tạo - Khảo thí")

        # Kiểm tra lọc theo noi_ban_hanh
        res_filter = self.client.get("/api/documents/?loai=DI&noi_ban_hanh=Khảo thí")
        self.assertEqual(res_filter.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(res_filter.data["count"], 1)

    # ─────────────────────────────────────────────────────────────
    # 5. Status Restoration on Delete of Replacement Target
    # ─────────────────────────────────────────────────────────────
    def test_status_restoration_logic_on_replacement_delete(self):
        """P2: Khôi phục hiệu lực chỉ khi không còn liên kết thay thế nào khác."""
        doc_a = VanBanDen.objects.create(
            nam=2026,
            so_hieu="DOC-A",
            so_thu_tu=1,
            trich_yeu="Văn bản cũ",
            hieu_luc=HieuLuc.HET_VA_THAY_THE,
            link_thay_the="DOC-B, DOC-C",
            nguoi_tao=self.admin_user,
        )
        doc_b = VanBanDen.objects.create(
            nam=2026,
            so_hieu="DOC-B",
            so_thu_tu=2,
            trich_yeu="Văn bản thay thế 1",
            hieu_luc=HieuLuc.CON_HIEU_LUC,
            nguoi_tao=self.admin_user,
        )
        doc_c = VanBanDen.objects.create(
            nam=2026,
            so_hieu="DOC-C",
            so_thu_tu=3,
            trich_yeu="Văn bản thay thế 2",
            hieu_luc=HieuLuc.CON_HIEU_LUC,
            nguoi_tao=self.admin_user,
        )

        # Xóa DOC-B: DOC-A vẫn còn DOC-C thay thế -> giữ HET_VA_THAY_THE
        cleanup_replacement_links_on_delete(doc_b)
        doc_a.refresh_from_db()
        self.assertEqual(doc_a.hieu_luc, HieuLuc.HET_VA_THAY_THE)
        self.assertEqual(doc_a.link_thay_the, "DOC-C")

        # Xóa nốt DOC-C: DOC-A không còn ai thay thế -> khôi phục CON_HIEU_LUC
        cleanup_replacement_links_on_delete(doc_c)
        doc_a.refresh_from_db()
        self.assertEqual(doc_a.hieu_luc, HieuLuc.CON_HIEU_LUC)
        self.assertEqual(doc_a.link_thay_the, "")
