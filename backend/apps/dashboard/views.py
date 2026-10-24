from datetime import timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.selectors import nhan_vien_sinh_ngay
from document_templates.selectors import tai_lieu_hieu_luc_xem_duoc
from documents.selectors import tep_dinh_kem_hien_hanh, van_ban_xem_duoc
from signing.selectors import tong_quan_dashboard
from work.models import TaskStatus
from work.selectors import cong_viec_xem_duoc

RECENT_LIMIT = 5
ATTACHMENT_TYPES = {
    "excel": ("xls", "xlsx"),
    "word": ("doc", "docx"),
    "image": ("jpg", "jpeg", "png", "gif", "webp"),
}


def _attachment_type(name):
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    for kind, exts in ATTACHMENT_TYPES.items():
        if ext in exts:
            return kind
    return "pdf"


def _recent_documents(user, loai, date_field, extra_field, extra_key, extra_default):
    """Top văn bản gần nhất mà user được xem, cùng bộ đếm trong năm hiện tại.

    Cả bộ đếm và danh sách dùng selector chung `van_ban_xem_duoc` nên không lộ văn bản HAN_CHE.
    """
    visible = van_ban_xem_duoc(user, loai)
    year_total = visible.filter(**{f"{date_field}__year": timezone.localdate().year}).count()
    documents = list(visible.order_by(f"-{date_field}", "-pk")[:RECENT_LIMIT])

    attachments = {}
    for att in tep_dinh_kem_hien_hanh(loai, [d.pk for d in documents]):
        attachments.setdefault(att.document_id, []).append(
            {"name": att.name, "url": att.path, "type": _attachment_type(att.name), "size": ""}
        )

    items = []
    for doc in documents:
        shown = doc.ngay_van_ban or getattr(doc, date_field)
        items.append(
            {
                "id": doc.pk,
                "code": doc.so_hieu,
                "title": doc.trich_yeu,
                "date": timezone.localtime(shown).strftime("%d/%m/%Y"),
                extra_key: getattr(doc, extra_field) or extra_default,
                "scope": doc.pham_vi,
                "attachments": attachments.get(doc.pk, []),
            }
        )
    return year_total, items


def _tasks(user, today):
    statuses = {
        TaskStatus.CHO_XU_LY: ("processing", "Chờ xử lý", "info"),
        TaskStatus.DANG_XU_LY: ("processing", "Đang xử lý", "info"),
        TaskStatus.CHO_DUYET: ("pending", "Chờ duyệt", "warning"),
        TaskStatus.HOAN_THANH: ("completed", "Hoàn thành", "success"),
        TaskStatus.CHUA_HOAN_THANH: ("overdue", "Chưa hoàn thành", "danger"),
        TaskStatus.QUA_HAN: ("overdue", "Quá hạn", "danger"),
    }
    rows = cong_viec_xem_duoc(user, today).order_by("-pk")[:20]
    tasks = []
    for task in rows:
        task_status, label, variant = statuses[task.status]
        tasks.append({
            "id": str(task.pk),
            "title": task.title,
            "due": task.due_date.strftime("%d/%m/%Y"),
            "status": task_status,
            "statusLabel": label,
            "workStatus": task.status,
            "variant": variant,
        })
    return tasks


def _resources(user):
    rows = tai_lieu_hieu_luc_xem_duoc(user).order_by("pk")[:RECENT_LIMIT]
    resources = []
    for resource in rows:
        name = resource.active_attachments[0].name if resource.active_attachments else ""
        ext = name.rsplit(".", 1)[-1].upper() if "." in name else "DOCX"
        resources.append({
            "code": resource.ky_hieu or f"BM-{resource.pk:02d}",
            "title": resource.tieu_de,
            "format": ext,
        })
    return resources


def _birthday_payload(employee, label, is_today, day):
    full_name = employee.ho_ten or employee.username
    position = employee.chuc_vu.name if employee.chuc_vu else "Chuyên viên"
    department = employee.don_vi.ten if employee.don_vi else "Ban Quản lý"
    return {
        "id": employee.id,
        "name": full_name,
        "fullName": full_name,
        "full_name": full_name,
        "birthdate": f"{day.strftime('%d/%m')} ({label})",
        "position": position,
        "roleTitle": position,
        "department": department,
        "unit": department,
        "isToday": is_today,
        "label": label,
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/dashboard/overview/
# ─────────────────────────────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def overview_view(request):
    """
    Tổng hợp số liệu cho Dashboard Nhóm 1.

    Yêu cầu Header: Authorization: Bearer <access_token>
    """
    today = timezone.localdate()
    tomorrow = today + timedelta(days=1)

    incoming_total, recent_incoming = _recent_documents(
        request.user, "DEN", "ngay_den", "noi_ban_hanh", "sender", "Cơ quan ban hành"
    )
    outgoing_total, recent_outgoing = _recent_documents(
        request.user, "DI", "ngay_ban_hanh", "nguoi_ky", "recipient", "Nơi nhận"
    )
    tasks = _tasks(request.user, today)
    resources = _resources(request.user)
    signing_overview = tong_quan_dashboard(request.user, gioi_han=RECENT_LIMIT)
    signing_pending = signing_overview["so_cho_ky"]
    recent_signing = []
    for item in signing_overview["gan_day"]:
        dt_val = item.get("ngay_trinh", "")
        formatted_date = ""
        if dt_val:
            try:
                formatted_date = timezone.datetime.fromisoformat(dt_val).strftime("%d/%m/%Y")
            except Exception:
                formatted_date = str(dt_val)[:10]
        recent_signing.append({
            **item,
            "code": f"TK-{item['id']:03d}",
            "ma_trinh_ky": f"TK-{item['id']:03d}",
            "title": item.get("tieu_de", ""),
            "submitter": item.get("nguoi_trinh", ""),
            "date": formatted_date,
            "ngay_gui": formatted_date,
            "status": item.get("trang_thai", ""),
            "statusLabel": item.get("nhan_trang_thai", ""),
            "trang_thai_display": item.get("nhan_trang_thai", ""),
        })
    tasks_pending = len([t for t in tasks if t["status"] in ("processing", "pending", "overdue")])
    # Lịch họp lấy từ module Nhóm 7 sau khi được tích hợp vào staging.
    today_meetings = []

    today_users = list(nhan_vien_sinh_ngay(today))
    tomorrow_users = list(nhan_vien_sinh_ngay(tomorrow))

    birthdays_list = [_birthday_payload(u, "Hôm nay", True, today) for u in today_users] + [
        _birthday_payload(u, "Ngày mai", False, tomorrow) for u in tomorrow_users
    ]

    def by_day(users):
        return [
            {"full_name": p["full_name"], "department": p["department"], "position": p["position"]}
            for p in (_birthday_payload(u, "", False, today) for u in users)
        ]

    stats = {
        "incoming_total": incoming_total,
        "outgoing_total": outgoing_total,
        "tasks_pending": tasks_pending,
        "signing_pending": signing_pending,
    }
    kpis = {
        "incomingCount": incoming_total,
        "outgoingCount": outgoing_total,
        "tasksCount": tasks_pending,
        "signingCount": signing_pending,
    }

    return Response(
        {
            # Hợp đồng chuẩn Hieu.md
            "kpis": kpis,
            "recentIncoming": recent_incoming,
            "recentOutgoing": recent_outgoing,
            "tasks": tasks,
            "resources": resources,
            "recentSigning": recent_signing,
            "signingCount": signing_pending,
            "meetingRooms": today_meetings,
            "birthdays": birthdays_list,
            # Tương thích backward
            "stats": stats,
            "recent_incoming": recent_incoming,
            "recent_outgoing": recent_outgoing,
            "recent_signing": recent_signing,
            "today_meetings": today_meetings,
            "birthdays_by_day": {"today": by_day(today_users), "tomorrow": by_day(tomorrow_users)},
        },
        status=status.HTTP_200_OK,
    )
