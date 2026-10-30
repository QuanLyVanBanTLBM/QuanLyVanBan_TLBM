"""
Kiểm quyền phân hệ Trình ký theo codename trần của DDL base (plan mục 8, Phase 6b).

Hợp đồng RBAC của Nhóm 7: `user.has_perm("<codename>")` qua `authorization.backends.RbacBackend`,
superuser luôn được phép. Khi backend này chưa được cấu hình (nhánh chưa có RBAC của Nhóm 7),
tra trực tiếp quyền riêng và quyền theo nhóm của người dùng; ModelBackend mặc định không nhận codename trần.
Mọi kiểm quyền của module đi qua `co_quyen`, nên khi RBAC lên staging chỉ cần sửa tệp này.
"""

from django.conf import settings
from django.contrib.auth.models import Permission
from django.db.models import Q
from rest_framework import status

from .errors import SigningError

RBAC_BACKEND = "authorization.backends.RbacBackend"

XEM_TRINH_KY = "view_trinhky"
TAO_TRINH_KY = "add_trinhky"
QUAN_LY_QUY_TRINH = "manage_signing_process"
GUI_TRINH_KY = "send_trinhky"
KY_TRINH_KY = "sign_trinhky"
HUY_TRINH_KY = "cancel_trinhky"
XEM_NHAT_KY = "view_signing_audit"


def co_quyen(user, codename):
    if not user or not user.is_authenticated or not user.is_active:
        return False
    if user.is_superuser:
        return True
    if RBAC_BACKEND in settings.AUTHENTICATION_BACKENDS:
        return user.has_perm(codename)
    return (
        Permission.objects.filter(codename=codename)
        .filter(Q(user=user) | Q(group__user=user))
        .order_by()
        .exists()
    )


def yeu_cau_quyen(user, codename):
    if not co_quyen(user, codename):
        raise SigningError(
            code="khong_co_quyen",
            detail="Tài khoản không có quyền thực hiện thao tác này.",
            status_code=status.HTTP_403_FORBIDDEN,
            fields={"quyen": [codename]},
        )
