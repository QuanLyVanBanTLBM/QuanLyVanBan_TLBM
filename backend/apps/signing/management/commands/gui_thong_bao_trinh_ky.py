"""Gửi lại email thông báo Trình ký còn `CHO_GUI`/`THAT_BAI` (quét outbox `signing_notification`; chạy định kỳ)."""
from django.core.management.base import BaseCommand

from signing.services.thong_bao import gui_lai_email_ton


class Command(BaseCommand):
    help = "Gửi lại email thông báo Trình ký chưa gửi được."

    def handle(self, *args, **options):
        da_gui, con_loi = gui_lai_email_ton()
        self.stdout.write(f"Đã gửi {da_gui} email; còn lỗi {con_loi}.")
