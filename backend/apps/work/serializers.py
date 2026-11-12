from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.urls import reverse
from django.utils import timezone
from rest_framework import serializers

from authorization.permissions import is_system_admin
from documents.selectors import van_ban_xem_duoc
from work.models import (
    AttachmentKind,
    DocumentKind,
    ParticipantRole,
    Task,
    TaskAttachment,
    TaskComment,
    TaskDonVi,
    TaskParticipant,
    TaskRuleError,
    TaskStatus,
    delete_stored_files_on_commit,
    validate_work_file,
)

User = get_user_model()


def employee_full_name(user):
    """Tên hiển thị: họ và tên (ho_ten) của Employee; chưa khai báo thì dùng username."""
    full_name = (user.get_full_name() or "").strip()
    return full_name or user.username


def employee_position(user):
    """
    Tên chức vụ đọc từ accounts.Position.name qua FK chuc_vu (model nhóm 7, chỉ đọc).
    An toàn null: model khai NOT NULL nhưng seed cũ có thể thiếu FK — thiếu thì trả "" chứ
    không raise, để một record lỗi không làm vỡ cả API danh sách.
    """
    try:
        position = user.chuc_vu
    except ObjectDoesNotExist:
        return ""
    return (getattr(position, "name", "") or "").strip()


def employee_department(user):
    """Tên phòng ban đọc từ organizations.DonVi.ten qua FK don_vi (model nhóm tổ chức, chỉ đọc). An toàn null như trên."""
    try:
        don_vi = user.don_vi
    except ObjectDoesNotExist:
        return ""
    return (getattr(don_vi, "ten", "") or "").strip()


def work_file_field():
    return serializers.FileField(
        validators=[validate_work_file],
        error_messages={
            "invalid": "Dữ liệu gửi lên không phải file. Hãy chọn lại file từ máy.",
            "empty": "File đang trống (0 byte). Hãy kiểm tra lại file trên máy rồi chọn lại.",
            "no_name": "Không đọc được tên file. Hãy đổi tên file rồi chọn lại.",
            "max_length": "Tên file quá dài. Hãy đổi tên file ngắn hơn 100 ký tự rồi chọn lại.",
        },
    )


# ==========================================================================
# ===== KHU VỰC: Dùng chung — CBNV rút gọn, file đính kèm, API trang chủ =====
# ==========================================================================

class EmployeeBriefSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    fullName = serializers.SerializerMethodField()
    position = serializers.SerializerMethodField()
    department = serializers.SerializerMethodField()

    def get_fullName(self, user):
        return employee_full_name(user)

    def get_position(self, user):
        return employee_position(user)

    def get_department(self, user):
        return employee_department(user)


class AttachmentSerializer(serializers.ModelSerializer):
    fileName = serializers.CharField(source="original_name", read_only=True)
    # CSDL không có cột dung lượng: đọc từ kho lưu trữ qua property của model.
    size = serializers.IntegerField(read_only=True)
    uploadedBy = EmployeeBriefSerializer(source="uploaded_by", read_only=True)
    uploadedAt = serializers.DateTimeField(source="uploaded_at", read_only=True)
    commentId = serializers.IntegerField(source="comment_id", read_only=True)
    downloadUrl = serializers.SerializerMethodField()
    canDelete = serializers.SerializerMethodField()
    deleteBlockedReason = serializers.SerializerMethodField()

    class Meta:
        model = TaskAttachment
        fields = [
            "id",
            "kind",
            "fileName",
            "size",
            "uploadedBy",
            "uploadedAt",
            "commentId",
            "downloadUrl",
            "canDelete",
            "deleteBlockedReason",
        ]

    def get_downloadUrl(self, obj):
        # Đường dẫn tương đối: build_absolute_uri mất cổng khi proxy chuyển Host không kèm cổng.
        return reverse("work:attachment-download", kwargs={"pk": obj.pk})

    def get_canDelete(self, obj):
        # Chỉ file bằng chứng mới có nút xóa riêng; file giao việc xóa trong màn hình sửa.
        task = self.context.get("task")
        request = self.context.get("request")
        if task is None or request is None or obj.kind != AttachmentKind.BANG_CHUNG:
            return False
        return task.can_delete_evidence(request.user, obj)

    def get_deleteBlockedReason(self, obj):
        """Người nộp file mà chưa xóa được (đã duyệt, file cuối sau hạn...) thì cho biết lý do và cách xử lý."""
        task = self.context.get("task")
        request = self.context.get("request")
        if task is None or request is None or obj.kind != AttachmentKind.BANG_CHUNG:
            return None
        if obj.uploaded_by_id != request.user.id:
            return None
        try:
            task.check_delete_evidence(request.user, obj)
        except TaskRuleError as error:
            return error.message
        return None


class LatestTaskSerializer(serializers.ModelSerializer):
    """API 5 công việc mới nhất cho trang chủ (nhóm 1)."""

    createdDate = serializers.DateField(source="created_date", read_only=True)
    dueDate = serializers.DateField(source="due_date", read_only=True)
    status = serializers.CharField(read_only=True)
    statusLabel = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = ["id", "title", "createdDate", "dueDate", "status", "statusLabel"]

    def get_statusLabel(self, obj):
        return TaskStatus(obj.get_status()).label


# ==========================================================================
# ===== KHU VỰC: Danh sách, chi tiết, thêm / sửa công việc =====
# ==========================================================================

class TaskListSerializer(serializers.ModelSerializer):
    createdDate = serializers.DateField(source="created_date", read_only=True)
    dueDate = serializers.DateField(source="due_date", read_only=True)
    status = serializers.SerializerMethodField()
    statusLabel = serializers.SerializerMethodField()
    isPublic = serializers.BooleanField(source="is_public", read_only=True)
    creator = EmployeeBriefSerializer(source="created_by", read_only=True)
    host = serializers.SerializerMethodField()
    directors = serializers.SerializerMethodField()
    participants = serializers.SerializerMethodField()
    myRoles = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            "id",
            "title",
            "requirement",
            "createdDate",
            "dueDate",
            "status",
            "statusLabel",
            "isPublic",
            "creator",
            "host",
            "directors",
            "participants",
            "myRoles",
            "permissions",
        ]

    def _current_user(self):
        request = self.context.get("request")
        return request.user if request else None

    def _people(self, obj, role):
        users = [p.user for p in obj.participants.all() if p.role == role]
        return EmployeeBriefSerializer(users, many=True).data

    def get_status(self, obj):
        return obj.get_status()

    def get_statusLabel(self, obj):
        return TaskStatus(obj.get_status()).label

    def get_host(self, obj):
        hosts = self._people(obj, ParticipantRole.CHU_TRI)
        return hosts[0] if hosts else None

    def get_directors(self, obj):
        return self._people(obj, ParticipantRole.CHI_DAO)

    def get_participants(self, obj):
        return self._people(obj, ParticipantRole.THAM_GIA)

    def get_myRoles(self, obj):
        return sorted(obj.roles_of(self._current_user()))

    def get_permissions(self, obj):
        user = self._current_user()
        return {
            "canEdit": obj.can_edit(user),
            "canDelete": obj.can_delete(user),
            "canExtend": obj.can_extend(user),
            "canReview": obj._can_approve(user),
            "canApprove": obj.can_approve(user),
            "canUnapprove": obj.can_unapprove(user),
        }


class TaskDetailSerializer(TaskListSerializer):
    firstOpenedAt = serializers.DateTimeField(source="first_opened_at", read_only=True)
    firstOpenedBy = EmployeeBriefSerializer(source="first_opened_by", read_only=True)
    firstEvidenceAt = serializers.SerializerMethodField()
    approvedAt = serializers.DateTimeField(source="approved_at", read_only=True)
    approvedBy = EmployeeBriefSerializer(source="approved_by", read_only=True)
    attachments = serializers.SerializerMethodField()
    evidences = serializers.SerializerMethodField()
    commentCount = serializers.SerializerMethodField()
    donViIds = serializers.SerializerMethodField()
    documentType = serializers.SerializerMethodField()
    documentId = serializers.SerializerMethodField()

    class Meta(TaskListSerializer.Meta):
        fields = TaskListSerializer.Meta.fields + [
            "firstOpenedAt",
            "firstOpenedBy",
            "firstEvidenceAt",
            "approvedAt",
            "approvedBy",
            "attachments",
            "evidences",
            "commentCount",
            "donViIds",
            "documentType",
            "documentId",
        ]

    def _files(self, obj, kind):
        files = [item for item in obj.attachments.all() if item.kind == kind and not item.is_deleted]
        context = {**self.context, "task": obj}
        return AttachmentSerializer(files, many=True, context=context).data

    def get_attachments(self, obj):
        return self._files(obj, AttachmentKind.GIAO_VIEC)

    def get_evidences(self, obj):
        return self._files(obj, AttachmentKind.BANG_CHUNG)

    def get_firstEvidenceAt(self, obj):
        evidences = obj.evidence_files()
        if not evidences:
            return None
        first = min(evidences, key=lambda item: item.uploaded_at)
        return serializers.DateTimeField().to_representation(first.uploaded_at)

    def get_donViIds(self, obj):
        """Id các phòng/ban được gắn. TODO: tra ve ca ten don vi khi co app organizations."""
        return sorted(link.don_vi_id for link in obj.don_vi_links.all())

    def get_commentCount(self, obj):
        return obj.comments.count()

    def _can_view_document(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated or not obj.document_id:
            return False
        loai = {"vanbanden": "DEN", "vanbandi": "DI"}.get(obj.document_type)
        if not loai:
            return False
        return van_ban_xem_duoc(request.user, loai).filter(pk=obj.document_id).exists()

    def get_documentType(self, obj):
        return obj.document_type if self._can_view_document(obj) else None

    def get_documentId(self, obj):
        return obj.document_id if self._can_view_document(obj) else None

    def get_permissions(self, obj):
        user = self._current_user()
        return {
            **super().get_permissions(obj),
            "canSubmitEvidence": obj.can_submit_evidence(user),
            "canComment": obj.can_comment(user),
        }


class TaskWriteSerializer(serializers.Serializer):
    """Dùng chung cho Thêm (POST) và Sửa (PATCH). Dữ liệu gửi dạng multipart/form-data."""

    PEOPLE_FIELDS = ("host", "directors", "participants")

    title = serializers.CharField(
        error_messages={
            "required": "Hãy nhập nội dung công việc.",
            "blank": "Nội dung công việc đang trống. Hãy nhập nội dung công việc.",
        },
    )
    createdDate = serializers.DateField(
        source="created_date",
        required=False,
        error_messages={"invalid": "Ngày tạo không hợp lệ. Hãy chọn lại ngày tạo trên lịch."},
    )
    dueDate = serializers.DateField(
        source="due_date",
        error_messages={
            "required": "Hãy chọn ngày xử lý.",
            "null": "Hãy chọn ngày xử lý.",
            "invalid": "Ngày xử lý không hợp lệ. Hãy chọn lại ngày xử lý trên lịch.",
        },
    )
    requirement = serializers.CharField(
        error_messages={
            "required": "Hãy nhập yêu cầu xử lý.",
            "blank": "Yêu cầu xử lý đang trống. Hãy nhập yêu cầu xử lý.",
        },
    )
    hostId = serializers.PrimaryKeyRelatedField(
        source="host",
        queryset=User.objects.filter(is_active=True),
        error_messages={
            "required": "Hãy chọn người chủ trì giải quyết công việc.",
            "null": "Hãy chọn người chủ trì giải quyết công việc.",
            "does_not_exist": "Không tìm thấy cán bộ chủ trì đã chọn. Hãy tải lại danh sách cán bộ rồi chọn lại.",
            "incorrect_type": "Người chủ trì không hợp lệ. Hãy chọn lại người chủ trì trong danh sách.",
        },
    )
    directorIds = serializers.PrimaryKeyRelatedField(
        source="directors",
        many=True,
        allow_empty=False,
        queryset=User.objects.filter(is_active=True),
        error_messages={
            "required": "Hãy chọn ít nhất một người chỉ đạo - theo dõi tiến độ.",
            "empty": "Hãy chọn ít nhất một người chỉ đạo - theo dõi tiến độ.",
        },
    )
    participantIds = serializers.PrimaryKeyRelatedField(
        source="participants",
        many=True,
        allow_empty=False,
        queryset=User.objects.filter(is_active=True),
        error_messages={
            "required": "Hãy chọn ít nhất một cán bộ tham gia giải quyết công việc.",
            "empty": "Hãy chọn ít nhất một cán bộ tham gia giải quyết công việc.",
        },
    )
    isPublic = serializers.BooleanField(source="is_public", required=False, default=True)
    donViIds = serializers.ListField(
        source="don_vi_ids",
        child=serializers.IntegerField(),
        required=False,
        error_messages={"invalid": "Danh sách phòng ban không hợp lệ. Hãy chọn lại phòng ban."},
    )
    documentType = serializers.ChoiceField(
        source="document_type",
        choices=DocumentKind.choices,
        required=False,
        allow_null=True,
        error_messages={
            "invalid_choice": "Loại văn bản không hợp lệ. Hãy chọn Văn bản đến hoặc Văn bản đi."
        },
    )
    documentId = serializers.IntegerField(source="document_id", required=False, allow_null=True)
    attachments = serializers.ListField(child=work_file_field(), required=False)
    removeAttachmentIds = serializers.ListField(
        source="remove_attachment_ids",
        child=serializers.IntegerField(),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Thông báo lỗi cho từng id sai trong danh sách nhiều người.
        for name, label in (("directorIds", "người chỉ đạo"), ("participantIds", "cán bộ tham gia")):
            self.fields[name].child_relation.error_messages.update({
                "does_not_exist": f"Không tìm thấy {label} đã chọn. Hãy tải lại danh sách cán bộ rồi chọn lại.",
                "incorrect_type": f"Danh sách {label} không hợp lệ. Hãy chọn lại {label} trong danh sách.",
            })

    def to_representation(self, instance):
        """Dữ liệu hiện tại theo đúng định dạng gửi lên — dùng để điền sẵn form PATCH của trang API trên trình duyệt."""
        people = list(instance.participants.all())
        return {
            "title": instance.title,
            "createdDate": instance.created_date.isoformat(),
            "dueDate": instance.due_date.isoformat(),
            "requirement": instance.requirement,
            "hostId": next((p.user_id for p in people if p.role == ParticipantRole.CHU_TRI), None),
            "directorIds": [p.user_id for p in people if p.role == ParticipantRole.CHI_DAO],
            "participantIds": [p.user_id for p in people if p.role == ParticipantRole.THAM_GIA],
            "isPublic": instance.is_public,
            "donViIds": sorted(link.don_vi_id for link in instance.don_vi_links.all()),
        }

    def validate(self, attrs):
        instance = self.instance
        today = timezone.localdate()
        errors = {}

        created_date = attrs.get("created_date", instance.created_date if instance else today)
        due_date = attrs.get("due_date", instance.due_date if instance else None)

        # Quy tắc "không chọn ngày quá khứ" chỉ áp dụng khi tạo mới.
        if instance is None and created_date < today:
            errors["createdDate"] = (
                "Ngày tạo không được ở trong quá khứ. Hãy chọn hôm nay hoặc một ngày sau hôm nay."
            )

        if due_date is not None and due_date < created_date:
            errors["dueDate"] = (
                "Ngày xử lý đang trước ngày tạo. Hãy chọn ngày xử lý bằng hoặc sau ngày tạo."
            )
        elif instance is not None and "due_date" in attrs and due_date < today:
            errors["dueDate"] = (
                "Hạn xử lý đã ở trong quá khứ nên công việc sẽ bị khóa ngay sau khi lưu. "
                "Hãy chọn hạn xử lý từ hôm nay trở đi."
            )

        people_sent = [name for name in self.PEOPLE_FIELDS if name in attrs]
        if instance is not None and 0 < len(people_sent) < len(self.PEOPLE_FIELDS):
            errors["non_field_errors"] = [
                "Khi thay đổi người liên quan, hãy gửi đủ cả người chủ trì, người chỉ đạo và cán bộ tham gia."
            ]
        elif people_sent:
            errors.update(self._validate_one_role_per_person(attrs))

        document_type = attrs.get("document_type", getattr(instance, "document_type", None))
        document_id = attrs.get("document_id", getattr(instance, "document_id", None))
        if bool(document_type) != bool(document_id):
            errors["documentType"] = (
                "Văn bản liên quan phải chọn đủ cả loại văn bản và mã văn bản, "
                "hoặc bỏ trống cả hai nếu công việc không phát sinh từ văn bản."
            )
        elif document_type and document_id and (
            instance is None or "document_type" in attrs or "document_id" in attrs
        ):
            request = self.context.get("request")
            loai = {"vanbanden": "DEN", "vanbandi": "DI"}.get(document_type)
            if (
                not request
                or not request.user.is_authenticated
                or not loai
                or not van_ban_xem_duoc(request.user, loai).filter(pk=document_id).exists()
            ):
                errors["documentId"] = (
                    "Không tìm thấy văn bản hoặc bạn không có quyền xem văn bản này."
                )

        remove_ids = attrs.get("remove_attachment_ids") or []
        if remove_ids:
            if instance is None:
                errors["removeAttachmentIds"] = "Công việc mới chưa có file để xóa. Hãy bỏ trường này khi tạo mới."
            else:
                valid_ids = set(
                    instance.attachments.filter(kind=AttachmentKind.GIAO_VIEC).values_list("id", flat=True)
                )
                invalid_ids = [str(item) for item in remove_ids if item not in valid_ids]
                if invalid_ids:
                    errors["removeAttachmentIds"] = (
                        f"File đính kèm có id {', '.join(invalid_ids)} không thuộc công việc này. "
                        "Hãy tải lại trang rồi thử lại."
                    )

        if errors:
            raise serializers.ValidationError(errors)
        return attrs

    def _validate_one_role_per_person(self, attrs):
        # Bỏ id trùng trong cùng một danh sách (chọn 2 lần cùng một người).
        attrs["directors"] = list({user.pk: user for user in attrs["directors"]}.values())
        attrs["participants"] = list({user.pk: user for user in attrs["participants"]}.values())

        seen = {attrs["host"].pk: "chủ trì"}
        for field_name, users, label in (
            ("directorIds", attrs["directors"], "chỉ đạo - theo dõi tiến độ"),
            ("participantIds", attrs["participants"], "cán bộ tham gia"),
        ):
            for user in users:
                if user.pk in seen:
                    return {
                        field_name: (
                            f"Cán bộ {employee_full_name(user)} đang được chọn ở cả vai trò "
                            f"{seen[user.pk]} và {label}. Mỗi cán bộ chỉ giữ một vai trò trong công việc, "
                            "hãy bỏ cán bộ này khỏi một trong hai vai trò."
                        )
                    }
                seen[user.pk] = label
        return {}

    def _save_people(self, task, attrs):
        if not all(name in attrs for name in self.PEOPLE_FIELDS):
            return
        task.participants.all().delete()
        rows = [TaskParticipant(task=task, user=attrs["host"], role=ParticipantRole.CHU_TRI)]
        rows += [TaskParticipant(task=task, user=u, role=ParticipantRole.CHI_DAO) for u in attrs["directors"]]
        rows += [TaskParticipant(task=task, user=u, role=ParticipantRole.THAM_GIA) for u in attrs["participants"]]
        # vai_tro là ENUM task_vaitro: bulk_create trên PostgreSQL ép kiểu varchar[] (UNNEST)
        # nên bị từ chối; tạo từng dòng.
        for row in rows:
            row.save()

    def _save_files(self, task, files, user):
        for uploaded in files:
            TaskAttachment.objects.create(
                task=task,
                kind=AttachmentKind.GIAO_VIEC,
                file=uploaded,
                uploaded_by=user,
            )

    def _save_don_vi(self, task, don_vi_ids):
        """Gắn lại danh sách phòng/ban cho công việc (gửi danh sách rỗng là bỏ hết)."""
        if don_vi_ids is None:
            return
        task.don_vi_links.all().delete()
        TaskDonVi.objects.bulk_create(
            [TaskDonVi(task=task, don_vi_id=don_vi_id) for don_vi_id in dict.fromkeys(don_vi_ids)]
        )

    @transaction.atomic
    def create(self, validated_data):
        user = self.context["request"].user
        files = validated_data.pop("attachments", [])
        people = {name: validated_data.pop(name) for name in self.PEOPLE_FIELDS}
        don_vi_ids = validated_data.pop("don_vi_ids", None)
        validated_data.pop("remove_attachment_ids", None)

        task = Task.objects.create(created_by=user, **validated_data)
        self._save_people(task, people)
        self._save_don_vi(task, don_vi_ids)
        self._save_files(task, files, user)
        return task

    @transaction.atomic
    def update(self, instance, validated_data):
        user = self.context["request"].user
        files = validated_data.pop("attachments", [])
        people = {name: validated_data.pop(name) for name in self.PEOPLE_FIELDS if name in validated_data}
        don_vi_ids = validated_data.pop("don_vi_ids", None)
        remove_ids = validated_data.pop("remove_attachment_ids", [])

        for field_name, value in validated_data.items():
            setattr(instance, field_name, value)
        instance.save()

        self._save_people(instance, people)
        self._save_don_vi(instance, don_vi_ids)

        if remove_ids:
            removed = instance.attachments.filter(kind=AttachmentKind.GIAO_VIEC, id__in=remove_ids)
            delete_stored_files_on_commit([item.file.name for item in removed])
            removed.delete()

        self._save_files(instance, files, user)
        return instance


# ==========================================================================
# ===== KHU VỰC: Ý kiến xử lý (kèm file kết quả = bằng chứng hoàn thành) =====
# ==========================================================================

class CommentSerializer(serializers.ModelSerializer):
    """
    Ghi ý kiến, có thể kèm file (không bắt buộc). File kèm theo là file kết quả (bằng chứng):
    có file đầu tiên thì công việc chuyển sang Chờ duyệt.
    """

    content = serializers.CharField(
        max_length=5000,
        allow_blank=True,
        required=False,
        default="",
        error_messages={
            "max_length": "Ý kiến dài quá 5000 ký tự. Hãy rút gọn hoặc tách thành nhiều ý kiến.",
        },
    )
    files = serializers.ListField(child=work_file_field(), required=False, write_only=True)
    author = EmployeeBriefSerializer(read_only=True)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    attachments = serializers.SerializerMethodField()

    class Meta:
        model = TaskComment
        fields = ["id", "content", "files", "author", "createdAt", "attachments"]

    def get_attachments(self, obj):
        files = [item for item in obj.attachments.all() if not item.is_deleted]
        return AttachmentSerializer(files, many=True, context=self.context).data

    def validate(self, attrs):
        attrs["content"] = attrs.get("content", "").strip()
        if not attrs["content"] and not attrs.get("files"):
            raise serializers.ValidationError({
                "content": "Ý kiến đang trống. Hãy nhập nội dung hoặc đính kèm file kết quả trước khi gửi."
            })
        return attrs

    def create(self, validated_data):
        files = validated_data.pop("files", [])
        comment = TaskComment.objects.create(**validated_data)
        for uploaded in files:
            TaskAttachment.objects.create(
                task=comment.task,
                comment=comment,
                kind=AttachmentKind.BANG_CHUNG,
                file=uploaded,
                uploaded_by=comment.author,
            )
        return comment


# ==========================================================================
# ===== KHU VỰC: Cán bộ nhân viên, người dùng hiện tại =====
# ==========================================================================

class EmployeeSerializer(EmployeeBriefSerializer):
    username = serializers.CharField(read_only=True)


class MeSerializer(EmployeeSerializer):
    isAdmin = serializers.SerializerMethodField()

    def get_isAdmin(self, obj):
        return is_system_admin(obj)
