from django.db import migrations

# DDL base bỏ văn bản mật (PR #81, Issue #83): gỡ 4 quyền khỏi DB đã seed từ trước.
VANBANMAT_CODENAMES = ("view_vanbanmat", "add_vanbanmat", "change_vanbanmat", "delete_vanbanmat")


def remove_vanbanmat_permissions(apps, schema_editor):
    """Xóa 4 quyền văn bản mật cùng các dòng gán cho nhóm và người dùng (idempotent)."""
    Employee = apps.get_model("accounts", "Employee")
    user_permissions_table = Employee._meta.get_field("user_permissions").remote_field.through._meta.db_table
    placeholders = ", ".join(["%s"] * len(VANBANMAT_CODENAMES))
    subquery = f"SELECT id FROM auth_permission WHERE codename IN ({placeholders})"

    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            f"DELETE FROM auth_group_permissions WHERE permission_id IN ({subquery})", VANBANMAT_CODENAMES
        )
        cursor.execute(
            f"DELETE FROM {schema_editor.quote_name(user_permissions_table)} WHERE permission_id IN ({subquery})",
            VANBANMAT_CODENAMES,
        )
        cursor.execute(f"DELETE FROM auth_permission WHERE codename IN ({placeholders})", VANBANMAT_CODENAMES)


class Migration(migrations.Migration):

    dependencies = [
        ("authorization", "0002_rbac_standard_data"),
        ("accounts", "0002_position_import_permission"),
    ]

    operations = [
        migrations.RunPython(remove_vanbanmat_permissions, migrations.RunPython.noop),
    ]
