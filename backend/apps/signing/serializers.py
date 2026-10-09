from django.contrib.auth import get_user_model
from rest_framework import serializers

from . import enums
from .models import (
    SigningAttempt, SigningAuditLog, SigningChangeMessage, SigningChangeThread, SigningKey, SigningKeyUnlock,
    SigningProcess, SigningProcessStep, SigningProcessStepSigner, SigningRequest, SigningRequestStep,
    SigningRequestStepSigner,
)
from .tich_hop import to_chuc
from .tich_hop.van_ban import mo_ta_van_ban


# ── Đầu vào: quy trình ───────────────────────────────────────────────────────


class NguoiKyInputSerializer(serializers.Serializer):
    thu_tu = serializers.IntegerField(min_value=0)
    nguoi_ky = serializers.PrimaryKeyRelatedField(
        queryset=get_user_model().objects.filter(is_active=True), required=False, allow_null=True
    )
    chuc_vu_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    pham_vi_chuc_vu = serializers.ChoiceField(choices=enums.PhamViChucVu.choices, required=False, allow_null=True)
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
    don_vi_ap_dung_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    cau_hinh_nhac_han = serializers.JSONField(required=False, allow_null=True)
    cap_ky = CapKyInputSerializer(many=True, required=False)


# ── Đầu ra: quy trình ────────────────────────────────────────────────────────


class NguoiKyCauHinhSerializer(serializers.ModelSerializer):
    ten_nguoi_ky = serializers.SerializerMethodField()

    class Meta:
        model = SigningProcessStepSigner
        fields = ["id", "nguoi_ky", "ten_nguoi_ky", "chuc_vu_id", "pham_vi_chuc_vu", "vai_tro_ky", "chan_ky_chinh",
                  "thu_tu"]

    def get_ten_nguoi_ky(self, obj):
        """Tên để xem trước người ký trước khi gửi (UI); người ký theo chức vụ được xác định lúc gửi."""
        return to_chuc.ten_hien_thi(obj.nguoi_ky) if obj.nguoi_ky_id else None


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
                  "don_vi_ap_dung_id", "cau_hinh_nhac_han", "create_by", "created_at", "update_by",
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


# ── Hồ sơ trình ký (Phase 7, #80) ────────────────────────────────────────────
# Không trả `vi_tri_luu_tep` (đường dẫn nội bộ); tệp tải qua API có kiểm quyền.


class TrinhKyTaoSerializer(serializers.Serializer):
    document_type = serializers.ChoiceField(choices=enums.LoaiVanBan.choices)
    van_ban_id = serializers.IntegerField(min_value=1)
    quy_trinh = serializers.PrimaryKeyRelatedField(queryset=SigningProcess.objects.all())
    muc_do = serializers.ChoiceField(choices=enums.MucDoTrinhKy.choices)
    han_chot = serializers.DateTimeField(required=False, allow_null=True)
    ghi_chu = serializers.CharField(required=False, allow_blank=True, default="")
    tep = serializers.FileField()


class TrinhKySuaSerializer(serializers.Serializer):
    muc_do = serializers.ChoiceField(choices=enums.MucDoTrinhKy.choices, required=False)
    han_chot = serializers.DateTimeField(required=False, allow_null=True)
    ghi_chu = serializers.CharField(required=False, allow_blank=True)
    tep = serializers.FileField(required=False)


class ViTriKySerializer(serializers.Serializer):
    """Khung ký theo tỷ lệ % của trang, gốc góc trên-trái (plan mục 3.2); khung phải nằm trọn trong trang."""

    trang_ky = serializers.IntegerField(min_value=1)
    toa_do_x = serializers.DecimalField(max_digits=7, decimal_places=4, min_value=0, max_value=100)
    toa_do_y = serializers.DecimalField(max_digits=7, decimal_places=4, min_value=0, max_value=100)
    chieu_rong_khung = serializers.DecimalField(max_digits=7, decimal_places=4, min_value=1, max_value=100)
    chieu_cao_khung = serializers.DecimalField(max_digits=7, decimal_places=4, min_value=1, max_value=100)

    def validate(self, attrs):
        if attrs["toa_do_x"] + attrs["chieu_rong_khung"] > 100 or attrs["toa_do_y"] + attrs["chieu_cao_khung"] > 100:
            raise serializers.ValidationError("Khung ký vượt ra ngoài trang.")
        return attrs


class ViTriKyJSONField(serializers.JSONField):
    """`vi_tri_ky` trong multipart (giải quyết yêu cầu sửa) gửi dạng chuỗi JSON."""

    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        if not isinstance(data, dict):
            raise serializers.ValidationError("Phải là object {id: vị trí}.")
        loi, ket_qua = {}, {}
        for khoa, gia_tri in data.items():
            vi_tri = ViTriKySerializer(data=gia_tri)
            if vi_tri.is_valid():
                ket_qua[str(khoa)] = vi_tri.validated_data
            else:
                loi[str(khoa)] = vi_tri.errors
        if loi:
            raise serializers.ValidationError(loi)
        return ket_qua


class GuiTrinhKySerializer(serializers.Serializer):
    # {id người ký cấu hình: id tài khoản được chọn} khi chức vụ có nhiều ứng viên
    chon_nguoi_ky = serializers.DictField(child=serializers.IntegerField(min_value=1), required=False, default=dict)
    # {id người ký cấu hình: khung ký} do người tạo đặt trên bản xem trước
    vi_tri_ky = ViTriKyJSONField(required=False, default=dict)


class HuyTrinhKySerializer(serializers.Serializer):
    ly_do = serializers.CharField(required=False, allow_blank=True, default="")


class TrinhLaiSerializer(serializers.Serializer):
    han_chot = serializers.DateTimeField(required=False, allow_null=True)


class NguoiKyLuotSerializer(serializers.ModelSerializer):
    chu_ky = serializers.SerializerMethodField()

    class Meta:
        model = SigningRequestStepSigner
        fields = ["id", "nguoi_ky", "ten_nguoi_ky", "ten_chuc_vu", "vai_tro_ky", "chan_ky_chinh", "trang_thai",
                  "thoi_diem_mo", "ngay_ky", "ngay_tu_choi", "ly_do_tu_choi", "uy_quyen_tu", "trang_ky", "toa_do_x",
                  "toa_do_y", "chieu_rong_khung", "chieu_cao_khung", "chu_ky"]

    def get_chu_ky(self, obj):
        """Chữ ký hiện hành (ghi chú, trễ hạn, kết quả xác minh, có ảnh snapshot); không trả nội dung chữ ký."""
        ck = obj.chu_ky_hien_hanh
        if ck is None:
            return None
        return {"id": ck.pk, "ngay_ky": ck.ngay_ky, "ghi_chu_ky": ck.ghi_chu_ky, "ky_tre_han": ck.ky_tre_han,
                "so_giay_tre": ck.so_giay_tre, "trang_thai_xac_minh": ck.trang_thai_xac_minh,
                "co_anh_chu_ky": bool(ck.vi_tri_anh_chu_ky)}


class CapLuotSerializer(serializers.ModelSerializer):
    nguoi_ky = NguoiKyLuotSerializer(source="nguoi_ky_set", many=True, read_only=True)

    class Meta:
        model = SigningRequestStep
        fields = ["id", "cap_ky", "ten_cap_ky", "thu_tu", "trang_thai", "han_xu_ly", "thoi_diem_mo",
                  "thoi_diem_hoan_thanh", "nguoi_ky"]


class YeuCauSuaThreadSerializer(serializers.ModelSerializer):
    class Meta:
        model = SigningChangeThread
        fields = ["id", "nguoi_yeu_cau", "tieu_de", "ly_do", "trang_thai", "created_at", "thoi_diem_giai_quyet"]


class TinNhanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SigningChangeMessage
        fields = ["id", "nguoi_viet", "noi_dung", "created_at"]
        read_only_fields = ["id", "nguoi_viet", "created_at"]


class LuotTrinhSerializer(serializers.ModelSerializer):
    cap_ky = CapLuotSerializer(source="cap_ky_set", many=True, read_only=True)
    yeu_cau_sua = YeuCauSuaThreadSerializer(source="yeu_cau_sua_set", many=True, read_only=True)
    ma_bam_bang_chung = serializers.SerializerMethodField()

    class Meta:
        model = SigningAttempt
        fields = ["id", "so_luot", "luot_truoc", "phien_ban_van_ban", "ma_bam_tai_lieu", "trang_thai", "ly_do",
                  "thoi_diem_gui", "thoi_diem_hoan_thanh", "thoi_diem_tu_choi", "thoi_diem_huy",
                  "trang_thai_tep_hoan_tat", "loi_tep_hoan_tat", "ma_bam_tep_hoan_tat", "ma_bam_bang_chung",
                  "cap_ky", "yeu_cau_sua"]

    def get_ma_bam_bang_chung(self, obj):
        manifest = obj.manifest_set.filter(trang_thai=enums.TrangThaiManifest.DA_CHOT).order_by("-id").first()
        return manifest.ma_bam_bang_chung if manifest else None


class NhatKyTrinhKySerializer(serializers.ModelSerializer):
    class Meta:
        model = SigningAuditLog
        fields = ["id", "hanh_dong", "nguoi_thuc_hien", "trang_thai_truoc", "trang_thai_sau", "chi_tiet",
                  "luot_trinh", "created_at"]


class TrinhKySerializer(serializers.ModelSerializer):
    ma_quy_trinh = serializers.CharField(source="quy_trinh.ma_quy_trinh", read_only=True)
    ten_quy_trinh = serializers.CharField(source="quy_trinh.ten_quy_trinh", read_only=True)
    ten_nguoi_tao = serializers.SerializerMethodField()
    van_ban = serializers.SerializerMethodField()
    dang_cho = serializers.SerializerMethodField()

    class Meta:
        model = SigningRequest
        fields = ["id", "document_type", "van_ban_id", "van_ban", "quy_trinh", "ma_quy_trinh", "ten_quy_trinh",
                  "phien_ban_quy_trinh", "muc_do", "trang_thai", "han_chot", "ngay_gui", "ngay_hoan_thanh",
                  "ngay_tu_choi", "ly_do_tu_choi", "ngay_huy", "ly_do_huy", "ghi_chu", "ho_so_goc",
                  "phien_ban_van_ban", "ma_bam_tai_lieu", "create_by", "ten_nguoi_tao", "created_at", "update_at",
                  "dang_cho"]
        read_only_fields = fields

    def get_ten_nguoi_tao(self, obj):
        return to_chuc.ten_hien_thi(obj.create_by)

    def get_van_ban(self, obj):
        """Số hiệu, trích yếu để hiển thị (đọc qua lớp tích hợp Nhóm 2; rỗng khi chưa đọc được)."""
        return mo_ta_van_ban(obj.document_type, obj.van_ban_id)

    def get_dang_cho(self, obj):
        """Người ký đang được mở và chờ ký trên lượt trình hiện hành."""
        if obj.trang_thai != enums.TrangThaiYeuCau.CHO_KY:
            return []
        return list(SigningRequestStepSigner.objects.filter(
            buoc_ky__luot_trinh__trinh_ky=obj, buoc_ky__luot_trinh__trang_thai=enums.TrangThaiLuotTrinh.CHO_KY,
            buoc_ky__trang_thai=enums.TrangThaiCapKy.DANG_KY, trang_thai=enums.TrangThaiNguoiKy.CHO_KY,
            thoi_diem_mo__isnull=False,
        ).values("id", "nguoi_ky", "ten_nguoi_ky", "vai_tro_ky"))


class TrinhKyChiTietSerializer(TrinhKySerializer):
    luot_trinh = serializers.SerializerMethodField()
    lich_su = serializers.SerializerMethodField()

    class Meta(TrinhKySerializer.Meta):
        fields = TrinhKySerializer.Meta.fields + ["luot_trinh", "lich_su"]
        read_only_fields = fields

    def get_luot_trinh(self, obj):
        luot = obj.luot_trinh_set.order_by("-so_luot").prefetch_related("cap_ky_set__nguoi_ky_set")
        return LuotTrinhSerializer(luot, many=True).data

    def get_lich_su(self, obj):
        return NhatKyTrinhKySerializer(SigningAuditLog.objects.filter(trinh_ky=obj).order_by("id"), many=True).data


# ── Hành động người ký (Phase 8, #80) ────────────────────────────────────────


class KySerializer(serializers.Serializer):
    khoa_ky = serializers.IntegerField(min_value=1)
    hash_tai_lieu = serializers.RegexField(r"^[0-9a-f]{64}$")
    chu_ky_so = serializers.CharField(max_length=200)  # Ed25519 Base64 là 88 ký tự
    ghi_chu_ky = serializers.CharField(required=False, allow_blank=True, default="")


class TuChoiSerializer(serializers.Serializer):
    ly_do_tu_choi = serializers.CharField()


class YeuCauSuaSerializer(serializers.Serializer):
    tieu_de = serializers.CharField(max_length=255)
    ly_do = serializers.CharField()


class TinNhanInputSerializer(serializers.Serializer):
    noi_dung = serializers.CharField()


class GiaiQuyetSerializer(serializers.Serializer):
    tep = serializers.FileField()
    # {id dòng người ký của lượt hiện hành: khung ký}; bỏ trống thì giữ vị trí của lượt trước
    vi_tri_ky = ViTriKyJSONField(required=False, default=dict)

