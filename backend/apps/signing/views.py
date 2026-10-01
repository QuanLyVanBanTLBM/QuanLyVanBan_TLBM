import base64

from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from . import enums
from .errors import SigningAPIView, SigningError
from .models import SigningKey, SigningProcess
from .serializers import (
    DatPinSerializer, DoiPinSerializer, KhoaDangKySerializer, KhoaSerializer, MoKhoaKySerializer,
    QuyTrinhInputSerializer, QuyTrinhSerializer, ThuHoiKhoaSerializer, XacMinhSoHuuSerializer,
    XoayVongSerializer,
)
from .services import keys as key_service
from .services import pin as pin_service
from .services import process as process_service


@api_view(["GET"])
def ping_view(request):
    """GET /api/v1/signing/ping/ — yêu cầu đăng nhập (permission mặc định IsAuthenticated)."""
    return Response({"module": "signing", "status": "ok"})


def _ip(request):
    return request.META.get("REMOTE_ADDR") or None


def _khong_co_quyen():
    return SigningError(
        code="khong_co_quyen", detail="Không có quyền thao tác trên đối tượng này.",
        status_code=status.HTTP_403_FORBIDDEN,
    )


# ── Quy trình ────────────────────────────────────────────────────────────────
# Phase 5: chưa có phân quyền theo vai trò (Phase 6). Tạm thời quy trình HOAT_DONG
# xem được với mọi người dùng đã đăng nhập; quy trình khác và mọi thao tác thay đổi
# chỉ dành cho người tạo.


def _quy_trinh_xem_duoc(user):
    return SigningProcess.objects.filter(
        Q(trang_thai=enums.TrangThaiQuyTrinh.HOAT_DONG) | Q(create_by=user)
    ).prefetch_related("cap_ky_set__nguoi_ky_set")


class QuyTrinhListCreateView(SigningAPIView):
    def get(self, request):
        queryset = _quy_trinh_xem_duoc(request.user).order_by("ma_quy_trinh", "-phien_ban")
        trang_thai = request.query_params.get("trang_thai")
        if trang_thai:
            queryset = queryset.filter(trang_thai=trang_thai)
        return Response(QuyTrinhSerializer(queryset, many=True).data)

    def post(self, request):
        data = QuyTrinhInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        process = process_service.tao_quy_trinh(request.user, **data.validated_data)
        process = _quy_trinh_xem_duoc(request.user).get(pk=process.pk)
        return Response(QuyTrinhSerializer(process).data, status=status.HTTP_201_CREATED)


class QuyTrinhDetailView(SigningAPIView):
    def get(self, request, pk):
        process = get_object_or_404(_quy_trinh_xem_duoc(request.user), pk=pk)
        return Response(QuyTrinhSerializer(process).data)


class QuyTrinhActionView(SigningAPIView):
    """POST /quy-trinh/<pk>/<action>/ với action = kich-hoat | ngung | nhan-ban."""

    actions = {
        "kich-hoat": process_service.kich_hoat,
        "ngung": process_service.ngung,
        "nhan-ban": process_service.nhan_ban,
    }
    action = None

    def post(self, request, pk):
        process = get_object_or_404(_quy_trinh_xem_duoc(request.user), pk=pk)
        if process.create_by_id != request.user.pk:
            raise _khong_co_quyen()
        result = self.actions[self.action](process, request.user)
        result = _quy_trinh_xem_duoc(request.user).get(pk=result.pk)
        code = status.HTTP_201_CREATED if self.action == "nhan-ban" else status.HTTP_200_OK
        return Response(QuyTrinhSerializer(result).data, status=code)


# ── Khóa ký ──────────────────────────────────────────────────────────────────
# Người dùng chỉ thấy và thao tác trên khóa của chính mình (khóa người khác trả 404).


def _khoa_cua_toi(request):
    return SigningKey.objects.filter(nguoi_so_huu=request.user)


class KhoaListCreateView(SigningAPIView):
    def get(self, request):
        return Response(KhoaSerializer(_khoa_cua_toi(request).order_by("-created_at"), many=True).data)

    def post(self, request):
        data = KhoaDangKySerializer(data=request.data)
        data.is_valid(raise_exception=True)
        key = key_service.dang_ky(request.user, dia_chi_ip=_ip(request), **data.validated_data)
        return Response(KhoaSerializer(key).data, status=status.HTTP_201_CREATED)


class KhoaThachThucView(SigningAPIView):
    def get(self, request, pk):
        key = get_object_or_404(_khoa_cua_toi(request), pk=pk)
        return Response({"thach_thuc": key_service.thach_thuc_so_huu(key)})


class KhoaActionView(SigningAPIView):
    """POST /khoa/<pk>/<action>/ với action = xac-minh | kich-hoat | thu-hoi | xoay-vong."""

    action = None

    def post(self, request, pk):
        key = get_object_or_404(_khoa_cua_toi(request), pk=pk)
        ip = _ip(request)
        if self.action == "xac-minh":
            data = XacMinhSoHuuSerializer(data=request.data)
            data.is_valid(raise_exception=True)
            result = key_service.xac_minh_so_huu(key, request.user, data.validated_data["chu_ky_so"], ip)
        elif self.action == "kich-hoat":
            result = key_service.kich_hoat(key, request.user, ip)
        elif self.action == "thu-hoi":
            data = ThuHoiKhoaSerializer(data=request.data)
            data.is_valid(raise_exception=True)
            result = key_service.thu_hoi(key, request.user, data.validated_data["ly_do"], ip)
        else:  # xoay-vong: key là khóa cũ, body chứa khóa mới
            data = XoayVongSerializer(data=request.data)
            data.is_valid(raise_exception=True)
            khoa_moi = get_object_or_404(_khoa_cua_toi(request), pk=data.validated_data["khoa_moi"])
            result = key_service.xoay_vong(key, khoa_moi, request.user, ip)
        return Response(KhoaSerializer(result).data)


# ── PIN mở khóa ký (Phase 6, plan mục 3.4) ───────────────────────────────────


class KhoaPinView(SigningAPIView):
    """
    POST /khoa/<pk>/<action>/ với action = dat-pin | mo-khoa-ky | doi-pin.
    Trả `manh_bi_mat` (k_srv, Base64) chỉ sau khi xác minh; không trả PIN, verifier hay bản bọc.
    """

    action = None

    def post(self, request, pk):
        key = get_object_or_404(_khoa_cua_toi(request), pk=pk)
        ip = _ip(request)
        http_status = status.HTTP_200_OK
        if self.action == "dat-pin":
            data = DatPinSerializer(data=request.data)
            data.is_valid(raise_exception=True)
            unlock, manh_bi_mat = pin_service.dat_pin(
                key, request.user, data.validated_data["xac_minh_pin"], data.validated_data["tham_so_kdf"], ip,
            )
            http_status = status.HTTP_201_CREATED
        elif self.action == "mo-khoa-ky":
            data = MoKhoaKySerializer(data=request.data)
            data.is_valid(raise_exception=True)
            unlock, manh_bi_mat = pin_service.mo_khoa_ky(key, request.user, data.validated_data["xac_minh_pin"], ip)
        else:  # doi-pin
            data = DoiPinSerializer(data=request.data)
            data.is_valid(raise_exception=True)
            unlock, manh_bi_mat = pin_service.doi_pin(
                key, request.user, data.validated_data["xac_minh_pin_cu"], data.validated_data["xac_minh_pin_moi"],
                data.validated_data["tham_so_kdf"], ip,
            )
        response = Response(
            {"khoa": key.pk, "manh_bi_mat": base64.b64encode(manh_bi_mat).decode(), "tham_so_kdf": unlock.tham_so_kdf},
            status=http_status,
        )
        response["Cache-Control"] = "no-store"
        return response
