"""
Tích hợp văn bản đi (Nhóm 2).

Hợp đồng: `kiem_tra_van_ban_trinh_ky(nguoi_dung, document_type, van_ban_id)` trả `VanBanDi` nếu văn bản
được phép trình ký, ngược lại ném `SigningError`. Quy tắc (#80, #82/#83):
- chỉ văn bản đi (`vanbandi`);
- văn bản phải tồn tại;
- văn bản `pham_vi = 'HAN_CHE'` không đi qua trình ký;
- người trình phải xem được văn bản.

Cài đặt tạm (chờ hàm "văn bản xem được" dùng chung của Nhóm 2, #68 mục C5):
- đọc trực tiếp bảng DDL `documents_vanbandi`, chỉ các cột `id`, `pham_vi`, `nguoi_tao_id` (tên chuẩn hóa ở #96;
  DB dựng từ DDL cũ dùng `nguoi_tao`), `trich_yeu`, `so_hieu`;
- quyền xem: người tạo văn bản hoặc có quyền `view_vanbandi`.
Khi Nhóm 2 có hàm dùng chung, thay thân `_doc_van_ban_di` và `_xem_duoc` bằng lời gọi hàm đó.

`mo_ta_van_ban(document_type, van_ban_id)`: số hiệu, trích yếu để ghi vào bằng chứng và trang phê duyệt
của tệp hoàn tất (Phase 10); không kiểm quyền, đọc lỗi thì trả rỗng để không chặn việc hoàn tất duyệt.
"""

import logging
from dataclasses import dataclass

from django.db import DatabaseError, connection, transaction
from rest_framework import status

from .. import enums
from ..errors import SigningError
from ..permissions import co_quyen

BANG_VAN_BAN_DI = "documents_vanbandi"
PHAM_VI_HAN_CHE = "HAN_CHE"

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class VanBanDi:
    id: int
    pham_vi: str
    nguoi_tao_id: int | None
    so_hieu: str
    trich_yeu: str


def _thong_tin_cot(cursor):
    """Xác định cột hỗ trợ cả schema chuẩn hóa (#96) lẫn schema cũ từ DDL trước đó."""
    cot = {c.name for c in connection.introspection.get_table_description(cursor, BANG_VAN_BAN_DI)}
    cot_nguoi_tao = "nguoi_tao_id" if "nguoi_tao_id" in cot else "nguoi_tao"
    co_pham_vi = "pham_vi" in cot
    return cot_nguoi_tao, co_pham_vi


def _cot_nguoi_tao(cursor):
    """Cột người tạo văn bản: `nguoi_tao_id` theo DDL chuẩn hóa (#96), `nguoi_tao` với DDL trước đó."""
    cot_nguoi_tao, _ = _thong_tin_cot(cursor)
    return cot_nguoi_tao


def _doc_van_ban_di(van_ban_id):
    if BANG_VAN_BAN_DI not in connection.introspection.table_names():
        raise SigningError(
            code="chua_co_du_lieu_van_ban",
            detail="Hệ thống chưa có dữ liệu văn bản đi (phân hệ Văn bản chưa được triển khai).",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    with connection.cursor() as cursor:
        cot_nguoi_tao, co_pham_vi = _thong_tin_cot(cursor)
        cot_pv = "pham_vi" if co_pham_vi else "'NOI_BO' AS pham_vi"
        cursor.execute(
            f"SELECT id, {cot_pv}, {cot_nguoi_tao}, so_hieu, trich_yeu FROM {BANG_VAN_BAN_DI} WHERE id = %s",
            [van_ban_id],
        )
        row = cursor.fetchone()
    if row is None:
        return None
    return VanBanDi(id=row[0], pham_vi=row[1], nguoi_tao_id=row[2], so_hieu=row[3] or "", trich_yeu=row[4] or "")


def _xem_duoc(nguoi_dung, van_ban):
    return van_ban.nguoi_tao_id == nguoi_dung.pk or co_quyen(nguoi_dung, "view_vanbandi")


def kiem_tra_van_ban_trinh_ky(nguoi_dung, document_type, van_ban_id):
    if document_type != enums.LoaiVanBan.VAN_BAN_DI:
        raise SigningError(code="chi_trinh_ky_van_ban_di", detail="Trình ký chỉ nhận văn bản đi.",
                           fields={"document_type": ["Chỉ nhận 'vanbandi'."]})
    van_ban = _doc_van_ban_di(van_ban_id)
    if van_ban is None:
        raise SigningError(code="khong_tim_thay_van_ban", detail="Không tìm thấy văn bản đi.",
                           status_code=status.HTTP_404_NOT_FOUND, fields={"van_ban_id": ["Không tồn tại."]})
    if van_ban.pham_vi == PHAM_VI_HAN_CHE:
        raise SigningError(code="van_ban_han_che_khong_trinh_ky",
                           detail="Văn bản hạn chế không đi qua trình ký.",
                           fields={"van_ban_id": ["Văn bản có phạm vi HAN_CHE."]})
    if not _xem_duoc(nguoi_dung, van_ban):
        # Không tiết lộ sự tồn tại của văn bản người dùng không được xem
        raise SigningError(code="khong_tim_thay_van_ban", detail="Không tìm thấy văn bản đi.",
                           status_code=status.HTTP_404_NOT_FOUND, fields={"van_ban_id": ["Không tồn tại."]})
    return van_ban


def mo_ta_van_ban(document_type, van_ban_id):
    """{"so_hieu", "trich_yeu"} của văn bản; rỗng khi không đọc được (bảng chưa có, văn bản đã xóa)."""
    if document_type != enums.LoaiVanBan.VAN_BAN_DI:
        return {}
    try:
        with transaction.atomic():  # savepoint: lỗi đọc không làm hỏng transaction hoàn tất duyệt
            van_ban = _doc_van_ban_di(van_ban_id)
    except SigningError:  # chưa có bảng văn bản (Nhóm 2 chưa triển khai): không có mô tả, không phải lỗi
        return {}
    except DatabaseError:
        logger.warning("Không đọc được mô tả văn bản %s #%s", document_type, van_ban_id)
        return {}
    if van_ban is None:
        return {}
    return {"so_hieu": van_ban.so_hieu, "trich_yeu": van_ban.trich_yeu}


TOI_DA_TIM = 20


def tim_van_ban_di(nguoi_dung, tu_khoa=""):
    """
    Văn bản đi người dùng được chọn khi tạo hồ sơ (#80 mục E): văn bản thường (không HAN_CHE), người dùng xem
    được; tìm theo số hiệu hoặc trích yếu. Chưa có bảng văn bản thì trả rỗng.
    Cài đặt tạm đọc bảng DDL; thay bằng hàm "văn bản xem được" của Nhóm 2 (#68 mục C5).
    """
    if BANG_VAN_BAN_DI not in connection.introspection.table_names():
        return []
    with connection.cursor() as cursor:
        cot_nguoi_tao, co_pham_vi = _thong_tin_cot(cursor)
        sql = f"SELECT id, so_hieu, trich_yeu FROM {BANG_VAN_BAN_DI} WHERE 1=1"
        tham_so = []
        if co_pham_vi:
            sql += " AND pham_vi <> %s"
            tham_so.append(PHAM_VI_HAN_CHE)
        if not co_quyen(nguoi_dung, "view_vanbandi"):
            sql += f" AND {cot_nguoi_tao} = %s"
            tham_so.append(nguoi_dung.pk)
        if tu_khoa:
            sql += " AND (UPPER(so_hieu) LIKE UPPER(%s) OR UPPER(trich_yeu) LIKE UPPER(%s))"
            tham_so += [f"%{tu_khoa}%", f"%{tu_khoa}%"]
        sql += f" ORDER BY id DESC LIMIT {TOI_DA_TIM}"
        cursor.execute(sql, tham_so)
        return [{"id": r[0], "so_hieu": r[1] or "", "trich_yeu": r[2] or ""} for r in cursor.fetchall()]
