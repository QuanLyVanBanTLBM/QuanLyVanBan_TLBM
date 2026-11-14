"""Gửi mail toàn hệ thống (#484) và đổi hiệu lực văn bản của người khác (#486) chỉ theo quyền trong Phân quyền."""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from authorization.models import GroupInfo
from documents.models import HieuLuc, PhamVi, VanBanDen, VanBanDi
from documents.views import can_send_mail_all

User = get_user_model()

ADD_PERMS = ["add_vanbanden", "add_vanbandi"]
VIEW_PERMS = ["view_vanbanden", "view_vanbandi"]


def user_in_group(username, group_name, codenames):
    group, _ = Group.objects.get_or_create(name=group_name)
    group.permissions.set(Permission.objects.filter(codename__in=codenames))
    user = User.objects.create_user(username=username, password="password123")
    user.groups.add(group)
    return User.objects.get(pk=user.pk)


def client_of(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


class GuiMailToanHeThongTheoQuyenTests(TestCase):
    def post_with_mail_all(self, user, loai):
        return client_of(user).post(
            "/api/documents/",
            {"loai": loai, "so_hieu": f"1/MAIL-{user.username}", "trich_yeu": "Gửi mail", "gui_mail_toan_he_thong": True},
            format="json",
        )

    def test_group_name_does_not_grant_permission(self):
        """Nhóm tên Văn thư, VT, Quản trị, admin... nhưng chưa có quyền send_mail_all_* thì bị từ chối."""
        for index, name in enumerate(["Văn thư", "vanthu", "VT", "Quản trị", "admin", "ADMIN", "Admin"]):
            user = user_in_group(f"khong_quyen_{index}", name, ADD_PERMS)
            self.assertFalse(can_send_mail_all(user, "DEN"), name)
            self.assertFalse(can_send_mail_all(user, "DI"), name)
            for loai in ("DEN", "DI"):
                response = self.post_with_mail_all(user, loai)
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, (name, loai))
                self.assertIn("gui_mail_toan_he_thong", response.data)

    def test_user_with_permission_can_send(self):
        user = user_in_group("co_quyen_den", "Nhóm tự tạo", ADD_PERMS + ["send_mail_all_vanbanden"])
        self.assertTrue(can_send_mail_all(user, "DEN"))
        self.assertFalse(can_send_mail_all(user, "DI"))
        self.assertEqual(self.post_with_mail_all(user, "DEN").status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.post_with_mail_all(user, "DI").status_code, status.HTTP_400_BAD_REQUEST)

    def test_system_admin_group_can_send_without_explicit_permission(self):
        user = User.objects.create_user(username="quan_tri_he_thong", password="password123")
        user.groups.add(Group.objects.get(pk=GroupInfo.objects.get(ma_nhom_quyen="ADMIN").pk))
        user = User.objects.get(pk=user.pk)
        self.assertTrue(can_send_mail_all(user, "DEN"))
        self.assertTrue(can_send_mail_all(user, "DI"))


class DoiHieuLucVanBanNguoiKhacTaoTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="nguoi_tao", password="password123")
        self.doc_den = VanBanDen.objects.create(
            so_hieu="1/DEN-HL", so_thu_tu=1, trich_yeu="Văn bản đến", nguoi_tao=self.owner,
            hieu_luc=HieuLuc.CON_HIEU_LUC, pham_vi=PhamVi.NOI_BO,
        )
        self.doc_di = VanBanDi.objects.create(
            so_hieu="1/DI-HL", so_thu_tu=1, trich_yeu="Văn bản đi", nguoi_tao=self.owner,
            hieu_luc=HieuLuc.CON_HIEU_LUC, pham_vi=PhamVi.NOI_BO,
        )
        self.only_validity = user_in_group(
            "chi_doi_hieu_luc", "Chỉ đổi hiệu lực",
            VIEW_PERMS + ["change_hieu_luc_vanbanden", "change_hieu_luc_vanbandi"],
        )
        self.no_validity = user_in_group("khong_doi_hieu_luc", "Chỉ xem", VIEW_PERMS)

    def urls(self):
        return [
            ("den", f"/api/documents/den/{self.doc_den.id}/", self.doc_den),
            ("chung_den", f"/api/documents/{self.doc_den.id}/?loai=DEN", self.doc_den),
            ("di", f"/api/documents/di/{self.doc_di.id}/", self.doc_di),
            ("chung_di", f"/api/documents/{self.doc_di.id}/?loai=DI", self.doc_di),
        ]

    def test_permission_holder_changes_only_validity_of_others_document(self):
        client = client_of(self.only_validity)
        for label, url, doc in self.urls():
            doc.refresh_from_db()
            doc.hieu_luc = HieuLuc.CON_HIEU_LUC
            doc.save(update_fields=["hieu_luc"])

            changed = client.patch(url, {"hieu_luc": HieuLuc.HET_HIEU_LUC}, format="json")
            self.assertEqual(changed.status_code, status.HTTP_200_OK, label)
            doc.refresh_from_db()
            self.assertEqual(doc.hieu_luc, HieuLuc.HET_HIEU_LUC, label)

            other_field = client.patch(url, {"trich_yeu": "Sửa trái quyền"}, format="json")
            self.assertEqual(other_field.status_code, status.HTTP_403_FORBIDDEN, label)
            doc.refresh_from_db()
            self.assertEqual(doc.trich_yeu, "Văn bản đến" if "den" in label else "Văn bản đi", label)

    def test_user_without_validity_permission_is_denied(self):
        client = client_of(self.no_validity)
        for label, url, doc in self.urls():
            response = client.patch(url, {"hieu_luc": HieuLuc.HET_HIEU_LUC}, format="json")
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, label)
            doc.refresh_from_db()
            self.assertEqual(doc.hieu_luc, HieuLuc.CON_HIEU_LUC, label)

    def test_list_flag_follows_permission(self):
        for user, expected in ((self.only_validity, True), (self.no_validity, False)):
            response = client_of(user).get("/api/documents/?loai=DEN")
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            rows = response.data.get("results", response.data)
            self.assertTrue(rows)
            self.assertEqual({bool(row.get("can_change_hieu_luc")) for row in rows}, {expected})
