from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.models import update_last_login
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from authorization.permissions import is_system_admin, require_permission
from .models import EmployeePasswordResetAudit
from .serializers import ChangePasswordSerializer
from .alpaca_auth import check_alpaca_auth
from . import otp_service, twofa


def _provision_alpaca_employee(username, user_info):
    """
    Tự động khởi tạo và đồng bộ hồ sơ CBNV từ API Bảo Long (Just-In-Time Provisioning).
    Gán chức vụ, đơn vị và nhóm quyền mặc định tương ứng với vị trí công tác.
    """
    UserModel = get_user_model()
    from accounts.models import Position
    from organizations.models import DonVi
    from .serializers import get_default_groups_for_position

    full_name = user_info.get("fullName") or username
    email = user_info.get("email") or f"{username}@baolong.vn"
    phone = user_info.get("phoneNumber") or ""
    pos_name = user_info.get("positionName") or ""
    dept_name = user_info.get("departmentName") or ""

    # Chỉ khớp đúng tên (không phân biệt hoa thường): khớp một phần có thể gán nhầm chức vụ cao hơn và nhóm quyền cao hơn.
    position = None
    if pos_name:
        position = Position.objects.filter(name__iexact=pos_name.strip()).first()
    if not position:
        position = Position.objects.filter(name="Chuyên viên").first() or Position.objects.first()

    don_vi = None
    if dept_name:
        don_vi = (
            DonVi.objects.filter(ten__iexact=dept_name.strip()).first()
            or DonVi.objects.filter(ten__icontains=dept_name.strip()).first()
        )
    if not don_vi:
        don_vi = DonVi.objects.filter(ten__icontains="Công nghệ thông tin").first() or DonVi.objects.first()

    target_user = UserModel.objects.create_user(
        username=username,
        ho_ten=full_name,
        email=email,
        sdt=phone,
        chuc_vu=position,
        don_vi=don_vi,
        is_active=True,
    )

    if position:
        default_groups = get_default_groups_for_position(position)
        if default_groups:
            target_user.groups.set(default_groups)

    return target_user


def _build_user_payload(user):
    """Trả về dict thông tin user dùng chung cho login & profile response, hỗ trợ cả camelCase lẫn snake_case."""
    full_name = user.ho_ten or user.username
    department = user.don_vi.ten if user.don_vi_id else "Văn phòng Trung tâm"
    position = user.chuc_vu.name if user.chuc_vu_id else ("Quản trị viên tối cao" if user.is_superuser else "Chuyên viên văn thư")
    date_joined_str = user.created_at.strftime("%Y-%m-%d") if user.created_at else ""

    user_don_vi_id = getattr(user, "don_vi_id", None)
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email or "",
        # CamelCase (theo API Contract Hieu.md)
        "fullName": full_name,
        "unit": department,
        "donViId": user_don_vi_id,
        "roleTitle": position,
        "dateJoined": date_joined_str,
        # Snake_case (tương thích backward)
        "full_name": full_name,
        "department": department,
        "don_vi_id": user_don_vi_id,
        "position": position,
        "role": "admin" if user.is_superuser else "staff",
        "phone": user.sdt,
        "avatar_url": "",
        "birthday": user.ngay_sinh.isoformat() if user.ngay_sinh else None,
        "is_2fa_enabled": bool(getattr(user, "is_2fa_enabled", False)),
        "has_usable_credential": bool(user.has_usable_password()),
    }


def _find_user_by_identifier(identifier: str):
    """Tìm nhân viên theo username chính xác hoặc email (không phân biệt hoa thường nếu duy nhất)."""
    cleaned = str(identifier or "").strip()
    if not cleaned:
        return None
    UserModel = get_user_model()
    user = UserModel.objects.filter(username=cleaned).first()
    if user is not None:
        return user
    if "@" in cleaned:
        matches = list(UserModel.objects.filter(email__iexact=cleaned)[:2])
        if len(matches) == 1:
            return matches[0]
    return None


def _issue_jwt_response(user, auth_provider: str, verified_via: str | None = None):
    """Cấp cặp access/refresh JWT và payload user thống nhất sau khi xác thực hoàn tất."""
    update_last_login(None, user)
    refresh = RefreshToken.for_user(user)
    access_token = str(refresh.access_token)

    user_payload = _build_user_payload(user)
    user_payload["auth_provider"] = auth_provider

    body = {
        "success": True,
        "token": access_token,
        "access": access_token,
        "refresh": str(refresh),
        "user": user_payload,
        "auth_provider": auth_provider,
    }
    if verified_via:
        body["verified_via"] = verified_via
    return Response(body, status=status.HTTP_200_OK)


def _login_or_2fa_response(request, user, auth_provider: str):
    """Kiểm tra trạng thái 2FA và thiết bị tin cậy: bỏ qua 2FA nếu có cookie hợp lệ, ngược lại trả challenge."""
    if getattr(user, "is_2fa_enabled", False) and getattr(user, "totp_secret", ""):
        trusted_cookie = request.COOKIES.get(twofa.TRUSTED_DEVICE_COOKIE_NAME)
        if twofa.is_trusted_device_valid(trusted_cookie, user):
            return _issue_jwt_response(user, auth_provider, verified_via="trusted_device")

        channels = otp_service.get_available_otp_channels(user)
        return Response(
            {
                "success": True,
                "require_2fa": True,
                "temp_token": twofa.create_login_challenge_token(user.id, auth_provider),
                "method": "totp",
                "auth_provider": auth_provider,
                "available_channels": {
                    "totp": True,
                    "backup": True,
                    "email": channels["email"],
                    "sms": channels["sms"],
                },
                "masked_email": channels["masked_email"],
                "masked_phone": channels["masked_phone"],
            },
            status=status.HTTP_200_OK,
        )
    return _issue_jwt_response(user, auth_provider)


def _twofa_error_response(exc: twofa.TwoFactorError) -> Response:
    return Response(
        {"detail": exc.message, "code": exc.code, **exc.extra},
        status=exc.http_status,
    )


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/auth/login/
# ─────────────────────────────────────────────────────────────────────────────

@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    """
    Đăng nhập và cấp JWT token.
    Khớp 100% API Contract của Hieu.md:
      Response 200: { "success": true, "token": "...", "access": "...", "user": { ... } }
      Response 401: { "success": false, "error": "...", "detail": "..." }
    """
    identifier = request.data.get("username", "").strip()
    password = request.data.get("password", "")

    if not identifier or not password:
        msg = "Vui lòng nhập đầy đủ tài khoản và mật khẩu."
        return Response(
            {"success": False, "error": msg, "detail": msg},
            status=status.HTTP_400_BAD_REQUEST,
        )

    target_user = _find_user_by_identifier(identifier)
    lookup_username = target_user.username if target_user else identifier

    # 1. Thử xác thực cục bộ (Local Auth)
    user = authenticate(request, username=lookup_username, password=password)

    if user is not None:
        if not user.is_active:
            msg = "Tài khoản đã bị vô hiệu hóa. Vui lòng liên hệ Quản trị viên."
            return Response(
                {"success": False, "error": msg, "detail": msg},
                status=status.HTTP_403_FORBIDDEN,
            )

        return _login_or_2fa_response(request, user, "local")

    # 2. Xử lý khi xác thực cục bộ thất bại:
    # 2.1. Nếu tài khoản cục bộ tồn tại nhưng bị vô hiệu hóa và đúng mật khẩu
    if target_user and not target_user.is_active and target_user.check_password(password):
        msg = "Tài khoản đã bị vô hiệu hóa. Vui lòng liên hệ Quản trị viên."
        return Response(
            {"success": False, "error": msg, "detail": msg},
            status=status.HTTP_403_FORBIDDEN,
        )

    # 2.2. [Điểm 1 & Điểm 2 từ Nhóm 7]:
    # Tuyệt đối KHÔNG gọi API ngoài đối với tài khoản quản trị/đặc quyền (is_superuser, is_staff).
    # Chặn rò rỉ mật khẩu admin ra hệ thống ngoài và ngăn ngừa leo thang chiếm quyền (Account Takeover).
    if target_user and (target_user.is_superuser or target_user.is_staff):
        msg = "Tên đăng nhập hoặc mật khẩu không chính xác!"
        return Response(
            {"success": False, "error": msg, "detail": msg},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    # 3. Kích hoạt xác thực kép qua API Ngân hàng Bảo Long (Alpaca)
    alpaca_res = check_alpaca_auth(lookup_username, password)

    if alpaca_res.get("success"):
        # [Điểm 3 & Điểm 4 từ Nhóm 7]:
        # Nếu tài khoản chưa có trong hệ thống QLVB:
        # - Trường hợp 1: Không có hồ sơ cán bộ thật (mock SIT Data=7) -> 403 Forbidden.
        # - Trường hợp 2: Có hồ sơ CBNV thật từ máy chủ Bảo Long -> Kích hoạt Just-In-Time (JIT) Provisioning
        #   để đồng bộ hồ sơ cán bộ vào CSDL và tự động gán quyền tương ứng.
        if not target_user:
            user_info = alpaca_res.get("user_info") or {}
            full_name = user_info.get("fullName", "").strip()

            if not full_name:
                msg = "Tài khoản chưa được phân quyền trong hệ thống. Vui lòng liên hệ Quản trị viên."
                return Response(
                    {"success": False, "error": msg, "detail": msg},
                    status=status.HTTP_403_FORBIDDEN,
                )

            target_user = _provision_alpaca_employee(lookup_username, user_info)

        if not target_user.is_active:
            msg = "Tài khoản đã bị vô hiệu hóa. Vui lòng liên hệ Quản trị viên."
            return Response(
                {"success": False, "error": msg, "detail": msg},
                status=status.HTTP_403_FORBIDDEN,
            )

        # [Điểm 2 từ Nhóm 7]:
        # KHÔNG ghi đè mật khẩu cục bộ của tài khoản (không gọi target_user.set_password).
        # Cấp token JWT trực tiếp cho phiên làm việc hiện tại của nhân viên.
        return _login_or_2fa_response(request, target_user, "alpaca_api")
    else:
        # Nếu Alpaca thông báo tài khoản bị khóa hoặc vô hiệu hóa
        if alpaca_res.get("status") in (0, 3):
            msg = alpaca_res.get("message") or "Tài khoản đã bị vô hiệu hóa hoặc khóa."
            return Response(
                {"success": False, "error": msg, "detail": msg},
                status=status.HTTP_403_FORBIDDEN,
            )

        msg = "Tên đăng nhập hoặc mật khẩu không chính xác!"
        return Response(
            {"success": False, "error": msg, "detail": msg},
            status=status.HTTP_401_UNAUTHORIZED,
        )


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/auth/admin-set-password/
# ─────────────────────────────────────────────────────────────────────────────

@api_view(["POST"])
@permission_classes([IsAuthenticated, require_permission("approve_password_reset_cbnv")])
def admin_set_password_view(request):
    """
    Quản trị viên đặt/cập nhật mật khẩu cho bất kỳ tài khoản nào (admin set pass).
    [Điểm 5 từ Nhóm 7]: Đi qua RBAC (quyền 'approve_password_reset_cbnv' hoặc 'is_superuser')
    và kiểm tra độ an toàn qua django.contrib.auth.password_validation.validate_password.
    Body: { "username": "...", "new_password": "..." }
    """
    target_username = request.data.get("username", "").strip()
    new_password = (
        request.data.get("new_password", "").strip()
        or request.data.get("password", "").strip()
    )

    if not target_username or not new_password:
        return Response(
            {"success": False, "error": "Vui lòng nhập tên đăng nhập và mật khẩu mới."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    UserModel = get_user_model()
    try:
        target_user = UserModel.objects.get(username=target_username)
    except UserModel.DoesNotExist:
        return Response(
            {"success": False, "error": f"Không tìm thấy tài khoản '{target_username}'."},
            status=status.HTTP_404_NOT_FOUND,
        )

    # Mật khẩu superuser chỉ superuser mới đặt lại được (nhóm ADMIN có approve_password_reset_cbnv nhưng không đủ).
    if target_user.is_superuser and not request.user.is_superuser:
        return Response(
            {"success": False, "error": "roles.messages.permissionDenied"},
            status=status.HTTP_403_FORBIDDEN,
        )

    # [Điểm 5]: Kiểm tra chất lượng mật khẩu bằng password validation chuẩn Django
    try:
        validate_password(new_password, user=target_user)
    except ValidationError as exc:
        return Response(
            {
                "success": False,
                "error": "; ".join(exc.messages),
                "errors": list(exc.messages),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    target_user.set_password(new_password)
    target_user.save(update_fields=["password"])
    return Response(
        {
            "success": True,
            "message": f"Đặt lại mật khẩu thành công cho tài khoản '{target_username}'.",
        },
        status=status.HTTP_200_OK,
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/auth/profile/
# ─────────────────────────────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def profile_view(request):
    """
    Lấy thông tin cá nhân của user đang đăng nhập.
    Yêu cầu Header: Authorization: Bearer <access_token>

    Response 200:
        { id, username, email, full_name, department, position, role, phone, avatar_url, birthday }
    """
    return Response(_build_user_payload(request.user), status=status.HTTP_200_OK)


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/auth/change-password/
# ─────────────────────────────────────────────────────────────────────────────

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def change_password_view(request):
    """
    Đổi mật khẩu người dùng đang đăng nhập.

    Request body:
        { "old_password": "...", "new_password": "..." }

    Response 200:
        { "detail": "Mật khẩu đã được cập nhật thành công." }

    Response 400:
        { "detail": "Mật khẩu cũ không đúng." }
    """
    serializer = ChangePasswordSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    user = request.user
    old_password = serializer.validated_data["old_password"]
    new_password = serializer.validated_data["new_password"]

    if not user.check_password(old_password):
        msg = "Mật khẩu hiện tại không chính xác!"
        return Response(
            {"success": False, "message": msg, "error": msg, "detail": msg},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if len(new_password) < 8:
        msg = "Mật khẩu mới phải có tối thiểu 8 ký tự!"
        return Response(
            {"success": False, "message": msg, "error": msg, "detail": msg},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if old_password == new_password:
        msg = "Mật khẩu mới phải khác mật khẩu cũ."
        return Response(
            {"success": False, "message": msg, "error": msg, "detail": msg},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user.set_password(new_password)
    user.save()

    msg = "Cập nhật mật khẩu thành công! Vui lòng đăng nhập lại."
    return Response(
        {"success": True, "message": msg, "detail": msg},
        status=status.HTTP_200_OK,
    )


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/auth/verify-password/
# ─────────────────────────────────────────────────────────────────────────────

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def verify_password_view(request):
    """
    Xác thực mật khẩu người dùng hiện tại để mở khóa màn hình làm việc hoặc xác nhận thao tác an toàn.
    Body: { "password": "..." }
    """
    password = request.data.get("password", "")
    if not password:
        msg = "Vui lòng nhập mật khẩu."
        return Response(
            {"success": False, "valid": False, "detail": msg, "error": msg},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = request.user
    is_valid = False

    # 1. Kiểm tra mật khẩu cục bộ nếu có mật khẩu hợp lệ
    if user.has_usable_password():
        is_valid = user.check_password(password)

    # 2. Nếu mật khẩu cục bộ chưa khớp, thử kiểm tra qua nhà cung cấp Alpaca (trừ tài khoản quản trị hệ thống)
    if not is_valid and not (user.is_superuser or user.is_staff):
        try:
            alpaca_res = check_alpaca_auth(user.username, password)
            if alpaca_res.get("result") is True or alpaca_res.get("success") is True:
                is_valid = True
        except Exception:
            pass

    if is_valid:
        return Response(
            {"success": True, "valid": True, "detail": "Mật khẩu chính xác."},
            status=status.HTTP_200_OK,
        )

    msg = "Mật khẩu không chính xác. Vui lòng thử lại."
    return Response(
        {"success": False, "valid": False, "detail": msg, "error": msg},
        status=status.HTTP_400_BAD_REQUEST,
    )


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/auth/logout/
# ─────────────────────────────────────────────────────────────────────────────

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """
    Đăng xuất — đưa refresh token vào blacklist để vô hiệu hóa (nếu có refresh token),
    hoặc hủy phiên làm việc.
    """
    refresh_token = request.data.get("refresh")

    if refresh_token:
        try:
            token = RefreshToken(refresh_token)
            if hasattr(token, "blacklist"):
                token.blacklist()
        except Exception:
            pass  # Nếu token không hợp lệ hoặc blacklist không bật, vẫn cho phép đăng xuất an toàn

    return Response(
        {"success": True, "message": "Đã đăng xuất", "detail": "Đã đăng xuất"},
        status=status.HTTP_200_OK,
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/accounts/staffs/ & GET /api/auth/staffs/
# ─────────────────────────────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def staffs_view(request):
    """
    GET /api/accounts/staffs/ & GET /api/auth/staffs/
    Danh sách cán bộ / nhân viên theo phòng ban cho các phân hệ khác (Document, Records...).
    Hỗ trợ lọc theo ?department= (tên đơn vị) hoặc ?don_vi_id= (ID đơn vị).
    """
    UserModel = get_user_model()
    queryset = (
        UserModel.objects.filter(is_active=True)
        .select_related("don_vi", "chuc_vu")
        .order_by("don_vi__stt_uu_tien", "chuc_vu__display_order", "ho_ten", "id")
    )

    don_vi_id = request.query_params.get("don_vi_id")
    department = request.query_params.get("department")

    if don_vi_id is not None and don_vi_id != "":
        don_vi_id_str = str(don_vi_id).strip()
        if not don_vi_id_str.isdigit():
            return Response(
                {"detail": "don_vi_id phải là số nguyên hợp lệ.", "error": "don_vi_id must be an integer."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        queryset = queryset.filter(don_vi_id=int(don_vi_id_str))
    elif department:
        queryset = queryset.filter(don_vi__ten__iexact=department.strip())

    data = []
    for u in queryset:
        dept_name = u.don_vi.ten if u.don_vi else ""
        position_name = u.chuc_vu.name if u.chuc_vu else ""
        full_name = u.ho_ten or u.username
        data.append({
            "id": u.id,
            "username": u.username,
            "ho_ten": full_name,
            "don_vi_id": u.don_vi_id,
            "don_vi_ten": dept_name,
            "chuc_vu_id": u.chuc_vu_id,
            "chuc_vu_ten": position_name,
        })
    return Response(data, status=status.HTTP_200_OK)


def _verify_sensitive_2fa_action(user, data) -> None:
    """Xác minh chủ sở hữu bằng mã OTP/Backup Code hoặc mật khẩu cục bộ khi thao tác nhạy cảm."""
    if not user.is_2fa_enabled or not user.totp_secret:
        raise twofa.TwoFactorError(
            "twofa_not_enabled",
            "Tài khoản chưa kích hoạt xác thực hai yếu tố.",
            status.HTTP_400_BAD_REQUEST,
        )

    raw_code = str(data.get("code") or "").strip()
    if raw_code:
        twofa.verify_user_twofa_code(user.id, raw_code, allow_backup_code=True)
        return

    raw_credential = data.get("password")
    if raw_credential is not None and str(raw_credential) != "":
        if not user.has_usable_password():
            raise twofa.TwoFactorError(
                "otp_required_for_external_auth",
                "Tài khoản đăng nhập qua hệ thống ngoài chưa có mật khẩu cục bộ. Vui lòng nhập mã OTP hiện tại hoặc mã dự phòng.",
                status.HTTP_400_BAD_REQUEST,
            )
        if not user.check_password(str(raw_credential)):
            raise twofa.TwoFactorError(
                "invalid_credential",
                "Mật khẩu hiện tại không chính xác.",
                status.HTTP_401_UNAUTHORIZED,
            )
        return

    raise twofa.TwoFactorError(
        "verification_required",
        "Vui lòng xác nhận bằng mật khẩu hiện tại hoặc mã xác thực 2FA.",
        status.HTTP_400_BAD_REQUEST,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def twofa_send_otp_view(request):
    """Gửi mã OTP 6 chữ số qua Email hoặc SĐT cho phiên đăng nhập 2FA."""
    temp_token = str(request.data.get("temp_token") or "").strip()
    channel = str(request.data.get("channel") or "").strip().lower()
    previous_otp_token = str(request.data.get("previous_otp_token") or "").strip() or None

    try:
        challenge = twofa.load_login_challenge_token(temp_token)
        UserModel = get_user_model()
        user = UserModel.objects.filter(pk=challenge["uid"]).first()
        if not user:
            raise twofa.TwoFactorError(
                "user_not_found",
                "Không tìm thấy tài khoản.",
                http_status=status.HTTP_401_UNAUTHORIZED,
            )
        if not user.is_active:
            raise twofa.TwoFactorError(
                "account_disabled",
                "Tài khoản đã bị vô hiệu hóa. Vui lòng liên hệ Quản trị viên.",
                http_status=status.HTTP_403_FORBIDDEN,
            )
        if not user.is_2fa_enabled or not user.totp_secret:
            raise twofa.TwoFactorError(
                "twofa_not_enabled",
                "Tài khoản chưa kích hoạt xác thực hai yếu tố.",
                http_status=status.HTTP_400_BAD_REQUEST,
            )

        result = otp_service.send_otp_challenge(
            user=user,
            channel=channel,
            purpose=otp_service.OTP_PURPOSE_2FA_LOGIN,
            previous_token=previous_otp_token,
        )
    except twofa.TwoFactorError as exc:
        return _twofa_error_response(exc)

    return Response(
        {
            "success": True,
            "otp_token": result["token"],
            "channel": result["channel"],
            "masked_destination": result["masked_destination"],
            "expires_in": result["expires_in"],
            "cooldown_seconds": result["cooldown_seconds"],
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def verify_2fa_view(request):
    """Bước 2 đăng nhập: xác thực TOTP, Backup Code hoặc Email/SMS OTP từ temp_token để cấp JWT."""
    temp_token = str(request.data.get("temp_token") or "").strip()
    raw_code = str(request.data.get("code") or "").strip()
    otp_token = str(request.data.get("otp_token") or "").strip()
    trust_device = bool(request.data.get("trust_device"))

    try:
        challenge = twofa.load_login_challenge_token(temp_token)
        if otp_token:
            verified_user, verified_method = otp_service.verify_otp_challenge(
                otp_token=otp_token,
                raw_code=raw_code,
                purpose=otp_service.OTP_PURPOSE_2FA_LOGIN,
                expected_user_id=challenge["uid"],
            )
        else:
            verified_user, verified_method = twofa.verify_user_twofa_code(
                challenge["uid"],
                raw_code,
                allow_backup_code=True,
            )
    except twofa.TwoFactorError as exc:
        return _twofa_error_response(exc)

    response = _issue_jwt_response(
        verified_user,
        auth_provider=challenge.get("provider") or "local",
        verified_via=verified_method,
    )
    if trust_device:
        response.set_cookie(
            key=twofa.TRUSTED_DEVICE_COOKIE_NAME,
            value=twofa.create_trusted_device_token(verified_user),
            max_age=twofa.TRUSTED_DEVICE_TTL_SECONDS,
            httponly=True,
            samesite="Lax",
            secure=bool(getattr(settings, "SESSION_COOKIE_SECURE", False)),
        )
    return response


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def twofa_status_view(request):
    """Lấy trạng thái 2FA và số lượng mã dự phòng còn lại của tài khoản đang đăng nhập."""
    user = request.user
    enabled = bool(user.is_2fa_enabled)
    return Response(
        {
            "enabled": enabled,
            "backup_codes_remaining": len(user.twofa_backup_codes or []) if enabled else 0,
            "has_usable_credential": bool(user.has_usable_password()),
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def twofa_setup_view(request):
    """Khởi tạo mã QR TOTP + secret tạm thời (chưa kích hoạt DB cho đến khi verify)."""
    user = request.user
    if user.is_2fa_enabled:
        return _twofa_error_response(
            twofa.TwoFactorError(
                "twofa_already_enabled",
                "Tài khoản đã bật xác thực hai yếu tố.",
                status.HTTP_400_BAD_REQUEST,
            )
        )
    return Response(twofa.create_setup_payload(user), status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def twofa_confirm_view(request):
    """Xác nhận mã OTP 6 số đầu tiên để bật 2FA chính thức và cấp 10 Backup Codes."""
    user = request.user
    if user.is_2fa_enabled:
        return _twofa_error_response(
            twofa.TwoFactorError(
                "twofa_already_enabled",
                "Tài khoản đã bật xác thực hai yếu tố.",
                status.HTTP_400_BAD_REQUEST,
            )
        )

    setup_token = str(request.data.get("setup_token") or "").strip()
    raw_code = str(request.data.get("code") or "").strip()

    try:
        raw_secret = twofa.load_setup_token(setup_token, expected_user_id=user.id)
        matched_step = twofa.find_matching_totp_step(raw_secret, raw_code, last_used_step=None)
    except twofa.TwoFactorError as exc:
        return _twofa_error_response(exc)

    if matched_step is None:
        return _twofa_error_response(
            twofa.TwoFactorError(
                "otp_invalid",
                "Mã OTP 6 chữ số không chính xác. Vui lòng kiểm tra đồng hồ thiết bị và thử lại.",
                status.HTTP_400_BAD_REQUEST,
            )
        )

    plain_codes, hashed_codes = twofa.generate_backup_codes()
    encrypted_secret = twofa.encrypt_secret(raw_secret)
    UserModel = get_user_model()

    with transaction.atomic():
        locked_user = UserModel.objects.select_for_update().get(pk=user.id)
        if locked_user.is_2fa_enabled:
            return _twofa_error_response(
                twofa.TwoFactorError(
                    "twofa_already_enabled",
                    "Tài khoản đã bật xác thực hai yếu tố.",
                    status.HTTP_400_BAD_REQUEST,
                )
            )
        locked_user.is_2fa_enabled = True
        locked_user.totp_secret = encrypted_secret
        locked_user.twofa_backup_codes = hashed_codes
        locked_user.totp_last_used_step = matched_step
        locked_user.twofa_failed_attempts = 0
        locked_user.twofa_locked_until = None
        locked_user.save(
            update_fields=[
                "is_2fa_enabled",
                "totp_secret",
                "twofa_backup_codes",
                "totp_last_used_step",
                "twofa_failed_attempts",
                "twofa_locked_until",
            ]
        )

    return Response(
        {
            "success": True,
            "enabled": True,
            "backup_codes": plain_codes,
            "backup_codes_remaining": len(plain_codes),
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def twofa_disable_view(request):
    """Tắt xác thực hai yếu tố và xóa secret/backup codes sau khi xác minh danh tính."""
    try:
        _verify_sensitive_2fa_action(request.user, request.data)
    except twofa.TwoFactorError as exc:
        return _twofa_error_response(exc)

    twofa.clear_user_twofa_state(request.user)

    return Response(
        {"success": True, "enabled": False, "backup_codes_remaining": 0},
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def twofa_regenerate_backup_codes_view(request):
    """Tạo mới bộ 10 mã dự phòng (vô hiệu hóa bộ cũ) sau khi xác minh danh tính."""
    try:
        _verify_sensitive_2fa_action(request.user, request.data)
    except twofa.TwoFactorError as exc:
        return _twofa_error_response(exc)

    plain_codes, hashed_codes = twofa.generate_backup_codes()
    UserModel = get_user_model()
    with transaction.atomic():
        locked_user = UserModel.objects.select_for_update().get(pk=request.user.id)
        if not locked_user.is_2fa_enabled:
            return _twofa_error_response(
                twofa.TwoFactorError(
                    "twofa_not_enabled",
                    "Tài khoản chưa kích hoạt xác thực hai yếu tố.",
                    status.HTTP_400_BAD_REQUEST,
                )
            )
        locked_user.twofa_backup_codes = hashed_codes
        locked_user.save(update_fields=["twofa_backup_codes"])

    return Response(
        {
            "success": True,
            "backup_codes": plain_codes,
            "backup_codes_remaining": len(plain_codes),
        },
        status=status.HTTP_200_OK,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Tự đặt lại mật khẩu (Forgot Password qua OTP Email / SMS)
# ─────────────────────────────────────────────────────────────────────────────

def _assert_self_reset_eligible(user):
    """Kiểm tra tài khoản được phép tự đặt lại mật khẩu (chặn admin cấp cao và tài khoản Bảo Long)."""
    if not user.is_active:
        raise twofa.TwoFactorError(
            "account_disabled",
            "Tài khoản đã bị vô hiệu hóa. Vui lòng liên hệ Quản trị viên.",
            http_status=status.HTTP_403_FORBIDDEN,
        )
    if user.is_superuser or user.is_staff or is_system_admin(user):
        raise twofa.TwoFactorError(
            "self_reset_restricted",
            "Tài khoản quản trị cấp cao không hỗ trợ tự đặt lại mật khẩu. Vui lòng liên hệ Quản trị viên tối cao.",
            http_status=status.HTTP_403_FORBIDDEN,
        )
    if not user.has_usable_password():
        raise twofa.TwoFactorError(
            "external_auth_restricted",
            "Tài khoản đăng nhập qua hệ thống Bảo Long. Vui lòng đổi mật khẩu trên cổng Bảo Long hoặc liên hệ Quản trị viên.",
            http_status=status.HTTP_403_FORBIDDEN,
        )


def _resolve_self_reset_user(identifier: str):
    """Tìm tài khoản theo username/email và kiểm tra điều kiện tự đặt lại mật khẩu."""
    cleaned = str(identifier or "").strip()
    if not cleaned:
        raise twofa.TwoFactorError(
            "identifier_required",
            "Vui lòng nhập tên đăng nhập hoặc email.",
            http_status=status.HTTP_400_BAD_REQUEST,
        )

    user = _find_user_by_identifier(cleaned)
    if not user:
        raise twofa.TwoFactorError(
            "account_not_found",
            "Không tìm thấy tài khoản phù hợp.",
            http_status=status.HTTP_404_NOT_FOUND,
        )
    _assert_self_reset_eligible(user)

    channels = otp_service.get_available_otp_channels(user)
    if not channels["email"] and not channels["sms"]:
        raise twofa.TwoFactorError(
            "no_recovery_channel",
            "Tài khoản chưa có email hoặc số điện thoại nhận mã. Vui lòng liên hệ Quản trị viên.",
            http_status=status.HTTP_400_BAD_REQUEST,
        )
    return user, channels


@api_view(["POST"])
@permission_classes([AllowAny])
def forgot_password_lookup_view(request):
    """Kiểm tra tài khoản và trả về kênh nhận OTP đã che (Email / SĐT)."""
    identifier = (
        request.data.get("identifier")
        or request.data.get("username")
        or request.data.get("email")
        or ""
    )
    try:
        _user, channels = _resolve_self_reset_user(str(identifier))
    except twofa.TwoFactorError as exc:
        return _twofa_error_response(exc)

    return Response(
        {
            "success": True,
            "channels": {
                "email": channels["email"],
                "sms": channels["sms"],
            },
            "masked_email": channels["masked_email"],
            "masked_phone": channels["masked_phone"],
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def forgot_password_send_otp_view(request):
    """Gửi mã OTP 6 chữ số qua Email hoặc SĐT để tự đặt lại mật khẩu."""
    identifier = (
        request.data.get("identifier")
        or request.data.get("username")
        or request.data.get("email")
        or ""
    )
    channel = str(request.data.get("channel") or "").strip().lower()
    previous_reset_token = str(request.data.get("previous_reset_token") or "").strip() or None

    try:
        user, _channels = _resolve_self_reset_user(str(identifier))
        result = otp_service.send_otp_challenge(
            user=user,
            channel=channel,
            purpose=otp_service.OTP_PURPOSE_PASSWORD_RESET,
            previous_token=previous_reset_token,
        )
    except twofa.TwoFactorError as exc:
        return _twofa_error_response(exc)

    return Response(
        {
            "success": True,
            "reset_token": result["token"],
            "channel": result["channel"],
            "masked_destination": result["masked_destination"],
            "expires_in": result["expires_in"],
            "cooldown_seconds": result["cooldown_seconds"],
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def forgot_password_confirm_view(request):
    """Xác thực OTP và cập nhật mật khẩu mới cho tài khoản đủ điều kiện."""
    reset_token = str(request.data.get("reset_token") or "").strip()
    raw_code = str(request.data.get("code") or "").strip()
    new_password = str(request.data.get("new_password") or "")
    confirm_password = str(request.data.get("confirm_password") or "")

    if not new_password or not confirm_password:
        return Response(
            {"detail": "Vui lòng nhập đầy đủ mật khẩu mới và xác nhận mật khẩu.", "code": "password_required"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if new_password != confirm_password:
        return Response(
            {"detail": "Mật khẩu xác nhận không khớp.", "code": "password_mismatch"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        verified_user, _channel = otp_service.verify_otp_challenge(
            otp_token=reset_token,
            raw_code=raw_code,
            purpose=otp_service.OTP_PURPOSE_PASSWORD_RESET,
        )
        _assert_self_reset_eligible(verified_user)
    except twofa.TwoFactorError as exc:
        return _twofa_error_response(exc)

    try:
        validate_password(new_password, user=verified_user)
    except ValidationError as exc:
        return Response(
            {
                "detail": "; ".join(exc.messages),
                "errors": list(exc.messages),
                "code": "password_invalid",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    with transaction.atomic():
        verified_user.set_password(new_password)
        verified_user.twofa_failed_attempts = 0
        verified_user.twofa_locked_until = None
        verified_user.save(update_fields=["password", "twofa_failed_attempts", "twofa_locked_until"])
        EmployeePasswordResetAudit.objects.create(
            actor=None,
            target=verified_user,
            actor_username="self_service",
            target_username=verified_user.get_username(),
            reason_code=EmployeePasswordResetAudit.Reason.FORGOT_PASSWORD,
            reason_detail=None,
        )

    return Response(
        {"success": True, "message": "Đặt lại mật khẩu thành công."},
        status=status.HTTP_200_OK,
    )


