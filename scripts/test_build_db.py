"""Test collation của scripts/build_db.py: DB tạo mới và --force phải là ICU vi-VN, DB có collation khác bị từ chối.

Dùng: python -m unittest discover -s scripts -p "test_build_db.py"
Kết nối lấy từ DB_HOST, DB_PORT, DB_USER, DB_PASSWORD (cần quyền CREATEDB).
"""
import gzip
import hashlib
import os
import subprocess
import sys
import shutil
import tempfile
import unittest
import uuid
from argparse import Namespace
from pathlib import Path
from unittest import mock

from psycopg import sql

import build_db


class CollationTest(unittest.TestCase):
    def setUp(self):
        self.args = Namespace(
            host=os.environ.get("DB_HOST", "localhost"), port=os.environ.get("DB_PORT", "5432"),
            user=os.environ.get("DB_USER", "postgres"), dbname="build_db_test_" + uuid.uuid4().hex[:10],
            force=False, if_empty=False,
        )

    def tearDown(self):
        with build_db.connect(self.args, "postgres", autocommit=True) as conn:
            conn.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(self.args.dbname)))

    def collation(self):
        with build_db.connect(self.args, "postgres", autocommit=True) as conn:
            return build_db.read_collation(conn, self.args.dbname)

    def create_with_icu_locale(self, icu_locale):
        with build_db.connect(self.args, "postgres", autocommit=True) as conn:
            conn.execute(
                sql.SQL(
                    "CREATE DATABASE {} TEMPLATE template0 ENCODING 'UTF8' "
                    "LOCALE_PROVIDER icu ICU_LOCALE {} LOCALE 'C.UTF-8'"
                ).format(sql.Identifier(self.args.dbname), sql.Literal(icu_locale))
            )

    def test_new_database_is_icu_vi_vn(self):
        self.assertEqual(build_db.prepare_database(self.args), ("drop", False))
        self.assertEqual(self.collation(), ("i", "vi-VN"))

    def test_force_recreates_with_icu_vi_vn(self):
        self.create_with_icu_locale("en-US")
        self.args.force = True
        self.assertEqual(build_db.prepare_database(self.args), ("drop", False))
        self.assertEqual(self.collation(), ("i", "vi-VN"))

    def exists(self):
        with build_db.connect(self.args, "postgres", autocommit=True) as conn:
            return conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", [self.args.dbname]).fetchone()

    def wrong_collation_create_sql(self):
        return mock.patch.object(build_db, "CREATE_DATABASE", build_db.CREATE_DATABASE.replace("vi-VN", "en-US"))

    def test_new_database_with_failed_collation_check_is_dropped(self):
        with self.wrong_collation_create_sql(), self.assertRaises(SystemExit):
            build_db.prepare_database(self.args)
        self.assertIsNone(self.exists())

    def test_force_database_with_failed_collation_check_is_dropped(self):
        self.create_with_icu_locale("vi-VN")
        self.args.force = True
        with self.wrong_collation_create_sql(), self.assertRaises(SystemExit):
            build_db.prepare_database(self.args)
        self.assertIsNone(self.exists())

    def test_existing_database_with_other_collation_is_rejected(self):
        self.create_with_icu_locale("en-US")
        with self.assertRaises(SystemExit) as raised:
            build_db.prepare_database(self.args)
        self.assertIn("--force", str(raised.exception))
        self.assertEqual(self.collation(), ("i", "en-US"))

    def test_sync_rejects_other_collation(self):
        self.create_with_icu_locale("en-US")
        with self.assertRaises(SystemExit) as raised:
            build_db.require_matching_mark(self.args)
        self.assertIn("collation", str(raised.exception))


class CheckNormalizationTest(unittest.TestCase):
    DIRECT_IN = (
        "CHECK (((pham_vi)::text = ANY ((ARRAY['NOI_BO'::character varying, 'HAN_CHE'::character varying])::text[])))"
    )
    RESTORED_IN = (
        "CHECK (((pham_vi)::text = ANY (ARRAY[('NOI_BO'::character varying)::text, "
        "('HAN_CHE'::character varying)::text])))"
    )
    DIRECT_NOT_IN = (
        "CHECK ((((hanh_dong)::text <> ALL ((ARRAY['A'::character varying, 'B'::character varying])::text[])) "
        "OR (u IS NOT NULL)))"
    )
    RESTORED_NOT_IN = (
        "CHECK (((NOT ((hanh_dong)::text = ANY (ARRAY[('A'::character varying)::text, "
        "('B'::character varying)::text]))) OR (u IS NOT NULL)))"
    )

    def norm(self, definition):
        return build_db._norm_schema_check(build_db._norm_schema_sql(definition))

    def test_restored_and_direct_forms_are_equal(self):
        self.assertEqual(self.norm(self.DIRECT_IN), self.norm(self.RESTORED_IN))
        self.assertEqual(self.norm(self.DIRECT_NOT_IN), self.norm(self.RESTORED_NOT_IN))

    def test_different_values_or_operators_stay_different(self):
        self.assertNotEqual(self.norm(self.RESTORED_IN), self.norm(self.RESTORED_IN.replace("HAN_CHE", "KHAC")))
        self.assertNotEqual(self.norm(self.RESTORED_IN), self.norm(self.RESTORED_IN.replace("NOI_BO", "")))
        self.assertNotEqual(self.norm(self.DIRECT_IN), self.norm(self.RESTORED_IN.replace("HAN_CHE", "KHAC")))
        self.assertNotEqual(self.norm(self.DIRECT_NOT_IN), self.norm(self.RESTORED_NOT_IN.replace("'B'", "'C'")))
        # = ANY và <> ALL cùng danh sách là hai điều kiện khác nhau.
        self.assertNotEqual(self.norm(self.DIRECT_IN), self.norm(self.DIRECT_IN.replace("= ANY", "<> ALL")))
        self.assertNotEqual(self.norm(self.DIRECT_NOT_IN), self.norm(self.DIRECT_NOT_IN.replace("<> ALL", "= ANY")))
        # NOT (x = ANY ...) khác x = ANY ...
        self.assertNotEqual(self.norm(self.RESTORED_NOT_IN), self.norm(self.RESTORED_NOT_IN.replace("NOT ", "")))


class DatabaseLifecycleTest(unittest.TestCase):
    def setUp(self):
        self.args = Namespace(
            host=os.environ.get("DB_HOST", "localhost"), port=os.environ.get("DB_PORT", "5432"),
            user=os.environ.get("DB_USER", "postgres"), dbname="build_db_lifecycle_" + uuid.uuid4().hex[:10],
            force=False, if_empty=True, seed=True, demo_data=False, ddl=build_db.DEFAULT_DDL,
        )
        self.root = Path(__file__).resolve().parents[1]
        self.base_env = os.environ.copy()
        self.base_env.update({
            "PYTHONUTF8": "1",
            "DB_ENGINE": "postgresql",
            "DB_HOST": self.args.host,
            "DB_PORT": str(self.args.port),
            "DB_USER": self.args.user,
            "DJANGO_SECRET_KEY": self.base_env.get("DJANGO_SECRET_KEY", "issue168-test-secret-key-at-least-32-characters"),
            "ADMIN_PASSWORD": "issue168-bootstrap-password",
        })
        self.base_env.setdefault("DB_PASSWORD", os.environ.get("DB_PASSWORD", ""))

    def tearDown(self):
        with build_db.connect(self.args, "postgres", autocommit=True) as conn:
            for dbname in [self.args.dbname, *getattr(self, "extra_dbs", [])]:
                conn.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(dbname)))

    def run_builder(self, *args, env=None, expect_success=True):
        run_env = self.base_env.copy()
        if env:
            run_env.update(env)
        command = [sys.executable, str(self.root / "scripts" / "build_db.py"), "--dbname", self.args.dbname, *args]
        result = subprocess.run(command, cwd=self.root, env=run_env, capture_output=True, text=True, encoding="utf-8")
        if expect_success and result.returncode != 0:
            self.fail(f"build_db thất bại ({result.returncode}):\n{result.stdout}\n{result.stderr}")
        if not expect_success and result.returncode == 0:
            self.fail(f"build_db bất ngờ thành công:\n{result.stdout}\n{result.stderr}")
        return result

    def run_manage(self, *args, expect_success=True):
        result = subprocess.run(
            [sys.executable, str(self.root / "backend" / "manage.py"), *args],
            cwd=self.root / "backend",
            env={**self.base_env, "DB_NAME": self.args.dbname},
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if expect_success and result.returncode != 0:
            self.fail(f"manage.py thất bại ({result.returncode}):\n{result.stdout}\n{result.stderr}")
        if not expect_success and result.returncode == 0:
            self.fail(f"manage.py bất ngờ thành công:\n{result.stdout}\n{result.stderr}")
        return result

    def run_seed(self, *args, env=None, expect_success=True):
        run_env = self.base_env.copy()
        if env:
            run_env.update(env)
        command = [sys.executable, str(self.root / "backend" / "manage.py"), "seed_db", *args]
        result = subprocess.run(
            command, cwd=self.root / "backend", env={**run_env, "DB_NAME": self.args.dbname},
            capture_output=True, text=True, encoding="utf-8",
        )
        if expect_success and result.returncode != 0:
            self.fail(f"seed_db thất bại ({result.returncode}):\n{result.stdout}\n{result.stderr}")
        if not expect_success and result.returncode == 0:
            self.fail(f"seed_db bất ngờ thành công:\n{result.stdout}\n{result.stderr}")
        return result

    def create_bootstrap_db(self):
        self.run_builder("--if-empty", "--seed")

    def forget_migration_history_and_descendants(self, app, name):
        script = "\n".join([
            "from django.db import connection",
            "from django.db.migrations.loader import MigrationLoader",
            f"root = ({app!r}, {name!r})",
            "loader = MigrationLoader(None)",
            "keys = {root}",
            "pending = list(loader.graph.node_map[root].children)",
            "while pending:",
            "    node = pending.pop()",
            "    if node.key in keys:",
            "        continue",
            "    keys.add(node.key)",
            "    pending.extend(node.children)",
            "with connection.cursor() as cursor:",
            "    for app_label, migration_name in sorted(keys):",
            "        cursor.execute(",
            "            'DELETE FROM django_migrations WHERE app = %s AND name = %s',",
            "            [app_label, migration_name],",
            "        )",
            "print('rewound migration history:', ','.join(f'{a}.{n}' for a, n in sorted(keys)))",
        ])
        self.run_manage("shell", "-c", script)

    def create_supported_v2_fixture(self):
        ddl_fixture = self.root / "scripts" / "fixtures" / "build_db_v2_22fa331_release_DDL.sql.gz"
        legacy_ddl_bytes = gzip.decompress(ddl_fixture.read_bytes())
        self.assertEqual(hashlib.sha256(legacy_ddl_bytes).hexdigest(), build_db.LEGACY_V2_DDL_SHA256)
        legacy_ddl = legacy_ddl_bytes.decode("utf-8")
        with build_db.connect(self.args, "postgres", autocommit=True) as conn:
            conn.execute(
                sql.SQL(
                    "CREATE DATABASE {} TEMPLATE template0 ENCODING 'UTF8' "
                    "LOCALE_PROVIDER icu ICU_LOCALE 'vi-VN' LOCALE 'C.UTF-8'"
                ).format(sql.Identifier(self.args.dbname))
            )
        with build_db.connect(self.args, self.args.dbname) as conn:
            conn.execute(legacy_ddl, prepare=False)
        # Reproduce 22fa331's per-app fake-or-run behavior using its pinned migration
        # set. Several framework/dashboard tables are migration-created, not in raw DDL.
        historical_bootstrap = "\n".join([
            "import sys",
            "sys.path.insert(0, '../scripts')",
            "import build_db",
            "from django.db import connection",
            "from django.db.migrations.executor import MigrationExecutor",
            "executor = MigrationExecutor(connection)",
            "loader = executor.loader",
            "legacy = set(build_db.LEGACY_V2_MIGRATIONS)",
            "leaves = [key for key in legacy if not any(child.key in legacy for child in loader.graph.node_map[key].children)]",
            "order = []",
            "for leaf in sorted(leaves):",
            "    for node in loader.graph.forwards_plan(leaf):",
            "        if node in legacy and node not in order:",
            "            order.append(node)",
            "state = loader.project_state(leaves)",
            "tables = {}",
            "for model in state.apps.get_models(include_auto_created=True):",
            "    meta = model._meta",
            "    if meta.managed and not meta.proxy and not meta.swapped:",
            "        tables.setdefault(meta.app_label, set()).add(meta.db_table)",
            "with connection.cursor() as cursor:",
            "    cursor.execute(\"SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE'\")",
            "    existing = {row[0] for row in cursor.fetchall()}",
            "fake = {}",
            "for app in {app for app, _ in order}:",
            "    expected = tables.get(app, set())",
            "    present = expected & existing",
            "    if expected and present and present != expected:",
            "        raise RuntimeError(f'partial historical DDL tables for {app}: {present} / {expected}')",
            "    fake[app] = bool(expected) and present == expected",
            "for app, name in order:",
            "    executor.loader.build_graph()",
            "    executor.migrate([(app, name)], fake=fake[app])",
        ])
        self.run_manage("shell", "-c", historical_bootstrap)
        # Seed synthetic test rows with current code so no old credentials or user
        # records enter the fixture.
        self.run_seed()
        with build_db.connect(self.args, self.args.dbname, autocommit=True) as conn:
            conn.execute(
                "UPDATE public.accounts_employee SET password = %s, is_active = FALSE, is_staff = FALSE, "
                "is_superuser = TRUE WHERE username = 'admin'",
                ["pbkdf2_sha256$system_seed_placeholder"],
            )
            conn.execute("UPDATE public.records_hoso SET ghi_chu = 'issue168-preserved-data' WHERE so_ky_hieu = 'HSC'")
        with build_db.connect(self.args, "postgres", autocommit=True) as conn:
            conn.execute(
                sql.SQL("COMMENT ON DATABASE {} IS {}").format(
                    sql.Identifier(self.args.dbname),
                    sql.Literal(
                        f"build_db:v2 ddl_sha256={build_db.LEGACY_V2_DDL_SHA256} "
                        "seed=1 collation=icu:vi-VN"
                    ),
                )
            )

    def marker(self):
        with build_db.connect(self.args, "postgres", autocommit=True) as conn:
            return build_db.read_mark(conn, self.args.dbname)

    def test_v2_adopt_runs_pending_runpython_and_upgrade_preserves_existing_data(self):
        self.create_supported_v2_fixture()
        with build_db.connect(self.args, self.args.dbname) as conn:
            self.assertEqual(build_db.schema_fingerprint(conn), build_db.LEGACY_V2_SCHEMA_SHA256)
            self.assertEqual(build_db.applied_migrations(conn), build_db.LEGACY_V2_MIGRATIONS)

        self.run_builder("--adopt")
        adopted = build_db.parse_mark(self.marker())
        self.assertEqual(adopted["version"], "build_db:v3")
        self.assertEqual(adopted["ddl_sha256"], build_db.LEGACY_V2_DDL_SHA256)
        with build_db.connect(self.args, self.args.dbname) as conn:
            self.assertEqual(
                build_db.applied_migrations(conn),
                build_db.LEGACY_V2_MIGRATIONS | build_db.LEGACY_V2_BASELINE_MIGRATIONS,
            )

        migration = self.run_builder("--sync")
        self.assertIn("0007_normalize_system_account_password", migration.stdout)
        self.assertIn("0003_reference_data_ddl", migration.stdout)
        with build_db.connect(self.args, self.args.dbname) as conn:
            admin_password = conn.execute(
                "SELECT password, is_active, is_staff, is_superuser FROM accounts_employee WHERE username = 'admin'"
            ).fetchone()
            hsc_note = conn.execute(
                "SELECT ghi_chu FROM records_hoso WHERE so_ky_hieu = 'HSC'"
            ).fetchone()[0]
        self.assertEqual(admin_password, ("!system_seed_placeholder", False, False, True))
        self.assertEqual(hsc_note, "issue168-preserved-data")

        # A subsequent code-only sync and seed rerun preserve account hash, flags and data.
        with build_db.connect(self.args, self.args.dbname, autocommit=True) as conn:
            conn.execute(
                "UPDATE accounts_employee SET password = %s, is_active = FALSE, is_staff = FALSE, "
                "is_superuser = TRUE WHERE username = 'admin'",
                ["$pbkdf2_sha256$stored-existing-hash"],
            )
            conn.execute("UPDATE accounts_position SET display_order = 77 WHERE name = 'Quản trị viên'")
        seed_result = self.run_seed(env={"ADMIN_PASSWORD": "different-bootstrap-password"})
        self.assertNotIn("different-bootstrap-password", seed_result.stdout + seed_result.stderr)
        before = self.marker()
        self.run_builder("--sync")
        after = self.marker()
        with build_db.connect(self.args, self.args.dbname) as conn:
            account = conn.execute(
                "SELECT password, is_active, is_staff, is_superuser FROM accounts_employee WHERE username = 'admin'"
            ).fetchone()
            hsc_note = conn.execute(
                "SELECT ghi_chu FROM records_hoso WHERE so_ky_hieu = 'HSC'"
            ).fetchone()[0]
            demo_count = conn.execute(
                "SELECT count(*) FROM accounts_employee WHERE username IN "
                "('truongphong_cntt', 'chuyenvien_cntt', 'vanthu_cntt')"
            ).fetchone()[0]
            admin_position_order = conn.execute(
                "SELECT display_order FROM accounts_position WHERE name = 'Quản trị viên'"
            ).fetchone()[0]
        self.assertEqual(account, ("$pbkdf2_sha256$stored-existing-hash", False, False, True))
        self.assertEqual(hsc_note, "issue168-preserved-data")
        self.assertEqual(demo_count, 0)
        self.assertEqual(admin_position_order, 77)
        self.assertEqual(before, after)

    def test_v2_schema_or_history_drift_fails_before_marker_or_data_changes(self):
        self.create_supported_v2_fixture()
        with build_db.connect(self.args, self.args.dbname, autocommit=True) as conn:
            conn.execute(
                "DELETE FROM django_migrations WHERE app = 'documents' "
                "AND name = '0005_alter_vanbandendanhmuc_unique_together_and_more'"
            )
        result = self.run_builder("--adopt", expect_success=False)
        self.assertIn("lịch sử migration không khớp", result.stderr)
        self.assertEqual(self.marker().split()[0], "build_db:v2")

        with build_db.connect(self.args, self.args.dbname, autocommit=True) as conn:
            conn.execute(
                "INSERT INTO django_migrations (app, name, applied) VALUES "
                "('documents', '0005_alter_vanbandendanhmuc_unique_together_and_more', now())"
            )
            conn.execute("ALTER TABLE records_hoso ADD COLUMN issue168_unexpected_column text")
        result = self.run_builder("--adopt", expect_success=False)
        self.assertIn("schema thực tế không khớp fingerprint", result.stderr)
        self.assertEqual(self.marker().split()[0], "build_db:v2")
        with build_db.connect(self.args, self.args.dbname) as conn:
            password = conn.execute(
                "SELECT password FROM accounts_employee WHERE username = 'admin'"
            ).fetchone()[0]
            probe_column = conn.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_name = 'records_hoso' "
                "AND column_name = 'issue168_unexpected_column'"
            ).fetchone()
        self.assertEqual(password, "pbkdf2_sha256$system_seed_placeholder")
        self.assertIsNotNone(probe_column)

    def test_reset_requires_admin_secret_before_drop_and_only_force_rebuilds(self):
        self.create_bootstrap_db()
        with build_db.connect(self.args, self.args.dbname, autocommit=True) as conn:
            conn.execute("UPDATE records_hoso SET ghi_chu = 'issue168-reset-probe' WHERE so_ky_hieu = 'HSC'")
        result = self.run_builder("--force", "--seed", env={"ADMIN_PASSWORD": ""}, expect_success=False)
        self.assertIn("Thiếu ADMIN_PASSWORD", result.stderr)
        with build_db.connect(self.args, self.args.dbname) as conn:
            note = conn.execute("SELECT ghi_chu FROM records_hoso WHERE so_ky_hieu = 'HSC'").fetchone()[0]
        self.assertEqual(note, "issue168-reset-probe")

        self.run_builder("--force", "--seed")
        mark = build_db.parse_mark(self.marker())
        self.assertEqual(mark["version"], "build_db:v3")
        self.assertEqual(mark["ddl_sha256"], build_db.ddl_sha256(self.args))
        with build_db.connect(self.args, self.args.dbname) as conn:
            note = conn.execute("SELECT ghi_chu FROM records_hoso WHERE so_ky_hieu = 'HSC'").fetchone()[0]
        self.assertNotEqual(note, "issue168-reset-probe")

    def test_ddl_hash_change_without_pending_migration_fails_before_database_mutation(self):
        self.create_bootstrap_db()
        with build_db.connect(self.args, self.args.dbname, autocommit=True) as conn:
            conn.execute("UPDATE records_hoso SET ghi_chu = 'issue168-ddl-drift-probe' WHERE so_ky_hieu = 'HSC'")
        before_marker = self.marker()

        with tempfile.TemporaryDirectory(prefix="issue168-ddl-drift-") as directory:
            altered_ddl = Path(directory) / "release_DDL.sql"
            altered_ddl.write_bytes(build_db.DEFAULT_DDL.read_bytes() + b"\n-- hash-only drift\n")
            result = self.run_builder("--sync", "--ddl", str(altered_ddl), expect_success=False)

        self.assertIn("release_DDL.sql đổi nhưng không có migration chờ", result.stderr)
        self.assertEqual(self.marker(), before_marker)
        with build_db.connect(self.args, self.args.dbname) as conn:
            note = conn.execute("SELECT ghi_chu FROM records_hoso WHERE so_ky_hieu = 'HSC'").fetchone()[0]
        self.assertEqual(note, "issue168-ddl-drift-probe")

    def test_sync_rejects_unexpected_release_schema_on_copy_before_live_mutation(self):
        self.create_bootstrap_db()
        with build_db.connect(self.args, self.args.dbname, autocommit=True) as conn:
            conn.execute(
                "UPDATE accounts_employee SET password = %s WHERE username = 'admin'",
                ["pbkdf2_sha256$system_seed_placeholder"],
            )
            conn.execute(
                "UPDATE records_hoso SET ghi_chu = 'issue168-release-preflight-probe' WHERE so_ky_hieu = 'HSC'"
            )
            conn.execute(
                "CREATE TABLE public.review_missing_upgrade ("
                "id bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY, payload text NOT NULL)"
            )
        self.forget_migration_history_and_descendants(
            "documents", "0008_ddl_integrity"
        )

        with build_db.connect(self.args, self.args.dbname) as conn:
            marker = build_db.build_mark(
                self.args,
                build_db.schema_fingerprint(conn),
                build_db.migration_fingerprint(build_db.applied_migrations(conn)),
                seed=True,
                ddl_hash=build_db.ddl_sha256(self.args),
            )
        with build_db.connect(self.args, "postgres", autocommit=True) as conn:
            conn.execute(
                sql.SQL("COMMENT ON DATABASE {} IS {}").format(
                    sql.Identifier(self.args.dbname), sql.Literal(marker)
                )
            )

        result = self.run_builder("--sync", expect_success=False)

        self.assertIn("Preflight schema khác release DDL/baseline", result.stderr)
        self.assertIn("review_missing_upgrade", result.stderr)
        self.assertIn("DB đích chưa bị thay đổi", result.stderr)
        self.assertEqual(self.marker(), marker)
        with build_db.connect(self.args, self.args.dbname) as conn:
            password = conn.execute(
                "SELECT password FROM accounts_employee WHERE username = 'admin'"
            ).fetchone()[0]
            note = conn.execute(
                "SELECT ghi_chu FROM records_hoso WHERE so_ky_hieu = 'HSC'"
            ).fetchone()[0]
            pending_migration = conn.execute(
                "SELECT 1 FROM django_migrations WHERE app = 'documents' "
                "AND name = '0008_ddl_integrity'"
            ).fetchone()
            pending_dependents = conn.execute(
                "SELECT app, name FROM django_migrations WHERE "
                "app = 'documents' AND name IN ('0009_schema_scalars', '0012_tep_dinh_kem_kho_dung_chung')"
            ).fetchall()
            extra_table = conn.execute(
                "SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' "
                "AND table_name = 'review_missing_upgrade'"
            ).fetchone()
        self.assertEqual(password, "pbkdf2_sha256$system_seed_placeholder")
        self.assertEqual(note, "issue168-release-preflight-probe")
        self.assertIsNone(pending_migration)
        self.assertEqual(pending_dependents, [])
        self.assertIsNotNone(extra_table)

    def test_failed_pending_migration_keeps_existing_database_and_data(self):
        self.create_bootstrap_db()
        with build_db.connect(self.args, self.args.dbname, autocommit=True) as conn:
            conn.execute(
                "UPDATE accounts_employee SET password = %s WHERE username = 'admin'",
                ["pbkdf2_sha256$system_seed_placeholder"],
            )
            conn.execute(
                "UPDATE records_hoso SET ghi_chu = 'issue168-failed-upgrade-probe' WHERE so_ky_hieu = 'HSC'"
            )
            conn.execute(
                "CREATE FUNCTION public.issue168_fail_system_password_upgrade() RETURNS trigger "
                "LANGUAGE plpgsql AS $$ BEGIN "
                "IF OLD.username = 'admin' AND OLD.password = 'pbkdf2_sha256$system_seed_placeholder' THEN "
                "RAISE EXCEPTION 'issue168 migration failure probe'; END IF; RETURN NEW; END $$"
            )
            conn.execute(
                "CREATE TRIGGER issue168_fail_system_password_upgrade "
                "BEFORE UPDATE ON accounts_employee FOR EACH ROW "
                "EXECUTE FUNCTION public.issue168_fail_system_password_upgrade()"
            )
        self.forget_migration_history_and_descendants(
            "accounts", "0007_normalize_system_account_password"
        )

        with build_db.connect(self.args, self.args.dbname) as conn:
            marker = build_db.build_mark(
                self.args,
                build_db.schema_fingerprint(conn),
                build_db.migration_fingerprint(build_db.applied_migrations(conn)),
                seed=True,
                ddl_hash=build_db.ddl_sha256(self.args),
            )
        with build_db.connect(self.args, "postgres", autocommit=True) as conn:
            conn.execute(
                sql.SQL("COMMENT ON DATABASE {} IS {}").format(
                    sql.Identifier(self.args.dbname), sql.Literal(marker)
                )
            )

        result = self.run_builder("--sync", expect_success=False)
        self.assertIn("issue168 migration failure probe", result.stderr)
        self.assertIn("Migration thất bại", result.stderr)
        self.assertEqual(self.marker(), marker)
        with build_db.connect(self.args, self.args.dbname) as conn:
            password = conn.execute(
                "SELECT password FROM accounts_employee WHERE username = 'admin'"
            ).fetchone()[0]
            note = conn.execute(
                "SELECT ghi_chu FROM records_hoso WHERE so_ky_hieu = 'HSC'"
            ).fetchone()[0]
            pending_migration = conn.execute(
                "SELECT 1 FROM django_migrations WHERE app = 'accounts' "
                "AND name = '0007_normalize_system_account_password'"
            ).fetchone()
            pending_dependents = conn.execute(
                "SELECT app, name FROM django_migrations WHERE "
                "(app = 'documents' AND name = '0008_ddl_integrity') OR "
                "(app = 'document_templates' AND name = '0003_ddl_integrity')"
            ).fetchall()
            failure_trigger = conn.execute(
                "SELECT 1 FROM pg_trigger WHERE tgname = 'issue168_fail_system_password_upgrade' "
                "AND NOT tgisinternal"
            ).fetchone()
        self.assertEqual(password, "pbkdf2_sha256$system_seed_placeholder")
        self.assertEqual(note, "issue168-failed-upgrade-probe")
        self.assertIsNone(pending_migration)
        self.assertEqual(pending_dependents, [])
        self.assertIsNotNone(failure_trigger)


    def _find_tool(self, tool):
        pg16_path = Path("/usr/lib/postgresql/16/bin") / tool
        if pg16_path.is_file() and os.access(pg16_path, os.X_OK):
            return str(pg16_path)
        found = shutil.which(tool)
        self.assertIsNotNone(found, f"thiếu {tool} trong PATH")
        return found

    def dump_restore(self, source, prefix):
        """pg_dump -Fc rồi pg_restore --no-owner --no-privileges vào DB scratch mới, như deploy.sh. Thiếu công cụ thì fail."""
        pg_dump_cmd = self._find_tool("pg_dump")
        pg_restore_cmd = self._find_tool("pg_restore")
        target = prefix + uuid.uuid4().hex[:10]
        self.extra_dbs = getattr(self, "extra_dbs", []) + [target]
        env = {**os.environ, "PGPASSWORD": self.base_env.get("DB_PASSWORD", "")}
        conn_args = ["-h", self.args.host, "-p", str(self.args.port), "-U", self.args.user]
        with tempfile.TemporaryDirectory() as tmp:
            dump = str(Path(tmp) / "db.dump")
            subprocess.run([pg_dump_cmd, *conn_args, "-Fc", "-f", dump, source], check=True, env=env)
            self.create_scratch(target)
            proc = subprocess.run(
                [pg_restore_cmd, *conn_args, "--no-owner", "--no-privileges", "-d", target, dump],
                check=False, env=env, capture_output=True, text=True,
            )
            if proc.returncode != 0:
                stderr = proc.stderr or ""
                # Khi pg_dump được chạy bởi client PG 17+ trên runner, lệnh dump tự chèn
                # "SET transaction_timeout = 0;". PostgreSQL 16 server trả về lỗi không nhận diện tham số này.
                # pg_restore ghi warning: errors ignored on restore: 1 và thoát mã 1 dù database đã nạp hoàn chỉnh.
                is_transaction_timeout_only = (
                    'unrecognized configuration parameter "transaction_timeout"' in stderr
                    and "errors ignored on restore: 1" in stderr
                )
                if not is_transaction_timeout_only:
                    sys.stderr.write(stderr)
                    proc.check_returncode()
        return target

    def create_scratch(self, dbname):
        self.extra_dbs = getattr(self, "extra_dbs", [])
        if dbname not in self.extra_dbs:
            self.extra_dbs.append(dbname)
        with build_db.connect(self.args, "postgres", autocommit=True) as conn:
            conn.execute(
                sql.SQL(
                    "CREATE DATABASE {} TEMPLATE template0 ENCODING 'UTF8' "
                    "LOCALE_PROVIDER icu ICU_LOCALE 'vi-VN' LOCALE 'C.UTF-8'"
                ).format(sql.Identifier(dbname))
            )

    def fingerprint(self, dbname):
        with build_db.connect(self.args, dbname) as conn:
            return build_db.schema_fingerprint(conn)

    def build_ddl_expected(self):
        expected = "qlvb_ddlexpect_" + uuid.uuid4().hex[:10]
        self.create_scratch(expected)
        with build_db.connect(self.args, expected) as conn:
            conn.execute(Path(build_db.DEFAULT_DDL).read_text(encoding="utf-8"), prepare=False)
        return expected

    def test_dump_restore_keeps_fingerprint_and_ddl_comparison_for_v2_and_head(self):
        self.create_supported_v2_fixture()
        v2_restored = self.dump_restore(self.args.dbname, "qlvb_migtest_")
        self.assertEqual(self.fingerprint(self.args.dbname), build_db.LEGACY_V2_SCHEMA_SHA256)
        self.assertEqual(self.fingerprint(v2_restored), build_db.LEGACY_V2_SCHEMA_SHA256)
        with build_db.connect(self.args, "postgres", autocommit=True) as conn:
            marker = build_db.read_mark(conn, self.args.dbname)
            conn.execute(
                sql.SQL("COMMENT ON DATABASE {} IS {}").format(sql.Identifier(v2_restored), sql.Literal(marker))
            )

        # Chuỗi như bước 5 của deploy.sh trên bản khôi phục.
        expected = self.build_ddl_expected()
        self.args.dbname, original = v2_restored, self.args.dbname
        try:
            self.run_builder("--adopt")
            self.run_builder("--sync", "--preflight-copy")
            self.run_manage("migrate", "--check")
            self.run_builder("--compare-schema-database", expected)
            head_fingerprint = self.fingerprint(v2_restored)
        finally:
            self.args.dbname = original

        # DB đã sync lên head: dump/restore giữ nguyên fingerprint và vẫn khớp DDL, kể cả marker v3 ở bản khôi phục.
        head_restored = self.dump_restore(v2_restored, "qlvb_migtest_")
        self.assertEqual(self.fingerprint(head_restored), head_fingerprint)
        self.run_builder_on(head_restored, "--compare-schema-database", expected)

    def run_builder_on(self, dbname, *args):
        original, self.args.dbname = self.args.dbname, dbname
        try:
            return self.run_builder(*args)
        finally:
            self.args.dbname = original

    def test_fresh_build_survives_dump_restore(self):
        self.run_builder("--seed")
        restored = self.dump_restore(self.args.dbname, "qlvb_migtest_")
        self.assertEqual(self.fingerprint(restored), self.fingerprint(self.args.dbname))
        self.run_builder_on(restored, "--compare-schema-database", self.build_ddl_expected())


if __name__ == "__main__":
    unittest.main()
