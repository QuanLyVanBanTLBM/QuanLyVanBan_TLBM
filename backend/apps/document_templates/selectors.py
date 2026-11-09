from django.db.models import Prefetch, Q

from authorization.permissions import is_system_admin

from .models import ChiTietTaiLieuAttachment, TaiLieuChiTiet


def visible_resources(qs, user):
    """Áp dụng cùng phạm vi xem cho danh sách tài liệu và dashboard."""
    # Người dùng chưa đăng nhập: chỉ thấy tài liệu công khai (TAT_CA)
    if not user or not user.is_authenticated:
        return qs.filter(hien_thi='TAT_CA')

    # Quản trị hệ thống (superuser, nhóm ADMIN) và Staff: thấy toàn bộ
    if user.is_staff or is_system_admin(user):
        return qs

    # Người dùng đăng nhập: thấy tài liệu TAT_CA, hoặc do chính mình tạo, hoặc cùng đơn vị/phòng ban
    user_don_vi_ids = set()
    user_don_vi_id = getattr(user, "don_vi_id", None)
    if user_don_vi_id:
        user_don_vi_ids.add(user_don_vi_id)

    if hasattr(user, "assignments"):
        try:
            user_don_vi_ids.update(user.assignments.values_list("don_vi_id", flat=True))
        except Exception:
            pass

    q_filter = Q(hien_thi='TAT_CA') | Q(nguoi_tao=user)
    if user_don_vi_ids:
        q_filter |= Q(hien_thi='NOI_BO_PHONG_BAN', don_vi_id__in=user_don_vi_ids)

    return qs.filter(q_filter).distinct()


def tai_lieu_hieu_luc_xem_duoc(user):
    """Tài liệu còn hiệu lực mà user được xem (cùng phạm vi `visible_resources`).

    Mỗi bản ghi có `active_attachments`: tệp đính kèm chưa xoá mềm, theo thứ tự id.
    """
    return visible_resources(TaiLieuChiTiet.objects.all(), user).filter(
        hieu_luc="CON_HIEU_LUC"
    ).prefetch_related(Prefetch(
        "attachments",
        queryset=ChiTietTaiLieuAttachment.objects.filter(is_deleted=False).order_by("pk"),
        to_attr="active_attachments",
    ))
