"""
Lệnh seed dữ liệu mẫu công việc (Tasks) cho Dashboard và kiểm thử tích hợp.
Cung cấp 7 công việc mẫu đầy đủ các trạng thái và phân quyền cho:
- canbo / chuyenvien (Cán bộ / Chuyên viên)
- truongphong (Trưởng phòng)
- giamdoc (Giám đốc)

Trạng thái hỗ trợ:
- CHO_XU_LY (Chờ xử lý)
- DANG_XU_LY (Đang xử lý)
- CHO_DUYET (Chờ duyệt - đã nộp bằng chứng)
- HOAN_THANH (Hoàn thành - đã duyệt)
- QUA_HAN (Quá hạn - chưa mở)
- CHUA_HOAN_THANH (Chưa hoàn thành - quá hạn đã mở)

Mức độ ưu tiên thể hiện qua tiền tố tiêu đề ([Khẩn], [Gấp], [Thường])
và metadata để Dashboard hiển thị trực quan.
"""

from datetime import timedelta
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.contrib.auth.hashers import make_password

from accounts.models import Employee, Position
from organizations.models import DonVi
from work.models import (
    AttachmentKind,
    ParticipantRole,
    Task,
    TaskAttachment,
    TaskComment,
    TaskParticipant,
    TaskStatus,
)


class Command(BaseCommand):
    help = "Seed 5 - 8 công việc mẫu gán cho canbo, truongphong, giamdoc phục vụ Dashboard."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clean",
            action="store_true",
            help="Xóa dữ liệu mẫu cũ trước khi tạo lại.",
        )

    def handle(self, *args, **options):
        self.stdout.write("==> Bắt đầu nạp dữ liệu mẫu Công việc (seed_work)...")

        with transaction.atomic():
            if options.get("clean"):
                deleted_count, _ = Task.objects.filter(title__contains="[DEMO-DASHBOARD]").delete()
                self.stdout.write(f"    - Đã dọn {deleted_count} công việc demo cũ.")

            # 1. Tìm hoặc khởi tạo tài khoản demo: canbo, truongphong, giamdoc, admin
            user_map = self._get_or_create_demo_users()

            # 2. Tạo 7 công việc mẫu
            created_tasks = self._create_demo_tasks(user_map)

        self.stdout.write(self.style.SUCCESS(f"==> Hoàn tất! Đã tạo thành công {len(created_tasks)} công việc mẫu."))

    def _get_or_create_demo_users(self):
        """Đảm bảo có đủ 4 tài khoản: admin, canbo, truongphong, giamdoc."""
        donvi = DonVi.objects.first()
        pos_chuyenvien = Position.objects.filter(name__icontains="Chuyên viên").first() or Position.objects.first()
        pos_truongphong = Position.objects.filter(name__icontains="Trưởng phòng").first() or Position.objects.first()
        pos_giamdoc = Position.objects.filter(name__icontains="Giám đốc").first() or Position.objects.first()

        defaults = {
            "ngay_sinh": "1990-01-01",
            "don_vi": donvi,
            "chuc_vu": pos_chuyenvien,
            "password": make_password("@django_CD25CT_CLC"),
            "trang_thai": Employee.Status.LAM_VIEC,
            "is_public": True,
            "is_active": True,
        }

        # canbo / chuyenvien
        canbo = Employee.objects.filter(username__in=["canbo", "chuyenvien", "chuyenvien_cntt"]).first()
        if not canbo:
            canbo, _ = Employee.objects.get_or_create(
                username="canbo",
                defaults={**defaults, "ho_ten": "Nguyễn Văn Cán Bộ", "email": "canbo@baolong.vn"},
            )

        # truongphong
        truongphong = Employee.objects.filter(username__in=["truongphong", "truongphong_cntt"]).first()
        if not truongphong:
            truongphong, _ = Employee.objects.get_or_create(
                username="truongphong",
                defaults={**defaults, "ho_ten": "Trần Thị Trưởng Phòng", "email": "truongphong@baolong.vn", "chuc_vu": pos_truongphong},
            )

        # giamdoc
        giamdoc = Employee.objects.filter(username__in=["giamdoc", "lanhdao"]).first()
        if not giamdoc:
            giamdoc, _ = Employee.objects.get_or_create(
                username="giamdoc",
                defaults={**defaults, "ho_ten": "Lê Hoàng Giám Đốc", "email": "giamdoc@baolong.vn", "chuc_vu": pos_giamdoc},
            )

        # admin (người giao việc hoặc quản trị)
        admin = Employee.objects.filter(username="admin").first() or giamdoc

        self.stdout.write(f"    - Cán bộ/Chuyên viên: {canbo.username} ({canbo.ho_ten})")
        self.stdout.write(f"    - Trưởng phòng:       {truongphong.username} ({truongphong.ho_ten})")
        self.stdout.write(f"    - Giám đốc:           {giamdoc.username} ({giamdoc.ho_ten})")

        return {
            "canbo": canbo,
            "truongphong": truongphong,
            "giamdoc": giamdoc,
            "admin": admin,
        }

    def _create_demo_tasks(self, u):
        today = timezone.localdate()
        now = timezone.now()

        tasks_spec = [
            # 1. Chờ xử lý (Khẩn)
            {
                "title": "[DEMO-DASHBOARD] [Khẩn] Soạn thảo báo cáo tài chính quý III phục vụ thanh tra Ban Giám đốc",
                "requirement": "Rà soát toàn bộ số liệu thu chi nghiệp vụ bảo hiểm quý III, chuẩn bị bản in gửi phòng Thanh tra.",
                "created_date": today,
                "due_date": today + timedelta(days=2),
                "created_by": u["truongphong"],
                "host": u["canbo"],
                "monitor": u["truongphong"],
                "priority": "Khẩn",
                "status_expected": TaskStatus.CHO_XU_LY,
            },
            # 2. Đang xử lý (Gấp)
            {
                "title": "[DEMO-DASHBOARD] [Gấp] Rà soát và cập nhật biểu mẫu giải quyết quyền lợi bảo hiểm năm 2026",
                "requirement": "Cập nhật các mẫu đơn bồi thường bảo hiểm sức khỏe theo quy chuẩn ban hành mới.",
                "created_date": today - timedelta(days=2),
                "due_date": today + timedelta(days=4),
                "created_by": u["truongphong"],
                "host": u["canbo"],
                "monitor": u["truongphong"],
                "opened_at": now - timedelta(days=1),
                "opened_by": u["canbo"],
                "priority": "Gấp",
                "status_expected": TaskStatus.DANG_XU_LY,
            },
            # 3. Chờ duyệt (Thường)
            {
                "title": "[DEMO-DASHBOARD] [Thường] Kiểm tra hạ tầng CNTT và hệ thống máy chủ chi nhánh miền Nam",
                "requirement": "Kiểm tra tình trạng vận hành thiết bị lưu trữ, sao lưu dữ liệu văn bản điều hành.",
                "created_date": today - timedelta(days=4),
                "due_date": today + timedelta(days=5),
                "created_by": u["truongphong"],
                "host": u["canbo"],
                "monitor": u["giamdoc"],
                "opened_at": now - timedelta(days=3),
                "opened_by": u["canbo"],
                "with_evidence": True,
                "priority": "Thường",
                "status_expected": TaskStatus.CHO_DUYET,
            },
            # 4. Hoàn thành (Gấp)
            {
                "title": "[DEMO-DASHBOARD] [Gấp] Thẩm định hồ sơ bồi thường nghiệp vụ bảo hiểm hàng hải số 108/BH",
                "requirement": "Xác minh biên bản giám định hiện trường, tính toán mức bồi thường tổn thất thân tàu.",
                "created_date": today - timedelta(days=6),
                "due_date": today + timedelta(days=3),
                "created_by": u["truongphong"],
                "host": u["canbo"],
                "monitor": u["truongphong"],
                "opened_at": now - timedelta(days=5),
                "opened_by": u["canbo"],
                "with_evidence": True,
                "approved_at": now - timedelta(hours=3),
                "approved_by": u["truongphong"],
                "priority": "Gấp",
                "status_expected": TaskStatus.HOAN_THANH,
            },
            # 5. Quá hạn (Khẩn)
            {
                "title": "[DEMO-DASHBOARD] [Khẩn] Báo cáo tình hình tiếp nhận và xử lý văn bản đến tháng 10",
                "requirement": "Thống kê danh sách văn bản đến chưa hoàn tất xử lý, phân loại theo đơn vị chủ trì.",
                "created_date": today - timedelta(days=10),
                "due_date": today - timedelta(days=3),
                "created_by": u["truongphong"],
                "host": u["canbo"],
                "monitor": u["truongphong"],
                "priority": "Khẩn",
                "status_expected": TaskStatus.QUA_HAN,
            },
            # 6. Chờ xử lý (Thường)
            {
                "title": "[DEMO-DASHBOARD] [Thường] Chuẩn bị hồ sơ dự thảo chiến lược chuyển đổi số 2026-2030",
                "requirement": "Tổng hợp ý kiến các phòng ban về kế hoạch số hóa lưu trữ và tích hợp chữ ký số.",
                "created_date": today - timedelta(days=1),
                "due_date": today + timedelta(days=10),
                "created_by": u["giamdoc"],
                "host": u["truongphong"],
                "monitor": u["giamdoc"],
                "participant": u["canbo"],
                "priority": "Thường",
                "status_expected": TaskStatus.CHO_XU_LY,
            },
            # 7. Chưa hoàn thành (Gấp)
            {
                "title": "[DEMO-DASHBOARD] [Gấp] Trình phê duyệt kế hoạch tổ chức hội nghị khách hàng bảo hiểm thân tàu",
                "requirement": "Lập dự toán kinh phí và danh sách khách mời đại biểu, trình duyệt phòng Tài vụ.",
                "created_date": today - timedelta(days=8),
                "due_date": today - timedelta(days=2),
                "created_by": u["truongphong"],
                "host": u["canbo"],
                "monitor": u["truongphong"],
                "opened_at": now - timedelta(days=6),
                "opened_by": u["canbo"],
                "priority": "Gấp",
                "status_expected": TaskStatus.CHUA_HOAN_THANH,
            },
        ]

        created_objs = []
        for spec in tasks_spec:
            task, _ = Task.objects.get_or_create(
                title=spec["title"],
                defaults={
                    "requirement": spec["requirement"],
                    "created_date": spec["created_date"],
                    "due_date": spec["due_date"],
                    "created_by": spec["created_by"],
                    "first_opened_at": spec.get("opened_at"),
                    "first_opened_by": spec.get("opened_by"),
                    "approved_at": spec.get("approved_at"),
                    "approved_by": spec.get("approved_by"),
                },
            )

            # Gán Chủ trì (host)
            if spec.get("host"):
                TaskParticipant.objects.get_or_create(
                    task=task,
                    user=spec["host"],
                    defaults={"role": ParticipantRole.CHU_TRI},
                )

            # Gán Chỉ đạo (monitor)
            if spec.get("monitor") and spec["monitor"] != spec.get("host"):
                TaskParticipant.objects.get_or_create(
                    task=task,
                    user=spec["monitor"],
                    defaults={"role": ParticipantRole.CHI_DAO},
                )

            # Gán Cán bộ tham gia (participant)
            if spec.get("participant") and spec["participant"] not in (spec.get("host"), spec.get("monitor")):
                TaskParticipant.objects.get_or_create(
                    task=task,
                    user=spec["participant"],
                    defaults={"role": ParticipantRole.THAM_GIA},
                )

            # Bằng chứng (kèm comment) nếu có
            if spec.get("with_evidence"):
                comment, _ = TaskComment.objects.get_or_create(
                    task=task,
                    author=spec["host"],
                    defaults={"content": "Đã hoàn thành nội dung công việc. Kính gửi file báo cáo kết quả đính kèm."},
                )
                TaskAttachment.objects.get_or_create(
                    task=task,
                    kind=AttachmentKind.BANG_CHUNG,
                    comment=comment,
                    defaults={
                        "original_name": "bao_cao_ket_qua_hoan_thanh.pdf",
                        "file": "test/bao_cao_ket_qua_hoan_thanh.pdf",
                        "uploaded_by": spec["host"],
                    },
                )

            computed_st = task.get_status()
            self.stdout.write(f"    + [{spec['priority']:<5}] [{computed_st:<15}] #{task.id}: {task.title[:50]}...")
            created_objs.append(task)

        return created_objs
