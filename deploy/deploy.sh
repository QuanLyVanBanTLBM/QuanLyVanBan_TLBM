#!/usr/bin/env bash
# Deploy backend QLVB:  deploy.sh <ten-release>  (nguon duy nhat: deploy/deploy.sh trong repo, moi lan deploy duoc day len ~/deploy/ cung tarball)
# Can co ~/deploy/qlvb-<ten-release>.tar.gz (thu muc goc chua backend/, scripts/, docs/common/database/ va comparator schema). Tao tren may dev:
#   git -c core.autocrlf=false archive --format=tar.gz -o qlvb-<sha>.tar.gz <sha> backend scripts docs/common/database .github/scripts/compare_schema_ddl.py
#   scp -P 2150 qlvb-<sha>.tar.gz <user>@<host>:deploy/
# Can co ~/deploy/qlvb-frontend.nginx (ban sao deploy/nginx/qlvb-frontend.conf cung commit).
# Thu tu: giai nen -> venv -> check -> nginx -> dung service -> full backup/preflight -> DB -> doi symlink -> restart -> readiness.
#         nginx cai truoc khi dung service: loi nginx chi khoi phuc cau hinh cu, chua cham service/DB/release.
#         Service dung ca deploy, ke ca sync khong co migration cho; loi truoc DB change co the phuc hoi release cu.
#         Sau DB mutation attempt, deploy fail-closed va giu service dung.
#         Chay lai cung release (push trung, re-run): neu release do dang la current, service active va DB_MODE=sync
#         thi bo qua, exit 0; release ton tai o moi trang thai khac van tu choi deploy.
# DB_MODE (bien moi truong, mac dinh sync):
#   sync     xac minh marker/history; thu migration tren ban khoi phuc va so schema voi release DDL/baseline,
#            sau do chay migration that tren DB hien tai. Khong dung lai DB.
#   rebuild  xoa va dung lai DB tu release_DDL.sql (`build_db.py --seed`). Chi chon bang thao tac reset ro rang.
# Bien tuy chon cho test: QLVB_BASE, QLVB_ENVF, QLVB_NGINX_SITE.
set -euo pipefail
umask 022

NAME=${1:?"Dung: deploy.sh <ten-release>"}
[[ $NAME =~ ^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$ ]] || { echo "Ten release khong hop le: $NAME"; exit 2; }
DB_MODE=${DB_MODE:-sync}
[[ $DB_MODE == sync || $DB_MODE == rebuild ]] || { echo "DB_MODE khong hop le: $DB_MODE (sync|rebuild)"; exit 2; }

BASE=${QLVB_BASE:-/srv/qlvb}
REL=$BASE/releases/$NAME
TAR=$HOME/deploy/qlvb-$NAME.tar.gz
ENVF=${QLVB_ENVF:-/etc/qlvb/backend.env}
SERVICE=qlvb-backend
PORT=8001
KEEP=5
LOG=$BASE/deploy.log
# Ba lenh sudo nginx phai khop dung rule sudoers (install tu ~/deploy/qlvb-frontend.nginx, nginx -t, reload).
NGINX_NEW=$HOME/deploy/qlvb-frontend.nginx
NGINX_PREV=$HOME/deploy/qlvb-frontend.nginx.prev
NGINX_SITE=${QLVB_NGINX_SITE:-/etc/nginx/sites-available/qlvb-frontend}

exec > >(exec 9>&-; exec tee -a "$LOG") 2>&1
step() { echo; echo "[$(date -u +%H:%M:%S)] $*"; }

exec 9>"$BASE/.deploy.lock"
flock -n 9 || { echo "Dang co deploy khac chay."; exit 1; }

CREATED=0; SWITCHED=0; TMPDB=""; TMPDDLDB=""; DUMP_DIR=""; DUMP=""; PREV=""; MARKFILE=""
BACKUP_TOOL=""; BACKUP_ARCHIVE=""; BACKUP_SHA256=""; BACKUP_SIZE=""
DB_REBUILT=0; DB_CHANGE_POSSIBLE=0; SERVICE_WAS_ACTIVE=0; SERVICE_STATE_CAPTURED=0; HAS_PENDING_MIGRATIONS=0; LIVE_SYNC_NOOP=0
cleanup() {
  rc=$?
  if [ -n "$TMPDB" ]; then sudo -n -u postgres /usr/bin/dropdb --if-exists "$TMPDB" >/dev/null 2>&1 || true; fi
  if [ -n "$TMPDDLDB" ]; then sudo -n -u postgres /usr/bin/dropdb --if-exists "$TMPDDLDB" >/dev/null 2>&1 || true; fi
  if [ -n "$DUMP_DIR" ] && [[ "$DUMP_DIR" == "$BASE/backups"/.qlvb-deploy-dump.* ]]; then
    rm -rf -- "$DUMP_DIR"
  fi
  if [ $rc -ne 0 ]; then
    echo; echo "DEPLOY THAT BAI (exit $rc)."
    if [ "$DB_CHANGE_POSSIBLE" -eq 1 ]; then
      if systemctl is-active --quiet "$SERVICE"; then
        sudo -n /usr/bin/systemctl stop "$SERVICE" \
          || echo "CANH BAO: khong dung duoc $SERVICE; can dung service thu cong ngay."
      fi
      echo "DB co the da thay doi mot phan; giu service dung, khong tu dong doi code cu hoac restore/reset DB."
      [ "$DB_REBUILT" -eq 1 ] && echo "DB_MODE=rebuild da bat dau; service van phai dung cho den khi phuc hoi/kiem tra thu cong."
    else
      if [ "$SWITCHED" -eq 1 ]; then
        if [ -d "$PREV" ]; then
          ln -sfn "$PREV" "$BASE/current" \
            && echo "DB chua bi thay doi; da dua current ve release truoc $PREV." \
            || echo "CANH BAO: khong dua duoc current ve release truoc; can xu ly thu cong."
        else
          echo "Khong tim thay release truoc $PREV; khong doi symlink current."
        fi
      fi
      if [ "$SERVICE_STATE_CAPTURED" -eq 1 ]; then
        if [ "$SERVICE_WAS_ACTIVE" -eq 1 ]; then
          if [ "$SWITCHED" -eq 1 ] || ! systemctl is-active --quiet "$SERVICE"; then
            if [ -d "$PREV" ]; then
              sudo -n /usr/bin/systemctl restart "$SERVICE" \
                || echo "CANH BAO: restart release truoc that bai; service can xu ly thu cong."
            else
              echo "CANH BAO: service truoc deploy dang dung va khong co release truoc de restart."
            fi
          fi
        elif systemctl is-active --quiet "$SERVICE"; then
          sudo -n /usr/bin/systemctl stop "$SERVICE" \
            || echo "CANH BAO: service truoc deploy khong active nhung khong dung lai duoc."
        fi
      else
        echo "Khong ghi nhan duoc trang thai service ban dau; cleanup khong tu thay doi service."
      fi
      if [ "$SWITCHED" -eq 0 ] && [ "$CREATED" -eq 1 ]; then
        rm -rf "$REL"; echo "Da xoa release dang do: $REL"
      fi
    fi
    echo "Ban dang chay: $(readlink -f "$BASE/current")"
    [ -n "$BACKUP_ARCHIVE" ] && echo "Full backup archive: $BACKUP_ARCHIVE"
    [ -n "$BACKUP_SHA256" ] && echo "Full backup SHA-256: $BACKUP_SHA256"
    [ -n "$BACKUP_SIZE" ] && echo "Full backup size: $BACKUP_SIZE bytes"
    [ -n "$MARKFILE" ] && echo "Marker DB truoc deploy: $MARKFILE"
  fi
}
trap cleanup EXIT

step "1/9 Kiem tra dau vao ($NAME, DB_MODE=$DB_MODE)"
[ -f "$TAR" ] || { echo "Thieu file $TAR"; exit 1; }
[ -s "$NGINX_NEW" ] || { echo "Thieu file cau hinh nginx $NGINX_NEW"; exit 1; }
[ -f "$NGINX_SITE" ] && [ -r "$NGINX_SITE" ] \
  || { echo "Khong doc duoc cau hinh nginx dang chay $NGINX_SITE; khong co ban de khoi phuc."; exit 1; }
PREV=$(readlink -f "$BASE/current")
echo "Ban hien tai: $PREV"
if [ -e "$REL" ]; then
  [ "$PREV" = "$REL" ] \
    || { echo "Release $NAME da ton tai nhung khong phai ban dang chay; tu choi deploy."; exit 1; }
  [ "$DB_MODE" = sync ] \
    || { echo "Release $NAME dang chay; DB_MODE=$DB_MODE khong duoc bo qua, tu choi deploy."; exit 1; }
  systemctl is-active --quiet "$SERVICE" \
    || { echo "Release $NAME dang chay nhung $SERVICE khong active; tu choi deploy."; exit 1; }
  echo "Release $NAME da ton tai va dang chay ($SERVICE active); bo qua deploy."
  exit 0
fi
if systemctl is-active --quiet "$SERVICE"; then
  SERVICE_WAS_ACTIVE=1
else
  SERVICE_QUERY_STATUS=$?
  if [ "$SERVICE_QUERY_STATUS" -eq 3 ]; then
    SERVICE_WAS_ACTIVE=0
    echo "CANH BAO: $SERVICE khong active truoc khi deploy"
  else
    echo "Khong xac dinh duoc trang thai ban dau cua $SERVICE; tu choi deploy."
    exit 1
  fi
fi
SERVICE_STATE_CAPTURED=1

step "2/9 Giai nen va cai thu vien"
mkdir -p "$REL"; CREATED=1
tar -xzf "$TAR" -C "$REL"
for f in backend/manage.py backend/requirements-linux-py312.lock scripts/build_db.py scripts/backup_restore.py docs/common/database/release_DDL.sql .github/scripts/compare_schema_ddl.py docs/common/database/schema_drift_baseline.txt; do
  [ -f "$REL/$f" ] || { echo "Tarball khong co $f"; exit 1; }
done
python3 -m venv "$REL/venv"
"$REL/venv/bin/python" -m pip install -q --upgrade pip
"$REL/venv/bin/python" -m pip install -q -r "$REL/backend/requirements-linux-py312.lock"
"$REL/venv/bin/python" -m pip check
PY="$REL/venv/bin/python"
BUILD_DB="$REL/scripts/build_db.py"
BACKUP_TOOL="$REL/scripts/backup_restore.py"
DDL="$REL/docs/common/database/release_DDL.sql"

step "3/9 Nap cau hinh, check, collectstatic"
set -a; . "$ENVF"; set +a
if [ "$DB_MODE" = rebuild ] && [ -z "${ADMIN_PASSWORD//[[:space:]]/}" ]; then
  echo "Thieu ADMIN_PASSWORD trong $ENVF; tu choi rebuild truoc khi dung service hoac xoa DB."
  exit 1
fi
cd "$REL/backend"
$PY manage.py check
$PY manage.py collectstatic --noinput | tail -1

step "4/9 Cau hinh nginx"
# Cau hinh khong phu thuoc release (/static/ tro qua current). Lam truoc khi dung service de loi nginx
# chi can khoi phuc file cu; nginx dang chay giu cau hinh cu vi chua reload.
if cmp -s -- "$NGINX_NEW" "$NGINX_SITE"; then
  echo "Cau hinh nginx khong doi; bo qua cai dat va reload."
else
  cp -- "$NGINX_SITE" "$NGINX_PREV"
  echo "Da luu cau hinh nginx dang chay: $NGINX_PREV"
  if sudo -n /usr/bin/install -m 644 "$NGINX_NEW" "$NGINX_SITE" \
    && sudo -n /usr/sbin/nginx -t \
    && sudo -n /usr/bin/systemctl reload nginx; then
    echo "Da cai va reload cau hinh nginx moi."
  else
    echo "Cai cau hinh nginx THAT BAI; khoi phuc ban truoc."
    cp -- "$NGINX_PREV" "$NGINX_NEW"
    if sudo -n /usr/bin/install -m 644 "$NGINX_NEW" "$NGINX_SITE" && sudo -n /usr/sbin/nginx -t; then
      echo "Da khoi phuc cau hinh nginx truoc; chua dung service, chua thay doi DB."
    else
      echo "CANH BAO: khoi phuc cau hinh nginx that bai; can xu ly thu cong tu $NGINX_PREV."
    fi
    exit 1
  fi
fi

# psql bang role ung dung (thong tin tu backend.env)
pgapp() { PGPASSWORD="${DB_PASSWORD:-}" psql -h "${DB_HOST:-127.0.0.1}" -p "${DB_PORT:-5432}" -U "$DB_USER" -X -At -v ON_ERROR_STOP=1 "$@"; }
ICU_CREATE=(-T template0 -E UTF8 --locale-provider=icu --icu-locale=vi-VN --locale=C.UTF-8)

step "5/9 Backup truoc khi doi"
RELEASES_ROOT=$(readlink -f "$BASE/releases") || { echo "Khong xac dinh duoc thu muc release de kiem tra data root."; exit 1; }
[[ -d "$PREV" ]] || { echo "Release dang chay truoc deploy khong ton tai: $PREV"; exit 1; }
case "$PREV" in
  "$RELEASES_ROOT"/*) ;;
  *) echo "Release dang chay truoc deploy nam ngoai thu muc releases."; exit 1 ;;
esac
PREVIOUS_RELEASE_ID=${PREV##*/}
[[ $PREVIOUS_RELEASE_ID =~ ^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$ ]] \
  || { echo "ID release dang chay truoc deploy khong hop le cho backup."; exit 1; }
validate_external_root() {
  local label=$1 path=$2 resolved
  [ -n "$path" ] || { echo "Thieu data root bat buoc: $label"; return 1; }
  [[ "$path" == /* ]] || { echo "Data root $label phai la duong dan tuyet doi."; return 1; }
  [ -d "$path" ] || { echo "Data root $label khong ton tai hoac khong phai thu muc."; return 1; }
  resolved=$(readlink -f "$path") || { echo "Khong xac dinh duoc data root $label."; return 1; }
  case "$resolved" in
    "$RELEASES_ROOT"|"$RELEASES_ROOT"/*)
      echo "Data root $label khong duoc nam trong thu muc release."; return 1 ;;
  esac
}
validate_external_root DJANGO_MEDIA_ROOT "${DJANGO_MEDIA_ROOT:-}"
validate_external_root SIGNING_DOCUMENT_ROOT "${SIGNING_DOCUMENT_ROOT:-}"
validate_external_root AI_DATA_DIR "${AI_DATA_DIR:-}"
validate_external_root DOCUMENT_STORAGE_ROOT "${DOCUMENT_STORAGE_ROOT:-}"
BACKUP_PARENT="$BASE/backups"
mkdir -p "$BACKUP_PARENT"
BACKUP_PARENT=$(readlink -f "$BACKUP_PARENT") || { echo "Khong xac dinh duoc thu muc backup rieng."; exit 1; }
BACKUP_DIR="$BACKUP_PARENT/full"
[ -w "$BACKUP_PARENT" ] || { echo "Khong ghi duoc thu muc backup rieng."; exit 1; }
sudo -n /usr/bin/systemctl stop "$SERVICE" \
  || { echo "Khong dung duoc $SERVICE truoc khi backup; chua thay doi DB."; exit 1; }
if systemctl is-active --quiet "$SERVICE"; then
  echo "$SERVICE van active sau lenh stop; tu choi backup khi chua quiesce writer."
  exit 1
fi
BACKUP_JSON=$("$PY" "$BACKUP_TOOL" backup \
  --database "$DB_NAME" \
  --release-id "$PREVIOUS_RELEASE_ID" \
  --output-dir "$BACKUP_DIR" \
  --media-dir "$DJANGO_MEDIA_ROOT" \
  --signing-dir "$SIGNING_DOCUMENT_ROOT" \
  --ai-dir "$AI_DATA_DIR" \
  --storage-dir "$DOCUMENT_STORAGE_ROOT" \
  --private-config "$ENVF" \
  --include-private-config \
  --files-quiesced \
  --json)
if ! BACKUP_FIELDS=$(printf '%s\n' "$BACKUP_JSON" | "$PY" -c 'import json,re,sys; d=json.load(sys.stdin); p=d.get("archive"); h=d.get("sha256"); n=d.get("size_bytes"); assert isinstance(p,str) and p.startswith("/") and isinstance(h,str) and re.fullmatch("[0-9a-f]{64}",h) and isinstance(n,int) and n > 0; print(p); print(h); print(n)'); then
  echo "Ket qua JSON cua backup khong hop le; khong thay doi DB."
  exit 1
fi
mapfile -t BACKUP_META <<< "$BACKUP_FIELDS"
[ "${#BACKUP_META[@]}" -eq 3 ] || { echo "Thieu metadata backup; khong thay doi DB."; exit 1; }
BACKUP_ARCHIVE=${BACKUP_META[0]}
BACKUP_SHA256=${BACKUP_META[1]}
BACKUP_SIZE=${BACKUP_META[2]}
case "$BACKUP_ARCHIVE" in
  "$BACKUP_DIR"/qlvb-backup-*.tar.gz) ;;
  *) echo "Archive path khong nam trong thu muc backup rieng; khong thay doi DB."; exit 1 ;;
esac
[ -f "$BACKUP_ARCHIVE" ] && [ ! -L "$BACKUP_ARCHIVE" ] \
  || { echo "Archive full backup khong phai file thuong; khong thay doi DB."; exit 1; }
ACTUAL_BACKUP_SHA256=$(sha256sum -- "$BACKUP_ARCHIVE" | cut -d' ' -f1)
ACTUAL_BACKUP_SIZE=$(stat -c '%s' -- "$BACKUP_ARCHIVE")
[ "$ACTUAL_BACKUP_SHA256" = "$BACKUP_SHA256" ] && [ "$ACTUAL_BACKUP_SIZE" = "$BACKUP_SIZE" ] \
  || { echo "Hash/kich thuoc archive khong khop metadata; khong thay doi DB."; exit 1; }
echo "Full backup archive: $BACKUP_ARCHIVE"
echo "Full backup SHA-256: $BACKUP_SHA256"
echo "Full backup size: $BACKUP_SIZE bytes"
MARKFILE="$BACKUP_ARCHIVE.marker"
MARK=$(pgapp -d postgres -c "SELECT coalesce(shobj_description(oid,'pg_database'),'') FROM pg_database WHERE datname='$DB_NAME'")
(umask 077; set -o noclobber; printf '%s\n' "$MARK" > "$MARKFILE")
echo "Marker metadata: $MARKFILE"
DUMP_DIR=$(mktemp -d "$BACKUP_PARENT/.qlvb-deploy-dump.XXXXXX")
DUMP="$DUMP_DIR/database.dump"
"$PY" "$BACKUP_TOOL" extract-database-dump --archive "$BACKUP_ARCHIVE" --output "$DUMP"
test -s "$DUMP" || { echo "Dump PostgreSQL duoc trich xuat bi rong; khong thay doi DB."; exit 1; }

step "6/9 Co so du lieu ($DB_MODE)"
if [ "$DB_MODE" = rebuild ]; then
  [[ ${DB_NAME:-} =~ ^[a-z_][a-z0-9_]*$ && ${DB_USER:-} =~ ^[a-z_][a-z0-9_]*$ ]] \
    || { echo "DB_NAME/DB_USER trong $ENVF khong hop le"; exit 1; }
  test -s "$DUMP" || { echo "Dump da xac minh khong doc duoc: $DUMP"; exit 1; }
  if systemctl is-active --quiet "$SERVICE"; then
    echo "$SERVICE active tro lai truoc khi rebuild; tu choi thay doi DB."
    exit 1
  fi
  DB_CHANGE_POSSIBLE=1
  DB_REBUILT=1
  sudo -n -u postgres /usr/bin/dropdb --if-exists --force "$DB_NAME"
  sudo -n -u postgres /usr/bin/createdb -O "$DB_USER" "${ICU_CREATE[@]}" "$DB_NAME"
  $PY "$BUILD_DB" --seed
  COLL=$(pgapp -d postgres -c "SELECT datlocprovider::text || '|' || coalesce(to_jsonb(d)->>'datlocale', to_jsonb(d)->>'daticulocale') FROM pg_database d WHERE datname='$DB_NAME'")
  [ "$COLL" = 'i|vi-VN' ] || { echo "Collation DB sai: $COLL"; exit 1; }
  HASH=$(sha256sum "$DDL" | cut -d' ' -f1)
  MARK=$(pgapp -d postgres -c "SELECT coalesce(shobj_description(oid,'pg_database'),'') FROM pg_database WHERE datname='$DB_NAME'")
  [[ $MARK =~ ^build_db:v3\ ddl_sha256=$HASH\ seed=1\ collation=icu:vi-VN\ schema_sha256=[0-9a-f]{64}\ migrations_sha256=[0-9a-f]{64}$ ]] \
    || { echo "Dau build_db:v3 khong khop DDL/schema/history: $MARK"; exit 1; }
  $PY manage.py migrate --check
  echo "DB dung lai xong: collation=$COLL, marker/schema/history khop, khong con migration cho."
else
  # Luon thu tren ban khoi phuc truoc. build_db --adopt chi ghi marker sau khi schema va migration history
  # khop baseline duoc ho tro; --sync chay migration that, khong fake, va tu choi DDL drift khong co migration.
  echo "Ke hoach migration tren DB hien tai:"
  PLAN=$("$PY" manage.py migrate --plan)
  printf '%s\n' "$PLAN"
  if [[ "$PLAN" == *"No planned migration operations."* ]]; then
    HAS_PENDING_MIGRATIONS=0
  else
    # Unknown/changed plan output is treated as a migration so old writers are stopped.
    HAS_PENDING_MIGRATIONS=1
  fi
  if [ "$HAS_PENDING_MIGRATIONS" -eq 0 ] && [[ "$MARK" == build_db:v3\ * ]]; then
    # A verified v3 marker plus an empty migration plan makes --adopt and --sync read-only.
    LIVE_SYNC_NOOP=1
  fi
  TMPDB="qlvb_migtest_$$"
  ME=$(id -un)
  echo "Thu adopt va migration tren ban khoi phuc backup (DB tam $TMPDB)..."
  sudo -n -u postgres /usr/bin/createdb -O "$ME" "${ICU_CREATE[@]}" "$TMPDB"
  pg_restore --no-owner --no-privileges -d "$TMPDB" "$DUMP"
  # pg_dump -Fc khong mang COMMENT ON DATABASE; giu marker goc de preflight dung baseline.
  psql -X -q -v ON_ERROR_STOP=1 -v m="$MARK" -d postgres <<<"COMMENT ON DATABASE \"$TMPDB\" IS :'m';"
  TESTENV=(DB_NAME="$TMPDB" DB_USER="$ME" DB_PASSWORD= DB_HOST=/var/run/postgresql DB_PORT=5432)
  env "${TESTENV[@]}" "$PY" "$BUILD_DB" --adopt
  env "${TESTENV[@]}" "$PY" "$BUILD_DB" --sync --preflight-copy
  env "${TESTENV[@]}" "$PY" manage.py migrate --check
  TMPDDLDB="qlvb_ddlexpect_$$"
  sudo -n -u postgres /usr/bin/createdb -O "$ME" "${ICU_CREATE[@]}" "$TMPDDLDB"
  PGPASSWORD= psql -h /var/run/postgresql -p 5432 -U "$ME" -X -q -v ON_ERROR_STOP=1 -d "$TMPDDLDB" -f "$DDL"
  env "${TESTENV[@]}" DB_NAME="$TMPDB" "$PY" "$BUILD_DB" --compare-schema-database "$TMPDDLDB"
  sudo -n -u postgres /usr/bin/dropdb "$TMPDB"; TMPDB=""
  sudo -n -u postgres /usr/bin/dropdb "$TMPDDLDB"; TMPDDLDB=""
  echo "Preflight migration tren ban sao va schema theo release DDL/baseline: DAT."
  if [ "$LIVE_SYNC_NOOP" -eq 1 ]; then
    echo "Marker v3 va khong co migration dang cho; kiem tra read-only tren DB dang chay."
  else
    if [ "$HAS_PENDING_MIGRATIONS" -eq 1 ]; then
      echo "Migration dang cho; $SERVICE da dung truoc backup va se tiep tuc dung."
    else
      echo "DB co the can adopt; $SERVICE da dung truoc backup va se tiep tuc dung."
    fi
    if systemctl is-active --quiet "$SERVICE"; then
      echo "$SERVICE active tro lai truoc khi thay doi metadata; tu choi thay doi DB."
      exit 1
    fi
    # Adoption can record baseline rows or update the marker before a later failure.
    DB_CHANGE_POSSIBLE=1
  fi
  echo "Adopt metadata va kiem tra migration tren DB $DB_NAME..."
  $PY "$BUILD_DB" --adopt
  if [ "$LIVE_SYNC_NOOP" -eq 0 ]; then
    $PY "$BUILD_DB" --sync --preflight-verified-ddl-sha256 "$(sha256sum "$DDL" | cut -d' ' -f1)"
  fi
  $PY manage.py migrate --check
fi

step "7/9 Chuyen release va restart"
ln -sfn "$REL" "$BASE/current"; SWITCHED=1
if ! sudo -n /usr/bin/systemctl restart "$SERVICE"; then
  echo "Restart $SERVICE THAT BAI sau khi chuyen release."
  exit 1
fi

step "8/9 Kiem tra sau deploy"
ok=0; code=000; actual_release=""
for _ in $(seq 1 15); do
  sleep 2
  response=$(curl -sS -m 5 -w $'\n%{http_code}' -H 'Host: 127.0.0.1' \
    "http://127.0.0.1:$PORT/api/health/ready/" 2>/dev/null || true)
  code=${response##*$'\n'}
  body=${response%$'\n'*}
  if [ "$code" = "200" ]; then
    actual_release=$(printf '%s' "$body" | "$PY" -c \
      'import json,sys; data=json.load(sys.stdin); print(data.get("release", "") if data.get("status") == "ready" else "")' \
      2>/dev/null || true)
    if [ "$actual_release" = "$NAME" ] && systemctl is-active --quiet "$SERVICE"; then ok=1; break; fi
  fi
done
if [ $ok -ne 1 ]; then
  echo "Readiness THAT BAI (http=$code, release=$actual_release, expected=$NAME)."
  exit 1
fi
echo "Readiness DAT: DB query OK, release=$actual_release, service active."

step "9/9 Don release cu (giu $KEEP ban moi nhat)"
CUR=$(readlink -f "$BASE/current")
ls -1dt "$BASE"/releases/*/ | tail -n +$((KEEP+1)) | while read -r d; do
  d=${d%/}
  if [ "$d" = "$CUR" ] || [ "$d" = "$PREV" ]; then continue; fi
  echo "xoa $d"; rm -rf "$d"
done

echo; echo "DEPLOY OK: $PREV -> $REL"
