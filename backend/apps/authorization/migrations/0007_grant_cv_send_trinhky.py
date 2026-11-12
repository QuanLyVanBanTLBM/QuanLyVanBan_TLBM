from django.db import migrations

# Issue #226 (release_DDL.sql [CVTK]): nhóm Chuyên viên tự gửi hồ sơ trình ký do mình tạo.
CV_CODE = "CV"
CODENAME = "send_trinhky"


def grant_cv_send_trinhky(apps, schema_editor):
    """Gán send_trinhky cho nhóm Chuyên viên trên DB đã seed từ trước (idempotent)."""
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO auth_group_permissions (group_id, permission_id) "
            "SELECT g.id, p.id FROM auth_group g, auth_permission p "
            "WHERE g.ma_nhom_quyen = %s AND p.codename = %s "
            "AND NOT EXISTS (SELECT 1 FROM auth_group_permissions x "
            "WHERE x.group_id = g.id AND x.permission_id = p.id)",
            [CV_CODE, CODENAME],
        )


def revoke_cv_send_trinhky(apps, schema_editor):
    """Rollback: bỏ send_trinhky khỏi nhóm Chuyên viên."""
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            "DELETE FROM auth_group_permissions x USING auth_group g, auth_permission p "
            "WHERE x.group_id = g.id AND x.permission_id = p.id "
            "AND g.ma_nhom_quyen = %s AND p.codename = %s",
            [CV_CODE, CODENAME],
        )


class Migration(migrations.Migration):

    dependencies = [
        ("authorization", "0006_align_permission_defaults_and_labels"),
    ]

    operations = [
        migrations.RunPython(grant_cv_send_trinhky, revoke_cv_send_trinhky),
    ]
