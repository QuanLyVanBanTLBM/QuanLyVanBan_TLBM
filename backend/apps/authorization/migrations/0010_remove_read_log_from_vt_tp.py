"""Bỏ quyền xem nhật ký xem văn bản khỏi nhóm Văn thư và Trưởng phòng (release_DDL.sql [RLOG]).

- Nhật ký xem văn bản đến/đi chỉ ADMIN và BGD xem được (quyết định nhóm trưởng).
- Gỡ view_read_log_vanbanden, view_read_log_vanbandi khỏi VT và view_read_log_vanbanden khỏi TP (theo ma_nhom_quyen).
- Idempotent: chạy lại không đổi thêm gì; không đụng quyền của nhóm khác (TLBGD, KT, BGD, ADMIN giữ nguyên).
- Reverse gán lại đúng ba lượt này.
"""
from django.db import migrations

# (mã nhóm, codename) đã bị bỏ; bản chép cố định tại thời điểm tạo migration.
REMOVED = [
    ("VT", "view_read_log_vanbanden"),
    ("VT", "view_read_log_vanbandi"),
    ("TP", "view_read_log_vanbanden"),
]


def remove_read_log(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        for group_code, codename in REMOVED:
            cursor.execute(
                "DELETE FROM auth_group_permissions x USING auth_group g, auth_permission p "
                "WHERE x.group_id = g.id AND x.permission_id = p.id "
                "AND g.ma_nhom_quyen = %s AND p.codename = %s",
                [group_code, codename],
            )


def restore_read_log(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        for group_code, codename in REMOVED:
            cursor.execute(
                "INSERT INTO auth_group_permissions (group_id, permission_id) "
                "SELECT g.id, p.id FROM auth_group g, auth_permission p "
                "WHERE g.ma_nhom_quyen = %s AND p.codename = %s "
                "AND NOT EXISTS (SELECT 1 FROM auth_group_permissions x "
                "WHERE x.group_id = g.id AND x.permission_id = p.id)",
                [group_code, codename],
            )


class Migration(migrations.Migration):

    dependencies = [
        ("authorization", "0009_add_export_cbnv_permission"),
    ]

    operations = [
        migrations.RunPython(remove_read_log, restore_read_log),
    ]
