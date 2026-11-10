import calendar
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
from .models import BirthdayEmailLog, BirthdayEmailStatus

PRE_ACCEPTANCE_SMTP_ERRORS = (
    Exception,
)

STALE_SENDING_NOTE = "Kết quả gửi không xác định, cần đối soát."
SKIPPED_EMAIL_PREFIX = "Bỏ qua:"
BIRTHDAY_CARD_TOKEN_SALT = "birthdays.animated-card"
BIRTHDAY_CARD_TOKEN_MAX_AGE_SECONDS = 30 * 24 * 60 * 60


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


def generate_birthday_card_url(employee: Employee) -> str:
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
            "birthday_card_url": card_url if card_url is not None else generate_birthday_card_url(employee),
        },
    )


def generate_birthday_email_text(employee: Employee, card_url: str | None = None) -> str:
    """Tạo bản text khớp nội dung thiệp HTML và thông tin công tác của nhân viên."""
    birthday_date = employee.ngay_sinh.strftime("%d/%m") if employee.ngay_sinh else ""
    department = employee.don_vi.ten if employee.don_vi else "Cơ quan"
    position = employee.chuc_vu.name if employee.chuc_vu else "Cán bộ"
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
    if resolved_card_url:
        text += f"\n\nMở thiệp chúc mừng sinh nhật: {resolved_card_url}"
    return text


def _email_log(employee: Employee, sent_date: date, recipient: str, subject: str) -> BirthdayEmailLog:
    log, _ = BirthdayEmailLog.objects.get_or_create(
        employee=employee,
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
    return str(error) or type(error).__name__


def _claim_delivery(log: BirthdayEmailLog, recipient: str, subject: str, max_retries: int) -> bool:
    """
    Claim delivery of a birthday email using select_for_update within transaction.atomic.
    Only rows in eligible states (PENDING or RETRY/FAILED with retry_count <= max_retries)
    can be claimed. Sets trang_thai to SENDING.
    """
    with transaction.atomic():
        locked_log = (
            BirthdayEmailLog.objects.select_for_update()
            .filter(pk=log.pk)
            .first()
        )
        if not locked_log:
            return False

        is_eligible = (
            locked_log.trang_thai == BirthdayEmailStatus.PENDING
            or (
                locked_log.trang_thai in (BirthdayEmailStatus.RETRY, BirthdayEmailStatus.FAILED)
                and locked_log.retry_count <= max_retries
                and not (locked_log.error_message or "").startswith(STALE_SENDING_NOTE)
            )
        )
        if locked_log.next_retry_at and locked_log.next_retry_at > timezone.now():
            is_eligible = False
        if not is_eligible:
            log.refresh_from_db()
            return False

        now = timezone.now()
        locked_log.trang_thai = BirthdayEmailStatus.SENDING
        locked_log.recipient_email = recipient
        locked_log.subject = subject
        locked_log.error_message = None
        locked_log.sent_at = now
        locked_log.save(
            update_fields=[
                "trang_thai",
                "recipient_email",
                "subject",
                "error_message",
                "sent_at",
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
            return False

        now = timezone.now()
        locked_log.trang_thai = new_status
        update_fields = ["trang_thai", "updated_at"]

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


def send_automated_birthday_emails(
    target_date: date = None,
    max_retries: int = 3,
    leap_year_strategy: str = None,
    allow_test_email_backend: bool = False,
) -> dict:
    """
    Send birthday messages for the target date and due RETRY rows from the prior
    three days. A stale SENDING row is marked FAILED for manual reconciliation.
    """
    if target_date is None:
        target_date = timezone.localdate()
    if not 0 <= max_retries <= 10:
        raise ValueError("max_retries must be between 0 and 10")

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

    if leap_year_strategy is None:
        leap_year_strategy = getattr(settings, "BIRTHDAY_LEAP_DAY_STRATEGY", "FEB_28")
    if leap_year_strategy not in ("SKIP", "FEB_28", "MAR_01"):
        raise ValueError("Invalid leap-year birthday strategy")

    now = timezone.now()
    stale_cutoff = now - timedelta(minutes=30)
    stale_failed_count = BirthdayEmailLog.objects.filter(
        trang_thai=BirthdayEmailStatus.SENDING,
        updated_at__lt=stale_cutoff,
    ).update(
        trang_thai=BirthdayEmailStatus.FAILED,
        error_message=STALE_SENDING_NOTE,
        next_retry_at=None,
        updated_at=now,
    )

    active_employees = (
        Employee.objects.filter(is_active=True)
        .exclude(ngay_sinh__isnull=True)
        .select_related("don_vi", "chuc_vu")
    )
    eligible_employees = [
        emp
        for emp in active_employees
        if is_birthday_on_date(emp.ngay_sinh, target_date, leap_year_strategy=leap_year_strategy)
    ]
    retry_start_date = target_date - timedelta(days=3)
    retry_logs = list(
        BirthdayEmailLog.objects.filter(
            trang_thai=BirthdayEmailStatus.RETRY,
            sent_date__gte=retry_start_date,
            sent_date__lte=target_date,
        )
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
    sender_email = getattr(settings, "DEFAULT_FROM_EMAIL", "") or None

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
        log = existing_log or _email_log(employee, sent_date, recipient, subject)

        try:
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

            if not _claim_delivery(log, recipient, subject, max_retries):
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

            send_error = None
            try:
                card_url = generate_birthday_card_url(employee)
                accepted = send_mail(
                    subject=subject,
                    message=generate_birthday_email_text(employee, card_url=card_url),
                    from_email=sender_email,
                    recipient_list=[recipient],
                    html_message=generate_birthday_email_html(employee, card_url=card_url),
                    fail_silently=False,
                )
                if accepted != 1:
                    send_error = RuntimeError("SMTP did not accept the message.")
            except Exception as exc:
                send_error = exc

            if send_error is not None:
                next_status = BirthdayEmailStatus.RETRY if log.retry_count < max_retries else BirthdayEmailStatus.FAILED
                _record_delivery_result(
                    log=log,
                    new_status=next_status,
                    error_message=_safe_error(send_error),
                )
                results["failed_count"] += 1
                if next_status == BirthdayEmailStatus.RETRY:
                    results["retry_count"] += 1
                results["details"].append({
                    "employee_id": employee.id,
                    "full_name": employee.ho_ten,
                    "trang_thai": next_status,
                    "error": _safe_error(send_error),
                })
            else:
                _record_delivery_result(
                    log=log,
                    new_status=BirthdayEmailStatus.SUCCESS,
                    sent_at=timezone.now(),
                    smtp_response_code="250 OK",
                )
                results["sent_count"] += 1
                results["details"].append({
                    "employee_id": employee.id,
                    "full_name": employee.ho_ten,
                    "trang_thai": "SUCCESS",
                    "recipient_email": recipient,
                })
        except Exception as exc:
            log.refresh_from_db()
            if log.trang_thai == BirthdayEmailStatus.SENDING:
                try:
                    _record_delivery_result(
                        log=log,
                        new_status=BirthdayEmailStatus.RETRY,
                        error_message=_safe_error(exc),
                    )
                except Exception:
                    pass
            results["failed_count"] += 1
            results["details"].append({
                "employee_id": employee.id,
                "full_name": employee.ho_ten,
                "trang_thai": "RETRY",
                "error": _safe_error(exc),
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
