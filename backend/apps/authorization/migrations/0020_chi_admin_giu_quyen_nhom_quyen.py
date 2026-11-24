"""Gỡ view/add/change/delete_nhomquyen khỏi mọi nhóm khác ADMIN và khỏi quyền gán thẳng cho người dùng (issue #846).

- Chỉ nhóm ADMIN được giữ quyền quản lý nhóm quyền; seed release_DDL.sql vốn chỉ cấp 4 quyền này cho ADMIN, lượt gán
  ở nhóm khác là gán tay trên trang Phân quyền.
- RbacBackend cộng cả quyền gán thẳng cho người dùng (accounts_employee_user_permissions), nên gỡ luôn ở đó: thành viên
  nhóm ADMIN vẫn có quyền qua nhóm, superuser vốn có mọi quyền.
- Idempotent; không đụng nhóm ADMIN và các quyền khác.
- Reverse không làm gì: không biết trước đó nhóm hoặc người dùng nào đã được gán tay.
"""
from django.db import migrations

CODENAMES = ["view_nhomquyen", "add_nhomquyen", "change_nhomquyen", "delete_nhomquyen"]


def remove_role_management_from_non_admin(apps, schema_editor):
    Employee = apps.get_model("accounts", "Employee")
    user_permissions_table = Employee._meta.get_field("user_permissions").remote_field.through._meta.db_table

    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            "DELETE FROM auth_group_permissions x USING auth_group g, auth_permission p "
            "WHERE x.group_id = g.id AND x.permission_id = p.id "
            "AND g.ma_nhom_quyen IS DISTINCT FROM 'ADMIN' AND p.codename = ANY(%s)",
            [CODENAMES],
        )
        cursor.execute(
            f"DELETE FROM {schema_editor.quote_name(user_permissions_table)} x USING auth_permission p "
            "WHERE x.permission_id = p.id AND p.codename = ANY(%s)",
            [CODENAMES],
        )


class Migration(migrations.Migration):

    dependencies = [
        ("authorization", "0019_van_thu_them_sua_ho_so"),
    ]

    operations = [
        migrations.RunPython(remove_role_management_from_non_admin, migrations.RunPython.noop),
    ]
