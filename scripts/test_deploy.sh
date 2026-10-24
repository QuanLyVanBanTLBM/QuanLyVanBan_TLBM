#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
DEPLOY="$ROOT/deploy/deploy.sh"
TEST_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/qlvb-deploy-test.XXXXXX")
MOCK_BIN="$TEST_ROOT/bin"
MOCK_PYTHON="$TEST_ROOT/mock-python"
MOCK_PIP="$TEST_ROOT/mock-pip"
mkdir -p "$MOCK_BIN"
trap 'rm -rf "$TEST_ROOT"' EXIT

fail() { echo "FAIL: $*" >&2; exit 1; }
pass() { echo "PASS: $*"; }
assert_eq() { [ "$1" = "$2" ] || fail "$3 (expected '$2', got '$1')"; }
assert_event_absent() { ! grep -q "^$1$" "$EVENTS" || fail "unexpected event: $1"; }
assert_event_count() {
  local actual
  actual=$(grep -c "^$1$" "$EVENTS" || true)
  assert_eq "$actual" "$2" "event count for $1"
}
assert_backup_release_id() {
  local actual
  actual=$(cat "$CASE_ROOT/backup-release-id")
  assert_eq "$actual" "previous" "backup release id in $(basename "$CASE_ROOT")"
}
assert_event_before() {
  local first second
  first=$(grep -n "^$1$" "$EVENTS" | head -1 | cut -d: -f1 || true)
  second=$(grep -n "^$2$" "$EVENTS" | head -1 | cut -d: -f1 || true)
  if [[ -z "$first" || -z "$second" || "$first" -ge "$second" ]]; then
    cat "$CASE_ROOT/output.log" >&2
    cat "$EVENTS" >&2
    fail "event '$1' must happen before '$2' in $(basename "$CASE_ROOT")"
  fi
}
assert_no_live_database_mutation() {
  assert_event_absent adopt
  assert_event_absent live-sync
  assert_event_absent seed
}

cat > "$MOCK_PYTHON" <<'MOCK'
#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == "-c" ]]; then
  response=$(cat)
  if [[ "${2:-}" == *'re.fullmatch'* ]]; then
    archive=$(sed -n 's/.*"archive":"\([^"]*\)".*/\1/p' <<< "$response")
    sha=$(sed -n 's/.*"sha256":"\([^"]*\)".*/\1/p' <<< "$response")
    size=$(sed -n 's/.*"size_bytes":\([0-9][0-9]*\).*/\1/p' <<< "$response")
    [[ -n "$archive" && -n "$sha" && -n "$size" ]] || exit 1
    printf '%s\n%s\n%s\n' "$archive" "$sha" "$size"
  elif [[ "$response" == *'"status":"ready"'* ]]; then
    sed -n 's/.*"release":"\([^"]*\)".*/\1/p' <<< "$response"
  fi
  exit 0
fi
if [[ "${1:-}" == "manage.py" ]]; then
  case "${2:-}" in
    check|collectstatic) exit 0 ;;
    migrate)
      if [[ "${3:-}" == "--plan" ]]; then
        echo "Planned operations:"
        if [[ "${MOCK_PENDING:-0}" == "1" ]]; then
          echo "accounts.0007_test_migration"
        else
          echo "  No planned migration operations."
        fi
      fi
      exit 0
      ;;
  esac
fi
if [[ "${1##*/}" == "backup_restore.py" ]]; then
  command=${2:-}
  if [[ "$command" == "backup" ]]; then
    echo backup >> "$EVENTS"
    [[ "$(cat "$SERVICE_STATE")" == "inactive" ]] || exit 60
    [[ "${MOCK_BACKUP_FAIL:-0}" == "0" ]] || exit 61
    release_id=""
    storage_dir=""
    while (($#)); do
      case "$1" in
        --release-id) release_id=$2; shift 2 ;;
        --storage-dir) storage_dir=$2; shift 2 ;;
        *) shift ;;
      esac
    done
    [[ -n "$release_id" ]] || exit 65
    [[ -n "$storage_dir" && "$storage_dir" == "$CASE_ROOT/shared/storage" ]] || exit 66
    printf '%s\n' "$release_id" > "$CASE_ROOT/backup-release-id"
    backup_dir="$QLVB_BASE/backups/full"
    mkdir -p "$backup_dir"
    archive="$backup_dir/qlvb-backup-$release_id-20261020T000000Z.tar.gz"
    printf 'mock verified full backup\n' > "$archive"
    sha=$(sha256sum "$archive" | awk '{print $1}')
    size=$(stat -c '%s' "$archive")
    if [[ "${MOCK_BACKUP_BAD_JSON:-0}" == "1" ]]; then
      echo 'not json'
    else
      printf '{"archive":"%s","size_bytes":%s,"sha256":"%s"}\n' "$archive" "$size" "$sha"
    fi
    exit 0
  elif [[ "$command" == "extract-database-dump" ]]; then
    echo extract >> "$EVENTS"
    [[ "$(cat "$SERVICE_STATE")" == "inactive" ]] || exit 62
    [[ "${MOCK_EXTRACT_FAIL:-0}" == "0" ]] || exit 63
    output=""
    while (($#)); do
      if [[ "$1" == "--output" ]]; then output=$2; shift 2; else shift; fi
    done
    [[ -n "$output" ]] || exit 64
    printf 'mock verified PostgreSQL dump\n' > "$output"
    chmod 600 "$output"
    exit 0
  fi
fi
if [[ "${1##*/}" == "build_db.py" ]]; then
  if [[ " $* " == *" --preflight-copy "* ]]; then
    echo preflight >> "$EVENTS"
    [[ "${MOCK_PREFLIGHT_FAIL:-0}" == "0" ]] || exit 41
  elif [[ " $* " == *" --preflight-verified-ddl-sha256 "* ]]; then
    echo live-sync >> "$EVENTS"
    if [[ "${MOCK_MIGRATION_FAIL:-0}" == "1" ]]; then
      [[ "${MOCK_NON_ATOMIC:-0}" == "0" ]] || touch "$CASE_ROOT/partial_write"
      exit 42
    fi
  elif [[ " $* " == *" --adopt "* ]]; then
    if [[ "${DB_NAME:-}" != "qlvb_test" ]]; then
      echo preflight-adopt >> "$EVENTS"
    elif [[ "${MOCK_PENDING:-0}" == "0" && "${MOCK_MARK_VERSION:-3}" == "3" ]]; then
      echo adopt-readonly >> "$EVENTS"
    else
      echo adopt >> "$EVENTS"
    fi
    if [[ "${MOCK_ADOPT_FAIL:-0}" == "1" && "${DB_NAME:-}" == "qlvb_test" ]]; then
      exit 43
    fi
  elif [[ " $* " == *" --seed "* ]]; then
    echo seed >> "$EVENTS"
    [[ "${MOCK_SEED_FAIL:-0}" == "0" ]] || exit 44
  elif [[ " $* " == *" --compare-schema-database "* ]]; then
    echo compare >> "$EVENTS"
  fi
  exit 0
fi
exit 0
MOCK

cat > "$MOCK_PIP" <<'MOCK'
#!/usr/bin/env bash
exit 0
MOCK

cat > "$MOCK_BIN/python3" <<'MOCK'
#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == "-m" && "${2:-}" == "venv" ]]; then
  mkdir -p "$3/bin"
  cp "$MOCK_PYTHON" "$3/bin/python"
  cp "$MOCK_PIP" "$3/bin/pip"
  chmod +x "$3/bin/python" "$3/bin/pip"
fi
MOCK

cat > "$MOCK_BIN/tar" <<'MOCK'
#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == "-xzf" ]]; then
  dest=${4:?missing extraction directory}
  mkdir -p "$dest/backend" "$dest/scripts" "$dest/docs/common/database" "$dest/.github/scripts"
  touch "$dest/backend/manage.py" "$dest/backend/requirements-linux-py312.lock" "$dest/scripts/build_db.py"
      [[ "${MOCK_OMIT_BACKUP_TOOL:-0}" == "1" ]] || touch "$dest/scripts/backup_restore.py"
  echo "SELECT 1;" > "$dest/docs/common/database/release_DDL.sql"
  touch "$dest/docs/common/database/schema_drift_baseline.txt" "$dest/.github/scripts/compare_schema_ddl.py"
fi
MOCK

cat > "$MOCK_BIN/psql" <<'MOCK'
#!/usr/bin/env bash
set -euo pipefail
case "$*" in
  *datlocprovider*) echo 'i|vi-VN' ;;
  *shobj_description*)
    hash=$(sha256sum "$RELEASE_DIR/docs/common/database/release_DDL.sql" | awk '{print $1}')
    zeros=$(printf '%064d' 0)
    if [[ "${MOCK_MARK_VERSION:-3}" == "2" ]]; then
      echo "build_db:v2 ddl_sha256=$hash seed=1 collation=icu:vi-VN"
    else
      echo "build_db:v3 ddl_sha256=$hash seed=1 collation=icu:vi-VN schema_sha256=$zeros migrations_sha256=$zeros"
    fi
    ;;
esac
MOCK

cat > "$MOCK_BIN/pg_restore" <<'MOCK'
#!/usr/bin/env bash
set -euo pipefail
if [[ " $* " == *" -l "* ]]; then echo 'TABLE public fixture'; fi
MOCK

cat > "$MOCK_BIN/readlink" <<'MOCK'
#!/usr/bin/env bash
set -euo pipefail
if [[ "${2:-}" == "$QLVB_BASE/current" ]]; then
  cat "$CURRENT_FILE"
elif [[ "${1:-}" == "-f" ]]; then
  /usr/bin/readlink -f "$2"
else
  cat "$CURRENT_FILE"
fi
MOCK

cat > "$MOCK_BIN/ln" <<'MOCK'
#!/usr/bin/env bash
set -euo pipefail
target=${2:?missing symlink target}
printf '%s\n' "$target" > "$CURRENT_FILE"
echo "switch:$target" >> "$EVENTS"
MOCK

cat > "$MOCK_BIN/systemctl" <<'MOCK'
#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == "is-active" ]]; then
  [[ "${MOCK_SYSTEMCTL_QUERY_ERROR:-0}" == "0" ]] || exit 4
  [[ "$(cat "$SERVICE_STATE")" == "active" ]] && exit 0 || exit 3
fi
exit 0
MOCK

cat > "$MOCK_BIN/sudo" <<'MOCK'
#!/usr/bin/env bash
set -euo pipefail
args=("$@")
i=0
[[ "${args[$i]:-}" == "-n" ]] && i=$((i + 1))
if [[ "${args[$i]:-}" == "-u" ]]; then i=$((i + 2)); fi
command=${args[$i]:-}
action=${args[$((i + 1))]:-}
if [[ "$command" == "/usr/bin/systemctl" ]]; then
  echo "$action" >> "$EVENTS"
  case "$action" in
    stop)
      [[ "${MOCK_STOP_FAIL:-0}" == "0" ]] || exit 45
      [[ "${MOCK_STOP_LEAVES_ACTIVE:-0}" == "1" ]] || echo inactive > "$SERVICE_STATE"
      ;;
    restart)
      count=$(grep -c '^restart$' "$EVENTS" || true)
      if [[ "${MOCK_RESTART_FAIL:-0}" == "1" || ( "${MOCK_RESTART_FAIL_ONCE:-0}" == "1" && "$count" == "1" ) ]]; then
        echo inactive > "$SERVICE_STATE"
        exit 46
      fi
      echo active > "$SERVICE_STATE"
      ;;
  esac
  if [[ "$action" == "reload" ]]; then
    [[ "${MOCK_NGINX_RELOAD_FAIL:-0}" == "0" ]] || exit 48
  fi
elif [[ "$command" == "/usr/bin/install" ]]; then
  echo nginx-install >> "$EVENTS"
  [[ "${args[*]:$((i + 1))}" == "-m 644 $HOME/deploy/qlvb-frontend.nginx $QLVB_NGINX_SITE" ]] || exit 49
  cp "$HOME/deploy/qlvb-frontend.nginx" "$QLVB_NGINX_SITE"
elif [[ "$command" == "/usr/sbin/nginx" ]]; then
  echo nginx-test >> "$EVENTS"
  [[ "$action" == "-t" ]] || exit 50
  ! grep -q MOCK_INVALID "$QLVB_NGINX_SITE" || exit 47
elif [[ "$command" == "/usr/bin/dropdb" ]]; then
  echo dropdb >> "$EVENTS"
elif [[ "$command" == "/usr/bin/createdb" ]]; then
  echo createdb >> "$EVENTS"
fi
MOCK

cat > "$MOCK_BIN/curl" <<'MOCK'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n%s' "$MOCK_HEALTH_BODY" "$MOCK_HEALTH_CODE"
MOCK

cat > "$MOCK_BIN/sleep" <<'MOCK'
#!/usr/bin/env bash
exit 0
MOCK

cat > "$MOCK_BIN/flock" <<'MOCK'
#!/usr/bin/env bash
exit 0
MOCK

chmod +x "$MOCK_PYTHON" "$MOCK_PIP" "$MOCK_BIN"/*

make_case() {
  local label=$1 state=${2:-active}
  CASE_ROOT="$TEST_ROOT/$label"
  NAME="release-$label"
  QLVB_BASE="$CASE_ROOT/base"
  HOME="$CASE_ROOT/home"
  EVENTS="$CASE_ROOT/events"
  SERVICE_STATE="$CASE_ROOT/service-state"
  CURRENT_FILE="$CASE_ROOT/current-release"
  RELEASE_DIR="$QLVB_BASE/releases/$NAME"
  QLVB_ENVF="$CASE_ROOT/backend.env"
  mkdir -p "$QLVB_BASE/releases/previous" "$QLVB_BASE/backups" "$QLVB_BASE/tools" "$HOME/deploy"
  mkdir -p "$CASE_ROOT/shared/media" "$CASE_ROOT/shared/signing" "$CASE_ROOT/shared/ai" "$CASE_ROOT/shared/storage"
  : > "$HOME/deploy/qlvb-$NAME.tar.gz"
  QLVB_NGINX_SITE="$CASE_ROOT/nginx-site"
  echo 'server { listen 8088; }' > "$QLVB_NGINX_SITE"
  echo 'server { listen 8088; server_name new; }' > "$HOME/deploy/qlvb-frontend.nginx"
  echo "$QLVB_BASE/releases/previous" > "$CURRENT_FILE"
  echo "$state" > "$SERVICE_STATE"
  : > "$EVENTS"
  cat > "$QLVB_ENVF" <<'ENV'
DB_NAME=qlvb_test
DB_USER=deploy_test
DB_PASSWORD=test-only
DJANGO_SECRET_KEY=test-only
SIGNING_PIN_SECRET=synthetic-test-only
DJANGO_MEDIA_ROOT=$CASE_ROOT/shared/media
SIGNING_DOCUMENT_ROOT=$CASE_ROOT/shared/signing
AI_DATA_DIR=$CASE_ROOT/shared/ai
DOCUMENT_STORAGE_ROOT=$CASE_ROOT/shared/storage
ADMIN_PASSWORD=test-only
ENV
  export CASE_ROOT NAME HOME EVENTS SERVICE_STATE CURRENT_FILE RELEASE_DIR QLVB_BASE QLVB_ENVF QLVB_NGINX_SITE
  export MOCK_BIN MOCK_PYTHON MOCK_PIP MOCK_NGINX_RELOAD_FAIL=0
  export MOCK_PENDING=0 MOCK_PREFLIGHT_FAIL=0 MOCK_MIGRATION_FAIL=0 MOCK_NON_ATOMIC=0
  export MOCK_ADOPT_FAIL=0 MOCK_SEED_FAIL=0 MOCK_STOP_FAIL=0 MOCK_STOP_LEAVES_ACTIVE=0 MOCK_RESTART_FAIL=0 MOCK_RESTART_FAIL_ONCE=0 MOCK_SYSTEMCTL_QUERY_ERROR=0
  export MOCK_BACKUP_FAIL=0 MOCK_BACKUP_BAD_JSON=0 MOCK_EXTRACT_FAIL=0 MOCK_OMIT_BACKUP_TOOL=0
  export MOCK_MARK_VERSION=3
  export MOCK_HEALTH_CODE=200 MOCK_HEALTH_BODY="{\"status\":\"ready\",\"release\":\"$NAME\"}"
}

run_deploy() {
  local mode=${1:-sync}
  ( export PATH="$MOCK_BIN:$PATH" DB_MODE="$mode"; cd "$CASE_ROOT"; bash "$DEPLOY" "$NAME" ) > "$CASE_ROOT/output.log" 2>&1
}

expect_failure() {
  if run_deploy "${1:-sync}"; then fail "deployment unexpectedly passed in $CASE_ROOT"; fi
}

expect_state() {
  local current state
  current=$(cat "$CURRENT_FILE")
  state=$(cat "$SERVICE_STATE")
  if [ "$current" != "$1" ] || [ "$state" != "$2" ]; then
    echo "--- deployment log: $(basename "$CASE_ROOT") ---" >&2
    cat "$CASE_ROOT/output.log" >&2
    echo "--- events ---" >&2
    cat "$EVENTS" >&2
  fi
  assert_eq "$current" "$1" "current release in $(basename "$CASE_ROOT")"
  assert_eq "$state" "$2" "service state in $(basename "$CASE_ROOT")"
}

make_case missing-backup-tool
export MOCK_OMIT_BACKUP_TOOL=1
expect_failure
expect_state "$QLVB_BASE/releases/previous" active
assert_event_absent stop
assert_event_absent backup
pass "release artifact missing the backup CLI fails before service stop"

make_case missing-tarball
rm "$HOME/deploy/qlvb-$NAME.tar.gz"
expect_failure
expect_state "$QLVB_BASE/releases/previous" active
assert_event_absent stop
assert_event_absent restart
assert_event_absent backup
pass "missing tarball leaves the initially active service untouched"

make_case existing-release
mkdir -p "$RELEASE_DIR"
expect_failure
expect_state "$QLVB_BASE/releases/previous" active
assert_event_absent stop
assert_event_absent restart
assert_event_absent backup
test -d "$RELEASE_DIR" || fail "existing release was removed during early failure"
grep -q 'khong phai ban dang chay' "$CASE_ROOT/output.log" || fail "non-current existing release reason was not logged"
pass "existing target release leaves the initially active service untouched"

make_case already-running-release
mkdir -p "$RELEASE_DIR"
echo "$RELEASE_DIR" > "$CURRENT_FILE"
if ! run_deploy; then
  cat "$CASE_ROOT/output.log" >&2
  cat "$EVENTS" >&2
  fail "redeploy of the running release failed instead of skipping"
fi
expect_state "$RELEASE_DIR" active
assert_eq "$(cat "$EVENTS")" "" "events for already-running release"
test -d "$RELEASE_DIR" || fail "running release was removed during skip"
grep -q 'bo qua deploy' "$CASE_ROOT/output.log" || fail "skip reason was not logged"
pass "redeploy of the running release with an active service is a no-op success"

make_case running-release-service-inactive inactive
mkdir -p "$RELEASE_DIR"
echo "$RELEASE_DIR" > "$CURRENT_FILE"
expect_failure
expect_state "$RELEASE_DIR" inactive
assert_eq "$(cat "$EVENTS")" "" "events for running release with inactive service"
test -d "$RELEASE_DIR" || fail "running release was removed during early failure"
pass "redeploy of the running release with an inactive service fails without changes"

make_case running-release-rebuild
mkdir -p "$RELEASE_DIR"
echo "$RELEASE_DIR" > "$CURRENT_FILE"
expect_failure rebuild
expect_state "$RELEASE_DIR" active
assert_eq "$(cat "$EVENTS")" "" "events for rebuild of running release"
test -d "$RELEASE_DIR" || fail "running release was removed during early failure"
pass "rebuild requested for the running release is rejected instead of skipped"

make_case service-query-error
export MOCK_SYSTEMCTL_QUERY_ERROR=1
expect_failure
expect_state "$QLVB_BASE/releases/previous" active
assert_event_absent stop
assert_event_absent restart
assert_event_absent backup
pass "unexpected service-state query failure aborts without changing service state"

make_case invalid-release-name
if ( export PATH="$MOCK_BIN:$PATH"; cd "$CASE_ROOT"; bash "$DEPLOY" "_invalid" ); then
  fail "release name beginning with punctuation was unexpectedly accepted"
fi
expect_state "$QLVB_BASE/releases/previous" active
assert_event_absent stop
assert_event_absent backup
pass "release name outside the backup ID contract fails before service stop"

make_case missing-media-root
sed -i '/^DJANGO_MEDIA_ROOT=/d' "$QLVB_ENVF"
expect_failure
expect_state "$QLVB_BASE/releases/previous" active
assert_event_absent stop
assert_event_absent backup
pass "missing explicit media root fails before service stop"

make_case relative-media-root
sed -i 's#^DJANGO_MEDIA_ROOT=.*#DJANGO_MEDIA_ROOT=relative/media#' "$QLVB_ENVF"
expect_failure
expect_state "$QLVB_BASE/releases/previous" active
assert_event_absent stop
assert_event_absent backup
pass "relative data root fails before service stop"

make_case release-local-media-root
sed -i "s#^DJANGO_MEDIA_ROOT=.*#DJANGO_MEDIA_ROOT=$QLVB_BASE/releases/previous#" "$QLVB_ENVF"
expect_failure
expect_state "$QLVB_BASE/releases/previous" active
assert_event_absent stop
assert_event_absent backup
pass "release-local data root fails before service stop"

make_case missing-storage-root
sed -i '/^DOCUMENT_STORAGE_ROOT=/d' "$QLVB_ENVF"
expect_failure
expect_state "$QLVB_BASE/releases/previous" active
assert_event_absent stop
assert_event_absent backup
pass "missing document storage root fails before service stop"

make_case relative-storage-root
sed -i 's#^DOCUMENT_STORAGE_ROOT=.*#DOCUMENT_STORAGE_ROOT=relative/storage#' "$QLVB_ENVF"
expect_failure
expect_state "$QLVB_BASE/releases/previous" active
assert_event_absent stop
assert_event_absent backup
pass "relative document storage root fails before service stop"

make_case release-local-storage-root
sed -i "s#^DOCUMENT_STORAGE_ROOT=.*#DOCUMENT_STORAGE_ROOT=$QLVB_BASE/releases/previous#" "$QLVB_ENVF"
expect_failure
expect_state "$QLVB_BASE/releases/previous" active
assert_event_absent stop
assert_event_absent backup
pass "release-local document storage root fails before service stop"

make_case backup-failure
export MOCK_BACKUP_FAIL=1
expect_failure
expect_state "$QLVB_BASE/releases/previous" active
assert_event_count stop 1
assert_event_count backup 1
assert_event_absent extract
assert_event_absent dropdb
assert_no_live_database_mutation
assert_event_count restart 1
pass "backup failure restores an initially active service before any DB mutation"

make_case invalid-backup-json
export MOCK_BACKUP_BAD_JSON=1
expect_failure
expect_state "$QLVB_BASE/releases/previous" active
assert_event_count stop 1
assert_event_absent extract
assert_event_absent dropdb
assert_no_live_database_mutation
assert_event_count restart 1
pass "invalid backup metadata fails closed and restores the prior service"

make_case extraction-failure
export MOCK_EXTRACT_FAIL=1
expect_failure
expect_state "$QLVB_BASE/releases/previous" active
assert_event_count stop 1
assert_event_before backup extract
assert_event_absent dropdb
assert_no_live_database_mutation
assert_event_count restart 1
test -s "$QLVB_BASE/backups/full/qlvb-backup-previous-20261020T000000Z.tar.gz" || fail "verified archive was not retained"
assert_backup_release_id
grep -q 'Full backup SHA-256:' "$CASE_ROOT/output.log" || fail "archive hash was not logged"
if find "$QLVB_BASE/backups" -maxdepth 1 -type d -name '.qlvb-deploy-dump.*' | grep -q .; then fail "temporary dump directory was not cleaned"; fi
pass "extraction failure retains the archive and restores prior state without DB mutation"

make_case preflight-failure
export MOCK_PENDING=1 MOCK_PREFLIGHT_FAIL=1
expect_failure
expect_state "$QLVB_BASE/releases/previous" active
assert_event_count stop 1
assert_event_before stop backup
assert_event_before backup extract
assert_event_absent live-sync
test ! -e "$RELEASE_DIR" || fail "preflight failure left an unused release"
assert_event_count restart 1
pass "preflight failure restores the active release after full backup capture"

make_case stop-failure
export MOCK_PENDING=1 MOCK_STOP_FAIL=1
expect_failure
expect_state "$QLVB_BASE/releases/previous" active
assert_event_absent live-sync
assert_event_absent backup
assert_event_count stop 1
pass "service stop failure aborts before backup or database work"

make_case stop-not-effective
export MOCK_STOP_LEAVES_ACTIVE=1
expect_failure
expect_state "$QLVB_BASE/releases/previous" active
assert_event_count stop 1
assert_event_absent backup
assert_no_live_database_mutation
pass "successful stop command that leaves service active is rejected before backup"

make_case adopt-failure-after-stop
export MOCK_PENDING=1 MOCK_MARK_VERSION=2 MOCK_ADOPT_FAIL=1
expect_failure
expect_state "$QLVB_BASE/releases/previous" inactive
assert_event_absent live-sync
assert_event_absent restart
pass "partial legacy adoption remains fail-closed"

make_case legacy-adopt-without-migrations
export MOCK_MARK_VERSION=2 MOCK_ADOPT_FAIL=1
expect_failure
expect_state "$QLVB_BASE/releases/previous" inactive
assert_event_absent live-sync
assert_event_absent restart
pass "legacy adoption stops the service and fails closed even with an empty migration plan"

make_case partial-migration-failure
export MOCK_PENDING=1 MOCK_MIGRATION_FAIL=1 MOCK_NON_ATOMIC=1
expect_failure
expect_state "$QLVB_BASE/releases/previous" inactive
test -f "$CASE_ROOT/partial_write" || fail "partial migration marker was not written"
test -s "$QLVB_BASE/backups/full/qlvb-backup-previous-20261020T000000Z.tar.gz" || fail "pre-deploy full backup was not retained"
assert_backup_release_id
grep -q 'Full backup SHA-256:' "$CASE_ROOT/output.log" || fail "archive hash was not logged"
assert_event_absent restart
test -d "$RELEASE_DIR" || fail "candidate release was not retained for recovery"
pass "partial migration failure keeps the service stopped and retains recovery evidence"

make_case restart-failure-after-migration
export MOCK_PENDING=1 MOCK_RESTART_FAIL=1
expect_failure
expect_state "$RELEASE_DIR" inactive
assert_event_count restart 1
pass "restart failure after a migration does not switch back to old code"

make_case wrong-release-after-migration
export MOCK_PENDING=1 MOCK_HEALTH_BODY='{"status":"ready","release":"old-release"}'
expect_failure
expect_state "$RELEASE_DIR" inactive
assert_event_count restart 1
assert_event_count stop 2
pass "wrong loaded release after migration fails closed"

make_case restart-failure-without-migration
export MOCK_RESTART_FAIL_ONCE=1
expect_failure
expect_state "$QLVB_BASE/releases/previous" active
assert_event_count restart 2
assert_event_count stop 1
pass "restart failure without DB changes restores the prior active release"

make_case wrong-release-without-migration
export MOCK_HEALTH_BODY='{"status":"ready","release":"old-release"}'
expect_failure
expect_state "$QLVB_BASE/releases/previous" active
assert_event_count restart 2
assert_event_count stop 1
pass "wrong process identity without DB changes restarts the restored prior release"

make_case database-down-readiness
export MOCK_HEALTH_CODE=503 MOCK_HEALTH_BODY='{"status":"not_ready"}'
expect_failure
expect_state "$QLVB_BASE/releases/previous" active
assert_event_count restart 2
assert_event_count stop 1
pass "database-unready probe rolls back only when no DB mutation was attempted"

make_case prior-service-inactive inactive
export MOCK_RESTART_FAIL=1
expect_failure
expect_state "$QLVB_BASE/releases/previous" inactive
assert_event_count restart 1
assert_event_count stop 1
pass "failure does not start a service that was inactive before deploy"

make_case ready-no-migration
if ! run_deploy; then
  cat "$CASE_ROOT/output.log" >&2
  cat "$EVENTS" >&2
  fail "no-pending-migration deployment failed unexpectedly"
fi
expect_state "$RELEASE_DIR" active
assert_event_count stop 1
assert_event_count restart 1
assert_event_before stop backup
assert_event_before backup extract
assert_event_before extract preflight
assert_event_absent live-sync
assert_event_absent adopt
assert_event_before backup restart
assert_backup_release_id
grep -q 'Full backup archive:' "$CASE_ROOT/output.log" || fail "archive path was not logged"
grep -q 'Full backup SHA-256:' "$CASE_ROOT/output.log" || fail "archive hash was not logged"
assert_event_count nginx-install 1
assert_event_count nginx-test 1
assert_event_count reload 1
assert_event_before reload stop
cmp -s "$QLVB_NGINX_SITE" "$HOME/deploy/qlvb-frontend.nginx" || fail "changed nginx config was not installed"
pass "no-pending-migration deployment verifies a full backup before read-only preflight"

make_case missing-nginx-config
rm "$HOME/deploy/qlvb-frontend.nginx"
expect_failure
expect_state "$QLVB_BASE/releases/previous" active
assert_event_absent nginx-install
assert_event_absent stop
assert_event_absent backup
pass "missing nginx config fails before nginx or service changes"

make_case nginx-invalid-restored
echo 'server { MOCK_INVALID; }' > "$HOME/deploy/qlvb-frontend.nginx"
expect_failure
expect_state "$QLVB_BASE/releases/previous" active
assert_eq "$(cat "$QLVB_NGINX_SITE")" 'server { listen 8088; }' "restored nginx site"
assert_eq "$(cat "$HOME/deploy/qlvb-frontend.nginx")" 'server { listen 8088; }' "nginx install source after restore"
assert_event_count nginx-install 2
assert_event_count nginx-test 2
assert_event_absent reload
assert_event_absent stop
assert_event_absent backup
assert_no_live_database_mutation
test ! -e "$RELEASE_DIR" || fail "nginx failure left an unused release"
pass "invalid nginx config is restored before service stop or DB work"

make_case nginx-reload-failure
export MOCK_NGINX_RELOAD_FAIL=1
expect_failure
expect_state "$QLVB_BASE/releases/previous" active
assert_eq "$(cat "$QLVB_NGINX_SITE")" 'server { listen 8088; }' "restored nginx site after reload failure"
assert_event_count reload 1
assert_event_count nginx-install 2
assert_event_absent stop
assert_event_absent backup
pass "nginx reload failure restores the previous config before service stop"

make_case nginx-unchanged
cp "$QLVB_NGINX_SITE" "$HOME/deploy/qlvb-frontend.nginx"
if ! run_deploy; then
  cat "$CASE_ROOT/output.log" >&2
  cat "$EVENTS" >&2
  fail "deployment with unchanged nginx config failed unexpectedly"
fi
expect_state "$RELEASE_DIR" active
assert_event_absent nginx-install
assert_event_absent nginx-test
assert_event_absent reload
pass "unchanged nginx config is not reinstalled or reloaded"

make_case rebuild-failure
export MOCK_SEED_FAIL=1
expect_failure rebuild
expect_state "$QLVB_BASE/releases/previous" inactive
test -s "$QLVB_BASE/backups/full/qlvb-backup-previous-20261020T000000Z.tar.gz" || fail "rebuild failure lost the pre-deploy full backup"
assert_backup_release_id
grep -q 'Full backup SHA-256:' "$CASE_ROOT/output.log" || fail "archive hash was not logged"
assert_event_before stop backup
assert_event_before backup extract
assert_event_absent restart
pass "failed rebuild leaves the service down without automatic restore or code rollback"
