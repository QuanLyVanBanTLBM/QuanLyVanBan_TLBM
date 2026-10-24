"""Align document integrity rules with the canonical PostgreSQL DDL.

The SQL function bodies below are copied into this migration so a later edit to
release_DDL.sql cannot silently change an already deployed migration.  The
reverse operation is intentionally a no-op: these are integrity protections,
and removing them during a code rollback could make adopted production data
unsafe.
"""

from django.db import migrations


JUNCTION_KEYS = [
    ("documents_vanbanden_nguoinhan", ("vanbanden_id", "employee_id"), "pk_vbd_nguoinhan"),
    ("documents_vanbanden_hoso", ("vanbanden_id", "hoso_id"), "pk_vbd_hoso"),
    ("documents_vanbanden_danhmuc", ("vanbanden_id", "loaivanban_id"), "pk_vbd_danhmuc"),
    ("documents_vanbanden_donvinhan", ("vanbanden_id", "donvi_id"), "pk_vbd_donvinhan"),
    ("documents_vanbandi_nguoinhan", ("vanbandi_id", "employee_id"), "pk_vbi_nguoinhan"),
    ("documents_vanbandi_hoso", ("vanbandi_id", "hoso_id"), "pk_vbi_hoso"),
    ("documents_vanbandi_danhmuc", ("vanbandi_id", "loaivanban_id"), "pk_vbi_danhmuc"),
    ("documents_vanbandi_donvinhan", ("vanbandi_id", "donvi_id"), "pk_vbi_donvinhan"),
    ("documents_vanbandi_noibanhanh", ("vanbandi_id", "donvi_id"), "pk_vbi_noibanhanh"),
]

# table, columns, referenced table, referenced columns, ON DELETE, nullable
FOREIGN_KEYS = [
    ("documents_vanbanden", ("nguoi_tao_id",), "accounts_employee", ("id",), "SET NULL", True),
    ("documents_vanbandi", ("nguoi_tao_id",), "accounts_employee", ("id",), "SET NULL", True),
    ("documents_vanbanden_nguoinhan", ("vanbanden_id",), "documents_vanbanden", ("id",), "CASCADE", False),
    ("documents_vanbanden_nguoinhan", ("employee_id",), "accounts_employee", ("id",), "RESTRICT", False),
    ("documents_vanbanden_hoso", ("vanbanden_id",), "documents_vanbanden", ("id",), "CASCADE", False),
    ("documents_vanbanden_hoso", ("hoso_id",), "records_hoso", ("id",), "RESTRICT", False),
    ("documents_vanbanden_danhmuc", ("vanbanden_id",), "documents_vanbanden", ("id",), "CASCADE", False),
    ("documents_vanbanden_danhmuc", ("loaivanban_id",), "records_loaivanban", ("id",), "RESTRICT", False),
    ("documents_vanbanden_donvinhan", ("vanbanden_id",), "documents_vanbanden", ("id",), "CASCADE", False),
    ("documents_vanbanden_donvinhan", ("donvi_id",), "organizations_donvi", ("id",), "RESTRICT", False),
    ("documents_vanbandi_nguoinhan", ("vanbandi_id",), "documents_vanbandi", ("id",), "CASCADE", False),
    ("documents_vanbandi_nguoinhan", ("employee_id",), "accounts_employee", ("id",), "RESTRICT", False),
    ("documents_vanbandi_hoso", ("vanbandi_id",), "documents_vanbandi", ("id",), "CASCADE", False),
    ("documents_vanbandi_hoso", ("hoso_id",), "records_hoso", ("id",), "RESTRICT", False),
    ("documents_vanbandi_danhmuc", ("vanbandi_id",), "documents_vanbandi", ("id",), "CASCADE", False),
    ("documents_vanbandi_danhmuc", ("loaivanban_id",), "records_loaivanban", ("id",), "RESTRICT", False),
    ("documents_vanbandi_noibanhanh", ("vanbandi_id",), "documents_vanbandi", ("id",), "CASCADE", False),
    ("documents_vanbandi_noibanhanh", ("donvi_id",), "organizations_donvi", ("id",), "RESTRICT", False),
    ("documents_vanbandi_donvinhan", ("vanbandi_id",), "documents_vanbandi", ("id",), "CASCADE", False),
    ("documents_vanbandi_donvinhan", ("donvi_id",), "organizations_donvi", ("id",), "RESTRICT", False),
    ("documents_vanbanden_attachment", ("document_id",), "documents_vanbanden", ("id",), "CASCADE", False),
    ("documents_vanbanden_attachment", ("nguoi_tao_id",), "accounts_employee", ("id",), "SET NULL", True),
    ("documents_vanbandi_attachment", ("document_id",), "documents_vanbandi", ("id",), "CASCADE", False),
    ("documents_vanbandi_attachment", ("nguoi_tao_id",), "accounts_employee", ("id",), "SET NULL", True),
    ("documents_view_log", ("user_id",), "accounts_employee", ("id",), "CASCADE", False),
    ("documents_access_log", ("user_id",), "accounts_employee", ("id",), "RESTRICT", False),
    ("documents_access_log", ("doi_tuong_user_id",), "accounts_employee", ("id",), "RESTRICT", True),
]


FUNCTION_BODIES = {
    "check_vanbanden_cross_reference": """
DECLARE
v_hoso_id BIGINT;
BEGIN
SELECT ho_so_id INTO v_hoso_id FROM records_loaivanban WHERE id = NEW.loaivanban_id;
IF EXISTS (SELECT 1 FROM documents_vanbanden_hoso WHERE vanbanden_id = NEW.vanbanden_id) THEN
IF NOT EXISTS (
SELECT 1 FROM documents_vanbanden_hoso
WHERE vanbanden_id = NEW.vanbanden_id AND hoso_id = v_hoso_id
) THEN
RAISE EXCEPTION 'Vi phạm toàn vẹn tham chiếu chéo: Loại văn bản (id=%) thuộc Hồ sơ (id=%), nhưng Văn bản đến (id=%) không liên kết với Hồ sơ này.',
NEW.loaivanban_id, v_hoso_id, NEW.vanbanden_id;
END IF;
END IF;
RETURN NEW;
END;
""",
    "check_vanbanden_hoso_delete_cross_ref": """
BEGIN
-- Nếu văn bản cha không còn tồn tại (đang trong luồng ON DELETE CASCADE của documents_vanbanden), bỏ qua không chặn
IF NOT EXISTS (SELECT 1 FROM documents_vanbanden WHERE id = OLD.vanbanden_id) THEN
RETURN OLD;
END IF;

IF EXISTS (
SELECT 1 FROM documents_vanbanden_danhmuc dm
JOIN records_loaivanban lvb ON dm.loaivanban_id = lvb.id
WHERE dm.vanbanden_id = OLD.vanbanden_id AND lvb.ho_so_id = OLD.hoso_id
) THEN
RAISE EXCEPTION 'Không thể gỡ Hồ sơ (id=%) khỏi Văn bản đến (id=%): văn bản vẫn còn chứa Loại văn bản thuộc Hồ sơ này.',
OLD.hoso_id, OLD.vanbanden_id;
END IF;
RETURN OLD;
END;
""",
    "check_vanbandi_cross_reference": """
DECLARE
v_hoso_id BIGINT;
BEGIN
SELECT ho_so_id INTO v_hoso_id FROM records_loaivanban WHERE id = NEW.loaivanban_id;
IF EXISTS (SELECT 1 FROM documents_vanbandi_hoso WHERE vanbandi_id = NEW.vanbandi_id) THEN
IF NOT EXISTS (
SELECT 1 FROM documents_vanbandi_hoso
WHERE vanbandi_id = NEW.vanbandi_id AND hoso_id = v_hoso_id
) THEN
RAISE EXCEPTION 'Vi phạm toàn vẹn tham chiếu chéo: Loại văn bản (id=%) thuộc Hồ sơ (id=%), nhưng Văn bản đi (id=%) không liên kết với Hồ sơ này.',
NEW.loaivanban_id, v_hoso_id, NEW.vanbandi_id;
END IF;
END IF;
RETURN NEW;
END;
""",
    "check_vanbandi_hoso_delete_cross_ref": """
BEGIN
-- Nếu văn bản cha không còn tồn tại (đang trong luồng ON DELETE CASCADE của documents_vanbandi), bỏ qua không chặn
IF NOT EXISTS (SELECT 1 FROM documents_vanbandi WHERE id = OLD.vanbandi_id) THEN
RETURN OLD;
END IF;

IF EXISTS (
SELECT 1 FROM documents_vanbandi_danhmuc dm
JOIN records_loaivanban lvb ON dm.loaivanban_id = lvb.id
WHERE dm.vanbandi_id = OLD.vanbandi_id AND lvb.ho_so_id = OLD.hoso_id
) THEN
RAISE EXCEPTION 'Không thể gỡ Hồ sơ (id=%) khỏi Văn bản đi (id=%): văn bản vẫn còn chứa Loại văn bản thuộc Hồ sơ này.',
OLD.hoso_id, OLD.vanbandi_id;
END IF;
RETURN OLD;
END;
""",
    "trg_cleanup_viewlog_on_doc_delete": """
BEGIN
    DELETE FROM documents_view_log
    WHERE document_id = OLD.id AND document_type = TG_ARGV[0]::document_kind;
    RETURN OLD;
END;
""",
    "prevent_modify_documents_access_log": """
BEGIN
    RAISE EXCEPTION 'Nhật ký truy cập văn bản hạn chế (documents_access_log id=%) chỉ được thêm, nghiêm cấm sửa hoặc xóa.', OLD.id;
END;
""",
    "prevent_delete_van_ban_han_che": """
BEGIN
    IF OLD.pham_vi = 'HAN_CHE' THEN
        RAISE EXCEPTION 'Văn bản hạn chế (id=%) không được xóa.', OLD.id;
    END IF;
    RETURN OLD;
END;
""",
    "prevent_change_pham_vi": """
BEGIN
    IF NEW.pham_vi IS DISTINCT FROM OLD.pham_vi THEN
        RAISE EXCEPTION 'Phạm vi văn bản (id=%) không được đổi sau khi tạo.', OLD.id;
    END IF;
    RETURN NEW;
END;
""",
}

FUNCTION_BOUNDARY_BLANKS = {
    "check_vanbanden_cross_reference",
    "check_vanbanden_hoso_delete_cross_ref",
    "check_vanbandi_cross_reference",
    "check_vanbandi_hoso_delete_cross_ref",
}


TRIGGERS = [
    {
        "table": "documents_vanbanden_danhmuc",
        "name": "trg_vanbanden_danhmuc_cross_ref",
        "function": "check_vanbanden_cross_reference",
        "events": 23,
        "constraint": False,
        "deferrable": False,
        "initially_deferred": False,
        "arguments": (),
        "update_columns": (),
        "sql": """CREATE TRIGGER trg_vanbanden_danhmuc_cross_ref
  BEFORE INSERT OR UPDATE ON documents_vanbanden_danhmuc
  FOR EACH ROW EXECUTE FUNCTION check_vanbanden_cross_reference();""",
    },
    {
        "table": "documents_vanbanden_hoso",
        "name": "trg_vanbanden_hoso_del_cross_ref",
        "function": "check_vanbanden_hoso_delete_cross_ref",
        "events": 9,
        "constraint": True,
        "deferrable": True,
        "initially_deferred": False,
        "arguments": (),
        "update_columns": (),
        "sql": """CREATE CONSTRAINT TRIGGER trg_vanbanden_hoso_del_cross_ref
  AFTER DELETE ON documents_vanbanden_hoso
  DEFERRABLE INITIALLY IMMEDIATE
  FOR EACH ROW EXECUTE FUNCTION check_vanbanden_hoso_delete_cross_ref();""",
    },
    {
        "table": "documents_vanbandi_danhmuc",
        "name": "trg_vanbandi_danhmuc_cross_ref",
        "function": "check_vanbandi_cross_reference",
        "events": 23,
        "constraint": False,
        "deferrable": False,
        "initially_deferred": False,
        "arguments": (),
        "update_columns": (),
        "sql": """CREATE TRIGGER trg_vanbandi_danhmuc_cross_ref
  BEFORE INSERT OR UPDATE ON documents_vanbandi_danhmuc
  FOR EACH ROW EXECUTE FUNCTION check_vanbandi_cross_reference();""",
    },
    {
        "table": "documents_vanbandi_hoso",
        "name": "trg_vanbandi_hoso_del_cross_ref",
        "function": "check_vanbandi_hoso_delete_cross_ref",
        "events": 9,
        "constraint": True,
        "deferrable": True,
        "initially_deferred": False,
        "arguments": (),
        "update_columns": (),
        "sql": """CREATE CONSTRAINT TRIGGER trg_vanbandi_hoso_del_cross_ref
  AFTER DELETE ON documents_vanbandi_hoso
  DEFERRABLE INITIALLY IMMEDIATE
  FOR EACH ROW EXECUTE FUNCTION check_vanbandi_hoso_delete_cross_ref();""",
    },
    {
        "table": "documents_vanbanden",
        "name": "trg_del_viewlog_vanbanden",
        "function": "trg_cleanup_viewlog_on_doc_delete",
        "events": 9,
        "constraint": False,
        "deferrable": False,
        "initially_deferred": False,
        "arguments": ("vanbanden",),
        "update_columns": (),
        "sql": """CREATE TRIGGER trg_del_viewlog_vanbanden AFTER DELETE ON documents_vanbanden
    FOR EACH ROW EXECUTE FUNCTION trg_cleanup_viewlog_on_doc_delete('vanbanden');""",
    },
    {
        "table": "documents_vanbandi",
        "name": "trg_del_viewlog_vanbandi",
        "function": "trg_cleanup_viewlog_on_doc_delete",
        "events": 9,
        "constraint": False,
        "deferrable": False,
        "initially_deferred": False,
        "arguments": ("vanbandi",),
        "update_columns": (),
        "sql": """CREATE TRIGGER trg_del_viewlog_vanbandi AFTER DELETE ON documents_vanbandi
    FOR EACH ROW EXECUTE FUNCTION trg_cleanup_viewlog_on_doc_delete('vanbandi');""",
    },
    {
        "table": "documents_access_log",
        "name": "trg_documents_access_log_immutable",
        "function": "prevent_modify_documents_access_log",
        "events": 11,
        "constraint": False,
        "deferrable": False,
        "initially_deferred": False,
        "arguments": (),
        "update_columns": (),
        "sql": """CREATE TRIGGER trg_documents_access_log_immutable
    BEFORE UPDATE OR DELETE ON documents_access_log
    FOR EACH ROW EXECUTE FUNCTION prevent_modify_documents_access_log();""",
    },
    {
        "table": "documents_vanbanden",
        "name": "trg_vanbanden_no_hard_delete_han_che",
        "function": "prevent_delete_van_ban_han_che",
        "events": 11,
        "constraint": False,
        "deferrable": False,
        "initially_deferred": False,
        "arguments": (),
        "update_columns": (),
        "sql": """CREATE TRIGGER trg_vanbanden_no_hard_delete_han_che BEFORE DELETE ON documents_vanbanden
    FOR EACH ROW EXECUTE FUNCTION prevent_delete_van_ban_han_che();""",
    },
    {
        "table": "documents_vanbandi",
        "name": "trg_vanbandi_no_hard_delete_han_che",
        "function": "prevent_delete_van_ban_han_che",
        "events": 11,
        "constraint": False,
        "deferrable": False,
        "initially_deferred": False,
        "arguments": (),
        "update_columns": (),
        "sql": """CREATE TRIGGER trg_vanbandi_no_hard_delete_han_che BEFORE DELETE ON documents_vanbandi
    FOR EACH ROW EXECUTE FUNCTION prevent_delete_van_ban_han_che();""",
    },
    {
        "table": "documents_vanbanden",
        "name": "trg_vanbanden_pham_vi_bat_bien",
        "function": "prevent_change_pham_vi",
        "events": 19,
        "constraint": False,
        "deferrable": False,
        "initially_deferred": False,
        "arguments": (),
        "update_columns": ("pham_vi",),
        "sql": """CREATE TRIGGER trg_vanbanden_pham_vi_bat_bien BEFORE UPDATE OF pham_vi ON documents_vanbanden
    FOR EACH ROW EXECUTE FUNCTION prevent_change_pham_vi();""",
    },
    {
        "table": "documents_vanbandi",
        "name": "trg_vanbandi_pham_vi_bat_bien",
        "function": "prevent_change_pham_vi",
        "events": 19,
        "constraint": False,
        "deferrable": False,
        "initially_deferred": False,
        "arguments": (),
        "update_columns": ("pham_vi",),
        "sql": """CREATE TRIGGER trg_vanbandi_pham_vi_bat_bien BEFORE UPDATE OF pham_vi ON documents_vanbandi
    FOR EACH ROW EXECUTE FUNCTION prevent_change_pham_vi();""",
    },
]

DOCUMENT_KIND_LOG_TABLES = ("documents_view_log", "documents_access_log")
LEGACY_DOCUMENT_KIND = "vanbanmat"


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
    with schema_editor.connection.cursor() as cursor:
        for table, columns, _name in JUNCTION_KEYS:
            table_sql = q(table)
            null_predicate = " OR ".join(f"{q(column)} IS NULL" for column in columns)
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

        for table, columns, target, target_columns, _action, nullable in FOREIGN_KEYS:
            table_sql = q(table)
            target_sql = q(target)
            source_column = columns[0]
            target_column = target_columns[0]
            if not nullable:
                null_count = _count(cursor, f"SELECT COUNT(*) FROM {table_sql} WHERE {q(source_column)} IS NULL")
                if null_count:
                    raise RuntimeError(f"{table}: {null_count} hàng có khóa ngoại NULL; migration không thay đổi dữ liệu.")

            orphan_count = _count(
                cursor,
                f"SELECT COUNT(*) FROM {table_sql} AS source "
                f"LEFT JOIN {target_sql} AS target ON source.{q(source_column)} = target.{q(target_column)} "
                f"WHERE source.{q(source_column)} IS NOT NULL AND target.{q(target_column)} IS NULL",
            )
            if orphan_count:
                raise RuntimeError(f"{table}: {orphan_count} hàng có khóa ngoại mồ côi; migration không thay đổi dữ liệu.")


def _preflight_document_kind_logs(schema_editor):
    q = schema_editor.connection.ops.quote_name
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            """SELECT enum.enumlabel
               FROM pg_enum enum
               JOIN pg_type type ON type.oid = enum.enumtypid
               WHERE type.typnamespace = current_schema()::regnamespace
                 AND type.typname = 'document_kind'
               ORDER BY enum.enumsortorder"""
        )
        labels = tuple(row[0] for row in cursor.fetchall())
        if labels != ("vanbanden", "vanbandi"):
            raise RuntimeError("document_kind: 1 ENUM chưa khớp hai loại văn bản chuẩn; migration không thay đổi dữ liệu.")

        column_types = {}
        alias_counts = {}
        for table in DOCUMENT_KIND_LOG_TABLES:
            cursor.execute(
                """SELECT udt_name
                   FROM information_schema.columns
                   WHERE table_schema = current_schema() AND table_name = %s
                     AND column_name = 'document_type'""",
                [table],
            )
            row = cursor.fetchone()
            if not row:
                raise RuntimeError(f"{table}: 1 cột document_type không tồn tại; migration không thay đổi dữ liệu.")
            column_types[table] = row[0]
            if row[0] not in ("varchar", "document_kind"):
                raise RuntimeError(f"{table}: 1 cột document_type có kiểu không hỗ trợ; migration không thay đổi dữ liệu.")

            table_sql = q(table)
            unknown_count = _count(
                cursor,
                f"SELECT COUNT(*) FROM {table_sql} "
                "WHERE document_type IS NULL OR document_type::text NOT IN ('vanbanden', 'vanbandi', 'vanbanmat')",
            )
            if unknown_count:
                raise RuntimeError(f"{table}: {unknown_count} hàng có document_type không được nhận diện; migration không thay đổi dữ liệu.")

            alias_count = _count(
                cursor,
                f"SELECT COUNT(*) FROM {table_sql} WHERE document_type::text = '{LEGACY_DOCUMENT_KIND}'",
            )
            alias_counts[table] = alias_count
            if alias_count:
                unverified_alias_count = _count(
                    cursor,
                    f"SELECT COUNT(*) FROM {table_sql} AS log "
                    "LEFT JOIN documents_vanbanden AS document "
                    "ON document.id = log.document_id AND document.pham_vi = 'HAN_CHE' "
                    f"WHERE log.document_type::text = '{LEGACY_DOCUMENT_KIND}' AND document.id IS NULL",
                )
                if unverified_alias_count:
                    raise RuntimeError(f"{table}: {unverified_alias_count} hàng alias không trỏ tới văn bản đến hạn chế; migration không thay đổi dữ liệu.")

                if table == "documents_view_log":
                    collision_count = _count(
                        cursor,
                        """SELECT COUNT(*)
                           FROM documents_view_log legacy
                           JOIN documents_view_log canonical
                             ON canonical.document_type::text = 'vanbanden'
                            AND canonical.document_id = legacy.document_id
                            AND canonical.user_id = legacy.user_id
                           WHERE legacy.document_type::text = 'vanbanmat'""",
                    )
                    if collision_count:
                        raise RuntimeError(f"{table}: {collision_count} hàng alias xung đột khóa duy nhất; migration không thay đổi dữ liệu.")

                if table == "documents_access_log":
                    cursor.execute(
                        """SELECT COUNT(*)
                           FROM pg_trigger trigger
                           WHERE trigger.tgrelid = %s::regclass
                             AND NOT trigger.tgisinternal
                             AND trigger.tgenabled <> 'D'
                             AND (trigger.tgtype & 16) <> 0""",
                        [table],
                    )
                    protected_updates = cursor.fetchone()[0]
                    if protected_updates:
                        raise RuntimeError(f"{table}: {alias_count} hàng alias gặp trigger bảo vệ UPDATE; migration không thay đổi dữ liệu.")

        return column_types, alias_counts


def _canonicalize_document_kind_logs(schema_editor, preflight):
    column_types, alias_counts = preflight
    q = schema_editor.connection.ops.quote_name
    with schema_editor.connection.cursor() as cursor:
        # Preserve each historical row and its primary key, timestamp and action.
        # The preflight proved every alias points to a restricted incoming record,
        # and checked the view-log unique key before changing its kind.
        for table in DOCUMENT_KIND_LOG_TABLES:
            if alias_counts[table]:
                cursor.execute(
                    f"UPDATE {q(table)} SET document_type = 'vanbanden' "
                    f"WHERE document_type::text = '{LEGACY_DOCUMENT_KIND}'"
                )
            if column_types[table] != "document_kind":
                cursor.execute(
                    f"ALTER TABLE {q(table)} ALTER COLUMN document_type TYPE document_kind "
                    "USING document_type::text::document_kind"
                )


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


def _ensure_primary_key(schema_editor, table, columns, constraint_name):
    q = schema_editor.connection.ops.quote_name
    with schema_editor.connection.cursor() as cursor:
        primary_keys = _constraint_columns(cursor, table, "p")
        exact = next((row for row in primary_keys if tuple(row[1]) == tuple(columns) and row[2]), None)
        if exact:
            keep_name = exact[0]
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

        constraint_name = "fk_" + table.removeprefix("documents_") + "_" + "_".join(columns)
        local_sql = ", ".join(q(column) for column in columns)
        target_columns_sql = ", ".join(q(column) for column in target_columns)
        action_sql = "" if on_delete == "NO ACTION" else f" ON DELETE {on_delete}"
        cursor.execute(
            f"ALTER TABLE {q(table)} ADD CONSTRAINT {q(constraint_name)} "
            f"FOREIGN KEY ({local_sql}) REFERENCES {q(target)} ({target_columns_sql}){action_sql}"
        )


def _ensure_function(schema_editor, name, body):
    q = schema_editor.connection.ops.quote_name
    code = body.strip()
    boundary = "\n\n" if name in FUNCTION_BOUNDARY_BLANKS else "\n"
    expected_source = boundary + code + boundary
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            """SELECT p.prosrc, p.prorettype::regtype::text, language.lanname,
                      p.provolatile, p.prosecdef, p.proisstrict, p.proleakproof,
                      p.proparallel, p.procost, p.proconfig, p.prokind
               FROM pg_proc p
               JOIN pg_language language ON language.oid = p.prolang
               WHERE p.pronamespace = current_schema()::regnamespace
                 AND p.proname = %s AND p.pronargs = 0""",
            [name],
        )
        row = cursor.fetchone()
        if row and (
            row[0].replace("\r\n", "\n") == expected_source
            and row[1] == "trigger"
            and row[2] == "plpgsql"
            and row[3] == "v"
            and not row[4]
            and not row[5]
            and not row[6]
            and row[7] == "u"
            and float(row[8]) == 100.0
            and row[9] is None
            and row[10] == "f"
        ):
            return

        if row and row[1] != "trigger":
            # CREATE OR REPLACE cannot change a function's return type. Do not CASCADE:
            # an unrelated dependency must stop this migration rather than be removed.
            cursor.execute(f"DROP FUNCTION {q(name)}()")
        sql = (
            f"CREATE OR REPLACE FUNCTION {q(name)}() RETURNS TRIGGER "
            "LANGUAGE plpgsql VOLATILE CALLED ON NULL INPUT SECURITY INVOKER "
            f"PARALLEL UNSAFE COST 100 AS $${expected_source}$$;"
        )
        cursor.execute(sql, params=None)


def _trigger_args(raw):
    if raw is None:
        return ()
    return tuple(part.decode("utf-8") for part in bytes(raw).split(b"\0") if part)


def _trigger_rows(cursor, table):
    cursor.execute(
        """SELECT trigger.tgname, trigger.tgtype, trigger.tgconstraint <> 0,
                  trigger.tgdeferrable, trigger.tginitdeferred, trigger.tgenabled,
                  function.proname, trigger.tgargs, trigger.tgqual IS NULL,
                  ARRAY(
                      SELECT att.attname
                      FROM unnest(trigger.tgattr::smallint[]) WITH ORDINALITY AS key(attnum, ord)
                      JOIN pg_attribute att ON att.attrelid = trigger.tgrelid AND att.attnum = key.attnum
                      ORDER BY key.ord
                  )
           FROM pg_trigger trigger
           JOIN pg_proc function ON function.oid = trigger.tgfoid
           WHERE trigger.tgrelid = %s::regclass AND NOT trigger.tgisinternal""",
        [table],
    )
    return cursor.fetchall()


def _ensure_trigger(schema_editor, spec):
    q = schema_editor.connection.ops.quote_name
    expected = (
        spec["events"], spec["constraint"], spec["deferrable"],
        spec["initially_deferred"], "O", spec["function"],
        spec["arguments"], True, spec["update_columns"],
    )
    with schema_editor.connection.cursor() as cursor:
        rows = _trigger_rows(cursor, spec["table"])
        by_name = next((row for row in rows if row[0] == spec["name"]), None)

        def definition(row):
            return (
                row[1], row[2], row[3], row[4], row[5], row[6],
                _trigger_args(row[7]), row[8], tuple(row[9] or ()),
            )

        if by_name and definition(by_name) == expected:
            return

        equivalent = next((row for row in rows if definition(row) == expected), None)
        if by_name:
            cursor.execute(
                f"DROP TRIGGER {q(spec['name'])} ON {q(spec['table'])}"
            )
        if equivalent:
            cursor.execute(
                f"ALTER TRIGGER {q(equivalent[0])} ON {q(spec['table'])} "
                f"RENAME TO {q(spec['name'])}"
            )
            return

        cursor.execute(spec["sql"], params=None)


def install_integrity(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        raise RuntimeError("documents 0008 integrity requires PostgreSQL.")

    # Check every table before the first DDL change. The migration is atomic on
    # PostgreSQL, and the catalog constraints repeat these checks under lock.
    document_kind_preflight = _preflight_document_kind_logs(schema_editor)
    _preflight(schema_editor)
    _canonicalize_document_kind_logs(schema_editor, document_kind_preflight)

    for table, columns, constraint_name in JUNCTION_KEYS:
        _ensure_primary_key(schema_editor, table, columns, constraint_name)
    for foreign_key in FOREIGN_KEYS:
        _ensure_foreign_key(schema_editor, foreign_key)
    for name, body in FUNCTION_BODIES.items():
        _ensure_function(schema_editor, name, body)
    for trigger in TRIGGERS:
        _ensure_trigger(schema_editor, trigger)


class Migration(migrations.Migration):
    atomic = True

    dependencies = [
        ("accounts", "0007_normalize_system_account_password"),
        ("documents", "0007_folder_is_local_folder_local_path_and_more"),
        ("organizations", "0005_reference_data_ddl"),
        ("records", "0003_reference_data_ddl"),
        ("work", "0007_align_defaults_fks_check"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[migrations.RunPython(install_integrity, migrations.RunPython.noop)],
            state_operations=[],
        ),
    ]
