"""
API Views cho Module Văn Bản — Kiến trúc 2 Model (VanBanDen, VanBanDi).

Hỗ trợ 2 tầng ViewSets:
1. ViewSet chuyên biệt:
   - VanBanDenViewSet:  /api/documents/den/  (hoặc /api/van-ban-den/)
   - VanBanDiViewSet:   /api/documents/di/   (hoặc /api/van-ban-di/)
2. ViewSet hợp nhất (Unified Facade):
   - DocumentViewSet:   /api/documents/      (Hỗ trợ nguyên vẹn 100% frontend React và test suite)
"""

from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, NotFound
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from .filters import (
    DocumentFilter,
    VanBanDenFilter,
    VanBanDiFilter,
    ViewerFilter,
    get_filter_class_for_model,
)
from .models import (
    HieuLuc,
    LoaiVanBan,
    PhamVi,
    VanBanDen,
    VanBanDenAttachment,
    VanBanDi,
    VanBanDiAttachment,
    DocumentViewLog,
    DocumentAccessLog,
    get_document_model,
    get_attachment_model,
)
from .selectors import (
    van_ban_xem_duoc,
    la_nguoi_xem_duoc,
    log_access,
)
from .serializers import (
    DocumentCreateUpdateSerializer,
    DocumentDetailSerializer,
    DocumentListSerializer,
    DocumentViewLogSerializer,
    VanBanDenSerializer,
    VanBanDiSerializer,
)
from .services import (
    check_and_update_expired_documents,
    export_to_excel,
    generate_excel_template,
    generate_so_thu_tu,
    get_accessible_documents,
    import_from_excel,
    log_document_view,
)


def get_client_ip(request):
    """Lấy địa chỉ IP của client từ request headers."""
    if not request:
        return None
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")



# ═══════════════════════════════════════════════════════════════════
# Pagination
# ═══════════════════════════════════════════════════════════════════

class DocumentPagination(PageNumberPagination):
    """Phân trang chuẩn: 10, 20, 50 bản ghi/trang."""
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 50


# ═══════════════════════════════════════════════════════════════════
# Helper Functions cho Phân Quyền & Quan Hệ Thay Thế
# ═══════════════════════════════════════════════════════════════════

def is_admin_user(user):
    """Kiểm tra người dùng có quyền Quản trị viên (Admin) hay không."""
    if not user or not user.is_authenticated:
        return False
    if user.is_staff or user.is_superuser:
        return True
    profile = getattr(user, "profile", None)
    if profile and profile.role == "admin":
        return True
    return False


def can_edit_document(user, instance):
    """Kiểm tra quyền chỉnh sửa văn bản."""
    if not user or not user.is_authenticated:
        return False
    if is_admin_user(user):
        return True
    if instance.nguoi_tao == user:
        return True
    model_name = instance._meta.model_name
    if (
        user.has_perm(f"documents.change_{model_name}")
        or user.has_perm(f"change_{model_name}")
    ):
        return True
    return False


def can_create_document(user, loai="DEN"):
    """Kiểm tra quyền tạo văn bản (RBAC add_vanbanden, add_vanbandi)."""
    if not user or not user.is_authenticated:
        return False
    if is_admin_user(user):
        return True
    model_name = "vanbanden"
    if str(loai).upper() in ("DI", "VANBANDI"):
        model_name = "vanbandi"

    if (
        user.has_perm(f"documents.add_{model_name}")
        or user.has_perm(f"add_{model_name}")
    ):
        return True
    return False


def can_delete_document(user, instance):
    """Kiểm tra quyền xóa văn bản."""
    if not user or not user.is_authenticated:
        return False
    if is_admin_user(user):
        return True
    model_name = instance._meta.model_name
    if (
        user.has_perm(f"documents.delete_{model_name}")
        or user.has_perm("documents.delete_document")
        or user.has_perm("documents.delete_vanbanden")
    ):
        return True
    return False


from .services import (
    sync_replacement_document,
    cleanup_old_replacement_link,
    cleanup_replacement_links_on_delete,
)


def handle_attachments(document, request):
    """Lưu các file đính kèm từ request.FILES vào model attachment tương ứng."""
    files = request.FILES.getlist("files")
    att_model = get_attachment_model(document)
    for f in files:
        att_model.objects.create(
            document=document,
            file=f,
            name=f.name,
            file_size=f.size,
            created_user=request.user if request.user.is_authenticated else None,
        )


# ═══════════════════════════════════════════════════════════════════
# Document ViewSet — Unified Facade Endpoint (/api/documents/)
# ═══════════════════════════════════════════════════════════════════

class DocumentViewSet(viewsets.ViewSet):
    """
    API endpoint hợp nhất quản lý Văn bản (Đến / Đi).
    Đảm bảo 100% tương thích ngược với React frontend và các unit tests.
    """

    permission_classes = [permissions.IsAuthenticated]
    pagination_class = DocumentPagination
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def _get_active_model(self):
        loai = self.request.query_params.get("loai") or self.request.query_params.get("type", "DEN")
        return get_document_model(loai)

    def _get_queryset_for_model(self, model):
        check_and_update_expired_documents()
        doc_type = getattr(model, "document_kind", "vanbanden")
        return van_ban_xem_duoc(self.request.user, doc_type)

    def _get_object_across_models(self, pk, record_log=True, action_type="XEM", tep_id=None):
        loai = self.request.query_params.get("loai") or self.request.query_params.get("type")
        found_doc = None
        if loai:
            model = get_document_model(loai)
            found_doc = model.objects.filter(pk=pk).first()

        if not found_doc:
            for model in (VanBanDen, VanBanDi):
                obj = model.objects.filter(pk=pk).first()
                if obj:
                    found_doc = obj
                    break

        if not found_doc:
            raise NotFound(f"Không tìm thấy văn bản với ID {pk}.")

        user = self.request.user
        if not la_nguoi_xem_duoc(user, found_doc):
            if getattr(found_doc, "pham_vi", None) == PhamVi.HAN_CHE:
                log_access(
                    document_type=found_doc.document_kind,
                    document_id=found_doc.pk,
                    user=user,
                    hanh_dong=DocumentAccessLog.HanhDong.BI_TU_CHOI,
                    tep_id=tep_id,
                    dia_chi_ip=get_client_ip(self.request),
                )
                raise NotFound(f"Không tìm thấy văn bản với ID {pk}.")
            raise PermissionDenied("Bạn không có quyền truy cập văn bản này.")

        if record_log:
            if getattr(found_doc, "pham_vi", None) == PhamVi.HAN_CHE:
                if action_type in (DocumentAccessLog.HanhDong.XEM, DocumentAccessLog.HanhDong.TAI_FILE):
                    log_access(
                        document_type=found_doc.document_kind,
                        document_id=found_doc.pk,
                        user=user,
                        hanh_dong=action_type,
                        tep_id=tep_id,
                        dia_chi_ip=get_client_ip(self.request),
                    )
            else:
                log_document_view(found_doc, user)

        return found_doc

    def list(self, request):
        """GET /api/documents/?loai=DEN&nam=...&q=..."""
        loai_param = request.query_params.get("loai") or request.query_params.get("type")

        if loai_param:
            model = get_document_model(loai_param)
        else:
            model = VanBanDen

        qs = self._get_queryset_for_model(model)
        filter_cls = get_filter_class_for_model(model)
        doc_filter = filter_cls(request.query_params, queryset=qs)
        filtered_qs = doc_filter.qs

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(filtered_qs, request, view=self)
        if page is not None:
            serializer = DocumentListSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = DocumentListSerializer(filtered_qs, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        """GET /api/documents/{id}/"""
        instance = self._get_object_across_models(
            pk,
            record_log=True,
            action_type=DocumentAccessLog.HanhDong.XEM,
        )
        serializer = DocumentDetailSerializer(instance)
        return Response(serializer.data)

    def create(self, request):
        """POST /api/documents/"""
        serializer = DocumentCreateUpdateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        loai = serializer.validated_data.get("loai", LoaiVanBan.DEN)
        if not can_create_document(request.user, loai):
            raise PermissionDenied("Bạn không có quyền tạo văn bản mới. Vui lòng liên hệ Quản trị viên để được cấp quyền.")

        nam = serializer.validated_data.get("nam", timezone.now().year)

        extra_kwargs = {
            "nguoi_tao": request.user,
            "so_thu_tu": generate_so_thu_tu(loai, nam),
        }

        if str(loai).upper() in ("DEN", "VANBANDEN") and not serializer.validated_data.get("ngay_den"):
            extra_kwargs["ngay_den"] = timezone.now()
        elif str(loai).upper() in ("DI", "VANBANDI") and not serializer.validated_data.get("ngay_ban_hanh"):
            extra_kwargs["ngay_ban_hanh"] = timezone.now()

        instance = serializer.save(**extra_kwargs)
        handle_attachments(instance, request)

        if (
            instance.hieu_luc == HieuLuc.CON_HIEU_LUC
            and instance.ngay_het_hieu_luc
            and instance.ngay_het_hieu_luc <= timezone.now()
        ):
            instance.hieu_luc = HieuLuc.HET_HIEU_LUC
            instance.save(update_fields=["hieu_luc"])

        auto_update = request.data.get("auto_update_replaced_doc", "true")
        if str(auto_update).lower() in ("true", "1") and instance.link_thay_the:
            sync_replacement_document(instance)

        out_serializer = DocumentDetailSerializer(instance)
        return Response(out_serializer.data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, pk=None):
        """PATCH /api/documents/{id}/"""
        return self.update(request, pk, partial=True)

    def update(self, request, pk=None, partial=False):
        """PUT /api/documents/{id}/"""
        instance = self._get_object_across_models(pk, record_log=False)
        user = request.user
        is_admin = is_admin_user(user)

        if getattr(instance, "pham_vi", None) == PhamVi.HAN_CHE and not is_admin and instance.nguoi_tao != user:
            raise PermissionDenied("Chỉ người tạo mới có quyền chỉnh sửa văn bản hạn chế.")

        if not can_edit_document(user, instance):
            raise PermissionDenied("Bạn không có quyền chỉnh sửa văn bản này. Chỉ Quản trị viên, Người tạo hoặc Cán bộ được cấp quyền mới được phép chỉnh sửa.")

        old_link = (instance.link_thay_the or "").strip()
        old_so_hieu = (instance.so_hieu or "").strip()

        serializer = DocumentCreateUpdateSerializer(
            instance,
            data=request.data,
            partial=partial,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        doc = serializer.save()

        handle_attachments(doc, request)

        if (
            doc.hieu_luc == HieuLuc.CON_HIEU_LUC
            and doc.ngay_het_hieu_luc
            and doc.ngay_het_hieu_luc <= timezone.now()
        ):
            doc.hieu_luc = HieuLuc.HET_HIEU_LUC
            doc.save(update_fields=["hieu_luc"])

        new_link = (doc.link_thay_the or "").strip()
        if old_link and old_link.lower() != new_link.lower():
            cleanup_old_replacement_link(old_link, old_so_hieu)

        auto_update = request.data.get("auto_update_replaced_doc", "true")
        if str(auto_update).lower() in ("true", "1") and doc.link_thay_the:
            sync_replacement_document(doc)

        out_serializer = DocumentDetailSerializer(doc)
        return Response(out_serializer.data, status=status.HTTP_200_OK)

    def destroy(self, request, pk=None):
        """DELETE /api/documents/{id}/"""
        instance = self._get_object_across_models(pk, record_log=False)
        if getattr(instance, "pham_vi", None) == PhamVi.HAN_CHE:
            raise PermissionDenied("Văn bản hạn chế không được phép xóa.")

        user = request.user
        is_admin = is_admin_user(user)

        if not can_delete_document(user, instance):
            raise PermissionDenied("Bạn không có quyền xóa văn bản này. Quyền xóa chỉ dành cho Quản trị viên (Admin) hoặc Cán bộ được phân quyền.")

        cleanup_replacement_links_on_delete(instance)
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get"], url_path=r"attachments/(?P<tep_id>[0-9]+)/download")
    def download_attachment(self, request, pk=None, tep_id=None):
        """GET /api/documents/{id}/attachments/{tep_id}/download/"""
        tep_int = int(tep_id) if tep_id and str(tep_id).isdigit() else None
        instance = self._get_object_across_models(
            pk,
            record_log=True,
            action_type=DocumentAccessLog.HanhDong.TAI_FILE,
            tep_id=tep_int,
        )
        att = instance.attachments.filter(pk=tep_int, is_deleted=False).first()
        if not att:
            raise NotFound(f"Không tìm thấy tệp đính kèm với ID {tep_id}.")
        response = HttpResponse(att.file.read(), content_type="application/octet-stream")
        response["Content-Disposition"] = f'attachment; filename="{att.name}"'
        return response

    @action(detail=True, methods=["get"], url_path=r"download/(?P<tep_id>[0-9]+)")
    def download_attachment_alias(self, request, pk=None, tep_id=None):
        return self.download_attachment(request, pk, tep_id)

    # ───────────────────────────────────────────────────────────────
    # Custom Actions
    # ───────────────────────────────────────────────────────────────

    @action(detail=True, methods=["get"], url_path="viewers")
    def viewers(self, request, pk=None):
        """GET /api/documents/{id}/viewers/"""
        instance = self._get_object_across_models(pk)
        if request.user and request.user.is_authenticated:
            log_document_view(instance, request.user)

        view_logs = DocumentViewLog.objects.filter(
            document_type=instance.document_kind,
            document_id=instance.pk,
        ).select_related("user").order_by("-viewed_at")

        viewer_filter = ViewerFilter(request.query_params, queryset=view_logs)
        filtered_logs = viewer_filter.qs

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(filtered_logs, request, view=self)
        if page is not None:
            serializer = DocumentViewLogSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = DocumentViewLogSerializer(filtered_logs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="template")
    def template(self, request):
        """GET /api/documents/template/?loai=DEN"""
        raw_loai = request.query_params.get("loai") or request.query_params.get("type", "DEN")
        loai = str(raw_loai).strip().upper()

        excel_file = generate_excel_template(loai)
        filename = f"Mau_VanBan_{loai}_{timezone.now().strftime('%Y%m%d')}.xlsx"

        response = HttpResponse(
            excel_file.read(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    @action(
        detail=False,
        methods=["post"],
        url_path="import",
        parser_classes=[MultiPartParser],
    )
    def import_excel(self, request):
        """POST /api/documents/import/"""
        file_obj = request.FILES.get("file")
        raw_loai = request.data.get("loai") or request.data.get("type", "DEN")
        loai = str(raw_loai).strip().upper()

        if not file_obj:
            return Response({"error": "Vui lòng chọn file Excel."}, status=status.HTTP_400_BAD_REQUEST)

        if not file_obj.name.endswith((".xlsx", ".xls")):
            return Response({"error": "Chỉ chấp nhận file Excel (.xlsx, .xls)."}, status=status.HTTP_400_BAD_REQUEST)

        result = import_from_excel(file_obj, loai, request.user)
        return Response(
            {
                "message": f"Import thành công {result['created']} văn bản.",
                "created": result["created"],
                "errors": result["errors"],
            },
            status=status.HTTP_201_CREATED if result["created"] > 0 else status.HTTP_400_BAD_REQUEST,
        )

    @action(
        detail=False,
        methods=["post"],
        url_path="import_excel",
        parser_classes=[MultiPartParser],
    )
    def import_excel_alias(self, request):
        return self.import_excel(request)

    @action(detail=False, methods=["get"], url_path="export")
    def export(self, request):
        """GET /api/documents/export/?loai=DEN"""
        raw_loai = request.query_params.get("loai") or request.query_params.get("type", "DEN")
        loai = str(raw_loai).strip().upper()

        model = get_document_model(loai)
        qs = self._get_queryset_for_model(model)
        filter_cls = get_filter_class_for_model(model)
        doc_filter = filter_cls(request.query_params, queryset=qs)
        filtered_qs = doc_filter.qs

        excel_file = export_to_excel(filtered_qs, loai)
        filename = f"DanhSach_VanBan_{loai}_{timezone.now().strftime('%Y%m%d_%H%M')}.xlsx"

        response = HttpResponse(
            excel_file.read(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    @action(detail=False, methods=["get"], url_path="years")
    def years(self, request):
        """GET /api/documents/years/?loai=DEN"""
        raw_loai = request.query_params.get("loai") or request.query_params.get("type", "DEN")
        model = get_document_model(raw_loai)
        qs = self._get_queryset_for_model(model)
        years = qs.values_list("nam", flat=True).distinct().order_by("-nam")
        return Response(list(years))


# ═══════════════════════════════════════════════════════════════════
# Dedicated ViewSets cho từng Model
# ═══════════════════════════════════════════════════════════════════

class VanBanDenViewSet(viewsets.ModelViewSet):
    """API ViewSet riêng biệt cho Văn bản Đến."""
    queryset = VanBanDen.objects.select_related("nguoi_tao").prefetch_related("attachments", "nguoi_nhan")
    serializer_class = VanBanDenSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = DocumentPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = VanBanDenFilter

    def get_queryset(self):
        return van_ban_xem_duoc(self.request.user, "vanbanden")

    def retrieve(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        obj = VanBanDen.objects.filter(pk=pk).first()
        if not obj:
            raise NotFound(f"Không tìm thấy văn bản với ID {pk}.")
        if not la_nguoi_xem_duoc(request.user, obj):
            if obj.pham_vi == PhamVi.HAN_CHE:
                log_access("vanbanden", obj.pk, request.user, DocumentAccessLog.HanhDong.BI_TU_CHOI, dia_chi_ip=get_client_ip(request))
                raise NotFound(f"Không tìm thấy văn bản với ID {pk}.")
            raise PermissionDenied("Bạn không có quyền xem văn bản này.")
        if obj.pham_vi == PhamVi.HAN_CHE:
            log_access("vanbanden", obj.pk, request.user, DocumentAccessLog.HanhDong.XEM, dia_chi_ip=get_client_ip(request))
        else:
            log_document_view(obj, request.user)
        serializer = self.get_serializer(obj)
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        obj = VanBanDen.objects.filter(pk=pk).first()
        if not obj:
            raise NotFound(f"Không tìm thấy văn bản với ID {pk}.")
        if not la_nguoi_xem_duoc(request.user, obj):
            if obj.pham_vi == PhamVi.HAN_CHE:
                log_access("vanbanden", obj.pk, request.user, DocumentAccessLog.HanhDong.BI_TU_CHOI, dia_chi_ip=get_client_ip(request))
                raise NotFound(f"Không tìm thấy văn bản với ID {pk}.")
            raise PermissionDenied("Bạn không có quyền xóa văn bản này.")
        if obj.pham_vi == PhamVi.HAN_CHE:
            raise PermissionDenied("Văn bản hạn chế không được phép xóa.")
        cleanup_replacement_links_on_delete(obj)
        return super().destroy(request, *args, **kwargs)

    def perform_create(self, serializer):
        nam = serializer.validated_data.get("nam", timezone.now().year)
        so_thu_tu = generate_so_thu_tu("DEN", nam)
        ngay_den = serializer.validated_data.get("ngay_den") or timezone.now()
        doc = serializer.save(nguoi_tao=self.request.user, so_thu_tu=so_thu_tu, ngay_den=ngay_den)
        handle_attachments(doc, self.request)


class VanBanDiViewSet(viewsets.ModelViewSet):
    """API ViewSet riêng biệt cho Văn bản Đi."""
    serializer_class = VanBanDiSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = DocumentPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = VanBanDiFilter

    def get_queryset(self):
        return van_ban_xem_duoc(self.request.user, "vanbandi")

    def retrieve(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        obj = VanBanDi.objects.filter(pk=pk).first()
        if not obj:
            raise NotFound(f"Không tìm thấy văn bản với ID {pk}.")
        if not la_nguoi_xem_duoc(request.user, obj):
            if obj.pham_vi == PhamVi.HAN_CHE:
                log_access("vanbandi", obj.pk, request.user, DocumentAccessLog.HanhDong.BI_TU_CHOI, dia_chi_ip=get_client_ip(request))
                raise NotFound(f"Không tìm thấy văn bản với ID {pk}.")
            raise PermissionDenied("Bạn không có quyền xem văn bản này.")
        if obj.pham_vi == PhamVi.HAN_CHE:
            log_access("vanbandi", obj.pk, request.user, DocumentAccessLog.HanhDong.XEM, dia_chi_ip=get_client_ip(request))
        else:
            log_document_view(obj, request.user)
        serializer = self.get_serializer(obj)
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        obj = VanBanDi.objects.filter(pk=pk).first()
        if not obj:
            raise NotFound(f"Không tìm thấy văn bản với ID {pk}.")
        if not la_nguoi_xem_duoc(request.user, obj):
            if obj.pham_vi == PhamVi.HAN_CHE:
                log_access("vanbandi", obj.pk, request.user, DocumentAccessLog.HanhDong.BI_TU_CHOI, dia_chi_ip=get_client_ip(request))
                raise NotFound(f"Không tìm thấy văn bản với ID {pk}.")
            raise PermissionDenied("Bạn không có quyền xóa văn bản này.")
        if obj.pham_vi == PhamVi.HAN_CHE:
            raise PermissionDenied("Văn bản hạn chế không được phép xóa.")
        cleanup_replacement_links_on_delete(obj)
        return super().destroy(request, *args, **kwargs)

    def perform_create(self, serializer):
        nam = serializer.validated_data.get("nam", timezone.now().year)
        so_thu_tu = generate_so_thu_tu("DI", nam)
        ngay_ban_hanh = serializer.validated_data.get("ngay_ban_hanh") or timezone.now()
        doc = serializer.save(nguoi_tao=self.request.user, so_thu_tu=so_thu_tu, ngay_ban_hanh=ngay_ban_hanh)
        handle_attachments(doc, self.request)
