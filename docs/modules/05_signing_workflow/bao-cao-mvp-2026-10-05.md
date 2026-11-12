# Báo cáo công việc Nhóm 5 — Trình ký (MVP, 05/10/2026)

Người thực hiện: Lê Thành Tài · Nhánh: `5_signing_workflow` · Từ `7f9b308` đến `6db7bbc`
Căn cứ: issue #64, #67, #68; plan `docs/modules/05_signing_workflow/`.

## 1. Tóm tắt

| Commit | Nội dung | Issue |
|---|---|---|
| `f866df7` | Phase 6a — Bảo vệ khóa ký bằng PIN (đặt PIN, mở khóa ký, đổi PIN) | plan mục 3.4 |
| `4690de7` | Phase 6b — Kiểm quyền API quy trình và khóa ký theo quyền trong DDL; đổi cột cho khớp DDL base | #64, #67 mục 6, #68 C3 |
| `6db7bbc` | Sửa lỗi: mỗi mã quy trình chỉ một phiên bản hoạt động; tăng tốc test | #68 |

Phạm vi MVP Nhóm 5 theo #68: **quy trình ký mẫu + khóa ký**. Tạo/gửi yêu cầu trình ký cần bảng văn bản Nhóm 2 nên thuộc Phase 7, chưa làm.

## 2. Chi tiết từng phần

### 2.1. PIN khóa ký (Phase 6a)
- 3 API mới:
  - `POST /api/v1/signing/khoa/{id}/dat-pin/` — đặt PIN lần đầu.
  - `POST /api/v1/signing/khoa/{id}/mo-khoa-ky/` — nhập PIN trước khi ký.
  - `POST /api/v1/signing/khoa/{id}/doi-pin/` — đổi PIN (phải đúng PIN cũ).
- Server **không nhận PIN**, chỉ nhận mã xác minh do trình duyệt tính từ PIN; lưu dạng băm HMAC.
- "Mảnh bí mật" (`k_srv`): chuỗi ngẫu nhiên 32 byte do server tạo, lưu mã hóa AES-256-GCM, chỉ trả khi nhập đúng PIN. Trình duyệt ghép với PIN để mở private key.
- Chống đoán PIN: sai 5 lần khóa 15 phút; sai 10 lần khóa hẳn (HTTP 423). Đếm đúng kể cả khi nhiều yêu cầu cùng lúc.
- Bảng mới `signing_key_unlock` (đã có trong DDL base v1).
- Mọi sự kiện PIN ghi vào nhật ký `signing_audit_log`.

### 2.2. Kiểm quyền (Phase 6b, sửa #64)
Trước đây chỉ cần đăng nhập là tạo và kích hoạt được quy trình. Nay kiểm theo quyền trong DDL:

| Thao tác | Quyền cần |
|---|---|
| Xem quy trình | `view_trinhky` (chỉ thấy bản đang hoạt động) hoặc `manage_signing_process` (thấy mọi trạng thái) |
| Tạo, kích hoạt, ngừng, nhân bản quy trình | `manage_signing_process` |
| Đăng ký, xác minh, kích hoạt, xoay vòng khóa; đặt/mở/đổi PIN | `sign_trinhky` |
| Xem và thu hồi khóa của chính mình | Chỉ cần đăng nhập |

Theo nhóm quyền có sẵn trong DDL: chỉ **ADMIN** quản lý quy trình; **ADMIN, BGD, TP** có khóa ký; **CV, VT** chỉ xem.

- Tệp mới `backend/apps/signing/permissions.py`: mọi kiểm quyền đi qua đây. Dùng RBAC của Nhóm 7 (`RbacBackend`) khi có; khi RBAC lên staging chỉ sửa tệp này.
- Thiếu quyền trả 403, mã lỗi `khong_co_quyen`, kèm tên quyền thiếu.
- Test tạo người dùng qua `get_user_model()`, không còn import `auth.User` (#68 mục C3).

### 2.3. Khớp DDL base v1 (#67 mục 6)
- `signing_key_unlock`: đổi cột `update_at` → `updated_at` cho khớp DDL.
- So tự động 15 bảng `signing_*` giữa DB nạp DDL và DB dựng bằng migration: khớp bảng, cột, ràng buộc. `migrate signing --fake` chạy sạch.

### 2.4. Sửa lỗi phiên bản quy trình
- Lỗi cũ: kích hoạt phiên bản 2 thì phiên bản 1 vẫn hoạt động → một mã có 2 bản chạy song song, người trình ký có thể chọn nhầm.
- Nay: kích hoạt bản mới thì bản cũ **tự chuyển Ngừng** trong cùng giao dịch, ghi nhật ký bản thay thế; yêu cầu đã tạo từ bản cũ không bị ảnh hưởng.

### 2.5. Tăng tốc test
- Test không còn băm mật khẩu cho tài khoản thử: bộ test `signing` chạy **0,8 giây** thay vì ~5 phút.

## 3. Kiểm thử

| Kiểm tra | Kết quả |
|---|---|
| `manage.py check`, `makemigrations --check` | Sạch |
| `manage.py test signing` trên SQLite | 126/126 đạt (1 test chỉ chạy trên PostgreSQL) |
| `manage.py test signing` trên PostgreSQL + `Employee` + RBAC Nhóm 7 | 126/126 đạt |
| Gọi API thật (đăng nhập JWT) trên DB dựng từ DDL base | Tất cả các bước đúng như mong đợi |

Luồng đã chạy thử: CV bị chặn tạo quy trình (403) → ADMIN tạo, kích hoạt, nhân bản → kích hoạt bản 2 thì bản 1 tự ngừng → CV bị chặn đăng ký khóa (403) → TP đăng ký khóa, chứng minh sở hữu, kích hoạt → đặt PIN → nhập sai (còn 4 lần) → nhập đúng nhận mảnh bí mật → nhật ký ghi đủ 8 sự kiện.

## 4. Tệp thay đổi

- Mới: `backend/apps/signing/services/pin.py`, `permissions.py`, `migrations/0003_mo_khoa_ky_bang_pin.py`, `tests/test_pin_phase6.py`, `tests/helpers.py`.
- Sửa: `models.py`, `crypto.py`, `serializers.py`, `views.py`, `urls.py`, `services/process.py`, các tệp test, `config/settings.py` (biến `SIGNING_PIN_SECRET`), `.env.example`.
- Tài liệu: `plan-trien-khai-theo-phase.md` (Phase 6a, 6b, mục 5 đối chiếu DDL), `signing-backend-plan.md` (mục 3.1, 5.2, 7.4).

## 5. Việc còn lại

| Việc | Phụ thuộc |
|---|---|
| Lên `staging` | Nhóm 7 đưa `Employee` + RBAC lên staging (#68 C1, C2) |
| Quản trị mở lại PIN bị khóa hẳn | Chưa làm; người dùng vẫn tự thu hồi khóa và đăng ký khóa mới được |
| Cột ảnh chữ ký `anh_chu_ky` | Chưa chốt với Nhóm 7 (#67 mục 2) |
| Yêu cầu trình ký, lượt trình (Phase 7) | Bảng văn bản Nhóm 2 lên staging |
| Ký, từ chối, thu hồi chữ ký; thông báo; giao diện; Argon2id ở trình duyệt (Phase 8–10) | Sau Phase 7 |

## 6. Cấu hình khi triển khai
- Đặt biến môi trường `SIGNING_PIN_SECRET` riêng trên staging/production (để trống thì dùng `SECRET_KEY`, chỉ dành cho máy dev). Đổi giá trị này làm mọi PIN đã đặt mất hiệu lực.
- DB dựng từ DDL: chạy `python manage.py migrate signing --fake` theo quy trình ở #68 mục 2.
