import base64

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from . import crypto
from .errors import ConflictError, SigningAPIView, SigningError
from .models import SigningKey, SigningRequest, SigningSignature
from .permissions import (
    GUI_TRINH_KY, HUY_TRINH_KY, KY_TRINH_KY, QUAN_LY_QUY_TRINH, TAO_TRINH_KY, XEM_NHAT_KY, XEM_TRINH_KY, co_quyen,
    yeu_cau_quyen,
)
from .serializers import (
    DatPinSerializer, DoiPinSerializer, GiaiQuyetSerializer, GuiTrinhKySerializer, HuyTrinhKySerializer,
    KhoaDangKySerializer,
    KhoaSerializer, KySerializer, MoKhoaKySerializer, QuyTrinhInputSerializer, QuyTrinhSerializer, ThuHoiKhoaSerializer,
    TrinhKyChiTietSerializer, TrinhKySerializer, TrinhKySuaSerializer, TrinhKyTaoSerializer, TrinhLaiSerializer,
    TinNhanInputSerializer, TinNhanSerializer, TuChoiSerializer, XacMinhSoHuuSerializer, XoayVongSerializer,
    YeuCauSuaSerializer, YeuCauSuaThreadSerializer,
)
from .services import bang_chung as bang_chung_service
from .services import hanh_dong_ky as hanh_dong_service
from .services import keys as key_service
from .services import pin as pin_service
from .services import process as process_service
from .services import tep_hoan_tat as tep_hoan_tat_service
from .services import trinh_ky as trinh_ky_service
from .services import yeu_cau_sua as yeu_cau_sua_service
from .storage import StorageError, get_storage
from .tich_hop import to_chuc
from .tich_hop.van_ban import tim_van_ban_di


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
    return process_service.quy_trinh_xem_duoc(user)


class QuyTrinhListCreateView(SigningAPIView):
    def get(self, request):
        queryset = _quy_trinh_xem_duoc(request.user).order_by("ma_quy_trinh", "-phien_ban")
        trang_thai = request.query_params.get("trang_thai")
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


class TrinhKyListCreateView(SigningAPIView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        hop = request.query_params.get("hop", "tat_ca")
        if hop == "can_toi_ky":
            queryset = trinh_ky_service.dang_cho_toi_ky(request.user)
        elif hop == "toi_gui":
            queryset = SigningRequest.objects.filter(create_by=request.user)
        elif hop == "tat_ca":
            queryset = trinh_ky_service.trinh_ky_xem_duoc(request.user)
        else:
            raise SigningError(code="tham_so_khong_hop_le", detail="hop phải là can_toi_ky, toi_gui hoặc tat_ca.",
                               fields={"hop": ["Giá trị không hợp lệ."]})
        for ten in ("trang_thai", "muc_do"):
            if request.query_params.get(ten):
                queryset = queryset.filter(**{ten: request.query_params[ten]})
        queryset = queryset.select_related("quy_trinh").order_by("-created_at")
        return Response(TrinhKySerializer(queryset, many=True).data)

    def post(self, request):
        yeu_cau_quyen(request.user, TAO_TRINH_KY)
        data = TrinhKyTaoSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        ho_so = trinh_ky_service.tao_nhap(request.user, dia_chi_ip=_ip(request), **data.validated_data)
        return Response(TrinhKyChiTietSerializer(ho_so).data, status=status.HTTP_201_CREATED)


class TrinhKyDetailView(SigningAPIView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request, pk):
        return Response(TrinhKyChiTietSerializer(_ho_so_xem_duoc(request, pk)).data)

    def patch(self, request, pk):
        ho_so = _ho_so_xem_duoc(request, pk)
        data = TrinhKySuaSerializer(data=request.data, partial=True)
        data.is_valid(raise_exception=True)
        ho_so = trinh_ky_service.cap_nhat_nhap(ho_so, request.user, dia_chi_ip=_ip(request), **data.validated_data)
        return Response(TrinhKyChiTietSerializer(ho_so).data)


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
        return Response(TrinhKyChiTietSerializer(ket_qua).data, status=code)


class TrinhKyTepView(SigningAPIView):
    """GET /trinh-ky/<pk>/tep/: tệp của lượt trình hiện hành (hoặc dự thảo khi còn nháp), kiểm quyền xem."""

    def get(self, request, pk):
        ho_so = _ho_so_xem_duoc(request, pk)
        luot = trinh_ky_service.luot_hien_hanh(ho_so)
        vi_tri = luot.vi_tri_luu_tep if luot else ho_so.vi_tri_luu_tep
        try:
            data = get_storage().read_bytes(vi_tri)
        except StorageError:
            raise SigningError(code="khong_doc_duoc_tep", detail="Không đọc được tệp của hồ sơ.",
                               status_code=status.HTTP_404_NOT_FOUND)
        response = HttpResponse(data, content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="trinh-ky-{ho_so.pk}.pdf"'
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
        return Response(TrinhKyChiTietSerializer(ket_qua).data)


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
        return Response(TrinhKyChiTietSerializer(ket_qua).data)


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
        tin_nhan = thread.tin_nhan_set.order_by("id")
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
        return Response(TrinhKyChiTietSerializer(ket_qua).data)


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
        return Response(TrinhKyChiTietSerializer(SigningRequest.objects.get(pk=ho_so.pk)).data)


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


class NguoiDungView(SigningAPIView):
    """
    GET /nguoi-dung/?q=: tìm tài khoản đang hoạt động để chọn người ký khi cấu hình quy trình (manage_signing_process).
    Chỉ trả thông tin hiển thị; danh bạ đầy đủ do Nhóm 7 cung cấp.
    """

    TOI_DA = 20

    def get(self, request):
        yeu_cau_quyen(request.user, QUAN_LY_QUY_TRINH)
        tu_khoa = request.query_params.get("q", "").strip()
        User = get_user_model()
        queryset = User.objects.filter(is_active=True)
        if tu_khoa:
            dieu_kien = Q(username__icontains=tu_khoa)
            for truong in ("ho_ten", "first_name", "last_name"):
                if any(f.name == truong for f in User._meta.get_fields()):
                    dieu_kien |= Q(**{f"{truong}__icontains": tu_khoa})
            queryset = queryset.filter(dieu_kien)
        return Response([
            {"id": u.pk, "ten": to_chuc.ten_hien_thi(u), "ten_dang_nhap": u.get_username(),
             "chuc_vu": to_chuc.ten_chuc_vu(u) or None, "don_vi_id": to_chuc.don_vi_cua(u)}
            for u in queryset.order_by("pk")[: self.TOI_DA]
        ])


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
        return Response(tim_van_ban_di(request.user, request.query_params.get("q", "").strip()[:100]))
