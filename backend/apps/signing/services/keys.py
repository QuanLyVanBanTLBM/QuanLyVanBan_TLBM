from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import status

from .. import crypto, enums
from ..errors import ConflictError, SigningError
from ..models import SigningKey
from .audit import ghi_nhat_ky

LOAI = "signing_key"


def thach_thuc_so_huu(key):
    """Chuỗi cố định gắn với khóa; người dùng ký chuỗi này bằng khóa bí mật để chứng minh sở hữu."""
    return f"signing-key-ownership:{key.dau_van_tay}"


def _chu_so_huu(key, nguoi_thuc_hien):
    if key.nguoi_so_huu_id != nguoi_thuc_hien.pk:
        raise SigningError(
            code="khong_co_quyen", detail="Không có quyền thao tác trên khóa này.",
            status_code=status.HTTP_403_FORBIDDEN,
        )


def _khoa(key_id):
    return SigningKey.objects.select_for_update().get(pk=key_id)


@transaction.atomic
def dang_ky(nguoi_so_huu, *, ma_khoa, khoa_cong_khai, ngay_hieu_luc, ngay_het_han=None, ghi_chu="", dia_chi_ip=None):
    if not crypto.is_valid_public_key(khoa_cong_khai):
        raise SigningError(code="khoa_cong_khai_khong_hop_le", detail="Khóa công khai Ed25519 không hợp lệ.")
    try:
        with transaction.atomic():
            key = SigningKey.objects.create(
                nguoi_so_huu=nguoi_so_huu, ma_khoa=ma_khoa, khoa_cong_khai=khoa_cong_khai,
                dau_van_tay=crypto.key_fingerprint(khoa_cong_khai), thuat_toan=crypto.ALGORITHM,
                ngay_hieu_luc=ngay_hieu_luc, ngay_het_han=ngay_het_han, ghi_chu=ghi_chu,
            )
    except IntegrityError:
        raise ConflictError(code="khoa_trung", detail="Mã khóa hoặc dấu vân tay khóa đã tồn tại.")
    ghi_nhat_ky(nguoi_so_huu, LOAI, key.pk, "DANG_KY_KHOA", trang_thai_sau=key.trang_thai, dia_chi_ip=dia_chi_ip)
    return key


@transaction.atomic
def xac_minh_so_huu(key, nguoi_thuc_hien, chu_ky_so, dia_chi_ip=None):
    key = _khoa(key.pk)
    _chu_so_huu(key, nguoi_thuc_hien)
    if key.trang_thai != enums.TrangThaiKhoa.CHO_KICH_HOAT:
        raise ConflictError(code="khoa_khong_cho_kich_hoat", detail="Khóa không ở trạng thái chờ kích hoạt.")
    if not crypto.verify_signature(key.khoa_cong_khai, thach_thuc_so_huu(key).encode(), chu_ky_so):
        raise SigningError(code="chung_minh_so_huu_that_bai", detail="Chữ ký chứng minh sở hữu khóa không hợp lệ.")
    key.thoi_diem_xac_minh_so_huu = timezone.now()
    key.save(update_fields=["thoi_diem_xac_minh_so_huu"])
    ghi_nhat_ky(nguoi_thuc_hien, LOAI, key.pk, "XAC_MINH_SO_HUU_KHOA", trang_thai_truoc=key.trang_thai,
                trang_thai_sau=key.trang_thai, dia_chi_ip=dia_chi_ip)
    return key


def _kich_hoat_khoa_da_khoa(key, dia_chi_ip, nguoi_thuc_hien, hanh_dong):
    if key.trang_thai != enums.TrangThaiKhoa.CHO_KICH_HOAT:
        raise ConflictError(code="khoa_khong_cho_kich_hoat", detail="Khóa không ở trạng thái chờ kích hoạt.")
    if key.thoi_diem_xac_minh_so_huu is None:
        raise SigningError(code="khoa_chua_xac_minh_so_huu", detail="Khóa chưa được xác minh sở hữu.")
    truoc = key.trang_thai
    key.trang_thai = enums.TrangThaiKhoa.HOAT_DONG
    key.thoi_diem_kich_hoat = timezone.now()
    key.save(update_fields=["trang_thai", "thoi_diem_kich_hoat"])
    ghi_nhat_ky(nguoi_thuc_hien, LOAI, key.pk, hanh_dong, trang_thai_truoc=truoc,
                trang_thai_sau=key.trang_thai, dia_chi_ip=dia_chi_ip)


@transaction.atomic
def kich_hoat(key, nguoi_thuc_hien, dia_chi_ip=None):
    key = _khoa(key.pk)
    _chu_so_huu(key, nguoi_thuc_hien)
    if SigningKey.objects.filter(
        nguoi_so_huu=key.nguoi_so_huu, trang_thai=enums.TrangThaiKhoa.HOAT_DONG
    ).exists():
        raise ConflictError(
            code="da_co_khoa_hoat_dong",
            detail="Người dùng đã có khóa đang hoạt động; hãy xoay vòng khóa.",
        )
    _kich_hoat_khoa_da_khoa(key, dia_chi_ip, nguoi_thuc_hien, "KICH_HOAT_KHOA")
    return key


@transaction.atomic
def xoay_vong(khoa_cu, khoa_moi, nguoi_thuc_hien, dia_chi_ip=None):
    """Khóa cũ (đang hoạt động) -> DA_XOAY_VONG; khóa mới (đã xác minh) -> HOAT_DONG, cùng transaction."""
    khoa_cu, khoa_moi = _khoa(khoa_cu.pk), _khoa(khoa_moi.pk)
    _chu_so_huu(khoa_cu, nguoi_thuc_hien)
    _chu_so_huu(khoa_moi, nguoi_thuc_hien)
    if khoa_cu.trang_thai != enums.TrangThaiKhoa.HOAT_DONG:
        raise ConflictError(code="khoa_cu_khong_hoat_dong", detail="Khóa cũ không đang hoạt động.")
    truoc = khoa_cu.trang_thai
    khoa_cu.trang_thai = enums.TrangThaiKhoa.DA_XOAY_VONG
    khoa_cu.khoa_thay_the = khoa_moi
    khoa_cu.save(update_fields=["trang_thai", "khoa_thay_the"])
    ghi_nhat_ky(nguoi_thuc_hien, LOAI, khoa_cu.pk, "XOAY_VONG_KHOA", trang_thai_truoc=truoc,
                trang_thai_sau=khoa_cu.trang_thai, du_lieu_kem_theo={"khoa_thay_the": khoa_moi.pk},
                dia_chi_ip=dia_chi_ip)
    _kich_hoat_khoa_da_khoa(khoa_moi, dia_chi_ip, nguoi_thuc_hien, "KICH_HOAT_KHOA_XOAY_VONG")
    return khoa_moi


@transaction.atomic
def thu_hoi(key, nguoi_thuc_hien, ly_do, dia_chi_ip=None):
    key = _khoa(key.pk)
    _chu_so_huu(key, nguoi_thuc_hien)
    if key.trang_thai not in (enums.TrangThaiKhoa.HOAT_DONG, enums.TrangThaiKhoa.CHO_KICH_HOAT):
        raise ConflictError(code="khoa_khong_the_thu_hoi", detail="Khóa không ở trạng thái có thể thu hồi.")
    if not (ly_do or "").strip():
        raise SigningError(code="thieu_ly_do_thu_hoi", detail="Phải nhập lý do thu hồi.")
    truoc = key.trang_thai
    key.trang_thai = enums.TrangThaiKhoa.THU_HOI
    key.ngay_thu_hoi = timezone.now()
    key.save(update_fields=["trang_thai", "ngay_thu_hoi"])
    ghi_nhat_ky(nguoi_thuc_hien, LOAI, key.pk, "THU_HOI_KHOA", trang_thai_truoc=truoc,
                trang_thai_sau=key.trang_thai, chi_tiet=ly_do, dia_chi_ip=dia_chi_ip)
    return key
