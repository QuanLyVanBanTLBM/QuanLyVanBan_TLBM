"""Văn bản: quản trị hệ thống (superuser, nhóm ADMIN) được nhận diện, username admin/quantri không còn đặc quyền."""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from authorization.models import GroupInfo
from documents import selectors, views
from documents.models import PhamVi, VanBanDen

User = get_user_model()


def make_user(username, group_code=None):
    user = User.objects.filter(username=username).first() or User.objects.create_user(
        username=username, password="TestOnly12345"
    )
    user.is_superuser = user.is_staff = False
    user.save()
    user.groups.clear()
    user.user_permissions.clear()
    if group_code:
        user.groups.add(Group.objects.get(pk=GroupInfo.objects.get(ma_nhom_quyen=group_code).pk))
    return user


class DocumentSystemAdminTest(TestCase):
    def setUp(self):
        self.owner = make_user("vb_owner")
        self.doc = VanBanDen.objects.create(
            nam=2026, so_hieu="1/SA", so_thu_tu=1, trich_yeu="Văn bản của người khác", nguoi_tao=self.owner,
        )

    def test_admin_group_is_admin_in_both_helpers(self):
        member = make_user("vb_admin_member", "ADMIN")
        self.assertTrue(selectors.is_admin_user(member))
        self.assertTrue(views.is_admin_user(member))
        self.assertTrue(views.can_edit_document(member, self.doc))

    def test_username_admin_without_admin_group_has_no_privilege(self):
        for name in ("admin", "quantri"):
            fake = make_user(name)
            self.assertFalse(selectors.is_admin_user(fake), name)
            self.assertFalse(views.is_admin_user(fake), name)
            self.assertFalse(views.can_edit_document(fake, self.doc), name)

    def test_admin_group_can_patch_document_of_another_user(self):
        member = make_user("vb_admin_patch", "ADMIN")
        client = APIClient()
        client.force_authenticate(user=member)
        res = client.patch(f"/api/documents/{self.doc.id}/", {"trich_yeu": "Quản trị sửa"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.content)

    def test_admin_group_can_edit_restricted_document_of_another_user(self):
        restricted = VanBanDen.objects.create(
            nam=2026, so_hieu="2/SA", so_thu_tu=2, trich_yeu="Văn bản hạn chế", nguoi_tao=self.owner,
            pham_vi=PhamVi.HAN_CHE,
        )
        member = make_user("vb_admin_hc", "ADMIN")
        self.assertTrue(views.can_edit_document(member, restricted))
        other = make_user("vb_other", "CV")
        self.assertFalse(views.can_edit_document(other, restricted))
