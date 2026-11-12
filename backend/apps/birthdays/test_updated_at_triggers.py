from datetime import date, timedelta
from importlib import import_module
from types import SimpleNamespace
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.utils import timezone

from birthdays.models import BirthdayEmailLog, BirthdayWish


class BirthdayUpdatedAtTriggerTest(TestCase):
    def setUp(self):
        self.employee = get_user_model().objects.create_user(
            username=f"birthday_{uuid4().hex[:12]}",
            email=f"{uuid4().hex[:12]}@example.test",
            ho_ten="Birthday trigger test",
        )
        self.wish = BirthdayWish.objects.create(
            employee=self.employee,
            sender_name="Sender",
            message="Happy birthday",
        )
        self.email_log = BirthdayEmailLog.objects.create(
            employee=self.employee,
            sent_date=date(2026, 10, 20),
            recipient_email="recipient@example.test",
            subject="Birthday",
        )

    def test_raw_wish_update_refreshes_updated_at(self):
        old = timezone.now() - timedelta(days=2)
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE birthdays_birthdaywish SET updated_at = %s WHERE id = %s",
                [old, self.wish.pk],
            )
            cursor.execute(
                "UPDATE birthdays_birthdaywish SET likes_count = likes_count + 1 WHERE id = %s",
                [self.wish.pk],
            )
        self.assertGreater(BirthdayWish.objects.get(pk=self.wish.pk).updated_at, old)

    def test_raw_email_log_update_refreshes_updated_at(self):
        old = timezone.now() - timedelta(days=2)
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE birthdays_birthdayemaillog SET updated_at = %s WHERE id = %s",
                [old, self.email_log.pk],
            )
            cursor.execute(
                "UPDATE birthdays_birthdayemaillog SET retry_count = retry_count + 1 WHERE id = %s",
                [self.email_log.pk],
            )
        self.assertGreater(BirthdayEmailLog.objects.get(pk=self.email_log.pk).updated_at, old)

    def test_conflicting_named_trigger_aborts_before_installing_sibling(self):
        migration = import_module("birthdays.migrations.0004_install_updated_at_triggers")
        with connection.cursor() as cursor:
            cursor.execute("DROP TRIGGER trg_birthdaywish_updated_at ON birthdays_birthdaywish")
            cursor.execute("DROP TRIGGER trg_emaillog_updated_at ON birthdays_birthdayemaillog")
            cursor.execute("""CREATE TRIGGER trg_emaillog_updated_at BEFORE UPDATE
                               ON birthdays_birthdayemaillog FOR EACH ROW
                               WHEN (NEW.id > 0) EXECUTE FUNCTION set_updated_at()""")

        with self.assertRaisesRegex(RuntimeError, "trigger khác định nghĩa"):
            migration.install_birthday_updated_at(None, SimpleNamespace(connection=connection))

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT count(*) FROM pg_trigger WHERE tgrelid = %s::regclass "
                "AND tgname = 'trg_birthdaywish_updated_at' AND NOT tgisinternal",
                ["birthdays_birthdaywish"],
            )
            self.assertEqual(cursor.fetchone()[0], 0)
