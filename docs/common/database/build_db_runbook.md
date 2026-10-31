# Dựng DB từ `release_DDL.sql` và runbook staging

`docs/common/database/release_DDL.sql` là nguồn schema. `scripts/build_db.py` là quy trình dựng DB duy nhất cho local, CI và staging.

## Script `scripts/build_db.py`

### Các chế độ

- **Bootstrap** (`--if-empty`): tạo DB rỗng, nạp `release_DDL.sql`, ghi nhận baseline migration và marker `build_db:v3`. Nếu DB đã có marker v3 khớp DDL/seed thì script kiểm lại fingerprint schema và lịch sử migration trước khi bỏ qua. DB bẩn, thiếu marker hoặc marker không khớp không bị reset.
- **Adopt** (`--adopt`): chỉ hỗ trợ marker `build_db:v2` của release DDL đã ghim. Trước khi đổi marker, script yêu cầu đúng lịch sử migration cũ và fingerprint catalog khớp schema release đó. Chỉ marker được cập nhật; không chạy migration hay seed.
- **Upgrade** (`--sync`): chỉ nhận marker v3 hợp lệ, so schema và migration history thực tế với fingerprint trong marker, rồi chạy `manage.py migrate` không dùng `fake`. Sau khi tất cả migration thành công, ghi marker v3 mới với DDL hash, schema fingerprint, migration fingerprint và trạng thái seed.
- **Reset** (`--force --seed`): thao tác xóa DB có chủ ý; cần `ADMIN_PASSWORD` trước khi drop. `release_DDL.sql` đổi hash không tự kích hoạt chế độ này.

Marker v3 có dạng `build_db:v3 ddl_sha256=<hash> seed=<0|1> collation=icu:vi-VN schema_sha256=<hash> migrations_sha256=<hash>`. Fingerprint schema gồm bảng, cột, constraint, index, enum, view, function và trigger; fingerprint migration tính từ toàn bộ `django_migrations`. Với v2, marker comment một mình không đủ: chỉ một DDL hash, một schema fingerprint và tập migration leaf cũ cụ thể mới được chấp nhận.

Nếu DDL hash thay đổi nhưng không có migration chờ, `--sync` dừng trước khi ghi DB. CI so sánh schema/data từ migration với `release_DDL.sql` theo `schema_drift_baseline.txt`; drift mới hoặc baseline đã hết lệch làm gate thất bại. Nếu schema hoặc migration history trong DB thật lệch fingerprint đã ghi, phải xử lý drift trước khi nâng cấp.

`--sync` không tạo/xóa DB, không nạp lại DDL, không seed và không tự reset. Nếu migration thất bại, script giữ nguyên DB và backup; migration có thể đã ghi một phần tùy transaction của migration, nên cần phục hồi từ backup hoặc xử lý thủ công trước lần chạy tiếp theo.

`--seed` cần `ADMIN_PASSWORD`; ở bootstrap nó tạo quản trị viên hoặc chỉ khởi tạo đúng placeholder hệ thống chưa có credential. Seed rerun không đổi hash mật khẩu, role hoặc trạng thái tài khoản đã có. Demo accounts chỉ được tạo khi truyền `--demo-data`, với `DEMO_PASSWORD`; seed rerun bỏ qua account đã tồn tại. Không có mật khẩu nào được in ra.

Kết nối đọc từ `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` (`--host`, `--port`, `--user`, `--dbname` ghi đè; mật khẩu chỉ đọc từ `DB_PASSWORD`). Bootstrap/reset cần quyền `CREATEDB`; host deploy dùng `sudo -u postgres` tạo DB tạm và role ứng dụng sở hữu DB. Cần `DJANGO_SECRET_KEY` và các thư viện trong `backend/requirements.txt`.

```bash
python scripts/build_db.py --dbname <tên DB> --if-empty --seed
python scripts/build_db.py --dbname <tên DB> --adopt
python scripts/build_db.py --dbname <tên DB> --sync
python scripts/build_db.py --dbname <tên DB> --force --seed
python scripts/build_db.py --dbname <tên DB> --if-empty --seed --demo-data
```

## Test trên PostgreSQL

Test chạy trên PostgreSQL; test DB do Django tự dựng bằng migration (không dùng template DDL):

```bash
pnpm test:backend    # local: PostgreSQL của compose.yaml
```

CI và host staging chạy `python manage.py test` trong `backend/` với `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` (và `DB_ENGINE=postgresql` nếu có) trỏ tới một PostgreSQL có quyền `CREATEDB`.

CI chạy thêm `scripts/build_db.py` trên một DB riêng để kiểm chứng DDL nạp được và migration đồng bộ được.

## Nạp workbook dữ liệu mẫu (tùy chọn)

`import_common_sample_data` chỉ ghi dữ liệu khi có `--apply`; mặc định và `--dry-run` chỉ kiểm tra workbook, đối chiếu cấu trúc và in số dòng. Trước khi dùng `--apply`, đặt `DEMO_PASSWORD` trong môi trường của tiến trình để khởi tạo mật khẩu cho các tài khoản có trong sheet `TaiKhoanDemo`, rồi kiểm tra `DB_HOST` và `DB_NAME` đang trỏ tới DB local/dev dự định.

Chạy từ thư mục gốc repo trên PowerShell:

```powershell
$securePassword = Read-Host "DEMO_PASSWORD" -AsSecureString
$env:DEMO_PASSWORD = [System.Net.NetworkCredential]::new("", $securePassword).Password
.\backend\.venv\Scripts\python.exe backend\manage.py import_common_sample_data --file "<đường dẫn workbook.xlsx>" --dry-run
.\backend\.venv\Scripts\python.exe backend\manage.py import_common_sample_data --file "<đường dẫn workbook.xlsx>" --apply
Remove-Item Env:DEMO_PASSWORD
```

Lệnh nhập theo transaction: nếu một dòng lỗi thì toàn bộ lần nhập được rollback. Lệnh này không chạy trong migration, `build_db.py` hay deploy; không dùng để thay đổi DB staging thủ công.

## Dựng lại DB staging

Dữ liệu staging là dữ liệu thử nghiệm. Thực hiện trên host staging, tài khoản có quyền `CREATEDB`, trong thư mục mã nguồn đã checkout đúng release và đã kích hoạt môi trường Python của backend. Mỗi quy trình nằm trong subshell `( set -euo pipefail; ... )`: lỗi ở bước nào thì quy trình dừng tại đó, phiên SSH không bị thoát.

Kiểm tra dump (`test -s`, `pg_restore -l`, số entry > 0) chỉ xác nhận archive đọc được danh mục; chưa chứng minh restore thành công toàn bộ.

```bash
(
  set -euo pipefail
  export DB_HOST=127.0.0.1 DB_PORT=5432 DB_USER=<user DB> DB_PASSWORD=<mật khẩu> DJANGO_SECRET_KEY=<khóa> ADMIN_PASSWORD=<mật khẩu bootstrap>
  DUMP=<thư mục sao lưu trên host>/qlvb_$(date +%Y%m%d_%H%M%S).dump

  # 1. Sao lưu DB hiện tại ra host và kiểm tra archive
  PGPASSWORD="$DB_PASSWORD" pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -Fc qlvb > "$DUMP"
  test -s "$DUMP"
  test "$(pg_restore -l "$DUMP" | grep -vc '^;')" -gt 0

  # 2. Dừng backend, dựng lại DB
  sudo systemctl stop <tên service backend>
  python scripts/build_db.py --dbname qlvb --force --seed

  # 3. Kiểm tra collation (kỳ vọng: i|vi-VN), migration, rồi khởi động lại backend
  COLLATION="$(PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -At \
    -c "SELECT datlocprovider::text || '|' || coalesce(to_jsonb(d)->>'datlocale', to_jsonb(d)->>'daticulocale') FROM pg_database d WHERE datname = 'qlvb'")"
  test "$COLLATION" = 'i|vi-VN'
  MIGRATIONS="$(cd backend && DB_ENGINE=postgresql DB_NAME=qlvb python manage.py showmigrations)"
  test -n "$MIGRATIONS"
  if grep -q '\[ \]' <<< "$MIGRATIONS"; then echo 'Còn migration chưa áp dụng' >&2; exit 1; fi
  sudo systemctl start <tên service backend>
)
```

Cluster staging cần hỗ trợ ICU và locale hệ điều hành `C.UTF-8` (PostgreSQL 16 build với ICU). Nếu bước 2 báo lỗi khi `CREATE DATABASE` (không có ICU hoặc `C.UTF-8`) thì dừng và báo người phụ trách, không đổi locale để vượt qua. Nếu bước 2 hoặc 3 lỗi sau khi backend đã dừng, backend giữ nguyên trạng thái dừng; xử lý lỗi rồi khởi động lại thủ công. Script tự dọn DB dựng dở (xem phần Script). DB gốc chỉ khôi phục được từ file dump ở bước 1.

Quy trình rebuild này chỉ dành cho reset staging. Deploy thường chạy migration thật trên bản sao backup rồi DB hiện tại; schema/data thay đổi phải có migration và qua schema/baseline CI gate.

## Deploy backend

`deploy/deploy.sh <tên release>` trong repo là nguồn duy nhất của quy trình deploy backend; mỗi lần deploy script được đẩy lên `~/deploy/` cùng tarball và chạy từ đó. Tarball phải có `scripts/backup_restore.py`; deploy dùng công cụ này để tạo full backup trước preflight, không gọi `/srv/qlvb/tools/backup.sh`. Push vào `staging` deploy với `DB_MODE=sync`; `workflow_dispatch` chỉ rebuild khi chọn rõ `reset_database=true`. Đầu vào là `~/deploy/qlvb-<tên release>.tar.gz` chứa `backend/`, `scripts/`, `docs/common/database/` và `.github/scripts/compare_schema_ddl.py`, cùng `~/deploy/qlvb-frontend.nginx` là bản sao `deploy/nginx/qlvb-frontend.conf` của cùng commit.

Tạo tarball từ commit cần phát hành bằng lệnh sau; comparator phải có trong archive vì `build_db.py` dùng nó để preflight schema:

```bash
SHA7=$(git rev-parse --short=7 HEAD)
git -c core.autocrlf=false archive --format=tar.gz -o "qlvb-$SHA7.tar.gz" "$SHA7" backend scripts docs/common/database .github/scripts/compare_schema_ddl.py
```

Các bước (log `/srv/qlvb/deploy.log`, khóa `flock` ở `/srv/qlvb/.deploy.lock`):

1. Kiểm đầu vào (tên release 1–64 ký tự, bắt đầu bằng chữ/số; tarball; `~/deploy/qlvb-frontend.nginx`; cấu hình nginx đang chạy đọc được; release chưa tồn tại).
2. Giải nén vào `/srv/qlvb/releases/<tên>`, tạo venv bằng Python 3.12, cài `backend/requirements-linux-py312.lock`.
3. Nạp `/etc/qlvb/backend.env`. Với `rebuild`, kiểm tra `ADMIN_PASSWORD` trước khi dừng service hoặc xóa DB. Sau đó chạy `manage.py check`, `collectstatic`.
4. Cấu hình nginx (xem mục [Đường vào staging và nginx](#đường-vào-staging-và-nginx)).
5. Kiểm tra `DJANGO_MEDIA_ROOT`, `SIGNING_DOCUMENT_ROOT`, `AI_DATA_DIR` và `DOCUMENT_STORAGE_ROOT` được đặt tường minh thành các thư mục tuyệt đối ngoài cây release. Dừng `qlvb-backend` trước khi chụp DB và bốn data root; tạo full backup trong thư mục riêng `backups/full`, xác minh archive, rồi trích `database.dump` đã xác minh vào thư mục tạm riêng để chạy preflight. Service tiếp tục dừng qua preflight, migration/kiểm tra DB và switch code, kể cả khi schema không có migration chờ. `release-id` trong archive là release thực tế đang chạy trước deploy; recovery point gồm DB và file trước khi áp dụng release mục tiêu mới. Log ghi đường dẫn archive và SHA-256; archive được giữ lại khi deploy lỗi.
6. Cơ sở dữ liệu theo `DB_MODE` (xem dưới).
7. Chuyển symlink `current`, `systemctl restart qlvb-backend`.
8. Kiểm tra `http://127.0.0.1:8001/api/health/ready/` trả 200 với `status=ready`, truy vấn DB thành công và `release` đúng tên release đang deploy; service cũng phải active (15 lần × 2 giây).
9. Giữ 5 release mới nhất, không xóa release đang chạy và release trước đó.

Deploy mở một cửa sổ bảo trì có downtime: `qlvb-backend` dừng trước khi chụp database và ba data root, rồi giữ dừng qua backup, preflight, migration/kiểm tra DB và switch code; sau đó deploy restart service rồi kiểm readiness. Deploy `sync` không có migration chờ vẫn có downtime; đây không phải rollout zero-downtime. Nếu lỗi trước khi DB có thể thay đổi, xóa release đang dựng, giữ nguyên `current`, xóa dump tạm và chỉ restart release trước nếu service ban đầu active; service ban đầu inactive vẫn inactive. Archive full backup và marker sidecar được giữ lại để điều tra.

Sau backup và restore-preflight trên bản sao, service vẫn dừng cho tới khi deploy hoàn tất. Trước khi chạy `--adopt`/`--sync` có thể ghi DB, deploy đánh dấu trạng thái DB có thể đổi. Nếu thao tác migration/adopt lỗi, kể cả khi `django_migrations` chưa có row, không chuyển code về bản cũ, không tự restore/reset DB và không khởi động service; giữ archive, log, release để xử lý thủ công. `rebuild` cũng fail-closed sau khi bắt đầu drop DB. Nếu restart hoặc readiness lỗi sau khi DB có thể đổi, giữ service stopped và không chạy code cũ trên schema chưa được chứng minh tương thích.

Readiness lấy release ID một lần khi process nạp settings từ đường dẫn vật lý trong `/srv/qlvb/releases/<tên release>`. Process cũ giữ ID cũ sau khi symlink `current` đổi; do đó probe từ nhầm process sẽ không đạt dù trả HTTP 200. Endpoint chỉ trả trạng thái và release ID, không trả thông tin kết nối hay exception DB.

### `DB_MODE`

| | `sync` (mặc định) | `rebuild` (chỉ staging) |
|---|---|---|
| Dùng cho | Deploy thường, giữ nguyên dữ liệu | Chỉ khi chủ ý xóa dữ liệu staging |
| Bước 6 | Restore dump đã xác minh vào DB tạm ICU `vi-VN`, chép marker, chạy `--adopt` để xác minh (nếu v2), rồi `--sync` thật trên DB tạm. Sau đó adopt/sync DB thật khi marker cần adopt hoặc migration đang chờ. Marker v3 hợp lệ cùng plan rỗng chỉ cần kiểm tra read-only. Service được giữ dừng từ lúc bắt đầu backup đến lúc deploy hoàn tất. | Kiểm `ADMIN_PASSWORD` và dump đã xác minh trước, service đã dừng, `dropdb --if-exists --force`, `createdb` ICU `vi-VN` owner là role ứng dụng, chạy `build_db.py --seed`; kiểm collation, marker v3, fingerprint schema/history và `migrate --check`. |
| DB thiếu marker hoặc schema/history lệch | Dừng trên bản khôi phục; không sửa DB thật hoặc switch release | Không áp dụng |
| Lỗi | Lỗi ở preflight không đổi DB thật. Lỗi khi adopt/migration có thể để lại schema/history/data một phần; giữ service stopped, backup và release, không tự đổi code hoặc restore DB. | Sau khi bắt đầu drop, DB có thể rỗng hoặc được nạp một phần; giữ service stopped và backup, không tự đổi code hoặc restore DB; `stop` lỗi thì dừng trước drop |

`pg_dump -Fc` không mang `COMMENT ON DATABASE`, nên script đọc marker từ DB thật và đặt lại trên bản restore. `--adopt` chỉ cập nhật marker sau khi xác minh schema fingerprint và đúng tập migration v2 đã hỗ trợ. Bản restore kiểm thử đường nâng cấp trước khi marker hoặc dữ liệu DB thật bị đổi.

`rebuild` là thao tác reset rõ ràng; không được chọn tự động vì hash DDL lệch hoặc migration lỗi. Sau khi nạp DDL, seed tạo/khởi tạo quản trị viên bằng `ADMIN_PASSWORD`. `DEMO_PASSWORD` chỉ cần khi gọi seed với `--demo-data`; deploy rebuild không tạo demo accounts.

### Điều kiện tiên quyết trên host

- User deploy là user chạy script, có quyền ghi `/srv/qlvb` và `~/deploy`, có role PostgreSQL cùng tên (kết nối qua socket `/var/run/postgresql`, peer) để restore vào DB tạm, và `python3` (3.12) kèm `venv`.
- Quyền `sudo` không mật khẩu đã dùng: `sudo -n -u postgres /usr/bin/createdb`, `sudo -n -u postgres /usr/bin/dropdb`, `sudo -n /usr/bin/systemctl stop qlvb-backend`, `sudo -n /usr/bin/systemctl restart qlvb-backend`, và ba lệnh nginx (đúng nguyên văn, không thêm quyền ghi khác vào `/etc/nginx`):

  ```
  <user deploy> ALL=(root) NOPASSWD: /usr/bin/install -m 644 /home/<user deploy>/deploy/qlvb-frontend.nginx /etc/nginx/sites-available/qlvb-frontend
  <user deploy> ALL=(root) NOPASSWD: /usr/sbin/nginx -t
  <user deploy> ALL=(root) NOPASSWD: /usr/bin/systemctl reload nginx
  ```
- `/etc/nginx/sites-enabled/qlvb-frontend` là symlink tới `/etc/nginx/sites-available/qlvb-frontend`; ngoài `default`, `sites-enabled` không có site nào khác nghe cổng 8088.
- Mọi deploy dừng `qlvb-backend` trước khi tạo full backup; user deploy cần quyền `systemctl stop` và phải đọc được ba data root tuyệt đối nằm ngoài thư mục release. Với `rebuild`, `ADMIN_PASSWORD` cũng phải có trong `/etc/qlvb/backend.env`:

```
<user deploy> ALL=(root) NOPASSWD: /usr/bin/systemctl stop qlvb-backend
```

  Thiếu quyền stop, deploy hủy trước backup; nếu service ban đầu active và đã dừng thì cleanup khởi động lại release trước. Thiếu secret hoặc rule sudo cho reset, `rebuild` dừng trước `dropdb`.
- Role ứng dụng (`DB_USER`) là owner DB, không cần `CREATEDB` hay superuser. Cluster hỗ trợ ICU và locale `C.UTF-8`.
- `/etc/qlvb/backend.env` đọc được bởi user deploy (script `source` file này), có cấu hình PostgreSQL, `DJANGO_SECRET_KEY`, `SIGNING_PIN_SECRET` literal và ba data root tường minh. Backup từ chối private config nếu file cho group/other quyền truy cập; không sao chép secret sang file quyền khác để né kiểm tra.
- User deploy có quyền tạo thư mục archive private `0700` và archive `0600` dưới `/srv/qlvb/backups/full`; dump preflight tạm nằm trong thư mục private và được dọn sau deploy.

### Chạy tay (không qua CI)

Từ máy dev (Windows 10/11, Linux, macOS) có `git`, `node`, OpenSSH client (`ssh`, `scp`), tại thư mục gốc repo:

```bash
pnpm deploy:staging
pnpm deploy:staging --reset-db
```

Lệnh fetch `origin/staging` rồi deploy đúng commit; không pull, không checkout, working tree và nhánh hiện tại không bị đổi. Mặc định in `DB_MODE=sync` và yêu cầu gõ `DEPLOY`. Chỉ khi thêm `--reset-db`, lệnh chọn `rebuild` và bắt buộc gõ `RESET`; `--yes` chỉ bỏ xác nhận `DEPLOY`, không bỏ xác nhận `RESET`. Tarball (`backend`, `scripts`, `docs/common/database`), `deploy/deploy.sh` và `deploy/nginx/qlvb-frontend.conf` (thành `qlvb-frontend.nginx`) của commit đó được gửi vào `~/deploy/`, sau đó chạy với `DB_MODE` đã chọn. Log stream ra terminal; file tạm được xóa sau khi chạy.

Workflow `CI` chỉ publish frontend/backend sau khi cả backend tests + migration/schema/baseline gate và frontend lint/i18n/token/tests/build đều đạt. Hai deploy jobs phụ thuộc cả hai gate để frontend và backend không phát hành độc lập sau một phần CI. Deploy tự động luôn dùng `sync`. Reset chỉ chạy qua `workflow_dispatch` trên `staging` khi chọn rõ input `reset_database`.

Cấu hình host (không ghi IP, tên tài khoản hay mật khẩu vào repo):

- `QLVB_DEPLOY_HOST` (bắt buộc): alias trong `~/.ssh/config` hoặc `user@host`. Ví dụ alias:

  ```
  Host qlvb-staging
      HostName <host>
      User <user deploy>
      Port 2150
  ```

  rồi đặt `QLVB_DEPLOY_HOST=qlvb-staging`.
- `QLVB_DEPLOY_PORT` (tùy chọn): chỉ khi đặt thì lệnh truyền `-p`/`-P`; không đặt thì cổng lấy từ cấu hình ssh (alias có `Port`, hoặc mặc định 22). Với `user@host` không qua alias, đặt `QLVB_DEPLOY_PORT=2150`.
- Mật khẩu SSH nhập trực tiếp khi `ssh`/`scp` hỏi (mỗi lần gọi một lần); nên dùng khóa SSH để tránh nhập lặp.

Điều kiện tiên quyết trên host giữ nguyên như mục trên, gồm rule sudoers `systemctl stop qlvb-backend`.

### Khôi phục từ dump

Dùng khi `DB_MODE=rebuild` lỗi từ bước 6 trở đi. `<dump>` là đường dẫn in ở cuối log; `<dump>.marker` lưu marker trước deploy; `<release cũ>` là release in ở dòng "Ban dang chay". Dump không mang collation hoặc database comment marker. Khôi phục marker sidecar rồi xác minh/adopt và sync trước khi khởi động service.

```bash
(
  set -euo pipefail
  sudo -n -u postgres /usr/bin/dropdb --if-exists --force qlvb
  sudo -n -u postgres /usr/bin/createdb -O <role ứng dụng> -T template0 -E UTF8 --locale-provider=icu --icu-locale=vi-VN --locale=C.UTF-8 qlvb
  PGPASSWORD=<mật khẩu> pg_restore -h 127.0.0.1 -U <role ứng dụng> -d qlvb --no-owner --exit-on-error <dump>
  MARKFILE=<dump>.marker
  test -s "$MARKFILE"
  MARK="$(cat "$MARKFILE")"
  PGPASSWORD=<mật khẩu> psql -h 127.0.0.1 -U <role ứng dụng> -d postgres -X -v ON_ERROR_STOP=1 -v m="$MARK" \
    -c "COMMENT ON DATABASE qlvb IS :'m'"
  DB_NAME=qlvb python scripts/build_db.py --adopt
  DB_NAME=qlvb python scripts/build_db.py --sync
  DB_NAME=qlvb python backend/manage.py migrate --check
  ln -sfn /srv/qlvb/releases/<release cũ> /srv/qlvb/current
  sudo -n /usr/bin/systemctl restart qlvb-backend
)
```

Đã kiểm trong container: restore dump của DB libc vào DB ICU thành công (65 bản ghi `django_migrations`). Chưa kiểm trên host thật.

## Đường vào staging và nginx

Đường vào duy nhất: `http://quanlyvanban.duckdns.org:8088`. Router NAT cổng 8088 về host; nginx nghe `8088` (IPv4 và IPv6), phục vụ SPA từ `/var/www/qlvb` và chuyển `/api/` tới Gunicorn `127.0.0.1:8001`. Không có tunnel hay site nginx thứ hai.

Nguồn duy nhất của cấu hình là `deploy/nginx/qlvb-frontend.conf`; không sửa tay `/etc/nginx` trên host. Thay đổi cấu hình đi qua PR, CI kiểm cú pháp bằng `nginx -t` (image `nginx:1.24`, cùng phiên bản Ubuntu 24.04), deploy cài vào `/etc/nginx/sites-available/qlvb-frontend`.

| Đường dẫn | Xử lý |
|---|---|
| `/`, route SPA | `try_files` về `index.html`; `index.html` gửi `Cache-Control: no-cache` |
| `/assets/` | cache 30 ngày, `immutable` |
| `/api/`, `/api`, `/health/ai` | proxy `127.0.0.1:8001` |
| `/static/` | alias `/srv/qlvb/current/backend/staticfiles/` |
| `/media/` | 404 |
| `/admin` | chỉ `127.0.0.1`/`::1`; từ internet 403 |

Header chuyển tiếp (`Host`, `X-Real-IP`, `X-Forwarded-For`, `X-Forwarded-Proto`) do nginx ghi đè từ kết nối thực tế, không giữ giá trị client gửi; `X-Forwarded-Proto` là `$scheme` (hiện tại `http`). Giới hạn body 50 MB (ứng dụng giới hạn 20 MB mỗi tệp).

Bước 4 của deploy:

1. Nội dung `~/deploy/qlvb-frontend.nginx` giống hệt file đang chạy: bỏ qua cài đặt và reload.
2. Khác: chép file đang chạy sang `~/deploy/qlvb-frontend.nginx.prev`, `install` bản mới, `nginx -t`, `systemctl reload nginx`.
3. Một trong ba lệnh lỗi: chép `.prev` về `~/deploy/qlvb-frontend.nginx`, cài lại, `nginx -t`, rồi deploy báo lỗi. Nginx chưa reload nên vẫn chạy cấu hình cũ.

Bước này chạy trước khi dừng `qlvb-backend`: lỗi nginx chỉ xóa release đang dựng, không gây downtime, không chạm DB hay `current`. Cấu hình không phụ thuộc release (`/static/` trỏ qua `current`), nên được cài trước khi chuyển release. Nếu deploy lỗi ở bước sau, cấu hình nginx mới vẫn giữ.

Truy cập `/admin` từ máy dev qua SSH tunnel (alias `qlvb-staging` như mục [Chạy tay](#chạy-tay-không-qua-ci)):

```bash
ssh -L 8088:127.0.0.1:8088 qlvb-staging
```

rồi mở `http://127.0.0.1:8088/admin/`. Đăng nhập admin dùng session và CSRF cookie qua HTTP, nên cần `DJANGO_ALLOWED_HOSTS` có `127.0.0.1`, `DJANGO_CSRF_TRUSTED_ORIGINS` có `http://127.0.0.1:8088`, và trình duyệt chấp nhận cookie `Secure` trên `http://127.0.0.1` khi `DJANGO_SECURE_COOKIES` bật.

Biến môi trường backend tương ứng với đường vào HTTP (`/etc/qlvb/backend.env`): `DJANGO_ALLOWED_HOSTS` gồm `quanlyvanban.duckdns.org`, IP host và `127.0.0.1`; `DJANGO_CSRF_TRUSTED_ORIGINS` gồm `http://quanlyvanban.duckdns.org:8088` và `http://127.0.0.1:8088`; `DJANGO_SECURE_SSL_REDIRECT=False` (không có HTTPS, bật sẽ chuyển hướng tới địa chỉ không phục vụ).

## Dọn instance PostgreSQL thừa trên host staging

Container `qlvb-main-db` (DB `qlvb_main`, `qlvb_ddl_verify_tmp`, volume `qlvb_main_pgdata`) không được backend tham chiếu. Dump ghi ra host, ngoài container và volume sắp xoá; chỉ xoá sau khi archive đọc được:

```bash
(
  set -euo pipefail
  DUMP=<thư mục sao lưu trên host>/qlvb_main_$(date +%Y%m%d_%H%M%S).dump

  docker exec qlvb-main-db pg_dump -U <user DB> -Fc qlvb_main > "$DUMP"
  test -s "$DUMP"
  test "$(pg_restore -l "$DUMP" | grep -vc '^;')" -gt 0

  docker stop qlvb-main-db
  docker rm qlvb-main-db
  docker volume rm qlvb_main_pgdata
)
```

Sau khi xóa, host chỉ còn một instance PostgreSQL (native, cổng 5432).
