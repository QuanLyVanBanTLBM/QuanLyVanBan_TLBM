"""Xác minh PIN ký bằng PBKDF2-SHA256 và bí mật máy chủ riêng."""

import hashlib
import hmac
import logging
import re
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction
from django.utils import timezone
from rest_framework import status

from ..errors import SigningError
from ..models import SigningPinCredential
from .audit import ghi_nhat_ky

logger = logging.getLogger(__name__)
PIN_HOP_LE = re.compile(r"^\d{6}$")
SO_LAN_SAI_TOI_DA_MOI_NGAY = 15
SO_LAN_SAI_MOI_CHU_KY = 5
THOI_GIAN_KHOA = timedelta(minutes=30)


def _bi_mat_may_chu():
    secret = getattr(settings, "SIGNING_PIN_SECRET", "")
    if not secret:
        if not settings.DEBUG:
            logger.error("Thiếu SIGNING_PIN_SECRET: từ chối thao tác PIN (signing.E001).")
            raise SigningError(
                code="chua_cau_hinh_bi_mat_pin",
                detail="Chức năng PIN chưa được cấu hình trên máy chủ. Liên hệ quản trị hệ thống.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        secret = settings.SECRET_KEY
    if secret == settings.SECRET_KEY and not settings.DEBUG:
        raise SigningError(
            code="chua_cau_hinh_bi_mat_pin",
            detail="Cấu hình PIN không hợp lệ. Liên hệ quản trị hệ thống.",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    return secret.encode()


def kiem_tra_pin(pin, field="pin"):
    if not isinstance(pin, str) or not PIN_HOP_LE.fullmatch(pin):
        raise SigningError(
            code="pin_khong_hop_le", detail="PIN ký phải gồm đúng 6 chữ số.",
            fields={field: ["Phải gồm đúng 6 chữ số."]},
        )
    return pin


def _preimage(pin):
    kiem_tra_pin(pin)
    return hmac.new(_bi_mat_may_chu(), b"signing-pin-verifier-v1:" + pin.encode(), hashlib.sha256).hexdigest()


def tao_verifier(pin):
    return make_password(_preimage(pin), hasher="pbkdf2_sha256")


def _dau_ngay_ke_tiep(bay_gio):
    dia_phuong = timezone.localtime(bay_gio)
    return (dia_phuong + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)


def _loi_khoa_tam(het_han, so_lan_con_lai=0):
    return SigningError(
        code="pin_bi_khoa_tam_thoi",
        detail="Đã nhập sai PIN 5 lần liên tiếp. Tạm khóa nhập PIN trong 30 phút.",
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        fields={"so_lan_con_lai": [so_lan_con_lai], "thu_lai_sau": [het_han.isoformat()]},
    )


def _loi_het_luot(het_ngay):
    return SigningError(
        code="pin_het_luot_trong_ngay",
        detail=(f"Đã nhập sai PIN {SO_LAN_SAI_TOI_DA_MOI_NGAY} lần trong ngày; thử lại sau "
                f"{timezone.localtime(het_ngay):%d/%m/%Y %H:%M} hoặc liên hệ quản trị viên."),
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        fields={"so_lan_con_lai": [0], "thu_lai_sau": [het_ngay.isoformat()]},
    )


def dat_pin(nguoi_dung, pin, *, dia_chi_ip=None):
    """Lưu PIN mới sau khi lớp OTP đã xác minh mã; thao tác reset bộ đếm/khóa PIN."""
    return dat_verifier(nguoi_dung, tao_verifier(pin), dia_chi_ip=dia_chi_ip)


def dat_verifier(nguoi_dung, verifier, *, dia_chi_ip=None, du_lieu_kem_theo=None):
    """Ghi verifier đã tạo từ PIN rõ hoặc OTP đã xác minh, không nhận plaintext PIN."""
    with transaction.atomic():
        credential = SigningPinCredential.objects.select_for_update().filter(nguoi_dung=nguoi_dung).first()
        la_khoi_phuc = credential is not None
        if credential is None:
            credential = SigningPinCredential.objects.create(
                nguoi_dung=nguoi_dung, ma_bam_xac_minh_pin=verifier,
            )
        else:
            credential.ma_bam_xac_minh_pin = verifier
            credential.so_lan_sai_ngay = 0
            credential.so_lan_sai_chu_ky = 0
            credential.ngay_dem_sai = None
            credential.khoa_den = None
            credential.save(update_fields=[
                "ma_bam_xac_minh_pin", "so_lan_sai_ngay", "so_lan_sai_chu_ky", "ngay_dem_sai", "khoa_den", "updated_at",
            ])
        ghi_nhat_ky(
            nguoi_dung, "signing_pin_credential", credential.pk,
            "KHOI_PHUC_PIN" if la_khoi_phuc else "TAO_PIN",
            dia_chi_ip=dia_chi_ip,
            du_lieu_kem_theo={"bo_dem_sai_dat_lai": la_khoi_phuc, **(du_lieu_kem_theo or {})},
        )
    return credential


def _ghi_nhat_loi(nguoi_dung, credential, *, hanh_dong, ip, so_lan_con_lai, thoi_diem):
    ghi_nhat_ky(
        nguoi_dung, "signing_pin_credential", credential.pk, hanh_dong,
        dia_chi_ip=ip,
        du_lieu_kem_theo={
            "so_lan_sai_ngay": credential.so_lan_sai_ngay,
            "so_lan_sai_chu_ky": credential.so_lan_sai_chu_ky,
            "so_lan_con_lai": so_lan_con_lai,
            "khoa_den": credential.khoa_den.isoformat() if credential.khoa_den else None,
            "thoi_diem": thoi_diem.isoformat(),
        },
    )


def _xac_thuc_trong_giao_dich(nguoi_dung, pin, dia_chi_ip):
    """Đọc và cập nhật một lần thử trong transaction đã khóa credential."""
    bay_gio = timezone.now()
    hom_nay = timezone.localdate(bay_gio)
    credential = SigningPinCredential.objects.select_for_update().filter(nguoi_dung=nguoi_dung).first()
    if credential is None:
        raise SigningError(code="pin_chua_dat", detail="Tài khoản chưa tạo PIN ký.")

    if credential.ngay_dem_sai != hom_nay:
        credential.so_lan_sai_ngay = 0
        credential.ngay_dem_sai = hom_nay
        if not credential.khoa_den or credential.khoa_den <= bay_gio:
            credential.so_lan_sai_chu_ky = 0
            credential.khoa_den = None
        credential.save(update_fields=["so_lan_sai_ngay", "so_lan_sai_chu_ky", "ngay_dem_sai", "khoa_den", "updated_at"])

    if credential.so_lan_sai_ngay >= SO_LAN_SAI_TOI_DA_MOI_NGAY:
        return _loi_het_luot(_dau_ngay_ke_tiep(bay_gio))
    if credential.khoa_den and credential.khoa_den > bay_gio:
        return _loi_khoa_tam(credential.khoa_den)
    if credential.khoa_den:
        credential.khoa_den = None
        credential.so_lan_sai_chu_ky = 0
        credential.save(update_fields=["khoa_den", "so_lan_sai_chu_ky", "updated_at"])

    if check_password(_preimage(pin), credential.ma_bam_xac_minh_pin):
        if credential.so_lan_sai_chu_ky or credential.khoa_den:
            credential.so_lan_sai_chu_ky = 0
            credential.khoa_den = None
            credential.save(update_fields=["so_lan_sai_chu_ky", "khoa_den", "updated_at"])
        return True

    credential.so_lan_sai_ngay += 1
    credential.so_lan_sai_chu_ky += 1
    so_lan_con_lai = max(0, SO_LAN_SAI_MOI_CHU_KY - credential.so_lan_sai_chu_ky)
    hanh_dong = "PIN_SAI"
    if credential.so_lan_sai_chu_ky >= SO_LAN_SAI_MOI_CHU_KY:
        credential.khoa_den = bay_gio + THOI_GIAN_KHOA
        hanh_dong = "KHOA_PIN_30_PHUT"
    credential.save(update_fields=[
        "so_lan_sai_ngay", "so_lan_sai_chu_ky", "ngay_dem_sai", "khoa_den", "updated_at",
    ])
    _ghi_nhat_loi(
        nguoi_dung, credential, hanh_dong=hanh_dong, ip=dia_chi_ip,
        so_lan_con_lai=so_lan_con_lai, thoi_diem=bay_gio,
    )
    if credential.so_lan_sai_ngay >= SO_LAN_SAI_TOI_DA_MOI_NGAY:
        return _loi_het_luot(_dau_ngay_ke_tiep(bay_gio))
    if credential.khoa_den:
        return _loi_khoa_tam(credential.khoa_den, so_lan_con_lai)
    return SigningError(
        code="pin_khong_dung",
        detail=f"PIN không đúng. Còn {so_lan_con_lai} lần thử; nhập sai đủ 5 lần sẽ tạm khóa 30 phút.",
        fields={"so_lan_con_lai": [so_lan_con_lai]},
    )


def xac_thuc(nguoi_dung, pin, *, dia_chi_ip=None):
    """Xác minh PIN, nối 5 lần sai thành chu kỳ khóa 30 phút, tối đa 15 lần/ngày."""
    kiem_tra_pin(pin)
    with transaction.atomic():
        ket_qua = _xac_thuc_trong_giao_dich(nguoi_dung, pin, dia_chi_ip)
    if isinstance(ket_qua, SigningError):
        raise ket_qua
    return ket_qua
