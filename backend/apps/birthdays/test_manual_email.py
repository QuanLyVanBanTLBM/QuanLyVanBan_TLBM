from datetime import date
from smtplib import SMTPDataError, SMTPServerDisconnected
from unittest.mock import patch

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import Employee, Position

from birthdays.models import BirthdayEmailLog, BirthdayEmailStatus, BirthdayEmailTemplate
from birthdays.services import send_automated_birthday_emails
from birthdays.templates_service import LAYOUT_DEFAULTS


@override_settings(
    MAILERS={"default": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"}},
    DEFAULT_FROM_EMAIL="noreply@example.test",
    BIRTHDAY_CARD_BASE_URL="https://example.test/birthday-card.html",
    SIGNING_FRONTEND_URL="https://example.test",
)
class ManualBirthdayEmailTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        position, _ = Position.objects.get_or_create(
            name="Giám đốc Ban", defaults={"display_order": Position.get_next_display_order()},
        )
        cls.admin = Employee.objects.create_superuser(username="birthday-admin", password=None)
        cls.leader = Employee.objects.create_user(
            username="birthday-leader", email="leader@example.test",
            ho_ten="CBNV <A>", chuc_vu=position, chuc_danh="Chức danh riêng",
            ngay_sinh=date(1980, 5, 20),
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)
        self.year = timezone.localdate().year
        self.draft = {
            "employee_id": self.leader.pk, "year": self.year,
            "template_id": "layout:01", "layout": "01",
            "subject": "Mừng sinh nhật {{ employee_name }}",
            "message": "Kính chúc {{ employee_name }} có một ngày vui.",
        }

    def preview(self, draft=None):
        response = self.client.post(reverse("birthdays:manual_preview"), draft or self.draft, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        return response.data

    def send(self, preview, **changes):
        payload = {**self.draft, "preview_token": preview["preview_token"], **changes}
        return self.client.post(reverse("birthdays:manual_send"), payload, format="json")

    def test_catalog_and_each_layout_render_safely_with_matching_card(self):
        catalog = self.client.get(reverse("birthdays:email_templates")).data["templates"]
        self.assertEqual(len(catalog), 10)
        for template in catalog:
            layout = template["layout"]
            with self.subTest(layout=layout):
                preview = self.preview({**self.draft, **LAYOUT_DEFAULTS[layout], "layout": layout, "template_id": template["id"]})
                self.assertIn("CBNV &lt;A&gt;", preview["html"])
                self.assertIn("Chức danh riêng", preview["html"])
                self.assertIn(f"https://example.test/birthday-cards/{layout}.html#token=", preview["card_url"])
                self.assertIn(f'href="{preview["card_url"]}"', preview["html"])
                self.assertIn("🎁 Mở thiệp sinh nhật 3D", preview["html"])
                self.assertNotRegex(
                    preview["html"],
                    r"(?is)<script\b|<iframe\b|<canvas\b|@keyframes|\banimation\s*:|\btransform\s*:",
                )
                self.assertNotIn("Nguyễn Văn An", preview["html"])
        self.assertFalse(BirthdayEmailLog.objects.filter(employee=self.leader).exists())

    @patch("birthdays.manual_views.require_delivery_backend")
    def test_non_leadership_employee_can_preview_and_send_manually(self, _backend):
        position, _ = Position.objects.get_or_create(
            name="Chuyên viên", defaults={"display_order": Position.get_next_display_order()},
        )
        employee = Employee.objects.create_user(
            username="birthday-staff", email="staff@example.test",
            ho_ten="Nhân viên thử", chuc_vu=position, ngay_sinh=date(1985, 5, 20),
        )
        draft = {**self.draft, "employee_id": employee.pk}

        recipient_response = self.client.get(
            reverse("birthdays:manual_recipients"), {"q": "Nhân viên thử"},
        )
        self.assertEqual(recipient_response.status_code, 200)
        self.assertEqual([item["id"] for item in recipient_response.data["recipients"]], [employee.pk])

        preview_response = self.client.post(
            reverse("birthdays:manual_preview"), draft, format="json",
        )
        self.assertEqual(preview_response.status_code, 200, preview_response.data)

        send_response = self.client.post(
            reverse("birthdays:manual_send"),
            {**draft, "preview_token": preview_response.data["preview_token"]},
            format="json",
        )
        self.assertEqual(send_response.status_code, 200, send_response.data)
        self.assertEqual(send_response.data["log"]["trang_thai"], BirthdayEmailStatus.SUCCESS)
        self.assertEqual(send_response.data["log"]["delivery_source"], "MANUAL")
        self.assertEqual(send_response.data["log"]["smtp_response_code"], "250 OK")
        self.assertEqual(mail.outbox[-1].to, [employee.email])

    @patch("birthdays.manual_views.require_delivery_backend")
    def test_preview_is_bound_to_content_and_send_is_unique(self, _backend):
        preview = self.preview()
        self.assertEqual(self.send(preview, message="Nội dung bị đổi.").status_code, 409)
        response = self.send(preview)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["log"]["trang_thai"], BirthdayEmailStatus.SUCCESS)
        self.assertEqual(self.send(preview).status_code, 409)
        log = BirthdayEmailLog.objects.get(employee=self.leader)
        self.assertEqual(log.sent_date, date(self.year, 5, 20))
        self.assertEqual(log.last_operator, self.admin.username)
        self.assertEqual(log.delivery_source, "MANUAL")
        self.assertEqual(log.delivery_snapshot["html"], mail.outbox[0].alternatives[0].content)
        self.assertEqual(len(mail.outbox), 1)
        Employee.objects.filter(pk=self.leader.pk).update(ngay_sinh=date(1980, 5, 21))
        self.assertEqual(self.send(self.preview()).status_code, 409)

    @patch("birthdays.manual_views.require_delivery_backend")
    def test_retry_preserves_snapshot_and_checks_corrected_recipient(self, _backend):
        preview = self.preview()
        with patch("birthdays.services.send_mail", side_effect=SMTPDataError(550, b"Rejected")):
            response = self.send(preview)
        log = BirthdayEmailLog.objects.get(employee=self.leader)
        self.assertTrue(response.data["log"]["can_retry"])
        Employee.objects.filter(pk=self.leader.pk).update(email="corrected@example.test", ho_ten="Tên đã đổi")
        url = reverse("birthdays:retry_email", args=[log.pk])
        self.assertEqual(self.client.post(url, {"recipient": log.recipient_email}, format="json").status_code, 409)
        self.assertEqual(self.client.post(url, {"recipient": "corrected@example.test"}, format="json").status_code, 200)
        self.assertEqual(mail.outbox[0].to, ["corrected@example.test"])
        self.assertEqual(mail.outbox[0].body, log.delivery_snapshot["text"])

    @patch("birthdays.manual_views.require_delivery_backend")
    def test_inactive_employee_retry_is_hidden_and_rejected(self, _backend):
        preview = self.preview()
        with patch("birthdays.services.send_mail", side_effect=SMTPDataError(550, b"Rejected")):
            response = self.send(preview)
            log_id = response.data["log"]["id"]
            Employee.objects.filter(pk=self.leader.pk).update(is_active=False)

            logs_response = self.client.get(
                reverse("birthdays:logs"),
                {"date": timezone.localdate().isoformat()},
            )
            logged = next(row for row in logs_response.data["logs"] if row["id"] == log_id)
            self.assertFalse(logged["can_retry"])
            self.assertEqual(logged["retry_block_reason"], "inactive")

            retry_response = self.client.post(
                reverse("birthdays:retry_email", args=[log_id]),
                {"recipient": self.leader.email},
                format="json",
            )
            self.assertEqual(retry_response.status_code, 404)

    @patch("birthdays.manual_views.require_delivery_backend")
    def test_unconfirmed_smtp_result_blocks_both_send_and_retry(self, _backend):
        preview = self.preview()
        with patch("birthdays.services.send_mail", side_effect=SMTPServerDisconnected):
            response = self.send(preview)
        log = response.data["log"]
        self.assertTrue(log["delivery_uncertain"])
        self.assertFalse(log["can_retry"])
        self.assertEqual(self.send(preview).status_code, 409)
        url = reverse("birthdays:retry_email", args=[log["id"]])
        self.assertEqual(self.client.post(url, {"recipient": self.leader.email}, format="json").status_code, 409)

    def test_automatic_delivery_skips_leaders(self):
        send_automated_birthday_emails(date(self.year, 5, 20), allow_test_email_backend=True)
        self.assertFalse(BirthdayEmailLog.objects.filter(employee=self.leader).exists())

    @patch("birthdays.draft_ai.complete_draft")
    def test_ai_draft_requires_admin_and_explicit_save(self, complete):
        url = reverse("birthdays:ai_email_draft")
        self.client.force_authenticate(user=self.leader)
        self.assertEqual(self.client.post(url, {"instruction": "Mẫu trang trọng"}, format="json").status_code, 403)
        complete.assert_not_called()
        self.client.force_authenticate(user=self.admin)
        complete.return_value = '{"layout":"02","subject":"Chúc mừng","message":"Kính gửi {{ employee_name }}"}'
        response = self.client.post(url, {"instruction": "Mẫu trang trọng"}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertNotIn(self.leader.email, complete.call_args.args[0])
        self.assertFalse(BirthdayEmailTemplate.objects.exists())
        payload = {**response.data["draft"], "name": "Mẫu trang trọng"}
        response = self.client.post(reverse("birthdays:email_templates"), payload, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(BirthdayEmailTemplate.objects.get().layout, "02")
