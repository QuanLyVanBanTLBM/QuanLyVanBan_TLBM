from rest_framework import serializers
from django.utils import timezone
from .models import PhongHop, DatPhongHop


class PhongHopSerializer(serializers.ModelSerializer):
    """
    Serializer cho danh mục phòng họp.
    """
    class Meta:
        model = PhongHop
        fields = [
            "id",
            "ten_phong",
            "vi_tri",
            "suc_chua",
            "thiet_bi",
            "is_public",
            "ghi_chu",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_suc_chua(self, value):
        if value <= 0:
            raise serializers.ValidationError("Sức chứa phòng họp phải lớn hơn 0.")
        return value

    def validate_ten_phong(self, value):
        val = value.strip()
        if not val:
            raise serializers.ValidationError("Tên phòng họp không được để trống.")
        return val


class UserSimpleSerializer(serializers.Serializer):
    """
    Thông tin rút gọn của người dùng/CBNV đặt phòng.
    """
    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(read_only=True)
    full_name = serializers.SerializerMethodField()
    department = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()

    def get_full_name(self, obj):
        if hasattr(obj, "profile") and obj.profile.full_name:
            return obj.profile.full_name
        return obj.get_full_name() or obj.username

    def get_department(self, obj):
        if hasattr(obj, "profile"):
            return obj.profile.department or ""
        return ""

    def get_role(self, obj):
        if hasattr(obj, "profile"):
            return obj.profile.role or "staff"
        return "admin" if obj.is_staff else "staff"


class DatPhongHopSerializer(serializers.ModelSerializer):
    """
    Serializer cho đặt lịch phòng họp.
    """
    nguoi_dat_detail = UserSimpleSerializer(source="nguoi_dat", read_only=True)
    phong_hop_detail = PhongHopSerializer(source="phong_hop", read_only=True)

    class Meta:
        model = DatPhongHop
        fields = [
            "id",
            "phong_hop",
            "phong_hop_detail",
            "nguoi_dat",
            "nguoi_dat_detail",
            "don_vi_to_chuc",
            "tieu_de",
            "thoi_gian_bat_dau",
            "thoi_gian_ket_thuc",
            "so_nguoi_tham_gia",
            "trang_thai",
            "ghi_chu",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "nguoi_dat", "created_at", "updated_at"]

    def validate(self, attrs):
        start = attrs.get("thoi_gian_bat_dau", getattr(self.instance, "thoi_gian_bat_dau", None))
        end = attrs.get("thoi_gian_ket_thuc", getattr(self.instance, "thoi_gian_ket_thuc", None))
        phong = attrs.get("phong_hop", getattr(self.instance, "phong_hop", None))
        status = attrs.get("trang_thai", getattr(self.instance, "trang_thai", DatPhongHop.STATUS_DA_DAT))
        so_nguoi = attrs.get("so_nguoi_tham_gia", getattr(self.instance, "so_nguoi_tham_gia", 1))

        if start and end and start >= end:
            raise serializers.ValidationError({
                "thoi_gian_ket_thuc": "Thời gian kết thúc phải diễn ra sau thời gian bắt đầu."
            })

        if so_nguoi <= 0:
            raise serializers.ValidationError({
                "so_nguoi_tham_gia": "Số người tham gia phải lớn hơn 0."
            })

        if phong and so_nguoi > phong.suc_chua:
            raise serializers.ValidationError({
                "so_nguoi_tham_gia": f"Số người tham gia ({so_nguoi}) vượt quá sức chứa của phòng '{phong.ten_phong}' ({phong.suc_chua} người)."
            })

        # Kiểm tra trùng lịch
        if status != DatPhongHop.STATUS_DA_HUY and phong and start and end:
            conflicts = DatPhongHop.objects.filter(
                phong_hop=phong,
                thoi_gian_bat_dau__lt=end,
                thoi_gian_ket_thuc__gt=start,
            ).exclude(trang_thai=DatPhongHop.STATUS_DA_HUY)

            if self.instance and self.instance.pk:
                conflicts = conflicts.exclude(pk=self.instance.pk)

            if conflicts.exists():
                conflict = conflicts.first()
                nguoi_dat_name = conflict.nguoi_dat.get_full_name() or conflict.nguoi_dat.username
                if hasattr(conflict.nguoi_dat, "profile") and conflict.nguoi_dat.profile.full_name:
                    nguoi_dat_name = conflict.nguoi_dat.profile.full_name

                tz = timezone.get_current_timezone()
                c_start = timezone.localtime(conflict.thoi_gian_bat_dau, tz).strftime("%H:%M")
                c_end = timezone.localtime(conflict.thoi_gian_ket_thuc, tz).strftime("%H:%M ngày %d/%m/%Y")
                raise serializers.ValidationError({
                    "non_field_errors": f"Phòng họp '{phong.ten_phong}' đã có lịch đặt: '{conflict.tieu_de}' ({c_start} - {c_end}) bởi {nguoi_dat_name}. Vui lòng chọn khung giờ khác!"
                })

        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        if request and hasattr(request, "user") and request.user.is_authenticated:
            validated_data["nguoi_dat"] = request.user
            # Nếu chưa điền đơn vị tổ chức, tự động lấy từ CBNV profile
            if not validated_data.get("don_vi_to_chuc"):
                if hasattr(request.user, "profile") and request.user.profile.department:
                    validated_data["don_vi_to_chuc"] = request.user.profile.department
        return super().create(validated_data)
