"""
Unit tests toàn diện cho phân hệ Cơ cấu Tổ chức & Đơn vị (Module 7.3 - Nhóm 7).
Tác giả: Lê Duy Khánh.
"""
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
import openpyxl
from io import BytesIO

from .models import KhoiKhuVuc, DonVi


class OrganizationsTests(TestCase):
    """
    Test suite kiểm thử chức năng CRUD, Business Rules, Validation và Excel Export.
    """

    def setUp(self):
        self.client = APIClient()

        # Tạo user kiểm thử
        self.user = User.objects.create_user(
            username="khanh_test",
            password="TestPassword@123",
            first_name="Khánh",
            last_name="Lê Duy",
        )
        self.client.force_authenticate(user=self.user)

        # Tạo dữ liệu mẫu Khối / Khu vực
        self.khoi_1 = KhoiKhuVuc.objects.create(
            ten="KHU VỰC MIỀN NAM",
            thu_tu_hien_thi=1,
        )
        self.khoi_2 = KhoiKhuVuc.objects.create(
            ten="KHU VỰC MIỀN BẮC",
            thu_tu_hien_thi=2,
        )

        # Tạo dữ liệu mẫu Đơn vị / Phòng ban
        self.don_vi_1 = DonVi.objects.create(
            khoi=self.khoi_1,
            stt_uu_tien=1,
            ten="Bảo Long Sài Gòn",
            dia_chi="123 Nguyễn Thị Minh Khai, Q.1, TP.HCM",
            dien_thoai="0901234567",
            email="saigon@baolong.vn",
            is_public=True,
        )
        self.don_vi_2 = DonVi.objects.create(
            khoi=self.khoi_1,
            stt_uu_tien=2,
            ten="Bảo Long Chợ Lớn",
            dia_chi="456 Hồng Bàng, Q.5, TP.HCM",
            dien_thoai="0909876543",
            email="cholon@baolong.vn",
            is_public=False,
        )

    # ── 1. Kiểm thử Khối / Khu vực ───────────────────────────────────────

    def test_list_regions(self):
        """Kiểm tra lấy danh sách Khối / Khu vực có phân trang chuẩn."""
        response = self.client.get("/api/organizations/regions/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        self.assertIn("count", response.data)
        self.assertEqual(response.data["count"], 2)
        results = response.data["results"]
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["ten"], "KHU VỰC MIỀN NAM")
        self.assertEqual(results[0]["don_vi_count"], 2)

    def test_create_region_success(self):
        """Tạo mới Khối / Khu vực thành công."""
        payload = {"ten": "KHỐI VĂN PHÒNG TỔNG CÔNG TY", "thu_tu_hien_thi": 3}
        response = self.client.post("/api/organizations/regions/", payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["ten"], "KHỐI VĂN PHÒNG TỔNG CÔNG TY")
        self.assertTrue(KhoiKhuVuc.objects.filter(ten="KHỐI VĂN PHÒNG TỔNG CÔNG TY").exists())

    def test_validate_region_empty_name(self):
        """Từ chối tạo Khối / Khu vực có tên để trống hoặc chỉ chứa khoảng trắng."""
        payload = {"ten": "   ", "thu_tu_hien_thi": 4}
        response = self.client.post("/api/organizations/regions/", payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("ten", response.data)

    def test_prevent_delete_region_with_child_units(self):
        """Ràng buộc toàn vẹn: Không cho phép xóa Khối đang có Đơn vị trực thuộc."""
        response = self.client.delete(f"/api/organizations/regions/{self.khoi_1.id}/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data.get("code"), "HAS_CHILD_UNITS")
        # Bản ghi vẫn phải tồn tại
        self.assertTrue(KhoiKhuVuc.objects.filter(id=self.khoi_1.id).exists())

    def test_delete_empty_region_success(self):
        """Cho phép xóa Khối khi không còn Đơn vị trực thuộc."""
        response = self.client.delete(f"/api/organizations/regions/{self.khoi_2.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(KhoiKhuVuc.objects.filter(id=self.khoi_2.id).exists())

    # ── 2. Kiểm thử Đơn vị / Phòng ban ────────────────────────────────────

    def test_list_units_pagination(self):
        """Kiểm tra danh sách đơn vị có phân trang."""
        response = self.client.get("/api/organizations/units/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        self.assertIn("count", response.data)
        self.assertEqual(response.data["count"], 2)

    def test_create_unit_auto_stt(self):
        """Tự động tăng STT ưu tiên (Max + 1) nếu không truyền vào."""
        payload = {
            "khoi_id": self.khoi_2.id,
            "ten": "Bảo Long Thăng Long",
            "dia_chi": "789 Hoàng Hoa Thám, Hà Nội",
            "dien_thoai": "0912345678",
            "email": "thanglong@baolong.vn",
            "is_public": True,
        }
        response = self.client.post("/api/organizations/units/", payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # STT hiện có là 1, 2 -> tự động gán là 3
        self.assertEqual(response.data["stt_uu_tien"], 3)
        self.assertEqual(response.data["khoi_ten"], "KHU VỰC MIỀN BẮC")

    def test_create_unit_duplicate_stt(self):
        """Chống trùng STT ưu tiên hiển thị."""
        payload = {
            "khoi_id": self.khoi_2.id,
            "stt_uu_tien": 1,  # Đã tồn tại ở don_vi_1
            "ten": "Bảo Long Hà Nội",
        }
        response = self.client.post("/api/organizations/units/", payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("stt_uu_tien", response.data)

    def test_concurrent_create_unit_auto_stt(self):
        """Kiểm tra việc tính STT tự động an toàn khi nhiều request thêm mới liên tiếp."""
        payload1 = {"khoi_id": self.khoi_1.id, "ten": "Đơn vị Tự động 1"}
        payload2 = {"khoi_id": self.khoi_1.id, "ten": "Đơn vị Tự động 2"}
        res1 = self.client.post("/api/organizations/units/", payload1)
        res2 = self.client.post("/api/organizations/units/", payload2)
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res2.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res1.data["stt_uu_tien"], 3)
        self.assertEqual(res2.data["stt_uu_tien"], 4)

    def test_update_unit_success(self):
        """Cập nhật thông tin đơn vị thành công."""
        payload = {
            "khoi_id": self.khoi_1.id,
            "stt_uu_tien": 1,  # Giữ nguyên STT của chính nó
            "ten": "Bảo Long TP.HCM (Tên Mới)",
            "dia_chi": "Địa chỉ cập nhật",
            "dien_thoai": "0987654321",
            "email": "hcm_updated@baolong.vn",
            "is_public": True,
        }
        response = self.client.put(f"/api/organizations/units/{self.don_vi_1.id}/", payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.don_vi_1.refresh_from_db()
        self.assertEqual(self.don_vi_1.ten, "Bảo Long TP.HCM (Tên Mới)")

    def test_filter_units_by_region(self):
        """Lọc danh sách đơn vị theo Khối / Khu vực."""
        response = self.client.get(f"/api/organizations/units/?region_id={self.khoi_1.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)

        # Lọc theo Khối 2 (chưa có đơn vị)
        response_empty = self.client.get(f"/api/organizations/units/?region_id={self.khoi_2.id}")
        self.assertEqual(response_empty.status_code, status.HTTP_200_OK)
        self.assertEqual(response_empty.data["count"], 0)

    def test_filter_units_by_is_public(self):
        """Lọc theo trạng thái is_public."""
        res_public = self.client.get("/api/organizations/units/?is_public=true")
        self.assertEqual(res_public.data["count"], 1)
        self.assertEqual(res_public.data["results"][0]["ten"], "Bảo Long Sài Gòn")

        res_private = self.client.get("/api/organizations/units/?is_public=false")
        self.assertEqual(res_private.data["count"], 1)
        self.assertEqual(res_private.data["results"][0]["ten"], "Bảo Long Chợ Lớn")

    def test_delete_unit(self):
        """Xóa đơn vị thành công."""
        response = self.client.delete(f"/api/organizations/units/{self.don_vi_2.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(DonVi.objects.filter(id=self.don_vi_2.id).exists())

    # ── 3. Kiểm thử Xuất file Excel ───────────────────────────────────────

    def test_export_units_excel(self):
        """Kiểm thử API xuất file Excel danh sách đơn vị."""
        response = self.client.get("/api/organizations/units/export/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        self.assertIn("Danh_sach_don_vi_phong_ban.xlsx", response["Content-Disposition"])

        # Kiểm tra tính toàn vẹn của file Excel xuất ra
        wb = openpyxl.load_workbook(BytesIO(response.content))
        ws = wb.active
        self.assertEqual(ws.title, "Danh Sách Đơn Vị")
        # Tiêu đề bảng ở ô A1
        self.assertIn("DANH SÁCH ĐƠN VỊ", ws["A1"].value)
        # Header ở dòng 3
        self.assertEqual(ws["A3"].value, "STT Ưu Tiên")
        self.assertEqual(ws["B3"].value, "Tên Đơn Vị / Phòng Ban")
        # Có dữ liệu ở dòng 4 và 5
        self.assertEqual(ws["A4"].value, 1)
        self.assertEqual(ws["B4"].value, "Bảo Long Sài Gòn")

    # ── 4. Kiểm thử Bảo mật & Xác thực ───────────────────────────────────

    def test_unauthenticated_access_denied(self):
        """Từ chối truy cập 401 khi chưa đăng nhập."""
        unauthed_client = APIClient()
        response = unauthed_client.get("/api/organizations/units/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
