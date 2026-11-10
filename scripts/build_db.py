"""Bootstrap, adopt đã xác minh, đồng bộ migration hoặc reset có chủ ý cho PostgreSQL.

--if-empty bootstrap DB rỗng; --adopt xác minh marker v2 cũ; --sync chạy migration thật trên DB v3;
--force xóa và dựng lại DB. Hash DDL đổi không tự kích hoạt reset. Kết nối lấy từ DB_HOST, DB_PORT,
DB_USER, DB_PASSWORD, DB_NAME; cần DJANGO_SECRET_KEY và thư viện backend.

Dùng: python scripts/build_db.py --dbname TÊN --if-empty --seed
     python scripts/build_db.py --dbname TÊN --adopt | --sync
     python scripts/build_db.py --dbname TÊN --force --seed
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import uuid
from pathlib import Path

import psycopg
from psycopg import sql

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
DEFAULT_DDL = ROOT / "docs" / "common" / "database" / "release_DDL.sql"
MAINTENANCE_DB = "postgres"
MARK_PREFIX = "build_db:v3"
LEGACY_MARK_PREFIX = "build_db:v2"
# The only v2 database supported for adoption is the release at 22fa331. Its DDL
# fingerprint, catalog fingerprint (DDL plus migrations actually applied by that
# release's builder), and complete historical migration set are pinned; the marker
# by itself is never treated as proof that a database is safe to upgrade.
LEGACY_V2_DDL_SHA256 = "419d9dcf65ff3b79cdc1b6c44967421b3ba04009b62cf6a1c6071b60d70d6a6a"
LEGACY_V2_SCHEMA_SHA256 = "d13c158260c4a330b63552f17a1d44deb9055f8a0ca4934ea9bd799e3c468f49"
LEGACY_V2_MIGRATIONS = frozenset({
    ("accounts", "0001_initial"),
    ("accounts", "0002_position_import_permission"),
    ("accounts", "0003_alter_employee_sdt"),
    ("accounts", "0004_align_release_ddl"),
    ("accounts", "0005_align_release_ddl"),
    ("admin", "0001_initial"),
    ("admin", "0002_logentry_remove_auto_add"),
    ("admin", "0003_logentry_add_action_flag_choices"),
    ("auth", "0001_initial"),
    ("auth", "0002_alter_permission_name_max_length"),
    ("auth", "0003_alter_user_email_max_length"),
    ("auth", "0004_alter_user_username_opts"),
    ("auth", "0005_alter_user_last_login_null"),
    ("auth", "0006_require_contenttypes_0002"),
    ("auth", "0007_alter_validators_add_error_messages"),
    ("auth", "0008_alter_user_username_max_length"),
    ("auth", "0009_alter_user_last_name_max_length"),
    ("auth", "0010_alter_group_name_max_length"),
    ("auth", "0011_update_proxy_permissions"),
    ("auth", "0012_alter_user_first_name_max_length"),
    ("authorization", "0001_initial"),
    ("authorization", "0002_rbac_standard_data"),
    ("authorization", "0003_remove_vanbanmat_permissions"),
    ("authorization", "0004_grant_tp_manage_signing_process"),
    ("birthdays", "0001_initial_birthdays_sql_fix4"),
    ("birthdays", "0002_align_release_ddl"),
    ("contenttypes", "0001_initial"),
    ("contenttypes", "0002_remove_content_type_name"),
    ("dashboard", "0001_initial"),
    ("document_templates", "0001_initial"),
    ("document_templates", "0002_normalize_column_names_ddl_pr96"),
    ("documents", "0001_initial"),
    ("documents", "0002_documentaccesslog_vanbanden_pham_vi_vanbandi_pham_vi_and_more"),
    ("documents", "0003_alter_vanbanden_nguoi_tao_and_more"),
    ("documents", "0004_vanbandendanhmuc_vanbandendonvinhan_vanbandenhoso_and_more"),
    ("documents", "0005_alter_vanbandendanhmuc_unique_together_and_more"),
    ("meetings", "0001_initial"),
    ("meetings", "0002_align_release_ddl"),
    ("organizations", "0001_initial"),
    ("organizations", "0002_alter_khoikhuvuc_options_khoikhuvuc_thu_tu_hien_thi_and_more"),
    ("organizations", "0003_remove_donvi_created_at_remove_donvi_updated_at_and_more"),
    ("organizations", "0004_align_release_ddl"),
    ("sessions", "0001_initial"),
    ("signing", "0001_khoi_tao_khoa_va_quy_trinh"),
    ("signing", "0002_khoi_tao_luong_trinh_ky"),
    ("signing", "0003_mo_khoa_ky_bang_pin"),
    ("signing", "0004_bo_vanbanmat"),
    ("signing", "0005_bo_kieu_ky_chi_nhan_van_ban_di"),
    ("signing", "0006_ho_so_goc_pham_vi_chuc_vu_muc_do"),
    ("signing", "0007_tep_hoan_tat"),
    ("signing", "0008_don_vi_ap_dung"),
    ("signing", "0009_doi_ten_cot_theo_ddl_chuan_hoa"),
    ("token_blacklist", "0001_initial"),
    ("token_blacklist", "0002_outstandingtoken_jti_hex"),
    ("token_blacklist", "0003_auto_20171017_2007"),
    ("token_blacklist", "0004_auto_20171017_2013"),
    ("token_blacklist", "0005_remove_outstandingtoken_jti"),
    ("token_blacklist", "0006_auto_20171017_2113"),
    ("token_blacklist", "0007_auto_20171017_2214"),
    ("token_blacklist", "0008_migrate_to_bigautofield"),
    ("token_blacklist", "0010_fix_migrate_to_bigautofield"),
    ("token_blacklist", "0011_linearizes_history"),
    ("token_blacklist", "0012_alter_outstandingtoken_user"),
    ("token_blacklist", "0013_alter_blacklistedtoken_options_and_more"),
})
# These migrations did not have rows in the supported release history, but their
# schema effects are present in that exact release schema (some were applied after
# loading the raw DDL). Adoption records only these named baseline operations after
# the whole catalog fingerprint matches. All other pending migrations, including
# RunPython/RunSQL data changes, execute normally in --sync.
LEGACY_V2_BASELINE_MIGRATIONS = frozenset({
    ("records", "0001_initial"),
    ("records", "0002_hoso_guards"),
    ("work", "0001_initial"),
    ("work", "0002_taskattachment_comment_and_more"),
    ("work", "0003_taskdonvi_alter_task_options_and_more"),
    ("work", "0004_alter_task_options_and_more"),
    ("work", "0005_taskdonvi_don_vi_fk"),
    ("work", "0006_align_ddl_enums_triggers"),
    ("work", "0007_align_defaults_fks_check"),
})
# Collation của mọi DB do repo tạo: thứ tự ORDER BY theo chuỗi trong query của app và view (ví dụ
# string_agg(... ORDER BY dv.ten)) phụ thuộc collation nên phải cố định.
ICU_LOCALE = "vi-VN"
LIBC_LOCALE = "C.UTF-8"
CREATE_DATABASE = (
    "CREATE DATABASE {} TEMPLATE template0 ENCODING 'UTF8' "
    "LOCALE_PROVIDER icu ICU_LOCALE '" + ICU_LOCALE + "' LOCALE '" + LIBC_LOCALE + "'"
)


def parse_args():
    env = os.environ
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--host", default=env.get("DB_HOST", "localhost"))
    parser.add_argument("--port", default=env.get("DB_PORT", "5432"))
    parser.add_argument("--user", default=env.get("DB_USER", "postgres"))
    parser.add_argument("--dbname", default=env.get("DB_NAME"), required="DB_NAME" not in env)
    parser.add_argument("--ddl", type=Path, default=DEFAULT_DDL)
    parser.add_argument("--seed", action="store_true", help="chạy seed_db sau khi dựng")
    parser.add_argument("--demo-data", action="store_true", help="tạo tài khoản demo; cần --seed và DEMO_PASSWORD")
    existing = parser.add_mutually_exclusive_group()
    existing.add_argument("--force", action="store_true", help="xóa và dựng lại DB đã tồn tại")
    existing.add_argument("--if-empty", action="store_true", help="bỏ qua (exit 0) nếu DB đã có bảng")
    existing.add_argument("--adopt", action="store_true", help="xác minh DB build_db:v2 rồi nâng dấu lên v3")
    existing.add_argument("--sync", action="store_true", help="áp dụng thật migration chưa áp dụng lên DB hiện có")
    parser.add_argument(
        "--preflight-copy", action="store_true", help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--preflight-verified-ddl-sha256", help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--compare-schema-database", help=argparse.SUPPRESS,
    )
    args = parser.parse_args()
    if args.demo_data and not args.seed:
        parser.error("--demo-data cần đi cùng --seed")
    if args.force and not args.seed:
        parser.error("--force cần --seed để bootstrap tài khoản hệ thống")
    if (args.sync or args.adopt) and (args.seed or args.demo_data):
        parser.error("--sync/--adopt không dùng chung với --seed hoặc --demo-data")
    if args.preflight_copy and not args.sync:
        parser.error("--preflight-copy chỉ dùng cùng --sync")
    if args.preflight_verified_ddl_sha256 and not args.sync:
        parser.error("--preflight-verified-ddl-sha256 chỉ dùng cùng --sync")
    if args.preflight_copy and args.preflight_verified_ddl_sha256:
        parser.error("không dùng đồng thời hai cờ preflight")
    if args.preflight_copy and not args.dbname.startswith(("qlvb_migtest_", "build_db_preflight_")):
        parser.error("--preflight-copy chỉ chấp nhận DB scratch có tiền tố qlvb_migtest_ hoặc build_db_preflight_")
    if args.preflight_verified_ddl_sha256 and not re.fullmatch(r"[0-9a-f]{64}", args.preflight_verified_ddl_sha256):
        parser.error("--preflight-verified-ddl-sha256 cần SHA-256 dạng 64 ký tự hex chữ thường")
    return args


def connect(args, dbname, **kwargs):
    return psycopg.connect(
        dbname=dbname, host=args.host, port=args.port, user=args.user,
        password=os.environ.get("DB_PASSWORD", ""), **kwargs,
    )


def ddl_sha256(args):
    return hashlib.sha256(args.ddl.read_bytes()).hexdigest()


def parse_mark(mark):
    parts = (mark or "").split()
    if not parts or parts[0] not in {MARK_PREFIX, LEGACY_MARK_PREFIX}:
        return None
    values = {}
    for part in parts[1:]:
        key, sep, value = part.partition("=")
        if not sep or not key or key in values:
            return None
        values[key] = value
    return {"version": parts[0], **values}


def mark_matches_bootstrap_request(mark, args):
    parsed = parse_mark(mark)
    return bool(
        parsed
        and parsed["version"] == MARK_PREFIX
        and parsed.get("ddl_sha256") == ddl_sha256(args)
        and parsed.get("seed") == str(int(args.seed))
        and parsed.get("collation") == f"icu:{ICU_LOCALE}"
        and set(parsed) == {"version", "ddl_sha256", "seed", "collation", "schema_sha256", "migrations_sha256"}
        and re.fullmatch(r"[0-9a-f]{64}", parsed.get("schema_sha256", ""))
        and re.fullmatch(r"[0-9a-f]{64}", parsed.get("migrations_sha256", ""))
    )


def build_mark(args, schema_sha256, migrations_sha256, *, seed=None, ddl_hash=None):
    seed = args.seed if seed is None else bool(seed)
    ddl_hash = ddl_sha256(args) if ddl_hash is None else ddl_hash
    return (
        f"{MARK_PREFIX} ddl_sha256={ddl_hash} seed={int(seed)} collation=icu:{ICU_LOCALE} "
        f"schema_sha256={schema_sha256} migrations_sha256={migrations_sha256}"
    )


def read_collation(conn, dbname):
    """(provider, icu_locale) của DB; PG16 gọi cột là daticulocale, PG17 đổi thành datlocale."""
    row = conn.execute(
        "SELECT datlocprovider, coalesce(to_jsonb(d)->>'datlocale', to_jsonb(d)->>'daticulocale') "
        "FROM pg_database d WHERE datname = %s",
        [dbname],
    ).fetchone()
    return row if row else None


def require_collation(conn, dbname):
    collation = read_collation(conn, dbname)
    if collation != ("i", ICU_LOCALE):
        raise SystemExit(
            f"DB {dbname} có collation (provider, locale) = {collation}, cần ('i', '{ICU_LOCALE}') "
            f"(ICU {ICU_LOCALE}). Dùng --force để xóa và dựng lại với collation đúng."
        )


def pristine_violations(args):
    """Liệt kê dấu hiệu DB không còn nguyên trạng; danh sách rỗng nghĩa là DB mới tạo, chưa có gì."""
    queries = {
        "schema ngoài public": (
            "SELECT nspname FROM pg_namespace WHERE nspname NOT IN ('public', 'pg_catalog', 'information_schema') "
            "AND nspname NOT LIKE 'pg\\_toast%' AND nspname NOT LIKE 'pg\\_temp%'"
        ),
        "relation trong public": (
            "SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE n.nspname = 'public'"
        ),
        "type trong public": (
            "SELECT t.typname FROM pg_type t JOIN pg_namespace n ON n.oid = t.typnamespace "
            "WHERE n.nspname = 'public' AND t.typtype <> 'c' AND t.typcategory <> 'A'"
        ),
        "function/procedure trong public": (
            "SELECT p.proname FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace "
            "WHERE n.nspname = 'public'"
        ),
        "extension": "SELECT extname FROM pg_extension WHERE extname <> 'plpgsql'",
    }
    found = []
    with connect(args, args.dbname) as conn:
        for label, query in queries.items():
            names = [row[0] for row in conn.execute(query).fetchall()]
            if names:
                found.append(f"{label}: {sorted(names)[:5]}")
    return found


def read_mark(conn, dbname):
    row = conn.execute(
        "SELECT shobj_description(oid, 'pg_database') FROM pg_database WHERE datname = %s", [dbname]
    ).fetchone()
    return row[0] if row else None


def _norm_schema_sql(value):
    if value is None:
        return None
    value = re.sub(r"::[a-z_ ]+(\[\])?", "", value)
    return re.sub(r"\s+", " ", value).strip()


_CHECK_ARRAY = r"ARRAY\[(?:[^\]']|'(?:[^']|'')*')*\]"


def _norm_check_arrays(definition):
    """Đưa ARRAY trong CHECK sau pg_restore (phần tử bọc ngoặc, một lớp ngoặc) về dạng của DB nạp DDL trực tiếp."""
    definition = re.sub(r"(?:(?<=\[)|(?<=, ))\('((?:[^']|'')*)'\)", r"'\1'", definition)
    return re.sub(rf"\b(ANY|ALL) \(\(({_CHECK_ARRAY})\)\)", r"\1 (\2)", definition)


def _norm_schema_check(definition):
    definition = re.sub(r"\(NOT \(TRIM\(BOTH FROM \(?([\w]+)\)?\) = ''\)\)", r"(btrim((\1)) <> '')", definition)
    definition = re.sub(r"btrim\(\(?([\w]+)\)?\) <> ''", r"btrim((\1)) <> ''", definition)
    definition = _norm_check_arrays(definition)
    definition = re.sub(rf"\(NOT \(\((\w+)\)= ANY \(({_CHECK_ARRAY})\)\)\)", r"((\1)<> ALL (\2))", definition)
    definition = re.sub(r"\(NOT \(\(([\w]+)\)= ('[^']*')\)\)", r"((\1)<> \2)", definition)
    return re.sub(r"\(NOT ([\w]+)\)", r"(\1 = false)", definition)


def schema_fingerprint(connection):
    """Hash structural catalog state using the same normalized objects as schema integration checks."""
    with connection.cursor() as cur:
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
                columns[name] = f"{udt}({length or ''}) null={nullable} default={_norm_schema_sql(default)}"
            cur.execute(
                "SELECT contype, pg_get_constraintdef(oid) FROM pg_constraint "
                "WHERE conrelid = %s::regclass AND contype IN ('c', 'f', 'p', 'u', 'x')",
                [f'public."{table}"'],
            )
            constraints = set()
            for kind, definition in cur.fetchall():
                definition = _norm_schema_sql(definition)
                if kind == "c":
                    definition = _norm_schema_check(definition)
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
                indexes.add(_norm_schema_sql(re.sub(r"^CREATE (UNIQUE )?INDEX \S+ ON \S+ ", r"\1", definition)))
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

    def canonical(value):
        if isinstance(value, dict):
            return {key: canonical(value[key]) for key in sorted(value)}
        if isinstance(value, set):
            return sorted((canonical(item) for item in value), key=repr)
        if isinstance(value, tuple):
            return [canonical(item) for item in value]
        return value

    snapshot = canonical((tables, enums, views, functions, triggers))
    encoded = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def migration_fingerprint(applied):
    payload = "\n".join(f"{app}.{name}" for app, name in sorted(applied))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def applied_migrations(connection):
    with connection.cursor() as cursor:
        cursor.execute("SELECT app, name FROM django_migrations")
        return {(app, name) for app, name in cursor.fetchall()}


def create_database(conn, dbname):
    """Tạo DB với collation chuẩn; kiểm tra lại, sai thì xóa chính DB vừa tạo rồi báo lỗi."""
    conn.execute(sql.SQL(CREATE_DATABASE).format(sql.Identifier(dbname)))
    try:
        require_collation(conn, dbname)
    except BaseException:
        conn.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(dbname)))
        raise


def prepare_database(args):
    """Chuẩn bị DB đích. Trả về cách dọn khi lỗi: 'drop', 'reset' hoặc None; None kèm skip=True là bỏ qua."""
    name = sql.Identifier(args.dbname)
    with connect(args, MAINTENANCE_DB, autocommit=True) as conn:
        exists = conn.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", [args.dbname]
        ).fetchone()
        if not exists:
            create_database(conn, args.dbname)
            return "drop", False
        if args.force:
            conn.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(name))
            create_database(conn, args.dbname)
            return "drop", False
        require_collation(conn, args.dbname)
        mark = read_mark(conn, args.dbname)
    violations = pristine_violations(args) if mark is None else ["đã có dấu hoàn tất"]
    if not violations:
        return "reset", False
    if args.if_empty and mark_matches_bootstrap_request(mark, args):
        print(f"DB {args.dbname} có dấu bootstrap v3 phù hợp; kiểm tra schema và lịch sử migration trước khi bỏ qua.")
        return None, True
    if args.if_empty:
        raise SystemExit(
            f"DB {args.dbname} không có marker v3 khớp DDL/seed hiện tại (dấu: {mark!r}); bootstrap bị từ chối, "
            "không có dữ liệu nào bị xóa. DB v2 đã biết cần `--adopt` rồi `--sync`; reset chỉ dùng khi chủ ý "
            "với `--force --seed`."
        )
    raise SystemExit(
        f"DB {args.dbname} đã tồn tại và không ở nguyên trạng mới tạo ({'; '.join(violations)}). "
        "Không rõ nội dung nên không chạm vào. Dùng --force để xóa và dựng lại."
    )


def require_matching_mark(args):
    """Read and structurally validate a v2/v3 marker without changing the target database."""
    with connect(args, MAINTENANCE_DB, autocommit=True) as conn:
        exists = conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", [args.dbname]).fetchone()
        mark = read_mark(conn, args.dbname) if exists else None
        if exists:
            require_collation(conn, args.dbname)
    if not exists:
        raise SystemExit(f"DB {args.dbname} chưa tồn tại. Chạy `pnpm db:setup` trước.")
    parsed = parse_mark(mark)
    if not parsed or parsed.get("seed") not in {"0", "1"} or parsed.get("collation") != f"icu:{ICU_LOCALE}":
        raise SystemExit(f"DB {args.dbname} thiếu dấu build_db v2/v3 hợp lệ; không thay đổi gì.")
    if parsed["version"] == LEGACY_MARK_PREFIX:
        if set(parsed) != {"version", "ddl_sha256", "seed", "collation"}:
            raise SystemExit(f"Marker v2 của DB {args.dbname} có trường không được hỗ trợ; không thay đổi gì.")
        if parsed.get("ddl_sha256") != LEGACY_V2_DDL_SHA256:
            raise SystemExit(
                f"Không thể adopt build_db:v2 với DDL hash {parsed.get('ddl_sha256')!r}; "
                "chỉ hỗ trợ chính xác release v2 đã ghim. DB không bị thay đổi."
            )
    elif set(parsed) != {
        "version", "ddl_sha256", "seed", "collation", "schema_sha256", "migrations_sha256"
    } or not all(
        re.fullmatch(r"[0-9a-f]{64}", parsed.get(key, ""))
        for key in ("ddl_sha256", "schema_sha256", "migrations_sha256")
    ):
        raise SystemExit(f"Dấu build_db:v3 của DB {args.dbname} không hợp lệ; không thay đổi gì.")
    return mark


def cleanup(args, mode):
    """Dọn DB sau khi lỗi. Ném SystemExit nếu không dọn được."""
    if "django" in sys.modules:
        from django.db import connections

        connections.close_all()
    if mode == "drop":
        with connect(args, MAINTENANCE_DB, autocommit=True) as conn:
            conn.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(args.dbname)))
        print(f"Đã xóa DB {args.dbname} do lượt dựng thất bại.", file=sys.stderr)
    elif mode == "reset":
        with connect(args, args.dbname, autocommit=True) as conn:
            conn.execute("DROP SCHEMA public CASCADE")
            conn.execute("CREATE SCHEMA public")
        print(f"Đã trả DB {args.dbname} về trạng thái rỗng do lượt dựng thất bại.", file=sys.stderr)


def load_ddl(args):
    with connect(args, args.dbname) as conn:
        conn.execute(args.ddl.read_text(encoding="utf-8"))
    print(f"Đã nạp {args.ddl.name}.")


def write_mark(args, *, seed=None, ddl_hash=None):
    from django.db import connection

    schema_hash = schema_fingerprint(connection)
    migrations_hash = migration_fingerprint(applied_migrations(connection))
    mark = build_mark(args, schema_hash, migrations_hash, seed=seed, ddl_hash=ddl_hash)
    with connect(args, MAINTENANCE_DB, autocommit=True) as conn:
        conn.execute(
            sql.SQL("COMMENT ON DATABASE {} IS {}").format(
                sql.Identifier(args.dbname), sql.Literal(mark)
            )
        )
    print(f"Đã ghi dấu build_db:v3 cho DB {args.dbname}.")


def validate_legacy_v2(mark):
    from django.db import connection
    from django.db.migrations.loader import MigrationLoader

    parsed = parse_mark(mark)
    if parsed is None or parsed.get("version") != LEGACY_MARK_PREFIX:
        raise SystemExit("Không phải dấu build_db:v2 cần adopt.")
    # Use the current graph without loading applied rows: the supported old release
    # predates the work/records migration modules, so its exact history is intentionally
    # checked against the historical set pinned above rather than current dependency closure.
    loader = MigrationLoader(None, ignore_no_migrations=True)
    for app, name in LEGACY_V2_MIGRATIONS | LEGACY_V2_BASELINE_MIGRATIONS:
        if (app, name) not in loader.graph:
            raise SystemExit(f"Không thể adopt v2: thiếu migration gốc đã hỗ trợ {app}.{name}.")
    actual_migrations = applied_migrations(connection)
    supported_history_states = {
        LEGACY_V2_MIGRATIONS,
        LEGACY_V2_MIGRATIONS | LEGACY_V2_BASELINE_MIGRATIONS,
    }
    if frozenset(actual_migrations) not in supported_history_states:
        expected_migrations = LEGACY_V2_MIGRATIONS
        missing = sorted(expected_migrations - actual_migrations)
        extra = sorted(actual_migrations - (expected_migrations | LEGACY_V2_BASELINE_MIGRATIONS))
        raise SystemExit(
            "Không thể adopt build_db:v2: lịch sử migration không khớp release được hỗ trợ "
            f"(thiếu={missing[:8]}, thừa={extra[:8]}). DB không bị thay đổi."
        )
    for app, name in LEGACY_V2_MIGRATIONS | LEGACY_V2_BASELINE_MIGRATIONS:
        node = loader.graph.node_map[(app, name)]
        for parent in node.parents:
            if parent.key not in actual_migrations | LEGACY_V2_BASELINE_MIGRATIONS:
                raise SystemExit(
                    "Không thể adopt build_db:v2: dependency migration hiện tại không có trong "
                    f"lịch sử release đã hỗ trợ ({app}.{name} cần {parent.key[0]}.{parent.key[1]}). "
                    "DB không bị thay đổi."
                )
    actual_schema = schema_fingerprint(connection)
    if actual_schema != LEGACY_V2_SCHEMA_SHA256:
        raise SystemExit(
            "Không thể adopt build_db:v2: schema thực tế không khớp fingerprint release đã hỗ trợ. "
            "DB không bị thay đổi. Cần xác định và sửa drift bằng quy trình nâng cấp có migration."
        )
    return parsed, actual_migrations


def validate_v3_mark(mark):
    from django.db import connection

    parsed = parse_mark(mark)
    if parsed is None or parsed.get("version") != MARK_PREFIX:
        raise SystemExit("--sync cần dấu build_db:v3; chạy `pnpm db:adopt` nếu DB đang ở v2.")
    actual_schema = schema_fingerprint(connection)
    actual_migrations = migration_fingerprint(applied_migrations(connection))
    if actual_schema != parsed.get("schema_sha256"):
        raise SystemExit(
            "Schema thực tế khác fingerprint đã ghi trong dấu build_db:v3. "
            "DB không bị thay đổi; cần xử lý drift trước khi nâng cấp."
        )
    if actual_migrations != parsed.get("migrations_sha256"):
        raise SystemExit(
            "Lịch sử django_migrations khác fingerprint đã ghi trong dấu build_db:v3. "
            "DB không bị thay đổi; cần xác minh migration history trước khi nâng cấp."
        )
    return parsed


def adopt_database(args):
    mark = require_matching_mark(args)
    setup_django(args)
    from django.db import connection

    parsed = parse_mark(mark)
    if parsed["version"] == MARK_PREFIX:
        validate_v3_mark(mark)
        print(f"DB {args.dbname} đã được adopt và vượt qua schema/history preflight.")
        return
    parsed, actual_migrations = validate_legacy_v2(mark)
    if actual_migrations == LEGACY_V2_MIGRATIONS:
        from django.db import transaction
        from django.db.migrations.recorder import MigrationRecorder

        # Record only the nine schema operations already present in the exact release
        # DDL. The raw catalog fingerprint above proves those tables, functions, triggers,
        # indexes and constraints exist; data migrations remain pending for real execution.
        recorder = MigrationRecorder(connection)
        with transaction.atomic():
            for app, name in sorted(LEGACY_V2_BASELINE_MIGRATIONS):
                recorder.record_applied(app, name)
    # The v2 DDL hash stays in the v3 marker until --sync executes all remaining migrations.
    # This also makes an interrupted adoption retryable: both pre-stamp and post-stamp
    # history states are accepted above, while any partial or unrelated history is rejected.
    from django.db.migrations.executor import MigrationExecutor

    MigrationExecutor(connection)
    write_mark(args, seed=parsed["seed"] == "1", ddl_hash=parsed["ddl_sha256"])
    print(
        f"DB {args.dbname} đã được adopt sau khi xác minh schema và lịch sử migration; "
        f"đã ghi nhận {len(LEGACY_V2_BASELINE_MIGRATIONS)} migration baseline đã có trong DDL."
    )


def builder_command(args, dbname, *flags):
    return [
        sys.executable,
        str(Path(__file__).resolve()),
        "--host", str(args.host),
        "--port", str(args.port),
        "--user", str(args.user),
        "--dbname", dbname,
        "--ddl", str(args.ddl),
        *flags,
    ]


def run_builder_copy(args, dbname, *flags):
    result = subprocess.run(
        builder_command(args, dbname, *flags),
        cwd=ROOT,
        env={**os.environ, "PYTHONUTF8": "1"},
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode:
        details = "\n".join(part.strip() for part in (result.stdout, result.stderr) if part.strip())
        raise SystemExit(
            "Preflight trên bản sao thất bại; DB đích chưa bị thay đổi. "
            f"Lệnh build_db.py {flags!r} trả mã {result.returncode}.\n{details}"
        )
    return result.stdout


def compare_database_schema(args):
    """Compare a copied upgrade against the release DDL using the checked-in schema baseline."""
    import importlib.util

    comparator_path = ROOT / ".github" / "scripts" / "compare_schema_ddl.py"
    spec = importlib.util.spec_from_file_location("qlvb_compare_schema_ddl", comparator_path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"Không tải được schema comparator: {comparator_path}")
    comparator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(comparator)
    # The comparator's CLI reads POSTGRES_*; use this builder invocation's connection
    # settings so local, CI, and deployment preflight share one target.
    comparator.connect = lambda dbname: connect(args, dbname)
    differences = comparator.drift(args.dbname, args.compare_schema_database, include_data=False)
    baseline_path = ROOT / "docs" / "common" / "database" / "schema_drift_baseline.txt"
    baseline = {
        line.rstrip("\n")
        for line in baseline_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith(("#", "SEED "))
    }
    new = sorted(set(differences) - baseline)
    fixed = sorted(baseline - set(differences))
    if new:
        raise SystemExit(
            "Preflight schema khác release DDL/baseline; DB đích chưa bị thay đổi. "
            f"Lệch mới={new[:20]}."
        )
    print(
        "Preflight schema đạt theo baseline: "
        f"{args.dbname} so với {args.compare_schema_database}; "
        f"{len(differences)} lệch schema thuộc baseline, "
        f"{len(fixed)} lệch baseline đã được khắc phục, không có lệch mới."
    )


def preflight_sync_on_copy(args, current_mark, current_ddl_hash):
    """Run pending migrations against a template copy, then compare its catalog to a clean release build."""
    from django.db import connections

    suffix = uuid.uuid4().hex[:12]
    copy_db = f"build_db_preflight_copy_{suffix}"
    expected_db = f"build_db_preflight_expected_{suffix}"
    created = []
    connections.close_all()
    try:
        with connect(args, MAINTENANCE_DB, autocommit=True) as conn:
            conn.execute(
                sql.SQL("CREATE DATABASE {} WITH TEMPLATE {}").format(
                    sql.Identifier(copy_db), sql.Identifier(args.dbname)
                )
            )
            created.append(copy_db)
            conn.execute(
                sql.SQL("COMMENT ON DATABASE {} IS {}").format(
                    sql.Identifier(copy_db), sql.Literal(current_mark)
                )
            )
            create_database(conn, expected_db)
            created.append(expected_db)

        # The copy contains the target's real rows. Migration operations (including
        # RunPython/RunSQL) execute there before any corresponding change is made live.
        run_builder_copy(args, copy_db, "--sync", "--preflight-copy")
        # Load raw release DDL as the schema reference. The comparator applies the
        # checked-in schema baseline and excludes user rows; the preceding copy migration
        # has already executed data operations against the target's actual rows.
        expected_args = argparse.Namespace(**vars(args))
        expected_args.dbname = expected_db
        load_ddl(expected_args)
        compare_args = argparse.Namespace(**vars(args))
        compare_args.dbname = copy_db
        compare_args.compare_schema_database = expected_db
        compare_database_schema(compare_args)
        print(f"Preflight trên bản sao đạt cho DDL sha256={current_ddl_hash}.")
    except psycopg.Error as exc:
        raise SystemExit(
            "Không tạo hoặc xác minh được DB sao chép cho preflight; DB đích chưa bị thay đổi. "
            "Cần quyền CREATEDB/quyền sở hữu DB và không còn kết nối khác giữ DB nguồn đang mở. "
            f"Lỗi: {exc!r}"
        ) from exc
    finally:
        connections.close_all()
        cleanup_error = None
        if created:
            try:
                with connect(args, MAINTENANCE_DB, autocommit=True) as conn:
                    for dbname in reversed(created):
                        conn.execute(
                            sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(
                                sql.Identifier(dbname)
                            )
                        )
            except Exception as exc:  # cleanup must not be mistaken for a passed preflight
                cleanup_error = exc
        if cleanup_error:
            raise SystemExit(
                "Preflight chưa được xem là đạt vì DB tạm không thể dọn; DB đích chưa bị thay đổi. "
                f"DB tạm: {created}; lỗi dọn: {cleanup_error!r}"
            ) from cleanup_error


def sync_database(args):
    from django.core.management import call_command
    from django.db import connection
    from django.db.migrations.executor import MigrationExecutor

    mark = require_matching_mark(args)
    setup_django(args)
    parsed = validate_v3_mark(mark)
    executor = MigrationExecutor(connection)
    leaves = sorted(executor.loader.graph.leaf_nodes())
    pending = executor.migration_plan(leaves)
    current_ddl_hash = ddl_sha256(args)
    if parsed["ddl_sha256"] != current_ddl_hash and not pending:
        raise SystemExit(
            "release_DDL.sql đổi nhưng không có migration chờ. Không thể chứng minh đường nâng cấp; "
            "DB không bị thay đổi. Thêm migration tương ứng hoặc xác minh drift trước khi deploy."
        )
    if pending:
        verified_hash = args.preflight_verified_ddl_sha256
        if verified_hash and verified_hash != current_ddl_hash:
            raise SystemExit(
                "Hash DDL đã preflight không khớp release_DDL.sql hiện tại; DB không bị thay đổi."
            )
        if not args.preflight_copy and not verified_hash:
            preflight_sync_on_copy(args, mark, current_ddl_hash)
            # Reject schema/history changes made after the disposable copy was created.
            validate_v3_mark(mark)
        names = [f"{migration.app_label}.{migration.name}" for migration, _ in pending]
        print(f"Áp dụng migration thật: {names}")
        try:
            # Deliberately no fake/fake-initial: pending RunPython and RunSQL must execute.
            call_command("migrate", interactive=False, verbosity=1)
        except Exception as exc:
            raise SystemExit(
                f"Migration thất bại; DB không được reset. Backup cần giữ nguyên để phục hồi: {exc!r}"
            ) from exc
    else:
        print("Không còn migration chưa áp dụng.")
    remaining = MigrationExecutor(connection).migration_plan(
        MigrationExecutor(connection).loader.graph.leaf_nodes()
    )
    if remaining:
        raise SystemExit(f"Còn migration chưa áp dụng: {[f'{m.app_label}.{m.name}' for m, _ in remaining]}")
    if pending:
        write_mark(args, seed=parsed["seed"] == "1", ddl_hash=current_ddl_hash)
    else:
        print("DB đã đồng bộ; marker không cần cập nhật.")


def setup_django(args):
    os.environ.update({
        "DB_ENGINE": "postgresql", "DB_HOST": args.host, "DB_PORT": str(args.port),
        "DB_USER": args.user, "DB_NAME": args.dbname,
    })
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    sys.path.insert(0, str(BACKEND))
    os.chdir(BACKEND)
    import django

    django.setup()


def app_tables(state):
    """Bảng vật lý của từng app theo trạng thái migration cuối cùng."""
    tables = {}
    for model in state.apps.get_models(include_auto_created=True):
        meta = model._meta
        if meta.managed and not meta.proxy and not meta.swapped:
            tables.setdefault(meta.app_label, set()).add(meta.db_table)
    return tables


def decide_fake(app_labels, tables_by_app, existing, hint):
    fake = {}
    for app in sorted(app_labels):
        tables = tables_by_app.get(app, set())
        present = tables & existing
        if tables and present == tables:
            fake[app] = True
        elif not present:
            fake[app] = False
        else:
            raise SystemExit(
                f"App '{app}' có một phần bảng trong DB: có {sorted(present)}, "
                f"thiếu {sorted(tables - present)}. Không thể fake một phần. {hint}"
            )
    return fake


def adopt_migrations():
    from django.core.management import call_command
    from django.db import connection
    from django.db.migrations.executor import MigrationExecutor

    executor = MigrationExecutor(connection)
    loader = executor.loader
    leaves = sorted(loader.graph.leaf_nodes())
    order = []
    for leaf in leaves:
        order.extend(n for n in loader.graph.forwards_plan(leaf) if n not in order)

    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
        )
        existing = {row[0] for row in cursor.fetchall()}
    apps_in_order = {app for app, _ in order}
    state = loader.project_state(leaves)
    fake = decide_fake(
        apps_in_order,
        app_tables(state),
        existing,
        "release_DDL.sql chưa có đủ bảng; cần sửa baseline trước khi bootstrap.",
    )
    for app, is_fake in fake.items():
        print(f"  {app}: {'fake (bảng đã có trong DB)' if is_fake else 'migrate thật'}")

    done = []
    try:
        for app, name in order:
            executor.loader.build_graph()
            # The complete release DDL is the bootstrap schema/data baseline. This is not
            # the upgrade path: sync_database() applies every pending migration without fake.
            executor.migrate([(app, name)], fake=fake[app])
            done.append(f"{app}.{name}")
    except BaseException as exc:
        raise SystemExit(
            f"Migration lỗi sau khi đã ghi nhận {done or 'không migration nào'}; DB không được dọn: {exc!r}"
        ) from exc

    # Chạy migrate rỗng để phát tín hiệu post_migrate một lần (contenttypes, v.v.) và xác nhận kết quả.
    call_command("migrate", interactive=False, verbosity=0)
    pending = MigrationExecutor(connection).migration_plan(
        MigrationExecutor(connection).loader.graph.leaf_nodes()
    )
    if pending:
        raise SystemExit(f"Còn migration chưa áp dụng: {[f'{m.app_label}.{m.name}' for m, _ in pending]}")
    print("Không còn migration chưa áp dụng.")


def build(args):
    load_ddl(args)
    setup_django(args)
    adopt_migrations()
    if args.seed:
        from django.core.management import call_command

        call_command("seed_db", demo_data=args.demo_data)
    write_mark(args)
    print(f"Đã dựng DB {args.dbname}.")


def require_seed_secrets(args):
    if args.seed and not os.environ.get("ADMIN_PASSWORD", "").strip():
        raise SystemExit("Thiếu ADMIN_PASSWORD; chưa thay đổi database.")
    if args.demo_data and not os.environ.get("DEMO_PASSWORD", "").strip():
        raise SystemExit("Thiếu DEMO_PASSWORD cho --demo-data; chưa thay đổi database.")


def main():
    args = parse_args()
    if args.compare_schema_database:
        compare_database_schema(args)
        return
    if args.sync:
        if not args.ddl.is_file():
            raise SystemExit(f"Không thấy file DDL: {args.ddl}")
        sync_database(args)
        return
    if args.adopt:
        adopt_database(args)
        return
    if not args.ddl.is_file():
        raise SystemExit(f"Không thấy file DDL: {args.ddl}")
    require_seed_secrets(args)
    mode, skip = prepare_database(args)
    if skip:
        mark = require_matching_mark(args)
        setup_django(args)
        validate_v3_mark(mark)
        print(f"DB {args.dbname} đã dựng hoàn tất với DDL và yêu cầu seed hiện tại; bỏ qua.")
        return
    try:
        build(args)
    except BaseException as exc:
        try:
            cleanup(args, mode)
        except Exception as cleanup_exc:
            raise SystemExit(
                f"Dựng DB {args.dbname} thất bại: {exc!r}. Dọn DB cũng thất bại: {cleanup_exc!r}. "
                f"DB {args.dbname} có thể còn sót, cần xử lý thủ công."
            ) from exc
        raise


if __name__ == "__main__":
    main()
