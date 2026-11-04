from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Case, CharField, Exists, F, IntegerField, OuterRef, Q, Value, When
from django.utils import timezone

from document_storage import build_dated_path, get_document_storage


# ==========================================================================
# HẰNG SỐ & VALIDATOR FILE
# Dùng chung cho file đính kèm lúc giao việc và file bằng chứng hoàn thành.
# ==========================================================================

ALLOWED_FILE_EXTENSIONS = {"pdf", "doc", "docx", "jpg", "jpeg", "png"}
IMAGE_FILE_EXTENSIONS = {"jpg", "jpeg", "png"}
MAX_FILE_SIZE = 20 * 1024 * 1024  # dung lượng phải NHỎ HƠN 20MB

# Vai trò "người tạo" không lưu trong TaskParticipant, chỉ dùng khi tính quyền.
ROLE_CREATOR = "NGUOI_TAO"


def validate_work_file(file):
    """Kiểm tra định dạng và dung lượng file tải lên."""
    file_name = Path(file.name).name
    extension = Path(file_name).suffix.lower().lstrip(".")

    if extension not in ALLOWED_FILE_EXTENSIONS:
        raise ValidationError(
            f'File "{file_name}" không đúng định dạng. '
            "Hãy chọn file PDF, DOC/DOCX, JPG, JPEG hoặc PNG."
        )

    if file.size >= MAX_FILE_SIZE:
        size_mb = file.size / (1024 * 1024)
        raise ValidationError(
            f'File "{file_name}" có dung lượng {size_mb:.1f} MB, vượt giới hạn. '
            "Hãy chọn file dưới 20 MB hoặc nén file trước khi tải lên."
        )

    # Chỉ kiểm tra nội dung ảnh với file mới tải lên (file đã lưu thì đã được kiểm tra trước đó).
    is_new_upload = not getattr(file, "_committed", False)
    if extension in IMAGE_FILE_EXTENSIONS and is_new_upload:
        from PIL import Image

        try:
            file.seek(0)
            Image.open(file).verify()
        except Exception:
            raise ValidationError(
                f'File "{file_name}" có đuôi .{extension} nhưng không phải ảnh hợp lệ. '
                "Hãy mở thử file trên máy, lưu lại dưới dạng JPG hoặc PNG rồi tải lên lại."
            )
        finally:
            file.seek(0)


def attachment_upload_to(instance, filename):
    """
    Lưu vào DOCUMENT_STORAGE_ROOT/cong-viec/YYYY/MM/DD/<uuid>.<ext>.
    Tên file trên đĩa là chuỗi ngẫu nhiên để tránh trùng tên và lỗi ký tự tiếng Việt;
    tên gốc được giữ ở cột original_name.
    """
    return build_dated_path("cong-viec", filename)


def delete_stored_files_on_commit(file_names):
    """
    Xóa file vật lý sau khi transaction commit thành công.
    Django không tự xóa file khi xóa bản ghi; nếu transaction lỗi thì file vẫn được giữ lại.
    """
    names = [name for name in file_names if name]
    if not names:
        return

    def _delete():
        storage = get_document_storage()
        for name in names:
            try:
                storage.delete(name)
            except OSError:
                # File đã mất trên đĩa thì bỏ qua, không làm hỏng thao tác xóa dữ liệu.
                pass

    transaction.on_commit(_delete)


# ==========================================================================
# LỰA CHỌN (CHOICES)
# ==========================================================================

class TaskStatus(models.TextChoices):
    """Trạng thái công việc — giá trị TÍNH TOÁN, không lưu trong DB."""

    CHO_XU_LY = "CHO_XU_LY", "Chờ xử lý"
    DANG_XU_LY = "DANG_XU_LY", "Đang xử lý"
    CHO_DUYET = "CHO_DUYET", "Chờ duyệt"
    HOAN_THANH = "HOAN_THANH", "Hoàn thành"
    CHUA_HOAN_THANH = "CHUA_HOAN_THANH", "Chưa hoàn thành"
    QUA_HAN = "QUA_HAN", "Quá hạn"


FROZEN_STATUSES = {TaskStatus.CHUA_HOAN_THANH, TaskStatus.QUA_HAN}


class TaskRuleError(Exception):
    """
    Thao tác bị chặn theo quy tắc nghiệp vụ.
    - kind = "forbidden": sai vai trò (view trả 403)
    - kind = "invalid_state": đúng vai trò nhưng trạng thái không cho phép (view trả 400)
    Thông báo luôn nêu lý do và cách khắc phục.
    """

    FORBIDDEN = "forbidden"
    INVALID_STATE = "invalid_state"

    def __init__(self, message, kind=FORBIDDEN):
        super().__init__(message)
        self.message = message
        self.kind = kind


FROZEN_MESSAGE = (
    "Công việc đã hết hạn khi chưa nộp bằng chứng nên đã bị khóa, không thể {action}. "
    "Nếu vẫn cần thực hiện, hãy đề nghị người tạo giao công việc mới."
)


class ParticipantRole(models.TextChoices):
    CHU_TRI = "CHU_TRI", "Chủ trì giải quyết công việc"
    CHI_DAO = "CHI_DAO", "Chỉ đạo - Theo dõi tiến độ xử lý công việc"
    THAM_GIA = "THAM_GIA", "Cán bộ tham gia giải quyết công việc"


# Người được duyệt / hủy duyệt: người tạo, chủ trì, chỉ đạo.
APPROVER_ROLES = {ROLE_CREATOR, ParticipantRole.CHU_TRI, ParticipantRole.CHI_DAO}


class AttachmentKind(models.TextChoices):
    GIAO_VIEC = "GIAO_VIEC", "Đính kèm lúc giao việc"
    BANG_CHUNG = "BANG_CHUNG", "Bằng chứng hoàn thành"


class DocumentKind(models.TextChoices):
    """
    Loại văn bản của nhóm 2 mà công việc phát sinh từ đó (enum document_kind).
    Chỉ còn văn bản đến và văn bản đi — GVHD đã bỏ hẳn văn bản mật (issue #83).
    """

    VAN_BAN_DEN = "vanbanden", "Văn bản đến"
    VAN_BAN_DI = "vanbandi", "Văn bản đi"


# Mã quyền do nhóm 7 cấp; gom một chỗ để đổi nhanh khi hệ thống phân quyền xong.
PERM_VIEW_ALL_TASK = "view_all_congviec"
PERM_VIEW_DEPT_TASK = "view_dept_congviec"


def user_has_task_permission(user, permission_code):
    """
    Kiểm tra người dùng có mã quyền của module Công việc hay không.
    TODO: Noi vao he thong phan quyen cua nhom 7 khi san sang.
    Hiện tạm dùng permission có sẵn của Django, chấp nhận cả dạng có và không có tiền tố app.
    """
    if user is None or not user.is_authenticated:
        return False
    return user.has_perm(permission_code) or user.has_perm(f"work.{permission_code}")


def user_don_vi_id(user):
    """
    Đơn vị của người dùng (accounts_employee.don_vi_id). Mỗi người thuộc đúng 1 đơn vị.
    TODO: Bo getattr khi AUTH_USER_MODEL doi sang accounts.Employee cua nhom 7.
    """
    return getattr(user, "don_vi_id", None)


# ==========================================================================
# QUERYSET
# ==========================================================================

class TaskQuerySet(models.QuerySet):
    def with_status(self, today=None):
        """
        Gắn cột `status` tính ngay trong DB để lọc theo trạng thái và phân trang không bị sai.
        Thứ tự When quyết định độ ưu tiên — KHÔNG đổi thứ tự nếu chưa hỏi trưởng nhóm.
        """
        today = today or timezone.localdate()
        evidences = TaskAttachment.objects.filter(
            task=OuterRef("pk"),
            kind=AttachmentKind.BANG_CHUNG,
            is_deleted=False,
        )
        return self.annotate(has_evidence=Exists(evidences)).annotate(
            status=Case(
                When(approved_at__isnull=False, then=Value(TaskStatus.HOAN_THANH)),
                # Đã nộp bằng chứng thì không bị đóng băng, kể cả khi quá hạn.
                When(has_evidence=True, then=Value(TaskStatus.CHO_DUYET)),
                When(
                    due_date__lt=today,
                    first_opened_at__isnull=False,
                    then=Value(TaskStatus.CHUA_HOAN_THANH),
                ),
                When(due_date__lt=today, then=Value(TaskStatus.QUA_HAN)),
                When(first_opened_at__isnull=False, then=Value(TaskStatus.DANG_XU_LY)),
                default=Value(TaskStatus.CHO_XU_LY),
                output_field=CharField(),
            )
        )

    def with_priority_for(self, user):
        """
        Gắn cột `priority_bucket` (1 = cao nhất) để đưa việc đang CHỜ CHÍNH USER HÀNH ĐỘNG
        lên đầu danh sách. CHỈ SẮP XẾP, không lọc, không ẩn việc nào.

        YÊU CẦU: gọi SAU .with_status() vì cần cột annotate `status`.

        Bậc ưu tiên (cao → thấp):
          1. User là chủ trì/tham gia, việc còn phải làm (Chờ xử lý hoặc Đang xử lý).
          2. User là chỉ đạo/chủ trì, việc đang Chờ duyệt (chờ chính user duyệt minh chứng).
          3. User là chủ trì/tham gia, việc đã trễ (Quá hạn hoặc Chưa hoàn thành).
          4. Các việc còn lại user có quyền xem.
        Trong cùng một bậc: sắp theo due_date tăng dần (do view order_by đảm nhận).
        """
        if user is None or not user.is_authenticated:
            return self.annotate(priority_bucket=Value(4, output_field=IntegerField()))

        def role_exists(role):
            return Exists(
                TaskParticipant.objects.filter(task=OuterRef("pk"), user=user, role=role)
            )

        return self.annotate(
            _is_host=role_exists(ParticipantRole.CHU_TRI),
            _is_part=role_exists(ParticipantRole.THAM_GIA),
            _is_dir=role_exists(ParticipantRole.CHI_DAO),
        ).annotate(
            priority_bucket=Case(
                When(
                    (Q(_is_host=True) | Q(_is_part=True))
                    & Q(status__in=[TaskStatus.CHO_XU_LY, TaskStatus.DANG_XU_LY]),
                    then=Value(1),
                ),
                When(
                    (Q(_is_dir=True) | Q(_is_host=True)) & Q(status=TaskStatus.CHO_DUYET),
                    then=Value(2),
                ),
                When(
                    (Q(_is_host=True) | Q(_is_part=True))
                    & Q(status__in=[TaskStatus.QUA_HAN, TaskStatus.CHUA_HOAN_THANH]),
                    then=Value(3),
                ),
                default=Value(4),
                output_field=IntegerField(),
            )
        )

    def visible_to(self, user):
        """
        Quyền xem 3 lớp:
        1. Người liên quan: người tạo, hoặc có tên trong task_participant.
        2. Quyền `view_all_congviec`: xem toàn bộ công việc.
        3. Quyền `view_dept_congviec`: xem công việc gắn với đơn vị của chính mình.

        Công việc đang ẩn (hien_thi = false) chỉ người tạo, quản trị viên và người có
        quyền xem toàn hệ thống mới thấy.
        """
        if user is None or not user.is_authenticated:
            return self.none()
        if user.is_superuser or user_has_task_permission(user, PERM_VIEW_ALL_TASK):
            return self

        is_participant = Exists(
            TaskParticipant.objects.filter(task=OuterRef("pk"), user=user)
        )
        condition = Q(created_by=user) | Q(is_public=True, is_participant=True)

        don_vi_id = user_don_vi_id(user)
        if don_vi_id and user_has_task_permission(user, PERM_VIEW_DEPT_TASK):
            in_my_don_vi = Exists(
                TaskDonVi.objects.filter(task=OuterRef("pk"), don_vi_id=don_vi_id)
            )
            condition |= Q(is_public=True) & Q(in_my_don_vi=True)
            return self.alias(is_participant=is_participant, in_my_don_vi=in_my_don_vi).filter(condition)

        return self.alias(is_participant=is_participant).filter(condition)


# ==========================================================================
# MODEL
# ==========================================================================

class Task(models.Model):
    """
    Bảng `task_congviec` theo CSDL PM chốt. Tên trường trong Python giữ tiếng Anh cho khớp
    API camelCase và code frontend; tên cột trong DB dùng đúng tên PM (db_column).
    """

    title = models.TextField("Nội dung công việc", db_column="noi_dung")
    created_date = models.DateField("Ngày tạo", default=timezone.localdate, db_column="ngay_tao_cv")
    due_date = models.DateField("Ngày xử lý", db_column="ngay_xu_ly")
    requirement = models.TextField("Yêu cầu xử lý", db_column="yeu_cau_xu_ly")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Người tạo",
        on_delete=models.PROTECT,
        related_name="work_created_tasks",
        db_column="nguoi_tao_id",
    )
    is_public = models.BooleanField("Trạng thái hiển thị", default=True, db_column="hien_thi")

    # Văn bản liên quan (công việc phát sinh từ Văn bản đến / đi của nhóm 2).
    # TODO: doi document_id thanh FK that khi nhom 2 chot ten model van ban.
    # TODO(issue #83): khi hien thi hoac kiem tra van ban lien quan, dung ham dung chung
    # van_ban_xem_duoc(user, loai) cua nhom 2 (ham nay chua co tren nhanh).
    document_type = models.CharField(
        "Loại văn bản liên quan",
        max_length=20,
        choices=DocumentKind.choices,
        null=True,
        blank=True,
    )
    document_id = models.BigIntegerField("Id văn bản liên quan", null=True, blank=True)

    # Mốc hệ thống phục vụ tính trạng thái (đầy đủ giờ - phút - giây).
    first_opened_at = models.DateTimeField(
        "Thời điểm mở lần đầu", null=True, blank=True, db_column="opened_at"
    )
    first_opened_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Người mở lần đầu",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        db_column="opened_by",
    )
    approved_at = models.DateTimeField("Thời điểm duyệt", null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Người duyệt",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        db_column="approved_by",
    )

    created_at = models.DateTimeField("Tạo lúc", auto_now_add=True)
    updated_at = models.DateTimeField("Cập nhật lúc", auto_now=True)

    objects = TaskQuerySet.as_manager()

    class Meta:
        db_table = "task_congviec"
        verbose_name = "Công việc"
        verbose_name_plural = "Công việc"
        ordering = ["-created_date", "-created_at"]
        indexes = [
            # Khớp CREATE INDEX idx_task_congviec_document ON task_congviec (document_type, document_id)
            models.Index(fields=["document_type", "document_id"], name="idx_task_congviec_document"),
        ]
        # Permission: 7 ma DDL seed (view_congviec, add_congviec, change_congviec, delete_congviec,
        # approve_congviec, assign_congviec, comment_congviec) do nhom 7 cap. KHONG khai bao
        # Meta.permissions o day vi authorization/apps.py tren staging da tat tin hieu tu sinh.
        constraints = [
            models.CheckConstraint(
                condition=Q(due_date__gte=F("created_date")),
                name="chk_task_due_after_created",
                violation_error_message=(
                    "Ngày xử lý đang trước ngày tạo. "
                    "Hãy chọn ngày xử lý bằng hoặc sau ngày tạo."
                ),
            ),
            models.CheckConstraint(
                condition=(
                    Q(document_type__isnull=True, document_id__isnull=True)
                    | Q(document_type__isnull=False, document_id__isnull=False)
                ),
                name="chk_task_document",
                violation_error_message=(
                    "Văn bản liên quan phải có đủ cả loại văn bản và mã văn bản. "
                    "Hãy chọn lại văn bản, hoặc bỏ trống cả hai nếu công việc không phát sinh từ văn bản."
                ),
            ),
        ]

    def __str__(self):
        return self.title[:80]

    def roles_of(self, user):
        """Tập vai trò của user trong công việc: NGUOI_TAO, CHU_TRI, CHI_DAO, THAM_GIA."""
        roles = set()
        if user is None or not user.is_authenticated:
            return roles
        if self.created_by_id == user.id:
            roles.add(ROLE_CREATOR)
        # Dùng .all() để tận dụng prefetch_related khi có.
        for participant in self.participants.all():
            if participant.user_id == user.id:
                roles.add(participant.role)
        return roles

    def get_status(self):
        """Trạng thái đã annotate bởi with_status(); nếu chưa có thì truy vấn lại DB."""
        status = getattr(self, "status", None)
        if status is None:
            status = Task.objects.with_status().values_list("status", flat=True).get(pk=self.pk)
            self.status = status
        return status

    def evidence_files(self):
        # Dùng .all() rồi lọc bằng Python để tận dụng prefetch_related khi có.
        return [
            item
            for item in self.attachments.all()
            if item.kind == AttachmentKind.BANG_CHUNG and not item.is_deleted
        ]

    def is_overdue(self):
        return self.due_date < timezone.localdate()

    # ----------------------------------------------------------------------
    # QUY TẮC QUYỀN
    # check_*: ném TaskRuleError kèm thông báo có hướng khắc phục.
    # can_*:   trả True/False, dùng để sinh cờ `permissions` cho frontend.
    # View và serializer CHỈ dùng các hàm này, không tự viết lại điều kiện.
    # ----------------------------------------------------------------------

    def check_edit(self, user):
        roles = self.roles_of(user)
        if not roles & {ROLE_CREATOR, ParticipantRole.CHU_TRI}:
            raise TaskRuleError(
                "Chỉ người tạo hoặc người chủ trì mới được sửa công việc này. "
                "Nếu cần thay đổi, hãy liên hệ người tạo hoặc người chủ trì."
            )
        status = self.get_status()
        if status == TaskStatus.CHO_DUYET:
            raise TaskRuleError(
                "Công việc đang chờ duyệt nên không thể sửa. "
                "Nếu thông tin sai nghiêm trọng, hãy xóa công việc và tạo lại.",
                TaskRuleError.INVALID_STATE,
            )
        if status == TaskStatus.HOAN_THANH:
            raise TaskRuleError(
                "Công việc đã hoàn thành nên không thể sửa. "
                "Nếu thông tin sai nghiêm trọng, hãy xóa công việc và tạo lại.",
                TaskRuleError.INVALID_STATE,
            )
        if status in FROZEN_STATUSES:
            raise TaskRuleError(FROZEN_MESSAGE.format(action="sửa"), TaskRuleError.INVALID_STATE)

    def check_delete(self, user):
        if not self.roles_of(user) & {ROLE_CREATOR, ParticipantRole.CHU_TRI}:
            raise TaskRuleError(
                "Chỉ người tạo hoặc người chủ trì mới được xóa công việc này. "
                "Nếu cần xóa, hãy liên hệ người tạo hoặc người chủ trì."
            )

    def can_mark_opened(self, user):
        """Chỉ chủ trì / chỉ đạo / tham gia mở lần đầu, và chỉ khi chưa quá hạn, mới tính là 'đã mở'."""
        roles = self.roles_of(user)
        return (
            bool(roles & {ParticipantRole.CHU_TRI, ParticipantRole.CHI_DAO, ParticipantRole.THAM_GIA})
            and self.first_opened_at is None
            and not self.is_overdue()
        )

    def check_submit_evidence(self, user):
        if not self.roles_of(user) & {ParticipantRole.CHU_TRI, ParticipantRole.THAM_GIA}:
            raise TaskRuleError(
                "Chỉ người chủ trì hoặc cán bộ tham gia mới được đính kèm file kết quả vào ý kiến. "
                "Hãy bỏ file và gửi ý kiến dạng chữ, hoặc báo người chủ trì nộp kết quả."
            )
        status = self.get_status()
        if status == TaskStatus.HOAN_THANH:
            raise TaskRuleError(
                "Công việc đã được duyệt hoàn thành nên không thể đính kèm thêm file kết quả. "
                "Hãy gửi ý kiến không kèm file, hoặc đề nghị người có quyền duyệt hủy duyệt trước.",
                TaskRuleError.INVALID_STATE,
            )
        if status in FROZEN_STATUSES:
            raise TaskRuleError(
                FROZEN_MESSAGE.format(action="nộp kết quả"), TaskRuleError.INVALID_STATE
            )

    def check_delete_evidence(self, user, attachment):
        if attachment.task_id != self.pk or attachment.kind != AttachmentKind.BANG_CHUNG:
            raise TaskRuleError(
                "File này không phải file bằng chứng của công việc. "
                "File đính kèm lúc giao việc chỉ xóa được trong màn hình sửa công việc.",
                TaskRuleError.INVALID_STATE,
            )
        if attachment.is_deleted:
            raise TaskRuleError(
                "File này đã được xóa trước đó. Hãy tải lại trang để xem danh sách mới nhất.",
                TaskRuleError.INVALID_STATE,
            )
        if user is None or attachment.uploaded_by_id != user.id:
            raise TaskRuleError(
                "Bạn chỉ được xóa file bằng chứng do chính mình tải lên. "
                "Nếu file này sai, hãy báo người đã tải file để họ xóa."
            )
        if self.get_status() == TaskStatus.HOAN_THANH:
            raise TaskRuleError(
                "Công việc đã được duyệt nên không thể xóa file bằng chứng. "
                "Nếu cần thay file, hãy đề nghị người có quyền duyệt (người tạo, chủ trì hoặc chỉ đạo) hủy duyệt trước.",
                TaskRuleError.INVALID_STATE,
            )
        if self.is_overdue() and len(self.evidence_files()) <= 1:
            raise TaskRuleError(
                "Công việc đã quá hạn, không thể xóa file bằng chứng cuối cùng. "
                "Hãy nộp file mới trước rồi xóa file cũ sau.",
                TaskRuleError.INVALID_STATE,
            )

    def check_approve(self, user):
        if not self.roles_of(user) & APPROVER_ROLES:
            raise TaskRuleError(
                "Chỉ người tạo, người chủ trì hoặc người chỉ đạo mới được duyệt công việc. "
                "Hãy báo một trong những người này vào duyệt."
            )
        status = self.get_status()
        if status == TaskStatus.HOAN_THANH:
            raise TaskRuleError(
                "Công việc đã được duyệt trước đó. Hãy tải lại trang để xem trạng thái mới nhất.",
                TaskRuleError.INVALID_STATE,
            )
        if status in FROZEN_STATUSES:
            raise TaskRuleError(FROZEN_MESSAGE.format(action="duyệt"), TaskRuleError.INVALID_STATE)
        if status != TaskStatus.CHO_DUYET:
            raise TaskRuleError(
                "Công việc chưa có file kết quả nào nên chưa thể duyệt. "
                "Hãy chờ người chủ trì hoặc cán bộ tham gia gửi ý kiến kèm file kết quả.",
                TaskRuleError.INVALID_STATE,
            )

    def check_unapprove(self, user):
        if not self.roles_of(user) & APPROVER_ROLES:
            raise TaskRuleError(
                "Chỉ người tạo, người chủ trì hoặc người chỉ đạo mới được hủy duyệt công việc. "
                "Hãy báo một trong những người này nếu cần thu hồi kết quả duyệt."
            )
        if self.get_status() != TaskStatus.HOAN_THANH:
            raise TaskRuleError(
                "Công việc chưa được duyệt nên không có gì để hủy duyệt. "
                "Hãy tải lại trang để xem trạng thái mới nhất.",
                TaskRuleError.INVALID_STATE,
            )

    def check_comment(self, user):
        if not self.roles_of(user):
            raise TaskRuleError(
                "Chỉ người liên quan đến công việc mới được ghi ý kiến. "
                "Nếu bạn cần góp ý, hãy đề nghị người tạo thêm bạn vào công việc."
            )
        if self.get_status() in FROZEN_STATUSES:
            raise TaskRuleError(FROZEN_MESSAGE.format(action="ghi thêm ý kiến"), TaskRuleError.INVALID_STATE)

    def _passes(self, check, *args):
        try:
            check(*args)
        except TaskRuleError:
            return False
        return True

    def can_edit(self, user):
        return self._passes(self.check_edit, user)

    def can_delete(self, user):
        return self._passes(self.check_delete, user)

    def can_submit_evidence(self, user):
        return self._passes(self.check_submit_evidence, user)

    def can_delete_evidence(self, user, attachment):
        return self._passes(self.check_delete_evidence, user, attachment)

    def can_approve(self, user):
        return self._passes(self.check_approve, user)

    def can_unapprove(self, user):
        return self._passes(self.check_unapprove, user)

    def can_comment(self, user):
        return self._passes(self.check_comment, user)


class TaskParticipant(models.Model):
    task = models.ForeignKey(
        Task,
        verbose_name="Công việc",
        on_delete=models.CASCADE,
        related_name="participants",
        db_column="cong_viec",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Cán bộ",
        on_delete=models.PROTECT,
        related_name="work_participations",
        db_column="can_bo",
    )
    role = models.CharField("Vai trò", max_length=20, choices=ParticipantRole.choices, db_column="vai_tro")

    class Meta:
        db_table = "task_participant"
        verbose_name = "Người liên quan"
        verbose_name_plural = "Người liên quan"
        constraints = [
            models.UniqueConstraint(
                fields=["task", "user"],
                name="uq_task_participant",
                violation_error_message=(
                    "Một cán bộ chỉ được giữ một vai trò trong cùng công việc. "
                    "Hãy bỏ cán bộ này khỏi các vai trò còn lại."
                ),
            ),
            models.UniqueConstraint(
                fields=["task"],
                condition=Q(role=ParticipantRole.CHU_TRI),
                name="uq_task_participant_one_host",
                violation_error_message=(
                    "Mỗi công việc chỉ có một người chủ trì. "
                    "Hãy giữ lại một người chủ trì và chuyển những người còn lại sang vai trò khác."
                ),
            ),
        ]

    def __str__(self):
        return f"{self.get_role_display()}: {self.user}"


class TaskComment(models.Model):
    task = models.ForeignKey(
        Task,
        verbose_name="Công việc",
        on_delete=models.CASCADE,
        related_name="comments",
        db_column="cong_viec",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Người ghi",
        on_delete=models.PROTECT,
        related_name="+",
        db_column="nguoi_ghi",
    )
    content = models.TextField("Nội dung ý kiến", db_column="noi_dung")
    created_at = models.DateTimeField("Ghi lúc", auto_now_add=True)

    class Meta:
        db_table = "task_comment"
        verbose_name = "Ý kiến"
        verbose_name_plural = "Ý kiến"
        ordering = ["created_at", "id"]
        indexes = [
            # Khớp CREATE INDEX idx_comment_congviec ON task_comment (cong_viec)
            models.Index(fields=["task"], name="idx_comment_congviec"),
        ]

    def __str__(self):
        return self.content[:80]


class TaskDonVi(models.Model):
    """
    Bảng `task_congviec_donvi`: một công việc gắn được nhiều phòng/ban.
    Liên kết trực tiếp với organizations.DonVi theo DDL.
    """

    task = models.ForeignKey(
        Task,
        verbose_name="Công việc",
        on_delete=models.CASCADE,
        related_name="don_vi_links",
        db_column="cong_viec",
    )
    don_vi = models.ForeignKey(
        "organizations.DonVi",
        verbose_name="Đơn vị",
        on_delete=models.CASCADE,
        related_name="task_links",
        db_column="don_vi",
        db_index=False,
    )
    created_at = models.DateTimeField("Gắn lúc", auto_now_add=True)

    class Meta:
        db_table = "task_congviec_donvi"
        verbose_name = "Phòng ban của công việc"
        verbose_name_plural = "Phòng ban của công việc"
        indexes = [
            # Khớp 2 index DDL: idx_task_donvi_congviec (cong_viec), idx_task_donvi_donvi (don_vi)
            models.Index(fields=["task"], name="idx_task_donvi_congviec"),
            models.Index(fields=["don_vi"], name="idx_task_donvi_donvi"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["task", "don_vi"],
                name="uq_task_congviec_donvi",
                violation_error_message=(
                    "Phòng ban này đã được gắn cho công việc. Hãy bỏ bớt phòng ban trùng."
                ),
            ),
        ]

    def __str__(self):
        return f"Công việc #{self.task_id} - đơn vị #{self.don_vi_id}"


class TaskAttachment(models.Model):
    """
    Bảng `task_attachment` bản 9 cột PM chốt: name, path, cong_viec_id, y_kien_id, loai,
    is_deleted, created_time, created_user_id (cộng khóa chính id).
    Dung lượng file không lưu cột riêng, đọc trực tiếp từ kho lưu trữ khi cần.
    """

    task = models.ForeignKey(
        Task,
        verbose_name="Công việc",
        on_delete=models.CASCADE,
        related_name="attachments",
        db_column="cong_viec_id",
    )
    kind = models.CharField("Loại file", max_length=20, choices=AttachmentKind.choices, db_column="loai")
    # File bằng chứng luôn nằm trong một ý kiến: nộp kết quả = ghi ý kiến kèm file.
    comment = models.ForeignKey(
        TaskComment,
        verbose_name="Ý kiến chứa file",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="attachments",
        db_column="y_kien_id",
    )
    file = models.FileField(
        "File",
        upload_to=attachment_upload_to,
        storage=get_document_storage,
        max_length=500,
        validators=[validate_work_file],
        db_column="path",
    )
    original_name = models.CharField("Tên file gốc", max_length=255, blank=True, db_column="name")
    is_deleted = models.BooleanField("Đã xóa", default=False)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Người tải lên",
        on_delete=models.PROTECT,
        related_name="+",
        db_column="nguoi_tao_id",
    )
    uploaded_at = models.DateTimeField("Tải lên lúc", auto_now_add=True, db_column="created_at")

    class Meta:
        db_table = "task_attachment"
        verbose_name = "File đính kèm"
        verbose_name_plural = "File đính kèm"
        ordering = ["uploaded_at", "id"]
        indexes = [
            # Khớp CREATE INDEX idx_task_attachment_congviec ON task_attachment (cong_viec_id)
            models.Index(fields=["task"], name="idx_task_attachment_congviec"),
            # idx_task_attachment_deleted là index thường trong DDL (không WHERE), không dùng partial
            models.Index(fields=["is_deleted"], name="idx_task_attachment_deleted"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(kind=AttachmentKind.GIAO_VIEC, comment__isnull=True)
                    | Q(kind=AttachmentKind.BANG_CHUNG, comment__isnull=False)
                ),
                name="chk_task_attachment_evidence",
                violation_error_message=(
                    "File bằng chứng phải nằm trong một ý kiến, còn file giao việc thì không. "
                    "Hãy nộp kết quả bằng cách ghi ý kiến kèm file trên trang chi tiết công việc."
                ),
            ),
        ]

    def __str__(self):
        return self.original_name or Path(self.file.name).name

    def save(self, *args, **kwargs):
        # Ghi lại tên gốc TRƯỚC khi upload_to đổi tên file trên đĩa.
        if self.file and not self.file._committed and not self.original_name:
            self.original_name = Path(self.file.name).name[:255]
        super().save(*args, **kwargs)

    @property
    def size(self):
        """Dung lượng đọc từ kho lưu trữ (CSDL không có cột dung lượng)."""
        try:
            return self.file.size
        except (OSError, ValueError):
            return 0
