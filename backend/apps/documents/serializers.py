"""
Serializers cho Module Văn Bản (Đến / Đi) — Kiến trúc 2 Model.

Hỗ trợ:
- Serializer riêng biệt cho từng phân hệ: VanBanDen, VanBanDi
- Serializer hợp nhất cho API facade (DocumentListSerializer, DocumentDetailSerializer, DocumentCreateUpdateSerializer)
- Serializer tệp đính kèm và lịch sử người xem
"""

from django.contrib.auth import get_user_model
from django.db import models
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
    VanBanMat,
    VanBanMatAttachment,
    DocumentViewLog,
    DocumentAccessLog,
    Folder,
    FolderFile,
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

    file = serializers.SerializerMethodField()
    file_name = serializers.CharField(source="name", read_only=True)
    uploaded_at = serializers.DateTimeField(source="created_at", read_only=True)
    created_time = serializers.DateTimeField(source="created_at", read_only=True)

    def get_file(self, obj):
        doc_id = getattr(obj, "document_id", None) or getattr(obj, "vanbanden_id", None) or getattr(obj, "vanbandi_id", None) or getattr(obj, "vanbanmat_id", None)
        if doc_id:
            return f"/api/documents/{doc_id}/attachments/{obj.pk}/download/"
        if obj.file:
            try:
                return obj.file.url
            except Exception:
                return None
        return None

    class Meta:
        model = VanBanDenAttachment
        fields = ["id", "file", "name", "file_name", "path", "file_size", "is_deleted", "uploaded_at", "created_at", "created_time"]
        read_only_fields = ["id", "name", "file_name", "path", "file_size", "uploaded_at", "created_at", "created_time"]


class VanBanDenAttachmentSerializer(serializers.ModelSerializer):
    file = serializers.SerializerMethodField()
    created_time = serializers.DateTimeField(source="created_at", read_only=True)

    def get_file(self, obj):
        doc_id = getattr(obj, "document_id", None) or getattr(obj, "vanbanden_id", None)
        if doc_id:
            return f"/api/documents/{doc_id}/attachments/{obj.pk}/download/"
        if obj.file:
            try:
                return obj.file.url
            except Exception:
                return None
        return None

    class Meta:
        model = VanBanDenAttachment
        fields = ["id", "file", "name", "path", "file_size", "is_deleted", "created_at", "created_time"]
        read_only_fields = ["id", "name", "path", "file_size", "created_at", "created_time"]


class VanBanDiAttachmentSerializer(serializers.ModelSerializer):
    file = serializers.SerializerMethodField()
    created_time = serializers.DateTimeField(source="created_at", read_only=True)

    def get_file(self, obj):
        doc_id = getattr(obj, "document_id", None) or getattr(obj, "vanbandi_id", None)
        if doc_id:
            return f"/api/documents/{doc_id}/attachments/{obj.pk}/download/"
        if obj.file:
            try:
                return obj.file.url
            except Exception:
                return None
        return None

    class Meta:
        model = VanBanDiAttachment
        fields = ["id", "file", "name", "path", "file_size", "is_deleted", "created_at", "created_time"]
        read_only_fields = ["id", "name", "path", "file_size", "created_at", "created_time"]


class VanBanMatAttachmentSerializer(serializers.ModelSerializer):
    file = serializers.SerializerMethodField()
    created_time = serializers.DateTimeField(source="created_at", read_only=True)

    def get_file(self, obj):
        doc_id = getattr(obj, "document_id", None) or getattr(obj, "vanbanmat_id", None)
        if doc_id:
            return f"/api/documents/{doc_id}/attachments/{obj.pk}/download/"
        if obj.file:
            try:
                return obj.file.url
            except Exception:
                return None
        return None

    class Meta:
        model = VanBanMatAttachment
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
    so_thu_tu = serializers.SerializerMethodField()
    ngay_den = serializers.DateTimeField(read_only=True, default=None)
    ngay_ban_hanh = serializers.DateTimeField(read_only=True, default=None)
    ngay_van_ban = serializers.DateTimeField(read_only=True, default=None)
    trich_yeu = serializers.CharField(read_only=True)
    noi_ban_hanh = serializers.SerializerMethodField()
    nguoi_ky = serializers.CharField(read_only=True, default="")
    chuc_vu = serializers.CharField(read_only=True, default="")
    hieu_luc = serializers.CharField(read_only=True)
    hieu_luc_display = serializers.CharField(source="get_hieu_luc_display", read_only=True)
    ngay_het_hieu_luc = serializers.DateTimeField(read_only=True, default=None)
    link_thay_the = serializers.SerializerMethodField()
    danh_sach_thay_the = serializers.SerializerMethodField()
    thay_the_cho = serializers.SerializerMethodField()
    bi_thay_boi = serializers.SerializerMethodField()
    pham_vi = serializers.CharField(read_only=True, default="NOI_BO")
    pham_vi_display = serializers.SerializerMethodField()
    danh_muc_ho_so = serializers.SerializerMethodField()
    ten_loai_van_ban = serializers.SerializerMethodField()
    hien_thi = serializers.BooleanField(read_only=True)
    nguoi_tao_name = serializers.SerializerMethodField()
    nguoi_tao_username = serializers.CharField(source="nguoi_tao.username", read_only=True, default=None)
    can_edit = serializers.SerializerMethodField()
    can_delete = serializers.SerializerMethodField()
    attachment_count = serializers.SerializerMethodField()
    first_attachment_url = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(read_only=True)

    def get_noi_ban_hanh(self, obj):
        if getattr(obj, "loai", None) == "DI" or getattr(obj, "document_kind", None) == "vanbandi":
            if hasattr(obj, "noibanhanh_links"):
                first_link = obj.noibanhanh_links.first()
                if first_link:
                    try:
                        from organizations.models import DonVi
                        dv = DonVi.objects.filter(pk=first_link.donvi_id).first()
                        if dv:
                            return dv.ten
                    except Exception:
                        pass
            val = getattr(obj, "_noi_ban_hanh", None)
            if val:
                return val
        return getattr(obj, "noi_ban_hanh", "") or ""

    def get_danh_muc_ho_so(self, obj):
        if hasattr(obj, "hoso"):
            first_hs = obj.hoso.first()
            if first_hs:
                try:
                    from records.models import HoSo
                    hs = HoSo.objects.filter(pk=first_hs.hoso_id).first()
                    if hs:
                        return hs.ten_ho_so
                except Exception:
                    pass
        return getattr(obj, "_danh_muc_ho_so", None) or getattr(obj, "danh_muc_ho_so", "") or ""

    def get_ten_loai_van_ban(self, obj):
        if hasattr(obj, "danhmuc"):
            first_dm = obj.danhmuc.first()
            if first_dm:
                try:
                    from records.models import LoaiVanBan as RecordLoaiVanBan
                    lvb = RecordLoaiVanBan.objects.filter(pk=first_dm.loaivanban_id).first()
                    if lvb:
                        return lvb.ten_loai
                except Exception:
                    pass
        val = getattr(obj, "_ten_loai_van_ban", None) or getattr(obj, "ten_loai_van_ban", "") or ""
        if val:
            return val
        from .services import infer_doc_type
        return infer_doc_type(getattr(obj, "so_hieu", ""), getattr(obj, "trich_yeu", ""))

    def get_so_thu_tu(self, obj):
        # CHỈ áp dụng tính STT tự động reset theo năm riêng cho Văn bản Mật
        if getattr(obj, "loai", None) == "MAT" or getattr(obj, "document_kind", None) == "vanbanmat":
            nam = getattr(obj, "nam", None) or (obj.created_at.year if getattr(obj, "created_at", None) else None)
            if nam:
                date_val = getattr(obj, "ngay_ban_hanh", None) or getattr(obj, "created_at", None)
                qs = obj.__class__.objects.filter(nam=nam)
                if date_val:
                    earlier_count = qs.filter(
                        models.Q(ngay_ban_hanh__lt=date_val) |
                        models.Q(ngay_ban_hanh=date_val, id__lte=obj.id)
                    ).count()
                    return earlier_count if earlier_count > 0 else 1
                return qs.filter(id__lte=obj.id).count() or 1
            return 1
        # Với Văn bản Đến và Văn bản Đi: Giữ nguyên 100% logic cũ, lấy trực tiếp trường so_thu_tu có sẵn
        return getattr(obj, "so_thu_tu", None)

    def get_can_edit(self, obj):
        request = self.context.get("request")
        if not request or not request.user or not request.user.is_authenticated:
            return False
        from .views import can_edit_document
        return can_edit_document(request.user, obj)

    def get_can_delete(self, obj):
        request = self.context.get("request")
        if not request or not request.user or not request.user.is_authenticated:
            return False
        from .views import can_delete_document
        return can_delete_document(request.user, obj)

    def get_pham_vi_display(self, obj):
        pv = getattr(obj, "pham_vi", "NOI_BO")
        return "Hạn chế" if pv == "HAN_CHE" else "Nội bộ"

    def get_danh_sach_thay_the(self, obj):
        from .services import get_dynamic_replacements
        return get_dynamic_replacements(obj)

    def get_thay_the_cho(self, obj):
        from .services import get_replacement_relations
        return get_replacement_relations(obj).get("thay_the_cho", [])

    def get_bi_thay_boi(self, obj):
        from .services import get_replacement_relations
        return get_replacement_relations(obj).get("bi_thay_boi", [])

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
            if hasattr(obj, "_prefetched_objects_cache") and "attachments" in obj._prefetched_objects_cache:
                return sum(1 for a in obj.attachments.all() if not getattr(a, "is_deleted", False))
            return obj.attachments.filter(is_deleted=False).count()
        return 0

    def get_first_attachment_url(self, obj):
        if hasattr(obj, "attachments"):
            if hasattr(obj, "_prefetched_objects_cache") and "attachments" in obj._prefetched_objects_cache:
                att = next((a for a in obj.attachments.all() if not getattr(a, "is_deleted", False)), None)
            else:
                att = obj.attachments.filter(is_deleted=False).first()
            if att:
                request = self.context.get("request")
                doc_id = getattr(att, "vanbanden_id", None) or getattr(att, "vanbandi_id", None) or getattr(att, "vanbanmat_id", None) or getattr(obj, "pk", None)
                if doc_id:
                    rel_url = f"/api/documents/{doc_id}/attachments/{att.pk}/download/"
                    if request:
                        return request.build_absolute_uri(rel_url)
                    return rel_url
                if att.file:
                    try:
                        if request:
                            return request.build_absolute_uri(att.file.url)
                        return att.file.url
                    except Exception:
                        return None
        return None


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
    so_thu_tu = serializers.SerializerMethodField()
    ngay_den = serializers.DateTimeField(read_only=True, default=None)
    ngay_ban_hanh = serializers.DateTimeField(read_only=True, default=None)
    ngay_van_ban = serializers.DateTimeField(read_only=True, default=None)
    trich_yeu = serializers.CharField(read_only=True)
    noi_ban_hanh = serializers.SerializerMethodField()
    nguoi_ky = serializers.CharField(read_only=True, default="")
    chuc_vu = serializers.CharField(read_only=True, default="")
    hieu_luc = serializers.CharField(read_only=True)
    hieu_luc_display = serializers.CharField(source="get_hieu_luc_display", read_only=True)
    ngay_het_hieu_luc = serializers.DateTimeField(read_only=True, default=None)
    link_thay_the = serializers.SerializerMethodField()
    danh_sach_thay_the = serializers.SerializerMethodField()
    thay_the_cho = serializers.SerializerMethodField()
    bi_thay_boi = serializers.SerializerMethodField()
    pham_vi = serializers.CharField(read_only=True, default="NOI_BO")
    pham_vi_display = serializers.SerializerMethodField()
    danh_muc_ho_so = serializers.SerializerMethodField()
    ten_loai_van_ban = serializers.SerializerMethodField()
    ghi_chu = serializers.CharField(read_only=True, default="")
    hien_thi = serializers.BooleanField(read_only=True)
    gui_mail_toan_he_thong = serializers.BooleanField(read_only=True)
    attachments = serializers.SerializerMethodField()
    nguoi_tao_name = serializers.SerializerMethodField()
    nguoi_tao_username = serializers.CharField(source="nguoi_tao.username", read_only=True, default=None)
    can_edit = serializers.SerializerMethodField()
    can_delete = serializers.SerializerMethodField()
    nguoi_nhan_list = serializers.SerializerMethodField()
    don_vi_nhan = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    def get_noi_ban_hanh(self, obj):
        if getattr(obj, "loai", None) == "DI" or getattr(obj, "document_kind", None) == "vanbandi":
            if hasattr(obj, "noibanhanh_links"):
                first_link = obj.noibanhanh_links.first()
                if first_link:
                    try:
                        from organizations.models import DonVi
                        dv = DonVi.objects.filter(pk=first_link.donvi_id).first()
                        if dv:
                            return dv.ten
                    except Exception:
                        pass
            val = getattr(obj, "_noi_ban_hanh", None)
            if val:
                return val
        return getattr(obj, "noi_ban_hanh", "") or ""

    def get_danh_muc_ho_so(self, obj):
        if hasattr(obj, "hoso"):
            first_hs = obj.hoso.first()
            if first_hs:
                try:
                    from records.models import HoSo
                    hs = HoSo.objects.filter(pk=first_hs.hoso_id).first()
                    if hs:
                        return hs.ten_ho_so
                except Exception:
                    pass
        return getattr(obj, "_danh_muc_ho_so", None) or getattr(obj, "danh_muc_ho_so", "") or ""

    def get_ten_loai_van_ban(self, obj):
        if hasattr(obj, "danhmuc"):
            first_dm = obj.danhmuc.first()
            if first_dm:
                try:
                    from records.models import LoaiVanBan as RecordLoaiVanBan
                    lvb = RecordLoaiVanBan.objects.filter(pk=first_dm.loaivanban_id).first()
                    if lvb:
                        return lvb.ten_loai
                except Exception:
                    pass
        val = getattr(obj, "_ten_loai_van_ban", None) or getattr(obj, "ten_loai_van_ban", "") or ""
        if val:
            return val
        from .services import infer_doc_type
        return infer_doc_type(getattr(obj, "so_hieu", ""), getattr(obj, "trich_yeu", ""))

    def get_don_vi_nhan(self, obj):
        try:
            if hasattr(obj, "donvinhan"):
                first_dvn = obj.donvinhan.first()
                if first_dvn:
                    from organizations.models import DonVi
                    dv = DonVi.objects.filter(pk=first_dvn.donvi_id).first()
                    if dv:
                        return dv.ten
            if hasattr(obj, "nguoi_nhan"):
                first_user = obj.nguoi_nhan.select_related("don_vi").first()
                if first_user and first_user.don_vi:
                    return first_user.don_vi.ten
        except Exception:
            pass
        return ""

    def get_so_thu_tu(self, obj):
        # CHỈ áp dụng tính STT tự động reset theo năm riêng cho Văn bản Mật
        if getattr(obj, "loai", None) == "MAT" or getattr(obj, "document_kind", None) == "vanbanmat":
            nam = getattr(obj, "nam", None) or (obj.created_at.year if getattr(obj, "created_at", None) else None)
            if nam:
                date_val = getattr(obj, "ngay_ban_hanh", None) or getattr(obj, "created_at", None)
                qs = obj.__class__.objects.filter(nam=nam)
                if date_val:
                    earlier_count = qs.filter(
                        models.Q(ngay_ban_hanh__lt=date_val) |
                        models.Q(ngay_ban_hanh=date_val, id__lte=obj.id)
                    ).count()
                    return earlier_count if earlier_count > 0 else 1
                return qs.filter(id__lte=obj.id).count() or 1
            return 1
        return getattr(obj, "so_thu_tu", None)

    def get_can_edit(self, obj):
        request = self.context.get("request")
        if not request or not request.user or not request.user.is_authenticated:
            return False
        from .views import can_edit_document
        return can_edit_document(request.user, obj)

    def get_can_delete(self, obj):
        request = self.context.get("request")
        if not request or not request.user or not request.user.is_authenticated:
            return False
        from .views import can_delete_document
        return can_delete_document(request.user, obj)

    def get_pham_vi_display(self, obj):
        pv = getattr(obj, "pham_vi", "NOI_BO")
        return "Hạn chế" if pv == "HAN_CHE" else "Nội bộ"

    def get_danh_sach_thay_the(self, obj):
        from .services import get_dynamic_replacements
        return get_dynamic_replacements(obj)

    def get_thay_the_cho(self, obj):
        from .services import get_replacement_relations
        return get_replacement_relations(obj).get("thay_the_cho", [])

    def get_bi_thay_boi(self, obj):
        from .services import get_replacement_relations
        return get_replacement_relations(obj).get("bi_thay_boi", [])

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
                    "don_vi_id": u.don_vi_id,
                    "don_vi_ten": u.don_vi.ten if u.don_vi else "",
                    "department": u.don_vi.ten if u.don_vi else "",
                }
                for u in obj.nguoi_nhan.select_related("don_vi").all()
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
    danh_muc_ho_so = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    ten_loai_van_ban = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    ghi_chu = serializers.CharField(required=False, allow_blank=True, default="")
    pham_vi = serializers.ChoiceField(choices=PhamVi.choices, default=PhamVi.NOI_BO, required=False)
    hien_thi = serializers.BooleanField(default=True)
    gui_mail_toan_he_thong = serializers.BooleanField(default=False)
    don_vi_nhan = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")
    nguoi_nhan = TolerantPrimaryKeyRelatedField(
        many=True,
        queryset=User.objects.all(),
        required=False,
    )

    def validate_nguoi_nhan(self, value):
        return [u for u in value if u is not None]

    def validate(self, attrs):
        loai = attrs.get("loai") or (getattr(self.instance, "loai", None) if self.instance else LoaiVanBan.DEN)

        # Đảm bảo thời gian ngày đến / ngày ban hành không bị full 0 (00:00:00) khi client gửi ngày dạng YYYY-MM-DD
        now = timezone.now()
        for date_field in ("ngay_den", "ngay_ban_hanh"):
            dt_val = attrs.get(date_field)
            if dt_val and hasattr(dt_val, "hour") and dt_val.hour == 0 and dt_val.minute == 0 and dt_val.second == 0 and dt_val.microsecond == 0:
                old_dt = getattr(self.instance, date_field, None) if self.instance else None
                if old_dt and hasattr(old_dt, "hour") and (old_dt.hour != 0 or old_dt.minute != 0 or old_dt.second != 0):
                    attrs[date_field] = dt_val.replace(
                        hour=old_dt.hour,
                        minute=old_dt.minute,
                        second=old_dt.second,
                        microsecond=old_dt.microsecond,
                    )
                else:
                    attrs[date_field] = dt_val.replace(
                        hour=now.hour,
                        minute=now.minute,
                        second=now.second,
                        microsecond=now.microsecond,
                    )

        # Ràng buộc nghiệp vụ: Ngày hết hiệu lực không được nhỏ hơn ngày ban hành / ngày đến
        ngay_het_hieu_luc = attrs.get("ngay_het_hieu_luc")
        if ngay_het_hieu_luc is not None:
            compare_date = attrs.get("ngay_ban_hanh") or attrs.get("ngay_den") or attrs.get("ngay_van_ban")
            if not compare_date and self.instance:
                compare_date = getattr(self.instance, "ngay_ban_hanh", None) or getattr(self.instance, "ngay_den", None) or getattr(self.instance, "ngay_van_ban", None)
            if compare_date and ngay_het_hieu_luc < compare_date:
                raise serializers.ValidationError(
                    {"ngay_het_hieu_luc": "Ngày hết hiệu lực không được nhỏ hơn ngày ban hành / ngày đến của văn bản."}
                )

        if loai == LoaiVanBan.MAT:
            attrs["pham_vi"] = PhamVi.HAN_CHE
            attrs["gui_mail_toan_he_thong"] = False

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

        # Chặn tự thay thế, chặn văn bản không tồn tại và vòng lặp thay thế 2 chiều (Replacement Guard)
        so_hieu = (attrs.get("so_hieu") or (getattr(self.instance, "so_hieu", "") if self.instance else "")).strip()
        raw_link = attrs.get("link_thay_the") if "link_thay_the" in attrs else (getattr(self.instance, "link_thay_the", "") if self.instance else "")
        raw_link_str = str(raw_link or "").strip()
        if raw_link_str:
            from .services import parse_replacement_target, find_replacement_target_document
            targets = [t.strip() for t in raw_link_str.split(",") if t.strip()]
            target_model = VanBanDi if str(loai).upper() in ("DI", "VANBANDI") else (VanBanMat if str(loai).upper() in ("MAT", "VANBANMAT") else VanBanDen)
            current_pham_vi = attrs.get("pham_vi") or (getattr(self.instance, "pham_vi", PhamVi.NOI_BO) if self.instance else PhamVi.NOI_BO)
            loai_label = "Văn bản Đi" if str(loai).upper() in ("DI", "VANBANDI") else ("Văn bản Mật" if str(loai).upper() in ("MAT", "VANBANMAT") else "Văn bản Đến")

            for target in targets:
                parsed = parse_replacement_target(target)
                base_target = parsed["base_so_hieu"]

                # 1. Chặn tự thay thế chính mình:
                # Nếu đang chỉnh sửa bản ghi hiện tại và mục tiêu chỉ rõ số thứ tự trùng với bản ghi hiện tại:
                if self.instance and so_hieu and base_target.lower() == so_hieu.lower():
                    target_stt = parsed.get("so_thu_tu")
                    inst_stt = getattr(self.instance, "so_thu_tu", None)
                    if target_stt is not None and inst_stt is not None and target_stt == inst_stt:
                        raise serializers.ValidationError(
                            {"link_thay_the": "Văn bản không thể tự thiết lập thay thế chính nó."}
                        )

                # 2. Khóa nghiệp vụ: Bắt buộc văn bản mục tiêu phải cùng phân hệ (loai)
                for other_model, other_label in ((VanBanDen, "Văn bản Đến"), (VanBanDi, "Văn bản Đi"), (VanBanMat, "Văn bản Mật")):
                    if other_model != target_model:
                        other_match = find_replacement_target_document(target, target_model=other_model)
                        if other_match:
                            raise serializers.ValidationError(
                                {"link_thay_the": f"Văn bản mục tiêu '{target}' là {other_label}. {loai_label} chỉ được phép thay thế cho văn bản cùng phân hệ ({loai_label})."}
                            )

                # Tìm trong đúng model mục tiêu và khớp theo định danh (loại trừ chính bản ghi đang sửa)
                target_doc = find_replacement_target_document(
                    target,
                    current_doc=self.instance,
                    target_model=target_model,
                    current_pham_vi=current_pham_vi,
                )
                if not target_doc:
                    # Nếu không tìm thấy văn bản khác và số hiệu trùng nhau, người dùng đang cố ý thay thế chính nó
                    if self.instance and so_hieu and base_target.lower() == so_hieu.lower():
                        raise serializers.ValidationError(
                            {"link_thay_the": "Văn bản không thể tự thiết lập thay thế chính nó."}
                        )
                    raise serializers.ValidationError(
                        {"link_thay_the": f"Văn bản mục tiêu '{target}' không tồn tại trong hệ thống {loai_label}. Vui lòng chọn văn bản hợp lệ từ danh sách gợi ý."}
                    )

                # Nếu tìm thấy nhưng lại trùng đúng PK của bản ghi đang sửa
                if self.instance and target_doc.pk == self.instance.pk:
                    raise serializers.ValidationError(
                        {"link_thay_the": "Văn bản không thể tự thiết lập thay thế chính nó."}
                    )

                # 3. Khóa nghiệp vụ: Bắt buộc cùng phạm vi (Nội bộ chỉ thay thế Nội bộ, Hạn chế chỉ thay thế Hạn chế)
                if getattr(target_doc, "pham_vi", PhamVi.NOI_BO) != current_pham_vi:
                    scope_curr_label = "Văn bản nội bộ" if current_pham_vi == PhamVi.NOI_BO else "Văn bản hạn chế"
                    scope_target_label = "nội bộ" if target_doc.pham_vi == PhamVi.NOI_BO else "hạn chế"
                    raise serializers.ValidationError(
                        {"link_thay_the": f"Văn bản mục tiêu '{target}' là văn bản {scope_target_label}. {scope_curr_label} chỉ được phép thay thế cho văn bản cùng phạm vi."}
                    )

                # 4. Chặn vòng lặp thay thế hai chiều khi cả hai văn bản đều đòi Còn hiệu lực toàn phần
                other_links = [
                    s.strip() for s in (target_doc.link_thay_the or "").split(",") if s.strip()
                ]
                current_hieu_luc = attrs.get("hieu_luc", HieuLuc.CON_HIEU_LUC)

                def link_targets_current(l_str: str) -> bool:
                    p = parse_replacement_target(l_str)
                    if p["base_so_hieu"].lower() != so_hieu.lower():
                        return False
                    if self.instance and getattr(self.instance, "so_thu_tu", None) is not None and p["so_thu_tu"] is not None:
                        return p["so_thu_tu"] == self.instance.so_thu_tu
                    return True

                if (
                    so_hieu
                    and any(link_targets_current(l) for l in other_links)
                    and target_doc.hieu_luc == HieuLuc.CON_HIEU_LUC
                    and current_hieu_luc == HieuLuc.CON_HIEU_LUC
                ):
                    raise serializers.ValidationError(
                        {"link_thay_the": f"Xung đột nghiệp vụ: Văn bản '{target_doc.so_hieu}' đang còn hiệu lực toàn phần và đã được thiết lập thay thế cho văn bản này. Không thể tạo vòng lặp thay thế hai chiều!"}
                    )

        # Issue #82 & Quyền thay đổi phạm vi lưu hành:
        # CHỈ RIÊNG Quản trị viên (Admin) mới có quyền chỉnh sửa phạm vi từ NOI_BO sang HAN_CHE và ngược lại sau khi thêm
        if self.instance and "pham_vi" in attrs and attrs["pham_vi"] != self.instance.pham_vi:
            request = self.context.get("request")
            user = getattr(request, "user", None) if request else None
            profile = getattr(user, "profile", None) if user else None
            is_admin = bool(
                user
                and (
                    user.is_superuser
                    or (profile and getattr(profile, "role", None) == "admin")
                    or getattr(user, "username", "") in ("admin", "quantri")
                )
            )
            if not is_admin:
                raise serializers.ValidationError(
                    {"pham_vi": "Chỉ Quản trị viên (Admin) mới có quyền thay đổi phạm vi lưu hành của văn bản."}
                )
            self.instance._allow_scope_change = True

        pham_vi = attrs.get("pham_vi") or (getattr(self.instance, "pham_vi", PhamVi.NOI_BO) if self.instance else PhamVi.NOI_BO)
        if pham_vi == PhamVi.HAN_CHE or loai == LoaiVanBan.MAT:
            if attrs.get("gui_mail_toan_he_thong"):
                raise serializers.ValidationError(
                    {"gui_mail_toan_he_thong": "Văn bản hạn chế không được phép gửi email toàn hệ thống."}
                )
            attrs["gui_mail_toan_he_thong"] = False

            # Bắt buộc có ít nhất 1 người nhận khi tạo mới hoặc khi chuyển sang phạm vi Hạn chế
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
            elif self.instance and getattr(self.instance, "pham_vi", None) != PhamVi.HAN_CHE:
                has_recipients = bool(attrs.get("nguoi_nhan")) or self.instance.nguoi_nhan.exists()
                if not has_recipients:
                    raise serializers.ValidationError(
                        {"nguoi_nhan": "Khi chuyển sang phạm vi Hạn chế, bắt buộc phải chọn ít nhất một người nhận."}
                    )

        return attrs

    def _save_don_vi_nhan(self, instance, don_vi_name: str):
        try:
            from organizations.models import DonVi
            from .models import VanBanDenDonViNhan, VanBanDiDonViNhan

            dv = None
            if don_vi_name and str(don_vi_name).strip():
                dv = DonVi.objects.filter(ten__iexact=str(don_vi_name).strip()).first()

            kind = getattr(instance, "document_kind", "")
            if kind in ("vanbanden", "vanbanmat"):
                VanBanDenDonViNhan.objects.filter(vanbanden=instance).delete()
                if dv:
                    VanBanDenDonViNhan.objects.create(vanbanden=instance, donvi_id=dv.id)
            elif kind == "vanbandi":
                VanBanDiDonViNhan.objects.filter(vanbandi=instance).delete()
                if dv:
                    VanBanDiDonViNhan.objects.create(vanbandi=instance, donvi_id=dv.id)
        except Exception:
            pass

    def _save_hoso_and_danhmuc(self, instance, ho_so_val, loai_vb_val):
        try:
            from records.models import HoSo, LoaiVanBan as RecordLoaiVanBan
            from .models import (
                VanBanDenHoSo, VanBanDenDanhmuc,
                VanBanDiHoSo, VanBanDiDanhmuc,
            )
            from .services import ensure_hoso_and_doc_type

            kind = getattr(instance, "document_kind", "")
            is_di = (kind == "vanbandi")
            hoso_model = VanBanDiHoSo if is_di else VanBanDenHoSo
            danhmuc_model = VanBanDiDanhmuc if is_di else VanBanDenDanhmuc

            creator = getattr(instance, "nguoi_tao", None)

            existing_hs_name = ""
            if ho_so_val is None and hasattr(instance, "hoso") and instance.hoso.exists():
                first_h = instance.hoso.first()
                if first_h:
                    try:
                        h_obj = HoSo.objects.filter(pk=first_h.hoso_id).first()
                        if h_obj:
                            existing_hs_name = h_obj.ten_ho_so
                    except Exception:
                        pass

            target_hs_val = ho_so_val if ho_so_val is not None else existing_hs_name
            hs, lvb = ensure_hoso_and_doc_type(target_hs_val, loai_vb_val or "", creator=creator)

            if ho_so_val is not None:
                clean_hs = str(ho_so_val).strip()
                if clean_hs and hs:
                    if is_di:
                        hoso_model.objects.filter(vanbandi=instance).delete()
                        hoso_model.objects.create(vanbandi=instance, hoso_id=hs.pk)
                    else:
                        hoso_model.objects.filter(vanbanden=instance).delete()
                        hoso_model.objects.create(vanbanden=instance, hoso_id=hs.pk)
                else:
                    if is_di:
                        hoso_model.objects.filter(vanbandi=instance).delete()
                    else:
                        hoso_model.objects.filter(vanbanden=instance).delete()

            if loai_vb_val is not None:
                clean_lvb = str(loai_vb_val).strip()
                if clean_lvb and lvb:
                    # Đảm bảo Loại văn bản phải thuộc đúng Hồ sơ hs để thỏa mãn Database Trigger PostgreSQL
                    if hs and getattr(lvb, "ho_so_id", None) != hs.pk:
                        lvb_under_hs = RecordLoaiVanBan.objects.filter(ten_loai__iexact=clean_lvb, ho_so=hs).first()
                        if not lvb_under_hs:
                            try:
                                lvb_under_hs = RecordLoaiVanBan.objects.create(ho_so=hs, ten_loai=clean_lvb)
                            except Exception:
                                lvb_under_hs = RecordLoaiVanBan.objects.filter(ten_loai__iexact=clean_lvb, ho_so=hs).first()
                        if lvb_under_hs:
                            lvb = lvb_under_hs

                    if is_di:
                        danhmuc_model.objects.filter(vanbandi=instance).delete()
                        danhmuc_model.objects.create(vanbandi=instance, loaivanban_id=lvb.pk)
                    else:
                        danhmuc_model.objects.filter(vanbanden=instance).delete()
                        danhmuc_model.objects.create(vanbanden=instance, loaivanban_id=lvb.pk)
                else:
                    if is_di:
                        danhmuc_model.objects.filter(vanbandi=instance).delete()
                    else:
                        danhmuc_model.objects.filter(vanbanden=instance).delete()
        except Exception:
            pass

    def _save_noi_ban_hanh(self, instance, nbh_val):
        try:
            from organizations.models import DonVi
            from .models import VanBanDiNoiBanHanh

            kind = getattr(instance, "document_kind", "")
            if kind == "vanbandi":
                VanBanDiNoiBanHanh.objects.filter(vanbandi=instance).delete()
                if nbh_val and str(nbh_val).strip():
                    clean_nbh = str(nbh_val).strip()
                    dv = None
                    if clean_nbh.isdigit():
                        dv = DonVi.objects.filter(pk=int(clean_nbh)).first()
                    if not dv:
                        dv = DonVi.objects.filter(ten__iexact=clean_nbh).first() or DonVi.objects.filter(ma_dinh_danh__iexact=clean_nbh).first()
                    if not dv:
                        dv = DonVi.objects.filter(ten__icontains=clean_nbh).first() or DonVi.objects.filter(ma_dinh_danh__icontains=clean_nbh).first()
                    if not dv:
                        for candidate in DonVi.objects.all():
                            if candidate.ten and (candidate.ten.lower() in clean_nbh.lower() or clean_nbh.lower() in candidate.ten.lower()):
                                dv = candidate
                                break
                    if dv:
                        VanBanDiNoiBanHanh.objects.create(vanbandi=instance, donvi_id=dv.pk)
                    instance._noi_ban_hanh = clean_nbh
            else:
                if nbh_val is not None:
                    instance.noi_ban_hanh = str(nbh_val)
                    instance.save(update_fields=["noi_ban_hanh"])
        except Exception:
            pass

    def create(self, validated_data):
        from .selectors import log_access

        don_vi_nhan = validated_data.pop("don_vi_nhan", None)
        nguoi_nhan = validated_data.pop("nguoi_nhan", [])
        danh_muc_ho_so = validated_data.pop("danh_muc_ho_so", None)
        ten_loai_van_ban = validated_data.pop("ten_loai_van_ban", None)
        loai = validated_data.pop("loai", LoaiVanBan.DEN)
        model = get_document_model(loai)

        # VB hạn chế / VB Mật không gửi mail toàn trường
        pham_vi = validated_data.get("pham_vi", PhamVi.NOI_BO)
        if pham_vi == PhamVi.HAN_CHE or loai == LoaiVanBan.MAT:
            validated_data["pham_vi"] = PhamVi.HAN_CHE
            validated_data["gui_mail_toan_he_thong"] = False

        if loai == LoaiVanBan.MAT:
            validated_data.pop("so_thu_tu", None)
        elif "so_thu_tu" not in validated_data or not validated_data["so_thu_tu"]:
            from .services import generate_so_thu_tu
            year = validated_data.get("nam") or timezone.now().year
            validated_data["so_thu_tu"] = generate_so_thu_tu(loai, year) or 1

        # Xử lý tương thích trường ngày giữa các model Đến và Đi
        noi_ban_hanh = None
        if model == VanBanDen:
            ngay_ban_hanh = validated_data.pop("ngay_ban_hanh", None)
            if ngay_ban_hanh and not validated_data.get("ngay_den"):
                validated_data["ngay_den"] = ngay_ban_hanh
            if ngay_ban_hanh and not validated_data.get("ngay_van_ban"):
                validated_data["ngay_van_ban"] = ngay_ban_hanh
        elif model == VanBanDi:
            ngay_den = validated_data.pop("ngay_den", None)
            if ngay_den and not validated_data.get("ngay_ban_hanh"):
                validated_data["ngay_ban_hanh"] = ngay_den
            if ngay_den and not validated_data.get("ngay_van_ban"):
                validated_data["ngay_van_ban"] = ngay_den
            noi_ban_hanh = validated_data.pop("noi_ban_hanh", None)

        if validated_data.get("hieu_luc") == HieuLuc.CON_HIEU_LUC and not validated_data.get("ngay_het_hieu_luc"):
            validated_data["ngay_het_hieu_luc"] = None

        model_field_names = {f.name for f in model._meta.get_fields()}
        create_kwargs = {k: v for k, v in validated_data.items() if k in model_field_names}

        instance = model.objects.create(**create_kwargs)
        if don_vi_nhan is not None:
            self._save_don_vi_nhan(instance, don_vi_nhan)

        if model == VanBanDi and noi_ban_hanh is not None:
            self._save_noi_ban_hanh(instance, noi_ban_hanh)

        if danh_muc_ho_so is not None or ten_loai_van_ban is not None:
            self._save_hoso_and_danhmuc(instance, danh_muc_ho_so, ten_loai_van_ban)

        if danh_muc_ho_so is not None:
            instance._danh_muc_ho_so = danh_muc_ho_so
        if ten_loai_van_ban is not None:
            instance._ten_loai_van_ban = ten_loai_van_ban
        if noi_ban_hanh is not None and model == VanBanDi:
            instance._noi_ban_hanh = noi_ban_hanh

        if nguoi_nhan:
            instance.nguoi_nhan.set(nguoi_nhan)

        # Ghi log THEM_NGUOI_XEM ban đầu cho văn bản hạn chế
        if getattr(instance, "pham_vi", None) == PhamVi.HAN_CHE or loai == LoaiVanBan.MAT:
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

        don_vi_nhan = validated_data.pop("don_vi_nhan", None)
        nguoi_nhan = validated_data.pop("nguoi_nhan", None)
        danh_muc_ho_so = validated_data.pop("danh_muc_ho_so", None)
        ten_loai_van_ban = validated_data.pop("ten_loai_van_ban", None)
        noi_ban_hanh = validated_data.pop("noi_ban_hanh", None) if getattr(instance, "document_kind", "") == "vanbandi" else None
        validated_data.pop("loai", None)
        validated_data.pop("so_thu_tu", None)  # Read-only! Khóa cứng Số đi / Số đến
        validated_data.pop("nam", None)        # Read-only! Khóa cứng Năm khi cập nhật văn bản

        if "pham_vi" in validated_data and validated_data["pham_vi"] != instance.pham_vi:
            req = self.context.get("request")
            user = getattr(req, "user", None) if req else None
            profile = getattr(user, "profile", None) if user else None
            is_admin = bool(
                user
                and (
                    user.is_superuser
                    or (profile and getattr(profile, "role", None) == "admin")
                    or getattr(user, "username", "") in ("admin", "quantri")
                )
            )
            if not is_admin:
                raise serializers.ValidationError({"pham_vi": "Chỉ Quản trị viên (Admin) mới có quyền thay đổi phạm vi lưu hành của văn bản."})
            instance._allow_scope_change = True

        if getattr(instance, "pham_vi", None) == PhamVi.HAN_CHE or getattr(instance, "loai", None) == "MAT":
            validated_data["gui_mail_toan_he_thong"] = False

        model_field_names = {f.name for f in instance._meta.get_fields()}
        for attr, value in validated_data.items():
            if attr in model_field_names:
                setattr(instance, attr, value)

        current_hieu_luc = validated_data.get("hieu_luc", getattr(instance, "hieu_luc", None))
        if current_hieu_luc == HieuLuc.CON_HIEU_LUC and not validated_data.get("ngay_het_hieu_luc"):
            instance.ngay_het_hieu_luc = None

        instance.save()

        if don_vi_nhan is not None:
            self._save_don_vi_nhan(instance, don_vi_nhan)

        if noi_ban_hanh is not None:
            self._save_noi_ban_hanh(instance, noi_ban_hanh)

        if danh_muc_ho_so is not None or ten_loai_van_ban is not None:
            self._save_hoso_and_danhmuc(instance, danh_muc_ho_so, ten_loai_van_ban)

        if danh_muc_ho_so is not None:
            instance._danh_muc_ho_so = danh_muc_ho_so
        if ten_loai_van_ban is not None:
            instance._ten_loai_van_ban = ten_loai_van_ban
        if noi_ban_hanh is not None and getattr(instance, "document_kind", "") == "vanbandi":
            instance._noi_ban_hanh = noi_ban_hanh

        if nguoi_nhan is not None:
            if getattr(instance, "pham_vi", None) == PhamVi.HAN_CHE or getattr(instance, "loai", None) == "MAT":
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
    ngay_het_hieu_luc = attrs.get("ngay_het_hieu_luc")
    if ngay_het_hieu_luc is not None:
        compare_date = attrs.get("ngay_ban_hanh") or attrs.get("ngay_den") or attrs.get("ngay_van_ban")
        if not compare_date and instance:
            compare_date = getattr(instance, "ngay_ban_hanh", None) or getattr(instance, "ngay_den", None) or getattr(instance, "ngay_van_ban", None)
        if compare_date and ngay_het_hieu_luc < compare_date:
            raise serializers.ValidationError(
                {"ngay_het_hieu_luc": "Ngày hết hiệu lực không được nhỏ hơn ngày ban hành / ngày đến của văn bản."}
            )


class VanBanDenSerializer(serializers.ModelSerializer):
    loai_display = serializers.CharField(source="get_loai_display", read_only=True)
    hieu_luc_display = serializers.CharField(source="get_hieu_luc_display", read_only=True)
    attachments = serializers.SerializerMethodField()

    def get_attachments(self, obj):
        if hasattr(obj, "attachments"):
            return VanBanDenAttachmentSerializer(obj.attachments.filter(is_deleted=False), many=True).data
        return []

    def validate(self, attrs):
        attrs = super().validate(attrs)
        _validate_replacement_link(attrs, self.instance)
        return attrs

    def update(self, instance, validated_data):
        validated_data.pop("so_thu_tu", None)
        validated_data.pop("nam", None)
        return super().update(instance, validated_data)

    class Meta:
        model = VanBanDen
        fields = "__all__"
        read_only_fields = ["id", "so_thu_tu", "created_at", "updated_at"]


class VanBanDiSerializer(serializers.ModelSerializer):
    loai_display = serializers.CharField(source="get_loai_display", read_only=True)
    hieu_luc_display = serializers.CharField(source="get_hieu_luc_display", read_only=True)
    attachments = serializers.SerializerMethodField()

    def get_attachments(self, obj):
        if hasattr(obj, "attachments"):
            return VanBanDiAttachmentSerializer(obj.attachments.filter(is_deleted=False), many=True).data
        return []

    def validate(self, attrs):
        attrs = super().validate(attrs)
        _validate_replacement_link(attrs, self.instance)
        return attrs

    def update(self, instance, validated_data):
        validated_data.pop("so_thu_tu", None)
        validated_data.pop("nam", None)
        return super().update(instance, validated_data)

    class Meta:
        model = VanBanDi
        fields = "__all__"
        read_only_fields = ["id", "so_thu_tu", "created_at", "updated_at"]


class VanBanMatSerializer(serializers.ModelSerializer):
    so_thu_tu = serializers.SerializerMethodField()
    loai_display = serializers.CharField(source="get_loai_display", read_only=True)
    hieu_luc_display = serializers.CharField(source="get_hieu_luc_display", read_only=True)
    attachments = serializers.SerializerMethodField()

    def get_attachments(self, obj):
        if hasattr(obj, "attachments"):
            return VanBanMatAttachmentSerializer(obj.attachments.filter(is_deleted=False), many=True).data
        return []

    def get_so_thu_tu(self, obj):
        return getattr(obj, "so_thu_tu", 1) or 1

    def validate(self, attrs):
        attrs = super().validate(attrs)
        _validate_replacement_link(attrs, self.instance)
        return attrs

    def update(self, instance, validated_data):
        validated_data.pop("nam", None)
        return super().update(instance, validated_data)

    class Meta:
        model = VanBanMat
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


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


# ═══════════════════════════════════════════════════════════════════
# Folder & FolderFile Serializers — Thư mục nhiều cấp
# ═══════════════════════════════════════════════════════════════════

class FolderFileSerializer(serializers.ModelSerializer):
    """Serializer cho file trong thư mục."""
    uploaded_by_name = serializers.SerializerMethodField()

    class Meta:
        model = FolderFile
        fields = [
            "id",
            "folder",
            "file_name",
            "file_path",
            "file_size",
            "file_type",
            "description",
            "is_local",
            "uploaded_by",
            "uploaded_by_name",
            "created_at",
        ]
        read_only_fields = ["id", "created_at", "uploaded_by_name"]

    def get_uploaded_by_name(self, obj):
        if obj.uploaded_by:
            return getattr(obj.uploaded_by, "full_name", None) or getattr(obj.uploaded_by, "username", str(obj.uploaded_by))
        return None


class FolderSerializer(serializers.ModelSerializer):
    """
    Serializer cho CRUD Folder đơn lẻ.
    Hỗ trợ parent_id để tạo/gán thư mục cha.
    """
    parent_id = serializers.PrimaryKeyRelatedField(
        queryset=Folder.objects.all(),
        source="parent",
        required=False,
        allow_null=True,
        default=None,
    )
    full_path_display = serializers.ReadOnlyField()
    children_count = serializers.SerializerMethodField()
    files_count = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Folder
        fields = [
            "id",
            "name",
            "parent_id",
            "path",
            "depth",
            "order",
            "description",
            "is_local",
            "local_path",
            "full_path_display",
            "children_count",
            "files_count",
            "created_by",
            "created_by_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "path",
            "depth",
            "full_path_display",
            "children_count",
            "files_count",
            "created_by",
            "created_by_name",
            "created_at",
            "updated_at",
        ]
        validators = []

    def get_children_count(self, obj):
        return obj.children.count()

    def get_files_count(self, obj):
        return obj.files.count()

    def get_created_by_name(self, obj):
        if obj.created_by:
            return getattr(obj.created_by, "full_name", None) or getattr(obj.created_by, "username", str(obj.created_by))
        return None

    def validate(self, attrs):
        parent = attrs.get("parent", getattr(self.instance, "parent", None) if self.instance else None)
        name = attrs.get("name", getattr(self.instance, "name", None) if self.instance else None)
        qs = Folder.objects.filter(parent=parent, name=name)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            parent_name = parent.name if parent else "Gốc (Root)"
            raise serializers.ValidationError(
                {"name": f"Thư mục '{name}' đã tồn tại trong thư mục '{parent_name}'."}
            )
        return attrs


class FolderTreeSerializer(serializers.ModelSerializer):
    """
    Serializer đệ quy để xuất cây thư mục đầy đủ (Tree View).
    Mỗi node bao gồm children của nó và số lượng file.
    """
    children = serializers.SerializerMethodField()
    files_count = serializers.SerializerMethodField()
    full_path_display = serializers.ReadOnlyField()
    parent_id = serializers.PrimaryKeyRelatedField(source="parent", read_only=True)

    class Meta:
        model = Folder
        fields = [
            "id",
            "name",
            "parent_id",
            "path",
            "depth",
            "order",
            "description",
            "is_local",
            "local_path",
            "full_path_display",
            "files_count",
            "children",
            "created_at",
            "updated_at",
        ]

    def get_children(self, obj):
        children = obj.children.all().order_by("order", "name")
        return FolderTreeSerializer(children, many=True, context=self.context).data

    def get_files_count(self, obj):
        return obj.files.count()


class FolderBreadcrumbSerializer(serializers.ModelSerializer):
    """Serializer cho một node trong breadcrumb."""
    class Meta:
        model = Folder
        fields = ["id", "name", "depth", "path"]


class FolderMoveSerializer(serializers.Serializer):
    """Serializer nhận dữ liệu di chuyển thư mục."""
    target_parent_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="ID của thư mục cha mới. null nếu muốn di chuyển thành thư mục gốc.",
    )

