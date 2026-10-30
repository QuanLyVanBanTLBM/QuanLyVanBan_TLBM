"""
Kiểm tra thẩm quyền ký của dòng người ký đã được ủy quyền trước đây.

Chức năng tạo ủy quyền ký và cấu hình người được ký thay đã bỏ khỏi module Trình ký. Hồ sơ đang `CHO_KY` có dòng
người ký được ủy quyền từ trước vẫn ký được, nên giữ lại bước kiểm tra này: người nhận phải còn giữ chức danh được
cấu hình ký thay chức danh gốc (bảng `signing_delegation_role`, giữ nguyên dữ liệu, không còn giao diện chỉnh sửa).
"""

from rest_framework import status

from ..errors import SigningError
from ..models import SigningDelegationRole


def chuc_vu_goc(dong):
    """Giữ thẩm quyền của vị trí ban đầu khi chuyển người ký nhiều lần."""
    if dong.chuc_vu_goc_uy_quyen_id:
        return dong.chuc_vu_goc_uy_quyen_id
    if dong.uy_quyen_tu_id:
        return None  # lịch sử cũ không lưu chức danh gốc; không suy đoán từ chức danh hiện tại
    return dong.chuc_vu_id


def kiem_tra_tham_quyen_ky(dong, nguoi_nhan):
    """Kiểm lại chức danh được phép ký thay từ dữ liệu hiện tại ngay trước khi ký."""
    chuc_vu_giao = chuc_vu_goc(dong)
    duoc_phep = chuc_vu_giao and nguoi_nhan.chuc_vu_id and SigningDelegationRole.objects.select_for_update().filter(
        chuc_vu_giao_id=chuc_vu_giao, chuc_vu_nhan_id=nguoi_nhan.chuc_vu_id,
    ).first()
    if dong.uy_quyen_tu_id and not duoc_phep:
        raise SigningError(
            code="uy_quyen_khong_con_hop_le",
            detail="Người nhận không còn chức danh được phép ký thay; cần kiểm tra và ủy quyền lại.",
            status_code=status.HTTP_403_FORBIDDEN,
        )
