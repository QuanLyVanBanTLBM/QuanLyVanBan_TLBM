"""Align the document-template tables with their canonical PostgreSQL DDL.

These database-only references remain in the migration because their legacy
model fields intentionally preserve the existing ORM API.  The reverse
operation is a no-op so a code rollback cannot remove data integrity rules.
"""

from django.db import migrations


PRIMARY_KEY = (
    "records_chitiettailieu_loaitailieu",
    ("chitiettailieu_id", "loaitailieu_id"),
    "pk_chitiettailieu_loaitailieu",
)

# table, columns, referenced table, referenced columns, ON DELETE, nullable
FOREIGN_KEYS = [
    ("records_chitiettailieu", ("dm_tai_lieu",), "records_tailieu", ("id",), "RESTRICT", False),
    ("records_chitiettailieu", ("don_vi_id",), "organizations_donvi", ("id",), "RESTRICT", True),
    ("records_chitiettailieu", ("nguoi_tao_id",), "accounts_employee", ("id",), "SET NULL", True),
    ("records_chitiettailieu_loaitailieu", ("chitiettailieu_id",), "records_chitiettailieu", ("id",), "CASCADE", False),
    ("records_chitiettailieu_loaitailieu", ("loaitailieu_id",), "records_loaitailieu", ("id",), "RESTRICT", False),
    ("records_chitiettailieu_attachment", ("document_id",), "records_chitiettailieu", ("id",), "CASCADE", False),
    ("records_chitiettailieu_attachment", ("nguoi_tao_id",), "accounts_employee", ("id",), "SET NULL", True),
]


def _columns_sql(alias, key_name, relation_name):
    return f"""ARRAY(
        SELECT att.attname
        FROM unnest({alias}.{key_name}) WITH ORDINALITY AS key(attnum, ord)
        JOIN pg_attribute att ON att.attrelid = {relation_name} AND att.attnum = key.attnum
        ORDER BY key.ord
    )"""


def _count(cursor, sql):
    cursor.execute(sql)
    return cursor.fetchone()[0]


def _preflight(schema_editor):
    q = schema_editor.connection.ops.quote_name
    table, columns, _constraint_name = PRIMARY_KEY
    table_sql = q(table)
    null_predicate = " OR ".join(f"{q(column)} IS NULL" for column in columns)
    with schema_editor.connection.cursor() as cursor:
        null_count = _count(cursor, f"SELECT COUNT(*) FROM {table_sql} WHERE {null_predicate}")
        if null_count:
            raise RuntimeError(f"{table}: {null_count} hàng có khóa ghép NULL; migration không thay đổi dữ liệu.")

        group_columns = ", ".join(q(column) for column in columns)
        duplicate_count = _count(
            cursor,
            f"SELECT COALESCE(SUM(row_count), 0) FROM ("
            f"SELECT COUNT(*) AS row_count FROM {table_sql} GROUP BY {group_columns} "
            "HAVING COUNT(*) > 1) AS duplicate_keys",
        )
        if duplicate_count:
            raise RuntimeError(f"{table}: {duplicate_count} hàng thuộc khóa ghép trùng; migration không thay đổi dữ liệu.")

        for source_table, source_columns, target_table, target_columns, _action, nullable in FOREIGN_KEYS:
            source_column = source_columns[0]
            target_column = target_columns[0]
            if not nullable:
                null_count = _count(
                    cursor,
                    f"SELECT COUNT(*) FROM {q(source_table)} WHERE {q(source_column)} IS NULL",
                )
                if null_count:
                    raise RuntimeError(f"{source_table}: {null_count} hàng có khóa ngoại NULL; migration không thay đổi dữ liệu.")

            orphan_count = _count(
                cursor,
                f"SELECT COUNT(*) FROM {q(source_table)} AS source "
                f"LEFT JOIN {q(target_table)} AS target ON source.{q(source_column)} = target.{q(target_column)} "
                f"WHERE source.{q(source_column)} IS NOT NULL AND target.{q(target_column)} IS NULL",
            )
            if orphan_count:
                raise RuntimeError(f"{source_table}: {orphan_count} hàng có khóa ngoại mồ côi; migration không thay đổi dữ liệu.")


def _constraint_columns(cursor, table, constraint_type):
    cursor.execute(
        f"""SELECT con.conname, {_columns_sql('con', 'conkey', 'con.conrelid')}, con.convalidated
            FROM pg_constraint con
            WHERE con.conrelid = %s::regclass AND con.contype = %s""",
        [table, constraint_type],
    )
    return cursor.fetchall()


def _standalone_unique_index(cursor, table, columns):
    cursor.execute(
        """SELECT index_class.relname
           FROM pg_index index_meta
           JOIN pg_class index_class ON index_class.oid = index_meta.indexrelid
           WHERE index_meta.indrelid = %s::regclass
             AND index_meta.indisunique AND index_meta.indisvalid AND index_meta.indisready
             AND index_meta.indpred IS NULL AND index_meta.indexprs IS NULL
             AND index_meta.indnkeyatts = %s AND index_meta.indnatts = %s
             AND ARRAY(
                 SELECT att.attname::text
                 FROM unnest(index_meta.indkey::smallint[]) WITH ORDINALITY AS key(attnum, ord)
                 JOIN pg_attribute att ON att.attrelid = index_meta.indrelid AND att.attnum = key.attnum
                 ORDER BY key.ord
             ) = %s
             AND NOT EXISTS (
                 SELECT 1 FROM pg_constraint con WHERE con.conindid = index_meta.indexrelid
             )
           ORDER BY index_class.relname
           LIMIT 1""",
        [table, len(columns), len(columns), list(columns)],
    )
    row = cursor.fetchone()
    return row[0] if row else None


def _ensure_primary_key(schema_editor):
    table, columns, constraint_name = PRIMARY_KEY
    q = schema_editor.connection.ops.quote_name
    with schema_editor.connection.cursor() as cursor:
        primary_keys = _constraint_columns(cursor, table, "p")
        exact = next((row for row in primary_keys if tuple(row[1]) == tuple(columns) and row[2]), None)
        if exact:
            for name, cols, _validated in _constraint_columns(cursor, table, "u"):
                if tuple(cols) == tuple(columns):
                    cursor.execute(f"ALTER TABLE {q(table)} DROP CONSTRAINT {q(name)}")
            return

        for name, _cols, _validated in primary_keys:
            cursor.execute(f"ALTER TABLE {q(table)} DROP CONSTRAINT {q(name)}")
        for name, cols, _validated in _constraint_columns(cursor, table, "u"):
            if tuple(cols) == tuple(columns):
                cursor.execute(f"ALTER TABLE {q(table)} DROP CONSTRAINT {q(name)}")

        index_name = _standalone_unique_index(cursor, table, columns)
        columns_sql = ", ".join(q(column) for column in columns)
        if index_name:
            cursor.execute(
                f"ALTER TABLE {q(table)} ADD CONSTRAINT {q(constraint_name)} "
                f"PRIMARY KEY USING INDEX {q(index_name)}"
            )
        else:
            cursor.execute(
                f"ALTER TABLE {q(table)} ADD CONSTRAINT {q(constraint_name)} "
                f"PRIMARY KEY ({columns_sql})"
            )


def _foreign_key_rows(cursor, table):
    cursor.execute(
        f"""SELECT con.conname,
                   {_columns_sql('con', 'conkey', 'con.conrelid')},
                   target.relname,
                   {_columns_sql('con', 'confkey', 'con.confrelid')},
                   con.confupdtype, con.confdeltype, con.confmatchtype,
                   con.condeferrable, con.condeferred, con.convalidated
            FROM pg_constraint con
            JOIN pg_class target ON target.oid = con.confrelid
            WHERE con.conrelid = %s::regclass AND con.contype = 'f'""",
        [table],
    )
    return cursor.fetchall()


def _ensure_foreign_key(schema_editor, spec):
    table, columns, target, target_columns, on_delete, _nullable = spec
    q = schema_editor.connection.ops.quote_name
    delete_code = {"NO ACTION": "a", "RESTRICT": "r", "CASCADE": "c", "SET NULL": "n"}[on_delete]
    with schema_editor.connection.cursor() as cursor:
        rows = _foreign_key_rows(cursor, table)
        matching_local = [row for row in rows if tuple(row[1]) == tuple(columns)]
        exact = [
            row for row in matching_local
            if row[2] == target
            and tuple(row[3]) == tuple(target_columns)
            and row[4] == "a"
            and row[5] == delete_code
            and row[6] == "s"
            and not row[7]
            and not row[8]
            and row[9]
        ]
        keep = exact[0] if exact else None
        for row in matching_local:
            if keep is None or row[0] != keep[0]:
                cursor.execute(f"ALTER TABLE {q(table)} DROP CONSTRAINT {q(row[0])}")
        if keep:
            return

        constraint_name = "fk_" + table.removeprefix("records_") + "_" + "_".join(columns)
        local_sql = ", ".join(q(column) for column in columns)
        target_columns_sql = ", ".join(q(column) for column in target_columns)
        action_sql = "" if on_delete == "NO ACTION" else f" ON DELETE {on_delete}"
        cursor.execute(
            f"ALTER TABLE {q(table)} ADD CONSTRAINT {q(constraint_name)} "
            f"FOREIGN KEY ({local_sql}) REFERENCES {q(target)} ({target_columns_sql}){action_sql}"
        )


def install_integrity(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        raise RuntimeError("document_templates 0003 integrity requires PostgreSQL.")

    # Validate all relevant data before the first DDL statement. PostgreSQL's
    # migration transaction rolls back the whole change if later catalog DDL fails.
    _preflight(schema_editor)
    _ensure_primary_key(schema_editor)
    for foreign_key in FOREIGN_KEYS:
        _ensure_foreign_key(schema_editor, foreign_key)


class Migration(migrations.Migration):
    atomic = True

    dependencies = [
        ("accounts", "0007_normalize_system_account_password"),
        ("document_templates", "0002_normalize_column_names_ddl_pr96"),
        ("organizations", "0005_reference_data_ddl"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[migrations.RunPython(install_integrity, migrations.RunPython.noop)],
            state_operations=[],
        ),
    ]
