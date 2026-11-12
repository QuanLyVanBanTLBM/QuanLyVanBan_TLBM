"""System check của kho lưu tệp nghiệp vụ (issue #192)."""

from django.conf import settings
from django.core.checks import Error, Tags, register


@register(Tags.security, deploy=True)
def kiem_tra_kho_luu_tep(app_configs, **kwargs):
    """
    Production lưu tệp nghiệp vụ ở DOCUMENT_STORAGE_ROOT (thư mục tuyệt đối, tồn tại, ngoài thư mục
    release). Giá trị đã đặt nhưng sai bị `config/settings.py` từ chối khi nạp cấu hình; check này
    bắt trường hợp thiếu biến. Không đăng ký thành check thường vì `manage.py test` chạy với
    DEBUG = False và CI không đặt biến này.
    """
    if not getattr(settings, "DOCUMENT_STORAGE_ROOT", ""):
        return [Error(
            "Chưa đặt DOCUMENT_STORAGE_ROOT cho môi trường production.",
            hint="Đặt biến môi trường DOCUMENT_STORAGE_ROOT là thư mục tuyệt đối đã tồn tại, ngoài thư mục release.",
            id="documents.E001",
        )]
    return []
