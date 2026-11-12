"""Reconcile scalar document columns and their low-risk DDL defaults/triggers."""

import django.utils.timezone
from django.db import migrations, models


HIEU_LUC_LABELS = (
    "CON_HIEU_LUC",
    "CON_HIEU_LUC_1_PHAN",
    "HET_HIEU_LUC",
    "HET_VA_THAY_THE",
)
HIEU_LUC_COLUMNS = (
    ("documents_vanbanden", "hieu_luc"),
    ("documents_vanbandi", "hieu_luc"),
)
NULLABLE_COLUMNS = (
    ("documents_vanbanden", "ngay_van_ban"),
    ("documents_vanbanden", "noi_ban_hanh"),
    ("documents_vanbanden", "nguoi_ky"),
    ("documents_vanbanden", "chuc_vu"),
    ("documents_vanbanden", "link_thay_the"),
    ("documents_vanbanden", "ghi_chu"),
    ("documents_vanbandi", "nguoi_ky"),
    ("documents_vanbandi", "chuc_vu"),
    ("documents_vanbandi", "link_thay_the"),
    ("documents_vanbandi", "ghi_chu"),
)
DEFAULTS = (
    ("documents_access_log", "created_at", "now()"),
    ("documents_vanbanden", "created_at", "now()"),
    ("documents_vanbanden", "updated_at", "now()"),
    ("documents_vanbanden", "pham_vi", "'NOI_BO'"),
    ("documents_vanbanden", "hien_thi", "TRUE"),
    ("documents_vanbanden", "gui_mail_toan_he_thong", "FALSE"),
    ("documents_vanbanden_attachment", "created_at", "now()"),
    ("documents_vanbanden_attachment", "is_deleted", "FALSE"),
    ("documents_vanbandi", "created_at", "now()"),
    ("documents_vanbandi", "updated_at", "now()"),
    ("documents_vanbandi", "pham_vi", "'NOI_BO'"),
    ("documents_vanbandi", "hien_thi", "TRUE"),
    ("documents_vanbandi", "gui_mail_toan_he_thong", "FALSE"),
    ("documents_vanbandi_attachment", "created_at", "now()"),
    ("documents_vanbandi_attachment", "is_deleted", "FALSE"),
)
TRIGGERS = (
    ("documents_vanbanden", "trg_vanbanden_updated_at"),
    ("documents_vanbandi", "trg_vanbandi_updated_at"),
)
HIEU_LUC_INDEXES = (
    ("documents_vanbanden", "idx_vanbanden_hieu_luc"),
    ("documents_vanbandi", "idx_vanbandi_hieu_luc"),
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


def _preflight_enum_column(cursor, table, column):
    attnum, type_kind, type_name, type_schema = _require_column(cursor, table, column)
    target_labels = _enum_labels(cursor, "hieu_luc_status")
    if target_labels is not None and target_labels != list(HIEU_LUC_LABELS):
        raise RuntimeError(
            "hieu_luc_status đã tồn tại nhưng nhãn không khớp DDL; migration không thay đổi dữ liệu."
        )
    if type_kind == "e":
        if type_schema != "public" or type_name != "hieu_luc_status" or target_labels != list(HIEU_LUC_LABELS):
            raise RuntimeError(
                f"{table}.{column}: enum không khớp hieu_luc_status của DDL; migration không thay đổi dữ liệu."
            )
        return False
    if type_kind != "b" or type_name not in ("varchar", "bpchar", "text"):
        raise RuntimeError(
            f"{table}.{column}: kiểu hiện tại không thể chuyển an toàn sang hieu_luc_status; "
            "migration không thay đổi dữ liệu."
        )

    cursor.execute(
        f"SELECT COUNT(*) FROM {table} WHERE {column} IS NULL OR {column}::text <> ALL(%s)",
        [list(HIEU_LUC_LABELS)],
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
    return True


def _preflight_index(cursor):
    cursor.execute(
        """SELECT relation.relkind, index.indrelid = 'documents_view_log'::regclass,
                  index.indisunique, index.indisvalid, index.indisready,
                  index.indpred IS NULL, index.indexprs IS NULL,
                  index.indnkeyatts, index.indnatts,
                  ARRAY(
                      SELECT attribute.attname
                      FROM unnest(index.indkey::smallint[]) WITH ORDINALITY AS key(attnum, ord)
                      JOIN pg_attribute attribute ON attribute.attrelid = index.indrelid
                                                 AND attribute.attnum = key.attnum
                      WHERE key.ord <= index.indnkeyatts
                      ORDER BY key.ord
                  )
           FROM pg_class relation
           JOIN pg_namespace namespace ON namespace.oid = relation.relnamespace
           LEFT JOIN pg_index index ON index.indexrelid = relation.oid
           WHERE namespace.nspname = 'public' AND relation.relname = 'idx_viewlog_document'"""
    )
    row = cursor.fetchone()
    if row is None:
        return False
    (relation_kind, on_expected_table, unique, valid, ready, no_predicate, no_expressions,
     key_count, total_count, columns) = row
    exact = (
        relation_kind == "i" and on_expected_table and not unique and valid and ready
        and no_predicate and no_expressions and key_count == 2 and total_count == 2
        and columns == ["document_type", "document_id"]
    )
    if not exact:
        raise RuntimeError(
            "idx_viewlog_document: tên đã tồn tại với định nghĩa khác; migration không thay đổi dữ liệu."
        )
    return True


def _column_indexes(cursor, table):
    cursor.execute(
        """SELECT index_class.relname, access_method.amname, index_meta.indisunique,
                  index_meta.indisvalid, index_meta.indisready,
                  index_meta.indpred IS NULL, index_meta.indexprs IS NULL,
                  index_meta.indnkeyatts, index_meta.indnatts,
                  ARRAY(
                      SELECT attribute.attname
                      FROM unnest(index_meta.indkey::smallint[]) WITH ORDINALITY AS key(attnum, ord)
                      JOIN pg_attribute attribute ON attribute.attrelid = index_meta.indrelid
                                                 AND attribute.attnum = key.attnum
                      WHERE key.ord <= index_meta.indnkeyatts
                      ORDER BY key.ord
                  ),
                  ARRAY(
                      SELECT operator_class.opcname
                      FROM unnest(index_meta.indclass::oid[]) WITH ORDINALITY AS key(opcoid, ord)
                      JOIN pg_opclass operator_class ON operator_class.oid = key.opcoid
                      WHERE key.ord <= index_meta.indnkeyatts
                      ORDER BY key.ord
                  ),
                  ARRAY(
                      SELECT operator_class.opcdefault
                      FROM unnest(index_meta.indclass::oid[]) WITH ORDINALITY AS key(opcoid, ord)
                      JOIN pg_opclass operator_class ON operator_class.oid = key.opcoid
                      WHERE key.ord <= index_meta.indnkeyatts
                      ORDER BY key.ord
                  )
           FROM pg_index index_meta
           JOIN pg_class index_class ON index_class.oid = index_meta.indexrelid
           JOIN pg_am access_method ON access_method.oid = index_class.relam
           WHERE index_meta.indrelid = %s::regclass
           ORDER BY index_class.relname""",
        [table],
    )
    return cursor.fetchall()


def _is_default_hieu_luc_index(index):
    return (
        index[1] == "btree"
        and not index[2]
        and index[3]
        and index[4]
        and index[5]
        and index[6]
        and index[7] == 1
        and index[8] == 1
        and index[9] == ["hieu_luc"]
        and len(index[11]) == 1
        and index[11][0]
    )


def _preflight_hieu_luc_indexes(cursor):
    for table, canonical_name in HIEU_LUC_INDEXES:
        indexes = _column_indexes(cursor, table)
        cursor.execute(
            """SELECT relation.relkind
               FROM pg_class relation
               JOIN pg_namespace namespace ON namespace.oid = relation.relnamespace
               WHERE namespace.nspname = 'public' AND relation.relname = %s""",
            [canonical_name],
        )
        named_relation = cursor.fetchone()
        named_index = next((index for index in indexes if index[0] == canonical_name), None)
        if named_relation and (
            named_relation[0] != "i"
            or named_index is None
            or not _is_default_hieu_luc_index(named_index)
        ):
            raise RuntimeError(
                f"{canonical_name}: tên index đã có định nghĩa khác; migration không thay đổi dữ liệu."
            )

        for index in indexes:
            if "hieu_luc" not in index[9]:
                continue
            if "varchar_pattern_ops" in index[10]:
                if not (
                    index[9] == ["hieu_luc"]
                    and index[10] == ["varchar_pattern_ops"]
                    and not index[2]
                    and index[3]
                    and index[4]
                    and index[5]
                    and index[6]
                ):
                    raise RuntimeError(
                        f"{table}.{index[0]}: index pattern không thể chuyển an toàn; "
                        "migration không thay đổi dữ liệu."
                    )
            elif not all(index[11]):
                raise RuntimeError(
                    f"{table}.{index[0]}: opclass index không thể chuyển an toàn; "
                    "migration không thay đổi dữ liệu."
                )


def _reconcile_hieu_luc_indexes(cursor, schema_editor):
    q = schema_editor.connection.ops.quote_name
    for table, canonical_name in HIEU_LUC_INDEXES:
        indexes = _column_indexes(cursor, table)
        canonical = next((index for index in indexes if index[0] == canonical_name), None)
        if canonical and _is_default_hieu_luc_index(canonical):
            continue
        equivalent = next((index for index in indexes if _is_default_hieu_luc_index(index)), None)
        if equivalent:
            cursor.execute(
                f"ALTER INDEX {q(equivalent[0])} RENAME TO {q(canonical_name)}"
            )
        else:
            cursor.execute(
                f"CREATE INDEX {q(canonical_name)} ON {q(table)} ({q('hieu_luc')})"
            )


def _drop_pattern_indexes(cursor, schema_editor):
    q = schema_editor.connection.ops.quote_name
    for table, _canonical_name in HIEU_LUC_INDEXES:
        for index in _column_indexes(cursor, table):
            if "varchar_pattern_ops" in index[10]:
                cursor.execute(f"DROP INDEX {q(index[0])}")


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
    exact = row == (19, "O", 0, 0, 0, "set_updated_at", "public")
    if not exact:
        raise RuntimeError(
            f"{table}.{name}: trigger cùng tên có định nghĩa khác; migration không thay đổi dữ liệu."
        )
    return True


def preflight_schema_scalars(schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        raise RuntimeError("documents 0009 schema scalars requires PostgreSQL.")
    with schema_editor.connection.cursor() as cursor:
        for table, column in HIEU_LUC_COLUMNS:
            _preflight_enum_column(cursor, table, column)
        _preflight_index(cursor)
        _preflight_hieu_luc_indexes(cursor)
        for table, name in TRIGGERS:
            _trigger_exists(cursor, table, name)
        for table, column in NULLABLE_COLUMNS:
            _require_column(cursor, table, column)
        for table, column, _default in DEFAULTS:
            _require_column(cursor, table, column)


def install_schema_scalars(apps, schema_editor):
    preflight_schema_scalars(schema_editor)
    q = schema_editor.connection.ops.quote_name
    with schema_editor.connection.cursor() as cursor:
        _drop_pattern_indexes(cursor, schema_editor)
        if _enum_labels(cursor, "hieu_luc_status") is None:
            labels = ", ".join("'" + label.replace("'", "''") + "'" for label in HIEU_LUC_LABELS)
            cursor.execute(f"CREATE TYPE public.hieu_luc_status AS ENUM ({labels})")

        for table, column in HIEU_LUC_COLUMNS:
            _attnum, type_kind, type_name, type_schema = _require_column(cursor, table, column)
            if not (type_kind == "e" and type_name == "hieu_luc_status" and type_schema == "public"):
                cursor.execute(
                    f"ALTER TABLE {q(table)} ALTER COLUMN {q(column)} TYPE {q('hieu_luc_status')} "
                    f"USING {q(column)}::text::{q('hieu_luc_status')}"
                )

        for table, column in NULLABLE_COLUMNS:
            cursor.execute(f"ALTER TABLE {q(table)} ALTER COLUMN {q(column)} DROP NOT NULL")
        for table, column, default_sql in DEFAULTS:
            cursor.execute(
                f"ALTER TABLE {q(table)} ALTER COLUMN {q(column)} SET DEFAULT {default_sql}"
            )

        _reconcile_hieu_luc_indexes(cursor, schema_editor)

        if not _preflight_index(cursor):
            cursor.execute(
                "CREATE INDEX idx_viewlog_document ON documents_view_log (document_type, document_id)"
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
        ("documents", "0008_ddl_integrity"),
        ("document_templates", "0003_ddl_integrity"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(install_schema_scalars, migrations.RunPython.noop),
            ],
            state_operations=[
                migrations.AlterField(
                    model_name="documentaccesslog",
                    name="created_at",
                    field=models.DateTimeField(auto_now_add=True, db_default=models.Func(function="now", output_field=models.DateTimeField()), verbose_name="Thời điểm"),
                ),
                migrations.AlterField(
                    model_name="vanbanden",
                    name="chuc_vu",
                    field=models.CharField(blank=True, default="", max_length=255, null=True, verbose_name="Chức vụ người ký"),
                ),
                migrations.AlterField(
                    model_name="vanbanden",
                    name="created_at",
                    field=models.DateTimeField(auto_now_add=True, db_default=models.Func(function="now", output_field=models.DateTimeField()), verbose_name="Ngày tạo"),
                ),
                migrations.AlterField(
                    model_name="vanbanden",
                    name="ghi_chu",
                    field=models.TextField(blank=True, default="", null=True, verbose_name="Ghi chú"),
                ),
                migrations.AlterField(
                    model_name="vanbanden",
                    name="gui_mail_toan_he_thong",
                    field=models.BooleanField(db_default=False, default=False, verbose_name="Gửi mail toàn hệ thống"),
                ),
                migrations.AlterField(
                    model_name="vanbanden",
                    name="hien_thi",
                    field=models.BooleanField(db_default=True, default=True, help_text="False = ẩn với user thường, admin vẫn thấy (đổi màu).", verbose_name="Trạng thái hiển thị"),
                ),
                migrations.AlterField(
                    model_name="vanbanden",
                    name="hieu_luc",
                    field=models.CharField(choices=[("CON_HIEU_LUC", "Còn hiệu lực"), ("CON_HIEU_LUC_1_PHAN", "Còn hiệu lực 1 phần"), ("HET_HIEU_LUC", "Hết hiệu lực"), ("HET_VA_THAY_THE", "Hết hiệu lực và thay thế")], default="CON_HIEU_LUC", max_length=20, verbose_name="Hiệu lực"),
                ),
                migrations.AlterField(
                    model_name="vanbanden",
                    name="link_thay_the",
                    field=models.CharField(blank=True, default="", max_length=500, null=True, verbose_name="Link văn bản thay thế"),
                ),
                migrations.AlterField(
                    model_name="vanbanden",
                    name="ngay_van_ban",
                    field=models.DateTimeField(blank=True, default=django.utils.timezone.now, help_text="Dùng để lọc/sắp xếp danh sách.", null=True, verbose_name="Ngày văn bản"),
                ),
                migrations.AlterField(
                    model_name="vanbanden",
                    name="nguoi_ky",
                    field=models.CharField(blank=True, default="", max_length=255, null=True, verbose_name="Người ký"),
                ),
                migrations.AlterField(
                    model_name="vanbanden",
                    name="noi_ban_hanh",
                    field=models.CharField(blank=True, default="", max_length=500, null=True, verbose_name="Nơi ban hành"),
                ),
                migrations.AlterField(
                    model_name="vanbanden",
                    name="pham_vi",
                    field=models.CharField(choices=[("NOI_BO", "Nội bộ"), ("HAN_CHE", "Hạn chế")], db_default="NOI_BO", db_index=True, default="NOI_BO", help_text="NOI_BO: Văn bản nội bộ; HAN_CHE: Văn bản hạn chế (mật nội bộ).", max_length=20, verbose_name="Phạm vi"),
                ),
                migrations.AlterField(
                    model_name="vanbanden",
                    name="updated_at",
                    field=models.DateTimeField(auto_now=True, db_default=models.Func(function="now", output_field=models.DateTimeField()), verbose_name="Ngày cập nhật"),
                ),
                migrations.AlterField(
                    model_name="vanbandenattachment",
                    name="created_at",
                    field=models.DateTimeField(db_column="created_at", db_default=models.Func(function="now", output_field=models.DateTimeField()), default=django.utils.timezone.now, verbose_name="Ngày upload"),
                ),
                migrations.AlterField(
                    model_name="vanbandenattachment",
                    name="is_deleted",
                    field=models.BooleanField(db_default=False, default=False, verbose_name="Cờ xóa mềm"),
                ),
                migrations.AlterField(
                    model_name="vanbandi",
                    name="chuc_vu",
                    field=models.CharField(blank=True, default="", max_length=255, null=True, verbose_name="Chức vụ người ký"),
                ),
                migrations.AlterField(
                    model_name="vanbandi",
                    name="created_at",
                    field=models.DateTimeField(auto_now_add=True, db_default=models.Func(function="now", output_field=models.DateTimeField()), verbose_name="Ngày tạo"),
                ),
                migrations.AlterField(
                    model_name="vanbandi",
                    name="ghi_chu",
                    field=models.TextField(blank=True, default="", null=True, verbose_name="Ghi chú"),
                ),
                migrations.AlterField(
                    model_name="vanbandi",
                    name="gui_mail_toan_he_thong",
                    field=models.BooleanField(db_default=False, default=False, verbose_name="Gửi mail toàn hệ thống"),
                ),
                migrations.AlterField(
                    model_name="vanbandi",
                    name="hien_thi",
                    field=models.BooleanField(db_default=True, default=True, help_text="False = ẩn với user thường, admin vẫn thấy (đổi màu).", verbose_name="Trạng thái hiển thị"),
                ),
                migrations.AlterField(
                    model_name="vanbandi",
                    name="hieu_luc",
                    field=models.CharField(choices=[("CON_HIEU_LUC", "Còn hiệu lực"), ("CON_HIEU_LUC_1_PHAN", "Còn hiệu lực 1 phần"), ("HET_HIEU_LUC", "Hết hiệu lực"), ("HET_VA_THAY_THE", "Hết hiệu lực và thay thế")], default="CON_HIEU_LUC", max_length=20, verbose_name="Hiệu lực"),
                ),
                migrations.AlterField(
                    model_name="vanbandi",
                    name="link_thay_the",
                    field=models.CharField(blank=True, default="", max_length=500, null=True, verbose_name="Link văn bản thay thế"),
                ),
                migrations.AlterField(
                    model_name="vanbandi",
                    name="nguoi_ky",
                    field=models.CharField(blank=True, default="", max_length=255, null=True, verbose_name="Người ký"),
                ),
                migrations.AlterField(
                    model_name="vanbandi",
                    name="pham_vi",
                    field=models.CharField(choices=[("NOI_BO", "Nội bộ"), ("HAN_CHE", "Hạn chế")], db_default="NOI_BO", db_index=True, default="NOI_BO", help_text="NOI_BO: Văn bản nội bộ; HAN_CHE: Văn bản hạn chế (mật nội bộ).", max_length=20, verbose_name="Phạm vi"),
                ),
                migrations.AlterField(
                    model_name="vanbandi",
                    name="updated_at",
                    field=models.DateTimeField(auto_now=True, db_default=models.Func(function="now", output_field=models.DateTimeField()), verbose_name="Ngày cập nhật"),
                ),
                migrations.AlterField(
                    model_name="vanbandiattachment",
                    name="created_at",
                    field=models.DateTimeField(db_column="created_at", db_default=models.Func(function="now", output_field=models.DateTimeField()), default=django.utils.timezone.now, verbose_name="Ngày upload"),
                ),
                migrations.AlterField(
                    model_name="vanbandiattachment",
                    name="is_deleted",
                    field=models.BooleanField(db_default=False, default=False, verbose_name="Cờ xóa mềm"),
                ),
                migrations.AddIndex(
                    model_name="documentviewlog",
                    index=models.Index(fields=["document_type", "document_id"], name="idx_viewlog_document"),
                ),
                migrations.AddIndex(
                    model_name="vanbanden",
                    index=models.Index(fields=["hieu_luc"], name="idx_vanbanden_hieu_luc"),
                ),
                migrations.AddIndex(
                    model_name="vanbandi",
                    index=models.Index(fields=["hieu_luc"], name="idx_vanbandi_hieu_luc"),
                ),
            ],
        ),
    ]
