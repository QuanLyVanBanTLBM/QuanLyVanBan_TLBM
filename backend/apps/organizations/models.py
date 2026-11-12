import re

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

# SĐT đơn vị: số cố định/di động Việt Nam, đầu 0 hoặc +84 (cùng quy ước với SĐT CBNV).
PHONE_PATTERN = r"(0|\+84)[235789]\d{8,9}"


def normalize_phone(value: str) -> str:
    """Bỏ khoảng trắng, dấu chấm, gạch nối trước khi so mẫu; giá trị lưu giữ nguyên như người nhập."""
    return re.sub(r"[\s.-]", "", value or "")


class KhoiKhuVuc(models.Model):
    """
    Tier 1: Region / Block.
    """
    # DDL không có UNIQUE cho tên Khối; trùng tên được chặn ở serializer (so không phân biệt hoa thường).
    ten = models.CharField(
        max_length=255,
        verbose_name="organizations.region.nameLabel",
    )

    thu_tu_hien_thi = models.IntegerField(
        default=0,
        db_default=0,
        validators=[MinValueValidator(0)],
        verbose_name="organizations.region.displayOrderLabel",
        help_text="organizations.region.displayOrderHelp",
    )

    class Meta:
        db_table = "organizations_khoi"
        app_label = "organizations"
        verbose_name = "organizations.tabs.regions"
        verbose_name_plural = "organizations.tabs.regions"
        ordering = ["thu_tu_hien_thi", "ten"]

    def clean(self):
        super().clean()
        self.ten = self.ten.strip()
        if not self.ten:
            raise ValidationError({"ten": "organizations.messages.nameRequired"})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.ten


class DonVi(models.Model):
    """
    Tier 2: Unit / Department.
    """
    khoi = models.ForeignKey(
        KhoiKhuVuc,
        on_delete=models.PROTECT,
        db_index=False,
        related_name="don_vi_list",
        verbose_name="organizations.unit.regionLabel",
    )
    stt_uu_tien = models.IntegerField(
        unique=True,
        validators=[MinValueValidator(1)],
        verbose_name="organizations.unit.priorityLabel",
        help_text="organizations.unit.priorityHelp",
    )
    ten = models.CharField(
        max_length=255,
        verbose_name="organizations.unit.nameLabel",
    )
    dia_chi = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        default="",
        verbose_name="organizations.unit.addressLabel",
    )
    dien_thoai = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        default="",
        verbose_name="organizations.unit.phoneLabel",
    )
    email = models.EmailField(
        null=True,
        blank=True,
        default="",
        verbose_name="organizations.unit.emailLabel",
    )
    is_public = models.BooleanField(
        default=True,
        db_default=True,
        verbose_name="organizations.unit.isPublicLabel",
        help_text="organizations.unit.isPublicHelp",
    )
    ghi_chu = models.TextField(
        null=True,
        blank=True,
        default="",
        verbose_name="organizations.unit.notesLabel",
    )

    class Meta:
        db_table = "organizations_donvi"
        app_label = "organizations"
        verbose_name = "organizations.tabs.units"
        verbose_name_plural = "organizations.tabs.units"
        ordering = ["stt_uu_tien", "ten"]
        indexes = [
            models.Index(fields=["khoi"], name="idx_donvi_khoi"),
        ]
        permissions = [
            ("export_donvi", "organizations.unit.exportPermission"),
        ]

    def clean(self):
        super().clean()
        errors = {}

        self.ten = self.ten.strip()
        if not self.ten:
            errors["ten"] = "organizations.messages.nameRequired"

        if self.stt_uu_tien is not None and self.stt_uu_tien <= 0:
            errors["stt_uu_tien"] = "organizations.messages.priorityPositive"

        if self.dien_thoai:
            if not re.fullmatch(PHONE_PATTERN, normalize_phone(self.dien_thoai)):
                errors["dien_thoai"] = "organizations.messages.phoneInvalid"

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.ten} ({self.khoi.ten})"
