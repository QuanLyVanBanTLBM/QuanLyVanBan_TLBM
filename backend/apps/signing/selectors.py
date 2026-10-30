"""
Selector chỉ đọc của phân hệ Trình ký cho module khác (Dashboard Nhóm 1). Module khác gọi hàm này, không truy vấn
bảng `signing_*` trực tiếp (AGENTS.md mục 6).
"""

from django.db.models import OuterRef, Q, Subquery
from django.db.models.functions import Coalesce
from django.utils import timezone

from . import enums
from .models import SigningAttempt, SigningRequest
from .services.trinh_ky import dang_cho_toi_ky
from .tich_hop.to_chuc import ten_hien_thi
from .tich_hop.van_ban import mo_ta_nhieu_ho_so

GIOI_HAN_GAN_DAY = 5
NHAN_TRANG_THAI = {
    enums.TrangThaiYeuCau.NHAP: "Nháp",
    enums.TrangThaiYeuCau.CHO_KY: "Đang chờ ký",
    enums.TrangThaiYeuCau.HOAN_THANH: "Hoàn tất duyệt nội bộ",
    enums.TrangThaiYeuCau.TU_CHOI: "Đã từ chối",
    enums.TrangThaiYeuCau.HUY: "Đã hủy",
    enums.TrangThaiLuotTrinh.YEU_CAU_SUA: "Chờ người trình sửa",
}


def ho_so_lien_quan(nguoi):
    """Hồ sơ người dùng tạo hoặc có tên trong luồng ký ; không mở rộng theo quyền
    kiểm toán để Dashboard chỉ hiện việc của chính người đó."""
    return SigningRequest.objects.filter(
        Q(create_by=nguoi) | Q(luot_trinh_set__cap_ky_set__nguoi_ky_set__nguoi_ky=nguoi)
    ).distinct()


def tong_quan_dashboard(nguoi, gioi_han=GIOI_HAN_GAN_DAY):
    """
    {"so_cho_ky": số hồ sơ đang chờ người dùng ký, "gan_day": [phiếu gần nhất]}. Phiếu: id, tieu_de, nguoi_trinh,
    ngay_trinh (ISO; ngày gửi, chưa gửi thì ngày tạo; mới nhất trước), trang_thai (mã), nhan_trang_thai, can_toi_ky.
    """
    cho_toi = set(dang_cho_toi_ky(nguoi).values_list("pk", flat=True))
    luot_cuoi = SigningAttempt.objects.filter(trinh_ky_id=OuterRef("pk")).order_by("-so_luot", "-pk").values("trang_thai")[:1]
    ho_so = list(SigningRequest.objects.filter(pk__in=ho_so_lien_quan(nguoi).values("pk"))
                 .annotate(trang_thai_luot=Subquery(luot_cuoi))
                 .annotate(ngay_trinh=Coalesce("ngay_gui", "created_at")).select_related("create_by")
                 .order_by("-ngay_trinh", "-pk")[:gioi_han])
    mo_ta = mo_ta_nhieu_ho_so(ho_so)
    gan_day = []
    for h in ho_so:
        vb = mo_ta.get(h.pk, {})
        trang_thai_hien_thi = h.trang_thai
        if (h.trang_thai == enums.TrangThaiYeuCau.CHO_KY
                and h.trang_thai_luot == enums.TrangThaiLuotTrinh.YEU_CAU_SUA):
            trang_thai_hien_thi = enums.TrangThaiLuotTrinh.YEU_CAU_SUA
        gan_day.append({
            "id": h.pk,
            "tieu_de": " — ".join(x for x in (vb.get("so_hieu"), vb.get("trich_yeu")) if x) or f"Hồ sơ #{h.pk}",
            "nguoi_trinh": ten_hien_thi(h.create_by),
            "ngay_trinh": timezone.localtime(h.ngay_trinh).isoformat(),
            "trang_thai": h.trang_thai,
            "trang_thai_luot": h.trang_thai_luot,
            "nhan_trang_thai": NHAN_TRANG_THAI.get(trang_thai_hien_thi, trang_thai_hien_thi),
            "can_toi_ky": h.pk in cho_toi,
        })
    return {"so_cho_ky": len(cho_toi), "gan_day": gan_day}
