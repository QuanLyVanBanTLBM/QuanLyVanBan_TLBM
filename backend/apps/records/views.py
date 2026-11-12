from django.db import IntegrityError
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import HoSo, LoaiVanBan
from .permissions import RecordsPermission
from .pagination import RecordsPagination
from .serializers import (
    HoSoSerializer,
    LoaiVanBanSerializer,
)


def filter_by_year(queryset, year_value):
    if not year_value:
        return queryset

    try:
        year = int(year_value)
    except (TypeError, ValueError) as error:
        raise ValidationError(
            {"year": "Năm phải là một số nguyên hợp lệ."}
        ) from error

    if year < 1 or year > 9999:
        raise ValidationError(
            {"year": "Năm phải nằm trong khoảng từ 1 đến 9999."}
        )

    return queryset.filter(ngay_lap__year=year)


class HoSoListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = HoSoSerializer
    permission_classes = [IsAuthenticated, RecordsPermission]
    pagination_class = RecordsPagination

    def get_queryset(self):
        queryset = HoSo.objects.select_related("nguoi_lap").all()

        search = self.request.query_params.get("search", "").strip()
        if search:
            queryset = queryset.filter(
                Q(so_ky_hieu__icontains=search)
                | Q(ten_ho_so__icontains=search)
                | Q(ghi_chu__icontains=search)
            )

        return filter_by_year(
            queryset,
            self.request.query_params.get("year"),
        )

    def perform_create(self, serializer):
        serializer.save(nguoi_lap=self.request.user)


class HoSoDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = HoSo.objects.select_related("nguoi_lap").all()
    serializer_class = HoSoSerializer
    permission_classes = [IsAuthenticated, RecordsPermission]
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        if instance.is_he_thong:
            return Response(
                {
                    "detail": (
                        "Không thể xóa Hồ sơ chung hoặc hồ sơ hệ thống."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        try:
            self.perform_destroy(instance)
        except (ProtectedError, IntegrityError):
            return Response(
                {
                    "detail": (
                        "Không thể xóa hồ sơ vì vẫn còn loại văn bản, văn bản "
                        "hoặc tài liệu đang tham chiếu hồ sơ này."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )
        except ValueError as error:
            return Response(
                {"detail": str(error)},
                status=status.HTTP_409_CONFLICT,
            )

        return Response(status=status.HTTP_204_NO_CONTENT)


class LoaiVanBanListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = LoaiVanBanSerializer
    permission_classes = [IsAuthenticated, RecordsPermission]
    pagination_class = RecordsPagination

    def get_dossier(self):
        if not hasattr(self, "_dossier"):
            self._dossier = get_object_or_404(
                HoSo,
                pk=self.kwargs["dossier_id"],
            )
        return self._dossier

    def get_queryset(self):
        queryset = (
            LoaiVanBan.objects
            .select_related("ho_so")
            .filter(ho_so=self.get_dossier())
        )

        search = self.request.query_params.get("search", "").strip()
        if search:
            queryset = queryset.filter(
                Q(ten_loai__icontains=search)
                | Q(ghi_chu__icontains=search)
            )

        return filter_by_year(
            queryset,
            self.request.query_params.get("year"),
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["dossier"] = self.get_dossier()
        return context

    def perform_create(self, serializer):
        serializer.save(ho_so=self.get_dossier())


class LoaiVanBanDetailAPIView(
    generics.RetrieveUpdateDestroyAPIView
):
    queryset = LoaiVanBan.objects.select_related("ho_so").all()
    serializer_class = LoaiVanBanSerializer
    permission_classes = [IsAuthenticated, RecordsPermission]
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            self.perform_destroy(instance)
        except (ProtectedError, IntegrityError):
            return Response(
                {
                    "detail": (
                        "Không thể xóa loại văn bản vì vẫn còn văn bản "
                        "đang tham chiếu đến loại này."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)



class DocumentTypeCatalogAPIView(generics.ListAPIView):
    """The independent level-2 catalog; nested CRUD remains dossier-scoped."""

    serializer_class = LoaiVanBanSerializer
    permission_classes = [IsAuthenticated, RecordsPermission]
    pagination_class = RecordsPagination

    def get_queryset(self):
        queryset = LoaiVanBan.objects.select_related("ho_so").all()
        dossier = self.request.query_params.get("ho_so")
        if dossier:
            if not dossier.isascii() or not dossier.isdecimal() or int(dossier) < 1:
                raise ValidationError({"ho_so": "ID hồ sơ phải là số nguyên dương."})
            queryset = queryset.filter(ho_so_id=int(dossier))
        search = self.request.query_params.get("search", "").strip()
        if search:
            queryset = queryset.filter(Q(ten_loai__icontains=search) | Q(ghi_chu__icontains=search))
        return filter_by_year(queryset, self.request.query_params.get("year"))
