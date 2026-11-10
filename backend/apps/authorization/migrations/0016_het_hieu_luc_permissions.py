"""Quyền xem và xử lý văn bản hết hiệu lực đến/đi (cùng seed auth_permission, auth_group_permissions của release_DDL.sql [XHHL]).

- Thêm view_het_hieu_luc_vanbanden, view_het_hieu_luc_vanbandi; gán cho nhóm ADMIN và VT (theo ma_nhom_quyen).
- Thêm manage_het_hieu_luc_vanbanden, manage_het_hieu_luc_vanbandi (sửa, xóa văn bản hết hiệu lực); gán cho nhóm ADMIN.
- Idempotent: chỉ chèn quyền và lượt gán còn thiếu, không sửa dữ liệu phân quyền khác.
- Reverse không xóa: quyền có thể đã được gán thêm cho nhóm khác.
"""
from django.db import migrations

# Bản chép cố định tại thời điểm tạo migration (test kiểm khớp release_DDL.sql).
PERMISSIONS = [
    ("Xem văn bản đến hết hiệu lực", "view_het_hieu_luc_vanbanden", "Văn bản đến"),
    ("Xử lý (sửa, xóa) văn bản đến hết hiệu lực", "manage_het_hieu_luc_vanbanden", "Văn bản đến"),
    ("Xem văn bản đi hết hiệu lực", "view_het_hieu_luc_vanbandi", "Văn bản đi"),
    ("Xử lý (sửa, xóa) văn bản đi hết hiệu lực", "manage_het_hieu_luc_vanbandi", "Văn bản đi"),
]
GROUP_CODES = {
    "view_het_hieu_luc_vanbanden": ["ADMIN", "VT"],
    "view_het_hieu_luc_vanbandi": ["ADMIN", "VT"],
    "manage_het_hieu_luc_vanbanden": ["ADMIN"],
    "manage_het_hieu_luc_vanbandi": ["ADMIN"],
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
        ("authorization", "0015_remove_delegate_trinhky"),
    ]

    operations = [
        migrations.RunPython(add_permissions, migrations.RunPython.noop),
    ]
