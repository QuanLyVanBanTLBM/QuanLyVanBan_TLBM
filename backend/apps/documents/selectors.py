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
- tep_dinh_kem_hien_hanh(loai, document_ids): Tệp đính kèm chưa xoá mềm của các văn bản, theo thứ tự tải lên.
"""

from django.db.models import Q
from .models import (
    LoaiVanBan,
    PhamVi,
    HieuLuc,
    VanBanDen,
    VanBanDi,
    VanBanMat,
    get_document_model,
    get_attachment_model,
    DocumentAccessLog,
    canonical_document_kind,
)


def is_admin_user(user):
    """Kiểm tra người dùng có quyền Quản trị viên (Admin) hay không."""
    if not user or not user.is_authenticated:
        return False
    if getattr(user, "is_staff", False) or getattr(user, "is_superuser", False):
        return True
    profile = getattr(user, "profile", None)
    if profile and getattr(profile, "role", None) == "admin":
        return True
    if getattr(user, "username", "") in ("admin", "quantri"):
        return True
    return False


def van_ban_xem_duoc(user, loai="DEN"):
    """
    Quy tắc xem văn bản chuẩn:
    - user không tồn tại hoặc is_active = False: trả về none()
    - Quản trị viên (Admin): Có quyền xem toàn bộ văn bản để quản lý, thanh tra chống gian dối.
    - Cán bộ thường đối với NOI_BO: xem được nếu có quyền view_* hoặc hien_thi = True.
    - Đối với HAN_CHE: CHỈ cán bộ được chỉ định (nguoi_nhan) hoặc người tạo (nguoi_tao) mới được quyền xem (và chỉ được quyền xem).
    """
    model = get_document_model(loai)

    if not user or not user.is_authenticated or not getattr(user, "is_active", True):
        return model.objects.none()

    model_name = getattr(model, "document_kind", "vanbanden")

    # Điều kiện xem HAN_CHE (Issue #82 & #83):
    # - Nếu văn bản có chỉ định đích danh người nhận (nguoi_nhan): CHỈ đích danh người nhận hoặc người tạo xem được.
    # - Nếu văn bản KHÔNG chỉ định đích danh người nhận: cán bộ thuộc đơn vị nhận (donvinhan) mới xem được.
    # Tuyệt đối KHÔNG có ngoại lệ cho superuser hay quyền view_*.
    q_han_che_user = Q(nguoi_tao=user) | Q(nguoi_nhan=user)
    user_don_vi_id = getattr(user, "don_vi_id", None)
    if user_don_vi_id is None and hasattr(user, "don_vi"):
        user_don_vi_id = getattr(user.don_vi, "id", None)

    if user_don_vi_id is not None:
        q_han_che_dept = Q(donvinhan__donvi_id=user_don_vi_id, nguoi_nhan__isnull=True)
        q_han_che = q_han_che_user | q_han_che_dept
    else:
        q_han_che = q_han_che_user
    cond_han_che = Q(pham_vi=PhamVi.HAN_CHE) & q_han_che

    # Với Văn bản Mật (loai=MAT): CHỈ áp dụng điều kiện bảo mật nghiêm ngặt (q_han_che)
    if getattr(model, "loai", None) == "MAT" or str(loai).strip().upper() in ("MAT", "VANBANMAT"):
        return model.objects.filter(q_han_che).distinct()

    # Điều kiện xem NOI_BO: Phân quyền theo mã chuẩn trong seed DDL (view_vanbanden, view_vanbandi)
    try:
        has_view_perm = (
            user.is_staff
            or user.is_superuser
            or user.has_perm(f"documents.view_{model_name}")
            or user.has_perm(f"view_{model_name}")
        )
    except Exception:
        has_view_perm = bool(user.is_staff or user.is_superuser)
    if has_view_perm:
        cond_noi_bo = Q(pham_vi=PhamVi.NOI_BO)
    else:
        # Cán bộ thường không có quyền view_*:
        # - Chỉ tài khoản chỉ định (người tạo, người nhận) mới được xem văn bản hết hiệu lực
        # - Tài khoản không chỉ định thì chỉ xem được văn bản còn hiệu lực (CON_HIEU_LUC, CON_HIEU_LUC_1_PHAN)
        cond_active = Q(hieu_luc__in=[HieuLuc.CON_HIEU_LUC, HieuLuc.CON_HIEU_LUC_1_PHAN])
        cond_noi_bo = Q(pham_vi=PhamVi.NOI_BO, hien_thi=True) & (q_han_che_user | cond_active)

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
    is_confidential = (getattr(van_ban, "loai", None) == "MAT") or (pham_vi == PhamVi.HAN_CHE)
    if is_confidential:
        if van_ban.nguoi_tao_id == user.pk:
            return True
        has_recipients = hasattr(van_ban, "nguoi_nhan") and van_ban.nguoi_nhan.exists()
        if has_recipients:
            return van_ban.nguoi_nhan.filter(pk=user.pk).exists()
        user_don_vi_id = getattr(user, "don_vi_id", None)
        if user_don_vi_id is None and hasattr(user, "don_vi"):
            user_don_vi_id = getattr(user.don_vi, "id", None)
        if user_don_vi_id is not None and hasattr(van_ban, "donvinhan"):
            return van_ban.donvinhan.filter(donvi_id=user_don_vi_id).exists()
        return False

    # NOI_BO: Văn bản nội bộ hiển thị cho mọi cán bộ nhân viên đang hoạt động
    if getattr(van_ban, "hien_thi", True):
        # Nếu văn bản đã hết hiệu lực: chỉ tài khoản chỉ định (Admin, Người tạo, Người nhận) hoặc quyền view_* mới xem được
        is_expired = getattr(van_ban, "hieu_luc", None) in (HieuLuc.HET_HIEU_LUC, HieuLuc.HET_VA_THAY_THE)
        if is_expired:
            if user.is_staff or user.is_superuser or van_ban.nguoi_tao_id == user.pk:
                return True
            if hasattr(van_ban, "nguoi_nhan") and van_ban.nguoi_nhan.filter(pk=user.pk).exists():
                return True
            model_name = getattr(van_ban, "document_kind", "vanbanden")
            try:
                if user.has_perm(f"documents.view_{model_name}") or user.has_perm(f"view_{model_name}"):
                    return True
            except Exception:
                pass
            return False
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
        document_type=canonical_document_kind(document_type),
        document_id=document_id,
        user=user,
        hanh_dong=hanh_dong,
        doi_tuong_user=doi_tuong_user,
        tep_id=tep_id,
        dia_chi_ip=dia_chi_ip,
    )


def tep_dinh_kem_hien_hanh(loai, document_ids):
    """Tệp đính kèm chưa xoá mềm của các văn bản `document_ids` thuộc loại `loai` (DEN/DI), theo thứ tự tải lên.

    Không tự kiểm quyền xem: `document_ids` phải lấy từ `van_ban_xem_duoc`.
    """
    return get_attachment_model(loai).objects.filter(
        document_id__in=document_ids, is_deleted=False
    ).order_by("created_at", "pk")
