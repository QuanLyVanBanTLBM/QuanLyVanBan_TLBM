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

    # ── Liên kết Loại văn bản (URL route từ Nhóm 3: ?loai_van_ban=<id>) ──
    loai_van_ban = django_filters.CharFilter(
        method="filter_loai_van_ban",
        label="Loại văn bản",
        help_text="Lọc theo loại văn bản ID (Nhóm 3 liên kết)",
    )

    def filter_loai_van_ban(self, queryset, name, value):
        if not value:
            return queryset
        if hasattr(queryset.model, "danhmuc"):
            if str(value).isdigit():
                return queryset.filter(danhmuc__loaivanban_id=int(value))
        return queryset

    def filter_search(self, queryset, name, value):
        """Tìm kiếm từ khóa trên nhiều trường (icontains)."""
        if not value:
            return queryset
        return queryset.filter(
            Q(so_hieu__icontains=value)
            | Q(trich_yeu__icontains=value)
            | Q(noi_ban_hanh__icontains=value)
        )

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
        fields = [f.name for f in queryset.model._meta.fields]
        if "ngay_den" in fields:
            return queryset.filter(ngay_den__lte=value)
        elif "ngay_ban_hanh" in fields:
            return queryset.filter(ngay_ban_hanh__lte=value)
        elif "ngay_van_ban" in fields:
            return queryset.filter(ngay_van_ban__lte=value)
        return queryset


class VanBanDenFilter(BaseDocumentFilter):
    class Meta:
        model = VanBanDen
        fields = [
            "nam", "year", "hien_thi", "is_public"
        ]


class VanBanDiFilter(BaseDocumentFilter):
    class Meta:
        model = VanBanDi
        fields = [
            "nam", "year", "hien_thi", "is_public"
        ]


DocumentFilter = VanBanDenFilter


def get_filter_class_for_model(model):
    if model == VanBanDi:
        return VanBanDiFilter
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
