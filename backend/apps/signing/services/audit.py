from ..models import SigningAuditLog


def ghi_nhat_ky(
    nguoi_thuc_hien,
    loai_doi_tuong,
    ma_doi_tuong,
    hanh_dong,
    *,
    trinh_ky=None,
    luot_trinh=None,
    buoc_ky=None,
    trang_thai_truoc="",
    trang_thai_sau="",
    chi_tiet="",
    du_lieu_kem_theo=None,
    dia_chi_ip=None,
):
    """Ghi một dòng nhật ký; gọi trong cùng transaction với hành động được ghi."""
    return SigningAuditLog.objects.create(
        nguoi_thuc_hien=nguoi_thuc_hien,
        loai_doi_tuong=loai_doi_tuong,
        ma_doi_tuong=ma_doi_tuong,
        hanh_dong=hanh_dong,
        trinh_ky=trinh_ky,
        luot_trinh=luot_trinh,
        buoc_ky=buoc_ky,
        trang_thai_truoc=trang_thai_truoc,
        trang_thai_sau=trang_thai_sau,
        chi_tiet=chi_tiet,
        du_lieu_kem_theo=du_lieu_kem_theo,
        dia_chi_ip=dia_chi_ip,
    )
