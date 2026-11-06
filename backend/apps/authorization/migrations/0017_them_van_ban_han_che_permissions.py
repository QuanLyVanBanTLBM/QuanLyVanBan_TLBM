"""Quyền thêm văn bản đến/đi phạm vi Hạn chế (cùng seed auth_permission, auth_group_permissions của release_DDL.sql [TVHC]).

- Thêm add_han_che_vanbanden, add_han_che_vanbandi; gán cho nhóm ADMIN và VT (theo ma_nhom_quyen).
- Idempotent: chỉ chèn quyền và lượt gán còn thiếu, không sửa dữ liệu phân quyền khác.
- Reverse không xóa: quyền có thể đã được gán thêm cho nhóm khác.
"""
from django.db import migrations

# Bản chép cố định tại thời điểm tạo migration (test kiểm khớp release_DDL.sql).
PERMISSIONS = [
    ("Thêm văn bản đến hạn chế", "add_han_che_vanbanden", "Văn bản đến"),
    ("Thêm văn bản đi hạn chế", "add_han_che_vanbandi", "Văn bản đi"),
]
GROUP_CODES = {
    "add_han_che_vanbanden": ["ADMIN", "VT"],
    "add_han_che_vanbandi": ["ADMIN", "VT"],
}


def add_permissions(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        for name, codename, module_ten in PERMISSIONS:
            cursor.execute(
                "INSERT INTO auth_permission (name, codename, module_ten) "
                "SELECT %s, %s, %s WHERE NOT EXISTS (SELECT 1 FROM auth_permission WHERE codename = %s)",
                [name, codename, module_ten, codename],
            )
            for group_code in GROUP_CODES[codename]:
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
        ("authorization", "0016_het_hieu_luc_permissions"),
    ]

    operations = [
        migrations.RunPython(add_permissions, migrations.RunPython.noop),
    ]
