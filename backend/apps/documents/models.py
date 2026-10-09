"""
Models cho Module Văn Bản (Đến / Đi) — Kiến trúc theo chuẩn CSDL QLVB&TL.

Kiến trúc:
1. VanBanDen  (db_table: 'documents_vanbanden')   — Văn bản Đến
2. VanBanDi   (db_table: 'documents_vanbandi')    — Văn bản Đi
Cả 2 model kế thừa từ abstract model BaseVanBan chứa các trường chung, tránh trùng lặp mã.
Văn bản hạn chế được quản lý qua cờ pham_vi = 'HAN_CHE' (theo Issue #82 & DDL chuẩn hóa).

Tệp đính kèm (Attachment - Hướng A: 7 trường):
- VanBanDenAttachment  (db_table: 'documents_vanbanden_attachment')
- VanBanDiAttachment   (db_table: 'documents_vanbandi_attachment')

Bảng liên kết & M2M Through models (Khớp 100% DDL):
- documents_vanbanden_nguoinhan  (VanBanDenNguoiNhan)
- documents_vanbanden_hoso       (VanBanDenHoSo)
- documents_vanbanden_danhmuc     (VanBanDenDanhmuc)
- documents_vanbanden_donvinhan  (VanBanDenDonViNhan)
- documents_vanbandi_nguoinhan   (VanBanDiNguoiNhan)
- documents_vanbandi_hoso        (VanBanDiHoSo)
- documents_vanbandi_danhmuc      (VanBanDiDanhmuc)
- documents_vanbandi_noibanhanh  (VanBanDiNoiBanHanh)
- documents_vanbandi_donvinhan   (VanBanDiDonViNhan)

Lịch sử & Nhật ký:
- DocumentViewLog    (db_table: 'documents_view_log')
- DocumentAccessLog  (db_table: 'documents_access_log')

Đồng thời cung cấp Facade / Helper `Document` và `DocumentAttachment` để đảm bảo tương thích ngược.
"""

import os
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError, models, transaction
from django.utils import timezone


# ═══════════════════════════════════════════════════════════════════
# ENUM & Choices
# ═══════════════════════════════════════════════════════════════════

class PhamVi(models.TextChoices):
    NOI_BO = "NOI_BO", "Nội bộ"
    HAN_CHE = "HAN_CHE", "Hạn chế"


class LoaiVanBan(models.TextChoices):
    DEN = "DEN", "Văn bản Đến"
    DI = "DI", "Văn bản Đi"


class HieuLuc(models.TextChoices):
    CON_HIEU_LUC = "CON_HIEU_LUC", "Còn hiệu lực"
    CON_HIEU_LUC_1_PHAN = "CON_HIEU_LUC_1_PHAN", "Còn hiệu lực 1 phần"
    HET_HIEU_LUC = "HET_HIEU_LUC", "Hết hiệu lực"
    HET_VA_THAY_THE = "HET_VA_THAY_THE", "Hết hiệu lực và thay thế"


# ═══════════════════════════════════════════════════════════════════
# Abstract Base Model
# ═══════════════════════════════════════════════════════════════════

class BaseVanBan(models.Model):
    """
    Model cơ sở trừu tượng chứa các trường dùng chung cho các phân hệ văn bản (Đến, Đi).
    """

    PhamVi = PhamVi
    HieuLuc = HieuLuc
    LoaiVanBan = LoaiVanBan

    # ── Phạm vi lưu hành (Issue #82: NOI_BO / HAN_CHE) ────────────
    pham_vi = models.CharField(
        "Phạm vi",
        max_length=20,
        choices=PhamVi.choices,
        default=PhamVi.NOI_BO,
        db_index=True,
        help_text="NOI_BO: Văn bản nội bộ; HAN_CHE: Văn bản hạn chế (mật nội bộ).",
    )

    # ── Năm & Ký hiệu ──────────────────────────────────────────────
    nam = models.PositiveSmallIntegerField(
        "Năm",
        default=timezone.now().year,
        db_index=True,
        help_text="Mặc định năm hiện tại, cho phép sửa.",
    )
    so_hieu = models.CharField(
        "Số, ký hiệu văn bản",
        max_length=255,
    )

    # ── Nội dung & Ngày (NOT NULL per DDL & NĐ 30/2020) ───────────
    trich_yeu = models.TextField("Trích yếu nội dung")
    ngay_van_ban = models.DateTimeField(
        "Ngày văn bản",
        default=timezone.now,
        help_text="Dùng để lọc/sắp xếp danh sách.",
    )
    nguoi_ky = models.CharField(
        "Người ký",
        max_length=255,
        blank=True,
        default="",
    )
    chuc_vu = models.CharField(
        "Chức vụ người ký",
        max_length=255,
        blank=True,
        default="",
    )

    # ── Hiệu lực ──────────────────────────────────────────────────
    hieu_luc = models.CharField(
        "Hiệu lực",
        max_length=20,
        choices=HieuLuc.choices,
        default=HieuLuc.CON_HIEU_LUC,
        db_index=True,
    )
    ngay_het_hieu_luc = models.DateTimeField(
        "Ngày hết hiệu lực",
        null=True,
        blank=True,
    )
    link_thay_the = models.CharField(
        "Link văn bản thay thế",
        max_length=500,
        blank=True,
        default="",
    )

    # ── Ghi chú & Cờ hệ thống ──────────────────────────────────────
    ghi_chu = models.TextField("Ghi chú", blank=True, default="")
    hien_thi = models.BooleanField(
        "Trạng thái hiển thị",
        default=True,
        help_text="False = ẩn với user thường, admin vẫn thấy (đổi màu).",
    )
    gui_mail_toan_he_thong = models.BooleanField(
        "Gửi mail toàn hệ thống",
        default=False,
    )

    # ── Audit ──────────────────────────────────────────────────────
    nguoi_tao = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Người tạo",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="nguoi_tao_id",
        related_name="%(class)s_created",
    )
    created_at = models.DateTimeField("Ngày tạo", auto_now_add=True)
    updated_at = models.DateTimeField("Ngày cập nhật", auto_now=True)

    class Meta:
        abstract = True

    def clean(self):
        super().clean()
        if self.pham_vi == self.PhamVi.HAN_CHE and self.gui_mail_toan_he_thong:
            raise ValidationError(
                {"gui_mail_toan_he_thong": "Văn bản hạn chế không được phép gửi email toàn hệ thống."}
            )

    def save(self, *args, **kwargs):
        if self.pk:
            old_inst = self.__class__.objects.filter(pk=self.pk).values("pham_vi").first()
            if old_inst and old_inst["pham_vi"] != self.pham_vi:
                raise ValidationError("Phạm vi văn bản không được đổi sau khi tạo.")
        if self.pham_vi == self.PhamVi.HAN_CHE:
            self.gui_mail_toan_he_thong = False
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.pham_vi == self.PhamVi.HAN_CHE:
            raise ValidationError("Văn bản hạn chế không được phép xóa.")
        return super().delete(*args, **kwargs)

    @property
    def is_expired(self):
        """Kiểm tra văn bản đã hết hiệu lực chưa."""
        return self.hieu_luc in (self.HieuLuc.HET_HIEU_LUC, self.HieuLuc.HET_VA_THAY_THE)

    @property
    def view_logs(self):
        """Lấy danh sách log người xem tương ứng."""
        return DocumentViewLog.objects.filter(
            document_type=self.document_kind,
            document_id=self.pk,
        ).order_by("-viewed_at")


# ═══════════════════════════════════════════════════════════════════
# 1. Văn bản Đến (documents_vanbanden)
# ═══════════════════════════════════════════════════════════════════

class VanBanDen(BaseVanBan):
    """
    Model quản lý Văn bản Đến — Nghị định 30/2020/NĐ-CP.
    Khớp 100% với bảng vật lý `documents_vanbanden`.
    """

    loai = "DEN"
    document_kind = "vanbanden"

    so_thu_tu = models.PositiveIntegerField(
        "Số đến",
        default=1,
        help_text="Tự động tăng theo năm (Số đến).",
    )
    ngay_den = models.DateTimeField(
        "Ngày đến",
        default=timezone.now,
        help_text="Lấy đầy đủ ngày giờ phút giây.",
    )
    noi_ban_hanh = models.CharField(
        "Nơi ban hành",
        max_length=500,
        blank=True,
        default="",
    )
    nguoi_nhan = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="VanBanDenNguoiNhan",
        verbose_name="Người nhận",
        related_name="vanbanden_received",
        blank=True,
        help_text="Cán bộ nhân viên nhận văn bản đến.",
    )

    def save(self, *args, **kwargs):
        if not self.ngay_den:
            self.ngay_den = timezone.now()
        if not self.ngay_van_ban:
            self.ngay_van_ban = self.ngay_den

        is_new = self._state.adding or not self.pk
        if not is_new:
            return super().save(*args, **kwargs)

        # Với bản ghi mới: cấp số và retry nếu gặp IntegrityError (concurrency race condition - Issue B-1)
        from .services import generate_so_thu_tu
        max_retries = 3
        for attempt in range(max_retries):
            if not self.so_thu_tu or self.so_thu_tu == 1 or attempt > 0:
                next_stt = generate_so_thu_tu("DEN", self.nam or timezone.now().year)
                if next_stt:
                    self.so_thu_tu = next_stt
            try:
                with transaction.atomic():
                    return super().save(*args, **kwargs)
            except IntegrityError as exc:
                err_str = str(exc).lower()
                if "so_thu_tu" in err_str or "stt" in err_str or "unique" in err_str:
                    if attempt == max_retries - 1:
                        raise
                    continue
                raise

    class Meta:
        db_table = "documents_vanbanden"
        verbose_name = "Văn bản Đến"
        verbose_name_plural = "Văn bản Đến"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["nam", "so_thu_tu"], name="idx_vbden_nam_stt"),
            models.Index(fields=["ngay_den"], name="idx_vbden_ngay_den"),
            models.Index(fields=["so_hieu"], name="idx_vanbanden_sohieu"),
            models.Index(fields=["nam"], name="idx_vanbanden_nam"),
        ]
        constraints = [
            models.UniqueConstraint(fields=["nam", "so_thu_tu"], name="uq_vanbanden_nam_stt"),
            models.CheckConstraint(
                condition=models.Q(pham_vi__in=["NOI_BO", "HAN_CHE"]),
                name="chk_vanbanden_pham_vi",
            ),
            models.CheckConstraint(
                condition=~models.Q(pham_vi="HAN_CHE") | models.Q(gui_mail_toan_he_thong=False),
                name="chk_vanbanden_han_che_khong_mail_toan_he_thong",
            ),
        ]

    def get_loai_display(self):
        return "Văn bản Đến"

    def __str__(self):
        label = self.so_hieu or f"#{self.pk}"
        return f"[Văn bản Đến] {label}"


# ── M2M Through & Junction Models cho Văn bản Đến ────────────────

class VanBanDenNguoiNhan(models.Model):
    """
    Bảng liên kết người nhận văn bản đến (documents_vanbanden_nguoinhan).
    Khớp DDL: vanbanden_id, employee_id, PK (vanbanden_id, employee_id).
    """

    pk = models.CompositePrimaryKey("vanbanden", "employee")
    vanbanden = models.ForeignKey(
        VanBanDen,
        on_delete=models.CASCADE,
        db_column="vanbanden_id",
        related_name="+",
    )
    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.RESTRICT,
        db_column="employee_id",
        related_name="+",
    )

    class Meta:
        db_table = "documents_vanbanden_nguoinhan"
        verbose_name = "Người nhận văn bản đến"
        verbose_name_plural = "Người nhận văn bản đến"

    def __str__(self):
        return f"{self.vanbanden_id} - {self.employee_id}"


class VanBanDenHoSo(models.Model):
    """
    Bảng liên kết Hồ sơ văn bản đến (documents_vanbanden_hoso).
    Khớp DDL: vanbanden_id, hoso_id.
    """

    pk = models.CompositePrimaryKey("vanbanden", "hoso_id")
    vanbanden = models.ForeignKey(
        VanBanDen,
        on_delete=models.CASCADE,
        db_column="vanbanden_id",
        related_name="hoso",
    )
    hoso_id = models.BigIntegerField("ID Hồ sơ", db_index=True)

    class Meta:
        db_table = "documents_vanbanden_hoso"
        verbose_name = "Hồ sơ văn bản đến"
        verbose_name_plural = "Hồ sơ văn bản đến"
        indexes = [
            models.Index(fields=["hoso_id"], name="idx_vanbanden_hoso_hoso"),
        ]

    def __str__(self):
        return f"{self.vanbanden_id} - {self.hoso_id}"


class VanBanDenDanhmuc(models.Model):
    """
    Bảng liên kết Loại văn bản / Danh mục văn bản đến (documents_vanbanden_danhmuc).
    Khớp DDL: vanbanden_id, loaivanban_id.
    """

    pk = models.CompositePrimaryKey("vanbanden", "loaivanban_id")
    vanbanden = models.ForeignKey(
        VanBanDen,
        on_delete=models.CASCADE,
        db_column="vanbanden_id",
        related_name="danhmuc",
    )
    loaivanban_id = models.BigIntegerField("ID Loại văn bản", db_index=True)

    class Meta:
        db_table = "documents_vanbanden_danhmuc"
        verbose_name = "Danh mục loại văn bản đến"
        verbose_name_plural = "Danh mục loại văn bản đến"
        indexes = [
            models.Index(fields=["loaivanban_id"], name="idx_vanbanden_danhmuc_loai"),
        ]

    def __str__(self):
        return f"{self.vanbanden_id} - {self.loaivanban_id}"


class VanBanDenDonViNhan(models.Model):
    """
    Bảng liên kết đơn vị nhận văn bản đến (documents_vanbanden_donvinhan).
    Khớp DDL: vanbanden_id, donvi_id.
    """

    pk = models.CompositePrimaryKey("vanbanden", "donvi_id")
    vanbanden = models.ForeignKey(
        VanBanDen,
        on_delete=models.CASCADE,
        db_column="vanbanden_id",
        related_name="donvinhan",
    )
    donvi_id = models.BigIntegerField("ID Đơn vị nhận", db_index=True)

    class Meta:
        db_table = "documents_vanbanden_donvinhan"
        verbose_name = "Đơn vị nhận văn bản đến"
        verbose_name_plural = "Đơn vị nhận văn bản đến"

    def __str__(self):
        return f"{self.vanbanden_id} - {self.donvi_id}"


# ═══════════════════════════════════════════════════════════════════
# 2. Văn bản Đi (documents_vanbandi)
# ═══════════════════════════════════════════════════════════════════

class VanBanDi(BaseVanBan):
    """
    Model quản lý Văn bản Đi — Nghị định 30/2020/NĐ-CP.
    Khớp 100% với bảng vật lý `documents_vanbandi`.
    """

    loai = "DI"
    document_kind = "vanbandi"

    so_thu_tu = models.PositiveIntegerField(
        "Số đi",
        default=1,
        help_text="Tự động tăng theo năm (Số đi).",
    )
    ngay_ban_hanh = models.DateTimeField(
        "Ngày ban hành",
        default=timezone.now,
        help_text="Ngày ban hành cho Văn bản Đi.",
    )
    nguoi_nhan = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="VanBanDiNguoiNhan",
        verbose_name="Người nhận",
        related_name="vanbandi_received",
        blank=True,
        help_text="Cán bộ nhân viên nhận văn bản đi.",
    )

    @property
    def noi_ban_hanh(self):
        # N2-9: Bỏ gán cứng "Trường ITC"; nơi ban hành văn bản đi lưu tại documents_vanbandi_noibanhanh
        return getattr(self, "_noi_ban_hanh", "")

    @noi_ban_hanh.setter
    def noi_ban_hanh(self, val):
        self._noi_ban_hanh = val

    def save(self, *args, **kwargs):
        if not self.ngay_ban_hanh:
            self.ngay_ban_hanh = timezone.now()
        if not self.ngay_van_ban:
            self.ngay_van_ban = self.ngay_ban_hanh

        is_new = self._state.adding or not self.pk
        if not is_new:
            return super().save(*args, **kwargs)

        # Với bản ghi mới: cấp số và retry nếu gặp IntegrityError (concurrency race condition - Issue B-1)
        from .services import generate_so_thu_tu
        max_retries = 3
        for attempt in range(max_retries):
            if not self.so_thu_tu or self.so_thu_tu == 1 or attempt > 0:
                next_stt = generate_so_thu_tu("DI", self.nam or timezone.now().year)
                if next_stt:
                    self.so_thu_tu = next_stt
            try:
                with transaction.atomic():
                    return super().save(*args, **kwargs)
            except IntegrityError as exc:
                err_str = str(exc).lower()
                if "so_thu_tu" in err_str or "stt" in err_str or "unique" in err_str:
                    if attempt == max_retries - 1:
                        raise
                    continue
                raise

    class Meta:
        db_table = "documents_vanbandi"
        verbose_name = "Văn bản Đi"
        verbose_name_plural = "Văn bản Đi"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["nam", "so_thu_tu"], name="idx_vbdi_nam_stt"),
            models.Index(fields=["ngay_ban_hanh"], name="idx_vbdi_ngay_ban_hanh"),
            models.Index(fields=["so_hieu"], name="idx_vanbandi_sohieu"),
            models.Index(fields=["nam"], name="idx_vanbandi_nam"),
        ]
        constraints = [
            models.UniqueConstraint(fields=["nam", "so_thu_tu"], name="uq_vanbandi_nam_stt"),
            models.CheckConstraint(
                condition=models.Q(pham_vi__in=["NOI_BO", "HAN_CHE"]),
                name="chk_vanbandi_pham_vi",
            ),
            models.CheckConstraint(
                condition=~models.Q(pham_vi="HAN_CHE") | models.Q(gui_mail_toan_he_thong=False),
                name="chk_vanbandi_han_che_khong_mail_toan_he_thong",
            ),
        ]

    def get_loai_display(self):
        return "Văn bản Đi"

    def __str__(self):
        label = self.so_hieu or f"#{self.pk}"
        return f"[Văn bản Đi] {label}"


# ── M2M Through & Junction Models cho Văn bản Đi ─────────────────

class VanBanDiNguoiNhan(models.Model):
    """
    Bảng liên kết người nhận văn bản đi (documents_vanbandi_nguoinhan).
    Khớp DDL: vanbandi_id, employee_id, PK (vanbandi_id, employee_id).
    """

    pk = models.CompositePrimaryKey("vanbandi", "employee")
    vanbandi = models.ForeignKey(
        VanBanDi,
        on_delete=models.CASCADE,
        db_column="vanbandi_id",
        related_name="+",
    )
    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.RESTRICT,
        db_column="employee_id",
        related_name="+",
    )

    class Meta:
        db_table = "documents_vanbandi_nguoinhan"
        verbose_name = "Người nhận văn bản đi"
        verbose_name_plural = "Người nhận văn bản đi"

    def __str__(self):
        return f"{self.vanbandi_id} - {self.employee_id}"


class VanBanDiHoSo(models.Model):
    """
    Bảng liên kết Hồ sơ văn bản đi (documents_vanbandi_hoso).
    Khớp DDL: vanbandi_id, hoso_id.
    """

    pk = models.CompositePrimaryKey("vanbandi", "hoso_id")
    vanbandi = models.ForeignKey(
        VanBanDi,
        on_delete=models.CASCADE,
        db_column="vanbandi_id",
        related_name="hoso",
    )
    hoso_id = models.BigIntegerField("ID Hồ sơ", db_index=True)

    class Meta:
        db_table = "documents_vanbandi_hoso"
        verbose_name = "Hồ sơ văn bản đi"
        verbose_name_plural = "Hồ sơ văn bản đi"
        indexes = [
            models.Index(fields=["hoso_id"], name="idx_vanbandi_hoso_hoso"),
        ]

    def __str__(self):
        return f"{self.vanbandi_id} - {self.hoso_id}"


class VanBanDiDanhmuc(models.Model):
    """
    Bảng liên kết Loại văn bản / Danh mục văn bản đi (documents_vanbandi_danhmuc).
    Khớp DDL: vanbandi_id, loaivanban_id.
    """

    pk = models.CompositePrimaryKey("vanbandi", "loaivanban_id")
    vanbandi = models.ForeignKey(
        VanBanDi,
        on_delete=models.CASCADE,
        db_column="vanbandi_id",
        related_name="danhmuc",
    )
    loaivanban_id = models.BigIntegerField("ID Loại văn bản", db_index=True)

    class Meta:
        db_table = "documents_vanbandi_danhmuc"
        verbose_name = "Danh mục loại văn bản đi"
        verbose_name_plural = "Danh mục loại văn bản đi"
        indexes = [
            models.Index(fields=["loaivanban_id"], name="idx_vanbandi_danhmuc_loai"),
        ]

    def __str__(self):
        return f"{self.vanbandi_id} - {self.loaivanban_id}"


class VanBanDiDonViNhan(models.Model):
    """
    Bảng liên kết đơn vị nhận văn bản đi (documents_vanbandi_donvinhan).
    Khớp DDL: vanbandi_id, donvi_id.
    """

    pk = models.CompositePrimaryKey("vanbandi", "donvi_id")
    vanbandi = models.ForeignKey(
        VanBanDi,
        on_delete=models.CASCADE,
        db_column="vanbandi_id",
        related_name="donvinhan",
    )
    donvi_id = models.BigIntegerField("ID Đơn vị nhận", db_index=True)

    class Meta:
        db_table = "documents_vanbandi_donvinhan"
        verbose_name = "Đơn vị nhận văn bản đi"
        verbose_name_plural = "Đơn vị nhận văn bản đi"

    def __str__(self):
        return f"{self.vanbandi_id} - {self.donvi_id}"


class VanBanDiNoiBanHanh(models.Model):
    """
    Bảng liên kết nơi ban hành văn bản đi (documents_vanbandi_noibanhanh).
    Khớp DDL: vanbandi_id, donvi_id.
    """

    pk = models.CompositePrimaryKey("vanbandi", "donvi_id")
    vanbandi = models.ForeignKey(
        VanBanDi,
        on_delete=models.CASCADE,
        db_column="vanbandi_id",
        related_name="noibanhanh_links",
    )
    donvi_id = models.BigIntegerField("ID Đơn vị ban hành", db_index=True)

    class Meta:
        db_table = "documents_vanbandi_noibanhanh"
        verbose_name = "Nơi ban hành văn bản đi"
        verbose_name_plural = "Nơi ban hành văn bản đi"
        indexes = [
            models.Index(fields=["donvi_id"], name="idx_vanbandi_noibanhanh_donvi"),
        ]

    def __str__(self):
        return f"{self.vanbandi_id} - {self.donvi_id}"


# ═══════════════════════════════════════════════════════════════════
# Attachment Models (Hướng A: 7 trường chuẩn hóa)
# ═══════════════════════════════════════════════════════════════════

def document_attachment_path(instance, filename):
    """
    Xác định đường dẫn lưu file đính kèm:
    02_documents/<loai>/<muc_do>/<nam>/<thang>/<ngay>/<filename>
    - <loai>: den | di
    - <muc_do>: thuong | han_che
    """
    doc = getattr(instance, "document", None)
    subfolder = "den"
    muc_do = "thuong"
    date_val = None
    year = None

    if doc:
        loai = getattr(doc, "loai", "DEN")
        subfolder = "di" if loai == "DI" else "den"
        pham_vi = getattr(doc, "pham_vi", "NOI_BO")
        muc_do = "han_che" if pham_vi == "HAN_CHE" else "thuong"
        year = getattr(doc, "nam", timezone.now().year)
        if loai == "DEN":
            date_val = getattr(doc, "ngay_den", None) or getattr(doc, "ngay_van_ban", None)
        else:
            date_val = getattr(doc, "ngay_ban_hanh", None) or getattr(doc, "ngay_van_ban", None)

    if not date_val:
        date_val = timezone.now()
    if not year:
        year = date_val.year

    return f"02_documents/{subfolder}/{muc_do}/{year}/{date_val.month:02d}/{date_val.day:02d}/{filename}"


class BaseDocumentAttachment(models.Model):
    """Abstract model chứa 7 trường chuẩn Hướng A cho tệp đính kèm."""

    name = models.CharField("Tên gốc file", max_length=255)
    file = models.FileField(
        "File đính kèm",
        upload_to=document_attachment_path,
        db_column="path",
        max_length=500,
        default="",
        help_text="Chấp nhận: PDF, DOC, DOCX, JPG, JPEG, PNG. Tối đa 20MB.",
    )
    is_deleted = models.BooleanField("Cờ xóa mềm", default=False)
    created_at = models.DateTimeField("Ngày upload", default=timezone.now, db_column="created_at")
    nguoi_tao = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Người tải lên",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="nguoi_tao_id",
        related_name="%(class)s_uploaded",
    )

    # ── Backward-compatibility properties cho created_time & created_user ──
    @property
    def created_time(self):
        return self.created_at

    @created_time.setter
    def created_time(self, val):
        self.created_at = val

    @property
    def created_user(self):
        return self.nguoi_tao

    @created_user.setter
    def created_user(self, val):
        self.nguoi_tao = val

    class Meta:
        abstract = True
        ordering = ["created_at"]

    def __init__(self, *args, **kwargs):
        path_val = kwargs.pop("path", None)
        file_size_val = kwargs.pop("file_size", None)
        file_name_val = kwargs.pop("file_name", None)
        created_time_val = kwargs.pop("created_time", None)
        created_user_val = kwargs.pop("created_user", None)
        super().__init__(*args, **kwargs)
        if path_val and not self.file:
            self.file = path_val
        if file_size_val:
            self._file_size = file_size_val
        if file_name_val and not self.name:
            self.name = file_name_val
        if created_time_val and not self.created_at:
            self.created_at = created_time_val
        if created_user_val and not self.nguoi_tao:
            self.nguoi_tao = created_user_val

    @property
    def path(self):
        return self.file.name if self.file else ""

    @path.setter
    def path(self, val):
        self.file = val

    @property
    def file_size(self):
        try:
            return self.file.size if self.file else (getattr(self, "_file_size", 0) or 0)
        except Exception:
            return getattr(self, "_file_size", 0) or 0

    @file_size.setter
    def file_size(self, val):
        self._file_size = val

    @property
    def file_name(self):
        return self.name

    @property
    def uploaded_at(self):
        return self.created_at

    def save(self, *args, **kwargs):
        if self.file and not self.name:
            self.name = os.path.basename(self.file.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name or f"Attachment #{self.pk}"


class VanBanDenAttachment(BaseDocumentAttachment):
    document = models.ForeignKey(
        VanBanDen,
        on_delete=models.CASCADE,
        related_name="attachments",
        verbose_name="Văn bản đến",
    )

    class Meta:
        db_table = "documents_vanbanden_attachment"
        verbose_name = "Tệp đính kèm VB Đến"
        verbose_name_plural = "Tệp đính kèm VB Đến"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["document"], name="idx_vbden_att_doc"),
            models.Index(fields=["is_deleted"], name="idx_vbden_att_del"),
        ]


class VanBanDiAttachment(BaseDocumentAttachment):
    document = models.ForeignKey(
        VanBanDi,
        on_delete=models.CASCADE,
        related_name="attachments",
        verbose_name="Văn bản đi",
    )

    class Meta:
        db_table = "documents_vanbandi_attachment"
        verbose_name = "Tệp đính kèm VB Đi"
        verbose_name_plural = "Tệp đính kèm VB Đi"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["document"], name="idx_vbdi_att_doc"),
            models.Index(fields=["is_deleted"], name="idx_vbdi_att_del"),
        ]


# ═══════════════════════════════════════════════════════════════════
# DocumentViewLog (documents_view_log)
# ═══════════════════════════════════════════════════════════════════

class DocumentViewLog(models.Model):
    """
    Ghi nhận lịch sử người đã xem văn bản.
    Khớp 100% với bảng `documents_view_log` (document_type, document_id, user_id, viewed_at).
    """

    class DocumentKind(models.TextChoices):
        VANBANDEN = "vanbanden", "Văn bản Đến"
        VANBANDI = "vanbandi", "Văn bản Đi"

    document_type = models.CharField(
        "Loại văn bản",
        max_length=20,
        choices=DocumentKind.choices,
        default=DocumentKind.VANBANDEN,
    )
    document_id = models.PositiveBigIntegerField("ID văn bản")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="document_views",
        verbose_name="Người xem",
    )
    viewed_at = models.DateTimeField("Thời gian xem", auto_now=True)

    class Meta:
        db_table = "documents_view_log"
        verbose_name = "Lịch sử xem văn bản"
        verbose_name_plural = "Lịch sử xem văn bản"
        unique_together = [("document_type", "document_id", "user")]
        ordering = ["-viewed_at"]

    def __str__(self):
        return f"{self.user} xem {self.document_type}#{self.document_id} lúc {self.viewed_at}"


# ═══════════════════════════════════════════════════════════════════
# DocumentAccessLog (documents_access_log - Issue #82 & PR #92 DDL)
# ═══════════════════════════════════════════════════════════════════

class DocumentAccessLog(models.Model):
    """
    Nhật ký truy cập văn bản hạn chế (documents_access_log).
    Chỉ ghi cho văn bản pham_vi = 'HAN_CHE'. WORM (Write-Once-Read-Many): Không sửa/xóa.
    hanh_dong: XEM | TAI_FILE | BI_TU_CHOI | THEM_NGUOI_XEM | BOT_NGUOI_XEM.
    """

    class HanhDong(models.TextChoices):
        XEM = "XEM", "Xem"
        TAI_FILE = "TAI_FILE", "Tải file"
        BI_TU_CHOI = "BI_TU_CHOI", "Bị từ chối"
        THEM_NGUOI_XEM = "THEM_NGUOI_XEM", "Thêm người xem"
        BOT_NGUOI_XEM = "BOT_NGUOI_XEM", "Bớt người xem"

    document_type = models.CharField("Loại văn bản", max_length=20)
    document_id = models.BigIntegerField("ID văn bản")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Người thực hiện",
        on_delete=models.RESTRICT,
        related_name="document_access_logs",
        db_column="user_id",
    )
    hanh_dong = models.CharField(
        "Hành động",
        max_length=20,
        choices=HanhDong.choices,
    )
    doi_tuong_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Người bị thêm/bớt",
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        related_name="document_access_target_logs",
        db_column="doi_tuong_user_id",
    )
    tep_id = models.BigIntegerField("ID tệp tin", null=True, blank=True)
    dia_chi_ip = models.CharField("Địa chỉ IP", max_length=45, null=True, blank=True)
    created_at = models.DateTimeField("Thời điểm", auto_now_add=True)

    class Meta:
        db_table = "documents_access_log"
        verbose_name = "Nhật ký truy cập văn bản hạn chế"
        verbose_name_plural = "Nhật ký truy cập văn bản hạn chế"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["document_type", "document_id", "created_at"], name="idx_access_log_doc"),
            models.Index(fields=["user", "created_at"], name="idx_access_log_user"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(hanh_dong__in=["XEM", "TAI_FILE", "BI_TU_CHOI", "THEM_NGUOI_XEM", "BOT_NGUOI_XEM"]),
                name="chk_access_log_hanh_dong",
            ),
            models.CheckConstraint(
                condition=~models.Q(hanh_dong__in=["THEM_NGUOI_XEM", "BOT_NGUOI_XEM"]) | models.Q(doi_tuong_user__isnull=False),
                name="chk_access_log_doi_tuong",
            ),
        ]

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("Nhật ký truy cập văn bản hạn chế không được phép chỉnh sửa.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Nhật ký truy cập văn bản hạn chế không được phép xóa.")

    def __str__(self):
        return f"[{self.hanh_dong}] {self.user} - {self.document_type}#{self.document_id} lúc {self.created_at}"


# ═══════════════════════════════════════════════════════════════════
# Helper Functions & Backward-Compatibility Facade
# ═══════════════════════════════════════════════════════════════════

def get_document_model(loai: str):
    """Trả về Model Class tương ứng với loại văn bản (DEN hoặc DI)."""
    loai_str = str(loai).strip().upper()
    if loai_str in ("DI", "VANBANDI"):
        return VanBanDi
    return VanBanDen


def get_attachment_model(loai_or_doc):
    """Trả về Attachment Model tương ứng (DEN hoặc DI)."""
    if isinstance(loai_or_doc, VanBanDi) or getattr(loai_or_doc, "loai", "") == "DI":
        return VanBanDiAttachment
    loai_str = str(loai_or_doc).strip().upper()
    if loai_str in ("DI", "VANBANDI"):
        return VanBanDiAttachment
    return VanBanDenAttachment


class DocumentManager:
    """Manager giả lập cho facade Document phục vụ tương thích ngược."""

    def create(self, **kwargs):
        loai = kwargs.pop("loai", "DEN")
        model = get_document_model(loai)
        return model.objects.create(**kwargs)

    def filter(self, *args, **kwargs):
        loai = kwargs.pop("loai", None)
        if loai:
            model = get_document_model(loai)
            return model.objects.filter(*args, **kwargs)
        return VanBanDen.objects.filter(*args, **kwargs)

    def get(self, *args, **kwargs):
        loai = kwargs.pop("loai", None)
        if loai:
            return get_document_model(loai).objects.get(*args, **kwargs)
        for model in (VanBanDen, VanBanDi):
            try:
                return model.objects.get(*args, **kwargs)
            except model.DoesNotExist:
                continue
        raise VanBanDen.DoesNotExist(f"Document with kwargs {kwargs} does not exist.")

    def all(self):
        return VanBanDen.objects.all()

    def count(self):
        return VanBanDen.objects.count() + VanBanDi.objects.count()


class DocumentFacade:
    """
    Facade class tương thích ngược cho `Document`.
    Cho phép gọi: Document.objects.create(loai="DEN", ...), Document.HieuLuc, Document.LoaiVanBan
    """

    HieuLuc = HieuLuc
    LoaiVanBan = LoaiVanBan
    objects = DocumentManager()

    DoesNotExist = VanBanDen.DoesNotExist


Document = DocumentFacade


class DocumentAttachmentFacade:
    """Facade tương thích ngược cho DocumentAttachment."""

    class Manager:
        def create(self, **kwargs):
            doc = kwargs.get("document")
            att_model = get_attachment_model(doc)
            if "file_name" in kwargs and "name" not in kwargs:
                kwargs["name"] = kwargs.pop("file_name")
            return att_model.objects.create(**kwargs)

        def filter(self, *args, **kwargs):
            return VanBanDenAttachment.objects.filter(*args, **kwargs)

        def all(self):
            return VanBanDenAttachment.objects.all()

    objects = Manager()


DocumentAttachment = DocumentAttachmentFacade
