"""
Thay người ký của hồ sơ đang chờ người ký bị khóa quyền ký (issue #499, phân vùng 3 của #447).

- Người thực hiện: quản trị viên hoặc người tạo hồ sơ; bắt buộc nhập lý do.
- Đối tượng thay: người ký đang chờ (`CHO_KY`, đã được mở) ở cấp đang ký của lượt trình đang chờ ký, có quyền ký
  đang bị khóa. Người ký khác, cấp khác và chữ ký đã có giữ nguyên.
- Người thay: tài khoản hoạt động, có `sign_trinhky`, không bị khóa quyền ký, không trùng trong cấp, thỏa quy tắc
  thứ bậc chức vụ giữa các cấp (#351).
- Cập nhật tại chỗ dòng người ký (vị trí ký giữ nguyên), ghi `signing_audit_log` và báo người ký mới trong cùng
  transaction. Hủy hồ sơ vẫn là lối thoát riêng.
"""

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework import status

from .. import enums
from ..errors import ConflictError, SigningError
from ..models import SigningRequest, SigningRequestStepSigner
from ..permissions import KY_TRINH_KY, co_quyen
from ..tich_hop import to_chuc
from . import process as process_service
from . import quyen_ky, thong_bao
from .audit import ghi_nhat_ky

LOAI = "signing_request_step_signer"


def duoc_thay_nguoi_ky(yeu_cau, nguoi):
    """Người dùng được phép thay người ký của hồ sơ: người tạo hoặc quản trị viên."""
    return yeu_cau.create_by_id == nguoi.pk or to_chuc.la_quan_tri(nguoi)


def ids_thay_duoc(yeu_cau, nguoi):
    """Id dòng người ký `nguoi` được thay trên lượt hiện hành của hồ sơ (rỗng khi không đủ quyền hoặc không có)."""
    if yeu_cau.trang_thai != enums.TrangThaiYeuCau.CHO_KY or not duoc_thay_nguoi_ky(yeu_cau, nguoi):
        return set()
    luot = yeu_cau.luot_trinh_set.order_by("-so_luot").first()
    if luot is None or luot.trang_thai != enums.TrangThaiLuotTrinh.CHO_KY:
        return set()
    bi_khoa = quyen_ky.ids_dang_bi_khoa()
    if not bi_khoa:
        return set()
    return set(SigningRequestStepSigner.objects.filter(
        buoc_ky__luot_trinh=luot, buoc_ky__trang_thai=enums.TrangThaiCapKy.DANG_KY,
        trang_thai=enums.TrangThaiNguoiKy.CHO_KY, thoi_diem_mo__isnull=False, nguoi_ky_id__in=bi_khoa,
    ).values_list("pk", flat=True))


def _luot_dang_cho_ky(yeu_cau):
    if yeu_cau.trang_thai != enums.TrangThaiYeuCau.CHO_KY:
        raise ConflictError(code="ho_so_khong_cho_ky", detail="Chỉ thay người ký của hồ sơ đang chờ ký.")
    luot = yeu_cau.luot_trinh_set.order_by("-so_luot").first()
    if luot is None or luot.trang_thai != enums.TrangThaiLuotTrinh.CHO_KY:
        raise ConflictError(code="ho_so_khong_cho_ky", detail="Chỉ thay người ký của hồ sơ đang chờ ký.")
    return luot


def _kiem_tra_nguoi_thay(nguoi_ky, nguoi_moi):
    if not nguoi_moi.is_active:
        raise SigningError(code="nguoi_ky_moi_khong_hoat_dong", detail="Tài khoản người ký mới không còn hoạt động.",
                           fields={"nguoi_ky_moi_id": ["Tài khoản không hoạt động."]})
    if not co_quyen(nguoi_moi, KY_TRINH_KY):
        raise SigningError(code="nguoi_ky_thieu_quyen_ky", detail="Người ký mới không có quyền ký trình ký.",
                           fields={"nguoi_ky_moi_id": ["Thiếu quyền ký."]})
    if quyen_ky.khoa_dang_hieu_luc(nguoi_moi) is not None:
        raise SigningError(code="nguoi_ky_bi_khoa_quyen_ky",
                           detail="Người ký mới tạm thời không có quyền ký; chọn người khác.",
                           fields={"nguoi_ky_moi_id": ["Quyền ký đang bị khóa."]})
    if nguoi_moi.pk == nguoi_ky.nguoi_ky_id or nguoi_ky.buoc_ky.nguoi_ky_set.filter(nguoi_ky_id=nguoi_moi.pk).exists():
        raise SigningError(code="nguoi_ky_trung_trong_cap", detail="Người ký mới đã có trong cấp ký này.",
                           fields={"nguoi_ky_moi_id": ["Đã có trong cấp."]})


def _kiem_tra_thu_bac(luot, nguoi_ky, chuc_vu_moi_id):
    """Áp dụng quy tắc thứ bậc chức vụ giữa các cấp (#351) cho lượt trình sau khi thay."""
    cap_ky = []
    for cap in luot.cap_ky_set.order_by("thu_tu").prefetch_related("nguoi_ky_set"):
        nguoi_cap = [
            {"chuc_vu_id": chuc_vu_moi_id if n.pk == nguoi_ky.pk else n.chuc_vu_id} for n in cap.nguoi_ky_set.all()
        ]
        cap_ky.append({"thu_tu": cap.thu_tu, "nguoi_ky": nguoi_cap})
    process_service._kiem_tra_thu_bac_chuc_vu_cap_ky(cap_ky)


@transaction.atomic
def thay_nguoi_ky(yeu_cau, nguoi_thuc_hien, *, nguoi_ky_id, nguoi_ky_moi_id, ly_do, dia_chi_ip=None):
    """Thay `nguoi_ky_id` (id dòng người ký của lượt hiện hành) bằng tài khoản `nguoi_ky_moi_id`."""
    if not duoc_thay_nguoi_ky(yeu_cau, nguoi_thuc_hien):
        raise SigningError(code="khong_co_quyen", detail="Chỉ người tạo hoặc quản trị viên được thay người ký.",
                           status_code=status.HTTP_403_FORBIDDEN)
    ly_do = (ly_do or "").strip()
    if not ly_do:
        raise SigningError(code="thieu_ly_do", detail="Phải nhập lý do thay người ký.", fields={"ly_do": ["Bắt buộc."]})
    yeu_cau = SigningRequest.objects.select_for_update().get(pk=yeu_cau.pk)
    luot = _luot_dang_cho_ky(yeu_cau)

    nguoi_ky = (SigningRequestStepSigner.objects.select_for_update().select_related("buoc_ky")
                .filter(pk=nguoi_ky_id, buoc_ky__luot_trinh=luot).first())
    if nguoi_ky is None:
        raise SigningError(code="khong_tim_thay_nguoi_ky", detail="Không tìm thấy người ký trong lượt trình hiện hành.",
                           status_code=status.HTTP_404_NOT_FOUND)
    if (nguoi_ky.buoc_ky.trang_thai != enums.TrangThaiCapKy.DANG_KY
            or nguoi_ky.trang_thai != enums.TrangThaiNguoiKy.CHO_KY or nguoi_ky.thoi_diem_mo is None):
        raise ConflictError(code="nguoi_ky_khong_the_thay",
                            detail="Chỉ thay người ký đang chờ ở cấp đang ký.")
    if quyen_ky.khoa_dang_hieu_luc(nguoi_ky.nguoi_ky) is None:
        raise ConflictError(code="nguoi_ky_khong_bi_khoa_quyen_ky",
                            detail="Chỉ thay người ký có quyền ký đang bị khóa.")

    nguoi_moi = get_user_model().objects.select_for_update().filter(pk=nguoi_ky_moi_id).first()
    if nguoi_moi is None:
        raise SigningError(code="khong_tim_thay_tai_khoan", detail="Không tìm thấy tài khoản người ký mới.",
                           status_code=status.HTTP_404_NOT_FOUND, fields={"nguoi_ky_moi_id": ["Không tồn tại."]})
    _kiem_tra_nguoi_thay(nguoi_ky, nguoi_moi)
    chuc_vu_moi_id = getattr(nguoi_moi, "chuc_vu_id", None)
    _kiem_tra_thu_bac(luot, nguoi_ky, chuc_vu_moi_id)

    nguoi_ky_cu_id = nguoi_ky.nguoi_ky_id
    nguoi_ky.nguoi_ky = nguoi_moi
    nguoi_ky.chuc_vu_id = chuc_vu_moi_id
    nguoi_ky.ten_nguoi_ky = to_chuc.ten_hien_thi(nguoi_moi) or nguoi_moi.get_username()
    nguoi_ky.ten_chuc_vu = to_chuc.ten_chuc_vu(nguoi_moi) or None
    nguoi_ky.thoi_diem_mo = timezone.now()
    nguoi_ky.save(update_fields=["nguoi_ky", "chuc_vu", "ten_nguoi_ky", "ten_chuc_vu", "thoi_diem_mo"])
    ghi_nhat_ky(
        nguoi_thuc_hien, LOAI, nguoi_ky.pk, "THAY_NGUOI_KY", trinh_ky=yeu_cau, luot_trinh=luot, buoc_ky=nguoi_ky,
        trang_thai_truoc=enums.TrangThaiNguoiKy.CHO_KY, trang_thai_sau=enums.TrangThaiNguoiKy.CHO_KY, chi_tiet=ly_do,
        du_lieu_kem_theo={"cap_ky": nguoi_ky.buoc_ky_id, "nguoi_ky_cu_id": nguoi_ky_cu_id,
                          "nguoi_ky_moi_id": nguoi_moi.pk},
        dia_chi_ip=dia_chi_ip,
    )
    thong_bao.can_ky(nguoi_ky)
    return yeu_cau
