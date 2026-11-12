from django.db import migrations


def _foreign_keys(cursor):
    cursor.execute(
        "SELECT c.conname, "
        "ARRAY(SELECT a.attname::text FROM unnest(c.conkey) WITH ORDINALITY AS k(attnum, ord) "
        "JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = k.attnum ORDER BY k.ord), "
        "pg_get_constraintdef(c.oid), c.convalidated, c.confrelid::regclass::text, "
        "ARRAY(SELECT a.attname::text FROM unnest(c.confkey) WITH ORDINALITY AS k(attnum, ord) "
        "JOIN pg_attribute a ON a.attrelid = c.confrelid AND a.attnum = k.attnum ORDER BY k.ord) "
        "FROM pg_constraint c WHERE c.conrelid = 'meetings_meetingbooking'::regclass AND c.contype = 'f'"
    )
    return [
        (name, columns or [], definition, validated, referenced_table, referenced_columns or [])
        for name, columns, definition, validated, referenced_table, referenced_columns in cursor.fetchall()
    ]


def set_null_department_fk(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return

    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            "SELECT source.data_type, target.data_type "
            "FROM information_schema.columns source, information_schema.columns target "
            "WHERE source.table_schema = current_schema() AND source.table_name = 'meetings_meetingbooking' "
            "AND source.column_name = 'department_id' AND target.table_schema = current_schema() "
            "AND target.table_name = 'organizations_donvi' AND target.column_name = 'id'"
        )
        types = cursor.fetchone()
        if types is None or types[0] != types[1]:
            raise RuntimeError("C1B preflight failed; meetings department FK columns are missing or have different types.")

        cursor.execute(
            "SELECT count(*) FROM meetings_meetingbooking source "
            "WHERE source.department_id IS NOT NULL AND NOT EXISTS "
            "(SELECT 1 FROM organizations_donvi target WHERE target.id = source.department_id)"
        )
        orphan_count = cursor.fetchone()[0]
        if orphan_count:
            raise RuntimeError(
                f"C1B preflight failed; meetings_meetingbooking.department_id has {orphan_count} orphan row(s); "
                "no data was modified."
            )

        matches = [row for row in _foreign_keys(cursor) if "department_id" in row[1]]
        if len(matches) > 1:
            raise RuntimeError("C1B found multiple foreign keys using meetings_meetingbooking.department_id.")
        if matches:
            _, columns, _, _, referenced_table, referenced_columns = matches[0]
            if (
                columns != ["department_id"]
                or referenced_table.split(".")[-1].strip('"') != "organizations_donvi"
                or referenced_columns != ["id"]
            ):
                raise RuntimeError("C1B found an unexpected foreign key on meetings_meetingbooking.department_id.")

        matches = [row for row in _foreign_keys(cursor) if row[1] == ["department_id"]]
        if matches and "ON DELETE SET NULL" in matches[0][2]:
            if not matches[0][3]:
                cursor.execute(
                    f"ALTER TABLE {schema_editor.quote_name('meetings_meetingbooking')} "
                    f"VALIDATE CONSTRAINT {schema_editor.quote_name(matches[0][0])}"
                )
            return

        constraint_name = matches[0][0] if matches else "meetings_meetingbooking_department_id_fkey"
        if matches:
            cursor.execute(
                f"ALTER TABLE {schema_editor.quote_name('meetings_meetingbooking')} "
                f"DROP CONSTRAINT {schema_editor.quote_name(constraint_name)}"
            )
        cursor.execute(
            f"ALTER TABLE {schema_editor.quote_name('meetings_meetingbooking')} "
            f"ADD CONSTRAINT {schema_editor.quote_name(constraint_name)} "
            f"FOREIGN KEY ({schema_editor.quote_name('department_id')}) "
            f"REFERENCES {schema_editor.quote_name('organizations_donvi')} ({schema_editor.quote_name('id')}) "
            "ON DELETE SET NULL DEFERRABLE INITIALLY DEFERRED"
        )


class Migration(migrations.Migration):
    atomic = True

    dependencies = [
        ("meetings", "0002_align_release_ddl"),
    ]

    operations = [
        migrations.RunPython(set_null_department_fk, migrations.RunPython.noop),
    ]
