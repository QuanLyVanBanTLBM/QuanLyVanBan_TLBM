from django.contrib.auth.models import Group
from django.db import IntegrityError
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import PermissionInfo
from .permissions import is_system_admin, require_permission
from .serializers import GroupSerializer, PermissionSerializer, standard_code

# Quyền theo method, kiểm bằng helper chung trước khi view chạy (kể cả trước khi tra bản ghi,
# nên người thiếu quyền không dò được id nhóm nào tồn tại).
LIST_PERMS = {"GET": "view_nhomquyen", "POST": "add_nhomquyen"}
DETAIL_PERMS = {
    "GET": "view_nhomquyen",
    "PUT": "change_nhomquyen",
    "PATCH": "change_nhomquyen",
    "DELETE": "delete_nhomquyen",
}


class StandardPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated, require_permission(LIST_PERMS)])
def group_list_create_view(request):
    if request.method == "GET":
        queryset = Group.objects.all().order_by("name")
        search = request.query_params.get("search", "").strip()
        if search:
            queryset = queryset.filter(name__icontains=search)

        if request.query_params.get("all") == "true":
            serializer = GroupSerializer(queryset, many=True)
            return Response(serializer.data)

        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = GroupSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    # POST
    serializer = GroupSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        serializer.save()
    except IntegrityError:
        return Response(
            {"name": ["roles.messages.nameExists"]}, status=status.HTTP_400_BAD_REQUEST
        )
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated, require_permission(DETAIL_PERMS)])
def group_detail_view(request, pk):
    try:
        group = Group.objects.get(pk=pk)
    except Group.DoesNotExist:
        return Response({"detail": "roles.messages.groupNotFound"}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        serializer = GroupSerializer(group)
        return Response(serializer.data)

    if request.method in ("PUT", "PATCH"):
        serializer = GroupSerializer(group, data=request.data, partial=request.method == "PATCH")
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            serializer.save()
        except IntegrityError:
            return Response(
                {"name": ["roles.messages.nameExists"]}, status=status.HTTP_400_BAD_REQUEST
            )
        return Response(serializer.data)

    # DELETE
    if standard_code(group):
        return Response({"detail": "roles.messages.groupProtected"}, status=status.HTTP_400_BAD_REQUEST)
    if group.user_set.exists():
        return Response({"detail": "roles.messages.groupHasUsers"}, status=status.HTTP_400_BAD_REQUEST)
    group.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
@permission_classes([IsAuthenticated, require_permission("view_nhomquyen")])
def permission_list_view(request):
    serializer = PermissionSerializer(PermissionInfo.objects.all(), many=True)
    return Response(serializer.data)


@api_view(["PUT"])
@permission_classes([IsAuthenticated, require_permission("change_nhomquyen")])
def group_permissions_view(request, pk):
    """Gán/bỏ quyền cho một nhóm: thay toàn bộ tập quyền bằng `permission_ids`."""
    try:
        group = Group.objects.get(pk=pk)
    except Group.DoesNotExist:
        return Response({"detail": "roles.messages.groupNotFound"}, status=status.HTTP_404_NOT_FOUND)

    if "permission_ids" not in request.data:
        return Response(
            {"permission_ids": ["roles.messages.permissionInvalid"]}, status=status.HTTP_400_BAD_REQUEST
        )
    serializer = GroupSerializer(group, data={"permission_ids": request.data["permission_ids"]}, partial=True)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    serializer.save()
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_permissions_view(request):
    """Quyền của user đang đăng nhập (codename). Frontend chỉ dùng để ẩn/hiện thao tác; backend vẫn kiểm quyền thật."""
    user = request.user
    return Response(
        {
            "is_superuser": user.is_superuser,
            "is_system_admin": is_system_admin(user),
            "permissions": sorted(user.get_all_permissions()),
        }
    )
