"""
Sinh tệp PDF hoàn tất — phần lõi Phase 10 (#80, mục D).

- Lượt trình hoàn thành thì `trang_thai_tep_hoan_tat = DANG_XU_LY` và bằng chứng được chốt trong cùng transaction;
  `tao_tep_hoan_tat` chạy sau commit (`transaction.on_commit`). Sau này chuyển thành task Celery chỉ nhận id.
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
from ..models import SigningAttempt, SigningRequest, SigningSignature
from ..pdf_hoan_tat import LoiTaoTep, dung_tep_hoan_tat
from ..permissions import XEM_NHAT_KY, co_quyen
from ..storage import StorageError, get_storage
from .audit import ghi_nhat_ky
from .bang_chung import bang_chung_cua
from .trinh_ky import luot_hien_hanh

logger = logging.getLogger(__name__)
THOI_HAN_XU_LY = timedelta(minutes=10)
THU_MUC = "hoan_tat"
LOAI = "signing_attempt"


def _ket_thuc(luot_id, nguoi_id, *, loi="", vi_tri="", ma_bam=""):
    with transaction.atomic():
        luot = SigningAttempt.objects.select_for_update().select_related("trinh_ky").get(pk=luot_id)
        if luot.trang_thai_tep_hoan_tat != enums.TrangThaiTepHoanTat.DANG_XU_LY:
            return luot  # lượt khác đã kết thúc trước (tệp vừa ghi bị bỏ, không thay bản đã có)
        if loi:
            luot.trang_thai_tep_hoan_tat, luot.loi_tep_hoan_tat = enums.TrangThaiTepHoanTat.LOI, loi
            hanh_dong, du_lieu = "LOI_TAO_TEP_HOAN_TAT", {"loi": loi}
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
    transaction.on_commit(lambda: tao_tep_hoan_tat(luot.pk, nguoi.pk), robust=True)


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
