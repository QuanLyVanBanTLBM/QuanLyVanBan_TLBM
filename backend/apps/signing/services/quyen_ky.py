"""
Khóa tạm thời quyền ký của tài khoản do quản trị viên đặt (issue #449, phân vùng 3 của #447).

- khoa_quyen: khóa 1 giờ, 8 giờ, 24 giờ hoặc đến khi được bật lại; bắt buộc lý do.
- bat_lai_quyen: bật lại trước hạn hoặc khi khóa không thời hạn; bắt buộc lý do.
- kiem_tra_duoc_ky: chặn thao tác ký khi quyền ký đang bị khóa.

Mỗi tài khoản có tối đa một dòng khóa chưa được bật lại (chỉ mục duy nhất một phần). Dòng đã qua hạn nhưng chưa đóng
được đóng khi khóa lại; trong thời gian đó `khoa_dang_hieu_luc` đã coi như không còn khóa. Mọi thao tác ghi
`signing_audit_log` trong cùng transaction.
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import status

from ..errors import ConflictError, SigningError
from ..models import SigningRightLock
from ..tich_hop import to_chuc
from .audit import ghi_nhat_ky

LOAI = "signing_right_lock"
TRANG_THAI_DANG_KHOA = "DANG_KHOA"
TRANG_THAI_DA_BAT_LAI = "DA_BAT_LAI"

DEN_KHI_BAT_LAI = "den_khi_bat_lai"
THOI_HAN_KHOA = {
    "1_gio": timedelta(hours=1),
    "8_gio": timedelta(hours=8),
    "24_gio": timedelta(hours=24),
    DEN_KHI_BAT_LAI: None,
}


def _yeu_cau_quan_tri(nguoi_thuc_hien):
    if not to_chuc.la_quan_tri(nguoi_thuc_hien):
        raise SigningError(
            code="khong_co_quyen", detail="Chỉ quản trị viên được khóa hoặc bật lại quyền ký của tài khoản khác.",
            status_code=status.HTTP_403_FORBIDDEN,
        )


def _yeu_cau_ly_do(ly_do, code):
    ly_do = (ly_do or "").strip()
    if not ly_do:
        raise SigningError(code=code, detail="Phải nhập lý do.", fields={"ly_do": ["Bắt buộc."]})
    return ly_do


def khoa_dang_hieu_luc(nguoi, thoi_diem=None):
    """Dòng khóa đang hiệu lực của tài khoản hoặc None (chưa bật lại và chưa quá hạn)."""
    thoi_diem = thoi_diem or timezone.now()
    khoa = SigningRightLock.objects.filter(nguoi_bi_khoa_id=nguoi.pk, bat_lai_luc__isnull=True).first()
    if khoa is None or (khoa.khoa_den is not None and khoa.khoa_den <= thoi_diem):
        return None
    return khoa


def ids_dang_bi_khoa(thoi_diem=None):
    """Tập id tài khoản đang bị khóa quyền ký (chưa bật lại và chưa quá hạn)."""
    thoi_diem = thoi_diem or timezone.now()
    return set(
        SigningRightLock.objects.filter(bat_lai_luc__isnull=True)
        .filter(Q(khoa_den__isnull=True) | Q(khoa_den__gt=thoi_diem))
        .values_list("nguoi_bi_khoa_id", flat=True)
    )


def kiem_tra_duoc_ky(nguoi):
    khoa = khoa_dang_hieu_luc(nguoi)
    if khoa is not None:
        raise SigningError(
            code="quyen_ky_bi_khoa",
            detail="Quyền ký của tài khoản đang bị quản trị viên khóa. Liên hệ quản trị viên.",
            status_code=status.HTTP_403_FORBIDDEN,
            fields={"khoa_den": [khoa.khoa_den.isoformat() if khoa.khoa_den else None]},
        )


def _khoa_tai_khoan(nguoi_bi_khoa_id):
    """Khóa dòng tài khoản để hai thao tác khóa/bật lại cùng tài khoản chạy tuần tự."""
    tai_khoan = get_user_model().objects.select_for_update().filter(pk=nguoi_bi_khoa_id).first()
    if tai_khoan is None:
        raise SigningError(code="khong_tim_thay_tai_khoan", detail="Không tìm thấy tài khoản.",
                           status_code=status.HTTP_404_NOT_FOUND)
    return tai_khoan


@transaction.atomic
def khoa_quyen(nguoi_bi_khoa_id, nguoi_thuc_hien, *, ly_do, thoi_han, dia_chi_ip=None):
    _yeu_cau_quan_tri(nguoi_thuc_hien)
    if thoi_han not in THOI_HAN_KHOA:
        raise SigningError(code="thoi_han_khoa_khong_hop_le", detail="Thời hạn khóa không hợp lệ.",
                           fields={"thoi_han": [f"Chọn một trong: {', '.join(THOI_HAN_KHOA)}."]})
    ly_do = _yeu_cau_ly_do(ly_do, "thieu_ly_do_khoa_quyen_ky")
    if nguoi_bi_khoa_id == nguoi_thuc_hien.pk:
        raise SigningError(code="khong_the_khoa_chinh_minh", detail="Không thể khóa quyền ký của chính mình.")
    tai_khoan = _khoa_tai_khoan(nguoi_bi_khoa_id)
    thoi_diem = timezone.now()

    cu = SigningRightLock.objects.select_for_update().filter(nguoi_bi_khoa=tai_khoan, bat_lai_luc__isnull=True).first()
    if cu is not None:
        if cu.khoa_den is None or cu.khoa_den > thoi_diem:
            raise ConflictError(code="quyen_ky_da_bi_khoa", detail="Quyền ký của tài khoản đang bị khóa.")
        cu.bat_lai_luc = cu.khoa_den  # hết hạn tự nhiên: không có người bật lại
        cu.save(update_fields=["bat_lai_luc", "updated_at"])

    han = THOI_HAN_KHOA[thoi_han]
    khoa = SigningRightLock.objects.create(
        nguoi_bi_khoa=tai_khoan, nguoi_khoa=nguoi_thuc_hien, ly_do_khoa=ly_do, khoa_tu=thoi_diem,
        khoa_den=thoi_diem + han if han else None,
    )
    ghi_nhat_ky(
        nguoi_thuc_hien, LOAI, khoa.pk, "KHOA_QUYEN_KY",
        trang_thai_truoc=TRANG_THAI_DA_BAT_LAI, trang_thai_sau=TRANG_THAI_DANG_KHOA, chi_tiet=ly_do,
        du_lieu_kem_theo={"nguoi_bi_khoa_id": tai_khoan.pk, "thoi_han": thoi_han,
                          "khoa_den": khoa.khoa_den.isoformat() if khoa.khoa_den else None},
        dia_chi_ip=dia_chi_ip,
    )
    return khoa


@transaction.atomic
def bat_lai_quyen(nguoi_bi_khoa_id, nguoi_thuc_hien, *, ly_do, dia_chi_ip=None):
    _yeu_cau_quan_tri(nguoi_thuc_hien)
    ly_do = _yeu_cau_ly_do(ly_do, "thieu_ly_do_bat_lai_quyen_ky")
    tai_khoan = _khoa_tai_khoan(nguoi_bi_khoa_id)
    thoi_diem = timezone.now()
    khoa = SigningRightLock.objects.select_for_update().filter(
        nguoi_bi_khoa=tai_khoan, bat_lai_luc__isnull=True,
    ).first()
    if khoa is None or (khoa.khoa_den is not None and khoa.khoa_den <= thoi_diem):
        raise ConflictError(code="quyen_ky_khong_bi_khoa", detail="Quyền ký của tài khoản hiện không bị khóa.")
    khoa.bat_lai_luc = thoi_diem
    khoa.nguoi_bat_lai = nguoi_thuc_hien
    khoa.ly_do_bat_lai = ly_do
    khoa.save(update_fields=["bat_lai_luc", "nguoi_bat_lai", "ly_do_bat_lai", "updated_at"])
    ghi_nhat_ky(
        nguoi_thuc_hien, LOAI, khoa.pk, "BAT_LAI_QUYEN_KY",
        trang_thai_truoc=TRANG_THAI_DANG_KHOA, trang_thai_sau=TRANG_THAI_DA_BAT_LAI, chi_tiet=ly_do,
        du_lieu_kem_theo={"nguoi_bi_khoa_id": tai_khoan.pk}, dia_chi_ip=dia_chi_ip,
    )
    return khoa
