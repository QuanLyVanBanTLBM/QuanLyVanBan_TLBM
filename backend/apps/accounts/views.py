from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from authorization.permissions import require_permission
from .serializers import ChangePasswordSerializer
from .alpaca_auth import check_alpaca_auth


def _build_user_payload(user):
    """Trả về dict thông tin user dùng chung cho login & profile response, hỗ trợ cả camelCase lẫn snake_case."""
    full_name = user.ho_ten or user.username
    department = user.don_vi.ten if user.don_vi_id else "Văn phòng Trung tâm"
    position = user.chuc_vu.name if user.chuc_vu_id else ("Quản trị viên tối cao" if user.is_superuser else "Chuyên viên văn thư")
    date_joined_str = user.created_at.strftime("%Y-%m-%d") if user.created_at else ""

    return {
        "id": user.id,
        "username": user.username,
        "email": user.email or "",
        # CamelCase (theo API Contract Hieu.md)
        "fullName": full_name,
        "unit": department,
        "roleTitle": position,
        "dateJoined": date_joined_str,
        # Snake_case (tương thích backward)
        "full_name": full_name,
        "department": department,
        "position": position,
        "role": "admin" if user.is_superuser else "staff",
        "phone": user.sdt,
        "avatar_url": "",
        "birthday": user.ngay_sinh.isoformat() if user.ngay_sinh else None,
    }


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
    username = request.data.get("username", "").strip()
    password = request.data.get("password", "")

    if not username or not password:
        msg = "Vui lòng nhập đầy đủ tài khoản và mật khẩu."
        return Response(
            {"success": False, "error": msg, "detail": msg},
            status=status.HTTP_400_BAD_REQUEST,
        )

    UserModel = get_user_model()
    target_user = UserModel.objects.filter(username=username).first()

    # 1. Thử xác thực cục bộ (Local Auth)
    user = authenticate(request, username=username, password=password)

    if user is not None:
        if not user.is_active:
            msg = "Tài khoản đã bị vô hiệu hóa. Vui lòng liên hệ Quản trị viên."
            return Response(
                {"success": False, "error": msg, "detail": msg},
                status=status.HTTP_403_FORBIDDEN,
            )

        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        user_payload = _build_user_payload(user)
        user_payload["auth_provider"] = "local"

        return Response(
            {
                "success": True,
                "token": access_token,
                "access": access_token,
                "refresh": str(refresh),
                "user": user_payload,
                "auth_provider": "local",
            },
            status=status.HTTP_200_OK,
        )

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
    alpaca_res = check_alpaca_auth(username, password)

    if alpaca_res.get("success"):
        # [Điểm 3 & Điểm 4 từ Nhóm 7]:
        # Nếu tài khoản chưa có trong hệ thống QLVB, TUYỆT ĐỐI KHÔNG tự động tạo hồ sơ CBNV.
        # CBNV bắt buộc phải được Quản trị viên khởi tạo và phân quyền trước trong CSDL.
        if not target_user:
            msg = "Tài khoản chưa được phân quyền trong hệ thống. Vui lòng liên hệ Quản trị viên."
            return Response(
                {"success": False, "error": msg, "detail": msg},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not target_user.is_active:
            msg = "Tài khoản đã bị vô hiệu hóa. Vui lòng liên hệ Quản trị viên."
            return Response(
                {"success": False, "error": msg, "detail": msg},
                status=status.HTTP_403_FORBIDDEN,
            )

        # [Điểm 2 từ Nhóm 7]:
        # KHÔNG ghi đè mật khẩu cục bộ của tài khoản (không gọi target_user.set_password).
        # Cấp token JWT trực tiếp cho phiên làm việc hiện tại của nhân viên.
        refresh = RefreshToken.for_user(target_user)
        access_token = str(refresh.access_token)

        user_payload = _build_user_payload(target_user)
        user_payload["auth_provider"] = "alpaca_api"

        return Response(
            {
                "success": True,
                "token": access_token,
                "access": access_token,
                "refresh": str(refresh),
                "user": user_payload,
                "auth_provider": "alpaca_api",
            },
            status=status.HTTP_200_OK,
        )
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


