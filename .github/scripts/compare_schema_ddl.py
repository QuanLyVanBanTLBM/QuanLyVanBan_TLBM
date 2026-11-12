"""So schema PostgreSQL tạo bằng Django migration với schema dựng từ release_DDL.sql.

So theo catalog (bảng, cột, kiểu, NULL, DEFAULT, constraint, index, ENUM, function, trigger, VIEW gồm
nội dung, dữ liệu seed), không so văn bản pg_dump, và bỏ qua các khác biệt do Django luôn sinh ra mà không phải lệch nghiệp vụ:
- tên constraint/index do Django tự đặt (so theo nội dung, không so theo tên);
- FK của Django luôn DEFERRABLE INITIALLY DEFERRED; ON DELETE RESTRICT/NO ACTION được Django
  xử lý ở tầng ứng dụng (on_delete=PROTECT/RESTRICT);
- index *_like (varchar_pattern_ops) Django tự thêm cho cột varchar có index/unique;
- index thường thừa (Django tự tạo index cho cột FK) không làm sai dữ liệu; index UNIQUE thừa vẫn báo;
- bảng của framework: django_*, token_blacklist_*;
- dữ liệu seed: bảng nào có dòng ở ít nhất một DB thì so tập dòng (đa tập, không phụ thuộc thứ tự) trên các
  cột chung, bỏ cột tự sinh (nextval/identity) và cột có DEFAULT không xác định (now(), CURRENT_TIMESTAMP,
  gen_random_uuid()); mỗi bảng một dòng lệch ghi số dòng thiếu/thừa kèm dấu vân tay (sha256) nội dung.

Hai DB phải cùng collation (datlocprovider, locale ICU), nếu không script dừng với lỗi: thứ tự ORDER BY theo
chuỗi trong query của app và view (ví dụ string_agg(... ORDER BY dv.ten)) phụ thuộc collation.

Function, trigger và view so nguyên văn đầu ra pg_get_functiondef (chỉ đổi CRLF thành LF), pg_get_triggerdef,
pg_get_viewdef; trạng thái bật/tắt của trigger (tgenabled) so riêng. Không chuẩn hoá khoảng trắng vì khoảng trắng
trong literal hoặc thân function có thể đổi kết quả chạy. Hệ quả: migration RunSQL tạo function/trigger/view phải
chép nguyên văn từ release_DDL.sql.

Các lệch đã biết, đang chờ nhóm phụ trách sửa, ghi trong file baseline (mỗi dòng một lệch,
dòng bắt đầu bằng # là chú thích). Job fail khi:
- có lệch mới không nằm trong baseline (chặn lệch phát sinh);
- có dòng trong baseline không còn lệch (đã sửa xong thì phải xóa khỏi baseline).

Dùng: python compare_schema_ddl.py <db_migration> <db_ddl> <baseline_file> [--write-baseline]
Kết nối lấy từ POSTGRES_HOST/PORT/USER/PASSWORD.
"""
import hashlib
import os
import re
import sys
from collections import Counter

import psycopg
from psycopg import sql

FRAMEWORK_TABLE_PREFIXES = ("django_", "token_blacklist_")


def connect(db):
    return psycopg.connect(
        dbname=db,
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=os.environ.get("POSTGRES_PORT", "5432"),
        user=os.environ.get("POSTGRES_USER", "postgres"),
        password=os.environ.get("POSTGRES_PASSWORD", ""),
    )


def norm(sql):
    if sql is None:
        return None
    sql = re.sub(r"::[a-z_ ]+(\[\])?", "", sql)
    return re.sub(r"\s+", " ", sql).strip()


CHECK_ARRAY = r"ARRAY\[(?:[^\]']|'(?:[^']|'')*')*\]"


def norm_check_arrays(definition):
    definition = re.sub(r"(?:(?<=\[)|(?<=, ))\('((?:[^']|'')*)'\)", r"'\1'", definition)
    return re.sub(rf"\b(ANY|ALL) \(\(({CHECK_ARRAY})\)\)", r"\1 (\2)", definition)


def norm_check(definition):
    """Đưa các dạng viết tương đương mà Django sinh cho Q(~...) về dạng DDL hay dùng."""
    signer_one_of_two_ddl = (
        "CHECK ((((chuc_vu_id IS NULL) AND (nguoi_ky_id IS NOT NULL)) OR "
        "((chuc_vu_id IS NOT NULL) AND (nguoi_ky_id IS NULL))))"
    )
    signer_one_of_two_migration = (
        "CHECK ((((nguoi_ky_id IS NOT NULL) AND (chuc_vu_id IS NULL)) OR "
        "((nguoi_ky_id IS NULL) AND (chuc_vu_id IS NOT NULL))))"
    )
    if definition in {signer_one_of_two_ddl, signer_one_of_two_migration}:
        return signer_one_of_two_ddl
    # NOT (TRIM(BOTH FROM col) = '')  ->  (btrim((col)) <> '')   (dạng Django sinh so với btrim(col) <> '' của DDL)
    definition = re.sub(r"\(NOT \(TRIM\(BOTH FROM \(?(\w+)\)?\) = ''\)\)", r"(btrim((\1)) <> '')", definition)
    # btrim(col) <> ''  ->  btrim((col)) <> ''   (cột varchar có thêm lớp ngoặc do ép kiểu đã bị norm() bỏ)
    definition = re.sub(r"btrim\(\(?(\w+)\)?\) <> ''", r"btrim((\1)) <> ''", definition)
    # ARRAY sau pg_restore: ANY (ARRAY[('a'), ('b')])  ->  ANY (ARRAY['a', 'b']);  ANY ((ARRAY[...]))  ->  ANY (ARRAY[...])
    definition = norm_check_arrays(definition)
    # NOT ((col)= ANY (ARRAY[...]))  ->  ((col)<> ALL (ARRAY[...]))
    definition = re.sub(rf"\(NOT \(\((\w+)\)= ANY \(({CHECK_ARRAY})\)\)\)", r"((\1)<> ALL (\2))", definition)
    # NOT ((col)= 'x')  ->  ((col)<> 'x')
    definition = re.sub(r"\(NOT \(\((\w+)\)= ('[^']*')\)\)", r"((\1)<> \2)", definition)
    # (NOT col)  ->  (col = false)
    definition = re.sub(r"\(NOT (\w+)\)", r"(\1 = false)", definition)
    return definition


def snapshot(db):
    with connect(db) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
        )
        tables = {}
        for (table,) in cur.fetchall():
            cur.execute(
                "SELECT column_name, udt_name, character_maximum_length, is_nullable, column_default, is_identity "
                "FROM information_schema.columns WHERE table_schema = 'public' AND table_name = %s",
                [table],
            )
            columns = {}
            for name, udt, length, nullable, default, identity in cur.fetchall():
                if identity == "YES" or (default or "").startswith("nextval("):
                    default = "<tự tăng>"
                columns[name] = f"{udt}({length or ''}) null={nullable} default={norm(default)}"
            cur.execute(
                "SELECT contype, pg_get_constraintdef(oid) FROM pg_constraint "
                "WHERE conrelid = %s::regclass AND contype IN ('c', 'f', 'p', 'u', 'x')",
                [f'public."{table}"'],
            )
            constraints = set()
            for kind, definition in cur.fetchall():
                definition = norm(definition)
                if kind == "c":
                    definition = norm_check(definition)
                if kind == "f":
                    definition = re.sub(r" DEFERRABLE INITIALLY DEFERRED", "", definition)
                    definition = re.sub(r" ON DELETE (RESTRICT|NO ACTION)", "", definition)
                constraints.add(definition)
            cur.execute(
                "SELECT indexname, indexdef FROM pg_indexes WHERE schemaname = 'public' AND tablename = %s",
                [table],
            )
            indexes = set()
            for name, definition in cur.fetchall():
                if name.endswith("_like") or "_pattern_ops" in definition:
                    continue
                indexes.add(norm(re.sub(r"^CREATE (UNIQUE )?INDEX \S+ ON \S+ ", r"\1", definition)))
            tables[table] = (columns, constraints, indexes)
        cur.execute(
            "SELECT t.typname, string_agg(e.enumlabel, ',' ORDER BY e.enumsortorder) "
            "FROM pg_type t JOIN pg_enum e ON e.enumtypid = t.oid GROUP BY t.typname"
        )
        enums = dict(cur.fetchall())
        cur.execute(
            "SELECT v.viewname, pg_get_viewdef(c.oid, true), c.reloptions "
            "FROM pg_views v JOIN pg_class c ON c.relname = v.viewname AND c.relnamespace = 'public'::regnamespace "
            "WHERE v.schemaname = 'public'"
        )
        views = {name: f"{definition} options={sorted(options or [])}" for name, definition, options in cur.fetchall()}
        cur.execute(
            "SELECT p.proname || '(' || pg_get_function_identity_arguments(p.oid) || ')', pg_get_functiondef(p.oid) "
            "FROM pg_proc p WHERE p.pronamespace = 'public'::regnamespace AND p.prokind IN ('f', 'p') "
            "AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.objid = p.oid AND d.deptype = 'e')"
        )
        functions = {name: definition.replace("\r\n", "\n") for name, definition in cur.fetchall()}
        cur.execute(
            "SELECT c.relname || '.' || t.tgname, pg_get_triggerdef(t.oid), t.tgenabled "
            "FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid "
            "WHERE c.relnamespace = 'public'::regnamespace AND NOT t.tgisinternal"
        )
        triggers = {name: (definition, enabled) for name, definition, enabled in cur.fetchall()}
    return tables, enums, views, functions, triggers


VOLATILE_DEFAULT = re.compile(r"nextval\(|now\(\)|current_timestamp|current_date|gen_random_uuid|uuid_generate", re.I)


def seed_rows(cur, table, columns):
    cur.execute(
        sql.SQL("SELECT ROW({})::text FROM {}").format(
            sql.SQL(", ").join(sql.Identifier(c) for c in columns), sql.Identifier(table)
        )
    )
    return Counter(row[0] for row in cur.fetchall())


def fingerprint(rows):
    """Dấu vân tay xác định của đa tập dòng: sha256 của các cặp (dòng, số lần) đã sắp xếp."""
    if not rows:
        return "-"
    digest = hashlib.sha256()
    for row, count in sorted(rows.items()):
        digest.update(f"{count}\t{row}\n".encode("utf-8"))
    return digest.hexdigest()[:16]


def row_count(cur, table):
    cur.execute(sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(table)))
    return cur.fetchone()[0]


def semantic_seed_rows(cur, table):
    """Rows for RBAC seed tables, keyed by stable permission/group semantics."""
    if table == "auth_permission":
        cur.execute(
            "SELECT ROW(permission.codename, permission.name, permission.module_ten, "
            "content_type.app_label, content_type.model)::text "
            "FROM auth_permission permission "
            "LEFT JOIN django_content_type content_type "
            "ON content_type.id = permission.content_type_id"
        )
    elif table == "auth_group_permissions":
        cur.execute(
            "SELECT ROW(group_info.ma_nhom_quyen, "
            "CASE WHEN group_info.ma_nhom_quyen IS NULL THEN group_info.name END, "
            "permission.codename)::text "
            "FROM auth_group_permissions grant_row "
            "JOIN auth_group group_info ON group_info.id = grant_row.group_id "
            "JOIN auth_permission permission ON permission.id = grant_row.permission_id"
        )
    else:
        raise ValueError(f"No semantic seed mapping for {table}.")
    return Counter(row[0] for row in cur.fetchall())


def seed_drift(migration_db, ddl_db, mig_tables, ddl_tables):
    """So đa tập dòng của bảng có dữ liệu ở ít nhất một DB, trên cột chung và xác định.

    Dòng lệch ghi số dòng thiếu/thừa kèm dấu vân tay nội dung, nên đổi giá trị mà giữ số đếm vẫn đổi dòng.
    """
    found = []
    with connect(migration_db) as mig_conn, connect(ddl_db) as ddl_conn:
        mig_cur, ddl_cur = mig_conn.cursor(), ddl_conn.cursor()
        for table in sorted(set(mig_tables) & set(ddl_tables)):
            if table.startswith(FRAMEWORK_TABLE_PREFIXES):
                continue
            if row_count(ddl_cur, table) == 0 and row_count(mig_cur, table) == 0:
                continue
            mig_cols, ddl_cols = mig_tables[table][0], ddl_tables[table][0]
            keep = sorted(
                c for c in set(mig_cols) & set(ddl_cols)
                if "<tự tăng>" not in ddl_cols[c] and not VOLATILE_DEFAULT.search(ddl_cols[c])
                and not VOLATILE_DEFAULT.search(mig_cols[c])
            )
            if (
                table == "auth_permission"
                and {"name", "codename", "module_ten", "content_type_id"} <= set(keep)
                and "django_content_type" in mig_tables
                and "django_content_type" in ddl_tables
            ):
                expected = semantic_seed_rows(ddl_cur, table)
                actual = semantic_seed_rows(mig_cur, table)
            elif (
                table == "auth_group_permissions"
                and "group_id" in keep
                and "permission_id" in keep
                and "auth_group" in mig_tables
                and "auth_group" in ddl_tables
                and "auth_permission" in mig_tables
                and "auth_permission" in ddl_tables
                and {"ma_nhom_quyen", "name"} <= set(mig_tables["auth_group"][0])
                and "codename" in set(mig_tables["auth_permission"][0])
                and {"ma_nhom_quyen", "name"} <= set(ddl_tables["auth_group"][0])
                and "codename" in set(ddl_tables["auth_permission"][0])
            ):
                expected = semantic_seed_rows(ddl_cur, table)
                actual = semantic_seed_rows(mig_cur, table)
            else:
                expected, actual = seed_rows(ddl_cur, table, keep), seed_rows(mig_cur, table, keep)
            missing, extra = expected - actual, actual - expected
            if missing or extra:
                found.append(
                    f"SEED {table}: DDL {sum(expected.values())} dòng, "
                    f"migration thiếu {sum(missing.values())} #{fingerprint(missing)}, "
                    f"thừa {sum(extra.values())} #{fingerprint(extra)}"
                )
    return found


def collation(db):
    """(provider, icu_locale) của DB; PG16 gọi cột là daticulocale, PG17 đổi thành datlocale."""
    with connect(db) as conn:
        return conn.execute(
            "SELECT datlocprovider, coalesce(to_jsonb(d)->>'datlocale', to_jsonb(d)->>'daticulocale') "
            "FROM pg_database d WHERE datname = current_database()"
        ).fetchone()


def require_same_collation(migration_db, ddl_db):
    """ORDER BY theo chuỗi (app, view) phụ thuộc collation: hai DB khác collation thì không so."""
    mig, ddl = collation(migration_db), collation(ddl_db)
    if mig != ddl:
        raise SystemExit(
            f"Hai DB khác collation (provider, locale): {migration_db} = {mig}, {ddl_db} = {ddl}. "
            "Dựng lại cả hai với cùng collation (ICU vi-VN) trước khi so schema."
        )


def drift(migration_db, ddl_db, *, include_data=True):
    require_same_collation(migration_db, ddl_db)
    mig_tables, mig_enums, mig_views, mig_funcs, mig_trigs = snapshot(migration_db)
    ddl_tables, ddl_enums, ddl_views, ddl_funcs, ddl_trigs = snapshot(ddl_db)
    found = []
    for table in sorted(set(mig_tables) | set(ddl_tables)):
        if table not in mig_tables:
            found.append(f"{table}: thiếu bảng")
            continue
        if table not in ddl_tables:
            if not table.startswith(FRAMEWORK_TABLE_PREFIXES):
                found.append(f"{table}: bảng không có trong DDL")
            continue
        mig_cols, mig_cons, mig_idx = mig_tables[table]
        ddl_cols, ddl_cons, ddl_idx = ddl_tables[table]
        for col in sorted(set(mig_cols) | set(ddl_cols)):
            if col not in mig_cols:
                found.append(f"{table}.{col}: thiếu cột, DDL: {ddl_cols[col]}")
            elif col not in ddl_cols:
                found.append(f"{table}.{col}: cột không có trong DDL")
            elif mig_cols[col] != ddl_cols[col]:
                found.append(f"{table}.{col}: migration {mig_cols[col]} | DDL {ddl_cols[col]}")
        for item in sorted(ddl_cons - mig_cons):
            found.append(f"{table}: thiếu constraint {item}")
        for item in sorted(mig_cons - ddl_cons):
            found.append(f"{table}: constraint không có trong DDL {item}")
        for item in sorted(ddl_idx - mig_idx):
            found.append(f"{table}: thiếu index {item}")
        for item in sorted(mig_idx - ddl_idx):
            # Index thường thừa không làm sai dữ liệu; UNIQUE thừa là ràng buộc nghiệp vụ DDL không có.
            if item.startswith("UNIQUE "):
                found.append(f"{table}: index UNIQUE không có trong DDL {item}")
    for enum in sorted(set(mig_enums) | set(ddl_enums)):
        if enum not in mig_enums:
            found.append(f"ENUM {enum}: thiếu ({ddl_enums[enum]})")
        elif enum not in ddl_enums:
            found.append(f"ENUM {enum}: không có trong DDL")
        elif mig_enums[enum] != ddl_enums[enum]:
            found.append(f"ENUM {enum}: migration ({mig_enums[enum]}) | DDL ({ddl_enums[enum]})")
    for view in sorted(set(mig_views) | set(ddl_views)):
        if view not in mig_views:
            found.append(f"VIEW {view}: thiếu")
        elif view not in ddl_views:
            found.append(f"VIEW {view}: không có trong DDL")
        elif mig_views[view] != ddl_views[view]:
            found.append(f"VIEW {view}: khác định nghĩa so với DDL")
    for name in sorted(set(mig_funcs) | set(ddl_funcs)):
        if name not in mig_funcs:
            found.append(f"FUNCTION {name}: thiếu")
        elif name not in ddl_funcs:
            found.append(f"FUNCTION {name}: không có trong DDL")
        elif mig_funcs[name] != ddl_funcs[name]:
            found.append(f"FUNCTION {name}: khác định nghĩa so với DDL")
    for name in sorted(set(mig_trigs) | set(ddl_trigs)):
        if name not in mig_trigs:
            found.append(f"TRIGGER {name}: thiếu")
        elif name not in ddl_trigs:
            found.append(f"TRIGGER {name}: không có trong DDL")
        else:
            (mig_def, mig_state), (ddl_def, ddl_state) = mig_trigs[name], ddl_trigs[name]
            if mig_def != ddl_def:
                found.append(f"TRIGGER {name}: khác định nghĩa so với DDL")
            if mig_state != ddl_state:
                found.append(f"TRIGGER {name}: trạng thái migration {mig_state} | DDL {ddl_state}")
    if include_data:
        found.extend(seed_drift(migration_db, ddl_db, mig_tables, ddl_tables))
    return found


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    migration_db, ddl_db, baseline_path = args
    current = drift(migration_db, ddl_db, include_data="--schema-only" not in sys.argv)

    if "--write-baseline" in sys.argv:
        with open(baseline_path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("# Lệch schema đã biết giữa Django migration và release_DDL.sql, chờ nhóm phụ trách sửa.\n")
            fh.write("# Sinh bởi .github/scripts/compare_schema_ddl.py --write-baseline. Sửa xong lệch nào thì xóa dòng đó.\n")
            for line in current:
                fh.write(line + "\n")
        print(f"Đã ghi {len(current)} lệch vào {baseline_path}")
        return 0

    with open(baseline_path, encoding="utf-8") as fh:
        baseline = {line.rstrip("\n") for line in fh if line.strip() and not line.startswith("#")}
    new = [line for line in current if line not in baseline]
    fixed = sorted(baseline - set(current))

    print(f"Lệch hiện tại: {len(current)} | trong baseline: {len(baseline)}")
    if new:
        print(f"\n::error::{len(new)} lệch MỚI so với release_DDL.sql (không có trong baseline):")
        for line in new:
            print("  " + line)
    if fixed:
        print(f"\n::error::{len(fixed)} dòng baseline đã hết lệch, xóa khỏi {baseline_path}:")
        for line in fixed:
            print("  " + line)
    return 1 if new or fixed else 0


if __name__ == "__main__":
    sys.exit(main())
