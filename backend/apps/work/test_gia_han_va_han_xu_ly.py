"""Công việc: gia hạn việc quá hạn và hạn xử lý chỉ do người giao việc, quản trị hệ thống đổi (#683)."""
from django.contrib.auth.models import Group, Permission

from authorization.models import GroupInfo
from work.tests import WorkTestBase

URL_DATE_FMT = "%Y-%m-%d"


class DeadlineRulesTests(WorkTestBase):
    def setUp(self):
        super().setUp()
        # Văn thư và chuyên viên trong seed có change_congviec; tài khoản admin theo nhóm ADMIN (không phải superuser).
        change = Permission.objects.get(codename="change_congviec")
        self.member.user_permissions.add(change)
        self.host.user_permissions.add(change)
        self.admin_group_user = self.make_group_user("quantri_nhom", "ADMIN")

    def make_group_user(self, username, group_code):
        from django.contrib.auth import get_user_model

        user = get_user_model().objects.create_user(username, ho_ten=username, don_vi=self.default_unit)
        user.groups.add(Group.objects.get(pk=GroupInfo.objects.get(ma_nhom_quyen=group_code).pk))
        return user

    def patch_due(self, task, offset, **extra):
        return self.client.patch(
            self.task_url(task), {"dueDate": self.days(offset).strftime(URL_DATE_FMT), **extra}, format="multipart"
        )

    # ----- gia hạn việc quá hạn -----

    def test_nguoi_giao_gia_han_viec_qua_han(self):
        task = self.make_task(created_offset=-10, due_offset=-2)
        self.assertEqual(self.status_of(task), "QUA_HAN")
        self.login(self.creator)
        response = self.patch_due(task, 5)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(self.status_of(task), "CHO_XU_LY")
        task.refresh_from_db()
        self.assertEqual(task.due_date, self.days(5))

    def test_quan_tri_nhom_admin_va_superuser_gia_han_duoc(self):
        for user in (self.admin_group_user, self.admin):
            task = self.make_task(created_offset=-10, due_offset=-2, title=f"qua han {user.username}")
            self.login(user)
            response = self.patch_due(task, 4)
            self.assertEqual(response.status_code, 200, (user.username, response.content))
            self.assertNotIn(self.status_of(task), ("QUA_HAN", "CHUA_HOAN_THANH"))

    def test_chu_tri_va_nguoi_tham_gia_khong_gia_han_duoc(self):
        task = self.make_task(created_offset=-10, due_offset=-2)
        for user in (self.host, self.member, self.director):
            self.login(user)
            response = self.patch_due(task, 5)
            self.assertEqual(response.status_code, 403, (user.username, response.content))
        task.refresh_from_db()
        self.assertEqual(task.due_date, self.days(-2))

    def test_gia_han_chi_nhan_hạn_khong_kem_truong_khac(self):
        task = self.make_task(created_offset=-10, due_offset=-2)
        self.login(self.creator)
        response = self.patch_due(task, 5, title="Đổi nội dung khi quá hạn")
        self.assertEqual(response.status_code, 400, response.content)

    def test_gia_han_khong_nhan_ngay_trong_qua_khu(self):
        task = self.make_task(created_offset=-10, due_offset=-5)
        self.login(self.creator)
        self.assertEqual(self.patch_due(task, -1).status_code, 400)

    def test_co_canExtend_chi_dung_cho_nguoi_giao_va_quan_tri_khi_qua_han(self):
        late = self.make_task(created_offset=-10, due_offset=-2, title="qua han")
        normal = self.make_task(title="binh thuong")
        expected = {self.creator: True, self.admin_group_user: True, self.admin: True, self.host: False, self.member: False}
        for user, flag in expected.items():
            self.login(user)
            late_flags = self.client.get(self.task_url(late)).json()["permissions"]
            normal_flags = self.client.get(self.task_url(normal)).json()["permissions"]
            self.assertEqual(late_flags["canExtend"], flag, user.username)
            self.assertFalse(normal_flags["canExtend"], user.username)

    # ----- hạn xử lý ở việc chưa quá hạn -----

    def test_chu_tri_va_nguoi_giu_change_congviec_khong_doi_duoc_han(self):
        task = self.make_task()
        for user in (self.host, self.member):
            self.login(user)
            response = self.patch_due(task, 9)
            self.assertEqual(response.status_code, 403, (user.username, response.content))
        task.refresh_from_db()
        self.assertEqual(task.due_date, self.days(3))

    def test_gui_lai_dung_han_hien_tai_khong_bi_chan(self):
        """Form sửa luôn gửi cả hạn xử lý: không đổi hạn thì người có quyền sửa vẫn sửa được nội dung."""
        task = self.make_task()
        self.login(self.creator)
        response = self.client.patch(
            self.task_url(task),
            {"title": "Nội dung mới", "dueDate": self.days(3).strftime(URL_DATE_FMT)},
            format="multipart",
        )
        self.assertEqual(response.status_code, 200, response.content)

    def test_nguoi_giao_va_quan_tri_doi_duoc_han(self):
        for user in (self.creator, self.admin_group_user, self.admin):
            task = self.make_task(title=f"doi han {user.username}")
            self.login(user)
            response = self.patch_due(task, 8)
            self.assertEqual(response.status_code, 200, (user.username, response.content))

    def test_me_isAdmin_theo_nhom_admin(self):
        self.login(self.admin_group_user)
        self.assertTrue(self.client.get("/api/work/me/").json()["isAdmin"])
        self.login(self.host)
        self.assertFalse(self.client.get("/api/work/me/").json()["isAdmin"])
