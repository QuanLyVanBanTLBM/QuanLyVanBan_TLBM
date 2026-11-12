"""Trình ký: API chỉ dành cho tài khoản có quyền thuộc phân hệ; tài khoản không quyền nhận 403."""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from authorization.models import GroupInfo
from signing.permissions import (
    GUI_TRINH_KY, HUY_TRINH_KY, KY_TRINH_KY, QUAN_LY_QUY_TRINH, TAO_TRINH_KY, XEM_NHAT_KY, XEM_TAT_CA, XEM_TRINH_KY,
)

from .helpers import cap_quyen

User = get_user_model()

ENDPOINTS = (
    "pin/",
    "trinh-ky/",
    "trinh-ky/thong-ke/",
    "trinh-ky/don-vi-ap-dung/",
    "tai-lieu/",
    "toi/",
    "dashboard/",
    "thong-bao/",
    "anh-chu-ky-ca-nhan/",
    "nguoi-ky-co-quyen/",
    "quy-trinh/",
)
BASE = "/api/v1/signing/"


def client_of(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


class SigningAccessByPermissionTests(TestCase):
    def test_account_without_any_signing_permission_is_blocked_everywhere(self):
        client = client_of(User.objects.create_user(username="tk_khong_quyen"))
        for endpoint in ENDPOINTS:
            response = client.get(BASE + endpoint)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, endpoint)
            self.assertEqual(response.json()["code"], "khong_co_quyen", endpoint)

    def test_ping_stays_open_for_authenticated_accounts(self):
        client = client_of(User.objects.create_user(username="tk_ping"))
        self.assertEqual(client.get(BASE + "ping/").status_code, status.HTTP_200_OK)

    def test_anonymous_gets_401_not_403(self):
        self.assertEqual(APIClient().get(BASE + "toi/").status_code, status.HTTP_401_UNAUTHORIZED)

    def test_any_single_signing_permission_opens_the_api(self):
        for index, codename in enumerate((
            XEM_TRINH_KY, TAO_TRINH_KY, GUI_TRINH_KY, KY_TRINH_KY, HUY_TRINH_KY, XEM_NHAT_KY, XEM_TAT_CA,
            QUAN_LY_QUY_TRINH,
        )):
            user = User.objects.create_user(username=f"tk_quyen_{index}")
            cap_quyen(user, codename)
            response = client_of(user).get(BASE + "toi/")
            self.assertEqual(response.status_code, status.HTTP_200_OK, codename)

    def test_every_standard_group_keeps_access(self):
        for code in ("VT", "CV", "TP", "BGD", "ADMIN"):
            user = User.objects.create_user(username=f"tk_nhom_{code}")
            user.groups.add(Group.objects.get(pk=GroupInfo.objects.get(ma_nhom_quyen=code).pk))
            client = client_of(user)
            for endpoint in ("toi/", "trinh-ky/", "dashboard/", "pin/", "thong-bao/"):
                response = client.get(BASE + endpoint)
                self.assertEqual(response.status_code, status.HTTP_200_OK, (code, endpoint, response.content))
