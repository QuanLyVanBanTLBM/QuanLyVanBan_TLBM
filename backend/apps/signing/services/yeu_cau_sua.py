"""
Trả lại để sửa — phần lõi Phase 9 (#80; plan mục 3.3 "Nhánh 2", 6.1).

- yeu_cau_sua: người ký đang được mở yêu cầu sửa (bắt buộc tiêu đề, lý do). Người ký và lượt trình
  YEU_CAU_SUA, cấp đang ký TAM_DUNG; không ai ký tiếp trên lượt này. Mở thread trao đổi. Hồ sơ vẫn CHO_KY.
- gui_tin_nhan: người tạo hồ sơ và người yêu cầu sửa trao đổi trong thread đang mở.
- giai_quyet: người tạo tải bản mới, thread DA_GIAI_QUYET, tạo lượt trình mới (`luot_truoc` trỏ lượt cũ)
  với cùng người ký của lượt cũ; toàn bộ các cấp ký lại. Lượt cũ giữ YEU_CAU_SUA làm lịch sử; chữ ký cũ
  thuộc lượt cũ, không dùng lại cho tệp mới.
"""

from django.db import transaction
from django.utils import timezone
from rest_framework import status

from .. import enums
from ..errors import ConflictError, SigningError
from ..models import (
    SigningAttempt, SigningChangeMessage, SigningChangeThread, SigningRequest, SigningRequestStep,
    SigningRequestStepSigner,
)
from .audit import ghi_nhat_ky
from .hanh_dong_ky import _dong_cua_toi, _khoa_luot_hien_hanh, _thao_tac_lap
from .trinh_ky import TRUONG_VI_TRI, doc_tep_pdf, kiem_tra_vi_tri_ky, luot_hien_hanh, luu_du_lieu_pdf, mo_cap


def thread_dang_mo(yeu_cau):
    luot = luot_hien_hanh(yeu_cau)
    if luot is None:
        return None
    return luot.yeu_cau_sua_set.filter(trang_thai=enums.TrangThaiThread.DANG_MO).first()


@transaction.atomic
def yeu_cau_sua(yeu_cau, nguoi, *, tieu_de, ly_do, khoa_chong_trung, dia_chi_ip=None):
    if not tieu_de.strip() or not ly_do.strip():
        raise SigningError(code="thieu_ly_do", detail="Trả lại để sửa phải có tiêu đề và lý do.",
                           fields={"tieu_de": ["Bắt buộc."], "ly_do": ["Bắt buộc."]})
    if _thao_tac_lap(yeu_cau, nguoi, khoa_chong_trung):
        return SigningRequest.objects.get(pk=yeu_cau.pk)
    luot = _khoa_luot_hien_hanh(yeu_cau)
    if _thao_tac_lap(yeu_cau, nguoi, khoa_chong_trung):
        return SigningRequest.objects.get(pk=yeu_cau.pk)
    dong = _dong_cua_toi(luot, nguoi)
    dong.trang_thai = enums.TrangThaiNguoiKy.YEU_CAU_SUA
    dong.khoa_chong_trung_thao_tac = khoa_chong_trung
    dong.save(update_fields=["trang_thai", "khoa_chong_trung_thao_tac"])
    luot.trang_thai = enums.TrangThaiLuotTrinh.YEU_CAU_SUA
    luot.ly_do = ly_do
    luot.save(update_fields=["trang_thai", "ly_do", "update_at"])
    SigningRequestStep.objects.filter(luot_trinh=luot, trang_thai=enums.TrangThaiCapKy.DANG_KY).update(
        trang_thai=enums.TrangThaiCapKy.TAM_DUNG)
    thread = SigningChangeThread.objects.create(luot_trinh=luot, nguoi_yeu_cau=nguoi, tieu_de=tieu_de, ly_do=ly_do)
    ghi_nhat_ky(nguoi, "signing_request_step_signer", dong.pk, "YEU_CAU_SUA", trinh_ky=luot.trinh_ky,
                luot_trinh=luot, buoc_ky=dong, trang_thai_truoc=enums.TrangThaiLuotTrinh.CHO_KY,
                trang_thai_sau=luot.trang_thai, chi_tiet=tieu_de, dia_chi_ip=dia_chi_ip,
                du_lieu_kem_theo={"thread": thread.pk})
    return SigningRequest.objects.get(pk=yeu_cau.pk)


def duoc_trao_doi(thread, nguoi):
    return nguoi.pk in (thread.nguoi_yeu_cau_id, thread.luot_trinh.trinh_ky.create_by_id)


@transaction.atomic
def gui_tin_nhan(yeu_cau, nguoi, *, noi_dung):
    if not noi_dung.strip():
        raise SigningError(code="thieu_noi_dung", detail="Tin nhắn không được trống.",
                           fields={"noi_dung": ["Bắt buộc."]})
    thread = thread_dang_mo(yeu_cau)
    yeu_cau = SigningRequest.objects.get(pk=yeu_cau.pk)
    if thread is None or yeu_cau.trang_thai != enums.TrangThaiYeuCau.CHO_KY:
        raise ConflictError(code="khong_co_trao_doi_dang_mo", detail="Hồ sơ không có yêu cầu sửa đang mở.")
    if not duoc_trao_doi(thread, nguoi):
        raise SigningError(code="khong_co_quyen", detail="Chỉ người tạo hồ sơ và người yêu cầu sửa được trao đổi.",
                           status_code=status.HTTP_403_FORBIDDEN)
    return SigningChangeMessage.objects.create(yeu_cau_sua=thread, nguoi_viet=nguoi, noi_dung=noi_dung)


def _cap_ky_luot_cu(luot_cu):
    """Cấp và người ký của lượt cũ; báo lỗi nếu có người ký không còn hoạt động (kiểm trước khi lưu tệp)."""
    cap_cu = list(luot_cu.cap_ky_set.order_by("thu_tu").prefetch_related("nguoi_ky_set__nguoi_ky"))
    khong_hoat_dong = [n.pk for c in cap_cu for n in c.nguoi_ky_set.all() if not n.nguoi_ky.is_active]
    if khong_hoat_dong:
        raise SigningError(code="khong_xac_dinh_duoc_nguoi_ky",
                           detail="Có người ký của lượt trước không còn hoạt động; hãy hủy và tạo hồ sơ mới.",
                           fields={"nguoi_ky": [{"loai": "nguoi_ky_khong_hoat_dong", "dong": khong_hoat_dong}]})
    return cap_cu


def _vi_tri_luot_moi(cap_cu, vi_tri_ky, so_trang):
    """Vị trí của lượt cũ, ghi đè bằng `vi_tri_ky` (khóa = id dòng người ký lượt cũ); kiểm với số trang tệp mới."""
    dong_cu = [n for c in cap_cu for n in c.nguoi_ky_set.all()]
    vi_tri = {str(n.pk): {f: getattr(n, f) for f in TRUONG_VI_TRI} for n in dong_cu if n.trang_ky is not None}
    vi_tri.update(vi_tri_ky or {})
    kiem_tra_vi_tri_ky(vi_tri, {str(n.pk) for n in dong_cu}, so_trang)
    return vi_tri


def _sao_chep_luot(luot_cu, cap_cu, yeu_cau, nguoi, khoa_chong_trung, thoi_diem, vi_tri):
    """Lượt mới: cùng cấp và người ký của lượt cũ, mọi trạng thái về ban đầu. Trả về (lượt, cấp đầu)."""
    luot = SigningAttempt.objects.create(
        trinh_ky=yeu_cau, so_luot=luot_cu.so_luot + 1, luot_truoc=luot_cu,
        phien_ban_van_ban=yeu_cau.phien_ban_van_ban, vi_tri_luu_tep=yeu_cau.vi_tri_luu_tep,
        ma_bam_tai_lieu=yeu_cau.ma_bam_tai_lieu, trang_thai=enums.TrangThaiLuotTrinh.CHO_KY,
        khoa_chong_trung=khoa_chong_trung, thoi_diem_gui=thoi_diem, create_by=nguoi,
    )
    cap_dau = None
    for cap in cap_cu:
        cap_moi = SigningRequestStep.objects.create(
            luot_trinh=luot, buoc_quy_trinh_id=cap.buoc_quy_trinh_id, cap_ky=cap.cap_ky, ten_cap_ky=cap.ten_cap_ky,
            thu_tu=cap.thu_tu,
        )
        cap_dau = cap_dau or cap_moi
        for n in cap.nguoi_ky_set.all():
            SigningRequestStepSigner.objects.create(
                buoc_ky=cap_moi, nguoi_ky=n.nguoi_ky, chuc_vu_id=n.chuc_vu_id, ten_nguoi_ky=n.ten_nguoi_ky,
                ten_chuc_vu=n.ten_chuc_vu, vai_tro_ky=n.vai_tro_ky, chan_ky_chinh=n.chan_ky_chinh,
                **vi_tri.get(str(n.pk), {}),
            )
    return luot, cap_dau


def _giai_quyet_lap(yeu_cau, khoa_chong_trung):
    # Lượt do giải quyết tạo luôn có lượt trước; khóa của lần `gui` (lượt đầu) không được coi là thao tác lặp
    da_co = SigningAttempt.objects.filter(khoa_chong_trung=khoa_chong_trung).first()
    if da_co is not None and (da_co.trinh_ky_id != yeu_cau.pk or da_co.luot_truoc_id is None):
        raise ConflictError(code="khoa_chong_trung_da_dung", detail="Idempotency-Key đã dùng cho thao tác khác.")
    return da_co is not None


@transaction.atomic
def giai_quyet(yeu_cau, nguoi, *, tep, khoa_chong_trung, vi_tri_ky=None, dia_chi_ip=None):
    if _giai_quyet_lap(yeu_cau, khoa_chong_trung):
        return SigningRequest.objects.get(pk=yeu_cau.pk)
    yeu_cau = SigningRequest.objects.select_for_update().get(pk=yeu_cau.pk)
    if _giai_quyet_lap(yeu_cau, khoa_chong_trung):  # yêu cầu trùng chạy song song đã xong trước khi có khóa
        return yeu_cau
    if yeu_cau.create_by_id != nguoi.pk:
        raise SigningError(code="khong_co_quyen", detail="Chỉ người tạo hồ sơ được giải quyết yêu cầu sửa.",
                           status_code=status.HTTP_403_FORBIDDEN)
    luot_cu = luot_hien_hanh(yeu_cau)
    luot_cu = SigningAttempt.objects.select_for_update().get(pk=luot_cu.pk) if luot_cu else None
    thread = thread_dang_mo(yeu_cau)
    if (yeu_cau.trang_thai != enums.TrangThaiYeuCau.CHO_KY or luot_cu is None
            or luot_cu.trang_thai != enums.TrangThaiLuotTrinh.YEU_CAU_SUA or thread is None):
        raise ConflictError(code="khong_co_yeu_cau_sua_dang_mo", detail="Hồ sơ không có yêu cầu sửa đang mở.")
    cap_cu = _cap_ky_luot_cu(luot_cu)
    du_lieu, so_trang = doc_tep_pdf(tep)
    vi_tri = _vi_tri_luot_moi(cap_cu, vi_tri_ky, so_trang)  # kiểm trước khi lưu tệp
    thoi_diem = timezone.now()
    yeu_cau.vi_tri_luu_tep, yeu_cau.ma_bam_tai_lieu = luu_du_lieu_pdf(du_lieu)
    yeu_cau.phien_ban_van_ban = str(int(yeu_cau.phien_ban_van_ban or "0") + 1)
    yeu_cau.update_by = nguoi
    yeu_cau.save(update_fields=["vi_tri_luu_tep", "ma_bam_tai_lieu", "phien_ban_van_ban", "update_by", "update_at"])
    thread.trang_thai = enums.TrangThaiThread.DA_GIAI_QUYET
    thread.thoi_diem_giai_quyet = thoi_diem
    thread.save(update_fields=["trang_thai", "thoi_diem_giai_quyet", "update_at"])
    luot, cap_dau = _sao_chep_luot(luot_cu, cap_cu, yeu_cau, nguoi, khoa_chong_trung, thoi_diem, vi_tri)
    ghi_nhat_ky(nguoi, "signing_request", yeu_cau.pk, "GIAI_QUYET_YEU_CAU_SUA", trinh_ky=yeu_cau, luot_trinh=luot,
                trang_thai_truoc=enums.TrangThaiLuotTrinh.YEU_CAU_SUA, trang_thai_sau=luot.trang_thai,
                dia_chi_ip=dia_chi_ip, du_lieu_kem_theo={"thread": thread.pk, "luot_truoc": luot_cu.pk,
                                                       "ma_bam_tai_lieu": luot.ma_bam_tai_lieu})
    mo_cap(luot, cap_dau, thoi_diem, nguoi)  # sau nhật ký giải quyết để dòng thời gian đúng thứ tự
    return yeu_cau
