"""
MFA qua email khi ký (issue #509, phân vùng 2 của #447), lưu trạng thái trong PostgreSQL thay Redis.

- Cờ `SIGNING_MFA_EMAIL_ENABLED` (biến môi trường hoặc `settings`), mặc định TẮT: cờ tắt thì luồng ký không đổi.
- `yeu_cau_ma`: gửi mã 6 chữ số tới email tài khoản. Mã lưu dạng HMAC (`signing_mfa_otp`), hiệu lực 10 phút, hai
  lần gửi cách nhau tối thiểu 2 phút (HTTP 429), lần gửi chỉ được ghi nhận khi email gửi thành công. Không gửi khi
  email chưa cấu hình thật (mailer console/dummy/filebased), để mã không lọt ra log máy chủ.
- `xac_minh_ma`: nhập đúng mã thì dòng mã được đánh dấu đã dùng và gắn với access token hiện tại đến khi token hết
  hạn. Kiểm tra và đánh dấu trong một giao dịch khóa dòng tài khoản nên một mã chỉ dùng được một lần, hai yêu cầu
  đồng thời cùng mã chỉ một yêu cầu thành công. Sai 5 lần thì hủy mã.
- `kiem_tra_da_xac_thuc`: `hanh_dong_ky.ky` gọi hàm này khi cờ bật; gọi thẳng API ký không vòng qua được.
Không ghi mã vào nhật ký, log hay phản hồi lỗi. Bản ghi cũ được xóa lười khi gửi mã mới (không cần cron).
Không đếm giới hạn theo ngày hoặc cửa sổ 30 phút (thuộc phương án Redis của #447).
"""

import hashlib
import hmac
import logging
import os
import re
import secrets
from datetime import datetime, timedelta, timezone as dt_timezone

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import mail
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import status

from .. import crypto
from ..errors import SigningError
from ..models import SigningMfaOtp
from . import pin as pin_service
from . import quyen_ky, thong_bao
from .audit import ghi_nhat_ky

logger = logging.getLogger(__name__)

LOAI = "signing_mfa_otp"
MUC_DICH_KY = "KY"
HAN_MA = timedelta(minutes=10)
GIAN_CACH_GUI = timedelta(minutes=2)
SO_LAN_SAI_TOI_DA = 5
GIU_BAN_GHI = timedelta(hours=1)
MA_HOP_LE = re.compile(r"^\d{6}$")
GIA_TRI_BAT = {"1", "true", "yes", "on"}
MAILER_KHONG_GUI_THAT = (
    "django.core.mail.backends.console.EmailBackend",
    "django.core.mail.backends.dummy.EmailBackend",
    "django.core.mail.backends.filebased.EmailBackend",
)


class Phien:
    """Phiên xác thực = access token đang dùng: định danh (`jti`) và thời điểm hết hạn."""

    def __init__(self, jti, het_han):
        self.jti = jti
        self.het_han = het_han


def dang_bat():
    """Cờ MFA khi ký. Đọc ở mỗi lần gọi; mặc định tắt khi không cấu hình."""
    gia_tri = getattr(settings, "SIGNING_MFA_EMAIL_ENABLED", None)
    if gia_tri is None:
        gia_tri = os.environ.get("SIGNING_MFA_EMAIL_ENABLED", "")
    return str(gia_tri).strip().lower() in GIA_TRI_BAT


def phien_tu_request(request):
    """Phiên của request: lấy `jti` và `exp` từ access token; request không có token JWT thì trả None."""
    token = getattr(request, "auth", None)
    try:
        jti = str(token["jti"])
        het_han = datetime.fromtimestamp(int(token["exp"]), tz=dt_timezone.utc)
    except (TypeError, KeyError, ValueError):
        return None
    return Phien(jti[:64], het_han)


def email_kha_dung():
    """True khi mailer sẽ gửi email thật. Mailer console/dummy/filebased hoặc thiếu máy chủ SMTP thì False."""
    duong_dan = getattr(settings, "SIGNING_EMAIL_BACKEND", "")
    if not duong_dan or duong_dan == thong_bao.SMTP_BACKEND:
        mailers = getattr(settings, "MAILERS", None)
        if mailers is not None and hasattr(mail, "mailers"):  # Django 6.1+
            duong_dan = (mailers.get("default") or {}).get("BACKEND", "")
        else:
            duong_dan = getattr(settings, "EMAIL_BACKEND", "")
            if duong_dan == thong_bao.SMTP_BACKEND and not (getattr(settings, "EMAIL_HOST", "") or "").strip():
                return False
    return bool(duong_dan) and duong_dan not in MAILER_KHONG_GUI_THAT


def _bam(nguoi_id, ma):
    khoa = crypto.derive_subkey(pin_service._bi_mat_may_chu(), "mfa-ky-otp")
    return hmac.new(khoa, f"{nguoi_id}:{ma}".encode(), hashlib.sha256).hexdigest()


def _khoa_tai_khoan(nguoi):
    """Khóa dòng tài khoản để các yêu cầu cùng lúc của một người chạy tuần tự."""
    return get_user_model().objects.select_for_update().get(pk=nguoi.pk)


def _gui_email(tai_khoan, ma):
    phut = int(HAN_MA.total_seconds() // 60)
    than = (
        f"Mã xác thực ký: {ma}\n"
        f"Mã có hiệu lực {phut} phút. Nếu bạn không thực hiện thao tác ký, hãy bỏ qua thư này và báo quản trị viên.\n\n"
        f"Signing verification code: {ma}\n"
        f"The code is valid for {phut} minutes. If you are not signing a document, ignore this email and tell an "
        "administrator.\n\n"
        "Thư gửi tự động từ phân hệ Trình ký / Automated email from the signing module."
    )
    thu = mail.EmailMessage("[Trình ký] Mã xác thực ký / Signing verification code", than, None, [tai_khoan.email])
    thong_bao.ket_noi_email().send_messages([thu])


def _xoa_ban_ghi_cu(bay_gio):
    """Xóa lười: bản ghi quá 1 giờ và không còn gắn với phiên còn hiệu lực. Giữ đủ lâu để giãn cách gửi còn đúng."""
    SigningMfaOtp.objects.filter(created_at__lt=bay_gio - GIU_BAN_GHI).filter(
        Q(phien_het_han__isnull=True) | Q(phien_het_han__lte=bay_gio)
    ).delete()


def yeu_cau_ma(nguoi, dia_chi_ip=None):
    """Sinh và gửi mã. Trả thời điểm hết hạn của mã."""
    if not dang_bat():
        raise SigningError(code="mfa_chua_bat", detail="Xác thực MFA khi ký chưa được bật.")
    if not email_kha_dung():
        raise SigningError(
            code="mfa_email_khong_kha_dung",
            detail="Email xác thực chưa được cấu hình trên máy chủ. Liên hệ quản trị viên.",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    quyen_ky.kiem_tra_tai_khoan_hoat_dong(nguoi)
    with transaction.atomic():
        tai_khoan = _khoa_tai_khoan(nguoi)
        if not (tai_khoan.email or "").strip():
            raise SigningError(
                code="tai_khoan_chua_co_email",
                detail="Tài khoản chưa cập nhật email công vụ để nhận mã xác thực ký duyệt. Liên hệ quản trị viên.",
            )
        bay_gio = timezone.now()
        gan_nhat = (SigningMfaOtp.objects.filter(nguoi_dung=tai_khoan, muc_dich=MUC_DICH_KY)
                    .order_by("-created_at", "-pk").first())
        if gan_nhat and bay_gio - gan_nhat.created_at < GIAN_CACH_GUI:
            thu_lai = gan_nhat.created_at + GIAN_CACH_GUI
            raise SigningError(
                code="gui_ma_qua_nhanh",
                detail="Vừa gửi mã xác thực, hãy chờ trước khi yêu cầu lại.",
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                fields={"thu_lai_sau": [thu_lai.isoformat()]},
            )
        _xoa_ban_ghi_cu(bay_gio)
        SigningMfaOtp.objects.filter(
            nguoi_dung=tai_khoan, muc_dich=MUC_DICH_KY, da_dung_luc__isnull=True, het_han__gt=bay_gio
        ).update(het_han=bay_gio)  # chỉ mã mới nhất còn hiệu lực
        ma = f"{secrets.randbelow(10**6):06d}"
        ban_ghi = SigningMfaOtp.objects.create(
            nguoi_dung=tai_khoan, muc_dich=MUC_DICH_KY, ma_bam=_bam(tai_khoan.pk, ma), het_han=bay_gio + HAN_MA,
        )
        try:
            _gui_email(tai_khoan, ma)
        except Exception as exc:  # SMTP/cấu hình: hoàn tác để không đặt giãn cách khi chưa gửi được
            logger.warning("Gửi mã MFA khi ký cho tài khoản %s thất bại (%s).", tai_khoan.pk, type(exc).__name__)
            raise SigningError(
                code="gui_email_that_bai",
                detail="Không gửi được email mã xác thực. Thử lại sau hoặc liên hệ quản trị viên.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            ) from None
        ghi_nhat_ky(tai_khoan, LOAI, ban_ghi.pk, "YEU_CAU_MA_MFA_KY", dia_chi_ip=dia_chi_ip)
    return ban_ghi.het_han


def xac_minh_ma(nguoi, ma, phien, dia_chi_ip=None):
    """Kiểm mã; đúng thì gắn mã với phiên hiện tại. Trả thời điểm hết hạn của phiên đã xác thực."""
    ma = (ma or "").strip()
    if not MA_HOP_LE.match(ma):  # sai định dạng không tính vào số lần sai
        raise SigningError(code="ma_khong_hop_le", detail="Mã xác thực gồm đúng 6 chữ số.")
    if phien is None:
        raise SigningError(code="phien_khong_hop_le", detail="Phiên đăng nhập không hợp lệ, hãy đăng nhập lại.")
    loi = None
    with transaction.atomic():
        tai_khoan = _khoa_tai_khoan(nguoi)
        bay_gio = timezone.now()
        ban_ghi = (SigningMfaOtp.objects.select_for_update()
                   .filter(nguoi_dung=tai_khoan, muc_dich=MUC_DICH_KY).order_by("-created_at", "-pk").first())
        if ban_ghi is None:
            raise SigningError(code="mfa_ma_khong_co", detail="Không có mã còn hiệu lực. Hãy yêu cầu gửi mã mới.")
        if ban_ghi.da_dung_luc is not None:
            raise SigningError(code="mfa_ma_da_dung", detail="Mã đã được sử dụng. Hãy yêu cầu gửi mã mới.")
        if ban_ghi.so_lan_sai >= SO_LAN_SAI_TOI_DA:
            raise SigningError(code="mfa_vuot_gioi_han_nhap",
                               detail="Nhập sai quá số lần cho phép, mã đã bị hủy. Hãy yêu cầu gửi mã mới.")
        if ban_ghi.het_han <= bay_gio:
            raise SigningError(code="mfa_ma_het_han", detail="Mã đã hết hạn. Hãy yêu cầu gửi mã mới.")
        if hmac.compare_digest(ban_ghi.ma_bam, _bam(tai_khoan.pk, ma)):
            ban_ghi.da_dung_luc = bay_gio
            ban_ghi.phien_jti = phien.jti
            ban_ghi.phien_het_han = phien.het_han
            ban_ghi.save(update_fields=["da_dung_luc", "phien_jti", "phien_het_han"])
            ghi_nhat_ky(tai_khoan, LOAI, ban_ghi.pk, "XAC_MINH_MFA_KY", dia_chi_ip=dia_chi_ip)
            return phien.het_han
        ban_ghi.so_lan_sai += 1
        con_lai = SO_LAN_SAI_TOI_DA - ban_ghi.so_lan_sai
        if con_lai <= 0:
            ban_ghi.het_han = bay_gio  # hủy mã
        ban_ghi.save(update_fields=["so_lan_sai", "het_han"])
        ghi_nhat_ky(tai_khoan, LOAI, ban_ghi.pk, "MA_MFA_KY_SAI", du_lieu_kem_theo={"so_lan_sai": ban_ghi.so_lan_sai},
                    dia_chi_ip=dia_chi_ip)
        loi = SigningError(
            code="mfa_ma_sai" if con_lai > 0 else "mfa_vuot_gioi_han_nhap",
            detail=(f"Mã không đúng. Còn {con_lai} lần thử." if con_lai > 0
                    else "Nhập sai quá số lần cho phép, mã đã bị hủy. Hãy yêu cầu gửi mã mới."),
            fields={"so_lan_con_lai": [max(con_lai, 0)]},
        )
    raise loi  # ném sau khi giao dịch đã lưu bộ đếm


def het_han_xac_thuc(nguoi, phien):
    """Thời điểm hết hạn của phiên đã xác thực cho đúng người dùng và access token này; None nếu chưa xác thực."""
    if phien is None or not phien.jti:
        return None
    return (SigningMfaOtp.objects
            .filter(nguoi_dung_id=nguoi.pk, muc_dich=MUC_DICH_KY, da_dung_luc__isnull=False, phien_jti=phien.jti,
                    phien_het_han__gt=timezone.now())
            .order_by("-phien_het_han").values_list("phien_het_han", flat=True).first())


def kiem_tra_da_xac_thuc(nguoi, phien):
    """Cờ tắt thì bỏ qua; cờ bật mà phiên chưa xác thực thì từ chối ký."""
    if dang_bat() and het_han_xac_thuc(nguoi, phien) is None:
        raise SigningError(
            code="mfa_chua_xac_thuc",
            detail="Cần xác thực mã gửi qua email trước khi ký.",
            status_code=status.HTTP_403_FORBIDDEN,
        )


def trang_thai(nguoi, phien):
    """Trạng thái MFA cho giao diện (`GET /toi/`)."""
    bat = dang_bat()
    het_han = het_han_xac_thuc(nguoi, phien) if bat else None
    return {"bat": bat, "da_xac_thuc": het_han is not None, "het_han": het_han}
