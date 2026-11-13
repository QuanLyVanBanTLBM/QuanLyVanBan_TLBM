import time
from datetime import date

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from birthdays.services import send_automated_birthday_emails


class Command(BaseCommand):
    help = "Gửi email sinh nhật CBNV theo ngày dương lịch của dự án."

    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            help="Ngày cần gửi YYYY-MM-DD (mặc định: ngày hiện tại theo TIME_ZONE của dự án)",
        )
        parser.add_argument("--username", help="Chỉ gửi cho tài khoản chỉ định trong ngày cần gửi")
        parser.add_argument(
            "--trigger-source",
            choices=("SCHEDULED", "RECOVERY"),
            help="Nguồn khởi chạy để hiển thị đúng trong nhật ký (mặc định suy ra từ tham số)",
        )
        parser.add_argument(
            "--retries",
            type=int,
            default=3,
            help="Số lần thử lại tối đa sau lần gửi đầu (mặc định: 3)",
        )
        parser.add_argument(
            "--allow-locmem",
            action="store_true",
            help="Chỉ dùng trong kiểm thử với backend email trong bộ nhớ",
        )

    def handle(self, *args, **options):
        if not 0 <= options["retries"] <= 10:
            raise CommandError("--retries phải từ 0 đến 10.")

        if options["date"]:
            try:
                target_date = date.fromisoformat(options["date"])
            except ValueError as exc:
                raise CommandError("--date phải theo định dạng YYYY-MM-DD.") from exc
            if target_date.isoformat() != options["date"]:
                raise CommandError("--date phải theo định dạng YYYY-MM-DD.")
        else:
            target_date = timezone.localdate()

        trigger_source = options["trigger_source"] or (
            "RECOVERY" if options["date"] or options["username"] else "SCHEDULED"
        )

        def _safe_write(writer, text):
            try:
                writer(text)
            except UnicodeEncodeError:
                safe_text = text.encode("ascii", errors="backslashreplace").decode("ascii")
                writer(safe_text)

        started_at = timezone.now()
        started_monotonic = time.monotonic()
        started_at_local = timezone.localtime(started_at).isoformat(timespec="seconds")
        _safe_write(
            self.stdout.write,
            "BIRTHDAY_EMAIL_START "
            f"date={target_date.isoformat()} trigger={trigger_source} started_at={started_at_local}",
        )

        try:
            self._validate_delivery_backend(options["allow_locmem"])
            results = send_automated_birthday_emails(
                target_date=target_date,
                max_retries=options["retries"],
                allow_test_email_backend=options["allow_locmem"],
                username=options["username"],
                trigger_source=trigger_source,
            )
        except Exception as exc:
            ended_at_local = timezone.localtime(timezone.now()).isoformat(timespec="seconds")
            duration_ms = int((time.monotonic() - started_monotonic) * 1000)
            _safe_write(
                self.stdout.write,
                "BIRTHDAY_EMAIL_SUMMARY "
                f"date={target_date.isoformat()} trigger={trigger_source} "
                f"started_at={started_at_local} ended_at={ended_at_local} duration_ms={duration_ms} "
                "eligible=unknown sent=unknown skipped=unknown retry=unknown stale=unknown failed=unknown "
                f"outcome=error error_type={type(exc).__name__}",
            )
            raise

        for detail in results["details"]:
            name = detail["full_name"]
            if detail.get("skipped"):
                _safe_write(self.stdout.write, self.style.WARNING(f"Bỏ qua: {name} - {detail['reason']}"))
            elif detail.get("trang_thai") == "SUCCESS":
                _safe_write(self.stdout.write, self.style.SUCCESS(f"Đã gửi: {name}"))
            else:
                _safe_write(self.stderr.write, self.style.ERROR(f"Cần xử lý: {name} - {detail.get('error', '')}"))

        summary = (
            f"Tổng: {results['total_eligible']} | "
            f"Đã gửi: {results['sent_count']} | "
            f"Bỏ qua: {results['skipped_count']} | "
            f"Chờ gửi lại: {results.get('retry_count', 0)} | "
            f"SENDING kẹt cần đối soát: {results.get('stale_failed_count', 0)} | "
            f"Thất bại: {results['failed_count']}"
        )
        _safe_write(self.stdout.write, summary)
        ended_at_local = timezone.localtime(timezone.now()).isoformat(timespec="seconds")
        duration_ms = int((time.monotonic() - started_monotonic) * 1000)
        targeted_without_success = options["username"] is not None and not any(
            detail.get("trang_thai") == "SUCCESS" for detail in results["details"]
        )
        outcome = "failed" if results["failed_count"] or targeted_without_success else "completed"
        _safe_write(
            self.stdout.write,
            "BIRTHDAY_EMAIL_SUMMARY "
            f"date={target_date.isoformat()} trigger={trigger_source} "
            f"started_at={started_at_local} ended_at={ended_at_local} duration_ms={duration_ms} "
            f"eligible={results['total_eligible']} sent={results['sent_count']} "
            f"skipped={results['skipped_count']} retry={results.get('retry_count', 0)} "
            f"stale={results.get('stale_failed_count', 0)} failed={results['failed_count']} outcome={outcome}",
        )
        if results["failed_count"]:
            raise CommandError("Có email chưa được xác nhận gửi thành công; xem nhật ký BirthdayEmailLog.")
        if targeted_without_success:
            raise CommandError("Tài khoản chưa có lần gửi thành công cho ngày được chọn.")

    def _validate_delivery_backend(self, allow_test_email_backend):
        current_backend = None
        if hasattr(settings, "MAILERS"):
            mailers_dict = getattr(settings, "MAILERS", {})
            default_mailer = mailers_dict.get("default", {})
            current_backend = default_mailer.get("BACKEND")
        elif hasattr(settings, "EMAIL_BACKEND"):
            try:
                current_backend = settings.EMAIL_BACKEND
            except AttributeError:
                current_backend = None

        smtp_backend = "django.core.mail.backends.smtp.EmailBackend"
        memory_backend = "django.core.mail.backends.locmem.EmailBackend"
        if current_backend != smtp_backend and not (
            allow_test_email_backend and (current_backend == memory_backend or "locmem" in str(current_backend))
        ):
            raise CommandError(
                "Cần cấu hình email backend dạng SMTP trước khi gửi email sinh nhật."
            )
        if current_backend == smtp_backend and not getattr(settings, "DEFAULT_FROM_EMAIL", "").strip():
            raise CommandError("Cần cấu hình DEFAULT_FROM_EMAIL trước khi gửi email sinh nhật.")
