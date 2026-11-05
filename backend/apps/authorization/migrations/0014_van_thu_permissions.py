"""Đặt lại quyền nhóm Văn thư đúng 30 quyền (release_DDL.sql [VTQ]).

- Quyết định nhóm trưởng (02-03/11/2026): Văn thư xem, thêm, import văn bản đến/đi, xuất Excel văn bản đến,
  đổi hiệu lực qua change_hieu_luc_*; không sửa, xóa văn bản của người khác, không gửi mail toàn hệ thống;
  giữ các quyền chung của CBNV.
- Forward: nhóm VT (theo ma_nhom_quyen) chỉ còn đúng VAN_THU_PERMISSIONS; gỡ mọi lượt khác (kể cả quyền gán tay
  như view_nhomquyen), chèn lượt còn thiếu. Idempotent; không đụng nhóm khác.
- Reverse: đặt lại nhóm VT đúng danh sách seed trước [VTQ] (OLD_VAN_THU_PERMISSIONS).
"""
from django.db import migrations

GROUP_CODE = "VT"

# Bản chép cố định tại thời điểm tạo migration (test kiểm khớp release_DDL.sql).
VAN_THU_PERMISSIONS = [
    "view_donvi",
    "view_chucvu",
    "view_loaitailieubieumau",
    "view_list_cbnv",
    "change_self_cbnv",
    "view_vanbanden",
    "add_vanbanden",
    "import_vanbanden",
    "export_vanbanden",
    "change_hieu_luc_vanbanden",
    "view_vanbandi",
    "add_vanbandi",
    "import_vanbandi",
    "change_hieu_luc_vanbandi",
    "view_hoso",
    "view_tailieu",
    "view_trinhky",
    "send_trinhky",
    "add_trinhky",
    "view_all_trinhky",
    "view_congviec",
    "view_dept_congviec",
    "add_congviec",
    "change_congviec",
    "view_schedule_phonghop",
    "add_datphonghop",
    "change_own_datphonghop",
    "view_sinhnhat",
    "send_wish_sinhnhat",
    "use_aiassistant",
]

# Seed nhóm VT trước [VTQ]: 30 quyền trên cộng 13 quyền đã bỏ.
OLD_VAN_THU_PERMISSIONS = VAN_THU_PERMISSIONS + [
    "change_vanbanden",
    "delete_vanbanden",
    "send_mail_all_vanbanden",
    "change_vanbandi",
    "delete_vanbandi",
    "export_vanbandi",
    "send_mail_all_vanbandi",
    "add_hoso",
    "change_hoso",
    "toggle_status_hoso",
    "manage_documents_hoso",
    "add_tailieu",
    "change_tailieu",
]


def set_group_permissions(schema_editor, codenames):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            "DELETE FROM auth_group_permissions x USING auth_group g, auth_permission p "
            "WHERE x.group_id = g.id AND x.permission_id = p.id "
            "AND g.ma_nhom_quyen = %s AND NOT (p.codename = ANY(%s))",
            [GROUP_CODE, list(codenames)],
        )
        cursor.execute(
            "INSERT INTO auth_group_permissions (group_id, permission_id) "
            "SELECT g.id, p.id FROM auth_group g, auth_permission p "
            "WHERE g.ma_nhom_quyen = %s AND p.codename = ANY(%s) "
            "AND NOT EXISTS (SELECT 1 FROM auth_group_permissions x "
            "WHERE x.group_id = g.id AND x.permission_id = p.id)",
            [GROUP_CODE, list(codenames)],
        )


def apply_van_thu_permissions(apps, schema_editor):
    set_group_permissions(schema_editor, VAN_THU_PERMISSIONS)


def restore_old_van_thu_permissions(apps, schema_editor):
    set_group_permissions(schema_editor, OLD_VAN_THU_PERMISSIONS)


class Migration(migrations.Migration):

    dependencies = [
        ("authorization", "0013_add_view_all_trinhky_permission"),
    ]

    operations = [
        migrations.RunPython(apply_van_thu_permissions, restore_old_van_thu_permissions),
    ]
