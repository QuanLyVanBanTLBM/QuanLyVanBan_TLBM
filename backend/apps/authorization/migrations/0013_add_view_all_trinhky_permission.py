from django.db import migrations

NAME = "Xem tất cả hồ sơ trình ký"
CODENAME = "view_all_trinhky"
MODULE_TEN = "Trình ký"
GROUP_CODES = ["VT", "BGD", "ADMIN"]
GROUP_NAMES = ["Văn thư", "Ban Giám đốc", "Quản trị hệ thống"]


def add_view_all_trinhky(apps, schema_editor):
    """
    Thêm quyền view_all_trinhky và gán cho Văn thư (VT), Ban Giám đốc (BGD), Quản trị hệ thống (ADMIN)
    trên DB đã seed từ trước (idempotent).
    """
    with schema_editor.connection.cursor() as cursor:
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
        for code, name in zip(GROUP_CODES, GROUP_NAMES):
            cursor.execute(
                "INSERT INTO auth_group_permissions (group_id, permission_id) "
                "SELECT g.id, p.id FROM auth_group g, auth_permission p "
                "WHERE (g.ma_nhom_quyen = %s OR g.name = %s) AND p.codename = %s "
                "AND NOT EXISTS (SELECT 1 FROM auth_group_permissions x "
                "WHERE x.group_id = g.id AND x.permission_id = p.id)",
                [code, name, CODENAME],
            )


def remove_view_all_trinhky(apps, schema_editor):
    """Gỡ quyền view_all_trinhky và các lượt phân quyền tương ứng."""
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            "DELETE FROM auth_group_permissions "
            "WHERE permission_id IN (SELECT id FROM auth_permission WHERE codename = %s)",
            [CODENAME],
        )
        cursor.execute("DELETE FROM auth_permission WHERE codename = %s", [CODENAME])


class Migration(migrations.Migration):

    dependencies = [
        ("authorization", "0012_grant_export_donvi_tp_bgd"),
    ]

    operations = [
        migrations.RunPython(add_view_all_trinhky, remove_view_all_trinhky),
    ]
