"""
Các models cho phân hệ Cơ cấu Tổ chức & Đơn vị (Module 7.3 - Nhóm 7).
Tác giả: Lê Duy Khánh.
"""
from django.db import models
from django.db.models import Max
from django.core.validators import RegexValidator


# Validator số điện thoại Việt Nam (di động 10 số hoặc máy bàn 10-11 số)
vietnam_phone_regex = RegexValidator(
    regex=r"^(0|\+84)[1-9][0-9]{7,9}$",
    message="Số điện thoại không hợp lệ. Vui lòng nhập định dạng Việt Nam hợp lệ (ví dụ: 0912345678 hoặc 0281234567).",
)


class KhoiKhuVuc(models.Model):
    """
    Cấp 1 của Cơ cấu tổ chức: Khối / Khu vực.
    Bảng CSDL: organizations_khoi
    """

    ten = models.CharField(
        max_length=255,
        verbose_name="Tên khối / khu vực",
        help_text="Bắt buộc nhập, ví dụ: KHU VỰC MIỀN NAM, KHỐI VĂN PHÒNG...",
    )
    thu_tu_hien_thi = models.PositiveIntegerField(
        default=0,
        verbose_name="Thứ tự hiển thị",
        help_text="Thứ tự hiển thị sắp xếp từ nhỏ đến lớn.",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Ngày tạo",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Ngày cập nhật",
    )

    class Meta:
        db_table = "organizations_khoi"
        verbose_name = "Khối / Khu vực"
        verbose_name_plural = "Danh mục Khối / Khu vực"
        ordering = ["thu_tu_hien_thi", "ten", "id"]

    def __str__(self):
        return self.ten


class DonVi(models.Model):
    """
    Cấp 2 của Cơ cấu tổ chức: Đơn vị / Phòng ban.
    Trực thuộc Khối / Khu vực (Cấp 1).
    Bảng CSDL: organizations_donvi
    """

    khoi = models.ForeignKey(
        KhoiKhuVuc,
        on_delete=models.RESTRICT,
        related_name="don_vi_list",
        verbose_name="Khối / Khu vực",
        help_text="Chọn Khối / Khu vực cấp trên trực thuộc.",
    )
    stt_uu_tien = models.PositiveIntegerField(
        unique=True,
        verbose_name="STT ưu tiên hiển thị",
        help_text="Số nguyên dương duy nhất. Nếu không nhập, hệ thống tự động lấy Max + 1.",
    )
    ten = models.CharField(
        max_length=255,
        verbose_name="Tên đơn vị, phòng/ban",
        help_text="Bắt buộc nhập, ví dụ: Phòng Hành chính Tổng hợp, Bảo Long Khánh Hòa...",
    )
    dia_chi = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="Địa chỉ trụ sở / văn phòng",
    )
    dien_thoai = models.CharField(
        max_length=20,
        blank=True,
        default="",
        validators=[vietnam_phone_regex],
        verbose_name="Số điện thoại liên hệ",
    )
    email = models.EmailField(
        max_length=254,
        blank=True,
        default="",
        verbose_name="Hộp thư điện tử (Email)",
    )
    is_public = models.BooleanField(
        default=True,
        verbose_name="Hiển thị công khai (isPublic)",
        help_text="Mặc định True. Nếu False vẫn hiển thị cho Admin nhưng được cảnh báo đổi màu.",
    )
    ghi_chu = models.TextField(
        blank=True,
        default="",
        verbose_name="Ghi chú thêm",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Ngày tạo",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Ngày cập nhật",
    )

    class Meta:
        db_table = "organizations_donvi"
        verbose_name = "Đơn vị / Phòng ban"
        verbose_name_plural = "Danh mục Đơn vị / Phòng ban"
        ordering = ["stt_uu_tien", "ten", "id"]
        permissions = [
            ("export_donvi", "Can export don vi list to Excel"),
        ]

    def __str__(self):
        return f"{self.ten} ({self.khoi.ten})"

    @classmethod
    def get_next_stt(cls) -> int:
        """
        Tính số thứ tự ưu tiên tiếp theo (Max + 1).
        """
        latest = cls.objects.order_by("-stt_uu_tien").first()
        return (latest.stt_uu_tien + 1) if latest else 1

    def save(self, *args, **kwargs):
        # Tự động gán stt_uu_tien nếu chưa được thiết lập
        if not self.stt_uu_tien:
            self.stt_uu_tien = self.get_next_stt()
        super().save(*args, **kwargs)
