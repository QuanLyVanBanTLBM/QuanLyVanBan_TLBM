from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

from . import enums
from .errors import ImmutableEvidenceError

User = settings.AUTH_USER_MODEL
DB_NOW = models.Func(function="now", output_field=models.DateTimeField())


def sha256_or_null(field):
    """CHECK: giá trị rỗng (NULL) hoặc SHA-256 hex 64 ký tự thường."""
    return Q(**{f"{field}__isnull": True}) | Q(**{f"{field}__regex": r"^[0-9a-f]{64}$"})


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 — model chỉ phụ thuộc người dùng
# ─────────────────────────────────────────────────────────────────────────────


class SigningKey(models.Model):
    """Khóa công khai Ed25519 của người dùng. Backend không lưu khóa bí mật."""

    nguoi_so_huu = models.ForeignKey(User, on_delete=models.PROTECT, related_name="signing_keys")
    ma_khoa = models.CharField(max_length=100, unique=True)
    dau_van_tay = models.CharField(max_length=64, unique=True)
    thuat_toan = models.CharField(max_length=50, db_default="Ed25519", default="Ed25519")
    khoa_cong_khai = models.TextField()
    trang_thai = models.CharField(
        max_length=20, choices=enums.TrangThaiKhoa.choices, db_default="CHO_KICH_HOAT", default=enums.TrangThaiKhoa.CHO_KICH_HOAT
    )
    thoi_diem_xac_minh_so_huu = models.DateTimeField(null=True, blank=True)
    thoi_diem_kich_hoat = models.DateTimeField(null=True, blank=True)
    ngay_hieu_luc = models.DateTimeField()
    ngay_het_han = models.DateTimeField(null=True, blank=True)
    ngay_thu_hoi = models.DateTimeField(null=True, blank=True)
    khoa_thay_the = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    ghi_chu = models.TextField(blank=True, db_default="", default="")
    created_at = models.DateTimeField(auto_now_add=True, db_default=DB_NOW)

    class Meta:
        db_table = "signing_key"
        constraints = [
            models.UniqueConstraint(
                fields=["nguoi_so_huu"],
                condition=Q(trang_thai=enums.TrangThaiKhoa.HOAT_DONG),
                name="uq_signing_key_mot_khoa_hoat_dong",
            ),
            models.CheckConstraint(
                condition=~Q(trang_thai=enums.TrangThaiKhoa.HOAT_DONG)
                | Q(thoi_diem_xac_minh_so_huu__isnull=False),
                name="chk_signing_key_hoat_dong_da_xac_minh",
            ),
        ]

    def __str__(self):
        return f"{self.ma_khoa} ({self.trang_thai})"


class SigningProcess(models.Model):
    # Tên cột theo DDL chuẩn hóa (#96, quy ước #68): db_column giữ nguyên tên thuộc tính và API.
    ma_quy_trinh = models.CharField(max_length=50)
    ten_quy_trinh = models.CharField(max_length=255)
    mo_ta = models.TextField(blank=True, db_default="", default="")
    phien_ban = models.PositiveSmallIntegerField(db_default=1, default=1)
    trang_thai = models.CharField(
        max_length=20, choices=enums.TrangThaiQuyTrinh.choices, db_default="NHAP", default=enums.TrangThaiQuyTrinh.NHAP
    )
    pham_vi = models.CharField(max_length=20, choices=enums.PhamViQuyTrinh.choices)
    # Bắt buộc khi PHONG_BAN, rỗng khi CONG_TY (#80 mục A). FK organizations_donvi theo DDL.
    don_vi_ap_dung = models.ForeignKey(
        "organizations.DonVi", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    cau_hinh_nhac_han = models.JSONField(null=True, blank=True)
    create_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="+", db_column="nguoi_tao_id")
    created_at = models.DateTimeField(auto_now_add=True, db_default=DB_NOW)
    update_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+", db_column="nguoi_cap_nhat_id"
    )
    update_at = models.DateTimeField(auto_now=True, db_column="updated_at", db_default=DB_NOW)

    class Meta:
        db_table = "signing_process"
        constraints = [
            models.UniqueConstraint(fields=["ma_quy_trinh", "phien_ban"], name="uq_signing_process_ma_phien_ban"),
            models.CheckConstraint(
                condition=(Q(pham_vi=enums.PhamViQuyTrinh.PHONG_BAN) & Q(don_vi_ap_dung_id__isnull=False))
                | (Q(pham_vi=enums.PhamViQuyTrinh.CONG_TY) & Q(don_vi_ap_dung_id__isnull=True)),
                name="chk_signing_process_don_vi_ap_dung",
            ),
        ]

    def __str__(self):
        return f"{self.ma_quy_trinh} v{self.phien_ban}"


class SigningProcessStep(models.Model):
    quy_trinh = models.ForeignKey(SigningProcess, on_delete=models.CASCADE, related_name="cap_ky_set")
    cap_ky = models.PositiveSmallIntegerField()
    ten_cap_ky = models.CharField(max_length=255)
    thu_tu = models.PositiveSmallIntegerField()
    # Đơn vị cố định cho người ký theo chức vụ; DDL không đánh index.
    don_vi = models.ForeignKey(
        "organizations.DonVi", null=True, blank=True, on_delete=models.SET_NULL, related_name="+", db_index=False
    )
    so_gio_xu_ly = models.PositiveIntegerField(null=True, blank=True)
    dang_ap_dung = models.BooleanField(db_default=True, default=True)
    ghi_chu = models.TextField(blank=True, db_default="", default="")
    created_at = models.DateTimeField(auto_now_add=True, db_default=DB_NOW)

    class Meta:
        db_table = "signing_process_step"
        ordering = ["thu_tu"]
        constraints = [
            models.UniqueConstraint(fields=["quy_trinh", "thu_tu"], name="uq_signing_process_step_thu_tu"),
        ]

    def __str__(self):
        return f"{self.quy_trinh_id}/{self.thu_tu} {self.ten_cap_ky}"


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3 — model phụ thuộc Phase 2
# Không dùng default cho document_type: người tạo phải chỉ rõ loại văn bản.
# chuc_vu là FK accounts_position theo DDL; DDL không đánh index cột này.
# ─────────────────────────────────────────────────────────────────────────────


class SigningProcessStepSigner(models.Model):
    buoc_quy_trinh = models.ForeignKey(SigningProcessStep, on_delete=models.CASCADE, related_name="nguoi_ky_set")
    nguoi_ky = models.ForeignKey(User, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    chuc_vu = models.ForeignKey(
        "accounts.Position", null=True, blank=True, on_delete=models.PROTECT, related_name="+", db_index=False
    )
    # Chỉ dùng khi cấu hình theo chức vụ; rỗng khi cấu hình theo tài khoản (#80 Phase 7)
    pham_vi_chuc_vu = models.CharField(max_length=20, choices=enums.PhamViChucVu.choices, null=True, blank=True)
    vai_tro_ky = models.CharField(max_length=20, choices=enums.VaiTroKy.choices, db_default="KY_CHINH", default=enums.VaiTroKy.KY_CHINH)
    thu_tu = models.PositiveSmallIntegerField()
    created_at = models.DateTimeField(auto_now_add=True, db_default=DB_NOW)

    class Meta:
        db_table = "signing_process_step_signer"
        constraints = [
            models.CheckConstraint(
                condition=(Q(nguoi_ky__isnull=False) & Q(chuc_vu_id__isnull=True))
                | (Q(nguoi_ky__isnull=True) & Q(chuc_vu_id__isnull=False)),
                name="chk_signing_process_step_signer_mot_doi_tuong",
            ),
        ]


class SigningRequest(models.Model):
    # Văn bản trình ký: gắn văn bản đi đã đăng ký hoặc PDF dự thảo chưa vào sổ; hồ sơ có id tự cấp.
    # PDF đã chọn được sao chép vào kho Trình ký để chụp nguyên bản tài liệu của lượt trình.
    document_type = models.CharField(max_length=20, choices=enums.LoaiVanBan.choices, null=True, blank=True)
    van_ban_id = models.BigIntegerField(db_column="document_id", null=True, blank=True)
    so_hieu_van_ban = models.CharField(max_length=100, blank=True, db_default="", default="")
    trich_yeu_van_ban = models.TextField(blank=True, db_default="", default="")
    # Bản sao từ lượt trình hiện hành; nguồn sự thật là SigningAttempt.
    phien_ban_van_ban = models.CharField(max_length=50, null=True, blank=True)
    vi_tri_luu_tep = models.CharField(max_length=500, null=True, blank=True)
    ma_bam_tai_lieu = models.CharField(max_length=64, null=True, blank=True)
    quy_trinh = models.ForeignKey(SigningProcess, on_delete=models.PROTECT, related_name="+")
    phien_ban_quy_trinh = models.PositiveSmallIntegerField()
    # Trình lại sau từ chối tạo yêu cầu mới trỏ về yêu cầu bị từ chối (#80 Phase 7)
    ho_so_goc = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="trinh_lai_set")
    trang_thai = models.CharField(
        max_length=20, choices=enums.TrangThaiYeuCau.choices, db_default="NHAP", default=enums.TrangThaiYeuCau.NHAP
    )
    han_chot = models.DateTimeField(null=True, blank=True)
    ngay_gui = models.DateTimeField(null=True, blank=True)
    ngay_hoan_thanh = models.DateTimeField(null=True, blank=True)
    ngay_tu_choi = models.DateTimeField(null=True, blank=True)
    ly_do_tu_choi = models.TextField(blank=True, db_default="", default="")
    ngay_huy = models.DateTimeField(null=True, blank=True)
    ly_do_huy = models.TextField(blank=True, db_default="", default="")
    ghi_chu = models.TextField(blank=True, db_default="", default="")
    create_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="+", db_column="nguoi_tao_id")
    created_at = models.DateTimeField(auto_now_add=True, db_default=DB_NOW)
    update_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+", db_column="nguoi_cap_nhat_id"
    )
    update_at = models.DateTimeField(auto_now=True, db_column="updated_at", db_default=DB_NOW)

    class Meta:
        db_table = "signing_request"
        indexes = [
            models.Index(fields=["trang_thai"], name="idx_signing_req_trang_thai"),
            models.Index(fields=["document_type", "van_ban_id"], name="idx_signing_req_document"),
            models.Index(fields=["han_chot"], name="idx_signing_req_hanchot"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=sha256_or_null("ma_bam_tai_lieu"), name="chk_signing_request_ma_bam_sha256"
            ),
            models.CheckConstraint(
                condition=(Q(document_type__isnull=False) & Q(van_ban_id__isnull=False))
                | (Q(document_type__isnull=True) & Q(van_ban_id__isnull=True) & ~Q(trich_yeu_van_ban="")),
                name="chk_signing_request_van_ban",
            ),
            models.UniqueConstraint(
                fields=["document_type", "van_ban_id"],
                condition=Q(trang_thai=enums.TrangThaiYeuCau.HOAN_THANH, van_ban_id__isnull=False),
                name="uq_signing_completed_doc",
            ),
        ]


class SigningAttempt(models.Model):
    trinh_ky = models.ForeignKey(SigningRequest, on_delete=models.PROTECT, related_name="luot_trinh_set")
    so_luot = models.PositiveSmallIntegerField()
    luot_truoc = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    phien_ban_van_ban = models.CharField(max_length=50, null=True, blank=True)
    vi_tri_luu_tep = models.CharField(max_length=500)
    ma_bam_tai_lieu = models.CharField(max_length=64)
    trang_thai = models.CharField(
        max_length=20, choices=enums.TrangThaiLuotTrinh.choices, db_default="NHAP", default=enums.TrangThaiLuotTrinh.NHAP
    )
    ly_do = models.TextField(blank=True, db_default="", default="")
    khoa_chong_trung = models.CharField(max_length=255, null=True, blank=True, unique=True)
    thoi_diem_gui = models.DateTimeField(null=True, blank=True)
    thoi_diem_hoan_thanh = models.DateTimeField(null=True, blank=True)
    thoi_diem_tu_choi = models.DateTimeField(null=True, blank=True)
    thoi_diem_huy = models.DateTimeField(null=True, blank=True)
    vi_tri_tep_hoan_tat = models.CharField(max_length=500, blank=True, db_default="", default="")
    ma_bam_tep_hoan_tat = models.CharField(max_length=64, blank=True, db_default="", default="")
    trang_thai_tep_hoan_tat = models.CharField(
        max_length=20, choices=enums.TrangThaiTepHoanTat.choices, null=True, blank=True
    )
    loi_tep_hoan_tat = models.CharField(max_length=100, blank=True, db_default="", default="")
    create_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="+", db_column="nguoi_tao_id")
    created_at = models.DateTimeField(auto_now_add=True, db_default=DB_NOW)
    update_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+", db_column="nguoi_cap_nhat_id"
    )
    update_at = models.DateTimeField(auto_now=True, db_column="updated_at", db_default=DB_NOW)

    class Meta:
        db_table = "signing_attempt"
        constraints = [
            models.UniqueConstraint(fields=["trinh_ky", "so_luot"], name="uq_signing_attempt_so_luot"),
            models.CheckConstraint(
                condition=Q(ma_bam_tai_lieu__regex=r"^[0-9a-f]{64}$"), name="chk_signing_attempt_ma_bam_sha256"
            ),
        ]

    def delete(self, *args, **kwargs):
        if self.trang_thai != enums.TrangThaiLuotTrinh.NHAP or self.manifest_set.exists():
            raise ImmutableEvidenceError("bang_chung_bat_bien", "Lượt trình đã gửi không được xóa.")
        return super().delete(*args, **kwargs)


class SigningRequestStep(models.Model):
    luot_trinh = models.ForeignKey(SigningAttempt, on_delete=models.PROTECT, related_name="cap_ky_set")
    buoc_quy_trinh = models.ForeignKey(SigningProcessStep, on_delete=models.PROTECT, related_name="+")
    cap_ky = models.PositiveSmallIntegerField()
    ten_cap_ky = models.CharField(max_length=255)
    thu_tu = models.PositiveSmallIntegerField()
    trang_thai = models.CharField(
        max_length=20, choices=enums.TrangThaiCapKy.choices, db_default="CHUA_MO", default=enums.TrangThaiCapKy.CHUA_MO
    )
    han_xu_ly = models.DateTimeField(null=True, blank=True)
    thoi_diem_mo = models.DateTimeField(null=True, blank=True)
    thoi_diem_hoan_thanh = models.DateTimeField(null=True, blank=True)
    ghi_chu = models.TextField(blank=True, db_default="", default="")
    created_at = models.DateTimeField(auto_now_add=True, db_default=DB_NOW)

    class Meta:
        db_table = "signing_request_step"
        ordering = ["thu_tu"]
        indexes = [models.Index(fields=["han_xu_ly"], name="idx_signing_step_hanxuly")]
        constraints = [
            models.UniqueConstraint(fields=["luot_trinh", "thu_tu"], name="uq_signing_request_step_thu_tu"),
        ]


class SigningRequestStepSigner(models.Model):
    buoc_ky = models.ForeignKey(SigningRequestStep, on_delete=models.PROTECT, related_name="nguoi_ky_set")
    nguoi_ky = models.ForeignKey(User, on_delete=models.PROTECT, related_name="+")
    chuc_vu = models.ForeignKey(
        "accounts.Position", null=True, blank=True, on_delete=models.SET_NULL, related_name="+", db_index=False
    )
    ten_nguoi_ky = models.CharField(max_length=255)
    ten_chuc_vu = models.CharField(max_length=255, null=True, blank=True)
    vai_tro_ky = models.CharField(max_length=20, choices=enums.VaiTroKy.choices)
    trang_thai = models.CharField(
        max_length=20, choices=enums.TrangThaiNguoiKy.choices, db_default="CHO_KY", default=enums.TrangThaiNguoiKy.CHO_KY
    )
    thoi_diem_mo = models.DateTimeField(null=True, blank=True)
    ngay_ky = models.DateTimeField(null=True, blank=True)
    ngay_tu_choi = models.DateTimeField(null=True, blank=True)
    ly_do_tu_choi = models.TextField(blank=True, db_default="", default="")
    # Con trỏ chữ ký hiện hành; ràng buộc "thuộc đúng người ký" kiểm ở tầng service.
    chu_ky_hien_hanh = models.ForeignKey(
        "SigningSignature", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    trang_ky = models.PositiveIntegerField(null=True, blank=True)
    toa_do_x = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    toa_do_y = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    chieu_rong_khung = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    chieu_cao_khung = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    khoa_chong_trung_thao_tac = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_default=DB_NOW)

    class Meta:
        db_table = "signing_request_step_signer"
        constraints = [
            models.UniqueConstraint(fields=["buoc_ky", "nguoi_ky"], name="uq_signing_request_step_signer_nguoi_ky"),
        ]


class EvidenceQuerySet(models.QuerySet):
    """QuerySet chặn UPDATE/DELETE hàng loạt lên bằng chứng (SQLite không có trigger)."""

    def update(self, **kwargs):
        raise ImmutableEvidenceError()

    def delete(self):
        raise ImmutableEvidenceError()


class SignatureQuerySet(EvidenceQuerySet):
    VERIFY_FIELDS = {"trang_thai_xac_minh", "thoi_diem_xac_minh"}

    def update(self, **kwargs):
        if not set(kwargs) <= self.VERIFY_FIELDS:
            raise ImmutableEvidenceError("bang_chung_bat_bien", "Chữ ký số chỉ được cập nhật kết quả xác minh.")
        return super(EvidenceQuerySet, self).update(**kwargs)


class SigningSignature(models.Model):
    luot_trinh = models.ForeignKey(SigningAttempt, on_delete=models.PROTECT, related_name="chu_ky_set")
    buoc_ky = models.ForeignKey(SigningRequestStepSigner, on_delete=models.PROTECT, related_name="chu_ky_set")
    khoa_ky = models.ForeignKey(SigningKey, on_delete=models.PROTECT, related_name="+")
    hash_tai_lieu = models.CharField(max_length=64)
    thuat_toan = models.CharField(max_length=50)
    chu_ky_so = models.TextField()
    ghi_chu_ky = models.TextField(blank=True, db_default="", default="")
    ky_tre_han = models.BooleanField(db_default=False, default=False)
    so_giay_tre = models.PositiveIntegerField(null=True, blank=True)
    ngay_ky = models.DateTimeField(db_default=DB_NOW, default=timezone.now)
    trang_thai_xac_minh = models.CharField(
        max_length=20, choices=enums.TrangThaiXacMinh.choices, db_default="HOP_LE", default=enums.TrangThaiXacMinh.HOP_LE
    )
    thoi_diem_xac_minh = models.DateTimeField(null=True, blank=True)
    vi_tri_anh_chu_ky = models.CharField(max_length=500, blank=True, db_default="", default="")
    ma_bam_anh_chu_ky = models.CharField(max_length=64, blank=True, db_default="", default="")
    created_at = models.DateTimeField(auto_now_add=True, db_default=DB_NOW)

    objects = SignatureQuerySet.as_manager()
    VERIFY_FIELDS = SignatureQuerySet.VERIFY_FIELDS

    class Meta:
        db_table = "signing_signature"
        constraints = [
            models.CheckConstraint(
                condition=Q(hash_tai_lieu__regex=r"^[0-9a-f]{64}$"), name="chk_signing_signature_hash_sha256"
            ),
        ]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            old = type(self).objects.get(pk=self.pk)
            core = [f.attname for f in self._meta.concrete_fields if f.name not in self.VERIFY_FIELDS]
            if any(getattr(old, f) != getattr(self, f) for f in core):
                raise ImmutableEvidenceError("bang_chung_bat_bien", "Chữ ký số chỉ được cập nhật kết quả xác minh.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ImmutableEvidenceError("bang_chung_bat_bien", "Chữ ký số không được xóa.")


class ManifestQuerySet(models.QuerySet):
    def update(self, **kwargs):
        if self.filter(trang_thai=enums.TrangThaiManifest.DA_CHOT).exists():
            raise ImmutableEvidenceError()
        return super().update(**kwargs)

    def delete(self):
        if self.filter(trang_thai=enums.TrangThaiManifest.DA_CHOT).exists():
            raise ImmutableEvidenceError()
        return super().delete()


class SigningManifest(models.Model):
    luot_trinh = models.ForeignKey(SigningAttempt, on_delete=models.PROTECT, related_name="manifest_set")
    phien_ban_bang_chung = models.PositiveSmallIntegerField(db_default=1, default=1)
    noi_dung_chuan_hoa = models.JSONField()
    ma_bam_bang_chung = models.CharField(max_length=64)
    vi_tri_luu = models.CharField(max_length=500, null=True, blank=True)
    trang_thai = models.CharField(
        max_length=20, choices=enums.TrangThaiManifest.choices, db_default="NHAP", default=enums.TrangThaiManifest.NHAP
    )
    thoi_diem_chot = models.DateTimeField(null=True, blank=True)
    create_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="+", db_column="nguoi_tao_id")
    created_at = models.DateTimeField(auto_now_add=True, db_default=DB_NOW)

    objects = ManifestQuerySet.as_manager()

    class Meta:
        db_table = "signing_manifest"
        constraints = [
            models.CheckConstraint(
                condition=Q(ma_bam_bang_chung__regex=r"^[0-9a-f]{64}$"), name="chk_signing_manifest_ma_bam_sha256"
            ),
        ]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            if type(self).objects.filter(pk=self.pk, trang_thai=enums.TrangThaiManifest.DA_CHOT).exists():
                raise ImmutableEvidenceError("bang_chung_bat_bien", "Manifest đã chốt không được sửa.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.trang_thai == enums.TrangThaiManifest.DA_CHOT:
            raise ImmutableEvidenceError("bang_chung_bat_bien", "Manifest đã chốt không được xóa.")
        return super().delete(*args, **kwargs)


class SigningChangeThread(models.Model):
    luot_trinh = models.ForeignKey(SigningAttempt, on_delete=models.PROTECT, related_name="yeu_cau_sua_set")
    nguoi_yeu_cau = models.ForeignKey(User, on_delete=models.PROTECT, related_name="+")
    tieu_de = models.CharField(max_length=255)
    ly_do = models.TextField()
    trang_thai = models.CharField(
        max_length=20, choices=enums.TrangThaiThread.choices, db_default="DANG_MO", default=enums.TrangThaiThread.DANG_MO
    )
    thoi_diem_giai_quyet = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_default=DB_NOW)
    update_at = models.DateTimeField(auto_now=True, db_column="updated_at", db_default=DB_NOW)

    class Meta:
        db_table = "signing_change_thread"


class SigningChangeMessage(models.Model):
    yeu_cau_sua = models.ForeignKey(SigningChangeThread, on_delete=models.PROTECT, related_name="tin_nhan_set")
    nguoi_viet = models.ForeignKey(User, on_delete=models.PROTECT, related_name="+")
    noi_dung = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True, db_default=DB_NOW)

    class Meta:
        db_table = "signing_change_message"


class SigningAuditLog(models.Model):
    """Nhật ký chỉ ghi thêm; không UPDATE, không DELETE."""

    LOAI_LUONG_KY = (
        "signing_request", "signing_attempt", "signing_request_step_signer", "signing_signature",
    )

    trinh_ky = models.ForeignKey(SigningRequest, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    luot_trinh = models.ForeignKey(SigningAttempt, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    buoc_ky = models.ForeignKey(
        SigningRequestStepSigner, null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    loai_doi_tuong = models.CharField(max_length=50)
    ma_doi_tuong = models.BigIntegerField()
    nguoi_thuc_hien = models.ForeignKey(User, on_delete=models.PROTECT, related_name="+")
    hanh_dong = models.CharField(max_length=50)
    trang_thai_truoc = models.CharField(max_length=20, blank=True, db_default="", default="")
    trang_thai_sau = models.CharField(max_length=20, blank=True, db_default="", default="")
    chi_tiet = models.TextField(blank=True, db_default="", default="")
    du_lieu_kem_theo = models.JSONField(null=True, blank=True)
    dia_chi_ip = models.CharField(max_length=45, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_default=DB_NOW)

    objects = EvidenceQuerySet.as_manager()

    class Meta:
        db_table = "signing_audit_log"
        constraints = [
            models.CheckConstraint(
                condition=~Q(loai_doi_tuong__in=["signing_request", "signing_attempt",
                                                 "signing_request_step_signer", "signing_signature"])
                | Q(trinh_ky__isnull=False),
                name="chk_signing_audit_log_luong_ky_co_trinh_ky",
            ),
        ]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ImmutableEvidenceError("bang_chung_bat_bien", "Nhật ký trình ký chỉ được ghi thêm.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ImmutableEvidenceError("bang_chung_bat_bien", "Nhật ký trình ký không được xóa.")


class SigningNotification(models.Model):
    trinh_ky = models.ForeignKey(SigningRequest, on_delete=models.CASCADE, related_name="+")
    buoc_ky = models.ForeignKey(
        SigningRequestStepSigner, null=True, blank=True, on_delete=models.CASCADE, related_name="+"
    )
    nguoi_nhan = models.ForeignKey(User, on_delete=models.PROTECT, related_name="+")
    kenh = models.CharField(max_length=20, choices=enums.KenhThongBao.choices)
    loai_thong_bao = models.CharField(max_length=50)
    trang_thai = models.CharField(
        max_length=20, choices=enums.TrangThaiThongBao.choices, db_default="CHO_GUI", default=enums.TrangThaiThongBao.CHO_GUI
    )
    hen_gio_gui = models.DateTimeField(null=True, blank=True)
    khoa_chong_gui_trung = models.CharField(max_length=255, unique=True)
    so_lan_gui_lai = models.PositiveIntegerField(db_default=0, default=0)
    thoi_diem_gui = models.DateTimeField(null=True, blank=True)
    loi_gui = models.TextField(blank=True, db_default="", default="")
    created_at = models.DateTimeField(auto_now_add=True, db_default=DB_NOW)

    class Meta:
        db_table = "signing_notification"
        indexes = [models.Index(fields=["trang_thai", "hen_gio_gui"], name="idx_signing_notif_outbox")]


# ─────────────────────────────────────────────────────────────────────────────
# Phase 6 — mở khóa ký bằng PIN (signing-backend-plan.md mục 3.4, bảng signing_key_unlock)
# ─────────────────────────────────────────────────────────────────────────────


class SigningKeyUnlock(models.Model):
    """
    Trạng thái mở khóa ký bằng PIN của một khóa ký. Bảng trạng thái (được cập nhật),
    không phải bảng bằng chứng; mọi sự kiện ghi vào signing_audit_log.
    Không lưu PIN, không lưu khóa bí mật hay bản bọc khóa bí mật.
    """

    khoa = models.OneToOneField(SigningKey, on_delete=models.PROTECT, related_name="mo_khoa_pin")
    ma_bam_xac_minh_pin = models.TextField()  # HMAC của verifier, không lưu PIN
    manh_bi_mat_ma_hoa = models.TextField()  # k_srv mã hóa khi lưu; không log
    tham_so_kdf = models.JSONField()  # thuật toán, m, t, p, phiên bản
    so_lan_sai = models.PositiveIntegerField(db_default=0, default=0)
    khoa_den = models.DateTimeField(null=True, blank=True)  # rỗng: không bị khóa tạm
    created_at = models.DateTimeField(auto_now_add=True, db_default=DB_NOW)
    # DDL base dùng updated_at (trigger set_updated_at), khác update_at của các bảng signing_* khác
    updated_at = models.DateTimeField(auto_now=True, db_default=DB_NOW)

    class Meta:
        db_table = "signing_key_unlock"

    def __str__(self):
        return f"PIN của khóa {self.khoa_id} (sai {self.so_lan_sai} lần)"


class SigningUserSignature(models.Model):
    """
    Ảnh chữ ký cá nhân (PNG) của người dùng để dán lên tệp PDF hoàn tất khi ký duyệt.
    Mỗi người dùng có một ảnh chữ ký hiện hành.
    """

    nguoi_dung = models.OneToOneField(User, on_delete=models.CASCADE, related_name="anh_chu_ky_ca_nhan")
    vi_tri_tep = models.CharField(max_length=500)
    ma_bam = models.CharField(max_length=64)
    dung_luong_bytes = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True, db_default=DB_NOW)
    updated_at = models.DateTimeField(auto_now=True, db_default=DB_NOW)

    class Meta:
        db_table = "signing_user_signature"

    def __str__(self):
        return f"Chữ ký của user {self.nguoi_dung_id} ({self.ma_bam[:8]})"
