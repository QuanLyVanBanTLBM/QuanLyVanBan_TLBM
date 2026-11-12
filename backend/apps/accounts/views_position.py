"""
API Danh mục Chức vụ (Issue #20): /api/positions/...

Quyền (codename theo RBAC contract Issue #21): view_chucvu, add_chucvu, change_chucvu, delete_chucvu, import_chucvu.
Chức vụ is_public = False chỉ hiển thị với quản trị (superuser hoặc có change_chucvu).
"""
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.http import HttpResponse
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from authorization.permissions import require_permission
from organizations.references import position_in_use

from .excel_position import ImportFileError, generate_position_template, import_positions_from_excel
from .models import Position
from .serializers import PositionSerializer

DENIED = "positions.messages.permissionDenied"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

# Quyền theo method, kiểm bằng helper chung trước khi view chạy (người thiếu quyền nhận 403 kể cả với id không tồn tại).
LIST_PERMS = {"GET": "view_chucvu", "POST": "add_chucvu"}
DETAIL_PERMS = {"GET": "view_chucvu", "PUT": "change_chucvu", "PATCH": "change_chucvu", "DELETE": "delete_chucvu"}


class StandardPositionPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


def _can_see_internal(user) -> bool:
    return bool(user.is_superuser or user.has_perm("change_chucvu"))


def _visible_positions(user):
    queryset = Position.objects.all().order_by("display_order", "name", "id")
    if not _can_see_internal(user):
        queryset = queryset.filter(is_public=True)
    return queryset


def _stt_conflict():
    return Response({"display_order": ["positions.messages.sttExists"]}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated, require_permission(LIST_PERMS, DENIED)])
def position_list_create_view(request):
    if request.method == "GET":
        queryset = _visible_positions(request.user)
        search = request.query_params.get("search", "").strip()
        if search:
            queryset = queryset.filter(name__icontains=search)

        if request.query_params.get("all", "").lower() == "true":
            return Response(PositionSerializer(queryset, many=True).data)

        paginator = StandardPositionPagination()
        page = paginator.paginate_queryset(queryset, request)
        return paginator.get_paginated_response(PositionSerializer(page, many=True).data)

    serializer = PositionSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    try:
        serializer.save()
    except IntegrityError:
        return _stt_conflict()
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated, require_permission(DETAIL_PERMS, DENIED)])
def position_detail_view(request, pk):
    position = _visible_positions(request.user).filter(pk=pk).first()
    if position is None:
        return Response({"detail": "positions.messages.notFound"}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        return Response(PositionSerializer(position).data)

    if request.method == "DELETE":
        if position_in_use(position.pk):
            return Response({"detail": "positions.messages.inUseByModule"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            with transaction.atomic():
                position.delete()
        except ProtectedError:
            return Response({"detail": "positions.messages.inUse"}, status=status.HTTP_400_BAD_REQUEST)
        except IntegrityError:  # DB dựng từ DDL chặn bằng ON DELETE RESTRICT
            return Response({"detail": "positions.messages.inUseByModule"}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = PositionSerializer(position, data=request.data, partial=request.method == "PATCH")
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    try:
        serializer.save()
    except IntegrityError:
        return _stt_conflict()
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated, require_permission("import_chucvu", DENIED)])
def position_import_template_view(request):
    response = HttpResponse(generate_position_template().getvalue(), content_type=XLSX)
    response["Content-Disposition"] = 'attachment; filename="mau_import_chuc_vu.xlsx"'
    return response


@api_view(["POST"])
@permission_classes([IsAuthenticated, require_permission("import_chucvu", DENIED)])
@parser_classes([MultiPartParser, FormParser])
def position_import_view(request):
    upload = request.FILES.get("file")
    if upload is None:
        return Response({"detail": "positions.import.errors.fileRequired"}, status=status.HTTP_400_BAD_REQUEST)
    if not upload.name.lower().endswith(".xlsx"):
        return Response({"detail": "positions.import.errors.invalidFile"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        result = import_positions_from_excel(upload)
    except ImportFileError as exc:
        return Response({"detail": exc.key}, status=status.HTTP_400_BAD_REQUEST)
    return Response(result, status=status.HTTP_200_OK)
