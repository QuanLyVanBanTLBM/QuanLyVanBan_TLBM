import re

from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework import serializers

from . import enums
from .errors import SigningError
from .models import (
    SigningAttempt, SigningAuditLog, SigningChangeMessage, SigningChangeThread, SigningKey, SigningKeyUnlock,
    SigningProcess, SigningProcessStep, SigningProcessStepSigner, SigningRequest, SigningRequestStep,
    SigningRequestStepSigner,
)
from .tich_hop import to_chuc
from .tich_hop.van_ban import mo_ta_ho_so


# Giới hạn độ dài văn bản nhập tay (cột TextField không giới hạn); giao diện đặt `maxLength` bằng các số này
MAX_TRICH_YEU = 1000
MAX_GHI_CHU = 2000
MAX_LY_DO = 2000
MAX_TIN_NHAN = 2000
MA_QUY_TRINH = re.compile(r"[A-Za-z0-9_.\-]+")
MAX_SO_GIO_XU_LY = 24 * 365  # một năm; lớn hơn thì tràn cột integer hoặc vượt phạm vi ngày giờ


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
    so_gio_xu_ly = serializers.IntegerField(min_value=0, max_value=MAX_SO_GIO_XU_LY, required=False, allow_null=True)
    ghi_chu = serializers.CharField(max_length=MAX_GHI_CHU, required=False, allow_blank=True, default="")
    nguoi_ky = NguoiKyInputSerializer(many=True, required=False)

    def validate_nguoi_ky(self, danh_sach):
        """Một người (hoặc một chức vụ cùng phạm vi) chỉ xuất hiện một lần trong cấp: trùng thì hồ sơ không gửi được."""
        da_co = set()
        for n in danh_sach:
            khoa = (("nguoi", n["nguoi_ky"].pk) if n.get("nguoi_ky") else ("chuc_vu", n.get("chuc_vu_id"), n.get("pham_vi_chuc_vu")))
            if khoa in da_co:
                raise SigningError(code="nguoi_ky_trung_trong_cap", detail="Người ký bị trùng trong cùng một cấp.")
            da_co.add(khoa)
        return danh_sach


class QuyTrinhInputSerializer(serializers.Serializer):
    ma_quy_trinh = serializers.CharField(max_length=50)
    ten_quy_trinh = serializers.CharField(max_length=255)
    mo_ta = serializers.CharField(max_length=MAX_GHI_CHU, required=False, allow_blank=True, default="")
    pham_vi = serializers.ChoiceField(choices=enums.PhamViQuyTrinh.choices)
    don_vi_ap_dung_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    cau_hinh_nhac_han = serializers.JSONField(required=False, allow_null=True)
    cap_ky = CapKyInputSerializer(many=True, required=False)

    def validate_ma_quy_trinh(self, ma):
        """Mã gồm chữ không dấu, số, `-`, `_`, `.`; khi sửa nháp (mã không đổi được) giữ nguyên mã đã có."""
        if not self.context.get("giu_ma_cu") and not MA_QUY_TRINH.fullmatch(ma):
            raise serializers.ValidationError("Chỉ gồm chữ không dấu, số, dấu gạch ngang, gạch dưới, dấu chấm.")
        return ma


# ── Đầu ra: quy trình ────────────────────────────────────────────────────────


class NguoiKyCauHinhSerializer(serializers.ModelSerializer):
    ten_nguoi_ky = serializers.SerializerMethodField()
    # Tên chức vụ theo Danh mục chức vụ của phân hệ CBNV (FK accounts_position)
    ten_chuc_vu = serializers.CharField(source="chuc_vu.name", read_only=True, default=None)

    class Meta:
        model = SigningProcessStepSigner
        fields = ["id", "nguoi_ky", "ten_nguoi_ky", "chuc_vu_id", "ten_chuc_vu", "pham_vi_chuc_vu", "vai_tro_ky",
                  "chan_ky_chinh", "thu_tu"]

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
    ten_don_vi_ap_dung = serializers.CharField(source="don_vi_ap_dung.ten", read_only=True, default=None)
    so_ho_so = serializers.SerializerMethodField()

    class Meta:
        model = SigningProcess
        fields = ["id", "ma_quy_trinh", "ten_quy_trinh", "mo_ta", "phien_ban", "trang_thai", "pham_vi",
                  "don_vi_ap_dung_id", "ten_don_vi_ap_dung", "cau_hinh_nhac_han", "create_by", "created_at",
                  "update_by", "update_at", "cap_ky", "so_ho_so"]

    def get_so_ho_so(self, obj):
        """Số hồ sơ trình ký (mọi trạng thái) dùng phiên bản quy trình này; còn hồ sơ thì không xóa được."""
        return SigningRequest.objects.filter(quy_trinh=obj).count()


# ── Khóa ký ──────────────────────────────────────────────────────────────────


class KhoaDangKySerializer(serializers.Serializer):
    ma_khoa = serializers.CharField(max_length=100)
    khoa_cong_khai = serializers.CharField()
    ngay_hieu_luc = serializers.DateTimeField()
    ngay_het_han = serializers.DateTimeField(required=False, allow_null=True)
    ghi_chu = serializers.CharField(max_length=MAX_GHI_CHU, required=False, allow_blank=True, default="")


class XacMinhSoHuuSerializer(serializers.Serializer):
    chu_ky_so = serializers.CharField()


class ThuHoiKhoaSerializer(serializers.Serializer):
    ly_do = serializers.CharField(max_length=MAX_LY_DO)


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
    """Văn bản trình ký: `van_ban_id` (văn bản đi, không bắt buộc) hoặc `trich_yeu_van_ban` (+ `so_hieu_van_ban`)
    nhập tay; service kiểm điều kiện "một trong hai"."""

    document_type = serializers.ChoiceField(choices=enums.LoaiVanBan.choices, required=False, allow_null=True)
    van_ban_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    so_hieu_van_ban = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    trich_yeu_van_ban = serializers.CharField(max_length=MAX_TRICH_YEU, required=False, allow_blank=True, default="")
    quy_trinh = serializers.PrimaryKeyRelatedField(queryset=SigningProcess.objects.all())
    han_chot = serializers.DateTimeField(required=False, allow_null=True)
    ghi_chu = serializers.CharField(max_length=MAX_GHI_CHU, required=False, allow_blank=True, default="")
    tep = serializers.FileField()


class TrinhKySuaSerializer(serializers.Serializer):
    han_chot = serializers.DateTimeField(required=False, allow_null=True)
    ghi_chu = serializers.CharField(max_length=MAX_GHI_CHU, required=False, allow_blank=True)
    so_hieu_van_ban = serializers.CharField(max_length=100, required=False, allow_blank=True)
    trich_yeu_van_ban = serializers.CharField(max_length=MAX_TRICH_YEU, required=False, allow_blank=True)
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
    ly_do = serializers.CharField(max_length=MAX_LY_DO, required=False, allow_blank=True, default="")


class UyQuyenSerializer(serializers.Serializer):
    dong_nguoi_ky = serializers.IntegerField(min_value=1)
    nguoi_nhan = serializers.IntegerField(min_value=1)
    ly_do_uy_quyen = serializers.CharField(max_length=MAX_LY_DO)


class TrinhLaiSerializer(serializers.Serializer):
    han_chot = serializers.DateTimeField(required=False, allow_null=True)


class NguoiKyLuotSerializer(serializers.ModelSerializer):
    chu_ky = serializers.SerializerMethodField()

    class Meta:
        model = SigningRequestStepSigner
        fields = ["id", "nguoi_ky", "ten_nguoi_ky", "ten_chuc_vu", "vai_tro_ky", "chan_ky_chinh", "trang_thai",
                  "thoi_diem_mo", "ngay_ky", "ngay_tu_choi", "ly_do_tu_choi", "uy_quyen_tu", "ten_nguoi_uy_quyen",
                  "ly_do_uy_quyen", "ngay_uy_quyen", "trang_ky", "toa_do_x", "toa_do_y", "chieu_rong_khung",
                  "chieu_cao_khung", "chu_ky"]

    ten_nguoi_uy_quyen = serializers.SerializerMethodField()

    def get_ten_nguoi_uy_quyen(self, obj):
        return to_chuc.ten_hien_thi(obj.uy_quyen_tu) if obj.uy_quyen_tu_id else None

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
    ten_nguoi_viet = serializers.SerializerMethodField()

    class Meta:
        model = SigningChangeMessage
        fields = ["id", "nguoi_viet", "ten_nguoi_viet", "noi_dung", "created_at"]
        read_only_fields = ["id", "nguoi_viet", "ten_nguoi_viet", "created_at"]

    def get_ten_nguoi_viet(self, obj):
        return to_chuc.ten_hien_thi(obj.nguoi_viet)


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
    ten_nguoi_thuc_hien = serializers.SerializerMethodField()

    class Meta:
        model = SigningAuditLog
        fields = ["id", "hanh_dong", "nguoi_thuc_hien", "ten_nguoi_thuc_hien", "trang_thai_truoc", "trang_thai_sau",
                  "chi_tiet", "luot_trinh", "created_at"]

    def get_ten_nguoi_thuc_hien(self, obj):
        return to_chuc.ten_hien_thi(obj.nguoi_thuc_hien)


class TrinhKySerializer(serializers.ModelSerializer):
    ma_quy_trinh = serializers.CharField(source="quy_trinh.ma_quy_trinh", read_only=True)
    ten_quy_trinh = serializers.CharField(source="quy_trinh.ten_quy_trinh", read_only=True)
    ten_nguoi_tao = serializers.SerializerMethodField()
    van_ban = serializers.SerializerMethodField()
    dang_cho = serializers.SerializerMethodField()

    class Meta:
        model = SigningRequest
        fields = ["id", "document_type", "van_ban_id", "so_hieu_van_ban", "trich_yeu_van_ban", "van_ban", "quy_trinh", "ma_quy_trinh", "ten_quy_trinh",
                  "phien_ban_quy_trinh", "trang_thai", "han_chot", "ngay_gui", "ngay_hoan_thanh",
                  "ngay_tu_choi", "ly_do_tu_choi", "ngay_huy", "ly_do_huy", "ghi_chu", "ho_so_goc",
                  "phien_ban_van_ban", "ma_bam_tai_lieu", "create_by", "ten_nguoi_tao", "created_at", "update_at",
                  "dang_cho", "trang_thai_luot", "qua_han", "qua_han_cap", "han_xu_ly_cap"]
        read_only_fields = fields

    trang_thai_luot = serializers.SerializerMethodField()
    qua_han = serializers.SerializerMethodField()
    qua_han_cap = serializers.SerializerMethodField()
    han_xu_ly_cap = serializers.SerializerMethodField()

    def get_trang_thai_luot(self, obj):
        """Trạng thái lượt trình hiện hành (YEU_CAU_SUA: hồ sơ đang trả lại để sửa dù hồ sơ vẫn CHO_KY)."""
        return obj.luot_trinh_set.order_by("-so_luot").values_list("trang_thai", flat=True).first()

    def get_qua_han(self, obj):
        """Hồ sơ chờ ký đã qua hạn chót, hoặc có cấp đang ký đã qua hạn xử lý (cùng điều kiện thẻ lọc "quá hạn")."""
        if obj.trang_thai != enums.TrangThaiYeuCau.CHO_KY:
            return False
        bay_gio = timezone.now()
        return bool(obj.han_chot and obj.han_chot < bay_gio) or SigningRequestStep.objects.filter(
            luot_trinh__trinh_ky=obj, trang_thai=enums.TrangThaiCapKy.DANG_KY, han_xu_ly__lt=bay_gio).exists()

    def get_qua_han_cap(self, obj):
        """Chỉ trễ hạn ở cấp ký đang mở (hạn chót tổng thể của hồ sơ chưa qua hoặc không có)."""
        if obj.trang_thai != enums.TrangThaiYeuCau.CHO_KY:
            return False
        bay_gio = timezone.now()
        if obj.han_chot and obj.han_chot < bay_gio:
            return False
        return SigningRequestStep.objects.filter(
            luot_trinh__trinh_ky=obj, trang_thai=enums.TrangThaiCapKy.DANG_KY, han_xu_ly__lt=bay_gio).exists()

    def get_han_xu_ly_cap(self, obj):
        """Hạn xử lý của cấp ký đang mở hiện hành (nếu có)."""
        if obj.trang_thai != enums.TrangThaiYeuCau.CHO_KY:
            return None
        return SigningRequestStep.objects.filter(
            luot_trinh__trinh_ky=obj, trang_thai=enums.TrangThaiCapKy.DANG_KY
        ).values_list("han_xu_ly", flat=True).first()

    def get_ten_nguoi_tao(self, obj):
        return to_chuc.ten_hien_thi(obj.create_by)

    def get_van_ban(self, obj):
        """Số hiệu, trích yếu của văn bản trình ký: văn bản đi (đọc qua lớp tích hợp Nhóm 2; rỗng khi chưa đọc được)
        hoặc nội dung nhập tay."""
        return mo_ta_ho_so(obj)

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
        return NhatKyTrinhKySerializer(SigningAuditLog.objects.filter(trinh_ky=obj).select_related("nguoi_thuc_hien")
                                       .order_by("id"), many=True).data


# ── Hành động người ký (Phase 8, #80) ────────────────────────────────────────


class KySerializer(serializers.Serializer):
    khoa_ky = serializers.IntegerField(min_value=1)
    hash_tai_lieu = serializers.RegexField(r"^[0-9a-f]{64}$")
    chu_ky_so = serializers.CharField(max_length=200)  # Ed25519 Base64 là 88 ký tự
    ghi_chu_ky = serializers.CharField(max_length=MAX_GHI_CHU, required=False, allow_blank=True, default="")


class TuChoiSerializer(serializers.Serializer):
    ly_do_tu_choi = serializers.CharField(max_length=MAX_LY_DO)


class YeuCauSuaSerializer(serializers.Serializer):
    tieu_de = serializers.CharField(max_length=255)
    ly_do = serializers.CharField(max_length=MAX_LY_DO)


class TinNhanInputSerializer(serializers.Serializer):
    noi_dung = serializers.CharField(max_length=MAX_TIN_NHAN)


class GiaiQuyetSerializer(serializers.Serializer):
    tep = serializers.FileField()
    # {id dòng người ký của lượt hiện hành: khung ký}; bỏ trống thì giữ vị trí của lượt trước
    vi_tri_ky = ViTriKyJSONField(required=False, default=dict)

