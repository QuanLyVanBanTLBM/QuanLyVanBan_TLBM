"""Issue #83 (mục Nhóm 7): tài khoản bị khóa (is_active = False) bị từ chối ở mọi request, kể cả token đã cấp."""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db.models import Max
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from organizations.models import DonVi, KhoiKhuVuc

ME_PERMISSIONS = "/api/auth/me/permissions/"
UNITS = "/api/organizations/units/"
REFRESH = "/api/auth/token/refresh/"


class InactiveAccountTokenTest(TestCase):
    def setUp(self):
        priority = (DonVi.objects.aggregate(m=Max("stt_uu_tien"))["m"] or 0) + 1
        unit = DonVi.objects.create(khoi=KhoiKhuVuc.objects.create(ten="Khối token"), stt_uu_tien=priority, ten="Đơn vị token")
        self.user = get_user_model().objects.create_user(username="locked_later", password="x", don_vi=unit)
        self.user.user_permissions.add(Permission.objects.get(codename="view_donvi"))
        self.refresh = RefreshToken.for_user(self.user)
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.refresh.access_token}")

    def lock(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])

    def test_token_works_while_account_is_active(self):
        self.assertEqual(self.client.get(ME_PERMISSIONS).status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.get(UNITS).status_code, status.HTTP_200_OK)

    def test_issued_access_token_is_rejected_after_account_is_locked(self):
        self.lock()
        for url in (ME_PERMISSIONS, UNITS):
            self.assertEqual(self.client.get(url).status_code, status.HTTP_401_UNAUTHORIZED, url)

    def test_issued_refresh_token_cannot_mint_a_new_access_token_after_lock(self):
        self.lock()
        response = APIClient().post(REFRESH, {"refresh": str(self.refresh)}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotIn("access", response.data)
