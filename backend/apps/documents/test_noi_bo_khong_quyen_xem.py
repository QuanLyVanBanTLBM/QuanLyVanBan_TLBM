"""Văn bản nội bộ: tài khoản không có quyền xem chỉ thấy văn bản do mình tạo, kể cả khi hien_thi = True."""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from authorization.models import GroupInfo
from documents.models import VanBanDen, VanBanDi

User = get_user_model()


def make_user(username, group=None, perms=()):
    user = User.objects.create_user(username=username, password="TestOnly12345")
    if group:
        user.groups.add(Group.objects.get(pk=GroupInfo.objects.get(ma_nhom_quyen=group).pk))
    for codename in perms:
        user.user_permissions.add(Permission.objects.get(codename=codename))
    return user


def api(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


class InternalDocumentVisibilityTest(TestCase):
    def setUp(self):
        self.owner = make_user("nb_owner", "CV")
        self.nobody = make_user("nb_none")
        self.viewer = make_user("nb_viewer", perms=("view_vanbanden", "view_vanbandi"))
        self.staff_cv = make_user("nb_cv", "CV")
        self.den = VanBanDen.objects.create(
            nam=2026, so_hieu="1/NB", so_thu_tu=701, trich_yeu="den", nguoi_tao=self.owner, hien_thi=True
        )
        self.di = VanBanDi.objects.create(
            nam=2026, so_hieu="2/NB", so_thu_tu=702, trich_yeu="di", nguoi_tao=self.owner, hien_thi=True
        )

    def _ids(self, user, url):
        response = api(user).get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        data = response.json()
        return {item["id"] for item in data.get("results", data)}

    def test_account_without_view_permission_does_not_see_others_documents(self):
        self.assertNotIn(self.den.pk, self._ids(self.nobody, "/api/documents/den/"))
        self.assertNotIn(self.di.pk, self._ids(self.nobody, "/api/documents/di/"))
        self.assertNotIn(self.den.pk, self._ids(self.nobody, "/api/documents/?loai=DEN"))
        self.assertNotIn(self.di.pk, self._ids(self.nobody, "/api/documents/?loai=DI"))

    def test_account_without_view_permission_gets_403_on_detail(self):
        self.assertEqual(api(self.nobody).get(f"/api/documents/den/{self.den.pk}/").status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(api(self.nobody).get(f"/api/documents/di/{self.di.pk}/").status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            api(self.nobody).get(f"/api/documents/{self.den.pk}/?loai=DEN").status_code, status.HTTP_403_FORBIDDEN
        )

    def test_account_without_view_permission_sees_own_documents(self):
        mine = VanBanDen.objects.create(
            nam=2026, so_hieu="3/NB", so_thu_tu=703, trich_yeu="của tôi", nguoi_tao=self.nobody, hien_thi=True
        )
        self.assertEqual(self._ids(self.nobody, "/api/documents/den/"), {mine.pk})
        self.assertEqual(api(self.nobody).get(f"/api/documents/den/{mine.pk}/").status_code, status.HTTP_200_OK)

    def test_recipient_can_still_open_detail(self):
        self.den.nguoi_nhan.add(self.nobody)
        self.assertEqual(api(self.nobody).get(f"/api/documents/den/{self.den.pk}/").status_code, status.HTTP_200_OK)

    def test_accounts_with_view_permission_see_internal_documents(self):
        for user in (self.viewer, self.staff_cv):
            self.assertIn(self.den.pk, self._ids(user, "/api/documents/den/"), user.username)
            self.assertIn(self.di.pk, self._ids(user, "/api/documents/di/"), user.username)
            self.assertEqual(api(user).get(f"/api/documents/den/{self.den.pk}/").status_code, status.HTTP_200_OK)
