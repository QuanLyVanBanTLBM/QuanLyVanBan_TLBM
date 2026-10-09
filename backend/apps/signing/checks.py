"""System check của phân hệ Trình ký (issue #79): bí mật PIN riêng ở môi trường production."""

from django.conf import settings
from django.core.checks import Error, Tags, Warning, register


@register(Tags.security, deploy=True)
def kiem_tra_bi_mat_pin(app_configs, **kwargs):
    """
    `SIGNING_PIN_SECRET` dẫn xuất khóa băm verifier PIN và khóa mã hóa `k_srv` (plan mục 3.4).
    Chạy trong `manage.py check --deploy` (cổng kiểm tra cấu hình production). Không đăng ký thành
    check thường vì `manage.py test` luôn đặt DEBUG = False: check thường sẽ chặn test của mọi nhóm
    khi CI không đặt biến này. Lúc chạy, `services.pin._bi_mat_may_chu` từ chối hoạt động nếu
    DEBUG = False mà thiếu biến, kể cả khi server không chạy system check (gunicorn).
    """
    bi_mat = getattr(settings, "SIGNING_PIN_SECRET", "")
    if not bi_mat:
        return [Error(
            "Chưa đặt SIGNING_PIN_SECRET cho môi trường production.",
            hint="Đặt biến môi trường SIGNING_PIN_SECRET (chuỗi ngẫu nhiên riêng, không dùng lại SECRET_KEY).",
            id="signing.E001",
        )]
    if bi_mat == settings.SECRET_KEY:
        return [Error(
            "SIGNING_PIN_SECRET trùng SECRET_KEY.",
            hint="Dùng một chuỗi ngẫu nhiên riêng cho SIGNING_PIN_SECRET.",
            id="signing.E002",
        )]
    return []


@register(Tags.security, deploy=True)
def kiem_tra_thu_muc_tep(app_configs, **kwargs):
    """Production lưu tệp trình ký ở thư mục cấu hình riêng (storage.py); dev dùng backend/media/signing."""
    if not getattr(settings, "SIGNING_DOCUMENT_ROOT", ""):
        return [Error(
            "Chưa đặt SIGNING_DOCUMENT_ROOT cho môi trường production.",
            hint="Đặt biến môi trường SIGNING_DOCUMENT_ROOT là thư mục lưu tệp trình ký (ngoài thư mục mã nguồn).",
            id="signing.E003",
        )]
    return []


@register(Tags.compatibility, deploy=True)
def kiem_tra_phong_chu_pdf(app_configs, **kwargs):
    """Tệp PDF hoàn tất cần phông có dấu tiếng Việt (Phase 10); thiếu thì việc ký vẫn chạy, tạo tệp báo lỗi."""
    from .pdf_hoan_tat import tim_phong_chu

    if tim_phong_chu() is None:
        return [Warning(
            "Không tìm thấy phông chữ tiếng Việt để tạo tệp PDF hoàn tất của Trình ký.",
            hint="Cài fonts-dejavu-core (hoặc Noto Sans) hoặc đặt SIGNING_PDF_FONT là đường dẫn tệp .ttf "
                 "có dấu tiếng Việt.",
            id="signing.W001",
        )]
    return []
