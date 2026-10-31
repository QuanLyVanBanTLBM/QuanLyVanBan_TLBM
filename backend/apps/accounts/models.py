import datetime
import uuid

from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.db.models.functions import Now

# Regex kiểm tra số điện thoại Việt Nam chuẩn
vietnam_phone_regex = RegexValidator(
    regex=r"^(0|\+84)[1-9][0-9]{7,9}$",
    message="employees.messages.invalidPhone",
)


class DbNow(Now):
    """DEFAULT now() như release_DDL.sql (Now() của Django sinh STATEMENT_TIMESTAMP() trên PostgreSQL)."""

    def as_postgresql(self, compiler, connection, **extra_context):
        return self.as_sql(compiler, connection, template="now()", **extra_context)


# accounts_position.display_order là INTEGER (32 bit) trong DDL: vượt giá trị này PostgreSQL báo "integer out of range".
MAX_DISPLAY_ORDER = 2147483647


class Position(models.Model):
    """Danh mục Chức vụ — bảng accounts_position theo SQL_Fix4."""

    display_order = models.IntegerField(
        unique=True,
        validators=[MinValueValidator(1)],
        verbose_name="STT ưu tiên hiển thị",
        help_text="Số nguyên dương duy nhất, sắp xếp từ nhỏ đến lớn.",
    )
    name = models.CharField(
        max_length=255,
        verbose_name="Tên chức vụ",
        help_text="Bắt buộc, ví dụ: Tổng Giám đốc, Trưởng phòng, Chuyên viên...",
    )
    is_public = models.BooleanField(default=True, db_default=True, verbose_name="Hiển thị công khai (isPublic)")
    note = models.TextField(null=True, blank=True, default="", verbose_name="Ghi chú")

    class Meta:
        db_table = "accounts_position"
        verbose_name = "Chức vụ"
        verbose_name_plural = "Danh mục Chức vụ"
        ordering = ["display_order", "name", "id"]
        default_permissions = ()
        permissions = [
            ("view_chucvu", "Xem danh sách chức vụ"),
            ("add_chucvu", "Thêm chức vụ"),
            ("change_chucvu", "Sửa chức vụ"),
            ("delete_chucvu", "Xóa chức vụ"),
            ("import_chucvu", "Import file chức vụ"),
        ]

    def __str__(self):
        return self.name

    @classmethod
    def get_next_display_order(cls) -> int:
        """MAX + 1; khi MAX đã chạm trần cột INTEGER của DDL thì lấy số trống nhỏ nhất."""
        latest = cls.objects.order_by("-display_order").values_list("display_order", flat=True).first()
        if latest is None:
            return 1
        if latest < MAX_DISPLAY_ORDER:
            return latest + 1
        expected = 1
        for value in cls.objects.order_by("display_order").values_list("display_order", flat=True):
            if value > expected:
                break
            expected = value + 1
        return expected


class EmployeeManager(BaseUserManager):
    use_in_migrations = True

    def _fill_required_refs(self, extra):
        """DDL bắt buộc ho_ten, ngay_sinh, chuc_vu, don_vi — điền mặc định khi nơi gọi (createsuperuser, test) không truyền."""
        from organizations.models import DonVi, KhoiKhuVuc

        if not extra.get("chuc_vu") and not extra.get("chuc_vu_id"):
            position = Position.objects.order_by("display_order").first()
            if position is None:
                position = Position.objects.create(
                    display_order=Position.get_next_display_order(), name="Quản trị viên"
                )
            extra["chuc_vu"] = position
        if not extra.get("don_vi") and not extra.get("don_vi_id"):
            don_vi = DonVi.objects.order_by("stt_uu_tien").first()
            if don_vi is None:
                khoi, _ = KhoiKhuVuc.objects.get_or_create(ten="Mặc định")
                latest = DonVi.objects.order_by("-stt_uu_tien").first()
                don_vi = DonVi.objects.create(
                    khoi=khoi,
                    stt_uu_tien=(latest.stt_uu_tien + 1) if latest else 1,
                    ten="Quản trị hệ thống",
                )
            extra["don_vi"] = don_vi
        extra.setdefault("ngay_sinh", datetime.date(1990, 1, 1))

    def _create_employee(self, username, password, **extra):
        if not username:
            raise ValueError("Tên đăng nhập không được để trống.")
        extra.setdefault("ho_ten", username)
        self._fill_required_refs(extra)
        email = extra.pop("email", None) or None
        if email:
            email = self.normalize_email(email)
        employee = self.model(username=username, email=email, **extra)
        employee.set_password(password)
        employee.save(using=self._db)
        return employee

    def create_user(self, username, password=None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create_employee(username, password, **extra)

    def create_superuser(self, username, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        if extra.get("is_staff") is not True or extra.get("is_superuser") is not True:
            raise ValueError("Superuser phải có is_staff=True và is_superuser=True.")
        return self._create_employee(username, password, **extra)


class Employee(AbstractBaseUser, PermissionsMixin):
    """
    Cán bộ nhân viên — bảng accounts_employee theo SQL_Fix4, đồng thời là Custom User Model.
    groups / user_permissions (PermissionsMixin) ánh xạ đúng accounts_employee_groups
    và accounts_employee_user_permissions trong DDL.
    """

    class Status(models.TextChoices):
        LAM_VIEC = "LAM_VIEC", "Đang làm việc"
        NGHI_VIEC = "NGHI_VIEC", "Nghỉ việc"

    ho_ten = models.CharField(max_length=150, verbose_name="Họ và tên")
    ngay_sinh = models.DateField(
        verbose_name="Ngày sinh",
        help_text="Lưu đủ ngày/tháng/năm; giao diện che năm với người không có quyền xem đầy đủ.",
    )
    chuc_vu = models.ForeignKey(
        Position,
        on_delete=models.PROTECT,
        db_index=False,
        related_name="employees",
        verbose_name="Chức vụ",
    )
    chuc_danh = models.CharField(
        max_length=150,
        null=True,
        blank=True,
        default="",
        verbose_name="Chức danh (tự do)",
    )
    email = models.EmailField(max_length=254, unique=True, null=True, blank=True, verbose_name="Email")
    sdt = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        default="",
        validators=[vietnam_phone_regex],
        verbose_name="Số điện thoại",
    )
    don_vi = models.ForeignKey(
        "organizations.DonVi",
        on_delete=models.PROTECT,
        db_index=False,
        related_name="employees",
        verbose_name="Đơn vị / Phòng ban",
    )
    username = models.CharField(max_length=150, unique=True, verbose_name="Tên đăng nhập")
    # DDL: password VARCHAR(255) (AbstractBaseUser mặc định 128)
    password = models.CharField(max_length=255, verbose_name="password")
    is_active = models.BooleanField(default=True, db_default=True, verbose_name="Đang hoạt động")
    is_staff = models.BooleanField(default=False, db_default=False, verbose_name="Quyền truy cập trang quản trị")
    is_superuser = models.BooleanField(
        default=False,
        db_default=False,
        verbose_name="superuser status",
        help_text="Designates that this user has all permissions without explicitly assigning them.",
    )
    is_public = models.BooleanField(default=True, db_default=True, verbose_name="Hiển thị công khai")
    # Cột trang_thai dùng ENUM employee_work_status của DDL (đổi kiểu trong migration 0005).
    trang_thai = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.LAM_VIEC,
        db_default=Status.LAM_VIEC,
        verbose_name="Trạng thái làm việc",
    )
    ghi_chu = models.TextField(null=True, blank=True, default="", verbose_name="Ghi chú")
    created_at = models.DateTimeField(auto_now_add=True, db_default=DbNow(), verbose_name="Ngày tạo")
    updated_at = models.DateTimeField(auto_now=True, db_default=DbNow(), verbose_name="Cập nhật lần cuối")

    objects = EmployeeManager()

    USERNAME_FIELD = "username"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["email", "ho_ten"]

    class Meta:
        db_table = "accounts_employee"
        verbose_name = "Cán bộ nhân viên"
        verbose_name_plural = "Cán bộ nhân viên"
        ordering = ["don_vi__stt_uu_tien", "chuc_vu__display_order", "ho_ten", "id"]
        indexes = [
            models.Index(fields=["don_vi"], name="idx_employee_donvi"),
            models.Index(fields=["chuc_vu"], name="idx_employee_chucvu"),
            models.Index(fields=["is_active"], name="idx_employee_is_active"),
        ]
        default_permissions = ()
        permissions = [
            ("view_list_cbnv", "Xem danh sách CBNV"),
            ("view_full_cbnv", "Xem đầy đủ thông tin CBNV (gồm năm sinh, nhóm quyền)"),
            ("add_cbnv", "Thêm CBNV"),
            ("change_full_cbnv", "Sửa mọi thông tin CBNV"),
            ("change_self_cbnv", "Sửa thông tin cá nhân của mình"),
            ("delete_cbnv", "Xóa CBNV"),
            ("approve_password_reset_cbnv", "Duyệt cấp lại mật khẩu CBNV"),
            ("import_cbnv", "Nhập CBNV từ file Excel"),
        ]

    def __str__(self):
        return f"{self.ho_ten} ({self.username})"

    def get_full_name(self):
        return self.ho_ten

    def get_short_name(self):
        return self.ho_ten.split(" ")[-1] if self.ho_ten else self.username

    def save(self, *args, **kwargs):
        if self.trang_thai == self.Status.NGHI_VIEC:
            self.is_active = False
        super().save(*args, **kwargs)


class EmployeeAssignment(models.Model):
    """
    Phân công công tác / Kiêm nhiệm đơn vị & chức vụ của Cán bộ nhân viên (Issue #24).
    Cho phép một nhân viên có thể thuộc nhiều phòng ban và đảm nhiệm nhiều chức vụ khác nhau.
    """

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="assignments",
        verbose_name="Cán bộ nhân viên",
    )
    don_vi = models.ForeignKey(
        "organizations.DonVi",
        on_delete=models.PROTECT,
        related_name="employee_assignments",
        verbose_name="Đơn vị / Phòng ban",
    )
    chuc_vu = models.ForeignKey(
        Position,
        on_delete=models.PROTECT,
        related_name="employee_assignments",
        verbose_name="Chức vụ",
    )
    chuc_danh = models.CharField(
        max_length=150,
        null=True,
        blank=True,
        default="",
        verbose_name="Chức danh kiêm nhiệm (tự do)",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_default=DbNow(),
        verbose_name="Ngày phân công",
    )

    class Meta:
        db_table = "accounts_employee_assignment"
        verbose_name = "Phân công kiêm nhiệm"
        verbose_name_plural = "Danh sách phân công kiêm nhiệm"
        unique_together = ("employee", "don_vi", "chuc_vu")
        indexes = [
            models.Index(fields=["employee"], name="idx_emp_assign_emp"),
            models.Index(fields=["don_vi"], name="idx_emp_assign_donvi"),
            models.Index(fields=["chuc_vu"], name="idx_emp_assign_chucvu"),
        ]

    def __str__(self):
        return f"{self.employee.ho_ten} - {self.don_vi.ten} ({self.chuc_vu.name})"


class EmployeeImportJob(models.Model):
    """Trạng thái bền vững của một lượt nhập Excel CBNV nền."""

    class Status(models.TextChoices):
        QUEUED = "queued", "Đang chờ"
        PROCESSING = "processing", "Đang xử lý"
        DONE = "done", "Hoàn tất"
        FAILED = "failed", "Thất bại"

    class Phase(models.TextChoices):
        QUEUED = "queued", "Đang chờ"
        VALIDATION = "validation", "Kiểm tra dữ liệu"
        SAVING = "saving", "Đang lưu"
        COMPLETE = "complete", "Hoàn tất"
        FAILED = "failed", "Thất bại"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="employee_import_jobs",
    )
    idempotency_key = models.CharField(max_length=128, null=True, blank=True)
    active_key = models.CharField(max_length=32, null=True, blank=True)
    file_path = models.CharField(max_length=1024)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.QUEUED,
        db_default=Status.QUEUED,
    )
    phase = models.CharField(
        max_length=16,
        choices=Phase.choices,
        default=Phase.QUEUED,
        db_default=Phase.QUEUED,
    )
    processed = models.PositiveIntegerField(default=0, db_default=0)
    total = models.PositiveIntegerField(default=0, db_default=0)
    created_count = models.PositiveIntegerField(default=0, db_default=0)
    errors = models.JSONField(default=list, db_default=models.Value([], output_field=models.JSONField()))
    message = models.CharField(max_length=100, blank=True, default="", db_default="")
    created_at = models.DateTimeField(auto_now_add=True, db_default=DbNow())
    updated_at = models.DateTimeField(auto_now=True, db_default=DbNow())

    class Meta:
        db_table = "accounts_employee_import_job"
        verbose_name = "Lượt nhập Excel CBNV"
        verbose_name_plural = "Lượt nhập Excel CBNV"
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "idempotency_key"],
                name="uq_employee_import_owner_idem",
            ),
            models.UniqueConstraint(
                fields=["active_key"],
                name="uq_employee_import_active_key",
            ),
        ]
        indexes = [
            models.Index(fields=["status", "created_at"], name="idx_employee_import_status"),
        ]


class EmployeePasswordResetAudit(models.Model):
    """Nhật ký kiểm toán về lần admin đặt lại mật khẩu CBNV."""

    class Reason(models.TextChoices):
        FORGOT_PASSWORD = "FORGOT_PASSWORD", "Quên mật khẩu"
        COMPROMISED = "COMPROMISED", "Bị xâm phạm"
        LOST_ACCESS = "LOST_ACCESS", "Mất quyền truy cập"
        OTHER = "OTHER", "Khác"

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        db_index=False,
        related_name="password_reset_actions",
        verbose_name="Quản trị viên thực hiện",
    )
    target = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        db_index=False,
        related_name="password_reset_events",
        verbose_name="Tài khoản được đặt lại mật khẩu",
    )
    actor_username = models.CharField(max_length=150)
    target_username = models.CharField(max_length=150)
    reason_code = models.CharField(max_length=32, choices=Reason.choices)
    reason_detail = models.CharField(max_length=500, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_default=DbNow())

    class Meta:
        db_table = "accounts_password_reset_audit"
        verbose_name = "Nhật ký đặt lại mật khẩu CBNV"
        verbose_name_plural = "Nhật ký đặt lại mật khẩu CBNV"
        default_permissions = ()
        indexes = [
            models.Index(fields=["target", "created_at"], name="idx_pwd_reset_target_time"),
            models.Index(fields=["actor", "created_at"], name="idx_pwd_reset_actor_time"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    reason_code__in=["FORGOT_PASSWORD", "COMPROMISED", "LOST_ACCESS", "OTHER"]
                ),
                name="chk_pwd_reset_reason_code",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(reason_code="OTHER", reason_detail__isnull=False)
                )
                | (
                    ~models.Q(reason_code="OTHER")
                    & models.Q(reason_detail__isnull=True)
                ),
                name="chk_pwd_reset_reason_detail",
            ),
        ]
