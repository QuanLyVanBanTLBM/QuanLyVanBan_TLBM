from rest_framework.permissions import BasePermission


class RecordsPermission(BasePermission):
    """Require the release codename for each catalog operation."""
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated or not user.is_active:
            return False
        action = {"GET": "view", "HEAD": "view", "OPTIONS": "view", "POST": "add", "PATCH": "change", "PUT": "change", "DELETE": "delete"}.get(request.method)
        model = getattr(view, "permission_model", "hoso")
        return bool(action and user.has_perm(f"records.{action}_{model}"))
