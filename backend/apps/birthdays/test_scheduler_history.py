from datetime import date, datetime, timedelta
from io import StringIO
from smtplib import SMTPDataError
from unittest.mock import patch

from django.core import mail
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import Employee
from birthdays.models import BirthdayEmailLog, BirthdaySchedulerRun, BirthdaySchedulerStatus
from birthdays.scheduler import VIETNAM_TIME_ZONE


@override_settings(
    MAILERS={"default": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"}},
    DEFAULT_FROM_EMAIL="birthday@example.test",
    BIRTHDAY_CARD_BASE_URL="https://example.test/birthday-card.html",
    SIGNING_FRONTEND_URL="https://example.test",
)
class BirthdaySchedulerHistoryTests(TestCase):
    processing_date = date(2040, 2, 29)

    @classmethod
    def setUpTestData(cls):
        cls.admin = Employee.objects.create_superuser(username="scheduler-admin", password=None)

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

    def history(self):
        response = self.client.get(reverse("birthdays:logs"), {"date": self.processing_date.isoformat()})
        self.assertEqual(response.status_code, 200, response.data)
        return response.data["scheduler"]

    def run_slot(self, run_id, slot, attempt=1, allow_locmem=True):
        call_command(
            "send_birthday_emails",
            date=self.processing_date.isoformat(),
            trigger_source="RECOVERY" if slot == "07:37" else "SCHEDULED",
            scheduled_slot=slot,
            github_run_id=str(run_id),
            github_run_attempt=str(attempt),
            allow_locmem=allow_locmem,
            stdout=StringIO(),
            stderr=StringIO(),
        )

    def test_zero_candidates_records_actual_times_and_deduplicates_only_same_attempt(self):
        actual = datetime(2040, 2, 29, 7, 2, 15, tzinfo=VIETNAM_TIME_ZONE)
        with patch("birthdays.scheduler.timezone.now", return_value=actual):
            self.run_slot(101, "07:00")
            self.run_slot(101, "07:00")
            self.run_slot(101, "07:00", attempt=2)
        self.assertEqual(BirthdaySchedulerRun.objects.count(), 2)
        run = BirthdaySchedulerRun.objects.get(execution_id="github:101:1")
        self.assertEqual(run.started_at, actual)
        self.assertGreaterEqual(run.ended_at, run.started_at)
        self.assertEqual(run.status, BirthdaySchedulerStatus.SUCCESS)
        self.assertEqual((run.total_eligible, run.sent_count, run.failed_count, run.skipped_count, run.retry_count), (0, 0, 0, 0, 0))
        history = self.history()
        self.assertEqual(history["slots"][0]["status"], "SUCCESS")
        self.assertEqual(history["runs"][0]["started_at"], actual.isoformat())

    def test_missing_and_upcoming_slots_are_independent_of_delivery_logs(self):
        employee = Employee.objects.create_user(username="scheduler-employee", ngay_sinh=date(2000, 2, 29))
        BirthdayEmailLog.objects.create(
            employee=employee, sent_date=self.processing_date,
            recipient_email="employee@example.test", subject="Birthday", trang_thai="SUCCESS",
        )
        actual = datetime(2040, 2, 29, 7, 15, tzinfo=VIETNAM_TIME_ZONE)
        with patch("birthdays.scheduler.timezone.now", return_value=actual):
            history = self.history()
        self.assertEqual([slot["status"] for slot in history["slots"]], ["MISSING", "UPCOMING"])
        self.assertEqual(history["runs"], [])

    def test_failed_and_interrupted_runs_have_distinct_statuses(self):
        actual = datetime(2040, 2, 29, 7, 2, tzinfo=VIETNAM_TIME_ZONE)
        with patch("birthdays.scheduler.timezone.now", return_value=actual):
            with self.assertRaises(CommandError):
                self.run_slot(201, "07:00", allow_locmem=False)
        failed = BirthdaySchedulerRun.objects.get(execution_id="github:201:1")
        self.assertEqual(failed.status, BirthdaySchedulerStatus.FAILED)
        self.assertIsNotNone(failed.ended_at)
        self.assertIsNotNone(failed.error_reason)
        with patch("birthdays.management.commands.send_birthday_emails.send_automated_birthday_emails", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.run_slot(202, "07:37")
        self.assertEqual(BirthdaySchedulerRun.objects.get(execution_id="github:202:1").status, "UNKNOWN")
        abandoned = BirthdaySchedulerRun.objects.create(
            execution_id="github:203:1", processing_date=self.processing_date, trigger_source="RECOVERY",
            scheduled_slot="07:37", started_at=actual + timedelta(minutes=36), status="RUNNING",
        )
        for elapsed, expected in ((30, "RUNNING"), (150, "UNKNOWN")):
            with self.subTest(status=expected):
                with patch("birthdays.scheduler.timezone.now", return_value=abandoned.started_at + timedelta(minutes=elapsed)):
                    history = self.history()
                self.assertEqual(history["slots"][1]["status"], expected)
                observed = next(run for run in history["runs"] if run["id"] == abandoned.pk)
                self.assertIsNone(observed["ended_at"])
                self.assertIsNone(observed["sent_count"])

    def test_fallback_skips_accepted_primary_with_resend_history_and_catches_up(self):
        primary = Employee.objects.create_user(
            username="primary-recipient", email="primary@example.test", ngay_sinh=date(2000, 2, 29),
        )
        self.run_slot(301, "07:00")
        with patch("birthdays.manual_views.require_delivery_backend"):
            response = self.client.post(reverse("birthdays:resend_email"), {
                "employee_id": primary.pk, "sent_date": self.processing_date.isoformat(),
                "recipient": primary.email, "request_id": "ac9df692-3552-4e5a-a99b-e0435d6907ce",
            }, format="json")
        self.assertEqual(response.data["log"]["trang_thai"], "SUCCESS", response.data)
        Employee.objects.create_user(
            username="catchup-recipient", email="catchup@example.test", ngay_sinh=date(2000, 2, 29),
        )
        self.run_slot(302, "07:37")
        run = BirthdaySchedulerRun.objects.get(execution_id="github:302:1")
        self.assertEqual((run.total_eligible, run.sent_count, run.failed_count, run.skipped_count), (2, 1, 0, 1))
        self.assertEqual([item.to[0] for item in mail.outbox], [primary.email, primary.email, "catchup@example.test"])
        self.assertCountEqual(
            BirthdayEmailLog.objects.filter(employee=primary).values_list("delivery_source", flat=True),
            ["AUTO", "MANUAL_RESEND"],
        )

    def test_fallback_retries_a_confirmed_smtp_rejection_and_records_the_retry(self):
        employee = Employee.objects.create_user(
            username="retry-recipient", email="retry@example.test", ngay_sinh=date(2000, 2, 29),
        )
        with patch("birthdays.services.send_mail", side_effect=SMTPDataError(451, b"Try later")):
            with self.assertRaises(CommandError):
                self.run_slot(401, "07:00")
        primary = BirthdaySchedulerRun.objects.get(execution_id="github:401:1")
        self.assertEqual((primary.status, primary.failed_count), ("FAILED", 1))
        log = BirthdayEmailLog.objects.get(employee=employee)
        self.assertEqual((log.trang_thai, log.smtp_response_code), ("RETRY", "451"))

        self.run_slot(402, "07:37")
        fallback = BirthdaySchedulerRun.objects.get(execution_id="github:402:1")
        self.assertEqual((fallback.status, fallback.sent_count, fallback.retry_count), ("SUCCESS", 1, 1))
        log.refresh_from_db()
        self.assertEqual((log.trang_thai, log.delivery_snapshot["trigger_source"]), ("SUCCESS", "RETRY"))
        self.assertEqual([message.to for message in mail.outbox], [[employee.email]])
