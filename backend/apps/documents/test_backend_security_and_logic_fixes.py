"""
Tests kiểm thử toàn diện các bản sửa lỗi logic nghiệp vụ và bảo mật Backend:
1. Chống tấn công Path Traversal / Arbitrary File Read trong FolderFileViewSet.download
2. Giới hạn phần mở rộng tệp tin an toàn trong FolderViewSet.files
3. Phân quyền xóa và di chuyển thư mục (FolderViewSet.destroy & move)
4. Ràng buộc ngày hết hiệu lực phải sau hoặc bằng ngày ban hành / ngày đến
5. Lưu trữ và truy xuất danh_muc_ho_so, ten_loai_van_ban, noi_ban_hanh vào các bảng quan hệ
6. Phân quyền can_edit_document và can_create_document trong các ViewSet chuyên biệt
7. Logic khôi phục hiệu lực khi xóa văn bản thay thế (bảo toàn trạng thái nếu còn liên kết khác hoặc đã hết hạn)
"""

import tempfile
import datetime
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from documents.models import (
    VanBanDen,
    VanBanDi,
    VanBanMat,
    Folder,
    FolderFile,
    HieuLuc,
    PhamVi,
    LoaiVanBan,
    VanBanDenHoSo,
    VanBanDenDanhmuc,
    VanBanDiNoiBanHanh,
)
from documents.services import cleanup_replacement_links_on_delete
from organizations.models import DonVi, KhoiKhuVuc
from records.models import HoSo, LoaiVanBan as RecordLoaiVanBan

User = get_user_model()
TEMP_STORAGE = tempfile.mkdtemp()


@override_settings(DOCUMENT_STORAGE_ROOT=TEMP_STORAGE, MEDIA_ROOT=TEMP_STORAGE)
class BackendSecurityAndLogicFixesTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin_sec",
            email="admin_sec@example.com",
            password="adminpassword123",
        )
        self.staff_user = User.objects.create_user(
            username="staff_sec",
            email="staff_sec@example.com",
            password="staffpassword123",
        )
        self.other_staff = User.objects.create_user(
            username="other_sec",
            email="other_sec@example.com",
            password="otherpassword123",
        )

        khoi = KhoiKhuVuc.objects.create(ten="Khối Văn phòng", thu_tu_hien_thi=1)
        self.don_vi = DonVi.objects.create(khoi=khoi, ten="Văn phòng Bộ", stt_uu_tien=100)
        self.ho_so = HoSo.objects.create(so_ky_hieu="HS-01", ten_ho_so="Hồ sơ tài liệu năm 2026", nguoi_lap=self.staff_user)
        self.record_loai_vb = RecordLoaiVanBan.objects.create(ho_so=self.ho_so, ten_loai="Chỉ thị")

    def test_path_traversal_prevention_on_folder_file_download(self):
        """1. Kiểm tra FolderFileViewSet.download chặn triệt để tấn công Path Traversal."""
        folder = Folder.objects.create(name="Secure Folder", created_by=self.admin_user)
        # Tạo FolderFile chứa file_path cố tình traversal ra ngoài root
        malicious_file = FolderFile.objects.create(
            file_name="passwd",
            folder=folder,
            file_path="../../../../etc/passwd",
            file_size=100,
        )

        client = APIClient()
        client.force_authenticate(user=self.admin_user)

        res = client.get(f"/api/folder-files/{malicious_file.pk}/download/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("Path Traversal", res.data.get("detail", ""))

    def test_folder_file_extension_restriction(self):
        """2. Kiểm tra FolderViewSet.files chặn upload file có phần mở rộng nguy hiểm (.exe, .sh)."""
        folder = Folder.objects.create(name="Upload Test", created_by=self.admin_user)
        client = APIClient()
        client.force_authenticate(user=self.admin_user)

        # Upload file .exe nguy hiểm
        bad_file = SimpleUploadedFile("payload.exe", b"malicious binary content", content_type="application/octet-stream")
        res_bad = client.post(
            f"/api/folders/{folder.pk}/files/",
            {"file": bad_file, "name": "payload.exe"},
            format="multipart",
        )
        self.assertEqual(res_bad.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("không được phép", res_bad.data.get("detail", ""))

        # Upload file hợp lệ .pdf
        good_file = SimpleUploadedFile("report.pdf", b"%PDF-1.4 sample content", content_type="application/pdf")
        res_good = client.post(
            f"/api/folders/{folder.pk}/files/",
            {"file": good_file, "name": "report.pdf"},
            format="multipart",
        )
        self.assertEqual(res_good.status_code, status.HTTP_201_CREATED)

    def test_folder_permission_checks_on_destroy_and_move(self):
        """3. Kiểm tra phân quyền xóa và di chuyển thư mục."""
        f_admin = Folder.objects.create(name="Admin Folder", created_by=self.admin_user)
        f_staff = Folder.objects.create(name="Staff Folder", created_by=self.staff_user)

        client = APIClient()
        # Cán bộ khác không thể xóa thư mục của admin hoặc của staff_user
        client.force_authenticate(user=self.other_staff)
        res_del = client.delete(f"/api/folders/{f_admin.pk}/")
        self.assertEqual(res_del.status_code, status.HTTP_403_FORBIDDEN)

        # Cán bộ khác không thể di chuyển thư mục của staff_user
        res_move = client.post(f"/api/folders/{f_staff.pk}/move/", {"target_parent_id": f_admin.pk})
        self.assertEqual(res_move.status_code, status.HTTP_403_FORBIDDEN)

        # Người tạo (staff_user) có quyền xóa thư mục do chính mình tạo
        client.force_authenticate(user=self.staff_user)
        res_del_own = client.delete(f"/api/folders/{f_staff.pk}/")
        self.assertEqual(res_del_own.status_code, status.HTTP_204_NO_CONTENT)

    def test_expiration_date_cannot_be_earlier_than_issue_date(self):
        """4. Kiểm tra logic nghiệp vụ: Ngày hết hiệu lực không được trước ngày ban hành."""
        client = APIClient()
        client.force_authenticate(user=self.admin_user)

        payload = {
            "loai": "DI",
            "so_hieu": "99/QD-TEST",
            "trich_yeu": "Quyết định thử nghiệm",
            "ngay_ban_hanh": "2026-05-10",
            "ngay_het_hieu_luc": "2026-05-01",  # Trước ngày ban hành 9 ngày -> Không hợp lệ
            "hieu_luc": "CON_HIEU_LUC",
        }

        res = client.post("/api/documents/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("ngay_het_hieu_luc", res.data)

    def test_save_and_retrieve_danhmuc_hoso_and_noi_ban_hanh(self):
        """5. Kiểm tra lưu và lấy danh_muc_ho_so, ten_loai_van_ban và noi_ban_hanh qua junction tables."""
        client = APIClient()
        client.force_authenticate(user=self.admin_user)

        # Tạo văn bản đến kèm hồ sơ và danh mục
        payload_den = {
            "loai": "DEN",
            "so_hieu": "100/CV-DEN",
            "trich_yeu": "Văn bản đến có hồ sơ",
            "danh_muc_ho_so": self.ho_so.id,
            "ten_loai_van_ban": self.record_loai_vb.id,
        }
        res_den = client.post("/api/documents/", payload_den, format="json")
        self.assertEqual(res_den.status_code, status.HTTP_201_CREATED)
        doc_den_id = res_den.data["id"]

        # Kiểm tra bảng trung gian
        self.assertTrue(VanBanDenHoSo.objects.filter(vanbanden_id=doc_den_id, hoso_id=self.ho_so.id).exists())
        self.assertTrue(VanBanDenDanhmuc.objects.filter(vanbanden_id=doc_den_id, loaivanban_id=self.record_loai_vb.id).exists())

        # Truy xuất chi tiết văn bản
        res_detail = client.get(f"/api/documents/{doc_den_id}/")
        self.assertEqual(res_detail.status_code, status.HTTP_200_OK)
        self.assertEqual(res_detail.data.get("danh_muc_ho_so"), self.ho_so.ten_ho_so)
        self.assertEqual(res_detail.data.get("ten_loai_van_ban"), self.record_loai_vb.ten_loai)

        # Tạo văn bản đi có nơi ban hành (ID đơn vị)
        payload_di = {
            "loai": "DI",
            "so_hieu": "101/CV-DI",
            "ngay_ban_hanh": "2026-10-24T08:00:00Z",
            "trich_yeu": "Văn bản đi có nơi ban hành",
            "noi_ban_hanh": self.don_vi.id,
        }
        res_di = client.post("/api/documents/", payload_di, format="json")
        self.assertEqual(res_di.status_code, status.HTTP_201_CREATED)
        doc_di_id = res_di.data["id"]

        self.assertTrue(VanBanDiNoiBanHanh.objects.filter(vanbandi_id=doc_di_id, donvi_id=self.don_vi.id).exists())

        res_di_detail = client.get(f"/api/documents/{doc_di_id}/")
        self.assertEqual(res_di_detail.status_code, status.HTTP_200_OK)
        self.assertEqual(res_di_detail.data.get("noi_ban_hanh"), self.don_vi.ten)

    def test_dedicated_viewsets_permission_enforcement(self):
        """6. Kiểm tra can_edit_document và can_create_document trên các ViewSet chuyên biệt."""
        doc = VanBanDen.objects.create(
            so_hieu="102/VB-DEN",
            trich_yeu="Văn bản gốc",
            nguoi_tao=self.admin_user,
        )

        client = APIClient()
        # Cán bộ thường không phải người tạo và không có quyền sửa -> Bị 403
        client.force_authenticate(user=self.staff_user)
        res_patch = client.patch(
            f"/api/documents/den/{doc.pk}/",
            {"trich_yeu": "Sửa trái phép"},
            format="json",
        )
        self.assertEqual(res_patch.status_code, status.HTTP_403_FORBIDDEN)

        # Cán bộ thường thử tạo văn bản mật qua /api/documents/mat/ -> Bị 403
        res_mat = client.post(
            "/api/documents/mat/",
            {"so_hieu": "01/MAT", "trich_yeu": "Văn bản mật"},
            format="json",
        )
        self.assertEqual(res_mat.status_code, status.HTTP_403_FORBIDDEN)

    def test_cleanup_replacement_links_on_delete_edge_cases(self):
        """7. Kiểm tra khôi phục trạng thái khi xóa văn bản thay thế."""
        # Trường hợp 1: Còn văn bản thay thế khác -> Giữ nguyên thay thế
        doc_target = VanBanDen.objects.create(
            so_hieu="200/VB-TARGET",
            trich_yeu="Văn bản bị thay thế bởi 2 văn bản khác",
            hieu_luc=HieuLuc.HET_VA_THAY_THE,
            link_thay_the="201/VB-NEW, 202/VB-NEW",
        )
        doc_replacer_1 = VanBanDen.objects.create(
            so_hieu="201/VB-NEW",
            trich_yeu="Văn bản thay thế 1",
            hieu_luc=HieuLuc.CON_HIEU_LUC,
            link_thay_the="200/VB-TARGET",
        )
        # Xóa replacer 1
        cleanup_replacement_links_on_delete(doc_replacer_1)
        doc_target.refresh_from_db()
        # link_thay_the phải còn 202/VB-NEW và hiệu lực vẫn là HET_VA_THAY_THE
        self.assertIn("202/VB-NEW", doc_target.link_thay_the)
        self.assertNotIn("201/VB-NEW", doc_target.link_thay_the)
        self.assertEqual(doc_target.hieu_luc, HieuLuc.HET_VA_THAY_THE)

        # Trường hợp 2: Đã quá hạn ngày hết hiệu lực -> Trở thành HET_HIEU_LUC chứ không thành CON_HIEU_LUC
        past_date = (timezone.now() - datetime.timedelta(days=10)).date()
        doc_expired = VanBanDen.objects.create(
            so_hieu="300/VB-EXPIRED",
            trich_yeu="Văn bản đã qua ngày hết hiệu lực",
            ngay_het_hieu_luc=past_date,
            hieu_luc=HieuLuc.HET_VA_THAY_THE,
            link_thay_the="301/VB-REP",
        )
        doc_replacer_sole = VanBanDen.objects.create(
            so_hieu="301/VB-REP",
            trich_yeu="Văn bản thay thế duy nhất",
            hieu_luc=HieuLuc.CON_HIEU_LUC,
            link_thay_the="300/VB-EXPIRED",
        )
        cleanup_replacement_links_on_delete(doc_replacer_sole)
        doc_expired.refresh_from_db()
        # Đã xóa link thay thế, nhưng do past_date nên trở thành HET_HIEU_LUC
        self.assertEqual(doc_expired.link_thay_the, "")
        self.assertEqual(doc_expired.hieu_luc, HieuLuc.HET_HIEU_LUC)

    def test_delete_document_with_hoso_and_danhmuc_success(self):
        """Kiểm thử xóa văn bản có gắn Hồ sơ và Loại văn bản thành công, không bị lỗi trigger CSDL."""
        from records.models import HoSo, LoaiVanBan
        from documents.models import VanBanDenHoSo, VanBanDenDanhmuc

        hs = HoSo.objects.create(so_ky_hieu="HS-TEST-DEL", ten_ho_so="Hồ sơ test xóa", nguoi_lap=self.admin_user)
        lvb = LoaiVanBan.objects.create(ho_so=hs, ten_loai="Loại VB test xóa")

        doc = VanBanDen.objects.create(
            so_hieu="TEST-DEL-CROSS",
            trich_yeu="Kiểm tra xóa văn bản có liên kết hồ sơ",
            nam=2026,
            so_thu_tu=8888,
            pham_vi="NOI_BO",
            nguoi_tao=self.admin_user,
        )
        VanBanDenHoSo.objects.create(vanbanden=doc, hoso_id=hs.id)
        VanBanDenDanhmuc.objects.create(vanbanden=doc, loaivanban_id=lvb.id)

        # Gọi API xóa bằng quyền Admin
        client = APIClient()
        client.force_authenticate(user=self.admin_user)
        res = client.delete(f"/api/documents/{doc.id}/")
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(VanBanDen.objects.filter(pk=doc.id).exists())
        self.assertFalse(VanBanDenHoSo.objects.filter(vanbanden_id=doc.id).exists())
        self.assertFalse(VanBanDenDanhmuc.objects.filter(vanbanden_id=doc.id).exists())

