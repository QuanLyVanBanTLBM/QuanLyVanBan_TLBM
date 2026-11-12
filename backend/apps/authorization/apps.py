from django.apps import AppConfig
from django.db.models.signals import post_migrate


class AuthorizationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "authorization"
    verbose_name = "roles.title"

    def ready(self):
        from django.contrib.auth.management import create_permissions

        # Quyền do SQL_Fix4/migration quản lý (codename trần, content_type NULL, module_ten NOT NULL).
        # Tín hiệu tự sinh quyền của Django sẽ vi phạm NOT NULL(module_ten) và UNIQUE(codename) nên phải tắt.
        post_migrate.disconnect(create_permissions, dispatch_uid="django.contrib.auth.management.create_permissions")

        # Meta.ordering mặc định của Permission đi qua content_type -> INNER JOIN làm mất mọi quyền có
        # content_type_id NULL (toàn bộ quyền chuẩn SQL_Fix4) ở has_perm, M2M group.permissions, v.v.
        from django.contrib.auth.models import Permission

        Permission._meta.ordering = ["id"]
