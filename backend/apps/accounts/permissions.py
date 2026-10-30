"""
Permissions cho phân hệ Quản lý Cán bộ Nhân viên (accounts - Issue #24).
"""
from rest_framework.permissions import BasePermission
from authorization.permissions import require_permission, DEFAULT_DENIED_MESSAGE


class CanChangeEmployeePermission(BasePermission):
    """
    Quyền cập nhật thông tin Cán bộ Nhân viên (accounts.Employee):
    - Superuser: Toàn quyền sửa bất kỳ CBNV nào.
    - Chỉ superuser/admin được sửa bất kỳ CBNV nào trong hệ thống.
    - Có quyền 'change_self_cbnv': CHỈ ĐƯỢC sửa chính bản thân mình (obj.id == request.user.id),
      và CHỈ ĐƯỢC sửa các trường thông tin cá nhân (sdt, email, ngay_sinh, avatar_url).
      Nếu gửi bất kỳ trường nào khác (nhom_quyen_ids, trang_thai, don_vi_id, chuc_vu_id, chuc_danh, is_public, ghi_chu)
      thì bị từ chối 403 Forbidden với DEFAULT_DENIED_MESSAGE.
    - Ngược lại: 403 Forbidden.
    """
    message = DEFAULT_DENIED_MESSAGE

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        return bool(user.has_perm("change_full_cbnv") or user.has_perm("change_self_cbnv"))

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        if obj.id != user.id or not user.has_perm("change_self_cbnv"):
            return False
        # Người không phải admin chỉ được cập nhật trường hồ sơ cá nhân.
        if hasattr(request, "data") and isinstance(request.data, dict):
            allowed_self_fields = {"sdt", "email", "ngay_sinh", "avatar_url"}
            disallowed = set(request.data.keys()) - allowed_self_fields
            if disallowed:
                return False
        return True


class IsEmployeeAdminOnly(BasePermission):
    """Chỉ tài khoản quản trị tối cao được thực hiện thao tác quản trị CBNV."""
    message = DEFAULT_DENIED_MESSAGE

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_superuser)


class CanViewGroupPermission(BasePermission):
    """
    Quyền xem danh sách nhóm quyền phục vụ cấu hình CBNV:
    Yêu cầu quyền view_nhomquyen, change_full_cbnv hoặc add_cbnv (hoặc superuser).
    """
    message = DEFAULT_DENIED_MESSAGE

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        return bool(
            user.has_perm("view_nhomquyen")
            or user.has_perm("change_full_cbnv")
            or user.has_perm("add_cbnv")
        )
