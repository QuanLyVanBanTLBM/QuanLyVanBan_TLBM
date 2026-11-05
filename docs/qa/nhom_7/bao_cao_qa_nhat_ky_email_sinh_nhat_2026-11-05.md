# Báo cáo QA/UAT: Nhật ký email chúc mừng sinh nhật

**Ngày kiểm thử:** 05/11/2026
**Issue:** #576
**Nhánh kiểm thử:** `fix/576-birthday-email-log-date-filter`

## Phạm vi và môi trường

- Backend: PostgreSQL 16 cục bộ; bộ test sinh nhật chạy trên database test riêng, được tạo và hủy bởi Django test runner.
- Email trong test: `django.core.mail.backends.locmem.EmailBackend`; không gửi SMTP thật.
- Frontend: test Vitest và bản xem trước component cục bộ. Ảnh xem trước dùng dữ liệu minh họa và đã hiển thị trong hội thoại; ảnh không được lưu thành tệp do chính sách browser chặn thao tác lưu screenshot.
- Staging: kiểm tra chỉ đọc tại `http://staging-quanlyvanban.bhbl.vn:8088/birthdays`. Bản đang chạy chưa có thay đổi của nhánh này.

## Kết quả các ca nghiệp vụ

| # | Ca kiểm thử | Kết quả và bằng chứng |
|---|---|---|
| 1 | Hôm nay chưa có nhật ký | Đạt ở frontend: trạng thái trống và tổng 0 được kiểm tra bằng test. |
| 2 | Ngày được chọn có 2 nhật ký | Đạt ở backend: truy vấn ngày Việt Nam trả đúng 2 bản ghi thuộc ngày yêu cầu. |
| 3 | Không đưa bản ghi ngày trước/sau vào kết quả | Đạt ở backend: test ranh giới loại bản ghi ngay trước đầu ngày và tại đầu ngày kế tiếp. Staging bản cũ vẫn đang hiển thị dữ liệu nhiều ngày. |
| 4 | Tra cứu ngày quá khứ | Đạt: API nhận `date=YYYY-MM-DD` và trả ngày được chọn. |
| 5 | Kết hợp ngày và trạng thái | Đạt: bộ lọc trạng thái `PENDING` trên ngày được chọn trả đúng 1 bản ghi. |
| 6 | Tải lại nhật ký không gửi email | Đạt ở frontend: tải lại phát sinh GET nhật ký; test xác nhận không gọi POST gửi email. Không gửi email thật. |
| 7 | Chuyển ngày lúc 00:00 Việt Nam | Đạt ở frontend: test chuyển từ 16:59 UTC sang 17:00 UTC và tự đổi ngày khi đang theo dõi hôm nay. Ngày lịch sử được giữ nguyên. |
| 8 | Chống gửi trùng và retry | Không thay đổi mã gửi, scheduler hoặc retry. Các test hiện có về xử lý song song, retry và log đang gửi đều qua trong bộ test sinh nhật. |
| 9 | Mốc UTC sát ranh giới ngày Việt Nam | Đạt ở backend: test dùng `16:59:59.999999 UTC` và `17:00:00 UTC`; khoảng lọc là đầu ngày bao gồm đến đầu ngày sau không bao gồm. |
| 10 | Hồi quy phân hệ sinh nhật | Đạt: 31/31 test backend của app `birthdays` qua trên PostgreSQL 16. |

## Responsive và kiểm tra staging

- Desktop đã xem ở 1366×768, 1920×1080, 1280×720 và 2560×1440.
- Viewport mobile/tablet mô phỏng trong Edge đã xem ở 360×800, 375×667, 390×844, 412×915, 430×932 và 768×1024. Chiều rộng trang khớp viewport; bảng cuộn ngang bên trong trên màn hình hẹp.
- Kiểm tra mobile là viewport emulation trên Edge, không phải thiết bị Android/iOS thật.
- Trên staging hiện tại, bộ lọc ngày và nút “Hôm nay” chưa xuất hiện; bảng vẫn gộp 9 nhật ký của các ngày 02–04/11/2026. Nhấn tải lại giữ nguyên 9 bản ghi. Đây là kết quả của bản staging trước thay đổi, nên UAT staging sau triển khai chưa thể thực hiện.
- Console browser không ghi nhận lỗi trong lần mở trang staging. Chưa xác minh trực tiếp API hoặc database staging; không đọc/ghi dữ liệu staging.

## Cổng kỹ thuật đã chạy

- `pnpm run test`: **850/850 test qua**, 77 file.
- `pnpm run lint`: không có lỗi; có 3 cảnh báo dependency `handleLoadError` sẵn có tại `frontend/src/pages/organizations/OrganizationsPage.tsx`.
- `pnpm run check:i18n`: qua, 2651 key / 18 module.
- `pnpm run check:tokens`: qua, 8 tệp CSS.
- `pnpm run build`: qua; Vite có cảnh báo một số chunk lớn hơn 500 kB.
- `python backend/manage.py check`: qua, không có vấn đề.
- `python backend/manage.py makemigrations --check --dry-run`: qua, không phát sinh migration.
- `python backend/manage.py test birthdays --verbosity=2`: **31/31 test qua** trên PostgreSQL 16.
- `git diff --check`: qua.

## Giới hạn còn lại

- `migrate --check` trên database phát triển cục bộ không qua do database đang thiếu migration của các app `accounts`, `authorization`, `organizations` và `signing`. Không chạy `migrate` để tránh thay đổi database cục bộ; database test riêng đã được dựng qua migration bởi test runner.
- Chưa chạy toàn bộ backend test suite hoặc đối chiếu schema DDL. PR không thay đổi schema hay migration.
- Chưa xác nhận bản mới trên staging, SMTP thật, scheduler production, thiết bị mobile thật hoặc hành vi lỗi mạng qua browser. Các mục này cần CI và UAT sau khi PR được merge/deploy.
- Không lưu ảnh staging thành tệp. Ảnh xem trước component hiển thị trong hội thoại chỉ xác nhận bố cục; dữ liệu trong ảnh là dữ liệu minh họa.
