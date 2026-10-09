from django.db import IntegrityError, transaction
from django.db.models import Max, Q
from rest_framework import status

from .. import enums
from ..errors import ConflictError, SigningError
from ..models import SigningProcess, SigningProcessStep, SigningProcessStepSigner
from ..permissions import QUAN_LY_QUY_TRINH, XEM_TRINH_KY, co_quyen
from ..tich_hop import to_chuc
from .audit import ghi_nhat_ky

LOAI = "signing_process"
CAU_HINH_NHAC_HAN_MAC_DINH = {"truoc_han_gio": [24], "dung_han": True}


def _khoa(process_id):
    """Khóa dòng quy trình trong transaction hiện tại (không tác dụng trên SQLite)."""
    return SigningProcess.objects.select_for_update().get(pk=process_id)


def _yeu_cau_ban_nhap(process):
    if process.trang_thai != enums.TrangThaiQuyTrinh.NHAP:
        raise ConflictError(
            code="quy_trinh_khong_the_sua",
            detail="Chỉ được sửa quy trình ở trạng thái nháp; hãy nhân bản để tạo phiên bản mới.",
        )


# ── Phạm vi quy trình theo đơn vị (#80 mục A; plan mục 3.1, 8) ──────────────


def kiem_tra_pham_vi(pham_vi, don_vi_ap_dung_id):
    if pham_vi == enums.PhamViQuyTrinh.PHONG_BAN and don_vi_ap_dung_id is None:
        raise SigningError(code="quy_trinh_phong_ban_thieu_don_vi",
                           detail="Quy trình phạm vi phòng ban phải có đơn vị áp dụng.",
                           fields={"don_vi_ap_dung_id": ["Bắt buộc khi pham_vi = PHONG_BAN."]})
    if pham_vi == enums.PhamViQuyTrinh.CONG_TY and don_vi_ap_dung_id is not None:
        raise SigningError(code="quy_trinh_cong_ty_co_don_vi",
                           detail="Quy trình phạm vi công ty không gắn đơn vị áp dụng.",
                           fields={"don_vi_ap_dung_id": ["Bỏ trống khi pham_vi = CONG_TY."]})


def duoc_quan_ly(nguoi, pham_vi, don_vi_ap_dung_id):
    """CONG_TY: quản trị. PHONG_BAN: quản trị hoặc lãnh đạo của đơn vị áp dụng (có manage_signing_process)."""
    if to_chuc.la_quan_tri(nguoi):
        return True
    return pham_vi == enums.PhamViQuyTrinh.PHONG_BAN and to_chuc.la_lanh_dao_don_vi(nguoi, don_vi_ap_dung_id)


def yeu_cau_quan_ly(nguoi, pham_vi, don_vi_ap_dung_id):
    if not duoc_quan_ly(nguoi, pham_vi, don_vi_ap_dung_id):
        raise SigningError(code="khong_co_quyen", status_code=status.HTTP_403_FORBIDDEN,
                           detail="Quy trình công ty do quản trị quản lý; quy trình phòng ban do lãnh đạo đơn vị "
                                  "áp dụng hoặc quản trị quản lý.",
                           fields={"quyen": [QUAN_LY_QUY_TRINH]})


def dung_duoc(nguoi):
    """Điều kiện quy trình người dùng được chọn khi trình ký: CONG_TY hoặc PHONG_BAN của đơn vị mình."""
    don_vi = to_chuc.don_vi_cua(nguoi)
    dieu_kien = Q(pham_vi=enums.PhamViQuyTrinh.CONG_TY)
    if don_vi is not None:
        dieu_kien |= Q(pham_vi=enums.PhamViQuyTrinh.PHONG_BAN, don_vi_ap_dung_id=don_vi)
    return dieu_kien


def quy_trinh_xem_duoc(nguoi):
    """
    Quản trị thấy mọi quy trình; lãnh đạo đơn vị thấy mọi trạng thái của quy trình đơn vị mình; người có
    view_trinhky thấy quy trình đang hoạt động mình dùng được (không thấy quy trình phòng ban khác).
    """
    queryset = SigningProcess.objects.prefetch_related("cap_ky_set__nguoi_ky_set")
    if to_chuc.la_quan_tri(nguoi):
        return queryset
    dieu_kien = Q(pk__in=[])
    if co_quyen(nguoi, XEM_TRINH_KY):
        dieu_kien |= Q(trang_thai=enums.TrangThaiQuyTrinh.HOAT_DONG) & dung_duoc(nguoi)
    don_vi = to_chuc.don_vi_cua(nguoi)
    if to_chuc.la_lanh_dao_don_vi(nguoi, don_vi):
        dieu_kien |= Q(pham_vi=enums.PhamViQuyTrinh.PHONG_BAN, don_vi_ap_dung_id=don_vi)
    return queryset.filter(dieu_kien)


@transaction.atomic
def tao_quy_trinh(nguoi_tao, *, ma_quy_trinh, ten_quy_trinh, pham_vi, don_vi_ap_dung_id=None,
                  mo_ta="", cau_hinh_nhac_han=None, cap_ky=()):
    """Tạo quy trình nháp (phiên bản 1) kèm các cấp và người ký cấu hình sẵn.

    `cap_ky`: danh sách dict {cap_ky, ten_cap_ky, thu_tu, don_vi_id?, so_gio_xu_ly?, ghi_chu?,
    nguoi_ky: [{nguoi_ky?, chuc_vu_id?, vai_tro_ky?, chan_ky_chinh?, thu_tu}]}.
    """
    kiem_tra_pham_vi(pham_vi, don_vi_ap_dung_id)
    try:
        with transaction.atomic():
            process = SigningProcess.objects.create(
                ma_quy_trinh=ma_quy_trinh, ten_quy_trinh=ten_quy_trinh, mo_ta=mo_ta, pham_vi=pham_vi,
                don_vi_ap_dung_id=don_vi_ap_dung_id,
                cau_hinh_nhac_han=cau_hinh_nhac_han or CAU_HINH_NHAC_HAN_MAC_DINH,
                phien_ban=1, create_by=nguoi_tao,
            )
    except IntegrityError:
        raise ConflictError(code="quy_trinh_trung_ma", detail="Mã quy trình đã tồn tại.")
    for cap in cap_ky:
        them_cap_ky(process, nguoi_tao, **cap, _ghi_nhat_ky=False)
    ghi_nhat_ky(nguoi_tao, LOAI, process.pk, "TAO_QUY_TRINH", trang_thai_sau=process.trang_thai)
    return process


@transaction.atomic
def them_cap_ky(process, nguoi_thuc_hien, *, cap_ky, ten_cap_ky, thu_tu, nguoi_ky=(),
                don_vi_id=None, so_gio_xu_ly=None, ghi_chu="", _ghi_nhat_ky=True):
    process = _khoa(process.pk)
    _yeu_cau_ban_nhap(process)
    try:
        with transaction.atomic():
            step = SigningProcessStep.objects.create(
                quy_trinh=process, cap_ky=cap_ky, ten_cap_ky=ten_cap_ky, thu_tu=thu_tu,
                don_vi_id=don_vi_id, so_gio_xu_ly=so_gio_xu_ly, ghi_chu=ghi_chu,
            )
    except IntegrityError:
        raise ConflictError(code="cap_ky_trung_thu_tu", detail="Thứ tự cấp ký đã tồn tại trong quy trình.")
    for nk in nguoi_ky:
        them_nguoi_ky(step, nguoi_thuc_hien, **nk)
    if _ghi_nhat_ky:
        ghi_nhat_ky(nguoi_thuc_hien, LOAI, process.pk, "THEM_CAP_KY", chi_tiet=f"thu_tu={thu_tu}")
    return step


@transaction.atomic
def them_nguoi_ky(step, nguoi_thuc_hien, *, thu_tu, nguoi_ky=None, chuc_vu_id=None, pham_vi_chuc_vu=None,
                  vai_tro_ky=enums.VaiTroKy.KY_CHINH, chan_ky_chinh=True):
    process = _khoa(step.quy_trinh_id)
    _yeu_cau_ban_nhap(process)
    if (nguoi_ky is None) == (chuc_vu_id is None):
        raise SigningError(
            code="nguoi_ky_hoac_chuc_vu",
            detail="Phải nhập đúng một trong hai: người ký hoặc chức vụ ký.",
        )
    if nguoi_ky is not None:
        if pham_vi_chuc_vu:
            raise SigningError(code="pham_vi_chuc_vu_khong_ap_dung",
                               detail="Phạm vi chức vụ chỉ dùng cho người ký cấu hình theo chức vụ.",
                               fields={"pham_vi_chuc_vu": ["Bỏ trống khi chọn người ký cụ thể."]})
    else:
        pham_vi_chuc_vu = pham_vi_chuc_vu or enums.PhamViChucVu.DON_VI_NGUOI_TAO
        if pham_vi_chuc_vu == enums.PhamViChucVu.DON_VI_CO_DINH and step.don_vi_id is None:
            raise SigningError(code="cap_ky_thieu_don_vi",
                               detail="Phạm vi 'đơn vị cố định' cần cấp ký có đơn vị.",
                               fields={"pham_vi_chuc_vu": ["Cấp ký chưa có don_vi_id."]})
    return SigningProcessStepSigner.objects.create(
        buoc_quy_trinh=step, nguoi_ky=nguoi_ky, chuc_vu_id=chuc_vu_id, pham_vi_chuc_vu=pham_vi_chuc_vu,
        vai_tro_ky=vai_tro_ky, chan_ky_chinh=chan_ky_chinh, thu_tu=thu_tu,
    )


def kiem_tra_truoc_khi_kich_hoat(process):
    """Quy trình phải có cấp đang áp dụng và mỗi cấp phải có người ký."""
    steps = list(process.cap_ky_set.filter(dang_ap_dung=True).prefetch_related("nguoi_ky_set"))
    if not steps:
        raise SigningError(code="quy_trinh_khong_co_cap", detail="Quy trình chưa có cấp ký nào đang áp dụng.")
    thieu = [s.thu_tu for s in steps if not s.nguoi_ky_set.all()]
    if thieu:
        raise SigningError(
            code="cap_ky_khong_co_nguoi_ky",
            detail="Có cấp ký chưa có người ký.",
            fields={"cap_ky_thieu_nguoi_ky": thieu},
        )


@transaction.atomic
def kich_hoat(process, nguoi_thuc_hien):
    """
    Kích hoạt một phiên bản nháp. Mỗi mã quy trình chỉ có một phiên bản HOAT_DONG: phiên bản đang
    hoạt động khác cùng mã chuyển NGUNG trong cùng transaction (giữ lại để tra cứu; yêu cầu đã tạo
    từ phiên bản cũ không bị ảnh hưởng). Khóa mọi phiên bản cùng mã theo thứ tự pk để hai lượt
    kích hoạt đồng thời không cùng để lại hai bản hoạt động.
    """
    ma = SigningProcess.objects.values_list("ma_quy_trinh", flat=True).get(pk=process.pk)
    cung_ma = list(SigningProcess.objects.select_for_update().filter(ma_quy_trinh=ma).order_by("pk"))
    process = next(p for p in cung_ma if p.pk == process.pk)
    if process.trang_thai != enums.TrangThaiQuyTrinh.NHAP:
        raise ConflictError(code="quy_trinh_khong_o_trang_thai_nhap", detail="Chỉ kích hoạt được quy trình nháp.")
    kiem_tra_truoc_khi_kich_hoat(process)
    for cu in cung_ma:
        if cu.pk != process.pk and cu.trang_thai == enums.TrangThaiQuyTrinh.HOAT_DONG:
            cu.trang_thai = enums.TrangThaiQuyTrinh.NGUNG
            cu.update_by = nguoi_thuc_hien
            cu.save(update_fields=["trang_thai", "update_by", "update_at"])
            ghi_nhat_ky(nguoi_thuc_hien, LOAI, cu.pk, "NGUNG_QUY_TRINH",
                        trang_thai_truoc=enums.TrangThaiQuyTrinh.HOAT_DONG, trang_thai_sau=cu.trang_thai,
                        chi_tiet=f"Thay bằng phiên bản {process.phien_ban}",
                        du_lieu_kem_theo={"thay_the_boi": process.pk, "phien_ban_moi": process.phien_ban})
    truoc = process.trang_thai
    process.trang_thai = enums.TrangThaiQuyTrinh.HOAT_DONG
    process.update_by = nguoi_thuc_hien
    process.save(update_fields=["trang_thai", "update_by", "update_at"])
    ghi_nhat_ky(nguoi_thuc_hien, LOAI, process.pk, "KICH_HOAT_QUY_TRINH",
                trang_thai_truoc=truoc, trang_thai_sau=process.trang_thai)
    return process


@transaction.atomic
def ngung(process, nguoi_thuc_hien):
    process = _khoa(process.pk)
    if process.trang_thai != enums.TrangThaiQuyTrinh.HOAT_DONG:
        raise ConflictError(code="quy_trinh_khong_hoat_dong", detail="Chỉ ngừng được quy trình đang hoạt động.")
    truoc = process.trang_thai
    process.trang_thai = enums.TrangThaiQuyTrinh.NGUNG
    process.update_by = nguoi_thuc_hien
    process.save(update_fields=["trang_thai", "update_by", "update_at"])
    ghi_nhat_ky(nguoi_thuc_hien, LOAI, process.pk, "NGUNG_QUY_TRINH",
                trang_thai_truoc=truoc, trang_thai_sau=process.trang_thai)
    return process


@transaction.atomic
def nhan_ban(process, nguoi_thuc_hien):
    """Tạo phiên bản mới (nháp) từ quy trình hiện có, sao chép cấp và người ký."""
    nguon = SigningProcess.objects.get(pk=process.pk)
    ban_moi_nhat = SigningProcess.objects.select_for_update().filter(
        ma_quy_trinh=nguon.ma_quy_trinh
    ).aggregate(m=Max("phien_ban"))["m"]
    moi = SigningProcess.objects.create(
        ma_quy_trinh=nguon.ma_quy_trinh, ten_quy_trinh=nguon.ten_quy_trinh, mo_ta=nguon.mo_ta,
        pham_vi=nguon.pham_vi, don_vi_ap_dung_id=nguon.don_vi_ap_dung_id,
        cau_hinh_nhac_han=nguon.cau_hinh_nhac_han, phien_ban=ban_moi_nhat + 1,
        create_by=nguoi_thuc_hien,
    )
    for step in nguon.cap_ky_set.prefetch_related("nguoi_ky_set"):
        step_moi = SigningProcessStep.objects.create(
            quy_trinh=moi, cap_ky=step.cap_ky, ten_cap_ky=step.ten_cap_ky, thu_tu=step.thu_tu,
            don_vi_id=step.don_vi_id, so_gio_xu_ly=step.so_gio_xu_ly,
            dang_ap_dung=step.dang_ap_dung, ghi_chu=step.ghi_chu,
        )
        for nk in step.nguoi_ky_set.all():
            SigningProcessStepSigner.objects.create(
                buoc_quy_trinh=step_moi, nguoi_ky=nk.nguoi_ky, chuc_vu_id=nk.chuc_vu_id,
                pham_vi_chuc_vu=nk.pham_vi_chuc_vu,
                vai_tro_ky=nk.vai_tro_ky, chan_ky_chinh=nk.chan_ky_chinh, thu_tu=nk.thu_tu,
            )
    ghi_nhat_ky(nguoi_thuc_hien, LOAI, moi.pk, "NHAN_BAN_QUY_TRINH", trang_thai_sau=moi.trang_thai,
                du_lieu_kem_theo={"tu_quy_trinh": nguon.pk, "phien_ban": moi.phien_ban})
    return moi
