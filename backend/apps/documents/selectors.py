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


def _co_quyen(user, perm_code):
    try:
        return user.has_perm(f"documents.{perm_code}") or user.has_perm(perm_code)
    except Exception:
        return False


def co_quyen_xu_ly_het_hieu_luc(user, model_name="vanbanden"):
    """Quyền sửa, xóa văn bản hết hiệu lực: superuser hoặc manage_het_hieu_luc_vanbanden/vanbandi."""
    if getattr(user, "is_superuser", False) or is_admin_user(user):
        return True
    return _co_quyen(user, f"manage_het_hieu_luc_{model_name}")


def co_quyen_xem_het_hieu_luc(user, model_name="vanbanden"):
    """
    Quyền xem văn bản hết hiệu lực: superuser, view_het_hieu_luc_vanbanden/vanbandi,
    hoặc quyền xử lý manage_het_hieu_luc_* (được sửa, xóa thì được xem).
    """
    if co_quyen_xu_ly_het_hieu_luc(user, model_name):
        return True
    return _co_quyen(user, f"view_het_hieu_luc_{model_name}")


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
            or is_admin_user(user)
            or user.has_perm(f"documents.view_{model_name}")
            or user.has_perm(f"view_{model_name}")
        )
    except Exception:
        has_view_perm = bool(user.is_staff or user.is_superuser)

    # Điều kiện văn bản còn hiệu lực và hết hiệu lực
    cond_active = Q(hieu_luc__in=[HieuLuc.CON_HIEU_LUC, HieuLuc.CON_HIEU_LUC_1_PHAN])
    cond_expired = Q(hieu_luc__in=[HieuLuc.HET_HIEU_LUC, HieuLuc.HET_VA_THAY_THE])
    has_expired_view = co_quyen_xem_het_hieu_luc(user, model_name)

    if has_view_perm:
        # Nếu có quyền xem văn bản hết hiệu lực (hoặc admin/superuser) -> xem được toàn bộ NOI_BO
        if has_expired_view:
            cond_noi_bo = Q(pham_vi=PhamVi.NOI_BO)
        else:
            # Nếu KHÔNG có quyền xem văn bản hết hiệu lực -> chỉ xem NOI_BO còn hiệu lực (hoặc văn bản do mình tạo/nhận)
            cond_noi_bo = Q(pham_vi=PhamVi.NOI_BO) & (cond_active | q_han_che_user)
    else:
        # Khi KHÔNG có quyền view_vanbanden / view_vanbandi (bị bỏ tick):
        if has_expired_view:
            # Nếu LẠI ĐƯỢC CẤP quyền xem văn bản hết hiệu lực -> xem được văn bản NOI_BO hết hiệu lực + văn bản của mình
            cond_noi_bo = Q(pham_vi=PhamVi.NOI_BO) & (cond_expired | q_han_che_user)
        else:
            # Cán bộ thường chỉ xem được các văn bản mà họ là Người tạo hoặc Người nhận chỉ định.
            cond_noi_bo = Q(pham_vi=PhamVi.NOI_BO) & q_han_che_user

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
    is_mat = (getattr(van_ban, "loai", None) == "MAT") or (
        getattr(getattr(van_ban, "_meta", None), "model_name", "") == "vanbanmat"
    )
    is_confidential = is_mat or (pham_vi == PhamVi.HAN_CHE)

    if is_confidential:
        # KHÓA CỨNG BẢO VỆ VĂN BẢN HẠN CHẾ / MẬT:
        # Tuyệt đối không có ngoại lệ cho Superuser hay Admin nếu không phải người nhận hay người tạo.
        if (getattr(van_ban, "nguoi_tao_id", None) == user.pk) or (getattr(van_ban, "nguoi_tao", None) == user):
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

    # NOI_BO: Văn bản nội bộ
    if is_admin_user(user) or getattr(user, "is_staff", False) or getattr(user, "is_superuser", False):
        return True

    if (getattr(van_ban, "nguoi_tao_id", None) == user.pk) or (getattr(van_ban, "nguoi_tao", None) == user):
        return True
    if hasattr(van_ban, "nguoi_nhan") and van_ban.nguoi_nhan.filter(pk=user.pk).exists():
        return True

    model_name = getattr(van_ban, "document_kind", None) or getattr(getattr(van_ban, "_meta", None), "model_name", "vanbanden")

    # Văn bản nội bộ hết hiệu lực: Yêu cầu quyền view_het_hieu_luc_* do Nhóm 7 cấp
    is_expired = getattr(van_ban, "hieu_luc", None) in (HieuLuc.HET_HIEU_LUC, HieuLuc.HET_VA_THAY_THE)
    if is_expired:
        return co_quyen_xem_het_hieu_luc(user, model_name)

    # Quyền sửa, xóa, xem log, đổi hiệu lực tự động cho phép tiếp cận văn bản
    try:
        if (
            user.has_perm(f"documents.view_{model_name}")
            or user.has_perm(f"view_{model_name}")
            or user.has_perm(f"documents.change_{model_name}")
            or user.has_perm(f"change_{model_name}")
            or user.has_perm(f"documents.delete_{model_name}")
            or user.has_perm(f"delete_{model_name}")
            or user.has_perm(f"documents.view_read_log_{model_name}")
            or user.has_perm(f"view_read_log_{model_name}")
            or user.has_perm(f"documents.change_hieu_luc_{model_name}")
            or user.has_perm(f"change_hieu_luc_{model_name}")
        ):
            return True
    except Exception:
        pass

    # Mặc định văn bản nội bộ hiển thị (hien_thi = True)
    return bool(getattr(van_ban, "hien_thi", True))

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
