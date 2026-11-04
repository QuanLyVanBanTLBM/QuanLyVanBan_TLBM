from django.db import migrations

# Ủy quyền ký đã bỏ (#374, #383); gỡ quyền delegate_trinhky khỏi DB đã seed từ trước (issue #519).
CODENAME = "delegate_trinhky"


def remove_delegate_trinhky(apps, schema_editor):
    """Xóa quyền delegate_trinhky cùng các dòng gán cho nhóm và người dùng (idempotent)."""
    Employee = apps.get_model("accounts", "Employee")
    user_permissions_table = Employee._meta.get_field("user_permissions").remote_field.through._meta.db_table
    subquery = "SELECT id FROM auth_permission WHERE codename = %s"

    with schema_editor.connection.cursor() as cursor:
        cursor.execute(f"DELETE FROM auth_group_permissions WHERE permission_id IN ({subquery})", [CODENAME])
        cursor.execute(
            f"DELETE FROM {schema_editor.quote_name(user_permissions_table)} WHERE permission_id IN ({subquery})",
            [CODENAME],
        )
        cursor.execute("DELETE FROM auth_permission WHERE codename = %s", [CODENAME])


class Migration(migrations.Migration):

    dependencies = [
        ("authorization", "0014_van_thu_permissions"),
        ("accounts", "0002_position_import_permission"),
    ]

    operations = [
        migrations.RunPython(remove_delegate_trinhky, migrations.RunPython.noop),
    ]
