"""
Đồng bộ DB defaults, FK ON DELETE, CHECK operand order, và document_kind ENUM
để schema từ Django migrations khớp release_DDL.sql (phần app work, nhóm 6).

Chỉ chạy trên PostgreSQL — SQLite (test mặc định) tự bỏ qua.
"""

from django.db import migrations


def is_postgres(schema_editor):
    return schema_editor.connection.vendor == "postgresql"


def _fk_constraint_name(schema_editor, table, column):
    """Tìm tên FK constraint trên table.column từ pg_catalog."""
    with schema_editor.connection.cursor() as cur:
        cur.execute("""
            SELECT con.conname
            FROM pg_constraint con
            JOIN pg_attribute att ON att.attnum = ANY(con.conkey)
                AND att.attrelid = con.conrelid
            WHERE con.conrelid = %s::regclass
                AND att.attname = %s
                AND con.contype = 'f'
            LIMIT 1
        """, [table, column])
        row = cur.fetchone()
        return row[0] if row else None


def _check_constraint_name(schema_editor, table, name_pattern):
    """Tìm tên CHECK constraint trên table chứa name_pattern."""
    with schema_editor.connection.cursor() as cur:
        cur.execute("""
            SELECT con.conname
            FROM pg_constraint con
            WHERE con.conrelid = %s::regclass
                AND con.contype = 'c'
                AND con.conname LIKE %s
            LIMIT 1
        """, [table, f'%{name_pattern}%'])
        row = cur.fetchone()
        return row[0] if row else None


# ── Step 1: DB defaults ──

DEFAULTS = [
    ("task_congviec", "created_at", "now()"),
    ("task_congviec", "updated_at", "now()"),
    ("task_congviec", "hien_thi", "true"),
    ("task_congviec_donvi", "created_at", "now()"),
    ("task_comment", "created_at", "now()"),
    ("task_attachment", "created_at", "now()"),
    ("task_attachment", "is_deleted", "false"),
]


def forward_defaults(apps, schema_editor):
    if not is_postgres(schema_editor):
        return
    for table, col, default in DEFAULTS:
        schema_editor.execute(
            f"ALTER TABLE {table} ALTER COLUMN {col} SET DEFAULT {default};"
        )


def reverse_defaults(apps, schema_editor):
    if not is_postgres(schema_editor):
        return
    for table, col, _default in DEFAULTS:
        schema_editor.execute(
            f"ALTER TABLE {table} ALTER COLUMN {col} DROP DEFAULT;"
        )


# ── Step 2: FK ON DELETE CASCADE / SET NULL ──

FK_CASCADE = [
    ("task_attachment", "cong_viec_id", "task_congviec", "id", "CASCADE"),
    ("task_attachment", "y_kien_id", "task_comment", "id", "CASCADE"),
    ("task_comment", "cong_viec", "task_congviec", "id", "CASCADE"),
    ("task_congviec_donvi", "cong_viec", "task_congviec", "id", "CASCADE"),
    ("task_congviec_donvi", "don_vi", "organizations_donvi", "id", "CASCADE"),
    ("task_participant", "cong_viec", "task_congviec", "id", "CASCADE"),
    ("task_congviec", "approved_by", "accounts_employee", "id", "SET NULL"),
    ("task_congviec", "opened_by", "accounts_employee", "id", "SET NULL"),
]


def forward_fks(apps, schema_editor):
    if not is_postgres(schema_editor):
        return
    for table, col, ref_table, ref_col, on_delete in FK_CASCADE:
        old_name = _fk_constraint_name(schema_editor, table, col)
        if not old_name:
            continue
        new_name = f"fk_{table}_{col}"
        schema_editor.execute(
            f"ALTER TABLE {table} DROP CONSTRAINT {old_name};"
        )
        schema_editor.execute(
            f"ALTER TABLE {table} ADD CONSTRAINT {new_name} "
            f"FOREIGN KEY ({col}) REFERENCES {ref_table} ({ref_col}) "
            f"ON DELETE {on_delete};"
        )


def reverse_fks(apps, schema_editor):
    """Khôi phục FK Django mặc định (DEFERRABLE INITIALLY DEFERRED, không ON DELETE)."""
    if not is_postgres(schema_editor):
        return
    for table, col, ref_table, ref_col, _on_delete in FK_CASCADE:
        old_name = _fk_constraint_name(schema_editor, table, col)
        if not old_name:
            continue
        new_name = f"fk_{table}_{col}_django"
        schema_editor.execute(
            f"ALTER TABLE {table} DROP CONSTRAINT {old_name};"
        )
        schema_editor.execute(
            f"ALTER TABLE {table} ADD CONSTRAINT {new_name} "
            f"FOREIGN KEY ({col}) REFERENCES {ref_table} ({ref_col}) "
            f"DEFERRABLE INITIALLY DEFERRED;"
        )


# ── Step 3: CHECK constraint operand order ──

def forward_check_document(apps, schema_editor):
    """Thay CHECK document_id/type (Django order) bằng DDL order (document_type first)."""
    if not is_postgres(schema_editor):
        return
    old_name = _check_constraint_name(schema_editor, "task_congviec", "document")
    if old_name:
        schema_editor.execute(
            f"ALTER TABLE task_congviec DROP CONSTRAINT {old_name};"
        )
    schema_editor.execute("""
ALTER TABLE task_congviec ADD CONSTRAINT chk_task_document CHECK (
    (document_type IS NULL AND document_id IS NULL)
    OR (document_type IS NOT NULL AND document_id IS NOT NULL)
);
""")


def reverse_check_document(apps, schema_editor):
    if not is_postgres(schema_editor):
        return
    schema_editor.execute(
        "ALTER TABLE task_congviec DROP CONSTRAINT IF EXISTS chk_task_document;"
    )
    schema_editor.execute("""
ALTER TABLE task_congviec ADD CONSTRAINT chk_task_document CHECK (
    (document_id IS NULL AND document_type IS NULL)
    OR (document_id IS NOT NULL AND document_type IS NOT NULL)
);
""")


# ── Step 4: document_kind ENUM ──

def forward_document_kind(apps, schema_editor):
    if not is_postgres(schema_editor):
        return
    schema_editor.execute("""\
DO $$ BEGIN
    CREATE TYPE document_kind AS ENUM ('vanbanden', 'vanbandi');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
""")
    schema_editor.execute("""
ALTER TABLE task_congviec
    ALTER COLUMN document_type TYPE document_kind
    USING document_type::document_kind;
""")


def reverse_document_kind(apps, schema_editor):
    if not is_postgres(schema_editor):
        return
    schema_editor.execute("""
ALTER TABLE task_congviec
    ALTER COLUMN document_type TYPE varchar(20)
    USING document_type::text;
""")


class Migration(migrations.Migration):

    dependencies = [
        ("work", "0006_align_ddl_enums_triggers"),
    ]

    operations = [
        migrations.RunPython(forward_defaults, reverse_defaults),
        migrations.RunPython(forward_fks, reverse_fks),
        migrations.RunPython(forward_check_document, reverse_check_document),
        migrations.RunPython(forward_document_kind, reverse_document_kind),
    ]
