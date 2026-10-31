"""
Unit tests cho cơ chế xác thực kép:
1. Admin set pass (Xác thực cục bộ & Quản trị viên đổi mật khẩu)
2. API check pass (Xác thực qua API Ngân hàng Bảo Long / Alpaca theo tài liệu GVHD)
"""
import json
import urllib.error
from unittest.mock import patch

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from accounts.alpaca_auth import (
    generate_alpaca_auth_mac,
    generate_alpaca_user_exist_mac,
    check_alpaca_auth,
)

User = get_user_model()


class DualAuthenticationTests(TestCase):
    def setUp(self):
        provider = patch("accounts.alpaca_auth.urllib.request.urlopen", side_effect=urllib.error.URLError("offline test"))
        self.provider = provider.start()
        self.addCleanup(provider.stop)
        self.client = APIClient()
        self.secret_key = "9089e45b638cee8f83ab423d2cb498b5"

        # 1. Tạo tài khoản Admin nội bộ (admin set pass)
        self.admin = User.objects.create_superuser(
            username="admin_test",
            password="AdminPassword@2026",
            email="admin_test@baolong.vn",
            ho_ten="Quản Trị Viên Test",
        )

        # 2. Tạo tài khoản nhân viên thường
        self.staff = User.objects.create_user(
            username="staff_test",
            password="InitialPassword@123",
            email="staff_test@baolong.vn",
            ho_ten="Cán Bộ Test",
        )

    def test_mac_generation_matches_specification(self):
        """Kiểm tra thuật toán sinh mã MAC khớp 100% với tài liệu và ảnh minh họa."""
        # Test case 1: check-user-exist (Ảnh 1 và 3 trong tài liệu)
        mac_user_exist = generate_alpaca_user_exist_mac("phanquocdung", self.secret_key)
        self.assertEqual(mac_user_exist, "E23232F0A22FABB7FBC751D851B1B124")

        # Test case 2: check-auth-user (Ảnh 5 và 6 trong tài liệu)
        # Sắp xếp alphabet: password đứng trước userName
        mac_auth = generate_alpaca_auth_mac("phanquocdung", "Alpaca#2025", self.secret_key)
        self.assertEqual(mac_auth, "CAA667FD71C897E5EF8FD3BA7FC48BC4")

    def test_admin_set_pass_login(self):
        """Xác thực thành công với tài khoản do Admin set mật khẩu trong hệ thống (Local Auth)."""
        response = self.client.post(
            "/api/auth/login/",
            {"username": "admin_test", "password": "AdminPassword@2026"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertIn("token", response.data)
        self.assertIn("access", response.data)
        self.assertEqual(response.data["auth_provider"], "local")

    def test_api_check_pass_login(self):
        """Xác thực thành công với tài khoản Ngân hàng Bảo Long qua API check pass khi tài khoản đã được cấp trong hệ thống."""
        # Tài khoản CBNV đã được Quản trị viên khởi tạo trước trong hệ thống
        dung_user = User.objects.create_user(
            username="phanquocdung",
            password="InitialLocalPassword#123",
            email="phanquocdung@baolong.vn",
            ho_ten="Phan Quốc Dũng",
        )
        self.provider.side_effect = None
        self.provider.return_value.__enter__.return_value.read.return_value = json.dumps({"Success": True, "Data": 7}).encode()
        response = self.client.post(
            "/api/auth/login/",
            {"username": "phanquocdung", "password": "Alpaca#2025"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertIn("token", response.data)
        self.assertEqual(response.data["auth_provider"], "alpaca_api")
        self.assertEqual(response.data["user"]["fullName"], "Phan Quốc Dũng")

        # [Điểm 2]: Mật khẩu cục bộ KHÔNG bị ghi đè bởi mật khẩu Alpaca
        dung_user.refresh_from_db()
        self.assertTrue(dung_user.check_password("InitialLocalPassword#123"))

    def test_unprovisioned_alpaca_user_returns_403(self):
        """[Điểm 3]: Tài khoản Alpaca hợp lệ nhưng chưa được Quản trị viên cấp trong hệ thống -> 403 Forbidden, không tự tạo."""
        self.provider.side_effect = None
        self.provider.return_value.__enter__.return_value.read.return_value = json.dumps({"Success": True, "Data": 7}).encode()
        response = self.client.post(
            "/api/auth/login/",
            {"username": "unprovisioned_user", "password": "Alpaca#2025"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("chưa được phân quyền", response.data.get("error", ""))
        self.assertFalse(User.objects.filter(username="unprovisioned_user").exists())

    def test_privileged_user_never_calls_external_api_on_failed_local_auth(self):
        """[Điểm 1 & Điểm 2]: Tài khoản admin/staff nhập sai mật khẩu cục bộ thì trả 401 ngay, TUYỆT ĐỐI không gọi Alpaca API."""
        with patch("accounts.views.check_alpaca_auth") as mock_check_alpaca:
            response = self.client.post("/api/auth/login/", {
                "username": self.admin.username,
                "password": "WrongAdminPassword@123",
            })
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
            mock_check_alpaca.assert_not_called()

    def test_admin_set_password_endpoint(self):
        """Admin đổi mật khẩu cho nhân viên, sau đó nhân viên đăng nhập bằng mật khẩu mới."""
        # 1. User thường không có quyền đổi mật khẩu người khác -> 403 Forbidden
        self.client.force_authenticate(user=self.staff)
        res_forbidden = self.client.post(
            "/api/auth/admin-set-password/",
            {"username": "staff_test", "new_password": "NewSecretPass#2026"},
            format="json",
        )
        self.assertEqual(res_forbidden.status_code, status.HTTP_403_FORBIDDEN)

        # 2. Xác thực bằng admin (có quyền RBAC hoặc is_superuser)
        self.client.force_authenticate(user=self.admin)

        # 2.1 Thử đặt mật khẩu yếu -> Bị từ chối bởi validate_password của Django (400)
        res_weak = self.client.post(
            "/api/auth/admin-set-password/",
            {"username": "staff_test", "new_password": "123"},
            format="json",
        )
        self.assertEqual(res_weak.status_code, status.HTTP_400_BAD_REQUEST)

        # 2.2 Đặt mật khẩu hợp lệ -> 200 OK
        res_change = self.client.post(
            "/api/auth/admin-set-password/",
            {"username": "staff_test", "new_password": "NewSecretPass#2026"},
            format="json",
        )
        self.assertEqual(res_change.status_code, status.HTTP_200_OK)
        self.assertTrue(res_change.data["success"])

        # 3. Bỏ authenticate admin và thử đăng nhập bằng mật khẩu mới của staff
        self.client.force_authenticate(user=None)
        res_login_old = self.client.post(
            "/api/auth/login/",
            {"username": "staff_test", "password": "InitialPassword@123"},
            format="json",
        )
        # Mật khẩu cũ không còn đúng
        self.assertEqual(res_login_old.status_code, status.HTTP_401_UNAUTHORIZED)

        # Mật khẩu mới đăng nhập thành công
        res_login_new = self.client.post(
            "/api/auth/login/",
            {"username": "staff_test", "password": "NewSecretPass#2026"},
            format="json",
        )
        self.assertEqual(res_login_new.status_code, status.HTTP_200_OK)
        self.assertTrue(res_login_new.data["success"])
        self.assertEqual(res_login_new.data["auth_provider"], "local")

    def test_login_invalid_credentials(self):
        """Nhập sai thông tin đăng nhập bị từ chối 401."""
        response = self.client.post(
            "/api/auth/login/",
            {"username": "non_existent_user", "password": "WrongPassword!999"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertFalse(response.data["success"])

    def test_provider_errors_never_accept_sample_credentials(self):
        for error in (urllib.error.URLError("offline"), TimeoutError(), ValueError("invalid JSON")):
            with self.subTest(error=type(error).__name__):
                if isinstance(error, ValueError):
                    self.provider.side_effect = None
                    self.provider.return_value.__enter__.return_value.read.return_value = b"not-json"
                else:
                    self.provider.side_effect = error
                with self.assertLogs("accounts.alpaca_auth", level="WARNING"):
                    result = check_alpaca_auth("phanquocdung", "Alpaca#2025")
                    self.assertFalse(result["success"])
                    self.assertFalse(result["is_fallback"])
                    response = self.client.post("/api/auth/login/", {
                        "username": "phanquocdung", "password": "Alpaca#2025",
                    })
                self.assertEqual(response.status_code, 401)
                self.assertNotIn("access", response.data)
                self.assertFalse(User.objects.filter(username="phanquocdung").exists())

    def test_external_success_preserves_local_disabled_account(self):
        self.staff.is_active = False
        self.staff.save(update_fields=["is_active"])
        old_hash = self.staff.password
        with patch("accounts.views.check_alpaca_auth", return_value={"success": True}):
            response = self.client.post("/api/auth/login/", {
                "username": self.staff.username, "password": "ExternalPassword123",
            })
        self.assertEqual(response.status_code, 403)
        self.assertNotIn("access", response.data)
        self.staff.refresh_from_db()
        self.assertFalse(self.staff.is_active)
        self.assertEqual(self.staff.password, old_hash)

    def test_external_success_does_not_overwrite_local_password(self):
        """[Điểm 2]: Khi xác thực Alpaca thành công, mật khẩu cục bộ KHÔNG bị ghi đè."""
        old_password_hash = self.staff.password
        with patch("accounts.views.check_alpaca_auth", return_value={"success": True}):
            response = self.client.post("/api/auth/login/", {
                "username": self.staff.username, "password": "ExternalPassword123",
            })
        self.assertEqual(response.status_code, 200)
        self.staff.refresh_from_db()
        self.assertEqual(self.staff.password, old_password_hash)
        self.assertTrue(self.staff.check_password("InitialPassword@123"))
        self.assertFalse(self.staff.check_password("ExternalPassword123"))

