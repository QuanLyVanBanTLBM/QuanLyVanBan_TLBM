"""
Sinh tệp PDF hoàn tất — phần lõi Phase 10 (#80, mục D).

- Lượt trình hoàn thành thì `trang_thai_tep_hoan_tat = DANG_XU_LY` và bằng chứng được chốt trong cùng transaction;
  `tao_tep_hoan_tat` được đưa vào Celery sau commit (`transaction.on_commit`), task chỉ nhận ID.
- Tệp hoàn tất ghi một lần (tệp mới, không ghi đè): lỗi thì `LOI` kèm mã lỗi, không ảnh hưởng chữ ký đã có,
  không yêu cầu ký lại; người tạo hồ sơ hoặc kiểm toán thử lại (`tao_lai_tep_hoan_tat`). Đã `THANH_CONG` thì
  không sinh lại, tránh hai bản kết quả khác nhau.
- Đang xử lý quá `THOI_HAN_XU_LY` (tiến trình chết giữa chừng) thì được phép thử lại.
"""

import logging
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework import status

from .. import crypto, enums
from ..errors import ConflictError, SigningError
from ..models import SigningAttempt, SigningAuditLog, SigningRequest, SigningSignature
from ..pdf_hoan_tat import LoiTaoTep, dung_tep_da_ky_tien_trinh, dung_tep_hoan_tat
from ..permissions import XEM_NHAT_KY, co_quyen
from ..storage import StorageError, get_storage, xoa_tep_sau_commit
from .audit import ghi_nhat_ky
from .bang_chung import bang_chung_cua, noi_dung_bang_chung
from .trinh_ky import luot_hien_hanh

logger = logging.getLogger(__name__)
THOI_HAN_XU_LY = timedelta(minutes=10)
# Lỗi do dữ liệu hồ sơ: dựng lại không khắc phục được (mã băm tệp gốc hoặc ảnh chữ ký lệch bằng chứng đã chốt,
# tệp gốc bị mã hóa, chưa có bằng chứng). Các mã khác (lưu/đọc tệp, thiếu phông, lỗi không xác định) là lỗi tạm hoặc
# do cấu hình: thử lại được sau khi khắc phục (#497).
LOI_VINH_VIEN = frozenset({"chua_co_bang_chung", "tep_goc_khong_khop", "tep_goc_bi_ma_hoa", "anh_chu_ky_khong_khop"})


def la_loi_vinh_vien(ma):
    return ma in LOI_VINH_VIEN
THU_MUC = "hoan_tat"
LOAI = "signing_attempt"


def _ket_thuc(luot_id, nguoi_id, *, loi="", vi_tri="", ma_bam=""):
    with transaction.atomic():
        luot = SigningAttempt.objects.select_for_update().select_related("trinh_ky").get(pk=luot_id)
        if luot.trang_thai_tep_hoan_tat != enums.TrangThaiTepHoanTat.DANG_XU_LY:
            if vi_tri:
                xoa_tep_sau_commit(vi_tri)  # tệp vừa ghi bị bỏ, không thay bản đã có
            return luot  # lượt khác đã kết thúc trước
        if loi:
            luot.trang_thai_tep_hoan_tat, luot.loi_tep_hoan_tat = enums.TrangThaiTepHoanTat.LOI, loi
            hanh_dong, du_lieu = "LOI_TAO_TEP_HOAN_TAT", {"loi": loi, "vinh_vien": la_loi_vinh_vien(loi)}
        else:
            luot.trang_thai_tep_hoan_tat, luot.loi_tep_hoan_tat = enums.TrangThaiTepHoanTat.THANH_CONG, ""
            luot.vi_tri_tep_hoan_tat, luot.ma_bam_tep_hoan_tat = vi_tri, ma_bam
            hanh_dong, du_lieu = "TAO_TEP_HOAN_TAT", {"ma_bam_tep_hoan_tat": ma_bam}
        luot.save(update_fields=["trang_thai_tep_hoan_tat", "loi_tep_hoan_tat", "vi_tri_tep_hoan_tat",
                                 "ma_bam_tep_hoan_tat", "update_at"])
        nguoi = get_user_model().objects.get(pk=nguoi_id)
        ghi_nhat_ky(nguoi, LOAI, luot.pk, hanh_dong, trinh_ky=luot.trinh_ky, luot_trinh=luot,
                    trang_thai_truoc=enums.TrangThaiTepHoanTat.DANG_XU_LY,
                    trang_thai_sau=luot.trang_thai_tep_hoan_tat, chi_tiet=loi, du_lieu_kem_theo=du_lieu)
        return luot


def _anh_chu_ky_theo_bang_chung(noi_dung, storage):
    """Ảnh snapshot của các chữ ký trong bằng chứng, kiểm mã băm từng ảnh với mã băm đã chốt."""
    can = {n["chu_ky"]["id"]: n["chu_ky"]["ma_bam_anh_chu_ky"] for c in noi_dung["cap_ky"] for n in c["nguoi_ky"]
           if n["chu_ky"] and n["chu_ky"].get("ma_bam_anh_chu_ky")}
    ket_qua = {}
    for chu_ky in SigningSignature.objects.filter(pk__in=can):
        try:
            anh = storage.read_bytes(chu_ky.vi_tri_anh_chu_ky)
        except StorageError as exc:
            raise LoiTaoTep("anh_chu_ky_khong_doc_duoc", str(exc)) from exc
        if crypto.sha256_hex(anh) != can[chu_ky.pk]:
            raise LoiTaoTep("anh_chu_ky_khong_khop", f"Ảnh chữ ký {chu_ky.pk} khác bản đã chốt.")
        ket_qua[chu_ky.pk] = anh
    return ket_qua


def tao_tep_hoan_tat(luot_id, nguoi_id):
    """Sinh tệp cho lượt `DANG_XU_LY`; không ném lỗi (chạy sau commit của thao tác ký cuối)."""
    luot = SigningAttempt.objects.get(pk=luot_id)
    if luot.trang_thai_tep_hoan_tat != enums.TrangThaiTepHoanTat.DANG_XU_LY:
        return luot
    manifest = bang_chung_cua(luot)
    storage = get_storage()
    try:
        if manifest is None:
            raise LoiTaoTep("chua_co_bang_chung")
        try:
            goc = storage.read_bytes(luot.vi_tri_luu_tep)
        except StorageError as exc:
            raise LoiTaoTep("tep_goc_khong_doc_duoc", str(exc)) from exc
        if crypto.sha256_hex(goc) != luot.ma_bam_tai_lieu:
            raise LoiTaoTep("tep_goc_khong_khop", "Mã băm tệp gốc khác bản đã khóa.")
        anh = _anh_chu_ky_theo_bang_chung(manifest.noi_dung_chuan_hoa, storage)
        du_lieu = dung_tep_hoan_tat(goc, manifest.noi_dung_chuan_hoa, manifest.ma_bam_bang_chung, anh)
        try:
            meta = storage.save_bytes(du_lieu, THU_MUC, "pdf")
        except (StorageError, OSError) as exc:
            raise LoiTaoTep("loi_luu_tep", str(exc)) from exc
    except LoiTaoTep as exc:
        logger.error("Không tạo được tệp hoàn tất lượt %s: %s", luot_id, exc)
        return _ket_thuc(luot_id, nguoi_id, loi=exc.ma)
    except Exception:  # noqa: BLE001 — lỗi bất ngờ của thư viện PDF: ghi LOI để thử lại, không làm hỏng lượt ký
        logger.exception("Lỗi không xác định khi tạo tệp hoàn tất lượt %s", luot_id)
        return _ket_thuc(luot_id, nguoi_id, loi="loi_khong_xac_dinh")
    return _ket_thuc(luot_id, nguoi_id, vi_tri=meta.vi_tri_luu_tep, ma_bam=crypto.sha256_hex(du_lieu))


def bat_dau_sau_commit(luot, nguoi):
    luot_id, nguoi_id = luot.pk, nguoi.pk

    def dua_vao_hang():
        from signing.tasks import tao_tep_hoan_tat as task_tao_tep

        task_tao_tep.delay(luot_id, nguoi_id)

    transaction.on_commit(dua_vao_hang, robust=True)


def tao_lai_tep_hoan_tat(yeu_cau, nguoi):
    """Người tạo hồ sơ hoặc kiểm toán (`view_signing_audit`) thử lại khi `LOI` hoặc đang xử lý quá hạn."""
    if yeu_cau.create_by_id != nguoi.pk and not co_quyen(nguoi, XEM_NHAT_KY):
        raise SigningError(code="khong_co_quyen", detail="Chỉ người tạo hồ sơ hoặc kiểm toán được tạo lại tệp.",
                           status_code=status.HTTP_403_FORBIDDEN)
    with transaction.atomic():
        yeu_cau = SigningRequest.objects.get(pk=yeu_cau.pk)
        luot = luot_hien_hanh(yeu_cau)
        if luot is None or yeu_cau.trang_thai != enums.TrangThaiYeuCau.HOAN_THANH:
            raise ConflictError(code="ho_so_chua_hoan_thanh", detail="Hồ sơ chưa hoàn tất duyệt.")
        luot = SigningAttempt.objects.select_for_update().get(pk=luot.pk)
        trang_thai = luot.trang_thai_tep_hoan_tat
        if trang_thai == enums.TrangThaiTepHoanTat.THANH_CONG:
            return luot
        if trang_thai == enums.TrangThaiTepHoanTat.DANG_XU_LY and luot.update_at > timezone.now() - THOI_HAN_XU_LY:
            raise ConflictError(code="dang_tao_tep_hoan_tat", detail="Tệp hoàn tất đang được tạo, thử lại sau.")
        if trang_thai == enums.TrangThaiTepHoanTat.LOI and la_loi_vinh_vien(luot.loi_tep_hoan_tat):
            raise ConflictError(code="loi_tep_vinh_vien",
                                detail="Lỗi do dữ liệu hồ sơ, tạo lại không khắc phục được. Liên hệ quản trị viên.",
                                fields={"loi_tep_hoan_tat": [luot.loi_tep_hoan_tat]})
        luot.trang_thai_tep_hoan_tat, luot.loi_tep_hoan_tat = enums.TrangThaiTepHoanTat.DANG_XU_LY, ""
        luot.save(update_fields=["trang_thai_tep_hoan_tat", "loi_tep_hoan_tat", "update_at"])
        ghi_nhat_ky(nguoi, LOAI, luot.pk, "TAO_LAI_TEP_HOAN_TAT", trinh_ky=yeu_cau, luot_trinh=luot,
                    trang_thai_truoc=trang_thai or "", trang_thai_sau=luot.trang_thai_tep_hoan_tat)
    return tao_tep_hoan_tat(luot.pk, nguoi.pk)


def doc_tep_hoan_tat(luot):
    """Bytes tệp hoàn tất đã kiểm mã băm; chưa sẵn sàng hoặc tệp bị đổi thì lỗi có mã."""
    if luot is None or luot.trang_thai_tep_hoan_tat != enums.TrangThaiTepHoanTat.THANH_CONG:
        raise ConflictError(code="tep_hoan_tat_chua_san_sang", detail="Tệp hoàn tất chưa sẵn sàng.",
                            fields={"trang_thai_tep_hoan_tat": [luot.trang_thai_tep_hoan_tat if luot else None]})
    try:
        du_lieu = get_storage().read_bytes(luot.vi_tri_tep_hoan_tat)
    except StorageError:
        raise SigningError(code="khong_doc_duoc_tep", detail="Không đọc được tệp hoàn tất.",
                           status_code=status.HTTP_404_NOT_FOUND)
    if crypto.sha256_hex(du_lieu) != luot.ma_bam_tep_hoan_tat:
        logger.error("Tệp hoàn tất lượt %s không khớp mã băm đã lưu", luot.pk)
        raise ConflictError(code="tep_hoan_tat_bi_thay_doi", detail="Tệp hoàn tất không khớp mã băm đã lưu.")
    return du_lieu


def luot_can_phuc_hoi(bay_gio=None):
    """Lượt hoàn tất cần dựng lại: kẹt `DANG_XU_LY` quá hạn xử lý, hoặc `LOI` tạm (không phải lỗi vĩnh viễn)."""
    bay_gio = bay_gio or timezone.now()
    ung_vien = SigningAttempt.objects.filter(
        trang_thai=enums.TrangThaiLuotTrinh.HOAN_THANH,
        trang_thai_tep_hoan_tat__in=(enums.TrangThaiTepHoanTat.DANG_XU_LY, enums.TrangThaiTepHoanTat.LOI),
    ).select_related("trinh_ky").order_by("pk")
    return [luot for luot in ung_vien if _co_the_phuc_hoi(luot, bay_gio)]


def _co_the_phuc_hoi(luot, bay_gio):
    return (
        luot.trang_thai_tep_hoan_tat == enums.TrangThaiTepHoanTat.DANG_XU_LY
        and luot.update_at <= bay_gio - THOI_HAN_XU_LY
    ) or (
        luot.trang_thai_tep_hoan_tat == enums.TrangThaiTepHoanTat.LOI
        and not la_loi_vinh_vien(luot.loi_tep_hoan_tat)
    )


def _nguoi_thuc_hien_phuc_hoi(luot):
    """Người ký cuối (ghi trong nhật ký hoàn tất), không có thì người tạo hồ sơ."""
    ban_ghi = SigningAuditLog.objects.filter(
        luot_trinh=luot, hanh_dong="HOAN_THANH_TRINH_KY").order_by("-pk").select_related("nguoi_thuc_hien").first()
    return ban_ghi.nguoi_thuc_hien if ban_ghi else luot.trinh_ky.create_by


def phuc_hoi_mot_luot_tep_hoan_tat(luot_id, bay_gio=None):
    """Phục hồi một lượt PDF retryable; dùng được từ lệnh vận hành và task Celery."""
    bay_gio = bay_gio or timezone.now()
    ung_vien = (SigningAttempt.objects.filter(pk=luot_id, trang_thai=enums.TrangThaiLuotTrinh.HOAN_THANH)
                .select_related("trinh_ky__create_by").first())
    if ung_vien is None or not _co_the_phuc_hoi(ung_vien, bay_gio):
        return None

    nguoi = _nguoi_thuc_hien_phuc_hoi(ung_vien)
    with transaction.atomic():
        luot = SigningAttempt.objects.select_for_update().select_related("trinh_ky").get(pk=ung_vien.pk)
        truoc = luot.trang_thai_tep_hoan_tat
        if not _co_the_phuc_hoi(luot, bay_gio):
            return None
        luot.trang_thai_tep_hoan_tat, luot.loi_tep_hoan_tat = enums.TrangThaiTepHoanTat.DANG_XU_LY, ""
        luot.save(update_fields=["trang_thai_tep_hoan_tat", "loi_tep_hoan_tat", "update_at"])
        ghi_nhat_ky(nguoi, LOAI, luot.pk, "PHUC_HOI_TEP_HOAN_TAT", trinh_ky=luot.trinh_ky, luot_trinh=luot,
                    trang_thai_truoc=truoc or "", trang_thai_sau=luot.trang_thai_tep_hoan_tat)
    sau = tao_tep_hoan_tat(luot.pk, nguoi.pk)
    return luot.pk, truoc, sau.trang_thai_tep_hoan_tat


def phuc_hoi_tep_hoan_tat(bay_gio=None):
    """
    Dựng lại tệp hoàn tất cho các lượt từ `luot_can_phuc_hoi`; không cần người dùng bấm thủ công. Trả danh sách
    `(id lượt, trạng thái trước, trạng thái sau)`. Lượt đã được tiến trình khác xử lý trong lúc quét thì bỏ qua.
    """
    bay_gio = bay_gio or timezone.now()
    ket_qua = []
    for ung_vien in luot_can_phuc_hoi(bay_gio):
        ket_qua_luot = phuc_hoi_mot_luot_tep_hoan_tat(ung_vien.pk, bay_gio)
        if ket_qua_luot is not None:
            ket_qua.append(ket_qua_luot)
    return ket_qua


def sinh_tep_da_ky_tien_trinh(luot):
    """Trả về bytes PDF chứa các chữ ký lũy kế đã có của lượt trình."""
    storage = get_storage()
    try:
        goc = storage.read_bytes(luot.vi_tri_luu_tep)
    except StorageError as exc:
        raise LoiTaoTep("tep_goc_khong_doc_duoc", str(exc)) from exc
    noi_dung = noi_dung_bang_chung(luot)
    chu_ky_ids = [n["chu_ky"]["id"] for c in noi_dung["cap_ky"] for n in c["nguoi_ky"] if n.get("chu_ky")]
    anh_chu_ky = {}
    for ck in SigningSignature.objects.filter(pk__in=chu_ky_ids):
        if ck.vi_tri_anh_chu_ky:
            try:
                anh_chu_ky[ck.pk] = storage.read_bytes(ck.vi_tri_anh_chu_ky)
            except StorageError:
                pass
    return dung_tep_da_ky_tien_trinh(goc, noi_dung, anh_chu_ky)

