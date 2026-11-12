"""
Gửi email nhắc việc SẮP đến hạn và việc QUÁ HẠN (module Công việc, nhóm 6).

Chạy tay hoặc đặt lịch (cron) hằng ngày — KHÔNG đụng workflow CI. Người nhận: chủ trì +
cán bộ tham gia (không gửi người tạo, không gửi chỉ đạo).

AN TOÀN:
- --dry-run: chỉ đếm số thư sẽ gửi (dùng backend dummy, KHÔNG gửi gì), rồi dừng.
- Backend lấy từ settings.MAILERS (đọc env). Dev mặc định là console → không ra ngoài.
- Nếu backend là SMTP thật: phải thêm --yes-send-real mới thực sự gửi (tránh gửi nhầm ra ngoài).
- KHÔNG hardcode cấu hình/mật khẩu SMTP.
"""

from django.conf import settings
from django.core.mail.backends.dummy import EmailBackend as DummyEmailBackend
from django.core.management.base import BaseCommand

from work.services.email import (
    DEFAULT_DUE_SOON_DAYS,
    send_due_soon_reminders,
    send_overdue_reminders,
)

SMTP_BACKEND_SUFFIX = "smtp.EmailBackend"


def _resolved_backend():
    mailers = getattr(settings, "MAILERS", None)
    if isinstance(mailers, dict):
        return mailers.get("default", {}).get("BACKEND", "")
    return getattr(settings, "EMAIL_BACKEND", "")


class Command(BaseCommand):
    help = "Gửi mail nhắc việc sắp đến hạn / quá hạn. Có --dry-run; backend SMTP thật cần --yes-send-real."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Chỉ đếm số thư sẽ gửi, KHÔNG gửi gì (dùng backend dummy).",
        )
        parser.add_argument(
            "--days",
            type=int,
            default=DEFAULT_DUE_SOON_DAYS,
            help=f"Số ngày coi là 'sắp đến hạn' (mặc định {DEFAULT_DUE_SOON_DAYS}).",
        )
        parser.add_argument(
            "--yes-send-real",
            action="store_true",
            dest="send_real",
            help="Xác nhận gửi khi backend là SMTP thật. Thiếu cờ này mà backend SMTP thì sẽ từ chối.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        days = options["days"]
        send_real = options["send_real"]

        backend = _resolved_backend()
        is_real_smtp = backend.endswith(SMTP_BACKEND_SUFFIX)

        self.stdout.write("")
        self.stdout.write("  ===== NHẮC VIỆC SẮP ĐẾN HẠN / QUÁ HẠN (NHÓM 6) =====")
        self.stdout.write(f"  Mail backend: {backend or '(mặc định)'}")
        self.stdout.write(f"  Cửa sổ 'sắp đến hạn': trong {days} ngày tới")
        self.stdout.write(f"  Người nhận: chủ trì + cán bộ tham gia (không gửi người tạo/chỉ đạo)")

        if dry_run:
            # Backend dummy: nhận và loại bỏ thư, trả về số lượng — đếm mà KHÔNG gửi gì.
            connection = DummyEmailBackend()
            due = send_due_soon_reminders(days_ahead=days, connection=connection)
            overdue = send_overdue_reminders(connection=connection)
            self.stdout.write("")
            self.stdout.write(self.style.WARNING(
                f"  DRY-RUN — không gửi gì. Sẽ gửi: {due} thư sắp đến hạn, {overdue} thư quá hạn."
            ))
            return

        if is_real_smtp and not send_real:
            self.stdout.write("")
            self.stdout.write(self.style.ERROR(
                "  Backend là SMTP THẬT nhưng thiếu --yes-send-real → KHÔNG gửi.\n"
                "  Chạy --dry-run để xem trước, hoặc thêm --yes-send-real nếu chắc chắn gửi thật."
            ))
            return

        due = send_due_soon_reminders(days_ahead=days)
        overdue = send_overdue_reminders()
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"Đã gửi {due} thư nhắc sắp đến hạn, {overdue} thư nhắc quá hạn."
        ))
