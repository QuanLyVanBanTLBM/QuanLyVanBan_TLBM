"""
Đặt lại PIN bằng mã xác thực gửi qua email (issue #478, phân vùng 1 của #447).

Private key được mã hóa độc lập PIN bằng SIGNING_KEY_PEPPER; xác thực email chỉ thay verifier PIN
và bộ đếm sai, không thu hồi khóa, đổi public key hoặc ghi lại ciphertext.
- `yeu_cau_ma`: gửi mã 6 chữ số tới email tài khoản; mã lưu dạng băm (`signing_pin_reset_code`), hiệu lực 10 phút,
  hai lần gửi cách nhau tối thiểu 2 phút. Lần gửi chỉ được ghi nhận khi email gửi thành công.
- `xac_nhan_ma`: nhập đúng mã và PIN mới; chỉ cập nhật verifier của khóa đang hoạt động.
  Sai 5 lần thì hủy mã (mã 6 chữ số cần giới hạn riêng để không bị dò trong thời gian hiệu lực).
Không giới hạn thao tác nhập PIN khi ký ở đây; xem `pin.py`.
"""

import hashlib
import hmac
import logging
import re
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import mail
from django.db import transaction
from django.utils import timezone
from rest_framework import status

from .. import crypto, enums
from ..errors import ConflictError, SigningError
from ..models import SigningKey, SigningKeyUnlock, SigningPinResetCode
from ..tich_hop.to_chuc import ten_hien_thi
from . import pin as pin_service
from . import quyen_ky, thong_bao
from .audit import ghi_nhat_ky

logger = logging.getLogger(__name__)

LOAI = "signing_pin_reset"
HAN_MA = timedelta(minutes=10)
GIAN_CACH_GUI = timedelta(minutes=2)
SO_LAN_SAI_TOI_DA = 5
MA_HOP_LE = re.compile(r"^\d{6}$")


def _bam(ma):
    khoa = crypto.derive_subkey(pin_service._bi_mat_may_chu(), "pin-reset-code")
    return hmac.new(khoa, ma.encode(), hashlib.sha256).hexdigest()


def _khoa_tai_khoan(nguoi):
    """Khóa dòng tài khoản để các yêu cầu cùng lúc của một người chạy tuần tự."""
    return get_user_model().objects.select_for_update().get(pk=nguoi.pk)


def _gui_email(tai_khoan, ma):
    ten = ten_hien_thi(tai_khoan)
    phut = int(HAN_MA.total_seconds() // 60)
    than = (
        f"Xin chào {ten},\n\n"
        f"Mã xác thực đặt lại PIN ký: {ma}\n"
        f"Mã có hiệu lực {phut} phút. Nhập mã cùng PIN mới để giữ nguyên khóa ký hiện tại. "
        "Nếu bạn không yêu cầu, hãy bỏ qua thư này và báo quản trị viên.\n\n"
        f"Hello {ten},\n\n"
        f"Your signing PIN reset code: {ma}\n"
        f"The code is valid for {phut} minutes. Enter it with a new PIN to keep your current signing key. "
        "If you did not request it, ignore this email and tell an administrator.\n\n"
        "Thư gửi tự động từ phân hệ Trình ký / Automated email from the signing module."
    )
    thu = mail.EmailMessage("[Trình ký] Mã đặt lại PIN / PIN reset code", than, None, [tai_khoan.email])
    thong_bao.ket_noi_email().send_messages([thu])


def yeu_cau_ma(nguoi, dia_chi_ip=None):
    """Sinh và gửi mã. Trả thời điểm hết hạn của mã."""
    quyen_ky.kiem_tra_tai_khoan_hoat_dong(nguoi)
    with transaction.atomic():
        tai_khoan = _khoa_tai_khoan(nguoi)
        if not (tai_khoan.email or "").strip():
            raise SigningError(
                code="tai_khoan_chua_co_email",
                detail="Tài khoản chưa cập nhật email công vụ để nhận mã xác thực. Liên hệ quản trị viên.",
            )
        key = (SigningKey.objects.select_for_update().filter(
            nguoi_so_huu=tai_khoan,
            trang_thai=enums.TrangThaiKhoa.HOAT_DONG,
        ).order_by("pk").first())
        if key is None or not SigningKeyUnlock.objects.filter(khoa=key).exists():
            raise ConflictError(
                code="pin_chua_dat",
                detail="Tài khoản không có khóa ký hoạt động đã đặt PIN để khôi phục.",
            )
        bay_gio = timezone.now()
        gan_nhat = SigningPinResetCode.objects.filter(nguoi_dung=tai_khoan).order_by("-created_at", "-pk").first()
        if gan_nhat and bay_gio - gan_nhat.created_at < GIAN_CACH_GUI:
            thu_lai = gan_nhat.created_at + GIAN_CACH_GUI
            raise SigningError(
                code="gui_ma_qua_nhanh",
                detail="Vừa gửi mã xác thực, hãy chờ trước khi yêu cầu lại.",
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                fields={"thu_lai_sau": [thu_lai.isoformat()]},
            )
        SigningPinResetCode.objects.filter(
            nguoi_dung=tai_khoan, da_dung_luc__isnull=True, het_han__gt=bay_gio
        ).update(het_han=bay_gio)  # chỉ mã mới nhất còn hiệu lực
        ma = f"{secrets.randbelow(10**6):06d}"
        ban_ghi = SigningPinResetCode.objects.create(
            nguoi_dung=tai_khoan, khoa=key, ma_bam=_bam(ma), het_han=bay_gio + HAN_MA,
        )
        try:
            _gui_email(tai_khoan, ma)
        except Exception as exc:  # SMTP/cấu hình: hoàn tác để không đặt giãn cách khi chưa gửi được
            logger.warning("Gửi mã đặt lại PIN cho tài khoản %s thất bại: %s", tai_khoan.pk, exc)
            raise SigningError(
                code="gui_email_that_bai",
                detail="Không gửi được email mã xác thực. Thử lại sau hoặc liên hệ quản trị viên.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            ) from exc
        ghi_nhat_ky(tai_khoan, LOAI, ban_ghi.pk, "YEU_CAU_MA_DAT_LAI_PIN", dia_chi_ip=dia_chi_ip)
    return ban_ghi.het_han


def xac_nhan_ma(nguoi, ma, pin_moi, dia_chi_ip=None):
    """Kiểm mã và thay verifier PIN cho khóa đang hoạt động; không đổi khóa/ciphertext."""
    ma = (ma or "").strip()
    if not MA_HOP_LE.match(ma):  # sai định dạng không tính vào số lần sai
        raise SigningError(code="ma_khong_hop_le", detail="Mã xác thực gồm đúng 6 chữ số.")
    pin_moi = pin_service.kiem_tra_pin(pin_moi, "pin_moi")
    loi = None
    with transaction.atomic():
        tai_khoan = _khoa_tai_khoan(nguoi)
        bay_gio = timezone.now()
        ban_ghi = (SigningPinResetCode.objects.select_for_update()
                   .filter(nguoi_dung=tai_khoan, da_dung_luc__isnull=True, het_han__gt=bay_gio,
                           so_lan_sai__lt=SO_LAN_SAI_TOI_DA)
                   .order_by("-created_at", "-pk").first())
        if ban_ghi is None:
            raise SigningError(
                code="ma_het_han_hoac_khong_co",
                detail="Không có mã còn hiệu lực. Hãy yêu cầu gửi mã mới.",
            )
        if hmac.compare_digest(ban_ghi.ma_bam, _bam(ma)):
            key = (SigningKey.objects.select_for_update()
                   .filter(pk=ban_ghi.khoa_id, nguoi_so_huu=tai_khoan,
                           trang_thai=enums.TrangThaiKhoa.HOAT_DONG)
                   .order_by("pk").first())
            if key is None:
                raise ConflictError(
                    code="khoa_khong_dung_trang_thai",
                    detail="Không còn khóa ký hoạt động để khôi phục PIN.",
                )
            unlock = SigningKeyUnlock.objects.select_for_update().filter(khoa=key).first()
            if unlock is None:
                raise ConflictError(code="pin_chua_dat", detail="Khóa ký hiện tại chưa có verifier PIN.")
            try:
                tham_so = pin_service.kiem_tra_tham_so_kdf(unlock.tham_so_kdf)
            except SigningError as exc:
                raise SigningError(
                    code="khoa_bi_mat_khong_doc_duoc",
                    detail="Cấu hình khóa ký trong CSDL không hợp lệ.",
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                ) from exc
            pepper = pin_service._pepper_khoa_ky()
            try:
                private_key = pin_service._giai_ma_khoa(key, unlock, tham_so, pepper)
            except SigningError as exc:
                if exc.get_codes() != "khoa_bi_mat_khong_khop":
                    raise
                private_key = None
            if private_key is None:
                raise ConflictError(
                    code="khoa_bi_mat_khong_doc_duoc",
                    detail=("Không thể xác minh khóa ký hiện tại nên chưa đặt lại PIN. "
                            "Khóa và PIN hiện tại chưa thay đổi; hãy liên hệ quản trị hệ thống."),
                )
            unlock.ma_bam_xac_minh_pin = pin_service.bam_pin(pin_moi, tham_so, pepper)
            unlock.so_lan_sai = 0
            unlock.khoa_den = None
            unlock.save(update_fields=["ma_bam_xac_minh_pin", "so_lan_sai", "khoa_den", "updated_at"])
            ban_ghi.da_dung_luc = bay_gio
            ban_ghi.save(update_fields=["da_dung_luc"])
            ghi_nhat_ky(tai_khoan, "signing_key", key.pk, "DAT_LAI_PIN_QUA_EMAIL",
                        du_lieu_kem_theo={"ma_dat_lai_id": ban_ghi.pk}, dia_chi_ip=dia_chi_ip)
            ghi_nhat_ky(tai_khoan, LOAI, ban_ghi.pk, "XAC_NHAN_MA_DAT_LAI_PIN",
                        du_lieu_kem_theo={"khoa_id": key.pk}, dia_chi_ip=dia_chi_ip)
            return key.pk
        ban_ghi.so_lan_sai += 1
        con_lai = SO_LAN_SAI_TOI_DA - ban_ghi.so_lan_sai
        if con_lai <= 0:
            ban_ghi.het_han = bay_gio  # hủy mã
        ban_ghi.save(update_fields=["so_lan_sai", "het_han"])
        ghi_nhat_ky(tai_khoan, LOAI, ban_ghi.pk, "MA_DAT_LAI_PIN_SAI",
                    du_lieu_kem_theo={"so_lan_sai": ban_ghi.so_lan_sai}, dia_chi_ip=dia_chi_ip)
        loi = SigningError(
            code="ma_khong_dung" if con_lai > 0 else "ma_bi_huy",
            detail=(f"Mã không đúng. Còn {con_lai} lần thử." if con_lai > 0
                    else "Nhập sai quá số lần cho phép, mã đã bị hủy. Hãy yêu cầu gửi mã mới."),
            fields={"so_lan_con_lai": [max(con_lai, 0)]},
        )
    raise loi  # ném sau khi giao dịch đã lưu bộ đếm
