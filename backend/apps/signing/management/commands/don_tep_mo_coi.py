"""Dọn tệp ảnh chữ ký và tệp hoàn tất của Trình ký không còn bản ghi tham chiếu.

Mặc định chỉ liệt kê; thêm `--xoa` để xóa. Bỏ qua tệp mới hơn `--tuoi-toi-thieu-gio` giờ để không đụng tệp
vừa ghi mà transaction chưa commit. Không quét thư mục tệp văn bản gốc (`trinh_ky`).
"""
import time

from django.core.management.base import BaseCommand

from signing.models import SigningAttempt, SigningSignature, SigningUserSignature
from signing.services.hanh_dong_ky import THU_MUC_ANH_CHU_KY
from signing.services.tep_hoan_tat import THU_MUC as THU_MUC_HOAN_TAT
from signing.storage import THU_MUC_ANH_CA_NHAN, get_storage


def _tham_chieu():
    """Mỗi thư mục được quét kèm tập vị trí lưu còn được bản ghi tham chiếu."""
    return {
        THU_MUC_ANH_CA_NHAN: set(SigningUserSignature.objects.values_list("vi_tri_tep", flat=True)),
        THU_MUC_ANH_CHU_KY: set(
            SigningSignature.objects.exclude(vi_tri_anh_chu_ky="").values_list("vi_tri_anh_chu_ky", flat=True)),
        THU_MUC_HOAN_TAT: set(
            SigningAttempt.objects.exclude(vi_tri_tep_hoan_tat="").values_list("vi_tri_tep_hoan_tat", flat=True)),
    }


class Command(BaseCommand):
    help = "Liệt kê (mặc định) hoặc xóa (--xoa) tệp của Trình ký không còn bản ghi tham chiếu."

    def add_arguments(self, parser):
        parser.add_argument("--xoa", action="store_true", help="Xóa tệp mồ côi thay vì chỉ liệt kê.")
        parser.add_argument("--tuoi-toi-thieu-gio", type=float, default=24.0,
                            help="Chỉ xét tệp cũ hơn số giờ này (mặc định 24).")

    def handle(self, *args, **options):
        storage = get_storage()
        gioi_han = time.time() - options["tuoi_toi_thieu_gio"] * 3600
        so_tep = 0
        for thu_muc, dang_dung in _tham_chieu().items():
            for vi_tri, sua_cuoi in storage.list_files(thu_muc):
                if vi_tri in dang_dung or sua_cuoi > gioi_han:
                    continue
                so_tep += 1
                if options["xoa"]:
                    storage.delete(vi_tri)
                self.stdout.write(f"{'Đã xóa' if options['xoa'] else 'Mồ côi'}: {vi_tri}")
        self.stdout.write(f"Tổng {so_tep} tệp mồ côi{' (đã xóa)' if options['xoa'] else ''}.")
