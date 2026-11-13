"""Synthetic, local-only backup/restore drill and fail-closed tests."""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "backend" / "apps"))

from backup_restore import (  # noqa: E402
    BackupError,
    _backup,
    _check_private_file,
    _database_info,
    _empty_state,
    _extract_file_tree,
    _hash_file,
    _inspect_file_tree,
    _mode_without_named_acl,
    _parse_private_config,
    _restore,
    _verified_archive,
    _write_tree_archive,
    main,
)


class PrivateInputTests(unittest.TestCase):
    def test_missing_required_key_fails_without_returning_secret_values(self):
        with self.assertRaisesRegex(BackupError, "required signing/application keys"):
            _parse_private_config(b"DJANGO_SECRET_KEY=synthetic-only\n")

    def test_missing_private_config_file_fails_closed(self):
        with tempfile.TemporaryDirectory(prefix="qlvb-missing-config-") as temp_name:
            with self.assertRaisesRegex(BackupError, "missing or unreadable"):
                _check_private_file(Path(temp_name) / "backend.env")

    def test_environment_expressions_are_not_evaluated_for_signing_keys(self):
        with self.assertRaisesRegex(BackupError, "literal value"):
            _parse_private_config(
                b"DJANGO_SECRET_KEY=synthetic-only\nSIGNING_PIN_SECRET=$SOME_OTHER_KEY\n"
            )

    def test_single_quoted_literal_dollar_is_preserved(self):
        values, _ = _parse_private_config(
            b"DJANGO_SECRET_KEY='synthetic$literal'\nSIGNING_PIN_SECRET='another$literal'\n"
        )
        self.assertEqual(values["SIGNING_PIN_SECRET"], "another$literal")

    @unittest.skipUnless(os.name == "posix", "POSIX file-mode contract")
    def test_private_configuration_rejects_group_or_other_access(self):
        with tempfile.TemporaryDirectory(prefix="qlvb-public-config-") as temp_name:
            config_path = Path(temp_name) / "backend.env"
            config_path.write_text(
                "DJANGO_SECRET_KEY=synthetic-only\nSIGNING_PIN_SECRET=synthetic-only\n",
                encoding="utf-8",
            )
            os.chmod(config_path, 0o640)
            with self.assertRaisesRegex(BackupError, "must not grant group or other access"):
                _check_private_file(config_path)

    def test_archive_paths_reject_parent_and_windows_drive_segments(self):
        from backup_restore import _safe_relative_path

        for unsafe in ("../escape", "/absolute", "C:/outside", "a/../../outside", "a\\..\\outside"):
            with self.subTest(path=unsafe), self.assertRaises(BackupError):
                _safe_relative_path(unsafe)

    def test_file_tree_rejects_traversal_entry(self):
        with tempfile.TemporaryDirectory(prefix="qlvb-malicious-tar-") as temp_name:
            archive_path = Path(temp_name) / "unsafe.tar"
            content = b"x"
            with tarfile.open(archive_path, "w") as archive:
                member = tarfile.TarInfo("../escape.txt")
                member.size = len(content)
                archive.addfile(member, io.BytesIO(content))
            with self.assertRaisesRegex(BackupError, "unsafe file path"):
                _inspect_file_tree(
                    archive_path,
                    expected={"entries": 1, "files": 1, "bytes": 1},
                )


class FileRootPermissionTests(unittest.TestCase):
    @staticmethod
    def _named_user_acl_data():
        import struct

        acl_entries = (
            (0x01, 0o6, 0xFFFFFFFF),
            (0x02, 0o4, 1000),
            (0x04, 0o0, 0xFFFFFFFF),
            (0x10, 0o4, 0xFFFFFFFF),
            (0x20, 0o0, 0xFFFFFFFF),
        )
        return struct.pack("<I", 0x0002) + b"".join(
            struct.pack("<HHI", *entry) for entry in acl_entries
        )

    def test_named_user_acl_mask_keeps_group_mode_at_base_permission(self):
        from unittest.mock import patch

        with patch(
            "backup_restore.os.getxattr",
            return_value=self._named_user_acl_data(),
            create=True,
        ):
            mode = _mode_without_named_acl(Path("sample.pdf"), 0o640)
        self.assertEqual(mode, 0o600)

    def test_named_user_acl_mask_does_not_become_group_mode_in_archive_or_restore(self):
        import errno
        from unittest.mock import patch

        with tempfile.TemporaryDirectory(prefix="qlvb-acl-mode-") as temp_name:
            root = Path(temp_name) / "source"
            root.mkdir()
            source_file = root / "sample.pdf"
            source_file.write_bytes(b"synthetic-pdf")
            os.chmod(source_file, 0o640)
            acl_data = self._named_user_acl_data()
            archive_path = Path(temp_name) / "files.tar"
            destination = Path(temp_name) / "restored"

            def fake_getxattr(path, attribute, *, follow_symlinks=True):
                if Path(path) == source_file and attribute == "system.posix_acl_access":
                    return acl_data
                missing_errno = getattr(errno, "ENODATA", getattr(errno, "ENOATTR", errno.EIO))
                raise OSError(missing_errno, "attribute not found")

            with patch("backup_restore.os.getxattr", side_effect=fake_getxattr, create=True):
                _write_tree_archive(root, archive_path)
            with tarfile.open(archive_path, mode="r:") as archive:
                self.assertEqual(archive.getmember("sample.pdf").mode, 0o600)
            _extract_file_tree(archive_path, destination)

            if os.name == "posix":
                restored_mode = (destination / "sample.pdf").stat().st_mode & 0o777
                self.assertEqual(restored_mode, 0o600)


class PostgreSQLBackupRestoreDrill(unittest.TestCase):
    """Requires explicit opt-in and a loopback PostgreSQL 16 test cluster."""

    @classmethod
    def setUpClass(cls):
        if os.environ.get("QLVB_BACKUP_TEST_ENABLED") != "1":
            raise unittest.SkipTest("set QLVB_BACKUP_TEST_ENABLED=1 only for a disposable loopback PG16 cluster")
        if os.environ.get("DB_HOST", "localhost").lower() not in ("localhost", "127.0.0.1", "::1"):
            raise unittest.SkipTest("backup/restore drill refuses non-loopback PostgreSQL hosts")
        if not os.environ.get("DB_USER"):
            raise unittest.SkipTest("DB_USER is required for the disposable restore drill")
        cls._assert_pg16_clients()
        try:
            import psycopg
            from psycopg import sql
        except ImportError as exc:
            raise unittest.SkipTest("psycopg is unavailable in the current Python runtime") from exc

        cls.psycopg = psycopg
        cls.sql = sql
        cls.suffix = os.urandom(6).hex()
        cls.source_db = f"qlvb_backup_test_src_{cls.suffix}"
        cls.restore_db = f"qlvb_backup_test_restore_{cls.suffix}"
        cls.corrupt_db = f"qlvb_backup_test_corrupt_{cls.suffix}"
        cls.guarded_db = f"qlvb_backup_test_guard_{cls.suffix}"
        cls.wrong_confirmation_db = f"qlvb_backup_test_confirm_{cls.suffix}"
        cls.created_databases: list[str] = []
        cls.temp = tempfile.TemporaryDirectory(prefix="qlvb-backup-restore-drill-")
        cls.root = Path(cls.temp.name)
        cls.addClassCleanup(cls._cleanup_test_resources)
        cls.roots = {name: cls.root / "source" / name for name in ("media", "signing", "ai", "storage")}
        for path in cls.roots.values():
            path.mkdir(parents=True)
        (cls.roots["media"] / "records").mkdir()
        (cls.roots["media"] / "records" / "synthetic.bin").write_bytes(b"media-payload-only")
        (cls.roots["storage"] / "van-ban-den" / "2026" / "10" / "21").mkdir(parents=True)
        (cls.roots["storage"] / "van-ban-den" / "2026" / "10" / "21" / "synthetic.pdf").write_bytes(b"synthetic-business-file")
        (cls.roots["signing"] / "documents").mkdir()
        (cls.roots["signing"] / "documents" / "synthetic.pdf").write_bytes(b"synthetic-signed-document")
        (cls.roots["ai"] / "docs").mkdir()
        (cls.roots["ai"] / "docs" / "synthetic.md").write_text("synthetic knowledge base\n", encoding="utf-8")
        (cls.roots["ai"] / "doc_registry.json").write_text('{"synthetic": true}\n', encoding="utf-8")

        cls.pin_secret = f"synthetic-signing-key-{cls.suffix}-never-log"
        cls.django_secret = f"synthetic-django-key-{cls.suffix}-never-log"
        cls.config_path = cls.root / "source-config" / "backend.env"
        cls.config_path.parent.mkdir()
        cls.config_path.write_text(
            "\n".join(
                (
                    f"DJANGO_SECRET_KEY={cls.django_secret}",
                    f"SIGNING_PIN_SECRET={cls.pin_secret}",
                    f"DJANGO_MEDIA_ROOT={cls.roots['media']}",
                    f"SIGNING_DOCUMENT_ROOT={cls.roots['signing']}",
                    f"AI_DATA_DIR={cls.roots['ai']}",
                    f"DOCUMENT_STORAGE_ROOT={cls.roots['storage']}",
                    "",
                )
            ),
            encoding="utf-8",
        )
        os.chmod(cls.config_path, 0o600)
        cls.output_parent = cls.root / "output-parent"
        cls.output_parent.mkdir()
        cls.output_dir = cls.output_parent / "backups"
        cls.restore_parent = cls.root / "restore-parent"
        cls.restore_parent.mkdir()
        cls.restore_root = cls.restore_parent / "restored"
        cls.archive_path = None

        cls._create_database(cls.source_db)
        cls._create_database(cls.restore_db)
        cls._create_database(cls.corrupt_db)
        cls._create_database(cls.guarded_db)
        cls._create_database(cls.wrong_confirmation_db)
        cls._prepare_source_database()

        cls.pin_code = "123456"
        cls._insert_signing_fixture()

        cls.archive_path = _backup(
            database=cls.source_db,
            release_id="synthetic-drill",
            output_dir=cls.output_dir,
            roots=cls.roots,
            private_config=cls.config_path,
            files_quiesced=True,
            include_private_config=True,
        )

    @classmethod
    def _assert_pg16_clients(cls):
        import subprocess

        for tool in ("psql", "pg_dump", "pg_restore"):
            result = subprocess.run(
                [tool, "--version"],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            if result.returncode or " 16." not in result.stdout:
                raise unittest.SkipTest(f"{tool} must be PostgreSQL 16 for this drill")

    @classmethod
    def _admin_connection(cls):
        return cls.psycopg.connect(
            host=os.environ.get("DB_HOST", "localhost"),
            port=os.environ.get("DB_PORT", "5432"),
            user=os.environ["DB_USER"],
            password=os.environ.get("DB_PASSWORD") or os.environ.get("PGPASSWORD"),
            dbname=os.environ.get("QLVB_BACKUP_TEST_ADMIN_DB", "postgres"),
            autocommit=True,
        )

    @classmethod
    def _create_database(cls, name: str):
        collation = (
            "CREATE DATABASE {} WITH TEMPLATE template0 ENCODING 'UTF8' "
            "LOCALE_PROVIDER icu ICU_LOCALE 'vi-VN'"
        )
        with cls._admin_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (name,))
                if cursor.fetchone():
                    raise RuntimeError("randomized test database name unexpectedly already exists")
                cursor.execute(cls.sql.SQL(collation).format(cls.sql.Identifier(name)))
        cls.created_databases.append(name)

    @classmethod
    def _database_connection(cls, name: str):
        return cls.psycopg.connect(
            host=os.environ.get("DB_HOST", "localhost"),
            port=os.environ.get("DB_PORT", "5432"),
            user=os.environ["DB_USER"],
            password=os.environ.get("DB_PASSWORD") or os.environ.get("PGPASSWORD"),
            dbname=name,
            autocommit=True,
        )

    @classmethod
    def _prepare_source_database(cls):
        marker = (
            "build_db:v3 ddl_sha256="
            + "a" * 64
            + " seed=0 collation=icu:vi-VN schema_sha256="
            + "b" * 64
            + " migrations_sha256="
            + "c" * 64
        )
        with cls._database_connection(cls.source_db) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    cls.sql.SQL("COMMENT ON DATABASE {} IS {}").format(
                        cls.sql.Identifier(cls.source_db), cls.sql.Literal(marker)
                    )
                )
                cursor.execute(
                    "CREATE TABLE signing_fixture ("
                    "id integer PRIMARY KEY, pin_verifier text NOT NULL, salt bytea NOT NULL, file_path text NOT NULL)"
                )

    @staticmethod
    def _pin_verifier(secret, pin, salt):
        """Cùng hợp đồng với signing.services.pin: HMAC(SIGNING_PIN_SECRET, PIN) rồi PBKDF2-SHA256."""
        import hashlib
        import hmac

        preimage = hmac.new(
            secret.encode(), b"signing-pin-verifier-v1:" + pin.encode(), hashlib.sha256
        ).hexdigest()
        return hashlib.pbkdf2_hmac("sha256", preimage.encode(), salt, 1000).hex()

    @classmethod
    def _insert_signing_fixture(cls):
        import os as _os

        salt = _os.urandom(16)
        verifier = cls._pin_verifier(cls.pin_secret, cls.pin_code, salt)
        with cls._database_connection(cls.source_db) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO signing_fixture (id,pin_verifier,salt,file_path) VALUES (42,%s,%s,%s)",
                    (verifier, salt, "documents/synthetic.pdf"),
                )

    @classmethod
    def _cleanup_test_resources(cls):
        try:
            if hasattr(cls, "created_databases"):
                if cls.created_databases:
                    with cls._admin_connection() as connection:
                        with connection.cursor() as cursor:
                            for name in reversed(cls.created_databases):
                                cursor.execute(
                                    cls.sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(
                                        cls.sql.Identifier(name)
                                    )
                                )
        finally:
            if hasattr(cls, "temp"):
                cls.temp.cleanup()

    def test_archive_is_private_verified_and_does_not_log_secrets(self):
        self.assertTrue(self.archive_path.is_file())
        self.assertEqual(self.archive_path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.output_dir.stat().st_mode & 0o777, 0o700)
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = main(["verify", "--archive", str(self.archive_path)])
        self.assertEqual(result, 0)
        self.assertIn("Verified backup", stdout.getvalue())
        self.assertNotIn(self.pin_secret, stdout.getvalue() + stderr.getvalue())
        self.assertNotIn(self.django_secret, stdout.getvalue() + stderr.getvalue())
        with _verified_archive(self.archive_path) as verified:
            self.assertEqual(verified["metadata"]["release_id"], "synthetic-drill")
            self.assertEqual(verified["marker"], verified["metadata"]["database"]["marker"])
            self.assertEqual(verified["metadata"]["database"]["server_version_num"] // 10000, 16)
            config = verified["payloads"]["private_config/backend.env"]
            self.assertEqual(config.stat().st_mode & 0o777, 0o600)
            self.assertNotIn(self.pin_secret, verified["payloads"]["metadata.json"].read_text(encoding="utf-8"))

    def test_backup_json_returns_absolute_archive_and_digest_without_secrets(self):
        output_dir = self.output_parent / "json-backups"
        stdout, stderr = io.StringIO(), io.StringIO()
        args = [
            "backup", "--database", self.source_db, "--release-id", "synthetic-json",
            "--output-dir", str(output_dir), "--media-dir", str(self.roots["media"]),
            "--signing-dir", str(self.roots["signing"]), "--ai-dir", str(self.roots["ai"]),
            "--storage-dir", str(self.roots["storage"]),
            "--private-config", str(self.config_path), "--include-private-config", "--files-quiesced", "--json",
        ]
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = main(args)
        self.assertEqual(result, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(set(payload), {"archive", "size_bytes", "sha256"})
        archive_path = Path(payload["archive"])
        self.assertTrue(archive_path.is_absolute())
        self.assertEqual(archive_path.parent, output_dir.resolve())
        self.assertEqual(archive_path.stat().st_mode & 0o777, 0o600)
        self.assertGreater(payload["size_bytes"], 0)
        self.assertEqual(_hash_file(archive_path), (payload["sha256"], payload["size_bytes"]))
        combined_output = stdout.getvalue() + stderr.getvalue()
        self.assertNotIn(self.pin_secret, combined_output)
        self.assertNotIn(self.django_secret, combined_output)

    def test_extract_database_dump_is_verified_private_and_non_overwriting(self):
        output_dir = self.root / "extracted-dump"
        output_dir.mkdir(mode=0o700)
        os.chmod(output_dir, 0o700)
        output_path = output_dir / "database.dump"
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = main([
                "extract-database-dump", "--archive", str(self.archive_path), "--output", str(output_path)
            ])
        self.assertEqual(result, 0)
        self.assertTrue(output_path.is_file())
        self.assertEqual(output_path.stat().st_mode & 0o777, 0o600)
        with _verified_archive(self.archive_path) as verified:
            expected_dump_hash = _hash_file(verified["payloads"]["database.dump"])
        self.assertEqual(_hash_file(output_path), expected_dump_hash)
        self.assertNotIn(self.pin_secret, stdout.getvalue() + stderr.getvalue())
        self.assertNotIn(self.django_secret, stdout.getvalue() + stderr.getvalue())

        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            result = main([
                "extract-database-dump", "--archive", str(self.archive_path), "--output", str(output_path)
            ])
        self.assertEqual(result, 2)
        self.assertEqual(_hash_file(output_path), expected_dump_hash)

    def test_extract_rejects_nonprivate_output_parent_without_writing(self):
        output_dir = self.root / "nonprivate-extract"
        output_dir.mkdir(mode=0o755)
        os.chmod(output_dir, 0o755)
        output_path = output_dir / "database.dump"
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = main([
                "extract-database-dump", "--archive", str(self.archive_path), "--output", str(output_path)
            ])
        self.assertEqual(result, 2)
        self.assertFalse(output_path.exists())
        self.assertNotIn(self.pin_secret, stdout.getvalue() + stderr.getvalue())
        self.assertNotIn(self.django_secret, stdout.getvalue() + stderr.getvalue())

    def test_missing_data_root_or_private_key_fails_before_archive_creation(self):
        missing_root_output = self.output_parent / "missing-root-backups"
        with self.assertRaisesRegex(BackupError, "ai path is missing"):
            _backup(
                database=self.source_db,
                release_id="missing-root",
                output_dir=missing_root_output,
                roots={**self.roots, "ai": self.root / "no-ai-root"},
                private_config=self.config_path,
                files_quiesced=True,
                include_private_config=True,
            )
        self.assertFalse(missing_root_output.exists())

        incomplete_config = self.root / "source-config" / "missing-signing-key.env"
        incomplete_config.write_text(f"DJANGO_SECRET_KEY={self.django_secret}\n", encoding="utf-8")
        os.chmod(incomplete_config, 0o600)
        missing_key_output = self.output_parent / "missing-key-backups"
        with self.assertRaisesRegex(BackupError, "required signing/application keys"):
            _backup(
                database=self.source_db,
                release_id="missing-key",
                output_dir=missing_key_output,
                roots=self.roots,
                private_config=incomplete_config,
                files_quiesced=True,
                include_private_config=True,
            )
        self.assertFalse(missing_key_output.exists())

    def test_missing_storage_root_fails_before_archive_creation(self):
        output = self.output_parent / "missing-storage-backups"
        with self.assertRaisesRegex(BackupError, "storage path is missing"):
            _backup(
                database=self.source_db,
                release_id="missing-storage",
                output_dir=output,
                roots={**self.roots, "storage": self.root / "no-storage-root"},
                private_config=self.config_path,
                files_quiesced=True,
                include_private_config=True,
            )
        self.assertFalse(output.exists())
        with self.assertRaisesRegex(BackupError, "all required"):
            _backup(
                database=self.source_db,
                release_id="no-storage-argument",
                output_dir=output,
                roots={name: path for name, path in self.roots.items() if name != "storage"},
                private_config=self.config_path,
                files_quiesced=True,
                include_private_config=True,
            )

    def _legacy_archive(self) -> Path:
        """Archive đúng định dạng trước khi có kho tệp nghiệp vụ: không có files/storage.tar."""
        legacy_dir = self.output_parent / "legacy-backups"
        legacy_dir.mkdir(mode=0o700, exist_ok=True)
        legacy = legacy_dir / "qlvb-backup-legacy-20260101T000000Z.tar.gz"
        with tempfile.TemporaryDirectory(prefix="legacy-archive-") as work_name:
            work = Path(work_name)
            payloads = {}
            with tarfile.open(self.archive_path, "r:gz") as source:
                for member in source.getmembers():
                    if member.name in ("manifest.json", "files/storage.tar"):
                        continue
                    payloads[member.name] = source.extractfile(member).read()
            metadata = json.loads(payloads["metadata.json"])
            del metadata["file_roots"]["storage"]
            payloads["metadata.json"] = json.dumps(metadata, sort_keys=True).encode()
            manifest = {
                "format_version": 1,
                "files": {
                    name: {"sha256": hashlib.sha256(data).hexdigest(), "size": len(data), "mode": 0o600}
                    for name, data in payloads.items()
                },
            }
            payloads["manifest.json"] = json.dumps(manifest, sort_keys=True).encode()
            with tarfile.open(legacy, "w:gz") as target:
                for name, data in payloads.items():
                    info = tarfile.TarInfo(name)
                    info.size, info.mode = len(data), 0o600
                    target.addfile(info, io.BytesIO(data))
        os.chmod(legacy, 0o600)
        return legacy

    def test_archive_without_storage_root_still_verifies_and_restores(self):
        legacy = self._legacy_archive()
        with _verified_archive(legacy) as verified:
            self.assertEqual(verified["roots"], ("media", "signing", "ai"))
        restore_db = f"qlvb_backup_test_legacy_{self.suffix}"
        self._create_database(restore_db)
        restore_root = self.restore_parent / "restored-legacy"
        _restore(archive_path=legacy, database=restore_db, confirm_target_db=restore_db, restore_root=restore_root)
        self.assertTrue((restore_root / "media/records/synthetic.bin").is_file())
        self.assertFalse((restore_root / "storage").exists())
        path_map = json.loads((restore_root / "config/recovered-paths.json").read_text(encoding="utf-8"))
        self.assertNotIn("DOCUMENT_STORAGE_ROOT", path_map)

    def test_reset_gate_preserves_nonempty_target(self):
        with self._database_connection(self.guarded_db) as connection:
            with connection.cursor() as cursor:
                cursor.execute("CREATE TABLE keep_me (value text NOT NULL)")
                cursor.execute("INSERT INTO keep_me VALUES ('preserve-this-row')")
        with self.assertRaisesRegex(BackupError, "not empty"):
            _restore(
                archive_path=self.archive_path,
                database=self.guarded_db,
                confirm_target_db=self.guarded_db,
                restore_root=self.restore_parent / "guarded",
            )
        with self._database_connection(self.guarded_db) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT value FROM keep_me")
                self.assertEqual(cursor.fetchone()[0], "preserve-this-row")
        self.assertFalse((self.restore_parent / "guarded").exists())

    def test_missing_and_corrupt_archives_leave_target_untouched(self):
        missing = self.root / "missing.tar.gz"
        with self.assertRaisesRegex(BackupError, "missing or unreadable"):
            _restore(
                archive_path=missing,
                database=self.corrupt_db,
                confirm_target_db=self.corrupt_db,
                restore_root=self.restore_parent / "missing-archive",
            )
        self.assertEqual(_empty_state(self.corrupt_db)["relations"], 0)

        corrupted = self.root / "corrupted.tar.gz"
        with tarfile.open(self.archive_path, mode="r:gz") as source:
            with tarfile.open(corrupted, mode="w:gz") as altered:
                for member in source:
                    stream = source.extractfile(member)
                    if stream is None:
                        self.fail("expected readable members in the source backup")
                    with stream:
                        if member.name == "metadata.json":
                            payload = stream.read()
                            altered.addfile(member, io.BytesIO(bytes([payload[0] ^ 0x20]) + payload[1:]))
                        else:
                            altered.addfile(member, stream)
        os.chmod(corrupted, 0o600)
        extract_root = self.root / "failed-extract"
        extract_root.mkdir(mode=0o700)
        os.chmod(extract_root, 0o700)
        failed_dump = extract_root / "database.dump"
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            result = main([
                "extract-database-dump", "--archive", str(corrupted), "--output", str(failed_dump)
            ])
        self.assertEqual(result, 2)
        self.assertFalse(failed_dump.exists())
        with self.assertRaises(BackupError):
            _restore(
                archive_path=corrupted,
                database=self.corrupt_db,
                confirm_target_db=self.corrupt_db,
                restore_root=self.restore_parent / "corrupt-archive",
            )
        self.assertTrue(corrupted.exists(), "failed verification must retain the backup copy")
        self.assertEqual(_empty_state(self.corrupt_db)["relations"], 0)
        self.assertFalse((self.restore_parent / "corrupt-archive").exists())

    def test_wrong_confirmation_fails_before_target_access(self):
        with self.assertRaisesRegex(BackupError, "must exactly match"):
            _restore(
                archive_path=self.archive_path,
                database=self.wrong_confirmation_db,
                confirm_target_db="some-other-database",
                restore_root=self.restore_parent / "wrong-confirmation",
            )
        self.assertEqual(_empty_state(self.wrong_confirmation_db)["relations"], 0)

    def test_full_restore_recovers_db_marker_files_pin_secret_and_access(self):
        import hmac

        from signing.storage import FilesystemStorageAdapter, StorageError

        _restore(
            archive_path=self.archive_path,
            database=self.restore_db,
            confirm_target_db=self.restore_db,
            restore_root=self.restore_root,
        )
        self.assertEqual(
            _database_info(self.restore_db)["marker"],
            _database_info(self.source_db)["marker"],
        )
        with self._database_connection(self.restore_db) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT pin_verifier,salt,file_path FROM signing_fixture WHERE id=42"
                )
                pin_verifier, salt, file_path = cursor.fetchone()
        self.assertEqual(file_path, "documents/synthetic.pdf")
        self.assertEqual((self.restore_root / "media/records/synthetic.bin").read_bytes(), b"media-payload-only")
        self.assertEqual(
            (self.restore_root / "storage/van-ban-den/2026/10/21/synthetic.pdf").read_bytes(),
            b"synthetic-business-file",
        )
        self.assertEqual((self.restore_root / "ai/docs/synthetic.md").read_text(encoding="utf-8"), "synthetic knowledge base\n")
        self.assertEqual((self.restore_root / "ai/doc_registry.json").read_text(encoding="utf-8"), '{"synthetic": true}\n')
        adapter = FilesystemStorageAdapter(root=self.restore_root / "signing")
        self.assertEqual(adapter.read_bytes(file_path), b"synthetic-signed-document")
        self.assertEqual(adapter.metadata(file_path).kich_thuoc, len(b"synthetic-signed-document"))
        with self.assertRaises(StorageError):
            adapter.read_bytes("../outside.txt")

        recovered_env = (self.restore_root / "private_config/backend.env").read_bytes()
        recovered_values, _ = _parse_private_config(recovered_env)
        recovered_secret = recovered_values["SIGNING_PIN_SECRET"]
        self.assertTrue(
            hmac.compare_digest(
                pin_verifier,
                self._pin_verifier(recovered_secret, self.pin_code, bytes(salt)),
            )
        )
        self.assertFalse(
            hmac.compare_digest(
                pin_verifier,
                self._pin_verifier(recovered_secret, "654321", bytes(salt)),
            )
        )
        path_map = __import__("json").loads(
            (self.restore_root / "config/recovered-paths.json").read_text(encoding="utf-8")
        )
        self.assertEqual(path_map["SIGNING_DOCUMENT_ROOT"], str(self.restore_root / "signing"))
        self.assertEqual(path_map["DOCUMENT_STORAGE_ROOT"], str(self.restore_root / "storage"))
        self.assertEqual(
            (self.restore_root / "private_config/backend.env").stat().st_mode & 0o777,
            0o600,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
