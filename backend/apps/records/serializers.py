from django.db.models.functions import Lower, Trim
from rest_framework import serializers

from .models import HoSo, LoaiVanBan


DATE_INPUT_FORMATS = ["iso-8601", "%Y-%m-%d"]


def get_user_display_name(user):
    if user is None:
        return None

    full_name_method = getattr(user, "get_full_name", None)
    if callable(full_name_method):
        full_name = full_name_method().strip()
        if full_name:
            return full_name

    for attribute in ("ho_ten", "full_name", "username"):
        value = getattr(user, attribute, None)
        if isinstance(value, str) and value.strip():
            return value.strip()

    return str(user)


class HoSoSerializer(serializers.ModelSerializer):
    nguoi_lap = serializers.SerializerMethodField()

    stt_uu_tien = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=1,
    )
    so_ky_hieu = serializers.CharField(max_length=255, validators=[])
    ngay_lap = serializers.DateTimeField(
        required=False,
        allow_null=True,
        input_formats=DATE_INPUT_FORMATS,
    )
    ghi_chu = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    class Meta:
        model = HoSo
        fields = [
            "id",
            "stt_uu_tien",
            "so_ky_hieu",
            "ten_ho_so",
            "nguoi_lap",
            "ngay_lap",
            "ghi_chu",
            "is_he_thong",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "nguoi_lap",
            "is_he_thong",
            "created_at",
            "updated_at",
        ]

    def get_nguoi_lap(self, obj):
        return get_user_display_name(obj.nguoi_lap)

    def validate_stt_uu_tien(self, value):
        if value is None:
            return value

        queryset = HoSo.objects.filter(stt_uu_tien=value)
        if self.instance is not None:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError(
                "Số thứ tự ưu tiên đã được sử dụng."
            )

        return value

    def validate_so_ky_hieu(self, value):
        normalized = value.strip()
        if not normalized:
            raise serializers.ValidationError(
                "Số ký hiệu không được để trống."
            )

        queryset = HoSo.objects.filter(so_ky_hieu=normalized)
        if self.instance is not None:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError(
                "Số ký hiệu đã tồn tại."
            )

        return normalized

    def validate_ten_ho_so(self, value):
        normalized = value.strip()
        if not normalized:
            raise serializers.ValidationError(
                "Tên hồ sơ không được để trống."
            )
        return normalized

    def create(self, validated_data):
        if validated_data.get("stt_uu_tien") is None:
            validated_data.pop("stt_uu_tien", None)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if validated_data.get("stt_uu_tien") is None:
            validated_data.pop("stt_uu_tien", None)
        return super().update(instance, validated_data)


class LoaiVanBanSerializer(serializers.ModelSerializer):
    ho_so = serializers.PrimaryKeyRelatedField(read_only=True)
    ten_ho_so = serializers.CharField(source="ho_so.ten_ho_so", read_only=True)

    ngay_lap = serializers.DateTimeField(
        required=False,
        allow_null=True,
        input_formats=DATE_INPUT_FORMATS,
    )
    ghi_chu = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    class Meta:
        model = LoaiVanBan
        fields = [
            "id",
            "ho_so",
            "ten_ho_so",
            "ten_loai",
            "ngay_lap",
            "ghi_chu",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "ho_so",
            "ten_ho_so",
            "created_at",
            "updated_at",
        ]

    def validate_ten_loai(self, value):
        normalized = value.strip()
        if not normalized:
            raise serializers.ValidationError(
                "Tên loại văn bản không được để trống."
            )
        return normalized

    def validate(self, attrs):
        attrs = super().validate(attrs)

        dossier = self.context.get("dossier")
        if dossier is None and self.instance is not None:
            dossier = self.instance.ho_so

        name = attrs.get(
            "ten_loai",
            getattr(self.instance, "ten_loai", None),
        )

        if dossier is not None and name:
            queryset = (
                LoaiVanBan.objects
                .filter(ho_so=dossier)
                .annotate(normalized_name=Lower(Trim("ten_loai")))
                .filter(normalized_name=name.strip().lower())
            )

            if self.instance is not None:
                queryset = queryset.exclude(pk=self.instance.pk)

            if queryset.exists():
                raise serializers.ValidationError(
                    {
                        "ten_loai": (
                            "Tên loại văn bản đã tồn tại trong hồ sơ này."
                        )
                    }
                )

        return attrs
