"""
Dịch vụ gửi email của module Công việc (nhóm 6).

Gửi thông báo đích danh tới người được giao (dùng email trong accounts_employee):
- Giao việc mới        → send_new_task_mail (giữ nguyên hành vi cũ, trước ở views.py).
- Việc sắp đến hạn      → send_due_soon_reminders.
- Việc quá hạn          → send_overdue_reminders.

KHÔNG hardcode cấu hình/mật khẩu SMTP: backend lấy từ settings.MAILERS (đọc từ env trong settings.py).
Dev mặc định là console backend nên không gửi ra ngoài; test dùng locmem.
"""

import datetime
import logging
import ssl

import django
from django.conf import settings
from django.core.mail import get_connection, send_mass_mail
from django.db.models import Prefetch
from django.utils import timezone

from work.models import ParticipantRole, Task, TaskParticipant, TaskStatus
from work.serializers import employee_full_name

logger = logging.getLogger(__name__)

# Chỉ nhắc người phải xử lý: chủ trì + cán bộ tham gia (không gửi người tạo, không gửi chỉ đạo).
REMINDER_ROLES = {ParticipantRole.CHU_TRI, ParticipantRole.THAM_GIA}

# Trạng thái còn phải làm → mới nhắc sắp đến hạn (đã nộp/đã duyệt thì thôi).
DUE_SOON_STATUSES = [TaskStatus.CHO_XU_LY, TaskStatus.DANG_XU_LY]
# Trạng thái quá hạn mà chưa xong.
OVERDUE_STATUSES = [TaskStatus.QUA_HAN, TaskStatus.CHUA_HOAN_THANH]

DEFAULT_DUE_SOON_DAYS = 3


def _legacy_tls_context():
    """SSL context cho mail server cũ yêu cầu TLS 1.0 + SECLEVEL=0."""
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    ctx.set_ciphers("DEFAULT:@SECLEVEL=0")
    ctx.minimum_version = ssl.TLSVersion.TLSv1
    ctx.options &= ~ssl.OP_NO_TLSv1
    ctx.options &= ~ssl.OP_NO_TLSv1_1
    return ctx


def work_mail_connection():
    """
    Kết nối gửi mail theo cấu hình MAILERS["default"] trong settings.py,
    với custom SSL context hỗ trợ mail server cũ (TLS 1.0 / SECLEVEL=0).

    - Django >= 6.1 tự đọc MAILERS, và get_connection(backend=...) đã bị bỏ (báo RuntimeError),
      nên trả None để dùng kết nối mặc định.
    - Django 5.2 (bản ghim trong requirements) chưa hiểu MAILERS, mặc định là SMTP, nên phải
      tạo kết nối theo backend khai báo trong MAILERS (console khi phát triển).
    """
    if django.VERSION >= (6, 1):
        return None

    mailers = getattr(settings, "MAILERS", None)
    backend = None
    if isinstance(mailers, dict):
        backend = mailers.get("default", {}).get("BACKEND")
    return get_connection(backend=backend, ssl_context=_legacy_tls_context())


def send_new_task_mail(task_id):
    """
    Báo công việc mới cho người liên quan (chủ trì, chỉ đạo, cán bộ tham gia), trừ người tạo.
    - Chỉ gửi lúc tạo mới, không gửi khi sửa.
    - Công việc đang ẩn vẫn gửi: người được giao thấy được việc ẩn của mình.
    - Người chưa khai báo email thì bỏ qua.
    Trả về số thư đã gửi.
    """
    task = (
        Task.objects.select_related("created_by")
        .prefetch_related(Prefetch("participants", queryset=TaskParticipant.objects.select_related("user")))
        .filter(pk=task_id)
        .first()
    )
    if task is None:
        return 0

    creator_name = employee_full_name(task.created_by)
    host = next((p.user for p in task.participants.all() if p.role == ParticipantRole.CHU_TRI), None)
    subject = f"[Công việc] Bạn được giao công việc mới: {task.title[:80]}"

    messages = []
    notified = set()
    for participant in task.participants.all():
        user = participant.user
        if user.pk == task.created_by_id or user.pk in notified or not user.email:
            continue
        notified.add(user.pk)
        body = "\n".join([
            f"Xin chào {employee_full_name(user)},",
            "",
            f"{creator_name} vừa giao một công việc mới. Vai trò của bạn: {participant.get_role_display()}.",
            "",
            f"Nội dung công việc: {task.title}",
            f"Yêu cầu xử lý: {task.requirement}",
            f"Ngày tạo: {task.created_date:%d/%m/%Y}",
            f"Hạn xử lý: {task.due_date:%d/%m/%Y}",
            f"Người chủ trì: {employee_full_name(host) if host else '—'}",
            "",
            'Hãy đăng nhập hệ thống, vào mục "Quản Lý Công Việc" để xem chi tiết và xử lý.',
            "",
            "Đây là thư tự động, vui lòng không trả lời thư này.",
        ])
        messages.append((subject, body, None, [user.email]))

    if not messages:
        return 0
    try:
        return send_mass_mail(messages, connection=work_mail_connection())
    except Exception:
        logger.exception("Không gửi được mail báo công việc mới #%s", task_id)
        return 0


def _reminder_recipients(task):
    """Chủ trì + cán bộ tham gia, có email, KHÔNG gồm người tạo. Trả [(user, role_display)], không trùng."""
    recipients = []
    seen = set()
    for participant in task.participants.all():
        user = participant.user
        if (
            participant.role not in REMINDER_ROLES
            or user.pk == task.created_by_id
            or user.pk in seen
            or not user.email
        ):
            continue
        seen.add(user.pk)
        recipients.append((user, participant.get_role_display()))
    return recipients


def _reminder_queryset(statuses, today):
    return (
        Task.objects.with_status(today=today)
        .filter(status__in=statuses)
        .prefetch_related(Prefetch("participants", queryset=TaskParticipant.objects.select_related("user")))
    )


def _send(messages, log_label, connection=None):
    if not messages:
        return 0
    try:
        return send_mass_mail(messages, connection=connection or work_mail_connection())
    except Exception:
        logger.exception("Không gửi được mail %s", log_label)
        return 0


def send_due_soon_reminders(days_ahead=DEFAULT_DUE_SOON_DAYS, today=None, connection=None):
    """
    Nhắc việc SẮP đến hạn (hạn trong khoảng [hôm nay, hôm nay + days_ahead]) và còn phải xử lý.
    Gửi đích danh chủ trì + cán bộ tham gia, không gửi người tạo. Trả về số thư đã gửi.
    """
    today = today or timezone.localdate()
    limit = today + datetime.timedelta(days=days_ahead)
    tasks = _reminder_queryset(DUE_SOON_STATUSES, today).filter(due_date__gte=today, due_date__lte=limit)

    messages = []
    for task in tasks:
        remaining = (task.due_date - today).days
        if remaining > 0:
            han = f"còn {remaining} ngày (hạn {task.due_date:%d/%m/%Y})"
        else:
            han = f"hạn là hôm nay ({task.due_date:%d/%m/%Y})"
        subject = f"[Công việc] Sắp đến hạn xử lý: {task.title[:80]}"
        for user, role_display in _reminder_recipients(task):
            body = "\n".join([
                f"Xin chào {employee_full_name(user)},",
                "",
                f"Công việc bạn đang xử lý sắp đến hạn — {han}. Vai trò của bạn: {role_display}.",
                "",
                f"Nội dung công việc: {task.title}",
                f"Yêu cầu xử lý: {task.requirement}",
                f"Hạn xử lý: {task.due_date:%d/%m/%Y}",
                "",
                'Hãy đăng nhập hệ thống, vào mục "Quản Lý Công Việc" để xử lý trước hạn.',
                "",
                "Đây là thư tự động, vui lòng không trả lời thư này.",
            ])
            messages.append((subject, body, None, [user.email]))

    return _send(messages, "nhắc việc sắp đến hạn", connection=connection)


def send_overdue_reminders(today=None, connection=None):
    """
    Nhắc việc ĐÃ quá hạn mà chưa hoàn thành. Gửi đích danh chủ trì + cán bộ tham gia,
    không gửi người tạo. Trả về số thư đã gửi.
    """
    today = today or timezone.localdate()
    tasks = _reminder_queryset(OVERDUE_STATUSES, today).filter(due_date__lt=today)

    messages = []
    for task in tasks:
        overdue_days = (today - task.due_date).days
        subject = f"[Công việc] ĐÃ QUÁ HẠN: {task.title[:80]}"
        for user, role_display in _reminder_recipients(task):
            body = "\n".join([
                f"Xin chào {employee_full_name(user)},",
                "",
                f"Công việc bạn đang xử lý đã quá hạn {overdue_days} ngày. Vai trò của bạn: {role_display}.",
                "",
                f"Nội dung công việc: {task.title}",
                f"Yêu cầu xử lý: {task.requirement}",
                f"Hạn xử lý: {task.due_date:%d/%m/%Y}",
                "",
                'Hãy đăng nhập hệ thống, vào mục "Quản Lý Công Việc" để xử lý và nộp kết quả sớm nhất.',
                "",
                "Đây là thư tự động, vui lòng không trả lời thư này.",
            ])
            messages.append((subject, body, None, [user.email]))

    return _send(messages, "nhắc việc quá hạn", connection=connection)
