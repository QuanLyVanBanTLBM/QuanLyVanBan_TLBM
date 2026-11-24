"""
Dịch vụ sinh, gửi và xác thực mã OTP 6 chữ số qua Email hoặc SMS cho đăng nhập 2FA
và tự đặt lại mật khẩu (stateless signed token + khóa chống brute-force trong PostgreSQL).
"""
import hashlib
import hmac
import json
import logging
import re
import secrets
from datetime import timedelta
import urllib.error
import urllib.request
import uuid

import django
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import signing
from django.core.mail import EmailMessage, get_connection
from django.db import transaction
from django.utils import timezone
from rest_framework import status

from .twofa import (
    LOCKOUT_MINUTES,
    MAX_FAILED_ATTEMPTS,
    TwoFactorError,
)

logger = logging.getLogger(__name__)

OTP_PURPOSE_2FA_LOGIN = "2fa_login"
OTP_PURPOSE_PASSWORD_RESET = "password_reset"

OTP_TTL_BY_PURPOSE = {
    OTP_PURPOSE_2FA_LOGIN: 300,
    OTP_PURPOSE_PASSWORD_RESET: 600,
}

OTP_RESEND_COOLDOWN_SECONDS = 60


def is_sms_configured() -> bool:
    """Kiểm tra cấu hình gateway SMS đã đầy đủ (dùng chung cấu hình SIGNING_SMS_*)."""
    url = (getattr(settings, "SIGNING_SMS_URL", "") or "").strip()
    authorization = (getattr(settings, "SIGNING_SMS_AUTHORIZATION", "") or "").strip()
    sender = (getattr(settings, "SIGNING_SMS_FROM", "") or "").strip()
    return bool(url and authorization and sender and url.startswith("https://"))


def is_sms_available() -> bool:
    """Cho phép kênh SMS khi đã cấu hình gateway hoặc đang chạy DEBUG (in console)."""
    return is_sms_configured() or bool(getattr(settings, "DEBUG", False))


def mask_email(email: str) -> str:
    cleaned = (email or "").strip()
    if "@" not in cleaned:
        return ""
    local, domain = cleaned.split("@", 1)
    if len(local) <= 1:
        masked_local = "*"
    elif len(local) <= 3:
        masked_local = local[0] + "*" * (len(local) - 1)
    else:
        masked_local = local[:2] + "*" * min(5, len(local) - 2)
    return f"{masked_local}@{domain}"


def mask_phone(phone: str) -> str:
    digits = re.sub(r"\s+", "", str(phone or ""))
    if len(digits) < 4:
        return ""
    return f"{digits[:2]}{'*' * max(2, len(digits) - 4)}{digits[-2:]}"


def get_available_otp_channels(user) -> dict:
    """Trả về thông tin kênh OTP khả dụng đã che dữ liệu liên hệ."""
    email = (getattr(user, "email", "") or "").strip()
    phone = (getattr(user, "sdt", "") or "").strip()
    has_email = bool(email)
    has_sms = bool(phone) and is_sms_available()
    return {
        "email": has_email,
        "sms": has_sms,
        "masked_email": mask_email(email) if has_email else "",
        "masked_phone": mask_phone(phone) if has_sms else "",
    }


def _mail_connection():
    """Tạo kết nối email tương thích Django 5.2 và Django 6.1+."""
    if django.VERSION >= (6, 1):
        return None
    mailers = getattr(settings, "MAILERS", None)
    backend = None
    if isinstance(mailers, dict):
        backend = mailers.get("default", {}).get("BACKEND")
    return get_connection(backend=backend)


def _send_email_otp(user, code: str, purpose: str) -> None:
    recipient = (getattr(user, "email", "") or "").strip()
    if not recipient:
        raise TwoFactorError(
            "email_not_available",
            "Tài khoản chưa có địa chỉ email.",
            http_status=status.HTTP_400_BAD_REQUEST,
        )

    brand = getattr(settings, "BRAND_NAME", "Bảo Long Insurance") or "Bảo Long Insurance"
    if purpose == OTP_PURPOSE_PASSWORD_RESET:
        subject = f"[{brand}] Mã xác nhận đặt lại mật khẩu"
        ttl_minutes = OTP_TTL_BY_PURPOSE[OTP_PURPOSE_PASSWORD_RESET] // 60
        body = (
            f"Xin chào {user.ho_ten or user.username},\n\n"
            f"Mã xác nhận đặt lại mật khẩu của bạn là: {code}\n"
            f"Mã có hiệu lực trong {ttl_minutes} phút. Không chia sẻ mã này cho người khác."
        )
    else:
        subject = f"[{brand}] Mã xác thực đăng nhập (2FA)"
        ttl_minutes = OTP_TTL_BY_PURPOSE[OTP_PURPOSE_2FA_LOGIN] // 60
        body = (
            f"Xin chào {user.ho_ten or user.username},\n\n"
            f"Mã xác thực đăng nhập của bạn là: {code}\n"
            f"Mã có hiệu lực trong {ttl_minutes} phút. Không chia sẻ mã này cho người khác."
        )

    try:
        message = EmailMessage(
            subject=subject,
            body=body,
            from_email=None,
            to=[recipient],
            connection=_mail_connection(),
        )
        if message.send() != 1:
            raise TwoFactorError(
                "otp_delivery_failed",
                "Không gửi được email OTP. Vui lòng thử lại sau.",
                http_status=status.HTTP_502_BAD_GATEWAY,
            )
    except TwoFactorError:
        raise
    except Exception as exc:
        logger.warning("Email OTP delivery failed (%s)", type(exc).__name__)
        raise TwoFactorError(
            "otp_delivery_failed",
            "Không gửi được email OTP. Vui lòng thử lại sau.",
            http_status=status.HTTP_502_BAD_GATEWAY,
        ) from None


def _send_sms_otp(user, code: str, purpose: str) -> None:
    phone = (getattr(user, "sdt", "") or "").strip()
    if not phone:
        raise TwoFactorError(
            "phone_not_available",
            "Tài khoản chưa có số điện thoại.",
            http_status=status.HTTP_400_BAD_REQUEST,
        )

    ttl_minutes = OTP_TTL_BY_PURPOSE.get(purpose, 300) // 60
    action_label = "dat lai mat khau" if purpose == OTP_PURPOSE_PASSWORD_RESET else "dang nhap"
    text = f"Ma OTP {action_label} QLVB Bao Long cua ban la {code}. Co hieu luc {ttl_minutes} phut."

    if not is_sms_configured():
        if getattr(settings, "DEBUG", False):
            logger.info("[DEV SMS OTP] to=%s purpose=%s code=%s", phone, purpose, code)
            print(f"[DEV SMS OTP] to={phone} purpose={purpose} code={code}")
            return
        raise TwoFactorError(
            "sms_not_configured",
            "Dịch vụ SMS OTP chưa được cấu hình trên máy chủ.",
            http_status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    url = settings.SIGNING_SMS_URL.strip()
    payload = json.dumps(
        {
            "from": settings.SIGNING_SMS_FROM.strip(),
            "to": phone,
            "text": text,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": settings.SIGNING_SMS_AUTHORIZATION.strip(),
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            if not 200 <= response.status < 300:
                raise TwoFactorError(
                    "otp_delivery_failed",
                    "Nhà cung cấp SMS từ chối gửi mã OTP.",
                    http_status=status.HTTP_502_BAD_GATEWAY,
                )
    except TwoFactorError:
        raise
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as exc:
        logger.warning("SMS OTP delivery failed (%s)", type(exc).__name__)
        raise TwoFactorError(
            "otp_delivery_failed",
            "Không gửi được SMS OTP. Vui lòng thử lại sau.",
            http_status=status.HTTP_502_BAD_GATEWAY,
        ) from None


def _user_state_version(user, purpose: str) -> str:
    if purpose == OTP_PURPOSE_PASSWORD_RESET:
        return hashlib.sha256((user.password or "").encode("utf-8")).hexdigest()[:16]
    return user.last_login.isoformat() if user.last_login else ""


def _otp_salt(purpose: str) -> str:
    return f"accounts.otp.{purpose}"


def _hash_otp_code(purpose: str, user_id: int, jti: str, code: str) -> str:
    msg = f"{purpose}:{user_id}:{jti}:{code}".encode("utf-8")
    return hmac.new(settings.SECRET_KEY.encode("utf-8"), msg, hashlib.sha256).hexdigest()


def check_resend_cooldown(previous_token: str | None, expected_user_id: int, purpose: str) -> None:
    """Chặn gửi lại mã OTP liên tiếp trong vòng 60 giây."""
    if not previous_token:
        return
    try:
        payload = signing.loads(
            previous_token,
            salt=_otp_salt(purpose),
            max_age=OTP_TTL_BY_PURPOSE[purpose],
        )
    except signing.BadSignature:
        return

    if payload.get("uid") != expected_user_id:
        return
    sent_at = int(payload.get("sent_at") or 0)
    elapsed = int(timezone.now().timestamp()) - sent_at
    if 0 <= elapsed < OTP_RESEND_COOLDOWN_SECONDS:
        retry_after = OTP_RESEND_COOLDOWN_SECONDS - elapsed
        raise TwoFactorError(
            "otp_cooldown",
            f"Vui lòng chờ {retry_after} giây trước khi yêu cầu mã mới.",
            http_status=status.HTTP_429_TOO_MANY_REQUESTS,
            extra={"retry_after_seconds": retry_after},
        )


def send_otp_challenge(
    user,
    channel: str,
    purpose: str,
    previous_token: str | None = None,
) -> dict:
    """Sinh OTP 6 chữ số, gửi qua Email/SMS và trả về token ký + thông tin đã che."""
    if purpose not in OTP_TTL_BY_PURPOSE:
        raise ValueError(f"Unsupported OTP purpose: {purpose}")

    normalized_channel = str(channel or "").strip().lower()
    if normalized_channel not in {"email", "sms"}:
        raise TwoFactorError(
            "invalid_otp_channel",
            "Kênh gửi mã phải là email hoặc sms.",
            http_status=status.HTTP_400_BAD_REQUEST,
        )

    now = timezone.now()
    if user.twofa_locked_until and user.twofa_locked_until > now:
        retry_after = max(1, int((user.twofa_locked_until - now).total_seconds()))
        raise TwoFactorError(
            "twofa_locked",
            f"Bạn đã nhập sai mã quá nhiều lần. Vui lòng thử lại sau {retry_after} giây.",
            http_status=status.HTTP_429_TOO_MANY_REQUESTS,
            extra={"retry_after_seconds": retry_after},
        )

    check_resend_cooldown(previous_token, user.id, purpose)

    code = f"{secrets.randbelow(1_000_000):06d}"
    jti = uuid.uuid4().hex
    if normalized_channel == "email":
        _send_email_otp(user, code, purpose)
        masked_destination = mask_email(user.email or "")
    else:
        _send_sms_otp(user, code, purpose)
        masked_destination = mask_phone(user.sdt or "")

    token = signing.dumps(
        {
            "uid": user.id,
            "channel": normalized_channel,
            "jti": jti,
            "otp_hmac": _hash_otp_code(purpose, user.id, jti, code),
            "ver": _user_state_version(user, purpose),
            "sent_at": int(now.timestamp()),
        },
        salt=_otp_salt(purpose),
    )

    return {
        "token": token,
        "channel": normalized_channel,
        "masked_destination": masked_destination,
        "expires_in": OTP_TTL_BY_PURPOSE[purpose],
        "cooldown_seconds": OTP_RESEND_COOLDOWN_SECONDS,
    }


def load_otp_challenge_token(token: str, purpose: str) -> dict:
    if not token:
        raise TwoFactorError(
            "otp_token_missing",
            "Thiếu mã phiên xác thực OTP.",
            http_status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        payload = signing.loads(
            token,
            salt=_otp_salt(purpose),
            max_age=OTP_TTL_BY_PURPOSE[purpose],
        )
    except signing.SignatureExpired as exc:
        raise TwoFactorError(
            "otp_token_expired",
            "Mã OTP đã hết hạn. Vui lòng yêu cầu mã mới.",
            http_status=status.HTTP_400_BAD_REQUEST,
        ) from exc
    except signing.BadSignature as exc:
        raise TwoFactorError(
            "otp_token_invalid",
            "Phiên xác thực OTP không hợp lệ.",
            http_status=status.HTTP_400_BAD_REQUEST,
        ) from exc

    if not payload.get("uid") or not payload.get("jti") or not payload.get("otp_hmac"):
        raise TwoFactorError(
            "otp_token_invalid",
            "Phiên xác thực OTP không hợp lệ.",
            http_status=status.HTTP_400_BAD_REQUEST,
        )
    return payload


def verify_otp_challenge(
    otp_token: str,
    raw_code: str,
    purpose: str,
    expected_user_id: int | None = None,
) -> tuple[object, str]:
    """
    Xác thực mã OTP Email/SMS một cách nguyên tử với select_for_update().
    Trả về (user, channel) nếu thành công; lưu số lần sai khi thất bại.
    """
    payload = load_otp_challenge_token(otp_token, purpose)
    uid = int(payload["uid"])
    if expected_user_id is not None and uid != expected_user_id:
        raise TwoFactorError(
            "otp_token_invalid",
            "Phiên xác thực OTP không khớp tài khoản.",
            http_status=status.HTTP_400_BAD_REQUEST,
        )

    digits = re.sub(r"\s+", "", str(raw_code or ""))
    if not digits:
        raise TwoFactorError(
            "otp_required",
            "Vui lòng nhập mã xác thực 6 chữ số.",
            http_status=status.HTTP_400_BAD_REQUEST,
        )

    UserModel = get_user_model()
    now = timezone.now()
    failure: TwoFactorError | None = None
    verified_user = None

    with transaction.atomic():
        user = (
            UserModel.objects.select_for_update()
            .select_related("don_vi", "chuc_vu")
            .filter(pk=uid)
            .first()
        )
        if not user:
            raise TwoFactorError(
                "user_not_found",
                "Không tìm thấy tài khoản.",
                http_status=status.HTTP_401_UNAUTHORIZED,
            )
        if not user.is_active:
            raise TwoFactorError(
                "account_disabled",
                "Tài khoản đã bị vô hiệu hóa. Vui lòng liên hệ Quản trị viên.",
                http_status=status.HTTP_403_FORBIDDEN,
            )
        if payload.get("ver", "") != _user_state_version(user, purpose):
            raise TwoFactorError(
                "otp_token_expired",
                "Phiên xác thực OTP đã hết hiệu lực. Vui lòng yêu cầu mã mới.",
                http_status=status.HTTP_400_BAD_REQUEST,
            )

        if user.twofa_locked_until and user.twofa_locked_until > now:
            retry_after = max(1, int((user.twofa_locked_until - now).total_seconds()))
            raise TwoFactorError(
                "twofa_locked",
                f"Bạn đã nhập sai mã quá nhiều lần. Vui lòng thử lại sau {retry_after} giây.",
                http_status=status.HTTP_429_TOO_MANY_REQUESTS,
                extra={"retry_after_seconds": retry_after},
            )

        if user.twofa_locked_until and user.twofa_locked_until <= now:
            user.twofa_failed_attempts = 0
            user.twofa_locked_until = None

        expected_hmac = _hash_otp_code(purpose, user.id, str(payload["jti"]), digits)
        is_valid = bool(re.fullmatch(r"\d{6}", digits)) and hmac.compare_digest(
            expected_hmac,
            str(payload["otp_hmac"]),
        )

        if is_valid:
            user.twofa_failed_attempts = 0
            user.twofa_locked_until = None
            user.save(update_fields=["twofa_failed_attempts", "twofa_locked_until"])
            verified_user = user
        else:
            next_attempts = (user.twofa_failed_attempts or 0) + 1
            if next_attempts >= MAX_FAILED_ATTEMPTS:
                user.twofa_failed_attempts = MAX_FAILED_ATTEMPTS
                user.twofa_locked_until = now + timedelta(minutes=LOCKOUT_MINUTES)
                user.save(update_fields=["twofa_failed_attempts", "twofa_locked_until"])
                failure = TwoFactorError(
                    "twofa_locked",
                    f"Đã nhập sai mã {MAX_FAILED_ATTEMPTS} lần liên tiếp. Tạm khóa trong {LOCKOUT_MINUTES} phút.",
                    http_status=status.HTTP_429_TOO_MANY_REQUESTS,
                    extra={"retry_after_seconds": LOCKOUT_MINUTES * 60},
                )
            else:
                remaining_tries = MAX_FAILED_ATTEMPTS - next_attempts
                user.twofa_failed_attempts = next_attempts
                user.save(update_fields=["twofa_failed_attempts", "twofa_locked_until"])
                failure = TwoFactorError(
                    "otp_invalid",
                    f"Mã xác thực không chính xác. Còn {remaining_tries} lần thử.",
                    http_status=status.HTTP_401_UNAUTHORIZED,
                    extra={"attempts_remaining": remaining_tries},
                )

    if failure is not None:
        raise failure

    return verified_user, str(payload.get("channel") or "email")
