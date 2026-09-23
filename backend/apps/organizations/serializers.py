"""
Serializers cho phân hệ Cơ cấu Tổ chức & Đơn vị (Module 7.3 - Nhóm 7).
Tác giả: Lê Duy Khánh.
"""
from rest_framework import serializers
from .models import KhoiKhuVuc, DonVi


class KhoiKhuVucSerializer(serializers.ModelSerializer):
    """
    Serializer cho Khối / Khu vực (Cấp 1).
    """
    don_vi_count = serializers.IntegerField(source="don_vi_list.count", read_only=True)

    class Meta:
        model = KhoiKhuVuc
        fields = [
            "id",
            "ten",
            "thu_tu_hien_thi",
            "don_vi_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "don_vi_count"]

    def validate_ten(self, value):
        trimmed = value.strip()
        if not trimmed:
            raise serializers.ValidationError("Tên khối/khu vực không được để trống hoặc chỉ chứa khoảng trắng.")
        return trimmed


class DonViSerializer(serializers.ModelSerializer):
    """
    Serializer cho Đơn vị / Phòng ban (Cấp 2).
    """
    khoi_id = serializers.PrimaryKeyRelatedField(
        queryset=KhoiKhuVuc.objects.all(),
        source="khoi",
        write_only=True,
        required=True,
        help_text="ID của Khối/Khu vực trực thuộc.",
    )
    khoi_ten = serializers.CharField(source="khoi.ten", read_only=True)
    stt_uu_tien = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=1,
        help_text="Số thứ tự ưu tiên. Nếu không truyền, hệ thống tự động tăng.",
    )

    class Meta:
        model = DonVi
        fields = [
            "id",
            "khoi_id",
            "khoi_ten",
            "stt_uu_tien",
            "ten",
            "dia_chi",
            "dien_thoai",
            "email",
            "is_public",
            "ghi_chu",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "khoi_ten", "created_at", "updated_at"]

    def validate_ten(self, value):
        trimmed = value.strip()
        if not trimmed:
            raise serializers.ValidationError("Tên đơn vị, phòng/ban không được để trống hoặc chỉ chứa khoảng trắng.")
        return trimmed

    def validate_stt_uu_tien(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError("STT ưu tiên hiển thị phải là số nguyên dương lớn hơn 0.")
        return value

    def validate(self, attrs):
        stt = attrs.get("stt_uu_tien")
        instance = getattr(self, "instance", None)

        if stt is not None:
            # Kiểm tra trùng stt_uu_tien (loại trừ chính bản ghi đang cập nhật)
            query = DonVi.objects.filter(stt_uu_tien=stt)
            if instance:
                query = query.exclude(pk=instance.pk)
            if query.exists():
                raise serializers.ValidationError({
                    "stt_uu_tien": f"STT ưu tiên {stt} đã tồn tại trong hệ thống. Vui lòng chọn số khác."
                })
        return attrs

    def create(self, validated_data):
        if "stt_uu_tien" not in validated_data or validated_data["stt_uu_tien"] is None:
            validated_data["stt_uu_tien"] = DonVi.get_next_stt()
        return super().create(validated_data)
