"""
Quản trị CBNV theo is_system_admin (superuser hoặc nhóm ADMIN):
- Chỉ quản trị hệ thống tạo và import CBNV; add_cbnv, import_cbnv một mình không đủ.
- Nhóm ADMIN (không phải superuser) sửa được hồ sơ người khác và đổi mật khẩu CBNV;
  không đổi được mật khẩu tài khoản superuser.
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from rest_framework import status

from accounts.models import Employee, EmployeePasswordResetAudit
from accounts.test_employees import EmployeeBaseTestCase
from authorization.models import GroupInfo

User = get_user_model()


def group_of(code):
    return Group.objects.get(pk=GroupInfo.objects.get(ma_nhom_quyen=code).pk)


class CbnvSystemAdminTests(EmployeeBaseTestCase):
    def setUp(self):
        super().setUp()
        self.admin_member = self.make_member("adm_member", "ADMIN")

    def make_member(self, username, group_code, perms=()):
        user = User.objects.create_user(
            username=username, email=f"{username}@baolong.vn", password="MemberPassword123",
            ho_ten=f"Thành viên {username}", don_vi=self.don_vi_1, chuc_vu=self.cv_chuyen_vien,
        )
        user.groups.add(group_of(group_code))
        if perms:
            user.user_permissions.add(*Permission.objects.filter(codename__in=perms))
        return user

    def payload(self, email):
        return {
            "ho_ten": "Người Mới Thử", "email": email, "ngay_sinh": "1990-01-01",
            "don_vi_id": self.don_vi_1.id, "chuc_vu_id": self.cv_chuyen_vien.id,
        }

    def test_admin_group_member_can_create_employee(self):
        self.client.force_authenticate(user=self.admin_member)
        res = self.client.post(self.employee_list_url, self.payload("created_by_group@baolong.vn"), format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.content)

    def test_non_admin_with_add_and_import_permissions_cannot_create_or_import(self):
        for code in ("TP", "BGD", "VT", "CV"):
            member = self.make_member(f"hr_{code}", code, perms=("add_cbnv", "import_cbnv"))
            self.client.force_authenticate(user=member)
            res = self.client.post(self.employee_list_url, self.payload(f"deny_{code}@baolong.vn"), format="json")
            self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN, code)
            self.assertFalse(Employee.objects.filter(email=f"deny_{code}@baolong.vn").exists())
            res = self.client.post(self.import_url, {}, format="multipart")
            self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN, code)
            res = self.client.post("/api/accounts/employees/import-async/", {}, format="multipart")
            self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN, code)

    def test_admin_group_member_reaches_import_endpoint(self):
        self.client.force_authenticate(user=self.admin_member)
        res = self.client.post(self.import_url, {}, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_admin_group_member_can_edit_other_employee(self):
        self.client.force_authenticate(user=self.admin_member)
        res = self.client.patch(
            f"{self.employee_list_url}{self.normal_user.id}/", {"sdt": "0988776655"}, format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.content)
        self.normal_user.refresh_from_db()
        self.assertEqual(self.normal_user.sdt, "0988776655")

    def test_admin_group_member_cannot_deactivate_superuser(self):
        self.client.force_authenticate(user=self.admin_member)
        res = self.client.patch(
            f"{self.employee_list_url}{self.admin_user.id}/", {"trang_thai": "NGHI_VIEC"}, format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_group_member_changes_password_of_employee_but_not_of_superuser(self):
        new_password = "Secure-Reset-Password-42!"
        body = {
            "new_password": new_password, "confirm_password": new_password,
            "reason_code": EmployeePasswordResetAudit.Reason.OTHER, "reason_detail": "Yêu cầu hỗ trợ đã xác minh",
        }
        self.client.force_authenticate(user=self.admin_member)
        ok = self.client.post(f"{self.employee_list_url}{self.normal_user.id}/change-password/", body, format="json")
        self.assertEqual(ok.status_code, status.HTTP_200_OK, ok.content)
        self.normal_user.refresh_from_db()
        self.assertTrue(self.normal_user.check_password(new_password))

        denied = self.client.post(f"{self.employee_list_url}{self.admin_user.id}/change-password/", body, format="json")
        self.assertEqual(denied.status_code, status.HTTP_403_FORBIDDEN)
        self.admin_user.refresh_from_db()
        self.assertFalse(self.admin_user.check_password(new_password))

    def test_admin_set_password_endpoint_protects_superuser(self):
        new_password = "Secure-Reset-Password-43!"
        self.client.force_authenticate(user=self.admin_member)
        denied = self.client.post(
            "/api/auth/admin-set-password/",
            {"username": self.admin_user.username, "new_password": new_password}, format="json",
        )
        self.assertEqual(denied.status_code, status.HTTP_403_FORBIDDEN)
        self.admin_user.refresh_from_db()
        self.assertFalse(self.admin_user.check_password(new_password))
        ok = self.client.post(
            "/api/auth/admin-set-password/",
            {"username": self.normal_user.username, "new_password": new_password}, format="json",
        )
        self.assertEqual(ok.status_code, status.HTTP_200_OK, ok.content)

    def test_superuser_still_creates_and_changes_everything(self):
        self.client.force_authenticate(user=self.admin_user)
        res = self.client.post(self.employee_list_url, self.payload("created_by_super@baolong.vn"), format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
