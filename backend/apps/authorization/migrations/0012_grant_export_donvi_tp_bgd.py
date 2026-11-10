from django.db import migrations

CODENAME = "export_donvi"
GROUP_CODES = ["TP", "BGD"]
GROUP_NAMES = ["Trưởng phòng", "Ban Giám đốc"]


def grant_export_donvi(apps, schema_editor):
    """Gán export_donvi cho nhóm Trưởng phòng (TP) và Ban Giám đốc (BGD) trên DB đã seed (idempotent)."""
    with schema_editor.connection.cursor() as cursor:
        for code, name in zip(GROUP_CODES, GROUP_NAMES):
            cursor.execute(
                "INSERT INTO auth_group_permissions (group_id, permission_id) "
                "SELECT g.id, p.id FROM auth_group g, auth_permission p "
                "WHERE (g.ma_nhom_quyen = %s OR g.name = %s) AND p.codename = %s "
                "AND NOT EXISTS (SELECT 1 FROM auth_group_permissions x "
                "WHERE x.group_id = g.id AND x.permission_id = p.id)",
                [code, name, CODENAME],
            )


def revoke_export_donvi(apps, schema_editor):
    """Gỡ export_donvi khỏi nhóm TP và BGD (ADMIN giữ nguyên)."""
    with schema_editor.connection.cursor() as cursor:
        for code, name in zip(GROUP_CODES, GROUP_NAMES):
            cursor.execute(
                "DELETE FROM auth_group_permissions USING auth_group g, auth_permission p "
                "WHERE auth_group_permissions.group_id = g.id AND auth_group_permissions.permission_id = p.id "
                "AND (g.ma_nhom_quyen = %s OR g.name = %s) AND p.codename = %s",
                [code, name, CODENAME],
            )


class Migration(migrations.Migration):

    dependencies = [
        ("authorization", "0011_change_hieu_luc_permissions"),
    ]

    operations = [
        migrations.RunPython(grant_export_donvi, revoke_export_donvi),
    ]
