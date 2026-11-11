# Sao lưu và khôi phục CSDL, tệp và cấu hình

Tài liệu này mô tả backup logic do **scripts/backup_restore.py** tạo. Công cụ không dừng dịch vụ, không tạo/xóa database đích, không tự xóa backup và không gửi dữ liệu ra ngoài máy.

## Dữ liệu cần giữ cùng nhau

| Nguồn | Dữ liệu | Cấu hình |
| --- | --- | --- |
| PostgreSQL | Bản dump custom của đúng database ứng dụng; database comment chứa marker **build_db:v2** hoặc **build_db:v3** được lưu thêm ở sidecar. | DB role, owner và các role/grant mà dump tham chiếu phải tồn tại trước khi restore. |
| Tệp tải lên | Toàn bộ cây thư mục **MEDIA_ROOT**. | Giá trị **DJANGO_MEDIA_ROOT**; nếu không đặt, Django dùng **media/** cạnh thư mục **backend**. |
| Tệp nghiệp vụ | Toàn bộ cây thư mục **DOCUMENT_STORAGE_ROOT** (văn bản đến/đi, công việc, biểu mẫu; xem mục Cây thư mục tệp nghiệp vụ). | Giá trị **DOCUMENT_STORAGE_ROOT**; bắt buộc ngoài môi trường dev. |
| Tệp trình ký | Toàn bộ cây thư mục **SIGNING_DOCUMENT_ROOT**. | Đường dẫn này bắt buộc trong production; storage lưu vị trí tương đối trong CSDL. |
| AI | Toàn bộ **AI_DATA_DIR**, gồm tài liệu, Chroma và **doc_registry.json**. | **backend/config/__init__.py** là module **config** đang được import; mặc định thư mục là **backend/data**, có thể đổi bằng **AI_DATA_DIR**. |
| Cấu hình riêng | Tệp được truyền bằng **--private-config**, mặc định triển khai trong source là **/etc/qlvb/backend.env**. | Backup yêu cầu **DJANGO_SECRET_KEY** và **SIGNING_PIN_SECRET** có giá trị literal, không rỗng. |

Bốn data root (**MEDIA_ROOT**, **SIGNING_DOCUMENT_ROOT**, **AI_DATA_DIR**, **DOCUMENT_STORAGE_ROOT**) phải được truyền tường minh và tồn tại. Không suy ra đường dẫn từ thư mục release khi chạy backup. **DJANGO_SECRET_KEY** và **SIGNING_PIN_SECRET** được giữ trong bản sao cấu hình riêng; các giá trị này không nằm trong metadata hoặc stdout. Metadata chỉ ghi tên khóa cần có, tên một số khóa được cấu hình và allowlist cấu hình không bí mật.

## Tạo backup

Điều kiện trước khi chạy:

1. Dùng Python 3.12 và các tiện ích **psql**, **pg_dump**, **pg_restore** phiên bản PostgreSQL 16.
2. Chạy dưới tài khoản backend có quyền đọc bốn data root và tệp cấu hình riêng. Thư mục backup mới có quyền **0700**; archive có quyền **0600**.
3. Tạm dừng thao tác ghi database, upload và trình ký trong suốt thời gian dump database và đóng gói file. **--files-quiesced** chỉ là xác nhận của người vận hành; công cụ không tự dừng dịch vụ hay tạo snapshot filesystem.
4. Xác định đúng đường dẫn hiệu lực của **MEDIA_ROOT**, **SIGNING_DOCUMENT_ROOT**, **AI_DATA_DIR** và **DOCUMENT_STORAGE_ROOT**. Không đưa tệp .env, systemd override hoặc secret khác vào archive ngoài tệp được chỉ định.
5. Chọn **release-id** trùng với release cần khôi phục, ví dụ commit SHA đã dùng để tạo artifact.

Nạp cấu hình trong shell hiện tại mà không in nội dung tệp:

    set -a
    . /etc/qlvb/backend.env
    set +a

Các biến kết nối được lấy từ **DB_NAME**, **DB_HOST**, **DB_PORT**, **DB_USER**, **DB_PASSWORD** hoặc cấu hình **PGPASSFILE**. Không truyền mật khẩu trên command line. Gán các biến đường dẫn dưới đây từ cấu hình hiệu lực trước khi chạy:

    MEDIA_ROOT_RESOLVED=/duong/dan/media
    SIGNING_ROOT_RESOLVED=/duong/dan/signing
    AI_ROOT_RESOLVED=/duong/dan/ai-data
    STORAGE_ROOT_RESOLVED=/duong/dan/storage
    BACKUP_DIR=/duong/dan/backup-rieng
    RELEASE_ID=<release-id>

Tạo và tự xác minh archive:

    python scripts/backup_restore.py backup \
      --database "$DB_NAME" \
      --release-id "$RELEASE_ID" \
      --output-dir "$BACKUP_DIR" \
      --media-dir "$MEDIA_ROOT_RESOLVED" \
      --signing-dir "$SIGNING_ROOT_RESOLVED" \
      --ai-dir "$AI_ROOT_RESOLVED" \
      --storage-dir "$STORAGE_ROOT_RESOLVED" \
      --private-config /etc/qlvb/backend.env \
      --include-private-config \
      --files-quiesced

**--include-private-config** là xác nhận tường minh rằng archive sẽ chứa bản sao cấu hình có secret. Tệp nguồn phải là file thường, không phải symlink, và trên Linux không được cấp quyền cho group/other. Nếu cấu hình secret ở một file khác, phải xác minh chính sách custody riêng và truyền đúng file đó; công cụ không đọc systemd hoặc tự tìm kiếm secret.

Backup thất bại nếu thiếu root, marker DB, khóa bắt buộc, client PG16, hoặc quyền tạo archive riêng. Một archive đã được xuất bản nhưng lỗi kiểm tra sẽ được giữ nguyên để điều tra; công cụ không tự xóa archive.

**Điều kiện first-activation trên host:** snapshot kiểm tra read-only gần nhất (2026-10-20 00:52 UTC) ghi nhận `/etc/qlvb/backend.env` mode **0640**. Validator từ chối mọi quyền group/other, nên lần kích hoạt host đầu tiên vẫn chờ người có thẩm quyền quyết định cách xử lý custody/quyền file. Kiểm tra lại trạng thái trực tiếp trước khi deploy; không tự `chmod`, sao chép secret sang file **0600** để né kiểm tra, hoặc nới validator.

Có thể thêm `--json` để nhận metadata máy đọc được với các trường `archive`, `size_bytes` và `sha256`. Không có `--json`, CLI giữ nguyên dòng kết quả dành cho người vận hành. Cả hai dạng chỉ trả metadata archive, không trả giá trị secret.

Khi deploy tạo archive, `release-id` xác định release đang chạy lúc chụp backup, không phải release mục tiêu sắp triển khai. Đây là recovery point của trạng thái trước deploy.

## Kiểm tra archive

    python scripts/backup_restore.py verify --archive /duong/dan/backup/qlvb-backup-<release-id>-<utc>.tar.gz

Kiểm tra xác nhận:

- Có đủ database dump, sidecar marker, các file root và cấu hình riêng.
- SHA-256 và kích thước từng payload khớp manifest; archive và file root đọc được hết.
- **pg_restore --list** đọc được dump; member lạ, symlink, hardlink, đường dẫn tuyệt đối và **..** bị từ chối.
- Marker sidecar khớp metadata; cấu hình riêng có đủ khóa bắt buộc.

Checksum phát hiện lỗi truyền/corruption ngẫu nhiên. Manifest nằm cùng archive nên không phải chữ ký chống sửa đổi có chủ đích. Kiểm tra archive không chứng minh đã phục hồi được; phải có restore drill riêng.

## Trích dump đã xác minh

Deploy dùng lệnh công khai sau để lấy database dump từ full archive sau khi archive đã được xác minh:

    python scripts/backup_restore.py extract-database-dump \
      --archive /duong/dan/backup/qlvb-backup-<release-id>-<utc>.tar.gz \
      --output /duong/dan/thu-muc-private/database.dump

Thư mục đích phải tồn tại, chỉ owner truy cập được và do user hiện tại sở hữu. Lệnh xác minh toàn bộ archive và `pg_restore --list` trước khi tạo file; file được tạo độc quyền với mode **0600**, không ghi đè file có sẵn. Nếu kiểm tra hoặc ghi file thất bại, archive giữ nguyên và file dump chưa hoàn tất được dọn.

## Restore vào môi trường mới

Restore chỉ nhận database đích mới, rỗng và có tên được xác nhận chính xác. Công cụ không tạo database, không chạy **DROP**, **TRUNCATE**, **--clean** hay reset schema.

1. Chạy **verify** trên bản sao backup cần khôi phục.
2. Tạo một database mới trên PostgreSQL 16. Tạo bằng template0 với encoding/provider/locale tương ứng metadata backup; chuẩn bị trước role owner và các role được dùng trong owner/ACL của dump. Source database comment lưu trong sidecar sẽ được ghi lại sau khi dump được nạp.
3. Chọn thư mục restore chưa tồn tại. Chạy dưới tài khoản backend để file được sở hữu bởi tài khoản đó:

    python scripts/backup_restore.py restore \
      --archive /duong/dan/backup/qlvb-backup-<release-id>-<utc>.tar.gz \
      --database "$RESTORE_DB" \
      --confirm-target-db "$RESTORE_DB" \
      --restore-root /duong/dan/restore-moi/<release-id>

Trước khi nạp, công cụ kiểm tra major version, provider/locale/collation version, owner/quyền, marker, toàn bộ object trong DB đích và tính rỗng của thư mục đầu ra. Database đích có bất kỳ relation, function, type, extension, schema không mặc định hoặc marker đều bị từ chối và giữ nguyên.

Sau restore, cây thư mục có dạng:

    <restore-root>/
      media/
      signing/
      ai/
      storage/
      private_config/backend.env
      config/recovered-paths.json

Archive tạo trước khi có kho tệp nghiệp vụ không có **storage/**; restore archive đó chỉ khôi phục ba root còn lại và **recovered-paths.json** không có **DOCUMENT_STORAGE_ROOT**.

Thư mục gốc có quyền owner-only; tệp private config có quyền **0600**. **recovered-paths.json** chỉ là gợi ý đường dẫn mới. Tệp **backend.env** được khôi phục nguyên trạng và vẫn có thể trỏ đến đường dẫn cũ; người vận hành phải kiểm tra rồi hợp nhất các path mới vào cấu hình dịch vụ trước khi khởi động ứng dụng. Không source cấu hình vừa khôi phục trước khi kiểm tra.

Nếu **pg_restore** lỗi, giao dịch restore được rollback và database không bị drop. Nếu marker hoặc cài file lỗi sau khi database đã nạp thành công, database và backup vẫn được giữ; không tự reset, cần kiểm tra trạng thái rồi hoàn tất thủ công từ backup. Thư mục staging được giữ trong trường hợp cần tiếp tục cài file.

## Cây thư mục tệp nghiệp vụ

Biến **DOCUMENT_STORAGE_ROOT** là gốc lưu tệp nghiệp vụ; cột đường dẫn trong CSDL chỉ giữ phần tương đối so với gốc này, nên restore sang gốc mới không đổi dữ liệu CSDL:

| Thư mục | Nội dung | Dạng đường dẫn |
| --- | --- | --- |
| van-ban-den, van-ban-di | Tệp đính kèm văn bản đến, văn bản đi | `<module>/YYYY/MM/DD/<uuid>.<ext>` theo ngày upload |
| cong-viec | Tệp giao việc và tệp bằng chứng | như trên |
| mau-van-ban | Tệp tài liệu và biểu mẫu | như trên |
| ho-so | Dành cho tệp hồ sơ (chưa có luồng ghi tệp) | như trên |
| nguoi-dung, he-thong, tmp | Dành cho tệp gắn đối tượng và tệp tạm | `<module>/<owner>/<filename>` |

Tên gốc của tệp nằm trong CSDL; tên trên đĩa là UUID. Tệp trình ký (**SIGNING_DOCUMENT_ROOT**) và dữ liệu AI (**AI_DATA_DIR**) nằm ngoài cây này.

Trên host staging gốc là **/srv/qlvb/shared/storage**, cùng chủ sở hữu và chế độ quyền với **media/** (user chạy service **qlvb** phải ghi được). Deploy dừng ở bước kiểm tra data root nếu biến thiếu, là đường dẫn tương đối, không tồn tại hoặc nằm trong thư mục release; việc này xảy ra trước khi dừng service.

## Secret và giới hạn khôi phục

- **SIGNING_PIN_SECRET** phải đúng giá trị đã dùng khi các mảnh khóa server được mã hóa. Nếu mất hoặc đổi khóa này, database còn nguyên nhưng không thể giải mã **k_srv** và tiếp tục mở khóa ký cũ. Drill synthetic kiểm tra đúng đường khôi phục này.
- **DJANGO_SECRET_KEY** cần được giữ để ứng dụng tiếp tục dùng cùng khóa phiên/token. Cấu hình DB, API AI, email và tích hợp tùy chọn cũng cần được khôi phục nếu chức năng tương ứng được bật.
- Archive chứa plaintext database, file nghiệp vụ và tệp cấu hình riêng. Mode **0600/0700** giới hạn user thường trên cùng host; không bảo vệ khi root hoặc storage bị xâm nhập. Chưa có đích off-host/encrypted được cấu hình và xác minh trong milestone này; backup chỉ ở cùng host không bảo vệ khi mất host/disk.
- Dump giữ owner/ACL của object nhưng không sao lưu role/global password, tablespace, **pg_hba.conf**, cấu hình PostgreSQL hoặc cài đặt extension ở cấp OS. Cần dựng role và môi trường đích trước restore.
- Archive chứa đúng database và các root được truyền; không chứa source/release artifact, log, static build, thư mục ngoài các root, systemd override hoặc secret nằm ở nơi khác. AI data được khôi phục nhưng truy vấn AI vẫn cần provider, credential và OS dependency tương ứng. PDF/OCR cũng có thể cần font/Poppler trên host.
- File tree được đóng gói tuần tự, không có filesystem snapshot. Cần quiesce ghi trong suốt backup để hạn chế DB/file mismatch. Công cụ xác minh archive và restore trên dữ liệu synthetic; chưa chạy backup/restore trên host hoặc dữ liệu thật.

Vì chưa xác minh được secret custody độc lập hoặc nơi lưu off-host, đây là backup/restore workflow có thể diễn tập cục bộ, chưa phải bằng chứng disaster recovery đầy đủ hay host acceptance.

## Dependency lock cho Linux

**backend/requirements.txt** giữ nguyên các constraint đầu vào. **backend/requirements-linux-py312.lock** khóa trực tiếp và transitives bằng phiên bản cho CPython 3.12 Linux x86_64; lock được sinh và cài sạch trong Python 3.12.15 / Debian Bookworm, dùng pip-tools 7.6.2. Windows environment không được dùng làm nguồn lock.

Tạo lại lock trong Linux Python 3.12 x86_64:

    python -m pip install pip-tools==7.6.2
    python -m piptools compile \
      --allow-unsafe \
      --no-strip-extras \
      --resolver=backtracking \
      --no-emit-index-url \
      --output-file=backend/requirements-linux-py312.lock \
      backend/requirements.txt

Kiểm tra từ virtualenv sạch:

    python -m pip install -r backend/requirements-linux-py312.lock
    python -m pip check

Để lock có hiệu lực khi cài release, installer ở workflow/deploy cần dùng:

    "$REL/venv/bin/python" -m pip install -r "$REL/backend/requirements-linux-py312.lock"

Phần đổi lệnh install và cache path thuộc milestone D (**deploy.sh** và CI workflow); file đó chưa bị sửa trong milestone E. OS package, font, Poppler, Python patch và cấu hình/collation PostgreSQL vẫn cần kiểm tra riêng trên host.
