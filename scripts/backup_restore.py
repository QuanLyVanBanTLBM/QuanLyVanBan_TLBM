#!/usr/bin/env python3
"""Create, inspect, and restore a protected PostgreSQL + file backup."""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import gzip
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path, PurePosixPath

ARCHIVE_VERSION = 1
POSTGRES_MAJOR = 16
ROOT_NAMES = ("media", "signing", "ai", "storage")
# Archive tạo trước khi có kho tệp nghiệp vụ (issue #192) không có gốc này vẫn phải kiểm tra và khôi phục được.
OPTIONAL_ROOT_NAMES = ("storage",)
ROOT_PATH_VARIABLES = {
    "media": "DJANGO_MEDIA_ROOT", "signing": "SIGNING_DOCUMENT_ROOT", "ai": "AI_DATA_DIR",
    "storage": "DOCUMENT_STORAGE_ROOT",
}
PRIVATE_CONFIG_MEMBER = "private_config/backend.env"
REQUIRED_CONFIG_KEYS = ("DJANGO_SECRET_KEY", "SIGNING_PIN_SECRET")
KNOWN_SECRET_KEYS = (
    "DJANGO_SECRET_KEY", "DB_PASSWORD", "DB_READONLY_PASSWORD", "SIGNING_PIN_SECRET",
    "GEMINI_API_KEY", "OPENAI_API_KEY", "ALPACA_SECRET_KEY", "EMAIL_HOST_PASSWORD",
)
NON_SECRET_ENV_KEYS = (
    "DJANGO_DEBUG", "DJANGO_ALLOWED_HOSTS", "DJANGO_CSRF_TRUSTED_ORIGINS",
    "DJANGO_SECURE_PROXY_SSL_HEADER", "DJANGO_SECURE_SSL_REDIRECT", "DJANGO_SECURE_COOKIES",
    "DJANGO_SECURE_HSTS_SECONDS", "DB_ENGINE", "DB_NAME", "DB_HOST", "DB_PORT", "DB_USER",
    "DB_READONLY_USER", "DB_READONLY_NAME", "DB_READONLY_HOST", "DB_READONLY_PORT",
    "DJANGO_MEDIA_ROOT", "SIGNING_DOCUMENT_ROOT", "SIGNING_PDF_FONT", "SIGNING_PDF_FONT_BOLD",
    "DOCUMENT_STORAGE_ROOT", "AI_DATA_DIR", "MODEL_PROVIDER", "COLLECTION_NAME", "EMBED_MODEL", "LLM_MODEL", "VISION_MODEL",
    "VISION_OCR_ENABLED", "VISION_OCR_MODE", "VISION_OCR_PDF_DPI", "VISION_OCR_TIMEOUT",
    "VISION_OCR_MAX_IMAGE_SIZE", "VISION_OCR_JPEG_QUALITY", "VISION_OCR_PARALLEL_WORKERS",
    "CHAT_HISTORY_MAX_TURNS", "CHAT_HISTORY_MAX_CHARS", "EMAIL_HOST", "EMAIL_PORT",
    "EMAIL_USE_TLS", "EMAIL_HOST_USER", "DEFAULT_FROM_EMAIL", "BRAND_NAME", "ORGANIZATION_NAME",
    "ALPACA_CHECK_AUTH_URL", "ALPACA_CHECK_USER_URL",
)
PAYLOAD_MEMBERS = (
    "metadata.json", "db_marker.json", "database.dump", "files/media.tar",
    "files/signing.tar", "files/ai.tar", "files/storage.tar", PRIVATE_CONFIG_MEMBER,
)
OPTIONAL_PAYLOAD_MEMBERS = tuple(f"files/{name}.tar" for name in OPTIONAL_ROOT_NAMES)
MAX_CONFIG_BYTES = 2 * 1024 * 1024
MAX_METADATA_BYTES = 32 * 1024 * 1024


class BackupError(Exception):
    """An expected, safe-to-display backup or restore failure."""


def _safe_release_id(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", value or ""):
        raise BackupError("release ID must use 1-64 letters, digits, dots, underscores, or hyphens.")
    return value


def _check_private_file(path: Path, *, max_bytes: int | None = None) -> bytes:
    try:
        info = path.lstat()
    except OSError as exc:
        raise BackupError("private configuration input is missing or unreadable.") from exc
    if not stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode):
        raise BackupError("private configuration input must be a regular file, not a symlink.")
    if os.name == "posix" and stat.S_IMODE(info.st_mode) & 0o077:
        raise BackupError("private configuration file must not grant group or other access.")
    if max_bytes is not None and info.st_size > max_bytes:
        raise BackupError("private configuration file exceeds the supported size limit.")
    try:
        return path.read_bytes()
    except OSError as exc:
        raise BackupError("private configuration input is unreadable.") from exc


def _has_shell_expansion(value: str) -> bool:
    quote: str | None = None
    escaped = False
    for char in value:
        if quote == "'":
            if char == "'":
                quote = None
            continue
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if quote == '"':
            if char == '"':
                quote = None
            elif char in ("$", chr(96)):
                return True
            continue
        if char in ("'", '"'):
            quote = char
        elif char in ("$", chr(96)):
            return True
    return False


def _parse_private_config(data: bytes) -> tuple[dict[str, str], set[str]]:
    """Read literal KEY=value assignments without evaluating shell expressions."""
    import shlex

    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise BackupError("private configuration file must be UTF-8 text.") from exc
    values: dict[str, str] = {}
    seen: set[str] = set()
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        key, separator, raw_value = line.partition("=")
        key = key.strip()
        if not separator or not re.fullmatch(r"[A-Z][A-Z0-9_]*", key):
            continue
        seen.add(key)
        if key not in REQUIRED_CONFIG_KEYS:
            continue
        if _has_shell_expansion(raw_value):
            raise BackupError(f"{key} must be a literal value in the private configuration file.")
        if key in values:
            raise BackupError(f"private configuration contains duplicate {key} assignments.")
        try:
            parsed = shlex.split(raw_value, comments=True, posix=True)
        except ValueError as exc:
            raise BackupError(f"private configuration has invalid quoting for {key}.") from exc
        if len(parsed) != 1 or not parsed[0]:
            raise BackupError(f"private configuration is missing a non-empty {key}.")
        values[key] = parsed[0]
    if any(key not in values for key in REQUIRED_CONFIG_KEYS):
        raise BackupError("private configuration is missing required signing/application keys.")
    return values, seen


def _safe_relative_path(name: str) -> PurePosixPath:
    if not name or "\\" in name or name.startswith("/") or "\x00" in name:
        raise BackupError("archive contains an unsafe file path.")
    path = PurePosixPath(name)
    if path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
        raise BackupError("archive contains an unsafe file path.")
    if path.parts and ":" in path.parts[0]:
        raise BackupError("archive contains an unsafe file path.")
    return path


def _assert_safe_path(path: Path, label: str) -> Path:
    try:
        info = path.lstat()
    except OSError as exc:
        raise BackupError(f"required {label} path is missing or unreadable.") from exc
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        raise BackupError(f"required {label} path must be a real directory, not a symlink.")
    try:
        resolved = path.resolve(strict=True)
        with os.scandir(resolved):
            pass
    except OSError as exc:
        raise BackupError(f"required {label} path is unreadable.") from exc
    return resolved


def _walk_tree(root: Path) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []

    def raise_walk_error(exc: OSError) -> None:
        target = getattr(exc, "filename", None) or str(exc)
        raise BackupError(f"a required data directory or file is unreadable: {target}") from exc

    for current, directories, filenames in os.walk(root, topdown=True, followlinks=False, onerror=raise_walk_error):
        directories.sort()
        filenames.sort()
        current_path = Path(current)
        for name in directories + filenames:
            path = current_path / name
            try:
                info = path.lstat()
            except OSError as exc:
                raise BackupError("a required data directory or file became unreadable.") from exc
            relative = path.relative_to(root).as_posix()
            _safe_relative_path(relative)
            if stat.S_ISLNK(info.st_mode):
                raise BackupError("data roots may not contain symlinks.")
            if stat.S_ISDIR(info.st_mode):
                kind, size = "directory", 0
            elif stat.S_ISREG(info.st_mode):
                kind, size = "file", info.st_size
                try:
                    with path.open("rb") as source:
                        while source.read(1024 * 1024):
                            pass
                except OSError as exc:
                    raise BackupError("a required data file is unreadable.") from exc
            else:
                raise BackupError("data roots may contain only regular files and directories.")
            entries.append({
                "path": relative, "kind": kind, "size": size,
                "mode": stat.S_IMODE(info.st_mode),
                "uid": getattr(info, "st_uid", 0), "gid": getattr(info, "st_gid", 0),
                "mtime": int(info.st_mtime),
            })
    return entries


def _private_output_dir(path: Path) -> Path:
    if os.path.lexists(path):
        try:
            info = path.lstat()
        except OSError as exc:
            raise BackupError("backup output directory is unavailable.") from exc
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            raise BackupError("backup output path must be a real directory.")
        if os.name == "posix" and stat.S_IMODE(info.st_mode) & 0o077:
            raise BackupError("backup output directory must grant access only to its owner.")
        if os.name == "posix" and info.st_uid != os.geteuid():
            raise BackupError("backup output directory must be owned by the backup process user.")
    else:
        if not path.parent.is_dir():
            raise BackupError("backup output parent directory must already exist.")
        try:
            path.mkdir(mode=0o700)
        except OSError as exc:
            raise BackupError("could not create a private backup output directory.") from exc
        if os.name == "posix":
            os.chmod(path, 0o700)
    return path.resolve(strict=True)


def _assert_paths_do_not_overlap(output: Path, roots: dict[str, Path], config: Path) -> None:
    for name, root in roots.items():
        if output == root or output.is_relative_to(root) or root.is_relative_to(output):
            raise BackupError(f"backup output directory must be separate from the {name} data root.")
        if config.is_relative_to(root):
            raise BackupError("private configuration file must be stored outside all data roots.")


def _pg_environment() -> dict[str, str]:
    env = os.environ.copy()
    if "DB_PASSWORD" in env and "PGPASSWORD" not in env:
        env["PGPASSWORD"] = env["DB_PASSWORD"]
    env.pop("DB_PASSWORD", None)
    return env


def _pg_connection_args(database: str) -> list[str]:
    host = os.environ.get("DB_HOST", "localhost")
    port = os.environ.get("DB_PORT", "5432")
    user = os.environ.get("DB_USER", "")
    if not user:
        raise BackupError("DB_USER is required for PostgreSQL backup and restore.")
    if not database or "\x00" in database:
        raise BackupError("database name is required.")
    return ["--host", host, "--port", port, "--username", user, "--dbname", database]


def _run_tool(command: list[str], *, output: Path | None = None, stdout: bool = False) -> str:
    try:
        result = subprocess.run(
            command, check=False, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=stdout, env=_pg_environment(),
        )
    except OSError as exc:
        raise BackupError(f"required PostgreSQL utility is unavailable: {Path(command[0]).name}.") from exc
    if result.returncode:
        raise BackupError(f"{Path(command[0]).name} failed (exit {result.returncode}); diagnostics suppressed.")
    if output is not None and not output.is_file():
        raise BackupError(f"{Path(command[0]).name} completed without producing its output.")
    return result.stdout if stdout else ""


def _tool_major(tool: str) -> int:
    try:
        result = subprocess.run(
            [tool, "--version"], check=False, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
    except OSError as exc:
        raise BackupError(f"required PostgreSQL utility is unavailable: {tool}.") from exc
    match = re.search(r"\(PostgreSQL\)\s+(\d+)", result.stdout or "")
    if result.returncode or not match:
        raise BackupError(f"could not identify the PostgreSQL {tool} version.")
    major = int(match.group(1))
    if major != POSTGRES_MAJOR:
        raise BackupError(f"{tool} major version must be PostgreSQL {POSTGRES_MAJOR}.")
    return major


DATABASE_INFO_SQL = """
SELECT json_build_object(
  'name', current_database(),
  'server_version', current_setting('server_version'),
  'server_version_num', current_setting('server_version_num')::integer,
  'owner', pg_get_userbyid(d.datdba),
  'is_superuser', r.rolsuper,
  'collation', json_build_object(
    'provider', d.datlocprovider,
    'locale', coalesce(to_jsonb(d)->>'daticulocale', to_jsonb(d)->>'datlocale'),
    'lc_collate', d.datcollate,
    'lc_ctype', d.datctype,
    'recorded_version', d.datcollversion,
    'actual_version', pg_database_collation_actual_version(d.oid)
  ),
  'marker', shobj_description(d.oid, 'pg_database')
)::text
FROM pg_database d
JOIN pg_roles r ON r.rolname = current_user
WHERE d.datname = current_database()
"""

EMPTY_STATE_SQL = """
SELECT json_build_object(
  'user_schemas', (
    SELECT count(*) FROM pg_namespace
    WHERE nspname NOT IN ('public', 'pg_catalog', 'information_schema')
      AND nspname NOT LIKE 'pg\\_%'
  ),
  'relations', (
    SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
      AND n.nspname NOT LIKE 'pg\\_%'
  ),
  'functions', (
    SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
      AND n.nspname NOT LIKE 'pg\\_%'
  ),
  'types', (
    SELECT count(*) FROM pg_type t JOIN pg_namespace n ON n.oid = t.typnamespace
    WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
      AND n.nspname NOT LIKE 'pg\\_%'
      AND t.typcategory <> 'A'
  ),
  'extensions', (SELECT count(*) FROM pg_extension WHERE extname <> 'plpgsql'),
  'marker', shobj_description(d.oid, 'pg_database'),
  'current_user', current_user,
  'is_superuser', r.rolsuper,
  'database_owner', pg_get_userbyid(d.datdba)
)::text
FROM pg_database d
JOIN pg_roles r ON r.rolname = current_user
WHERE d.datname = current_database()
"""


def _query_json(database: str, query: str) -> dict[str, object]:
    _tool_major("psql")
    command = [
        "psql", "--no-password", "--no-psqlrc", "--tuples-only", "--no-align",
        "--set=ON_ERROR_STOP=1", *_pg_connection_args(database), "--command", query,
    ]
    output = _run_tool(command, stdout=True).strip()
    try:
        value = json.loads(output)
    except (TypeError, json.JSONDecodeError) as exc:
        raise BackupError("PostgreSQL metadata query returned an invalid result.") from exc
    if not isinstance(value, dict):
        raise BackupError("PostgreSQL metadata query returned an invalid result.")
    return value


def _database_info(database: str, *, require_marker: bool = True) -> dict[str, object]:
    info = _query_json(database, DATABASE_INFO_SQL)
    version_num = info.get("server_version_num")
    if not isinstance(version_num, int) or version_num // 10000 != POSTGRES_MAJOR:
        raise BackupError(f"database server must be PostgreSQL {POSTGRES_MAJOR}.")
    marker = info.get("marker")
    valid_marker = isinstance(marker, str) and re.fullmatch(
        r"build_db:v[23](?: [A-Za-z0-9_.:=/-]+)*", marker
    )
    if require_marker and not valid_marker:
        raise BackupError("database does not have a supported build_db:v2/v3 marker.")
    if marker is not None and not valid_marker:
        raise BackupError("database has an unsupported marker comment.")
    if not isinstance(info.get("collation"), dict):
        raise BackupError("database collation metadata is unavailable.")
    return info


def _empty_state(database: str) -> dict[str, object]:
    return _query_json(database, EMPTY_STATE_SQL)


def _assert_target_empty(info: dict[str, object], database: str) -> None:
    state = _empty_state(database)
    if state.get("marker") is not None:
        raise BackupError("restore target has a database marker; it must remain untouched.")
    for key in ("user_schemas", "relations", "functions", "types", "extensions"):
        if state.get(key) != 0:
            raise BackupError("restore target is not empty; it was left unchanged.")
    if not state.get("is_superuser") and state.get("database_owner") != state.get("current_user"):
        raise BackupError("restore connection must own the empty target database or be a superuser.")
    target_version = info.get("server_version_num")
    if not isinstance(target_version, int) or target_version // 10000 != POSTGRES_MAJOR:
        raise BackupError(f"restore target server must be PostgreSQL {POSTGRES_MAJOR}.")


def _compare_collation(source: object, target: object) -> None:
    if not isinstance(source, dict) or not isinstance(target, dict):
        raise BackupError("source or restore target collation metadata is invalid.")
    keys = ("provider", "locale", "lc_collate", "lc_ctype", "recorded_version", "actual_version")
    if any(source.get(key) != target.get(key) for key in keys):
        raise BackupError("restore target database collation does not match the backup; no data was restored.")


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def _write_tree_archive(root: Path, target: Path) -> dict[str, int]:
    entries = _walk_tree(root)
    files, total_bytes = 0, 0
    try:
        with tarfile.open(target, mode="w", format=tarfile.PAX_FORMAT) as archive:
            for entry in entries:
                relative = str(entry["path"])
                source = root.joinpath(*PurePosixPath(relative).parts)
                is_directory = entry["kind"] == "directory"
                info = tarfile.TarInfo(relative + ("/" if is_directory else ""))
                info.type = tarfile.DIRTYPE if is_directory else tarfile.REGTYPE
                info.mode = int(entry["mode"]) & 0o777
                info.uid, info.gid = int(entry["uid"]), int(entry["gid"])
                info.mtime = int(entry["mtime"])
                if is_directory:
                    info.size = 0
                    archive.addfile(info)
                else:
                    info.size = int(entry["size"])
                    with source.open("rb") as content:
                        archive.addfile(info, content)
                    files += 1
                    total_bytes += info.size
    except (OSError, tarfile.TarError) as exc:
        raise BackupError("could not package a required data root.") from exc
    return {"entries": len(entries), "files": files, "bytes": total_bytes}


def _hash_file(path: Path) -> tuple[str, int]:
    digest, size = hashlib.sha256(), 0
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
                size += len(chunk)
    except OSError as exc:
        raise BackupError("backup payload could not be read for integrity verification.") from exc
    return digest.hexdigest(), size


def _create_private_config_copy(source: Path, destination: Path) -> None:
    data = _check_private_file(source, max_bytes=MAX_CONFIG_BYTES)
    _parse_private_config(data)
    try:
        with destination.open("xb") as target:
            target.write(data)
            target.flush()
            os.fsync(target.fileno())
        os.chmod(destination, 0o600)
    except OSError as exc:
        raise BackupError("could not stage the protected private configuration.") from exc


def _snapshot_environment(config_keys: set[str]) -> dict[str, object]:
    return {
        "non_secret_values": {key: os.environ[key] for key in NON_SECRET_ENV_KEYS if key in os.environ},
        "secret_names_present_in_private_config": sorted(config_keys.intersection(KNOWN_SECRET_KEYS)),
        "required_secret_names": list(REQUIRED_CONFIG_KEYS),
    }


def _backup(
    *,
    database: str,
    release_id: str,
    output_dir: Path,
    roots: dict[str, Path],
    private_config: Path,
    files_quiesced: bool,
    include_private_config: bool,
) -> Path:
    release_id = _safe_release_id(release_id)
    if not files_quiesced:
        raise BackupError("backup requires --files-quiesced after uploads and signing writes are paused.")
    if not include_private_config:
        raise BackupError("backup requires --include-private-config because application recovery needs signing keys.")
    config_bytes = _check_private_file(private_config, max_bytes=MAX_CONFIG_BYTES)
    _, config_keys = _parse_private_config(config_bytes)
    if set(roots) != set(ROOT_NAMES):
        raise BackupError("media, signing, AI, and document storage roots are all required.")
    resolved_roots = {name: _assert_safe_path(roots[name], name) for name in ROOT_NAMES}
    output = _private_output_dir(output_dir)
    config = private_config.resolve(strict=True)
    _assert_paths_do_not_overlap(output, resolved_roots, config)
    for root in resolved_roots.values():
        _walk_tree(root)
    source_db = _database_info(database)
    _tool_major("pg_dump")
    _tool_major("pg_restore")

    timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    final_path = output / f"qlvb-backup-{release_id}-{timestamp}.tar.gz"
    if os.path.lexists(final_path):
        raise BackupError("backup output already exists; it was left untouched.")

    with tempfile.TemporaryDirectory(prefix=".qlvb-backup-", dir=output) as temp_name:
        temp = Path(temp_name)
        if os.name == "posix":
            os.chmod(temp, 0o700)
        dump_path = temp / "database.dump"
        dump_path.touch(mode=0o600)
        _run_tool([
            "pg_dump", "--no-password", "--format=custom", "--file", str(dump_path),
            *_pg_connection_args(database),
        ], output=dump_path)

        root_metadata: dict[str, dict[str, object]] = {}
        for name, root in resolved_roots.items():
            tree_path = temp / f"{name}.tar"
            counts = _write_tree_archive(root, tree_path)
            os.chmod(tree_path, 0o600)
            root_metadata[name] = {"source_path": str(root), **counts}

        config_copy = temp / "backend.env"
        _create_private_config_copy(private_config, config_copy)
        source_db_name = source_db.get("name")
        if not isinstance(source_db_name, str):
            raise BackupError("source database name is unavailable.")
        metadata = {
            "format_version": ARCHIVE_VERSION,
            "created_at_utc": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
            "release_id": release_id,
            "files_quiesced": True,
            "database": source_db,
            "file_roots": root_metadata,
            "private_config": {
                "member": PRIVATE_CONFIG_MEMBER,
                "source_basename": private_config.name,
                "required_keys": list(REQUIRED_CONFIG_KEYS),
                "environment_inventory": _snapshot_environment(config_keys),
            },
        }
        marker_data = {
            "format_version": 1,
            "source_database": source_db_name,
            "marker": source_db["marker"],
        }
        payloads: dict[str, Path] = {
            "metadata.json": temp / "metadata.json",
            "db_marker.json": temp / "db_marker.json",
            "database.dump": dump_path,
            "files/media.tar": temp / "media.tar",
            "files/signing.tar": temp / "signing.tar",
            "files/ai.tar": temp / "ai.tar",
            "files/storage.tar": temp / "storage.tar",
            PRIVATE_CONFIG_MEMBER: config_copy,
        }
        payloads["metadata.json"].write_bytes(_json_bytes(metadata))
        payloads["db_marker.json"].write_bytes(_json_bytes(marker_data))
        for payload in (payloads["metadata.json"], payloads["db_marker.json"]):
            os.chmod(payload, 0o600)
        checksum_manifest: dict[str, dict[str, object]] = {}
        for member, payload in payloads.items():
            digest, size = _hash_file(payload)
            checksum_manifest[member] = {"sha256": digest, "size": size, "mode": 0o600}
        manifest_path = temp / "manifest.json"
        manifest_path.write_bytes(_json_bytes({"format_version": ARCHIVE_VERSION, "files": checksum_manifest}))
        os.chmod(manifest_path, 0o600)

        temporary_archive = temp / "backup.tar.gz"
        with temporary_archive.open("xb") as target:
            os.chmod(temporary_archive, 0o600)
            with tarfile.open(fileobj=target, mode="w:gz", compresslevel=6) as archive:
                for member in (*PAYLOAD_MEMBERS, "manifest.json"):
                    payload = manifest_path if member == "manifest.json" else payloads[member]
                    info = tarfile.TarInfo(member)
                    info.type, info.mode, info.size, info.mtime = tarfile.REGTYPE, 0o600, payload.stat().st_size, 0
                    with payload.open("rb") as content:
                        archive.addfile(info, content)
            target.flush()
            os.fsync(target.fileno())
        try:
            os.link(temporary_archive, final_path)
            os.chmod(final_path, 0o600)
        except OSError as exc:
            raise BackupError("could not publish the protected backup without overwriting another file.") from exc

    # Keep a published archive if verification fails; recovery evidence must not be deleted automatically.
    with _verified_archive(final_path):
        pass
    return final_path


def _read_json_member(path: Path, *, label: str) -> dict[str, object]:
    try:
        if path.stat().st_size > MAX_METADATA_BYTES:
            raise BackupError(f"{label} exceeds the supported size limit.")
        value = json.loads(path.read_text(encoding="utf-8"))
    except BackupError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BackupError(f"{label} is missing or invalid.") from exc
    if not isinstance(value, dict):
        raise BackupError(f"{label} is invalid.")
    return value


def _copy_outer_member(archive: tarfile.TarFile, member: tarfile.TarInfo, destination: Path) -> None:
    source = archive.extractfile(member)
    if source is None:
        raise BackupError("backup archive contains an unreadable payload.")
    try:
        with source, destination.open("xb") as target:
            shutil.copyfileobj(source, target, length=1024 * 1024)
            target.flush()
            os.fsync(target.fileno())
        os.chmod(destination, 0o600)
    except (OSError, tarfile.TarError) as exc:
        raise BackupError("backup payload could not be extracted for verification.") from exc


def _verified_archive(archive_path: Path):
    @contextlib.contextmanager
    def manager():
        try:
            info = archive_path.lstat()
        except OSError as exc:
            raise BackupError("backup archive is missing or unreadable.") from exc
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
            raise BackupError("backup archive must be a regular file, not a symlink.")
        if os.name == "posix" and stat.S_IMODE(info.st_mode) & 0o077:
            raise BackupError("backup archive must grant access only to its owner.")

        with tempfile.TemporaryDirectory(prefix="qlvb-backup-verify-") as temp_name:
            temp = Path(temp_name)
            if os.name == "posix":
                os.chmod(temp, 0o700)
            try:
                with tarfile.open(archive_path, mode="r:gz") as archive:
                    members = archive.getmembers()
                    by_name: dict[str, tarfile.TarInfo] = {}
                    for member in members:
                        if not member.isfile() or member.issym() or member.islnk():
                            raise BackupError("backup archive contains an unsupported entry.")
                        if member.name in by_name:
                            raise BackupError("backup archive contains a duplicate entry.")
                        if member.name not in (*PAYLOAD_MEMBERS, "manifest.json"):
                            raise BackupError("backup archive contains an unexpected entry.")
                        by_name[member.name] = member
                    required_members = [m for m in PAYLOAD_MEMBERS if m not in OPTIONAL_PAYLOAD_MEMBERS]
                    if not {*required_members, "manifest.json"} <= set(by_name):
                        raise BackupError("backup archive is missing a required payload.")
                    payload_members = [m for m in PAYLOAD_MEMBERS if m in by_name]

                    manifest_path = temp / "manifest.json"
                    _copy_outer_member(archive, by_name["manifest.json"], manifest_path)
                    manifest = _read_json_member(manifest_path, label="checksum manifest")
                    files = manifest.get("files")
                    if manifest.get("format_version") != ARCHIVE_VERSION or not isinstance(files, dict):
                        raise BackupError("checksum manifest version or structure is unsupported.")
                    if set(files) != set(payload_members):
                        raise BackupError("checksum manifest does not describe every required payload.")

                    payload_paths: dict[str, Path] = {}
                    for name in payload_members:
                        record = files.get(name)
                        member = by_name[name]
                        if not isinstance(record, dict) or member.mode & 0o077:
                            raise BackupError("backup payload permissions or checksum record are invalid.")
                        path = temp.joinpath(*PurePosixPath(name).parts)
                        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                        _copy_outer_member(archive, member, path)
                        digest, size = _hash_file(path)
                        if (
                            record.get("sha256") != digest or record.get("size") != size
                            or member.size != size or record.get("mode") != 0o600
                        ):
                            raise BackupError("backup payload checksum or size does not match.")
                        payload_paths[name] = path
            except BackupError:
                raise
            except (OSError, tarfile.TarError, EOFError, gzip.BadGzipFile) as exc:
                raise BackupError("backup archive is corrupt or cannot be read.") from exc

            metadata = _read_json_member(payload_paths["metadata.json"], label="backup metadata")
            marker_data = _read_json_member(payload_paths["db_marker.json"], label="database marker sidecar")
            if metadata.get("format_version") != ARCHIVE_VERSION:
                raise BackupError("backup format version is unsupported.")
            database = metadata.get("database")
            if not isinstance(database, dict) or not isinstance(database.get("collation"), dict):
                raise BackupError("backup database metadata is incomplete.")
            marker = marker_data.get("marker")
            if (
                marker_data.get("format_version") != 1 or marker != database.get("marker")
                or not isinstance(marker, str)
                or not re.fullmatch(r"build_db:v[23](?: [A-Za-z0-9_.:=/-]+)*", marker)
            ):
                raise BackupError("database marker sidecar is missing or inconsistent.")

            roots = metadata.get("file_roots")
            present_roots = tuple(name for name in ROOT_NAMES if f"files/{name}.tar" in payload_paths)
            if not isinstance(roots, dict) or set(roots) != set(present_roots):
                raise BackupError("backup is missing a required media, signing, AI, or document storage root.")
            for root_name in present_roots:
                _inspect_file_tree(payload_paths[f"files/{root_name}.tar"], expected=roots[root_name])

            private = metadata.get("private_config")
            if (
                not isinstance(private, dict) or private.get("member") != PRIVATE_CONFIG_MEMBER
                or private.get("required_keys") != list(REQUIRED_CONFIG_KEYS)
            ):
                raise BackupError("backup private configuration metadata is incomplete.")
            config_bytes = _check_private_file(payload_paths[PRIVATE_CONFIG_MEMBER], max_bytes=MAX_CONFIG_BYTES)
            _parse_private_config(config_bytes)
            _tool_major("pg_restore")
            _verify_pg_dump(payload_paths["database.dump"])
            yield {"metadata": metadata, "marker": marker, "payloads": payload_paths, "roots": present_roots}

    return manager()


def _inspect_file_tree(path: Path, *, expected: object) -> list[dict[str, object]]:
    if not isinstance(expected, dict):
        raise BackupError("backup file-root metadata is invalid.")
    entries: list[dict[str, object]] = []
    names: set[str] = set()
    files, total_bytes = 0, 0
    try:
        with tarfile.open(path, mode="r:") as archive:
            for member in archive:
                raw_name = member.name[:-1] if member.isdir() and member.name.endswith("/") else member.name
                relative = _safe_relative_path(raw_name)
                normalized = relative.as_posix()
                if normalized in names:
                    raise BackupError("a file-root archive contains duplicate paths.")
                names.add(normalized)
                if member.isdir():
                    kind, size = "directory", 0
                elif member.isfile():
                    kind, size = "file", member.size
                    stream = archive.extractfile(member)
                    if stream is None:
                        raise BackupError("a file-root archive contains an unreadable file.")
                    with stream:
                        while stream.read(1024 * 1024):
                            pass
                    files += 1
                    total_bytes += size
                else:
                    raise BackupError("file-root archives may contain only regular files and directories.")
                if member.mode & 0o7000:
                    raise BackupError("file-root archive contains unsafe special permission bits.")
                entries.append({"path": normalized, "kind": kind, "size": size})
    except BackupError:
        raise
    except (OSError, tarfile.TarError, EOFError) as exc:
        raise BackupError("a required file-root archive is corrupt.") from exc
    counts = {"entries": len(entries), "files": files, "bytes": total_bytes}
    if any(expected.get(key) != value for key, value in counts.items()):
        raise BackupError("file-root archive counts do not match backup metadata.")
    return entries


def _verify_pg_dump(path: Path) -> None:
    _tool_major("pg_restore")
    result = _run_tool(["pg_restore", "--list", str(path)], stdout=True)
    if not result.strip():
        raise BackupError("PostgreSQL archive list is empty.")


def _quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _quote_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _restore(*, archive_path: Path, database: str, confirm_target_db: str, restore_root: Path) -> Path:
    if not database or confirm_target_db != database:
        raise BackupError("--confirm-target-db must exactly match the explicitly supplied restore database.")
    if os.path.lexists(restore_root):
        raise BackupError("restore root already exists; it was left untouched.")
    if not restore_root.parent.is_dir() or restore_root.parent.is_symlink():
        raise BackupError("restore-root parent must already exist and may not be a symlink.")

    with _verified_archive(archive_path) as verified:
        metadata = verified["metadata"]
        source_db = metadata["database"]
        target_db = _database_info(database, require_marker=False)
        _assert_target_empty(target_db, database)
        _compare_collation(source_db["collation"], target_db["collation"])

        stage = Path(tempfile.mkdtemp(prefix=".qlvb-restore-", dir=restore_root.parent))
        if os.name == "posix":
            os.chmod(stage, 0o700)
        files_root = stage / "files"
        files_root.mkdir(mode=0o700)
        restored_roots = verified["roots"]
        for name in restored_roots:
            (files_root / name).mkdir(mode=0o700)
            _extract_file_tree(verified["payloads"][f"files/{name}.tar"], files_root / name)
        private_config_dir = stage / "private_config"
        private_config_dir.mkdir(mode=0o700)
        shutil.copyfile(verified["payloads"][PRIVATE_CONFIG_MEMBER], private_config_dir / "backend.env")
        os.chmod(private_config_dir / "backend.env", 0o600)
        config_dir = stage / "config"
        config_dir.mkdir(mode=0o700)
        path_map = {ROOT_PATH_VARIABLES[name]: str(restore_root / name) for name in restored_roots}
        recovered_paths = config_dir / "recovered-paths.json"
        recovered_paths.write_bytes(_json_bytes(path_map))
        os.chmod(recovered_paths, 0o600)

        _tool_major("pg_restore")
        _run_tool([
            "pg_restore", "--no-password", "--exit-on-error", "--single-transaction",
            *_pg_connection_args(database), str(verified["payloads"]["database.dump"]),
        ])
        marker = str(verified["marker"])
        comment_sql = f"COMMENT ON DATABASE {_quote_identifier(database)} IS {_quote_literal(marker)}"
        _run_tool([
            "psql", "--no-password", "--no-psqlrc", "--set=ON_ERROR_STOP=1",
            *_pg_connection_args(database), "--command", comment_sql,
        ])
        restored_db = _database_info(database)
        if restored_db.get("marker") != marker:
            raise BackupError(
                f"database restored but marker verification failed; preserve the database and backup. "
                f"File staging remains at {stage}."
            )
        _compare_collation(source_db["collation"], restored_db["collation"])

        if os.path.lexists(restore_root):
            raise BackupError(
                f"database restored but restore root appeared concurrently; file staging remains at {stage}."
            )
        try:
            restore_root.mkdir(mode=0o700)
            os.chmod(restore_root, 0o700)
            for item in restored_roots:
                os.rename(files_root / item, restore_root / item)
            os.rename(private_config_dir, restore_root / "private_config")
            os.rename(config_dir, restore_root / "config")
        except OSError as exc:
            raise BackupError(
                f"database restored but file installation is incomplete; preserve the database and backup. "
                f"File staging remains at {stage}."
            ) from exc
        shutil.rmtree(stage)
        return restore_root


def _extract_file_tree(archive_path: Path, destination: Path) -> None:
    directories: list[tuple[Path, int]] = []
    try:
        with tarfile.open(archive_path, mode="r:") as archive:
            for member in archive:
                raw_name = member.name[:-1] if member.isdir() and member.name.endswith("/") else member.name
                relative = _safe_relative_path(raw_name)
                target = destination.joinpath(*relative.parts)
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True, mode=0o700)
                    directories.append((target, member.mode))
                    continue
                if not member.isfile() or member.mode & 0o7000:
                    raise BackupError("file-root archive contains an unsupported entry.")
                target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                stream = archive.extractfile(member)
                if stream is None:
                    raise BackupError("file-root archive contains an unreadable file.")
                with stream, target.open("xb") as output:
                    shutil.copyfileobj(stream, output, length=1024 * 1024)
                    output.flush()
                    os.fsync(output.fileno())
                os.chmod(target, member.mode & 0o777)
    except BackupError:
        raise
    except (OSError, tarfile.TarError, EOFError) as exc:
        raise BackupError("could not restore a file-root archive safely.") from exc
    for directory, mode in reversed(directories):
        os.chmod(directory, mode & 0o777)


def _extract_database_dump(*, archive_path: Path, output_path: Path) -> Path:
    if os.path.lexists(output_path):
        raise BackupError("database dump output already exists; it was left untouched.")
    if not output_path.name or output_path.name in {".", ".."} or not output_path.parent.is_dir():
        raise BackupError("database dump output must be inside an existing private directory.")

    parent = _private_output_dir(output_path.parent)
    destination = parent / output_path.name
    if os.path.lexists(destination):
        raise BackupError("database dump output already exists; it was left untouched.")

    created = False
    descriptor: int | None = None
    try:
        with _verified_archive(archive_path) as verified:
            source = verified["payloads"]["database.dump"]
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
            descriptor = os.open(destination, flags, 0o600)
            created = True
            with os.fdopen(descriptor, "wb") as target:
                descriptor = None
                with source.open("rb") as content:
                    shutil.copyfileobj(content, target, length=1024 * 1024)
                target.flush()
                os.fsync(target.fileno())
            if os.name == "posix":
                os.chmod(destination, 0o600)
    except BackupError:
        if created:
            destination.unlink(missing_ok=True)
        raise
    except OSError as exc:
        if created:
            destination.unlink(missing_ok=True)
        raise BackupError("verified database dump could not be written safely.") from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)

    return destination.resolve(strict=True)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Protected PostgreSQL and file backup/restore.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    backup = subparsers.add_parser("backup", help="create and verify a new backup archive")
    backup.add_argument("--database", required=True)
    backup.add_argument("--release-id", required=True)
    backup.add_argument("--output-dir", required=True, type=Path)
    backup.add_argument("--media-dir", required=True, type=Path)
    backup.add_argument("--signing-dir", required=True, type=Path)
    backup.add_argument("--ai-dir", required=True, type=Path)
    backup.add_argument("--storage-dir", required=True, type=Path)
    backup.add_argument("--private-config", required=True, type=Path)
    backup.add_argument("--include-private-config", action="store_true")
    backup.add_argument("--files-quiesced", action="store_true")
    backup.add_argument("--json", action="store_true", help="print a machine-readable archive result")

    verify = subparsers.add_parser("verify", help="check checksums, file paths, and PostgreSQL list")
    verify.add_argument("--archive", required=True, type=Path)

    extract = subparsers.add_parser(
        "extract-database-dump", help="verify an archive and extract its PostgreSQL dump to a private file"
    )
    extract.add_argument("--archive", required=True, type=Path)
    extract.add_argument("--output", required=True, type=Path)

    restore = subparsers.add_parser("restore", help="restore into a confirmed, empty PostgreSQL database")
    restore.add_argument("--archive", required=True, type=Path)
    restore.add_argument("--database", required=True)
    restore.add_argument("--confirm-target-db", required=True)
    restore.add_argument("--restore-root", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "backup":
            archive = _backup(
                database=args.database, release_id=args.release_id, output_dir=args.output_dir,
                roots={
                    "media": args.media_dir, "signing": args.signing_dir, "ai": args.ai_dir,
                    "storage": args.storage_dir,
                },
                private_config=args.private_config, files_quiesced=args.files_quiesced,
                include_private_config=args.include_private_config,
            )
            digest, size = _hash_file(archive)
            if args.json:
                print(json.dumps(
                    {"archive": str(archive.resolve(strict=True)), "size_bytes": size, "sha256": digest},
                    sort_keys=True,
                    separators=(",", ":"),
                ))
            else:
                print(f"Verified backup: {archive.name} ({size} bytes, sha256 {digest})")
        elif args.command == "verify":
            with _verified_archive(args.archive) as verified:
                print(
                    f"Verified backup: release {verified['metadata']['release_id']}; "
                    "database marker and file roots are readable."
                )
        elif args.command == "extract-database-dump":
            output = _extract_database_dump(archive_path=args.archive, output_path=args.output)
            print(f"Verified database dump extracted: {output}")
        else:
            restored = _restore(
                archive_path=args.archive, database=args.database,
                confirm_target_db=args.confirm_target_db, restore_root=args.restore_root,
            )
            print(f"Restored database and file roots to {restored}")
        return 0
    except BackupError as exc:
        print(f"backup/restore error: {exc}", file=sys.stderr)
        return 2
    except Exception:
        print(
            "backup/restore error: unexpected failure; preserve the archive and inspect local operation logs.",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
