"""So schema PostgreSQL tạo bằng Django migration với schema dựng từ release_DDL.sql.

So theo catalog (bảng, cột, kiểu, NULL, DEFAULT, constraint, index, ENUM, VIEW), không so văn bản
pg_dump, và bỏ qua các khác biệt do Django luôn sinh ra mà không phải lệch nghiệp vụ:
- tên constraint/index do Django tự đặt (so theo nội dung, không so theo tên);
- FK của Django luôn DEFERRABLE INITIALLY DEFERRED; ON DELETE RESTRICT/NO ACTION được Django
  xử lý ở tầng ứng dụng (on_delete=PROTECT/RESTRICT);
- index *_like (varchar_pattern_ops) Django tự thêm cho cột varchar có index/unique;
- index thường thừa (Django tự tạo index cho cột FK) không làm sai dữ liệu; index UNIQUE thừa vẫn báo;
- bảng của framework: django_*, token_blacklist_*.

Các lệch đã biết, đang chờ nhóm phụ trách sửa, ghi trong file baseline (mỗi dòng một lệch,
dòng bắt đầu bằng # là chú thích). Job fail khi:
- có lệch mới không nằm trong baseline (chặn lệch phát sinh);
- có dòng trong baseline không còn lệch (đã sửa xong thì phải xóa khỏi baseline).

Dùng: python compare_schema_ddl.py <db_migration> <db_ddl> <baseline_file> [--write-baseline]
Kết nối lấy từ POSTGRES_HOST/PORT/USER/PASSWORD.
"""
import os
import re
import sys

import psycopg

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


def norm_check(definition):
    """Đưa các dạng viết tương đương mà Django sinh cho Q(~...) về dạng DDL hay dùng."""
    # NOT ((col)= ANY ((ARRAY[...])))  ->  ((col)<> ALL ((ARRAY[...])))
    definition = re.sub(r"\(NOT \(\((\w+)\)= ANY \(\((ARRAY\[[^\]]*\])\)\)\)\)", r"((\1)<> ALL ((\2)))", definition)
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
        cur.execute("SELECT table_name FROM information_schema.views WHERE table_schema = 'public'")
        views = {row[0] for row in cur.fetchall()}
    return tables, enums, views


def drift(migration_db, ddl_db):
    mig_tables, mig_enums, mig_views = snapshot(migration_db)
    ddl_tables, ddl_enums, ddl_views = snapshot(ddl_db)
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
    for view in sorted(ddl_views - mig_views):
        found.append(f"VIEW {view}: thiếu")
    return found


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    migration_db, ddl_db, baseline_path = args
    current = drift(migration_db, ddl_db)

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
