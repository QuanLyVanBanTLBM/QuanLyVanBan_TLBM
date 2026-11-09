"""System checks cho cấu hình PIN ký và nhà cung cấp SMS ở môi trường production."""

from django.conf import settings
from django.core.checks import Error, Tags, Warning, register


@register(Tags.security, deploy=True)
def kiem_tra_bi_mat_pin(app_configs, **kwargs):
    """
    `SIGNING_PIN_SECRET` dùng để tạo verifier PIN và HMAC OTP.
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
def kiem_tra_cau_hinh_sms_otp(app_configs, **kwargs):
    """SMS là kênh OTP mặc định; production phải có endpoint HTTPS, Authorization và sender."""
    url = getattr(settings, "SIGNING_SMS_URL", "")
    authorization = getattr(settings, "SIGNING_SMS_AUTHORIZATION", "")
    sender = getattr(settings, "SIGNING_SMS_FROM", "")
    if not url or not authorization or not sender:
        return [Error(
            "Chưa cấu hình đầy đủ SMS OTP cho môi trường production.",
            hint="Đặt SIGNING_SMS_URL, SIGNING_SMS_AUTHORIZATION và SIGNING_SMS_FROM; không lưu thông tin xác thực trong mã nguồn.",
            id="signing.E005",
        )]
    if not url.startswith("https://"):
        return [Error(
            "SIGNING_SMS_URL phải dùng HTTPS.",
            hint="Dùng endpoint HTTPS để bảo vệ mã OTP và thông tin người nhận khi gửi tới nhà cung cấp.",
            id="signing.E006",
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


def _backend_email_hieu_luc():
    """Đường dẫn backend email thực dùng để gửi thông báo trình ký (xem `services.thong_bao.ket_noi_email`)."""
    from .services.thong_bao import SMTP_BACKEND

    rieng = getattr(settings, "SIGNING_EMAIL_BACKEND", "")
    if rieng and rieng != SMTP_BACKEND:
        return rieng
    if hasattr(settings, "MAILERS"):  # Django 6.1: không đọc EMAIL_BACKEND khi đã khai báo MAILERS
        mac_dinh = settings.MAILERS.get("default")
        return mac_dinh.get("BACKEND", SMTP_BACKEND) if mac_dinh is not None else ""
    return settings.EMAIL_BACKEND


@register(Tags.compatibility)
def kiem_tra_cau_hinh_email(app_configs, **kwargs):
    """
    Thông báo trình ký gửi email bằng địa chỉ DEFAULT_FROM_EMAIL. Gửi qua SMTP mà để trống thì mọi thư lỗi
    "Invalid address ''" (ghi THAT_BAI trong outbox). SIGNING_EMAIL_BACKEND chỉ để chọn backend không cần máy chủ
    (console, locmem); đặt SMTP mà dự án chưa cấu hình EMAIL_HOST thì thư không đi SMTP.
    """
    from django.utils.module_loading import import_string

    from .services.thong_bao import SMTP_BACKEND

    loi = []
    rieng = getattr(settings, "SIGNING_EMAIL_BACKEND", "")
    if rieng and rieng != SMTP_BACKEND:
        try:
            import_string(rieng)
        except ImportError:
            loi.append(Error(
                f"SIGNING_EMAIL_BACKEND không nạp được: {rieng!r}.",
                hint="Để trống (dùng cấu hình email chung) hoặc đặt django.core.mail.backends.console.EmailBackend.",
                id="signing.E004",
            ))
            return loi
    backend = _backend_email_hieu_luc()
    if rieng == SMTP_BACKEND and backend != SMTP_BACKEND:
        loi.append(Warning(
            "SIGNING_EMAIL_BACKEND đặt SMTP nhưng cấu hình email chung chưa dùng SMTP (chưa đặt EMAIL_HOST).",
            hint="Đặt EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD; SIGNING_EMAIL_BACKEND để trống.",
            id="signing.W002",
        ))
    if backend == SMTP_BACKEND and not (getattr(settings, "DEFAULT_FROM_EMAIL", "") or "").strip():
        loi.append(Warning(
            "Gửi email qua SMTP nhưng DEFAULT_FROM_EMAIL trống: thông báo trình ký sẽ lỗi \"Invalid address ''\".",
            hint="Đặt biến môi trường DEFAULT_FROM_EMAIL, ví dụ: Hệ thống QLVB <qlvb@baohiembaolong.vn>.",
            id="signing.W003",
        ))
    return loi
