"""
Seed dữ liệu DEMO cho module Công việc (nhóm 6).

AN TOÀN:
- CHỈ dùng trên DB riêng của nhóm 6 (local / test_nhom6), KHÔNG chạy trên DB dùng chung.
- Mặc định chạy DRY-RUN: chỉ liệt kê sẽ tạo gì rồi dừng, KHÔNG ghi gì.
  Thêm cờ --yes-i-know mới thực thi ghi dữ liệu.
- Idempotent: get_or_create theo field định danh, chạy nhiều lần không nhân bản.
- CHỈ THÊM record test (nhãn [TEST] / username test_), KHÔNG sửa/xóa dữ liệu sẵn có của ai.

GHI VÀO BẢNG:
- accounts_employee  : thêm các user test (username bắt đầu "test_").
- accounts_position   : CHỈ tạo [TEST] khi bảng TRỐNG; nếu đã có chức vụ thật thì dùng lại (đọc).
- organizations_donvi : CHỈ tạo [TEST] khi bảng TRỐNG; nếu đã có phòng ban thật thì dùng lại (đọc).
- organizations_khoi  : chỉ tạo [TEST] khi phải tạo DonVi mà chưa có Khối nào.
- task_congviec (+ participant/comment/attachment): thêm công việc test (tiêu đề bắt đầu "[TEST]").

MẬT KHẨU: đọc từ biến môi trường WORK_SEED_PASSWORD; nếu không set thì sinh ngẫu nhiên và in ra
một lần khi tạo. KHÔNG hardcode mật khẩu trong mã nguồn.
"""

import datetime
import os
import secrets

from django.core.management.base import BaseCommand
from django.db import connections, transaction
from django.utils import timezone

from accounts.models import Employee, Position
from organizations.models import DonVi, KhoiKhuVuc
from work.models import (
    AttachmentKind,
    ParticipantRole,
    Task,
    TaskAttachment,
    TaskComment,
    TaskParticipant,
)

LEADER_USERNAME = "test_truongnhom6"
LEADER_EMAIL = "test_truongnhom6@work-demo.test"

# Nhân viên test dùng email thuộc miền .test để không gửi thư tới địa chỉ thật.
EMPLOYEES = [
    {"username": LEADER_USERNAME, "ho_ten": "Phan Tạ Hữu Đức", "email": LEADER_EMAIL, "pos": 0, "dv": 0},
    {"username": "test_cbnv_1", "ho_ten": "Lê Văn An", "email": "an@test.local", "pos": 1, "dv": 1},
    {"username": "test_cbnv_2", "ho_ten": "Trần Thị Bình", "email": "binh@test.local", "pos": 2, "dv": 0},
    {"username": "test_cbnv_3", "ho_ten": "Phạm Minh Châu", "email": "chau@test.local", "pos": 1, "dv": 1},
    {"username": "test_cbnv_4", "ho_ten": "Đỗ Quốc Dũng", "email": "dung@test.local", "pos": 2, "dv": 0},
]

TEST_POSITIONS = ["[TEST] Trưởng phòng", "[TEST] Phó phòng", "[TEST] Chuyên viên"]
TEST_DONVI = ["[TEST] Phòng Kế hoạch", "[TEST] Phòng Hành chính"]

# 6 trạng thái + due lệch nhau để minh họa badge (VIỆC 2) và thứ tự sắp xếp (VIỆC 3).
# host/participant: chỉ số trong danh sách EMPLOYEES (0 = leader).
TASKS = [
    {"title": "[TEST] Chờ xử lý — hạn gần (2 ngày)", "due": 2, "created_ago": 1, "host": 1, "parts": [0, 2], "st": "CHO_XU_LY"},
    {"title": "[TEST] Chờ xử lý — hạn xa (15 ngày)", "due": 15, "created_ago": 1, "host": 2, "parts": [0], "st": "CHO_XU_LY"},
    {"title": "[TEST] Đang xử lý — đã mở, còn hạn", "due": 9, "created_ago": 2, "host": 1, "parts": [3], "st": "DANG_XU_LY", "opened": True},
    {"title": "[TEST] Chờ duyệt — đã nộp bằng chứng", "due": 5, "created_ago": 3, "host": 3, "parts": [1], "st": "CHO_DUYET", "opened": True, "evidence": True},
    {"title": "[TEST] Hoàn thành — đã duyệt", "due": 12, "created_ago": 4, "host": 2, "parts": [1], "st": "HOAN_THANH", "opened": True, "evidence": True, "approved": True},
    {"title": "[TEST] Chưa hoàn thành — đã mở nhưng quá hạn", "due": -3, "created_ago": 14, "host": 4, "parts": [1], "st": "CHUA_HOAN_THANH", "opened": True},
    {"title": "[TEST] Quá hạn — chưa mở, đã quá hạn", "due": -7, "created_ago": 14, "host": 4, "parts": [2], "st": "QUA_HAN"},
]


class Command(BaseCommand):
    help = "Seed dữ liệu demo cho module Công việc (nhóm 6). Mặc định dry-run; thêm --yes-i-know để ghi."

    def add_arguments(self, parser):
        parser.add_argument(
            "--yes-i-know",
            action="store_true",
            dest="confirm",
            help="Xác nhận GHI dữ liệu vào DB hiện tại. Thiếu cờ này thì chỉ chạy dry-run.",
        )

    def handle(self, *args, **options):
        confirm = options["confirm"]

        db = connections["default"].settings_dict
        db_name = db.get("NAME")
        db_host = db.get("HOST") or "localhost"
        db_user = db.get("USER") or "-"

        positions_empty = not Position.objects.exists()
        donvi_empty = not DonVi.objects.exists()

        self.stdout.write("")
        self.stdout.write("  ===== SEED DỮ LIỆU DEMO — MODULE CÔNG VIỆC (NHÓM 6) =====")
        self.stdout.write(f"  CSDL đích : NAME={db_name}  HOST={db_host}  USER={db_user}")
        self.stdout.write("  Bảng sẽ GHI:")
        self.stdout.write(f"    - accounts_employee  : thêm {len(EMPLOYEES)} user test (username 'test_...').")
        self.stdout.write(
            "    - accounts_position   : "
            + (f"TẠO MỚI {len(TEST_POSITIONS)} chức vụ [TEST] (bảng đang trống)." if positions_empty
               else "DÙNG LẠI chức vụ sẵn có (chỉ đọc, không ghi).")
        )
        self.stdout.write(
            "    - organizations_donvi : "
            + (f"TẠO MỚI {len(TEST_DONVI)} phòng ban [TEST] (bảng đang trống)." if donvi_empty
               else "DÙNG LẠI phòng ban sẵn có (chỉ đọc, không ghi).")
        )
        self.stdout.write(f"    - task_congviec       : thêm {len(TASKS)} công việc test (tiêu đề '[TEST] ...').")
        self.stdout.write("")
        self.stdout.write("  Danh sách sẽ tạo (nếu chưa có):")
        for item in EMPLOYEES:
            self.stdout.write(f"    · CBNV  {item['username']:<18s} {item['ho_ten']}  <{item['email']}>")
        for task in TASKS:
            self.stdout.write(f"    · Việc  [{task['st']:<15s}] {task['title']}")
        self.stdout.write("")

        if not confirm:
            self.stdout.write(self.style.WARNING(
                "  ĐÂY LÀ DRY-RUN — chưa ghi gì cả.\n"
                "  CHỈ chạy trên DB riêng của nhóm 6 (local/test_nhom6), KHÔNG trên DB dùng chung.\n"
                "  Kiểm tra CSDL đích ở trên; nếu đúng, chạy lại kèm cờ:  --yes-i-know"
            ))
            return

        password = os.environ.get("WORK_SEED_PASSWORD") or secrets.token_urlsafe(12)
        password_generated = "WORK_SEED_PASSWORD" not in os.environ

        with transaction.atomic():
            positions = self._ensure_positions(positions_empty)
            donvis = self._ensure_donvi(donvi_empty)
            employees, created_users = self._ensure_employees(positions, donvis, password)
            tasks, created_tasks = self._ensure_tasks(employees)

        self.stdout.write("")
        for emp in employees:
            self.stdout.write(f"  id={emp.pk:<4d} {emp.username:<18s} {emp.get_full_name()}  <{emp.email or '—'}>")
        self.stdout.write("")
        for task in tasks:
            task.refresh_from_db()
            self.stdout.write(f"  id={task.pk:<4d} {task.get_status():<16s} {task.title}")
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"Xong. Mới tạo: {created_users} CBNV, {created_tasks} công việc "
            f"(các record đã có được giữ nguyên)."
        ))
        if created_users and password_generated:
            self.stdout.write(self.style.WARNING(
                f"  Mật khẩu các tài khoản VỪA TẠO: {password}\n"
                "  (sinh ngẫu nhiên vì chưa đặt WORK_SEED_PASSWORD — hãy lưu lại). "
                "Tài khoản đã có từ trước không bị đổi mật khẩu."
            ))

    # ------------------------------------------------------------------
    # Các bước ghi — đều get_or_create, chỉ thêm, không sửa/xóa record cũ.
    # ------------------------------------------------------------------
    def _ensure_positions(self, positions_empty):
        if not positions_empty:
            # Dùng lại chức vụ thật sẵn có (đọc), lấy vài cái để gán đa dạng.
            existing = list(Position.objects.order_by("display_order")[:3])
            while len(existing) < 3:
                existing.append(existing[-1])
            return existing

        created = []
        for name in TEST_POSITIONS:
            position, _ = Position.objects.get_or_create(
                name=name,
                defaults={"display_order": Position.get_next_display_order()},
            )
            created.append(position)
        return created

    def _ensure_donvi(self, donvi_empty):
        if not donvi_empty:
            existing = list(DonVi.objects.order_by("stt_uu_tien")[:2])
            while len(existing) < 2:
                existing.append(existing[-1])
            return existing

        khoi = KhoiKhuVuc.objects.order_by("thu_tu_hien_thi", "id").first()
        if khoi is None:
            khoi = KhoiKhuVuc.objects.create(ten="[TEST] Khối kiểm thử")

        created = []
        for name in TEST_DONVI:
            don_vi = DonVi.objects.filter(ten=name).first()
            if don_vi is None:
                latest = DonVi.objects.order_by("-stt_uu_tien").first()
                next_order = (latest.stt_uu_tien + 1) if latest else 1
                don_vi = DonVi.objects.create(khoi=khoi, stt_uu_tien=next_order, ten=name)
            created.append(don_vi)
        return created

    def _ensure_employees(self, positions, donvis, password):
        employees = []
        created_count = 0
        for item in EMPLOYEES:
            emp = Employee.objects.filter(username=item["username"]).first()
            if emp is None:
                emp = Employee.objects.create_user(
                    item["username"],
                    password=password,
                    ho_ten=item["ho_ten"],
                    email=item["email"],
                    chuc_vu=positions[item["pos"]],
                    don_vi=donvis[item["dv"]],
                    ngay_sinh=datetime.date(1990, 1, 1),
                )
                created_count += 1
            employees.append(emp)
        return employees, created_count

    def _ensure_tasks(self, employees):
        now = timezone.now()
        today = now.date()
        tasks = []
        created_count = 0

        for spec in TASKS:
            creator = employees[1]  # test_cbnv_1 làm người tạo chung.
            host = employees[spec["host"]]
            participant_users = [employees[i] for i in spec["parts"]]

            task = Task.objects.filter(title=spec["title"]).first()
            if task is not None:
                tasks.append(task)
                continue

            task = Task.objects.create(
                title=spec["title"],
                created_date=today - datetime.timedelta(days=spec["created_ago"]),
                due_date=today + datetime.timedelta(days=spec["due"]),
                requirement="Dữ liệu demo — tạo bởi seed_work_demo (nhóm 6).",
                created_by=creator,
            )
            created_count += 1

            links = [TaskParticipant(task=task, user=host, role=ParticipantRole.CHU_TRI)]
            for user in participant_users:
                if user.pk != host.pk:
                    links.append(TaskParticipant(task=task, user=user, role=ParticipantRole.THAM_GIA))
            # vai_tro là ENUM: không dùng bulk_create (UNNEST ép varchar[]).
            for link in links:
                link.save()

            if spec.get("opened"):
                Task.objects.filter(pk=task.pk).update(
                    first_opened_at=now - datetime.timedelta(days=1), first_opened_by=host
                )
            if spec.get("evidence"):
                comment = TaskComment.objects.create(task=task, author=host, content="Nộp bằng chứng (demo).")
                TaskAttachment.objects.create(
                    task=task,
                    comment=comment,
                    kind=AttachmentKind.BANG_CHUNG,
                    file="cong-viec/demo/bang_chung_demo.pdf",
                    original_name="bang_chung_demo.pdf",
                    uploaded_by=host,
                )
            if spec.get("approved"):
                Task.objects.filter(pk=task.pk).update(
                    approved_at=now - datetime.timedelta(days=1), approved_by=creator
                )

            tasks.append(task)

        return tasks, created_count
