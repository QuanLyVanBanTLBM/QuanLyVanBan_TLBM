from django.db import migrations

# DDL Phase 7 Trình ký (PR #111, Issue #80): nhóm Trưởng phòng được quản lý quy trình trình ký của đơn vị mình.
TP_CODE = "TP"
CODENAME = "manage_signing_process"


def grant_tp_manage_signing_process(apps, schema_editor):
    """Gán manage_signing_process cho nhóm Trưởng phòng trên DB đã seed từ trước (idempotent)."""
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO auth_group_permissions (group_id, permission_id) "
            "SELECT g.id, p.id FROM auth_group g, auth_permission p "
            "WHERE g.ma_nhom_quyen = %s AND p.codename = %s "
            "AND NOT EXISTS (SELECT 1 FROM auth_group_permissions x "
            "WHERE x.group_id = g.id AND x.permission_id = p.id)",
            [TP_CODE, CODENAME],
        )


class Migration(migrations.Migration):

    dependencies = [
        ("authorization", "0003_remove_vanbanmat_permissions"),
    ]

    operations = [
        migrations.RunPython(grant_tp_manage_signing_process, migrations.RunPython.noop),
    ]
