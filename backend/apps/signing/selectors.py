"""
Selector chỉ đọc của phân hệ Trình ký cho module khác (Dashboard Nhóm 1). Module khác gọi hàm này, không truy vấn
bảng `signing_*` trực tiếp (AGENTS.md mục 6).
"""

from django.db.models import Q
from django.db.models.functions import Coalesce
from django.utils import timezone

from . import enums
from .models import SigningRequest
from .services.trinh_ky import dang_cho_toi_ky
from .tich_hop.to_chuc import ten_hien_thi
from .tich_hop.van_ban import mo_ta_nhieu_ho_so

GIOI_HAN_GAN_DAY = 5
NHAN_TRANG_THAI = {
    enums.TrangThaiYeuCau.NHAP: "Nháp",
    enums.TrangThaiYeuCau.CHO_KY: "Chờ ký",
    enums.TrangThaiYeuCau.HOAN_THANH: "Đã ký",
    enums.TrangThaiYeuCau.TU_CHOI: "Từ chối",
    enums.TrangThaiYeuCau.HUY: "Đã hủy",
}


def ho_so_lien_quan(nguoi):
    """Hồ sơ người dùng tạo hoặc có tên trong luồng ký (kể cả người nhận/giao ủy quyền); không mở rộng theo quyền
    kiểm toán để Dashboard chỉ hiện việc của chính người đó."""
    return SigningRequest.objects.filter(
        Q(create_by=nguoi) | Q(luot_trinh_set__cap_ky_set__nguoi_ky_set__nguoi_ky=nguoi)
        | Q(luot_trinh_set__cap_ky_set__nguoi_ky_set__uy_quyen_tu=nguoi)
    ).distinct()


def tong_quan_dashboard(nguoi, gioi_han=GIOI_HAN_GAN_DAY):
    """
    {"so_cho_ky": số hồ sơ đang chờ người dùng ký, "gan_day": [phiếu gần nhất]}. Phiếu: id, tieu_de, nguoi_trinh,
    ngay_trinh (ISO; ngày gửi, chưa gửi thì ngày tạo; mới nhất trước), trang_thai (mã), nhan_trang_thai, can_toi_ky.
    """
    cho_toi = set(dang_cho_toi_ky(nguoi).values_list("pk", flat=True))
    ho_so = list(SigningRequest.objects.filter(pk__in=ho_so_lien_quan(nguoi).values("pk"))
                 .annotate(ngay_trinh=Coalesce("ngay_gui", "created_at")).select_related("create_by")
                 .order_by("-ngay_trinh", "-pk")[:gioi_han])
    mo_ta = mo_ta_nhieu_ho_so(ho_so)
    gan_day = []
    for h in ho_so:
        vb = mo_ta.get(h.pk, {})
        gan_day.append({
            "id": h.pk,
            "tieu_de": " — ".join(x for x in (vb.get("so_hieu"), vb.get("trich_yeu")) if x) or f"Hồ sơ #{h.pk}",
            "nguoi_trinh": ten_hien_thi(h.create_by),
            "ngay_trinh": timezone.localtime(h.ngay_trinh).isoformat(),
            "trang_thai": h.trang_thai,
            "nhan_trang_thai": NHAN_TRANG_THAI.get(h.trang_thai, h.trang_thai),
            "can_toi_ky": h.pk in cho_toi,
        })
    return {"so_cho_ky": len(cho_toi), "gan_day": gan_day}
