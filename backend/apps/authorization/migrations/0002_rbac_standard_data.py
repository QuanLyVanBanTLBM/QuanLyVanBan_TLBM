from django.db import migrations

from authorization.rbac_seed import (
    EXTRA_GROUP_PERMISSIONS,
    EXTRA_PERMISSIONS,
    GROUP_PERMISSIONS,
    GROUPS,
    PERMISSIONS,
)


def seed_rbac(apps, schema_editor):
    """
    Bổ sung phần còn thiếu của RBAC chuẩn (5 nhóm, quyền thao tác, ánh xạ) — idempotent.
    Dùng SQL thô vì auth.Permission của Django không biết cột module_ten (NOT NULL) trong DDL.
    """
    with schema_editor.connection.cursor() as cursor:
        for name, codename, module_ten in [*PERMISSIONS, *EXTRA_PERMISSIONS]:
            cursor.execute(
                "INSERT INTO auth_permission (name, codename, module_ten) "
                "SELECT %s, %s, %s WHERE NOT EXISTS (SELECT 1 FROM auth_permission WHERE codename = %s)",
                [name, codename, module_ten, codename],
            )
            cursor.execute(
                "UPDATE auth_permission SET module_ten = %s WHERE codename = %s AND module_ten = ''",
                [module_ten, codename],
            )

        for name, ma_nhom_quyen in GROUPS:
            cursor.execute(
                "INSERT INTO auth_group (name, ma_nhom_quyen) "
                "SELECT %s, %s WHERE NOT EXISTS (SELECT 1 FROM auth_group WHERE name = %s)",
                [name, ma_nhom_quyen, name],
            )
            cursor.execute(
                "UPDATE auth_group SET ma_nhom_quyen = %s "
                "WHERE name = %s AND ma_nhom_quyen IS NULL "
                "AND NOT EXISTS (SELECT 1 FROM auth_group WHERE ma_nhom_quyen = %s)",
                [ma_nhom_quyen, name, ma_nhom_quyen],
            )

        for mapping in (GROUP_PERMISSIONS, EXTRA_GROUP_PERMISSIONS):
            for group_name, codenames in mapping.items():
                for codename in codenames:
                    cursor.execute(
                        "INSERT INTO auth_group_permissions (group_id, permission_id) "
                        "SELECT g.id, p.id FROM auth_group g, auth_permission p "
                        "WHERE g.name = %s AND p.codename = %s "
                        "AND NOT EXISTS (SELECT 1 FROM auth_group_permissions x "
                        "WHERE x.group_id = g.id AND x.permission_id = p.id)",
                        [group_name, codename],
                    )


class Migration(migrations.Migration):

    dependencies = [
        ("authorization", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_rbac, migrations.RunPython.noop),
    ]
