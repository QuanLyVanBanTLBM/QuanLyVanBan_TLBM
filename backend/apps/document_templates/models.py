import os
from django.db import models
from django.core.exceptions import ValidationError
from django.conf import settings
from django.db.models import Max


# Hàm kiểm tra định dạng và dung lượng file đính kèm (< 20MB)
def validate_document_file(file):
    max_size_mb = 20
    if hasattr(file, 'size') and file.size > max_size_mb * 1024 * 1024:
        raise ValidationError(f"Dung lượng tệp đính kèm không được vượt quá {max_size_mb}MB.")

    valid_extensions = ['.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png', '.zip', '.rar']
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in valid_extensions:
        raise ValidationError(
            f"Định dạng tệp {ext} không được hỗ trợ. Chỉ chấp nhận PDF, DOC, DOCX, JPG, PNG, ZIP, RAR."
        )


class DanhMucTaiLieu(models.Model):
    """
    1. Danh mục Cấp 1 (Khớp bảng records_tailieu trong SQL)
    """
    stt_uu_tien = models.SmallIntegerField(unique=True, verbose_name="STT ưu tiên")
    ky_hieu = models.CharField(max_length=255, blank=True, null=True, verbose_name="Số ký hiệu")
    ten_tai_lieu = models.CharField(max_length=255, verbose_name="Tên tài liệu")
    nguoi_lap = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        db_column="nguoi_lap_id",
        verbose_name="Người lập"
    )
    ngay_lap = models.DateField(null=True, blank=True, verbose_name="Ngày lập")
    ghi_chu = models.TextField(blank=True, null=True, verbose_name="Ghi chú")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "records_tailieu"
        ordering = ["stt_uu_tien"]
        verbose_name = "Danh mục Tài liệu (Cấp 1)"
        verbose_name_plural = "Danh mục Tài liệu (Cấp 1)"

    def __str__(self):
        if self.ky_hieu:
            return f"[{self.ky_hieu}] {self.ten_tai_lieu}"
        return self.ten_tai_lieu

    def save(self, *args, **kwargs):
        if not self.stt_uu_tien:
            max_order = DanhMucTaiLieu.objects.aggregate(max_val=Max('stt_uu_tien'))['max_val']
            self.stt_uu_tien = (max_order or 0) + 1
        super().save(*args, **kwargs)


class LoaiTaiLieu(models.Model):
    """
    2. Loại tài liệu Cấp 2 (Khớp bảng records_loaitailieu trong SQL)
    """
    dm_tai_lieu = models.ForeignKey(
        DanhMucTaiLieu,
        on_delete=models.RESTRICT,
        db_column="dm_tai_lieu",
        related_name="danh_sach_loai",
        verbose_name="Thuộc danh mục cấp 1"
    )
    ten_loai = models.CharField(max_length=255, verbose_name="Tên loại tài liệu")
    is_public = models.BooleanField(default=True, verbose_name="Công khai")
    ngay_lap = models.DateTimeField(null=True, blank=True, verbose_name="Ngày lập")
    ghi_chu = models.TextField(blank=True, null=True, verbose_name="Ghi chú")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "records_loaitailieu"
        ordering = ["id"]
        verbose_name = "Loại tài liệu (Cấp 2)"
        verbose_name_plural = "Loại tài liệu (Cấp 2)"

    def __str__(self):
        return f"{self.ten_loai} ({self.dm_tai_lieu.ten_tai_lieu})"


class TaiLieuChiTiet(models.Model):
    """
    3. Chi tiết tài liệu chung (Khớp bảng records_chitiettailieu trong SQL)
    """
    HIEU_LUC_CHOICES = [
        ('CON_HIEU_LUC', 'Còn hiệu lực'),
        ('CON_HIEU_LUC_1_PHAN', 'Còn hiệu lực một phần'),
        ('HET_HIEU_LUC', 'Hết hiệu lực'),
        ('HET_VA_THAY_THE', 'Hết hiệu lực và thay thế'),
    ]

    HIEN_THI_CHOICES = [
        ('TAT_CA', 'Tất cả'),
        ('NOI_BO_PHONG_BAN', 'Nội bộ phòng ban'),
    ]

    dm_tai_lieu = models.ForeignKey(
        DanhMucTaiLieu,
        on_delete=models.RESTRICT,
        db_column="dm_tai_lieu",
        related_name='tai_lieu_thuoc_danh_muc',
        verbose_name="Danh mục tài liệu (Cấp 1)"
    )
    loai_tai_lieu = models.ManyToManyField(
        LoaiTaiLieu,
        through='ChiTietTaiLieuLoaiTaiLieu',
        blank=True,
        related_name='tai_lieu_thuoc_loai',
        verbose_name="Loại tài liệu (Cấp 2)"
    )
    ky_hieu = models.CharField(max_length=255, blank=True, null=True, verbose_name="Ký hiệu tài liệu")
    tieu_de = models.CharField(max_length=255, verbose_name="Tiêu đề")
    ngay_dang = models.DateField(verbose_name="Ngày đăng")
    noi_ban_hanh = models.CharField(max_length=255, blank=True, null=True, verbose_name="Nơi ban hành")
    hieu_luc = models.CharField(
        max_length=30,
        choices=HIEU_LUC_CHOICES,
        default='CON_HIEU_LUC',
        verbose_name="Hiệu lực"
    )
    ngay_het_hieu_luc = models.DateField(blank=True, null=True, verbose_name="Ngày hết hiệu lực")
    link_thay_the = models.CharField(max_length=500, blank=True, null=True, verbose_name="Link văn bản thay thế")
    ghi_chu = models.TextField(blank=True, null=True, verbose_name="Ghi chú")
    hien_thi = models.CharField(
        max_length=30,
        choices=HIEN_THI_CHOICES,
        default='TAT_CA',
        verbose_name="Hiển thị"
    )
    don_vi_id = models.BigIntegerField(
        null=True,
        blank=True,
        db_column='don_vi_id',
        db_index=True,
        verbose_name="Đơn vị sở hữu"
    )
    nguoi_tao = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="nguoi_tao_id",
        verbose_name="Người tạo"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "records_chitiettailieu"
        ordering = ["-ngay_dang", "-id"]
        verbose_name = "Chi tiết Tài liệu & Biểu mẫu"
        verbose_name_plural = "Danh sách Chi tiết Tài liệu & Biểu mẫu"

    def __init__(self, *args, **kwargs):
        file_dinh_kem = kwargs.pop('file_dinh_kem', None)
        super().__init__(*args, **kwargs)
        if file_dinh_kem:
            self._temp_file_dinh_kem = file_dinh_kem

    @property
    def file_dinh_kem(self):
        att = self.attachments.filter(is_deleted=False).last()
        return att.path if att else ""

    def __str__(self):
        return f"{self.tieu_de} ({self.get_hieu_luc_display()})"

    def clean(self):
        super().clean()
        if hasattr(self, '_temp_file_dinh_kem') and self._temp_file_dinh_kem:
            validate_document_file(self._temp_file_dinh_kem)
        if self.hieu_luc == 'HET_VA_THAY_THE' and not (self.link_thay_the and self.link_thay_the.strip()):
            raise ValidationError({
                'link_thay_the': 'Vui lòng cung cấp link văn bản thay thế khi chọn trạng thái Hết hiệu lực và thay thế.'
            })

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if hasattr(self, '_temp_file_dinh_kem') and self._temp_file_dinh_kem:
            from django.core.files.storage import default_storage
            file = self._temp_file_dinh_kem
            file_path = default_storage.save(f"documents/templates/{file.name}", file)
            storage_path = f"/media/{file_path}" if not file_path.startswith('/media/') else file_path
            ChiTietTaiLieuAttachment.objects.create(
                document=self,
                name=file.name,
                path=storage_path,
                file_size=getattr(file, 'size', None),
                mime_type=getattr(file, 'content_type', None),
                nguoi_tao=self.nguoi_tao
            )
            self._temp_file_dinh_kem = None


class ChiTietTaiLieuLoaiTaiLieu(models.Model):
    """
    Bảng nối Nhiều - Nhiều giữa Chi tiết tài liệu và Loại tài liệu cấp 2
    Khớp bảng records_chitiettailieu_loaitailieu trong DDL Base (Khóa chính ghép)
    """
    pk = models.CompositePrimaryKey('chitiettailieu', 'loaitailieu')
    chitiettailieu = models.ForeignKey(
        TaiLieuChiTiet,
        on_delete=models.CASCADE,
        db_column='chitiettailieu_id',
        verbose_name="Chi tiết tài liệu"
    )
    loaitailieu = models.ForeignKey(
        LoaiTaiLieu,
        on_delete=models.RESTRICT,
        db_column='loaitailieu_id',
        verbose_name="Loại tài liệu"
    )

    class Meta:
        db_table = "records_chitiettailieu_loaitailieu"
        verbose_name = "Chi tiết tài liệu - Loại tài liệu"
        verbose_name_plural = "Chi tiết tài liệu - Loại tài liệu"


class ChiTietTaiLieuAttachment(models.Model):
    """
    4. Tệp đính kèm Chi tiết tài liệu (Khớp bảng records_chitiettailieu_attachment trong DDL Base)
    Chuẩn hóa 1-N Hướng A theo GVHD Thầy Duy chốt.
    Chuẩn hóa tên cột: created_at, nguoi_tao_id theo PR #96 / PR #101.
    """
    document = models.ForeignKey(
        TaiLieuChiTiet,
        on_delete=models.CASCADE,
        related_name='attachments',
        db_column='document_id',
        verbose_name="Tài liệu"
    )
    name = models.CharField(max_length=255, verbose_name="Tên gốc file")
    path = models.CharField(max_length=500, verbose_name="Đường dẫn lưu file")
    file_size = models.BigIntegerField(null=True, blank=True, verbose_name="Dung lượng (byte)")
    mime_type = models.CharField(max_length=255, null=True, blank=True, verbose_name="Kiểu MIME")
    is_deleted = models.BooleanField(default=False, verbose_name="Xóa mềm")
    created_at = models.DateTimeField(auto_now_add=True, db_column='created_at', verbose_name="Thời điểm tải lên")
    nguoi_tao = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='nguoi_tao_id',
        verbose_name="Người tải file"
    )

    # Property alias hỗ trợ tương thích ngược (backward compatibility)
    @property
    def created_time(self):
        return self.created_at

    @property
    def created_user(self):
        return self.nguoi_tao

    class Meta:
        db_table = "records_chitiettailieu_attachment"
        verbose_name = "Tệp đính kèm tài liệu"
        verbose_name_plural = "Tệp đính kèm tài liệu"
        indexes = [
            models.Index(fields=['document'], name='idx_chitiettailieu_att_doc'),
            models.Index(fields=['is_deleted'], name='idx_chitiettailieu_att_del'),
        ]

    def __str__(self):
        return f"{self.name} ({self.document.tieu_de})"
