"""
Models cho phân hệ Phòng họp (Issue #22 - Nhóm 7).
Chuẩn hóa 100% theo DDL cơ sở dữ liệu release_DDL.sql (SQL_Fix4, Issue #53).

- MeetingRoom (bảng meetings_meetingroom): Danh mục phòng họp.
- MeetingBooking (bảng meetings_meetingbooking): Lịch đặt phòng họp & giữ chỗ.
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q
from django.db.models.functions import Now
from django.utils import timezone


class DbNow(Now):
    """DEFAULT now() như release_DDL.sql (Now() của Django sinh STATEMENT_TIMESTAMP() trên PostgreSQL)."""

    def as_postgresql(self, compiler, connection, **extra_context):
        return self.as_sql(compiler, connection, template="now()", **extra_context)


class MeetingRoom(models.Model):
    """
    Model đại diện cho danh mục phòng họp — bảng meetings_meetingroom theo SQL_Fix4.
    """

    class Status(models.TextChoices):
        AVAILABLE = "AVAILABLE", "Sẵn sàng"
        MAINTENANCE = "MAINTENANCE", "Bảo trì"
        UNAVAILABLE = "UNAVAILABLE", "Không khả dụng"

    name = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        verbose_name="Tên phòng họp",
        help_text="Tên nhận diện phòng họp (duy nhất)",
    )
    location = models.CharField(
        max_length=200,
        verbose_name="Vị trí",
        help_text="Tầng, tòa nhà hoặc khu vực",
    )
    capacity = models.IntegerField(
        default=10,
        validators=[MinValueValidator(1, message="Sức chứa phòng họp phải từ 1 người trở lên.")],
        verbose_name="Sức chứa (người)",
        help_text="Số lượng người tham gia tối đa",
    )
    amenities = models.TextField(
        null=True,
        blank=True,
        default="",
        verbose_name="Trang thiết bị",
        help_text="Mô tả thiết bị có sẵn (Máy chiếu, Micro, Hội nghị truyền hình...)",
    )
    is_public = models.BooleanField(
        default=True,
        db_default=True,
        verbose_name="Hiển thị công khai",
        help_text="Hiển thị công khai cho CBNV đặt (nếu False chỉ Admin/Lễ tân thấy)",
    )
    trang_thai = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.AVAILABLE,
        db_default=Status.AVAILABLE,
        verbose_name="Trạng thái phòng",
    )
    ghi_chu = models.TextField(
        null=True,
        blank=True,
        default="",
        verbose_name="Ghi chú",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_default=DbNow(),
        verbose_name="Ngày tạo",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        db_default=DbNow(),
        verbose_name="Cập nhật lần cuối",
    )

    class Meta:
        db_table = "meetings_meetingroom"
        verbose_name = "Phòng họp"
        verbose_name_plural = "Danh mục phòng họp"
        ordering = ["name", "id"]
        constraints = [
            models.CheckConstraint(condition=Q(capacity__gt=0), name="meetings_meetingroom_capacity_check"),
        ]
        default_permissions = ()
        permissions = [
            ("view_schedule_phonghop", "Xem lịch phòng họp"),
            ("add_phonghop", "Thêm phòng họp"),
            ("change_phonghop", "Sửa phòng họp"),
            ("delete_phonghop", "Xóa phòng họp"),
        ]

    def __str__(self):
        return f"{self.name} ({self.capacity} chỗ)"

    def clean(self):
        if self.capacity is not None and self.capacity <= 0:
            raise ValidationError({"capacity": "Sức chứa phòng họp phải lớn hơn 0."})


class MeetingBooking(models.Model):
    """
    Lịch đặt phòng họp & giữ chỗ khung giờ — bảng meetings_meetingbooking theo SQL_Fix4.
    """

    class Status(models.TextChoices):
        CONFIRMED = "CONFIRMED", "Đã xác nhận"
        CANCELLED = "CANCELLED", "Đã hủy"
        COMPLETED = "COMPLETED", "Đã hoàn thành"

    room = models.ForeignKey(
        MeetingRoom,
        on_delete=models.RESTRICT,
        db_index=False,
        related_name="bookings",
        verbose_name="Phòng họp",
    )
    organizer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.RESTRICT,
        db_index=False,
        related_name="meeting_bookings",
        verbose_name="Người đặt",
    )
    department = models.ForeignKey(
        "organizations.DonVi",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_index=False,
        related_name="meeting_bookings",
        verbose_name="Đơn vị tổ chức",
    )
    title = models.CharField(
        max_length=255,
        verbose_name="Tiêu đề cuộc họp / Nội dung",
    )
    date = models.DateField(
        verbose_name="Ngày họp",
    )
    start_time = models.TimeField(
        verbose_name="Giờ bắt đầu",
    )
    end_time = models.TimeField(
        verbose_name="Giờ kết thúc",
    )
    attendees_count = models.IntegerField(
        default=1,
        db_default=1,
        validators=[MinValueValidator(1, message="Số người tham gia phải lớn hơn 0.")],
        verbose_name="Số người tham gia",
    )
    purpose = models.TextField(
        null=True,
        blank=True,
        default="",
        verbose_name="Mục đích cuộc họp / Ghi chú",
    )
    trang_thai = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.CONFIRMED,
        db_default=Status.CONFIRMED,
        verbose_name="Trạng thái",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_default=DbNow(),
        verbose_name="Ngày tạo",
    )

    class Meta:
        db_table = "meetings_meetingbooking"
        verbose_name = "Lịch đặt phòng họp"
        verbose_name_plural = "Danh sách đặt phòng họp"
        ordering = ["-date", "-start_time", "-id"]
        indexes = [
            models.Index(fields=["room", "date"], name="idx_booking_room_date"),
        ]
        # Ràng buộc chống trùng giờ excl_room_time (EXCLUDE USING gist) chỉ có trên PostgreSQL,
        # được tạo trong migration 0002_align_release_ddl.
        constraints = [
            models.CheckConstraint(
                condition=Q(attendees_count__gt=0), name="meetings_meetingbooking_attendees_count_check"
            ),
            models.CheckConstraint(condition=Q(end_time__gt=F("start_time")), name="chk_booking_time"),
        ]
        default_permissions = ()
        permissions = [
            ("add_datphonghop", "Đặt phòng họp"),
            ("change_own_datphonghop", "Sửa/Hủy lịch do chính mình đặt"),
            ("change_any_datphonghop", "Sửa/Hủy mọi lịch đặt phòng (QT)"),
        ]

    def __str__(self):
        return f"[{self.room.name}] {self.title} ({self.date:%d/%m/%Y} {self.start_time:%H:%M} - {self.end_time:%H:%M})"

    @property
    def effective_status(self):
        """
        Tính trạng thái hiển thị động:
        Nếu lịch CONFIRMED nhưng thời điểm kết thúc đã qua thì hiển thị COMPLETED.
        """
        if self.trang_thai == self.Status.CONFIRMED and self.date and self.end_time:
            now_local = timezone.localtime(timezone.now())
            today = now_local.date()
            now_time = now_local.time()
            if self.date < today or (self.date == today and self.end_time <= now_time):
                return self.Status.COMPLETED
        return self.trang_thai

    def clean(self):
        super().clean()
        if self.start_time and self.end_time:
            if self.end_time <= self.start_time:
                raise ValidationError({
                    "end_time": "Giờ kết thúc phải diễn ra sau giờ bắt đầu."
                })

        if self.attendees_count is not None and self.attendees_count <= 0:
            raise ValidationError({
                "attendees_count": "Số người tham gia phải lớn hơn 0."
            })

        # Kiểm tra trạng thái phòng họp: MAINTENANCE hoặc UNAVAILABLE không cho đặt
        room = getattr(self, "room", None)
        if room:
            if room.trang_thai in [MeetingRoom.Status.MAINTENANCE, MeetingRoom.Status.UNAVAILABLE]:
                raise ValidationError({
                    "room": f"Phòng họp '{room.name}' đang ở trạng thái {room.get_trang_thai_display()}, không thể đặt lịch."
                })
            if self.attendees_count and self.attendees_count > room.capacity:
                raise ValidationError({
                    "attendees_count": f"Số người tham gia ({self.attendees_count}) vượt quá sức chứa tối đa của phòng ({room.capacity})."
                })

        # Kiểm tra trùng lịch đối với lịch có hiệu lực (khác CANCELLED)
        if self.trang_thai != self.Status.CANCELLED and self.room_id and self.date and self.start_time and self.end_time:
            conflicts = MeetingBooking.objects.filter(
                room_id=self.room_id,
                date=self.date,
                start_time__lt=self.end_time,
                end_time__gt=self.start_time,
            ).exclude(trang_thai=self.Status.CANCELLED)

            if self.pk:
                conflicts = conflicts.exclude(pk=self.pk)

            if conflicts.exists():
                conflict = conflicts.first()
                organizer = conflict.organizer
                host_name = getattr(organizer, "ho_ten", None) or organizer.get_full_name() or organizer.username
                c_start = conflict.start_time.strftime("%H:%M")
                c_end = conflict.end_time.strftime("%H:%M")
                c_date = conflict.date.strftime("%d/%m/%Y")
                raise ValidationError({
                    "non_field_errors": f"Khung giờ này đã bị trùng với cuộc họp '{conflict.title}' ({c_start} - {c_end} ngày {c_date}) bởi {host_name}."
                })
