"""Nhắc hạn người ký Trình ký (sắp đến hạn, quá hạn); chạy định kỳ, chạy lặp không gửi trùng."""
from django.core.management.base import BaseCommand

from signing.services.thong_bao import nhac_han


class Command(BaseCommand):
    help = "Tạo thông báo nhắc hạn/quá hạn cho người ký đang chờ ký."

    def handle(self, *args, **options):
        self.stdout.write(f"Đã tạo {nhac_han()} thông báo nhắc hạn.")
