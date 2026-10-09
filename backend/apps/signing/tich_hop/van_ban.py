"""
Tích hợp văn bản đi (Nhóm 2).

Hợp đồng: `kiem_tra_van_ban_trinh_ky(nguoi_dung, document_type, van_ban_id)` trả `VanBanDi` nếu văn bản
được phép trình ký, ngược lại ném `SigningError`. Quy tắc (#80, #82/#83):
- chỉ văn bản đi (`vanbandi`);
- văn bản phải tồn tại;
- văn bản `pham_vi = 'HAN_CHE'` không đi qua trình ký;
- người trình phải xem được văn bản.

Dùng model `documents.VanBanDi` và hàm dùng chung của Nhóm 2 (`documents.selectors`, #68 mục C5):
`la_nguoi_xem_duoc` cho quyền xem một văn bản, `van_ban_xem_duoc` cho danh sách văn bản xem được.

`mo_ta_van_ban(document_type, van_ban_id)`: số hiệu, trích yếu để ghi vào bằng chứng và trang phê duyệt
của tệp hoàn tất (Phase 10); không kiểm quyền, đọc lỗi thì trả rỗng để không chặn việc hoàn tất duyệt.
"""

import logging

from django.db import DatabaseError, transaction
from django.db.models import Q
from documents.models import PhamVi, VanBanDi
from documents.selectors import la_nguoi_xem_duoc, van_ban_xem_duoc
from rest_framework import status

from .. import enums
from ..errors import SigningError

logger = logging.getLogger(__name__)


def _doc_van_ban_di(van_ban_id):
    return VanBanDi.objects.filter(pk=van_ban_id).first()


def _xem_duoc(nguoi_dung, van_ban):
    return la_nguoi_xem_duoc(nguoi_dung, van_ban)


def kiem_tra_van_ban_trinh_ky(nguoi_dung, document_type, van_ban_id):
    if document_type != enums.LoaiVanBan.VAN_BAN_DI:
        raise SigningError(code="chi_trinh_ky_van_ban_di", detail="Trình ký chỉ nhận văn bản đi.",
                           fields={"document_type": ["Chỉ nhận 'vanbandi'."]})
    van_ban = _doc_van_ban_di(van_ban_id)
    if van_ban is None or not _xem_duoc(nguoi_dung, van_ban):
        # Kiểm quyền trước phạm vi để không tiết lộ văn bản người dùng không được xem.
        raise SigningError(code="khong_tim_thay_van_ban", detail="Không tìm thấy văn bản đi.",
                           status_code=status.HTTP_404_NOT_FOUND, fields={"van_ban_id": ["Không tồn tại."]})
    if van_ban.pham_vi == PhamVi.HAN_CHE:
        raise SigningError(code="van_ban_han_che_khong_trinh_ky",
                           detail="Văn bản hạn chế không đi qua trình ký.",
                           fields={"van_ban_id": ["Văn bản có phạm vi HAN_CHE."]})
    return van_ban


def mo_ta_van_ban(document_type, van_ban_id):
    """{"so_hieu", "trich_yeu"} của văn bản; rỗng khi không đọc được (văn bản đã xóa, lỗi CSDL)."""
    if document_type != enums.LoaiVanBan.VAN_BAN_DI:
        return {}
    try:
        with transaction.atomic():  # savepoint: lỗi đọc không làm hỏng transaction hoàn tất duyệt
            van_ban = _doc_van_ban_di(van_ban_id)
    except DatabaseError:
        logger.warning("Không đọc được mô tả văn bản %s #%s", document_type, van_ban_id)
        return {}
    if van_ban is None:
        return {}
    return {"so_hieu": van_ban.so_hieu or "", "trich_yeu": van_ban.trich_yeu or ""}


TOI_DA_TIM = 20


def tim_van_ban_di(nguoi_dung, tu_khoa=""):
    """
    Văn bản đi người dùng được chọn khi tạo hồ sơ (#80 mục E): văn bản xem được theo quy tắc của Nhóm 2, trừ
    văn bản HAN_CHE; tìm theo số hiệu hoặc trích yếu.
    """
    queryset = van_ban_xem_duoc(nguoi_dung, "DI").exclude(pham_vi=PhamVi.HAN_CHE)
    if tu_khoa:
        queryset = queryset.filter(Q(so_hieu__icontains=tu_khoa) | Q(trich_yeu__icontains=tu_khoa))
    return [{"id": v["id"], "so_hieu": v["so_hieu"] or "", "trich_yeu": v["trich_yeu"] or ""}
            for v in queryset.order_by("-id").values("id", "so_hieu", "trich_yeu")[:TOI_DA_TIM]]
