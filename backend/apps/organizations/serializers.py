import re
from django.db import IntegrityError, OperationalError, transaction
from django.db.models import Max
from rest_framework import serializers

from .models import PHONE_PATTERN, KhoiKhuVuc, DonVi, normalize_phone

# Cột INTEGER của DDL (thu_tu_hien_thi, stt_uu_tien)
INT_MAX = 2147483647


class KhoiKhuVucSerializer(serializers.ModelSerializer):
    """
    Serializer handling Tier-1 Region/Block data using pure translation keys.
    """
    don_vi_count = serializers.IntegerField(
        source="don_vi_list.count",
        read_only=True,
    )
    ten = serializers.CharField(
        max_length=255,
        error_messages={
            "blank": "organizations.messages.nameRequired",
            "required": "organizations.messages.nameRequired",
            "max_length": "organizations.messages.nameTooLong",
        }
    )
    thu_tu_hien_thi = serializers.IntegerField(
        required=False,
        min_value=0,
        max_value=INT_MAX,
        error_messages={
            "invalid": "organizations.messages.displayOrderInvalid",
            "min_value": "organizations.messages.displayOrderInvalid",
            "max_value": "organizations.messages.displayOrderInvalid",
        },
    )

    class Meta:
        model = KhoiKhuVuc
        fields = ["id", "ten", "thu_tu_hien_thi", "don_vi_count"]
        read_only_fields = ["id"]

    def validate_ten(self, value):
        ten_stripped = value.strip()
        if not ten_stripped:
            raise serializers.ValidationError("organizations.messages.nameRequired")
        instance = self.instance
        qs = KhoiKhuVuc.objects.filter(ten__iexact=ten_stripped)
        if instance:
            qs = qs.exclude(pk=instance.pk)
        if qs.exists():
            raise serializers.ValidationError("organizations.messages.nameExists")
        return ten_stripped

    def create(self, validated_data):
        # Khối mới không nhập thứ tự hiển thị thì xếp cuối danh sách (MAX + 1), không nhận 0 lên đầu.
        if validated_data.get("thu_tu_hien_thi") is None:
            max_order = KhoiKhuVuc.objects.aggregate(max_val=Max("thu_tu_hien_thi"))["max_val"]
            validated_data["thu_tu_hien_thi"] = (max_order or 0) + 1
        return super().create(validated_data)


class DonViSerializer(serializers.ModelSerializer):
    """
    Serializer handling Tier-2 Unit/Department data using pure translation keys.
    """
    khoi_ten = serializers.CharField(
        source="khoi.ten",
        read_only=True,
    )
    khoi = serializers.PrimaryKeyRelatedField(
        queryset=KhoiKhuVuc.objects.all(),
        error_messages={
            "required": "organizations.messages.regionRequired",
            "null": "organizations.messages.regionRequired",
            "does_not_exist": "organizations.messages.regionNotFound",
            "incorrect_type": "organizations.messages.regionNotFound",
        },
    )
    stt_uu_tien = serializers.IntegerField(
        required=False,
        allow_null=True,
        max_value=INT_MAX,
        error_messages={
            "invalid": "organizations.messages.priorityPositive",
            "max_value": "organizations.messages.priorityTooLarge",
        },
    )
    ten = serializers.CharField(
        max_length=255,
        error_messages={
            "blank": "organizations.messages.nameRequired",
            "required": "organizations.messages.nameRequired",
            "max_length": "organizations.messages.nameTooLong",
        },
    )
    dia_chi = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        allow_null=True,
        error_messages={"max_length": "organizations.messages.addressTooLong"},
    )
    dien_thoai = serializers.CharField(
        max_length=20,
        required=False,
        allow_blank=True,
        allow_null=True,
        error_messages={"max_length": "organizations.messages.phoneInvalid"},
    )
    ghi_chu = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    email = serializers.EmailField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=254,
        error_messages={
            "max_length": "organizations.messages.emailInvalid",
            "invalid": "organizations.messages.emailInvalid",
        },
    )

    class Meta:
        model = DonVi
        fields = [
            "id",
            "khoi",
            "khoi_ten",
            "stt_uu_tien",
            "ten",
            "dia_chi",
            "dien_thoai",
            "email",
            "is_public",
            "ghi_chu",
        ]
        read_only_fields = ["id"]

    def validate_ten(self, value):
        ten_stripped = value.strip()
        if not ten_stripped:
            raise serializers.ValidationError("organizations.messages.nameRequired")
        return ten_stripped

    def validate_dien_thoai(self, value):
        if not value:
            return ""
        if not re.fullmatch(PHONE_PATTERN, normalize_phone(value)):
            raise serializers.ValidationError("organizations.messages.phoneInvalid")
        return value.strip()

    def to_internal_value(self, data):
        # Chuyển đổi chuỗi rỗng từ form frontend thành None để kích hoạt tự động sinh STT
        if isinstance(data, dict) and data.get("stt_uu_tien") == "":
            data = data.copy()
            data["stt_uu_tien"] = None
        return super().to_internal_value(data)

    def validate_stt_uu_tien(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError("organizations.messages.priorityPositive")
        return value

    def validate(self, attrs):
        stt = attrs.get("stt_uu_tien")
        instance = self.instance

        # DDL không có UNIQUE (khoi_id, ten): trùng tên trong cùng khối chặn ở API, khác khối vẫn cho trùng
        # (dữ liệu thật có "Lãnh đạo khối" ở nhiều khối).
        khoi = attrs.get("khoi", instance.khoi if instance else None)
        ten = attrs.get("ten", instance.ten if instance else None)
        if khoi is not None and ten:
            same_name = DonVi.objects.filter(khoi=khoi, ten__iexact=ten.strip())
            if instance:
                same_name = same_name.exclude(pk=instance.pk)
            if same_name.exists():
                raise serializers.ValidationError({"ten": "organizations.messages.unitNameExists"})

        if stt is not None:
            qs = DonVi.objects.filter(stt_uu_tien=stt)
            if instance:
                qs = qs.exclude(pk=instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {"stt_uu_tien": "organizations.messages.priorityExists"}
                )

        return attrs

    def create(self, validated_data):
        if validated_data.get("stt_uu_tien") is not None:
            try:
                with transaction.atomic():
                    return super().create(validated_data)
            except IntegrityError as exc:
                raise serializers.ValidationError(
                    {"stt_uu_tien": "organizations.messages.priorityExists"}
                ) from exc

        for attempt in range(3):
            try:
                with transaction.atomic():
                    # Lock the current highest row before reading MAX on databases
                    # that support row-level locking. The retry also handles an
                    # empty table and backends where select_for_update is a no-op.
                    DonVi.objects.select_for_update().order_by(
                        "-stt_uu_tien"
                    ).first()
                    max_stt = DonVi.objects.aggregate(max_val=Max("stt_uu_tien"))["max_val"]
                    validated_data["stt_uu_tien"] = (max_stt or 0) + 1
                    return super().create(validated_data)
            except (IntegrityError, OperationalError) as exc:
                if isinstance(exc, OperationalError) and "locked" not in str(exc).lower():
                    raise
                if attempt == 2:
                    raise serializers.ValidationError(
                        {"stt_uu_tien": "organizations.messages.priorityConflict"}
                    ) from exc

        raise serializers.ValidationError(
            {"stt_uu_tien": "organizations.messages.priorityConflict"}
        )
