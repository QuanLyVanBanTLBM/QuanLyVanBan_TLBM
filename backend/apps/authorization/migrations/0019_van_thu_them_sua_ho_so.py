"""Cấp add_hoso, change_hoso cho nhóm VT (release_DDL.sql [VTHS], issue #647).

- Idempotent: chỉ chèn lượt gán còn thiếu, không đổi nhóm khác và không đụng quyền gán tay.
- Reverse gỡ đúng hai lượt gán khỏi nhóm VT (trả về trạng thái sau migration 0018).
"""
from django.db import migrations

CODENAMES = ["add_hoso", "change_hoso"]


def grant_to_van_thu(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO auth_group_permissions (group_id, permission_id) "
            "SELECT g.id, p.id FROM auth_group g, auth_permission p "
            "WHERE g.ma_nhom_quyen = 'VT' AND p.codename = ANY(%s) "
            "AND NOT EXISTS (SELECT 1 FROM auth_group_permissions x "
            "WHERE x.group_id = g.id AND x.permission_id = p.id)",
            [CODENAMES],
        )


def revoke_from_van_thu(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            "DELETE FROM auth_group_permissions WHERE group_id IN "
            "(SELECT id FROM auth_group WHERE ma_nhom_quyen = 'VT') AND permission_id IN "
            "(SELECT id FROM auth_permission WHERE codename = ANY(%s))",
            [CODENAMES],
        )


class Migration(migrations.Migration):

    dependencies = [
        ("authorization", "0018_remove_unused_permissions"),
    ]

    operations = [
        migrations.RunPython(grant_to_van_thu, revoke_from_van_thu),
    ]
