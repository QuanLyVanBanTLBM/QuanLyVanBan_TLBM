import calendar
from datetime import date, datetime, time, timedelta
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core import signing
from django.core.paginator import Paginator
from django.core.validators import validate_email
from django.db.models import Q
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from authorization.permissions import is_system_admin, require_permission
from accounts.models import Employee
from .models import BirthdayEmailLog, BirthdayEmailStatus
from .scheduler import VIETNAM_TIME_ZONE, scheduler_history
from .services import (
    can_retry_manually,
    get_eligible_automated_birthday_employees,
    is_birthday_on_date,
    load_birthday_card_token,
    retry_block_reason,
    serialize_staff_birthday,
)

def _active_employee_email(employee: Employee) -> str | None:
    if not employee.is_active:
        return None
    email = (employee.email or "").strip()
    try:
        validate_email(email)
    except ValidationError:
        return None
    return email


def serialize_email_log(log: BirthdayEmailLog) -> dict:
    can_retry = log.employee.is_active and can_retry_manually(log)
    delivery_snapshot = log.delivery_snapshot or {}
    visible_status = "UNKNOWN" if log.delivery_uncertain else log.trang_thai
    return {
        "id": log.id,
        "employee_id": log.employee_id,
        "employee_name": log.employee.ho_ten,
        "position": log.employee.chuc_vu.name if log.employee.chuc_vu else log.employee.chuc_danh or "",
        "department": log.employee.don_vi.ten if log.employee.don_vi else "",
        "birth_date": log.employee.ngay_sinh.strftime("%d/%m/%Y") if log.employee.ngay_sinh else None,
        "sent_date": log.sent_date.strftime("%d/%m/%Y"),
        "sent_date_iso": log.sent_date.isoformat(),
        "sent_at": timezone.localtime(log.sent_at, VIETNAM_TIME_ZONE).strftime("%d/%m/%Y %H:%M:%S") if log.sent_at else None,
        "recipient_email": log.recipient_email,
        "subject": log.subject,
        "card_template": log.card_template,
        "trang_thai": visible_status,
        "trang_thai_display": "Kết quả chưa xác định" if visible_status == "UNKNOWN" else log.get_trang_thai_display(),
        "retry_count": log.retry_count,
        "error_message": log.error_message or "",
        "smtp_response_code": log.smtp_response_code or "",
        "delivery_source": log.delivery_source,
        "delivery_context": delivery_snapshot.get("trigger_source") or (
            "RETRY" if log.last_operator and log.delivery_source != "MANUAL" else None
        ),
        "delivery_uncertain": log.delivery_uncertain,
        "employee_is_active": log.employee.is_active,
        "template_version": delivery_snapshot.get("template_version"),
        "last_operator": log.last_operator,
        "can_retry": can_retry,
        "current_recipient": _active_employee_email(log.employee) if can_retry else None,
        "admin_resend_recipient": (
            _active_employee_email(log.employee) if log.trang_thai != BirthdayEmailStatus.SENDING else None
        ),
        "retry_block_reason": retry_block_reason(log),
    }


def serialize_not_processed_employee(employee: Employee, target_date: date) -> dict:
    return {
        "id": None,
        "employee_id": employee.pk,
        "employee_name": employee.ho_ten,
        "position": employee.chuc_vu.name if employee.chuc_vu else employee.chuc_danh or "",
        "department": employee.don_vi.ten if employee.don_vi else "",
        "birth_date": employee.ngay_sinh.strftime("%d/%m/%Y"),
        "sent_date": target_date.strftime("%d/%m/%Y"),
        "sent_date_iso": target_date.isoformat(),
        "sent_at": None,
        "recipient_email": (employee.email or "").strip(),
        "subject": "",
        "card_template": "",
        "trang_thai": "NOT_PROCESSED",
        "trang_thai_display": "NOT_PROCESSED",
        "retry_count": 0,
        "error_message": "",
        "smtp_response_code": "",
        "delivery_source": "AUTO",
        "delivery_context": None,
        "delivery_uncertain": False,
        "employee_is_active": employee.is_active,
        "template_version": None,
        "last_operator": None,
        "can_retry": False,
        "current_recipient": None,
        "admin_resend_recipient": _active_employee_email(employee),
        "retry_block_reason": None,
    }


def _local_day_bounds(target_date: date) -> tuple[datetime, datetime]:
    start = timezone.make_aware(datetime.combine(target_date, time.min), VIETNAM_TIME_ZONE)
    end = timezone.make_aware(
        datetime.combine(target_date + timedelta(days=1), time.min),
        VIETNAM_TIME_ZONE,
    )
    return start, end


@api_view(["GET"])
@permission_classes([IsAuthenticated, require_permission("view_sinhnhat")])
def calendar_api(request):
    """
    Lịch sinh nhật dương lịch. Chỉ trả số lượng theo ngày, không trả hồ sơ.
    `year` là năm đang xem lịch, không phải năm sinh của CBNV.
    Yêu cầu quyền: view_sinhnhat.
    """
    now = timezone.localdate()
    month_raw = request.GET.get("month", str(now.month))
    year_raw = request.GET.get("year", str(now.year))

    try:
        month = int(month_raw)
        if month < 1 or month > 12:
            return Response({"success": False, "error": "Tháng không hợp lệ (1-12)."}, status=400)
    except (ValueError, TypeError):
        return Response({"success": False, "error": "Tham số tháng phải là số nguyên."}, status=400)

    try:
        year = int(year_raw)
        if year < 1900 or year > 2100:
            return Response({"success": False, "error": "Năm không hợp lệ (1900-2100)."}, status=400)
    except (ValueError, TypeError):
        return Response({"success": False, "error": "Tham số năm phải là số nguyên."}, status=400)

    days_in_month = calendar.monthrange(year, month)[1]
    leap_strategy = getattr(settings, "BIRTHDAY_LEAP_DAY_STRATEGY", "FEB_28")

    birthdays = Employee.objects.filter(is_active=True, is_public=True).exclude(ngay_sinh__isnull=True)
    birthday_filter = Q(ngay_sinh__month=month)
    if not calendar.isleap(year) and leap_strategy == "MAR_01" and month == 3:
        birthday_filter |= Q(ngay_sinh__month=2, ngay_sinh__day=29)
    birth_dates = birthdays.filter(birthday_filter).values_list("ngay_sinh", flat=True)

    days_map = {}
    for birth_date in birth_dates.iterator():
        if birth_date.month == 2 and birth_date.day == 29 and not calendar.isleap(year):
            if leap_strategy == "FEB_28" and month == 2:
                day = 28
            elif leap_strategy == "MAR_01" and month == 3:
                day = 1
            else:
                continue
        else:
            day = birth_date.day
        if day <= days_in_month and is_birthday_on_date(
            birth_date, date(year, month, day), leap_year_strategy=leap_strategy
        ):
            key = str(day)
            days_map[key] = days_map.get(key, 0) + 1

    return Response({
        "success": True,
        "month": month,
        "year": year,
        "days_in_month": days_in_month,
        "total_staff": sum(days_map.values()),
        "days": days_map,
    })
@api_view(["GET"])
@permission_classes([IsAuthenticated, require_permission("view_sinhnhat")])
def day_birthdays_api(request):
    """
    API lấy danh sách CBNV có sinh nhật dương lịch trong một ngày, có phân trang.
    Contract: GET /api/birthdays/day/?month=&day=&year=&page=&page_size=
    Yêu cầu quyền: view_sinhnhat.
    """
    now = timezone.localdate()
    month_raw = request.GET.get("month", str(now.month))
    day_raw = request.GET.get("day", str(now.day))
    year_raw = request.GET.get("year", str(now.year))
    page_raw = request.GET.get("page", "1")
    page_size_raw = request.GET.get("page_size", "10")

    try:
        month = int(month_raw)
        if month < 1 or month > 12:
            return Response({"success": False, "error": "Tháng không hợp lệ (1-12)."}, status=400)
    except (ValueError, TypeError):
        return Response({"success": False, "error": "Tham số tháng phải là số nguyên."}, status=400)

    try:
        year = int(year_raw)
        if year < 1900 or year > 2100:
            return Response({"success": False, "error": "Năm không hợp lệ (1900-2100)."}, status=400)
    except (ValueError, TypeError):
        return Response({"success": False, "error": "Tham số năm phải là số nguyên."}, status=400)

    days_in_month = calendar.monthrange(year, month)[1]
    try:
        day = int(day_raw)
        if day < 1 or day > days_in_month:
            return Response(
                {"success": False, "error": f"Ngày không hợp lệ trong tháng {month}/{year} (tối đa {days_in_month} ngày)."},
                status=400,
            )
    except (ValueError, TypeError):
        return Response({"success": False, "error": "Tham số ngày phải là số nguyên."}, status=400)

    try:
        page = int(page_raw)
        page_size = int(page_size_raw)
    except (ValueError, TypeError):
        return Response({"success": False, "error": "Trang và kích thước trang phải là số nguyên."}, status=400)
    if page < 1 or page_size < 1 or page_size > 50:
        return Response({"success": False, "error": "Trang phải từ 1; kích thước trang từ 1 đến 50."}, status=400)

    target_date = date(year, month, day)
    leap_strategy = getattr(settings, "BIRTHDAY_LEAP_DAY_STRATEGY", "FEB_28")

    birthday_filter = Q(ngay_sinh__month=month, ngay_sinh__day=day)
    if not calendar.isleap(year) and (
        (leap_strategy == "FEB_28" and month == 2 and day == 28)
        or (leap_strategy == "MAR_01" and month == 3 and day == 1)
    ):
        birthday_filter |= Q(ngay_sinh__month=2, ngay_sinh__day=29)

    staff_on_day = (
        Employee.objects.filter(is_active=True, is_public=True)
        .exclude(ngay_sinh__isnull=True)
        .filter(birthday_filter)
        .select_related("don_vi", "chuc_vu")
        .order_by("chuc_vu__display_order", "don_vi__stt_uu_tien", "ho_ten", "id")
    )

    paginator = Paginator(staff_on_day, page_size)
    current_page_data = paginator.get_page(page)

    return Response({
        "success": True,
        "date": target_date.strftime("%d/%m/%Y"),
        "day": day,
        "month": month,
        "year": year,
        "total": paginator.count,
        "page": current_page_data.number,
        "total_pages": paginator.num_pages,
        "has_next": current_page_data.has_next(),
        "has_previous": current_page_data.has_previous(),
        "employees": [serialize_staff_birthday(emp) for emp in current_page_data],
    })


@api_view(["POST"])
@permission_classes([AllowAny])
def birthday_card_api(request):
    """Trả dữ liệu tối thiểu cho thiệp web theo token ký, không cần tài khoản."""
    token = request.data.get("token", "") if isinstance(request.data, dict) else ""
    token = token.strip() if isinstance(token, str) else ""
    if not token:
        return Response({"success": False, "error": "Thiếu liên kết thiệp hợp lệ."}, status=400)

    try:
        card = load_birthday_card_token(token)
    except signing.SignatureExpired:
        return Response({"success": False, "error": "Liên kết thiệp đã hết hạn."}, status=410)
    except signing.BadSignature:
        return Response({"success": False, "error": "Liên kết thiệp không hợp lệ."}, status=400)

    response = Response({"success": True, "card": card})
    response["Cache-Control"] = "private, no-store"
    return response


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def birthday_email_logs_api(request):
    """
    API xem nhật ký gửi email chúc mừng sinh nhật tự động và thủ công.
    `date=YYYY-MM-DD` trả nhật ký gửi trong ngày hoặc thuộc kỳ sinh nhật đó, cùng nhân viên đủ điều kiện
    chưa có log; mặc định là ngày hiện tại theo múi giờ Việt Nam.
    `month`/`year` tiếp tục được hỗ trợ cho các client cũ.
    Tạm thời chỉ quản trị hệ thống (superuser, nhóm ADMIN) được xem cho đến khi DDL có quyền riêng.
    """
    if not is_system_admin(request.user):
        return Response(
            {"success": False, "error": "birthdays.messages.permissionDenied"},
            status=403,
        )

    logs = (
        BirthdayEmailLog.objects.all()
        .select_related("employee", "employee__don_vi", "employee__chuc_vu")
        .order_by("-sent_at", "-pk")
    )
    selected_date = None
    date_raw = request.GET.get("date")
    month_raw = request.GET.get("month")
    year_raw = request.GET.get("year")
    trang_thai_raw = request.GET.get("trang_thai")

    if date_raw:
        try:
            selected_date = date.fromisoformat(date_raw)
        except (TypeError, ValueError):
            return Response(
                {"success": False, "error": "birthdays.messages.invalidDate"},
                status=400,
            )

        start, end = _local_day_bounds(selected_date)
        logs = logs.filter(Q(sent_at__gte=start, sent_at__lt=end) | Q(sent_date=selected_date))
    elif month_raw or year_raw:
        # Keep the existing month/year API contract, but filter by send time rather than birthday date.
        if month_raw:
            try:
                month = int(month_raw)
            except ValueError:
                return Response(
                    {"success": False, "error": "Tham số tháng phải là số nguyên."},
                    status=400,
                )
            if month < 1 or month > 12:
                return Response(
                    {"success": False, "error": "Tháng không hợp lệ (1-12)."},
                    status=400,
                )
            logs = logs.filter(sent_at__month=month)

        if year_raw:
            try:
                logs = logs.filter(sent_at__year=int(year_raw))
            except ValueError:
                pass
    else:
        selected_date = timezone.localdate(timezone=VIETNAM_TIME_ZONE)
        start, end = _local_day_bounds(selected_date)
        logs = logs.filter(Q(sent_at__gte=start, sent_at__lt=end) | Q(sent_date=selected_date))

    normalized_trang_thai = None
    if trang_thai_raw:
        normalized_trang_thai = trang_thai_raw.upper()
        if normalized_trang_thai not in (*BirthdayEmailStatus.values, "NOT_PROCESSED", "UNKNOWN"):
            return Response(
                {"success": False, "error": "birthdays.messages.invalidStatus"},
                status=400,
            )
        if normalized_trang_thai == "NOT_PROCESSED":
            logs = logs.none()
        elif normalized_trang_thai == "UNKNOWN":
            logs = logs.filter(delivery_uncertain=True)
        else:
            logs = logs.filter(trang_thai=normalized_trang_thai, delivery_uncertain=False)

    if selected_date is None:
        paginator = Paginator(logs, 15)
        page_obj = paginator.get_page(request.GET.get("page", 1))
        page_logs = [serialize_email_log(log) for log in page_obj]
        total = paginator.count
        page_number = page_obj.number
        total_pages = paginator.num_pages
    else:
        log_items = list(logs)
        rows = [
            (log.sent_at or datetime.min.replace(tzinfo=VIETNAM_TIME_ZONE), log.pk, serialize_email_log(log))
            for log in log_items
        ]
        if normalized_trang_thai in (None, "NOT_PROCESSED"):
            logged_employee_ids = set(
                BirthdayEmailLog.objects.filter(sent_date=selected_date)
                .values_list("employee_id", flat=True)
            )
            unprocessed = get_eligible_automated_birthday_employees(selected_date)
            for employee in unprocessed:
                if employee.pk not in logged_employee_ids:
                    rows.append((datetime.min.replace(tzinfo=VIETNAM_TIME_ZONE), -employee.pk,
                        serialize_not_processed_employee(employee, selected_date)))
        rows.sort(key=lambda item: (item[0], item[1]), reverse=True)
        paginator = Paginator(rows, 15)
        page_obj = paginator.get_page(request.GET.get("page", 1))
        page_logs = [entry[2] for entry in page_obj.object_list]
        total = paginator.count
        page_number = page_obj.number
        total_pages = paginator.num_pages

    return Response({
        "success": True,
        "date": selected_date.isoformat() if selected_date else None,
        "total": total,
        "page": page_number,
        "total_pages": total_pages,
        "logs": page_logs,
        "scheduler": scheduler_history(selected_date) if selected_date else None,
    })


