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
from django.core.validators import MinValueValidator
from django.db import IntegrityError, models, transaction
from django.db.models import F, Value
from django.db.models.functions import Trim
from django.db.models.lookups import Exact
from django.utils import timezone

from document_storage import build_dated_path, get_document_storage

DB_NOW = models.Func(function="now", output_field=models.DateTimeField())


# ═══════════════════════════════════════════════════════════════════
# Folder Model — Thư mục nhiều cấp (Nested / Hierarchical)
# ═══════════════════════════════════════════════════════════════════

class Folder(models.Model):
    """
    Model quản lý thư mục phân cấp nhiều cấp (Nested Folder / Hierarchical Folder).

    Hỗ trợ:
    - Tự tham chiếu (self-referential ForeignKey) qua trường `parent`.
    - Materialized Path (`path`) cho truy vấn nhanh cây thư mục.
    - Giới hạn độ sâu tối đa (MAX_DEPTH = 10).
    - Chống vòng lặp thư mục (Circular Reference Prevention).
    - Cascade delete: xóa thư mục cha sẽ xóa toàn bộ con cháu.

    Cấu trúc ví dụ:
        Tài liệu (depth=0, path="/1/")
        ├── Lập trình (depth=1, path="/1/2/")
        │   ├── Python (depth=2, path="/1/2/3/")
        │   │   └── Bài tập (depth=3, path="/1/2/3/4/")
        │   └── Java (depth=2, path="/1/2/5/")
        └── Cơ sở dữ liệu (depth=1, path="/1/6/")
    """

    MAX_DEPTH = 10  # Giới hạn tối đa 10 cấp

    name = models.CharField(
        "Tên thư mục",
        max_length=255,
        help_text="Tên hiển thị của thư mục.",
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
        verbose_name="Thư mục cha",
        help_text="Để trống nếu là thư mục gốc (root).",
    )
    # Materialized Path: lưu đường dẫn ID từ gốc, ví dụ "/1/3/7/"
    path = models.CharField(
        "Đường dẫn phân cấp",
        max_length=1000,
        default="/",
        db_index=True,
        editable=False,
        help_text="Materialized Path — tự động tính toán, không sửa tay.",
    )
    depth = models.PositiveIntegerField(
        "Độ sâu",
        default=0,
        editable=False,
        help_text="0 = thư mục gốc, 1 = con của gốc, ...",
    )
    order = models.PositiveIntegerField(
        "Thứ tự hiển thị",
        default=0,
        help_text="Sắp xếp các thư mục cùng cấp.",
    )
    description = models.TextField(
        "Mô tả",
        blank=True,
        default="",
    )
    is_local = models.BooleanField(
        "Thư mục cục bộ (Local)",
        default=False,
        help_text="Thư mục được đồng bộ trực tiếp từ ổ đĩa máy tính.",
    )
    local_path = models.CharField(
        "Đường dẫn Local",
        max_length=1000,
        blank=True,
        default="",
        help_text="Đường dẫn thư mục thực tế trên ổ đĩa máy tính.",
    )

    # ── Audit ──────────────────────────────────────────────────────
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Người tạo",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="folders_created",
    )
    created_at = models.DateTimeField("Ngày tạo", auto_now_add=True)
    updated_at = models.DateTimeField("Ngày cập nhật", auto_now=True)

    class Meta:
        app_label = "documents"
        db_table = "documents_folder"
        verbose_name = "Thư mục"
        verbose_name_plural = "Thư mục"
        ordering = ["path", "order", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["parent", "name"],
                name="uq_folder_parent_name",
            ),
        ]
        indexes = [
            models.Index(fields=["parent"], name="idx_folder_parent"),
            models.Index(fields=["path"], name="idx_folder_path"),
            models.Index(fields=["depth"], name="idx_folder_depth"),
        ]

    def __str__(self):
        return self.name

    # ── Đường dẫn hiển thị ────────────────────────────────────────
    @property
    def full_path_display(self):
        """Trả về đường dẫn hiển thị dạng 'Tài liệu / Lập trình / Python'."""
        parts = []
        node = self
        while node:
            parts.append(node.name)
            node = node.parent
        return " / ".join(reversed(parts))

    # ── Lấy tất cả tổ tiên ───────────────────────────────────────
    def get_ancestors(self):
        """Trả về danh sách tổ tiên từ gốc đến cha trực tiếp (không bao gồm chính nó)."""
        ancestors = []
        node = self.parent
        while node:
            ancestors.append(node)
            node = node.parent
        return list(reversed(ancestors))

    # ── Lấy tất cả con cháu ──────────────────────────────────────
    def get_descendants(self):
        """Trả về QuerySet tất cả con cháu (dùng Materialized Path)."""
        if not self.pk:
            return Folder.objects.none()
        prefix = self.path
        return Folder.objects.filter(path__startswith=prefix).exclude(pk=self.pk)

    # ── Lấy breadcrumb ───────────────────────────────────────────
    def get_breadcrumb(self):
        """Trả về danh sách breadcrumb từ gốc đến thư mục hiện tại."""
        ancestors = self.get_ancestors()
        return [*ancestors, self]

    # ── Kiểm tra vòng lặp ────────────────────────────────────────
    def _check_circular(self, new_parent):
        """Kiểm tra di chuyển thư mục có tạo vòng lặp không."""
        if new_parent is None:
            return
        if new_parent.pk == self.pk:
            raise ValidationError(
                "Không thể đặt thư mục làm con của chính nó."
            )
        # Kiểm tra new_parent có phải là con cháu của self không
        descendant_ids = set(self.get_descendants().values_list("pk", flat=True))
        if new_parent.pk in descendant_ids:
            raise ValidationError(
                f"Không thể di chuyển thư mục '{self.name}' vào bên trong "
                f"thư mục con '{new_parent.name}' (tạo vòng lặp)."
            )

    # ── Tính toán path & depth ────────────────────────────────────
    def _compute_path_and_depth(self):
        """Tính toán materialized path và depth từ parent."""
        if self.parent:
            self.depth = self.parent.depth + 1
            # path sẽ được set sau save vì cần pk
        else:
            self.depth = 0

    # ── Cập nhật path cho bản thân và toàn bộ con cháu ───────────
    def _update_paths_recursive(self):
        """Cập nhật materialized path cho bản thân và tất cả con cháu."""
        if self.parent:
            self.path = f"{self.parent.path}{self.pk}/"
        else:
            self.path = f"/{self.pk}/"
        Folder.objects.filter(pk=self.pk).update(path=self.path)

        for child in Folder.objects.filter(parent=self):
            child.path = f"{self.path}{child.pk}/"
            child.depth = self.depth + 1
            Folder.objects.filter(pk=child.pk).update(
                path=child.path, depth=child.depth
            )
            child._update_paths_recursive_children()

    def _update_paths_recursive_children(self):
        """Cập nhật path cho con cháu (helper nội bộ)."""
        for child in Folder.objects.filter(parent=self):
            child.path = f"{self.path}{child.pk}/"
            child.depth = self.depth + 1
            Folder.objects.filter(pk=child.pk).update(
                path=child.path, depth=child.depth
            )
            child._update_paths_recursive_children()

    # ── Override save ─────────────────────────────────────────────
    def save(self, *args, **kwargs):
        # Kiểm tra vòng lặp nếu đang thay đổi parent
        if self.pk:
            try:
                old = Folder.objects.get(pk=self.pk)
                if old.parent_id != (self.parent_id if self.parent else None):
                    self._check_circular(self.parent)
            except Folder.DoesNotExist:
                pass

        # Kiểm tra giới hạn độ sâu
        self._compute_path_and_depth()
        if self.depth >= self.MAX_DEPTH:
            raise ValidationError(
                f"Thư mục không được vượt quá {self.MAX_DEPTH} cấp. "
                f"Cấp hiện tại: {self.depth}."
            )

        is_new = self._state.adding or not self.pk
        super().save(*args, **kwargs)

        # Cập nhật materialized path sau khi có pk
        if is_new:
            if self.parent:
                new_path = f"{self.parent.path}{self.pk}/"
            else:
                new_path = f"/{self.pk}/"
            if self.path != new_path:
                self.path = new_path
                Folder.objects.filter(pk=self.pk).update(path=self.path)
        else:
            # Nếu đang di chuyển thư mục, cập nhật path cho toàn bộ cây con
            self._update_paths_recursive()

    # ── Di chuyển thư mục ─────────────────────────────────────────
    def move_to(self, new_parent):
        """
        Di chuyển thư mục đến vị trí mới.
        new_parent = None: chuyển thành thư mục gốc.
        """
        self._check_circular(new_parent)
        self.parent = new_parent
        self.save()


# ═══════════════════════════════════════════════════════════════════
# FolderFile — Liên kết File với Folder
# ═══════════════════════════════════════════════════════════════════

class FolderFile(models.Model):
    """
    Model liên kết file/tài liệu với thư mục.
    Một file có thể thuộc một thư mục cụ thể.
    """

    folder = models.ForeignKey(
        Folder,
        on_delete=models.CASCADE,
        related_name="files",
        verbose_name="Thư mục",
    )
    file_name = models.CharField(
        "Tên file",
        max_length=500,
    )
    file_path = models.CharField(
        "Đường dẫn file",
        max_length=1000,
        blank=True,
        default="",
    )
    file_size = models.PositiveBigIntegerField(
        "Kích thước (bytes)",
        default=0,
    )
    file_type = models.CharField(
        "Loại file",
        max_length=50,
        blank=True,
        default="",
        help_text="Phần mở rộng: pdf, docx, txt, ...",
    )
    description = models.TextField(
        "Mô tả",
        blank=True,
        default="",
    )
    is_local = models.BooleanField(
        "File cục bộ (Local)",
        default=False,
        help_text="File nằm trên ổ đĩa máy tính, không lưu trong media server.",
    )

    # ── Audit ──────────────────────────────────────────────────────
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Người tải lên",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="folder_files_uploaded",
    )
    created_at = models.DateTimeField("Ngày tạo", auto_now_add=True)

    class Meta:
        app_label = "documents"
        db_table = "documents_folder_file"
        verbose_name = "File trong thư mục"
        verbose_name_plural = "File trong thư mục"
        ordering = ["file_name"]
        indexes = [
            models.Index(fields=["folder"], name="idx_folder_file_folder"),
        ]

    def __str__(self):
        return self.file_name


# ═══════════════════════════════════════════════════════════════════
# ENUM & Choices
# ═══════════════════════════════════════════════════════════════════

class PhamVi(models.TextChoices):
    NOI_BO = "NOI_BO", "Nội bộ"
    HAN_CHE = "HAN_CHE", "Hạn chế"


class LoaiVanBan(models.TextChoices):
    DEN = "DEN", "Văn bản Đến"
    DI = "DI", "Văn bản Đi"
    MAT = "MAT", "Văn bản Mật"


def canonical_document_kind(document_kind):
    """Map the compatibility alias to the kind of its shared backing table."""
    value = str(document_kind).lower()
    return "vanbanden" if value == "vanbanmat" else value


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
        db_default=PhamVi.NOI_BO,
        db_index=True,
        help_text="NOI_BO: Văn bản nội bộ; HAN_CHE: Văn bản hạn chế (mật nội bộ).",
    )

    # ── Năm & Ký hiệu ──────────────────────────────────────────────
    nam = models.SmallIntegerField(
        "Năm",
        default=timezone.now().year,
        validators=[MinValueValidator(0)],
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
        null=True,
    )
    chuc_vu = models.CharField(
        "Chức vụ người ký",
        max_length=255,
        blank=True,
        default="",
        null=True,
    )

    # ── Hiệu lực ──────────────────────────────────────────────────
    hieu_luc = models.CharField(
        "Hiệu lực",
        max_length=20,
        choices=HieuLuc.choices,
        default=HieuLuc.CON_HIEU_LUC,
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
        null=True,
    )

    # ── Ghi chú & Cờ hệ thống ──────────────────────────────────────
    ghi_chu = models.TextField("Ghi chú", blank=True, default="", null=True)
    hien_thi = models.BooleanField(
        "Trạng thái hiển thị",
        default=True,
        db_default=True,
        help_text="False = ẩn với user thường, admin vẫn thấy (đổi màu).",
    )
    gui_mail_toan_he_thong = models.BooleanField(
        "Gửi mail toàn hệ thống",
        default=False,
        db_default=False,
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
    created_at = models.DateTimeField("Ngày tạo", auto_now_add=True, db_default=DB_NOW)
    updated_at = models.DateTimeField("Ngày cập nhật", auto_now=True, db_default=DB_NOW)

    class Meta:
        abstract = True

    def clean(self):
        super().clean()
        if self.pham_vi == self.PhamVi.HAN_CHE and self.gui_mail_toan_he_thong:
            raise ValidationError(
                {"gui_mail_toan_he_thong": "Văn bản hạn chế không được phép gửi email toàn hệ thống."}
            )

    def save(self, *args, **kwargs):
        allow_scope_change = kwargs.pop("allow_scope_change", False) or getattr(self, "_allow_scope_change", False)
        if self.pk and not allow_scope_change:
            old_inst = self.__class__.objects.filter(pk=self.pk).values("pham_vi").first()
            if old_inst and old_inst["pham_vi"] != self.pham_vi:
                raise ValidationError("Phạm vi văn bản không được đổi sau khi tạo.")
        if self.pham_vi == self.PhamVi.HAN_CHE:
            self.gui_mail_toan_he_thong = False
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.pham_vi == self.PhamVi.HAN_CHE:
            raise ValidationError("Văn bản hạn chế không được phép xóa.")
        # Dọn dẹp liên kết Loại văn bản và Hồ sơ trước để thỏa mãn Trigger CSDL PostgreSQL
        if hasattr(self, "danhmuc"):
            self.danhmuc.all().delete()
        if hasattr(self, "hoso"):
            self.hoso.all().delete()
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

    ngay_van_ban = models.DateTimeField(
        "Ngày văn bản",
        default=timezone.now,
        null=True,
        blank=True,
        help_text="Dùng để lọc/sắp xếp danh sách.",
    )

    so_thu_tu = models.IntegerField(
        "Số đến",
        default=1,
        validators=[MinValueValidator(0)],
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
        null=True,
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
            models.Index(fields=["hieu_luc"], name="idx_vanbanden_hieu_luc"),
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
            models.CheckConstraint(
                condition=(
                    ~models.Q(hieu_luc="HET_VA_THAY_THE")
                    | (
                        models.Q(link_thay_the__isnull=False)
                        & ~Exact(Trim(F("link_thay_the")), Value(""))
                    )
                ),
                name="chk_vanbanden_link_thay_the",
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

    so_thu_tu = models.IntegerField(
        "Số đi",
        default=1,
        validators=[MinValueValidator(0)],
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
            models.Index(fields=["hieu_luc"], name="idx_vanbandi_hieu_luc"),
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
            models.CheckConstraint(
                condition=(
                    ~models.Q(hieu_luc="HET_VA_THAY_THE")
                    | (
                        models.Q(link_thay_the__isnull=False)
                        & ~Exact(Trim(F("link_thay_the")), Value(""))
                    )
                ),
                name="chk_vanbandi_link_thay_the",
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
    Đường dẫn lưu tệp đính kèm trong DOCUMENT_STORAGE_ROOT:
    van-ban-den|van-ban-di/YYYY/MM/DD/<uuid>.<ext> (ngày upload). Tên gốc giữ ở cột `name`.
    """
    doc = getattr(instance, "document", None)
    module = "van-ban-di" if getattr(doc, "loai", "DEN") == "DI" else "van-ban-den"
    return build_dated_path(module, filename)


class BaseDocumentAttachment(models.Model):
    """Abstract model chứa 7 trường chuẩn Hướng A cho tệp đính kèm."""

    name = models.CharField("Tên gốc file", max_length=255)
    file = models.FileField(
        "File đính kèm",
        upload_to=document_attachment_path,
        storage=get_document_storage,
        db_column="path",
        max_length=500,
        default="",
        help_text="Chấp nhận: PDF, DOC, DOCX, JPG, JPEG, PNG. Tối đa 20MB.",
    )
    is_deleted = models.BooleanField("Cờ xóa mềm", default=False, db_default=False)
    created_at = models.DateTimeField(
        "Ngày upload", default=timezone.now, db_default=DB_NOW, db_column="created_at"
    )
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
    document_id = models.BigIntegerField("ID văn bản", validators=[MinValueValidator(0)])
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
        indexes = [models.Index(fields=["document_type", "document_id"], name="idx_viewlog_document")]

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
    created_at = models.DateTimeField("Thời điểm", auto_now_add=True, db_default=DB_NOW)

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


# ═══════════════════════════════════════════════════════════════════
# Backward-Compatibility Aliases (Văn bản Mật gộp vào Văn bản Hạn chế)
# ═══════════════════════════════════════════════════════════════════
VanBanMat = VanBanDen
VanBanMatAttachment = VanBanDenAttachment
VanBanMatNguoiNhan = VanBanDenNguoiNhan
VanBanMatDonViNhan = VanBanDenDonViNhan
VanBanMatDanhmuc = VanBanDenDanhmuc
VanBanMatHoSo = VanBanDenHoSo
VanBanMatNoiBanHanh = VanBanDiNoiBanHanh
