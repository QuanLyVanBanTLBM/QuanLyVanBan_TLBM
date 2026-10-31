"""
Bộ kiểm thử toàn diện cho phân hệ Quản lý Cán bộ Nhân viên (CBNV - Issue #24).
Tác giả: Lê Duy Khánh (leduykhanhdevs).
Bao gồm:
1. CRUD nhân viên (tạo, đọc, sửa, xóa, tìm kiếm, lọc, sắp xếp theo STT Đơn vị -> Chức vụ).
2. Kiểm tra tính bảo mật & quyền riêng tư (che năm sinh DD/MM/---- và ẩn nhóm quyền nếu thiếu quyền view_full_cbnv).
3. Kiểm tra logic nghiệp vụ: trạng thái 'NGHI_VIEC' tự động vô hiệu hóa user.is_active = False.
4. Kiểm tra danh mục Chức vụ (Position) và Nhóm quyền (Group).
5. Kiểm tra Tải tệp mẫu Excel và Nhập Excel validate từng dòng dữ liệu.
"""
import base64
from io import BytesIO
import os
from pathlib import Path
from datetime import date, timedelta
from unittest.mock import patch
import openpyxl
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.db import connection
from django.db.models import ProtectedError, RestrictedError, Max
from django.test import TestCase, TransactionTestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from organizations.models import KhoiKhuVuc, DonVi
from accounts.models import Employee, EmployeeImportJob, Position, EmployeeAssignment
from accounts.excel_cbnv import import_cbnv_from_excel
from accounts.views_employee import _run_employee_import_job

User = get_user_model()


class EmployeeBaseTestCase(APITestCase):
    """Lớp nền tảng tạo sẵn dữ liệu mẫu cho các ca kiểm thử."""

    def setUp(self):
        # 1. Tạo Khối & Đơn vị
        self.khoi, _ = KhoiKhuVuc.objects.get_or_create(
            ten="Khối Cơ quan Điều hành",
            defaults={"thu_tu_hien_thi": 999},
        )
        max_stt = DonVi.objects.aggregate(Max("stt_uu_tien"))["stt_uu_tien__max"] or 0
        self.don_vi_1 = DonVi.objects.create(
            ten="Văn phòng Viện",
            khoi=self.khoi,
            stt_uu_tien=max_stt + 1,
            is_public=True,
        )
        self.don_vi_2 = DonVi.objects.create(
            ten="Phòng Kế toán - Tài chính",
            khoi=self.khoi,
            stt_uu_tien=max_stt + 2,
            is_public=True,
        )

        # 2. Tạo Chức vụ
        max_order = Position.objects.aggregate(Max("display_order"))["display_order__max"] or 0
        self.cv_truong_phong, _ = Position.objects.get_or_create(
            name="Trưởng phòng",
            defaults={"display_order": max_order + 1, "is_public": True},
        )
        max_order = Position.objects.aggregate(Max("display_order"))["display_order__max"] or 0
        self.cv_chuyen_vien, _ = Position.objects.get_or_create(
            name="Chuyên viên",
            defaults={"display_order": max_order + 1, "is_public": True},
        )

        # 3. Tạo Nhóm quyền
        # "Văn thư" là nhóm chuẩn đã được authorization seed sẵn (SQL_Fix4)
        self.group_van_thu, _ = Group.objects.get_or_create(name="Văn thư")
        self.group_lanh_dao, _ = Group.objects.get_or_create(name="Lãnh đạo đơn vị")

        # 4. Tạo Users (Employee là Custom User Model)
        # Superuser
        self.admin_user = User.objects.create_superuser(
            username="admin_user",
            email="admin@donvi.gov.vn",
            password="SuperPassword123",
            ho_ten="Quản trị viên",
            don_vi=self.don_vi_1,
            chuc_vu=self.cv_truong_phong,
        )

        # User thường (không có quyền view_full_cbnv)
        self.normal_user = User.objects.create_user(
            username="normal_user",
            email="normal@donvi.gov.vn",
            password="NormalPassword123",
            ho_ten="Nguyễn Văn Bình kiểm thử",
            ngay_sinh=date(1995, 5, 20),
            don_vi=self.don_vi_1,
            chuc_vu=self.cv_chuyen_vien,
            sdt="0912345678",
        )

        # User có quyền xem thông tin nhạy cảm
        self.sensitive_user = User.objects.create_user(
            username="sensitive_user",
            email="sensitive@donvi.gov.vn",
            password="SensitivePassword123",
            ho_ten="Trần Văn Hùng",
            ngay_sinh=date(1988, 10, 15),
            don_vi=self.don_vi_2,
            chuc_vu=self.cv_truong_phong,
            sdt="0987654321",
        )
        self.perm_view_list = Permission.objects.get(codename="view_list_cbnv")
        self.perm_sensitive = Permission.objects.get(codename="view_full_cbnv")
        self.perm_import = Permission.objects.get(codename="import_cbnv")
        self.perm_export = Permission.objects.get(codename="export_cbnv")
        self.perm_add = Permission.objects.get(codename="add_cbnv")
        self.perm_change_full = Permission.objects.get(codename="change_full_cbnv")
        self.perm_change_self = Permission.objects.get(codename="change_self_cbnv")
        self.perm_delete = Permission.objects.get(codename="delete_cbnv")

        self.normal_user.user_permissions.add(self.perm_view_list)
        self.sensitive_user.user_permissions.add(
            self.perm_view_list, self.perm_sensitive, self.perm_import, self.perm_export
        )

        # User không có quyền nào (để test 403)
        self.no_perm_user = User.objects.create_user(
            username="no_perm_user",
            email="noperm@donvi.gov.vn",
            password="NoPermPassword123",
            ho_ten="Người dùng không quyền",
            don_vi=self.don_vi_1,
            chuc_vu=self.cv_chuyen_vien,
        )

        # User chỉ có quyền thay đổi thông tin bản thân (change_self_cbnv)
        self.self_user = User.objects.create_user(
            username="self_user",
            email="self@donvi.gov.vn",
            password="SelfPassword123",
            ho_ten="Người dùng sửa bản thân",
            don_vi=self.don_vi_1,
            chuc_vu=self.cv_chuyen_vien,
            sdt="0911223344",
        )
        self.self_user.user_permissions.add(self.perm_view_list, self.perm_change_self)

        # URLs
        self.employee_list_url = "/api/accounts/employees/"
        self.group_list_url = "/api/accounts/groups/"
        self.template_url = "/api/accounts/employees/template/"
        self.import_url = "/api/accounts/employees/import/"
        self.export_url = "/api/accounts/employees/export/"


class EmployeeCRUDAndFilterTests(EmployeeBaseTestCase):
    """Kiểm tra tạo, đọc, cập nhật, xóa, tìm kiếm và phân trang CBNV."""

    def test_create_employee_success(self):
        """Tạo mới CBNV thành công, tự động tạo User, sinh mật khẩu tạm thời và hash mật khẩu."""
        self.client.force_authenticate(user=self.admin_user)
        payload = {
            "ho_ten": "Lê Thị Mai",
            "email": "mailt@donvi.gov.vn",
            "ngay_sinh": "1992-08-25",
            "don_vi_id": self.don_vi_1.id,
            "chuc_vu_id": self.cv_chuyen_vien.id,
            "chuc_danh": "Chuyên viên tổng hợp",
            "sdt": "0901234567",
            "nhom_quyen_ids": [self.group_van_thu.id],
            "trang_thai": "LAM_VIEC",
            "is_public": True,
            "ghi_chu": "Nhân viên mới tuyển dụng",
        }
        response = self.client.post(self.employee_list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertEqual(data["ho_ten"], "Lê Thị Mai")
        self.assertEqual(data["email"], "mailt@donvi.gov.vn")
        self.assertEqual(data["don_vi_ten"], "Văn phòng Viện")
        self.assertEqual(data["chuc_vu_ten"], "Chuyên viên")
        self.assertIsNotNone(data["temporary_password"])

        # Kiểm tra bản ghi User được tạo trong DB
        user = User.objects.get(email="mailt@donvi.gov.vn")
        self.assertTrue(user.is_active)
        self.assertTrue(user.check_password(data["temporary_password"]))
        # Kiểm tra nhóm quyền được liên kết
        self.assertTrue(user.groups.filter(id=self.group_van_thu.id).exists())

    def test_create_employee_validation_duplicate_email(self):
        """Tạo CBNV với email trùng lặp phải trả về lỗi 400."""
        self.client.force_authenticate(user=self.admin_user)
        payload = {
            "ho_ten": "Nguyễn Văn Trùng",
            "email": "normal@donvi.gov.vn",  # Trùng với self.normal_user
            "ngay_sinh": "1990-01-01",
        }
        response = self.client.post(self.employee_list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.json())

    def test_create_employee_validation_invalid_phone(self):
        """Tạo CBNV với số điện thoại sai định dạng VN phải trả về lỗi 400."""
        self.client.force_authenticate(user=self.admin_user)
        payload = {
            "ho_ten": "Trần Thị Sai SĐT",
            "email": "saisdt@donvi.gov.vn",
            "ngay_sinh": "1990-01-01",
            "sdt": "123456",  # Không phải số điện thoại VN hợp lệ
        }
        response = self.client.post(self.employee_list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("sdt", response.json())

    def test_list_employees_pagination_and_all(self):
        """Kiểm tra danh sách CBNV hỗ trợ phân trang và query all=true."""
        self.client.force_authenticate(user=self.admin_user)
        # Phân trang mặc định
        res = self.client.get(self.employee_list_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()
        self.assertIn("count", data)
        self.assertIn("results", data)

        # Lấy toàn bộ không phân trang với all=true
        res_all = self.client.get(f"{self.employee_list_url}?all=true")
        self.assertEqual(res_all.status_code, status.HTTP_200_OK)
        self.assertIsInstance(res_all.json(), list)

    def test_search_employees(self):
        """Tìm kiếm CBNV theo tên, email, sđt."""
        self.client.force_authenticate(user=self.admin_user)
        # Tìm theo tên
        res = self.client.get(f"{self.employee_list_url}?search=Bình kiểm thử")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        results = res.json()["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["ho_ten"], "Nguyễn Văn Bình kiểm thử")

        # Tìm theo SĐT
        res_phone = self.client.get(f"{self.employee_list_url}?search=0987654321")
        self.assertEqual(res_phone.status_code, status.HTTP_200_OK)
        results_phone = res_phone.json()["results"]
        self.assertEqual(len(results_phone), 1)
        self.assertEqual(results_phone[0]["ho_ten"], "Trần Văn Hùng")

    def test_filter_employees_by_unit_and_position(self):
        """Lọc CBNV theo đơn vị và chức vụ."""
        self.client.force_authenticate(user=self.admin_user)
        res_unit = self.client.get(f"{self.employee_list_url}?don_vi_id={self.don_vi_2.id}")
        self.assertEqual(res_unit.status_code, status.HTTP_200_OK)
        results = res_unit.json()["results"]
        self.assertTrue(all(item["don_vi_id"] == self.don_vi_2.id for item in results))

    def test_filter_unit_includes_concurrent_assignments_without_duplicates(self):
        """Lọc theo đơn vị phải gồm CBNV kiêm nhiệm đơn vị đó."""
        EmployeeAssignment.objects.create(
            employee=self.normal_user,
            don_vi=self.don_vi_2,
            chuc_vu=self.cv_truong_phong,
            chuc_danh="Phụ trách kiêm nhiệm",
        )
        self.client.force_authenticate(user=self.admin_user)

        response = self.client.get(f"{self.employee_list_url}?don_vi_id={self.don_vi_2.id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.json()["results"]
        employee_ids = [item["id"] for item in results]
        self.assertIn(self.normal_user.id, employee_ids)
        self.assertEqual(len(employee_ids), len(set(employee_ids)))

    def test_update_employee(self):
        """Cập nhật thông tin CBNV."""
        self.client.force_authenticate(user=self.admin_user)
        detail_url = f"{self.employee_list_url}{self.normal_user.id}/"
        payload = {
            "ho_ten": "Nguyễn Văn Bình (Cập nhật)",
            "chuc_danh": "Phó phòng phụ trách",
            "sdt": "0933333333",
        }
        res = self.client.patch(detail_url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()
        self.assertEqual(data["ho_ten"], "Nguyễn Văn Bình (Cập nhật)")
        self.assertEqual(data["chuc_danh"], "Phó phòng phụ trách")
        self.assertEqual(data["sdt"], "0933333333")

    def test_delete_employee(self):
        """Xóa CBNV (kèm mật khẩu quản trị viên xác nhận trong body JSON)."""
        self.client.force_authenticate(user=self.admin_user)
        target_user_id = self.normal_user.id
        detail_url = f"{self.employee_list_url}{target_user_id}/"

        res = self.client.delete(detail_url, {"password": "SuperPassword123"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(User.objects.filter(id=target_user_id).exists())

    def test_delete_employee_without_password_fails(self):
        """Xóa CBNV nhưng không gửi mật khẩu xác nhận trong body JSON phải trả về 400 Bad Request."""
        self.client.force_authenticate(user=self.admin_user)
        detail_url = f"{self.employee_list_url}{self.normal_user.id}/"
        res = self.client.delete(detail_url, {}, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data.get("detail"), "employees.messages.invalidPassword")
        self.assertTrue(User.objects.filter(id=self.normal_user.id).exists())

    def test_delete_employee_with_wrong_password_fails(self):
        """Xóa CBNV nhưng nhập sai mật khẩu xác nhận phải trả về 400 Bad Request."""
        self.client.force_authenticate(user=self.admin_user)
        target = User.objects.create_user(
            username="to_delete_wrong_pwd",
            email="to_delete_wrong_pwd@donvi.gov.vn",
            password="Password123",
            ho_ten="Sắp Xóa",
            ngay_sinh=date(1995, 5, 5),
            don_vi=self.don_vi_1,
            chuc_vu=self.cv_chuyen_vien,
        )
        detail_url = f"{self.employee_list_url}{target.id}/"
        res = self.client.delete(detail_url, {"password": "WrongPassword"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data.get("detail"), "employees.messages.invalidPassword")
        self.assertTrue(User.objects.filter(id=target.id).exists())

    def test_delete_employee_with_correct_password_succeeds(self):
        """Xóa CBNV khi nhập đúng mật khẩu xác nhận của admin thành công 204."""
        self.client.force_authenticate(user=self.admin_user)
        target = User.objects.create_user(
            username="to_delete_ok_pwd",
            email="to_delete_ok_pwd@donvi.gov.vn",
            password="Password123",
            ho_ten="Sắp Xóa Thành Công",
            ngay_sinh=date(1995, 5, 5),
            don_vi=self.don_vi_1,
            chuc_vu=self.cv_chuyen_vien,
        )
        detail_url = f"{self.employee_list_url}{target.id}/"
        res = self.client.delete(detail_url, {"password": "SuperPassword123"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(User.objects.filter(id=target.id).exists())


    def test_create_employee_requires_unit_and_position(self):
        """SQL_Fix4: don_vi_id và chuc_vu_id NOT NULL -> thiếu là 400."""
        self.client.force_authenticate(user=self.admin_user)
        payload = {"ho_ten": "Thiếu Đơn Vị", "email": "thieu@donvi.gov.vn", "ngay_sinh": "1990-01-01"}
        response = self.client.post(self.employee_list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        body = response.json()
        self.assertIn("don_vi_id", body)
        self.assertIn("chuc_vu_id", body)
        self.assertFalse(User.objects.filter(email="thieu@donvi.gov.vn").exists())

    def test_status_is_stored_with_ddl_enum_values(self):
        """API nhận và trả đúng giá trị ENUM employee_work_status của DDL."""
        self.client.force_authenticate(user=self.admin_user)
        res = self.client.patch(f"{self.employee_list_url}{self.normal_user.id}/", {"trang_thai": "NGHI_VIEC"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.json()["trang_thai"], "NGHI_VIEC")
        self.normal_user.refresh_from_db()
        self.assertEqual(self.normal_user.trang_thai, "NGHI_VIEC")

    def test_filter_by_status_uses_ddl_value(self):
        self.client.force_authenticate(user=self.admin_user)
        self.normal_user.trang_thai = Employee.Status.NGHI_VIEC
        self.normal_user.save()
        res = self.client.get(f"{self.employee_list_url}?trang_thai=NGHI_VIEC&all=true")
        expected = set(
            User.objects.filter(trang_thai=Employee.Status.NGHI_VIEC)
            .values_list("username", flat=True)
        )
        self.assertEqual({item["username"] for item in res.json()}, expected)


class EmployeeSecurityAndPrivacyTests(EmployeeBaseTestCase):
    """Kiểm tra các quy tắc bảo mật & quyền riêng tư trường dữ liệu nhạy cảm."""

    def test_birthday_masked_for_user_without_sensitive_perm(self):
        """User thường không có quyền view_full_cbnv: ngày sinh bị che thành DD/MM/---- và nhóm quyền rỗng."""
        self.client.force_authenticate(user=self.normal_user)
        detail_url = f"{self.employee_list_url}{self.sensitive_user.id}/"
        res = self.client.get(detail_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()

        # Ngày sinh gốc là 1988-10-15 -> phải được format thành 15/10/19xx
        self.assertEqual(data["ngay_sinh"], "15/10/----")
        self.assertIsNone(data.get("ngay_sinh_iso"))
        self.assertTrue(data["is_birthday_masked"])
        self.assertFalse(data["has_sensitive_permission"])
        self.assertEqual(data["nhom_quyen"], [])

    def test_birthday_full_for_user_with_sensitive_perm(self):
        """User có quyền view_full_cbnv: xem được ngày sinh đầy đủ DD/MM/YYYY và nhóm quyền."""
        self.client.force_authenticate(user=self.sensitive_user)
        # Gán nhóm quyền cho normal_profile
        self.normal_user.groups.add(self.group_van_thu)

        detail_url = f"{self.employee_list_url}{self.normal_user.id}/"
        res = self.client.get(detail_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()

        # Ngày sinh gốc 1995-05-20 -> trả về đúng 20/05/1995 và ngay_sinh_iso là 1995-05-20
        self.assertEqual(data["ngay_sinh"], "20/05/1995")
        self.assertEqual(data.get("ngay_sinh_iso"), "1995-05-20")
        self.assertFalse(data["is_birthday_masked"])
        self.assertTrue(data["has_sensitive_permission"])
        self.assertEqual(len(data["nhom_quyen"]), 1)
        self.assertEqual(data["nhom_quyen"][0]["name"], "Văn thư")

    def test_superuser_has_sensitive_perm_by_default(self):
        """Superuser luôn có toàn quyền xem ngày sinh đầy đủ."""
        self.client.force_authenticate(user=self.admin_user)
        detail_url = f"{self.employee_list_url}{self.normal_user.id}/"
        res = self.client.get(detail_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()
        self.assertEqual(data["ngay_sinh"], "20/05/1995")
        self.assertEqual(data.get("ngay_sinh_iso"), "1995-05-20")
        self.assertFalse(data["is_birthday_masked"])

    def test_owner_sees_unmasked_birthday(self):
        """Chủ tài khoản (dù không có quyền view_full_cbnv) luôn xem được ngày sinh đầy đủ của chính mình."""
        self.client.force_authenticate(user=self.normal_user)
        own_url = f"{self.employee_list_url}{self.normal_user.id}/"
        res = self.client.get(own_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()
        self.assertEqual(data["ngay_sinh"], "20/05/1995")
        self.assertEqual(data.get("ngay_sinh_iso"), "1995-05-20")
        self.assertFalse(data["is_birthday_masked"])

    def test_status_nghi_viec_deactivates_user(self):
        """Khi cập nhật trạng thái 'NGHI_VIEC', user.is_active tự động chuyển thành False."""
        self.client.force_authenticate(user=self.admin_user)
        detail_url = f"{self.employee_list_url}{self.normal_user.id}/"
        res = self.client.patch(detail_url, {"trang_thai": "NGHI_VIEC"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.normal_user.refresh_from_db()
        self.assertFalse(self.normal_user.is_active)

        # Chuyển lại 'LAM_VIEC' -> user.is_active trở lại True
        res_reactivate = self.client.patch(detail_url, {"trang_thai": "LAM_VIEC"}, format="json")
        self.assertEqual(res_reactivate.status_code, status.HTTP_200_OK)
        self.normal_user.refresh_from_db()
        self.assertTrue(self.normal_user.is_active)


class GroupAPITests(EmployeeBaseTestCase):
    """Kiểm tra API Nhóm quyền (Chức vụ có bộ test riêng ở test_positions.py)."""

    def test_list_groups_forbidden_without_permission(self):
        """User thường không có quyền add_cbnv / change_full_cbnv / view_nhomquyen bị chặn 403."""
        self.client.force_authenticate(user=self.normal_user)
        res = self.client.get(self.group_list_url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(res.data["detail"], "roles.messages.permissionDenied")

    def test_list_groups_success_with_permission(self):
        """Superuser hoặc User có quyền thêm CBNV (add_cbnv) được xem danh sách nhóm quyền (200)."""
        self.client.force_authenticate(user=self.admin_user)
        res = self.client.get(self.group_list_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()
        self.assertTrue(len(data) >= 2)


class EmployeeExcelImportExportTests(EmployeeBaseTestCase):
    """Kiểm tra tải tệp mẫu và nhập dữ liệu từ Excel."""

    def test_download_excel_template(self):
        """Tải tệp mẫu Excel trả về mã 200 và header tệp đính kèm .xlsx."""
        self.client.force_authenticate(user=self.admin_user)
        res = self.client.get(self.template_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(
            res["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        self.assertIn("mau_danh_sach_cbnv.xlsx", res["Content-Disposition"])

    def test_import_excel_permission_denied_for_normal_user(self):
        """User thường không có quyền import_cbnv bị từ chối với mã 403."""
        self.client.force_authenticate(user=self.normal_user)
        res = self.client.post(self.import_url, {}, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_import_excel_missing_file(self):
        """Gửi request import không có tệp đính kèm trả về mã 400."""
        self.client.force_authenticate(user=self.sensitive_user)
        res = self.client.post(self.import_url, {}, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_import_excel_with_validation_errors(self):
        """Nhập Excel có lỗi định dạng: báo lỗi chi tiết theo từng dòng."""
        self.client.force_authenticate(user=self.sensitive_user)

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Danh Sach CBNV"
        ws.append(["STT", "Họ và tên (*)", "Ngày sinh (*)", "Email (*)", "Số điện thoại", "Tên Đơn vị / Phòng ban (*)", "Tên Chức vụ (*)", "Chức danh", "Trạng thái", "Ghi chú"])
        ws.append(["(Ghi chú)", "", "", "", "", "", "", "", "", ""])

        # Dòng 3: Thiếu email, sđt sai, ngày sinh sai định dạng
        ws.append([1, "Lê Lỗi Dữ Liệu", "sai_ngay_sinh", "", "12345", "Đơn vị không tồn tại", "Chức vụ ảo", "", "Đang làm việc", ""])

        bio = BytesIO()
        wb.save(bio)
        bio.seek(0)
        bio.name = "danh_sach_loi.xlsx"

        res = self.client.post(self.import_url, {"file": bio}, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        data = res.json()
        self.assertFalse(data["success"])
        self.assertTrue(len(data["errors"]) > 0)
        self.assertEqual(data["errors"][0]["row"], 3)

    def test_import_excel_success(self):
        """Nhập Excel hợp lệ: tạo nhân viên và user thành công trong DB."""
        self.client.force_authenticate(user=self.sensitive_user)

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Danh Sach CBNV"
        ws.append(["STT", "Họ và tên (*)", "Ngày sinh (*)", "Email (*)", "Số điện thoại", "Tên Đơn vị / Phòng ban (*)", "Tên Chức vụ (*)", "Chức danh", "Trạng thái", "Ghi chú"])
        ws.append(["(Ghi chú)", "", "", "", "", "", "", "", "", ""])

        # Dòng 3: Dữ liệu hợp lệ
        ws.append([1, "Đoàn Văn Hậu", "1999-04-19", "doanvanhau@donvi.gov.vn", "0912345679", "Văn phòng Viện", "Chuyên viên", "Chuyên viên đối ngoại", "Đang làm việc", "Ghi chú mẫu"])

        bio = BytesIO()
        wb.save(bio)
        bio.seek(0)
        bio.name = "danh_sach_hop_le.xlsx"

        res = self.client.post(self.import_url, {"file": bio}, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["created_count"], 1)

        # Kiểm tra bản ghi trong DB
        self.assertTrue(User.objects.filter(email="doanvanhau@donvi.gov.vn").exists())
        self.assertTrue(User.objects.filter(ho_ten="Đoàn Văn Hậu", don_vi=self.don_vi_1).exists())

    def test_import_excel_prefetches_lookup_data_for_many_rows(self):
        """Số truy vấn đọc danh mục/email không tăng theo số dòng Excel."""
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append([
            "Họ và tên (*)", "Ngày sinh (*)", "Email (*)", "Số điện thoại",
            "Tên Khối / Khu vực (*)", "Tên Đơn vị / Phòng ban (*)",
            "Tên Chức vụ (*)", "Chức danh", "Trạng thái", "Ghi chú",
        ])
        for index in range(20):
            ws.append([
                f"Nhân viên tối ưu {index}", "1990-01-01", f"fast-import-{index}@example.test",
                "0912345678", self.khoi.ten, self.don_vi_1.ten, self.cv_chuyen_vien.name,
                "", "Đang làm việc", "",
            ])
        bio = BytesIO()
        wb.save(bio)
        bio.seek(0)
        bio.name = "danh_sach_toi_uu.xlsx"

        with CaptureQueriesContext(connection) as captured:
            result = import_cbnv_from_excel(bio)

        self.assertTrue(result["success"], result.get("errors"))
        self.assertEqual(result["created_count"], 20)
        select_queries = [
            query for query in captured.captured_queries
            if query["sql"].lstrip().upper().startswith("SELECT")
        ]
        self.assertLessEqual(len(select_queries), 10)

    def test_import_excel_async_returns_owned_job_and_deduplicates_retry(self):
        """Endpoint nền nhận nhanh, giới hạn xem trạng thái theo chủ job và chống gửi lặp."""
        self.client.force_authenticate(user=self.sensitive_user)
        upload = BytesIO(b"queued test payload")
        upload.name = "danh_sach.xlsx"
        idempotency_key = "9a04c357-e2fa-4b04-89da-6f459f8c367b"
        url = "/api/accounts/employees/import-async/"

        with patch("accounts.views_employee._start_employee_import_worker") as start_worker:
            response = self.client.post(
                url,
                {"file": upload},
                format="multipart",
                HTTP_IDEMPOTENCY_KEY=idempotency_key,
            )
            self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
            job_id = response.json()["job_id"]
            job = EmployeeImportJob.objects.get(pk=job_id)
            self.assertEqual(job.owner_id, self.sensitive_user.pk)
            self.assertEqual(job.status, EmployeeImportJob.Status.QUEUED)
            self.assertEqual(job.active_key, "cbnv-import")
            file_path = Path(settings.MEDIA_ROOT) / job.file_path
            self.addCleanup(file_path.unlink, missing_ok=True)
            start_worker.assert_called_once_with(job.pk)

            retry_upload = BytesIO(b"queued test payload")
            retry_upload.name = "danh_sach.xlsx"
            retry = self.client.post(
                url,
                {"file": retry_upload},
                format="multipart",
                HTTP_IDEMPOTENCY_KEY=idempotency_key,
            )
            self.assertEqual(retry.status_code, status.HTTP_202_ACCEPTED)
            self.assertEqual(retry.json()["job_id"], job_id)
            self.assertEqual(EmployeeImportJob.objects.count(), 1)

        status_url = f"/api/accounts/employees/import-jobs/{job_id}/"
        EmployeeImportJob.objects.filter(pk=job_id).update(
            status=EmployeeImportJob.Status.PROCESSING,
            updated_at=timezone.now() - timedelta(minutes=1),
        )
        status_response = self.client.get(status_url)
        self.assertEqual(status_response.status_code, status.HTTP_200_OK)
        self.assertEqual(status_response.json()["status"], "queued")
        self.assertNotIn("file_path", status_response.json())

        self.client.force_authenticate(user=self.admin_user)
        self.assertEqual(self.client.get(status_url).status_code, status.HTTP_404_NOT_FOUND)

    def test_import_excel_async_rejects_files_over_template_limit(self):
        self.client.force_authenticate(user=self.sensitive_user)
        upload = BytesIO(b"x" * (5 * 1024 * 1024 + 1))
        upload.name = "too-large.xlsx"
        response = self.client.post(
            "/api/accounts/employees/import-async/",
            {"file": upload},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["detail"], "employees.import.fileTooLarge")
        self.assertFalse(EmployeeImportJob.objects.exists())

    def test_import_excel_xls_format_rejected(self):
        """Tệp Excel định dạng cũ (.xls) bị từ chối 400 fileInvalidType (hệ thống chuẩn hóa chỉ hỗ trợ .xlsx)."""
        self.client.force_authenticate(user=self.sensitive_user)
        bio = BytesIO(b"fake .xls binary content")
        bio.name = "danh_sach_hop_le.xls"
        res = self.client.post(self.import_url, {"file": bio}, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.json()["detail"], "employees.messages.fileInvalidType")

    def test_import_excel_invalid_extension_rejected(self):
        """Tải tệp không có phần mở rộng .xlsx hoặc .xls bị từ chối 400."""
        self.client.force_authenticate(user=self.sensitive_user)
        bio = BytesIO(b"fake content")
        bio.name = "tai_lieu.pdf"
        res = self.client.post(self.import_url, {"file": bio}, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.json()["detail"], "employees.messages.fileInvalidType")

    def test_import_excel_does_not_create_position_on_error(self):
        """Review PR #71: Không tự ý tạo Chức vụ mới khi import nếu không tồn tại; phải báo lỗi dòng."""
        self.client.force_authenticate(user=self.sensitive_user)

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Danh Sach CBNV"
        ws.append(["STT", "Họ và tên (*)", "Ngày sinh (*)", "Email (*)", "Số điện thoại", "Tên Đơn vị / Phòng ban (*)", "Tên Chức vụ (*)", "Chức danh", "Trạng thái", "Ghi chú"])
        ws.append(["(Ghi chú)", "", "", "", "", "", "", "", "", ""])
        ws.append([1, "Lê Không Chức Vụ", "1990-01-01", "nochucvu@donvi.gov.vn", "0911223344", "Văn phòng Viện", "Chức Vụ Không Tồn Tại 999", "", "Đang làm việc", ""])

        bio = BytesIO()
        wb.save(bio)
        bio.seek(0)
        bio.name = "chuc_vu_la.xlsx"

        res = self.client.post(self.import_url, {"file": bio}, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        data = res.json()
        self.assertFalse(data["success"])
        self.assertTrue(any("Không tìm thấy Chức vụ" in err["message"] for err in data["errors"]))
        self.assertFalse(Position.objects.filter(name="Chức Vụ Không Tồn Tại 999").exists())

    def test_import_excel_duplicate_unit_name_fails(self):
        """Review PR #71: Đơn vị trùng tên giữa nhiều Khối/Khu vực phải báo lỗi yêu cầu ghi rõ."""
        self.client.force_authenticate(user=self.sensitive_user)

        # Tạo thêm 1 khối và 1 đơn vị cùng tên "Văn phòng Viện"
        khoi2 = KhoiKhuVuc.objects.create(ten="Khối Cơ quan phía Nam")
        max_stt = DonVi.objects.aggregate(Max("stt_uu_tien"))["stt_uu_tien__max"] or 0
        DonVi.objects.create(ten="Văn phòng Viện", khoi=khoi2, stt_uu_tien=max_stt + 1)

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Danh Sach CBNV"
        ws.append(["STT", "Họ và tên (*)", "Ngày sinh (*)", "Email (*)", "Số điện thoại", "Tên Đơn vị / Phòng ban (*)", "Tên Chức vụ (*)", "Chức danh", "Trạng thái", "Ghi chú"])
        ws.append(["(Ghi chú)", "", "", "", "", "", "", "", "", ""])
        ws.append([1, "Nguyễn Trùng Đơn Vị", "1990-01-01", "trungdonvi@donvi.gov.vn", "0911223344", "Văn phòng Viện", "Chuyên viên", "", "Đang làm việc", ""])

        bio = BytesIO()
        wb.save(bio)
        bio.seek(0)
        bio.name = "trung_don_vi.xlsx"

        res = self.client.post(self.import_url, {"file": bio}, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        data = res.json()
        self.assertFalse(data["success"])
        self.assertTrue(any("trùng lặp giữa nhiều Khối/Khu vực" in err["message"] for err in data["errors"]))

    def test_import_excel_duplicate_unit_name_resolves_by_block(self):
        """Đơn vị trùng tên được phân biệt chính xác khi file có cột Khối/Khu vực."""
        self.client.force_authenticate(user=self.sensitive_user)

        khoi2 = KhoiKhuVuc.objects.create(ten="Khối Cơ quan phía Nam")
        max_stt = DonVi.objects.aggregate(Max("stt_uu_tien"))["stt_uu_tien__max"] or 0
        don_vi_khoi2 = DonVi.objects.create(
            ten=self.don_vi_1.ten,
            khoi=khoi2,
            stt_uu_tien=max_stt + 1,
        )

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Danh Sach CBNV"
        ws.append([
            "STT", "Họ và tên (*)", "Ngày sinh (*)", "Email (*)", "Số điện thoại",
            "Tên Khối / Khu vực (*)", "Tên Đơn vị / Phòng ban (*)", "Tên Chức vụ (*)",
            "Chức danh", "Trạng thái", "Ghi chú",
        ])
        ws.append(["(Ghi chú)", "", "", "", "", "", "", "", "", "", ""])
        ws.append([
            1, "Nguyễn Trùng Đơn Vị", "1990-01-01", "trungdonvi.khoi2@donvi.gov.vn",
            "0911223345", khoi2.ten, self.don_vi_1.ten, "Chuyên viên", "",
            "Đang làm việc", "",
        ])

        bio = BytesIO()
        wb.save(bio)
        bio.seek(0)
        bio.name = "trung_don_vi_theo_khoi.xlsx"

        res = self.client.post(self.import_url, {"file": bio}, format="multipart")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.json()["created_count"], 1)
        imported_user = User.objects.get(email="trungdonvi.khoi2@donvi.gov.vn")
        self.assertEqual(imported_user.don_vi, don_vi_khoi2)

    def test_export_excel_forbidden_without_export_cbnv(self):
        """User thiếu quyền export_cbnv hoặc chưa đăng nhập bị từ chối xuất Excel."""
        # Chưa đăng nhập -> 401
        res = self.client.get(self.export_url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

        # Không có quyền nào -> 403
        self.client.force_authenticate(user=self.no_perm_user)
        res = self.client.get(self.export_url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        # Có view_list_cbnv nhưng không có export_cbnv -> 403
        self.client.force_authenticate(user=self.normal_user)
        res = self.client.get(self.export_url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_export_excel_rbac_roles_access(self):
        """
        Kiểm tra phân quyền RBAC:
        - TP (Trưởng phòng), BGD (Ban Giám đốc), ADMIN (Quản trị hệ thống) được phép xuất (200).
        - CV (Chuyên viên), VT (Văn thư) không có quyền export_cbnv -> bị từ chối 403.
        """
        # 1. Nhóm Trưởng phòng (TP)
        tp_group, _ = Group.objects.get_or_create(name="Trưởng phòng")
        tp_user = User.objects.create_user(
            username="tp_test_user",
            email="tp@donvi.gov.vn",
            password="Password123",
            ho_ten="Trưởng Phòng Test",
            don_vi=self.don_vi_1,
            chuc_vu=self.cv_truong_phong,
        )
        tp_user.groups.add(tp_group)
        self.client.force_authenticate(user=tp_user)
        res = self.client.get(self.export_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # 2. Nhóm Ban Giám đốc (BGD)
        bgd_group, _ = Group.objects.get_or_create(name="Ban Giám đốc")
        bgd_user = User.objects.create_user(
            username="bgd_test_user",
            email="bgd@donvi.gov.vn",
            password="Password123",
            ho_ten="Ban Giám Đốc Test",
            don_vi=self.don_vi_1,
            chuc_vu=self.cv_truong_phong,
        )
        bgd_user.groups.add(bgd_group)
        self.client.force_authenticate(user=bgd_user)
        res = self.client.get(self.export_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # 3. Superuser / ADMIN
        self.client.force_authenticate(user=self.admin_user)
        res = self.client.get(self.export_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # 4. Nhóm Chuyên viên (CV) -> 403
        cv_group, _ = Group.objects.get_or_create(name="Chuyên viên")
        cv_user = User.objects.create_user(
            username="cv_test_user",
            email="cv@donvi.gov.vn",
            password="Password123",
            ho_ten="Chuyên Viên Test",
            don_vi=self.don_vi_1,
            chuc_vu=self.cv_chuyen_vien,
        )
        cv_user.groups.add(cv_group)
        self.client.force_authenticate(user=cv_user)
        res = self.client.get(self.export_url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        # 5. Nhóm Văn thư (VT) -> 403
        vt_user = User.objects.create_user(
            username="vt_test_user",
            email="vt@donvi.gov.vn",
            password="Password123",
            ho_ten="Văn Thư Test",
            don_vi=self.don_vi_1,
            chuc_vu=self.cv_chuyen_vien,
        )
        vt_user.groups.add(self.group_van_thu)
        self.client.force_authenticate(user=vt_user)
        res = self.client.get(self.export_url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_export_excel_hierarchical_directory_format_and_formula_safe(self):
        """
        Kiểm tra danh bạ xuất Excel theo phân cấp Khối -> Đơn vị -> Nhân sự (6 cột)
        và chống Formula Injection bằng cách ép cell.data_type = 's'.
        """
        # Tạo nhân sự chứa ký tự công thức độc hại
        User.objects.create_user(
            username="formula_user",
            email="formula@donvi.gov.vn",
            password="Password123",
            ho_ten="=1+1",
            chuc_danh="@SUM(A1:B1)",
            don_vi=self.don_vi_1,
            chuc_vu=self.cv_chuyen_vien,
            sdt="+84912345678",
        )

        self.client.force_authenticate(user=self.sensitive_user)
        res = self.client.get(self.export_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(
            res["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        self.assertIn("danh_sach_cbnv.xlsx", res["Content-Disposition"])

        wb = openpyxl.load_workbook(BytesIO(res.content))
        ws = wb.active
        self.assertEqual(ws.title, "Danh Ba CBNV")

        # 1. Header Banner
        self.assertIn("Bảo Long Insurance", ws["A1"].value)
        self.assertIn("Danh bạ cán bộ nhân viên", ws["A2"].value)
        self.assertIn("Ngày xuất:", ws["A3"].value)

        # 2. Tiêu đề 6 cột tại dòng 5
        headers = [ws.cell(row=5, column=col).value for col in range(1, 7)]
        self.assertEqual(headers, ["STT", "Họ và tên", "Chức vụ", "Chức danh", "Điện thoại", "Email"])

        # 3. Duyệt kiểm tra các dòng dữ liệu và an toàn kiểu dữ liệu (ép kiểu string 's')
        found_formula_user = False
        for row in range(6, ws.max_row + 1):
            val_b = ws.cell(row=row, column=2).value
            if val_b == "=1+1":
                found_formula_user = True
                # Đảm bảo ô cell lưu dạng string ("s"), không bị Excel tự động diễn giải thành công thức ("f")
                self.assertEqual(ws.cell(row=row, column=2).data_type, "s")
                self.assertEqual(ws.cell(row=row, column=4).data_type, "s")
                self.assertEqual(ws.cell(row=row, column=5).data_type, "s")
        self.assertTrue(found_formula_user)

    def test_export_excel_active_only_and_privacy(self):
        """
        Xuất danh bạ chỉ gồm nhân sự đang làm việc (trang_thai = 'LAM_VIEC', is_active = True).
        Nhân sự nội bộ (is_public = False) chỉ xuất hiện khi người xuất có quyền view_full_cbnv.
        """
        # Tạo nhân sự đã nghỉ việc
        User.objects.create_user(
            username="retired_user",
            email="retired@donvi.gov.vn",
            password="Password123",
            ho_ten="Nguyễn Đã Nghỉ Việc",
            don_vi=self.don_vi_1,
            chuc_vu=self.cv_chuyen_vien,
            trang_thai="NGHI_VIEC",
            is_active=False,
        )

        # Tạo nhân sự nội bộ (is_public = False) đang làm việc
        User.objects.create_user(
            username="private_user",
            email="private@donvi.gov.vn",
            password="Password123",
            ho_ten="Trần Nội Bộ",
            don_vi=self.don_vi_1,
            chuc_vu=self.cv_chuyen_vien,
            trang_thai="LAM_VIEC",
            is_active=True,
            is_public=False,
        )

        # 1. Người xuất có quyền view_full_cbnv (sensitive_user)
        self.client.force_authenticate(user=self.sensitive_user)
        res = self.client.get(self.export_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        wb = openpyxl.load_workbook(BytesIO(res.content))
        ws = wb.active
        all_names = [ws.cell(row=r, column=2).value for r in range(6, ws.max_row + 1)]
        # Nhân sự nghỉ việc KHÔNG xuất hiện
        self.assertNotIn("Nguyễn Đã Nghỉ Việc", all_names)
        # Nhân sự nội bộ ĐƯỢC xuất hiện vì có view_full_cbnv
        self.assertIn("Trần Nội Bộ", all_names)

        # 2. Người xuất có export_cbnv nhưng KHÔNG có view_full_cbnv
        user_export_only = User.objects.create_user(
            username="export_only_user",
            email="export_only@donvi.gov.vn",
            password="Password123",
            ho_ten="Người Chỉ Có Quyền Xuất",
            don_vi=self.don_vi_1,
            chuc_vu=self.cv_chuyen_vien,
        )
        user_export_only.user_permissions.add(self.perm_export)
        self.client.force_authenticate(user=user_export_only)
        res = self.client.get(self.export_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        wb = openpyxl.load_workbook(BytesIO(res.content))
        ws = wb.active
        all_names_no_full = [ws.cell(row=r, column=2).value for r in range(6, ws.max_row + 1)]
        # Cả nhân sự nghỉ việc và nhân sự nội bộ đều KHÔNG xuất hiện
        self.assertNotIn("Nguyễn Đã Nghỉ Việc", all_names_no_full)
        self.assertNotIn("Trần Nội Bộ", all_names_no_full)

    def test_export_excel_concurrent_assignments(self):
        """
        Cán bộ kiêm nhiệm xuất hiện dưới từng đơn vị họ phụ trách.
        STT đánh số lại từ 1 tại mỗi đơn vị.
        """
        # normal_user có đơn vị chính là don_vi_1; kiêm nhiệm thêm don_vi_2
        EmployeeAssignment.objects.create(
            employee=self.normal_user,
            don_vi=self.don_vi_2,
            chuc_vu=self.cv_truong_phong,
            chuc_danh="Trưởng ban kiêm nhiệm",
        )

        self.client.force_authenticate(user=self.sensitive_user)
        res = self.client.get(self.export_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        wb = openpyxl.load_workbook(BytesIO(res.content))
        ws = wb.active

        # Đếm số lần normal_user xuất hiện trong bảng (phải là 2 lần: ở don_vi_1 và don_vi_2)
        normal_user_count = 0
        normal_user_chuc_danhs = []
        for r in range(6, ws.max_row + 1):
            if ws.cell(row=r, column=2).value == self.normal_user.ho_ten:
                normal_user_count += 1
                normal_user_chuc_danhs.append(ws.cell(row=r, column=4).value)
        self.assertEqual(normal_user_count, 2)
        self.assertTrue(any("kiêm nhiệm" in str(cd).lower() for cd in normal_user_chuc_danhs))

    def test_export_excel_excludes_non_public_units_without_change_donvi(self):
        """
        Mục 6: Đơn vị is_public = False và nhân sự trong đó chỉ xuất khi user là superuser
        hoặc có quyền change_donvi (khớp quy tắc _visible_units ở organizations/views.py).
        Trưởng phòng (chỉ có export_cbnv) không được thấy đơn vị nội bộ trong file xuất.
        """
        internal_unit = DonVi.objects.create(
            ten="Phòng Ban Nội Bộ Mật",
            khoi=self.khoi,
            stt_uu_tien=9999,
            is_public=False,
        )
        internal_emp = User.objects.create_user(
            username="internal_emp",
            email="internal_emp@donvi.gov.vn",
            password="Password123",
            ho_ten="Nhân Viên Ban Mật",
            don_vi=internal_unit,
            chuc_vu=self.cv_chuyen_vien,
            trang_thai="LAM_VIEC",
            is_active=True,
            is_public=True,
        )

        # 1. Trưởng phòng (có quyền export_cbnv nhưng không có change_donvi)
        tp_user = User.objects.create_user(
            username="tp_export_only",
            email="tp_export@donvi.gov.vn",
            password="Password123",
            ho_ten="Trưởng Phòng Export",
            don_vi=self.don_vi_1,
            chuc_vu=self.cv_truong_phong,
        )
        tp_user.user_permissions.add(self.perm_export)
        self.client.force_authenticate(user=tp_user)
        res_tp = self.client.get(self.export_url)
        self.assertEqual(res_tp.status_code, status.HTTP_200_OK)
        wb_tp = openpyxl.load_workbook(BytesIO(res_tp.content))
        ws_tp = wb_tp.active
        all_text_tp = [str(ws_tp.cell(row=r, column=c).value or "") for r in range(1, ws_tp.max_row + 1) for c in range(1, 7)]
        self.assertNotIn("Phòng Ban Nội Bộ Mật", all_text_tp)
        self.assertNotIn("Nhân Viên Ban Mật", all_text_tp)

        # 2. Cán bộ có quyền organizations.change_donvi -> được xem đơn vị nội bộ trong danh bạ
        user_with_change_donvi = User.objects.create_user(
            username="officer_change_dv",
            email="officer_dv@donvi.gov.vn",
            password="Password123",
            ho_ten="Cán Bộ Quản Lý Đơn Vị",
            don_vi=self.don_vi_1,
            chuc_vu=self.cv_chuyen_vien,
        )
        perm_change_donvi = Permission.objects.get(codename="change_donvi")
        user_with_change_donvi.user_permissions.add(self.perm_export, perm_change_donvi)
        self.client.force_authenticate(user=user_with_change_donvi)
        res_dv = self.client.get(self.export_url)
        self.assertEqual(res_dv.status_code, status.HTTP_200_OK)
        wb_dv = openpyxl.load_workbook(BytesIO(res_dv.content))
        ws_dv = wb_dv.active
        all_text_dv = [str(ws_dv.cell(row=r, column=c).value or "") for r in range(1, ws_dv.max_row + 1) for c in range(1, 7)]
        self.assertTrue(any("Phòng Ban Nội Bộ Mật".lower() in t.lower() for t in all_text_dv))
        self.assertIn("Nhân Viên Ban Mật", all_text_dv)

    def test_export_excel_includes_public_assignment_for_employee_with_internal_primary_unit(self):
        """Xuất đơn vị công khai vẫn liệt kê người kiêm nhiệm có đơn vị chính nội bộ."""
        internal_unit = DonVi.objects.create(
            ten="Phòng Ban Nội Bộ Gốc",
            khoi=self.khoi,
            stt_uu_tien=10000,
            is_public=False,
        )
        assigned_employee = User.objects.create_user(
            username="public_assignment_employee",
            email="public_assignment@donvi.gov.vn",
            password="Password123",
            ho_ten="Nhân Viên Có Kiêm Nhiệm Công Khai",
            don_vi=internal_unit,
            chuc_vu=self.cv_chuyen_vien,
            is_public=True,
        )
        EmployeeAssignment.objects.create(
            employee=assigned_employee,
            don_vi=self.don_vi_2,
            chuc_vu=self.cv_truong_phong,
            chuc_danh="Trưởng phòng",
        )

        tp_user = User.objects.create_user(
            username="tp_public_assignment_export",
            email="tp_public_assignment@donvi.gov.vn",
            password="Password123",
            ho_ten="Trưởng Phòng Export",
            don_vi=self.don_vi_1,
            chuc_vu=self.cv_truong_phong,
        )
        tp_user.user_permissions.add(self.perm_export)
        self.client.force_authenticate(user=tp_user)

        response = self.client.get(self.export_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ws = openpyxl.load_workbook(BytesIO(response.content)).active
        all_text = [
            str(ws.cell(row=row, column=column).value or "")
            for row in range(1, ws.max_row + 1)
            for column in range(1, 7)
        ]
        self.assertIn("Nhân Viên Có Kiêm Nhiệm Công Khai", all_text)
        self.assertNotIn("Phòng Ban Nội Bộ Gốc", all_text)

    def test_export_excel_excludes_system_admin_account(self):
        """
        Mục 6: Loại tài khoản superuser / hệ thống (admin@baolong.vn) khỏi danh bạ CBNV.
        """
        self.client.force_authenticate(user=self.admin_user)
        res = self.client.get(self.export_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        wb = openpyxl.load_workbook(BytesIO(res.content))
        ws = wb.active
        all_emails = [str(ws.cell(row=r, column=6).value or "") for r in range(6, ws.max_row + 1)]
        all_names = [str(ws.cell(row=r, column=2).value or "") for r in range(6, ws.max_row + 1)]
        self.assertNotIn("admin@baolong.vn", all_emails)
        self.assertNotIn("admin@donvi.gov.vn", all_emails)
        self.assertNotIn("Quản trị hệ thống", all_names)


class EmployeePermissionSecurityTests(EmployeeBaseTestCase):
    """
    Kiểm thử chuyên sâu bảo mật phân quyền RBAC (Issue #24 & Review PR #39).
    Kiểm tra 401 (chưa xác thực) và 403 (thiếu quyền) cho tất cả endpoint CRUD, import và xuất mẫu.
    """

    def test_unauthenticated_requests_return_401(self):
        """Request khi chưa đăng nhập (không có token) phải trả về 401 Unauthorized."""
        self.client.force_authenticate(user=None)

        detail_url = f"{self.employee_list_url}{self.normal_user.id}/"
        payload = {
            "ho_ten": "Test Unauthorized",
            "email": "unauth@donvi.gov.vn",
            "ngay_sinh": "1990-01-01",
            "don_vi_id": self.don_vi_1.id,
            "chuc_vu_id": self.cv_chuyen_vien.id,
        }

        # 1. Read endpoints
        self.assertEqual(self.client.get(self.employee_list_url).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.get(detail_url).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.get(self.template_url).status_code, status.HTTP_401_UNAUTHORIZED)

        # 2. Write endpoints
        self.assertEqual(self.client.post(self.employee_list_url, payload, format="json").status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.put(detail_url, payload, format="json").status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.patch(detail_url, {"sdt": "0912345678"}, format="json").status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.delete(detail_url).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.post(self.import_url, {}, format="multipart").status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_without_permissions_returns_403(self):
        """User đã đăng nhập nhưng không có quyền tương ứng phải bị từ chối với 403 Forbidden."""
        self.client.force_authenticate(user=self.no_perm_user)

        detail_url = f"{self.employee_list_url}{self.normal_user.id}/"
        payload = {
            "ho_ten": "CBNV Không Quyền",
            "email": "failperm@donvi.gov.vn",
            "ngay_sinh": "1990-01-01",
            "don_vi_id": self.don_vi_1.id,
            "chuc_vu_id": self.cv_chuyen_vien.id,
        }

        # Read endpoints
        self.assertEqual(self.client.get(self.employee_list_url).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.get(detail_url).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.get(self.template_url).status_code, status.HTTP_403_FORBIDDEN)

        # Write endpoints
        self.assertEqual(self.client.post(self.employee_list_url, payload, format="json").status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.patch(detail_url, {"sdt": "0912345678"}, format="json").status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.delete(detail_url).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.post(self.import_url, {}, format="multipart").status_code, status.HTTP_403_FORBIDDEN)

    def test_change_self_permission_isolated_to_own_profile(self):
        """User có quyền change_self_cbnv chỉ được sửa chính mình, sửa người khác trả về 403."""
        self.client.force_authenticate(user=self.self_user)

        # 1. Sửa thông tin cá nhân chính mình -> Thành công 200 OK
        own_url = f"{self.employee_list_url}{self.self_user.id}/"
        res_self = self.client.patch(own_url, {"sdt": "0909998877"}, format="json")
        self.assertEqual(res_self.status_code, status.HTTP_200_OK)
        self.self_user.refresh_from_db()
        self.assertEqual(self.self_user.sdt, "0909998877")

        # 2. Cố gắng sửa thông tin CBNV khác -> Bị từ chối 403 Forbidden
        other_url = f"{self.employee_list_url}{self.normal_user.id}/"
        res_other = self.client.patch(other_url, {"sdt": "0901112233"}, format="json")
        self.assertEqual(res_other.status_code, status.HTTP_403_FORBIDDEN)

        original_email = self.normal_user.email
        original_birthday = self.normal_user.ngay_sinh
        res_other_sensitive = self.client.patch(
            other_url,
            {"email": "unauthorized@example.com", "ngay_sinh": "1990-01-01"},
            format="json",
        )
        self.assertEqual(res_other_sensitive.status_code, status.HTTP_403_FORBIDDEN)
        self.normal_user.refresh_from_db()
        self.assertEqual(self.normal_user.email, original_email)
        self.assertEqual(self.normal_user.ngay_sinh, original_birthday)

    def test_admin_only_can_change_employee_password(self):
        """Password reset chỉ dành cho admin; RBAC change_full không đủ quyền."""
        url = f"{self.employee_list_url}{self.normal_user.id}/change-password/"
        new_password = "Secure-Reset-Password-42!"
        self.normal_user.user_permissions.add(self.perm_change_full)

        self.client.force_authenticate(user=self.normal_user)
        denied = self.client.post(
            url,
            {"new_password": new_password, "confirm_password": new_password},
            format="json",
        )
        self.assertEqual(denied.status_code, status.HTTP_403_FORBIDDEN)
        self.normal_user.refresh_from_db()
        self.assertTrue(self.normal_user.check_password("NormalPassword123"))

        self.client.force_authenticate(user=self.admin_user)
        mismatch = self.client.post(
            url,
            {"new_password": new_password, "confirm_password": "Different-Password-43!"},
            format="json",
        )
        self.assertEqual(mismatch.status_code, status.HTTP_400_BAD_REQUEST)
        self.normal_user.refresh_from_db()
        self.assertTrue(self.normal_user.check_password("NormalPassword123"))

        changed = self.client.post(
            url,
            {"new_password": new_password, "confirm_password": new_password},
            format="json",
        )
        self.assertEqual(changed.status_code, status.HTTP_200_OK)
        self.normal_user.refresh_from_db()
        self.assertTrue(self.normal_user.check_password(new_password))

    def test_change_self_cannot_escalate_privileges_or_modify_admin_fields(self):
        """
        Tài khoản chỉ có change_self_cbnv tuyệt đối không được tự nâng quyền
        hoặc thay đổi chức vụ, đơn vị, trạng thái, chức danh, nhóm quyền của chính mình (403 Forbidden).
        """
        self.client.force_authenticate(user=self.self_user)
        own_url = f"{self.employee_list_url}{self.self_user.id}/"

        # 1. Tự gán nhóm quyền cho mình -> Bị chặn 403
        res_group = self.client.patch(own_url, {"nhom_quyen_ids": [self.group_van_thu.id]}, format="json")
        self.assertEqual(res_group.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(res_group.data["detail"], "roles.messages.permissionDenied")
        self.self_user.refresh_from_db()
        self.assertEqual(self.self_user.groups.count(), 0)

        # 2. Tự đổi trạng thái làm việc / nghỉ việc -> 403
        res_status = self.client.patch(own_url, {"trang_thai": "NGHI_VIEC"}, format="json")
        self.assertEqual(res_status.status_code, status.HTTP_403_FORBIDDEN)
        self.self_user.refresh_from_db()
        self.assertEqual(self.self_user.trang_thai, Employee.Status.LAM_VIEC)

        # 3. Tự đổi đơn vị phòng ban -> 403
        res_unit = self.client.patch(own_url, {"don_vi_id": self.don_vi_2.id}, format="json")
        self.assertEqual(res_unit.status_code, status.HTTP_403_FORBIDDEN)
        self.self_user.refresh_from_db()
        self.assertEqual(self.self_user.don_vi_id, self.don_vi_1.id)

        # 4. Tự đổi chức vụ -> 403
        res_pos = self.client.patch(own_url, {"chuc_vu_id": self.cv_truong_phong.id}, format="json")
        self.assertEqual(res_pos.status_code, status.HTTP_403_FORBIDDEN)
        self.self_user.refresh_from_db()
        self.assertEqual(self.self_user.chuc_vu_id, self.cv_chuyen_vien.id)

        # 5. Tự đổi chức danh -> 403
        res_title = self.client.patch(own_url, {"chuc_danh": "Trưởng phòng phụ trách"}, format="json")
        self.assertEqual(res_title.status_code, status.HTTP_403_FORBIDDEN)

        # 6. Tự đổi ghi chú hoặc is_public -> 403
        self.assertEqual(self.client.patch(own_url, {"ghi_chu": "Hack ghi chú"}, format="json").status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.patch(own_url, {"is_public": False}, format="json").status_code, status.HTTP_403_FORBIDDEN)

        # 7. Gửi thông tin cá nhân hợp lệ (sdt, email, ngay_sinh) -> 200 OK
        res_ok = self.client.patch(
            own_url,
            {"sdt": "0988112233", "email": "newself@donvi.gov.vn", "ngay_sinh": "1993-03-03"},
            format="json"
        )
        self.assertEqual(res_ok.status_code, status.HTTP_200_OK)
        self.self_user.refresh_from_db()
        self.assertEqual(self.self_user.sdt, "0988112233")
        self.assertEqual(self.self_user.email, "newself@donvi.gov.vn")
        self.assertEqual(self.self_user.ngay_sinh.strftime("%Y-%m-%d"), "1993-03-03")

    def test_change_full_permission_cannot_edit_other_employee_without_admin_role(self):
        """Quyền change_full_cbnv không thay thế role admin khi sửa hồ sơ người khác."""
        hr_user = User.objects.create_user(
            username="hr_user",
            email="hr@donvi.gov.vn",
            password="HrPassword123",
            ho_ten="Cán bộ nhân sự",
            don_vi=self.don_vi_1,
            chuc_vu=self.cv_chuyen_vien,
        )
        hr_user.user_permissions.add(self.perm_view_list, self.perm_change_full)
        self.client.force_authenticate(user=hr_user)

        target_url = f"{self.employee_list_url}{self.normal_user.id}/"
        res = self.client.patch(target_url, {"sdt": "0988776655"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(res.data["detail"], "roles.messages.permissionDenied")
        self.normal_user.refresh_from_db()
        self.assertEqual(self.normal_user.sdt, "0912345678")

        self.client.force_authenticate(user=self.admin_user)
        admin_res = self.client.patch(target_url, {"sdt": "0988776655"}, format="json")
        self.assertEqual(admin_res.status_code, status.HTTP_200_OK)
        self.normal_user.refresh_from_db()
        self.assertEqual(self.normal_user.sdt, "0988776655")

    def test_add_and_delete_permissions_isolated(self):
        """Kiểm tra quyền add_cbnv và delete_cbnv hoạt động độc lập và chính xác."""
        creator_user = User.objects.create_user(
            username="creator_user",
            email="creator@donvi.gov.vn",
            password="CreatorPassword123",
            ho_ten="Cán bộ thêm mới",
            don_vi=self.don_vi_1,
            chuc_vu=self.cv_chuyen_vien,
        )
        creator_user.user_permissions.add(self.perm_add)
        self.client.force_authenticate(user=creator_user)

        # 1. Có quyền add_cbnv -> POST thành công
        payload = {
            "ho_ten": "Nhân viên mới do Creator tạo",
            "email": "newbie@donvi.gov.vn",
            "ngay_sinh": "1994-04-04",
            "don_vi_id": self.don_vi_1.id,
            "chuc_vu_id": self.cv_chuyen_vien.id,
        }
        res_create = self.client.post(self.employee_list_url, payload, format="json")
        self.assertEqual(res_create.status_code, status.HTTP_201_CREATED)
        new_emp_id = res_create.json()["id"]

        # 2. Không có quyền delete_cbnv -> DELETE bị từ chối 403
        del_url = f"{self.employee_list_url}{new_emp_id}/"
        res_delete_denied = self.client.delete(del_url)
        self.assertEqual(res_delete_denied.status_code, status.HTTP_403_FORBIDDEN)

        # 3. User có quyền delete_cbnv -> DELETE thành công 204
        deleter_user = User.objects.create_user(
            username="deleter_user",
            email="deleter@donvi.gov.vn",
            password="DeleterPassword123",
            ho_ten="Cán bộ xóa",
            don_vi=self.don_vi_1,
            chuc_vu=self.cv_chuyen_vien,
        )
        deleter_user.user_permissions.add(self.perm_delete)
        self.client.force_authenticate(user=deleter_user)
        res_delete_ok = self.client.delete(del_url, {"password": "DeleterPassword123"}, format="json")
        self.assertEqual(res_delete_ok.status_code, status.HTTP_204_NO_CONTENT)

    def test_superuser_bypasses_all_permission_gates(self):
        """Superuser không cần gán quyền lẻ tẻ, luôn vượt qua tất cả các chốt kiểm tra."""
        self.client.force_authenticate(user=self.admin_user)
        self.assertEqual(self.client.get(self.employee_list_url).status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.get(self.template_url).status_code, status.HTTP_200_OK)

    def test_ordering_and_filter_security(self):
        """Review PR #71: Chặn ordering bất hợp pháp, che ordering ngày sinh nếu thiếu quyền, validate filter int, chặn mảng JSON."""
        # 1. User thường (chỉ có view_list_cbnv) ordering field lạ -> 400 Bad Request
        self.client.force_authenticate(user=self.normal_user)
        res_bogus = self.client.get(f"{self.employee_list_url}?ordering=bogus_field")
        self.assertEqual(res_bogus.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res_bogus.data["detail"], "employees.messages.invalidOrdering")

        # 2. User thường ordering ngay_sinh mà không có view_full_cbnv -> 400 Bad Request
        res_birth = self.client.get(f"{self.employee_list_url}?ordering=ngay_sinh")
        self.assertEqual(res_birth.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res_birth.data["detail"], "employees.messages.invalidOrdering")

        # 3. User có view_full_cbnv ordering ngay_sinh -> 200 OK
        self.client.force_authenticate(user=self.sensitive_user)
        res_birth_ok = self.client.get(f"{self.employee_list_url}?ordering=-ngay_sinh")
        self.assertEqual(res_birth_ok.status_code, status.HTTP_200_OK)

        # 4. Filter id không phải số nguyên -> 400 Bad Request (thay vì 500)
        res_filter_err = self.client.get(f"{self.employee_list_url}?don_vi_id=abc")
        self.assertEqual(res_filter_err.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res_filter_err.data["detail"], "employees.messages.invalidFilterParam")

        # 5. Gửi body là mảng JSON thay vì dict -> 400 Bad Request (thay vì 500)
        self.client.force_authenticate(user=self.admin_user)
        res_array = self.client.patch(
            f"{self.employee_list_url}{self.normal_user.id}/",
            [{"ho_ten": "Hacked"}],
            format="json",
        )
        self.assertEqual(res_array.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res_array.data["detail"], "employees.messages.invalidDataFormat")

    def test_business_guards_on_delete_and_deactivate(self):
        """Review PR #71: Bảo vệ an toàn hệ thống khi xóa và thôi việc (nghỉ việc)."""
        # 1. Superuser cố gắng tự xóa chính mình -> 400
        self.client.force_authenticate(user=self.admin_user)
        res_self_del = self.client.delete(
            f"{self.employee_list_url}{self.admin_user.id}/",
            {"password": "SuperPassword123"},
            format="json",
        )
        self.assertEqual(res_self_del.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res_self_del.data["detail"], "employees.messages.cannotDeleteSelf")

        # 2. Superuser cố gắng tự thôi việc chính mình -> 400
        res_self_deact = self.client.patch(
            f"{self.employee_list_url}{self.admin_user.id}/",
            {"trang_thai": "NGHI_VIEC"},
            format="json",
        )
        self.assertEqual(res_self_deact.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res_self_deact.data["detail"], "employees.messages.cannotDeactivateSelf")

        # 3. User có delete_cbnv (nhưng không phải superuser) cố xóa superuser -> 403
        deleter_user = User.objects.create_user(
            username="guard_deleter",
            email="gdeleter@donvi.gov.vn",
            password="DeleterPass123",
            ho_ten="Deleter",
            don_vi=self.don_vi_1,
            chuc_vu=self.cv_chuyen_vien,
        )
        deleter_user.user_permissions.add(self.perm_delete)
        self.client.force_authenticate(user=deleter_user)
        res_del_su = self.client.delete(
            f"{self.employee_list_url}{self.admin_user.id}/",
            {"password": "DeleterPass123"},
            format="json",
        )
        self.assertEqual(res_del_su.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(res_del_su.data["detail"], "employees.messages.cannotDeleteSuperuser")

        # 4. User có change_full_cbnv (nhưng không phải superuser) cố chuyển superuser thành nghỉ việc -> 403
        hr_user = User.objects.create_user(
            username="guard_hr",
            email="ghr@donvi.gov.vn",
            password="HrPassword123",
            ho_ten="HR User",
            don_vi=self.don_vi_1,
            chuc_vu=self.cv_chuyen_vien,
        )
        hr_user.user_permissions.add(self.perm_change_full)
        self.client.force_authenticate(user=hr_user)
        res_deact_su = self.client.patch(
            f"{self.employee_list_url}{self.admin_user.id}/",
            {"trang_thai": "NGHI_VIEC"},
            format="json",
        )
        self.assertEqual(res_deact_su.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(res_deact_su.data["detail"], "roles.messages.permissionDenied")

        # 5. Superuser thứ 2 thôi việc superuser đầu tiên, nhưng không thể thôi việc superuser cuối cùng
        # Khôi phục dòng staging: loại tài khoản admin hệ thống khỏi phép đếm superuser
        User.objects.filter(is_superuser=True, is_active=True).exclude(pk=self.admin_user.pk).update(is_active=False)

        second_admin = User.objects.create_superuser(
            username="admin_2",
            email="admin2@donvi.gov.vn",
            password="AdminPassword123",
            ho_ten="Quản trị viên 2",
            don_vi=self.don_vi_1,
            chuc_vu=self.cv_truong_phong,
        )
        self.client.force_authenticate(user=second_admin)
        res_deact_1 = self.client.patch(
            f"{self.employee_list_url}{self.admin_user.id}/",
            {"trang_thai": "NGHI_VIEC"},
            format="json",
        )
        self.assertEqual(res_deact_1.status_code, status.HTTP_200_OK)

        # Giờ admin_user đã nghỉ việc, chỉ còn second_admin là superuser active.
        # Nếu ai đó cố gắng xóa hoặc thôi việc admin_2 -> 400 cannotDeactivateLastSuperuser / cannotDeleteLastSuperuser
        third_admin = User.objects.create_superuser(
            username="admin_3",
            email="admin3@donvi.gov.vn",
            password="AdminPassword123",
            ho_ten="Quản trị viên 3",
            don_vi=self.don_vi_1,
            chuc_vu=self.cv_truong_phong,
            trang_thai=Employee.Status.NGHI_VIEC,
        )
        self.client.force_authenticate(user=third_admin)
        res_last = self.client.patch(
            f"{self.employee_list_url}{second_admin.id}/",
            {"trang_thai": "NGHI_VIEC"},
            format="json",
        )
        self.assertEqual(res_last.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res_last.data["detail"], "employees.messages.cannotDeactivateLastSuperuser")



    def test_manual_create_rejects_weak_password(self):
        """Review PR #71: Tạo tài khoản thủ công với mật khẩu yếu phải bị từ chối 400 qua validate_password."""
        self.client.force_authenticate(user=self.admin_user)
        payload = {
            "ho_ten": "Tài Khoản Mật Khẩu Yếu",
            "email": "weakpass@donvi.gov.vn",
            "ngay_sinh": "1990-01-01",
            "don_vi_id": self.don_vi_1.id,
            "chuc_vu_id": self.cv_chuyen_vien.id,
            "password": "123",
        }
        res = self.client.post(self.employee_list_url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", res.json())


class ReviewRound4FixesTests(EmployeeBaseTestCase):
    """
    Bộ kiểm thử cho các phản hồi Review Vòng 4 từ Trưởng nhóm:
    1. Xóa CBNV có quan hệ RESTRICT / PROTECT không gây lỗi 500, trả về 400 + i18n key rõ ràng.
    2. Ngày sinh không thể ở tương lai hoặc ngoài khoảng độ tuổi [18, 100].
    3. Filter ?trang_thai=bogus trả về 400 invalidFilterParam, không gây DataError trên PostgreSQL ENUM.
    4. PATCH is_active hỗ trợ chuỗi 'false'/'true' và đồng bộ với trang_thai, áp dụng đầy đủ guards.
    5. Các lỗi serializer DRF trả chuẩn i18n keys thay vì tiếng Anh mặc định.
    6. Import Excel validate ngày sinh tương lai và độ tuổi.
    """

    @patch.object(Employee, "delete")
    def test_delete_employee_with_restricted_relation_fails_gracefully(self, mock_delete):
        """Review Vòng 4: Xóa CBNV có dữ liệu ràng buộc RESTRICT trả về 400 và thông báo thân thiện."""
        mock_delete.side_effect = RestrictedError("Cannot delete restricted relation", [])
        self.client.force_authenticate(user=self.admin_user)
        res = self.client.delete(
            f"{self.employee_list_url}{self.normal_user.id}/",
            {"password": "SuperPassword123"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data["detail"], "employees.messages.cannotDeleteProtected")

    @patch.object(Employee, "delete")
    def test_delete_employee_with_protected_relation_fails_gracefully(self, mock_delete):
        """Review Vòng 4: Xóa CBNV có dữ liệu ràng buộc PROTECT trả về 400 và thông báo thân thiện."""
        mock_delete.side_effect = ProtectedError("Cannot delete protected relation", [])
        self.client.force_authenticate(user=self.admin_user)
        res = self.client.delete(
            f"{self.employee_list_url}{self.normal_user.id}/",
            {"password": "SuperPassword123"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data["detail"], "employees.messages.cannotDeleteProtected")

    def test_birthday_validation_future_and_age_range(self):
        """Review Vòng 4: Không cho phép ngày sinh tương lai hoặc độ tuổi ngoài khoảng [18, 100]."""
        self.client.force_authenticate(user=self.admin_user)
        today = date.today()

        # 1. Ngày mai -> 400 birthdayInFuture
        tomorrow = today + timedelta(days=1)
        res_fut = self.client.post(
            self.employee_list_url,
            {
                "ho_ten": "Người Tương Lai",
                "email": "future@donvi.gov.vn",
                "ngay_sinh": tomorrow.isoformat(),
                "don_vi_id": self.don_vi_1.id,
                "chuc_vu_id": self.cv_chuyen_vien.id,
            },
            format="json",
        )
        self.assertEqual(res_fut.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("employees.messages.birthdayInFuture", str(res_fut.json()))

        # 2. Dưới 18 tuổi (ví dụ: 17 tuổi) -> 400 birthdayOutOfRange
        under_18 = date(today.year - 17, today.month, today.day)
        res_u18 = self.client.post(
            self.employee_list_url,
            {
                "ho_ten": "Người Chưa Đủ 18",
                "email": "under18@donvi.gov.vn",
                "ngay_sinh": under_18.isoformat(),
                "don_vi_id": self.don_vi_1.id,
                "chuc_vu_id": self.cv_chuyen_vien.id,
            },
            format="json",
        )
        self.assertEqual(res_u18.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("employees.messages.birthdayOutOfRange", str(res_u18.json()))

        # 3. Trên 100 tuổi (ví dụ: 101 tuổi) -> 400 birthdayOutOfRange
        over_100 = date(today.year - 101, today.month, today.day)
        res_o100 = self.client.post(
            self.employee_list_url,
            {
                "ho_ten": "Cụ Thượng Thọ",
                "email": "over100@donvi.gov.vn",
                "ngay_sinh": over_100.isoformat(),
                "don_vi_id": self.don_vi_1.id,
                "chuc_vu_id": self.cv_chuyen_vien.id,
            },
            format="json",
        )
        self.assertEqual(res_o100.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("employees.messages.birthdayOutOfRange", str(res_o100.json()))

        # 4. Độ tuổi hợp lệ (ví dụ: 25 tuổi) -> 201 Created
        valid_bday = date(today.year - 25, today.month, today.day)
        res_ok = self.client.post(
            self.employee_list_url,
            {
                "ho_ten": "Người Hợp Lệ Tuổi",
                "email": "validage@donvi.gov.vn",
                "ngay_sinh": valid_bday.isoformat(),
                "don_vi_id": self.don_vi_1.id,
                "chuc_vu_id": self.cv_chuyen_vien.id,
            },
            format="json",
        )
        self.assertEqual(res_ok.status_code, status.HTTP_201_CREATED)

    def test_invalid_trang_thai_filter_param_returns_400(self):
        """Review Vòng 4: Filter ?trang_thai=bogus phải trả về 400 chứ không gây 500 DataError trên PostgreSQL."""
        self.client.force_authenticate(user=self.admin_user)
        res = self.client.get(f"{self.employee_list_url}?trang_thai=bogus")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.json()["detail"], "employees.messages.invalidFilterParam")

    def test_patch_is_active_string_boolean_and_guards(self):
        """Review Vòng 4: PATCH is_active dạng string 'false'/'true' phải được ghi nhận và đồng bộ trạng thái."""
        self.client.force_authenticate(user=self.admin_user)

        # 1. Khóa tài khoản qua is_active="false" (chuỗi)
        res_deact = self.client.patch(
            f"{self.employee_list_url}{self.normal_user.id}/",
            {"is_active": "false"},
            format="json",
        )
        self.assertEqual(res_deact.status_code, status.HTTP_200_OK)
        self.normal_user.refresh_from_db()
        self.assertFalse(self.normal_user.is_active)
        self.assertEqual(self.normal_user.trang_thai, Employee.Status.NGHI_VIEC)

        # 2. Mở khóa tài khoản qua is_active="true" (chuỗi)
        res_react = self.client.patch(
            f"{self.employee_list_url}{self.normal_user.id}/",
            {"is_active": "true"},
            format="json",
        )
        self.assertEqual(res_react.status_code, status.HTTP_200_OK)
        self.normal_user.refresh_from_db()
        self.assertTrue(self.normal_user.is_active)
        self.assertEqual(self.normal_user.trang_thai, Employee.Status.LAM_VIEC)

        # 3. Bảo vệ: Không cho phép tự khóa tài khoản của chính mình bằng is_active="false"
        res_self = self.client.patch(
            f"{self.employee_list_url}{self.admin_user.id}/",
            {"is_active": "false"},
            format="json",
        )
        self.assertEqual(res_self.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res_self.data["detail"], "employees.messages.cannotDeactivateSelf")

    def test_drf_serializer_error_messages_i18n(self):
        """Review Vòng 4: Toàn bộ lỗi validation từ DRF serializer phải trả mã i18n chuẩn."""
        self.client.force_authenticate(user=self.admin_user)

        # 1. Họ tên quá 150 ký tự
        res_name = self.client.post(
            self.employee_list_url,
            {
                "ho_ten": "A" * 151,
                "email": "nametoolong@donvi.gov.vn",
                "ngay_sinh": "1990-01-01",
                "don_vi_id": self.don_vi_1.id,
                "chuc_vu_id": self.cv_chuyen_vien.id,
            },
            format="json",
        )
        self.assertEqual(res_name.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res_name.json()["ho_ten"], ["employees.messages.nameTooLong"])

        # 2. Email sai định dạng
        res_email = self.client.post(
            self.employee_list_url,
            {
                "ho_ten": "Email Sai",
                "email": "invalid-email-format",
                "ngay_sinh": "1990-01-01",
                "don_vi_id": self.don_vi_1.id,
                "chuc_vu_id": self.cv_chuyen_vien.id,
            },
            format="json",
        )
        self.assertEqual(res_email.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res_email.json()["email"], ["employees.messages.invalidEmail"])

        # 3. Đơn vị không tồn tại
        res_donvi = self.client.post(
            self.employee_list_url,
            {
                "ho_ten": "Đơn Vị Ảo",
                "email": "donviao@donvi.gov.vn",
                "ngay_sinh": "1990-01-01",
                "don_vi_id": 999999,
                "chuc_vu_id": self.cv_chuyen_vien.id,
            },
            format="json",
        )
        self.assertEqual(res_donvi.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res_donvi.json()["don_vi_id"], ["employees.messages.unitNotFound"])

        # 4. Chức vụ không tồn tại
        res_chucvu = self.client.post(
            self.employee_list_url,
            {
                "ho_ten": "Chức Vụ Ảo",
                "email": "chucvuao@donvi.gov.vn",
                "ngay_sinh": "1990-01-01",
                "don_vi_id": self.don_vi_1.id,
                "chuc_vu_id": 999999,
            },
            format="json",
        )
        self.assertEqual(res_chucvu.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res_chucvu.json()["chuc_vu_id"], ["employees.messages.positionNotFound"])

        # 5. SĐT sai chuẩn VN (qua regex validator ở model)
        res_sdt = self.client.post(
            self.employee_list_url,
            {
                "ho_ten": "SĐT Sai",
                "email": "sdtsai@donvi.gov.vn",
                "ngay_sinh": "1990-01-01",
                "don_vi_id": self.don_vi_1.id,
                "chuc_vu_id": self.cv_chuyen_vien.id,
                "sdt": "09999",
            },
            format="json",
        )
        self.assertEqual(res_sdt.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res_sdt.json()["sdt"], ["employees.messages.invalidPhone"])

    def test_excel_import_birthday_validations(self):
        """Review Vòng 4: Import Excel kiểm tra ngày sinh tương lai và khoảng tuổi [18, 100]."""
        self.client.force_authenticate(user=self.sensitive_user)
        today = date.today()
        fut_date = (today + timedelta(days=5)).isoformat()
        u18_date = date(today.year - 16, today.month, today.day).isoformat()

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["Họ và tên", "Ngày sinh", "Email", "Số điện thoại", "Đơn vị", "Chức vụ", "Chức danh", "Trạng thái", "Ghi chú"])
        ws.append(["Tương Lai", fut_date, "fut@donvi.gov.vn", "0912345678", self.don_vi_1.ten, self.cv_truong_phong.name, "", "Đang làm việc", ""])
        ws.append(["Dưới 18", u18_date, "u18@donvi.gov.vn", "0912345679", self.don_vi_1.ten, self.cv_truong_phong.name, "", "Đang làm việc", ""])

        bio = BytesIO()
        wb.save(bio)
        bio.seek(0)
        bio.name = "test_birthdays.xlsx"

        res = self.client.post(self.import_url, {"file": bio}, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        errors = res.json()["errors"]
        codes = [err["code"] for err in errors]
        self.assertIn("employees.messages.birthdayInFuture", codes)
        self.assertIn("employees.messages.birthdayOutOfRange", codes)


class SeedDbCommandTests(APITestCase):
    """Seed dữ liệu tham chiếu theo kiểu create-only và giữ nguyên account có sẵn."""

    def test_seed_db_is_complete_and_idempotent(self):
        from django.core.management import call_command

        existing_demo = User.objects.create_user(
            username="truongphong_cntt",
            password="existing-demo-password",
            email="existing-demo@example.com",
            ho_ten="Tài khoản hiện có",
            don_vi=DonVi.objects.first(),
            chuc_vu=Position.objects.first(),
            is_active=False,
            is_staff=True,
            is_superuser=False,
        )
        existing_demo_hash = existing_demo.password

        with patch.dict("os.environ", {"ADMIN_PASSWORD": "seed-test-admin-password"}):
            call_command("seed_db", verbosity=0)
        self.assertEqual(KhoiKhuVuc.objects.count(), 16)
        self.assertEqual(DonVi.objects.count(), 82)
        self.assertEqual(DonVi.objects.filter(ten="Lãnh đạo khối").count(), 2)
        admin = User.objects.get(username="admin")
        self.assertTrue(admin.is_superuser)
        first_password_hash = admin.password
        self.assertFalse(User.objects.filter(username="chuyenvien_cntt").exists())

        with patch.dict("os.environ", {
            "ADMIN_PASSWORD": "different-seed-password",
            "DEMO_PASSWORD": "seed-test-demo-password",
        }):
            call_command("seed_db", demo_data=True, verbosity=0)
        self.assertEqual(DonVi.objects.count(), 82)
        self.assertEqual(Position.objects.count(), 25)
        self.assertEqual(User.objects.get(username="admin").password, first_password_hash)
        preserved_demo = User.objects.get(username="truongphong_cntt")
        self.assertEqual(preserved_demo.password, existing_demo_hash)
        self.assertFalse(preserved_demo.is_active)
        self.assertTrue(preserved_demo.is_staff)
        created_demo = User.objects.get(username="chuyenvien_cntt")
        self.assertTrue(created_demo.check_password("seed-test-demo-password"))

        with patch.dict("os.environ", {
            "ADMIN_PASSWORD": "later-admin-password",
            "DEMO_PASSWORD": "later-demo-password",
        }):
            call_command("seed_db", demo_data=True, verbosity=0)
        self.assertEqual(User.objects.get(username="admin").password, first_password_hash)
        self.assertEqual(User.objects.get(username="truongphong_cntt").password, existing_demo_hash)
        self.assertTrue(User.objects.get(username="chuyenvien_cntt").check_password("seed-test-demo-password"))

    def test_missing_seed_secrets_fail_before_reference_data_changes(self):
        from django.core.management import call_command
        from django.core.management.base import CommandError

        before = (KhoiKhuVuc.objects.count(), DonVi.objects.count(), Position.objects.count())
        with patch.dict("os.environ", {}, clear=True), self.assertRaises(CommandError):
            call_command("seed_db", verbosity=0)
        with patch.dict("os.environ", {"ADMIN_PASSWORD": "seed-test-admin-password"}, clear=True):
            with self.assertRaises(CommandError):
                call_command("seed_db", demo_data=True, verbosity=0)
        self.assertEqual((KhoiKhuVuc.objects.count(), DonVi.objects.count(), Position.objects.count()), before)


class EmployeeAssignmentTests(EmployeeBaseTestCase):
    """Kiểm tra chức năng Đa phòng ban & Đa chức vụ (EmployeeAssignment)."""

    def test_create_employee_with_assignments_success(self):
        """Tạo nhân viên kèm danh sách phòng ban & chức vụ kiêm nhiệm."""
        self.client.force_authenticate(user=self.admin_user)
        payload = {
            "ho_ten": "Hoàng Đa Nhiệm",
            "email": "daniem@donvi.gov.vn",
            "ngay_sinh": "1991-03-15",
            "don_vi_id": self.don_vi_1.id,
            "chuc_vu_id": self.cv_chuyen_vien.id,
            "chuc_danh": "Chuyên viên chính",
            "sdt": "0988776655",
            "trang_thai": "LAM_VIEC",
            "assignments": [
                {
                    "don_vi_id": self.don_vi_2.id,
                    "chuc_vu_id": self.cv_truong_phong.id,
                    "chuc_danh": "Phó phòng kiêm nhiệm",
                }
            ],
        }
        res = self.client.post(self.employee_list_url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        data = res.json()
        self.assertEqual(len(data.get("assignments", [])), 1)
        self.assertEqual(data["assignments"][0]["don_vi_id"], self.don_vi_2.id)
        self.assertEqual(data["assignments"][0]["chuc_vu_id"], self.cv_truong_phong.id)
        self.assertEqual(data["assignments"][0]["chuc_danh"], "Phó phòng kiêm nhiệm")

        # Kiểm tra trong DB
        user = User.objects.get(email="daniem@donvi.gov.vn")
        assignments = EmployeeAssignment.objects.filter(employee=user)
        self.assertEqual(assignments.count(), 1)
        self.assertEqual(assignments.first().don_vi, self.don_vi_2)
        self.assertEqual(assignments.first().chuc_vu, self.cv_truong_phong)

    def test_create_employee_duplicate_assignment_with_primary_unit_fails(self):
        """Phòng ban kiêm nhiệm trùng với phòng ban chính phải bị từ chối 400."""
        self.client.force_authenticate(user=self.admin_user)
        payload = {
            "ho_ten": "Trùng Phòng Ban Chính",
            "email": "trungchinh@donvi.gov.vn",
            "ngay_sinh": "1991-03-15",
            "don_vi_id": self.don_vi_1.id,
            "chuc_vu_id": self.cv_chuyen_vien.id,
            "assignments": [
                {
                    "don_vi_id": self.don_vi_1.id,
                    "chuc_vu_id": self.cv_truong_phong.id,
                }
            ],
        }
        res = self.client.post(self.employee_list_url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("assignments", res.json())

    def test_create_employee_duplicate_units_among_assignments_fails(self):
        """Hai phòng ban kiêm nhiệm trùng nhau phải bị từ chối 400."""
        # Tạo thêm đơn vị 3
        max_stt = DonVi.objects.aggregate(Max("stt_uu_tien"))["stt_uu_tien__max"] or 0
        don_vi_3 = DonVi.objects.create(ten="Phòng Khoa học & Công nghệ", khoi=self.khoi, stt_uu_tien=max_stt + 1)
        self.client.force_authenticate(user=self.admin_user)
        payload = {
            "ho_ten": "Trùng Kiêm Nhiệm",
            "email": "trungkiem@donvi.gov.vn",
            "ngay_sinh": "1991-03-15",
            "don_vi_id": self.don_vi_1.id,
            "chuc_vu_id": self.cv_chuyen_vien.id,
            "assignments": [
                {
                    "don_vi_id": don_vi_3.id,
                    "chuc_vu_id": self.cv_truong_phong.id,
                },
                {
                    "don_vi_id": don_vi_3.id,
                    "chuc_vu_id": self.cv_chuyen_vien.id,
                },
            ],
        }
        res = self.client.post(self.employee_list_url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("assignments", res.json())

    def test_update_employee_assignments(self):
        """Cập nhật thay thế danh sách phòng ban kiêm nhiệm thành công."""
        self.client.force_authenticate(user=self.admin_user)
        max_stt = DonVi.objects.aggregate(Max("stt_uu_tien"))["stt_uu_tien__max"] or 0
        don_vi_3 = DonVi.objects.create(ten="Phòng Hành chính", khoi=self.khoi, stt_uu_tien=max_stt + 1)

        # Cán bộ ban đầu kiêm nhiệm don_vi_2
        EmployeeAssignment.objects.create(
            employee=self.normal_user,
            don_vi=self.don_vi_2,
            chuc_vu=self.cv_truong_phong,
            chuc_danh="Tổ trưởng",
        )

        detail_url = f"{self.employee_list_url}{self.normal_user.id}/"
        payload = {
            "assignments": [
                {
                    "don_vi_id": don_vi_3.id,
                    "chuc_vu_id": self.cv_chuyen_vien.id,
                    "chuc_danh": "Phụ trách hành chính",
                }
            ]
        }
        res = self.client.patch(detail_url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()
        self.assertEqual(len(data["assignments"]), 1)
        self.assertEqual(data["assignments"][0]["don_vi_id"], don_vi_3.id)

        # Kiểm tra DB: don_vi_2 đã được thay bằng don_vi_3
        assignments = EmployeeAssignment.objects.filter(employee=self.normal_user)
        self.assertEqual(assignments.count(), 1)
        self.assertEqual(assignments.first().don_vi, don_vi_3)

    def test_protect_delete_don_vi_when_assigned_concurrently(self):
        """Không thể xóa Đơn vị khi đang có cán bộ kiêm nhiệm (on_delete=PROTECT)."""
        EmployeeAssignment.objects.create(
            employee=self.normal_user,
            don_vi=self.don_vi_2,
            chuc_vu=self.cv_chuyen_vien,
        )
        with self.assertRaises(ProtectedError):
            self.don_vi_2.delete()

    def test_protect_delete_chuc_vu_when_assigned_concurrently(self):
        """Không thể xóa Chức vụ khi đang có cán bộ kiêm nhiệm (on_delete=PROTECT)."""
        EmployeeAssignment.objects.create(
            employee=self.normal_user,
            don_vi=self.don_vi_2,
            chuc_vu=self.cv_chuyen_vien,
        )
        with self.assertRaises(ProtectedError):
            self.cv_chuyen_vien.delete()

    def test_validate_assignment_chuc_danh_max_length(self):
        """Chức danh kiêm nhiệm không được vượt quá 150 ký tự."""
        self.client.force_authenticate(user=self.admin_user)
        payload = {
            "assignments": [
                {
                    "don_vi_id": self.don_vi_2.id,
                    "chuc_vu_id": self.cv_chuyen_vien.id,
                    "chuc_danh": "A" * 151,
                }
            ]
        }
        detail_url = f"{self.employee_list_url}{self.normal_user.id}/"
        res = self.client.patch(detail_url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("assignments", res.json())


class ExportCbnvMigrationTests(TestCase):
    """Kiểm tra tính lũy đẳng (idempotent) của migration add_export_cbnv_permission."""

    def test_migration_add_export_cbnv_idempotent(self):
        from importlib import import_module

        mig = import_module("authorization.migrations.0009_add_export_cbnv_permission")

        add_export_cbnv_permission = mig.add_export_cbnv_permission
        CODENAME = mig.CODENAME

        class SchemaStub:
            connection = connection

        # Chạy lại hàm migration 2 lần liên tiếp không gây lỗi duplicate key
        add_export_cbnv_permission(None, SchemaStub)
        add_export_cbnv_permission(None, SchemaStub)

        perm = Permission.objects.filter(codename=CODENAME)
        self.assertEqual(perm.count(), 1)
        with connection.cursor() as cursor:
            cursor.execute("SELECT module_ten FROM auth_permission WHERE codename = %s", [CODENAME])
            row = cursor.fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row[0], "CBNV")


class EmployeeDefaultGroupAssignmentTests(EmployeeBaseTestCase):
    """
    Kiểm tra tự động gán nhóm quyền theo chức vụ khi tạo mới CBNV (Issue #24 / PR #211).
    Yêu cầu:
    1. Tra nhóm theo mã ma_nhom_quyen qua authorization.GroupInfo, không tra theo tên nhóm.
    2. Một chức vụ có thể nhận hai nhóm (ví dụ: Trợ lý TGĐ -> CV + TLBGD, Kiểm toán viên -> CV + KT).
    3. Chỉ áp dụng khi tạo CBNV mà không chọn nhóm quyền; nhóm chưa tồn tại trong DB thì bỏ qua, không trả lỗi 500.
    4. Hai nhóm TLBGD và KT sẽ được thêm bằng PR phân quyền riêng; trước khi PR đó merge, Trợ lý TGĐ và Kiểm toán viên chỉ nhận CV.
    5. Có chọn nhóm thủ công thì không tự gán.
    """

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(user=self.admin_user)

        # Đảm bảo các nhóm quyền chuẩn có mã ma_nhom_quyen tương ứng
        standard_groups = [
            ("Quản trị hệ thống", "ADMIN"),
            ("Ban Giám đốc", "BGD"),
            ("Trưởng phòng", "TP"),
            ("Chuyên viên", "CV"),
            ("Văn thư", "VT"),
        ]
        for name, code in standard_groups:
            g, _ = Group.objects.get_or_create(name=name)
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE auth_group SET ma_nhom_quyen = %s WHERE id = %s",
                    [code, g.id],
                )

    def _create_position(self, name):
        max_order = Position.objects.aggregate(Max("display_order"))["display_order__max"] or 0
        pos, _ = Position.objects.get_or_create(
            name=name,
            defaults={"display_order": max_order + 1, "is_public": True},
        )
        return pos

    def _post_employee(self, ho_ten, email, pos, nhom_quyen_ids=None):
        payload = {
            "ho_ten": ho_ten,
            "email": email,
            "ngay_sinh": "1990-01-01",
            "don_vi_id": self.don_vi_1.id,
            "chuc_vu_id": pos.id,
        }
        if nhom_quyen_ids is not None:
            payload["nhom_quyen_ids"] = nhom_quyen_ids
        response = self.client.post(self.employee_list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return User.objects.get(email=email)

    def test_import_excel_assigns_default_groups_by_position(self):
        """Import Excel dùng cùng bảng ánh xạ nhóm quyền mặc định như luồng tạo CBNV."""
        from authorization.models import GroupInfo

        supplementary_group, _ = Group.objects.get_or_create(name="Trợ lý Ban Giám đốc")
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE auth_group SET ma_nhom_quyen = %s WHERE id = %s",
                ["TLBGD", supplementary_group.id],
            )

        position = self._create_position("Trợ lý TGĐ")
        workbook = openpyxl.Workbook()
        worksheet = workbook.active
        worksheet.title = "Danh Sach CBNV"
        worksheet.append([
            "STT", "Họ và tên (*)", "Ngày sinh (*)", "Email (*)", "Số điện thoại",
            "Tên Đơn vị / Phòng ban (*)", "Tên Chức vụ (*)", "Chức danh", "Trạng thái", "Ghi chú",
        ])
        worksheet.append(["(Ghi chú)", "", "", "", "", "", "", "", "", ""])
        worksheet.append([
            1, "Trần Import Kiêm Quyền", "1990-01-01", "import_default_groups@donvi.gov.vn",
            "0912345679", "Văn phòng Viện", position.name, "", "Đang làm việc", "",
        ])
        file_obj = BytesIO()
        workbook.save(file_obj)
        file_obj.seek(0)
        file_obj.name = "danh_sach_cbnv.xlsx"

        response = self.client.post(self.import_url, {"file": file_obj}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        imported_employee = User.objects.get(email="import_default_groups@donvi.gov.vn")
        assigned_codes = set(
            GroupInfo.objects.filter(
                id__in=imported_employee.groups.values_list("id", flat=True)
            ).values_list("ma_nhom_quyen", flat=True)
        )
        self.assertEqual(assigned_codes, {"CV", "TLBGD"})

    def test_single_group_positions_auto_assign(self):
        """Các chức vụ gán 1 nhóm quyền: Tổng Giám đốc -> BGD, Trưởng phòng -> TP, Chuyên viên -> CV, Văn thư -> VT."""
        from authorization.models import GroupInfo

        cases = [
            ("Tổng Giám đốc", "BGD"),
            ("Chủ tịch HĐQT", "BGD"),
            ("Giám đốc Khối", "TP"),
            ("Trưởng phòng", "TP"),
            ("Chuyên viên", "CV"),
            ("Nhân viên", "CV"),
            ("Văn thư", "VT"),
        ]
        for idx, (pos_name, expected_code) in enumerate(cases):
            pos = self._create_position(pos_name)
            email = f"emp_auto_{idx}@donvi.gov.vn"
            emp = self._post_employee(f"CBNV {pos_name}", email, pos)

            assigned_group_ids = list(emp.groups.values_list("id", flat=True))
            assigned_codes = set(
                GroupInfo.objects.filter(id__in=assigned_group_ids).values_list("ma_nhom_quyen", flat=True)
            )
            self.assertIn(
                expected_code,
                assigned_codes,
                f"Chức vụ {pos_name} cần được tự động gán mã nhóm {expected_code}",
            )
            self.assertEqual(
                len(assigned_group_ids),
                1,
                f"Chức vụ {pos_name} chỉ được gán đúng 1 nhóm quyền chuẩn",
            )

    def test_two_group_position_when_both_groups_exist(self):
        """Chức vụ gán 2 nhóm: Trợ lý TGĐ -> CV + TLBGD; Kiểm toán viên -> CV + KT khi cả 2 nhóm đều có trong DB."""
        from authorization.models import GroupInfo

        # Tạo thêm nhóm TLBGD và KT
        for name, code in [("Trợ lý Ban Giám đốc", "TLBGD"), ("Kiểm toán", "KT")]:
            g, _ = Group.objects.get_or_create(name=name)
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE auth_group SET ma_nhom_quyen = %s WHERE id = %s",
                    [code, g.id],
                )

        pos_tro_ly = self._create_position("Trợ lý TGĐ")
        emp_tro_ly = self._post_employee("Trần Trợ Lý", "troly_both@donvi.gov.vn", pos_tro_ly)
        tro_ly_codes = set(
            GroupInfo.objects.filter(id__in=emp_tro_ly.groups.values_list("id", flat=True)).values_list(
                "ma_nhom_quyen", flat=True
            )
        )
        self.assertEqual(tro_ly_codes, {"CV", "TLBGD"})

        pos_kiem_toan = self._create_position("Kiểm toán viên")
        emp_kiem_toan = self._post_employee("Lê Kiểm Toán", "kiemtoan_both@donvi.gov.vn", pos_kiem_toan)
        kiem_toan_codes = set(
            GroupInfo.objects.filter(id__in=emp_kiem_toan.groups.values_list("id", flat=True)).values_list(
                "ma_nhom_quyen", flat=True
            )
        )
        self.assertEqual(kiem_toan_codes, {"CV", "KT"})

    def test_two_group_position_before_second_group_exists(self):
        """Trước khi nhóm TLBGD/KT tồn tại trong DB, Trợ lý TGĐ và Kiểm toán viên chỉ nhận nhóm CV."""
        from authorization.models import GroupInfo

        # Đảm bảo TLBGD và KT không tồn tại trong DB
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM auth_group WHERE ma_nhom_quyen IN ('TLBGD', 'KT')")

        pos_tro_ly = self._create_position("Trợ lý TGĐ")
        emp_tro_ly = self._post_employee("Trần Trợ Lý", "troly_cv_only@donvi.gov.vn", pos_tro_ly)
        tro_ly_codes = set(
            GroupInfo.objects.filter(id__in=emp_tro_ly.groups.values_list("id", flat=True)).values_list(
                "ma_nhom_quyen", flat=True
            )
        )
        self.assertEqual(tro_ly_codes, {"CV"})

        pos_kiem_toan = self._create_position("Kiểm toán viên")
        emp_kiem_toan = self._post_employee("Lê Kiểm Toán", "kiemtoan_cv_only@donvi.gov.vn", pos_kiem_toan)
        kiem_toan_codes = set(
            GroupInfo.objects.filter(id__in=emp_kiem_toan.groups.values_list("id", flat=True)).values_list(
                "ma_nhom_quyen", flat=True
            )
        )
        self.assertEqual(kiem_toan_codes, {"CV"})

    def test_group_not_exist_in_db_skips_without_500(self):
        """Nhóm trong bảng ánh xạ chưa tồn tại trong DB thì bỏ qua, không trả lỗi 500."""
        # Xóa nhóm BGD khỏi auth_group
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM auth_group WHERE ma_nhom_quyen = 'BGD'")

        pos = self._create_position("Tổng Giám đốc")
        emp = self._post_employee("Nguyễn Bgd Test", "bgd_skip_500@donvi.gov.vn", pos)
        self.assertEqual(emp.groups.count(), 0)

        pos_custom = self._create_position("Chức vụ Chưa Định Nghĩa")
        emp_custom = self._post_employee("Nguyễn Tự Do", "custom_pos@donvi.gov.vn", pos_custom)
        self.assertEqual(emp_custom.groups.count(), 0)

    def test_quan_tri_vien_position_does_not_auto_assign_admin(self):
        """Chức vụ Quản trị viên không tự nhận nhóm ADMIN, kể cả khi người tạo là superuser."""
        pos = self._create_position("Quản trị viên")
        emp = self._post_employee("Nguyễn Quản Trị", "qtv_no_auto@donvi.gov.vn", pos)
        self.assertEqual(emp.groups.count(), 0)

    def _manager_client(self, codename="change_full_cbnv"):
        from rest_framework.test import APIClient

        manager = User.objects.create_user(
            username=f"mgr_{codename}",
            email=f"mgr_{codename}@donvi.gov.vn",
            password="ManagerPassword123",
            ho_ten="Trưởng Phòng Quản Lý",
            ngay_sinh=date(1985, 1, 1),
            don_vi=self.don_vi_1,
            chuc_vu=self.cv_truong_phong,
        )
        manager.user_permissions.add(*Permission.objects.filter(codename__in=[codename, "add_cbnv"]))
        client = APIClient()
        client.force_authenticate(user=manager)
        return manager, client

    def _create_payload(self, email, pos, group_ids):
        return {
            "ho_ten": "Người Mới",
            "email": email,
            "ngay_sinh": "1990-01-01",
            "don_vi_id": self.don_vi_1.id,
            "chuc_vu_id": pos.id,
            "nhom_quyen_ids": group_ids,
        }

    def test_non_admin_cannot_grant_admin_group_on_create(self):
        admin_group = Group.objects.get(name="Quản trị hệ thống")
        cv_group = Group.objects.get(name="Chuyên viên")
        pos = self._create_position("Chuyên viên")
        _, client = self._manager_client()

        denied = client.post(self.employee_list_url, self._create_payload("deny_admin@donvi.gov.vn", pos, [admin_group.id]), format="json")
        self.assertEqual(denied.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("employees.messages.adminGroupForbidden", str(denied.data))
        self.assertFalse(User.objects.filter(email="deny_admin@donvi.gov.vn").exists())

        allowed = client.post(self.employee_list_url, self._create_payload("allow_cv@donvi.gov.vn", pos, [cv_group.id]), format="json")
        self.assertEqual(allowed.status_code, status.HTTP_201_CREATED)

    def test_admin_group_member_and_superuser_can_grant_admin_group(self):
        admin_group = Group.objects.get(name="Quản trị hệ thống")
        pos = self._create_position("Chuyên viên")

        superuser_emp = self._post_employee("Do Superuser", "by_super@donvi.gov.vn", pos, nhom_quyen_ids=[admin_group.id])
        self.assertTrue(superuser_emp.groups.filter(pk=admin_group.pk).exists())

        admin_member, client = self._manager_client()
        admin_member.groups.add(admin_group)
        response = client.post(self.employee_list_url, self._create_payload("by_member@donvi.gov.vn", pos, [admin_group.id]), format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_non_admin_cannot_add_or_remove_admin_group_on_update(self):
        """Người không phải ADMIN/superuser không đổi được thành viên nhóm ADMIN khi sửa CBNV.

        Từ khi chỉ superuser được sửa CBNV khác, view trả 403 trước; serializer vẫn chặn riêng
        như lớp bảo vệ thứ hai nên được kiểm thử trực tiếp.
        """
        from rest_framework.test import APIRequestFactory

        from accounts.serializers import EmployeeUpdateSerializer

        admin_group = Group.objects.get(name="Quản trị hệ thống")
        cv_group = Group.objects.get(name="Chuyên viên")
        pos = self._create_position("Chuyên viên")
        target = self._post_employee("Mục Tiêu", "target_update@donvi.gov.vn", pos, nhom_quyen_ids=[cv_group.id])
        url = f"{self.employee_list_url}{target.id}/"
        manager, client = self._manager_client()

        add = client.patch(url, {"nhom_quyen_ids": [cv_group.id, admin_group.id]}, format="json")
        self.assertEqual(add.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(target.groups.filter(pk=admin_group.pk).exists())

        request = APIRequestFactory().patch(url)
        request.user = manager
        serializer = EmployeeUpdateSerializer(
            target, data={"nhom_quyen_ids": [cv_group.id, admin_group.id]}, partial=True, context={"request": request}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("nhom_quyen_ids", serializer.errors)

        target.groups.add(admin_group)
        serializer = EmployeeUpdateSerializer(
            target, data={"nhom_quyen_ids": [cv_group.id]}, partial=True, context={"request": request}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("nhom_quyen_ids", serializer.errors)

        serializer = EmployeeUpdateSerializer(
            target, data={"nhom_quyen_ids": [admin_group.id, self.group_van_thu.id]}, partial=True, context={"request": request}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_superuser_can_add_admin_group_on_update(self):
        admin_group = Group.objects.get(name="Quản trị hệ thống")
        cv_group = Group.objects.get(name="Chuyên viên")
        pos = self._create_position("Chuyên viên")
        target = self._post_employee("Mục Tiêu Hai", "target_update2@donvi.gov.vn", pos, nhom_quyen_ids=[cv_group.id])

        response = self.client.patch(
            f"{self.employee_list_url}{target.id}/",
            {"nhom_quyen_ids": [cv_group.id, admin_group.id]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(target.groups.filter(pk=admin_group.pk).exists())

    def test_manual_group_selection_does_not_auto_assign(self):
        """Có chọn nhóm quyền thủ công thì không tự gán theo chức vụ."""
        from authorization.models import GroupInfo

        pos = self._create_position("Tổng Giám đốc")
        cv_group = Group.objects.get(name="Chuyên viên")

        emp = self._post_employee(
            "Phạm Tổng Giám Đốc",
            "tgd_manual@donvi.gov.vn",
            pos,
            nhom_quyen_ids=[cv_group.id],
        )

        assigned_group_ids = list(emp.groups.values_list("id", flat=True))
        assigned_codes = set(
            GroupInfo.objects.filter(id__in=assigned_group_ids).values_list("ma_nhom_quyen", flat=True)
        )
        self.assertEqual(assigned_codes, {"CV"})
        self.assertNotIn("BGD", assigned_codes)


class EmployeeImportWorkerIntegrationTests(TransactionTestCase):
    """Kiểm thử worker nền với transaction thật để thread khác đọc được job đã commit."""

    def setUp(self):
        super().setUp()
        EmployeeBaseTestCase.setUp(self)
        self.client = APIClient()

    def test_worker_persists_success_and_removes_private_file(self):
        self.client.force_authenticate(user=self.sensitive_user)
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.append([
            "Họ và tên (*)", "Ngày sinh (*)", "Email (*)", "Số điện thoại",
            "Tên Đơn vị / Phòng ban (*)", "Tên Chức vụ (*)", "Chức danh", "Trạng thái", "Ghi chú",
        ])
        sheet.append([
            "Nhân viên nền", "1990-01-01", "worker-import@example.test", "0912345678",
            self.don_vi_1.ten, self.cv_chuyen_vien.name, "", "Đang làm việc", "",
        ])
        file_obj = BytesIO()
        workbook.save(file_obj)
        file_obj.seek(0)
        file_obj.name = "worker_import.xlsx"

        with patch("accounts.views_employee._start_employee_import_worker"):
            response = self.client.post(
                "/api/accounts/employees/import-async/",
                {"file": file_obj},
                format="multipart",
                HTTP_IDEMPOTENCY_KEY="worker-success-import",
            )
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        job = EmployeeImportJob.objects.get(pk=response.json()["job_id"])
        stored_file = Path(settings.MEDIA_ROOT) / job.file_path
        _run_employee_import_job(job.pk)

        job.refresh_from_db()
        self.assertEqual(job.status, EmployeeImportJob.Status.DONE)
        self.assertIsNone(job.active_key)
        self.assertEqual(job.created_count, 1)
        self.assertTrue(User.objects.filter(email="worker-import@example.test").exists())
        self.assertFalse(stored_file.exists())
