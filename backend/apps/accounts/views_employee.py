"""
API ViewSets cho phân hệ Quản lý Cán bộ Nhân viên (CBNV - Issue #24).
Tác giả: Lê Duy Khánh (leduykhanhdevs).
"""
from django.db import transaction
from django.db.models import Q, ProtectedError, RestrictedError, Prefetch
from django.contrib.auth.models import Group
from django.http import HttpResponse
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Employee, EmployeeAssignment
from .serializers import (
    GroupSimpleSerializer,
    EmployeeSerializer,
    EmployeeCreateSerializer,
    EmployeeUpdateSerializer,
    user_can_view_sensitive,
)
from .excel_cbnv import generate_cbnv_template, import_cbnv_from_excel, export_cbnv_to_excel
from .permissions import CanChangeEmployeePermission, CanViewGroupPermission, require_permission


SAFE_ORDERING_FIELDS = {
    "ho_ten", "-ho_ten",
    "username", "-username",
    "email", "-email",
    "created_at", "-created_at",
    "don_vi__stt_uu_tien", "-don_vi__stt_uu_tien",
    "chuc_vu__display_order", "-chuc_vu__display_order",
    "id", "-id",
}


class StandardEmployeePagination(PageNumberPagination):
    """Phân trang chuẩn cho danh sách cán bộ nhân viên."""
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class GroupViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Danh sách Nhóm quyền (auth.Group) hỗ trợ cấu hình phân quyền cho CBNV.
    Yêu cầu quyền view_nhomquyen, change_full_cbnv hoặc add_cbnv.
    """
    queryset = Group.objects.all().order_by("name")
    serializer_class = GroupSimpleSerializer
    permission_classes = [IsAuthenticated, CanViewGroupPermission]

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class EmployeeViewSet(viewsets.ModelViewSet):
    """
    API Quản lý Cán bộ Nhân viên (CBNV - Issue #24).
    Hỗ trợ tìm kiếm, lọc theo đơn vị/chức vụ/trạng thái, tải file mẫu, xuất Excel và import Excel.
    """
    pagination_class = StandardEmployeePagination

    def get_permissions(self):
        if self.action in ["list", "retrieve", "template"]:
            permission_classes = [IsAuthenticated, require_permission("view_list_cbnv")]
        elif self.action == "export":
            permission_classes = [IsAuthenticated, require_permission("export_cbnv")]
        elif self.action == "create":
            permission_classes = [IsAuthenticated, require_permission("add_cbnv")]
        elif self.action in ["update", "partial_update"]:
            permission_classes = [IsAuthenticated, CanChangeEmployeePermission]
        elif self.action == "destroy":
            permission_classes = [IsAuthenticated, require_permission("delete_cbnv")]
        elif self.action == "import_excel":
            permission_classes = [IsAuthenticated, require_permission("import_cbnv")]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        queryset = (
            Employee.objects.select_related("don_vi__khoi", "chuc_vu")
            .prefetch_related(
                "groups",
                Prefetch(
                    "assignments",
                    queryset=EmployeeAssignment.objects.select_related("don_vi__khoi", "chuc_vu").order_by("id"),
                ),
            )
            .all()
        )

        search = self.request.query_params.get("search", "").strip()
        if search:
            queryset = queryset.filter(
                Q(ho_ten__icontains=search)
                | Q(username__icontains=search)
                | Q(email__icontains=search)
                | Q(sdt__icontains=search)
            )

        for param_name in ("don_vi_id", "khoi_id", "chuc_vu_id"):
            val = self.request.query_params.get(param_name)
            if val is not None and val != "":
                try:
                    int(val)
                except ValueError:
                    raise ValidationError({"detail": "employees.messages.invalidFilterParam"})

        don_vi_id = self.request.query_params.get("don_vi_id")
        if don_vi_id:
            queryset = queryset.filter(don_vi_id=don_vi_id)

        khoi_id = self.request.query_params.get("khoi_id")
        if khoi_id:
            queryset = queryset.filter(don_vi__khoi_id=khoi_id)

        chuc_vu_id = self.request.query_params.get("chuc_vu_id")
        if chuc_vu_id:
            queryset = queryset.filter(chuc_vu_id=chuc_vu_id)

        trang_thai = self.request.query_params.get("trang_thai")
        if trang_thai is not None and trang_thai != "":
            if trang_thai not in Employee.Status.values:
                raise ValidationError({"detail": "employees.messages.invalidFilterParam"})
            queryset = queryset.filter(trang_thai=trang_thai)

        is_public = self.request.query_params.get("is_public")
        if is_public is not None and is_public != "":
            queryset = queryset.filter(is_public=(is_public.lower() in ["true", "1"]))

        ordering = self.request.query_params.get("ordering")
        if ordering:
            allowed = set(SAFE_ORDERING_FIELDS)
            user = getattr(self.request, "user", None)
            if user and (user.is_superuser or user.has_perm("view_full_cbnv")):
                allowed.update({"ngay_sinh", "-ngay_sinh"})
            if ordering not in allowed:
                raise ValidationError({"detail": "employees.messages.invalidOrdering"})
            queryset = queryset.order_by(ordering)
        else:
            queryset = queryset.order_by(
                "don_vi__stt_uu_tien", "chuc_vu__display_order", "ho_ten", "id"
            )

        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        if request.query_params.get("all", "").lower() == "true":
            serializer = EmployeeSerializer(queryset, many=True, context={"request": request})
            return Response(serializer.data, status=status.HTTP_200_OK)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = EmployeeSerializer(page, many=True, context={"request": request})
            return self.get_paginated_response(serializer.data)

        serializer = EmployeeSerializer(queryset, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = EmployeeSerializer(instance, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        if not isinstance(request.data, dict):
            return Response(
                {"detail": "employees.messages.invalidDataFormat"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = EmployeeCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        employee = serializer.save()
        output_serializer = EmployeeSerializer(employee, context={"request": request})
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        if not isinstance(request.data, dict):
            return Response(
                {"detail": "employees.messages.invalidDataFormat"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        instance = self.get_object()
        user = request.user

        # Bảo vệ đặc quyền: Người dùng không có quyền change_full_cbnv và không phải superuser
        # CHỈ ĐƯỢC PHÉP sửa các trường thông tin cá nhân (sdt, email, ngay_sinh).
        if not (user.is_superuser or user.has_perm("change_full_cbnv")):
            allowed_self_fields = {"sdt", "email", "ngay_sinh"}
            disallowed_fields = set(request.data.keys()) - allowed_self_fields
            if disallowed_fields:
                return Response(
                    {"detail": "roles.messages.permissionDenied"},
                    status=status.HTTP_403_FORBIDDEN,
                )

        # Chốt nghiệp vụ khóa tài khoản / chuyển trạng thái nghỉ việc:
        new_status = request.data.get("trang_thai")
        raw_is_active = request.data.get("is_active")

        parsed_is_active = None
        if raw_is_active is not None:
            if isinstance(raw_is_active, bool):
                parsed_is_active = raw_is_active
            elif isinstance(raw_is_active, str):
                s = raw_is_active.strip().lower()
                if s in ("false", "0", "f"):
                    parsed_is_active = False
                elif s in ("true", "1", "t"):
                    parsed_is_active = True
            elif isinstance(raw_is_active, int):
                parsed_is_active = bool(raw_is_active)

        is_deactivating = (
            (new_status == Employee.Status.NGHI_VIEC)
            or (parsed_is_active is False)
        )
        if is_deactivating:
            if instance.id == user.id:
                return Response(
                    {"detail": "employees.messages.cannotDeactivateSelf"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if instance.is_superuser and not user.is_superuser:
                return Response(
                    {"detail": "employees.messages.cannotDeactivateSuperuser"},
                    status=status.HTTP_403_FORBIDDEN,
                )
            if instance.is_superuser:
                other_active = (
                    Employee.objects.filter(is_superuser=True, is_active=True)
                    .exclude(trang_thai=Employee.Status.NGHI_VIEC)
                    .exclude(id=instance.id)
                )
                if not other_active.exists():
                    return Response(
                        {"detail": "employees.messages.cannotDeactivateLastSuperuser"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

        serializer = EmployeeUpdateSerializer(
            instance, data=request.data, partial=partial, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        updated_employee = serializer.save()
        output_serializer = EmployeeSerializer(updated_employee, context={"request": request})
        return Response(output_serializer.data, status=status.HTTP_200_OK)

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        user = request.user

        # 0. Bắt buộc xác thực mật khẩu người thực hiện trong body JSON của DELETE
        password = None
        if isinstance(request.data, dict):
            password = request.data.get("password")

        if not password or not user.check_password(str(password)):
            return Response(
                {"detail": "employees.messages.invalidPassword"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 1. Không cho phép tự xóa chính mình
        if instance.id == user.id:
            return Response(
                {"detail": "employees.messages.cannotDeleteSelf"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 2. Không cho phép người không phải superuser xóa tài khoản superuser
        if instance.is_superuser and not user.is_superuser:
            return Response(
                {"detail": "employees.messages.cannotDeleteSuperuser"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # 3. Không để mất superuser hoạt động cuối cùng
        if instance.is_superuser:
            other_active = (
                Employee.objects.filter(is_superuser=True, is_active=True)
                .exclude(trang_thai=Employee.Status.NGHI_VIEC)
                .exclude(id=instance.id)
            )
            if not other_active.exists():
                return Response(
                    {"detail": "employees.messages.cannotDeleteLastSuperuser"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        try:
            with transaction.atomic():
                instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except (ProtectedError, RestrictedError):
            return Response(
                {
                    "detail": "employees.messages.cannotDeleteProtected"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=False, methods=["get"], url_path="template")
    def template(self, request):
        """Tải tệp Excel mẫu để nhập danh sách cán bộ nhân viên."""
        buffer = generate_cbnv_template()
        response = HttpResponse(
            buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = 'attachment; filename="mau_danh_sach_cbnv.xlsx"'
        return response

    @action(detail=False, methods=["get"], url_path="export")
    def export(self, request):
        """Xuất toàn bộ danh sách cán bộ nhân viên ra tệp Excel (.xlsx)."""
        queryset = self.filter_queryset(self.get_queryset())
        buffer = export_cbnv_to_excel(queryset, request.user)
        response = HttpResponse(
            buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = 'attachment; filename="danh_sach_cbnv.xlsx"'
        return response

    @action(detail=False, methods=["post"], url_path="import", parser_classes=[MultiPartParser, FormParser])
    def import_excel(self, request):
        """
        Nhập danh sách cán bộ nhân viên từ tệp Excel (.xlsx).
        Yêu cầu quyền import_cbnv hoặc superuser (kiểm soát bởi get_permissions).
        """

        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response(
                {"detail": "employees.messages.fileRequired"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not file_obj.name.lower().endswith(".xlsx"):
            return Response(
                {"detail": "employees.messages.fileInvalidType"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = import_cbnv_from_excel(file_obj)
        if not result["success"]:
            return Response(
                {
                    "success": False,
                    "message": "employees.messages.importHasErrors",
                    "errors": result["errors"],
                    "total_errors": len(result["errors"]),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "success": True,
                "message": "employees.messages.importSuccess",
                "created_count": result["created_count"],
            },
            status=status.HTTP_201_CREATED,
        )
