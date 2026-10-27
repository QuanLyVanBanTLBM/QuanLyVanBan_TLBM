"""
Tích hợp tổ chức, nhân sự (Nhóm 7).

Hợp đồng:
- `ten_hien_thi(nguoi_dung)`, `ten_chuc_vu(nguoi_dung)`: dữ liệu chụp vào snapshot người ký.
- `tim_ung_vien_theo_chuc_vu(chuc_vu_id, pham_vi_chuc_vu, nguoi_tao, don_vi_co_dinh_id)`: danh sách tài khoản
  đang hoạt động giữ chức vụ trong phạm vi (plan mục 3.2). Một ứng viên thì tự gán; nhiều ứng viên thì người tạo
  chọn; không có ai thì chặn gửi.

Dữ liệu thật của Nhóm 7 trên staging: Employee (`ho_ten`, `chuc_vu`, `don_vi`), `accounts.Position`,
`organizations.DonVi`. Các cột `chuc_vu_id`, `don_vi_id`, `don_vi_ap_dung_id` của Trình ký là FK theo DDL
(migration 0010). Model người dùng thiếu `chuc_vu`/`don_vi` thì người ký theo chức vụ không có ứng viên.
"""

import logging

from django.apps import apps
from django.contrib.auth import get_user_model
from organizations.models import DonVi

from .. import enums
from ..permissions import QUAN_LY_QUY_TRINH, co_quyen

logger = logging.getLogger(__name__)


def ten_hien_thi(nguoi_dung):
    return (getattr(nguoi_dung, "ho_ten", "") or nguoi_dung.get_full_name() or nguoi_dung.get_username()).strip()


def ten_chuc_vu(nguoi_dung):
    chuc_vu = getattr(nguoi_dung, "chuc_vu", None)
    return (getattr(chuc_vu, "name", "") or getattr(chuc_vu, "ten", "") or "") if chuc_vu else ""


def ten_don_vi(nguoi_dung):
    don_vi = getattr(nguoi_dung, "don_vi", None)
    return getattr(don_vi, "ten", "") or "" if don_vi else ""


def _co_du_lieu_to_chuc():
    fields = {f.name for f in get_user_model()._meta.get_fields()}
    return {"chuc_vu", "don_vi"} <= fields


def can_bo_giu_chuc_vu(chuc_vu_id, don_vi_id=None):
    """Cán bộ đang làm việc (is_active, trang_thai LAM_VIEC) giữ chức vụ; `don_vi_id` thì chỉ trong đơn vị đó."""
    if not _co_du_lieu_to_chuc():
        return get_user_model().objects.none()
    queryset = get_user_model().objects.filter(is_active=True, chuc_vu_id=chuc_vu_id)
    if don_vi_id is not None:
        queryset = queryset.filter(don_vi_id=don_vi_id)
    if hasattr(get_user_model(), "trang_thai"):
        queryset = queryset.filter(trang_thai="LAM_VIEC")
    return queryset


def tim_ung_vien_theo_chuc_vu(chuc_vu_id, pham_vi_chuc_vu, nguoi_tao, don_vi_co_dinh_id=None):
    don_vi_id = None
    if pham_vi_chuc_vu == enums.PhamViChucVu.DON_VI_NGUOI_TAO:
        don_vi_id = getattr(nguoi_tao, "don_vi_id", None)
        if don_vi_id is None:
            return []
    elif pham_vi_chuc_vu == enums.PhamViChucVu.DON_VI_CO_DINH:
        don_vi_id = don_vi_co_dinh_id
        if don_vi_id is None:
            return []
    return list(can_bo_giu_chuc_vu(chuc_vu_id, don_vi_id).order_by("pk"))


# ── Đơn vị và vai trò quản lý quy trình (#80 mục A, plan mục 3.1, 8) ────────
# Quy trình CONG_TY do quản trị quản lý; quy trình PHONG_BAN do lãnh đạo đơn vị áp dụng (có
# manage_signing_process) hoặc quản trị quản lý. Mã nhóm quyền (`auth_group.ma_nhom_quyen`, DDL) đọc qua
# `authorization.GroupInfo` của Nhóm 7. Chưa có model đó thì không phân biệt được quản trị với lãnh đạo:
# người có manage_signing_process được coi là quản trị (giữ hành vi Phase 6b) và chưa có lãnh đạo đơn vị.
# Khi Nhóm 7 có khái niệm lãnh đạo đơn vị riêng, thay thân `la_lanh_dao_don_vi`.

MA_NHOM_QUAN_TRI = "ADMIN"
MA_NHOM_LANH_DAO_DON_VI = "TP"


def don_vi_cua(nguoi_dung):
    return getattr(nguoi_dung, "don_vi_id", None)


# ── Ảnh chữ ký cá nhân (plan mục 3.4; #80 mục D) ────────────────────────────
# Hồ sơ cá nhân thuộc Nhóm 7 (field `anh_chu_ky`, PNG nền trong suốt, tối đa 2 MB). Trình ký chỉ đọc ảnh lúc
# ký để chụp snapshot. Cài đặt tạm: đọc field `anh_chu_ky` (ImageField/FileField) của model người dùng nếu có;
# chưa có field hoặc chưa tải ảnh thì trả None (tệp hoàn tất in khối chữ thay ảnh).

ANH_CHU_KY_TOI_DA = 2 * 1024 * 1024
CHU_KY_PNG = b"\x89PNG\r\n\x1a\n"


def anh_chu_ky(nguoi_dung):
    tep = getattr(nguoi_dung, "anh_chu_ky", None)
    if not tep:
        return None
    try:
        with tep.open("rb") as f:
            du_lieu = f.read(ANH_CHU_KY_TOI_DA + 1)
    except (OSError, ValueError):
        logger.warning("Không đọc được ảnh chữ ký của người dùng %s", nguoi_dung.pk)
        return None
    if len(du_lieu) > ANH_CHU_KY_TOI_DA or not du_lieu.startswith(CHU_KY_PNG):
        logger.warning("Ảnh chữ ký của người dùng %s không phải PNG hoặc quá 2 MB", nguoi_dung.pk)
        return None
    return du_lieu


def ma_nhom_cua(nguoi_dung):
    """Tập mã nhóm quyền của người dùng; None khi hệ thống chưa có mã nhóm (chưa có Nhóm 7)."""
    if not apps.is_installed("authorization"):
        return None
    try:
        group_info = apps.get_model("authorization", "GroupInfo")
    except LookupError:
        return None
    nhom = list(nguoi_dung.groups.values_list("pk", flat=True))
    if not nhom:
        return None
    ma = set(group_info.objects.filter(pk__in=nhom).exclude(ma_nhom_quyen=None)
             .values_list("ma_nhom_quyen", flat=True))
    return ma if ma else None


def la_quan_tri(nguoi_dung):
    if nguoi_dung.is_superuser:
        return True
    if not co_quyen(nguoi_dung, QUAN_LY_QUY_TRINH):
        return False
    ma_nhom = ma_nhom_cua(nguoi_dung)
    return ma_nhom is None or MA_NHOM_QUAN_TRI in ma_nhom


def don_vi_quan_ly_duoc(nguoi_dung):
    """Đơn vị người dùng được chọn làm đơn vị áp dụng quy trình PHONG_BAN: quản trị mọi đơn vị, lãnh đạo đơn vị
    chỉ đơn vị mình."""
    if la_quan_tri(nguoi_dung):
        return DonVi.objects.order_by("stt_uu_tien", "pk")
    don_vi_id = don_vi_cua(nguoi_dung)
    if la_lanh_dao_don_vi(nguoi_dung, don_vi_id):
        return DonVi.objects.filter(pk=don_vi_id)
    return DonVi.objects.none()


def la_lanh_dao_don_vi(nguoi_dung, don_vi_id):
    if don_vi_id is None or don_vi_cua(nguoi_dung) != don_vi_id or not co_quyen(nguoi_dung, QUAN_LY_QUY_TRINH):
        return False
    ma_nhom = ma_nhom_cua(nguoi_dung)
    return ma_nhom is not None and MA_NHOM_LANH_DAO_DON_VI in ma_nhom
