from datetime import date, timedelta
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Lock
import time
from unittest import skipUnless
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core import mail
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import close_old_connections, connection
from django.test import TestCase, TransactionTestCase, override_settings, skipUnlessDBFeature
from django.utils import timezone
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Position
from birthdays.models import BirthdayEmailLog, BirthdayEmailStatus, BirthdayWish
from birthdays.services import generate_birthday_email_html, is_birthday_on_date, send_automated_birthday_emails
from organizations.models import DonVi, KhoiKhuVuc

Employee = get_user_model()


class BirthdaySystemTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        khoi = KhoiKhuVuc.objects.create(ten="Khối Đào tạo")
        self.don_vi = DonVi.objects.create(khoi=khoi, stt_uu_tien=1, ten="Khoa CNTT")
        self.chuc_vu = Position.objects.create(display_order=1, name="Giảng viên")

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
        self.assertEqual(data["days"].get("20"), 2)  # An & Bình sinh 20/05
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
        self.assertEqual(data["total"], 2)
        employees = data["employees"]
        self.assertEqual(len(employees), 2)
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
        self.assertEqual(calendar_response.json()["days"].get("20"), 2)

        day_response = self.client.get(
            reverse("birthdays:day_birthdays"),
            {"month": 5, "day": 20, "year": 2026},
        )
        self.assertEqual(day_response.status_code, status.HTTP_200_OK)
        self.assertEqual(day_response.json()["total"], 2)

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
        self.assertEqual(results["total_eligible"], 3)
        self.assertEqual(results["sent_count"], 3)
        self.assertEqual(retry_log.trang_thai, BirthdayEmailStatus.SUCCESS)
        self.assertEqual(len(mail.outbox), 3)

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
        with connection.cursor() as cursor:
            # DB dựng từ release_DDL.sql có trigger BEFORE UPDATE luôn ghi đè updated_at bằng now():
            # tạm bỏ qua trigger (chỉ trong giao dịch của test) để lùi giờ updated_at khi dựng dữ liệu
            # "bản ghi SENDING quá hạn".
            if connection.vendor == "postgresql":
                cursor.execute("SET LOCAL session_replication_role = replica")
            BirthdayEmailLog.objects.filter(pk=stale_log.pk).update(
                updated_at=timezone.now() - timedelta(minutes=31),
            )
            if connection.vendor == "postgresql":
                cursor.execute("SET LOCAL session_replication_role = DEFAULT")

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

        self.assertEqual(results["total_eligible"], 2)  # An và Bình
        self.assertEqual(results["sent_count"], 2)
        self.assertEqual(results["failed_count"], 0)
        self.assertEqual(len(mail.outbox), 2)

        # Kiểm tra BirthdayEmailLog được tạo đúng trạng thái SUCCESS
        logs = BirthdayEmailLog.objects.filter(sent_date=target_date)
        self.assertEqual(logs.count(), 2)
        for log in logs:
            self.assertEqual(log.trang_thai, BirthdayEmailStatus.SUCCESS)
            self.assertIsNotNone(log.sent_at)

        # Chạy lại cùng ngày: Không gửi trùng (anti-duplicate)
        mail.outbox.clear()
        results_rerun = send_automated_birthday_emails(
            target_date=target_date,
            allow_test_email_backend=True,
        )
        self.assertEqual(results_rerun["sent_count"], 0)
        self.assertEqual(results_rerun["skipped_count"], 2)
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
        self.assertEqual(len(mail.outbox), 2)


@skipUnlessDBFeature("supports_transactions", "has_select_for_update")
class BirthdayEmailConcurrencyTests(TransactionTestCase):
    """The delivery claim must remain single-writer on databases with row locks."""

    reset_sequences = True

    def setUp(self):
        khoi = KhoiKhuVuc.objects.create(ten="Khối kiểm thử")
        don_vi = DonVi.objects.create(khoi=khoi, stt_uu_tien=1, ten="Đơn vị kiểm thử")
        chuc_vu = Position.objects.create(display_order=1, name="Chức vụ kiểm thử")
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
    def test_parallel_jobs_send_only_one_message(self):
        start = Barrier(2)
        call_lock = Lock()
        send_call_count = 0

        def fake_send_mail(**kwargs):
            nonlocal send_call_count
            with call_lock:
                send_call_count += 1
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
        self.assertEqual(send_call_count, 1)
        self.assertEqual(sum(result["sent_count"] for result in results), 1)
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
