"""
Dịch vụ xác thực hai yếu tố (2FA) theo chuẩn TOTP (RFC 6238) và Backup Codes (Issue #674).
- Mã hóa đối xứng totp_secret bằng Fernet dẫn xuất từ DJANGO_SECRET_KEY.
- Sinh mã QR PNG dạng Data URL và otpauth:// URI bằng pyotp + qrcode.
- Chống brute-force (tối đa 5 lần sai -> khóa 5 phút) và chống dùng lại mã (anti-replay)
  nguyên tử trên PostgreSQL thông qua select_for_update(), an toàn đa worker Gunicorn.
"""
import base64
from datetime import timedelta
import hashlib
import hmac
import io
import re
import secrets
import uuid

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import signing
from django.db import transaction
from django.utils import timezone
import pyotp
import qrcode
from rest_framework import status

TOTP_PERIOD_SECONDS = 30
TOTP_VALID_WINDOW = 1
TEMP_LOGIN_TTL_SECONDS = 300
SETUP_TOKEN_TTL_SECONDS = 600
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 5
BACKUP_CODE_COUNT = 10

LOGIN_SALT = "accounts.2fa.login"
SETUP_SALT = "accounts.2fa.setup"

# Loại trừ 0/O/I/1 để tránh nhầm lẫn khi cán bộ nhập tay mã dự phòng
_BACKUP_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"


class TwoFactorError(Exception):
    """Lỗi nghiệp vụ có mã chuẩn hóa phục vụ API & i18n frontend."""

    def __init__(
        self,
        code: str,
        message: str,
        http_status: int = status.HTTP_400_BAD_REQUEST,
        extra: dict | None = None,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status
        self.extra = extra or {}


def _get_fernet() -> Fernet:
    digest = hashlib.sha256(
        f"qlvb-accounts-2fa-totp:{settings.SECRET_KEY}".encode("utf-8")
    ).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(raw_secret: str) -> str:
    return _get_fernet().encrypt(raw_secret.encode("utf-8")).decode("ascii")


def decrypt_secret(stored_secret: str) -> str:
    if not stored_secret:
        raise TwoFactorError("twofa_not_configured", "Tài khoản chưa thiết lập khóa 2FA.")
    try:
        return _get_fernet().decrypt(stored_secret.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise TwoFactorError(
            "twofa_secret_invalid",
            "Không giải mã được khóa bí mật 2FA. Vui lòng liên hệ Quản trị viên.",
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        ) from exc


def normalize_otp_or_backup(raw_code: str) -> str:
    return re.sub(r"[\s-]+", "", str(raw_code or "")).upper()


def hash_backup_code(raw_code: str) -> str:
    normalized = normalize_otp_or_backup(raw_code)
    return hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        normalized.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def generate_backup_codes(count: int = BACKUP_CODE_COUNT) -> tuple[list[str], list[str]]:
    """Sinh danh sách mã dự phòng hiển thị 1 lần và danh sách mã băm lưu DB."""
    plain_codes: list[str] = []
    hashed_codes: list[str] = []
    for _ in range(count):
        raw = "".join(secrets.choice(_BACKUP_ALPHABET) for _ in range(8))
        formatted = f"{raw[:4]}-{raw[4:]}"
        plain_codes.append(formatted)
        hashed_codes.append(hash_backup_code(formatted))
    return plain_codes, hashed_codes


def _build_qr_data_url(otpauth_uri: str) -> str:
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=2,
    )
    qr.add_data(otpauth_uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def create_setup_payload(user) -> dict:
    """Khởi tạo secret tạm + QR PNG (Base64) trong token ký ngắn hạn, chưa ghi DB."""
    secret = pyotp.random_base32()
    issuer = getattr(settings, "BRAND_NAME", "Bao Long Insurance") or "Bao Long Insurance"
    account_label = user.email or user.username
    totp = pyotp.TOTP(secret, interval=TOTP_PERIOD_SECONDS)
    otpauth_uri = totp.provisioning_uri(name=account_label, issuer_name=issuer)

    setup_token = signing.dumps(
        {
            "uid": user.id,
            "sec": encrypt_secret(secret),
            "jti": uuid.uuid4().hex,
        },
        salt=SETUP_SALT,
    )

    return {
        "secret_key": secret,
        "otpauth_uri": otpauth_uri,
        "qr_code": _build_qr_data_url(otpauth_uri),
        "setup_token": setup_token,
        "expires_in": SETUP_TOKEN_TTL_SECONDS,
    }


def load_setup_token(setup_token: str, expected_user_id: int) -> str:
    """Giải mã setup_token, trả về raw Base32 secret nếu hợp lệ và khớp chủ sở hữu."""
    if not setup_token:
        raise TwoFactorError("setup_token_missing", "Thiếu phiên thiết lập 2FA.")
    try:
        payload = signing.loads(setup_token, salt=SETUP_SALT, max_age=SETUP_TOKEN_TTL_SECONDS)
    except signing.SignatureExpired as exc:
        raise TwoFactorError(
            "setup_token_expired",
            "Phiên thiết lập mã QR đã hết hạn. Vui lòng tạo mã QR mới.",
        ) from exc
    except signing.BadSignature as exc:
        raise TwoFactorError(
            "setup_token_invalid",
            "Phiên thiết lập mã QR không hợp lệ.",
        ) from exc

    if payload.get("uid") != expected_user_id or not payload.get("sec"):
        raise TwoFactorError("setup_token_invalid", "Phiên thiết lập 2FA không khớp tài khoản.")

    return decrypt_secret(payload["sec"])


def find_matching_totp_step(raw_secret: str, code: str, last_used_step: int | None = None) -> int | None:
    """
    Kiểm tra mã TOTP 6 chữ số trong cửa sổ +-30s (valid_window=1).
    Trả về time-step khớp nếu hợp lệ; ném TwoFactorError nếu mã bị dùng lại; trả None nếu sai.
    """
    digits = re.sub(r"\s+", "", str(code or ""))
    if not re.fullmatch(r"\d{6}", digits):
        return None

    totp = pyotp.TOTP(raw_secret, interval=TOTP_PERIOD_SECONDS)
    now_step = int(timezone.now().timestamp()) // TOTP_PERIOD_SECONDS

    for offset in range(-TOTP_VALID_WINDOW, TOTP_VALID_WINDOW + 1):
        step = now_step + offset
        expected = totp.at(step * TOTP_PERIOD_SECONDS)
        if hmac.compare_digest(digits, expected):
            if last_used_step is not None and step <= last_used_step:
                raise TwoFactorError(
                    "otp_reused",
                    "Mã OTP này vừa được sử dụng. Vui lòng chờ mã mới (sau 30 giây).",
                    http_status=status.HTTP_400_BAD_REQUEST,
                )
            return step
    return None


def create_login_challenge_token(user_id: int, auth_provider: str) -> str:
    return signing.dumps(
        {
            "uid": user_id,
            "provider": auth_provider,
            "jti": uuid.uuid4().hex,
        },
        salt=LOGIN_SALT,
    )


def load_login_challenge_token(temp_token: str) -> dict:
    if not temp_token:
        raise TwoFactorError(
            "temp_token_missing",
            "Thiếu mã phiên xác thực 2 bước.",
            http_status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        payload = signing.loads(temp_token, salt=LOGIN_SALT, max_age=TEMP_LOGIN_TTL_SECONDS)
    except signing.SignatureExpired as exc:
        raise TwoFactorError(
            "temp_token_expired",
            "Phiên xác thực 2FA đã hết hạn. Vui lòng đăng nhập lại.",
            http_status=status.HTTP_401_UNAUTHORIZED,
        ) from exc
    except signing.BadSignature as exc:
        raise TwoFactorError(
            "temp_token_invalid",
            "Phiên xác thực 2FA không hợp lệ.",
            http_status=status.HTTP_401_UNAUTHORIZED,
        ) from exc

    if not payload.get("uid"):
        raise TwoFactorError(
            "temp_token_invalid",
            "Phiên xác thực 2FA không hợp lệ.",
            http_status=status.HTTP_401_UNAUTHORIZED,
        )
    return payload


def _consume_backup_code(hashed_list: list[str], raw_code: str) -> tuple[bool, list[str]]:
    candidate_hash = hash_backup_code(raw_code)
    matched_idx = None
    for idx, stored in enumerate(hashed_list):
        if isinstance(stored, str) and hmac.compare_digest(stored, candidate_hash):
            matched_idx = idx
            break
    if matched_idx is None:
        return False, hashed_list
    remaining = hashed_list[:matched_idx] + hashed_list[matched_idx + 1 :]
    return True, remaining


def verify_user_twofa_code(user_id: int, raw_code: str, allow_backup_code: bool = True) -> tuple[object, str]:
    """
    Xác thực mã TOTP hoặc Backup Code một cách nguyên tử (select_for_update):
    - Kiểm tra khóa tạm thời (5 lần sai -> khóa 5 phút).
    - Chống dùng lại mã OTP trong cùng time-step.
    - Xóa backup code ngay sau khi sử dụng.
    Lưu bộ đếm sai ngay cả khi trả lỗi (raise TwoFactorError ngoài transaction.atomic).
    """
    UserModel = get_user_model()
    cleaned = str(raw_code or "").strip()
    if not cleaned:
        raise TwoFactorError(
            "otp_required",
            "Vui lòng nhập mã xác thực 6 chữ số hoặc mã dự phòng.",
            http_status=status.HTTP_400_BAD_REQUEST,
        )

    failure: TwoFactorError | None = None
    verified_user = None
    verified_method = ""
    now = timezone.now()

    with transaction.atomic():
        user = (
            UserModel.objects.select_for_update()
            .select_related("don_vi", "chuc_vu")
            .filter(pk=user_id)
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
        if not user.is_2fa_enabled or not user.totp_secret:
            raise TwoFactorError(
                "twofa_not_enabled",
                "Tài khoản chưa kích hoạt xác thực hai yếu tố.",
                http_status=status.HTTP_400_BAD_REQUEST,
            )

        if user.twofa_locked_until and user.twofa_locked_until > now:
            retry_after = max(1, int((user.twofa_locked_until - now).total_seconds()))
            raise TwoFactorError(
                "twofa_locked",
                f"Bạn đã nhập sai mã 2FA quá nhiều lần. Vui lòng thử lại sau {retry_after} giây.",
                http_status=status.HTTP_429_TOO_MANY_REQUESTS,
                extra={"retry_after_seconds": retry_after},
            )

        # Nếu đã hết hạn khóa cũ thì reset bộ đếm chu kỳ mới
        if user.twofa_locked_until and user.twofa_locked_until <= now:
            user.twofa_failed_attempts = 0
            user.twofa_locked_until = None

        raw_secret = decrypt_secret(user.totp_secret)

        try:
            matched_step = find_matching_totp_step(
                raw_secret,
                cleaned,
                last_used_step=user.totp_last_used_step,
            )
        except TwoFactorError as reused_err:
            # Không khóa tài khoản do bấm đúp trong cùng 30s, nhưng chặn tái sử dụng
            failure = reused_err
            matched_step = None

        if failure is None and matched_step is not None:
            user.totp_last_used_step = matched_step
            user.twofa_failed_attempts = 0
            user.twofa_locked_until = None
            user.save(
                update_fields=[
                    "totp_last_used_step",
                    "twofa_failed_attempts",
                    "twofa_locked_until",
                ]
            )
            verified_user = user
            verified_method = "totp"
        elif failure is None and allow_backup_code:
            backup_ok, remaining_codes = _consume_backup_code(
                list(user.twofa_backup_codes or []),
                cleaned,
            )
            if backup_ok:
                user.twofa_backup_codes = remaining_codes
                user.twofa_failed_attempts = 0
                user.twofa_locked_until = None
                user.save(
                    update_fields=[
                        "twofa_backup_codes",
                        "twofa_failed_attempts",
                        "twofa_locked_until",
                    ]
                )
                verified_user = user
                verified_method = "backup_code"

        if failure is None and verified_user is None:
            next_attempts = (user.twofa_failed_attempts or 0) + 1
            if next_attempts >= MAX_FAILED_ATTEMPTS:
                user.twofa_failed_attempts = MAX_FAILED_ATTEMPTS
                user.twofa_locked_until = now + timedelta(minutes=LOCKOUT_MINUTES)
                user.save(update_fields=["twofa_failed_attempts", "twofa_locked_until"])
                failure = TwoFactorError(
                    "twofa_locked",
                    f"Đã nhập sai mã 2FA {MAX_FAILED_ATTEMPTS} lần liên tiếp. Tạm khóa trong {LOCKOUT_MINUTES} phút.",
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

    return verified_user, verified_method

