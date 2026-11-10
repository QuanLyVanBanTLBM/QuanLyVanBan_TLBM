"""
Tìm kiếm không phân biệt hoa thường và dấu tiếng Việt cho danh sách hồ sơ, văn bản chọn khi trình ký.

Không dùng extension `unaccent` (phải đổi DDL, AGENTS.md mục 5): chuẩn hóa cột bằng hàm sẵn có của PostgreSQL
`LOWER(TRANSLATE(cột, <chữ có dấu>, <chữ không dấu>))`, từ khóa chuẩn hóa bằng `bo_dau` phía Python. Chỉ xử lý
dữ liệu dựng sẵn (NFC), là dạng mặc định khi nhập từ bàn phím và trình duyệt.
"""

import unicodedata

from django.db.models import F, Func, Q, TextField, Value

NGUYEN_AM = "aăâeêioôơuưy"
DAU = ("\u0300", "\u0301", "\u0309", "\u0303", "\u0323")  # huyền, sắc, hỏi, ngã, nặng


def _bang_chuyen():
    co_dau, khong_dau = ["đĐ"], ["dd"]
    for chu in NGUYEN_AM:
        goc = unicodedata.normalize("NFD", chu)[0]
        bien_the = [chu] + [unicodedata.normalize("NFC", chu + dau) for dau in DAU]
        for x in bien_the:
            if x != goc:  # chữ không dấu giữ nguyên, LOWER xử lý chữ hoa
                co_dau.append(x + x.upper())
                khong_dau.append(goc * 2)
    return "".join(co_dau), "".join(khong_dau)


CO_DAU, KHONG_DAU = _bang_chuyen()


def bo_dau(chuoi):
    """Chữ thường, bỏ dấu tiếng Việt (đ -> d)."""
    chuoi = unicodedata.normalize("NFD", (chuoi or "").lower()).replace("đ", "d")
    return "".join(c for c in chuoi if unicodedata.category(c) != "Mn")


class BoDau(Func):
    """Biểu thức SQL tương ứng `bo_dau` trên một cột."""

    template = "LOWER(TRANSLATE(%(expressions)s))"
    arg_joiner = ", "
    output_field = TextField()

    def __init__(self, cot, **extra):
        super().__init__(F(cot) if isinstance(cot, str) else cot, Value(CO_DAU), Value(KHONG_DAU), **extra)


def khop_khong_dau(tu_khoa, *cot):
    """Q: một trong các cột chứa từ khóa, không phân biệt hoa thường và dấu. Gắn alias `_bd_<cột>` qua `chu_thich`."""
    tu_khoa = bo_dau(tu_khoa)
    dieu_kien = Q()
    for c in cot:
        dieu_kien |= Q(**{f"{ten_bi_danh(c)}__contains": tu_khoa})
    return dieu_kien


def ten_bi_danh(cot):
    return "_bd_" + cot.replace("__", "_")


def chu_thich(queryset, *cot):
    """Thêm alias đã bỏ dấu cho các cột (dùng cùng `khop_khong_dau`)."""
    return queryset.alias(**{ten_bi_danh(c): BoDau(c) for c in cot})


def loc_khong_dau(queryset, tu_khoa, *cot):
    """Lọc queryset: một trong các cột chứa từ khóa (không phân biệt hoa thường và dấu)."""
    return chu_thich(queryset, *cot).filter(khop_khong_dau(tu_khoa, *cot))
