"""
Helper kiểm quyền dùng chung (RBAC contract Issue #21).

Mọi nhóm kiểm quyền bằng codename theo SQL_Fix4, không kèm app label:

    from authorization.permissions import require_permission

    @api_view(["GET"])
    @permission_classes([IsAuthenticated, require_permission("view_hoso")])
    def hoso_list(request): ...

Một view phục vụ nhiều method thì truyền dict {method: codename}:

    @api_view(["GET", "POST"])
    @permission_classes([IsAuthenticated, require_permission({"GET": "view_hoso", "POST": "add_hoso"})])
    def hoso_list_create(request): ...

Method không có trong dict bị từ chối; HEAD và OPTIONS dùng quyền của GET.
Quyền được kiểm trước khi view chạy, nên người thiếu quyền nhận 403 kể cả với id không tồn tại.

Chưa đăng nhập -> 401 (do IsAuthenticated), thiếu quyền -> 403.
Quản trị tối cao (is_superuser) luôn được phép; nhóm ADMIN được cấp đủ mọi quyền trong seed.
Chỗ kiểm theo vai trò (không phải codename) dùng `is_system_admin(user)` thay vì tự so username hay role.
"""
from rest_framework.permissions import BasePermission

DEFAULT_DENIED_MESSAGE = "roles.messages.permissionDenied"
ADMIN_GROUP_CODE = "ADMIN"


def is_system_admin(user) -> bool:
    """
    Quản trị hệ thống: tài khoản đang hoạt động là superuser hoặc thành viên nhóm quyền ADMIN (ma_nhom_quyen).

    Dùng cho các chỗ kiểm theo vai trò mà quyền codename không thay thế được (sửa dữ liệu của người khác,
    thao tác quản trị CBNV...). Không dùng username, role của hồ sơ hay is_staff để suy ra quản trị.
    Kết quả được nhớ trên đối tượng user trong vòng đời một request.
    """
    if not user or not user.is_authenticated or not user.is_active:
        return False
    if user.is_superuser:
        return True
    cached = getattr(user, "_is_system_admin", None)
    if cached is None:
        from .models import GroupInfo

        cached = GroupInfo.objects.filter(
            ma_nhom_quyen=ADMIN_GROUP_CODE, pk__in=user.groups.values("pk")
        ).exists()
        user._is_system_admin = cached
    return cached


def require_permission(codename, message: str = DEFAULT_DENIED_MESSAGE):
    """
    Tạo lớp permission DRF.

    `codename` là một chuỗi (một quyền cho mọi method) hoặc dict {method: codename} (quyền theo method).
    """
    if isinstance(codename, dict):
        mapping = {method.upper(): code for method, code in codename.items()}
        for method in ("HEAD", "OPTIONS"):
            if method not in mapping and "GET" in mapping:
                mapping[method] = mapping["GET"]
        label = "_".join(sorted(set(mapping.values())))

        def required_for(request):
            return mapping.get(request.method)

    else:
        label = codename

        def required_for(request):
            return codename

    class RequirePermission(BasePermission):
        def has_permission(self, request, view):
            user = request.user
            needed = required_for(request)
            return bool(user and user.is_authenticated and needed and user.has_perm(needed))

    RequirePermission.message = message
    RequirePermission.__name__ = f"Require_{label}"
    RequirePermission.__qualname__ = RequirePermission.__name__
    return RequirePermission
