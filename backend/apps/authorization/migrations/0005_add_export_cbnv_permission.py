from django.db import migrations

NAME = "Xuất Excel danh sách CBNV"
CODENAME = "export_cbnv"
MODULE_TEN = "Cán bộ nhân viên"
GROUP_CODES = ["TP", "BGD", "ADMIN"]
GROUP_NAMES = ["Trưởng phòng", "Ban Giám đốc", "Quản trị hệ thống"]


def add_export_cbnv_permission(apps, schema_editor):
    """
    Thêm quyền export_cbnv và gán cho 3 nhóm Trưởng phòng (TP), Ban Giám đốc (BGD),
    Quản trị hệ thống (ADMIN) trên DB đã seed từ trước (idempotent).
    """
    with schema_editor.connection.cursor() as cursor:
        # 1. Thêm permission nếu chưa có
        cursor.execute(
            "INSERT INTO auth_permission (name, codename, module_ten) "
            "SELECT %s, %s, %s "
            "WHERE NOT EXISTS (SELECT 1 FROM auth_permission WHERE codename = %s)",
            [NAME, CODENAME, MODULE_TEN, CODENAME],
        )
        cursor.execute(
            "UPDATE auth_permission SET module_ten = %s WHERE codename = %s AND (module_ten = '' OR module_ten IS NULL)",
            [MODULE_TEN, CODENAME],
        )

        # 2. Gán quyền cho 3 nhóm (TP, BGD, ADMIN)
        for code, name in zip(GROUP_CODES, GROUP_NAMES):
            cursor.execute(
                "INSERT INTO auth_group_permissions (group_id, permission_id) "
                "SELECT g.id, p.id FROM auth_group g, auth_permission p "
                "WHERE (g.ma_nhom_quyen = %s OR g.name = %s) AND p.codename = %s "
                "AND NOT EXISTS (SELECT 1 FROM auth_group_permissions x "
                "WHERE x.group_id = g.id AND x.permission_id = p.id)",
                [code, name, CODENAME],
            )


def remove_export_cbnv_permission(apps, schema_editor):
    """Gỡ quyền export_cbnv và các lượt phân quyền tương ứng."""
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            "DELETE FROM auth_group_permissions "
            "WHERE permission_id IN (SELECT id FROM auth_permission WHERE codename = %s)",
            [CODENAME],
        )
        cursor.execute(
            "DELETE FROM auth_permission WHERE codename = %s",
            [CODENAME],
        )


class Migration(migrations.Migration):

    dependencies = [
        ("authorization", "0004_grant_tp_manage_signing_process"),
    ]

    operations = [
        migrations.RunPython(add_export_cbnv_permission, remove_export_cbnv_permission),
    ]
