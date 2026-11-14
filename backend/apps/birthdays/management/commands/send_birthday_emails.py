import re
import time
from datetime import date
from uuid import uuid4

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from birthdays.models import BirthdaySchedulerRun, BirthdaySchedulerStatus
from birthdays.scheduler import VIETNAM_TIME_ZONE, run_status
from birthdays.services import send_automated_birthday_emails


class Command(BaseCommand):
    help = "Gửi email sinh nhật CBNV theo ngày dương lịch của dự án."

    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            help="Ngày cần gửi YYYY-MM-DD (mặc định: ngày hiện tại theo TIME_ZONE của dự án)",
        )
        parser.add_argument("--username", help="Chỉ gửi cho tài khoản chỉ định trong ngày cần gửi")
        parser.add_argument("--scheduled-slot", choices=BirthdaySchedulerRun.Slot.values)
        parser.add_argument("--github-run-id")
        parser.add_argument("--github-run-attempt")
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
            target_date = timezone.localdate(timezone=VIETNAM_TIME_ZONE)

        trigger_source = options["trigger_source"] or (
            "RECOVERY" if options["date"] or options["username"] else "SCHEDULED"
        )
        slot = options["scheduled_slot"]
        github_run_id = options["github_run_id"]
        github_run_attempt = options["github_run_attempt"]
        if github_run_id is not None or github_run_attempt is not None:
            if not all(re.fullmatch(r"[1-9][0-9]{0,23}", value or "") for value in (
                github_run_id, github_run_attempt,
            )):
                raise CommandError("Cần GitHub run ID và run attempt hợp lệ.")
            execution_id = f"github:{github_run_id}:{github_run_attempt}"
        else:
            execution_id = f"local:{uuid4()}"

        def _safe_write(writer, text):
            try:
                writer(text)
            except UnicodeEncodeError:
                safe_text = text.encode("ascii", errors="backslashreplace").decode("ascii")
                writer(safe_text)

        started_at = timezone.now()
        run, created = BirthdaySchedulerRun.objects.get_or_create(
            execution_id=execution_id,
            defaults={
                "processing_date": target_date,
                "trigger_source": trigger_source,
                "scheduled_slot": slot,
                "started_at": started_at,
                "status": BirthdaySchedulerStatus.RUNNING,
                "github_run_id": github_run_id,
            },
        )
        if not created:
            if (run.processing_date, run.trigger_source, run.scheduled_slot) != (target_date, trigger_source, slot):
                raise CommandError(f"Birthday email execution {execution_id} has different run parameters.")
            if run.status == BirthdaySchedulerStatus.SUCCESS:
                self.stdout.write(f"Birthday email execution {execution_id} was already recorded.")
                return
            raise CommandError(f"Birthday email execution {execution_id} already exists: {run_status(run, started_at)}.")
        started_monotonic = time.monotonic()
        started_at_local = started_at.astimezone(VIETNAM_TIME_ZONE).isoformat(timespec="seconds")
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
        except (Exception, KeyboardInterrupt) as exc:
            ended_at = timezone.now()
            run.ended_at = ended_at
            run.status = (
                BirthdaySchedulerStatus.UNKNOWN if isinstance(exc, KeyboardInterrupt)
                else BirthdaySchedulerStatus.FAILED
            )
            run.error_reason = str(exc) if isinstance(exc, CommandError) else type(exc).__name__
            run.save(update_fields=["ended_at", "status", "error_reason"])
            ended_at_local = ended_at.astimezone(VIETNAM_TIME_ZONE).isoformat(timespec="seconds")
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

        ended_at = timezone.now()
        targeted_without_success = options["username"] is not None and not any(
            detail.get("trang_thai") == "SUCCESS" for detail in results["details"]
        )
        error_reason = None
        if results["failed_count"] or (results["total_eligible"] and results.get("stale_failed_count", 0)):
            error_reason = "DELIVERY_FAILURE"
        elif targeted_without_success:
            error_reason = "TARGET_NOT_SENT"
        run.ended_at = ended_at
        run.status = BirthdaySchedulerStatus.FAILED if error_reason else BirthdaySchedulerStatus.SUCCESS
        run.total_eligible = results["total_eligible"]
        run.sent_count = results["sent_count"]
        run.failed_count = results["failed_count"]
        run.skipped_count = results["skipped_count"]
        run.retry_count = results["retried_count"]
        run.error_reason = error_reason
        run.save(update_fields=[
            "ended_at", "status", "total_eligible", "sent_count", "failed_count",
            "skipped_count", "retry_count", "error_reason",
        ])

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
        ended_at_local = ended_at.astimezone(VIETNAM_TIME_ZONE).isoformat(timespec="seconds")
        duration_ms = int((time.monotonic() - started_monotonic) * 1000)
        outcome = "failed" if error_reason else "completed"
        _safe_write(
            self.stdout.write,
            "BIRTHDAY_EMAIL_SUMMARY "
            f"date={target_date.isoformat()} trigger={trigger_source} "
            f"started_at={started_at_local} ended_at={ended_at_local} duration_ms={duration_ms} "
            f"eligible={results['total_eligible']} sent={results['sent_count']} "
            f"skipped={results['skipped_count']} retry={results.get('retry_count', 0)} "
            f"stale={results.get('stale_failed_count', 0)} failed={results['failed_count']} outcome={outcome}",
        )
        if error_reason == "DELIVERY_FAILURE":
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
