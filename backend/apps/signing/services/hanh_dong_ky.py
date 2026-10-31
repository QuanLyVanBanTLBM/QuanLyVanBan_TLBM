"""
Hành động người ký — Phase 8 (#80; plan mục 3.2, 3.4 "Chữ ký", 5.3, 6.2).

- ky: ký Ed25519 trên raw bytes của SHA-256 tệp đã khóa ở lượt trình; đóng cấp khi mọi người ký trong cấp
  đã ký, mở cấp sau hoặc hoàn thành lượt trình và hồ sơ.
- tu_choi: "không đồng ý ban hành", bắt buộc lý do; lượt trình và hồ sơ TU_CHOI (kết thúc).
- thu_hoi: khi cấp của người ký còn mở và lượt chưa hoàn thành.

Mọi hành động trên một lượt trình khóa dòng lượt trình trước (select_for_update) nên các thao tác đồng
thời (ký – ký, ký – từ chối, ký – hủy) được xử lý tuần tự; chỉ một kết quả hợp lệ. Chống thao tác lặp
bằng Idempotency-Key lưu ở `khoa_chong_trung_thao_tac` của dòng người ký.
"""

import logging

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework import status

from .. import crypto, enums
from ..errors import ConflictError, SigningError
from ..models import (
    SigningAttempt, SigningKey, SigningRequest, SigningRequestStep, SigningRequestStepSigner, SigningSignature,
)
from ..permissions import KY_TRINH_KY, co_quyen
from ..storage import StorageError, get_storage
from ..tich_hop import to_chuc
from . import tep_hoan_tat, thong_bao
from .audit import ghi_nhat_ky
from .bang_chung import chot_bang_chung
from .trinh_ky import dung_cap_dang_mo, luot_hien_hanh, mo_cap, mo_nguoi_ky_trong_cap

logger = logging.getLogger(__name__)
LOAI = "signing_request_step_signer"
THU_MUC_ANH_CHU_KY = "anh_chu_ky"


def _khoa_luot_hien_hanh(yeu_cau):
    # Thứ tự khóa thống nhất: hồ sơ rồi lượt trình (như gui, huy, giai_quyet), tránh deadlock khi
    # người ký cuối hoàn tất (khóa hồ sơ) cùng lúc với hủy (khóa hồ sơ rồi lượt).
    SigningRequest.objects.select_for_update().only("pk").get(pk=yeu_cau.pk)
    luot = luot_hien_hanh(yeu_cau)
    if luot is None:
        raise ConflictError(code="ho_so_chua_gui", detail="Hồ sơ chưa được gửi.")
    luot = SigningAttempt.objects.select_for_update().get(pk=luot.pk)
    if luot.trang_thai != enums.TrangThaiLuotTrinh.CHO_KY:
        raise ConflictError(code="luot_trinh_khong_cho_ky", detail="Lượt trình không còn ở trạng thái chờ ký.")
    return luot


def _dong_cua_toi(luot, nguoi, chi_dang_mo=True):
    """Dòng người ký của `nguoi` trong cấp đang ký của lượt (cấp mở tuần tự nên tối đa một dòng)."""
    queryset = SigningRequestStepSigner.objects.select_for_update().filter(
        buoc_ky__luot_trinh=luot, buoc_ky__trang_thai=enums.TrangThaiCapKy.DANG_KY, nguoi_ky=nguoi,
    )
    dong = queryset.first()
    if dong is None:
        raise SigningError(code="khong_phai_nguoi_ky_dang_mo",
                           detail="Bạn không có lượt ký đang mở trên hồ sơ này.", status_code=status.HTTP_403_FORBIDDEN)
    if chi_dang_mo and (dong.thoi_diem_mo is None or dong.trang_thai != enums.TrangThaiNguoiKy.CHO_KY):
        raise ConflictError(code="chua_den_luot_ky",
                            detail="Chưa đến lượt bạn ký vì cấp ký trước chưa hoàn tất, hoặc bạn đã xử lý.")
    return dong


def _nguoi_ky_hien_hanh(nguoi):
    """Đọc khóa tài khoản hiện tại để đổi quyền hoặc khóa tài khoản không bị lách bằng phiên cũ."""
    nguoi_hien_hanh = get_user_model().objects.select_for_update().filter(pk=nguoi.pk).first()
    if nguoi_hien_hanh is None or not co_quyen(nguoi_hien_hanh, KY_TRINH_KY):
        raise SigningError(code="khong_co_quyen", detail="Tài khoản không còn quyền ký.",
                           status_code=status.HTTP_403_FORBIDDEN)
    return nguoi_hien_hanh


def _thao_tac_lap(yeu_cau, nguoi, khoa_chong_trung):
    """True khi `nguoi` đã thực hiện thao tác với cùng khóa trên lượt trình hiện hành (kể cả lượt đã kết thúc)."""
    luot = luot_hien_hanh(yeu_cau)
    return luot is not None and SigningRequestStepSigner.objects.filter(
        buoc_ky__luot_trinh=luot, nguoi_ky=nguoi, khoa_chong_trung_thao_tac=khoa_chong_trung,
    ).exists()


def _hoan_tat_neu_du(luot, cap, nguoi, thoi_diem):
    """Đóng cấp khi mọi người ký trong cấp đã ký; mở cấp sau hoặc hoàn thành lượt trình và hồ sơ."""
    con_cho = cap.nguoi_ky_set.exclude(trang_thai=enums.TrangThaiNguoiKy.DA_KY).exists()
    if con_cho:
        mo_nguoi_ky_trong_cap(cap, thoi_diem)
        return
    cap.trang_thai = enums.TrangThaiCapKy.HOAN_THANH
    cap.thoi_diem_hoan_thanh = thoi_diem
    cap.save(update_fields=["trang_thai", "thoi_diem_hoan_thanh"])
    cap_sau = luot.cap_ky_set.filter(trang_thai=enums.TrangThaiCapKy.CHUA_MO).order_by("thu_tu").first()
    if cap_sau is not None:
        mo_cap(luot, cap_sau, thoi_diem, nguoi)
        return
    luot.trang_thai = enums.TrangThaiLuotTrinh.HOAN_THANH
    luot.thoi_diem_hoan_thanh = thoi_diem
    luot.trang_thai_tep_hoan_tat = enums.TrangThaiTepHoanTat.DANG_XU_LY
    luot.save(update_fields=["trang_thai", "thoi_diem_hoan_thanh", "trang_thai_tep_hoan_tat", "update_at"])
    yeu_cau = SigningRequest.objects.select_for_update().get(pk=luot.trinh_ky_id)
    yeu_cau.trang_thai = enums.TrangThaiYeuCau.HOAN_THANH
    yeu_cau.ngay_hoan_thanh = thoi_diem
    yeu_cau.save(update_fields=["trang_thai", "ngay_hoan_thanh", "update_at"])
    ghi_nhat_ky(nguoi, "signing_request", yeu_cau.pk, "HOAN_THANH_TRINH_KY", trinh_ky=yeu_cau, luot_trinh=luot,
                trang_thai_truoc=enums.TrangThaiYeuCau.CHO_KY, trang_thai_sau=yeu_cau.trang_thai)
    # Phase 10 lõi: chốt bằng chứng cùng transaction; tệp PDF hoàn tất sinh sau commit, lỗi thì thử lại được
    chot_bang_chung(luot, nguoi, thoi_diem)
    tep_hoan_tat.bat_dau_sau_commit(luot, nguoi)
    thong_bao.su_kien(yeu_cau, luot, "HOAN_THANH", nguoi)


def _chup_anh_chu_ky(nguoi, anh_tu_trinh_duyet=None):
    """
    Snapshot ảnh chữ ký cá nhân tại thời điểm ký (plan mục 3.2): đổi ảnh trong hồ sơ sau đó không làm đổi tệp
    hoàn tất. Ưu tiên ảnh phía server (Nhóm 7, nếu có); chưa có thì dùng ảnh PNG trình duyệt gửi kèm yêu cầu
    ký (đã kiểm ở serializer, #420). Chưa có ảnh hoặc không lưu được thì ký vẫn hợp lệ, tệp hoàn tất in khối chữ.
    """
    anh = to_chuc.anh_chu_ky(nguoi) or anh_tu_trinh_duyet
    if not anh:
        return "", ""
    try:
        meta = get_storage().save_bytes(anh, THU_MUC_ANH_CHU_KY, "png")
    except (StorageError, OSError):
        logger.exception("Không lưu được snapshot ảnh chữ ký của người dùng %s", nguoi.pk)
        return "", ""
    return meta.vi_tri_luu_tep, crypto.sha256_hex(anh)


def _kiem_tra_khoa(nguoi, khoa_ky_id, thoi_diem):
    khoa = SigningKey.objects.filter(pk=khoa_ky_id, nguoi_so_huu=nguoi).first()
    if khoa is None:
        raise SigningError(code="khoa_ky_khong_hop_le", detail="Khóa ký không thuộc người ký.",
                           fields={"khoa_ky": ["Không phải khóa của bạn."]})
    het_han = khoa.ngay_het_han is not None and khoa.ngay_het_han <= thoi_diem
    if khoa.trang_thai != enums.TrangThaiKhoa.HOAT_DONG or khoa.ngay_hieu_luc > thoi_diem or het_han:
        raise SigningError(code="khoa_ky_khong_hoat_dong", detail="Khóa ký không ở trạng thái hoạt động.",
                           fields={"khoa_ky": ["Khóa chưa kích hoạt, đã thu hồi, xoay vòng hoặc hết hạn."]})
    return khoa


@transaction.atomic
def ky(yeu_cau, nguoi, *, khoa_ky, hash_tai_lieu, chu_ky_so, khoa_chong_trung, ghi_chu_ky="", dia_chi_ip=None,
       anh_chu_ky=None):
    if _thao_tac_lap(yeu_cau, nguoi, khoa_chong_trung):
        return SigningRequest.objects.get(pk=yeu_cau.pk)  # ký lặp cùng khóa: trả kết quả lần trước
    luot = _khoa_luot_hien_hanh(yeu_cau)
    if _thao_tac_lap(yeu_cau, nguoi, khoa_chong_trung):  # lượt ký đồng thời cùng khóa đã xử lý xong trước
        return SigningRequest.objects.get(pk=yeu_cau.pk)
    dong = _dong_cua_toi(luot, nguoi)
    nguoi = _nguoi_ky_hien_hanh(nguoi)
    thoi_diem = timezone.now()
    khoa = _kiem_tra_khoa(nguoi, khoa_ky, thoi_diem)
    if hash_tai_lieu != luot.ma_bam_tai_lieu:
        raise ConflictError(code="ma_bam_khong_khop",
                            detail="Mã băm tài liệu khác bản đã khóa của lượt trình; tải lại hồ sơ trước khi ký.")
    if not crypto.verify_signature(khoa.khoa_cong_khai, bytes.fromhex(hash_tai_lieu), chu_ky_so):
        raise SigningError(code="chu_ky_khong_hop_le", detail="Chữ ký không hợp lệ với khóa và tài liệu.",
                           fields={"chu_ky_so": ["Không xác minh được."]})
    cap = SigningRequestStep.objects.select_for_update().get(pk=dong.buoc_ky_id)
    tre = cap.han_xu_ly is not None and thoi_diem > cap.han_xu_ly
    vi_tri_anh, ma_bam_anh = _chup_anh_chu_ky(nguoi, anh_chu_ky)
    chu_ky = SigningSignature.objects.create(
        luot_trinh=luot, buoc_ky=dong, khoa_ky=khoa, hash_tai_lieu=hash_tai_lieu, thuat_toan=khoa.thuat_toan,
        chu_ky_so=chu_ky_so, ghi_chu_ky=ghi_chu_ky, ky_tre_han=tre,
        so_giay_tre=int((thoi_diem - cap.han_xu_ly).total_seconds()) if tre else None,
        ngay_ky=thoi_diem, trang_thai_xac_minh=enums.TrangThaiXacMinh.HOP_LE, thoi_diem_xac_minh=thoi_diem,
        vi_tri_anh_chu_ky=vi_tri_anh, ma_bam_anh_chu_ky=ma_bam_anh,
    )
    dong.trang_thai = enums.TrangThaiNguoiKy.DA_KY
    dong.ngay_ky = thoi_diem
    dong.chu_ky_hien_hanh = chu_ky
    dong.khoa_chong_trung_thao_tac = khoa_chong_trung
    dong.save(update_fields=["trang_thai", "ngay_ky", "chu_ky_hien_hanh", "khoa_chong_trung_thao_tac"])
    ghi_nhat_ky(nguoi, LOAI, dong.pk, "KY", trinh_ky=luot.trinh_ky, luot_trinh=luot, buoc_ky=dong,
                trang_thai_truoc=enums.TrangThaiNguoiKy.CHO_KY, trang_thai_sau=dong.trang_thai,
                chi_tiet=ghi_chu_ky, dia_chi_ip=dia_chi_ip,
                du_lieu_kem_theo={"chu_ky": chu_ky.pk, "khoa_ky": khoa.pk, "ky_tre_han": tre})
    _hoan_tat_neu_du(luot, cap, nguoi, thoi_diem)
    return SigningRequest.objects.get(pk=yeu_cau.pk)


@transaction.atomic
def tu_choi(yeu_cau, nguoi, *, ly_do_tu_choi, khoa_chong_trung, dia_chi_ip=None):
    if not ly_do_tu_choi.strip():
        raise SigningError(code="thieu_ly_do", detail="Không đồng ý ban hành phải nêu lý do.",
                           fields={"ly_do_tu_choi": ["Bắt buộc."]})
    if _thao_tac_lap(yeu_cau, nguoi, khoa_chong_trung):
        return SigningRequest.objects.get(pk=yeu_cau.pk)  # thao tác lặp
    luot = _khoa_luot_hien_hanh(yeu_cau)
    if _thao_tac_lap(yeu_cau, nguoi, khoa_chong_trung):
        return SigningRequest.objects.get(pk=yeu_cau.pk)
    dong = _dong_cua_toi(luot, nguoi)
    thoi_diem = timezone.now()
    dong.trang_thai = enums.TrangThaiNguoiKy.TU_CHOI
    dong.ngay_tu_choi = thoi_diem
    dong.ly_do_tu_choi = ly_do_tu_choi
    dong.khoa_chong_trung_thao_tac = khoa_chong_trung
    dong.save(update_fields=["trang_thai", "ngay_tu_choi", "ly_do_tu_choi", "khoa_chong_trung_thao_tac"])
    luot.trang_thai = enums.TrangThaiLuotTrinh.TU_CHOI
    luot.thoi_diem_tu_choi = thoi_diem
    luot.ly_do = ly_do_tu_choi
    luot.save(update_fields=["trang_thai", "thoi_diem_tu_choi", "ly_do", "update_at"])
    dung_cap_dang_mo(luot)
    yeu_cau = SigningRequest.objects.select_for_update().get(pk=yeu_cau.pk)
    yeu_cau.trang_thai = enums.TrangThaiYeuCau.TU_CHOI
    yeu_cau.ngay_tu_choi = thoi_diem
    yeu_cau.ly_do_tu_choi = ly_do_tu_choi
    yeu_cau.save(update_fields=["trang_thai", "ngay_tu_choi", "ly_do_tu_choi", "update_at"])
    ghi_nhat_ky(nguoi, LOAI, dong.pk, "TU_CHOI", trinh_ky=yeu_cau, luot_trinh=luot, buoc_ky=dong,
                trang_thai_truoc=enums.TrangThaiYeuCau.CHO_KY, trang_thai_sau=yeu_cau.trang_thai,
                chi_tiet=ly_do_tu_choi, dia_chi_ip=dia_chi_ip)
    thong_bao.su_kien(yeu_cau, luot, "TU_CHOI", nguoi)
    return yeu_cau


@transaction.atomic
def thu_hoi(yeu_cau, nguoi, *, khoa_chong_trung, dia_chi_ip=None):
    if _thao_tac_lap(yeu_cau, nguoi, khoa_chong_trung):
        return SigningRequest.objects.get(pk=yeu_cau.pk)  # thao tác lặp
    luot = _khoa_luot_hien_hanh(yeu_cau)
    if _thao_tac_lap(yeu_cau, nguoi, khoa_chong_trung):
        return SigningRequest.objects.get(pk=yeu_cau.pk)
    dong = SigningRequestStepSigner.objects.select_for_update().filter(
        buoc_ky__luot_trinh=luot, nguoi_ky=nguoi, trang_thai=enums.TrangThaiNguoiKy.DA_KY,
        chu_ky_hien_hanh__isnull=False,
    ).select_related("buoc_ky").order_by("-buoc_ky__thu_tu").first()
    if dong is None:
        raise ConflictError(code="chua_ky_khong_thu_hoi", detail="Bạn chưa ký nên không có chữ ký để thu hồi.")
    if dong.buoc_ky.trang_thai != enums.TrangThaiCapKy.DANG_KY:
        raise ConflictError(code="cap_da_dong_khong_thu_hoi",
                            detail="Cấp ký đã đóng và luồng đã sang cấp sau; muốn sửa hãy trả lại để sửa.")
    SigningRequestStep.objects.select_for_update().get(pk=dong.buoc_ky_id)
    chu_ky_cu = dong.chu_ky_hien_hanh_id
    dong.trang_thai = enums.TrangThaiNguoiKy.CHO_KY
    dong.ngay_ky = None
    dong.chu_ky_hien_hanh = None
    dong.khoa_chong_trung_thao_tac = khoa_chong_trung
    dong.save(update_fields=["trang_thai", "ngay_ky", "chu_ky_hien_hanh", "khoa_chong_trung_thao_tac"])
    ghi_nhat_ky(nguoi, LOAI, dong.pk, "THU_HOI_CHU_KY", trinh_ky=yeu_cau, luot_trinh=luot, buoc_ky=dong,
                trang_thai_truoc=enums.TrangThaiNguoiKy.DA_KY, trang_thai_sau=dong.trang_thai,
                dia_chi_ip=dia_chi_ip, du_lieu_kem_theo={"chu_ky_thu_hoi": chu_ky_cu})
    return SigningRequest.objects.get(pk=yeu_cau.pk)
