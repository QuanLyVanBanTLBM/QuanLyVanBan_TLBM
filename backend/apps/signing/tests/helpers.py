from accounts.models import Position
from django.apps import apps
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db.models import Max
from organizations.models import DonVi, KhoiKhuVuc

from authorization.models import PermissionInfo
from signing.models import SigningProcess
from signing.permissions import QUAN_LY_QUY_TRINH


def tao_chuc_vu(ten="Chức vụ thử nghiệm"):
    """Chức vụ thật ở accounts_position (Nhóm 7); cột chuc_vu_id của Trình ký là FK."""
    thu_tu = (Position.objects.aggregate(m=Max("display_order"))["m"] or 0) + 1
    return Position.objects.create(display_order=thu_tu, name=f"{ten} {thu_tu}")


def tao_don_vi(ten="Đơn vị thử nghiệm"):
    """Đơn vị thật ở organizations_donvi (Nhóm 7); cột don_vi_id, don_vi_ap_dung_id của Trình ký là FK."""
    khoi = KhoiKhuVuc.objects.order_by("pk").first() or KhoiKhuVuc.objects.create(ten="Khối thử nghiệm")
    stt = (DonVi.objects.aggregate(m=Max("stt_uu_tien"))["m"] or 0) + 1
    return DonVi.objects.create(khoi=khoi, stt_uu_tien=stt, ten=f"{ten} {stt}")


def cap_quyen(user, *codenames):
    """
    Gán quyền riêng theo codename trần của DDL. DB dựng từ DDL hoặc có seed RBAC của Nhóm 7 đã có sẵn
    quyền; DB test dựng bằng migration của nhánh thì chưa có, nên tạo tạm gắn content type của app signing.
    """
    for codename in codenames:
        permission = Permission.objects.filter(codename=codename).order_by().first()
        if permission is None:
            permission_info = PermissionInfo.objects.create(
                codename=codename, name=codename,
                module_ten="Trình ký",
                content_type_id=ContentType.objects.get_for_model(SigningProcess).pk,
            )
            permission = Permission.objects.get(pk=permission_info.pk)
        user.user_permissions.add(permission)
        if codename == QUAN_LY_QUY_TRINH:
            them_vao_nhom_quan_tri(user)


def them_vao_nhom_quan_tri(user):
    """
    Khi có app `authorization` của Nhóm 7, người quản lý quy trình công ty phải thuộc nhóm `ADMIN`
    (quyền riêng chưa đủ, xem `tich_hop.to_chuc.la_quan_tri`). Nhánh chưa có app này thì bỏ qua.
    """
    if not apps.is_installed("authorization"):
        return
    group_info = apps.get_model("authorization", "GroupInfo")
    info = group_info.objects.filter(ma_nhom_quyen="ADMIN").first()
    if info is None:
        group = Group.objects.create(name="Quan tri he thong (test)")
        group_info.objects.filter(pk=group.pk).update(ma_nhom_quyen="ADMIN")
    else:
        group = Group.objects.get(pk=info.pk)
    user.groups.add(group)


def dat_anh_chu_ky(user, anh=None):
    """Gán ảnh chữ ký cá nhân phía máy chủ (signing_user_signature) cho người ký trong test; mặc định ảnh PNG mẫu."""
    import io

    from PIL import Image

    from signing import crypto
    from signing.models import SigningUserSignature
    from signing.storage import get_storage

    if anh is None:
        buf = io.BytesIO()
        Image.new("RGBA", (80, 30), (0, 0, 200, 255)).save(buf, format="PNG")
        anh = buf.getvalue()
    meta = get_storage().save_bytes(anh, "anh_chu_ky_nguoi_dung", "png")
    SigningUserSignature.objects.update_or_create(nguoi_dung=user, defaults={
        "vi_tri_tep": meta.vi_tri_luu_tep, "ma_bam": crypto.sha256_hex(anh), "dung_luong_bytes": meta.kich_thuoc})
    return anh
