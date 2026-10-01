from django.contrib.auth import get_user_model
from rest_framework import serializers

from . import enums
from .models import SigningKey, SigningKeyUnlock, SigningProcess, SigningProcessStep, SigningProcessStepSigner


# ── Đầu vào: quy trình ───────────────────────────────────────────────────────


class NguoiKyInputSerializer(serializers.Serializer):
    thu_tu = serializers.IntegerField(min_value=0)
    nguoi_ky = serializers.PrimaryKeyRelatedField(
        queryset=get_user_model().objects.filter(is_active=True), required=False, allow_null=True
    )
    chuc_vu_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    vai_tro_ky = serializers.ChoiceField(choices=enums.VaiTroKy.choices, default=enums.VaiTroKy.KY_CHINH)
    chan_ky_chinh = serializers.BooleanField(default=True)


class CapKyInputSerializer(serializers.Serializer):
    cap_ky = serializers.IntegerField(min_value=0)
    ten_cap_ky = serializers.CharField(max_length=255)
    thu_tu = serializers.IntegerField(min_value=0)
    don_vi_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    so_gio_xu_ly = serializers.IntegerField(min_value=0, required=False, allow_null=True)
    ghi_chu = serializers.CharField(required=False, allow_blank=True, default="")
    nguoi_ky = NguoiKyInputSerializer(many=True, required=False)


class QuyTrinhInputSerializer(serializers.Serializer):
    ma_quy_trinh = serializers.CharField(max_length=50)
    ten_quy_trinh = serializers.CharField(max_length=255)
    mo_ta = serializers.CharField(required=False, allow_blank=True, default="")
    pham_vi = serializers.ChoiceField(choices=enums.PhamViQuyTrinh.choices)
    kieu_ky_mac_dinh = serializers.ChoiceField(choices=enums.KieuKy.choices)
    cau_hinh_nhac_han = serializers.JSONField(required=False, allow_null=True)
    cap_ky = CapKyInputSerializer(many=True, required=False)


# ── Đầu ra: quy trình ────────────────────────────────────────────────────────


class NguoiKyCauHinhSerializer(serializers.ModelSerializer):
    class Meta:
        model = SigningProcessStepSigner
        fields = ["id", "nguoi_ky", "chuc_vu_id", "vai_tro_ky", "chan_ky_chinh", "thu_tu"]


class CapKyQuyTrinhSerializer(serializers.ModelSerializer):
    nguoi_ky = NguoiKyCauHinhSerializer(source="nguoi_ky_set", many=True, read_only=True)

    class Meta:
        model = SigningProcessStep
        fields = ["id", "cap_ky", "ten_cap_ky", "thu_tu", "don_vi_id", "so_gio_xu_ly",
                  "dang_ap_dung", "ghi_chu", "nguoi_ky"]


class QuyTrinhSerializer(serializers.ModelSerializer):
    cap_ky = CapKyQuyTrinhSerializer(source="cap_ky_set", many=True, read_only=True)

    class Meta:
        model = SigningProcess
        fields = ["id", "ma_quy_trinh", "ten_quy_trinh", "mo_ta", "phien_ban", "trang_thai", "pham_vi",
                  "kieu_ky_mac_dinh", "cau_hinh_nhac_han", "create_by", "created_at", "update_by",
                  "update_at", "cap_ky"]


# ── Khóa ký ──────────────────────────────────────────────────────────────────


class KhoaDangKySerializer(serializers.Serializer):
    ma_khoa = serializers.CharField(max_length=100)
    khoa_cong_khai = serializers.CharField()
    ngay_hieu_luc = serializers.DateTimeField()
    ngay_het_han = serializers.DateTimeField(required=False, allow_null=True)
    ghi_chu = serializers.CharField(required=False, allow_blank=True, default="")


class XacMinhSoHuuSerializer(serializers.Serializer):
    chu_ky_so = serializers.CharField()


class ThuHoiKhoaSerializer(serializers.Serializer):
    ly_do = serializers.CharField()


class XoayVongSerializer(serializers.Serializer):
    khoa_moi = serializers.IntegerField(min_value=1)


class KhoaSerializer(serializers.ModelSerializer):
    da_dat_pin = serializers.SerializerMethodField()

    class Meta:
        model = SigningKey
        fields = ["id", "nguoi_so_huu", "ma_khoa", "dau_van_tay", "thuat_toan", "khoa_cong_khai",
                  "trang_thai", "thoi_diem_xac_minh_so_huu", "thoi_diem_kich_hoat", "ngay_hieu_luc",
                  "ngay_het_han", "ngay_thu_hoi", "khoa_thay_the", "ghi_chu", "created_at", "da_dat_pin"]
        read_only_fields = fields

    def get_da_dat_pin(self, obj):
        return SigningKeyUnlock.objects.filter(khoa=obj).exists()


# ── PIN mở khóa ký (Phase 6) ─────────────────────────────────────────────────
# xac_minh_pin = Base64 của verifier 32 byte do client dẫn xuất; server không nhận PIN.


class DatPinSerializer(serializers.Serializer):
    xac_minh_pin = serializers.CharField()
    tham_so_kdf = serializers.JSONField()


class MoKhoaKySerializer(serializers.Serializer):
    xac_minh_pin = serializers.CharField()


class DoiPinSerializer(serializers.Serializer):
    xac_minh_pin_cu = serializers.CharField()
    xac_minh_pin_moi = serializers.CharField()
    tham_so_kdf = serializers.JSONField()
