from django.apps import AppConfig


class DocumentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "documents"
    verbose_name = "Quản lý Văn bản"

    def ready(self):
        from . import checks  # noqa: F401  đăng ký system check kho lưu tệp (issue #192)
