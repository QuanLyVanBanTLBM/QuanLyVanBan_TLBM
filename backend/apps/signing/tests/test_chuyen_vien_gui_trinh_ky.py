"""
Issue #226: tài khoản nhóm Chuyên viên (quyền lấy từ seed RBAC, không gán riêng) tự gửi hồ sơ mình tạo;
người không có send_trinhky và người không phải người tạo vẫn bị chặn.
"""

import importlib
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import connection

from .helpers import cap_quyen
from .test_trinh_ky_phase7 import TrinhKyBase

User = get_user_model()


class ChuyenVienGuiTrinhKyTests(TrinhKyBase):
    def setUp(self):
        super().setUp()
        importlib.import_module("authorization.migrations.0002_rbac_standard_data").seed_rbac(
            None, SimpleNamespace(connection=connection)
        )

    def thanh_vien_cv(self, username):
        user = User.objects.create_user(username)
        user.groups.add(Group.objects.get(name="Chuyên viên"))
        return self.client_cua(User.objects.get(pk=user.pk))

    def test_chuyen_vien_creates_and_sends_own_draft(self):
        c = self.thanh_vien_cv("cv_tao")
        r = self.tao_nhap(client=c)
        self.assertEqual(r.status_code, 201, r.data)
        r = self.gui(r.data["id"], client=c)
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data["trang_thai"], "CHO_KY")

    def test_chuyen_vien_cannot_send_draft_of_other_creator(self):
        pk = self.tao_nhap(client=self.thanh_vien_cv("cv_tao")).data["id"]
        r = self.gui(pk, client=self.thanh_vien_cv("cv_khac"))
        self.assertIn(r.status_code, (403, 404))
        self.assertNotEqual(r.data.get("trang_thai"), "CHO_KY")

    def test_account_without_send_permission_is_still_blocked(self):
        user = User.objects.create_user("chi_tao_ho_so")
        cap_quyen(user, "add_trinhky", "view_vanbandi")
        c = self.client_cua(User.objects.get(pk=user.pk))
        pk = self.tao_nhap(client=c).data["id"]
        r = self.gui(pk, client=c)
        self.assertEqual((r.status_code, r.data["fields"]), (403, {"quyen": ["send_trinhky"]}))
