"""
Bộ lọc nâng cao cho API Văn bản — Kiến trúc 3 Model.

Hỗ trợ:
- Tìm kiếm từ khóa (q / keyword): theo số hiệu, trích yếu, nơi ban hành
- Lọc theo loại văn bản (loai / type): hỗ trợ hoa/thường (DEN, den, DI, di, MAT, mat)
- Lọc theo năm (nam / year)
- Lọc theo khoảng ngày (tu_ngay / from_date, den_ngay / to_date)
- Lọc theo hiệu lực (hieu_luc / status): hỗ trợ hoa/thường
- Lọc theo trạng thái hiển thị (hien_thi / is_public)
- Lọc danh sách người xem văn bản (ViewerFilter)
"""

import django_filters
from django.contrib.auth import get_user_model
from django.db.models import Q

from .models import (
    HieuLuc,
    LoaiVanBan,
    VanBanDen,
    VanBanDi,
    VanBanMat,
    DocumentViewLog,
)


class BaseDocumentFilter(django_filters.FilterSet):
    """Bộ lọc cơ sở chứa toàn bộ các logic tìm kiếm và lọc dùng chung."""

    # ── Từ khóa tìm kiếm ──────────────────────────────────────────
    q = django_filters.CharFilter(
        method="filter_search",
        label="Tìm kiếm",
        help_text="Tìm theo số hiệu, trích yếu, nơi ban hành",
    )
    keyword = django_filters.CharFilter(
        method="filter_search",
        label="Keyword (English alias)",
    )

    # ── Loại văn bản (case-insensitive + English alias) ─────────────
    loai = django_filters.CharFilter(
        method="filter_loai",
        label="Loại văn bản",
    )
    type = django_filters.CharFilter(
        method="filter_loai",
        label="Type (English alias)",
    )

    # ── Năm ───────────────────────────────────────────────────────
    nam = django_filters.NumberFilter(
        field_name="nam",
        label="Năm",
    )
    year = django_filters.NumberFilter(
        field_name="nam",
        label="Year (English alias)",
    )

    # ── Khoảng ngày ────────────────────────────────────────────────
    tu_ngay = django_filters.DateTimeFilter(
        method="filter_tu_ngay",
        label="Từ ngày",
        help_text="Lọc từ ngày",
    )
    from_date = django_filters.DateTimeFilter(
        method="filter_tu_ngay",
        label="From date (English alias)",
    )
    den_ngay = django_filters.DateTimeFilter(
        method="filter_den_ngay",
        label="Đến ngày",
        help_text="Lọc đến ngày",
    )
    to_date = django_filters.DateTimeFilter(
        method="filter_den_ngay",
        label="To date (English alias)",
    )

    # ── Hiệu lực (case-insensitive + English alias) ────────────────
    hieu_luc = django_filters.CharFilter(
        method="filter_hieu_luc",
        label="Hiệu lực",
    )
    status = django_filters.CharFilter(
        method="filter_hieu_luc",
        label="Status (English alias)",
    )

    # ── Trạng thái hiển thị ───────────────────────────────────────
    hien_thi = django_filters.BooleanFilter(
        field_name="hien_thi",
        label="Trạng thái hiển thị",
    )
    is_public = django_filters.BooleanFilter(
        field_name="hien_thi",
        label="Is public (English alias)",
    )

    # ── Chỉ văn bản còn hiệu lực / Ẩn văn bản hết hiệu lực ───────
    chi_con_hieu_luc = django_filters.BooleanFilter(
        method="filter_chi_con_hieu_luc",
        label="Chỉ văn bản còn hiệu lực",
    )
    only_active = django_filters.BooleanFilter(
        method="filter_chi_con_hieu_luc",
        label="Only active (English alias)",
    )
    include_expired = django_filters.BooleanFilter(
        method="filter_noop",
        label="Bao gồm văn bản hết hiệu lực",
    )

    # ── Liên kết Loại văn bản (URL route từ Nhóm 3: ?loai_van_ban=<id> hoặc text) ──
    loai_van_ban = django_filters.CharFilter(
        method="filter_loai_van_ban",
        label="Loại văn bản",
        help_text="Lọc theo loại văn bản (Nhóm 3 liên kết)",
    )

    # ── Hồ sơ / Danh mục hồ sơ ───────────────────────────────────
    ho_so = django_filters.CharFilter(
        method="filter_ho_so",
        label="Hồ sơ",
        help_text="Lọc theo hồ sơ hoặc danh mục hồ sơ",
    )
    folder = django_filters.CharFilter(
        method="filter_ho_so",
        label="Folder (English alias)",
    )

    # ── Số hiệu và Trích yếu văn bản ─────────────────────────────
    so_hieu = django_filters.CharFilter(
        lookup_expr="icontains",
        label="Số hiệu văn bản",
    )
    trich_yeu = django_filters.CharFilter(
        lookup_expr="icontains",
        label="Trích yếu văn bản",
    )

    # ── Người ký, Nơi ban hành, Đơn vị nhận (Văn bản Đi / Đến) ───
    nguoi_ky = django_filters.CharFilter(
        lookup_expr="icontains",
        label="Người ký",
    )
    signer = django_filters.CharFilter(
        lookup_expr="icontains",
        label="Signer (English alias)",
    )
    noi_ban_hanh = django_filters.CharFilter(
        method="filter_noi_ban_hanh",
        label="Nơi ban hành",
    )
    issuing_unit = django_filters.CharFilter(
        method="filter_noi_ban_hanh",
        label="Issuing unit (English alias)",
    )
    don_vi_nhan = django_filters.CharFilter(
        method="filter_don_vi_nhan",
        label="Đơn vị nhận",
    )
    recipient_unit = django_filters.CharFilter(
        method="filter_don_vi_nhan",
        label="Recipient unit (English alias)",
    )

    # ── Phạm vi văn bản (URL route từ Nhóm 3: ?pham_vi=HAN_CHE hoặc NOI_BO) ──
    pham_vi = django_filters.CharFilter(
        method="filter_pham_vi",
        label="Phạm vi",
        help_text="Lọc theo phạm vi (NOI_BO hoặc HAN_CHE)",
    )
    scope = django_filters.CharFilter(
        method="filter_pham_vi",
        label="Scope (English alias)",
    )

    def filter_noi_ban_hanh(self, queryset, name, value):
        if not value:
            return queryset
        val = str(value).strip()
        fields = [f.name for f in queryset.model._meta.fields]
        q_cond = Q()
        if "noi_ban_hanh" in fields:
            q_cond |= Q(noi_ban_hanh__icontains=val)
        if hasattr(queryset.model, "noibanhanh_links") and val.isdigit():
            q_cond |= Q(noibanhanh_links__donvi_id=int(val))
        if q_cond:
            return queryset.filter(q_cond).distinct()
        return queryset

    def filter_don_vi_nhan(self, queryset, name, value):
        if not value:
            return queryset
        val = str(value).strip()
        fields = [f.name for f in queryset.model._meta.fields]
        q_cond = Q()
        if "don_vi_nhan" in fields:
            q_cond |= Q(don_vi_nhan__icontains=val)
        if hasattr(queryset.model, "donvinhan") and val.isdigit():
            q_cond |= Q(donvinhan__donvi_id=int(val))
        if q_cond:
            return queryset.filter(q_cond).distinct()
        return queryset

    def filter_pham_vi(self, queryset, name, value):
        if not value:
            return queryset
        val = value.strip().upper()
        fields = [f.name for f in queryset.model._meta.fields]
        if "pham_vi" in fields:
            return queryset.filter(pham_vi__iexact=val)
        return queryset

    def filter_loai_van_ban(self, queryset, name, value):
        if not value:
            return queryset
        val = str(value).strip()
        if val.isdecimal():
            if not hasattr(queryset.model, "danhmuc"):
                return queryset.none()
            return queryset.filter(danhmuc__loaivanban_id=int(val)).distinct()
        fields = [f.name for f in queryset.model._meta.fields]
        q_cond = Q()
        if "ten_loai_van_ban" in fields:
            q_cond |= Q(ten_loai_van_ban__icontains=val)
        type_abbr_map = {
            "QUYẾT ĐỊNH": ["QĐ", "QD", "QUYẾT ĐỊNH"],
            "THÔNG BÁO": ["TB", "THÔNG BÁO"],
            "HƯỚNG DẪN": ["HD", "HĐ", "HƯỚNG DẪN"],
            "KẾ HOẠCH": ["KH", "KẾ HOẠCH"],
            "CÔNG VĂN": ["CV", "CÔNG VĂN"],
            "CHỈ THỊ": ["CT", "CHỈ THỊ"],
            "TỜ TRÌNH": ["TTR", "TỜ TRÌNH"],
            "BÁO CÁO": ["BC", "BÁO CÁO"],
            "NGHỊ QUYẾT": ["NQ", "NGHỊ QUYẾT"],
        }
        val_upper = val.upper()
        if val_upper in type_abbr_map:
            abbrs = type_abbr_map[val_upper]
            q_cond |= Q(trich_yeu__icontains=val)
            for abbr in abbrs:
                q_cond |= Q(so_hieu__icontains=f"/{abbr}") | Q(so_hieu__icontains=f"{abbr}-")
        else:
            q_cond |= Q(trich_yeu__icontains=val) | Q(so_hieu__icontains=val)

        return queryset.filter(q_cond).distinct()

    def filter_ho_so(self, queryset, name, value):
        if not value:
            return queryset
        val = str(value).strip()
        fields = [f.name for f in queryset.model._meta.fields]
        q_cond = Q()
        if "danh_muc_ho_so" in fields:
            q_cond |= Q(danh_muc_ho_so__icontains=val)
        if hasattr(queryset.model, "hoso") and val.isdigit():
            q_cond |= Q(hoso__hoso_id=int(val))
        else:
            q_cond |= Q(trich_yeu__icontains=val)
        if q_cond:
            return queryset.filter(q_cond).distinct()
        return queryset

    def filter_search(self, queryset, name, value):
        """Tìm kiếm từ khóa trên nhiều trường (icontains)."""
        if not value:
            return queryset
        fields = [f.name for f in queryset.model._meta.fields]
        cond = Q(so_hieu__icontains=value) | Q(trich_yeu__icontains=value)
        if "noi_ban_hanh" in fields:
            cond |= Q(noi_ban_hanh__icontains=value)
        return queryset.filter(cond)

    def filter_loai(self, queryset, name, value):
        """Lọc loại văn bản, không phân biệt hoa/thường."""
        if not value:
            return queryset
        val = value.strip().upper()
        current_loai = getattr(queryset.model, "loai", "DEN")
        if val != current_loai and val != queryset.model._meta.model_name.upper():
            return queryset.none()

        return queryset

    def filter_chi_con_hieu_luc(self, queryset, name, value):
        if value:
            return queryset.exclude(hieu_luc=HieuLuc.HET_HIEU_LUC)
        return queryset

    def filter_noop(self, queryset, name, value):
        return queryset

    def filter_hieu_luc(self, queryset, name, value):
        """Lọc hiệu lực, không phân biệt hoa/thường."""
        if not value:
            return queryset
        val = value.strip().upper()
        if val in ("HIEU_LUC", "CON_HIEU_LUC_ALL", "ACTIVE_ALL"):
            return queryset.filter(hieu_luc__in=[HieuLuc.CON_HIEU_LUC, HieuLuc.CON_HIEU_LUC_1_PHAN])
        return queryset.filter(hieu_luc__iexact=value.strip())

    def filter_tu_ngay(self, queryset, name, value):
        if not value:
            return queryset
        fields = [f.name for f in queryset.model._meta.fields]
        if "ngay_den" in fields:
            return queryset.filter(ngay_den__gte=value)
        elif "ngay_ban_hanh" in fields:
            return queryset.filter(ngay_ban_hanh__gte=value)
        elif "ngay_van_ban" in fields:
            return queryset.filter(ngay_van_ban__gte=value)
        return queryset

    def filter_den_ngay(self, queryset, name, value):
        if not value:
            return queryset
        from datetime import datetime, time
        if isinstance(value, datetime) and value.time() == time.min:
            target_value = value.replace(hour=23, minute=59, second=59, microsecond=999999)
        elif hasattr(value, "hour") and value.hour == 0 and value.minute == 0:
            target_value = value.replace(hour=23, minute=59, second=59, microsecond=999999)
        else:
            target_value = value
        fields = [f.name for f in queryset.model._meta.fields]
        if "ngay_den" in fields:
            return queryset.filter(ngay_den__lte=target_value)
        elif "ngay_ban_hanh" in fields:
            return queryset.filter(ngay_ban_hanh__lte=target_value)
        elif "ngay_van_ban" in fields:
            return queryset.filter(ngay_van_ban__lte=target_value)
        return queryset


class VanBanDenFilter(BaseDocumentFilter):
    class Meta:
        model = VanBanDen
        fields = [
            "nam", "year", "hien_thi", "is_public", "pham_vi"
        ]


class VanBanDiFilter(BaseDocumentFilter):
    class Meta:
        model = VanBanDi
        fields = [
            "nam", "year", "hien_thi", "is_public", "pham_vi",
            "so_hieu", "trich_yeu", "nguoi_ky", "noi_ban_hanh", "don_vi_nhan"
        ]


class VanBanMatFilter(BaseDocumentFilter):
    class Meta:
        model = VanBanMat
        fields = [
            "q", "so_hieu", "trich_yeu", "nam", "year", "tu_ngay", "den_ngay", "hien_thi", "is_public", "pham_vi", "hieu_luc"
        ]


DocumentFilter = VanBanDenFilter


def get_filter_class_for_model(model):
    if model == VanBanDi:
        return VanBanDiFilter
    if model == VanBanMat:
        return VanBanMatFilter
    return VanBanDenFilter


class ViewerFilter(django_filters.FilterSet):
    """Bộ lọc cho danh sách người xem văn bản."""

    search = django_filters.CharFilter(
        method="filter_search",
        label="Tìm theo tên",
    )
    name = django_filters.CharFilter(
        method="filter_search",
        label="Name (English alias)",
    )
    don_vi = django_filters.CharFilter(
        method="filter_don_vi",
        label="Đơn vị / Phòng ban",
    )
    department = django_filters.CharFilter(
        method="filter_don_vi",
        label="Department (English alias)",
    )

    class Meta:
        model = DocumentViewLog
        fields = ["search", "name", "don_vi", "department"]

    def filter_search(self, queryset, name, value):
        if not value:
            return queryset
        user_model = get_user_model()
        q = Q(user__username__icontains=value)
        if hasattr(user_model, "ho_ten"):
            q |= Q(user__ho_ten__icontains=value)
        if hasattr(user_model, "first_name"):
            q |= Q(user__first_name__icontains=value)
        if hasattr(user_model, "last_name"):
            q |= Q(user__last_name__icontains=value)
        return queryset.filter(q)

    def filter_don_vi(self, queryset, name, value):
        if not value:
            return queryset
        user_model = get_user_model()
        if hasattr(user_model, "don_vi"):
            return queryset.filter(user__don_vi__ten__icontains=value)
        return queryset.filter(user__profile__department__icontains=value)
