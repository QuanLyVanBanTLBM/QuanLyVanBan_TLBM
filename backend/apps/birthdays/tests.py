from datetime import date, timedelta
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Lock
import time
from unittest import skipUnless
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core import mail
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.core.validators import validate_email
from django.db import close_old_connections, connection
from django.test import TestCase, TransactionTestCase, override_settings, skipUnlessDBFeature
from django.utils import timezone
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Position
from birthdays.models import BirthdayEmailLog, BirthdayEmailStatus, BirthdayWish
from birthdays.services import (
    generate_birthday_card_token,
    generate_birthday_email_html,
    generate_birthday_email_text,
    is_birthday_on_date,
    send_automated_birthday_emails,
)
from organizations.models import DonVi, KhoiKhuVuc

Employee = get_user_model()


class BirthdaySystemTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.baseline_active_may_20_ids = set(
            Employee.objects.filter(
                is_active=True, ngay_sinh__month=5, ngay_sinh__day=20
            ).values_list("pk", flat=True)
        )
        self.baseline_public_may_20_count = Employee.objects.filter(
            is_active=True,
            is_public=True,
            ngay_sinh__month=5,
            ngay_sinh__day=20,
        ).count()

        khoi = KhoiKhuVuc.objects.create(ten="Khối Đào tạo")
        latest_stt = DonVi.objects.order_by("-stt_uu_tien").values_list("stt_uu_tien", flat=True).first() or 0
        self.don_vi = DonVi.objects.create(khoi=khoi, stt_uu_tien=latest_stt + 1, ten="Khoa CNTT")
        self.chuc_vu = Position.objects.create(display_order=Position.get_next_display_order(), name="Giảng viên")

        # 1. Nhân viên thường (có quyền view_sinhnhat, send_wish_sinhnhat)
        self.emp_staff = Employee.objects.create_user(
            username="staff1",
            password="password123",
            email="staff1@itc.edu.vn",
            ho_ten="Nguyễn Văn An",
            ngay_sinh=date(1990, 5, 20),
            don_vi=self.don_vi,
            chuc_vu=self.chuc_vu,
            is_active=True,
        )
        perm_view = Permission.objects.get(codename="view_sinhnhat")
        perm_wish = Permission.objects.get(codename="send_wish_sinhnhat")
        self.emp_staff.user_permissions.add(perm_view, perm_wish)

        # 2. Quản trị viên (superuser)
        self.emp_admin = Employee.objects.create_superuser(
            username="admin1",
            password="password123",
            email="admin1@itc.edu.vn",
            ho_ten="Trần Thị Bình",
            ngay_sinh=date(1985, 5, 20),
            don_vi=self.don_vi,
            chuc_vu=self.chuc_vu,
        )

        # 3. Nhân viên sinh 29/02
        self.emp_leap = Employee.objects.create_user(
            username="leapuser",
            password="password123",
            email="leap@itc.edu.vn",
            ho_ten="Lê Nhuận",
            ngay_sinh=date(1996, 2, 29),
            don_vi=self.don_vi,
            chuc_vu=self.chuc_vu,
            is_active=True,
        )

        # 4. User không có quyền
        self.emp_no_perm = Employee.objects.create_user(
            username="noperm",
            password="password123",
            email="noperm@itc.edu.vn",
            ho_ten="Không Có Quyền",
            ngay_sinh=date(1992, 1, 1),
            don_vi=self.don_vi,
            chuc_vu=self.chuc_vu,
            is_active=True,
        )

    def test_leap_year_handling(self):
        """Kiểm tra xử lý ngày 29/02 trong năm nhuận và năm không nhuận."""
        birth_29_feb = date(1996, 2, 29)

        # Năm nhuận 2024: đúng ngày 29/02 là True
        self.assertTrue(is_birthday_on_date(birth_29_feb, date(2024, 2, 29)))

        # Năm không nhuận 2025: quy tắc FEB_28 (mặc định)
        self.assertTrue(is_birthday_on_date(birth_29_feb, date(2025, 2, 28)))
        self.assertFalse(is_birthday_on_date(birth_29_feb, date(2025, 3, 1)))

        # Năm không nhuận 2025: quy tắc MAR_01
        self.assertTrue(is_birthday_on_date(birth_29_feb, date(2025, 3, 1), leap_year_strategy="MAR_01"))

        # Quy tắc SKIP: không tự chuyển ngày trong năm không nhuận.
        self.assertFalse(is_birthday_on_date(birth_29_feb, date(2025, 2, 28), leap_year_strategy="SKIP"))
        self.assertFalse(is_birthday_on_date(birth_29_feb, date(2025, 3, 1), leap_year_strategy="SKIP"))

    def test_calendar_api_privacy_and_rbac(self):
        """Lịch chỉ trả số lượng theo ngày, yêu cầu quyền view_sinhnhat."""
        url = reverse("birthdays:calendar")

        # 401 khi chưa đăng nhập
        response = self.client.get(url, {"month": 5, "year": 2026})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # 403 khi thiếu quyền view_sinhnhat
        self.client.force_authenticate(user=self.emp_no_perm)
        response = self.client.get(url, {"month": 5, "year": 2026})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # 200 khi có quyền view_sinhnhat
        self.client.force_authenticate(user=self.emp_staff)
        response = self.client.get(url, {"month": 5, "year": 2026})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["month"], 5)
        self.assertEqual(data["year"], 2026)
        self.assertEqual(
            data["days"].get("20"), self.baseline_public_may_20_count + 2
        )  # Dữ liệu nền + An và Bình sinh 20/05
        # Đảm bảo không lộ danh sách cá nhân trong lịch tháng
        self.assertNotIn("employees", data)

    def test_day_birthdays_api(self):
        """API chi tiết ngày có phân trang và chỉ trả trường cần thiết, ẩn năm sinh."""
        url = reverse("birthdays:day_birthdays")
        self.client.force_authenticate(user=self.emp_staff)

        response = self.client.get(url, {"month": 5, "day": 20, "year": 2026})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["total"], self.baseline_public_may_20_count + 2)
        employees = data["employees"]
        self.assertEqual(len(employees), min(data["total"], 10))
        emp1 = employees[0]
        self.assertIn("ho_ten", emp1)
        self.assertIn("ngay", emp1)
        self.assertIn("thang", emp1)
        self.assertIn("chuc_vu", emp1)
        self.assertIn("don_vi", emp1)
        # Không công bố năm sinh, email, sdt
        self.assertNotIn("nam", emp1)
        self.assertNotIn("email", emp1)
        self.assertNotIn("sdt", emp1)

    def test_day_birthdays_prioritizes_position_before_unit_across_pages(self):
        high_position = Position.objects.create(
            display_order=Position.get_next_display_order(), name="Chức vụ ưu tiên cao"
        )
        low_position = Position.objects.create(
            display_order=Position.get_next_display_order(), name="Chức vụ ưu tiên thấp"
        )
        later_unit = DonVi.objects.create(
            khoi=self.don_vi.khoi,
            stt_uu_tien=self.don_vi.stt_uu_tien + 1,
            ten="Đơn vị kiểm thử khác",
        )
        low = Employee.objects.create_user(
            username="birthday_lower_position", ho_ten="Nhân viên A",
            ngay_sinh=date(1990, 10, 30), don_vi=self.don_vi, chuc_vu=low_position,
        )
        high = Employee.objects.create_user(
            username="birthday_higher_position", ho_ten="Nhân viên B",
            ngay_sinh=date(1990, 10, 30), don_vi=later_unit, chuc_vu=high_position,
        )
        self.client.force_authenticate(user=self.emp_staff)
        params = {"month": 10, "day": 30, "year": 2026, "page_size": 1}
        first = self.client.get(reverse("birthdays:day_birthdays"), {**params, "page": 1})
        second = self.client.get(reverse("birthdays:day_birthdays"), {**params, "page": 2})
        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(first.json()["employees"][0]["id"], high.id)
        self.assertEqual(second.json()["employees"][0]["id"], low.id)

    def test_birthday_email_logs_api(self):
        """API nhật ký chỉ cho superuser xem và chuẩn hóa trang_thai không phân biệt hoa thường."""
        log = BirthdayEmailLog.objects.create(
            employee=self.emp_staff,
            sent_date=date(2026, 5, 20),
            recipient_email=self.emp_staff.email,
            subject="Chúc mừng sinh nhật",
            trang_thai=BirthdayEmailStatus.SUCCESS,
        )

        url = reverse("birthdays:logs")
        self.client.force_authenticate(user=self.emp_staff)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.json()["error"], "birthdays.messages.permissionDenied")

        self.client.force_authenticate(user=self.emp_admin)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["logs"][0]["employee_name"], self.emp_staff.ho_ten)
        self.assertEqual(data["logs"][0]["trang_thai"], BirthdayEmailStatus.SUCCESS)

        lowercase_status = self.client.get(url, {"trang_thai": "success"})
        self.assertEqual(lowercase_status.status_code, status.HTTP_200_OK)
        self.assertEqual(lowercase_status.json()["total"], 1)

        invalid_status = self.client.get(url, {"trang_thai": "bogus"})
        self.assertEqual(invalid_status.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(invalid_status.json()["error"], "birthdays.messages.invalidStatus")

    def test_public_birthday_card_api_returns_only_signed_card_fields(self):
        token = generate_birthday_card_token(self.emp_staff)

        response = self.client.post(
            reverse("birthdays:birthday_card"),
            {"token": token},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        card = response.json()["card"]
        self.assertEqual(card["employee_name"], self.emp_staff.ho_ten)
        self.assertEqual(card["birthday_date"], "20/05")
        self.assertEqual(card["department"], self.don_vi.ten)
        self.assertEqual(card["position"], self.chuc_vu.name)
        self.assertNotIn("email", card)
        self.assertEqual(response["Cache-Control"], "private, no-store")

    def test_public_birthday_card_api_rejects_invalid_token(self):
        response = self.client.post(
            reverse("birthdays:birthday_card"),
            {"token": "invalid-token"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @override_settings(BIRTHDAY_CARD_BASE_URL="https://example.test/birthday-card.html")
    def test_birthday_email_includes_card_button_and_plain_text_link(self):
        html = generate_birthday_email_html(self.emp_staff)
        text = generate_birthday_email_text(self.emp_staff)

        self.assertIn('href="https://example.test/birthday-card.html#token=', html)
        self.assertIn("Mở thiệp chúc mừng sinh nhật", html)
        self.assertIn("Mở thiệp chúc mừng sinh nhật: https://example.test/birthday-card.html#token=", text)

    @override_settings(BIRTHDAY_CARD_BASE_URL="", SIGNING_FRONTEND_URL="https://example.test")
    def test_birthday_card_url_uses_shared_frontend_url_by_default(self):
        html = generate_birthday_email_html(self.emp_staff)

        self.assertIn('href="https://example.test/birthday-card.html#token=', html)

    def test_birthday_wishes_route_is_not_exposed(self):
        """Issue #23 không cung cấp API lời chúc thủ công; model vẫn được giữ theo DDL."""
        self.client.force_authenticate(user=self.emp_staff)
        response = self.client.post("/api/birthdays/wishes/", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(BirthdayWish._meta.db_table, "birthdays_birthdaywish")

    def test_birthday_status_fields_map_to_staging_columns(self):
        self.assertEqual(BirthdayWish._meta.get_field("trang_thai").column, "trang_thai")
        self.assertEqual(BirthdayEmailLog._meta.get_field("trang_thai").column, "trang_thai")

    def test_private_employees_are_hidden_from_calendar_and_day_api(self):
        Employee.objects.create_user(
            username="private-birthday",
            password="password123",
            email="private@example.test",
            ho_ten="Sinh Nhật Riêng Tư",
            ngay_sinh=date(1990, 5, 20),
            don_vi=self.don_vi,
            chuc_vu=self.chuc_vu,
            is_active=True,
            is_public=False,
        )
        self.client.force_authenticate(user=self.emp_staff)

        calendar_response = self.client.get(reverse("birthdays:calendar"), {"month": 5, "year": 2026})
        self.assertEqual(calendar_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            calendar_response.json()["days"].get("20"),
            self.baseline_public_may_20_count + 2,
        )

        day_response = self.client.get(
            reverse("birthdays:day_birthdays"),
            {"month": 5, "day": 20, "year": 2026},
        )
        self.assertEqual(day_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            day_response.json()["total"], self.baseline_public_may_20_count + 2
        )

    @override_settings(
        MAILERS={"default": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"}},
        DEFAULT_FROM_EMAIL="noreply@example.test",
    )
    def test_retry_log_from_previous_three_days_is_sent(self):
        mail.outbox.clear()
        target_date = date(2026, 5, 20)
        retry_date = target_date - timedelta(days=1)
        retry_log = BirthdayEmailLog.objects.create(
            employee=self.emp_no_perm,
            sent_date=retry_date,
            recipient_email=self.emp_no_perm.email,
            subject="Thư sinh nhật cần gửi lại",
            trang_thai=BirthdayEmailStatus.RETRY,
            retry_count=1,
        )

        results = send_automated_birthday_emails(target_date=target_date, allow_test_email_backend=True)

        retry_log.refresh_from_db()
        self.assertEqual(
            results["total_eligible"], len(self.baseline_active_may_20_ids) + 3
        )
        self.assertEqual(results["sent_count"] + results["skipped_count"], results["total_eligible"])
        self.assertEqual(retry_log.trang_thai, BirthdayEmailStatus.SUCCESS)
        self.assertIn(
            self.emp_no_perm.email,
            [recipient for message in mail.outbox for recipient in message.to],
        )

    @override_settings(
        MAILERS={"default": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"}},
        DEFAULT_FROM_EMAIL="noreply@example.test",
    )
    def test_stale_sending_log_is_failed_without_resend(self):
        mail.outbox.clear()
        target_date = date(2026, 5, 20)
        stale_log = BirthdayEmailLog.objects.create(
            employee=self.emp_staff,
            sent_date=target_date,
            recipient_email=self.emp_staff.email,
            subject="Chúc mừng sinh nhật",
            trang_thai=BirthdayEmailStatus.SENDING,
        )
        future_now = stale_log.updated_at + timedelta(minutes=31)
        with patch("birthdays.services.timezone.now", return_value=future_now):
            results = send_automated_birthday_emails(target_date=target_date, allow_test_email_backend=True)

        stale_log.refresh_from_db()
        self.assertEqual(results["stale_failed_count"], 1)
        self.assertEqual(stale_log.trang_thai, BirthdayEmailStatus.FAILED)
        self.assertTrue(stale_log.error_message.startswith("Kết quả gửi không xác định, cần đối soát."))
        self.assertNotIn(self.emp_staff.email, [message.to[0] for message in mail.outbox])

    @override_settings(
        MAILERS={"default": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"}},
        DEFAULT_FROM_EMAIL="noreply@example.test",
    )
    def test_invalid_email_creates_failed_skipped_log(self):
        mail.outbox.clear()
        self.emp_staff.email = "not-an-email"
        self.emp_staff.save(update_fields=["email"])
        target_date = date(2026, 5, 20)

        results = send_automated_birthday_emails(target_date=target_date, allow_test_email_backend=True)

        log = BirthdayEmailLog.objects.get(employee=self.emp_staff, sent_date=target_date)
        self.assertEqual(log.trang_thai, BirthdayEmailStatus.FAILED)
        self.assertTrue(log.error_message.startswith("Bỏ qua:"))
        self.assertEqual(results["skipped_count"], 1)
        self.assertNotIn("not-an-email", [message.to[0] for message in mail.outbox])

    @override_settings(BRAND_NAME="Tên thương hiệu kiểm thử", ORGANIZATION_NAME="Đơn vị kiểm thử")
    def test_email_uses_configured_branding(self):
        html = generate_birthday_email_html(self.emp_staff)
        self.assertIn("Tên thương hiệu kiểm thử", html)
        self.assertIn("Đơn vị kiểm thử", html)
        self.assertNotIn("Ban Giám hiệu", html)
        self.assertNotIn("Tài liệu Mật", html)

    @override_settings(
        MAILERS={"default": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"}},
        BIRTHDAY_LEAP_DAY_STRATEGY="FEB_28",
        DEFAULT_FROM_EMAIL="noreply@example.test",
    )
    def test_send_automated_birthday_emails_success(self):
        """Gửi email tự động thành công cho nhân viên đến ngày sinh nhật."""
        mail.outbox.clear()
        target_date = date(2026, 5, 20)

        results = send_automated_birthday_emails(
            target_date=target_date,
            allow_test_email_backend=True,
        )

        expected_eligible = len(self.baseline_active_may_20_ids) + 2
        self.assertEqual(results["total_eligible"], expected_eligible)
        self.assertEqual(
            results["sent_count"] + results["skipped_count"] + results["failed_count"],
            expected_eligible,
        )
        self.assertEqual(len(mail.outbox), results["sent_count"])
        sent_recipients = [recipient for message in mail.outbox for recipient in message.to]
        self.assertIn(self.emp_staff.email, sent_recipients)
        self.assertIn(self.emp_admin.email, sent_recipients)

        # Kiểm tra BirthdayEmailLog được tạo đúng trạng thái SUCCESS
        logs = BirthdayEmailLog.objects.filter(sent_date=target_date)
        self.assertEqual(logs.count(), expected_eligible)
        self.assertEqual(
            logs.filter(
                employee__in=(self.emp_staff, self.emp_admin),
                trang_thai=BirthdayEmailStatus.SUCCESS,
            ).count(),
            2,
        )
        for log in logs.filter(employee__in=(self.emp_staff, self.emp_admin)):
            self.assertEqual(log.trang_thai, BirthdayEmailStatus.SUCCESS)
            self.assertIsNotNone(log.sent_at)

        # Chạy lại cùng ngày: Không gửi trùng (anti-duplicate)
        mail.outbox.clear()
        results_rerun = send_automated_birthday_emails(
            target_date=target_date,
            allow_test_email_backend=True,
        )
        self.assertEqual(results_rerun["sent_count"], 0)
        self.assertEqual(results_rerun["skipped_count"], expected_eligible)
        self.assertEqual(len(mail.outbox), 0)

    @override_settings(
        MAILERS={"default": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"}},
        BIRTHDAY_LEAP_DAY_STRATEGY="FEB_28",
        DEFAULT_FROM_EMAIL="noreply@example.test",
    )
    def test_send_birthday_emails_management_command(self):
        """Kiểm tra lệnh quản trị send_birthday_emails qua call_command."""
        mail.outbox.clear()
        call_command(
            "send_birthday_emails",
            "--date=2026-05-20",
            "--allow-locmem",
        )
        sent_recipients = [recipient for message in mail.outbox for recipient in message.to]
        self.assertIn(self.emp_staff.email, sent_recipients)
        self.assertIn(self.emp_admin.email, sent_recipients)


@skipUnlessDBFeature("supports_transactions", "has_select_for_update")
class BirthdayEmailConcurrencyTests(TransactionTestCase):
    """The delivery claim must remain single-writer on databases with row locks."""

    def setUp(self):
        khoi = KhoiKhuVuc.objects.create(ten="Khối kiểm thử")
        latest_stt = DonVi.objects.order_by("-stt_uu_tien").values_list("stt_uu_tien", flat=True).first() or 0
        don_vi = DonVi.objects.create(khoi=khoi, stt_uu_tien=latest_stt + 1, ten="Đơn vị kiểm thử")
        chuc_vu = Position.objects.create(
            display_order=Position.get_next_display_order(), name="Chức vụ kiểm thử"
        )
        self.employee = Employee.objects.create_user(
            username="concurrent-birthday",
            password="password123",
            email="birthday@example.test",
            ho_ten="Cán bộ kiểm thử",
            ngay_sinh=date(1990, 5, 20),
            don_vi=don_vi,
            chuc_vu=chuc_vu,
            is_active=True,
        )

    @override_settings(
        MAILERS={"default": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"}},
        DEFAULT_FROM_EMAIL="noreply@example.test",
    )
    def test_parallel_jobs_send_each_eligible_employee_only_once(self):
        start = Barrier(2)
        call_lock = Lock()
        sent_recipients = []
        eligible_emails = Employee.objects.filter(
            is_active=True, ngay_sinh__month=5, ngay_sinh__day=20
        ).values_list("email", flat=True)
        expected_recipients = []
        for email in eligible_emails:
            if not email:
                continue
            try:
                validate_email(email)
            except ValidationError:
                continue
            expected_recipients.append(email)

        def fake_send_mail(**kwargs):
            with call_lock:
                sent_recipients.extend(kwargs["recipient_list"])
            time.sleep(0.15)
            return 1

        def run_job():
            close_old_connections()
            try:
                start.wait(timeout=5)
                return send_automated_birthday_emails(
                    target_date=date(2026, 5, 20),
                    allow_test_email_backend=True,
                )
            finally:
                close_old_connections()

        with patch("birthdays.services.send_mail", side_effect=fake_send_mail):
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(lambda _: run_job(), range(2)))

        log = BirthdayEmailLog.objects.get(employee=self.employee, sent_date=date(2026, 5, 20))
        self.assertCountEqual(sent_recipients, expected_recipients)
        self.assertEqual(sum(result["sent_count"] for result in results), len(expected_recipients))
        self.assertEqual(log.trang_thai, BirthdayEmailStatus.SUCCESS)


@skipUnless(connection.vendor == "postgresql", "Kiểu ENUM chỉ có trên PostgreSQL")
class BirthdaysReleaseDdlSchemaTests(TestCase):
    """Cột trang_thai tạo từ migration phải dùng đúng kiểu ENUM của release_DDL.sql."""

    def test_trang_thai_uses_ddl_enum_types(self):
        with connection.cursor() as cursor:
            for table, enum_type in [
                ("birthdays_birthdaywish", "birthdaywish_status"),
                ("birthdays_birthdayemaillog", "emaillog_status"),
            ]:
                cursor.execute(
                    "SELECT udt_name FROM information_schema.columns "
                    "WHERE table_schema = current_schema() AND table_name = %s AND column_name = 'trang_thai'",
                    [table],
                )
                self.assertEqual(cursor.fetchone()[0], enum_type)
