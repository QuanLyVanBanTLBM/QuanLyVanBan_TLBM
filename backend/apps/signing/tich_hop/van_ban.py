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

Văn bản trình ký của hồ sơ (#275 mục 3): bản ghi văn bản đi đã gắn hoặc PDF dự thảo chưa vào sổ (mã hồ sơ tự cấp,
số hiệu tham chiếu tùy chọn, trích yếu lưu trên hồ sơ cho đến khi liên kết). `mo_ta_ho_so`, `mo_ta_nhieu_ho_so` trả mô tả theo đúng nguồn.
"""

import logging

from django.db import DatabaseError, transaction
from documents.models import PhamVi, VanBanDi
from documents.selectors import la_nguoi_xem_duoc, van_ban_xem_duoc
from rest_framework import status

from .. import enums
from ..errors import SigningError
from ..tim_kiem import loc_khong_dau

logger = logging.getLogger(__name__)


def _doc_van_ban_di(van_ban_id):
    return VanBanDi.objects.filter(pk=van_ban_id).first()


def _xem_duoc(nguoi_dung, van_ban):
    return la_nguoi_xem_duoc(nguoi_dung, van_ban)


def kiem_tra_van_ban_trinh_ky(nguoi_dung, document_type, van_ban_id):
    if document_type != enums.LoaiVanBan.VAN_BAN_DI:
        raise SigningError(code="chi_trinh_ky_van_ban_di", detail="Trình ký chỉ nhận văn bản.",
                           fields={"document_type": ["Chỉ nhận 'vanbandi'."]})
    van_ban = _doc_van_ban_di(van_ban_id)
    if van_ban is None:
        raise SigningError(code="khong_tim_thay_van_ban", detail="Không tìm thấy văn bản.",
                           status_code=status.HTTP_404_NOT_FOUND, fields={"van_ban_id": ["Không tồn tại."]})
    if van_ban.pham_vi == PhamVi.HAN_CHE:
        raise SigningError(code="van_ban_han_che_khong_trinh_ky",
                           detail="Văn bản hạn chế không đi qua trình ký.",
                           fields={"van_ban_id": ["Văn bản có phạm vi HAN_CHE."]})
    if van_ban.nguoi_tao_id != nguoi_dung.pk and not _xem_duoc(nguoi_dung, van_ban):
        # Không tiết lộ sự tồn tại của văn bản người dùng không được xem
        raise SigningError(code="khong_tim_thay_van_ban", detail="Không tìm thấy văn bản.",
                           status_code=status.HTTP_404_NOT_FOUND, fields={"van_ban_id": ["Không tồn tại."]})
    return van_ban


def ma_van_ban_di_xem_duoc(nguoi_dung):
    """Truy vấn con các mã văn bản đi mà `nguoi_dung` xem được theo quy tắc của module Văn bản (`van_ban_xem_duoc`)."""
    return van_ban_xem_duoc(nguoi_dung, "DI").values("pk")


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


def mo_ta_ho_so(yeu_cau):
    """{"so_hieu", "trich_yeu"} của văn bản trình ký: văn bản đi đã gắn hoặc nội dung nhập tay trên hồ sơ."""
    if yeu_cau.van_ban_id is None:
        return {"so_hieu": yeu_cau.so_hieu_van_ban, "trich_yeu": yeu_cau.trich_yeu_van_ban}
    return mo_ta_van_ban(yeu_cau.document_type, yeu_cau.van_ban_id)


def mo_ta_nhieu_ho_so(ho_so):
    """{id hồ sơ: mô tả văn bản trình ký} của nhiều hồ sơ; văn bản đi đọc trong một truy vấn."""
    van_ban_di = mo_ta_nhieu(h.van_ban_id for h in ho_so if h.van_ban_id is not None)
    return {h.pk: van_ban_di.get(h.van_ban_id, {}) if h.van_ban_id is not None
            else {"so_hieu": h.so_hieu_van_ban, "trich_yeu": h.trich_yeu_van_ban} for h in ho_so}


def id_van_ban_khop(tu_khoa):
    """Id văn bản đi có số hiệu hoặc trích yếu chứa từ khóa, không phân biệt hoa thường và dấu (bộ lọc hồ sơ)."""
    return loc_khong_dau(VanBanDi.objects.all(), tu_khoa, "so_hieu", "trich_yeu").values("id")


def mo_ta_nhieu(van_ban_ids):
    """{id: {"so_hieu", "trich_yeu"}} của nhiều văn bản đi trong một truy vấn (trang tài liệu)."""
    return {v["id"]: {"so_hieu": v["so_hieu"] or "", "trich_yeu": v["trich_yeu"] or ""}
            for v in VanBanDi.objects.filter(pk__in=set(van_ban_ids)).values("id", "so_hieu", "trich_yeu")}


TOI_DA_TIM = 20


def tim_van_ban_di(nguoi_dung, tu_khoa=""):
    """
    Văn bản đi người dùng được chọn khi tạo hồ sơ (#80 mục E): văn bản xem được theo quy tắc của Nhóm 2, trừ
    văn bản HAN_CHE; tìm theo số hiệu hoặc trích yếu, không phân biệt hoa thường và dấu.
    """
    queryset = van_ban_xem_duoc(nguoi_dung, "DI").exclude(pham_vi=PhamVi.HAN_CHE)
    if tu_khoa:
        queryset = loc_khong_dau(queryset, tu_khoa, "so_hieu", "trich_yeu")
    return [{"id": v["id"], "so_hieu": v["so_hieu"] or "", "trich_yeu": v["trich_yeu"] or ""}
            for v in queryset.order_by("-id").values("id", "so_hieu", "trich_yeu")[:TOI_DA_TIM]]
