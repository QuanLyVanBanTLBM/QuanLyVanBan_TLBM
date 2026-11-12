import calendar
import smtplib
from datetime import date, timedelta
from urllib.parse import urlencode, urlsplit, urlunsplit

from django.conf import settings
from django.core import signing
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.db import transaction
from django.db.models import Q
from django.template.loader import render_to_string
from django.utils import timezone

from accounts.models import Employee
from .models import BirthdayEmailLog, BirthdayEmailSource, BirthdayEmailStatus
from .templates_service import LAYOUT_DEFAULTS, pick_hybrid_template, render_email_draft

PRE_ACCEPTANCE_SMTP_ERRORS = (
    smtplib.SMTPAuthenticationError,
    smtplib.SMTPConnectError,
    smtplib.SMTPDataError,
    smtplib.SMTPHeloError,
    smtplib.SMTPNotSupportedError,
    smtplib.SMTPRecipientsRefused,
    smtplib.SMTPSenderRefused,
)

STALE_SENDING_NOTE = "Kết quả gửi không xác định, cần đối soát."
SKIPPED_EMAIL_PREFIX = "Bỏ qua:"
BIRTHDAY_CARD_TOKEN_SALT = "birthdays.animated-card"
BIRTHDAY_CARD_TOKEN_MAX_AGE_SECONDS = 30 * 24 * 60 * 60
LEADERSHIP_POSITIONS = (
    "Chủ tịch HĐQT", "Phó Chủ tịch HĐQT", "Thành viên HĐQT",
    "Tổng Giám đốc", "Lãnh đạo cơ quan", "Phó Tổng Giám đốc điều hành",
    "Phó Tổng Giám đốc kinh doanh", "Giám đốc Khối", "Phó Giám đốc Khối",
    "Giám đốc Vùng", "Giám đốc", "Phó Giám đốc", "Giám đốc Ban",
    "Phụ trách Ban", "Trưởng Ban", "Phó Ban", "Trưởng Bộ phận", "Trưởng phòng", "Phó phòng",
)


def is_birthday_on_date(birth_date: date, target_date: date, leap_year_strategy: str = "FEB_28") -> bool:
    """
    Xác định xem ngày `target_date` có phải là ngày sinh nhật của `birth_date` hay không.
    Ngày sinh được hiểu theo dương lịch. Trong năm không nhuận, ngày sinh
    29/02 được ghi nhận vào 28/02 theo quy tắc đã thống nhất.

    Quy tắc cấu hình leap_year_strategy:
    - "SKIP": Không chuyển ngày 29/02 trong năm không nhuận.
    - "FEB_28": Chúc mừng vào ngày 28/02 nếu năm đích không nhuận (mặc định).
    - "MAR_01": Chúc mừng vào ngày 01/03 nếu năm đích không nhuận.
    """
    if birth_date is None or target_date is None:
        return False

    # Trường hợp thông thường: trùng cả tháng và ngày
    if birth_date.month == target_date.month and birth_date.day == target_date.day:
        return True

    # Trường hợp sinh ngày 29/02 trong năm không nhuận
    if birth_date.month == 2 and birth_date.day == 29:
        is_target_leap = calendar.isleap(target_date.year)
        if not is_target_leap:
            if leap_year_strategy == "FEB_28" and target_date.month == 2 and target_date.day == 28:
                return True
            if leap_year_strategy == "MAR_01" and target_date.month == 3 and target_date.day == 1:
                return True

    return False


def serialize_staff_birthday(employee: Employee) -> dict:
    """
    Chỉ trả đúng các trường tối thiểu trong hợp đồng API sinh nhật.
    Không công bố năm sinh, tuổi, email, số điện thoại hay tài khoản.
    """
    birth_date = employee.ngay_sinh
    chuc_vu_name = employee.chuc_vu.name if employee.chuc_vu else ""
    don_vi_name = employee.don_vi.ten if employee.don_vi else ""
    return {
        "id": employee.id,
        "ho_ten": employee.ho_ten,
        "ngay": birth_date.day if birth_date else None,
        "thang": birth_date.month if birth_date else None,
        "chuc_vu": chuc_vu_name,
        "don_vi": don_vi_name,
    }


def _birthday_card_data(employee: Employee) -> dict:
    brand_name = getattr(settings, "BRAND_NAME", "Bảo Long Insurance")
    return {
        "employee_name": employee.ho_ten,
        "birthday_date": employee.ngay_sinh.strftime("%d/%m") if employee.ngay_sinh else "",
        "department": employee.don_vi.ten if employee.don_vi else "Cơ quan",
        "position": employee.chuc_vu.name if employee.chuc_vu else "Cán bộ",
        "brand_name": brand_name,
        "organization_name": getattr(settings, "ORGANIZATION_NAME", brand_name),
    }


def generate_birthday_card_token(employee: Employee) -> str:
    """Ký snapshot tối thiểu của thiệp để người nhận xem mà không cần đăng nhập."""
    return signing.dumps(_birthday_card_data(employee), salt=BIRTHDAY_CARD_TOKEN_SALT, compress=True)


def load_birthday_card_token(token: str) -> dict:
    """Xác minh chữ ký và thời hạn token thiệp (30 ngày)."""
    return signing.loads(
        token,
        salt=BIRTHDAY_CARD_TOKEN_SALT,
        max_age=BIRTHDAY_CARD_TOKEN_MAX_AGE_SECONDS,
    )


def generate_birthday_card_url(employee: Employee, layout: str | None = None) -> str:
    """Tạo URL thiệp từ override riêng hoặc địa chỉ frontend dùng cho email."""
    base_url = (getattr(settings, "BIRTHDAY_CARD_BASE_URL", "") or "").strip()
    if not base_url:
        frontend_url = (getattr(settings, "SIGNING_FRONTEND_URL", "") or "").strip().rstrip("/")
        if not frontend_url:
            return ""
        base_url = f"{frontend_url}/birthday-card.html"

    parsed = urlsplit(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""

    fragment = urlencode({"token": generate_birthday_card_token(employee)})
    if layout is not None:
        folder = parsed.path.rsplit("/", 1)[0]
        parsed = parsed._replace(path=f"{folder}/birthday-cards/{layout}.html", query="")
    return urlunsplit(parsed._replace(fragment=fragment))


def generate_birthday_email_html(
    employee: Employee,
    card_template: str = "GOLDEN",
    card_url: str | None = None,
) -> str:
    """
    Kết xuất thiệp email theo thiết kế Bảo Long và dữ liệu của cán bộ nhân viên.

    TUÂN THỦ QUY ĐỊNH BẢO MẬT:
    - Tuyệt đối không hiển thị tuổi hoặc năm sinh trong nội dung thư chúc mừng.
    """
    card_data = _birthday_card_data(employee)
    return render_to_string(
        "birthdays/birthday_email.html",
        {
            **card_data,
            "chuc_danh": (employee.chuc_danh or "").strip(),
            "birthday_card_url": card_url if card_url is not None else generate_birthday_card_url(employee),
        },
    )


def generate_birthday_email_text(employee: Employee, card_url: str | None = None) -> str:
    """Tạo bản text khớp nội dung thiệp HTML và thông tin công tác của nhân viên."""
    birthday_date = employee.ngay_sinh.strftime("%d/%m") if employee.ngay_sinh else ""
    department = employee.don_vi.ten if employee.don_vi else "Cơ quan"
    position = employee.chuc_vu.name if employee.chuc_vu else "Cán bộ"
    job_title = (employee.chuc_danh or "").strip()
    brand_name = getattr(settings, "BRAND_NAME", "Bảo Long Insurance")
    organization_name = getattr(settings, "ORGANIZATION_NAME", brand_name)
    text = (
        f"Kính gửi {employee.ho_ten},\n\n"
        f"Nhân dịp sinh nhật ngày {birthday_date} của {employee.ho_ten}, Ban Lãnh đạo cùng toàn thể cán bộ nhân viên "
        f"{organization_name} trân trọng gửi đến {employee.ho_ten} lời chúc mừng sinh nhật nồng nhiệt và tốt đẹp nhất. "
        f"Chúc {employee.ho_ten} bước sang tuổi mới luôn dồi dào sức khỏe, tràn đầy năng lượng và đón nhận thật nhiều "
        "niềm vui, hạnh phúc viên mãn bên gia đình, người thân.\n\n"
        f"Ban Lãnh đạo ghi nhận và trân trọng cảm ơn những nỗ lực, cống hiến và tinh thần trách nhiệm mà "
        f"{employee.ho_ten} đã không ngừng đóng góp cho sự phát triển vững mạnh của {department} cũng như ngôi nhà chung "
        f"{organization_name} trong suốt thời gian qua.\n\n"
        f"Kính chúc {employee.ho_ten} trên cương vị {position} sẽ luôn vững vàng nhiệt huyết, tiếp tục phát huy tối đa "
        "năng lực để hoàn thành xuất sắc mọi mục tiêu đề ra, gặt hái thêm nhiều thành công rực rỡ và cùng tập thể "
        f"{brand_name} lan tỏa những giá trị tốt đẹp đến khách hàng và cộng đồng.\n\n"
        f"Thân mến,\nBan Lãnh đạo và tập thể {brand_name}"
    )
    resolved_card_url = card_url if card_url is not None else generate_birthday_card_url(employee)
    if job_title:
        text += f"\n\nChức danh: {job_title}"
    if resolved_card_url:
        text += f"\n\nMở thiệp chúc mừng sinh nhật: {resolved_card_url}"
    return text


def other_birthday_logs(employee_id: int, sent_date: date):
    return BirthdayEmailLog.objects.filter(
        employee_id=employee_id, sent_date__year=sent_date.year,
    ).exclude(sent_date=sent_date)


def _email_log(employee: Employee, sent_date: date, recipient: str, subject: str) -> BirthdayEmailLog | None:
    # Serialize creation across effective birthday dates if the employee record changed.
    with transaction.atomic():
        locked_employee = Employee.objects.select_for_update().filter(pk=employee.pk, is_active=True).first()
        if not locked_employee or other_birthday_logs(employee.pk, sent_date).exists():
            return None
        log, _ = BirthdayEmailLog.objects.get_or_create(
            employee=locked_employee,
            sent_date=sent_date,
            defaults={
                "sent_at": timezone.now(),
                "recipient_email": recipient or "unknown",
                "subject": subject,
                "card_template": "GOLDEN",
                "trang_thai": BirthdayEmailStatus.PENDING,
            },
        )
        return log


def _safe_error(error: Exception) -> str:
    smtp_code = getattr(error, "smtp_code", None)
    if smtp_code is not None:
        return f"{type(error).__name__} (SMTP {smtp_code})"
    return type(error).__name__


def can_retry_manually(log: BirthdayEmailLog) -> bool:
    return (
        log.trang_thai == BirthdayEmailStatus.FAILED
        or (
            log.trang_thai == BirthdayEmailStatus.RETRY
            and log.employee.chuc_vu is not None
            and log.employee.chuc_vu.name in LEADERSHIP_POSITIONS
        )
    ) and not (
        log.delivery_uncertain or (log.error_message or "").startswith(STALE_SENDING_NOTE)
    )


def _claim_delivery(
    log: BirthdayEmailLog, recipient: str, subject: str, max_retries: int = 0,
    *, operator: str | None = None, manual_snapshot: dict | None = None,
) -> bool:
    """Use the same locked log row for automatic, manual, and retry claims."""
    with transaction.atomic():
        employee = (
            Employee.objects.select_related("chuc_vu", "don_vi")
            .select_for_update(of=("self",)).filter(pk=log.employee_id, is_active=True).first()
        )
        if not employee:
            return False
        locked_log = (
            BirthdayEmailLog.objects.select_for_update()
            .filter(pk=log.pk)
            .first()
        )
        if not locked_log:
            return False
        locked_log.employee = employee

        if manual_snapshot is not None:
            is_eligible = locked_log.trang_thai == BirthdayEmailStatus.PENDING
        elif operator is not None:
            is_eligible = can_retry_manually(locked_log)
        else:
            is_eligible = locked_log.delivery_source == BirthdayEmailSource.AUTO and (
                locked_log.trang_thai == BirthdayEmailStatus.PENDING
                or (
                    locked_log.trang_thai in (BirthdayEmailStatus.RETRY, BirthdayEmailStatus.FAILED)
                    and locked_log.retry_count <= max_retries
                )
            )
            if employee.chuc_vu and employee.chuc_vu.name in LEADERSHIP_POSITIONS:
                is_eligible = False
            if locked_log.next_retry_at and locked_log.next_retry_at > timezone.now():
                is_eligible = False
        is_eligible = is_eligible and not (
            locked_log.delivery_uncertain or (locked_log.error_message or "").startswith(STALE_SENDING_NOTE)
        )
        if is_eligible and other_birthday_logs(employee.pk, locked_log.sent_date).filter(
            Q(trang_thai__in=(BirthdayEmailStatus.SENDING, BirthdayEmailStatus.SUCCESS))
            | Q(delivery_uncertain=True)
        ).exists():
            is_eligible = False
        if not is_eligible:
            log.refresh_from_db()
            return False

        if manual_snapshot is not None:
            locked_log.delivery_source = BirthdayEmailSource.MANUAL
            locked_log.card_template = manual_snapshot["layout"]
            locked_log.delivery_snapshot = manual_snapshot
        elif locked_log.delivery_snapshot is None:
            snapshot = _default_snapshot(locked_log.employee)
            locked_log.delivery_snapshot = snapshot
            if "layout" in snapshot:
                locked_log.card_template = snapshot["layout"]
            if "subject" in snapshot and snapshot["subject"]:
                locked_log.subject = snapshot["subject"]
                subject = snapshot["subject"]
        if operator is not None:
            locked_log.last_operator = operator

        locked_log.trang_thai = BirthdayEmailStatus.SENDING
        locked_log.recipient_email = recipient
        locked_log.subject = subject
        locked_log.error_message = None
        locked_log.smtp_response_code = None
        locked_log.sent_at = timezone.now()
        locked_log.save(
            update_fields=[
                "trang_thai",
                "recipient_email",
                "subject",
                "error_message",
                "smtp_response_code",
                "sent_at",
                "delivery_source",
                "delivery_snapshot",
                "card_template",
                "last_operator",
                "updated_at",
            ]
        )

    log.refresh_from_db()
    return True


def _record_delivery_result(
    log: BirthdayEmailLog,
    new_status: str,
    error_message: str = "",
    *,
    sent_at=None,
    smtp_response_code: str = None,
    uncertain: bool = False,
) -> bool:
    """
    Record the delivery outcome under a row lock (select_for_update).
    Only updates if currently SENDING.
    """
    with transaction.atomic():
        locked_log = (
            BirthdayEmailLog.objects.select_for_update()
            .filter(pk=log.pk)
            .first()
        )
        if not locked_log or locked_log.trang_thai != BirthdayEmailStatus.SENDING:
            if locked_log:
                log.refresh_from_db()
            return False

        now = timezone.now()
        locked_log.trang_thai = new_status
        locked_log.delivery_uncertain = uncertain
        update_fields = ["trang_thai", "delivery_uncertain", "updated_at"]

        if new_status == BirthdayEmailStatus.SUCCESS:
            locked_log.sent_at = sent_at or now
            locked_log.error_message = None
            locked_log.smtp_response_code = smtp_response_code or "250"
            locked_log.next_retry_at = None
            update_fields.extend(["sent_at", "error_message", "smtp_response_code", "next_retry_at"])
        elif new_status in (BirthdayEmailStatus.RETRY, BirthdayEmailStatus.FAILED):
            locked_log.retry_count = locked_log.retry_count + 1
            locked_log.error_message = error_message
            locked_log.next_retry_at = None
            if smtp_response_code:
                locked_log.smtp_response_code = smtp_response_code
                update_fields.append("smtp_response_code")
            update_fields.extend(["retry_count", "error_message", "next_retry_at"])
        else:
            locked_log.error_message = error_message
            update_fields.append("error_message")

        locked_log.save(update_fields=update_fields)

    log.refresh_from_db()
    return True


def _mark_invalid_email(log: BirthdayEmailLog, reason: str) -> bool:
    """Persist invalid or missing recipients without adding a new trang_thai value to the DDL enum."""
    with transaction.atomic():
        locked_log = BirthdayEmailLog.objects.select_for_update().filter(pk=log.pk).first()
        if (
            not locked_log
            or locked_log.delivery_source != BirthdayEmailSource.AUTO
            or locked_log.delivery_uncertain
            or locked_log.trang_thai in (BirthdayEmailStatus.SUCCESS, BirthdayEmailStatus.SENDING)
            or (locked_log.error_message or "").startswith(STALE_SENDING_NOTE)
        ):
            return False

        locked_log.trang_thai = BirthdayEmailStatus.FAILED
        locked_log.error_message = f"{SKIPPED_EMAIL_PREFIX} {reason}"
        locked_log.next_retry_at = None
        locked_log.save(update_fields=["trang_thai", "error_message", "next_retry_at", "updated_at"])

    log.refresh_from_db()
    return True


def require_delivery_backend(allow_test_email_backend: bool = False) -> None:
    smtp_backend = "django.core.mail.backends.smtp.EmailBackend"
    memory_backend = "django.core.mail.backends.locmem.EmailBackend"

    current_backend = None
    if hasattr(settings, "MAILERS"):
        mailers_dict = getattr(settings, "MAILERS", {})
        default_mailer = mailers_dict.get("default", {})
        current_backend = default_mailer.get("BACKEND")
    elif hasattr(settings, "EMAIL_BACKEND"):
        try:
            current_backend = settings.EMAIL_BACKEND
        except AttributeError:
            current_backend = None

    if not current_backend:
        current_backend = smtp_backend

    if current_backend != smtp_backend and not (
        allow_test_email_backend and (current_backend == memory_backend or "locmem" in current_backend)
    ):
        raise ImproperlyConfigured("Birthday email delivery requires an SMTP backend.")


def _default_snapshot(employee: Employee, *, layout: str | None = None, seed: int | str | None = None) -> dict:
    position_name = employee.chuc_vu.name if employee.chuc_vu else ""
    try:
        if layout is None:
            layout, template_draft = pick_hybrid_template(position_name, seed=seed)
        else:
            template_draft = LAYOUT_DEFAULTS.get(layout, LAYOUT_DEFAULTS["01"])

        card_url = generate_birthday_card_url(employee, layout)
        data = {
            **_birthday_card_data(employee),
            "chuc_danh": (employee.chuc_danh or "").strip(),
        }
        draft = {
            "layout": layout,
            "template_id": f"layout:{layout}",
            "subject": template_draft["subject"],
            "message": template_draft["message"],
        }
        subject, snapshot = render_email_draft(draft, data, card_url)
        return {
            **snapshot,
            "subject": subject,
        }
    except Exception:
        card_url = generate_birthday_card_url(employee)
        return {
            "layout": "GOLDEN",
            "template_version": "default:1",
            "html": generate_birthday_email_html(employee, card_url=card_url),
            "text": generate_birthday_email_text(employee, card_url=card_url),
            "subject": f"[{getattr(settings, 'BRAND_NAME', 'Bảo Long Insurance')}] Chúc mừng sinh nhật {employee.ho_ten}",
        }


def deliver_claimed_email(log: BirthdayEmailLog, max_retries: int = 0) -> None:
    uncertain = False
    error_message = ""
    smtp_code = None
    try:
        accepted = send_mail(
            subject=log.subject,
            message=log.delivery_snapshot["text"],
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "") or None,
            recipient_list=[log.recipient_email],
            html_message=log.delivery_snapshot["html"],
            fail_silently=False,
        )
        if accepted != 1:
            error_message = "SMTP did not accept the message."
    except PRE_ACCEPTANCE_SMTP_ERRORS as exc:
        error_message = _safe_error(exc)
        code = getattr(exc, "smtp_code", None)
        smtp_code = str(code) if code is not None else None
    except Exception as exc:
        uncertain = True
        error_message = f"{STALE_SENDING_NOTE} {_safe_error(exc)}"

    if not error_message:
        _record_delivery_result(log, BirthdayEmailStatus.SUCCESS, smtp_response_code="250 OK")
        return

    next_status = (
        BirthdayEmailStatus.RETRY
        if not uncertain and log.retry_count < max_retries
        else BirthdayEmailStatus.FAILED
    )
    _record_delivery_result(
        log, next_status, error_message, smtp_response_code=smtp_code, uncertain=uncertain,
    )


def send_automated_birthday_emails(
    target_date: date = None,
    max_retries: int = 3,
    leap_year_strategy: str = None,
    allow_test_email_backend: bool = False,
    *,
    username: str | None = None,
) -> dict:
    """Send due non-leadership birthdays and eligible automatic retries."""
    if target_date is None:
        target_date = timezone.localdate()
    if not 0 <= max_retries <= 10:
        raise ValueError("max_retries must be between 0 and 10")

    require_delivery_backend(allow_test_email_backend)

    if leap_year_strategy is None:
        leap_year_strategy = getattr(settings, "BIRTHDAY_LEAP_DAY_STRATEGY", "FEB_28")
    if leap_year_strategy not in ("SKIP", "FEB_28", "MAR_01"):
        raise ValueError("Invalid leap-year birthday strategy")

    now = timezone.now()
    stale_cutoff = now - timedelta(minutes=30)
    stale_logs = BirthdayEmailLog.objects.filter(
        trang_thai=BirthdayEmailStatus.SENDING,
        updated_at__lt=stale_cutoff,
    )
    if username is not None:
        stale_logs = stale_logs.filter(employee__username=username, sent_date=target_date)
    stale_failed_count = stale_logs.update(
        trang_thai=BirthdayEmailStatus.FAILED,
        error_message=STALE_SENDING_NOTE,
        delivery_uncertain=True,
        next_retry_at=None,
        updated_at=now,
    )

    active_employees = (
        Employee.objects.filter(is_active=True)
        .exclude(ngay_sinh__isnull=True)
        .exclude(chuc_vu__name__in=LEADERSHIP_POSITIONS)
        .select_related("don_vi", "chuc_vu")
    )
    if username is not None:
        active_employees = active_employees.filter(username=username)
    eligible_employees = [
        emp
        for emp in active_employees
        if is_birthday_on_date(emp.ngay_sinh, target_date, leap_year_strategy=leap_year_strategy)
    ]
    retry_start_date = target_date - timedelta(days=3)
    retry_logs = [] if username is not None else list(
        BirthdayEmailLog.objects.filter(
            trang_thai=BirthdayEmailStatus.RETRY,
            delivery_source=BirthdayEmailSource.AUTO,
            delivery_uncertain=False,
            employee__is_active=True,
            sent_date__gte=retry_start_date,
            sent_date__lte=target_date,
        )
        .exclude(employee__chuc_vu__name__in=LEADERSHIP_POSITIONS)
        .filter(Q(next_retry_at__isnull=True) | Q(next_retry_at__lte=now))
        .select_related("employee", "employee__don_vi", "employee__chuc_vu")
        .order_by("sent_date", "id")
    )
    candidate_keys = {(employee.id, target_date) for employee in eligible_employees}
    candidate_keys.update((log.employee_id, log.sent_date) for log in retry_logs)

    results = {
        "target_date": target_date.strftime("%d/%m/%Y"),
        "total_eligible": len(candidate_keys),
        "sent_count": 0,
        "skipped_count": 0,
        "failed_count": stale_failed_count,
        "stale_failed_count": stale_failed_count,
        "retry_count": 0,
        "details": [],
    }

    brand_name = getattr(settings, "BRAND_NAME", "Bảo Long Insurance")

    def process_delivery(employee: Employee, sent_date: date, existing_log=None) -> None:
        recipient = (
            existing_log.recipient_email
            if existing_log is not None
            else (employee.email or "")
        ).strip()
        subject = (
            existing_log.subject
            if existing_log is not None
            else f"[{brand_name}] Thư chúc mừng sinh nhật cán bộ nhân viên: {employee.ho_ten}"
        )
        claimed = False
        try:
            log = existing_log or _email_log(employee, sent_date, recipient, subject)
            if log is None:
                results["skipped_count"] += 1
                return
            try:
                validate_email(recipient)
            except ValidationError:
                _mark_invalid_email(log, "Địa chỉ email không hợp lệ hoặc bị để trống.")
                results["skipped_count"] += 1
                results["details"].append({
                    "employee_id": employee.id,
                    "full_name": employee.ho_ten,
                    "skipped": True,
                    "trang_thai": BirthdayEmailStatus.FAILED,
                    "reason": "Địa chỉ email không hợp lệ hoặc bị để trống.",
                })
                return

            claimed = _claim_delivery(log, recipient, subject, max_retries)
            if not claimed:
                reason = {
                    BirthdayEmailStatus.SUCCESS: "Đã gửi thành công trước đó.",
                    BirthdayEmailStatus.SENDING: "Đang được xử lý bởi tiến trình khác.",
                    BirthdayEmailStatus.FAILED: (
                        STALE_SENDING_NOTE
                        if (log.error_message or "").startswith(STALE_SENDING_NOTE)
                        else "Đã hết số lần thử lại hoặc cần đối soát."
                    ),
                }.get(log.trang_thai, "Không thể nhận quyền gửi.")
                results["skipped_count"] += 1
                results["details"].append({
                    "employee_id": employee.id,
                    "full_name": employee.ho_ten,
                    "skipped": True,
                    "trang_thai": log.trang_thai,
                    "reason": reason,
                })
                return

            deliver_claimed_email(log, max_retries)
            if log.trang_thai != BirthdayEmailStatus.SUCCESS:
                results["failed_count"] += 1
                if log.trang_thai == BirthdayEmailStatus.RETRY:
                    results["retry_count"] += 1
                results["details"].append({
                    "employee_id": employee.id,
                    "full_name": employee.ho_ten,
                    "trang_thai": log.trang_thai,
                    "error": log.error_message,
                })
            else:
                results["sent_count"] += 1
                results["details"].append({
                    "employee_id": employee.id,
                    "full_name": employee.ho_ten,
                    "trang_thai": "SUCCESS",
                    "recipient_email": recipient,
                })
        except Exception as exc:
            error_message = _safe_error(exc)
            if claimed:
                error_message = f"{STALE_SENDING_NOTE} {error_message}"
                try:
                    _record_delivery_result(
                        log=log,
                        new_status=BirthdayEmailStatus.FAILED,
                        error_message=error_message,
                        uncertain=True,
                    )
                except Exception:
                    pass
            results["failed_count"] += 1
            results["details"].append({
                "employee_id": employee.id,
                "full_name": employee.ho_ten,
                "trang_thai": BirthdayEmailStatus.FAILED,
                "error": error_message,
            })

    processed_keys = set()
    for retry_log in retry_logs:
        key = (retry_log.employee_id, retry_log.sent_date)
        processed_keys.add(key)
        process_delivery(retry_log.employee, retry_log.sent_date, existing_log=retry_log)

    for employee in eligible_employees:
        key = (employee.id, target_date)
        if key in processed_keys:
            continue
        process_delivery(employee, target_date)

    return results
