# PR #131 — Phân tích và sửa sai lệch DDL thuộc nhóm 3

Ngày kiểm tra: 17/10/2026. Bản sửa được tách vào nhánh `codex/group3-ddl-alignment-20261017` từ base nhóm 3 `aa19b88`, liên kết Issue #160 và chuẩn bị qua PR riêng vào `3_dossiers_documents`. Chưa tích hợp vào nhánh nhóm hoặc PR #131.

## Bằng chứng đầu vào

- PR: https://github.com/QuanLyVanBanTLBM/QuanLyVanBan_TLBM/pull/131
- Head đã kiểm tra: `aa19b880d7809b7e6572bacd69ce282fda2d54a2`.
- Review yêu cầu sửa: https://github.com/QuanLyVanBanTLBM/QuanLyVanBan_TLBM/pull/131#pullrequestreview-5556453381
- Job thất bại: https://github.com/QuanLyVanBanTLBM/QuanLyVanBan_TLBM/actions/runs/38666949000/job/116200961818
- Job migrate được database trống, nhưng dừng khi `diff -u` giữa dump migration và dump DDL. Test PostgreSQL sau đó bị skipped.
- Nguồn chuẩn: `docs/common/database/release_DDL.sql`, SHA-256 `0308b8dcd23e20b57994894653df1f49cf7fe212ef94c2f4a3de33ec74ed0b5f`. Bản sửa không thay đổi file này.

## Nguyên nhân thuộc nhóm 3

Hai bảng `records_hoso`, `records_loaivanban` có sai lệch thực tế giữa migration và DDL:

- Migration tạo identity, trong khi DDL dùng BIGSERIAL/sequence default.
- Thiếu default database `now()` cho timestamps và `false` cho cờ hồ sơ hệ thống. `auto_now`/`default` của ORM không thay thế default khi INSERT bằng SQL.
- Khóa ngoại Django có tên sinh tự động, mặc định NO ACTION và deferred, khác ON DELETE RESTRICT của DDL.
- Tên/biểu thức CHECK khác; PositiveIntegerField còn tạo CHECK `>= 0` thừa bên cạnh điều kiện `> 0`.
- Có pattern index phụ ngoài danh mục DDL; partial index hệ thống có cách biểu diễn khác.
- Trigger thời gian gọi helper riêng thay vì `set_updated_at`; nội dung một thông báo bảo vệ hồ sơ hệ thống khác DDL.

## Bản sửa

- `backend/apps/records/models.py`: khai báo database defaults, đồng bộ tên CHECK, dùng IntegerField có validator và CHECK `> 0`.
- `backend/apps/records/migrations/0006_align_release_schema.py`: migration forward đồng bộ đúng hai bảng; không sửa migration cũ hoặc tái tạo bảng. Lưu snapshot SQL của các hàm trong migration, không đọc DDL biến động khi chạy.
- Chuyển identity sang sequence của BIGSERIAL nhưng giữ giá trị đã cấp, tránh tái sử dụng ID sau khi có hàng bị xóa.
- Chỉ sửa FK xuất phát từ hai bảng nhóm 3; giữ nguyên FK đã đúng chuẩn. Khóa bảng có timeout 5 giây; schema bất thường làm giao dịch dừng.
- Không ghi đè hàm `set_updated_at` có sẵn. Chỉ tạo nếu thiếu; nếu định nghĩa có sẵn khác chuẩn, dừng để chủ sở hữu kiểm tra.
- Hàm cũ chỉ bị xóa bằng RESTRICT sau khi trigger nhóm 3 đã chuyển; không dùng CASCADE.
- Đồng bộ database state với migration state. Nhánh SQLite thực hiện state operations và cài lại guard sau các lần rebuild của SQLite.
- `backend/apps/records/test_release_schema.py`: test defaults bằng SQL, sequence, FK RESTRICT, trigger và adoption không đổi hàng dữ liệu.
- `backend/apps/records/test_index_adoption.py`: kiểm tra readiness theo migration cuối mới.

Migration forward này không có reverse tự động. Cần sao lưu và review trước khi triển khai lên database dùng chung. Trong lần kiểm chứng này chỉ áp dụng trên database kiểm chứng riêng.

## Kiểm chứng local trước khi tách nhánh

Môi trường: Python 3.12, Django 6.1.2, PostgreSQL 18.6 trên cluster riêng, cổng 55439. CI dùng PostgreSQL 16; kết quả local không thay thế CI.

- Tái hiện bằng hai database trống: một dựng từ migration, một nạp nguyên DDL phát hành.
- Sau sửa: catalog của hai bảng khớp ở cả 8 hạng mục (columns/defaults, constraints, indexes, triggers); nội dung các hàm trigger khớp sau chuẩn hóa CRLF/LF.
- Dump schema chỉ hai bảng, dùng `--schema-only --no-owner --no-privileges --no-comments`, bỏ dòng restrict ngẫu nhiên: không còn diff.
- `python backend/manage.py makemigrations --check --dry-run`: No changes detected.
- `python backend/manage.py test records --noinput` trên PostgreSQL riêng: 42 test đạt với cấu hình băm mặc định.
- Test records trên SQLite in-memory: 42 test, đạt, skipped 6 test PostgreSQL.
- Nâng cấp từ migration 0005 có dữ liệu và sequence đã cấp: giữ nguyên hàng dữ liệu, giá trị sequence và thứ tự cấp ID tiếp theo.
- Adoption trên database DDL đã seed: giữ nguyên dữ liệu của cả 55 bảng nghiệp vụ.
- Toàn bộ backend với MD5PasswordHasher chỉ trong test: 629 test, 3 lỗi tại accounts/dashboard. Bản HEAD trước sửa, được trích ra thư mục riêng và chạy cùng cấu hình: 623 test, đúng 3 lỗi tương ứng. Không ghi nhận toàn bộ backend đã đạt.
- Lỗi accounts là phép đối chiếu constraint chưa tính loại NOT NULL (`contype='n'`) trên PostgreSQL 18. Hai lỗi dashboard liên quan kỳ vọng dữ liệu văn bản trong các test thống kê cũ. Đây là lỗi tái hiện trong môi trường kiểm chứng cả trước và sau sửa; không kết luận ba lỗi này xuất hiện trên CI PostgreSQL 16.
- `git diff --check`: đạt. File DDL chuẩn, cấu hình, thông tin đăng nhập và các file ngoài phần sửa records được đối chiếu giữ nguyên. Các thay đổi Excel đang chờ được giữ lại.

Bằng chứng giữ riêng tại `.venv/group3-qa/pr131-ddl/`, không đưa mật khẩu cluster, log seed hoặc dump vào Git. Database nghiệm thu local, dữ liệu Excel, cấu hình và thông tin đăng nhập hiện hữu không được dùng để thử migration.

## Phần còn chặn CI chung

Diff CI gốc có 5970 dòng và còn sai lệch ngoài nhóm 3: enum, các bảng của signing/documents/document_templates, bảng hệ thống Django và các đối tượng khác. Tên bảng có tiền tố `records_` không đủ để xác định quyền sở hữu: các bảng tài liệu thuộc app `document_templates`, không thuộc app `records` của nhóm 3.

Không sửa model/migration của app khác, không sửa workflow chung hoặc bỏ qua gate DDL. Cần DevOps và nhóm phụ trách phân loại phần diff còn lại, xử lý các khác biệt cấu trúc thực và thống nhất cách đối chiếu các bảng hệ thống. Không chỉ loại bỏ tên đối tượng khỏi phép so sánh để làm CI xanh.

Sau khi bản sửa nhóm 3 được review và tích hợp vào nhánh nhóm, cần chạy lại CI trên commit PR mới. PR #131 còn yêu cầu xác nhận bộ lọc văn bản hạn chế ở nhóm 2; nội dung đó chưa được sửa trong nhiệm vụ DDL này. Chưa đủ điều kiện tuyên bố PR sẵn sàng merge staging.

Trong lượt kiểm chứng ban đầu không có push, merge, gửi review/comment hoặc thay đổi staging. Các thay đổi dữ liệu Excel đã được lưu riêng và không nằm trong nhánh PR DDL.


## Kiểm chứng nhánh PR sạch và phụ thuộc bàn giao

- Diff với nhánh nhóm 3 chỉ có 5 file của app records và tài liệu nhóm 3; không chứa công cụ nhập Excel hoặc dữ liệu local.
- PostgreSQL riêng: 35 test records đạt với bộ băm mặc định. SQLite in-memory: 35 test, đạt, skipped 6 test PostgreSQL.
- Toàn bộ backend trên nhánh sạch: 622 test, còn đúng 3 lỗi nền accounts/dashboard đã mô tả; MD5PasswordHasher chỉ trong cấu hình test. Không đánh dấu toàn bộ backend đã đạt.
- PR #139 hiện mở vào `7_meeting_rooms_birthdays_system`, chưa merge. Đây là phụ thuộc workflow/so sánh schema chung, nhóm 3 không tự sửa hoặc tích hợp thay nhóm phụ trách.
- PR #159 của nhóm 2 đang mở vào staging, có nội dung liên quan bộ lọc `pham_vi=HAN_CHE`; cần chủ sở hữu xác nhận luồng được route và test trước khi coi phụ thuộc #131 hoàn tất.
- PR #48 là implementation cũ ở `backend/records/`, model/serializer rỗng, view/test còn dùng Dossier/DocumentType không khớp HoSo/LoaiVanBan. Các chức năng scope, tìm kiếm và lọc năm đã có trong app hiện hành; hợp đồng UI cũ cần đối chiếu trước khi đóng PR. Chưa đóng #48 hoặc xóa nhánh.
- Công cụ bootstrap giữ kế hoạch adoption cũ và chặn graph ngoài kế hoạch trước khi ghi. Không dùng công cụ đó để bootstrap graph hiện tại; không tự chuyển các migration của nhóm khác thành fake để vượt kiểm tra. Kiểm tra readiness dùng migration leaf và đã đạt test.
- Bộ dữ liệu Excel là công việc riêng, chưa nằm trong nhánh nhóm 3. Không đưa vào PR DDL hoặc chuyển bản dump local vào repo.
