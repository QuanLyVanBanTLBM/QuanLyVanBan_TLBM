from django.db import migrations


CASCADE_FOREIGN_KEYS = [
    ("birthdays_birthdaywish", "employee_id", "accounts_employee"),
    ("birthdays_birthdayemaillog", "employee_id", "accounts_employee"),
]


def _constraints(cursor, table):
    cursor.execute(
        "SELECT c.conname, "
        "ARRAY(SELECT a.attname::text FROM unnest(c.conkey) WITH ORDINALITY AS k(attnum, ord) "
        "JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = k.attnum ORDER BY k.ord), "
        "pg_get_constraintdef(c.oid), c.convalidated, c.confrelid::regclass::text, "
        "ARRAY(SELECT a.attname::text FROM unnest(c.confkey) WITH ORDINALITY AS k(attnum, ord) "
        "JOIN pg_attribute a ON a.attrelid = c.confrelid AND a.attnum = k.attnum ORDER BY k.ord) "
        "FROM pg_constraint c WHERE c.conrelid = %s::regclass AND c.contype = 'f'",
        [table],
    )
    return [
        (name, columns or [], definition, validated, referenced_table, referenced_columns or [])
        for name, columns, definition, validated, referenced_table, referenced_columns in cursor.fetchall()
    ]


def _column_type(cursor, table, column):
    cursor.execute(
        "SELECT data_type FROM information_schema.columns "
        "WHERE table_schema = current_schema() AND table_name = %s AND column_name = %s",
        [table, column],
    )
    row = cursor.fetchone()
    return row[0] if row else None


def cascade_employee_fk(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return

    issues = []
    with schema_editor.connection.cursor() as cursor:
        for table, column, referenced in CASCADE_FOREIGN_KEYS:
            source_type = _column_type(cursor, table, column)
            target_type = _column_type(cursor, referenced, "id")
            if source_type is None or target_type is None:
                issues.append(f"missing column {table}.{column} or {referenced}.id")
                continue
            if source_type != target_type:
                issues.append(f"type mismatch {table}.{column} -> {referenced}.id")

            matches = [row for row in _constraints(cursor, table) if column in row[1]]
            if len(matches) > 1:
                issues.append(f"multiple foreign keys use {table}.{column}")
            elif matches:
                _, columns, _, _, referenced_table, referenced_columns = matches[0]
                if (
                    columns != [column]
                    or referenced_table.split(".")[-1].strip('"') != referenced
                    or referenced_columns != ["id"]
                ):
                    issues.append(f"unexpected foreign key on {table}.{column}")

            cursor.execute(
                f"SELECT count(*) FROM {table} source WHERE source.{column} IS NOT NULL "
                f"AND NOT EXISTS (SELECT 1 FROM {referenced} target WHERE target.id = source.{column})"
            )
            orphan_count = cursor.fetchone()[0]
            if orphan_count:
                issues.append(f"{table}.{column} -> {referenced}.id has {orphan_count} orphan row(s)")

        if issues:
            raise RuntimeError("C1B preflight failed; no data was modified: " + "; ".join(issues))

        for table, column, referenced in CASCADE_FOREIGN_KEYS:
            matches = [row for row in _constraints(cursor, table) if row[1] == [column]]
            if matches and "ON DELETE CASCADE" in matches[0][2]:
                if not matches[0][3]:
                    cursor.execute(
                        f"ALTER TABLE {schema_editor.quote_name(table)} "
                        f"VALIDATE CONSTRAINT {schema_editor.quote_name(matches[0][0])}"
                    )
                continue

            constraint_name = matches[0][0] if matches else f"{table}_{column}_fkey"
            if matches:
                cursor.execute(
                    f"ALTER TABLE {schema_editor.quote_name(table)} "
                    f"DROP CONSTRAINT {schema_editor.quote_name(constraint_name)}"
                )
            cursor.execute(
                f"ALTER TABLE {schema_editor.quote_name(table)} "
                f"ADD CONSTRAINT {schema_editor.quote_name(constraint_name)} "
                f"FOREIGN KEY ({schema_editor.quote_name(column)}) "
                f"REFERENCES {schema_editor.quote_name(referenced)} ({schema_editor.quote_name('id')}) "
                "ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED"
            )


class Migration(migrations.Migration):
    atomic = True

    dependencies = [
        ("birthdays", "0002_align_release_ddl"),
    ]

    operations = [
        migrations.RunPython(cascade_employee_fk, migrations.RunPython.noop),
    ]
