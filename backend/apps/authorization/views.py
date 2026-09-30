from django.contrib.auth.models import Group, Permission
from django.db import IntegrityError
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .serializers import GroupSerializer, PermissionSerializer


class StandardPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def group_list_create_view(request):
    if request.method == "GET":
        if not request.user.has_perm("auth.view_group"):
            return Response({"detail": "roles.messages.permissionDenied"}, status=status.HTTP_403_FORBIDDEN)

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
    if not request.user.has_perm("auth.add_group"):
        return Response({"detail": "roles.messages.permissionDenied"}, status=status.HTTP_403_FORBIDDEN)

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


@api_view(["GET", "PUT", "DELETE"])
@permission_classes([IsAuthenticated])
def group_detail_view(request, pk):
    try:
        group = Group.objects.get(pk=pk)
    except Group.DoesNotExist:
        return Response({"detail": "roles.messages.groupNotFound"}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        if not request.user.has_perm("auth.view_group"):
            return Response({"detail": "roles.messages.permissionDenied"}, status=status.HTTP_403_FORBIDDEN)
        serializer = GroupSerializer(group)
        return Response(serializer.data)

    if request.method == "PUT":
        if not request.user.has_perm("auth.change_group"):
            return Response({"detail": "roles.messages.permissionDenied"}, status=status.HTTP_403_FORBIDDEN)
        serializer = GroupSerializer(group, data=request.data)
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
    if not request.user.has_perm("auth.delete_group"):
        return Response({"detail": "roles.messages.permissionDenied"}, status=status.HTTP_403_FORBIDDEN)
    if group.user_set.exists():
        return Response({"detail": "roles.messages.groupHasUsers"}, status=status.HTTP_400_BAD_REQUEST)
    group.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def permission_list_view(request):
    if not request.user.has_perm("auth.view_group"):
        return Response({"detail": "roles.messages.permissionDenied"}, status=status.HTTP_403_FORBIDDEN)

    queryset = Permission.objects.select_related("content_type").order_by(
        "content_type__app_label", "codename"
    )
    serializer = PermissionSerializer(queryset, many=True)
    return Response(serializer.data)
