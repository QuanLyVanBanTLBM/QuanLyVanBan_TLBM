"""Phục hồi tệp PDF hoàn tất bị kẹt `DANG_XU_LY` quá hạn hoặc lỗi tạm (#497).

Mặc định chỉ liệt kê; thêm `--chay` để dựng lại. Không đụng lượt lỗi vĩnh viễn (dữ liệu hồ sơ lệch bằng chứng) và
lượt đang xử lý chưa quá hạn. Phù hợp để đặt lịch định kỳ khi hạ tầng tác vụ nền sẵn sàng (#415, #448).
"""
from django.core.management.base import BaseCommand

from signing.services import tep_hoan_tat


class Command(BaseCommand):
    help = "Liệt kê (mặc định) hoặc dựng lại (--chay) tệp hoàn tất bị kẹt hoặc lỗi tạm."

    def add_arguments(self, parser):
        parser.add_argument("--chay", action="store_true", help="Dựng lại tệp thay vì chỉ liệt kê.")

    def handle(self, *args, **options):
        if not options["chay"]:
            ds = tep_hoan_tat.luot_can_phuc_hoi()
            for luot in ds:
                self.stdout.write(f"Cần phục hồi: lượt {luot.pk} ({luot.trang_thai_tep_hoan_tat} {luot.loi_tep_hoan_tat})")
            self.stdout.write(f"Tổng {len(ds)} lượt cần phục hồi.")
            return
        ket_qua = tep_hoan_tat.phuc_hoi_tep_hoan_tat()
        for luot_id, truoc, sau in ket_qua:
            self.stdout.write(f"Lượt {luot_id}: {truoc} -> {sau}")
        self.stdout.write(f"Tổng {len(ket_qua)} lượt đã xử lý.")
