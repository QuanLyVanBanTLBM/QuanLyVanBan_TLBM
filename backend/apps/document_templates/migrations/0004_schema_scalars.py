"""Reconcile document-template scalar columns and updated_at triggers."""

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


HIEU_LUC_LABELS = (
    "CON_HIEU_LUC",
    "CON_HIEU_LUC_1_PHAN",
    "HET_HIEU_LUC",
    "HET_VA_THAY_THE",
)
ENUM_COLUMNS = (
    ("records_chitiettailieu", "hieu_luc", "hieu_luc_status", HIEU_LUC_LABELS),
    (
        "records_chitiettailieu",
        "hien_thi",
        "chitiettailieu_hienthi",
        ("TAT_CA", "NOI_BO_PHONG_BAN"),
    ),
)
DEFAULTS = (
    ("records_tailieu", "created_at", "now()"),
    ("records_tailieu", "updated_at", "now()"),
    ("records_loaitailieu", "created_at", "now()"),
    ("records_loaitailieu", "updated_at", "now()"),
    ("records_loaitailieu", "is_public", "TRUE"),
    ("records_chitiettailieu", "created_at", "now()"),
    ("records_chitiettailieu", "updated_at", "now()"),
    ("records_chitiettailieu_attachment", "created_at", "now()"),
    ("records_chitiettailieu_attachment", "is_deleted", "FALSE"),
)
TRIGGERS = (
    ("records_tailieu", "trg_tailieu_updated_at"),
    ("records_loaitailieu", "trg_loaitailieu_updated_at"),
    ("records_chitiettailieu", "trg_chitiettailieu_updated_at"),
)
SET_UPDATED_AT_SQL = """CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
NEW.updated_at = now();
RETURN NEW;
END;

$$
LANGUAGE plpgsql;"""


def _require_column(cursor, table, column):
    cursor.execute(
        """SELECT att.attnum, typ.typtype, typ.typname, namespace.nspname
           FROM pg_attribute att
           JOIN pg_type typ ON typ.oid = att.atttypid
           JOIN pg_namespace namespace ON namespace.oid = typ.typnamespace
           WHERE att.attrelid = %s::regclass AND att.attname = %s
             AND att.attnum > 0 AND NOT att.attisdropped""",
        [table, column],
    )
    row = cursor.fetchone()
    if row is None:
        raise RuntimeError(f"{table}.{column}: cột không tồn tại; migration không thay đổi dữ liệu.")
    return row


def _enum_labels(cursor, name):
    cursor.execute(
        """SELECT array_agg(value.enumlabel ORDER BY value.enumsortorder)
           FROM pg_type typ
           JOIN pg_namespace namespace ON namespace.oid = typ.typnamespace
           LEFT JOIN pg_enum value ON value.enumtypid = typ.oid
           WHERE namespace.nspname = 'public' AND typ.typname = %s
           GROUP BY typ.oid""",
        [name],
    )
    row = cursor.fetchone()
    return row[0] if row else None


def _view_dependencies(cursor, table, column_attnum):
    cursor.execute(
        """SELECT DISTINCT namespace.nspname, relation.relname
           FROM pg_depend dependency
           JOIN pg_rewrite rule ON dependency.classid = 'pg_rewrite'::regclass
                                AND dependency.objid = rule.oid
           JOIN pg_class relation ON relation.oid = rule.ev_class
           JOIN pg_namespace namespace ON namespace.oid = relation.relnamespace
           WHERE dependency.refclassid = 'pg_class'::regclass
             AND dependency.refobjid = %s::regclass
             AND dependency.refobjsubid = %s
             AND relation.relkind IN ('v', 'm')
           ORDER BY namespace.nspname, relation.relname""",
        [table, column_attnum],
    )
    return cursor.fetchall()


def _preflight_enum_column(cursor, table, column, type_name, labels):
    attnum, type_kind, current_type, type_schema = _require_column(cursor, table, column)
    target_labels = _enum_labels(cursor, type_name)
    if target_labels is not None and target_labels != list(labels):
        raise RuntimeError(
            f"{type_name} đã tồn tại nhưng nhãn không khớp DDL; migration không thay đổi dữ liệu."
        )
    if type_kind == "e":
        if type_schema != "public" or current_type != type_name or target_labels != list(labels):
            raise RuntimeError(
                f"{table}.{column}: enum không khớp {type_name} của DDL; migration không thay đổi dữ liệu."
            )
        return
    if type_kind != "b" or current_type not in ("varchar", "bpchar", "text"):
        raise RuntimeError(
            f"{table}.{column}: kiểu hiện tại không thể chuyển an toàn sang {type_name}; "
            "migration không thay đổi dữ liệu."
        )

    cursor.execute(
        f"SELECT COUNT(*) FROM {table} WHERE {column} IS NULL OR {column}::text <> ALL(%s)",
        [list(labels)],
    )
    invalid_count = cursor.fetchone()[0]
    if invalid_count:
        raise RuntimeError(
            f"{table}.{column}: {invalid_count} hàng NULL hoặc không hợp enum; "
            "migration không thay đổi dữ liệu."
        )
    dependencies = _view_dependencies(cursor, table, attnum)
    if dependencies:
        names = ", ".join(f"{schema}.{name}" for schema, name in dependencies)
        raise RuntimeError(
            f"{table}.{column}: có view phụ thuộc ({names}); enum conversion bị dừng trước DDL."
        )


def _trigger_exists(cursor, table, name):
    cursor.execute(
        """SELECT trigger.tgtype, trigger.tgenabled, trigger.tgnargs,
                  cardinality(trigger.tgattr::smallint[]), trigger.tgconstraint,
                  function.proname, namespace.nspname
           FROM pg_trigger trigger
           JOIN pg_class relation ON relation.oid = trigger.tgrelid
           JOIN pg_proc function ON function.oid = trigger.tgfoid
           JOIN pg_namespace namespace ON namespace.oid = function.pronamespace
           WHERE relation.oid = %s::regclass AND trigger.tgname = %s
             AND NOT trigger.tgisinternal""",
        [table, name],
    )
    row = cursor.fetchone()
    if row is None:
        return False
    if row != (19, "O", 0, 0, 0, "set_updated_at", "public"):
        raise RuntimeError(
            f"{table}.{name}: trigger cùng tên có định nghĩa khác; migration không thay đổi dữ liệu."
        )
    return True


def preflight_schema_scalars(schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        raise RuntimeError("document_templates 0004 schema scalars requires PostgreSQL.")
    with schema_editor.connection.cursor() as cursor:
        null_owner_count = 0
        cursor.execute("SELECT COUNT(*) FROM records_tailieu WHERE nguoi_lap_id IS NULL")
        null_owner_count = cursor.fetchone()[0]
        if null_owner_count:
            raise RuntimeError(
                f"records_tailieu.nguoi_lap_id: {null_owner_count} hàng NULL; "
                "migration không thay đổi dữ liệu."
            )

        for table, column, type_name, labels in ENUM_COLUMNS:
            _preflight_enum_column(cursor, table, column, type_name, labels)
        for table, column, _default in DEFAULTS:
            _require_column(cursor, table, column)
        _require_column(cursor, "records_tailieu", "nguoi_lap_id")
        for table, name in TRIGGERS:
            _trigger_exists(cursor, table, name)

        if _enum_labels(cursor, "hieu_luc_status") != list(HIEU_LUC_LABELS):
            raise RuntimeError("hieu_luc_status chưa sẵn sàng theo DDL; migration không thay đổi dữ liệu.")


def install_schema_scalars(apps, schema_editor):
    preflight_schema_scalars(schema_editor)
    q = schema_editor.connection.ops.quote_name
    with schema_editor.connection.cursor() as cursor:
        if _enum_labels(cursor, "chitiettailieu_hienthi") is None:
            cursor.execute(
                "CREATE TYPE public.chitiettailieu_hienthi AS ENUM ('TAT_CA', 'NOI_BO_PHONG_BAN')"
            )

        for table, column, type_name, _labels in ENUM_COLUMNS:
            _attnum, type_kind, current_type, type_schema = _require_column(cursor, table, column)
            if not (type_kind == "e" and current_type == type_name and type_schema == "public"):
                cursor.execute(
                    f"ALTER TABLE {q(table)} ALTER COLUMN {q(column)} TYPE {q(type_name)} "
                    f"USING {q(column)}::text::{q(type_name)}"
                )

        cursor.execute(
            f"ALTER TABLE {q('records_tailieu')} ALTER COLUMN {q('nguoi_lap_id')} SET NOT NULL"
        )
        for table, column, default_sql in DEFAULTS:
            cursor.execute(
                f"ALTER TABLE {q(table)} ALTER COLUMN {q(column)} SET DEFAULT {default_sql}"
            )

        cursor.execute(SET_UPDATED_AT_SQL)
        for table, name in TRIGGERS:
            if not _trigger_exists(cursor, table, name):
                cursor.execute(
                    f"CREATE TRIGGER {q(name)} BEFORE UPDATE ON {q(table)} "
                    "FOR EACH ROW EXECUTE FUNCTION set_updated_at()"
                )


class Migration(migrations.Migration):
    atomic = True

    dependencies = [
        ("document_templates", "0003_ddl_integrity"),
        ("documents", "0009_schema_scalars"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(install_schema_scalars, migrations.RunPython.noop),
            ],
            state_operations=[
                migrations.AlterField(
                    model_name="chitiettailieuattachment",
                    name="created_at",
                    field=models.DateTimeField(auto_now_add=True, db_column="created_at", db_default=models.Func(function="now", output_field=models.DateTimeField()), verbose_name="Thời điểm tải lên"),
                ),
                migrations.AlterField(
                    model_name="chitiettailieuattachment",
                    name="is_deleted",
                    field=models.BooleanField(db_default=False, default=False, verbose_name="Xóa mềm"),
                ),
                migrations.AlterField(
                    model_name="danhmuctailieu",
                    name="created_at",
                    field=models.DateTimeField(auto_now_add=True, db_default=models.Func(function="now", output_field=models.DateTimeField())),
                ),
                migrations.AlterField(
                    model_name="danhmuctailieu",
                    name="nguoi_lap",
                    field=models.ForeignKey(db_column="nguoi_lap_id", on_delete=django.db.models.deletion.RESTRICT, to=settings.AUTH_USER_MODEL, verbose_name="Người lập"),
                ),
                migrations.AlterField(
                    model_name="danhmuctailieu",
                    name="updated_at",
                    field=models.DateTimeField(auto_now=True, db_default=models.Func(function="now", output_field=models.DateTimeField())),
                ),
                migrations.AlterField(
                    model_name="loaitailieu",
                    name="created_at",
                    field=models.DateTimeField(auto_now_add=True, db_default=models.Func(function="now", output_field=models.DateTimeField())),
                ),
                migrations.AlterField(
                    model_name="loaitailieu",
                    name="is_public",
                    field=models.BooleanField(db_default=True, default=True, verbose_name="Công khai"),
                ),
                migrations.AlterField(
                    model_name="loaitailieu",
                    name="updated_at",
                    field=models.DateTimeField(auto_now=True, db_default=models.Func(function="now", output_field=models.DateTimeField())),
                ),
                migrations.AlterField(
                    model_name="tailieuchitiet",
                    name="created_at",
                    field=models.DateTimeField(auto_now_add=True, db_default=models.Func(function="now", output_field=models.DateTimeField())),
                ),
                migrations.AlterField(
                    model_name="tailieuchitiet",
                    name="updated_at",
                    field=models.DateTimeField(auto_now=True, db_default=models.Func(function="now", output_field=models.DateTimeField())),
                ),
            ],
        ),
    ]
