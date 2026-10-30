from rest_framework import serializers
from django.core.exceptions import ValidationError as DjangoValidationError
from .models import DanhMucTaiLieu, LoaiTaiLieu, TaiLieuChiTiet, ChiTietTaiLieuAttachment, store_template_file, validate_document_file


class DanhMucTaiLieuSerializer(serializers.ModelSerializer):
    """Serializer cho Danh mục Tài liệu (Cấp 1)"""
    nguoi_lap_name = serializers.SerializerMethodField()

    class Meta:
        model = DanhMucTaiLieu
        fields = [
            'id',
            'stt_uu_tien',
            'ky_hieu',
            'ten_tai_lieu',
            'nguoi_lap',
            'nguoi_lap_name',
            'ngay_lap',
            'ghi_chu',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'nguoi_lap', 'created_at', 'updated_at']

    def get_nguoi_lap_name(self, obj):
        if not obj.nguoi_lap:
            return None
        return obj.nguoi_lap.get_full_name() or obj.nguoi_lap.username


class LoaiTaiLieuSerializer(serializers.ModelSerializer):
    """Serializer cho Loại tài liệu (Cấp 2)"""
    dm_tai_lieu_name = serializers.CharField(source='dm_tai_lieu.ten_tai_lieu', read_only=True)

    class Meta:
        model = LoaiTaiLieu
        fields = [
            'id',
            'dm_tai_lieu',
            'dm_tai_lieu_name',
            'ten_loai',
            'is_public',
            'ngay_lap',
            'ghi_chu',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ChiTietTaiLieuAttachmentSerializer(serializers.ModelSerializer):
    """Serializer cho Tệp đính kèm (records_chitiettailieu_attachment)"""
    created_user = serializers.PrimaryKeyRelatedField(read_only=True, source='nguoi_tao')
    created_time = serializers.DateTimeField(read_only=True, source='created_at')
    created_user_name = serializers.SerializerMethodField()
    nguoi_tao_name = serializers.SerializerMethodField()

    class Meta:
        model = ChiTietTaiLieuAttachment
        fields = [
            'id',
            'document',
            'name',
            'path',
            'file_size',
            'mime_type',
            'is_deleted',
            'created_at',
            'created_time',
            'nguoi_tao',
            'nguoi_tao_name',
            'created_user',
            'created_user_name',
        ]
        read_only_fields = ['id', 'created_at', 'created_time', 'nguoi_tao', 'created_user']

    def get_created_user_name(self, obj):
        user = obj.nguoi_tao
        if not user:
            return None
        return user.get_full_name() or user.username

    def get_nguoi_tao_name(self, obj):
        return self.get_created_user_name(obj)


class TaiLieuChiTietSerializer(serializers.ModelSerializer):
    """
    Serializer cho Chi tiết tài liệu chung (khớp interface ResourceItem của frontend)
    """
    dm_tai_lieu_name = serializers.CharField(source='dm_tai_lieu.ten_tai_lieu', read_only=True)
    loai_tai_lieu = serializers.PrimaryKeyRelatedField(
        queryset=LoaiTaiLieu.objects.all(),
        many=True,
        required=False
    )
    loai_tai_lieu_names = serializers.SerializerMethodField()
    nguoi_tao_name = serializers.SerializerMethodField()
    attachments = ChiTietTaiLieuAttachmentSerializer(many=True, read_only=True)
    file_dinh_kem = serializers.FileField(required=False, allow_null=True)
    ngay_het_hieu_luc = serializers.DateField(required=False, allow_null=True)
    link_thay_the = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    is_expired = serializers.BooleanField(read_only=True)
    effective_hieu_luc = serializers.CharField(read_only=True)

    class Meta:
        model = TaiLieuChiTiet
        fields = [
            'id',
            'dm_tai_lieu',
            'dm_tai_lieu_name',
            'loai_tai_lieu',
            'loai_tai_lieu_names',
            'ky_hieu',
            'tieu_de',
            'ngay_dang',
            'noi_ban_hanh',
            'hieu_luc',
            'effective_hieu_luc',
            'is_expired',
            'ngay_het_hieu_luc',
            'link_thay_the',
            'ghi_chu',
            'file_dinh_kem',
            'attachments',
            'hien_thi',
            'don_vi_id',
            'nguoi_tao',
            'nguoi_tao_name',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'nguoi_tao', 'created_at', 'updated_at', 'is_expired', 'effective_hieu_luc']

    def to_internal_value(self, data):
        if hasattr(data, '_mutable'):
            # Tránh gọi data.copy() trên QueryDict vì QueryDict.copy() thực hiện deepcopy,
            # gây lỗi TypeError: cannot pickle 'BufferedRandom' instances khi đính kèm TemporaryUploadedFile
            orig_mutable = data._mutable
            data._mutable = True
            try:
                if data.get('ngay_het_hieu_luc') == '':
                    data['ngay_het_hieu_luc'] = None
                if data.get('link_thay_the') is None:
                    data['link_thay_the'] = ''
                return super().to_internal_value(data)
            finally:
                data._mutable = orig_mutable
        else:
            if isinstance(data, dict):
                data = data.copy()
            if data.get('ngay_het_hieu_luc') == '':
                data['ngay_het_hieu_luc'] = None
            if data.get('link_thay_the') is None:
                data['link_thay_the'] = ''
            return super().to_internal_value(data)

    def get_loai_tai_lieu_names(self, obj):
        return [loai.ten_loai for loai in obj.loai_tai_lieu.all()]

    def get_nguoi_tao_name(self, obj):
        if not obj.nguoi_tao:
            return None
        return obj.nguoi_tao.get_full_name() or obj.nguoi_tao.username

    def validate_file_dinh_kem(self, value):
        if value:
            validate_document_file(value)
        return value

    def validate(self, attrs):
        ngay_dang = attrs.get('ngay_dang') or (self.instance.ngay_dang if self.instance else None)
        ngay_het_hieu_luc = attrs.get('ngay_het_hieu_luc') if 'ngay_het_hieu_luc' in attrs else (self.instance.ngay_het_hieu_luc if self.instance else None)
        if ngay_het_hieu_luc and ngay_dang and ngay_het_hieu_luc < ngay_dang:
            raise serializers.ValidationError({
                'ngay_het_hieu_luc': 'Ngày hết hiệu lực không thể trước ngày đăng / ngày ban hành.'
            })

        hieu_luc = attrs.get('hieu_luc') or (self.instance.hieu_luc if self.instance else 'CON_HIEU_LUC')
        link_thay_the = attrs.get('link_thay_the') if 'link_thay_the' in attrs else (self.instance.link_thay_the if self.instance else '')
        if hieu_luc == 'HET_VA_THAY_THE' and not (link_thay_the and link_thay_the.strip()):
            raise serializers.ValidationError({
                'link_thay_the': 'Vui lòng cung cấp link văn bản thay thế khi chọn trạng thái Hết hiệu lực và thay thế.'
            })
        if hieu_luc == 'CON_HIEU_LUC':
            attrs['link_thay_the'] = ''
            if 'ngay_het_hieu_luc' not in attrs:
                attrs['ngay_het_hieu_luc'] = None
        elif hieu_luc in ('CON_HIEU_LUC_1_PHAN', 'HET_HIEU_LUC'):
            attrs['link_thay_the'] = ''

        # Kiểm tra tính hợp lệ và dung lượng (<= 20MB) của các tệp đính kèm trong request.FILES
        request = self.context.get('request')
        if request and hasattr(request, 'FILES') and hasattr(request.FILES, 'getlist'):
            for f in request.FILES.getlist('files'):
                try:
                    validate_document_file(f)
                except DjangoValidationError as exc:
                    msg = exc.messages if hasattr(exc, 'messages') else [str(exc)]
                    raise serializers.ValidationError({'files': msg})

        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Chỉ trả về các tệp đính kèm chưa bị xóa mềm (is_deleted=False)
        active_attachments = [att for att in instance.attachments.all() if not att.is_deleted]
        data['attachments'] = ChiTietTaiLieuAttachmentSerializer(active_attachments, many=True, context=self.context).data
        first_att = active_attachments[-1] if active_attachments else None
        data['file_dinh_kem'] = first_att.path if first_att else ''
        return data

    def create(self, validated_data):
        loai_tai_lieu = validated_data.pop('loai_tai_lieu', [])
        file_dinh_kem = validated_data.pop('file_dinh_kem', None)
        if not validated_data.get('ngay_dang'):
            from django.utils import timezone
            validated_data['ngay_dang'] = timezone.localdate()
        instance = TaiLieuChiTiet.objects.create(**validated_data)
        if loai_tai_lieu:
            instance.loai_tai_lieu.set(loai_tai_lieu)

        # Hỗ trợ đính kèm nhiều tệp từ request.FILES ('files' hoặc 'file_dinh_kem')
        request = self.context.get('request')
        uploaded_files = []
        if request and hasattr(request, 'FILES') and hasattr(request.FILES, 'getlist'):
            uploaded_files = request.FILES.getlist('files') or request.FILES.getlist('file_dinh_kem')
        if not uploaded_files and file_dinh_kem:
            uploaded_files = [file_dinh_kem]

        if uploaded_files:
            for f in uploaded_files:
                validate_document_file(f)
                ChiTietTaiLieuAttachment.objects.create(
                    document=instance,
                    name=f.name,
                    path=store_template_file(f),
                    file_size=getattr(f, 'size', None),
                    mime_type=getattr(f, 'content_type', None),
                    nguoi_tao=instance.nguoi_tao
                )
        return instance

    def update(self, instance, validated_data):
        loai_tai_lieu = validated_data.pop('loai_tai_lieu', None)
        file_dinh_kem = validated_data.pop('file_dinh_kem', None)
        validated_data.pop('nguoi_tao', None)
        validated_data.pop('ngay_dang', None)  # Ngày đăng cố định theo ngày tạo, không cho phép chỉnh sửa

        hieu_luc = validated_data.get('hieu_luc', instance.hieu_luc)
        if hieu_luc == 'CON_HIEU_LUC':
            validated_data['ngay_het_hieu_luc'] = None
            validated_data['link_thay_the'] = ''
        elif hieu_luc in ('CON_HIEU_LUC_1_PHAN', 'HET_HIEU_LUC'):
            validated_data['link_thay_the'] = ''

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if loai_tai_lieu is not None:
            instance.loai_tai_lieu.set(loai_tai_lieu)

        request = self.context.get('request')
        # Hỗ trợ xóa các tệp đính kèm được chọn xóa (an toàn cho cả multipart QueryDict và JSON dict)
        if request and hasattr(request, 'data'):
            if hasattr(request.data, 'getlist'):
                deleted_ids = request.data.getlist('deleted_attachment_ids')
            else:
                raw_deleted = request.data.get('deleted_attachment_ids')
                if isinstance(raw_deleted, (list, tuple)):
                    deleted_ids = raw_deleted
                elif raw_deleted:
                    deleted_ids = [raw_deleted]
                else:
                    deleted_ids = []

            if deleted_ids:
                instance.attachments.filter(id__in=deleted_ids).update(is_deleted=True)
                if hasattr(instance, '_prefetched_objects_cache') and 'attachments' in instance._prefetched_objects_cache:
                    del instance._prefetched_objects_cache['attachments']

        # Hỗ trợ thêm nhiều tệp đính kèm khi cập nhật
        uploaded_files = []
        if request and hasattr(request, 'FILES') and hasattr(request.FILES, 'getlist'):
            uploaded_files = request.FILES.getlist('files') or request.FILES.getlist('file_dinh_kem')
        if not uploaded_files and file_dinh_kem:
            uploaded_files = [file_dinh_kem]

        if uploaded_files:
            for f in uploaded_files:
                validate_document_file(f)
                ChiTietTaiLieuAttachment.objects.create(
                    document=instance,
                    name=f.name,
                    path=store_template_file(f),
                    file_size=getattr(f, 'size', None),
                    mime_type=getattr(f, 'content_type', None),
                    nguoi_tao=instance.nguoi_tao
                )
            if hasattr(instance, '_prefetched_objects_cache') and 'attachments' in instance._prefetched_objects_cache:
                del instance._prefetched_objects_cache['attachments']

        return instance
