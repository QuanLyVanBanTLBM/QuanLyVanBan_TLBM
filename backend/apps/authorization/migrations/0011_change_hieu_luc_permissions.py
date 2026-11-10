"""Quyền đổi hiệu lực văn bản đến/đi (cùng seed auth_permission, auth_group_permissions của release_DDL.sql).

- Thêm change_hieu_luc_vanbanden, change_hieu_luc_vanbandi; gán cho nhóm ADMIN và VT (theo ma_nhom_quyen).
- Idempotent: chỉ chèn quyền và lượt gán còn thiếu, không sửa dữ liệu phân quyền khác.
- Reverse không xóa: quyền có thể đã được gán thêm cho nhóm khác.
"""
from django.db import migrations

# Bản chép cố định tại thời điểm tạo migration (test kiểm khớp release_DDL.sql).
PERMISSIONS = [
    ("Đổi hiệu lực văn bản đến", "change_hieu_luc_vanbanden", "Văn bản đến"),
    ("Đổi hiệu lực văn bản đi", "change_hieu_luc_vanbandi", "Văn bản đi"),
]
GROUP_CODES = ["ADMIN", "VT"]


def add_permissions(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        for name, codename, module_ten in PERMISSIONS:
            cursor.execute(
                "INSERT INTO auth_permission (name, codename, module_ten) "
                "SELECT %s, %s, %s WHERE NOT EXISTS (SELECT 1 FROM auth_permission WHERE codename = %s)",
                [name, codename, module_ten, codename],
            )
            for group_code in GROUP_CODES:
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
        ("authorization", "0010_remove_read_log_from_vt_tp"),
    ]

    operations = [
        migrations.RunPython(add_permissions, migrations.RunPython.noop),
    ]
