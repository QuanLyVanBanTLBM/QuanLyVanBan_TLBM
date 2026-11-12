"""
Django Management Command: expire_documents

Quét và tự động chuyển trạng thái các văn bản đã tới hoặc quá ngày hết hiệu lực
sang 'HET_HIEU_LUC' trên cả 2 model: Văn bản Đến và Văn bản Đi.

Cách dùng:
    python manage.py expire_documents
    python manage.py expire_documents --dry-run
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from documents.models import HieuLuc, VanBanDen, VanBanDi
from documents.services import check_and_update_expired_documents


class Command(BaseCommand):
    help = "Quét và chuyển trạng thái các văn bản đã quá ngày hết hiệu lực sang HET_HIEU_LUC"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Chỉ kiểm tra và đếm số lượng văn bản hết hạn mà không lưu thay đổi vào CSDL",
        )

    def handle(self, *args, **options):
        dry_run = options.get("dry_run", False)
        now = timezone.now()

        expired_den = VanBanDen.objects.filter(
            hieu_luc=HieuLuc.CON_HIEU_LUC,
            ngay_het_hieu_luc__isnull=False,
            ngay_het_hieu_luc__lte=now,
        )
        expired_di = VanBanDi.objects.filter(
            hieu_luc=HieuLuc.CON_HIEU_LUC,
            ngay_het_hieu_luc__isnull=False,
            ngay_het_hieu_luc__lte=now,
        )

        total_count = expired_den.count() + expired_di.count()

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"[DRY-RUN] Tim thay {total_count} van ban da qua ngay het hieu luc (chua cap nhat DB)."
                )
            )
            for doc in list(expired_den) + list(expired_di):
                self.stdout.write(f"  - [{doc.get_loai_display()}] So hieu: {doc.so_hieu} | Het han: {doc.ngay_het_hieu_luc}")
            return

        updated = check_and_update_expired_documents()
        self.stdout.write(
            self.style.SUCCESS(
                f"Da cap nhat thanh cong {updated} van ban sang trang thai Het hieu luc."
            )
        )
