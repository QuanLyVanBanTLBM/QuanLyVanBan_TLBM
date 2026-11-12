"""Công việc: người nhận việc (chủ trì, tham gia) không sửa, xóa việc được giao, kể cả khi có change/delete_congviec."""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission

from authorization.models import GroupInfo
from work.models import Task
from work.tests import WorkTestBase, pdf_file


class RecipientReadOnlyTests(WorkTestBase):
    def setUp(self):
        super().setUp()
        perms = Permission.objects.filter(
            codename__in=("change_congviec", "delete_congviec", "view_all_congviec")
        )
        # Chủ trì, chỉ đạo, tham gia đều được cấp quyền toàn cục Sửa/Xóa để chứng minh quyền này không mở cho người nhận.
        for user in (self.host, self.director, self.member):
            user.user_permissions.add(*perms)
        self.reviewer = get_user_model().objects.create_user("nguoi_xet", ho_ten="Người xét", don_vi=self.default_unit)
        self.reviewer.user_permissions.add(*perms)
        self.admin_group_user = get_user_model().objects.create_user("qtht_nhom", ho_ten="QTHT", don_vi=self.default_unit)
        self.admin_group_user.groups.add(Group.objects.get(pk=GroupInfo.objects.get(ma_nhom_quyen="ADMIN").pk))

    def patch_title(self, task, user):
        self.login(user)
        return self.client.patch(self.task_url(task), {"title": "Sửa nội dung"}, format="multipart")

    def test_nguoi_nhan_co_change_congviec_khong_sua_duoc(self):
        task = self.make_task()
        for user in (self.host, self.member):
            self.assertEqual(self.patch_title(task, user).status_code, 403, user.username)
        task.refresh_from_db()
        self.assertEqual(task.title, "Công việc thử")

    def test_nguoi_nhan_co_delete_congviec_khong_xoa_duoc(self):
        task = self.make_task()
        for user in (self.host, self.member):
            self.login(user)
            self.assertEqual(self.client.delete(self.task_url(task)).status_code, 403, user.username)
        self.assertTrue(Task.objects.filter(pk=task.pk).exists())

    def test_co_canEdit_canDelete_false_voi_nguoi_nhan(self):
        task = self.make_task()
        for user in (self.host, self.member):
            self.login(user)
            flags = self.client.get(self.task_url(task)).json()["permissions"]
            self.assertFalse(flags["canEdit"], user.username)
            self.assertFalse(flags["canDelete"], user.username)

    def test_nguoi_co_quyen_khong_phai_nguoi_nhan_van_sua_duoc(self):
        for user in (self.director, self.reviewer, self.admin_group_user, self.creator):
            task = self.make_task(title=f"việc của {user.username}")
            self.assertEqual(self.patch_title(task, user).status_code, 200, user.username)
            self.login(user)
            flags = self.client.get(self.task_url(task)).json()["permissions"]
            self.assertTrue(flags["canEdit"], user.username)

    def test_nguoi_co_delete_congviec_khong_phai_nguoi_nhan_xoa_duoc(self):
        for user in (self.reviewer, self.admin_group_user, self.creator):  # creator được cấp delete_congviec ở dữ liệu nền
            task = self.make_task(title=f"xóa {user.username}")
            self.login(user)
            self.assertEqual(self.client.delete(self.task_url(task)).status_code, 204, user.username)

    def test_nguoi_nhan_van_nop_bang_chung_va_ghi_y_kien(self):
        task = self.make_task()
        for user in (self.host, self.member):
            self.login(user)
            res = self.client.post(
                self.task_url(task, "comments/"), {"content": "kết quả", "files": [pdf_file()]}, format="multipart"
            )
            self.assertEqual(res.status_code, 201, (user.username, res.content))
            flags = self.client.get(self.task_url(task)).json()["permissions"]
            self.assertTrue(flags["canComment"], user.username)

    def test_nguoi_nhan_khong_gia_han_khong_doi_han(self):
        """Không mâu thuẫn với gia hạn: chỉ người giao và quản trị đổi hạn; người nhận không."""
        late = self.make_task(created_offset=-10, due_offset=-2)
        for user in (self.host, self.member):
            self.login(user)
            res = self.client.patch(self.task_url(late), {"dueDate": self.days(5).isoformat()}, format="multipart")
            self.assertEqual(res.status_code, 403, user.username)


class PermissionOnlyTests(WorkTestBase):
    """Sửa, xóa, duyệt chỉ theo mã quyền hoặc quản trị hệ thống; người giao không có quyền thì không sửa, không xóa."""

    def setUp(self):
        super().setUp()
        # Giống Ban Giám đốc ở seed: được giao việc (add_congviec) nhưng không có change/delete_congviec.
        self.boss = get_user_model().objects.create_user("lanh_dao", ho_ten="Lãnh đạo", don_vi=self.default_unit)
        self.boss.user_permissions.add(Permission.objects.get(codename="add_congviec"))

    def make_boss_task(self, **extra):
        task = self.make_task(**extra)
        Task.objects.filter(pk=task.pk).update(created_by=self.boss)
        task.refresh_from_db()
        return task

    def test_nguoi_giao_khong_co_change_congviec_khong_sua_khong_xoa(self):
        task = self.make_boss_task()
        self.login(self.boss)
        res = self.client.patch(self.task_url(task), {"title": "Sửa"}, format="multipart")
        self.assertEqual(res.status_code, 403, res.content)
        self.assertEqual(self.client.delete(self.task_url(task)).status_code, 403)
        flags = self.client.get(self.task_url(task)).json()["permissions"]
        self.assertFalse(flags["canEdit"])
        self.assertFalse(flags["canDelete"])

    def test_nguoi_giao_co_change_congviec_nhung_khong_co_delete_congviec_chi_sua_khong_xoa(self):
        manager = get_user_model().objects.create_user("truong_phong", ho_ten="TP", don_vi=self.default_unit)
        manager.user_permissions.add(Permission.objects.get(codename="change_congviec"))
        task = self.make_task()
        Task.objects.filter(pk=task.pk).update(created_by=manager)
        self.login(manager)
        self.assertEqual(self.client.patch(self.task_url(task), {"title": "Sửa"}, format="multipart").status_code, 200)
        self.assertEqual(self.client.delete(self.task_url(task)).status_code, 403)
        flags = self.client.get(self.task_url(task)).json()["permissions"]
        self.assertTrue(flags["canEdit"])
        self.assertFalse(flags["canDelete"])

    def test_nguoi_co_delete_congviec_xoa_duoc(self):
        task = self.make_boss_task()
        self.boss.user_permissions.add(*Permission.objects.filter(codename__in=("delete_congviec",)))
        self.login(self.boss)
        self.assertEqual(self.client.delete(self.task_url(task)).status_code, 204)

    def test_chu_tri_va_chi_dao_khong_co_approve_congviec_khong_duyet(self):
        task = self.make_task(first_opened_at=None)
        self.add_evidence(task)
        for user in (self.host, self.director):
            self.login(user)
            res = self.client.post(self.task_url(task, "approve/"))
            self.assertEqual(res.status_code, 403, user.username)
            flags = self.client.get(self.task_url(task)).json()["permissions"]
            self.assertFalse(flags["canApprove"], user.username)
            self.assertFalse(flags["canReview"], user.username)

    def test_chi_nguoi_co_approve_congviec_hoac_quan_tri_duyet_duoc(self):
        task = self.make_task()
        self.add_evidence(task)
        admin_group = get_user_model().objects.create_user("qtht_duyet", ho_ten="QTHT", don_vi=self.default_unit)
        admin_group.groups.add(Group.objects.get(pk=GroupInfo.objects.get(ma_nhom_quyen="ADMIN").pk))
        self.login(self.creator)  # có approve_congviec
        self.assertEqual(self.client.post(self.task_url(task, "approve/")).status_code, 200)
        self.login(admin_group)
        self.assertEqual(self.client.post(self.task_url(task, "unapprove/")).status_code, 200)
