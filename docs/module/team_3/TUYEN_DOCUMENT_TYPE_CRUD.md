# Hoàn thiện CRUD Loại văn bản

## Mục tiêu và phạm vi

Trang Loại văn bản đã có danh sách và điều hướng sang module văn bản, nhưng chưa có thao tác thêm, sửa và xóa. Thay đổi bổ sung CRUD trên danh mục độc lập và danh mục theo hồ sơ, sử dụng API hiện hữu. Thao tác tạo ở danh mục độc lập yêu cầu chọn hồ sơ cha.

Phạm vi frontend Nhóm 3. Tìm kiếm tức thời được giao riêng và không nằm trong thay đổi này. Backend, DDL và dependency của repository không thay đổi.

## Hành vi giao diện

- Thêm và sửa bằng `RecordModal` ở chế độ Loại văn bản; tên bắt buộc và được trim trước khi gửi.
- Danh mục độc lập tải các trang danh sách hồ sơ để chọn hồ sơ cha. Danh mục theo hồ sơ sử dụng hồ sơ trong URL.
- Trường ngày lập nhận sự kiện `input` và `change`; ngày, tên và ghi chú được đưa vào payload.
- Trong khi lưu, form và nút bị khóa; các lần submit trùng không tạo thêm request.
- Lỗi validation và thiếu quyền hiển thị trong form, giữ nguyên dữ liệu đang nhập.
- Xóa có xác nhận. Lỗi API, gồm trường hợp còn văn bản tham chiếu, giữ hộp xác nhận và bản ghi.
- Thành công hiển thị thông báo và tải lại danh sách; xóa dòng cuối ở trang sau chuyển về trang trước.
- Modal hỗ trợ Escape, vòng Tab và phục hồi focus khi hủy.
- Nút sửa và xóa không kích hoạt popup điều hướng văn bản của dòng.
- Chuỗi giao diện mới có đủ bản dịch Việt và Anh, dùng design tokens hiện hữu.

## Endpoint đã sử dụng

| Thao tác | Endpoint |
|---|---|
| Danh mục độc lập | `GET /api/records/document-types/` |
| Danh mục trong hồ sơ | `GET /api/records/dossiers/{ho_so_id}/document-types/` |
| Danh sách hồ sơ để chọn | `GET /api/records/dossiers/?page={page}&page_size=100` |
| Tạo loại văn bản | `POST /api/records/dossiers/{ho_so_id}/document-types/` |
| Sửa loại văn bản | `PATCH /api/records/document-types/{id}/` |
| Xóa loại văn bản | `DELETE /api/records/document-types/{id}/` |

Payload thêm/sửa: `ten_loai`, `ngay_lap`, `ghi_chu`. Hồ sơ cha của thao tác tạo lấy từ URL; không gửi thay đổi `ho_so` trong PATCH. API độc lập vẫn chỉ dùng GET. Quyền CRUD dùng các codename hồ sơ theo contract hiện hành.

## Kiểm chứng ngày 15/10/2026

| Kiểm tra | Kết quả |
|---|---|
| 5 file test Records, modal và service | 25 test đạt |
| ESLint các file thay đổi | Đạt |
| Toàn bộ frontend Vitest | 39 file, 249 test đạt |
| Toàn bộ frontend ESLint | Đạt |
| Toàn bộ frontend i18n và CSS tokens | Đạt, 1196 key đồng bộ; 3 file CSS |
| TypeScript `tsc -b` | Đạt |
| Build Vite | Đạt; còn cảnh báo chunk lớn của bundle chung |
| Records i18n | Đạt, 1196 key đồng bộ |
| Records design tokens | Đạt |
| Django `check` với `config.records_release` | Đạt |
| Smoke auth/JWT, RBAC và API Records trên PostgreSQL local | Đạt, dữ liệu smoke được rollback |
| UI thật: thiếu hồ sơ, tên toàn khoảng trắng | Chặn trước khi gửi |
| UI thật: tạo và tải lại danh sách | Đạt |
| UI thật: tên trùng trong hồ sơ, khác hoa thường/khoảng trắng | Hiển thị lỗi API, giữ dữ liệu form |
| UI thật: sửa tên, ghi chú, ngày lập | Đạt; ngày hiển thị theo múi giờ địa phương |
| UI thật: hủy xóa và xác nhận xóa | Đạt; danh sách cập nhật |
| UI xử lý HTTP 403/409 và chống submit trùng | Test tự động đạt |

Lệnh chạy từ `frontend`:

```powershell
node node_modules/vitest/vitest.mjs run src/pages/records src/components/records src/lib/recordsService.test.ts src/lib/recordsDocumentNavigation.test.ts
node node_modules/eslint/bin/eslint.js src/pages/records/DocumentTypesPage.tsx src/pages/records/DocumentTypesPage.test.tsx src/components/records/RecordModal.tsx src/components/records/RecordModal.test.tsx src/components/records/ConfirmDialog.tsx
node node_modules/typescript/bin/tsc -b
node node_modules/vite/bin/vite.js build
node scripts/records-check-i18n.mjs
node scripts/records-check-tokens.mjs
node node_modules/vitest/vitest.mjs run
node node_modules/eslint/bin/eslint.js .
node scripts/check-i18n.mjs
node scripts/check-css-tokens.mjs
```

## Môi trường local và giới hạn kiểm chứng

Kiểm chứng trên Windows, Python 3.13.16, Node 24.19.0, PostgreSQL 18. Database local được dựng từ release DDL, sao lưu trước adoption, kiểm chứng giữ nguyên 55 bảng nghiệp vụ và thêm 5 bảng hệ thống Django. Công cụ setup riêng của máy không thuộc PR; cấu hình, credential, log và database backup không được đưa vào Git.

Profile `config.records_release` phục vụ Auth và Records. Dashboard và API các nhóm khác không được bật trong profile này. Luồng tạo/lọc văn bản ở Nhóm 2 không nằm trong kiểm chứng CRUD Loại văn bản.

Kết quả trên là kiểm chứng local. CI trên GitHub, review và kiểm tra sau khi merge vào nhánh Nhóm 3 vẫn là các bước bàn giao còn lại; chưa chạy toàn bộ test backend liên nhóm.
