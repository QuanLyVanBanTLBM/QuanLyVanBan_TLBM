"""Shared permission checks for the AI API and its SQL-backed source."""


def has_permission_codename(user, codename):
    """Kiểm quyền theo codename RBAC; tài khoản bị khóa hoặc chưa đăng nhập luôn bị từ chối."""
    if not getattr(user, "is_authenticated", False) or not getattr(user, "is_active", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    return user.has_perm(codename)


def is_ai_admin(user):
    """Quản lý kho tài liệu và cài đặt AI: chỉ superuser (MVP, chưa có mã quyền riêng trong DDL)."""
    return bool(
        getattr(user, "is_authenticated", False)
        and getattr(user, "is_active", False)
        and getattr(user, "is_superuser", False)
    )
