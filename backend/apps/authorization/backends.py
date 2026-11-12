from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import Permission


class RbacBackend(ModelBackend):
    """
    RBAC độc lập theo SQL_Fix4: quyền được định danh bằng codename trần (vd 'export_donvi'),
    auth_permission.content_type_id có thể NULL nên không thể dùng cách ghép 'app_label.codename' của ModelBackend.
    has_perm chấp nhận cả 'export_donvi' lẫn 'organizations.export_donvi' (phần app_label bị bỏ qua).
    """

    def _get_permissions(self, user_obj, obj, from_name):
        if not user_obj.is_active or user_obj.is_anonymous or obj is not None:
            return set()

        cache_name = f"_rbac_{from_name}_perm_cache"
        if not hasattr(user_obj, cache_name):
            if user_obj.is_superuser:
                perms = Permission.objects.all()
            elif from_name == "user":
                perms = Permission.objects.filter(user=user_obj)
            else:
                perms = Permission.objects.filter(group__user=user_obj)
            setattr(user_obj, cache_name, set(perms.values_list("codename", flat=True)))
        return getattr(user_obj, cache_name)

    def has_perm(self, user_obj, perm, obj=None):
        if not user_obj.is_active:
            return False
        return perm.rsplit(".", 1)[-1] in self.get_all_permissions(user_obj, obj)

    def has_module_perms(self, user_obj, app_label):
        return bool(user_obj.is_active and user_obj.is_staff)
