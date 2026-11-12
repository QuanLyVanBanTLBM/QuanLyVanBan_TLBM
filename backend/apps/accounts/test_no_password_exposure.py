"""
Không API nào được trả password hoặc password hash (Issue #21, tiêu chí nghiệm thu).

Mật khẩu tạm của CBNV vừa tạo là ngoại lệ có chủ đích: khóa `temporary_password`, chỉ trả một lần
khi tạo mới (không phải hash và không lưu plaintext).
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import Position
from organizations.models import DonVi, KhoiKhuVuc

HASH_MARKERS = ("pbkdf2_", "argon2", "bcrypt", "md5$", "sha1$", "scrypt$")
ALLOWED_PASSWORD_KEYS = {"temporary_password"}


def _walk(value, path=""):
    """Duyệt toàn bộ JSON, trả về (đường dẫn khóa, giá trị) của mọi phần tử."""
    if isinstance(value, dict):
        for key, child in value.items():
            yield from _walk(child, f"{path}.{key}" if path else key)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk(child, f"{path}[{index}]")
    else:
        yield path, value


class NoPasswordExposureTests(APITestCase):
    PASSWORD = "Sup3r-Secret-Password!"

    def setUp(self):
        User = get_user_model()
        khoi = KhoiKhuVuc.objects.create(ten="Khối Kiểm Thử")
        latest_stt = DonVi.objects.order_by("-stt_uu_tien").values_list("stt_uu_tien", flat=True).first() or 0
        self.don_vi = DonVi.objects.create(khoi=khoi, stt_uu_tien=latest_stt + 1, ten="Đơn vị kiểm thử")
        self.chuc_vu = Position.objects.create(display_order=Position.get_next_display_order(), name="Chuyên viên")
        self.admin = User.objects.create_superuser(
            username="admin_nopw",
            password=self.PASSWORD,
            email="admin_nopw@example.com",
            ho_ten="Quản trị kiểm thử",
        )
        self.staff = User.objects.create_user(
            username="staff_nopw",
            password=self.PASSWORD,
            email="staff_nopw@example.com",
            ho_ten="Nhân viên kiểm thử",
            don_vi=self.don_vi,
            chuc_vu=self.chuc_vu,
        )
        self.group = Group.objects.get(name="Quản trị hệ thống")
        self.client.force_authenticate(user=self.admin)

    def assert_no_password(self, response):
        self.assertIn(response.status_code, (status.HTTP_200_OK, status.HTTP_201_CREATED))
        payload = response.json()
        for path, value in _walk(payload):
            leaf = path.split(".")[-1].split("[")[0].lower()
            if "password" in leaf:
                self.assertIn(leaf, ALLOWED_PASSWORD_KEYS, f"API trả khóa mật khẩu ở '{path}'")
            if isinstance(value, str):
                self.assertNotIn(self.PASSWORD, value, f"API trả mật khẩu ở '{path}'")
                for marker in HASH_MARKERS:
                    self.assertFalse(value.lower().startswith(marker), f"API trả password hash ở '{path}'")

    def test_employee_endpoints_do_not_return_password_hash(self):
        base = "/api/accounts/employees/"
        self.assert_no_password(self.client.get(base))
        self.assert_no_password(self.client.get(f"{base}?all=true"))
        self.assert_no_password(self.client.get(f"{base}{self.staff.id}/"))
        self.assert_no_password(self.client.patch(f"{base}{self.staff.id}/", {"sdt": "0912345678"}, format="json"))

    def test_employee_create_returns_only_the_one_time_temporary_password(self):
        response = self.client.post(
            "/api/accounts/employees/",
            {
                "ho_ten": "Nhân viên mới",
                "email": "newbie_nopw@baolong.vn",
                "ngay_sinh": "1995-05-05",
                "don_vi_id": self.don_vi.id,
                "chuc_vu_id": self.chuc_vu.id,
            },
            format="json",
        )
        self.assert_no_password(response)
        body = response.json()
        self.assertTrue(body["temporary_password"])
        stored = get_user_model().objects.get(pk=body["id"])
        self.assertNotEqual(stored.password, body["temporary_password"])
        self.assertTrue(stored.check_password(body["temporary_password"]))

        # Lần đọc sau không còn mật khẩu tạm.
        again = self.client.get(f"/api/accounts/employees/{body['id']}/")
        self.assertIsNone(again.json()["temporary_password"])

    def test_authentication_endpoints_do_not_return_password_hash(self):
        self.client.force_authenticate(user=None)
        login = self.client.post(
            reverse("accounts:login"),
            {"username": "staff_nopw", "password": self.PASSWORD},
            format="json",
        )
        self.assert_no_password(login)

        self.client.force_authenticate(user=self.staff)
        self.assert_no_password(self.client.get(reverse("accounts:profile")))
        self.assert_no_password(self.client.get("/api/auth/me/permissions/"))

    def test_rbac_endpoints_do_not_return_password_hash(self):
        self.assert_no_password(self.client.get("/api/roles/"))
        self.assert_no_password(self.client.get(f"/api/roles/{self.group.id}/"))
        self.assert_no_password(self.client.get("/api/permissions/"))
