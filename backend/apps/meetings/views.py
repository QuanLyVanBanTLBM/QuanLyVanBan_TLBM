"""
Views cho phân hệ Phòng họp (Issue #22 - Nhóm 7).
Chuẩn hóa 100% theo DDL cơ sở dữ liệu release_DDL.sql (SQL_Fix4, Issue #53).
"""

from datetime import datetime
from django.db import transaction, IntegrityError
from django.db.models import Q, ProtectedError, RestrictedError
from django.utils import timezone
from rest_framework import status, viewsets, permissions
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from meetings.models import MeetingRoom, MeetingBooking
from meetings.serializers import MeetingRoomSerializer, MeetingBookingSerializer


class StandardPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class MeetingRoomPermission(permissions.BasePermission):
    """
    Quyền truy cập danh mục phòng họp theo chuẩn Django RBAC contract (Issue #21):
    - Xem (GET, HEAD, OPTIONS): Yêu cầu quyền 'view_schedule_phonghop' hoặc is_superuser
    - Thêm (POST): Cần quyền 'add_phonghop' hoặc is_superuser
    - Sửa (PUT, PATCH): Cần quyền 'change_phonghop' hoặc is_superuser
    - Xóa (DELETE): Cần quyền 'delete_phonghop' hoặc is_superuser
    (Bỏ hoàn toàn bypass is_staff, chỉ giữ is_superuser)
    """
    message = "meetings.messages.permissionDenied"

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        if request.method in permissions.SAFE_METHODS:
            return user.has_perm("view_schedule_phonghop")

        if request.method == "POST":
            return user.has_perm("add_phonghop")
        if request.method in ["PUT", "PATCH"]:
            return user.has_perm("change_phonghop")
        if request.method == "DELETE":
            return user.has_perm("delete_phonghop")

        return False


class MeetingRoomViewSet(viewsets.ModelViewSet):
    """
    API ViewSet quản lý CRUD Danh mục phòng họp:
    - GET /api/meeting-rooms/ : Xem danh sách (phân trang, tìm kiếm, lọc)
    - POST /api/meeting-rooms/ : Tạo phòng họp mới
    - GET /api/meeting-rooms/{id}/ : Chi tiết phòng họp
    - PUT/PATCH /api/meeting-rooms/{id}/ : Cập nhật phòng họp
    - DELETE /api/meeting-rooms/{id}/ : Xóa phòng họp (an toàn, bảo vệ dữ liệu liên kết)
    """

    queryset = MeetingRoom.objects.all()
    serializer_class = MeetingRoomSerializer
    pagination_class = StandardPagination
    permission_classes = [MeetingRoomPermission]

    def get_queryset(self):
        from rest_framework.exceptions import ValidationError

        user = self.request.user
        queryset = MeetingRoom.objects.all()

        # 1. Bảo mật phòng nội bộ (is_public=False)
        # Chỉ Admin hoặc người có quyền change_phonghop mới thấy phòng nội bộ
        can_manage = user.is_superuser or user.has_perm("change_phonghop")
        is_public_param = self.request.query_params.get("is_public")
        if is_public_param is not None and is_public_param != "":
            val = str(is_public_param).strip().lower()
            if val in ["true", "1"]:
                queryset = queryset.filter(is_public=True)
            elif val in ["false", "0"]:
                if can_manage:
                    queryset = queryset.filter(is_public=False)
                else:
                    queryset = queryset.none()
        elif not can_manage:
            queryset = queryset.filter(is_public=True)

        # 2. Lọc theo trạng thái trang_thai (chống 500 DataError trên PostgreSQL ENUM)
        trang_thai_param = self.request.query_params.get("trang_thai")
        if trang_thai_param:
            valid_values = [choice[0] for choice in MeetingRoom.Status.choices]
            cleaned_value = trang_thai_param.upper()
            if cleaned_value not in valid_values:
                raise ValidationError({
                    "trang_thai": "meetings.messages.invalidStatus"
                })
            queryset = queryset.filter(trang_thai=cleaned_value)

        # Tìm kiếm theo từ khóa (name, location, amenities, ghi_chu)
        search = self.request.query_params.get("search", "").strip()
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(location__icontains=search)
                | Q(amenities__icontains=search)
                | Q(ghi_chu__icontains=search)
            )

        # Sắp xếp
        ordering = self.request.query_params.get("ordering", "name")
        valid_orderings = [
            "name",
            "-name",
            "capacity",
            "-capacity",
            "created_at",
            "-created_at",
        ]
        if ordering in valid_orderings:
            queryset = queryset.order_by(ordering)
        else:
            queryset = queryset.order_by("name")

        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        # Hỗ trợ all=true để lấy toàn bộ danh sách không phân trang (cho dropdown)
        if request.query_params.get("all", "").lower() == "true":
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        """
        Xóa phòng họp an toàn. Chặn xóa nếu có dữ liệu liên kết.
        """
        try:
            return super().destroy(request, *args, **kwargs)
        except (ProtectedError, RestrictedError):
            return Response(
                {
                    "detail": "meetings.messages.cannotDeleteRoomHasBookings",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )


class IsOwnerOrAdminForBooking(permissions.BasePermission):
    """
    Quyền truy cập đặt lịch phòng họp theo chuẩn RBAC Issue #21 & DDL:
    - Xem danh sách / chi tiết: Cần quyền 'view_schedule_phonghop' hoặc is_superuser
    - Tạo mới (POST): Cần quyền 'add_datphonghop' hoặc is_superuser
    - Sửa / Hủy / Xóa:
      * Nếu là người đặt: cần quyền 'change_own_datphonghop' hoặc is_superuser
      * Nếu là người khác: cần quyền 'change_any_datphonghop' hoặc is_superuser
    (Bỏ hoàn toàn bypass is_staff, chỉ giữ is_superuser)
    """
    message = "meetings.messages.permissionDenied"

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        if request.method in permissions.SAFE_METHODS:
            return user.has_perm("view_schedule_phonghop")
        if request.method == "POST" and getattr(view, "action", None) != "cancel":
            return user.has_perm("add_datphonghop")
        return True

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_superuser:
            return True
        if request.method in permissions.SAFE_METHODS:
            return user.has_perm("view_schedule_phonghop")
        is_owner = obj.organizer_id == user.id
        if is_owner:
            return user.has_perm("change_own_datphonghop")
        return user.has_perm("change_any_datphonghop")


class MeetingBookingViewSet(viewsets.ModelViewSet):
    """
    API ViewSet quản lý Đặt lịch phòng họp:
    - GET /api/meeting-bookings/ : Danh sách lịch đặt (hỗ trợ lọc theo date, room, trang_thai)
    - POST /api/meeting-bookings/ : Tạo lịch đặt mới (Database Lock chống race condition)
    - GET /api/meeting-bookings/{id}/ : Chi tiết lịch đặt
    - PUT/PATCH /api/meeting-bookings/{id}/ : Cập nhật lịch đặt
    - DELETE /api/meeting-bookings/{id}/ : Xóa lịch đặt
    - POST /api/meeting-bookings/{id}/cancel/ : Hủy lịch giải phóng khung giờ
    """

    queryset = MeetingBooking.objects.select_related("room", "organizer", "department").all()
    serializer_class = MeetingBookingSerializer
    permission_classes = [IsOwnerOrAdminForBooking]
    pagination_class = StandardPagination

    def get_queryset(self):
        from rest_framework.exceptions import ValidationError

        qs = super().get_queryset().order_by("-date", "-start_time")

        # Bảo mật phòng nội bộ: Người không có change_phonghop chỉ thấy lịch phòng công khai hoặc lịch của mình
        user = self.request.user
        can_manage_private = user.is_authenticated and (user.is_superuser or user.has_perm("change_phonghop"))
        if not can_manage_private:
            if user.is_authenticated:
                qs = qs.filter(Q(room__is_public=True) | Q(organizer=user))
            else:
                qs = qs.filter(room__is_public=True)

        # 1. Lọc theo phòng họp an toàn (chống ValueError 500 khi room không phải số)
        room_param = self.request.query_params.get("room")
        if room_param:
            try:
                valid_room_id = int(room_param)
                qs = qs.filter(room_id=valid_room_id)
            except (ValueError, TypeError):
                raise ValidationError({
                    "room": "meetings.messages.invalidRoomId"
                })

        # 2. Lọc theo trạng thái an toàn (chống 500 DataError trên PostgreSQL ENUM)
        trang_thai_param = self.request.query_params.get("trang_thai")
        if trang_thai_param:
            mapped_status = str(trang_thai_param).upper()
            valid_values = [choice[0] for choice in MeetingBooking.Status.choices]
            if mapped_status not in valid_values:
                raise ValidationError({
                    "trang_thai": "meetings.messages.invalidStatus"
                })

            now_local = timezone.localtime(timezone.now())
            today = now_local.date()
            now_time = now_local.time()

            if mapped_status == MeetingBooking.Status.COMPLETED:
                qs = qs.filter(
                    Q(trang_thai=MeetingBooking.Status.COMPLETED)
                    | (
                        Q(trang_thai=MeetingBooking.Status.CONFIRMED)
                        & (Q(date__lt=today) | (Q(date=today) & Q(end_time__lte=now_time)))
                    )
                )
            elif mapped_status == MeetingBooking.Status.CONFIRMED:
                qs = qs.filter(
                    trang_thai=MeetingBooking.Status.CONFIRMED
                ).filter(
                    Q(date__gt=today) | (Q(date=today) & Q(end_time__gt=now_time))
                )
            else:
                qs = qs.filter(trang_thai=mapped_status)

        # 3. Lọc theo ngày cụ thể (YYYY-MM-DD) an toàn
        date_str = self.request.query_params.get("date")
        if date_str:
            try:
                target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                qs = qs.filter(date=target_date).order_by("start_time")
            except ValueError:
                raise ValidationError({
                    "date": "meetings.messages.invalidDateFormat"
                })

        # 4. Lọc theo khoảng ngày (start_date, end_date) an toàn
        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")
        if start_date:
            try:
                sd = datetime.strptime(start_date, "%Y-%m-%d").date()
                qs = qs.filter(date__gte=sd)
            except ValueError:
                raise ValidationError({
                    "start_date": "meetings.messages.invalidDateFormat"
                })
        if end_date:
            try:
                ed = datetime.strptime(end_date, "%Y-%m-%d").date()
                qs = qs.filter(date__lte=ed)
            except ValueError:
                raise ValidationError({
                    "end_date": "meetings.messages.invalidDateFormat"
                })

        return qs

    def create(self, request, *args, **kwargs):
        """
        Tạo lịch đặt phòng với Database Lock và chống race condition.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        room = serializer.validated_data["room"]
        booking_date = serializer.validated_data["date"]
        start = serializer.validated_data["start_time"]
        end = serializer.validated_data["end_time"]

        try:
            with transaction.atomic():
                # Khóa bản ghi phòng họp để các request đồng thời phải tuần tự kiểm tra
                locked_room = MeetingRoom.objects.select_for_update().get(id=room.id)

                if locked_room.trang_thai in [MeetingRoom.Status.MAINTENANCE, MeetingRoom.Status.UNAVAILABLE]:
                    return Response(
                        {
                            "detail": "meetings.messages.roomUnavailable",
                            "params": {
                                "room_name": locked_room.name,
                                "room_trang_thai": locked_room.trang_thai,
                            },
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                conflicts = MeetingBooking.objects.filter(
                    room=locked_room,
                    date=booking_date,
                    start_time__lt=end,
                    end_time__gt=start,
                ).exclude(trang_thai=MeetingBooking.Status.CANCELLED)

                if conflicts.exists():
                    conflict = conflicts.first()
                    organizer = conflict.organizer
                    host = getattr(organizer, "ho_ten", None) or organizer.get_full_name() or organizer.username
                    c_start = conflict.start_time.strftime("%H:%M")
                    c_end = conflict.end_time.strftime("%H:%M")
                    c_date = conflict.date.strftime("%d/%m/%Y")
                    return Response(
                        {
                            "detail": "meetings.messages.roomTimeConflict",
                            "params": {
                                "room_name": locked_room.name,
                                "conflict_title": conflict.title,
                                "start_time": c_start,
                                "end_time": c_end,
                                "date": c_date,
                                "organizer": host,
                            },
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                self.perform_create(serializer)

        except IntegrityError:
            # Bắt lỗi ràng buộc chống trùng cấp CSDL (PostgreSQL GiST excl_room_time)
            return Response(
                {
                    "detail": "meetings.messages.roomTimeConflict",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        serializer.save(organizer=self.request.user)

    def update(self, request, *args, **kwargs):
        """
        Cập nhật lịch đặt phòng với Database Lock và chống race condition.
        """
        partial = kwargs.pop("partial", False)
        instance = self.get_object()

        # Không cho phép cập nhật lịch đã kết thúc trong quá khứ
        if instance.effective_status == MeetingBooking.Status.COMPLETED:
            return Response(
                {
                    "detail": "meetings.messages.bookingAlreadyEnded",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Không cho phép cập nhật lịch đã bị hủy
        if instance.trang_thai == MeetingBooking.Status.CANCELLED:
            return Response(
                {
                    "detail": "meetings.messages.bookingAlreadyCancelled",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        room = serializer.validated_data.get("room", instance.room)
        booking_date = serializer.validated_data.get("date", instance.date)
        start = serializer.validated_data.get("start_time", instance.start_time)
        end = serializer.validated_data.get("end_time", instance.end_time)
        new_status = serializer.validated_data.get("trang_thai", instance.trang_thai)

        try:
            with transaction.atomic():
                locked_room = MeetingRoom.objects.select_for_update().get(id=room.id)

                if new_status != MeetingBooking.Status.CANCELLED:
                    if locked_room.trang_thai in [MeetingRoom.Status.MAINTENANCE, MeetingRoom.Status.UNAVAILABLE]:
                        return Response(
                            {
                                "detail": "meetings.messages.roomUnavailable",
                                "params": {
                                    "room_name": locked_room.name,
                                    "room_trang_thai": locked_room.trang_thai,
                                },
                            },
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                    conflicts = MeetingBooking.objects.filter(
                        room=locked_room,
                        date=booking_date,
                        start_time__lt=end,
                        end_time__gt=start,
                    ).exclude(trang_thai=MeetingBooking.Status.CANCELLED).exclude(pk=instance.pk)

                    if conflicts.exists():
                        conflict = conflicts.first()
                        organizer = conflict.organizer
                        host = getattr(organizer, "ho_ten", None) or organizer.get_full_name() or organizer.username
                        c_start = conflict.start_time.strftime("%H:%M")
                        c_end = conflict.end_time.strftime("%H:%M")
                        c_date = conflict.date.strftime("%d/%m/%Y")
                        return Response(
                            {
                                "detail": "meetings.messages.roomTimeConflict",
                                "params": {
                                    "room_name": locked_room.name,
                                    "conflict_title": conflict.title,
                                    "start_time": c_start,
                                    "end_time": c_end,
                                    "date": c_date,
                                    "organizer": host,
                                },
                            },
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                self.perform_update(serializer)

        except IntegrityError:
            return Response(
                {
                    "detail": "meetings.messages.roomTimeConflict",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        """
        Chặn xóa cứng lịch đặt phòng qua API (Issue #22: hủy lịch vẫn bảo toàn lịch sử).
        """
        return Response(
            {
                "detail": "meetings.messages.deleteBookingNotAllowed",
            },
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        """
        Hủy lịch đặt phòng họp: giải phóng khung giờ nhưng vẫn giữ lại bản ghi lịch sử.
        """
        booking = self.get_object()

        # Không cho phép hủy lịch đã hoàn thành / kết thúc trong quá khứ
        if booking.effective_status == MeetingBooking.Status.COMPLETED:
            return Response(
                {
                    "detail": "meetings.messages.bookingAlreadyEnded",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if booking.trang_thai == MeetingBooking.Status.CANCELLED:
            return Response(
                {
                    "detail": "meetings.messages.bookingAlreadyCancelled",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        booking.trang_thai = MeetingBooking.Status.CANCELLED
        reason = (request.data.get("cancel_reason") or "").strip()
        if reason:
            booking.purpose = f"{booking.purpose}\n---\n{reason}" if booking.purpose else f"\n---\n{reason}"
        booking.save()

        serializer = self.get_serializer(booking)
        return Response(
            {
                "detail": "meetings.messages.cancelSuccess",
                "booking": serializer.data,
            },
            status=status.HTTP_200_OK,
        )
