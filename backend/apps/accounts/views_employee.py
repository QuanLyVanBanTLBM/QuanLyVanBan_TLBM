"""
API ViewSets cho phân hệ Quản lý Cán bộ Nhân viên (CBNV - Issue #24).
Tác giả: Lê Duy Khánh (leduykhanhdevs).
"""
import logging
import queue
import threading
import uuid
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.db import IntegrityError, close_old_connections, transaction
from django.db.models import Q, ProtectedError, RestrictedError, Prefetch
from django.contrib.auth.models import Group
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Employee, EmployeeAssignment, EmployeeImportJob, EmployeePasswordResetAudit
from .serializers import (
    GroupSimpleSerializer,
    EmployeeSerializer,
    EmployeeCreateSerializer,
    EmployeeUpdateSerializer,
    EmployeeAdminPasswordChangeSerializer,
    user_can_view_sensitive,
)
from .excel_cbnv import generate_cbnv_template, import_cbnv_from_excel, export_cbnv_to_excel
from .permissions import CanChangeEmployeePermission, CanViewGroupPermission, IsEmployeeAdminOnly, require_permission


SAFE_ORDERING_FIELDS = {
    "ho_ten", "-ho_ten",
    "username", "-username",
    "email", "-email",
    "created_at", "-created_at",
    "don_vi__stt_uu_tien", "-don_vi__stt_uu_tien",
    "chuc_vu__display_order", "-chuc_vu__display_order",
    "id", "-id",
}

logger = logging.getLogger(__name__)
_employee_import_workers = {}
_employee_import_workers_lock = threading.Lock()
_EMPLOYEE_IMPORT_ACTIVE_KEY = "cbnv-import"
_EMPLOYEE_IMPORT_MAX_BYTES = 5 * 1024 * 1024
_EMPLOYEE_IMPORT_STALE_AFTER = timedelta(seconds=30)
_EMPLOYEE_IMPORT_HISTORY_TTL = timedelta(days=1)


def _employee_import_path(relative_path):
    root = (Path(settings.MEDIA_ROOT) / ".private" / "cbnv-import-jobs").resolve()
    file_path = (Path(settings.MEDIA_ROOT) / relative_path).resolve()
    if root not in file_path.parents:
        raise ValueError("Invalid CBNV import file path")
    return file_path


def _save_employee_import_upload(upload, job_id):
    if upload.size > _EMPLOYEE_IMPORT_MAX_BYTES:
        raise ValueError("employees.import.fileTooLarge")

    relative_path = f".private/cbnv-import-jobs/{job_id}.xlsx"
    file_path = _employee_import_path(relative_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        try:
            file_path.parent.chmod(0o755)
        except OSError:
            # Windows applies ACLs; production uses the owning service account on a private path.
            pass
        with file_path.open("xb") as destination:
            for chunk in upload.chunks():
                destination.write(chunk)
        try:
            file_path.chmod(0o644)
        except OSError:
            pass
        return relative_path
    except Exception:
        file_path.unlink(missing_ok=True)
        raise


def _update_employee_import_job(job_id, **values):
    values["updated_at"] = timezone.now()
    EmployeeImportJob.objects.filter(pk=job_id).update(**values)


def _run_employee_import_job(job_id):
    """Claim a persisted job once and publish progress outside the atomic employee insert transaction."""
    close_old_connections()
    claimed = EmployeeImportJob.objects.filter(
        pk=job_id,
        status=EmployeeImportJob.Status.QUEUED,
    ).update(
        status=EmployeeImportJob.Status.PROCESSING,
        phase=EmployeeImportJob.Phase.VALIDATION,
        message="employees.import.jobValidating",
        updated_at=timezone.now(),
    )
    if not claimed:
        close_old_connections()
        return

    job = EmployeeImportJob.objects.get(pk=job_id)
    updates = queue.Queue(maxsize=64)
    result_holder = {}
    source_thread = None

    def report_progress(phase, processed, total):
        updates.put((phase, processed, total))

    def run_import():
        close_old_connections()
        try:
            file_path = _employee_import_path(job.file_path)

            def mark_import_committed(created_count):
                EmployeeImportJob.objects.filter(
                    pk=job_id,
                    status=EmployeeImportJob.Status.PROCESSING,
                ).update(
                    status=EmployeeImportJob.Status.DONE,
                    active_key=None,
                    phase=EmployeeImportJob.Phase.COMPLETE,
                    processed=created_count,
                    total=created_count,
                    created_count=created_count,
                    errors=[],
                    message="employees.import.importSuccess",
                    updated_at=timezone.now(),
                )

            with file_path.open("rb") as source:
                result_holder["result"] = import_cbnv_from_excel(
                    source,
                    progress_callback=report_progress,
                    completion_callback=mark_import_committed,
                )
        except Exception as exc:
            result_holder["error"] = exc
        finally:
            close_old_connections()

    try:
        source_thread = threading.Thread(
            target=run_import,
            daemon=True,
            name=f"cbnv-import-db-{str(job_id)[:8]}",
        )
        source_thread.start()
        last_heartbeat = timezone.now()
        while source_thread.is_alive() or not updates.empty():
            try:
                phase, processed, total = updates.get(timeout=2)
                _update_employee_import_job(
                    job_id,
                    phase=phase,
                    processed=processed,
                    total=total,
                    message=(
                        "employees.import.jobSaving"
                        if phase == EmployeeImportJob.Phase.SAVING
                        else "employees.import.jobValidating"
                    ),
                )
                last_heartbeat = timezone.now()
            except queue.Empty:
                if (timezone.now() - last_heartbeat).total_seconds() >= 5:
                    _update_employee_import_job(job_id)
                    last_heartbeat = timezone.now()

        source_thread.join()
        result = result_holder.get("result")
        if result and result.get("success"):
            _update_employee_import_job(
                job_id,
                status=EmployeeImportJob.Status.DONE,
                active_key=None,
                phase=EmployeeImportJob.Phase.COMPLETE,
                processed=result.get("created_count", 0),
                total=result.get("created_count", 0),
                created_count=result.get("created_count", 0),
                errors=[],
                message="employees.import.importSuccess",
            )
        elif result:
            _update_employee_import_job(
                job_id,
                status=EmployeeImportJob.Status.FAILED,
                active_key=None,
                phase=EmployeeImportJob.Phase.VALIDATION,
                errors=result.get("errors", []),
                message=result.get("message", "employees.import.uploadError"),
            )
        else:
            raise result_holder.get("error", RuntimeError("Import returned no result"))
    except Exception:
        logger.exception("CBNV Excel import job failed: %s", job_id)
        EmployeeImportJob.objects.filter(
            pk=job_id,
            status=EmployeeImportJob.Status.PROCESSING,
        ).update(
            status=EmployeeImportJob.Status.FAILED,
            active_key=None,
            phase=EmployeeImportJob.Phase.FAILED,
            errors=[],
            message="employees.import.uploadError",
            updated_at=timezone.now(),
        )
    finally:
        try:
            _employee_import_path(job.file_path).unlink(missing_ok=True)
        except (OSError, ValueError):
            logger.warning("Unable to remove CBNV import file for job %s", job_id)
        with _employee_import_workers_lock:
            _employee_import_workers.pop(str(job_id), None)
        close_old_connections()


def _start_employee_import_worker(job_id):
    key = str(job_id)
    with _employee_import_workers_lock:
        worker = _employee_import_workers.get(key)
        if worker and worker.is_alive():
            return
        worker = threading.Thread(
            target=_run_employee_import_job,
            args=(job_id,),
            daemon=True,
            name=f"cbnv-import-{key[:8]}",
        )
        _employee_import_workers[key] = worker
        try:
            worker.start()
        except Exception:
            _employee_import_workers.pop(key, None)
            raise


def _resume_stale_employee_import_job(job):
    if job.status == EmployeeImportJob.Status.QUEUED:
        _start_employee_import_worker(job.pk)
        return job
    if (
        job.status != EmployeeImportJob.Status.PROCESSING
        or timezone.now() - job.updated_at <= _EMPLOYEE_IMPORT_STALE_AFTER
    ):
        return job

    with transaction.atomic():
        stale_job = EmployeeImportJob.objects.select_for_update().filter(pk=job.pk).first()
        if (
            stale_job
            and stale_job.status == EmployeeImportJob.Status.PROCESSING
            and timezone.now() - stale_job.updated_at > _EMPLOYEE_IMPORT_STALE_AFTER
        ):
            try:
                file_exists = _employee_import_path(stale_job.file_path).is_file()
            except ValueError:
                file_exists = False
            stale_job.status = EmployeeImportJob.Status.QUEUED
            stale_job.phase = EmployeeImportJob.Phase.QUEUED
            stale_job.processed = 0
            stale_job.total = 0
            stale_job.message = "employees.import.jobQueued"
            if not file_exists:
                stale_job.status = EmployeeImportJob.Status.FAILED
                stale_job.active_key = None
                stale_job.phase = EmployeeImportJob.Phase.FAILED
                stale_job.message = "employees.import.uploadError"
            stale_job.save(update_fields=[
                "status", "active_key", "phase", "processed", "total", "message", "updated_at",
            ])
            job = stale_job

    if job.status == EmployeeImportJob.Status.QUEUED:
        _start_employee_import_worker(job.pk)
    return job


class StandardEmployeePagination(PageNumberPagination):
    """Phân trang chuẩn cho danh sách cán bộ nhân viên."""
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class GroupViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Danh sách Nhóm quyền (auth.Group) hỗ trợ cấu hình phân quyền cho CBNV.
    Yêu cầu quyền view_nhomquyen, change_full_cbnv hoặc add_cbnv.
    """
    queryset = Group.objects.all().order_by("name")
    serializer_class = GroupSimpleSerializer
    permission_classes = [IsAuthenticated, CanViewGroupPermission]

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class EmployeeViewSet(viewsets.ModelViewSet):
    """
    API Quản lý Cán bộ Nhân viên (CBNV - Issue #24).
    Hỗ trợ tìm kiếm, lọc theo đơn vị/chức vụ/trạng thái, tải file mẫu, xuất Excel và import Excel.
    """
    pagination_class = StandardEmployeePagination

    def get_permissions(self):
        if self.action in ["list", "retrieve", "template"]:
            permission_classes = [IsAuthenticated, require_permission("view_list_cbnv")]
        elif self.action == "export":
            permission_classes = [IsAuthenticated, require_permission("export_cbnv")]
        elif self.action == "create":
            permission_classes = [IsAuthenticated, require_permission("add_cbnv")]
        elif self.action in ["update", "partial_update"]:
            permission_classes = [IsAuthenticated, CanChangeEmployeePermission]
        elif self.action == "change_password":
            permission_classes = [IsAuthenticated, IsEmployeeAdminOnly]
        elif self.action == "destroy":
            permission_classes = [IsAuthenticated, require_permission("delete_cbnv")]
        elif self.action in ["import_excel", "import_excel_async", "import_job_status"]:
            permission_classes = [IsAuthenticated, require_permission("import_cbnv")]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        queryset = (
            Employee.objects.select_related("don_vi__khoi", "chuc_vu")
            .prefetch_related(
                "groups",
                Prefetch(
                    "assignments",
                    queryset=EmployeeAssignment.objects.select_related("don_vi__khoi", "chuc_vu").order_by("id"),
                ),
            )
            .all()
        )

        search = self.request.query_params.get("search", "").strip()
        if search:
            queryset = queryset.filter(
                Q(ho_ten__icontains=search)
                | Q(username__icontains=search)
                | Q(email__icontains=search)
                | Q(sdt__icontains=search)
            )

        for param_name in ("don_vi_id", "khoi_id", "chuc_vu_id"):
            val = self.request.query_params.get(param_name)
            if val is not None and val != "":
                try:
                    int(val)
                except ValueError:
                    raise ValidationError({"detail": "employees.messages.invalidFilterParam"})

        don_vi_id = self.request.query_params.get("don_vi_id")
        if don_vi_id:
            queryset = queryset.filter(
                Q(don_vi_id=don_vi_id) | Q(assignments__don_vi_id=don_vi_id)
            ).distinct()

        khoi_id = self.request.query_params.get("khoi_id")
        if khoi_id:
            queryset = queryset.filter(don_vi__khoi_id=khoi_id)

        chuc_vu_id = self.request.query_params.get("chuc_vu_id")
        if chuc_vu_id:
            queryset = queryset.filter(chuc_vu_id=chuc_vu_id)

        trang_thai = self.request.query_params.get("trang_thai")
        if trang_thai is not None and trang_thai != "":
            if trang_thai not in Employee.Status.values:
                raise ValidationError({"detail": "employees.messages.invalidFilterParam"})
            queryset = queryset.filter(trang_thai=trang_thai)

        is_public = self.request.query_params.get("is_public")
        if is_public is not None and is_public != "":
            queryset = queryset.filter(is_public=(is_public.lower() in ["true", "1"]))

        ordering = self.request.query_params.get("ordering")
        if ordering:
            allowed = set(SAFE_ORDERING_FIELDS)
            user = getattr(self.request, "user", None)
            if user and (user.is_superuser or user.has_perm("view_full_cbnv")):
                allowed.update({"ngay_sinh", "-ngay_sinh"})
            if ordering not in allowed:
                raise ValidationError({"detail": "employees.messages.invalidOrdering"})
            queryset = queryset.order_by(ordering)
        else:
            queryset = queryset.order_by(
                "don_vi__stt_uu_tien", "chuc_vu__display_order", "ho_ten", "id"
            )

        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        if request.query_params.get("all", "").lower() == "true":
            serializer = EmployeeSerializer(queryset, many=True, context={"request": request})
            return Response(serializer.data, status=status.HTTP_200_OK)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = EmployeeSerializer(page, many=True, context={"request": request})
            return self.get_paginated_response(serializer.data)

        serializer = EmployeeSerializer(queryset, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = EmployeeSerializer(instance, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        if not isinstance(request.data, dict):
            return Response(
                {"detail": "employees.messages.invalidDataFormat"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = EmployeeCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        employee = serializer.save()
        output_serializer = EmployeeSerializer(employee, context={"request": request})
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        if not isinstance(request.data, dict):
            return Response(
                {"detail": "employees.messages.invalidDataFormat"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        instance = self.get_object()
        user = request.user

        # Người không phải admin chỉ được sửa hồ sơ của chính mình và các trường cá nhân.
        if not user.is_superuser:
            allowed_self_fields = {"sdt", "email", "ngay_sinh"}
            disallowed_fields = set(request.data.keys()) - allowed_self_fields
            if disallowed_fields:
                return Response(
                    {"detail": "roles.messages.permissionDenied"},
                    status=status.HTTP_403_FORBIDDEN,
                )

        # Chốt nghiệp vụ khóa tài khoản / chuyển trạng thái nghỉ việc:
        new_status = request.data.get("trang_thai")
        raw_is_active = request.data.get("is_active")

        parsed_is_active = None
        if raw_is_active is not None:
            if isinstance(raw_is_active, bool):
                parsed_is_active = raw_is_active
            elif isinstance(raw_is_active, str):
                s = raw_is_active.strip().lower()
                if s in ("false", "0", "f"):
                    parsed_is_active = False
                elif s in ("true", "1", "t"):
                    parsed_is_active = True
            elif isinstance(raw_is_active, int):
                parsed_is_active = bool(raw_is_active)

        is_deactivating = (
            (new_status == Employee.Status.NGHI_VIEC)
            or (parsed_is_active is False)
        )
        if is_deactivating:
            if instance.id == user.id:
                return Response(
                    {"detail": "employees.messages.cannotDeactivateSelf"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if instance.is_superuser and not user.is_superuser:
                return Response(
                    {"detail": "employees.messages.cannotDeactivateSuperuser"},
                    status=status.HTTP_403_FORBIDDEN,
                )
            if instance.is_superuser:
                other_active = (
                    Employee.objects.filter(is_superuser=True, is_active=True)
                    .exclude(trang_thai=Employee.Status.NGHI_VIEC)
                    .exclude(id=instance.id)
                )
                if not other_active.exists():
                    return Response(
                        {"detail": "employees.messages.cannotDeactivateLastSuperuser"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

        serializer = EmployeeUpdateSerializer(
            instance, data=request.data, partial=partial, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        updated_employee = serializer.save()
        output_serializer = EmployeeSerializer(updated_employee, context={"request": request})
        return Response(output_serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="change-password")
    def change_password(self, request, pk=None):
        employee = self.get_object()
        serializer = EmployeeAdminPasswordChangeSerializer(
            data=request.data,
            context={"employee": employee},
        )
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            employee.set_password(serializer.validated_data["new_password"])
            employee.save(update_fields=["password"])
            EmployeePasswordResetAudit.objects.create(
                actor=request.user,
                target=employee,
                actor_username=request.user.get_username(),
                target_username=employee.get_username(),
                reason_code=serializer.validated_data["reason_code"],
                reason_detail=serializer.validated_data["reason_detail"],
            )
        return Response(
            {"detail": "employees.messages.passwordChangeSuccess"},
            status=status.HTTP_200_OK,
        )

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        user = request.user

        # 0. Bắt buộc xác thực mật khẩu người thực hiện trong body JSON của DELETE
        password = None
        if isinstance(request.data, dict):
            password = request.data.get("password")

        if not password or not user.check_password(str(password)):
            return Response(
                {"detail": "employees.messages.invalidPassword"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 1. Không cho phép tự xóa chính mình
        if instance.id == user.id:
            return Response(
                {"detail": "employees.messages.cannotDeleteSelf"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 2. Không cho phép người không phải superuser xóa tài khoản superuser
        if instance.is_superuser and not user.is_superuser:
            return Response(
                {"detail": "employees.messages.cannotDeleteSuperuser"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # 3. Không để mất superuser hoạt động cuối cùng
        if instance.is_superuser:
            other_active = (
                Employee.objects.filter(is_superuser=True, is_active=True)
                .exclude(trang_thai=Employee.Status.NGHI_VIEC)
                .exclude(id=instance.id)
            )
            if not other_active.exists():
                return Response(
                    {"detail": "employees.messages.cannotDeleteLastSuperuser"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        try:
            with transaction.atomic():
                instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except (ProtectedError, RestrictedError):
            return Response(
                {
                    "detail": "employees.messages.cannotDeleteProtected"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=False, methods=["get"], url_path="template")
    def template(self, request):
        """Tải tệp Excel mẫu để nhập danh sách cán bộ nhân viên."""
        buffer = generate_cbnv_template()
        response = HttpResponse(
            buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = 'attachment; filename="mau_danh_sach_cbnv.xlsx"'
        return response

    @action(detail=False, methods=["get"], url_path="export")
    def export(self, request):
        """Xuất toàn bộ danh sách cán bộ nhân viên ra tệp Excel (.xlsx)."""
        queryset = self.filter_queryset(self.get_queryset())
        buffer = export_cbnv_to_excel(queryset, request.user)
        response = HttpResponse(
            buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = 'attachment; filename="danh_sach_cbnv.xlsx"'
        return response

    @action(detail=False, methods=["post"], url_path="import", parser_classes=[MultiPartParser, FormParser])
    def import_excel(self, request):
        """
        Nhập danh sách cán bộ nhân viên từ tệp Excel (.xlsx).
        Yêu cầu quyền import_cbnv hoặc superuser (kiểm soát bởi get_permissions).
        """

        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response(
                {"detail": "employees.messages.fileRequired"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not file_obj.name.lower().endswith(".xlsx"):
            return Response(
                {"detail": "employees.messages.fileInvalidType"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if file_obj.size > _EMPLOYEE_IMPORT_MAX_BYTES:
            return Response(
                {"detail": "employees.import.fileTooLarge"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = import_cbnv_from_excel(file_obj)
        if not result["success"]:
            return Response(
                {
                    "success": False,
                    "message": "employees.messages.importHasErrors",
                    "errors": result["errors"],
                    "total_errors": len(result["errors"]),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "success": True,
                "message": "employees.messages.importSuccess",
                "created_count": result["created_count"],
            },
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=False,
        methods=["post"],
        url_path="import-async",
        parser_classes=[MultiPartParser, FormParser],
    )
    def import_excel_async(self, request):
        """Lưu yêu cầu import bền vững rồi xử lý nền, không giữ request upload chờ đọc Excel."""
        upload = request.FILES.get("file")
        if not upload:
            return Response(
                {"detail": "employees.messages.fileRequired"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not upload.name.lower().endswith(".xlsx"):
            return Response(
                {"detail": "employees.messages.fileInvalidType"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if upload.size > _EMPLOYEE_IMPORT_MAX_BYTES:
            return Response(
                {"detail": "employees.import.fileTooLarge"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        raw_idempotency_key = request.headers.get("Idempotency-Key", "").strip()
        if len(raw_idempotency_key) > 128:
            return Response(
                {"detail": "Invalid Idempotency-Key."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        idempotency_key = raw_idempotency_key or None

        if idempotency_key:
            existing_job = EmployeeImportJob.objects.filter(
                owner=request.user,
                idempotency_key=idempotency_key,
            ).first()
            if existing_job:
                existing_job = _resume_stale_employee_import_job(existing_job)
                return Response(
                    {"job_id": str(existing_job.pk), "status": existing_job.status},
                    status=status.HTTP_202_ACCEPTED,
                )

        active_job = EmployeeImportJob.objects.filter(active_key=_EMPLOYEE_IMPORT_ACTIVE_KEY).first()
        if active_job:
            _resume_stale_employee_import_job(active_job)
            return Response(
                {"detail": "employees.import.jobAlreadyRunning"},
                status=status.HTTP_409_CONFLICT,
            )

        cutoff = timezone.now() - _EMPLOYEE_IMPORT_HISTORY_TTL
        EmployeeImportJob.objects.filter(
            status__in=[EmployeeImportJob.Status.DONE, EmployeeImportJob.Status.FAILED],
            created_at__lt=cutoff,
        ).delete()

        job_id = uuid.uuid4()
        relative_path = None
        try:
            relative_path = _save_employee_import_upload(upload, job_id)
            try:
                with transaction.atomic():
                    job = EmployeeImportJob.objects.create(
                        id=job_id,
                        owner=request.user,
                        idempotency_key=idempotency_key,
                        active_key=_EMPLOYEE_IMPORT_ACTIVE_KEY,
                        file_path=relative_path,
                        status=EmployeeImportJob.Status.QUEUED,
                        phase=EmployeeImportJob.Phase.QUEUED,
                        message="employees.import.jobQueued",
                    )
            except IntegrityError:
                _employee_import_path(relative_path).unlink(missing_ok=True)
                if idempotency_key:
                    existing_job = EmployeeImportJob.objects.filter(
                        owner=request.user,
                        idempotency_key=idempotency_key,
                    ).first()
                    if existing_job:
                        existing_job = _resume_stale_employee_import_job(existing_job)
                        return Response(
                            {"job_id": str(existing_job.pk), "status": existing_job.status},
                            status=status.HTTP_202_ACCEPTED,
                        )
                return Response(
                    {"detail": "employees.import.jobAlreadyRunning"},
                    status=status.HTTP_409_CONFLICT,
                )

            _start_employee_import_worker(job.pk)
        except ValueError as exc:
            if relative_path:
                _employee_import_path(relative_path).unlink(missing_ok=True)
            detail = str(exc) if str(exc) == "employees.import.fileTooLarge" else "employees.import.uploadError"
            return Response(
                {"detail": detail},
                status=status.HTTP_400_BAD_REQUEST if detail.endswith("fileTooLarge") else status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except Exception:
            logger.exception("Unable to start CBNV Excel import job: %s", job_id)
            if relative_path:
                _employee_import_path(relative_path).unlink(missing_ok=True)
            EmployeeImportJob.objects.filter(pk=job_id).update(
                status=EmployeeImportJob.Status.FAILED,
                active_key=None,
                phase=EmployeeImportJob.Phase.FAILED,
                message="employees.import.uploadError",
                updated_at=timezone.now(),
            )
            return Response(
                {"detail": "employees.import.uploadError"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response({"job_id": str(job.pk), "status": job.status}, status=status.HTTP_202_ACCEPTED)

    @action(
        detail=False,
        methods=["get"],
        url_path=r"import-jobs/(?P<job_id>[0-9a-f-]+)",
    )
    def import_job_status(self, request, job_id=None):
        """Trả trạng thái job; chỉ người đã tạo job được đọc kết quả và lỗi theo dòng."""
        try:
            job_id = uuid.UUID(job_id)
        except (AttributeError, TypeError, ValueError):
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        job = EmployeeImportJob.objects.filter(pk=job_id, owner=request.user).first()
        if not job:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        job = _resume_stale_employee_import_job(job)
        return Response({
            "job_id": str(job.pk),
            "status": job.status,
            "phase": job.phase,
            "processed": job.processed,
            "total": job.total,
            "created_count": job.created_count,
            "errors": job.errors,
            "message": job.message,
        }, status=status.HTTP_200_OK)
