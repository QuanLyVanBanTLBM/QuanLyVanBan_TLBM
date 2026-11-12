from django.apps import AppConfig


class SigningConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "signing"
    verbose_name = "Trình ký văn bản"

    def ready(self):
        from . import checks  # noqa: F401  đăng ký system check (issue #79)
