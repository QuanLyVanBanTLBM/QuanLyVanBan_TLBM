from django.apps import apps
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

from signing.models import SigningProcess
from signing.permissions import QUAN_LY_QUY_TRINH


def cap_quyen(user, *codenames):
    """
    Gán quyền riêng theo codename trần của DDL. DB dựng từ DDL hoặc có seed RBAC của Nhóm 7 đã có sẵn
    quyền; DB test dựng bằng migration của nhánh thì chưa có, nên tạo tạm gắn content type của app signing.
    """
    for codename in codenames:
        permission = Permission.objects.filter(codename=codename).order_by().first()
        if permission is None:
            permission = Permission.objects.create(
                codename=codename, name=codename,
                content_type=ContentType.objects.get_for_model(SigningProcess),
            )
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

