"""
Views và API Endpoints cho phân hệ Cơ cấu Tổ chức & Đơn vị (Module 7.3 - Nhóm 7).
Tác giả: Lê Duy Khánh.
"""
from io import BytesIO
from django.db.models import Q
from django.http import HttpResponse
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

from .models import KhoiKhuVuc, DonVi
from .serializers import KhoiKhuVucSerializer, DonViSerializer


class StandardResultsSetPagination(PageNumberPagination):
    """
    Phân trang chuẩn cho danh mục đơn vị (10 bản ghi/trang).
    """
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class KhoiKhuVucViewSet(viewsets.ModelViewSet):
    """
    API CRUD Khối / Khu vực (Cấp 1).
    Endpoint: /api/organizations/regions/
    """
    queryset = KhoiKhuVuc.objects.prefetch_related("don_vi_list").all()
    serializer_class = KhoiKhuVucSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["ten"]
    ordering_fields = ["thu_tu_hien_thi", "ten", "created_at"]
    ordering = ["thu_tu_hien_thi", "ten"]

    def destroy(self, request, *args, **kwargs):
        """
        Ngăn chặn xóa Khối/Khu vực nếu vẫn còn Đơn vị trực thuộc.
        Bảo đảm tính toàn vẹn dữ liệu.
        """
        instance = self.get_object()
        child_count = instance.don_vi_list.count()
        if child_count > 0:
            return Response(
                {
                    "detail": f"Không thể xóa Khối/Khu vực '{instance.ten}' vì hiện có {child_count} Đơn vị trực thuộc. Vui lòng chuyển hoặc xóa các Đơn vị con trước.",
                    "code": "HAS_CHILD_UNITS",
                    "child_count": child_count,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)


class DonViViewSet(viewsets.ModelViewSet):
    """
    API CRUD Đơn vị / Phòng ban (Cấp 2).
    Endpoint: /api/organizations/units/
    """
    serializer_class = DonViSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["ten", "dia_chi", "dien_thoai", "email", "ghi_chu"]
    ordering_fields = ["stt_uu_tien", "ten", "khoi__ten", "created_at"]
    ordering = ["stt_uu_tien", "ten"]

    def get_queryset(self):
        """
        Tối ưu truy vấn tránh N+1 (select_related khoi),
        hỗ trợ lọc theo khoi_id / region_id và xử lý hiển thị is_public.
        """
        queryset = DonVi.objects.select_related("khoi").all()

        # Lọc theo Khối / Khu vực
        region_id = self.request.query_params.get("region_id") or self.request.query_params.get("khoi_id")
        if region_id:
            queryset = queryset.filter(khoi_id=region_id)

        # Lọc theo trạng thái is_public
        is_public_param = self.request.query_params.get("is_public")
        if is_public_param is not None:
            if is_public_param.lower() in ["true", "1"]:
                queryset = queryset.filter(is_public=True)
            elif is_public_param.lower() in ["false", "0"]:
                queryset = queryset.filter(is_public=False)

        # Tìm kiếm nâng cao đa từ khóa nếu có
        search_query = self.request.query_params.get("search")
        if search_query:
            queryset = queryset.filter(
                Q(ten__icontains=search_query)
                | Q(dia_chi__icontains=search_query)
                | Q(dien_thoai__icontains=search_query)
                | Q(email__icontains=search_query)
                | Q(ghi_chu__icontains=search_query)
            )

        return queryset

    @action(detail=False, methods=["get"], url_path="export")
    def export_excel(self, request):
        """
        Xuất danh sách Đơn vị / Phòng ban ra tệp Excel (.xlsx).
        Áp dụng toàn bộ bộ lọc hiện thời của người dùng.
        """
        queryset = self.filter_queryset(self.get_queryset())

        # Tạo file Excel bằng openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Danh Sách Đơn Vị"

        # Định dạng Header
        header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")  # Blue 900
        header_font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
        center_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
        left_align = Alignment(horizontal="left", vertical="center")
        thin_border = Border(
            left=Side(style="thin", color="CBD5E1"),
            right=Side(style="thin", color="CBD5E1"),
            top=Side(style="thin", color="CBD5E1"),
            bottom=Side(style="thin", color="CBD5E1"),
        )

        # Tiêu đề bảng
        ws.merge_cells("A1:H1")
        title_cell = ws["A1"]
        title_cell.value = "DANH SÁCH ĐƠN VỊ / PHÒNG BAN — CƠ CẤU TỔ CHỨC ITC"
        title_cell.font = Font(name="Arial", size=14, bold=True, color="1E3A8A")
        title_cell.alignment = Alignment(horizontal="center", vertical="center")
        ws.row_dimensions[1].height = 35

        # Danh sách cột
        headers = [
            "STT Ưu Tiên",
            "Tên Đơn Vị / Phòng Ban",
            "Khối / Khu Vực Trực Thuộc",
            "Địa Chỉ",
            "Số Điện Thoại",
            "Email Liên Hệ",
            "Trạng Thái Hiển Thị",
            "Ghi Chú",
        ]

        for col_idx, header_text in enumerate(headers, start=1):
            cell = ws.cell(row=3, column=col_idx, value=header_text)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = center_align
            cell.border = thin_border
        ws.row_dimensions[3].height = 28

        # Ghi dữ liệu
        for row_idx, item in enumerate(queryset, start=4):
            status_text = "Công khai" if item.is_public else "Nội bộ (Ẩn)"
            row_data = [
                item.stt_uu_tien,
                item.ten,
                item.khoi.ten if item.khoi else "",
                item.dia_chi,
                item.dien_thoai,
                item.email,
                status_text,
                item.ghi_chu,
            ]
            for col_idx, val in enumerate(row_data, start=1):
                c = ws.cell(row=row_idx, column=col_idx, value=val)
                c.border = thin_border
                c.font = Font(name="Arial", size=10)
                if col_idx in [1, 7]:
                    c.alignment = center_align
                else:
                    c.alignment = left_align
            ws.row_dimensions[row_idx].height = 22

        # Căn chỉnh độ rộng cột tự động
        column_widths = {1: 14, 2: 35, 3: 30, 4: 35, 5: 18, 6: 28, 7: 20, 8: 30}
        for col_idx, width in column_widths.items():
            col_letter = openpyxl.utils.get_column_letter(col_idx)
            ws.column_dimensions[col_letter].width = width

        # Xuất buffer byte
        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        response = HttpResponse(
            buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = 'attachment; filename="Danh_sach_don_vi_phong_ban.xlsx"'
        return response
