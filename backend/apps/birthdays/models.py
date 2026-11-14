from django.conf import settings
from django.db import models
from django.db.models import Q
from django.db.models.functions import Now
from django.utils import timezone


class DbNow(Now):
    """DEFAULT now() như release_DDL.sql (Now() của Django sinh STATEMENT_TIMESTAMP() trên PostgreSQL)."""

    def as_postgresql(self, compiler, connection, **extra_context):
        return self.as_sql(compiler, connection, template="now()", **extra_context)


class BirthdayWishStatus(models.TextChoices):
    PENDING = "PENDING", "Chờ duyệt"
    APPROVED = "APPROVED", "Đã duyệt"
    REJECTED = "REJECTED", "Từ chối"


class BirthdayWish(models.Model):
    """Lời chúc mừng sinh nhật cán bộ nhân viên — bảng birthdays_birthdaywish theo SQL_Fix4."""

    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="birthday_wishes",
        verbose_name="Nhân viên nhận lời chúc",
    )
    sender_name = models.CharField(max_length=150, verbose_name="Người gửi lời chúc")
    message = models.TextField(verbose_name="Nội dung lời chúc mừng")
    card_template = models.CharField(
        max_length=50,
        default="GOLDEN",
        db_default="GOLDEN",
        verbose_name="Mẫu thiệp chúc mừng",
    )
    is_anonymous = models.BooleanField(default=False, db_default=False, verbose_name="Gửi ẩn danh")
    trang_thai = models.CharField(
        max_length=20,
        choices=BirthdayWishStatus.choices,
        default=BirthdayWishStatus.APPROVED,
        db_default=BirthdayWishStatus.APPROVED,
        verbose_name="Trạng thái kiểm duyệt",
    )
    sticker_url = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        verbose_name="Đường dẫn sticker",
    )
    likes_count = models.IntegerField(default=0, db_default=0, verbose_name="Lượt thích")
    created_at = models.DateTimeField(default=timezone.now, db_default=DbNow(), verbose_name="Thời gian gửi")
    updated_at = models.DateTimeField(auto_now=True, db_default=DbNow(), verbose_name="Cập nhật lần cuối")

    class Meta:
        db_table = "birthdays_birthdaywish"
        verbose_name = "Lời chúc sinh nhật"
        verbose_name_plural = "Danh sách lời chúc sinh nhật"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["employee"], name="idx_birthdaywish_employee"),
        ]

    def __str__(self):
        return f"Lời chúc gửi {self.employee}: {self.sender_name} - {self.get_trang_thai_display()}"


class BirthdayEmailStatus(models.TextChoices):
    PENDING = "PENDING", "Chờ xử lý"
    SENDING = "SENDING", "Đang gửi"
    SUCCESS = "SUCCESS", "Gửi thành công"
    FAILED = "FAILED", "Thất bại"
    RETRY = "RETRY", "Chờ gửi lại"


class BirthdayEmailSource(models.TextChoices):
    AUTO = "AUTO", "Tự động"
    MANUAL = "MANUAL", "Thủ công"
    MANUAL_RESEND = "MANUAL_RESEND", "Quản trị viên gửi lại"


class BirthdaySchedulerStatus(models.TextChoices):
    RUNNING = "RUNNING", "Đang chạy"
    SUCCESS = "SUCCESS", "Thành công"
    FAILED = "FAILED", "Thất bại"
    UNKNOWN = "UNKNOWN", "Chưa xác định"


class BirthdaySchedulerRun(models.Model):
    class Trigger(models.TextChoices):
        SCHEDULED = "SCHEDULED", "Theo lịch"
        RECOVERY = "RECOVERY", "Chạy bù"

    class Slot(models.TextChoices):
        PRIMARY = "07:00", "07:00"
        FALLBACK = "07:37", "07:37"

    execution_id = models.CharField(max_length=80, unique=True)
    processing_date = models.DateField()
    trigger_source = models.CharField(max_length=9, choices=Trigger.choices)
    scheduled_slot = models.CharField(max_length=5, choices=Slot.choices, null=True)
    started_at = models.DateTimeField()
    ended_at = models.DateTimeField(null=True)
    status = models.CharField(max_length=7, choices=BirthdaySchedulerStatus.choices)
    total_eligible = models.IntegerField(null=True)
    sent_count = models.IntegerField(null=True)
    failed_count = models.IntegerField(null=True)
    skipped_count = models.IntegerField(null=True)
    retry_count = models.IntegerField(null=True)
    error_reason = models.TextField(null=True)
    github_run_id = models.CharField(max_length=24, null=True)

    class Meta:
        db_table = "birthdays_birthdayschedulerrun"
        ordering = ["-started_at", "-pk"]
        indexes = [
            models.Index(fields=["processing_date", "-started_at"], name="idx_birthdayrun_date_started"),
        ]


class BirthdayEmailTemplate(models.Model):
    name = models.CharField(max_length=120)
    layout = models.CharField(max_length=2)
    subject = models.CharField(max_length=255)
    message = models.TextField()
    created_at = models.DateTimeField(default=timezone.now, db_default=Now())

    class Meta:
        db_table = "birthdays_birthdayemailtemplate"
        ordering = ["-id"]


class BirthdayEmailLog(models.Model):
    """Nhật ký gửi email chúc mừng sinh nhật theo kỳ của từng CBNV."""

    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        db_index=False,
        related_name="birthday_email_logs",
        verbose_name="Nhân viên được chúc mừng",
    )
    sent_date = models.DateField(verbose_name="Ngày sinh nhật ghi nhận")
    sent_at = models.DateTimeField(default=timezone.now, verbose_name="Thời điểm gửi")
    recipient_email = models.CharField(max_length=254, verbose_name="Địa chỉ email người nhận")
    subject = models.CharField(max_length=255, verbose_name="Tiêu đề email")
    card_template = models.CharField(
        max_length=50,
        default="GOLDEN",
        db_default="GOLDEN",
        verbose_name="Mẫu thiệp gửi kèm",
    )
    trang_thai = models.CharField(
        max_length=20,
        choices=BirthdayEmailStatus.choices,
        default=BirthdayEmailStatus.PENDING,
        db_default=BirthdayEmailStatus.PENDING,
        verbose_name="Trạng thái gửi",
    )
    error_message = models.TextField(
        null=True,
        blank=True,
        verbose_name="Chi tiết lỗi nếu thất bại",
    )
    retry_count = models.IntegerField(
        default=0,
        db_default=0,
        verbose_name="Số lần thử gửi lại",
    )
    next_retry_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Thời điểm thử lại tiếp theo",
    )
    smtp_response_code = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="Mã phản hồi SMTP",
    )
    opened_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Thời điểm mở thư",
    )
    clicked_count = models.IntegerField(
        default=0,
        db_default=0,
        verbose_name="Số lượt nhấn liên kết trong thư",
    )
    email_provider = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="Nhà cung cấp dịch vụ email",
    )
    delivery_source = models.CharField(
        max_length=16, choices=BirthdayEmailSource.choices,
        default=BirthdayEmailSource.AUTO, db_default=BirthdayEmailSource.AUTO,
    )
    delivery_snapshot = models.JSONField(null=True, blank=True)
    last_operator = models.CharField(max_length=150, null=True, blank=True)
    resend_request_id = models.UUIDField(null=True, blank=True, unique=True)
    delivery_uncertain = models.BooleanField(default=False, db_default=False)
    updated_at = models.DateTimeField(
        auto_now=True,
        db_default=DbNow(),
        verbose_name="Cập nhật lần cuối",
    )

    class Meta:
        db_table = "birthdays_birthdayemaillog"
        verbose_name = "Nhật ký email sinh nhật"
        verbose_name_plural = "Nhật ký email sinh nhật tự động"
        ordering = ["-sent_date", "-sent_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["employee", "sent_date"],
                condition=Q(delivery_source=BirthdayEmailSource.AUTO),
                name="uq_emaillog_employee_date_auto",
            ),
            models.UniqueConstraint(
                fields=["employee", "sent_date"],
                condition=Q(delivery_source=BirthdayEmailSource.MANUAL),
                name="uq_emaillog_employee_date_manual",
            ),
            models.UniqueConstraint(
                fields=["employee", "sent_date"],
                condition=Q(
                    delivery_source=BirthdayEmailSource.MANUAL_RESEND,
                    trang_thai=BirthdayEmailStatus.SENDING,
                ),
                name="uq_emaillog_resend_inflight",
            ),
        ]

    def __str__(self):
        return f"Email sinh nhật: {self.employee} ({self.sent_date:%d/%m/%Y}) - {self.get_trang_thai_display()}"
