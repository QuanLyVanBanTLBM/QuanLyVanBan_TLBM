from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.models import Position
from accounts.selectors import nhan_vien_sinh_ngay
from organizations.models import DonVi, KhoiKhuVuc


class NhanVienSinhNgayTests(TestCase):
    def setUp(self):
        khoi = KhoiKhuVuc.objects.create(ten="Khối Hỗ trợ")
        latest = DonVi.objects.order_by("-stt_uu_tien").values_list("stt_uu_tien", flat=True).first() or 0
        self.don_vi = DonVi.objects.create(khoi=khoi, stt_uu_tien=latest + 1, ten="Phòng Hành chính")
        self.chuc_vu = Position.objects.create(display_order=Position.get_next_display_order(), name="Chuyên viên")

    def _employee(self, username, birth, **extra):
        return get_user_model().objects.create_user(
            username=username, password="password123", don_vi=self.don_vi, chuc_vu=self.chuc_vu,
            ngay_sinh=birth, **extra,
        )

    def test_matches_day_and_month_of_active_employees(self):
        baseline_ids = set(
            get_user_model().objects.filter(
                is_active=True, ngay_sinh__month=6, ngay_sinh__day=15
            ).values_list("pk", flat=True)
        )
        same_day = self._employee("selector_a", date(1990, 6, 15))
        other_year = self._employee("selector_b", date(2001, 6, 15))
        self._employee("selector_c", date(1990, 6, 16))
        self._employee("selector_d", date(1990, 7, 15))
        self._employee("selector_e", date(1990, 6, 15), is_active=False)

        result = nhan_vien_sinh_ngay(date(2026, 6, 15))
        self.assertEqual(
            {employee.pk for employee in result},
            baseline_ids | {same_day.pk, other_year.pk},
        )

    def test_leap_day_birthday_is_not_moved_in_common_years(self):
        User = get_user_model()
        leap_day_baseline_ids = set(
            User.objects.filter(
                is_active=True, ngay_sinh__month=2, ngay_sinh__day=29
            ).values_list("pk", flat=True)
        )
        february_baseline_ids = set(
            User.objects.filter(
                is_active=True, ngay_sinh__month=2, ngay_sinh__day=28
            ).values_list("pk", flat=True)
        )
        march_baseline_ids = set(
            User.objects.filter(
                is_active=True, ngay_sinh__month=3, ngay_sinh__day=1
            ).values_list("pk", flat=True)
        )
        leap_born = self._employee("selector_f", date(2000, 2, 29))

        self.assertEqual(
            {e.pk for e in nhan_vien_sinh_ngay(date(2024, 2, 29))},
            leap_day_baseline_ids | {leap_born.pk},
        )
        self.assertEqual(
            {e.pk for e in nhan_vien_sinh_ngay(date(2026, 2, 28))},
            february_baseline_ids,
        )
        self.assertEqual(
            {e.pk for e in nhan_vien_sinh_ngay(date(2026, 3, 1))},
            march_baseline_ids,
        )

    def test_loads_unit_and_position_without_extra_queries(self):
        employee = self._employee("selector_g", date(1990, 6, 15))

        employees = list(nhan_vien_sinh_ngay(date(2026, 6, 15)))
        with self.assertNumQueries(0):
            result = next(item for item in employees if item.pk == employee.pk)
            self.assertEqual(result.don_vi.ten, "Phòng Hành chính")
            self.assertEqual(result.chuc_vu.name, "Chuyên viên")
