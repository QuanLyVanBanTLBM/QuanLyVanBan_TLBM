"""
Bảo vệ khóa ký bằng PIN — signing-backend-plan.md mục 3.4 (Phase 6).

Luồng:
- dat_pin: lưu HMAC(verifier) + tham số KDF, sinh k_srv (mã hóa khi lưu), trả k_srv một lần
  để client bọc private key bằng HKDF(master_pin, k_srv, "wrap").
- mo_khoa_ky: so verifier; đúng thì trả k_srv, sai thì đếm. Sai 5 lần khóa 15 phút,
  sai 10 lần khóa cứng (quản trị mở lại sau khi xác minh danh tính).
- doi_pin: cần verifier cũ (tính vào bộ đếm); giữ nguyên k_srv để client bọc lại private key.

Bộ đếm được cập nhật dưới select_for_update và commit TRƯỚC khi trả lỗi, để lỗi
không làm rollback số lần sai. Không nhận PIN, không log verifier hay k_srv.
"""

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

LOAI = "signing_key"
NGUONG_KHOA_TAM = 5
THOI_GIAN_KHOA_TAM = timedelta(minutes=15)
NGUONG_KHOA_CUNG = 10

# Mức sàn Argon2id theo plan: m = 64 MiB (tính bằng KiB), t = 3, p = 1
KDF_THUAT_TOAN = "argon2id"
KDF_SAN = {"m": 64 * 1024, "t": 3, "p": 1}
KDF_KHOA_HOP_LE = {"thuat_toan", "m", "t", "p", "phien_ban"}

TRANG_THAI_DAT_PIN = (enums.TrangThaiKhoa.CHO_KICH_HOAT, enums.TrangThaiKhoa.HOAT_DONG)


# ── Khóa máy chủ ────────────────────────────────────────────────────────────


def _bi_mat_may_chu():
    return (getattr(settings, "SIGNING_PIN_SECRET", "") or settings.SECRET_KEY).encode()


def _khoa_mac():
    return crypto.derive_subkey(_bi_mat_may_chu(), "pin-verifier")


def _khoa_ma_hoa():
    return crypto.derive_subkey(_bi_mat_may_chu(), "server-share")


def _aad(key):
    return f"signing_key:{key.pk}:{key.dau_van_tay}".encode()


# ── Kiểm tra đầu vào ────────────────────────────────────────────────────────


def _giai_ma_xac_minh(value, field):
    raw = crypto.decode_b64_exact(value, crypto.PIN_VERIFIER_BYTES)
    if raw is None:
        raise SigningError(
            code="xac_minh_pin_khong_hop_le",
            detail="Mã xác minh PIN phải là Base64 của đúng 32 byte.",
            fields={field: ["Sai định dạng."]},
        )
    return raw


def kiem_tra_tham_so_kdf(tham_so):
    """Chuẩn hóa tham số Argon2id; từ chối giá trị dưới mức sàn của plan."""
    if not isinstance(tham_so, dict) or set(tham_so) != KDF_KHOA_HOP_LE:
        raise SigningError(
            code="tham_so_kdf_khong_hop_le",
            detail="Tham số KDF phải có đúng các khóa: thuat_toan, m, t, p, phien_ban.",
            fields={"tham_so_kdf": ["Sai cấu trúc."]},
        )
    if str(tham_so["thuat_toan"]).lower() != KDF_THUAT_TOAN:
        raise SigningError(code="tham_so_kdf_khong_hop_le", detail="Chỉ chấp nhận Argon2id.",
                           fields={"tham_so_kdf": ["Sai thuật toán."]})
    ket_qua = {"thuat_toan": KDF_THUAT_TOAN}
    for khoa in ("m", "t", "p", "phien_ban"):
        gia_tri = tham_so[khoa]
        if isinstance(gia_tri, bool) or not isinstance(gia_tri, int) or gia_tri < 1:
            raise SigningError(code="tham_so_kdf_khong_hop_le", detail=f"'{khoa}' phải là số nguyên dương.",
                               fields={"tham_so_kdf": [f"Sai giá trị '{khoa}'."]})
        ket_qua[khoa] = gia_tri
    for khoa, san in KDF_SAN.items():
        if ket_qua[khoa] < san:
            raise SigningError(
                code="tham_so_kdf_duoi_muc_san",
                detail=f"Tham số Argon2id '{khoa}' thấp hơn mức sàn {san}.",
                fields={"tham_so_kdf": [f"'{khoa}' tối thiểu {san}."]},
            )
    return ket_qua


# ── Lỗi khóa PIN ────────────────────────────────────────────────────────────


def _loi_khoa_cung():
    return SigningError(
        code="pin_khoa_cung",
        detail="PIN đã bị khóa do nhập sai quá nhiều lần. Liên hệ quản trị viên để xác minh danh tính.",
        status_code=status.HTTP_423_LOCKED,
    )


def _loi_khoa_tam(khoa_den):
    return SigningError(
        code="pin_tam_khoa",
        detail=f"PIN đang bị khóa tạm đến {timezone.localtime(khoa_den):%d/%m/%Y %H:%M:%S}.",
        status_code=status.HTTP_423_LOCKED,
        fields={"khoa_den": [khoa_den.isoformat()]},
    )


def _khoa_ky_va_pin(key, nguoi_thuc_hien):
    key = SigningKey.objects.select_for_update().get(pk=key.pk)
    _chu_so_huu(key, nguoi_thuc_hien)
    unlock = SigningKeyUnlock.objects.select_for_update().filter(khoa=key).first()
    if unlock is None:
        raise ConflictError(code="pin_chua_dat", detail="Khóa ký chưa được đặt PIN.")
    return key, unlock


def _xac_minh(key, nguoi_thuc_hien, xac_minh_pin, field, trang_thai_cho_phep, khi_dung, dia_chi_ip):
    """So verifier; đúng thì gọi khi_dung(key, unlock) và trả kết quả, sai thì đếm rồi ném lỗi."""
    raw = _giai_ma_xac_minh(xac_minh_pin, field)  # sai định dạng không tính vào bộ đếm
    loi = None
    with transaction.atomic():
        key, unlock = _khoa_ky_va_pin(key, nguoi_thuc_hien)
        if key.trang_thai not in trang_thai_cho_phep:
            raise ConflictError(code="khoa_khong_dung_trang_thai",
                                detail="Khóa ký không ở trạng thái cho phép thao tác này.")
        now = timezone.now()
        if unlock.so_lan_sai >= NGUONG_KHOA_CUNG:
            raise _loi_khoa_cung()
        if unlock.khoa_den and unlock.khoa_den > now:
            raise _loi_khoa_tam(unlock.khoa_den)

        if crypto.verify_pin_verifier(raw, _khoa_mac(), unlock.ma_bam_xac_minh_pin):
            unlock.so_lan_sai = 0
            unlock.khoa_den = None
            unlock.save(update_fields=["so_lan_sai", "khoa_den", "update_at"])
            return khi_dung(key, unlock)

        unlock.so_lan_sai += 1
        ghi_nhat_ky(nguoi_thuc_hien, LOAI, key.pk, "PIN_SAI",
                    du_lieu_kem_theo={"so_lan_sai": unlock.so_lan_sai}, dia_chi_ip=dia_chi_ip)
        if unlock.so_lan_sai >= NGUONG_KHOA_CUNG:
            ghi_nhat_ky(nguoi_thuc_hien, LOAI, key.pk, "PIN_KHOA",
                        du_lieu_kem_theo={"loai": "khoa_cung", "so_lan_sai": unlock.so_lan_sai},
                        dia_chi_ip=dia_chi_ip)
            loi = _loi_khoa_cung()
        elif unlock.so_lan_sai == NGUONG_KHOA_TAM:
            unlock.khoa_den = now + THOI_GIAN_KHOA_TAM
            ghi_nhat_ky(nguoi_thuc_hien, LOAI, key.pk, "PIN_KHOA",
                        du_lieu_kem_theo={"loai": "khoa_tam", "so_lan_sai": unlock.so_lan_sai,
                                          "khoa_den": unlock.khoa_den.isoformat()},
                        dia_chi_ip=dia_chi_ip)
            loi = _loi_khoa_tam(unlock.khoa_den)
        else:
            nguong = NGUONG_KHOA_TAM if unlock.so_lan_sai < NGUONG_KHOA_TAM else NGUONG_KHOA_CUNG
            loi = SigningError(
                code="pin_khong_dung",
                detail=f"PIN không đúng. Còn {nguong - unlock.so_lan_sai} lần thử trước khi bị khóa.",
                fields={"so_lan_con_lai": [nguong - unlock.so_lan_sai]},
            )
        unlock.save(update_fields=["so_lan_sai", "khoa_den", "update_at"])
    # Ném lỗi sau khi transaction đã commit bộ đếm
    raise loi


def _giai_ma_manh_bi_mat(key, unlock):
    try:
        return crypto.decrypt_server_share(unlock.manh_bi_mat_ma_hoa, _khoa_ma_hoa(), _aad(key))
    except ValueError:
        raise SigningError(
            code="manh_bi_mat_khong_giai_ma_duoc",
            detail="Không giải mã được mảnh bí mật máy chủ (bí mật máy chủ đã thay đổi hoặc dữ liệu bị sửa).",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ── Nghiệp vụ ───────────────────────────────────────────────────────────────


@transaction.atomic
def dat_pin(key, nguoi_thuc_hien, xac_minh_pin, tham_so_kdf, dia_chi_ip=None):
    """Đặt PIN lần đầu. Trả (unlock, k_srv) — k_srv chỉ trả trong response này."""
    raw = _giai_ma_xac_minh(xac_minh_pin, "xac_minh_pin")
    tham_so = kiem_tra_tham_so_kdf(tham_so_kdf)
    key = SigningKey.objects.select_for_update().get(pk=key.pk)
    _chu_so_huu(key, nguoi_thuc_hien)
    if key.trang_thai not in TRANG_THAI_DAT_PIN:
        raise ConflictError(code="khoa_khong_dung_trang_thai",
                            detail="Chỉ đặt PIN cho khóa đang chờ kích hoạt hoặc đang hoạt động.")
    if SigningKeyUnlock.objects.filter(khoa=key).exists():
        raise ConflictError(code="pin_da_dat", detail="Khóa ký đã có PIN; dùng chức năng đổi PIN.")
    manh_bi_mat = crypto.new_server_share()
    unlock = SigningKeyUnlock.objects.create(
        khoa=key,
        ma_bam_xac_minh_pin=crypto.hash_pin_verifier(raw, _khoa_mac()),
        manh_bi_mat_ma_hoa=crypto.encrypt_server_share(manh_bi_mat, _khoa_ma_hoa(), _aad(key)),
        tham_so_kdf=tham_so,
    )
    ghi_nhat_ky(nguoi_thuc_hien, LOAI, key.pk, "DAT_PIN", du_lieu_kem_theo={"tham_so_kdf": tham_so},
                dia_chi_ip=dia_chi_ip)
    return unlock, manh_bi_mat


def mo_khoa_ky(key, nguoi_thuc_hien, xac_minh_pin, dia_chi_ip=None):
    """Xác minh PIN để lấy k_srv trước khi ký. Chỉ áp dụng cho khóa đang hoạt động."""

    def khi_dung(key, unlock):
        manh_bi_mat = _giai_ma_manh_bi_mat(key, unlock)
        ghi_nhat_ky(nguoi_thuc_hien, LOAI, key.pk, "MO_KHOA_KY", dia_chi_ip=dia_chi_ip)
        return unlock, manh_bi_mat

    return _xac_minh(key, nguoi_thuc_hien, xac_minh_pin, "xac_minh_pin",
                     (enums.TrangThaiKhoa.HOAT_DONG,), khi_dung, dia_chi_ip)


def doi_pin(key, nguoi_thuc_hien, xac_minh_pin_cu, xac_minh_pin_moi, tham_so_kdf, dia_chi_ip=None):
    """Đổi PIN (cần PIN cũ). Giữ nguyên k_srv và trả lại để client bọc lại private key."""
    raw_moi = _giai_ma_xac_minh(xac_minh_pin_moi, "xac_minh_pin_moi")
    tham_so = kiem_tra_tham_so_kdf(tham_so_kdf)

    def khi_dung(key, unlock):
        ma_bam_moi = crypto.hash_pin_verifier(raw_moi, _khoa_mac())
        if crypto.verify_pin_verifier(raw_moi, _khoa_mac(), unlock.ma_bam_xac_minh_pin):
            raise SigningError(code="pin_moi_trung_pin_cu", detail="PIN mới phải khác PIN hiện tại.",
                               fields={"xac_minh_pin_moi": ["Trùng PIN hiện tại."]})
        manh_bi_mat = _giai_ma_manh_bi_mat(key, unlock)
        unlock.ma_bam_xac_minh_pin = ma_bam_moi
        unlock.tham_so_kdf = tham_so
        unlock.save(update_fields=["ma_bam_xac_minh_pin", "tham_so_kdf", "update_at"])
        ghi_nhat_ky(nguoi_thuc_hien, LOAI, key.pk, "DOI_PIN", du_lieu_kem_theo={"tham_so_kdf": tham_so},
                    dia_chi_ip=dia_chi_ip)
        return unlock, manh_bi_mat

    return _xac_minh(key, nguoi_thuc_hien, xac_minh_pin_cu, "xac_minh_pin_cu", TRANG_THAI_DAT_PIN,
                     khi_dung, dia_chi_ip)
