import io
from datetime import datetime
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .filters import TaiLieuChiTietFilter
from .models import DanhMucTaiLieu, LoaiTaiLieu, TaiLieuChiTiet, ChiTietTaiLieuAttachment
from .serializers import (
    DanhMucTaiLieuSerializer,
    LoaiTaiLieuSerializer,
    TaiLieuChiTietSerializer,
    ChiTietTaiLieuAttachmentSerializer,
)


class DanhMucTaiLieuViewSet(viewsets.ModelViewSet):
    """
    ViewSet cho Danh mục Tài liệu (Cấp 1):
    - CRUD danh mục
    - Tự động gán người lập nếu đã đăng nhập
    - Tìm kiếm theo tên tài liệu, số ký hiệu
    - Xuất Excel danh mục Cấp 1
    """
    queryset = DanhMucTaiLieu.objects.select_related('nguoi_lap').all()
    serializer_class = DanhMucTaiLieuSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['ten_tai_lieu', 'ky_hieu', 'ghi_chu']
    ordering_fields = ['stt_uu_tien', 'id', 'created_at', 'ten_tai_lieu']
    ordering = ['stt_uu_tien', 'id']

    def perform_create(self, serializer):
        kwargs = {}
        if self.request.user and self.request.user.is_authenticated:
            if 'nguoi_lap' not in serializer.validated_data:
                kwargs['nguoi_lap'] = self.request.user
        serializer.save(**kwargs)

    @action(detail=False, methods=['get'], url_path='export-excel')
    def export_excel(self, request):
        qs = self.filter_queryset(self.get_queryset())
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "DanhMucCap1"

        header_font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
        center_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
        thin_border = Border(
            left=Side(style="thin", color="CCCCCC"),
            right=Side(style="thin", color="CCCCCC"),
            top=Side(style="thin", color="CCCCCC"),
            bottom=Side(style="thin", color="CCCCCC"),
        )

        headers = ["STT", "Số ký hiệu", "Tên tài liệu / Danh mục", "Người lập", "Ngày lập", "Ghi chú"]
        ws.append(headers)

        for col_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = center_align

        for idx, item in enumerate(qs, start=1):
            nguoi_lap_str = (
                item.nguoi_lap.get_full_name() or item.nguoi_lap.username
                if item.nguoi_lap else ""
            )
            ngay_lap_str = item.ngay_lap.strftime("%d/%m/%Y") if item.ngay_lap else ""
            row_data = [
                item.stt_uu_tien or idx,
                item.ky_hieu or "",
                item.ten_tai_lieu,
                nguoi_lap_str,
                ngay_lap_str,
                item.ghi_chu or "",
            ]
            ws.append(row_data)

        # Style data rows and auto width
        for row in ws.iter_rows(min_row=2, max_row=ws.max_row, min_col=1, max_col=len(headers)):
            for cell in row:
                cell.border = thin_border
                cell.alignment = Alignment(vertical="center")

        for col in ws.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            col_letter = get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)

        response = HttpResponse(
            output.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        response["Content-Disposition"] = f'attachment; filename="Danh_muc_cap1_{date_str}.xlsx"'
        return response


class LoaiTaiLieuViewSet(viewsets.ModelViewSet):
    """
    ViewSet cho Loại tài liệu (Cấp 2):
    - CRUD loại tài liệu
    - Lọc theo Cấp 1 (`dm_tai_lieu`)
    - Tìm kiếm theo tên loại
    """
    queryset = LoaiTaiLieu.objects.select_related('dm_tai_lieu').all()
    serializer_class = LoaiTaiLieuSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['dm_tai_lieu', 'is_public']
    search_fields = ['ten_loai', 'ghi_chu']
    ordering_fields = ['id', 'ten_loai', 'created_at']
    ordering = ['id']


class TaiLieuChiTietViewSet(viewsets.ModelViewSet):
    """
    ViewSet cho Chi tiết tài liệu chung:
    - CRUD chi tiết tài liệu (kèm ManyToMany loai_tai_lieu và FileField upload)
    - Quản lý trạng thái hiệu lực: CON_HIEU_LUC, HET_HIEU_LUC, HET_VA_THAY_THE
    - Upload file đính kèm với validator (< 20MB, định dạng hợp lệ)
    - Phân quyền hiển thị: TAT_CA hoặc NOI_BO_PHONG_BAN
    - Bộ lọc đa tiêu chí: dm_tai_lieu, loai_tai_lieu, nam, hieu_luc, search
    - Xuất Excel danh sách tài liệu theo đúng bộ lọc tìm kiếm
    """
    serializer_class = TaiLieuChiTietSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = TaiLieuChiTietFilter
    search_fields = ['tieu_de', 'ky_hieu', 'noi_ban_hanh', 'ghi_chu']
    ordering_fields = ['ngay_dang', 'id', 'tieu_de', 'ky_hieu']
    ordering = ['-ngay_dang', '-id']

    def get_queryset(self):
        qs = TaiLieuChiTiet.objects.select_related(
            'dm_tai_lieu', 'nguoi_tao'
        ).prefetch_related('loai_tai_lieu', 'attachments').all()

        user = self.request.user
        # Người dùng chưa đăng nhập: chỉ thấy tài liệu công khai (TAT_CA)
        if not user or not user.is_authenticated:
            return qs.filter(hien_thi='TAT_CA')

        # Quản trị viên và Staff: thấy toàn bộ
        if user.is_superuser or user.is_staff:
            return qs

        # Người dùng đăng nhập: thấy tài liệu TAT_CA, hoặc do chính mình tạo, hoặc cùng đơn vị/phòng ban
        user_dept = ""
        if hasattr(user, "profile"):
            user_dept = getattr(user.profile, "department", "")
        user_don_vi_id = getattr(user, "don_vi_id", None)

        q_filter = Q(hien_thi='TAT_CA') | Q(nguoi_tao=user)
        if user_don_vi_id:
            q_filter |= Q(hien_thi='NOI_BO_PHONG_BAN', don_vi_id=user_don_vi_id)
        if user_dept:
            q_filter |= Q(hien_thi='NOI_BO_PHONG_BAN', nguoi_tao__profile__department=user_dept)

        return qs.filter(q_filter).distinct()

    def perform_create(self, serializer):
        kwargs = {}
        if self.request.user and self.request.user.is_authenticated:
            kwargs['nguoi_tao'] = self.request.user
            if 'don_vi_id' not in serializer.validated_data and hasattr(self.request.user, 'don_vi_id'):
                kwargs['don_vi_id'] = getattr(self.request.user, 'don_vi_id')
        serializer.save(**kwargs)

    @action(detail=True, methods=['post'], url_path='toggle-validity')
    def toggle_validity(self, request, pk=None):
        """
        API chuyển đổi nhanh trạng thái hiệu lực
        """
        obj = self.get_object()
        target_status = request.data.get('hieu_luc') or request.data.get('status')
        link_thay_the = request.data.get('link_thay_the')
        ngay_het_hieu_luc = request.data.get('ngay_het_hieu_luc')

        if target_status:
            valid_statuses = [choice[0] for choice in TaiLieuChiTiet.HIEU_LUC_CHOICES]
            if target_status not in valid_statuses:
                return Response(
                    {'error': f"Trạng thái '{target_status}' không hợp lệ. Cho phép: {valid_statuses}"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            obj.hieu_luc = target_status
        else:
            # Toggle giữa CON_HIEU_LUC và HET_HIEU_LUC
            if obj.hieu_luc == 'CON_HIEU_LUC':
                obj.hieu_luc = 'HET_HIEU_LUC'
            else:
                obj.hieu_luc = 'CON_HIEU_LUC'

        if link_thay_the is not None:
            obj.link_thay_the = link_thay_the
        if ngay_het_hieu_luc is not None:
            obj.ngay_het_hieu_luc = ngay_het_hieu_luc

        try:
            obj.full_clean()
            obj.save()
        except DjangoValidationError as e:
            return Response(
                e.message_dict if hasattr(e, 'message_dict') else {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = self.get_serializer(obj)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='export-excel')
    def export_excel(self, request):
        """
        Xuất danh sách tài liệu chi tiết sang file Excel (.xlsx) theo đúng bộ lọc tìm kiếm hiện tại
        """
        filtered_qs = self.filter_queryset(self.get_queryset())

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "DanhSachTaiLieu"

        # Cấu hình phong cách bảng tính
        title_font = Font(name="Arial", size=14, bold=True, color="1E3A8A")
        header_font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
        dimmed_fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
        dimmed_font = Font(name="Arial", size=10, color="64748B")
        center_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
        left_align = Alignment(horizontal="left", vertical="center", wrap_text=True)
        thin_border = Border(
            left=Side(style="thin", color="CCCCCC"),
            right=Side(style="thin", color="CCCCCC"),
            top=Side(style="thin", color="CCCCCC"),
            bottom=Side(style="thin", color="CCCCCC"),
        )

        # Tiêu đề bảng
        ws.merge_cells("A1:L1")
        title_cell = ws["A1"]
        title_cell.value = "DANH SÁCH TÀI LIỆU VÀ BIỂU MẪU CHUNG"
        title_cell.font = title_font
        title_cell.alignment = Alignment(horizontal="center", vertical="center")
        ws.row_dimensions[1].height = 35

        # Dòng thời gian xuất
        ws.merge_cells("A2:L2")
        sub_cell = ws["A2"]
        sub_cell.value = f"Ngày xuất báo cáo: {datetime.now().strftime('%d/%m/%Y %H:%M')} | Tổng số tài liệu: {filtered_qs.count()}"
        sub_cell.font = Font(name="Arial", size=10, italic=True, color="475569")
        sub_cell.alignment = Alignment(horizontal="center", vertical="center")
        ws.row_dimensions[2].height = 20

        # Header
        headers = [
            "STT",
            "Số ký hiệu",
            "Tiêu đề tài liệu",
            "Danh mục Cấp 1",
            "Loại tài liệu Cấp 2",
            "Nơi ban hành",
            "Ngày đăng",
            "Hiệu lực",
            "Ngày hết hiệu lực",
            "Văn bản thay thế",
            "Phạm vi hiển thị",
            "Người tạo",
        ]
        ws.append([])  # Dòng trống row 3
        ws.append(headers)  # Row 4
        ws.row_dimensions[4].height = 28

        for col_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=4, column=col_idx)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = center_align
            cell.border = thin_border

        # Điền dữ liệu
        for idx, doc in enumerate(filtered_qs, start=1):
            loai_names = ", ".join([lt.ten_loai for lt in doc.loai_tai_lieu.all()])
            ngay_dang_str = doc.ngay_dang.strftime("%d/%m/%Y") if doc.ngay_dang else ""
            ngay_het_str = doc.ngay_het_hieu_luc.strftime("%d/%m/%Y") if doc.ngay_het_hieu_luc else ""
            nguoi_tao_str = (
                doc.nguoi_tao.get_full_name() or doc.nguoi_tao.username
                if doc.nguoi_tao else ""
            )

            is_expired = doc.hieu_luc in ['HET_HIEU_LUC', 'HET_VA_THAY_THE']

            row_data = [
                idx,
                doc.ky_hieu or "",
                doc.tieu_de,
                doc.dm_tai_lieu.ten_tai_lieu if doc.dm_tai_lieu else "",
                loai_names,
                doc.noi_ban_hanh or "",
                ngay_dang_str,
                doc.get_hieu_luc_display(),
                ngay_het_str,
                doc.link_thay_the or "",
                doc.get_hien_thi_display(),
                nguoi_tao_str,
            ]
            ws.append(row_data)
            current_row = ws.max_row
            ws.row_dimensions[current_row].height = 24

            for col_idx in range(1, len(headers) + 1):
                c = ws.cell(row=current_row, column=col_idx)
                c.border = thin_border
                if is_expired:
                    c.fill = dimmed_fill
                    c.font = dimmed_font

                # Căn lề
                if col_idx in [1, 2, 7, 8, 9, 11]:
                    c.alignment = center_align
                else:
                    c.alignment = left_align

        # Tự động canh chỉnh độ rộng cột
        for col in ws.columns:
            if col[0].row > 4:
                continue
            max_len = 0
            for cell in col:
                if cell.row < 4:
                    continue
                val = str(cell.value or "")
                if len(val) > max_len:
                    max_len = len(val)
            col_letter = get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)

        response = HttpResponse(
            output.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        response["Content-Disposition"] = f'attachment; filename="Danh_sach_tai_lieu_{date_str}.xlsx"'
        return response


class ChiTietTaiLieuAttachmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet cho Tệp đính kèm tài liệu (1-N Hướng A):
    - Quản lý danh sách, upload, xóa mềm tệp đính kèm theo DDL Base
    - Chuẩn hóa tên cột nguoi_tao_id, created_at (PR #96 / PR #101)
    """
    queryset = ChiTietTaiLieuAttachment.objects.filter(is_deleted=False).select_related('document', 'nguoi_tao')
    serializer_class = ChiTietTaiLieuAttachmentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['document']
    search_fields = ['name']

    def perform_create(self, serializer):
        kwargs = {}
        if self.request.user and self.request.user.is_authenticated:
            kwargs['nguoi_tao'] = self.request.user
        serializer.save(**kwargs)

    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.save()


