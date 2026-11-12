from django.db import migrations


# Các cột được release_DDL.sql khai báo BIGINT nhưng các migration auth cũ tạo INTEGER.
BIGINT_COLUMNS = [
    ("auth_group", "id"),
    ("auth_permission", "id"),
    ("auth_permission", "content_type_id"),
    ("auth_group_permissions", "group_id"),
    ("auth_group_permissions", "permission_id"),
    ("accounts_employee_groups", "group_id"),
    ("accounts_employee_user_permissions", "permission_id"),
]

CASCADE_FOREIGN_KEYS = [
    ("auth_group_permissions", "group_id", "auth_group"),
    ("auth_group_permissions", "permission_id", "auth_permission"),
    ("accounts_employee_groups", "employee_id", "accounts_employee"),
    ("accounts_employee_groups", "group_id", "auth_group"),
    ("accounts_employee_user_permissions", "employee_id", "accounts_employee"),
    ("accounts_employee_user_permissions", "permission_id", "auth_permission"),
]

PERMISSION_CONTENT_TYPE_FK = ("auth_permission", "content_type_id", "django_content_type")
OBSOLETE_PERMISSION_UNIQUE = ("content_type_id", "codename")
REQUIRED_UNIQUE_CONSTRAINTS = [
    ("auth_permission", "codename", "auth_permission_codename_key", "uq_auth_permission_codename"),
    ("auth_group", "ma_nhom_quyen", "auth_group_ma_nhom_quyen_key", "uq_auth_group_ma_nhom_quyen"),
]


def _constraints(cursor, table, kind):
    """Trả về constraint cùng thứ tự cột và bảng/cột được tham chiếu (nếu có)."""
    cursor.execute(
        "SELECT c.conname, "
        "ARRAY(SELECT a.attname::text FROM unnest(c.conkey) WITH ORDINALITY AS k(attnum, ord) "
        "JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = k.attnum ORDER BY k.ord), "
        "pg_get_constraintdef(c.oid), c.convalidated, "
        "CASE WHEN c.confrelid = 0 THEN NULL ELSE c.confrelid::regclass::text END, "
        "ARRAY(SELECT a.attname::text FROM unnest(c.confkey) WITH ORDINALITY AS k(attnum, ord) "
        "JOIN pg_attribute a ON a.attrelid = c.confrelid AND a.attnum = k.attnum ORDER BY k.ord) "
        "FROM pg_constraint c WHERE c.conrelid = %s::regclass AND c.contype = %s",
        [table, kind],
    )
    return [
        (name, columns or [], definition, validated, referenced_table, referenced_columns or [])
        for name, columns, definition, validated, referenced_table, referenced_columns in cursor.fetchall()
    ]


def _unconstrained_unique_indexes(cursor, table):
    cursor.execute(
        "SELECT index_class.relname, "
        "ARRAY(SELECT a.attname::text FROM unnest(i.indkey) WITH ORDINALITY AS k(attnum, ord) "
        "LEFT JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = k.attnum "
        "WHERE k.ord <= i.indnkeyatts ORDER BY k.ord), "
        "pg_get_expr(i.indpred, i.indrelid), i.indisvalid, i.indisready "
        "FROM pg_index i JOIN pg_class index_class ON index_class.oid = i.indexrelid "
        "WHERE i.indrelid = %s::regclass AND i.indisunique AND NOT i.indisprimary "
        "AND NOT EXISTS (SELECT 1 FROM pg_constraint c WHERE c.conindid = i.indexrelid)",
        [table],
    )
    return [(name, columns or [], predicate, valid, ready) for name, columns, predicate, valid, ready in cursor.fetchall()]


def _column_info(cursor, table, column):
    cursor.execute(
        "SELECT data_type FROM information_schema.columns "
        "WHERE table_schema = current_schema() AND table_name = %s AND column_name = %s",
        [table, column],
    )
    return cursor.fetchone()


def _preflight(cursor):
    issues = []
    required_columns = set(BIGINT_COLUMNS)
    required_columns.update((table, column) for table, column, _ in CASCADE_FOREIGN_KEYS)
    required_columns.update(
        {
            ("accounts_employee", "id"),
            ("django_content_type", "id"),
            ("organizations_donvi", "id"),
            ("auth_permission", "codename"),
            ("auth_group", "ma_nhom_quyen"),
        }
    )

    for table, column in sorted(required_columns):
        data_type = _column_info(cursor, table, column)
        if data_type is None:
            issues.append(f"missing column {table}.{column}")

    for table, column in BIGINT_COLUMNS:
        data_type = _column_info(cursor, table, column)
        if data_type and data_type[0] not in {"integer", "bigint"}:
            issues.append(f"unsupported type {table}.{column}={data_type[0]}")

    for table, column, referenced in CASCADE_FOREIGN_KEYS:
        source_type = _column_info(cursor, table, column)
        target_type = _column_info(cursor, referenced, "id")
        if source_type is None or target_type is None:
            continue
        if source_type[0] != target_type[0]:
            issues.append(f"type mismatch {table}.{column} -> {referenced}.id")
        cursor.execute(
            f"SELECT count(*) FROM {table} source "
            f"WHERE source.{column} IS NOT NULL AND NOT EXISTS "
            f"(SELECT 1 FROM {referenced} target WHERE target.id = source.{column})"
        )
        orphan_count = cursor.fetchone()[0]
        if orphan_count:
            issues.append(f"{table}.{column} -> {referenced}.id has {orphan_count} orphan row(s)")

    for table, column, _, _ in REQUIRED_UNIQUE_CONSTRAINTS:
        if _column_info(cursor, table, column) is None:
            continue
        cursor.execute(
            f"SELECT count(*) FROM (SELECT {column} FROM {table} WHERE {column} IS NOT NULL "
            f"GROUP BY {column} HAVING count(*) > 1) duplicate_values"
        )
        duplicate_groups = cursor.fetchone()[0]
        if duplicate_groups:
            issues.append(f"{table}.{column} has {duplicate_groups} duplicate group(s)")

    if issues:
        raise RuntimeError("C1B preflight failed; no data was modified: " + "; ".join(issues))


def _assert_expected_foreign_keys(cursor):
    for table, column, referenced in CASCADE_FOREIGN_KEYS:
        matches = [row for row in _constraints(cursor, table, "f") if column in row[1]]
        if len(matches) > 1:
            raise RuntimeError(f"C1B found multiple foreign keys using {table}.{column}; no schema was modified.")
        if matches:
            _, columns, _, _, referenced_table, referenced_columns = matches[0]
            if columns != [column] or referenced_table.split(".")[-1].strip('"') != referenced or referenced_columns != ["id"]:
                raise RuntimeError(f"C1B found an unexpected foreign key on {table}.{column}; no schema was modified.")

    table, column, referenced = PERMISSION_CONTENT_TYPE_FK
    matches = [row for row in _constraints(cursor, table, "f") if column in row[1]]
    if len(matches) > 1:
        raise RuntimeError(f"C1B found multiple foreign keys using {table}.{column}; no schema was modified.")
    if matches:
        _, columns, _, _, referenced_table, referenced_columns = matches[0]
        if columns != [column] or referenced_table.split(".")[-1].strip('"') != referenced or referenced_columns != ["id"]:
            raise RuntimeError(f"C1B found an unexpected foreign key on {table}.{column}; no schema was modified.")

    expected_incoming = {
        ("auth_group_permissions", ("group_id",), "auth_group"),
        ("accounts_employee_groups", ("group_id",), "auth_group"),
        ("auth_group_permissions", ("permission_id",), "auth_permission"),
        ("accounts_employee_user_permissions", ("permission_id",), "auth_permission"),
    }
    cursor.execute(
        "SELECT c.conrelid::regclass::text, "
        "ARRAY(SELECT a.attname::text FROM unnest(c.conkey) WITH ORDINALITY AS k(attnum, ord) "
        "JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = k.attnum ORDER BY k.ord), "
        "c.confrelid::regclass::text, "
        "ARRAY(SELECT a.attname::text FROM unnest(c.confkey) WITH ORDINALITY AS k(attnum, ord) "
        "JOIN pg_attribute a ON a.attrelid = c.confrelid AND a.attnum = k.attnum ORDER BY k.ord) "
        "FROM pg_constraint c WHERE c.contype = 'f' "
        "AND c.confrelid IN (%s::regclass, %s::regclass)",
        ["auth_group", "auth_permission"],
    )
    actual_incoming = set()
    for source_table, source_columns, target_table, target_columns in cursor.fetchall():
        actual_incoming.add(
            (
                source_table.split(".")[-1].strip('"'),
                tuple(source_columns or []),
                target_table.split(".")[-1].strip('"'),
            )
        )
        if target_columns != ["id"]:
            raise RuntimeError("C1B found an unexpected foreign key referencing an auth ID; no schema was modified.")
    if not actual_incoming.issubset(expected_incoming):
        raise RuntimeError("C1B found an unexpected inbound foreign key for auth IDs; no schema was modified.")


def _drop_permission_content_type_fk(cursor, schema_editor):
    table, column, _ = PERMISSION_CONTENT_TYPE_FK
    matches = [row for row in _constraints(cursor, table, "f") if row[1] == [column]]
    if matches:
        cursor.execute(
            f"ALTER TABLE {schema_editor.quote_name(table)} "
            f"DROP CONSTRAINT {schema_editor.quote_name(matches[0][0])}"
        )


def _drop_obsolete_permission_unique(cursor, schema_editor):
    table = "auth_permission"
    target_columns = set(OBSOLETE_PERMISSION_UNIQUE)
    constraints = [
        row for row in _constraints(cursor, table, "u") if set(row[1]) == target_columns and len(row[1]) == 2
    ]
    if len(constraints) > 1:
        raise RuntimeError("C1B found duplicate content_type/codename unique constraints; no schema was modified.")
    if constraints:
        cursor.execute(
            f"ALTER TABLE {schema_editor.quote_name(table)} "
            f"DROP CONSTRAINT {schema_editor.quote_name(constraints[0][0])}"
        )

    indexes = [row for row in _unconstrained_unique_indexes(cursor, table) if set(row[1]) == target_columns]
    for name, _, predicate, valid, ready in indexes:
        if predicate is not None or not valid or not ready:
            raise RuntimeError(f"C1B found an unsupported unique index on {table}; no schema was modified.")
        cursor.execute(f"DROP INDEX {schema_editor.quote_name(name)}")


def _ensure_unique_constraint(cursor, schema_editor, table, column, constraint_name):
    constraints = [row for row in _constraints(cursor, table, "u") if row[1] == [column]]
    if len(constraints) > 1:
        raise RuntimeError(f"C1B found duplicate UNIQUE constraints on {table}.{column}.")
    if constraints:
        if not constraints[0][3]:
            cursor.execute(
                f"ALTER TABLE {schema_editor.quote_name(table)} "
                f"VALIDATE CONSTRAINT {schema_editor.quote_name(constraints[0][0])}"
            )
        return

    indexes = [row for row in _unconstrained_unique_indexes(cursor, table) if row[1] == [column]]
    if len(indexes) > 1:
        raise RuntimeError(f"C1B found multiple UNIQUE indexes on {table}.{column}.")
    if indexes:
        index_name, _, predicate, valid, ready = indexes[0]
        if predicate is not None or not valid or not ready:
            raise RuntimeError(f"C1B found an unsupported UNIQUE index on {table}.{column}.")
        cursor.execute(
            f"ALTER TABLE {schema_editor.quote_name(table)} "
            f"ADD CONSTRAINT {schema_editor.quote_name(constraint_name)} "
            f"UNIQUE USING INDEX {schema_editor.quote_name(index_name)}"
        )
        return

    names = {row[0] for row in _constraints(cursor, table, "u")}
    if constraint_name in names:
        raise RuntimeError(f"C1B found a conflicting constraint name on {table}.{column}.")
    cursor.execute(
        f"ALTER TABLE {schema_editor.quote_name(table)} "
        f"ADD CONSTRAINT {schema_editor.quote_name(constraint_name)} UNIQUE ({schema_editor.quote_name(column)})"
    )


def _promote_sequence(cursor, schema_editor, table, column):
    cursor.execute("SELECT pg_get_serial_sequence(%s, %s)", [table, column])
    sequence_name = cursor.fetchone()[0]
    if not sequence_name:
        raise RuntimeError(f"C1B found no serial sequence for {table}.{column}; no schema was modified.")

    cursor.execute(
        "SELECT n.nspname, sequence_class.relname, format_type(sequence_info.seqtypid, NULL) "
        "FROM pg_class sequence_class JOIN pg_namespace n ON n.oid = sequence_class.relnamespace "
        "JOIN pg_sequence sequence_info ON sequence_info.seqrelid = sequence_class.oid "
        "WHERE sequence_class.oid = %s::regclass",
        [sequence_name],
    )
    schema_name, relation_name, sequence_type = cursor.fetchone()
    if sequence_type == "integer":
        cursor.execute(
            f"ALTER SEQUENCE {schema_editor.quote_name(schema_name)}.{schema_editor.quote_name(relation_name)} AS bigint"
        )
    elif sequence_type != "bigint":
        raise RuntimeError(f"C1B found unsupported sequence type for {table}.{column}; no schema was modified.")


def _promote_bigint_columns(cursor, schema_editor):
    for table, column in BIGINT_COLUMNS:
        data_type = _column_info(cursor, table, column)[0]
        if data_type == "integer":
            cursor.execute(
                f"ALTER TABLE {schema_editor.quote_name(table)} "
                f"ALTER COLUMN {schema_editor.quote_name(column)} TYPE bigint"
            )
        elif data_type != "bigint":
            raise RuntimeError(f"C1B found unsupported type for {table}.{column}; no schema was modified.")
        if column == "id":
            _promote_sequence(cursor, schema_editor, table, column)


def _align_cascade_foreign_keys(cursor, schema_editor):
    for table, column, referenced in CASCADE_FOREIGN_KEYS:
        matches = [row for row in _constraints(cursor, table, "f") if row[1] == [column]]
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


def align_structure(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return

    with schema_editor.connection.cursor() as cursor:
        _preflight(cursor)
        _assert_expected_foreign_keys(cursor)
        for table, column, constraint_name, _ in REQUIRED_UNIQUE_CONSTRAINTS:
            _ensure_unique_constraint(cursor, schema_editor, table, column, constraint_name)
        _drop_obsolete_permission_unique(cursor, schema_editor)

        # Bỏ FK content_type trước khi đổi kiểu cột; release DDL chủ ý không ràng buộc bảng Django content type.
        _drop_permission_content_type_fk(cursor, schema_editor)

        # Các FK liên quan auth_group/auth_permission phải được bỏ trước khi đổi int4 sang int8.
        for table, column, referenced in CASCADE_FOREIGN_KEYS:
            if referenced not in {"auth_group", "auth_permission"}:
                continue
            matches = [row for row in _constraints(cursor, table, "f") if row[1] == [column]]
            if matches:
                cursor.execute(
                    f"ALTER TABLE {schema_editor.quote_name(table)} "
                    f"DROP CONSTRAINT {schema_editor.quote_name(matches[0][0])}"
                )

        _promote_bigint_columns(cursor, schema_editor)
        _align_cascade_foreign_keys(cursor, schema_editor)


class Migration(migrations.Migration):
    atomic = True

    dependencies = [
        ("authorization", "0004_grant_tp_manage_signing_process"),
        ("accounts", "0007_normalize_system_account_password"),
    ]

    operations = [
        migrations.RunPython(align_structure, migrations.RunPython.noop),
    ]
