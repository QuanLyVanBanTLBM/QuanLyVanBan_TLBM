import copy

from django.db import migrations, models


def ensure_rbac_columns(apps, schema_editor):
    """
    Đưa auth_permission / auth_group về đúng SQL_Fix4 trên mọi nguồn DB:
    - DB dựng từ DDL: đã đủ cột, các bước dưới là no-op.
    - DB do Django tạo (dev, test): bổ sung module_ten, ma_nhom_quyen, cho phép content_type_id NULL.
    """
    from django.contrib.auth.models import Permission

    connection = schema_editor.connection
    introspection = connection.introspection

    # 1. content_type_id NULL (làm trước khi thêm cột lạ vì SQLite dựng lại bảng theo model chuẩn)
    old_field = Permission._meta.get_field("content_type")
    new_field = copy.copy(old_field)
    new_field.null = True
    schema_editor.alter_field(Permission, old_field, new_field)

    with connection.cursor() as cursor:
        permission_columns = {c.name for c in introspection.get_table_description(cursor, "auth_permission")}
        group_columns = {c.name for c in introspection.get_table_description(cursor, "auth_group")}
        permission_constraints = introspection.get_constraints(cursor, "auth_permission")
        group_constraints = introspection.get_constraints(cursor, "auth_group")

    def has_unique_on(constraints, column):
        return any(c["unique"] and c["columns"] == [column] for c in constraints.values())

    if "module_ten" not in permission_columns:
        schema_editor.execute("ALTER TABLE auth_permission ADD COLUMN module_ten varchar(150) NOT NULL DEFAULT ''")
    if not has_unique_on(permission_constraints, "codename"):
        schema_editor.execute("CREATE UNIQUE INDEX uq_auth_permission_codename ON auth_permission (codename)")

    if "ma_nhom_quyen" not in group_columns:
        schema_editor.execute("ALTER TABLE auth_group ADD COLUMN ma_nhom_quyen varchar(50) NULL")
    if not has_unique_on(group_constraints, "ma_nhom_quyen"):
        schema_editor.execute("CREATE UNIQUE INDEX uq_auth_group_ma_nhom_quyen ON auth_group (ma_nhom_quyen)")


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.CreateModel(
            name="GroupInfo",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=150, unique=True)),
                ("ma_nhom_quyen", models.CharField(blank=True, max_length=50, null=True, unique=True)),
            ],
            options={"db_table": "auth_group", "managed": False},
        ),
        migrations.CreateModel(
            name="PermissionInfo",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
                ("codename", models.CharField(max_length=100, unique=True)),
                ("module_ten", models.CharField(max_length=150)),
                ("content_type_id", models.BigIntegerField(blank=True, null=True)),
            ],
            options={"db_table": "auth_permission", "ordering": ["id"], "managed": False},
        ),
        migrations.RunPython(ensure_rbac_columns, migrations.RunPython.noop),
    ]
