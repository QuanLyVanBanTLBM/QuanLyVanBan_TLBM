from rest_framework import serializers
from .models import DanhMucTaiLieu, LoaiTaiLieu, TaiLieuChiTiet, ChiTietTaiLieuAttachment, validate_document_file


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
        read_only_fields = ['id', 'nguoi_tao', 'created_at', 'updated_at']

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
        hieu_luc = attrs.get('hieu_luc') or (self.instance.hieu_luc if self.instance else 'CON_HIEU_LUC')
        link_thay_the = attrs.get('link_thay_the') or (self.instance.link_thay_the if self.instance else '')
        if hieu_luc == 'HET_VA_THAY_THE' and not (link_thay_the and link_thay_the.strip()):
            raise serializers.ValidationError({
                'link_thay_the': 'Vui lòng cung cấp link văn bản thay thế khi chọn trạng thái Hết hiệu lực và thay thế.'
            })
        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        first_att = instance.attachments.filter(is_deleted=False).last()
        data['file_dinh_kem'] = first_att.path if first_att else ''
        return data

    def create(self, validated_data):
        loai_tai_lieu = validated_data.pop('loai_tai_lieu', [])
        file_dinh_kem = validated_data.pop('file_dinh_kem', None)
        instance = TaiLieuChiTiet.objects.create(**validated_data)
        if loai_tai_lieu:
            instance.loai_tai_lieu.set(loai_tai_lieu)
        if file_dinh_kem:
            from django.core.files.storage import default_storage
            file_path = default_storage.save(f"documents/templates/{file_dinh_kem.name}", file_dinh_kem)
            storage_path = f"/media/{file_path}" if not file_path.startswith('/media/') else file_path
            ChiTietTaiLieuAttachment.objects.create(
                document=instance,
                name=file_dinh_kem.name,
                path=storage_path,
                file_size=getattr(file_dinh_kem, 'size', None),
                mime_type=getattr(file_dinh_kem, 'content_type', None),
                nguoi_tao=instance.nguoi_tao
            )
        return instance

    def update(self, instance, validated_data):
        loai_tai_lieu = validated_data.pop('loai_tai_lieu', None)
        file_dinh_kem = validated_data.pop('file_dinh_kem', None)
        validated_data.pop('nguoi_tao', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if loai_tai_lieu is not None:
            instance.loai_tai_lieu.set(loai_tai_lieu)
        if file_dinh_kem:
            from django.core.files.storage import default_storage
            file_path = default_storage.save(f"documents/templates/{file_dinh_kem.name}", file_dinh_kem)
            storage_path = f"/media/{file_path}" if not file_path.startswith('/media/') else file_path
            ChiTietTaiLieuAttachment.objects.create(
                document=instance,
                name=file_dinh_kem.name,
                path=storage_path,
                file_size=getattr(file_dinh_kem, 'size', None),
                mime_type=getattr(file_dinh_kem, 'content_type', None),
                nguoi_tao=instance.nguoi_tao
            )
        return instance
