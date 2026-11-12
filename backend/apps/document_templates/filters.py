import django_filters
from django.db.models import Q
from .models import TaiLieuChiTiet


class TaiLieuChiTietFilter(django_filters.FilterSet):
    """
    Bộ lọc đa tiêu chí cho Danh sách tài liệu chung:
    - dm_tai_lieu: Lọc theo Danh mục Cấp 1
    - loai_tai_lieu: Lọc theo Loại tài liệu Cấp 2 (M2M)
    - nam: Lọc theo năm của ngày đăng (ngay_dang__year)
    - hieu_luc: Lọc theo trạng thái hiệu lực
    - hien_thi: Lọc theo phạm vi hiển thị
    - don_vi_id: Lọc theo đơn vị phòng ban sở hữu
    - search: Tìm kiếm theo tiêu đề, ký hiệu, nơi ban hành
    """
    dm_tai_lieu = django_filters.NumberFilter(field_name='dm_tai_lieu_id')
    loai_tai_lieu = django_filters.NumberFilter(field_name='loai_tai_lieu__id')
    nam = django_filters.NumberFilter(field_name='ngay_dang', lookup_expr='year')
    hieu_luc = django_filters.CharFilter(method='filter_hieu_luc')
    hien_thi = django_filters.CharFilter(field_name='hien_thi')
    don_vi_id = django_filters.NumberFilter(field_name='don_vi_id')
    search = django_filters.CharFilter(method='filter_search')
    search_field = django_filters.CharFilter(method='filter_search_field')

    class Meta:
        model = TaiLieuChiTiet
        fields = ['dm_tai_lieu', 'loai_tai_lieu', 'nam', 'hieu_luc', 'hien_thi', 'don_vi_id', 'search', 'search_field']

    def filter_search_field(self, queryset, name, value):
        return queryset

    def filter_hieu_luc(self, queryset, name, value):
        if not value:
            return queryset
        val = value.strip()
        from django.utils import timezone
        today = timezone.localdate()

        if val == 'CON_HIEU_LUC':
            return queryset.filter(
                Q(hieu_luc='CON_HIEU_LUC', ngay_het_hieu_luc__isnull=True) |
                Q(ngay_het_hieu_luc__gt=today, hieu_luc__in=['CON_HIEU_LUC', 'HET_HIEU_LUC', 'HET_VA_THAY_THE'])
            ).distinct()
        elif val == 'CON_HIEU_LUC_1_PHAN':
            return queryset.filter(
                Q(hieu_luc='CON_HIEU_LUC_1_PHAN') &
                (Q(ngay_het_hieu_luc__isnull=True) | Q(ngay_het_hieu_luc__gt=today))
            ).distinct()
        elif val == 'HET_HIEU_LUC':
            return queryset.filter(
                Q(ngay_het_hieu_luc__lte=today, hieu_luc__in=['CON_HIEU_LUC', 'HET_HIEU_LUC']) |
                Q(hieu_luc='HET_HIEU_LUC', ngay_het_hieu_luc__isnull=True)
            ).distinct()
        elif val == 'HET_VA_THAY_THE':
            return queryset.filter(
                Q(hieu_luc='HET_VA_THAY_THE') &
                (Q(ngay_het_hieu_luc__isnull=True) | Q(ngay_het_hieu_luc__lte=today))
            ).distinct()
        return queryset.filter(hieu_luc=val)

    def filter_search(self, queryset, name, value):
        if not value:
            return queryset
        val = value.strip()
        search_field = self.data.get('search_field', 'all')

        import re
        from datetime import datetime

        def parse_date_q(s):
            clean = s.replace('-', '/').strip()
            m_full = re.match(r'^(\d{1,2})/(\d{1,2})/(\d{4})$', clean)
            if m_full:
                d, m, y = int(m_full.group(1)), int(m_full.group(2)), int(m_full.group(3))
                try:
                    return Q(ngay_dang=datetime(y, m, d).date())
                except ValueError:
                    pass
            m_iso = re.match(r'^(\d{4})-(\d{1,2})-(\d{1,2})$', s)
            if m_iso:
                y, m, d = int(m_iso.group(1)), int(m_iso.group(2)), int(m_iso.group(3))
                try:
                    return Q(ngay_dang=datetime(y, m, d).date())
                except ValueError:
                    pass
            m_my = re.match(r'^(\d{1,2})/(\d{4})$', clean)
            if m_my:
                m, y = int(m_my.group(1)), int(m_my.group(2))
                if 1 <= m <= 12:
                    return Q(ngay_dang__month=m, ngay_dang__year=y)
            m_dm = re.match(r'^(\d{1,2})/(\d{1,2})$', clean)
            if m_dm:
                d, m = int(m_dm.group(1)), int(m_dm.group(2))
                if 1 <= m <= 12 and 1 <= d <= 31:
                    return Q(ngay_dang__day=d, ngay_dang__month=m)
            if re.match(r'^\d{4}$', s):
                return Q(ngay_dang__year=int(s))
            return None

        date_q = parse_date_q(val)

        if search_field == 'title':
            return queryset.filter(tieu_de__icontains=val)
        elif search_field == 'code':
            return queryset.filter(ky_hieu__icontains=val)
        elif search_field == 'date':
            if date_q:
                return queryset.filter(date_q)
            from django.db.models.functions import Cast
            from django.db.models import CharField
            return queryset.annotate(ngay_dang_str=Cast('ngay_dang', output_field=CharField())).filter(ngay_dang_str__icontains=val)
        elif search_field == 'authority':
            return queryset.filter(noi_ban_hanh__icontains=val)
        elif search_field == 'author':
            return queryset.filter(
                Q(nguoi_tao__ho_ten__icontains=val) |
                Q(nguoi_tao__username__icontains=val)
            ).distinct()
        elif search_field == 'attachment':
            return queryset.filter(attachments__name__icontains=val, attachments__is_deleted=False).distinct()

        base_q = (
            Q(tieu_de__icontains=val) |
            Q(ky_hieu__icontains=val) |
            Q(noi_ban_hanh__icontains=val) |
            Q(ghi_chu__icontains=val) |
            Q(nguoi_tao__ho_ten__icontains=val) |
            Q(nguoi_tao__username__icontains=val) |
            Q(attachments__name__icontains=val, attachments__is_deleted=False)
        )
        if date_q:
            base_q = base_q | date_q
        return queryset.filter(base_q).distinct()
