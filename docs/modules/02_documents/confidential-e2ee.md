# Văn bản mật E2EE — phạm vi và nghiệm thu

## Mục tiêu

Khôi phục trang `/documents/confidential` thành phân hệ mã hóa đầu cuối độc lập.
Nội dung, số hiệu, trích yếu, ghi chú, tên tệp và byte tệp được mã hóa trên thiết bị.
Server nhận bản mã, khóa nội dung đã bọc và chữ ký; không nhận mật khẩu mở khóa,
mã phục hồi hoặc khóa bí mật dạng rõ. Không thay đổi văn bản đến/đi, `HAN_CHE`,
trình ký hoặc đưa dữ liệu văn bản mật vào AI.

## Ranh giới bảo vệ

- Người ngoài danh sách, gồm staff/superuser và người có quyền quản trị, không có
  quyền tải gói văn bản. Admin không có khóa tổng hoặc quyền giải mã mặc định.
  Tài khoản admin được chọn làm người nhận có cùng quyền như người nhận thường.
- Bảo vệ bí mật dữ liệu lưu trên database, bản sao lưu và vận chuyển qua server
  khi ứng dụng phía người dùng và khóa người nhận được tin cậy.
- Người có quyền thay JavaScript phát hành vẫn có thể lấy bản rõ hoặc khóa lúc
  người dùng mở. Bản web này không chống được máy người dùng/website bị kiểm soát.
- Fingerprint SHA-256 phải được đối chiếu qua kênh độc lập trước lần gửi hoặc mở
  đầu tiên. Giá trị được ghim theo tài khoản trong trình duyệt; thay khóa sẽ chặn.
  Không coi việc chép fingerprint từ cùng website là xác minh độc lập.
- Server vẫn thấy danh tính người gửi/nhận, UUID, kích thước và thời điểm. Chỉ
  danh tính, UUID và nội dung mã hóa được gắn vào chữ ký; thời điểm server không
  phải chứng cứ thời gian đáng tin cậy độc lập.
- Thu hồi chặn tải tiếp qua API. Không thu hồi được khóa, bản mã hay bản rõ người
  nhận đã giữ. Không cam kết chống chụp màn hình, malware hoặc chuyển tiếp bản rõ.
- Không có forward secrecy: lộ khóa bí mật có thể làm lộ các bản cũ được bọc bằng
  khóa đó. Không có server OCR, preview, full-text search hoặc quét virus bản rõ.

## Giao thức v1

1. Khóa cá nhân: RSA-OAEP 3072 bit/SHA-256 cho phong bì khóa và ECDSA P-256/SHA-256
   cho chữ ký. Tách khỏi khóa Ed25519/PIN của phân hệ trình ký.
2. Mỗi snapshot: UUID mới, khóa AES-256 ngẫu nhiên mới, nonce GCM 96 bit mới;
   JSON gói nội dung và tệp được mã hóa bằng AES-GCM với tag 128 bit.
3. AAD và nhãn RSA-OAEP: JSON array `['document-v1', uuid, author_user_id,
   author_fingerprint]`. Gắn bản mã vào đúng snapshot và danh tính người tạo.
4. Thông điệp ký: JSON array `['document-v1', uuid, author_user_id,
   author_fingerprint, nonce_base64, sha256(ciphertext_bytes), envelopes]`;
   `envelopes` là array `[key_id, wrapped_key_base64]`, sắp xếp tăng theo key ID.
   Chữ ký trên wire là 64 byte `r || s`; Django đổi sang DER để xác minh.
5. Fingerprint là SHA-256 của SPKI encryption key nối SPKI signing key.
6. Kho khóa cá nhân: PKCS8 của hai khóa được mã hóa AES-256-GCM; khóa bảo vệ dẫn
   xuất bằng Argon2id (64 MiB, 3 lượt, parallelism 1, salt ngẫu nhiên 16 byte).
   Mật khẩu riêng 16–1024 ký tự; độ dài không bảo đảm entropy, cần passphrase mạnh.
   Một bản bọc khác dùng mã phục hồi ngẫu nhiên 256 bit do người dùng giữ.
7. AAD kho khóa: `['vault-v1', user_id, fingerprint]`. Thông điệp ký cập nhật kho:
   `['vault-v1', user_id, fingerprint, ciphertext, nonce, recovery_ciphertext,
   recovery_nonce, salt]`. Login/reset tài khoản không đủ để thay kho khóa.

Không tự chế thuật toán mật mã. Định dạng v1 sử dụng WebCrypto và Argon2id từ
dependency `hash-wasm` hiện có; cần review mật mã độc lập trước phát hành thật.

## Tính năng và giới hạn phiên bản này

- Tạo khóa, lưu mã phục hồi, tải/import bản sao khóa đã mã hóa, mở khóa và phục hồi
  cùng danh tính bằng mã phục hồi. Không thay khóa công khai qua API.
- Xác minh người liên hệ, gửi cho cá nhân, mở nội dung, tải tệp đã giải mã và thu
  hồi quyền tải tiếp. Không cấp quyền theo đơn vị hoặc admin override.
- Snapshot bất biến: không API edit/delete. Muốn sửa nội dung hoặc thêm người nhận,
  tạo bản phát hành mới với khóa mới; chưa có liên kết phiên bản tự động.
- Tối đa 10 tệp, tổng 10 MiB; gói mã hóa tối đa 16 MiB, JSON request tối đa 24 MiB,
  tối đa 100 phong bì bao gồm người tạo. Không ghi tệp lên `MEDIA_ROOT`.
- Khóa và bản rõ nằm trong bộ nhớ khi mở. Khóa khi ẩn tab, đổi phiên/tài khoản,
  bấm khóa hoặc sau 10 phút; kết quả bất đồng bộ đến sau khóa không được hiển thị.
  JavaScript không bảo đảm xóa sạch mọi bản sao trong bộ nhớ; endpoint compromise
  nằm ngoài bảo vệ. Browser fingerprint ghim không chứa khóa bí mật.
- Sự kiện server: CREATE, DELIVER, DENY, REVOKE. DELIVER chứng minh giao gói mã hóa,
  không chứng minh người nhận đã đọc. API không cung cấp sửa/xóa event; người kiểm
  soát database có thể sửa log, nên không coi đây là audit độc lập chống DB admin.
- Quyền `create_confidential_document` được cấp qua module phân quyền. Superuser
  có thể tạo bản riêng; không có quyền đọc bản người khác nếu không được chọn.

## Tiêu chí nghiệm thu

| Mã | Tiêu chí | Chứng cứ yêu cầu |
|---|---|---|
| AC01 | Không gửi/lưu bản rõ của metadata, tệp hoặc khóa bí mật | Crypto round-trip + kiểm tra payload/schema/API từ chối trường plaintext |
| AC02 | Người tạo/người nhận được tải; người ngoài và admin ngoài danh sách nhận cùng 404 như ID không tồn tại | API tests; danh sách không có bản ngoài quyền |
| AC03 | Sai khóa, khóa bị tráo, sửa bản mã/nonce/chữ ký/phong bì bị từ chối | Crypto tests, API signature validation, fingerprint verification |
| AC04 | Phục hồi giữ fingerprint và mở được văn bản cũ; sai mã không mở được; login không ghi đè kho khóa | Crypto tests + JWT HTTP interop + vault API tests |
| AC05 | Chỉ người tạo thu hồi; không tự thu hồi; retry không tạo event trùng; lần tải sau bị chặn | API tests + JWT HTTP interop; không hứa thu hồi bản đã lưu |
| AC06 | Khóa/đổi phiên xóa UI bản rõ; async cũ không mở lại; người nhận chưa xác minh không được chọn | React acceptance tests |
| AC07 | Bảng mới khớp DDL; migrate fresh và nhận bảng có sẵn không phá bản mã | PostgreSQL catalog/dump compare + populated adoption check |
| AC08 | Documents, signing, authorization hiện có không regression; UI có vi/en; build/lint/tokens qua | Related backend suite + full frontend suite/build/checks |

## Kiểm chứng local đã thực hiện

- 17 ca frontend mới: 9 mật mã thật, 8 giao diện React.
- 13 ca backend mới/liên quan trên SQLite và PostgreSQL 17.
- 1 ca HTTP opt-in: WebCrypto → JWT → Django → PostgreSQL, gồm đăng ký, gửi, mở,
  phục hồi mật khẩu giữ khóa và thu hồi. Dữ liệu/tài khoản dùng trong DB tạm riêng.
- Related backend: 339 ca documents/signing/authorization qua trên SQLite,
  5 ca chỉ hỗ trợ PostgreSQL được bỏ qua.
- Frontend đầy đủ: 232 ca qua, 1 ca HTTP opt-in bỏ qua khi không cấu hình fixture
  URL; ca HTTP này đã qua riêng với server và PostgreSQL tạm.
- Frontend build, lint, vi/en parity và CSS tokens qua. Bundle warning >500 kB
  của ứng dụng chung còn tồn tại; phân hệ E2EE được tải lười.
- Bốn bảng mới khớp chính xác schema dump PostgreSQL của DDL. Clone DB có snapshot
  mã hóa và chạy migration nhận bảng có sẵn: số bản và hash bản mã giữ nguyên.
- Không khẳng định toàn bộ schema cũ của dự án khớp DDL: thử bootstrap DDL trần
  thiếu `django_content_type`, nên không phải đường triển khai Django hoàn chỉnh.
- Chưa có CI remote, review mật mã độc lập, browser E2E trên thiết bị đích hoặc
  staging/production. PostgreSQL local 17 khác PostgreSQL 16 của CI hiện tại.

## Triển khai và dữ liệu

Nhánh local `feat/restore-confidential-documents`, nền staging `db249d43`.
Chạy migration `authorization.0005` và `documents.0006` trên DB Django hiện có
sau khi backup/đối chiếu schema; phân quyền tạo theo người được phụ trách chốt.
Không fake migration trên DB thật chỉ để vượt lỗi. DDL trần cần bootstrap đầy đủ
các bảng/ledger Django trước khi chạy app; kiểm tra riêng nếu dùng đường này.

Không chuyển `HAN_CHE` thành E2EE ở server: việc chuyển cần bên giữ bản rõ mã hóa
trên thiết bị và phân phối khóa. Không khôi phục các hàng plaintext `VanBanMat`
đã bị xóa trong lịch sử; muốn khôi phục dữ liệu cũ cần backup riêng.

Rollback code có thể giữ các bảng E2EE; reverse migration xóa bảng và làm mất
gói mã hóa, nên không dùng trên DB đã có dữ liệu nếu chưa có kế hoạch sao lưu.
Không commit/push/merge/deploy trong phạm vi triển khai local này.

Trạng thái bàn giao: `IMPLEMENTATION_DONE_READY_FOR_VERIFICATION`.
Các kết quả trên là tự kiểm chứng của lượt triển khai, chưa thay thế review độc lập.
