"""
Văn bản đến/đi hết hiệu lực (HET_HIEU_LUC, HET_VA_THAY_THE), cả NOI_BO lẫn HAN_CHE:
- Xem: chỉ superuser hoặc quyền view_het_hieu_luc_* / manage_het_hieu_luc_* (nhóm ADMIN, VT). Quyền view_vanbanden/
  view_vanbandi (nhóm CV, TP, BGD), cờ is_staff và tài khoản chỉ định (người tạo, người nhận, đơn vị nhận) không đủ.
- Sửa, xóa: chỉ superuser hoặc quyền manage_het_hieu_luc_* (nhóm ADMIN).
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from authorization.models import GroupInfo
from documents.models import HieuLuc, PhamVi, VanBanDen, VanBanDi
from documents.selectors import la_nguoi_xem_duoc, van_ban_xem_duoc
from documents.views import can_delete_document, can_edit_document
from organizations.models import DonVi


def group_of(code):
    return Group.objects.get(pk=GroupInfo.objects.get(ma_nhom_quyen=code).pk)


class VanBanHetHieuLucTest(TestCase):
    def setUp(self):
        User = get_user_model()

        def user_in(username, code=None):
            user = User.objects.create_user(username=username, password="TestOnly12345")
            if code:
                user.groups.add(group_of(code))
            return user

        self.clerk = user_in("hhl_vt", "VT")
        self.admin_group_user = user_in("hhl_admin", "ADMIN")
        self.specialist = user_in("hhl_cv", "CV")
        self.manager = user_in("hhl_tp", "TP")
        self.director = user_in("hhl_bgd", "BGD")
        self.creator = user_in("hhl_tao", "CV")
        self.recipient = user_in("hhl_nhan", "CV")
        self.superuser = User.objects.create_superuser(username="hhl_su", password="TestOnly12345")
        self.no_group = user_in("hhl_khong_nhom")

        self.docs = {}
        for loai, model in (("DEN", VanBanDen), ("DI", VanBanDi)):
            common = {"nam": 2026, "trich_yeu": f"Văn bản {loai}", "nguoi_tao": self.creator, "pham_vi": PhamVi.NOI_BO}
            expired = model.objects.create(
                so_thu_tu=1, so_hieu=f"1/{loai}-HHL", hieu_luc=HieuLuc.HET_HIEU_LUC, **common,
            )
            expired.nguoi_nhan.add(self.recipient)
            active = model.objects.create(
                so_thu_tu=2, so_hieu=f"2/{loai}-CHL", hieu_luc=HieuLuc.CON_HIEU_LUC, **common,
            )
            active.nguoi_nhan.add(self.recipient)
            self.docs[loai] = (expired, active)

    def visible(self, user, loai, doc):
        return van_ban_xem_duoc(user, loai).filter(pk=doc.pk).exists()

    def assert_sees_expired(self, user, expected):
        for loai, (expired, active) in self.docs.items():
            self.assertTrue(self.visible(user, loai, active), (user.username, loai))
            self.assertTrue(la_nguoi_xem_duoc(user, active), (user.username, loai))
            self.assertEqual(self.visible(user, loai, expired), expected, (user.username, loai))
            self.assertEqual(la_nguoi_xem_duoc(user, expired), expected, (user.username, loai))

    def test_view_permission_alone_does_not_show_expired_documents(self):
        for user in (self.specialist, self.manager, self.director, self.no_group):
            self.assert_sees_expired(user, False)

    def test_clerk_admin_group_and_superuser_see_expired_documents(self):
        for user in (self.clerk, self.admin_group_user, self.superuser):
            self.assert_sees_expired(user, True)

    def test_designated_accounts_without_permission_do_not_see_expired_documents(self):
        for user in (self.creator, self.recipient):
            self.assert_sees_expired(user, False)

    def test_staff_flag_alone_does_not_show_or_edit_expired_documents(self):
        self.specialist.is_staff = True
        self.specialist.save(update_fields=["is_staff"])
        self.assert_sees_expired(self.specialist, False)
        expired, _ = self.docs["DEN"]
        self.assertFalse(can_edit_document(self.specialist, expired))
        self.assertFalse(can_delete_document(self.specialist, expired))

    def test_replaced_documents_count_as_expired(self):
        for loai, model in (("DEN", VanBanDen), ("DI", VanBanDi)):
            replaced = model.objects.create(
                nam=2026, so_thu_tu=3, so_hieu=f"3/{loai}-TT", trich_yeu="Đã thay thế", nguoi_tao=self.creator,
                pham_vi=PhamVi.NOI_BO, hieu_luc=HieuLuc.HET_VA_THAY_THE, link_thay_the="https://example.test/moi",
            )
            for user, expected in ((self.specialist, False), (self.creator, False), (self.clerk, True)):
                self.assertEqual(self.visible(user, loai, replaced), expected, (user.username, loai))
                self.assertEqual(la_nguoi_xem_duoc(user, replaced), expected, (user.username, loai))

    def test_hidden_documents_keep_view_permission_rule(self):
        for loai, model in (("DEN", VanBanDen), ("DI", VanBanDi)):
            common = {"nam": 2026, "trich_yeu": "Ẩn", "nguoi_tao": self.creator, "pham_vi": PhamVi.NOI_BO, "hien_thi": False}
            hidden_active = model.objects.create(so_thu_tu=4, so_hieu=f"4/{loai}-AN", hieu_luc=HieuLuc.CON_HIEU_LUC, **common)
            hidden_expired = model.objects.create(so_thu_tu=5, so_hieu=f"5/{loai}-AN", hieu_luc=HieuLuc.HET_HIEU_LUC, **common)
            cases = (
                (self.specialist, hidden_active, True),
                (self.specialist, hidden_expired, False),
                (self.clerk, hidden_expired, True),
                (self.no_group, hidden_active, False),
                (self.no_group, hidden_expired, False),
            )
            for user, doc, expected in cases:
                self.assertEqual(self.visible(user, loai, doc), expected, (user.username, doc.so_hieu))
                self.assertEqual(la_nguoi_xem_duoc(user, doc), expected, (user.username, doc.so_hieu))

    def test_restricted_expired_documents_only_for_permission_holders(self):
        unit = DonVi.objects.order_by("pk").first()
        unit_member = get_user_model().objects.create_user(username="hhl_dv", password="TestOnly12345", don_vi=unit)
        unit_member.groups.add(group_of("CV"))
        for loai, model in (("DEN", VanBanDen), ("DI", VanBanDi)):
            common = {"nam": 2026, "trich_yeu": "Hạn chế", "nguoi_tao": self.creator, "pham_vi": PhamVi.HAN_CHE}
            named_expired = model.objects.create(so_thu_tu=6, so_hieu=f"6/{loai}-HC", hieu_luc=HieuLuc.HET_HIEU_LUC, **common)
            named_expired.nguoi_nhan.add(self.recipient)
            unit_expired = model.objects.create(so_thu_tu=7, so_hieu=f"7/{loai}-HC", hieu_luc=HieuLuc.HET_HIEU_LUC, **common)
            unit_expired.donvinhan.create(donvi_id=unit.pk)
            named_active = model.objects.create(so_thu_tu=8, so_hieu=f"8/{loai}-HC", hieu_luc=HieuLuc.CON_HIEU_LUC, **common)
            named_active.nguoi_nhan.add(self.recipient)
            cases = (
                # Hết hiệu lực: tài khoản chỉ định mất quyền xem; chỉ người có quyền xem.
                (self.creator, named_expired, False),
                (self.recipient, named_expired, False),
                (unit_member, unit_expired, False),
                (self.specialist, named_expired, False),
                (self.clerk, named_expired, True),
                (self.clerk, unit_expired, True),
                (self.admin_group_user, named_expired, True),
                (self.superuser, unit_expired, True),
                # Còn hiệu lực: quy tắc hạn chế giữ nguyên (chỉ tài khoản chỉ định).
                (self.creator, named_active, True),
                (self.recipient, named_active, True),
                (self.clerk, named_active, False),
                (self.admin_group_user, named_active, False),
            )
            for user, doc, expected in cases:
                self.assertEqual(self.visible(user, loai, doc), expected, (user.username, doc.so_hieu))
                self.assertEqual(la_nguoi_xem_duoc(user, doc), expected, (user.username, doc.so_hieu))
            self.assertFalse(can_edit_document(self.creator, named_expired), loai)
            self.assertTrue(can_edit_document(self.admin_group_user, named_expired), loai)
            self.assertTrue(can_edit_document(self.creator, named_active), loai)
            # Xóa văn bản hạn chế hết hiệu lực cũng theo quyền manage_het_hieu_luc_*.
            self.assertFalse(can_delete_document(self.creator, named_expired), loai)
            self.assertFalse(can_delete_document(self.clerk, named_expired), loai)
            self.assertTrue(can_delete_document(self.admin_group_user, named_expired), loai)
            self.assertTrue(can_delete_document(self.superuser, named_expired), loai)
            self.assertFalse(can_delete_document(self.admin_group_user, named_active), loai)

    def test_edit_and_delete_expired_documents_need_manage_permission(self):
        for loai, (expired, active) in self.docs.items():
            for user in (self.admin_group_user, self.superuser):
                self.assertTrue(can_edit_document(user, expired), (user.username, loai))
                self.assertTrue(can_delete_document(user, expired), (user.username, loai))
            for user in (self.clerk, self.specialist, self.manager, self.director, self.creator, self.recipient):
                self.assertFalse(can_edit_document(user, expired), (user.username, loai))
                self.assertFalse(can_delete_document(user, expired), (user.username, loai))
            # Văn bản còn hiệu lực: người tạo vẫn sửa, xóa được như trước.
            self.assertTrue(can_edit_document(self.creator, active), loai)
            self.assertTrue(can_delete_document(self.creator, active), loai)

    def test_manage_permission_granted_by_hand_allows_view_edit_delete(self):
        self.manager.user_permissions.add(Permission.objects.get(codename="manage_het_hieu_luc_vanbanden"))
        manager = get_user_model().objects.get(pk=self.manager.pk)
        expired, _ = self.docs["DEN"]
        client = APIClient()
        client.force_authenticate(user=manager)
        self.assertEqual(client.get(f"/api/documents/den/{expired.pk}/").status_code, status.HTTP_200_OK)
        res = client.patch(f"/api/documents/den/{expired.pk}/", {"trich_yeu": "TP sửa"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        expired.refresh_from_db()
        self.assertEqual(expired.trich_yeu, "TP sửa")
        # Quyền chỉ áp dụng cho văn bản đến.
        expired_di, _ = self.docs["DI"]
        self.assertFalse(la_nguoi_xem_duoc(manager, expired_di))
        self.assertEqual(client.delete(f"/api/documents/den/{expired.pk}/").status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(VanBanDen.objects.filter(pk=expired.pk).exists())

    def test_view_permission_granted_by_hand_shows_but_does_not_allow_edit(self):
        self.specialist.user_permissions.add(Permission.objects.get(codename="view_het_hieu_luc_vanbandi"))
        specialist = get_user_model().objects.get(pk=self.specialist.pk)
        expired_di, _ = self.docs["DI"]
        expired_den, _ = self.docs["DEN"]
        self.assertTrue(la_nguoi_xem_duoc(specialist, expired_di))
        self.assertFalse(la_nguoi_xem_duoc(specialist, expired_den))
        self.assertFalse(can_edit_document(specialist, expired_di))

    def test_api_list_detail_edit_delete(self):
        expired, active = self.docs["DEN"]
        client = APIClient()

        for user in (self.specialist, self.creator, self.recipient):
            client.force_authenticate(user=user)
            res = client.get("/api/documents/den/")
            self.assertEqual(res.status_code, status.HTTP_200_OK)
            ids = {row["id"] for row in res.data.get("results", res.data)}
            self.assertIn(active.pk, ids, user.username)
            self.assertNotIn(expired.pk, ids, user.username)
            self.assertEqual(client.get(f"/api/documents/den/{expired.pk}/").status_code,
                             status.HTTP_403_FORBIDDEN, user.username)
            self.assertEqual(client.patch(f"/api/documents/den/{expired.pk}/", {"trich_yeu": "Sửa"}, format="json")
                             .status_code, status.HTTP_403_FORBIDDEN, user.username)
            self.assertEqual(client.delete(f"/api/documents/den/{expired.pk}/").status_code,
                             status.HTTP_403_FORBIDDEN, user.username)

        client.force_authenticate(user=self.clerk)
        res = client.get("/api/documents/den/")
        ids = {row["id"] for row in res.data.get("results", res.data)}
        self.assertIn(expired.pk, ids)
        self.assertEqual(client.get(f"/api/documents/den/{expired.pk}/").status_code, status.HTTP_200_OK)
        # API chung (giao diện dùng can_edit/can_delete để hiện nút Sửa/Xóa).
        detail = client.get(f"/api/documents/{expired.pk}/?loai=DEN")
        self.assertEqual(detail.status_code, status.HTTP_200_OK)
        self.assertFalse(detail.data["can_edit"])
        self.assertFalse(detail.data["can_delete"])
        self.assertEqual(client.patch(f"/api/documents/den/{expired.pk}/", {"trich_yeu": "VT sửa"}, format="json")
                         .status_code, status.HTTP_403_FORBIDDEN)
        expired.refresh_from_db()
        self.assertEqual(expired.trich_yeu, "Văn bản DEN")

        client.force_authenticate(user=self.admin_group_user)
        detail = client.get(f"/api/documents/{expired.pk}/?loai=DEN")
        self.assertTrue(detail.data["can_edit"])
        self.assertTrue(detail.data["can_delete"])
        res = client.patch(f"/api/documents/den/{expired.pk}/", {"trich_yeu": "ADMIN sửa"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        self.assertEqual(client.delete(f"/api/documents/den/{expired.pk}/").status_code, status.HTTP_204_NO_CONTENT)
