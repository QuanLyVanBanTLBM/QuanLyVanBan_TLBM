"""
Xóa dữ liệu DEMO do seed_work_demo tạo (nhóm 6).

AN TOÀN:
- CHỈ dùng trên DB riêng của nhóm 6, KHÔNG trên DB dùng chung.
- Mặc định DRY-RUN: liệt kê sẽ xóa gì rồi dừng. Thêm --yes-i-know mới xóa thật.
- CHỈ xóa record test do seed tạo: Task tiêu đề "[TEST] ...", Employee username "test_...",
  và Position/DonVi/Khoi mang nhãn "[TEST]" nếu không còn ai tham chiếu (PROTECT thì bỏ qua).
- KHÔNG đụng record thật của bất kỳ ai; KHÔNG flush/drop.
"""

from django.core.management.base import BaseCommand
from django.db import connections, transaction
from django.db.models.deletion import ProtectedError

from accounts.models import Employee, Position
from organizations.models import DonVi, KhoiKhuVuc
from work.models import Task


class Command(BaseCommand):
    help = "Xóa dữ liệu demo của module Công việc. Mặc định dry-run; thêm --yes-i-know để xóa."

    def add_arguments(self, parser):
        parser.add_argument(
            "--yes-i-know",
            action="store_true",
            dest="confirm",
            help="Xác nhận XÓA dữ liệu demo khỏi DB hiện tại. Thiếu cờ này thì chỉ chạy dry-run.",
        )

    def handle(self, *args, **options):
        confirm = options["confirm"]

        db = connections["default"].settings_dict
        tasks = Task.objects.filter(title__startswith="[TEST]")
        employees = Employee.objects.filter(username__startswith="test_")
        positions = Position.objects.filter(name__startswith="[TEST]")
        donvis = DonVi.objects.filter(ten__startswith="[TEST]")
        khois = KhoiKhuVuc.objects.filter(ten__startswith="[TEST]")

        self.stdout.write("")
        self.stdout.write("  ===== XÓA DỮ LIỆU DEMO — MODULE CÔNG VIỆC (NHÓM 6) =====")
        self.stdout.write(f"  CSDL đích : NAME={db.get('NAME')}  HOST={db.get('HOST') or 'localhost'}")
        self.stdout.write(f"    - Công việc [TEST] : {tasks.count()}")
        self.stdout.write(f"    - CBNV test_       : {employees.count()}")
        self.stdout.write(f"    - Chức vụ [TEST]   : {positions.count()} (bỏ qua nếu còn người tham chiếu)")
        self.stdout.write(f"    - Phòng ban [TEST] : {donvis.count()} (bỏ qua nếu còn người tham chiếu)")
        self.stdout.write(f"    - Khối [TEST]      : {khois.count()} (bỏ qua nếu còn đơn vị tham chiếu)")
        self.stdout.write("")

        if not confirm:
            self.stdout.write(self.style.WARNING(
                "  ĐÂY LÀ DRY-RUN — chưa xóa gì cả.\n"
                "  Kiểm tra CSDL đích ở trên; nếu đúng, chạy lại kèm cờ:  --yes-i-know"
            ))
            return

        skipped = []
        with transaction.atomic():
            # Task trước (cascade participant/comment/attachment/donvi-link), rồi employee, rồi Position/DonVi/Khoi.
            deleted_tasks = tasks.count()
            tasks.delete()

            deleted_users = 0
            for emp in employees:
                try:
                    emp.delete()
                    deleted_users += 1
                except ProtectedError:
                    skipped.append(f"CBNV {emp.username} (còn tham chiếu ở dữ liệu thật)")

            deleted_pos = self._safe_delete(positions, skipped, "Chức vụ", "name")
            deleted_dv = self._safe_delete(donvis, skipped, "Phòng ban", "ten")
            deleted_khoi = self._safe_delete(khois, skipped, "Khối", "ten")

        self.stdout.write(self.style.SUCCESS(
            f"Đã xóa: {deleted_tasks} công việc, {deleted_users} CBNV, "
            f"{deleted_pos} chức vụ, {deleted_dv} phòng ban, {deleted_khoi} khối."
        ))
        for note in skipped:
            self.stdout.write(self.style.WARNING(f"  Bỏ qua: {note}"))

    def _safe_delete(self, queryset, skipped, label, name_field):
        count = 0
        for obj in queryset:
            try:
                obj.delete()
                count += 1
            except ProtectedError:
                skipped.append(f"{label} \"{getattr(obj, name_field)}\" (còn record tham chiếu)")
        return count
