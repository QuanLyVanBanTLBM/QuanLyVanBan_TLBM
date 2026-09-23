from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone


class PhongHop(models.Model):
    """
    Danh mục phòng họp của cơ quan / đơn vị.
    """
    ten_phong = models.CharField(
        max_length=150,
        unique=True,
        verbose_name="Tên phòng họp",
        help_text="Tên nhận diện phòng họp (duy nhất)",
    )
    vi_tri = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="Vị trí phòng",
        help_text="Tầng, tòa nhà hoặc khu vực",
    )
    suc_chua = models.PositiveIntegerField(
        default=10,
        verbose_name="Sức chứa (người)",
        help_text="Số lượng người tham gia tối đa",
    )
    thiet_bi = models.TextField(
        blank=True,
        default="",
        verbose_name="Trang thiết bị",
        help_text="Mô tả thiết bị có sẵn (Máy chiếu, Micro, Hội nghị truyền hình...)",
    )
    is_public = models.BooleanField(
        default=True,
        verbose_name="Hiển thị công khai",
        help_text="Trạng thái phòng có đang sẵn sàng cho CBNV đặt hay không",
    )
    ghi_chu = models.TextField(
        blank=True,
        default="",
        verbose_name="Ghi chú",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Ngày tạo",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Cập nhật lần cuối",
    )

    class Meta:
        verbose_name = "Phòng họp"
        verbose_name_plural = "Danh mục phòng họp"
        ordering = ["ten_phong"]

    def __str__(self):
        return f"{self.ten_phong} (Sức chứa: {self.suc_chua})"

    def clean(self):
        if self.suc_chua <= 0:
            raise ValidationError({"suc_chua": "Sức chứa phòng họp phải lớn hơn 0."})


class DatPhongHop(models.Model):
    """
    Lịch đặt phòng họp & giữ chỗ khung giờ.
    Chống đặt trùng lặp các lịch có hiệu lực trong cùng phòng họp.
    """

    STATUS_DA_DAT = "da_dat"
    STATUS_DA_HUY = "da_huy"
    STATUS_HOAN_THANH = "hoan_thanh"

    STATUS_CHOICES = [
        (STATUS_DA_DAT, "Đã đặt"),
        (STATUS_DA_HUY, "Đã hủy"),
        (STATUS_HOAN_THANH, "Đã hoàn thành"),
    ]

    phong_hop = models.ForeignKey(
        PhongHop,
        on_delete=models.PROTECT,
        related_name="bookings",
        verbose_name="Phòng họp",
    )
    nguoi_dat = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="meeting_bookings",
        verbose_name="Người đặt",
    )
    don_vi_to_chuc = models.CharField(
        max_length=200,
        blank=True,
        default="",
        verbose_name="Đơn vị tổ chức",
    )
    tieu_de = models.CharField(
        max_length=255,
        verbose_name="Tiêu đề cuộc họp / Nội dung",
    )
    thoi_gian_bat_dau = models.DateTimeField(
        verbose_name="Thời gian bắt đầu",
    )
    thoi_gian_ket_thuc = models.DateTimeField(
        verbose_name="Thời gian kết thúc",
    )
    so_nguoi_tham_gia = models.PositiveIntegerField(
        default=1,
        verbose_name="Số người tham gia",
    )
    trang_thai = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_DA_DAT,
        verbose_name="Trạng thái",
    )
    ghi_chu = models.TextField(
        blank=True,
        default="",
        verbose_name="Ghi chú",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Ngày tạo",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Cập nhật lần cuối",
    )

    class Meta:
        verbose_name = "Lịch đặt phòng họp"
        verbose_name_plural = "Danh sách đặt phòng họp"
        ordering = ["-thoi_gian_bat_dau"]
        permissions = [
            ("cancel_datphonghop", "Có thể hủy lịch đặt phòng họp"),
        ]

    def __str__(self):
        return f"[{self.phong_hop.ten_phong}] {self.tieu_de} ({self.thoi_gian_bat_dau:%d/%m/%Y %H:%M} - {self.thoi_gian_ket_thuc:%H:%M})"

    def clean(self):
        super().clean()
        if self.thoi_gian_bat_dau and self.thoi_gian_ket_thuc:
            if self.thoi_gian_bat_dau >= self.thoi_gian_ket_thuc:
                raise ValidationError({
                    "thoi_gian_ket_thuc": "Thời gian kết thúc phải diễn ra sau thời gian bắt đầu."
                })

            if self.so_nguoi_tham_gia <= 0:
                raise ValidationError({
                    "so_nguoi_tham_gia": "Số người tham gia phải lớn hơn 0."
                })

            # Kiểm tra sức chứa phòng họp nếu vượt quá quá nhiều
            if hasattr(self, "phong_hop") and self.phong_hop_id:
                if self.so_nguoi_tham_gia > self.phong_hop.suc_chua:
                    raise ValidationError({
                        "so_nguoi_tham_gia": f"Số người tham gia ({self.so_nguoi_tham_gia}) vượt quá sức chứa tối đa của phòng ({self.phong_hop.suc_chua})."
                    })

            # Kiểm tra trùng lịch đối với lịch có hiệu lực (khác da_huy)
            if self.trang_thai != self.STATUS_DA_HUY and self.phong_hop_id:
                conflicts = DatPhongHop.objects.filter(
                    phong_hop_id=self.phong_hop_id,
                    thoi_gian_bat_dau__lt=self.thoi_gian_ket_thuc,
                    thoi_gian_ket_thuc__gt=self.thoi_gian_bat_dau,
                ).exclude(trang_thai=self.STATUS_DA_HUY)

                if self.pk:
                    conflicts = conflicts.exclude(pk=self.pk)

                if conflicts.exists():
                    conflict = conflicts.first()
                    nguoi_dat_name = conflict.nguoi_dat.get_full_name() or conflict.nguoi_dat.username
                    if hasattr(conflict.nguoi_dat, "profile") and conflict.nguoi_dat.profile.full_name:
                        nguoi_dat_name = conflict.nguoi_dat.profile.full_name

                    tz = timezone.get_current_timezone()
                    c_start = timezone.localtime(conflict.thoi_gian_bat_dau, tz).strftime("%H:%M")
                    c_end = timezone.localtime(conflict.thoi_gian_ket_thuc, tz).strftime("%H:%M %d/%m/%Y")
                    raise ValidationError({
                        "non_field_errors": f"Khung giờ này đã bị trùng với cuộc họp '{conflict.tieu_de}' ({c_start} - {c_end}) bởi {nguoi_dat_name}."
                    })
