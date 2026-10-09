"""
Selectors cho Module Văn Bản — Hỗ trợ quy tắc xem văn bản chuẩn theo Issue #82 & Issue #83 & DDL.

Cung cấp cho các phân hệ khác (Dashboard Nhóm 1, Hồ sơ Nhóm 3, Công việc Nhóm 6):
- van_ban_xem_duoc(user, loai): Trả về QuerySet văn bản mà user được phép xem.
  + NOI_BO: Người có quyền view_* hoặc admin/staff xem được.
  + HAN_CHE: CHỈ người tạo (nguoi_tao), người nhận (nguoi_nhan), hoặc đơn vị nhận (donvinhan) xem được.
    Tuyệt đối không ngoại lệ cho superuser hay quyền view_*.
    Tài khoản bị khóa (is_active = FALSE) mất quyền xem.
- la_nguoi_xem_duoc(user, van_ban): Kiểm tra boolean quyền xem trên một đối tượng văn bản cụ thể.
- log_access(document_type, document_id, user, hanh_dong, ...): Ghi nhật ký vào documents_access_log.
"""

from django.db.models import Q
from .models import LoaiVanBan, PhamVi, VanBanDen, VanBanDi, get_document_model, DocumentAccessLog


def van_ban_xem_duoc(user, loai="DEN"):
    """
    Quy tắc xem văn bản chuẩn theo Issue #82 & Issue #83 & DDL:
    - user không tồn tại hoặc is_active = False: trả về none()
    - NOI_BO: xem được nếu có quyền view_vanbanden/view_vanbandi hoặc là staff/admin, hoặc hien_thi = True
    - HAN_CHE: chỉ người tạo (nguoi_tao = user), người nhận (nguoi_nhan = user), hoặc đơn vị nhận (donvinhan__donvi_id = user_don_vi_id).
      Tuyệt đối KHÔNG có ngoại lệ cho superuser hay quyền view_*.
    """
    model = get_document_model(loai)

    if not user or not user.is_authenticated or not getattr(user, "is_active", True):
        return model.objects.none()

    model_name = getattr(model, "document_kind", "vanbanden")

    # Điều kiện xem HAN_CHE (Issue #82 & #83 & N2-4): người tạo, người nhận, hoặc đơn vị nhận
    # Tuyệt đối KHÔNG có ngoại lệ cho superuser hay quyền view_*
    q_han_che_user = Q(nguoi_tao=user) | Q(nguoi_nhan=user)
    user_don_vi_id = getattr(user, "don_vi_id", None)
    if user_don_vi_id is None and hasattr(user, "don_vi"):
        user_don_vi_id = getattr(user.don_vi, "id", None)

    if user_don_vi_id is not None:
        q_han_che = q_han_che_user | Q(donvinhan__donvi_id=user_don_vi_id)
    else:
        q_han_che = q_han_che_user

    cond_han_che = Q(pham_vi=PhamVi.HAN_CHE) & q_han_che

    # Điều kiện xem NOI_BO: Phân quyền theo mã chuẩn trong seed DDL (view_vanbanden, view_vanbandi)
    has_view_perm = (
        user.is_staff
        or user.is_superuser
        or user.has_perm(f"documents.view_{model_name}")
        or user.has_perm(f"view_{model_name}")
    )
    if has_view_perm:
        cond_noi_bo = Q(pham_vi=PhamVi.NOI_BO)
    else:
        # Cán bộ thường không có quyền view_* thì xem các văn bản nội bộ công khai (hien_thi = True)
        cond_noi_bo = Q(pham_vi=PhamVi.NOI_BO, hien_thi=True)

    return model.objects.filter(cond_noi_bo | cond_han_che).distinct()


def la_nguoi_xem_duoc(user, van_ban):
    """
    Kiểm tra người dùng có quyền xem văn bản này hay không.
    Nhóm 6 (Công việc) và các phân hệ khác gọi hàm này trước khi giao việc từ văn bản hạn chế.
    Trả về True nếu được phép xem, False nếu không được phép hoặc chưa đăng nhập.
    """
    if not user or not user.is_authenticated or not getattr(user, "is_active", True):
        return False

    pham_vi = getattr(van_ban, "pham_vi", PhamVi.NOI_BO)
    if pham_vi == PhamVi.HAN_CHE:
        if van_ban.nguoi_tao_id == user.pk:
            return True
        if hasattr(van_ban, "nguoi_nhan") and van_ban.nguoi_nhan.filter(pk=user.pk).exists():
            return True
        user_don_vi_id = getattr(user, "don_vi_id", None)
        if user_don_vi_id is None and hasattr(user, "don_vi"):
            user_don_vi_id = getattr(user.don_vi, "id", None)
        if user_don_vi_id is not None and hasattr(van_ban, "donvinhan"):
            if van_ban.donvinhan.filter(donvi_id=user_don_vi_id).exists():
                return True
        return False

    # NOI_BO: Văn bản nội bộ hiển thị cho mọi cán bộ nhân viên đang hoạt động
    if getattr(van_ban, "hien_thi", True):
        return True

    if user.is_staff or user.is_superuser:
        return True

    model_name = getattr(van_ban, "document_kind", "vanbanden")
    try:
        return (
            user.has_perm(f"documents.view_{model_name}")
            or user.has_perm(f"view_{model_name}")
        )
    except Exception:
        return False


def log_access(document_type, document_id, user, hanh_dong, doi_tuong_user=None, tep_id=None, dia_chi_ip=None):
    """
    Ghi nhật ký vào documents_access_log cho văn bản HAN_CHE.
    """
    if not user or not user.is_authenticated:
        return None
    return DocumentAccessLog.objects.create(
        document_type=str(document_type).lower(),
        document_id=document_id,
        user=user,
        hanh_dong=hanh_dong,
        doi_tuong_user=doi_tuong_user,
        tep_id=tep_id,
        dia_chi_ip=dia_chi_ip,
    )
