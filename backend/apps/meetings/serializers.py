"""
Serializers cho phân hệ Phòng họp (Issue #22 - Nhóm 7).
Chuẩn hóa 100% theo DDL cơ sở dữ liệu release_DDL.sql (SQL_Fix4, Issue #53).
Tên field API trùng tên cột DDL, không dùng bí danh.
"""

from datetime import datetime
from django.utils import timezone
from rest_framework import serializers

from meetings.models import MeetingRoom, MeetingBooking
from organizations.models import DonVi


class MeetingRoomSerializer(serializers.ModelSerializer):
    """
    Serializer CRUD cho Danh mục phòng họp (MeetingRoom / meetings_meetingroom).
    """

    name = serializers.CharField(
        max_length=100,
        required=False,
        error_messages={
            "max_length": "meetings.messages.roomNameTooLong",
        },
    )
    location = serializers.CharField(
        max_length=200,
        required=False,
        allow_blank=True,
        default="",
        error_messages={
            "max_length": "meetings.messages.locationTooLong",
        },
    )
    capacity = serializers.IntegerField(
        min_value=1,
        max_value=2147483647,
        required=False,
        default=10,
        error_messages={
            "invalid": "meetings.messages.capacityMustBeInteger",
            "min_value": "meetings.messages.capacityMustBePositive",
            "max_value": "meetings.messages.capacityTooLarge",
        },
    )
    amenities = serializers.CharField(required=False, allow_blank=True, default="")
    is_public = serializers.BooleanField(required=False)
    trang_thai = serializers.ChoiceField(
        choices=MeetingRoom.Status.choices,
        required=False,
        error_messages={
            "invalid_choice": "meetings.messages.invalidStatus",
        },
    )
    ghi_chu = serializers.CharField(required=False, allow_blank=True, default="")

    class Meta:
        model = MeetingRoom
        fields = [
            "id",
            "name",
            "location",
            "capacity",
            "amenities",
            "is_public",
            "trang_thai",
            "ghi_chu",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def create(self, validated_data):
        if "trang_thai" not in validated_data:
            validated_data["trang_thai"] = MeetingRoom.Status.AVAILABLE
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if "trang_thai" not in validated_data:
            validated_data["trang_thai"] = instance.trang_thai
        return super().update(instance, validated_data)

    def to_internal_value(self, data):
        if hasattr(data, "dict"):
            d = data.dict()
        elif hasattr(data, "copy"):
            d = data.copy()
        else:
            d = dict(data)

        if "location" not in d and not self.partial and not self.instance:
            d["location"] = ""
        if "trang_thai" not in d:
            if self.instance:
                d["trang_thai"] = self.instance.trang_thai
            elif not self.partial:
                d["trang_thai"] = MeetingRoom.Status.AVAILABLE

        return super().to_internal_value(d)

    def validate(self, attrs):
        name = attrs.get("name")
        if not name and not self.instance:
            raise serializers.ValidationError({
                "name": "meetings.messages.roomNameRequired",
            })

        if name is not None:
            cleaned_name = str(name).strip()
            if not cleaned_name:
                raise serializers.ValidationError({
                    "name": "meetings.messages.roomNameRequired",
                })
            if len(cleaned_name) > 100:
                raise serializers.ValidationError({
                    "name": "meetings.messages.roomNameTooLong",
                })
            qs = MeetingRoom.objects.filter(name__iexact=cleaned_name)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError({
                    "name": "meetings.messages.roomNameExists",
                })
            attrs["name"] = cleaned_name

        capacity = attrs.get("capacity")
        if capacity is not None:
            if capacity < 1:
                raise serializers.ValidationError({
                    "capacity": "meetings.messages.capacityMustBePositive",
                })
            if capacity > 2147483647:
                raise serializers.ValidationError({
                    "capacity": "meetings.messages.capacityTooLarge",
                })

        return attrs


class UserSimpleSerializer(serializers.Serializer):
    """
    Thông tin rút gọn của người đặt phòng (accounts_employee), cùng tên field với API CBNV.
    """

    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(read_only=True)
    ho_ten = serializers.CharField(read_only=True)
    don_vi_ten = serializers.CharField(source="don_vi.ten", read_only=True, default="")
    chuc_vu_ten = serializers.SerializerMethodField()

    def get_chuc_vu_ten(self, obj):
        chuc_vu = getattr(obj, "chuc_vu", None)
        if chuc_vu and getattr(chuc_vu, "name", None):
            return chuc_vu.name
        return getattr(obj, "chuc_danh", "") or ""


class MeetingBookingSerializer(serializers.ModelSerializer):
    """
    Serializer CRUD & Validation cho Lịch đặt phòng họp (MeetingBooking / meetings_meetingbooking).
    """

    room = serializers.PrimaryKeyRelatedField(
        queryset=MeetingRoom.objects.all(),
        required=False,
        error_messages={
            "does_not_exist": "meetings.messages.roomNotFound",
            "incorrect_type": "meetings.messages.invalidRoomId",
        },
    )
    title = serializers.CharField(
        max_length=255,
        required=True,
        allow_blank=False,
        error_messages={
            "required": "meetings.messages.titleRequired",
            "blank": "meetings.messages.titleRequired",
            "max_length": "meetings.messages.titleTooLong",
        },
    )
    date = serializers.DateField(
        required=False,
        error_messages={
            "invalid": "meetings.messages.invalidDateFormat",
        },
    )
    start_time = serializers.TimeField(required=False)
    end_time = serializers.TimeField(required=False)
    attendees_count = serializers.IntegerField(
        min_value=1,
        max_value=2147483647,
        required=False,
        default=1,
        error_messages={
            "invalid": "meetings.messages.attendeesMustBeInteger",
            "min_value": "meetings.messages.attendeesMustBePositive",
        },
    )
    purpose = serializers.CharField(required=False, allow_blank=True, default="")
    trang_thai = serializers.CharField(read_only=True)
    department = serializers.PrimaryKeyRelatedField(
        queryset=DonVi.objects.all(), required=False, allow_null=True
    )

    # Details
    room_detail = MeetingRoomSerializer(source="room", read_only=True)
    organizer_detail = UserSimpleSerializer(source="organizer", read_only=True)
    department_name = serializers.CharField(source="department.ten", read_only=True, default="")

    class Meta:
        model = MeetingBooking
        fields = [
            "id",
            "room",
            "room_detail",
            "organizer",
            "organizer_detail",
            "department",
            "department_name",
            "title",
            "date",
            "start_time",
            "end_time",
            "attendees_count",
            "purpose",
            "trang_thai",
            "created_at",
        ]
        read_only_fields = ["id", "organizer", "trang_thai", "created_at"]

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        # Trạng thái hiển thị động: lịch CONFIRMED đã qua giờ kết thúc trả về COMPLETED
        ret["trang_thai"] = instance.effective_status
        return ret

    def validate(self, attrs):
        room = attrs.get("room", getattr(self.instance, "room", None))
        booking_date = attrs.get("date", getattr(self.instance, "date", None))
        start_time = attrs.get("start_time", getattr(self.instance, "start_time", None))
        end_time = attrs.get("end_time", getattr(self.instance, "end_time", None))
        attendees = attrs.get("attendees_count", getattr(self.instance, "attendees_count", 1))
        status_val = attrs.get("trang_thai", getattr(self.instance, "trang_thai", MeetingBooking.Status.CONFIRMED))

        title_val = attrs.get("title")
        if not self.instance and not title_val:
            raise serializers.ValidationError({
                "title": "meetings.messages.titleRequired",
            })
        if title_val is not None and not str(title_val).strip():
            raise serializers.ValidationError({
                "title": "meetings.messages.titleRequired",
            })

        if not room and not self.instance:
            raise serializers.ValidationError({
                "room": "meetings.messages.roomRequired",
            })

        # Chặn đặt phòng nội bộ nếu user không có change_phonghop
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if room and not room.is_public:
            has_perm = user and (user.is_superuser or user.has_perm("change_phonghop"))
            if not has_perm:
                raise serializers.ValidationError({
                    "room": "meetings.messages.privateRoomForbidden",
                })

        if not booking_date and not self.instance:
            raise serializers.ValidationError({"date": "meetings.messages.dateRequired"})

        if not start_time and not self.instance:
            raise serializers.ValidationError({
                "start_time": "meetings.messages.startTimeRequired",
            })

        if not end_time and not self.instance:
            raise serializers.ValidationError({
                "end_time": "meetings.messages.endTimeRequired",
            })

        # Chặn đặt lịch trong quá khứ hoặc dời lịch về quá khứ
        now_local = timezone.localtime(timezone.now())
        if booking_date and start_time:
            booking_start_dt = datetime.combine(booking_date, start_time)
            tz = timezone.get_current_timezone()
            if timezone.is_naive(booking_start_dt):
                booking_start_dt = timezone.make_aware(booking_start_dt, tz)
            else:
                booking_start_dt = timezone.localtime(booking_start_dt)

            is_creating = not self.instance
            is_rescheduling = bool(
                self.instance
                and (
                    attrs.get("date", self.instance.date) != self.instance.date
                    or attrs.get("start_time", self.instance.start_time) != self.instance.start_time
                )
            )
            if (is_creating or is_rescheduling) and booking_start_dt < now_local:
                raise serializers.ValidationError({
                    "start_time": "meetings.messages.bookingInPast",
                })

        # Phòng MAINTENANCE hoặc UNAVAILABLE không cho đặt
        if room and room.trang_thai in [MeetingRoom.Status.MAINTENANCE, MeetingRoom.Status.UNAVAILABLE]:
            raise serializers.ValidationError({
                "room": "meetings.messages.roomUnavailable",
            })

        if start_time and end_time and end_time <= start_time:
            raise serializers.ValidationError({
                "end_time": "meetings.messages.invalidTimeRange",
            })

        if attendees is not None and attendees <= 0:
            raise serializers.ValidationError({
                "attendees_count": "meetings.messages.attendeesRequired",
            })

        if room and attendees is not None and attendees > room.capacity:
            raise serializers.ValidationError({
                "attendees_count": "meetings.messages.capacityExceeded",
            })

        # Kiểm tra chống trùng lịch
        if status_val != MeetingBooking.Status.CANCELLED and room and booking_date and start_time and end_time:
            conflicts = MeetingBooking.objects.filter(
                room=room,
                date=booking_date,
                start_time__lt=end_time,
                end_time__gt=start_time,
            ).exclude(trang_thai=MeetingBooking.Status.CANCELLED)

            if self.instance and self.instance.pk:
                conflicts = conflicts.exclude(pk=self.instance.pk)

            if conflicts.exists():
                raise serializers.ValidationError({
                    "non_field_errors": "meetings.messages.roomTimeConflict",
                })

        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        if request and hasattr(request, "user") and request.user.is_authenticated:
            validated_data.setdefault("organizer", request.user)
            # Tự động gán phòng ban nếu chưa chọn
            if not validated_data.get("department") and hasattr(request.user, "don_vi"):
                validated_data["department"] = request.user.don_vi
        validated_data["trang_thai"] = MeetingBooking.Status.CONFIRMED
        return super().create(validated_data)
