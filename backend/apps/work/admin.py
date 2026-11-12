from django.contrib import admin
from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet

from work.models import AttachmentKind, ParticipantRole, Task, TaskAttachment, TaskComment, TaskParticipant, TaskStatus


class TaskParticipantInlineFormSet(BaseInlineFormSet):
    """Kiểm tra đúng 1 chủ trì trên cả form (ràng buộc DB chỉ bắt được khi đã lưu)."""

    def clean(self):
        super().clean()
        host_count = 0
        for form in self.forms:
            if not hasattr(form, "cleaned_data") or not form.cleaned_data:
                continue
            if form.cleaned_data.get("DELETE"):
                continue
            if form.cleaned_data.get("role") == ParticipantRole.CHU_TRI:
                host_count += 1

        if host_count == 0:
            raise ValidationError(
                "Công việc chưa có người chủ trì. "
                "Hãy thêm một dòng với vai trò \"Chủ trì giải quyết công việc\"."
            )
        if host_count > 1:
            raise ValidationError(
                "Công việc đang có nhiều hơn một người chủ trì. "
                "Hãy giữ lại một người chủ trì và chuyển những người còn lại sang vai trò khác."
            )


class TaskParticipantInline(admin.TabularInline):
    model = TaskParticipant
    formset = TaskParticipantInlineFormSet
    extra = 1
    fields = ("user", "role")


class TaskAttachmentInline(admin.TabularInline):
    """File đính kèm lúc giao việc: thêm / bỏ được."""

    model = TaskAttachment
    extra = 0
    verbose_name = "File đính kèm lúc giao việc"
    verbose_name_plural = "File đính kèm lúc giao việc"
    fields = ("file", "original_name", "size", "uploaded_by", "uploaded_at")
    readonly_fields = ("original_name", "size", "uploaded_by", "uploaded_at")

    def get_queryset(self, request):
        return super().get_queryset(request).filter(kind=AttachmentKind.GIAO_VIEC)


class TaskEvidenceInline(admin.TabularInline):
    """File bằng chứng luôn nằm trong ý kiến, chỉ tạo được từ trang chi tiết công việc."""

    model = TaskAttachment
    extra = 0
    verbose_name = "File bằng chứng (trong ý kiến)"
    verbose_name_plural = "File bằng chứng (trong ý kiến)"
    fields = ("original_name", "size", "comment", "uploaded_by", "uploaded_at")
    readonly_fields = fields

    def get_queryset(self, request):
        return super().get_queryset(request).filter(kind=AttachmentKind.BANG_CHUNG)

    def has_add_permission(self, request, obj=None):
        return False


class TaskCommentInline(admin.TabularInline):
    model = TaskComment
    extra = 0
    fields = ("content", "author", "created_at")
    readonly_fields = ("author", "created_at")


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "short_title",
        "created_by",
        "created_date",
        "due_date",
        "status_label",
        "is_public",
    )
    list_display_links = ("id", "short_title")
    list_filter = ("is_public", "created_date", "due_date")
    search_fields = ("title", "requirement")
    date_hierarchy = "created_date"
    readonly_fields = (
        "status_label",
        "first_opened_at",
        "first_opened_by",
        "approved_at",
        "approved_by",
        "created_at",
        "updated_at",
    )
    fieldsets = (
        (None, {
            "fields": ("title", "requirement", ("created_date", "due_date"), "created_by", "is_public"),
        }),
        ("Mốc xử lý (hệ thống ghi nhận)", {
            "fields": (
                "status_label",
                ("first_opened_at", "first_opened_by"),
                ("approved_at", "approved_by"),
                ("created_at", "updated_at"),
            ),
        }),
    )
    inlines = (TaskParticipantInline, TaskAttachmentInline, TaskCommentInline, TaskEvidenceInline)

    def get_queryset(self, request):
        return super().get_queryset(request).with_status().select_related("created_by")

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        initial.setdefault("created_by", request.user.pk)
        return initial

    @admin.display(description="Nội dung công việc")
    def short_title(self, obj):
        return str(obj)

    @admin.display(description="Trạng thái", ordering="status")
    def status_label(self, obj):
        status = getattr(obj, "status", None)
        if status is None:
            return "—"
        return TaskStatus(status).label

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for obj in formset.deleted_objects:
            obj.delete()
        for instance in instances:
            # Người tải file / người ghi ý kiến mặc định là tài khoản admin đang thao tác.
            if isinstance(instance, TaskAttachment):
                if not instance.kind:
                    instance.kind = AttachmentKind.GIAO_VIEC
                if not instance.uploaded_by_id:
                    instance.uploaded_by = request.user
            if isinstance(instance, TaskComment) and not instance.author_id:
                instance.author = request.user
            instance.save()
        formset.save_m2m()
