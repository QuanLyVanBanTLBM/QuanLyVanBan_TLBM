# Kế hoạch triển khai phân hệ Trình ký theo phase (Nhóm 5)

Tài liệu này là lộ trình triển khai backend, sắp xếp từ phần ít phụ thuộc nhất đi lên. Nội dung nghiệp vụ và mô hình dữ liệu tham chiếu `signing-backend-plan.md` và `spec.md` cùng thư mục.

## 1. Quy ước chung

- FK người dùng dùng `settings.AUTH_USER_MODEL`, không cố định `auth.User`.
- Tên field và enum tiếng Việt theo `signing-backend-plan.md` mục 5.2; enum khai báo bằng `models.TextChoices`.
- FK trỏ tới bảng lịch sử/bằng chứng dùng `on_delete=PROTECT`.
- `document_type` của yêu cầu trình ký bắt buộc truyền tường minh, không đặt giá trị mặc định ở model.
- Mỗi phase một commit. Điều kiện qua phase: `manage.py check`, `makemigrations --check`, toàn bộ test pass. Trước khi push: bổ sung `pnpm --dir frontend run build`.
- Không xử lý trong phase nào: giá trị mặc định thay cho dữ liệu nghiệp vụ, ghi đè bằng chứng đã chốt.

## 2. Lộ trình

| Phase | Nội dung | Điều kiện phụ thuộc | Trạng thái |
|---|---|---|---|
| 1 | Enums, crypto (SHA-256, Ed25519), storage adapter, định dạng lỗi | Không | Hoàn thành (`bfcb562`) |
| 2 | Model `SigningKey`, `SigningProcess`, `SigningProcessStep` + migration | `AUTH_USER_MODEL` | Hoàn thành (`469d499`) |
| 3 | 11 model còn lại + bất biến ở tầng model | Phase 2 | Hoàn thành (`e51cfda`) |
| 4 | Service quy trình và khóa ký, ghi nhật ký | Phase 3 | Hoàn thành (`97e5950`) |
| 5 | API quy trình và khóa ký, giới hạn theo quyền sở hữu | Phase 4 | Hoàn thành (`64ea1cd`) |
| 6a | Bảo vệ khóa ký bằng PIN (Argon2id + `k_srv`): model, service, API, nhật ký | Phase 5 | Hoàn thành (nhánh `feat/signing-phase6-pin`) |
| 6b | Phân quyền theo 8 quyền của phân hệ; quản trị mở lại PIN bị khóa cứng | Chốt model người dùng và cách gán quyền | Chờ quyết định |
| 7 | Yêu cầu trình ký, lượt trình, snapshot người ký | Bảng văn bản (Nhóm 2), `Chức vụ`, `Đơn vị` (Nhóm 7) | Chờ nhóm liên quan |
| 8 | Hành động ký, từ chối, thu hồi; manifest; khóa dòng và chống trùng | Phase 7; PostgreSQL cho test đồng thời | Chờ Phase 7 |
| 9 | Yêu cầu chỉnh sửa, ủy quyền, hạn xử lý, thông báo | Phase 8 | Chờ Phase 8 |
| 10 | Phẳng hóa PDF, adapter pháp lý, frontend | Phase 8; chốt hệ tọa độ vị trí ký | Chờ |

## 3. Chi tiết các phase

### Phase 1 — Nền tảng không phụ thuộc (hoàn thành)
- `enums.py`, `crypto.py`, `storage.py`, `errors.py`, cấu hình `SIGNING_DOCUMENT_ROOT`, dependency `cryptography`.
- Định dạng lỗi chỉ áp dụng cho view kế thừa `SigningAPIView`, không thay handler toàn cục của module khác.

### Phase 2 — Model phụ thuộc người dùng
- `SigningKey`: partial unique một khóa `HOAT_DONG` mỗi người; CHECK `HOAT_DONG` phải có `thoi_diem_xac_minh_so_huu`; không có trường khóa bí mật.
- `SigningProcess`: unique `(ma_quy_trinh, phien_ban)`.
- `SigningProcessStep`: unique `(quy_trinh, thu_tu)`; `don_vi` tạm là số nguyên cho phép rỗng, đổi sang FK khi Nhóm 7 hoàn tất.
- Test: từng ràng buộc bằng `IntegrityError`.

### Phase 3 — Các model còn lại
- `SigningProcessStepSigner`, `SigningRequest`, `SigningAttempt`, `SigningRequestStep`, `SigningRequestStepSigner`, `SigningSignature`, `SigningManifest`, `SigningChangeThread`, `SigningChangeMessage`, `SigningAuditLog`, `SigningNotification`.
- Văn bản: `document_type` (đến/đi/mật) + `van_ban_id`, không FK.
- Chức vụ: `chuc_vu_id` số nguyên cho phép rỗng tạm thời; CHECK "người ký hoặc chức vụ" khai báo ngay.
- Ràng buộc unique, CHECK SHA-256, CHECK nhật ký luồng ký, CHECK lý do ủy quyền theo `signing-backend-plan.md` mục 5.2, 5.3.
- Bất biến ở tầng model (môi trường SQLite chưa có trigger): chặn sửa chữ ký (trừ trường xác minh), chặn sửa/xóa manifest `DA_CHOT`, nhật ký chỉ ghi thêm.
- Trigger PostgreSQL tương ứng đã có trong CSDL chung; áp dụng khi chuyển sang PostgreSQL.

### Phase 4 — Service
- `process.py`: tạo, kích hoạt, ngừng, nhân bản (tăng `phien_ban`), chặn sửa quy trình đã kích hoạt, kiểm tra mỗi quy trình có cấp và mỗi cấp có người ký.
- `keys.py`: đăng ký khóa công khai, xác minh sở hữu (proof-of-possession), kích hoạt, xoay vòng, thu hồi.
- `audit.py`: ghi nhật ký dùng chung cho mọi hành động.

### Phase 5 — API
- `/api/v1/signing/quy-trinh/` (danh sách, tạo, kích hoạt, ngừng, nhân bản) và `/api/v1/signing/khoa/` (đăng ký, thách thức, xác minh, kích hoạt, xoay vòng, thu hồi).
- Challenge chứng minh sở hữu khóa là chuỗi cố định gắn dấu vân tay khóa, chưa có TTL/dùng một lần (xem `signing-backend-plan.md` mục 3.4).
- Xác thực bắt buộc; giới hạn theo người sở hữu/người tạo ở server. Phân quyền chi tiết để Phase 6.

### Phase 6a — Bảo vệ khóa ký bằng PIN (hoàn thành)
- Model `SigningKeyUnlock` (bảng `signing_key_unlock`, migration `0003_mo_khoa_ky_bang_pin`).
- `services/pin.py`: `dat_pin`, `mo_khoa_ky`, `doi_pin`. Server nhận `xac_minh_pin` = Base64 của verifier 32 byte, không nhận PIN.
- Lưu HMAC-SHA256(verifier) và `k_srv` mã hóa AES-256-GCM (gắn với id + dấu vân tay khóa); khóa dẫn xuất HKDF từ `SIGNING_PIN_SECRET` (dev: `SECRET_KEY`).
- Sai 5 lần khóa 15 phút; sai 10 lần khóa cứng (HTTP 423). Bộ đếm cập nhật dưới `select_for_update` và commit trước khi trả lỗi.
- Tham số Argon2id kiểm tra mức sàn `m >= 65536 KiB, t >= 3, p >= 1`. Chính sách PIN 8 chữ số kiểm tra ở frontend (server không thấy PIN).
- Test: `tests/test_pin_phase6.py` (khóa theo ngưỡng, đếm đồng thời trên PostgreSQL, `k_srv` chỉ trả sau xác minh, không trả PIN/hash/bản bọc).

### Phase 6b — Phân quyền (chờ quyết định)
- 8 quyền theo CSDL chung: `view_trinhky`, `add_trinhky`, `sign_trinhky`, `manage_signing_process`, `send_trinhky`, `delegate_trinhky`, `cancel_trinhky`, `view_signing_audit`.
- Cần chốt: model người dùng của hệ thống (`accounts_employee` hay `auth.User`) và cách kiểm tra quyền ở tầng API.
- Bảo vệ khóa ký bằng PIN theo `signing-backend-plan.md` mục 3.4: bảng `signing_key_unlock`, endpoint `dat-pin`, `mo-khoa-ky`, `doi-pin`, khóa theo số lần sai (5 lần: 15 phút; 10 lần: khóa cứng), nhật ký sự kiện PIN. Service và model nằm ở backend; phần Argon2id WASM nằm ở frontend (Phase 10).
- Test: sai PIN quá ngưỡng bị khóa; bộ đếm đúng khi gọi đồng thời; `k_srv` chỉ trả sau khi xác minh; không có endpoint nào trả bản bọc hoặc PIN.

### Phase 7 đến 10 — Phần phụ thuộc bên ngoài
- Trước Phase 7 cần xác nhận pháp chế: văn bản mật (`vanbanmat`) có ký trên hệ thống này không; hình thức ký thay (KT., TL., TUQ.) và thời hạn ủy quyền.
- Phase 7: cần bảng văn bản, `Chức vụ`, `Đơn vị`; thay các trường số nguyên tạm bằng FK.
- Phase 8: test đồng thời (hai người ký cùng lúc, gửi lặp, ký lặp) cần PostgreSQL.
- Phase 9: nhắc hạn cần cấu hình tác vụ định kỳ.
- Phase 10: cần chốt hệ tọa độ vị trí ký (tỷ lệ % hoặc điểm PDF); dòng nhận diện "bản duyệt nội bộ, chưa phát hành" trên tệp hoàn tất; màn hình ký hiển thị tên tệp và mã băm cùng ô nhập PIN; module Argon2id WASM.

## 4. Đối chiếu CSDL chung sau issue #47

Bản `csdl_qlvbtl_schema_final.sql` đính kèm phản hồi issue #47 đã đối chiếu mục 9. Các điểm đã cập nhật đúng đề xuất: `document_type` và index, trigger manifest `DA_CHOT`, trigger bất biến chữ ký và nhật ký, `ON DELETE RESTRICT` cho nhật ký/thread/message/người ký cấu hình, cột cho phép rỗng ở bản nháp, index `han_chot` và `han_xu_ly`, 5 quyền mới.

Các điểm lệch còn lại cần xác nhận:

1. `signing_request.document_type` có `DEFAULT 'vanbanden'`. Khi dữ liệu thiếu, văn bản đi hoặc mật bị ghi nhầm thành văn bản đến. Đề xuất bỏ giá trị mặc định.
2. Kiểu enum `signing_key_status` (`PENDING`, `ROTATED`...) không khớp trạng thái khóa dùng ở phân hệ (`CHO_KICH_HOAT`, `DA_XOAY_VONG`...), và cột `signing_key.trang_thai` không dùng kiểu này. Đề xuất bỏ kiểu enum thừa hoặc đồng bộ giá trị.
3. Tổng số lượt phân quyền: tiêu đề file ghi 178, phản hồi issue ghi 198. Header file ghi 73 quyền nhưng tiêu đề mục seed ghi 66. Danh sách quyền `send_trinhky`, `delegate_trinhky`, `cancel_trinhky`, `view_signing_audit` xuất hiện lặp hai lần trong danh sách quyền của nhóm `BGD` ở phần seed (không gây lỗi do `ON CONFLICT DO NOTHING`, nhưng làm sai lệch cách đếm).
4. Trigger `prevent_delete_or_tamper_signing_signature` chỉ so 9 cột; `ghi_chu_ky`, `ky_tre_han`, `so_giay_tre`, `created_at` vẫn sửa được ở DB, trong khi model chỉ cho đổi `trang_thai_xac_minh` và `thoi_diem_xac_minh`. Đề xuất chặn mọi cột trừ hai cột xác minh.
5. `ON DELETE` của DDL lệch model (PROTECT) ở `signing_attempt.trinh_ky_id` (CASCADE), `signing_attempt.luot_truoc_id` (SET NULL), `signing_request_step.luot_trinh_id` (CASCADE), `signing_request_step_signer.buoc_ky_id` (CASCADE), `signing_request_step_signer.uy_quyen_tu_id` (SET NULL), `signing_key.khoa_thay_the_id` (SET NULL). Đề xuất đổi sang `RESTRICT`.
6. DDL trỏ FK người dùng tới `accounts_employee`, còn migration nhánh 5 trỏ `auth_user`; DDL thêm FK cho `don_vi_id`, `chuc_vu_id` trong khi model là số nguyên. Chốt cùng Phase 6–7.
