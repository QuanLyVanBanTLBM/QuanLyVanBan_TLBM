from django.db import migrations

# release_DDL.sql khai FK employee_id của accounts_employee_assignment có ON DELETE CASCADE ở mức DB.
# Django chỉ tạo FK không có ON DELETE (xóa dây chuyền ở tầng ứng dụng). DB dựng từ DDL đã khớp nên bước này tự bỏ qua.
CASCADE_FOREIGN_KEYS = [
    ("accounts_employee_assignment", "employee_id", "accounts_employee"),
]


def foreign_keys(cursor, table):
    cursor.execute(
        "SELECT c.conname, "
        "(SELECT array_agg(a.attname::text) FROM pg_attribute a WHERE a.attrelid = c.conrelid AND a.attnum = ANY (c.conkey)), "
        "pg_get_constraintdef(c.oid) "
        "FROM pg_constraint c WHERE c.conrelid = %s::regclass AND c.contype = 'f'",
        [table],
    )
    return cursor.fetchall()


def cascade_employee_fk(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    with schema_editor.connection.cursor() as cursor:
        for table, column, referenced in CASCADE_FOREIGN_KEYS:
            for name, columns, definition in foreign_keys(cursor, table):
                if columns == [column] and "ON DELETE CASCADE" not in definition:
                    cursor.execute(f'ALTER TABLE {table} DROP CONSTRAINT "{name}"')
                    cursor.execute(
                        f'ALTER TABLE {table} ADD CONSTRAINT "{name}" FOREIGN KEY ({column}) '
                        f"REFERENCES {referenced} (id) ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED"
                    )


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0010_employeeassignment"),
    ]

    operations = [
        migrations.RunPython(cascade_employee_fk, migrations.RunPython.noop),
    ]
