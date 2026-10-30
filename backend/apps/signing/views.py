import base64
from collections.abc import Mapping

from django.contrib.auth import get_user_model
from django.db.models import Exists, OuterRef, Q, Subquery
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.decorators import api_view
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from . import crypto, enums, selectors, tim_kiem
from .errors import ConflictError, SigningAPIView, SigningError
from .models import (
    SigningAttempt, SigningKey, SigningNotification, SigningRequest, SigningRequestStep,
    SigningSignature,
)
from .permissions import (
    GUI_TRINH_KY, HUY_TRINH_KY, KY_TRINH_KY, QUAN_LY_QUY_TRINH, TAO_TRINH_KY, XEM_NHAT_KY,
    XEM_TRINH_KY, co_quyen, yeu_cau_quyen,
)
from .serializers import (
    DatPinSerializer, DoiPinSerializer, GiaiQuyetSerializer, GuiTrinhKySerializer, HuyTrinhKySerializer,
    KhoaDangKySerializer,
    KhoaSerializer, KySerializer, LienKetVanBanDiSerializer, MoKhoaKySerializer, QuyTrinhInputSerializer,
    QuyTrinhSerializer, ThuHoiKhoaSerializer, TrinhKyChiTietSerializer, TrinhKySerializer, TrinhKySuaSerializer,
    TrinhKyTaoSerializer, TrinhLaiSerializer,
    TinNhanInputSerializer, TinNhanSerializer, TuChoiSerializer, XacMinhSoHuuSerializer,
    XoayVongSerializer, YeuCauSuaSerializer, YeuCauSuaThreadSerializer,
)
from .services import bang_chung as bang_chung_service
from .services import hanh_dong_ky as hanh_dong_service
from .services import keys as key_service
from .services import pin as pin_service
from .services import process as process_service
from .services import thong_bao as thong_bao_service
from .services import tep_hoan_tat as tep_hoan_tat_service
from .services import trinh_ky as trinh_ky_service
from .services import yeu_cau_sua as yeu_cau_sua_service
from .storage import StorageError, get_storage
from .tich_hop import to_chuc
from .tich_hop.van_ban import id_van_ban_khop, mo_ta_nhieu_ho_so, tim_van_ban_di


@api_view(["GET"])
def ping_view(request):
    """GET /api/v1/signing/ping/ — yêu cầu đăng nhập (permission mặc định IsAuthenticated)."""
    return Response({"module": "signing", "status": "ok"})


def _ip(request):
    return request.META.get("REMOTE_ADDR") or None


# ── Quy trình ────────────────────────────────────────────────────────────────
# Phase 6b + #80 mục A (plan mục 3.1, 8): tạo, kích hoạt, ngừng, nhân bản cần manage_signing_process kèm
# phạm vi: quy trình CONG_TY do quản trị quản lý, quy trình PHONG_BAN do lãnh đạo đơn vị áp dụng hoặc
# quản trị. Xem: quản trị thấy mọi quy trình; lãnh đạo đơn vị thấy quy trình đơn vị mình; người có
# view_trinhky thấy quy trình đang hoạt động mình dùng được (CONG_TY và PHONG_BAN của đơn vị mình).


def _quy_trinh_xem_duoc(user):
    if not (co_quyen(user, XEM_TRINH_KY) or co_quyen(user, QUAN_LY_QUY_TRINH)):
        yeu_cau_quyen(user, XEM_TRINH_KY)
    return process_service.quy_trinh_xem_duoc(user).select_related("don_vi_ap_dung")


class QuyTrinhListCreateView(SigningAPIView):
    def get(self, request):
        queryset = _quy_trinh_xem_duoc(request.user).order_by("ma_quy_trinh", "-phien_ban")
        trang_thai = request.query_params.get("trang_thai", "").replace("\x00", "")
        if trang_thai:
            queryset = queryset.filter(trang_thai=trang_thai)
        return Response(QuyTrinhSerializer(queryset, many=True).data)

    def post(self, request):
        yeu_cau_quyen(request.user, QUAN_LY_QUY_TRINH)
        data = QuyTrinhInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        process_service.yeu_cau_quan_ly(request.user, data.validated_data["pham_vi"],
                                        data.validated_data.get("don_vi_ap_dung_id"))
        process = process_service.tao_quy_trinh(request.user, **data.validated_data)
        process = _quy_trinh_xem_duoc(request.user).get(pk=process.pk)
        return Response(QuyTrinhSerializer(process).data, status=status.HTTP_201_CREATED)


class QuyTrinhDetailView(SigningAPIView):
    """GET chi tiết; PUT sửa quy trình nháp (thay toàn bộ cấp ký); DELETE xóa phiên bản chưa có hồ sơ nào dùng
    (409 kèm số hồ sơ khi còn hồ sơ)."""

    def get(self, request, pk):
        process = get_object_or_404(_quy_trinh_xem_duoc(request.user), pk=pk)
        return Response(QuyTrinhSerializer(process).data)

    def _quan_ly(self, request, pk):
        yeu_cau_quyen(request.user, QUAN_LY_QUY_TRINH)
        process = get_object_or_404(_quy_trinh_xem_duoc(request.user), pk=pk)
        process_service.yeu_cau_quan_ly(request.user, process.pham_vi, process.don_vi_ap_dung_id)
        return process

    def put(self, request, pk):
        process = self._quan_ly(request, pk)
        if not isinstance(request.data, Mapping):
            raise serializers.ValidationError({"non_field_errors": ["Invalid data. Expected a dictionary."]})
        data = QuyTrinhInputSerializer(data={**request.data, "ma_quy_trinh": process.ma_quy_trinh},
                                       context={"giu_ma_cu": True})
        data.is_valid(raise_exception=True)
        process_service.yeu_cau_quan_ly(request.user, data.validated_data["pham_vi"],
                                        data.validated_data.get("don_vi_ap_dung_id"))
        process = process_service.sua_quy_trinh(process, request.user, **data.validated_data)
        return Response(QuyTrinhSerializer(_quy_trinh_xem_duoc(request.user).get(pk=process.pk)).data)

    def delete(self, request, pk):
        process_service.xoa_quy_trinh(self._quan_ly(request, pk), request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class QuyTrinhActionView(SigningAPIView):
    """POST /quy-trinh/<pk>/<action>/ với action = kich-hoat | ngung | nhan-ban."""

    actions = {
        "kich-hoat": process_service.kich_hoat,
        "ngung": process_service.ngung,
        "nhan-ban": process_service.nhan_ban,
    }
    action = None

    def post(self, request, pk):
        yeu_cau_quyen(request.user, QUAN_LY_QUY_TRINH)
        process = get_object_or_404(_quy_trinh_xem_duoc(request.user), pk=pk)
        process_service.yeu_cau_quan_ly(request.user, process.pham_vi, process.don_vi_ap_dung_id)
        result = self.actions[self.action](process, request.user)
        result = _quy_trinh_xem_duoc(request.user).get(pk=result.pk)
        code = status.HTTP_201_CREATED if self.action == "nhan-ban" else status.HTTP_200_OK
        return Response(QuyTrinhSerializer(result).data, status=code)


# ── Khóa ký ──────────────────────────────────────────────────────────────────
# Người dùng chỉ thấy và thao tác trên khóa của chính mình (khóa người khác trả 404).
# Đăng ký, xác minh, kích hoạt, xoay vòng khóa và thao tác PIN cần sign_trinhky.
# Xem danh sách, lấy challenge và thu hồi khóa của chính mình không cần quyền riêng:
# người bị gỡ quyền ký vẫn phải thu hồi được khóa của mình.


def _khoa_cua_toi(request):
    return SigningKey.objects.filter(nguoi_so_huu=request.user)


class KhoaListCreateView(SigningAPIView):
    def get(self, request):
        return Response(KhoaSerializer(_khoa_cua_toi(request).order_by("-created_at"), many=True).data)

    def post(self, request):
        yeu_cau_quyen(request.user, KY_TRINH_KY)
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
        if self.action != "thu-hoi":
            yeu_cau_quyen(request.user, KY_TRINH_KY)
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
    `doi-pin` trả thêm `manh_bi_mat_cu` (k_srv trước khi xoay vòng) để client mở bản bọc hiện có.
    """

    action = None

    def post(self, request, pk):
        yeu_cau_quyen(request.user, KY_TRINH_KY)
        key = get_object_or_404(_khoa_cua_toi(request), pk=pk)
        ip = _ip(request)
        http_status = status.HTTP_200_OK
        manh_bi_mat_cu = None
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
            unlock, manh_bi_mat_cu, manh_bi_mat = pin_service.doi_pin(
                key, request.user, data.validated_data["xac_minh_pin_cu"], data.validated_data["xac_minh_pin_moi"],
                data.validated_data["tham_so_kdf"], ip,
            )
        body = {
            "khoa": key.pk,
            "manh_bi_mat": base64.b64encode(manh_bi_mat).decode(),
            "tham_so_kdf": unlock.tham_so_kdf,
        }
        if manh_bi_mat_cu is not None:
            body["manh_bi_mat_cu"] = base64.b64encode(manh_bi_mat_cu).decode()
        response = Response(body, status=http_status)
        response["Cache-Control"] = "no-store"
        return response


# ── Hồ sơ trình ký (Phase 7, #80; plan mục 3.3, 6.1, 7.2) ────────────────────
# Xem: người tạo, người ký của hồ sơ, kiểm toán (view_signing_audit). Tạo: add_trinhky.
# Gửi, trình lại: send_trinhky + là người tạo. Hủy: người tạo, hoặc cancel_trinhky (bắt buộc lý do).
# Thao tác đổi trạng thái bắt buộc header Idempotency-Key (plan mục 7.5).

MAX_KHOA_CHONG_TRUNG = 200


def _khoa_chong_trung(request):
    khoa = request.headers.get("Idempotency-Key", "").strip()
    if not khoa or len(khoa) > MAX_KHOA_CHONG_TRUNG:
        raise SigningError(code="thieu_khoa_chong_trung",
                           detail=f"Cần header Idempotency-Key (1–{MAX_KHOA_CHONG_TRUNG} ký tự).")
    # Gắn với người gửi để khóa của hai người không trùng nhau
    return f"{request.user.pk}:{khoa}"


def _ho_so_xem_duoc(request, pk):
    return get_object_or_404(trinh_ky_service.trinh_ky_xem_duoc(request.user), pk=pk)


# Bộ lọc trạng thái của danh sách (#275 mục 5): bốn nhóm loại trừ nhau. Hồ sơ nháp, không đồng ý, đã hủy không có
# thẻ riêng, vẫn hiện ở "Tất cả".
NHANH = ("cho_ky", "qua_han", "hoan_thanh", "tra_lai")


def _dieu_kien_nhanh():
    """Điều kiện của từng thẻ lọc nhanh; cần queryset đã gắn `trang_thai_luot_cuoi` (`_gan_luot_cuoi`).
    Đang chờ ký: lượt hiện hành chờ ký, chưa quá hạn. Quá hạn: lượt hiện hành chờ ký, đã qua hạn chót hoặc có cấp
    đang ký đã qua hạn xử lý. Đã ký xong: hoàn tất. Trả lại để sửa: lượt hiện hành đang trả sửa."""
    tt, luot = enums.TrangThaiYeuCau, enums.TrangThaiLuotTrinh
    bay_gio = timezone.now()
    qua_han_cap = Exists(SigningRequestStep.objects.filter(
        luot_trinh__trinh_ky=OuterRef("pk"), trang_thai=enums.TrangThaiCapKy.DANG_KY, han_xu_ly__lt=bay_gio))
    dang_cho = Q(trang_thai=tt.CHO_KY, trang_thai_luot_cuoi=luot.CHO_KY)
    qua_han = Q(han_chot__lt=bay_gio) | qua_han_cap
    return {
        "cho_ky": dang_cho & ~qua_han,
        "qua_han": dang_cho & qua_han,
        "hoan_thanh": Q(trang_thai=tt.HOAN_THANH),
        "tra_lai": Q(trang_thai=tt.CHO_KY, trang_thai_luot_cuoi=luot.YEU_CAU_SUA),
    }


def _gan_luot_cuoi(queryset):
    luot_cuoi = SigningAttempt.objects.filter(trinh_ky=OuterRef("pk")).order_by("-so_luot").values("trang_thai")[:1]
    return queryset.annotate(trang_thai_luot_cuoi=Subquery(luot_cuoi))


def _ho_so_theo_hop(request):
    hop = request.query_params.get("hop", "tat_ca")
    if hop == "can_toi_ky":
        return trinh_ky_service.dang_cho_toi_ky(request.user)
    if hop == "toi_gui":
        return SigningRequest.objects.filter(create_by=request.user)
    if hop == "tat_ca":
        return trinh_ky_service.trinh_ky_xem_duoc(request.user)
    raise SigningError(code="tham_so_khong_hop_le", detail="hop phải là can_toi_ky, toi_gui hoặc tat_ca.",
                       fields={"hop": ["Giá trị không hợp lệ."]})


def _doc_khoang_ngay(tham_so):
    """Đọc khoảng ngày lọc `tu_ngay`/`den_ngay` (YYYY-MM-DD); sai định dạng hoặc `tu_ngay` > `den_ngay` thì trả 400."""
    khoang = {}
    for ten in ("tu_ngay", "den_ngay"):
        if tham_so.get(ten):
            try:
                khoang[ten] = parse_date(tham_so[ten])
            except ValueError:  # đúng dạng nhưng không có trong lịch (tháng 13, 30/02)
                khoang[ten] = None
            if khoang[ten] is None:
                raise SigningError(code="tham_so_khong_hop_le", detail=f"{ten} phải có dạng YYYY-MM-DD.",
                                   fields={ten: ["Ngày không hợp lệ."]})
    if khoang.get("tu_ngay") and khoang.get("den_ngay") and khoang["tu_ngay"] > khoang["den_ngay"]:
        raise SigningError(code="tham_so_khong_hop_le", detail="Từ ngày không được lớn hơn Đến ngày.",
                           fields={"tu_ngay": ["Từ ngày không được lớn hơn Đến ngày."]})
    return khoang


def _du_lieu_chi_tiet_trinh_ky(ho_so, request):
    return TrinhKyChiTietSerializer(ho_so, context={"request": request}).data


def tu_khoa_tim_kiem(gia_tri):
    """Từ khóa tìm kiếm: bỏ ký tự NUL (PostgreSQL không nhận trong văn bản), cắt khoảng trắng, tối đa 100 ký tự."""
    return (gia_tri or "").replace("\x00", "").strip()[:100]


def _loc_ho_so(queryset, tham_so):
    """Bộ lọc danh sách: trạng thái, quy trình (id), từ khóa (số hiệu, trích yếu văn bản trình ký — văn bản đi hoặc
    nhập tay, mã/tên quy trình, ghi chú, mã hồ sơ), khoảng ngày tạo `tu_ngay`/`den_ngay` (YYYY-MM-DD)."""
    if tham_so.get("trang_thai"):
        queryset = queryset.filter(trang_thai=tham_so["trang_thai"].replace("\x00", ""))
    if tham_so.get("nhanh"):
        if tham_so["nhanh"] not in NHANH:
            raise SigningError(code="tham_so_khong_hop_le", detail=f"nhanh phải là một trong {', '.join(NHANH)}.",
                               fields={"nhanh": ["Giá trị không hợp lệ."]})
        queryset = _gan_luot_cuoi(SigningRequest.objects.filter(pk__in=queryset.values("pk"))).filter(
            _dieu_kien_nhanh()[tham_so["nhanh"]])
    if tham_so.get("quy_trinh"):
        if not tham_so["quy_trinh"].isdigit():
            raise SigningError(code="tham_so_khong_hop_le", detail="quy_trinh phải là số.",
                               fields={"quy_trinh": ["Giá trị không hợp lệ."]})
        queryset = queryset.filter(quy_trinh_id=int(tham_so["quy_trinh"]))
    tu_khoa = tu_khoa_tim_kiem(tham_so.get("q"))
    if tu_khoa:
        cot = ("quy_trinh__ten_quy_trinh", "quy_trinh__ma_quy_trinh", "ghi_chu", "so_hieu_van_ban", "trich_yeu_van_ban")
        dieu_kien = Q(van_ban_id__in=id_van_ban_khop(tu_khoa)) | tim_kiem.khop_khong_dau(tu_khoa, *cot)
        if tu_khoa.lstrip("#").isdigit():
            dieu_kien |= Q(pk=int(tu_khoa.lstrip("#")))
        queryset = tim_kiem.chu_thich(queryset, *cot).filter(dieu_kien)
    khoang = _doc_khoang_ngay(tham_so)
    if khoang.get("tu_ngay"):
        queryset = queryset.filter(created_at__date__gte=khoang["tu_ngay"])
    if khoang.get("den_ngay"):
        queryset = queryset.filter(created_at__date__lte=khoang["den_ngay"])
    return queryset


class TrangHoSo(PageNumberPagination):
    """Phân trang danh sách hồ sơ theo cách các module khác đang dùng: `page`, `page_size` (mặc định 10, tối đa 100);
    trả {count, next, previous, results}."""

    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class TrinhKyListCreateView(SigningAPIView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        queryset = _loc_ho_so(_ho_so_theo_hop(request), request.query_params)
        queryset = queryset.select_related("quy_trinh").order_by("-created_at", "-pk")
        trang = TrangHoSo()
        ho_so = trang.paginate_queryset(queryset, request, view=self)
        return trang.get_paginated_response(TrinhKySerializer(ho_so, many=True).data)

    def post(self, request):
        yeu_cau_quyen(request.user, TAO_TRINH_KY)
        data = TrinhKyTaoSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        ho_so = trinh_ky_service.tao_nhap(request.user, dia_chi_ip=_ip(request), **data.validated_data)
        return Response(_du_lieu_chi_tiet_trinh_ky(ho_so, request), status=status.HTTP_201_CREATED)


class TrinhKyDetailView(SigningAPIView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request, pk):
        return Response(_du_lieu_chi_tiet_trinh_ky(_ho_so_xem_duoc(request, pk), request))

    def patch(self, request, pk):
        ho_so = _ho_so_xem_duoc(request, pk)
        data = TrinhKySuaSerializer(data=request.data, partial=True)
        data.is_valid(raise_exception=True)
        ho_so = trinh_ky_service.cap_nhat_nhap(ho_so, request.user, dia_chi_ip=_ip(request), **data.validated_data)
        return Response(_du_lieu_chi_tiet_trinh_ky(ho_so, request))


class TrinhKyLienKetVanBanDiView(SigningAPIView):
    """Liên kết hồ sơ hoàn tất với bản ghi văn bản đi đã đăng ký."""

    def post(self, request, pk):
        ho_so = _ho_so_xem_duoc(request, pk)
        data = LienKetVanBanDiSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        ho_so = trinh_ky_service.lien_ket_van_ban_di(
            ho_so, request.user, dia_chi_ip=_ip(request), **data.validated_data,
        )
        return Response(_du_lieu_chi_tiet_trinh_ky(ho_so, request))


class TrinhKyActionView(SigningAPIView):
    """POST /trinh-ky/<pk>/<action>/ với action = gui | huy | trinh-lai."""

    action = None

    def post(self, request, pk):
        ho_so = _ho_so_xem_duoc(request, pk)
        khoa = _khoa_chong_trung(request)
        ip = _ip(request)
        if self.action == "gui":
            yeu_cau_quyen(request.user, GUI_TRINH_KY)
            data = GuiTrinhKySerializer(data=request.data)
            data.is_valid(raise_exception=True)
            ket_qua = trinh_ky_service.gui(ho_so, request.user, khoa_chong_trung=khoa, dia_chi_ip=ip,
                                           chon_nguoi_ky=data.validated_data["chon_nguoi_ky"],
                                           vi_tri_ky=data.validated_data["vi_tri_ky"])
            code = status.HTTP_200_OK
        elif self.action == "huy":
            data = HuyTrinhKySerializer(data=request.data)
            data.is_valid(raise_exception=True)
            ket_qua = trinh_ky_service.huy(ho_so, request.user, khoa_chong_trung=khoa, dia_chi_ip=ip,
                                           ly_do=data.validated_data["ly_do"])
            code = status.HTTP_200_OK
        else:  # trinh-lai
            yeu_cau_quyen(request.user, GUI_TRINH_KY)
            data = TrinhLaiSerializer(data=request.data)
            data.is_valid(raise_exception=True)
            ket_qua = trinh_ky_service.trinh_lai(ho_so, request.user, khoa_chong_trung=khoa, dia_chi_ip=ip,
                                                 han_chot=data.validated_data.get("han_chot"))
            code = status.HTTP_201_CREATED
        return Response(_du_lieu_chi_tiet_trinh_ky(ket_qua, request), status=code)


class TrinhKyTepView(SigningAPIView):
    """
    GET /trinh-ky/<pk>/tep/: tệp của lượt trình hiện hành (hoặc dự thảo khi còn nháp), kiểm quyền xem.
    `?luot=<id>`: tệp của một lượt trình cụ thể của hồ sơ (trang tài liệu: mọi phiên bản đã trình).
    """

    def get(self, request, pk):
        ho_so = _ho_so_xem_duoc(request, pk)
        luot_id = request.query_params.get("luot")
        if luot_id:
            luot = get_object_or_404(ho_so.luot_trinh_set, pk=luot_id) if luot_id.isdigit() else None
            if luot is None:
                raise SigningError(code="tham_so_khong_hop_le", detail="luot phải là số.",
                                   fields={"luot": ["Giá trị không hợp lệ."]})
        else:
            luot = trinh_ky_service.luot_hien_hanh(ho_so)
        vi_tri = luot.vi_tri_luu_tep if luot else ho_so.vi_tri_luu_tep
        try:
            data = get_storage().read_bytes(vi_tri)
        except StorageError:
            raise SigningError(code="khong_doc_duoc_tep", detail="Không đọc được tệp của hồ sơ.",
                               status_code=status.HTTP_404_NOT_FOUND)
        response = HttpResponse(data, content_type="application/pdf")
        ten_tep = f"trinh-ky-{ho_so.pk}-luot-{luot.so_luot}.pdf" if luot else f"trinh-ky-{ho_so.pk}.pdf"
        response["Content-Disposition"] = f'inline; filename="{ten_tep}"'
        response["Cache-Control"] = "no-store"
        return response


# ── Hành động người ký (Phase 8, #80; plan mục 6.2) ─────────────────────────
# Người ký của cấp đang mở (sign_trinhky); bắt buộc Idempotency-Key.


class HanhDongKyView(SigningAPIView):
    """POST /trinh-ky/<pk>/<action>/ với action = ky | tu-choi | thu-hoi."""

    action = None

    def post(self, request, pk):
        ho_so = _ho_so_xem_duoc(request, pk)
        yeu_cau_quyen(request.user, KY_TRINH_KY)
        khoa = _khoa_chong_trung(request)
        ip = _ip(request)
        if self.action == "ky":
            data = KySerializer(data=request.data)
            data.is_valid(raise_exception=True)
            ket_qua = hanh_dong_service.ky(ho_so, request.user, khoa_chong_trung=khoa, dia_chi_ip=ip,
                                           **data.validated_data)
        elif self.action == "tu-choi":
            data = TuChoiSerializer(data=request.data)
            data.is_valid(raise_exception=True)
            ket_qua = hanh_dong_service.tu_choi(ho_so, request.user, khoa_chong_trung=khoa, dia_chi_ip=ip,
                                                ly_do_tu_choi=data.validated_data["ly_do_tu_choi"])
        else:  # thu-hoi
            ket_qua = hanh_dong_service.thu_hoi(ho_so, request.user, khoa_chong_trung=khoa, dia_chi_ip=ip)
        return Response(_du_lieu_chi_tiet_trinh_ky(ket_qua, request))


# ── Trả lại để sửa (lõi Phase 9, #80; plan mục 3.3 "Nhánh 2") ───────────────


class YeuCauSuaView(SigningAPIView):
    """POST /trinh-ky/<pk>/yeu-cau-sua/: người ký đang được mở trả lại để sửa (sign_trinhky)."""

    def post(self, request, pk):
        ho_so = _ho_so_xem_duoc(request, pk)
        yeu_cau_quyen(request.user, KY_TRINH_KY)
        khoa = _khoa_chong_trung(request)
        data = YeuCauSuaSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        ket_qua = yeu_cau_sua_service.yeu_cau_sua(ho_so, request.user, khoa_chong_trung=khoa, dia_chi_ip=_ip(request),
                                                  **data.validated_data)
        return Response(_du_lieu_chi_tiet_trinh_ky(ket_qua, request))


class TraoDoiView(SigningAPIView):
    """
    GET /trinh-ky/<pk>/trao-doi/: thread yêu cầu sửa gần nhất của lượt hiện hành và tin nhắn.
    POST: gửi tin nhắn vào thread đang mở. Người tạo hồ sơ và người yêu cầu sửa trao đổi;
    kiểm toán (view_signing_audit) chỉ đọc.
    """

    def get(self, request, pk):
        ho_so = _ho_so_xem_duoc(request, pk)
        luot = trinh_ky_service.luot_hien_hanh(ho_so)
        thread = luot.yeu_cau_sua_set.order_by("-id").first() if luot else None
        if thread is None:
            return Response({"thread": None, "tin_nhan": []})
        if not (yeu_cau_sua_service.duoc_trao_doi(thread, request.user) or co_quyen(request.user, XEM_NHAT_KY)):
            raise SigningError(code="khong_co_quyen", detail="Chỉ người tạo hồ sơ và người yêu cầu sửa xem trao đổi.",
                               status_code=status.HTTP_403_FORBIDDEN)
        tin_nhan = thread.tin_nhan_set.select_related("nguoi_viet").order_by("id")
        return Response({"thread": YeuCauSuaThreadSerializer(thread).data,
                         "tin_nhan": TinNhanSerializer(tin_nhan, many=True).data})

    def post(self, request, pk):
        ho_so = _ho_so_xem_duoc(request, pk)
        data = TinNhanInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        tin = yeu_cau_sua_service.gui_tin_nhan(ho_so, request.user, noi_dung=data.validated_data["noi_dung"])
        return Response(TinNhanSerializer(tin).data, status=status.HTTP_201_CREATED)


class GiaiQuyetView(SigningAPIView):
    """POST /trinh-ky/<pk>/giai-quyet/ (multipart `tep`): người tạo tải bản sửa, tạo lượt trình mới."""

    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk):
        ho_so = _ho_so_xem_duoc(request, pk)
        yeu_cau_quyen(request.user, GUI_TRINH_KY)
        khoa = _khoa_chong_trung(request)
        data = GiaiQuyetSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        ket_qua = yeu_cau_sua_service.giai_quyet(ho_so, request.user, tep=data.validated_data["tep"],
                                                 vi_tri_ky=data.validated_data["vi_tri_ky"],
                                                 khoa_chong_trung=khoa, dia_chi_ip=_ip(request))
        return Response(_du_lieu_chi_tiet_trinh_ky(ket_qua, request))


# ── Bằng chứng tổng hợp và tệp hoàn tất (lõi Phase 10, #80 mục D) ──────────
# Người xem được hồ sơ (người tạo, người ký, kiểm toán) xem bằng chứng và tải tệp hoàn tất.


class BangChungView(SigningAPIView):
    """GET /trinh-ky/<pk>/bang-chung/: bằng chứng đã chốt của lượt hiện hành và kết quả xác minh lại."""

    def get(self, request, pk):
        ho_so = _ho_so_xem_duoc(request, pk)
        manifest = bang_chung_service.bang_chung_cua(trinh_ky_service.luot_hien_hanh(ho_so))
        if manifest is None:
            raise ConflictError(code="chua_co_bang_chung", detail="Hồ sơ chưa hoàn tất duyệt, chưa có bằng chứng.")
        return Response({
            "luot_trinh": manifest.luot_trinh_id, "phien_ban_bang_chung": manifest.phien_ban_bang_chung,
            "ma_bam_bang_chung": manifest.ma_bam_bang_chung, "thoi_diem_chot": manifest.thoi_diem_chot,
            "noi_dung_chuan_hoa": manifest.noi_dung_chuan_hoa, "xac_minh": bang_chung_service.xac_minh(manifest),
        })


class TepHoanTatView(SigningAPIView):
    """GET /trinh-ky/<pk>/tep-hoan-tat/: tệp PDF hoàn tất (bản duyệt nội bộ, chưa phát hành), kiểm mã băm."""

    def get(self, request, pk):
        ho_so = _ho_so_xem_duoc(request, pk)
        data = tep_hoan_tat_service.doc_tep_hoan_tat(trinh_ky_service.luot_hien_hanh(ho_so))
        response = HttpResponse(data, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="trinh-ky-{ho_so.pk}-ban-duyet-noi-bo.pdf"'
        response["Cache-Control"] = "no-store"
        response["X-Content-Type-Options"] = "nosniff"
        return response


class TaoLaiTepHoanTatView(SigningAPIView):
    """POST /trinh-ky/<pk>/tao-lai-tep-hoan-tat/: thử lại khi tạo tệp lỗi; người tạo hồ sơ hoặc kiểm toán."""

    def post(self, request, pk):
        ho_so = _ho_so_xem_duoc(request, pk)
        tep_hoan_tat_service.tao_lai_tep_hoan_tat(ho_so, request.user)
        return Response(_du_lieu_chi_tiet_trinh_ky(SigningRequest.objects.get(pk=ho_so.pk), request))


class AnhChuKyView(SigningAPIView):
    """GET /trinh-ky/<pk>/anh-chu-ky/<chu_ky_id>/: ảnh snapshot lúc ký để UI vẽ lớp phủ (#80 mục D)."""

    def get(self, request, pk, chu_ky_id):
        ho_so = _ho_so_xem_duoc(request, pk)
        chu_ky = get_object_or_404(SigningSignature, pk=chu_ky_id, luot_trinh__trinh_ky=ho_so)
        if not chu_ky.vi_tri_anh_chu_ky:
            raise SigningError(code="khong_co_anh_chu_ky", detail="Chữ ký không có ảnh snapshot.",
                               status_code=status.HTTP_404_NOT_FOUND)
        try:
            data = get_storage().read_bytes(chu_ky.vi_tri_anh_chu_ky)
        except StorageError:
            raise SigningError(code="khong_doc_duoc_tep", detail="Không đọc được ảnh chữ ký.",
                               status_code=status.HTTP_404_NOT_FOUND)
        if crypto.sha256_hex(data) != chu_ky.ma_bam_anh_chu_ky:
            raise ConflictError(code="anh_chu_ky_bi_thay_doi", detail="Ảnh chữ ký không khớp mã băm đã lưu.")
        response = HttpResponse(data, content_type="image/png")
        response["Cache-Control"] = "no-store"
        response["X-Content-Type-Options"] = "nosniff"
        return response


class ThongKeHoSoView(SigningAPIView):
    """
    GET /trinh-ky/thong-ke/?hop=: số hồ sơ theo từng thẻ lọc nhanh của hộp. Nhận cùng các bộ lọc khác của danh sách
    (`q`, `quy_trinh`, `tu_ngay`, `den_ngay`) để số trên thẻ khớp với danh sách đang xem; `nhanh` không áp dụng vì
    mỗi thẻ chính là một giá trị của `nhanh`.
    """

    def get(self, request):
        loc = {k: v for k, v in request.query_params.items() if k not in ("nhanh", "trang_thai")}
        # Hộp có thể là queryset distinct qua nhiều bảng: lấy tập id trước rồi đếm trên bảng hồ sơ
        queryset = _gan_luot_cuoi(SigningRequest.objects.filter(
            pk__in=_loc_ho_so(_ho_so_theo_hop(request), loc).values("pk")))
        dem = {"tat_ca": queryset.count(), **{k: queryset.filter(v).count() for k, v in _dieu_kien_nhanh().items()}}
        return Response(dem)


class TaiLieuView(SigningAPIView):
    """
    GET /tai-lieu/: trang tài liệu — mọi tệp của các hồ sơ người dùng được xem: bản dự thảo (hồ sơ chưa gửi), tệp của
    từng lượt trình, tệp hoàn tất. Lọc `q` (như danh sách hồ sơ), `loai` (DU_THAO | LUOT | HOAN_TAT), `tu_ngay`,
    `den_ngay`; mới nhất trước. Phân trang như danh sách hồ sơ (`page`, `page_size`; trả {count, next, previous,
    results}). Tải tệp qua `tep/`, `tep/?luot=`, `tep-hoan-tat/` (kiểm quyền từng hồ sơ).
    """

    LOAI = ("DU_THAO", "LUOT", "HOAN_TAT")

    def get(self, request):
        ts = request.query_params
        loai = ts.get("loai", "")
        if loai and loai not in self.LOAI:
            raise SigningError(code="tham_so_khong_hop_le", detail="loai phải là DU_THAO, LUOT hoặc HOAN_TAT.",
                               fields={"loai": ["Giá trị không hợp lệ."]})
        khoang = _doc_khoang_ngay(ts)
        xem_duoc = _loc_ho_so(trinh_ky_service.trinh_ky_xem_duoc(request.user), {"q": ts.get("q", "")})
        ho_so = list(SigningRequest.objects.filter(pk__in=xem_duoc.values("pk")).select_related("quy_trinh")
                     .prefetch_related("luot_trinh_set").order_by("-created_at")[:500])
        mo_ta = mo_ta_nhieu_ho_so(ho_so)
        tep = []
        for h in ho_so:
            chung = {"trinh_ky": h.pk, "trang_thai_ho_so": h.trang_thai, "ten_quy_trinh": h.quy_trinh.ten_quy_trinh,
                     "van_ban": mo_ta.get(h.pk, {})}
            cac_luot = sorted(h.luot_trinh_set.all(), key=lambda x: x.so_luot)
            if not cac_luot and h.vi_tri_luu_tep:
                tep.append({**chung, "loai": "DU_THAO", "luot": None, "so_luot": None, "phien_ban": h.phien_ban_van_ban,
                            "ma_bam": h.ma_bam_tai_lieu, "thoi_diem": h.created_at,
                            "ten_tep": f"trinh-ky-{h.pk}-du-thao.pdf"})
            for luot in cac_luot:
                tep.append({**chung, "loai": "LUOT", "luot": luot.pk, "so_luot": luot.so_luot,
                            "phien_ban": luot.phien_ban_van_ban, "ma_bam": luot.ma_bam_tai_lieu,
                            "thoi_diem": luot.thoi_diem_gui or luot.created_at,
                            "ten_tep": f"trinh-ky-{h.pk}-luot-{luot.so_luot}.pdf"})
                if luot.trang_thai_tep_hoan_tat == enums.TrangThaiTepHoanTat.THANH_CONG and luot.vi_tri_tep_hoan_tat:
                    tep.append({**chung, "loai": "HOAN_TAT", "luot": luot.pk, "so_luot": luot.so_luot,
                                "phien_ban": luot.phien_ban_van_ban, "ma_bam": luot.ma_bam_tep_hoan_tat,
                                "thoi_diem": luot.thoi_diem_hoan_thanh or luot.created_at,
                                "ten_tep": f"trinh-ky-{h.pk}-ban-duyet-noi-bo.pdf"})
        if loai:
            tep = [x for x in tep if x["loai"] == loai]
        if khoang.get("tu_ngay"):
            tep = [x for x in tep if timezone.localdate(x["thoi_diem"]) >= khoang["tu_ngay"]]
        if khoang.get("den_ngay"):
            tep = [x for x in tep if timezone.localdate(x["thoi_diem"]) <= khoang["den_ngay"]]
        tep.sort(key=lambda x: x["thoi_diem"], reverse=True)
        trang = TrangHoSo()
        return trang.get_paginated_response(trang.paginate_queryset(tep, request, view=self))


def gio_dia_phuong(gia_tri):
    """Cùng định dạng giờ địa phương (+07:00) như các API khác; DRF để nguyên UTC với datetime trong dict thuần."""
    return serializers.DateTimeField().to_representation(gia_tri) if gia_tri else None


class ThongBaoView(SigningAPIView):
    """GET /thong-bao/: thông báo trong ứng dụng của người dùng hiện tại, mới nhất trước. Nhận `q` (tìm theo văn bản,
    quy trình, người thực hiện, lý do — không phân biệt hoa thường/dấu), `loai_thong_bao` (một khóa của `TEN_LOAI`)
    và phân trang `page`, `page_size` (mặc định 10, tối đa 100, như danh sách hồ sơ). `han_xu_ly`: hạn của cấp ký với
    thông báo cần ký, nhắc hạn, quá hạn."""

    GIOI_HAN = 500  # đủ cho lọc/tìm kiếm/phân trang trên lịch sử gần, tránh quét toàn bộ bảng

    def get(self, request):
        ts = request.query_params
        loai_loc = ts.get("loai_thong_bao", "")
        if loai_loc and loai_loc not in thong_bao_service.TEN_LOAI:
            raise SigningError(code="tham_so_khong_hop_le", detail="loai_thong_bao không hợp lệ.",
                               fields={"loai_thong_bao": ["Giá trị không hợp lệ."]})
        ket_qua = []
        danh_sach = list(thong_bao_service.cua_toi(request.user, gioi_han=self.GIOI_HAN))
        email_keys = [
            tb.khoa_chong_gui_trung[:-7] + ":EMAIL"
            for tb in danh_sach
            if tb.khoa_chong_gui_trung.endswith(":IN_APP")
        ]
        email_map = {
            nb.khoa_chong_gui_trung: nb
            for nb in SigningNotification.objects.filter(
                khoa_chong_gui_trung__in=email_keys,
                kenh=enums.KenhThongBao.EMAIL,
            )
        }
        for tb in danh_sach:
            _, _, ten_van_ban = thong_bao_service.noi_dung(tb)
            nguoi_thao_tac, ly_do = thong_bao_service.thao_tac(tb)
            email_key = (
                tb.khoa_chong_gui_trung[:-7] + ":EMAIL"
                if tb.khoa_chong_gui_trung.endswith(":IN_APP")
                else None
            )
            email_nb = email_map.get(email_key) if email_key else None
            ket_qua.append({
                "id": tb.pk,
                "loai_thong_bao": tb.loai_thong_bao,
                "trinh_ky": tb.trinh_ky_id,
                "van_ban": ten_van_ban,
                "trang_thai_ho_so": tb.trinh_ky.trang_thai,
                "ten_quy_trinh": tb.trinh_ky.quy_trinh.ten_quy_trinh,
                "created_at": gio_dia_phuong(tb.created_at),
                "kenh_in_app": True,
                "email_da_gui": email_nb.trang_thai == enums.TrangThaiThongBao.DA_GUI if email_nb else False,
                "email_trang_thai": email_nb.trang_thai if email_nb else None,
                "email_nguoi_nhan": tb.nguoi_nhan.email or None,
                "nguoi_thao_tac": nguoi_thao_tac or None,
                "ly_do": ly_do or None,
                "han_xu_ly": gio_dia_phuong(thong_bao_service.han_xu_ly(tb)),
            })
        if loai_loc:
            ket_qua = [tb for tb in ket_qua if tb["loai_thong_bao"] == loai_loc]
        tu_khoa_goc = tu_khoa_tim_kiem(ts.get("q"))
        if tu_khoa_goc:
            tu_khoa = tim_kiem.bo_dau(tu_khoa_goc)
            ket_qua = [
                tb for tb in ket_qua
                if tu_khoa in tim_kiem.bo_dau(" ".join(filter(
                    None, (tb["van_ban"], tb["ten_quy_trinh"], tb["nguoi_thao_tac"], tb["ly_do"]))))
            ]
        trang = TrangHoSo()
        return trang.get_paginated_response(trang.paginate_queryset(ket_qua, request, view=self))


class DonViView(SigningAPIView):
    """GET /don-vi/: đơn vị chọn được làm đơn vị áp dụng quy trình PHONG_BAN (manage_signing_process)."""

    def get(self, request):
        yeu_cau_quyen(request.user, QUAN_LY_QUY_TRINH)
        return Response([{"id": d.pk, "ten": d.ten} for d in to_chuc.don_vi_quan_ly_duoc(request.user)])


class ChucVuView(SigningAPIView):
    """GET /chuc-vu/: danh sách chức vụ công khai từ phân hệ Cán bộ Nhân viên (accounts.Position) để cấu hình người ký (QUAN_LY_QUY_TRINH)."""

    def get(self, request):
        yeu_cau_quyen(request.user, QUAN_LY_QUY_TRINH)
        from accounts.models import Position
        positions = Position.objects.filter(is_public=True).order_by("display_order", "name", "id")
        return Response([
            {"id": p.pk, "ten": p.name, "name": p.name, "stt": p.display_order, "display_order": p.display_order}
            for p in positions
        ])


class NguoiDungView(SigningAPIView):
    """
    GET /nguoi-dung/?q=: tìm tài khoản đang hoạt động để chọn người ký khi cấu hình quy trình (manage_signing_process).
    Tìm theo họ tên, tên đăng nhập, chức vụ, đơn vị; không phân biệt hoa thường và dấu tiếng Việt. Chỉ trả thông tin
    hiển thị; danh bạ đầy đủ do Nhóm 7 cung cấp.
    """

    TOI_DA = 500

    def get(self, request):
        yeu_cau_quyen(request.user, QUAN_LY_QUY_TRINH)
        tu_khoa = tim_kiem.bo_dau(tu_khoa_tim_kiem(request.query_params.get("q")))
        User = get_user_model()
        lien_quan = [f for f in ("chuc_vu", "don_vi") if any(x.name == f for x in User._meta.get_fields())]
        ket_qua = []
        users = User.objects.filter(is_active=True)
        for u in users.select_related(*lien_quan).order_by("pk").iterator(chunk_size=500):
            ten, chuc_vu, don_vi = to_chuc.ten_hien_thi(u), to_chuc.ten_chuc_vu(u), to_chuc.ten_don_vi(u)
            chuc_danh = getattr(u, "chuc_danh", "") or ""
            if tu_khoa and tu_khoa not in tim_kiem.bo_dau(" ".join((ten, u.get_username(), chuc_vu, chuc_danh, don_vi))):
                continue
            ket_qua.append({"id": u.pk, "ten": ten, "ten_dang_nhap": u.get_username(), "chuc_vu": chuc_vu or None,
                            "don_vi_id": to_chuc.don_vi_cua(u), "don_vi": don_vi or None})
            if len(ket_qua) >= self.TOI_DA:
                break
        return Response(ket_qua)


class CanBoTheoChucVuView(SigningAPIView):
    """
    GET /can-bo-theo-chuc-vu/?chuc_vu=<id>[&don_vi=<id>]: cán bộ đang làm việc giữ chức vụ (trong đơn vị nếu có) để
    form và trang chi tiết quy trình hiện tên những người khớp người ký cấu hình theo chức vụ (#275 mục 8). Dữ liệu
    nhân sự của phân hệ CBNV, cùng phạm vi danh bạ `/api/accounts/staffs/`; cần quyền xem hoặc quản lý quy trình.
    Trả {"count", "results": [{id, ten, chuc_vu, don_vi_id, don_vi}]} (tối đa 50 dòng, sắp theo đơn vị, họ tên).
    """

    TOI_DA = 50

    def get(self, request):
        if not co_quyen(request.user, QUAN_LY_QUY_TRINH):
            yeu_cau_quyen(request.user, XEM_TRINH_KY)
        tham_so = {}
        for ten, bat_buoc in (("chuc_vu", True), ("don_vi", False)):
            gia_tri = request.query_params.get(ten, "").strip()
            if not gia_tri and not bat_buoc:
                continue
            if not gia_tri.isdigit():
                raise SigningError(code="tham_so_khong_hop_le", detail=f"{ten} phải là số.",
                                   fields={ten: ["Giá trị không hợp lệ."]})
            tham_so[ten] = int(gia_tri)
        queryset = to_chuc.can_bo_giu_chuc_vu(tham_so["chuc_vu"], tham_so.get("don_vi"))
        can_bo = list(queryset.select_related("chuc_vu", "don_vi")
                      .order_by("don_vi__stt_uu_tien", "ho_ten", "pk")[: self.TOI_DA])
        return Response({"count": queryset.count(), "results": [
            {"id": u.pk, "ten": to_chuc.ten_hien_thi(u), "chuc_vu": to_chuc.ten_chuc_vu(u) or None,
             "don_vi_id": to_chuc.don_vi_cua(u), "don_vi": to_chuc.ten_don_vi(u) or None} for u in can_bo]})


class DashboardView(SigningAPIView):
    """
    GET /dashboard/: số hồ sơ đang chờ người dùng hiện tại ký và 5 phiếu gần nhất liên quan tới người đó (tạo hoặc
    có tên trong luồng ký) cho Dashboard/Header (Nhóm 1). Chỉ đọc, chỉ dữ liệu của chính người dùng.
    """

    def get(self, request):
        return Response(selectors.tong_quan_dashboard(request.user))


class ToiView(SigningAPIView):
    """GET /toi/: người dùng hiện tại và quyền Trình ký để UI ẩn/hiện thao tác (server vẫn kiểm từng thao tác)."""

    def get(self, request):
        u = request.user
        don_vi = to_chuc.don_vi_cua(u)
        return Response({
            "id": u.pk, "ten": to_chuc.ten_hien_thi(u), "don_vi_id": don_vi,
            "quyen": {ma: co_quyen(u, ma) for ma in (XEM_TRINH_KY, TAO_TRINH_KY, GUI_TRINH_KY, KY_TRINH_KY,
                                                     HUY_TRINH_KY, XEM_NHAT_KY, QUAN_LY_QUY_TRINH)},
            "la_quan_tri": to_chuc.la_quan_tri(u), "la_lanh_dao_don_vi": to_chuc.la_lanh_dao_don_vi(u, don_vi),
        })


class VanBanDiView(SigningAPIView):
    """GET /van-ban-di/?q=: văn bản đi (thường, xem được) để chọn khi tạo hồ sơ (add_trinhky)."""

    def get(self, request):
        yeu_cau_quyen(request.user, TAO_TRINH_KY)
        return Response(tim_van_ban_di(request.user, tu_khoa_tim_kiem(request.query_params.get("q"))))
