from django.db import migrations

# release_DDL.sql khai meetings_meetingbooking.department_id có ON DELETE SET NULL ở mức DB.
# Django chỉ tạo FK không có ON DELETE (SET_NULL xử lý ở tầng ứng dụng). DB dựng từ DDL đã khớp nên bước này tự bỏ qua.


def set_null_department_fk(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            "SELECT c.conname, "
            "(SELECT array_agg(a.attname::text) FROM pg_attribute a WHERE a.attrelid = c.conrelid AND a.attnum = ANY (c.conkey)), "
            "pg_get_constraintdef(c.oid) "
            "FROM pg_constraint c WHERE c.conrelid = 'meetings_meetingbooking'::regclass AND c.contype = 'f'"
        )
        for name, columns, definition in cursor.fetchall():
            if columns == ["department_id"] and "ON DELETE SET NULL" not in definition:
                cursor.execute(f'ALTER TABLE meetings_meetingbooking DROP CONSTRAINT "{name}"')
                cursor.execute(
                    f'ALTER TABLE meetings_meetingbooking ADD CONSTRAINT "{name}" FOREIGN KEY (department_id) '
                    "REFERENCES organizations_donvi (id) ON DELETE SET NULL DEFERRABLE INITIALLY DEFERRED"
                )


class Migration(migrations.Migration):

    dependencies = [
        ("meetings", "0002_align_release_ddl"),
    ]

    operations = [
        migrations.RunPython(set_null_department_fk, migrations.RunPython.noop),
    ]
