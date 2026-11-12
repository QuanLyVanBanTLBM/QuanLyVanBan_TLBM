from django.db import migrations

# Ba mã quyền không có chức năng nào dùng; gỡ khỏi DB đã seed từ trước (idempotent).
CODENAMES = ["toggle_status_hoso", "manage_documents_hoso", "send_wish_sinhnhat"]


def remove_unused_permissions(apps, schema_editor):
    """Xóa các quyền cùng các dòng gán cho nhóm và người dùng."""
    Employee = apps.get_model("accounts", "Employee")
    user_permissions_table = Employee._meta.get_field("user_permissions").remote_field.through._meta.db_table
    subquery = "SELECT id FROM auth_permission WHERE codename = ANY(%s)"

    with schema_editor.connection.cursor() as cursor:
        cursor.execute(f"DELETE FROM auth_group_permissions WHERE permission_id IN ({subquery})", [CODENAMES])
        cursor.execute(
            f"DELETE FROM {schema_editor.quote_name(user_permissions_table)} WHERE permission_id IN ({subquery})",
            [CODENAMES],
        )
        cursor.execute("DELETE FROM auth_permission WHERE codename = ANY(%s)", [CODENAMES])


class Migration(migrations.Migration):

    dependencies = [
        ("authorization", "0017_them_van_ban_han_che_permissions"),
        ("accounts", "0002_position_import_permission"),
    ]

    operations = [
        migrations.RunPython(remove_unused_permissions, migrations.RunPython.noop),
    ]
