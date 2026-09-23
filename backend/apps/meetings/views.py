from datetime import datetime
from django.db import transaction, models
from django.utils import timezone
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from .models import PhongHop, DatPhongHop
from .serializers import PhongHopSerializer, DatPhongHopSerializer


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class IsAdminOrStaffOrReadOnly(permissions.BasePermission):
    """
    Cho phép mọi người dùng đã đăng nhập xem (GET, HEAD, OPTIONS).
    Chỉ Quản trị viên (is_staff) hoặc có quyền Django tương ứng mới được tạo/sửa/xóa.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        # Ghi: kiểm tra quyền admin hoặc permission
        if request.user.is_staff or request.user.is_superuser:
            return True
        if hasattr(request.user, "profile") and request.user.profile.role == "admin":
            return True
        if request.method == "POST":
            return request.user.has_perm("meetings.add_phonghop")
        if request.method in ["PUT", "PATCH"]:
            return request.user.has_perm("meetings.change_phonghop")
        if request.method == "DELETE":
            return request.user.has_perm("meetings.delete_phonghop")
        return False


class IsOwnerOrAdminForBooking(permissions.BasePermission):
    """
    Quyền thao tác lịch đặt phòng họp:
    - Xem: Mọi user đã đăng nhập.
    - Tạo: Mọi user đã đăng nhập.
    - Sửa / Hủy / Xóa: Người đặt (chủ lịch) hoặc Quản trị viên / người có quyền.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        # Admin / Superuser / Staff luôn có quyền
        if request.user.is_staff or request.user.is_superuser:
            return True
        if hasattr(request.user, "profile") and request.user.profile.role == "admin":
            return True
        # Người tạo lịch
        if obj.nguoi_dat == request.user:
            return True
        # Hoặc có permission Django
        if request.method in ["PUT", "PATCH"] and request.user.has_perm("meetings.change_datphonghop"):
            return True
        if request.method == "DELETE" and request.user.has_perm("meetings.delete_datphonghop"):
            return True
        return False


class PhongHopViewSet(viewsets.ModelViewSet):
    """
    API CRUD Danh mục phòng họp:
    - GET /api/meeting-rooms/
    - POST /api/meeting-rooms/
    - GET /api/meeting-rooms/{id}/
    - PUT/PATCH /api/meeting-rooms/{id}/
    - DELETE /api/meeting-rooms/{id}/
    """
    queryset = PhongHop.objects.all().order_by("ten_phong")
    serializer_class = PhongHopSerializer
    permission_classes = [IsAdminOrStaffOrReadOnly]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        qs = super().get_queryset()
        search = self.request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(
                models.Q(ten_phong__icontains=search) |
                models.Q(vi_tri__icontains=search) |
                models.Q(thiet_bi__icontains=search)
            )

        is_public = self.request.query_params.get("is_public")
        if is_public is not None:
            val = is_public.lower() in ["true", "1", "yes"]
            qs = qs.filter(is_public=val)

        return qs

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        # Kiểm tra xem phòng họp đã có lịch đặt nào chưa
        has_bookings = DatPhongHop.objects.filter(phong_hop=instance).exists()
        if has_bookings:
            return Response(
                {
                    "error": (
                        f"Không thể xóa phòng '{instance.ten_phong}' vì đã có lịch sử đặt phòng họp. "
                        "Vui lòng chuyển trạng thái phòng sang 'Không công khai' (ẩn phòng) để tránh mất lịch sử cuộc họp!"
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        self.perform_destroy(instance)
        return Response(
            {"detail": f"Đã xóa thành công phòng họp '{instance.ten_phong}'."},
            status=status.HTTP_200_OK,
        )


class DatPhongHopViewSet(viewsets.ModelViewSet):
    """
    API Đặt lịch phòng họp:
    - GET /api/meeting-bookings/
    - POST /api/meeting-bookings/
    - GET /api/meeting-bookings/{id}/
    - PUT/PATCH /api/meeting-bookings/{id}/
    - DELETE /api/meeting-bookings/{id}/
    - POST /api/meeting-bookings/{id}/cancel/
    """
    queryset = DatPhongHop.objects.select_related("phong_hop", "nguoi_dat", "nguoi_dat__profile").all()
    serializer_class = DatPhongHopSerializer
    permission_classes = [IsOwnerOrAdminForBooking]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        qs = super().get_queryset().order_by("-thoi_gian_bat_dau")

        # Lọc theo phòng
        phong_id = self.request.query_params.get("room_id") or self.request.query_params.get("phong_hop")
        if phong_id:
            qs = qs.filter(phong_hop_id=phong_id)

        # Lọc theo trạng thái
        trang_thai = self.request.query_params.get("status") or self.request.query_params.get("trang_thai")
        if trang_thai:
            qs = qs.filter(trang_thai=trang_thai)

        # Lọc theo ngày cụ thể (YYYY-MM-DD)
        date_str = self.request.query_params.get("date")
        if date_str:
            try:
                target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                tz = timezone.get_current_timezone()
                start_of_day = timezone.make_aware(
                    datetime.combine(target_date, datetime.min.time()), tz
                )
                end_of_day = timezone.make_aware(
                    datetime.combine(target_date, datetime.max.time()), tz
                )
                qs = qs.filter(
                    thoi_gian_bat_dau__lt=end_of_day,
                    thoi_gian_ket_thuc__gt=start_of_day,
                )
            except ValueError:
                pass

        # Lọc theo khoảng thời gian
        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")
        if start_date:
            try:
                sd = datetime.strptime(start_date, "%Y-%m-%d").date()
                tz = timezone.get_current_timezone()
                qs = qs.filter(thoi_gian_ket_thuc__gte=timezone.make_aware(datetime.combine(sd, datetime.min.time()), tz))
            except ValueError:
                pass
        if end_date:
            try:
                ed = datetime.strptime(end_date, "%Y-%m-%d").date()
                tz = timezone.get_current_timezone()
                qs = qs.filter(thoi_gian_bat_dau__lte=timezone.make_aware(datetime.combine(ed, datetime.max.time()), tz))
            except ValueError:
                pass

        return qs

    def create(self, request, *args, **kwargs):
        """
        Tạo lịch đặt phòng với Database Lock (select_for_update) chống race condition.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phong_hop = serializer.validated_data["phong_hop"]
        start = serializer.validated_data["thoi_gian_bat_dau"]
        end = serializer.validated_data["thoi_gian_ket_thuc"]

        with transaction.atomic():
            # Khóa bản ghi phòng họp để các request đồng thời phải tuần tự kiểm tra
            locked_room = PhongHop.objects.select_for_update().get(id=phong_hop.id)

            conflicts = DatPhongHop.objects.filter(
                phong_hop=locked_room,
                thoi_gian_bat_dau__lt=end,
                thoi_gian_ket_thuc__gt=start,
            ).exclude(trang_thai=DatPhongHop.STATUS_DA_HUY)

            if conflicts.exists():
                conflict = conflicts.first()
                host = conflict.nguoi_dat.get_full_name() or conflict.nguoi_dat.username
                if hasattr(conflict.nguoi_dat, "profile") and conflict.nguoi_dat.profile.full_name:
                    host = conflict.nguoi_dat.profile.full_name
                tz = timezone.get_current_timezone()
                c_start = timezone.localtime(conflict.thoi_gian_bat_dau, tz).strftime("%H:%M")
                c_end = timezone.localtime(conflict.thoi_gian_ket_thuc, tz).strftime("%H:%M ngày %d/%m/%Y")
                return Response(
                    {
                        "error": f"Phòng '{locked_room.ten_phong}' vừa được đặt trùng khung giờ: '{conflict.tieu_de}' ({c_start} - {c_end}) bởi {host}. Vui lòng chọn khung giờ khác!"
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            self.perform_create(serializer)

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        """
        Cập nhật lịch đặt phòng với Database Lock và chống race condition.
        """
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        phong_hop = serializer.validated_data.get("phong_hop", instance.phong_hop)
        start = serializer.validated_data.get("thoi_gian_bat_dau", instance.thoi_gian_bat_dau)
        end = serializer.validated_data.get("thoi_gian_ket_thuc", instance.thoi_gian_ket_thuc)
        new_status = serializer.validated_data.get("trang_thai", instance.trang_thai)

        with transaction.atomic():
            locked_room = PhongHop.objects.select_for_update().get(id=phong_hop.id)

            if new_status != DatPhongHop.STATUS_DA_HUY:
                conflicts = DatPhongHop.objects.filter(
                    phong_hop=locked_room,
                    thoi_gian_bat_dau__lt=end,
                    thoi_gian_ket_thuc__gt=start,
                ).exclude(trang_thai=DatPhongHop.STATUS_DA_HUY).exclude(pk=instance.pk)

                if conflicts.exists():
                    conflict = conflicts.first()
                    host = conflict.nguoi_dat.get_full_name() or conflict.nguoi_dat.username
                    if hasattr(conflict.nguoi_dat, "profile") and conflict.nguoi_dat.profile.full_name:
                        host = conflict.nguoi_dat.profile.full_name
                    tz = timezone.get_current_timezone()
                    c_start = timezone.localtime(conflict.thoi_gian_bat_dau, tz).strftime("%H:%M")
                    c_end = timezone.localtime(conflict.thoi_gian_ket_thuc, tz).strftime("%H:%M ngày %d/%m/%Y")
                    return Response(
                        {
                            "error": f"Không thể đổi sang khung giờ này vì bị trùng với cuộc họp '{conflict.tieu_de}' ({c_start} - {c_end}) bởi {host}!"
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            self.perform_update(serializer)

        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        """
        Hủy lịch đặt phòng họp: giải phóng khung giờ nhưng vẫn giữ lại bản ghi lịch sử.
        """
        booking = self.get_object()
        if booking.trang_thai == DatPhongHop.STATUS_DA_HUY:
            return Response(
                {"detail": "Lịch đặt phòng này đã được hủy trước đó."},
                status=status.HTTP_200_OK,
            )

        booking.trang_thai = DatPhongHop.STATUS_DA_HUY
        reason = request.data.get("ly_do_huy", "").strip()
        if reason:
            booking.ghi_chu = (booking.ghi_chu + f"\n[Lý do hủy]: {reason}").strip()
        booking.save()

        serializer = self.get_serializer(booking)
        return Response(
            {
                "detail": "Đã hủy lịch đặt phòng thành công. Khung giờ đã được giải phóng.",
                "booking": serializer.data,
            },
            status=status.HTTP_200_OK,
        )
