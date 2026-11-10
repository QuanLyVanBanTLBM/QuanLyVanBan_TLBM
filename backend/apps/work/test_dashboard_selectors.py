from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from accounts.models import Position
from organizations.models import DonVi, KhoiKhuVuc
from work.models import Task, TaskStatus
from work.selectors import cong_viec_xem_duoc


class CongViecXemDuocTests(TestCase):
    def setUp(self):
        khoi = KhoiKhuVuc.objects.create(ten="Khối Hỗ trợ")
        latest = DonVi.objects.order_by("-stt_uu_tien").values_list("stt_uu_tien", flat=True).first() or 0
        don_vi = DonVi.objects.create(khoi=khoi, stt_uu_tien=latest + 1, ten="Phòng Hành chính")
        chuc_vu = Position.objects.create(display_order=Position.get_next_display_order(), name="Chuyên viên")
        users = get_user_model().objects
        self.owner = users.create_user(username="selector_owner", password="password123", don_vi=don_vi, chuc_vu=chuc_vu)
        self.other = users.create_user(username="selector_other", password="password123", don_vi=don_vi, chuc_vu=chuc_vu)
        self.admin = users.create_superuser(username="selector_admin", password="password123", don_vi=don_vi, chuc_vu=chuc_vu)
        self.today = timezone.localdate()

    def _task(self, title, creator, due_date=None, **extra):
        return Task.objects.create(
            title=title, created_by=creator, due_date=due_date or self.today, requirement="Xử lý", **extra
        )

    def test_matches_task_visibility_rules(self):
        own = self._task("own", self.owner)
        hidden = self._task("hidden", self.owner, is_public=False)
        foreign = self._task("foreign", self.other)

        self.assertEqual({task.pk for task in cong_viec_xem_duoc(self.owner)}, {own.pk, hidden.pk})
        self.assertEqual({task.pk for task in cong_viec_xem_duoc(self.other)}, {foreign.pk})
        self.assertEqual(
            {task.pk for task in cong_viec_xem_duoc(self.admin)}, {own.pk, hidden.pk, foreign.pk}
        )
        self.assertEqual(list(cong_viec_xem_duoc(None)), [])

    def test_status_is_computed_relative_to_today(self):
        task = self._task("due", self.owner, due_date=self.today)

        self.assertEqual(cong_viec_xem_duoc(self.owner, self.today).get(pk=task.pk).status, TaskStatus.CHO_XU_LY)
        later = self.today + timedelta(days=1)
        self.assertEqual(cong_viec_xem_duoc(self.owner, later).get(pk=task.pk).status, TaskStatus.QUA_HAN)

    def test_status_defaults_to_local_today(self):
        task = self._task("due", self.owner, due_date=self.today)

        self.assertEqual(cong_viec_xem_duoc(self.owner).get(pk=task.pk).status, TaskStatus.CHO_XU_LY)
