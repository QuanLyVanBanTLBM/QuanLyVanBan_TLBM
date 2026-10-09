"""
Serializers cho Module Văn Bản (Đến / Đi) — Kiến trúc 2 Model.

Hỗ trợ:
- Serializer riêng biệt cho từng phân hệ: VanBanDen, VanBanDi
- Serializer hợp nhất cho API facade (DocumentListSerializer, DocumentDetailSerializer, DocumentCreateUpdateSerializer)
- Serializer tệp đính kèm và lịch sử người xem
"""

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers

from .models import (
    HieuLuc,
    LoaiVanBan,
    PhamVi,
    VanBanDen,
    VanBanDenAttachment,
    VanBanDi,
    VanBanDiAttachment,
    DocumentViewLog,
    DocumentAccessLog,
    get_document_model,
)

User = get_user_model()


class TolerantPrimaryKeyRelatedField(serializers.PrimaryKeyRelatedField):
    """
    Bỏ qua an toàn các ID người dùng không tồn tại trong DB,
    tránh làm đứt gãy luồng thêm văn bản khi các nhóm khác chưa hoàn thiện dữ liệu CBNV.
    """

    def to_internal_value(self, data):
        try:
            return super().to_internal_value(data)
        except serializers.ValidationError:
            return None


# ═══════════════════════════════════════════════════════════════════
# Attachment Serializers
# ═══════════════════════════════════════════════════════════════════

class DocumentAttachmentSerializer(serializers.ModelSerializer):
    """Serializer dùng chung cho file đính kèm."""

    file_name = serializers.CharField(source="name", read_only=True)
    uploaded_at = serializers.DateTimeField(source="created_at", read_only=True)
    created_time = serializers.DateTimeField(source="created_at", read_only=True)

    class Meta:
        model = VanBanDenAttachment
        fields = ["id", "file", "name", "file_name", "path", "file_size", "is_deleted", "uploaded_at", "created_at", "created_time"]
        read_only_fields = ["id", "name", "file_name", "path", "file_size", "uploaded_at", "created_at", "created_time"]


class VanBanDenAttachmentSerializer(serializers.ModelSerializer):
    created_time = serializers.DateTimeField(source="created_at", read_only=True)

    class Meta:
        model = VanBanDenAttachment
        fields = ["id", "file", "name", "path", "file_size", "is_deleted", "created_at", "created_time"]
        read_only_fields = ["id", "name", "path", "file_size", "created_at", "created_time"]


class VanBanDiAttachmentSerializer(serializers.ModelSerializer):
    created_time = serializers.DateTimeField(source="created_at", read_only=True)

    class Meta:
        model = VanBanDiAttachment
        fields = ["id", "file", "name", "path", "file_size", "is_deleted", "created_at", "created_time"]
        read_only_fields = ["id", "name", "path", "file_size", "created_at", "created_time"]


# ═══════════════════════════════════════════════════════════════════
# Unified Document Serializers (GET list, GET detail, POST/PUT)
# ═══════════════════════════════════════════════════════════════════

class DocumentListSerializer(serializers.Serializer):
    """
    Serializer cho danh sách văn bản (GET list).
    Trả về định dạng chuẩn cho bảng hiển thị trên frontend.
    Hỗ trợ đồng nhất dữ liệu từ VanBanDen và VanBanDi.
    """

    id = serializers.IntegerField(read_only=True)
    loai = serializers.CharField(read_only=True)
    loai_display = serializers.SerializerMethodField()
    nam = serializers.IntegerField(read_only=True)
    so_hieu = serializers.CharField(read_only=True)
    so_thu_tu = serializers.IntegerField(read_only=True, default=None)
    ngay_den = serializers.DateTimeField(read_only=True, default=None)
    ngay_ban_hanh = serializers.DateTimeField(read_only=True, default=None)
    ngay_van_ban = serializers.DateTimeField(read_only=True, default=None)
    trich_yeu = serializers.CharField(read_only=True)
    noi_ban_hanh = serializers.CharField(read_only=True, default="")
    nguoi_ky = serializers.CharField(read_only=True, default="")
    hieu_luc = serializers.CharField(read_only=True)
    hieu_luc_display = serializers.CharField(source="get_hieu_luc_display", read_only=True)
    link_thay_the = serializers.SerializerMethodField()
    danh_sach_thay_the = serializers.SerializerMethodField()
    pham_vi = serializers.CharField(read_only=True, default="NOI_BO")
    pham_vi_display = serializers.SerializerMethodField()
    hien_thi = serializers.BooleanField(read_only=True)
    nguoi_tao_name = serializers.SerializerMethodField()
    attachment_count = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(read_only=True)

    def get_pham_vi_display(self, obj):
        pv = getattr(obj, "pham_vi", "NOI_BO")
        return "Hạn chế" if pv == "HAN_CHE" else "Nội bộ"

    def get_danh_sach_thay_the(self, obj):
        from .services import get_dynamic_replacements
        return get_dynamic_replacements(obj)

    def get_link_thay_the(self, obj):
        from .services import get_dynamic_replacements
        reps = get_dynamic_replacements(obj)
        return ", ".join(reps) if reps else (getattr(obj, "link_thay_the", "") or "")

    def get_loai_display(self, obj):
        if hasattr(obj, "get_loai_display"):
            return obj.get_loai_display()
        loai = getattr(obj, "loai", "DEN")
        return dict(LoaiVanBan.choices).get(loai, loai)

    def get_nguoi_tao_name(self, obj):
        if hasattr(obj, "nguoi_tao") and obj.nguoi_tao:
            full_name = obj.nguoi_tao.get_full_name()
            return full_name if full_name else obj.nguoi_tao.username
        return None

    def get_attachment_count(self, obj):
        if hasattr(obj, "attachments"):
            return obj.attachments.count()
        return 0


class DocumentDetailSerializer(serializers.Serializer):
    """
    Serializer cho chi tiết văn bản (GET detail).
    Đầy đủ mọi trường + danh sách file đính kèm.
    """

    id = serializers.IntegerField(read_only=True)
    loai = serializers.CharField(read_only=True)
    loai_display = serializers.SerializerMethodField()
    nam = serializers.IntegerField(read_only=True)
    so_hieu = serializers.CharField(read_only=True)
    so_thu_tu = serializers.IntegerField(read_only=True, default=None)
    ngay_den = serializers.DateTimeField(read_only=True, default=None)
    ngay_ban_hanh = serializers.DateTimeField(read_only=True, default=None)
    ngay_van_ban = serializers.DateTimeField(read_only=True, default=None)
    trich_yeu = serializers.CharField(read_only=True)
    noi_ban_hanh = serializers.CharField(read_only=True, default="")
    nguoi_ky = serializers.CharField(read_only=True, default="")
    chuc_vu = serializers.CharField(read_only=True, default="")
    hieu_luc = serializers.CharField(read_only=True)
    hieu_luc_display = serializers.CharField(source="get_hieu_luc_display", read_only=True)
    ngay_het_hieu_luc = serializers.DateTimeField(read_only=True, default=None)
    link_thay_the = serializers.SerializerMethodField()
    danh_sach_thay_the = serializers.SerializerMethodField()
    pham_vi = serializers.CharField(read_only=True, default="NOI_BO")
    pham_vi_display = serializers.SerializerMethodField()
    ghi_chu = serializers.CharField(read_only=True, default="")
    hien_thi = serializers.BooleanField(read_only=True)
    gui_mail_toan_he_thong = serializers.BooleanField(read_only=True)
    attachments = serializers.SerializerMethodField()
    nguoi_tao_name = serializers.SerializerMethodField()
    nguoi_tao_username = serializers.CharField(source="nguoi_tao.username", read_only=True, default=None)
    nguoi_nhan_list = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    def get_pham_vi_display(self, obj):
        pv = getattr(obj, "pham_vi", "NOI_BO")
        return "Hạn chế" if pv == "HAN_CHE" else "Nội bộ"

    def get_danh_sach_thay_the(self, obj):
        from .services import get_dynamic_replacements
        return get_dynamic_replacements(obj)

    def get_link_thay_the(self, obj):
        from .services import get_dynamic_replacements
        reps = get_dynamic_replacements(obj)
        return ", ".join(reps) if reps else (getattr(obj, "link_thay_the", "") or "")

    def get_loai_display(self, obj):
        if hasattr(obj, "get_loai_display"):
            return obj.get_loai_display()
        loai = getattr(obj, "loai", "DEN")
        return dict(LoaiVanBan.choices).get(loai, loai)

    def get_attachments(self, obj):
        if hasattr(obj, "attachments"):
            return DocumentAttachmentSerializer(obj.attachments.filter(is_deleted=False), many=True).data
        return []

    def get_nguoi_tao_name(self, obj):
        if hasattr(obj, "nguoi_tao") and obj.nguoi_tao:
            full_name = obj.nguoi_tao.get_full_name()
            return full_name if full_name else obj.nguoi_tao.username
        return None

    def get_nguoi_nhan_list(self, obj):
        if hasattr(obj, "nguoi_nhan"):
            return [
                {
                    "id": u.pk,
                    "username": u.username,
                    "full_name": u.get_full_name() or u.username,
                }
                for u in obj.nguoi_nhan.all()
            ]
        return []


class DocumentCreateUpdateSerializer(serializers.Serializer):
    """
    Serializer cho tạo mới / cập nhật văn bản (POST, PUT, PATCH).
    Nhận dữ liệu từ request, validate nghiệp vụ, và lưu vào đúng model tương ứng
    (VanBanDen hoặc VanBanDi).
    """

    id = serializers.IntegerField(read_only=True)
    loai = serializers.ChoiceField(choices=LoaiVanBan.choices, default=LoaiVanBan.DEN)
    nam = serializers.IntegerField(required=False)
    so_hieu = serializers.CharField(max_length=255)
    so_thu_tu = serializers.IntegerField(read_only=True)
    ngay_den = serializers.DateTimeField(required=False, allow_null=True)
    ngay_ban_hanh = serializers.DateTimeField(required=False, allow_null=True)
    ngay_van_ban = serializers.DateTimeField(required=False, allow_null=True)
    trich_yeu = serializers.CharField()
    noi_ban_hanh = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")
    nguoi_ky = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    chuc_vu = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    hieu_luc = serializers.ChoiceField(choices=HieuLuc.choices, default=HieuLuc.CON_HIEU_LUC)
    ngay_het_hieu_luc = serializers.DateTimeField(required=False, allow_null=True)
    link_thay_the = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")
    ghi_chu = serializers.CharField(required=False, allow_blank=True, default="")
    pham_vi = serializers.ChoiceField(choices=PhamVi.choices, default=PhamVi.NOI_BO, required=False)
    hien_thi = serializers.BooleanField(default=True)
    gui_mail_toan_he_thong = serializers.BooleanField(default=False)
    nguoi_nhan = TolerantPrimaryKeyRelatedField(
        many=True,
        queryset=User.objects.all(),
        required=False,
    )

    def validate_nguoi_nhan(self, value):
        return [u for u in value if u is not None]

    def validate(self, attrs):
        loai = attrs.get("loai") or (getattr(self.instance, "loai", None) if self.instance else LoaiVanBan.DEN)

        if loai == LoaiVanBan.DI:
            if not attrs.get("ngay_ban_hanh") and not (
                self.instance and getattr(self.instance, "ngay_ban_hanh", None)
            ):
                raise serializers.ValidationError(
                    {"ngay_ban_hanh": "Ngày ban hành là bắt buộc với Văn bản Đi."}
                )

        # Lỗi 2 Sub-issue #61: HET_VA_THAY_THE bắt buộc link_thay_the khác rỗng sau strip()
        hieu_luc = attrs.get("hieu_luc") or (getattr(self.instance, "hieu_luc", None) if self.instance else None)
        link_thay_the = attrs.get("link_thay_the") if "link_thay_the" in attrs else (getattr(self.instance, "link_thay_the", "") if self.instance else "")
        if hieu_luc == HieuLuc.HET_VA_THAY_THE:
            if not link_thay_the or not str(link_thay_the).strip():
                raise serializers.ValidationError(
                    {"link_thay_the": "Văn bản hết hiệu lực và được thay thế bắt buộc phải có liên kết văn bản thay thế (link_thay_the)."}
                )

        # Issue #82: Quy tắc nghiệp vụ văn bản hạn chế (HAN_CHE)
        if self.instance and "pham_vi" in attrs and attrs["pham_vi"] != self.instance.pham_vi:
            raise serializers.ValidationError(
                {"pham_vi": "Phạm vi văn bản không được đổi sau khi tạo."}
            )

        pham_vi = attrs.get("pham_vi") or (getattr(self.instance, "pham_vi", PhamVi.NOI_BO) if self.instance else PhamVi.NOI_BO)
        if pham_vi == PhamVi.HAN_CHE:
            if attrs.get("gui_mail_toan_he_thong"):
                raise serializers.ValidationError(
                    {"gui_mail_toan_he_thong": "Văn bản hạn chế không được phép gửi email toàn hệ thống."}
                )

            # Bắt buộc có ít nhất 1 người nhận khi tạo mới
            if not self.instance:
                nguoi_nhan = attrs.get("nguoi_nhan", [])
                if not nguoi_nhan:
                    raise serializers.ValidationError(
                        {"nguoi_nhan": "Văn bản hạn chế bắt buộc phải có ít nhất một người nhận được chọn."}
                    )
            elif "nguoi_nhan" in attrs and not attrs["nguoi_nhan"]:
                raise serializers.ValidationError(
                    {"nguoi_nhan": "Văn bản hạn chế bắt buộc phải có ít nhất một người nhận được chọn."}
                )

        return attrs

    def create(self, validated_data):
        from .selectors import log_access

        nguoi_nhan = validated_data.pop("nguoi_nhan", [])
        loai = validated_data.pop("loai", LoaiVanBan.DEN)
        model = get_document_model(loai)

        # VB hạn chế không gửi mail toàn trường
        pham_vi = validated_data.get("pham_vi", PhamVi.NOI_BO)
        if pham_vi == PhamVi.HAN_CHE:
            validated_data["gui_mail_toan_he_thong"] = False

        if "so_thu_tu" not in validated_data or not validated_data["so_thu_tu"]:
            from .services import generate_so_thu_tu
            year = validated_data.get("nam") or timezone.now().year
            validated_data["so_thu_tu"] = generate_so_thu_tu(loai, year) or 1

        instance = model.objects.create(**validated_data)
        if nguoi_nhan:
            instance.nguoi_nhan.set(nguoi_nhan)

        # Ghi log THEM_NGUOI_XEM ban đầu cho văn bản hạn chế
        if getattr(instance, "pham_vi", None) == PhamVi.HAN_CHE:
            creator = validated_data.get("nguoi_tao") or getattr(instance, "nguoi_tao", None)
            for user_obj in nguoi_nhan:
                log_access(
                    document_type=getattr(instance, "document_kind", "vanbanden"),
                    document_id=instance.pk,
                    user=creator,
                    hanh_dong=DocumentAccessLog.HanhDong.THEM_NGUOI_XEM,
                    doi_tuong_user=user_obj,
                )

        if instance.link_thay_the:
            from .services import sync_replacement_document
            sync_replacement_document(instance)

        return instance

    def update(self, instance, validated_data):
        from .selectors import log_access

        nguoi_nhan = validated_data.pop("nguoi_nhan", None)
        validated_data.pop("loai", None)
        validated_data.pop("so_thu_tu", None)  # Read-only!

        if "pham_vi" in validated_data and validated_data["pham_vi"] != instance.pham_vi:
            raise serializers.ValidationError({"pham_vi": "Phạm vi văn bản không được đổi sau khi tạo."})

        if getattr(instance, "pham_vi", None) == PhamVi.HAN_CHE:
            validated_data["gui_mail_toan_he_thong"] = False

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if nguoi_nhan is not None:
            if getattr(instance, "pham_vi", None) == PhamVi.HAN_CHE:
                req = self.context.get("request")
                current_user = req.user if req else instance.nguoi_tao
                old_recipients = set(instance.nguoi_nhan.all())
                new_recipients = set(nguoi_nhan)

                added = new_recipients - old_recipients
                removed = old_recipients - new_recipients

                instance.nguoi_nhan.set(nguoi_nhan)

                for u in added:
                    log_access(
                        document_type=getattr(instance, "document_kind", "vanbanden"),
                        document_id=instance.pk,
                        user=current_user,
                        hanh_dong=DocumentAccessLog.HanhDong.THEM_NGUOI_XEM,
                        doi_tuong_user=u,
                    )
                for u in removed:
                    log_access(
                        document_type=getattr(instance, "document_kind", "vanbanden"),
                        document_id=instance.pk,
                        user=current_user,
                        hanh_dong=DocumentAccessLog.HanhDong.BOT_NGUOI_XEM,
                        doi_tuong_user=u,
                    )
            else:
                instance.nguoi_nhan.set(nguoi_nhan)

        if instance.link_thay_the:
            from .services import sync_replacement_document
            sync_replacement_document(instance)

        return instance


# ═══════════════════════════════════════════════════════════════════
# Dedicated Model Serializers
# ═══════════════════════════════════════════════════════════════════

def _validate_replacement_link(attrs, instance=None):
    hieu_luc = attrs.get("hieu_luc") or (getattr(instance, "hieu_luc", None) if instance else None)
    link_thay_the = attrs.get("link_thay_the") if "link_thay_the" in attrs else (getattr(instance, "link_thay_the", "") if instance else "")
    if hieu_luc == HieuLuc.HET_VA_THAY_THE:
        if not link_thay_the or not str(link_thay_the).strip():
            raise serializers.ValidationError(
                {"link_thay_the": "Văn bản hết hiệu lực và được thay thế bắt buộc phải có liên kết văn bản thay thế (link_thay_the)."}
            )


class VanBanDenSerializer(serializers.ModelSerializer):
    loai_display = serializers.CharField(source="get_loai_display", read_only=True)
    hieu_luc_display = serializers.CharField(source="get_hieu_luc_display", read_only=True)
    attachments = VanBanDenAttachmentSerializer(many=True, read_only=True)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        _validate_replacement_link(attrs, self.instance)
        return attrs

    class Meta:
        model = VanBanDen
        fields = "__all__"
        read_only_fields = ["id", "so_thu_tu", "created_at", "updated_at"]


class VanBanDiSerializer(serializers.ModelSerializer):
    loai_display = serializers.CharField(source="get_loai_display", read_only=True)
    hieu_luc_display = serializers.CharField(source="get_hieu_luc_display", read_only=True)
    attachments = VanBanDiAttachmentSerializer(many=True, read_only=True)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        _validate_replacement_link(attrs, self.instance)
        return attrs

    class Meta:
        model = VanBanDi
        fields = "__all__"
        read_only_fields = ["id", "so_thu_tu", "created_at", "updated_at"]


# ═══════════════════════════════════════════════════════════════════
# DocumentViewLog Serializer
# ═══════════════════════════════════════════════════════════════════

class DocumentViewLogSerializer(serializers.ModelSerializer):
    """Serializer cho lịch sử xem văn bản (API viewers)."""

    user_id = serializers.IntegerField(source="user.id", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    full_name = serializers.SerializerMethodField()
    chuc_danh = serializers.SerializerMethodField()
    don_vi = serializers.SerializerMethodField()

    class Meta:
        model = DocumentViewLog
        fields = [
            "id",
            "user_id",
            "username",
            "full_name",
            "chuc_danh",
            "don_vi",
            "viewed_at",
        ]

    def get_full_name(self, obj):
        if hasattr(obj.user, "get_full_name"):
            full_name = obj.user.get_full_name()
            if full_name:
                return full_name
        return getattr(obj.user, "ho_ten", None) or obj.user.username

    def get_chuc_danh(self, obj):
        if hasattr(obj.user, "chuc_danh") and obj.user.chuc_danh:
            return obj.user.chuc_danh
        if hasattr(obj.user, "chuc_vu") and obj.user.chuc_vu:
            return getattr(obj.user.chuc_vu, "name", "")
        profile = getattr(obj.user, "profile", None)
        return getattr(profile, "position", "") if profile else ""

    def get_don_vi(self, obj):
        if hasattr(obj.user, "don_vi") and obj.user.don_vi:
            return getattr(obj.user.don_vi, "ten", "")
        profile = getattr(obj.user, "profile", None)
        return getattr(profile, "department", "") if profile else ""
