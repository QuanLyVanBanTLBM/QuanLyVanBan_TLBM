from django.apps import AppConfig

class RecordsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.records'  # Đường dẫn module chuẩn theo kiến trúc
    verbose_name = 'Quản lý Hồ sơ và Loại văn bản'