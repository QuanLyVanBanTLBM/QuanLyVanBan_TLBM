"""Bọc private key Ed25519 bằng server pepper; PIN là yếu tố xác nhận riêng cho thao tác ký."""

import hmac
import logging
import re
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework import status

from .. import crypto, enums
from ..errors import ConflictError, SigningError
from ..models import SigningKey, SigningKeyUnlock
from .audit import ghi_nhat_ky
from .keys import _chu_so_huu

logger = logging.getLogger(__name__)

LOAI = "signing_key"
SO_LAN_SAI_TOI_DA_MOI_NGAY = 15
KDF_THUAT_TOAN = "argon2id"
KDF_SAN = {"m": 64 * 1024, "t": 3, "p": 1, "phien_ban": 19}
KDF_KHOA_HOP_LE = {"thuat_toan", "m", "t", "p", "phien_ban", "salt"}
KDF_SALT_BYTES = 16
PIN_HOP_LE = re.compile(r"^\d{6}$")
TRANG_THAI_DAT_PIN = (enums.TrangThaiKhoa.CHO_KICH_HOAT, enums.TrangThaiKhoa.HOAT_DONG)


def _bi_mat_may_chu():
    """Giữ SIGNING_PIN_SECRET riêng cho HMAC mã đặt lại PIN qua email (#478)."""
    bi_mat = getattr(settings, "SIGNING_PIN_SECRET", "")
    if not bi_mat:
        if not settings.DEBUG:
            logger.error("Thiếu SIGNING_PIN_SECRET khi DEBUG = False: từ chối thao tác PIN (signing.E001).")
            raise SigningError(
                code="chua_cau_hinh_bi_mat_pin",
                detail="Chức năng PIN chưa được cấu hình trên máy chủ. Liên hệ quản trị hệ thống.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        bi_mat = settings.SECRET_KEY
    return bi_mat.encode()


def _pepper_khoa_ky():
    pepper = getattr(settings, "SIGNING_KEY_PEPPER", "")
    if not pepper:
        if not settings.DEBUG:
            logger.error("Thiếu SIGNING_KEY_PEPPER khi DEBUG = False: từ chối thao tác khóa ký (signing.E005).")
            raise SigningError(
                code="chua_cau_hinh_pepper_khoa_ky",
                detail="Chức năng khóa ký chưa được cấu hình trên máy chủ. Liên hệ quản trị hệ thống.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        pepper = settings.SECRET_KEY
    elif pepper == settings.SECRET_KEY or pepper == getattr(settings, "SIGNING_PIN_SECRET", ""):
        logger.error("SIGNING_KEY_PEPPER phải tách biệt với bí mật khác (signing.E006).")
        raise SigningError(
            code="chua_cau_hinh_pepper_khoa_ky",
            detail="Cấu hình pepper khóa ký không hợp lệ. Liên hệ quản trị hệ thống.",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    return pepper.encode()


def _aad(key):
    return f"tlbm-signing-private-key-v1:{key.pk}:{key.dau_van_tay}".encode()


def kiem_tra_pin(pin, field="pin"):
    if not isinstance(pin, str) or not PIN_HOP_LE.fullmatch(pin):
        raise SigningError(
            code="pin_khong_hop_le", detail="PIN ký phải gồm đúng 6 chữ số.",
            fields={field: ["Phải gồm đúng 6 chữ số."]},
        )
    return pin


def kiem_tra_tham_so_kdf(tham_so):
    """Chỉ chấp nhận mức Argon2id đã chốt để tránh tham số thấp hoặc request gây cạn tài nguyên."""
    if not isinstance(tham_so, dict) or set(tham_so) != KDF_KHOA_HOP_LE:
        raise SigningError(
            code="tham_so_kdf_khong_hop_le",
            detail="Tham số KDF phải có đúng các khóa: thuat_toan, m, t, p, phien_ban, salt.",
            fields={"tham_so_kdf": ["Sai cấu trúc."]},
        )
    if str(tham_so["thuat_toan"]).lower() != KDF_THUAT_TOAN:
        raise SigningError(code="tham_so_kdf_khong_hop_le", detail="Chỉ chấp nhận Argon2id.",
                           fields={"tham_so_kdf": ["Sai thuật toán."]})
    for field, expected in KDF_SAN.items():
        value = tham_so[field]
        if isinstance(value, bool) or not isinstance(value, int) or value != expected:
            raise SigningError(code="tham_so_kdf_khong_hop_le",
                               detail=f"Tham số Argon2id '{field}' phải bằng {expected}.",
                               fields={"tham_so_kdf": [f"Sai giá trị '{field}'."]})
    salt = tham_so["salt"]
    if not isinstance(salt, str) or crypto.decode_b64_exact(salt, KDF_SALT_BYTES) is None:
        raise SigningError(code="tham_so_kdf_khong_hop_le",
                           detail=f"'salt' phải là Base64 của đúng {KDF_SALT_BYTES} byte ngẫu nhiên.",
                           fields={"tham_so_kdf": ["Sai giá trị 'salt'."]})
    return {"thuat_toan": KDF_THUAT_TOAN, **KDF_SAN, "salt": salt}


def _khoa_ma_hoa(tham_so, pepper):
    return crypto.derive_signing_key_encryption_key(
        pepper, crypto.decode_b64_exact(tham_so["salt"], KDF_SALT_BYTES),
    )


def bam_pin(pin, tham_so, pepper):
    """Tạo verifier Argon2id độc lập với khóa AES; tham số/KDF vẫn được chốt tại máy chủ."""
    return crypto.derive_signing_pin_verifier(
        pin, pepper, crypto.decode_b64_exact(tham_so["salt"], KDF_SALT_BYTES),
        memory_cost=tham_so["m"], time_cost=tham_so["t"], parallelism=tham_so["p"],
    )


def _giai_ma_khoa(key, unlock, tham_so, pepper):
    kek = _khoa_ma_hoa(tham_so, pepper)
    try:
        private_key = crypto.decrypt_signing_private_key(unlock.khoa_bi_mat_ma_hoa, kek, _aad(key))
    except ValueError:
        return None
    if not crypto.signing_private_key_matches_public(private_key, key.khoa_cong_khai):
        raise SigningError(code="khoa_bi_mat_khong_khop",
                           detail="Khóa bí mật đã mã hóa không khớp với khóa công khai.",
                           status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return private_key


def _giai_ma_private_key_input(value, key):
    private_key = crypto.decode_b64_exact(value, crypto.PRIVATE_KEY_PKCS8_BYTES)
    if private_key is None or not crypto.signing_private_key_matches_public(private_key, key.khoa_cong_khai):
        raise SigningError(code="khoa_bi_mat_khong_hop_le",
                           detail="Private key Ed25519 không hợp lệ hoặc không khớp khóa công khai.",
                           fields={"khoa_bi_mat_pkcs8": ["Không khớp khóa công khai."]})
    return private_key


def _ma_hoa_khoa(private_key, key, tham_so, pepper):
    kek = _khoa_ma_hoa(tham_so, pepper)
    return crypto.encrypt_signing_private_key(private_key, kek, _aad(key))


def _loi_het_luot(het_ngay):
    return SigningError(
        code="pin_het_luot_trong_ngay",
        detail=(f"Đã nhập sai PIN {SO_LAN_SAI_TOI_DA_MOI_NGAY} lần trong ngày; thử lại sau "
                f"{timezone.localtime(het_ngay):%d/%m/%Y %H:%M} hoặc liên hệ quản trị viên."),
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        fields={"thu_lai_sau": [het_ngay.isoformat()]},
    )


def _dau_ngay_ke_tiep(bay_gio):
    dia_phuong = timezone.localtime(bay_gio)
    return (dia_phuong + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)


def _khoa_ky_va_pin(key, nguoi_thuc_hien):
    # PIN attempts serialize on the unlock row. Locking signing_key here can deadlock
    # with the signing transaction, which locks the request first then inserts a signature.
    key = SigningKey.objects.get(pk=key.pk)
    _chu_so_huu(key, nguoi_thuc_hien)
    unlock = SigningKeyUnlock.objects.select_for_update().filter(khoa_id=key.pk).first()
    if unlock is None:
        raise ConflictError(code="pin_chua_dat", detail="Khóa ký chưa được đặt PIN.")
    return key, unlock


def _xac_minh(key, nguoi_thuc_hien, pin, trang_thai_cho_phep, khi_dung, dia_chi_ip):
    """Giải mã dưới row lock; commit bộ đếm PIN sai trước khi trả lỗi."""
    pin = kiem_tra_pin(pin)
    pepper = _pepper_khoa_ky()
    loi = None
    with transaction.atomic():
        key, unlock = _khoa_ky_va_pin(key, nguoi_thuc_hien)
        if key.trang_thai not in trang_thai_cho_phep:
            raise ConflictError(code="khoa_khong_dung_trang_thai",
                                detail="Khóa ký không ở trạng thái cho phép thao tác này.")
        bay_gio = timezone.now()
        if unlock.so_lan_sai and timezone.localdate(unlock.updated_at) < timezone.localdate(bay_gio):
            unlock.so_lan_sai = 0
            unlock.save(update_fields=["so_lan_sai", "updated_at"])
        if unlock.so_lan_sai >= SO_LAN_SAI_TOI_DA_MOI_NGAY:
            raise _loi_het_luot(_dau_ngay_ke_tiep(bay_gio))

        try:
            tham_so = kiem_tra_tham_so_kdf(unlock.tham_so_kdf)
        except SigningError as exc:
            raise SigningError(code="khoa_bi_mat_khong_doc_duoc",
                               detail="Cấu hình khóa ký trong CSDL không hợp lệ.",
                               status_code=status.HTTP_500_INTERNAL_SERVER_ERROR) from exc

        verifier = bam_pin(pin, tham_so, pepper)
        if hmac.compare_digest(verifier, unlock.ma_bam_xac_minh_pin or ""):
            private_key = _giai_ma_khoa(key, unlock, tham_so, pepper)
            if private_key is None:
                raise SigningError(
                    code="khoa_bi_mat_khong_doc_duoc",
                    detail="Không thể mở khóa ký hiện tại. Hãy liên hệ quản trị hệ thống.",
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
            if unlock.so_lan_sai:
                unlock.so_lan_sai = 0
                unlock.save(update_fields=["so_lan_sai", "updated_at"])
            return khi_dung(key, unlock, private_key)

        unlock.so_lan_sai += 1
        ghi_nhat_ky(nguoi_thuc_hien, LOAI, key.pk, "PIN_SAI",
                    du_lieu_kem_theo={"so_lan_sai": unlock.so_lan_sai}, dia_chi_ip=dia_chi_ip)
        unlock.save(update_fields=["so_lan_sai", "updated_at"])
        if unlock.so_lan_sai >= SO_LAN_SAI_TOI_DA_MOI_NGAY:
            ghi_nhat_ky(nguoi_thuc_hien, LOAI, key.pk, "PIN_HET_LUOT",
                        du_lieu_kem_theo={"so_lan_sai": unlock.so_lan_sai}, dia_chi_ip=dia_chi_ip)
        con_lai = max(SO_LAN_SAI_TOI_DA_MOI_NGAY - unlock.so_lan_sai, 0)
        loi = SigningError(code="pin_khong_dung", detail=f"PIN không đúng. Còn {con_lai} lần thử trong ngày.",
                           fields={"so_lan_con_lai": [con_lai]})
    raise loi


@transaction.atomic
def dat_pin(key, nguoi_thuc_hien, pin, khoa_bi_mat_pkcs8, tham_so_kdf, dia_chi_ip=None):
    """Đặt PIN lần đầu, mã hóa PKCS#8 server-side và chỉ lưu ciphertext + salt/KDF."""
    pin = kiem_tra_pin(pin)
    tham_so = kiem_tra_tham_so_kdf(tham_so_kdf)
    key = SigningKey.objects.select_for_update().get(pk=key.pk)
    _chu_so_huu(key, nguoi_thuc_hien)
    if key.trang_thai not in TRANG_THAI_DAT_PIN:
        raise ConflictError(code="khoa_khong_dung_trang_thai",
                            detail="Chỉ đặt PIN cho khóa đang chờ kích hoạt hoặc đang hoạt động.")
    if SigningKeyUnlock.objects.filter(khoa=key).exists():
        raise ConflictError(code="pin_da_dat", detail="Khóa ký đã có PIN; dùng chức năng đổi PIN.")
    private_key = _giai_ma_private_key_input(khoa_bi_mat_pkcs8, key)
    pepper = _pepper_khoa_ky()
    unlock = SigningKeyUnlock.objects.create(
        khoa=key,
        ma_bam_xac_minh_pin=bam_pin(pin, tham_so, pepper),
        khoa_bi_mat_ma_hoa=_ma_hoa_khoa(private_key, key, tham_so, pepper),
        tham_so_kdf=tham_so,
    )
    ghi_nhat_ky(nguoi_thuc_hien, LOAI, key.pk, "DAT_PIN",
                du_lieu_kem_theo={"tham_so_kdf": {k: v for k, v in tham_so.items() if k != "salt"}},
                dia_chi_ip=dia_chi_ip)
    return unlock


def mo_khoa_ky(key, nguoi_thuc_hien, pin, dia_chi_ip=None):
    """Xác minh PIN và trả private bytes chỉ cho luồng ký nội bộ; API không serialize giá trị này."""

    def khi_dung(key, unlock, private_key):
        ghi_nhat_ky(nguoi_thuc_hien, LOAI, key.pk, "MO_KHOA_KY", dia_chi_ip=dia_chi_ip)
        return private_key

    return _xac_minh(key, nguoi_thuc_hien, pin, (enums.TrangThaiKhoa.HOAT_DONG,), khi_dung, dia_chi_ip)


def doi_pin(key, nguoi_thuc_hien, pin_cu, pin_moi, tham_so_kdf, dia_chi_ip=None):
    """Xác minh PIN cũ, đổi verifier và mã hóa lại cùng private key với salt mới."""
    pin_moi = kiem_tra_pin(pin_moi, "pin_moi")
    if pin_moi == pin_cu:
        raise SigningError(code="pin_moi_trung_pin_cu", detail="PIN mới phải khác PIN hiện tại.",
                           fields={"pin_moi": ["Trùng PIN hiện tại."]})
    tham_so = kiem_tra_tham_so_kdf(tham_so_kdf)
    pepper = _pepper_khoa_ky()

    def khi_dung(key, unlock, private_key):
        if tham_so["salt"] == (unlock.tham_so_kdf or {}).get("salt"):
            raise SigningError(code="salt_trung_salt_cu", detail="Đổi PIN phải dùng salt mới.",
                               fields={"tham_so_kdf": ["'salt' trùng salt hiện tại."]})
        unlock.ma_bam_xac_minh_pin = bam_pin(pin_moi, tham_so, pepper)
        unlock.khoa_bi_mat_ma_hoa = _ma_hoa_khoa(private_key, key, tham_so, pepper)
        unlock.tham_so_kdf = tham_so
        unlock.so_lan_sai = 0
        unlock.khoa_den = None
        unlock.save(update_fields=["ma_bam_xac_minh_pin", "khoa_bi_mat_ma_hoa", "tham_so_kdf",
                                   "so_lan_sai", "khoa_den", "updated_at"])
        ghi_nhat_ky(nguoi_thuc_hien, LOAI, key.pk, "DOI_PIN",
                    du_lieu_kem_theo={"tham_so_kdf": {k: v for k, v in tham_so.items() if k != "salt"}},
                    dia_chi_ip=dia_chi_ip)
        return unlock

    return _xac_minh(key, nguoi_thuc_hien, pin_cu, TRANG_THAI_DAT_PIN, khi_dung, dia_chi_ip)
