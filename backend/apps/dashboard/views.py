from datetime import timedelta
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.models import StaffProfile
from .models import IncomingDocument, OutgoingDocument, MeetingRoom


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/dashboard/overview/
# ─────────────────────────────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def overview_view(request):
    """
    Tổng hợp số liệu cho Dashboard Nhóm 1.

    Yêu cầu Header: Authorization: Bearer <access_token>

    Response 200:
    {
        "stats": {
            "incoming_total": <int>,
            "outgoing_total": <int>,
            "confidential_total": <int>,
            "tasks_pending": <int>
        },
        "recent_incoming": [
            { "code": "...", "title": "...", "date": "DD/MM/YYYY" },
            ...
        ],
        "recent_outgoing": [...],
        "today_meetings": [
            {
                "room_name": "...",
                "meeting_title": "...",
                "start_time": "HH:MM",
                "end_time": "HH:MM",
                "organizer": "...",
                "status": "upcoming|ongoing|done"
            },
            ...
        ],
        "birthdays": {
            "today": [
                { "full_name": "...", "department": "...", "label": "Hôm nay" },
                ...
            ],
            "tomorrow": [...]
        }
    }
    """
    today = timezone.localdate()
    tomorrow = today + timedelta(days=1)

    # ── 1. Thống kê số liệu tổng quan ──────────────────────────────────────
    user = request.user
    profile = getattr(user, "profile", None)
    is_admin = user.is_superuser or (profile and profile.role == "admin")

    current_year = today.year
    incoming_qs = IncomingDocument.objects.filter(issued_date__year=current_year)
    outgoing_qs = OutgoingDocument.objects.filter(issued_date__year=current_year)

    if not is_admin:
        # Cán bộ thường không được phép xem hoặc thống kê văn bản mật
        incoming_qs = incoming_qs.filter(is_confidential=False)
        outgoing_qs = outgoing_qs.filter(is_confidential=False)
        confidential_total = 0
    else:
        confidential_total = (
            incoming_qs.filter(is_confidential=True).count()
            + outgoing_qs.filter(is_confidential=True).count()
        )

    incoming_total = incoming_qs.count()
    outgoing_total = outgoing_qs.count()
    tasks_pending = 0  # Placeholder — sẽ tích hợp khi Nhóm 6 hoàn tất API Tasks

    stats = {
        "incoming_total": incoming_total,
        "outgoing_total": outgoing_total,
        "confidential_total": confidential_total,
        "tasks_pending": tasks_pending,
    }

    kpis = {
        "incomingCount": incoming_total,
        "outgoingCount": outgoing_total,
        "confidentialCount": confidential_total,
        "tasksCount": tasks_pending,
    }

    # ── 2. Top 5 văn bản đến mới nhất ──────────────────────────────────────
    recent_incoming_qs = IncomingDocument.objects.all()
    if not is_admin:
        recent_incoming_qs = recent_incoming_qs.filter(is_confidential=False)

    recent_incoming = [
        {
            "id": doc.id,
            "code": doc.code,
            "title": doc.title,
            "date": doc.issued_date.strftime("%d/%m/%Y"),
            "sender": doc.sender,
        }
        for doc in recent_incoming_qs[:5]
    ]

    # ── 3. Top 5 văn bản đi mới nhất ───────────────────────────────────────
    recent_outgoing_qs = OutgoingDocument.objects.all()
    if not is_admin:
        recent_outgoing_qs = recent_outgoing_qs.filter(is_confidential=False)

    recent_outgoing = [
        {
            "id": doc.id,
            "code": doc.code,
            "title": doc.title,
            "date": doc.issued_date.strftime("%d/%m/%Y"),
            "recipient": doc.recipient,
        }
        for doc in recent_outgoing_qs[:5]
    ]

    # ── 4. Lịch phòng họp hôm nay ──────────────────────────────────────────
    try:
        from meetings.models import DatPhongHop
        real_bookings = DatPhongHop.objects.filter(
            thoi_gian_bat_dau__date=today,
        ).exclude(trang_thai=DatPhongHop.STATUS_DA_HUY).select_related("phong_hop", "nguoi_dat")
        if real_bookings.exists():
            today_meetings = [
                {
                    "id": f"booking-{b.id}",
                    "room_name": b.phong_hop.ten_phong,
                    "roomName": b.phong_hop.ten_phong,
                    "meeting_title": b.tieu_de,
                    "topic": b.tieu_de,
                    "start_time": timezone.localtime(b.thoi_gian_bat_dau).strftime("%H:%M"),
                    "end_time": timezone.localtime(b.thoi_gian_ket_thuc).strftime("%H:%M"),
                    "time": f"{timezone.localtime(b.thoi_gian_bat_dau).strftime('%H:%M')} - {timezone.localtime(b.thoi_gian_ket_thuc).strftime('%H:%M')}",
                    "organizer": b.don_vi_to_chuc or (b.nguoi_dat.profile.full_name if hasattr(b.nguoi_dat, 'profile') else b.nguoi_dat.username),
                    "status": "ready" if b.trang_thai == DatPhongHop.STATUS_DA_DAT else b.trang_thai,
                }
                for b in real_bookings
            ]
        else:
            today_meetings = [
                {
                    "id": f"room-{m.id}",
                    "room_name": m.room_name,
                    "roomName": m.room_name,
                    "meeting_title": m.meeting_title,
                    "topic": m.meeting_title,
                    "start_time": m.start_time.strftime("%H:%M"),
                    "end_time": m.end_time.strftime("%H:%M"),
                    "time": f"{m.start_time.strftime('%H:%M')} - {m.end_time.strftime('%H:%M')}",
                    "organizer": m.organizer,
                    "status": m.status or "ready",
                }
                for m in MeetingRoom.objects.filter(date=today)
            ]
    except Exception:
        today_meetings = [
            {
                "id": f"room-{m.id}",
                "room_name": m.room_name,
                "roomName": m.room_name,
                "meeting_title": m.meeting_title,
                "topic": m.meeting_title,
                "start_time": m.start_time.strftime("%H:%M"),
                "end_time": m.end_time.strftime("%H:%M"),
                "time": f"{m.start_time.strftime('%H:%M')} - {m.end_time.strftime('%H:%M')}",
                "organizer": m.organizer,
                "status": m.status or "ready",
            }
            for m in MeetingRoom.objects.filter(date=today)
        ]

    # ── 5. Sinh nhật hôm nay (T) và ngày mai (T+1) ─────────────────────────
    today_profiles = StaffProfile.objects.filter(
        birthday__month=today.month,
        birthday__day=today.day,
    ).select_related("user")

    tomorrow_profiles = StaffProfile.objects.filter(
        birthday__month=tomorrow.month,
        birthday__day=tomorrow.day,
    ).select_related("user")

    # Mảng phẳng birthdays chuẩn BirthdayEmployee của React
    birthdays_list = []
    for p in today_profiles:
        birthdays_list.append({
            "id": p.id,
            "name": p.full_name,
            "fullName": p.full_name,
            "full_name": p.full_name,
            "birthdate": f"{today.strftime('%d/%m')} (Hôm nay)",
            "position": p.position or "Chuyên viên",
            "roleTitle": p.position or "Chuyên viên",
            "department": p.department or "Ban Quản lý",
            "unit": p.department or "Ban Quản lý",
            "isToday": True,
            "label": "Hôm nay",
        })
    for p in tomorrow_profiles:
        birthdays_list.append({
            "id": p.id,
            "name": p.full_name,
            "fullName": p.full_name,
            "full_name": p.full_name,
            "birthdate": f"{tomorrow.strftime('%d/%m')} (Ngày mai)",
            "position": p.position or "Chuyên viên",
            "roleTitle": p.position or "Chuyên viên",
            "department": p.department or "Ban Quản lý",
            "unit": p.department or "Ban Quản lý",
            "isToday": False,
            "label": "Ngày mai",
        })

    birthdays_by_day = {
        "today": [
            {
                "full_name": p.full_name,
                "department": p.department,
                "position": p.position,
            }
            for p in today_profiles
        ],
        "tomorrow": [
            {
                "full_name": p.full_name,
                "department": p.department,
                "position": p.position,
            }
            for p in tomorrow_profiles
        ],
    }

    return Response(
        {
            # Hợp đồng chuẩn Hieu.md
            "kpis": kpis,
            "recentIncoming": recent_incoming,
            "recentOutgoing": recent_outgoing,
            "tasks": [],
            "meetingRooms": today_meetings,
            "birthdays": birthdays_list,
            # Tương thích backward
            "stats": stats,
            "recent_incoming": recent_incoming,
            "recent_outgoing": recent_outgoing,
            "today_meetings": today_meetings,
            "birthdays_by_day": birthdays_by_day,
        },
        status=status.HTTP_200_OK,
    )
