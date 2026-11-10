"""Selector công khai của module Công việc cho các phân hệ khác (Dashboard Nhóm 1)."""
from .models import Task


def cong_viec_xem_duoc(user, today=None):
    """Công việc user được xem, kèm trạng thái tính theo `today` (cùng quy tắc API công việc)."""
    return Task.objects.visible_to(user).with_status(today)
