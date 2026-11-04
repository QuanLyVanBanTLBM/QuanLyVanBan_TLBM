import datetime

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Exists, F, OuterRef, Prefetch, Q
from django.http import FileResponse, Http404
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import (
    NotAuthenticated,
    NotFound,
    PermissionDenied,
    ValidationError,
)
from rest_framework.filters import OrderingFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from authorization.permissions import require_permission
from work.models import (
    AttachmentKind,
    Task,
    TaskAttachment,
    TaskDonVi,
    TaskComment,
    TaskParticipant,
    TaskRuleError,
    TaskStatus,
    delete_stored_files_on_commit,
)
from work.serializers import (
    CommentSerializer,
    EmployeeSerializer,
    LatestTaskSerializer,
    MeSerializer,
    TaskDetailSerializer,
    TaskListSerializer,
    TaskWriteSerializer,
)
from work.services.email import send_new_task_mail

User = get_user_model()

TASK_NOT_FOUND_MESSAGE = (
    "Không tìm thấy công việc, hoặc bạn không có quyền xem công việc này. "
    "Hãy quay lại danh sách và tải lại trang."
)


# ==========================================================================
# ===== KHU VỰC: Phân trang, lớp nền =====
# ==========================================================================

class TaskPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "pageSize"
    max_page_size = 100
    invalid_page_message = (
        "Trang {page_number} không tồn tại. Hãy quay về trang 1 hoặc chọn trang nhỏ hơn."
    )

    def get_paginated_response(self, data):
        return Response({
            "count": self.page.paginator.count,
            "page": self.page.number,
            "pageSize": self.page.paginator.per_page,
            "totalPages": self.page.paginator.num_pages,
            "results": data,
        })


class WorkApiMixin:
    """Cấu hình chung cho mọi API của module Công việc."""

    # Dùng đúng cơ chế đăng nhập chung của dự án: JWT do `accounts/login/` cấp.
    # Không còn lớp xác thực giả lập: request không có token thì trả 401 (issue #65-1).
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def permission_denied(self, request, message=None, code=None):
        if request.authenticators and not request.successful_authenticator:
            raise NotAuthenticated(
                "Bạn chưa đăng nhập. Hãy đăng nhập để lấy token rồi thử lại."
            )
        super().permission_denied(request, message=message, code=code)


def raise_rule_error(error):
    """Đổi TaskRuleError của models.py thành lỗi HTTP: sai vai trò → 403, sai trạng thái → 400."""
    if error.kind == TaskRuleError.INVALID_STATE:
        raise ValidationError({"detail": error.message})
    raise PermissionDenied(error.message)


def parse_date_param(request, name, label):
    raw = request.query_params.get(name, "").strip()
    if not raw:
        return None
    try:
        return datetime.date.fromisoformat(raw)
    except ValueError:
        raise ValidationError({name: [f"{label} không hợp lệ. Hãy chọn lại {label.lower()} trên lịch."]})


class TaskViewSet(
    WorkApiMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    /api/work/tasks/ — công việc.
    Quyền xem được lọc ở get_queryset (không thấy → 404).
    Quyền thao tác kiểm tra bằng các hàm check_* trong models.py.
    """

    http_method_names = ["get", "post", "patch", "delete", "head", "options"]
    # JSON đứng đầu để trang API trên trình duyệt điền sẵn form; upload file vẫn dùng multipart.
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    pagination_class = TaskPagination
    lookup_value_regex = r"\d+"

    # Khi request có ?ordering=... thì OrderingFilter override thứ tự mặc định ở get_queryset
    # (lựa chọn sort cột của người dùng thắng). Không đặt thuộc tính `ordering` mặc định ở đây
    # để khi KHÔNG có param thì vẫn giữ nguyên thứ tự 3 tầng tùy chỉnh. "status" là cột annotate.
    filter_backends = [OrderingFilter]
    ordering_fields = ["due_date", "created_date", "status", "title"]

    def get_permissions(self):
        permissions = super().get_permissions()
        if self.action == "create":
            permissions.append(require_permission("add_congviec")())
        return permissions

    def get_queryset(self):
        participants = Prefetch(
            "participants",
            # Kèm chuc_vu + don_vi để serializer hiện Chức vụ - Phòng ban mà không gây N+1.
            queryset=TaskParticipant.objects.select_related(
                "user", "user__chuc_vu", "user__don_vi"
            ).order_by("id"),
        )
        queryset = (
            Task.objects.visible_to(self.request.user)
            .with_status()
            .select_related(
                "created_by",
                "created_by__chuc_vu",
                "created_by__don_vi",
                "first_opened_by",
                "first_opened_by__chuc_vu",
                "first_opened_by__don_vi",
                "approved_by",
                "approved_by__chuc_vu",
                "approved_by__don_vi",
            )
            .prefetch_related(participants)
            # Thứ tự mặc định ưu tiên theo CHÍNH NGƯỜI ĐANG XEM (chỉ sắp xếp, không lọc):
            # 1. priority_bucket: việc đang chờ user hành động lên đầu (xem with_priority_for).
            # 2. Trong mỗi bậc: hạn xử lý gần nhất lên trước (asc).
            # 3. Việc không có hạn xuống cuối (nulls_last) — hiện due_date NOT NULL nên là
            #    phòng thủ, chỉ có tác dụng nếu sau này cho phép việc không hạn.
            # Tie-break cuối cùng là -id (luôn unique) để phân trang ổn định tuyệt đối,
            # không để 2 record cùng due_date + cùng timestamp nhảy trang.
            # Khi request có ?ordering=... thì OrderingFilter override thứ tự này.
            .with_priority_for(self.request.user)
            .order_by("priority_bucket", F("due_date").asc(nulls_last=True), "-created_at", "-id")
        )
        if self.action != "list":
            attachments = Prefetch(
                "attachments",
                queryset=TaskAttachment.objects.filter(is_deleted=False)
                .select_related("uploaded_by")
                .order_by("uploaded_at", "id"),
            )
            queryset = queryset.prefetch_related(attachments, "don_vi_links")
        return queryset

    def get_object(self):
        try:
            return super().get_object()
        except Http404:
            raise NotFound(TASK_NOT_FOUND_MESSAGE)

    def get_serializer_class(self):
        if self.action == "list":
            return TaskListSerializer
        if self.action in ("create", "partial_update"):
            return TaskWriteSerializer
        return TaskDetailSerializer

    def detail_response(self, pk, http_status=status.HTTP_200_OK):
        """Đọc lại công việc từ DB (trạng thái mới nhất) rồi trả về dạng chi tiết."""
        task = self.get_queryset().get(pk=pk)
        serializer = TaskDetailSerializer(task, context=self.get_serializer_context())
        return Response(serializer.data, status=http_status)

    # ----------------------------------------------------------------------
    # API trang chủ (nhóm 1): GET /api/work/tasks/latest/?limit=5
    # ----------------------------------------------------------------------
    @action(detail=False, methods=["get"])
    def latest(self, request):
        raw_limit = request.query_params.get("limit", "5")
        if not raw_limit.isdigit() or not 1 <= int(raw_limit) <= 20:
            raise ValidationError({"limit": ["Số công việc cần lấy phải từ 1 đến 20. Hãy gửi lại limit trong khoảng này."]})
        tasks = (
            Task.objects.visible_to(request.user)
            .with_status()
            .order_by("-created_date", "-created_at", "-id")[: int(raw_limit)]
        )
        return Response(LatestTaskSerializer(tasks, many=True).data)

    # ======================================================================
    # ===== KHU VỰC: Danh sách, chi tiết, thêm / sửa / xóa =====
    # ======================================================================

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        if self.action != "list":
            return queryset

        params = self.request.query_params

        search = params.get("search", "").strip()
        if search:
            queryset = queryset.filter(title__icontains=search)

        status_value = params.get("status", "").strip()
        if status_value:
            if status_value not in TaskStatus.values:
                raise ValidationError({
                    "status": [f"Tình trạng \"{status_value}\" không hợp lệ. Hãy chọn một tình trạng trong danh sách."]
                })
            # Lọc trên cột annotate → điều kiện nằm trong câu SQL, phân trang đếm đúng.
            queryset = queryset.filter(status=status_value)

        created_from = parse_date_param(self.request, "createdFrom", "Từ ngày tạo")
        created_to = parse_date_param(self.request, "createdTo", "Đến ngày tạo")
        if created_from and created_to and created_from > created_to:
            raise ValidationError({
                "createdFrom": ["Từ ngày tạo đang sau đến ngày tạo. Hãy chọn lại khoảng ngày tạo."]
            })
        if created_from:
            queryset = queryset.filter(created_date__gte=created_from)
        if created_to:
            queryset = queryset.filter(created_date__lte=created_to)

        return queryset

    def create(self, request, *args, **kwargs):
        # IsAuthenticated chặn ẩn danh; RBAC chặn tài khoản không có add_congviec.
        serializer = TaskWriteSerializer(data=request.data, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        task = serializer.save()
        # Chỉ gửi khi dữ liệu đã lưu chắc chắn; gửi lỗi cũng không làm hỏng việc tạo công việc.
        transaction.on_commit(lambda: send_new_task_mail(task.pk))
        return self.detail_response(task.pk, status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        task = self.get_object()
        try:
            task.check_edit(request.user)
        except TaskRuleError as error:
            raise_rule_error(error)

        serializer = TaskWriteSerializer(
            task,
            data=request.data,
            partial=True,
            context=self.get_serializer_context(),
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return self.detail_response(task.pk)

    def destroy(self, request, *args, **kwargs):
        task = self.get_object()
        try:
            task.check_delete(request.user)
        except TaskRuleError as error:
            raise_rule_error(error)

        with transaction.atomic():
            file_names = list(task.attachments.values_list("file", flat=True))
            task.delete()
            delete_stored_files_on_commit(file_names)
        return Response(status=status.HTTP_204_NO_CONTENT)

    # ======================================================================
    # ===== KHU VỰC: Mở chi tiết, bằng chứng, duyệt, ý kiến =====
    # ======================================================================

    @action(detail=True, methods=["post"])
    def open(self, request, pk=None):
        """Trang chi tiết gọi khi vừa mở. Ghi nhận 'đã mở' nếu đủ điều kiện, trả về chi tiết."""
        task = self.get_object()
        if task.can_mark_opened(request.user):
            # UPDATE có điều kiện: nhiều người mở cùng lúc thì chỉ người đầu tiên được ghi nhận.
            Task.objects.filter(
                pk=task.pk,
                first_opened_at__isnull=True,
                due_date__gte=timezone.localdate(),
            ).update(first_opened_at=timezone.now(), first_opened_by=request.user)
        return self.detail_response(task.pk)

    @action(detail=True, methods=["delete"], url_path=r"evidences/(?P<attachment_id>\d+)")
    def delete_evidence(self, request, pk=None, attachment_id=None):
        task = self.get_object()
        attachment = next((item for item in task.attachments.all() if item.pk == int(attachment_id)), None)
        if attachment is None:
            raise NotFound(
                "Không tìm thấy file bằng chứng. Có thể file đã bị xóa trước đó, hãy tải lại trang."
            )
        try:
            task.check_delete_evidence(request.user, attachment)
        except TaskRuleError as error:
            raise_rule_error(error)

        # Xóa mềm theo chuẩn CSDL (cột is_deleted): giữ bản ghi và file, chỉ thôi hiển thị.
        attachment.is_deleted = True
        attachment.save(update_fields=["is_deleted"])
        return self.detail_response(task.pk)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        task = self.get_object()
        try:
            task.check_approve(request.user)
        except TaskRuleError as error:
            raise_rule_error(error)

        has_evidence = Exists(
            TaskAttachment.objects.filter(task=OuterRef("pk"), kind=AttachmentKind.BANG_CHUNG)
        )
        with transaction.atomic():
            updated = (
                Task.objects.filter(pk=task.pk, approved_at__isnull=True)
                .filter(has_evidence)
                .update(approved_at=timezone.now(), approved_by=request.user)
            )
        if not updated:
            raise ValidationError({
                "detail": "Trạng thái công việc vừa thay đổi nên chưa duyệt được. Hãy tải lại trang rồi thử lại."
            })
        return self.detail_response(task.pk)

    @action(detail=True, methods=["post"])
    def unapprove(self, request, pk=None):
        task = self.get_object()
        try:
            task.check_unapprove(request.user)
        except TaskRuleError as error:
            raise_rule_error(error)

        with transaction.atomic():
            updated = Task.objects.filter(pk=task.pk, approved_at__isnull=False).update(
                approved_at=None,
                approved_by=None,
            )
        if not updated:
            raise ValidationError({
                "detail": "Công việc vừa được người khác hủy duyệt. Hãy tải lại trang để xem trạng thái mới nhất."
            })
        return self.detail_response(task.pk)

    @action(detail=True, methods=["get", "post"])
    def comments(self, request, pk=None):
        """
        GET: danh sách ý kiến (cũ trước, mới sau) kèm file.
        POST: ghi ý kiến, có thể kèm file kết quả; đây là cách duy nhất để nộp bằng chứng hoàn thành.
        """
        task = self.get_object()
        context = {**self.get_serializer_context(), "task": task}

        if request.method == "GET":
            attachments = Prefetch(
                "attachments",
                queryset=TaskAttachment.objects.filter(is_deleted=False)
                .select_related("uploaded_by")
                .order_by("uploaded_at", "id"),
            )
            items = (
                TaskComment.objects.filter(task=task)
                .select_related("author")
                .prefetch_related(attachments)
                .order_by("created_at", "id")
            )
            return Response(CommentSerializer(items, many=True, context=context).data)

        try:
            task.check_comment(request.user)
        except TaskRuleError as error:
            raise_rule_error(error)

        serializer = CommentSerializer(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        if serializer.validated_data.get("files"):
            try:
                task.check_submit_evidence(request.user)
            except TaskRuleError as error:
                raise_rule_error(error)

        with transaction.atomic():
            comment = serializer.save(task=task, author=request.user)

        # Đọc lại công việc để cờ canDelete của file mới tính theo trạng thái mới nhất.
        fresh_task = self.get_queryset().get(pk=task.pk)
        data = CommentSerializer(comment, context={**context, "task": fresh_task}).data
        return Response(data, status=status.HTTP_201_CREATED)


class AttachmentViewSet(WorkApiMixin, viewsets.GenericViewSet):
    """/api/work/attachments/{id}/download/ — tải file, có kiểm tra quyền xem công việc."""

    lookup_value_regex = r"\d+"

    def get_queryset(self):
        visible_tasks = Task.objects.visible_to(self.request.user)
        return TaskAttachment.objects.filter(task__in=visible_tasks, is_deleted=False)

    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        attachment = self.get_queryset().filter(pk=pk).first()
        if attachment is None:
            raise NotFound(
                "Không tìm thấy file, hoặc bạn không có quyền xem công việc chứa file này. "
                "Hãy tải lại trang chi tiết công việc rồi thử lại."
            )
        try:
            file_handle = attachment.file.open("rb")
        except (FileNotFoundError, OSError):
            raise NotFound(
                "File không còn trên máy chủ. Hãy báo người đã tải file lên để nộp lại file."
            )
        return FileResponse(file_handle, as_attachment=True, filename=attachment.original_name)


# ==========================================================================
# ===== KHU VỰC: Cán bộ nhân viên, người dùng hiện tại =====
# ==========================================================================

class EmployeeViewSet(WorkApiMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    /api/work/employees/?search= — danh sách CBNV cho ô chọn người.
    Trả mảng phẳng (ô chọn người của frontend cần mảng), không theo phân trang chung của dự án.
    """

    serializer_class = EmployeeSerializer
    pagination_class = None

    def get_queryset(self):
        queryset = (
            User.objects.filter(is_active=True)
            # chuc_vu + don_vi để serializer hiện Chức vụ - Phòng ban, tránh N+1 khi list.
            .select_related("chuc_vu", "don_vi")
            .order_by("ho_ten", "username")
        )
        search = self.request.query_params.get("search", "").strip()
        if search:
            queryset = queryset.filter(
                Q(username__icontains=search)
                | Q(ho_ten__icontains=search)
            )
        return queryset


class MeView(WorkApiMixin, APIView):
    """/api/work/me/ — người dùng đang đăng nhập (đang giả lập)."""

    def get(self, request):
        return Response(MeSerializer(request.user).data)
