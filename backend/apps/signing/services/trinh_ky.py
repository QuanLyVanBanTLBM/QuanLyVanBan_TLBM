"""
Hồ sơ trình ký, lượt trình và snapshot người ký — Phase 7 (#80; plan mục 3.2, 3.3, 5.3, 6.1).

Vòng đời yêu cầu: NHAP -> CHO_KY (gui) -> HOAN_THANH | TU_CHOI | HUY; NHAP -> HUY.
TU_CHOI là kết thúc; trình lại tạo yêu cầu mới có `ho_so_goc` trỏ về yêu cầu bị từ chối.
Cấp ký mở tuần tự theo `thu_tu`; người trong cùng cấp ký song song.
"""

import io
from datetime import timedelta

from django.db import connection, transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import status

from .. import crypto, enums
from ..errors import ConflictError, SigningError
from ..models import (
    SigningAttempt, SigningAuditLog, SigningProcess, SigningRequest, SigningRequestStep, SigningRequestStepSigner,
)
from ..permissions import HUY_TRINH_KY, KY_TRINH_KY, XEM_NHAT_KY, XEM_TAT_CA, co_quyen
from ..storage import StorageError, get_storage
from ..tich_hop import to_chuc
from ..tich_hop.van_ban import kiem_tra_van_ban_trinh_ky, ma_van_ban_di_xem_duoc
from . import process as process_service
from . import thong_bao
from .audit import ghi_nhat_ky

LOAI = "signing_request"
THU_MUC_TEP = "trinh_ky"
TEP_TOI_DA = 20 * 1024 * 1024  # 20 MB
CHU_KY_PDF = b"%PDF-"


# ── Tiện ích ────────────────────────────────────────────────────────────────


def _loi(code, detail, status_code=status.HTTP_400_BAD_REQUEST, **fields):
    return SigningError(code=code, detail=detail, status_code=status_code, fields=fields or None)


def _khoa_yeu_cau(pk):
    return SigningRequest.objects.select_for_update().get(pk=pk)


def _yeu_cau_nguoi_tao(yeu_cau, nguoi):
    if yeu_cau.create_by_id != nguoi.pk:
        raise _loi("khong_co_quyen", "Chỉ người tạo hồ sơ được thực hiện thao tác này.", status.HTTP_403_FORBIDDEN)


def luot_hien_hanh(yeu_cau):
    """Lượt trình hiện hành là lượt có số lượt lớn nhất (plan mục 3.3)."""
    return yeu_cau.luot_trinh_set.order_by("-so_luot").first()


def _so_trang_hoac_loi(data):
    """(số trang, mã lỗi): lỗi khi PDF không đọc được trang hoặc có mật khẩu (tệp hoàn tất dựng từ tệp này)."""
    from pypdf import PdfReader

    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted and not reader.decrypt(""):
            return 0, "tep_pdf_co_mat_khau"
        so_trang = len(reader.pages)
        return so_trang, (None if so_trang > 0 else "tep_khong_phai_pdf")
    except Exception:  # noqa: BLE001 — pypdf ném nhiều loại lỗi với tệp hỏng
        return 0, "tep_khong_phai_pdf"


def doc_tep_pdf(tep):
    """Kiểm tệp PDF tải lên, chưa lưu. Trả (bytes, số trang)."""
    if tep is None:
        raise _loi("thieu_tep", "Cần tải lên tệp PDF dự thảo.", tep=["Bắt buộc."])
    if tep.size > TEP_TOI_DA:
        raise _loi("tep_qua_lon", "Tệp vượt quá 20 MB.", tep=["Tối đa 20 MB."])
    return kiem_tra_du_lieu_pdf(tep.read())


def kiem_tra_du_lieu_pdf(data):
    """Kiểm dung lượng và nội dung PDF đã đọc từ nguồn upload hoặc bản ghi văn bản đi."""
    if len(data) > TEP_TOI_DA:
        raise _loi("tep_qua_lon", "Tệp vượt quá 20 MB.", tep=["Tối đa 20 MB."])
    if not data.startswith(CHU_KY_PDF):
        raise _loi("tep_khong_phai_pdf", "Chỉ nhận tệp PDF.", tep=["Không phải tệp PDF."])
    so_trang, loi_pdf = _so_trang_hoac_loi(data)
    if loi_pdf == "tep_pdf_co_mat_khau":
        raise _loi(loi_pdf, "Không nhận PDF có mật khẩu.", tep=["Gỡ mật khẩu trước khi tải lên."])
    if loi_pdf:
        raise _loi(loi_pdf, "Tệp PDF hỏng hoặc không có trang.", tep=["Không đọc được tệp PDF."])
    return data, so_trang


def doc_tep_dinh_kem_pdf(nguoi, van_ban_id, tep_dinh_kem_id):
    """Đọc và kiểm PDF đính kèm của đúng văn bản đi mà người trình được phép xem."""
    from documents.models import VanBanDiAttachment

    van_ban = kiem_tra_van_ban_trinh_ky(nguoi, enums.LoaiVanBan.VAN_BAN_DI, van_ban_id)
    tep_dinh_kem = VanBanDiAttachment.objects.filter(
        document_id=van_ban.pk, pk=tep_dinh_kem_id, is_deleted=False,
    ).first()
    if tep_dinh_kem is None or not tep_dinh_kem.file:
        raise _loi("khong_tim_thay_tep_dinh_kem", "Không tìm thấy tệp đính kèm của văn bản đi.",
                   status.HTTP_404_NOT_FOUND, tep_dinh_kem_id=["Tệp không tồn tại hoặc đã bị xóa."])
    if not (tep_dinh_kem.name or "").lower().endswith(".pdf"):
        raise _loi("tep_khong_phai_pdf", "Chỉ chọn tệp PDF đính kèm.", tep_dinh_kem_id=["Tệp không phải PDF."])
    try:
        if tep_dinh_kem.file.size > TEP_TOI_DA:
            raise _loi("tep_qua_lon", "Tệp vượt quá 20 MB.", tep_dinh_kem_id=["Tối đa 20 MB."])
        with tep_dinh_kem.file.open("rb") as stored:
            data = stored.read(TEP_TOI_DA + 1)
    except (FileNotFoundError, OSError, ValueError) as exc:
        raise _loi("khong_doc_duoc_tep_dinh_kem", "Không đọc được tệp đính kèm trên máy chủ.",
                   status.HTTP_503_SERVICE_UNAVAILABLE, tep_dinh_kem_id=["Không đọc được tệp."]) from exc
    return kiem_tra_du_lieu_pdf(data)


def luu_du_lieu_pdf(data):
    """Lưu bytes PDF đã kiểm; server tự tính SHA-256 trên bytes đã lưu. Trả (vị trí, mã băm)."""
    try:
        meta = get_storage().save_bytes(data, THU_MUC_TEP, "pdf")
    except StorageError as exc:
        raise _loi("khong_luu_duoc_tep", str(exc), status.HTTP_503_SERVICE_UNAVAILABLE)
    return meta.vi_tri_luu_tep, crypto.sha256_hex(data)


def luu_tep_pdf(tep):
    return luu_du_lieu_pdf(doc_tep_pdf(tep)[0])


# ── Vị trí ký (#80 mục A, D; plan mục 3.2) ──────────────────────────────────
# Hệ tọa độ: tỷ lệ % theo khung trang (MediaBox), gốc ở góc trên-trái như khi hiển thị; khung nằm trọn trong
# trang. Vị trí được chụp vào dòng người ký của lượt trình lúc gửi (cùng với tệp và mã băm).

TRUONG_VI_TRI = ("trang_ky", "toa_do_x", "toa_do_y", "chieu_rong_khung", "chieu_cao_khung")


def so_trang_pdf(vi_tri_luu_tep):
    from pypdf import PdfReader

    try:
        return len(PdfReader(io.BytesIO(get_storage().read_bytes(vi_tri_luu_tep))).pages)
    except StorageError as exc:
        raise _loi("khong_doc_duoc_tep", str(exc), status.HTTP_503_SERVICE_UNAVAILABLE)


def kiem_tra_vi_tri_ky(vi_tri_ky, khoa_hop_le, so_trang):
    """`vi_tri_ky` đã qua serializer (phạm vi 0–100, khung trong trang); kiểm khóa và số trang của tệp."""
    loi = [{"loai": "khong_co_nguoi_ky", "khoa": k} for k in vi_tri_ky if str(k) not in khoa_hop_le]
    loi += [{"loai": "ngoai_so_trang", "khoa": k, "so_trang": so_trang}
            for k, v in vi_tri_ky.items() if v["trang_ky"] > so_trang]
    if loi:
        raise _loi("vi_tri_ky_khong_hop_le", "Vị trí ký không hợp lệ với người ký hoặc số trang của tệp.",
                   vi_tri_ky=loi)


def _kiem_tra_han_chot(han_chot):
    if han_chot is not None and han_chot <= timezone.now():
        raise _loi("han_chot_khong_hop_le", "Hạn chót phải sau thời điểm hiện tại.", han_chot=["Đã qua."])


def _kiem_tra_quy_trinh(quy_trinh, nguoi_tao):
    if quy_trinh.trang_thai != enums.TrangThaiQuyTrinh.HOAT_DONG:
        raise ConflictError(code="quy_trinh_khong_hoat_dong", detail="Chỉ trình ký theo quy trình đang hoạt động.")
    if not SigningProcess.objects.filter(pk=quy_trinh.pk).filter(process_service.dung_duoc(nguoi_tao)).exists():
        raise _loi("quy_trinh_khong_ap_dung", "Chỉ chọn quy trình công ty hoặc quy trình phòng ban của đơn vị mình.",
                   status.HTTP_403_FORBIDDEN, quy_trinh=["Quy trình không áp dụng cho đơn vị của người trình."])


# ── Phạm vi xem ─────────────────────────────────────────────────────────────


def trinh_ky_xem_duoc(nguoi):
    """
    Người tạo, người ký của bất kỳ lượt trình nào, người có quyền xem nhật ký trình ký (kiểm toán) xem được hồ sơ.
    Người có quyền xem tất cả hồ sơ trình ký (`view_all_trinhky`) xem được mọi hồ sơ nháp (chưa gắn văn bản)
    và hồ sơ gắn văn bản đi mà họ xem được theo quy tắc của module Văn bản (`van_ban_xem_duoc`), nên hồ sơ của
    văn bản hạn chế không bị lộ. Quyền này chỉ mở việc xem, không mở ký, hủy, trả lại hay sửa.
    """
    queryset = SigningRequest.objects.select_related("quy_trinh", "create_by")
    if co_quyen(nguoi, XEM_NHAT_KY):
        return queryset
    dieu_kien = Q(create_by=nguoi) | Q(luot_trinh_set__cap_ky_set__nguoi_ky_set__nguoi_ky=nguoi)
    if co_quyen(nguoi, XEM_TAT_CA):
        dieu_kien |= Q(van_ban_id__isnull=True) | Q(van_ban_id__in=ma_van_ban_di_xem_duoc(nguoi))
    return queryset.filter(dieu_kien).distinct()


def dang_cho_toi_ky(nguoi):
    """Hồ sơ có người ký là `nguoi` đã được mở, đang chờ ký, trên lượt trình đang chờ ký."""
    return SigningRequest.objects.filter(
        trang_thai=enums.TrangThaiYeuCau.CHO_KY,
        luot_trinh_set__trang_thai=enums.TrangThaiLuotTrinh.CHO_KY,
        luot_trinh_set__cap_ky_set__trang_thai=enums.TrangThaiCapKy.DANG_KY,
        luot_trinh_set__cap_ky_set__nguoi_ky_set__nguoi_ky=nguoi,
        luot_trinh_set__cap_ky_set__nguoi_ky_set__trang_thai=enums.TrangThaiNguoiKy.CHO_KY,
        luot_trinh_set__cap_ky_set__nguoi_ky_set__thoi_diem_mo__isnull=False,
    ).distinct()


# ── Quy tắc số hồ sơ theo văn bản đi ────────────────────────────────────────

TRANG_THAI_DANG_MO = (enums.TrangThaiYeuCau.NHAP, enums.TrangThaiYeuCau.CHO_KY)


def _kiem_tra_van_ban_co_the_trinh(document_type, van_ban_id, tru=None):
    """
    Mỗi văn bản chỉ có một hồ sơ đang mở và tối đa một hồ sơ hoàn tất. Hồ sơ bị từ chối hoặc hủy không chặn gửi lại.
    Khóa advisory theo văn bản (giữ đến hết transaction) để hai yêu cầu đồng thời không cùng qua.
    """
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_xact_lock(hashtext(%s), %s)", [f"signing:{document_type}", van_ban_id])
    da_hoan_tat = SigningRequest.objects.filter(
        document_type=document_type,
        van_ban_id=van_ban_id,
        trang_thai=enums.TrangThaiYeuCau.HOAN_THANH,
    )
    if tru is not None:
        da_hoan_tat = da_hoan_tat.exclude(pk=tru)
    ho_so_hoan_tat = da_hoan_tat.order_by("pk").first()
    if ho_so_hoan_tat is not None:
        raise ConflictError(
            code="van_ban_da_co_ho_so_hoan_tat",
            detail=f"Văn bản đi đã có hồ sơ trình ký #{ho_so_hoan_tat.pk} hoàn tất. Tạo văn bản đi mới nếu cần ký bản khác.",
            fields={"van_ban_id": [f"Đã có hồ sơ hoàn tất #{ho_so_hoan_tat.pk}."]},
        )
    dang_mo = SigningRequest.objects.filter(document_type=document_type, van_ban_id=van_ban_id,
                                            trang_thai__in=TRANG_THAI_DANG_MO)
    if tru is not None:
        dang_mo = dang_mo.exclude(pk=tru)
    ho_so = dang_mo.order_by("pk").first()
    if ho_so is not None:
        raise ConflictError(
            code="van_ban_da_co_ho_so_dang_mo",
            detail=f"Văn bản đã có hồ sơ trình ký #{ho_so.pk} đang mở. Hoàn tất hoặc hủy hồ sơ đó trước khi trình hồ sơ mới.",
            fields={"van_ban_id": [f"Đang có hồ sơ #{ho_so.pk}."]},
        )


# ── Chống trùng thao tác (header Idempotency-Key, plan mục 7.5) ─────────────


def _thao_tac_da_xu_ly(hanh_dong, khoa_chong_trung, yeu_cau):
    """Bản ghi nhật ký của lần xử lý trước cùng khóa trên chính hồ sơ này, hoặc None.
    Khóa đã dùng cho hồ sơ khác thì báo lỗi, không trả kết quả của hồ sơ khác."""
    da_co = SigningAuditLog.objects.filter(
        hanh_dong=hanh_dong, du_lieu_kem_theo__khoa_chong_trung=khoa_chong_trung,
    ).order_by("id").first()
    if da_co is not None and da_co.trinh_ky_id != yeu_cau.pk:
        raise ConflictError(code="khoa_chong_trung_da_dung", detail="Idempotency-Key đã dùng cho hồ sơ khác.")
    return da_co


# ── Văn bản trình ký (#275 mục 3) ───────────────────────────────────────────
# Hồ sơ dùng tệp PDF đính kèm của văn bản đi, hoặc một PDF dự thảo chưa vào sổ (số hiệu tham chiếu tùy chọn,
# trích yếu bắt buộc). Văn bản đi chỉ có tối đa một hồ sơ đang mở và một hồ sơ hoàn tất.


def _kiem_tra_van_ban_gan(nguoi, document_type, van_ban_id, tru=None):
    if van_ban_id is None:
        return
    kiem_tra_van_ban_trinh_ky(nguoi, document_type, van_ban_id)
    _kiem_tra_van_ban_co_the_trinh(document_type, van_ban_id, tru=tru)


def _kiem_tra_trich_yeu(trich_yeu):
    if not (trich_yeu or "").strip():
        raise _loi("thieu_van_ban_trinh_ky", "Chọn văn bản đi có sẵn hoặc nhập trích yếu cho PDF dự thảo chưa vào sổ.",
                   trich_yeu_van_ban=["Bắt buộc khi không gắn bản ghi văn bản đi."])


# ── Tạo, sửa nháp ───────────────────────────────────────────────────────────


@transaction.atomic
def tao_nhap(nguoi_tao, *, quy_trinh, tep=None, tep_dinh_kem_id=None, document_type=None, van_ban_id=None,
             so_hieu_van_ban="", trich_yeu_van_ban="", han_chot=None, ghi_chu="", dia_chi_ip=None):
    if van_ban_id is not None:
        if tep is not None:
            raise _loi("du_lieu_tep_khong_hop_le", "Văn bản đi có sẵn phải dùng tệp đính kèm trên bản ghi.",
                       tep=["Không tải thêm PDF khi đã chọn văn bản đi."])
        if tep_dinh_kem_id is None:
            raise _loi("thieu_tep_dinh_kem", "Chọn tệp PDF đính kèm của văn bản đi.",
                       tep_dinh_kem_id=["Bắt buộc."])
        if document_type not in (None, enums.LoaiVanBan.VAN_BAN_DI):
            kiem_tra_van_ban_trinh_ky(nguoi_tao, document_type, van_ban_id)
        document_type = enums.LoaiVanBan.VAN_BAN_DI
        so_hieu_van_ban = trich_yeu_van_ban = ""  # văn bản đi là nguồn mô tả
        data, _ = doc_tep_dinh_kem_pdf(nguoi_tao, van_ban_id, tep_dinh_kem_id)
    else:
        if tep_dinh_kem_id is not None:
            raise _loi("tep_dinh_kem_khong_hop_le", "Tệp đính kèm chỉ dùng khi chọn văn bản đi.",
                       tep_dinh_kem_id=["Không áp dụng cho PDF dự thảo chưa vào sổ."])
        document_type = None
        _kiem_tra_trich_yeu(trich_yeu_van_ban)
        data, _ = doc_tep_pdf(tep)
    if van_ban_id is not None:
        _kiem_tra_van_ban_co_the_trinh(document_type, van_ban_id)
    quy_trinh = SigningProcess.objects.get(pk=quy_trinh.pk)
    _kiem_tra_quy_trinh(quy_trinh, nguoi_tao)
    _kiem_tra_han_chot(han_chot)
    vi_tri, ma_bam = luu_du_lieu_pdf(data)
    yeu_cau = SigningRequest.objects.create(
        document_type=document_type, van_ban_id=van_ban_id, so_hieu_van_ban=so_hieu_van_ban.strip(),
        trich_yeu_van_ban=trich_yeu_van_ban.strip(), quy_trinh=quy_trinh,
        phien_ban_quy_trinh=quy_trinh.phien_ban, han_chot=han_chot, ghi_chu=ghi_chu,
        phien_ban_van_ban="1", vi_tri_luu_tep=vi_tri, ma_bam_tai_lieu=ma_bam, create_by=nguoi_tao,
    )
    ghi_nhat_ky(nguoi_tao, LOAI, yeu_cau.pk, "TAO_TRINH_KY", trinh_ky=yeu_cau,
                trang_thai_sau=yeu_cau.trang_thai, dia_chi_ip=dia_chi_ip,
                du_lieu_kem_theo={"ma_bam_tai_lieu": ma_bam, "quy_trinh": quy_trinh.pk})
    return yeu_cau


@transaction.atomic
def lien_ket_van_ban_di(yeu_cau, nguoi, *, van_ban_id, dia_chi_ip=None):
    """Liên kết một PDF đã hoàn tất duyệt nội bộ với bản ghi văn bản đi đã đăng ký."""
    yeu_cau = _khoa_yeu_cau(yeu_cau.pk)
    _yeu_cau_nguoi_tao(yeu_cau, nguoi)
    if yeu_cau.trang_thai != enums.TrangThaiYeuCau.HOAN_THANH:
        raise ConflictError(code="ho_so_chua_hoan_tat", detail="Chỉ liên kết sau khi hồ sơ hoàn tất duyệt nội bộ.")
    if yeu_cau.van_ban_id is not None:
        raise ConflictError(code="ho_so_da_lien_ket_van_ban", detail="Hồ sơ đã gắn với văn bản đi.")
    luot = luot_hien_hanh(yeu_cau)
    if (luot is None or luot.trang_thai != enums.TrangThaiLuotTrinh.HOAN_THANH
            or luot.trang_thai_tep_hoan_tat != enums.TrangThaiTepHoanTat.THANH_CONG
            or not luot.vi_tri_tep_hoan_tat or not luot.ma_bam_tep_hoan_tat):
        raise ConflictError(code="tep_hoan_tat_chua_san_sang",
                            detail="Tệp hoàn tất chưa được tạo thành công; hãy thử lại sau khi tệp sẵn sàng.")
    van_ban = kiem_tra_van_ban_trinh_ky(nguoi, enums.LoaiVanBan.VAN_BAN_DI, van_ban_id)
    _kiem_tra_van_ban_co_the_trinh(enums.LoaiVanBan.VAN_BAN_DI, van_ban.pk, tru=yeu_cau.pk)
    yeu_cau.document_type = enums.LoaiVanBan.VAN_BAN_DI
    yeu_cau.van_ban_id = van_ban.pk
    yeu_cau.so_hieu_van_ban = ""
    yeu_cau.trich_yeu_van_ban = ""
    yeu_cau.update_by = nguoi
    yeu_cau.save(update_fields=["document_type", "van_ban_id", "so_hieu_van_ban", "trich_yeu_van_ban",
                                 "update_by", "update_at"])
    so_hieu = van_ban.so_hieu or ""
    ghi_nhat_ky(nguoi, LOAI, yeu_cau.pk, "LIEN_KET_VAN_BAN_DI", trinh_ky=yeu_cau, luot_trinh=luot,
                trang_thai_truoc=yeu_cau.trang_thai, trang_thai_sau=yeu_cau.trang_thai,
                chi_tiet=f"#{van_ban.pk} · {so_hieu}", dia_chi_ip=dia_chi_ip,
                du_lieu_kem_theo={"van_ban_id": van_ban.pk, "so_hieu": so_hieu})
    return yeu_cau


@transaction.atomic
def cap_nhat_nhap(yeu_cau, nguoi, *, tep=None, dia_chi_ip=None, **thay_doi):
    """Sửa hồ sơ NHAP (hạn chót, ghi chú, tệp; số hiệu tham chiếu, trích yếu khi dùng PDF dự thảo chưa vào sổ). Thay tệp tăng
    `phien_ban_van_ban`."""
    yeu_cau = _khoa_yeu_cau(yeu_cau.pk)
    _yeu_cau_nguoi_tao(yeu_cau, nguoi)
    if yeu_cau.trang_thai != enums.TrangThaiYeuCau.NHAP:
        raise ConflictError(code="ho_so_khong_o_trang_thai_nhap", detail="Chỉ sửa được hồ sơ nháp.")
    if "han_chot" in thay_doi:
        _kiem_tra_han_chot(thay_doi["han_chot"])
    nhap_tay = {k for k in ("so_hieu_van_ban", "trich_yeu_van_ban") if k in thay_doi}
    if nhap_tay and yeu_cau.van_ban_id is not None:
        raise _loi("van_ban_da_gan", "Hồ sơ gắn văn bản đi; số hiệu, trích yếu lấy theo văn bản đi.",
                   **{k: ["Không sửa được khi đã gắn văn bản đi."] for k in nhap_tay})
    for k in nhap_tay:
        thay_doi[k] = thay_doi[k].strip()
    if "trich_yeu_van_ban" in thay_doi:
        _kiem_tra_trich_yeu(thay_doi["trich_yeu_van_ban"])
    quy_trinh_cu = None
    phien_ban_cu = yeu_cau.phien_ban_quy_trinh
    quy_trinh_moi = thay_doi.pop("quy_trinh", None)
    fields = []
    if quy_trinh_moi is not None:
        quy_trinh_cu = SigningProcess.objects.get(pk=yeu_cau.quy_trinh_id)
        if quy_trinh_cu.trang_thai == enums.TrangThaiQuyTrinh.HOAT_DONG:
            raise ConflictError(code="quy_trinh_chua_ngung",
                                detail="Chỉ chuyển bản nháp khi phiên bản quy trình hiện tại đã ngừng.")
        quy_trinh_moi = SigningProcess.objects.select_for_update().get(pk=quy_trinh_moi.pk)
        if (quy_trinh_moi.ma_quy_trinh != quy_trinh_cu.ma_quy_trinh
                or quy_trinh_moi.phien_ban <= phien_ban_cu):
            raise ConflictError(code="quy_trinh_thay_the_khong_hop_le",
                                detail="Chỉ chuyển sang phiên bản mới hơn của cùng quy trình.")
        _kiem_tra_quy_trinh(quy_trinh_moi, nguoi)
        yeu_cau.quy_trinh = quy_trinh_moi
        yeu_cau.phien_ban_quy_trinh = quy_trinh_moi.phien_ban
        fields += ["quy_trinh", "phien_ban_quy_trinh"]
    for ten, gia_tri in thay_doi.items():
        setattr(yeu_cau, ten, gia_tri)
        fields.append(ten)
    if tep is not None:
        yeu_cau.vi_tri_luu_tep, yeu_cau.ma_bam_tai_lieu = luu_tep_pdf(tep)
        yeu_cau.phien_ban_van_ban = str(int(yeu_cau.phien_ban_van_ban or "0") + 1)
        fields += ["vi_tri_luu_tep", "ma_bam_tai_lieu", "phien_ban_van_ban"]
    yeu_cau.update_by = nguoi
    yeu_cau.save(update_fields=fields + ["update_by", "update_at"])
    du_lieu_kem_theo = {"truong": sorted(set(fields))}
    if quy_trinh_cu is not None and quy_trinh_moi is not None:
        du_lieu_kem_theo["quy_trinh_cu"] = {"id": quy_trinh_cu.pk, "phien_ban": phien_ban_cu}
        du_lieu_kem_theo["quy_trinh_moi"] = {
            "id": quy_trinh_moi.pk, "phien_ban": quy_trinh_moi.phien_ban,
        }
    ghi_nhat_ky(nguoi, LOAI, yeu_cau.pk, "SUA_NHAP_TRINH_KY", trinh_ky=yeu_cau, dia_chi_ip=dia_chi_ip,
                du_lieu_kem_theo=du_lieu_kem_theo)
    return yeu_cau


# ── Snapshot người ký và mở cấp ─────────────────────────────────────────────


def _xac_dinh_nguoi_ky(yeu_cau, cau_hinh, chon_nguoi_ky):
    """Trả (tài khoản, lỗi). Lỗi là dict mô tả để gom báo một lần cho người tạo."""
    if cau_hinh.nguoi_ky_id is not None:
        nguoi = cau_hinh.nguoi_ky
        if not nguoi.is_active:
            return None, {"loai": "nguoi_ky_khong_hoat_dong", "cau_hinh": cau_hinh.pk}
        return nguoi, None
    ung_vien = to_chuc.tim_ung_vien_theo_chuc_vu(
        cau_hinh.chuc_vu_id, cau_hinh.pham_vi_chuc_vu, yeu_cau.create_by, cau_hinh.buoc_quy_trinh.don_vi_id,
    )
    if not ung_vien:
        return None, {"loai": "khong_co_ung_vien", "cau_hinh": cau_hinh.pk, "chuc_vu_id": cau_hinh.chuc_vu_id}
    if len(ung_vien) == 1:
        return ung_vien[0], None
    da_chon = chon_nguoi_ky.get(str(cau_hinh.pk))
    for nguoi in ung_vien:
        if nguoi.pk == da_chon:
            return nguoi, None
    return None, {
        "loai": "can_chon_nguoi_ky", "cau_hinh": cau_hinh.pk,
        "ung_vien": [{"id": u.pk, "ten": to_chuc.ten_hien_thi(u), "co_quyen_ky": co_quyen(u, KY_TRINH_KY)}
                     for u in ung_vien],
    }


def _han_xu_ly(cap, thoi_diem_mo, han_chot, so_cap_chua_mo):
    """`so_gio_xu_ly` của cấp nếu có; không thì chia đều thời gian còn lại đến hạn chót (plan mục 3.5)."""
    if cap.buoc_quy_trinh.so_gio_xu_ly:
        han = thoi_diem_mo + timedelta(hours=cap.buoc_quy_trinh.so_gio_xu_ly)
        return min(han, han_chot) if han_chot else han
    if han_chot is None:
        return None
    con_lai = han_chot - thoi_diem_mo
    if con_lai <= timedelta(0):
        return han_chot
    return thoi_diem_mo + con_lai / max(so_cap_chua_mo, 1)


def mo_nguoi_ky_trong_cap(cap, thoi_diem):
    """Mở mọi người ký còn chờ trong cấp đang ký. Trả danh sách người ký vừa được mở."""
    vua_mo = []
    for n in cap.nguoi_ky_set.select_for_update().order_by("pk"):
        if n.thoi_diem_mo is not None or n.trang_thai != enums.TrangThaiNguoiKy.CHO_KY:
            continue
        n.thoi_diem_mo = thoi_diem
        n.save(update_fields=["thoi_diem_mo"])
        vua_mo.append(n)
        thong_bao.can_ky(n)
    return vua_mo


def dung_cap_dang_mo(luot):
    """Lượt kết thúc (từ chối, hủy): cấp đang ký chuyển TAM_DUNG để không còn hiện "đang ký"; người ký chưa ký giữ
    CHO_KY làm lịch sử (giao diện hiển thị theo trạng thái lượt). Trả số cấp đã dừng."""
    return SigningRequestStep.objects.filter(luot_trinh=luot, trang_thai=enums.TrangThaiCapKy.DANG_KY).update(
        trang_thai=enums.TrangThaiCapKy.TAM_DUNG)


def mo_cap(luot, cap, thoi_diem, nguoi_thuc_hien):
    so_cap_chua_mo = luot.cap_ky_set.filter(trang_thai=enums.TrangThaiCapKy.CHUA_MO).count()
    cap.trang_thai = enums.TrangThaiCapKy.DANG_KY
    cap.thoi_diem_mo = thoi_diem
    cap.han_xu_ly = _han_xu_ly(cap, thoi_diem, luot.trinh_ky.han_chot, so_cap_chua_mo)
    cap.save(update_fields=["trang_thai", "thoi_diem_mo", "han_xu_ly"])
    vua_mo = mo_nguoi_ky_trong_cap(cap, thoi_diem)
    ghi_nhat_ky(nguoi_thuc_hien, "signing_attempt", luot.pk, "MO_CAP_KY", trinh_ky=luot.trinh_ky,
                luot_trinh=luot, chi_tiet=f"thu_tu={cap.thu_tu}",
                du_lieu_kem_theo={"cap": cap.pk, "nguoi_ky_mo": [n.pk for n in vua_mo]})
    return vua_mo


def tao_luot_trinh(yeu_cau, nguoi, *, chon_nguoi_ky, khoa_chong_trung, vi_tri_ky=None, luot_truoc=None):
    """
    Khóa tệp/mã băm hiện tại của hồ sơ, snapshot cấp, người ký và vị trí ký. Trả (lượt, cấp đầu); người gọi mở cấp
    đầu bằng `mo_cap` sau khi ghi nhật ký gửi để lịch sử đúng thứ tự (gửi rồi mới mở cấp).
    `vi_tri_ky`: {id người ký cấu hình: {trang_ky, toa_do_x, toa_do_y, chieu_rong_khung, chieu_cao_khung}}.
    """
    cau_hinh_cap = list(
        yeu_cau.quy_trinh.cap_ky_set.filter(dang_ap_dung=True).order_by("thu_tu").prefetch_related("nguoi_ky_set")
    )
    if not cau_hinh_cap or any(not c.nguoi_ky_set.all() for c in cau_hinh_cap):
        raise _loi("quy_trinh_thieu_nguoi_ky", "Quy trình không có cấp ký hoặc có cấp chưa có người ký.")
    vi_tri_ky = vi_tri_ky or {}
    cau_hinh_ids = {str(n.pk) for c in cau_hinh_cap for n in c.nguoi_ky_set.all()}
    kiem_tra_vi_tri_ky(vi_tri_ky, cau_hinh_ids, so_trang_pdf(yeu_cau.vi_tri_luu_tep) if vi_tri_ky else 0)
    xac_dinh, loi = [], []
    for cap in cau_hinh_cap:
        nguoi_cap = []
        for cau_hinh in sorted(cap.nguoi_ky_set.all(), key=lambda c: (c.thu_tu, c.pk)):
            tai_khoan, van_de = _xac_dinh_nguoi_ky(yeu_cau, cau_hinh, chon_nguoi_ky)
            if van_de:
                loi.append(van_de)
            elif not co_quyen(tai_khoan, KY_TRINH_KY):
                loi.append({"loai": "nguoi_ky_thieu_quyen_ky", "cau_hinh": cau_hinh.pk, "nguoi_ky": tai_khoan.pk,
                            "ten": to_chuc.ten_hien_thi(tai_khoan) or tai_khoan.get_username()})
            elif any(t.pk == tai_khoan.pk for _, t in nguoi_cap):
                loi.append({"loai": "nguoi_ky_trung_trong_cap", "cau_hinh": cau_hinh.pk, "nguoi_ky": tai_khoan.pk})
            else:
                nguoi_cap.append((cau_hinh, tai_khoan))
        xac_dinh.append((cap, nguoi_cap))
    if loi:
        thieu_quyen = [v for v in loi if v["loai"] == "nguoi_ky_thieu_quyen_ky"]
        if thieu_quyen:
            raise SigningError(
                code="nguoi_ky_thieu_quyen_ky",
                detail="Có người ký không có quyền ký trình ký; chọn người khác hoặc cấp quyền trước khi gửi.",
                fields={"nguoi_ky": loi},
            )
        can_chon = [v for v in loi if v["loai"] == "can_chon_nguoi_ky"]
        raise SigningError(
            code="can_chon_nguoi_ky" if len(can_chon) == len(loi) else "khong_xac_dinh_duoc_nguoi_ky",
            detail="Chưa xác định được người ký; xem chi tiết từng người ký cấu hình.",
            fields={"nguoi_ky": loi},
        )

    thoi_diem = timezone.now()
    so_luot = (luot_truoc.so_luot + 1) if luot_truoc else 1
    luot = SigningAttempt.objects.create(
        trinh_ky=yeu_cau, so_luot=so_luot, luot_truoc=luot_truoc, phien_ban_van_ban=yeu_cau.phien_ban_van_ban,
        vi_tri_luu_tep=yeu_cau.vi_tri_luu_tep, ma_bam_tai_lieu=yeu_cau.ma_bam_tai_lieu,
        trang_thai=enums.TrangThaiLuotTrinh.CHO_KY, khoa_chong_trung=khoa_chong_trung,
        thoi_diem_gui=thoi_diem, create_by=nguoi,
    )
    cap_dau = None
    for cap, nguoi_cap in xac_dinh:
        cap_luot = SigningRequestStep.objects.create(
            luot_trinh=luot, buoc_quy_trinh=cap, cap_ky=cap.cap_ky, ten_cap_ky=cap.ten_cap_ky, thu_tu=cap.thu_tu,
        )
        cap_dau = cap_dau or cap_luot
        for cau_hinh, tai_khoan in nguoi_cap:
            SigningRequestStepSigner.objects.create(
                buoc_ky=cap_luot, nguoi_ky=tai_khoan,
                chuc_vu_id=cau_hinh.chuc_vu_id or getattr(tai_khoan, "chuc_vu_id", None),
                ten_nguoi_ky=to_chuc.ten_hien_thi(tai_khoan) or tai_khoan.get_username(),
                ten_chuc_vu=to_chuc.ten_chuc_vu(tai_khoan) or None,
                vai_tro_ky=cau_hinh.vai_tro_ky,
                **vi_tri_ky.get(str(cau_hinh.pk), {}),
            )
    return luot, cap_dau


# ── Gửi, hủy, trình lại ─────────────────────────────────────────────────────


def _luot_da_gui(yeu_cau, khoa_chong_trung):
    # Lượt do `gui` tạo không có lượt trước; lượt do giải quyết yêu cầu sửa (Phase 9) luôn có
    da_co = SigningAttempt.objects.filter(khoa_chong_trung=khoa_chong_trung).first()
    if da_co is not None and (da_co.trinh_ky_id != yeu_cau.pk or da_co.luot_truoc_id is not None):
        raise ConflictError(code="khoa_chong_trung_da_dung", detail="Idempotency-Key đã dùng cho thao tác khác.")
    return da_co


@transaction.atomic
def gui(yeu_cau, nguoi, *, khoa_chong_trung, chon_nguoi_ky=None, vi_tri_ky=None, dia_chi_ip=None):
    if _luot_da_gui(yeu_cau, khoa_chong_trung):
        return SigningRequest.objects.get(pk=yeu_cau.pk)  # gửi lặp: trả kết quả lần trước
    yeu_cau = _khoa_yeu_cau(yeu_cau.pk)
    if _luot_da_gui(yeu_cau, khoa_chong_trung):  # lượt gửi đồng thời cùng khóa đã xử lý xong trước
        return yeu_cau
    _yeu_cau_nguoi_tao(yeu_cau, nguoi)
    if yeu_cau.trang_thai != enums.TrangThaiYeuCau.NHAP:
        raise ConflictError(code="ho_so_khong_o_trang_thai_nhap", detail="Chỉ gửi được hồ sơ nháp.")
    _kiem_tra_van_ban_gan(nguoi, yeu_cau.document_type, yeu_cau.van_ban_id, tru=yeu_cau.pk)
    _kiem_tra_quy_trinh(yeu_cau.quy_trinh, nguoi)
    _kiem_tra_han_chot(yeu_cau.han_chot)
    luot, cap_dau = tao_luot_trinh(yeu_cau, nguoi, chon_nguoi_ky=chon_nguoi_ky or {},
                                   khoa_chong_trung=khoa_chong_trung, vi_tri_ky=vi_tri_ky)
    yeu_cau.trang_thai = enums.TrangThaiYeuCau.CHO_KY
    yeu_cau.ngay_gui = luot.thoi_diem_gui
    yeu_cau.update_by = nguoi
    yeu_cau.save(update_fields=["trang_thai", "ngay_gui", "update_by", "update_at"])
    ghi_nhat_ky(nguoi, LOAI, yeu_cau.pk, "GUI_TRINH_KY", trinh_ky=yeu_cau, luot_trinh=luot,
                trang_thai_truoc=enums.TrangThaiYeuCau.NHAP, trang_thai_sau=yeu_cau.trang_thai,
                dia_chi_ip=dia_chi_ip, du_lieu_kem_theo={"khoa_chong_trung": khoa_chong_trung,
                                                       "ma_bam_tai_lieu": luot.ma_bam_tai_lieu})
    mo_cap(luot, cap_dau, luot.thoi_diem_gui, nguoi)  # sau nhật ký gửi để dòng thời gian đúng thứ tự
    return yeu_cau


@transaction.atomic
def huy(yeu_cau, nguoi, *, khoa_chong_trung, ly_do="", dia_chi_ip=None):
    """Người tạo hủy trước khi hoàn thành; quản trị (`cancel_trinhky`) hủy thay, bắt buộc lý do."""
    if _thao_tac_da_xu_ly("HUY_TRINH_KY", khoa_chong_trung, yeu_cau):
        return SigningRequest.objects.get(pk=yeu_cau.pk)
    yeu_cau = _khoa_yeu_cau(yeu_cau.pk)
    if _thao_tac_da_xu_ly("HUY_TRINH_KY", khoa_chong_trung, yeu_cau):
        return yeu_cau
    la_nguoi_tao = yeu_cau.create_by_id == nguoi.pk
    if not la_nguoi_tao:
        if not co_quyen(nguoi, HUY_TRINH_KY):
            raise _loi("khong_co_quyen", "Chỉ người tạo hoặc quản trị được hủy hồ sơ.", status.HTTP_403_FORBIDDEN)
        if not ly_do.strip():
            raise _loi("thieu_ly_do", "Quản trị hủy thay phải nêu lý do.", ly_do=["Bắt buộc."])
    if yeu_cau.trang_thai not in (enums.TrangThaiYeuCau.NHAP, enums.TrangThaiYeuCau.CHO_KY):
        raise ConflictError(code="ho_so_da_ket_thuc", detail="Hồ sơ đã kết thúc, không hủy được.")
    thoi_diem = timezone.now()
    luot = luot_hien_hanh(yeu_cau)
    if luot is not None and luot.trang_thai in (enums.TrangThaiLuotTrinh.CHO_KY, enums.TrangThaiLuotTrinh.YEU_CAU_SUA):
        luot = SigningAttempt.objects.select_for_update().get(pk=luot.pk)
        luot.trang_thai = enums.TrangThaiLuotTrinh.HUY
        luot.thoi_diem_huy = thoi_diem
        luot.update_by = nguoi
        luot.save(update_fields=["trang_thai", "thoi_diem_huy", "update_by", "update_at"])
        dung_cap_dang_mo(luot)
    truoc = yeu_cau.trang_thai
    yeu_cau.trang_thai = enums.TrangThaiYeuCau.HUY
    yeu_cau.ngay_huy = thoi_diem
    yeu_cau.ly_do_huy = ly_do
    yeu_cau.update_by = nguoi
    yeu_cau.save(update_fields=["trang_thai", "ngay_huy", "ly_do_huy", "update_by", "update_at"])
    ghi_nhat_ky(nguoi, LOAI, yeu_cau.pk, "HUY_TRINH_KY", trinh_ky=yeu_cau, luot_trinh=luot,
                trang_thai_truoc=truoc, trang_thai_sau=yeu_cau.trang_thai, chi_tiet=ly_do, dia_chi_ip=dia_chi_ip,
                du_lieu_kem_theo={"khoa_chong_trung": khoa_chong_trung, "huy_thay": not la_nguoi_tao})
    thong_bao.su_kien(yeu_cau, luot, "HUY", nguoi)
    return yeu_cau


@transaction.atomic
def trinh_lai(yeu_cau, nguoi, *, khoa_chong_trung, han_chot=None, dia_chi_ip=None):
    """
    Tạo hồ sơ NHAP mới từ hồ sơ bị từ chối (plan mục 3.3): giữ văn bản trình ký (văn bản đi hoặc nhập tay), tệp của
    lượt cuối;
    dùng phiên bản đang hoạt động của cùng mã quy trình; `ho_so_goc` trỏ về hồ sơ cũ.
    """
    da_xu_ly = _thao_tac_da_xu_ly("TRINH_LAI", khoa_chong_trung, yeu_cau)
    if da_xu_ly:
        return SigningRequest.objects.get(pk=da_xu_ly.du_lieu_kem_theo["ho_so_moi"])
    yeu_cau = _khoa_yeu_cau(yeu_cau.pk)
    da_xu_ly = _thao_tac_da_xu_ly("TRINH_LAI", khoa_chong_trung, yeu_cau)
    if da_xu_ly:
        return SigningRequest.objects.get(pk=da_xu_ly.du_lieu_kem_theo["ho_so_moi"])
    _yeu_cau_nguoi_tao(yeu_cau, nguoi)
    if yeu_cau.trang_thai != enums.TrangThaiYeuCau.TU_CHOI:
        raise ConflictError(code="chi_trinh_lai_ho_so_bi_tu_choi", detail="Chỉ trình lại hồ sơ bị từ chối.")
    _kiem_tra_van_ban_gan(nguoi, yeu_cau.document_type, yeu_cau.van_ban_id)
    quy_trinh = SigningProcess.objects.filter(
        ma_quy_trinh=yeu_cau.quy_trinh.ma_quy_trinh, trang_thai=enums.TrangThaiQuyTrinh.HOAT_DONG,
    ).first()
    if quy_trinh is None:
        raise ConflictError(code="quy_trinh_khong_hoat_dong",
                            detail="Mã quy trình của hồ sơ gốc không còn phiên bản đang hoạt động.")
    _kiem_tra_quy_trinh(quy_trinh, nguoi)
    _kiem_tra_han_chot(han_chot)
    luot = luot_hien_hanh(yeu_cau)
    moi = SigningRequest.objects.create(
        document_type=yeu_cau.document_type, van_ban_id=yeu_cau.van_ban_id,
        so_hieu_van_ban=yeu_cau.so_hieu_van_ban, trich_yeu_van_ban=yeu_cau.trich_yeu_van_ban, quy_trinh=quy_trinh,
        phien_ban_quy_trinh=quy_trinh.phien_ban, han_chot=han_chot,
        ghi_chu=yeu_cau.ghi_chu, phien_ban_van_ban=luot.phien_ban_van_ban, vi_tri_luu_tep=luot.vi_tri_luu_tep,
        ma_bam_tai_lieu=luot.ma_bam_tai_lieu, ho_so_goc=yeu_cau, create_by=nguoi,
    )
    ghi_nhat_ky(nguoi, LOAI, yeu_cau.pk, "TRINH_LAI", trinh_ky=yeu_cau, dia_chi_ip=dia_chi_ip,
                du_lieu_kem_theo={"khoa_chong_trung": khoa_chong_trung, "ho_so_moi": moi.pk})
    ghi_nhat_ky(nguoi, LOAI, moi.pk, "TAO_TRINH_KY", trinh_ky=moi, trang_thai_sau=moi.trang_thai,
                dia_chi_ip=dia_chi_ip, du_lieu_kem_theo={"ho_so_goc": yeu_cau.pk, "quy_trinh": quy_trinh.pk})
    return moi
