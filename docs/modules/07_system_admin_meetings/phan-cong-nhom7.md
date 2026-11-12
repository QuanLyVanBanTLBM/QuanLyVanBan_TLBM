# Phân công chi tiết & Quy tắc kỹ thuật — Nhóm 7 (bản 2026-09-27 v5)

*Lịch sử: v1 (gốc) → v2 (2026-09-19, Tân chốt lại Phòng họp/Sinh nhật) → v3 (2026-09-20, đổi chéo Khánh ↔ Quang, gộp Hiếu+Tình làm chung Phòng họp/Sinh nhật) → v4 (2026-09-27 sáng, tách riêng Hiếu/Tình, Hiếu chuyển sang hỗ trợ Phân quyền) → **v5 (2026-09-27, Tân chốt lại lần 5): Hiếu chuyển hẳn sang phụ Tân làm Phân quyền full-time; Phòng họp giao lại cho Nguyễn Duy Bảo (mượn từ Nhóm 6) làm lại từ đầu — PR #27 cũ của Hiếu không dùng nữa.** Module gốc thầy giao: Phòng họp (0.40), Sinh nhật (0.40), Hệ thống (0.80: Đơn vị/phòng ban, Chức vụ, CBNV, Phân quyền). "Loại tài liệu biểu mẫu" đã chuyển hẳn cho Nhóm 4, không còn thuộc Nhóm 7.*

> ⚠️ **Cần báo PM (Châu Tuấn Kiệt) trước khi Bảo bắt đầu code:** Nguyễn Duy Bảo hiện thuộc quyền `team_6` trên GitHub, chưa có quyền PR vào branch `7_meeting_rooms_birthdays_system`. Cần PM/Admin thêm Bảo vào `team_7` (hoặc hướng dẫn Bảo fork riêng) trước.
> ⚠️ **PR #27 (Hiếu, Phòng họp) sẽ bị đóng, không merge** — dù đã pass 27/27 test. Cần báo Hiếu biết trước khi đóng PR.

## 1. Phân công

| Người | Phụ trách | Ghi chú |
| --- | --- | --- |
| Tô Thanh Tân (DA, Trưởng nhóm) | **Phân quyền** (nhóm quyền, gán quyền) + ERD/schema tổng toàn dự án — **có Hiếu phụ full-time** | Không đổi vai trò chính, Hiếu chuyển từ "hỗ trợ" sang phụ hẳn |
| Lê Duy Khánh | **CBNV** (cán bộ nhân viên) — Issue #20, chưa có PR | Không đổi. Đang chặn Phân quyền (Tân/Hiếu) và các module còn lại |
| Đỗ Mạnh Quang | **Đơn vị, phòng ban** (đã xong, PR #36 đã merge vào branch nhóm) + **Chức vụ** (chưa có PR) | Không đổi |
| Nguyễn Phan Minh Hiếu | **Phân quyền** — phụ Tân full-time | **Đổi so với v4** (trước còn giữ Phòng họp, nay giao hẳn cho Bảo) |
| Trần Đình Tình | **Sinh nhật** (hiển thị lịch, `SinhNhatLog` gửi mail) — làm riêng, đã hoàn thành (PR #30) | Không đổi so với v4 |
| **Nguyễn Duy Bảo** *(mượn từ Nhóm 6)* | **Phòng họp** (`PhongHop`, `DatPhongHop`) — làm lại từ đầu | **Mới** — thay thế PR #27 của Hiếu (không dùng nữa) |

## 2. Chi tiết chức năng & field theo module (nguồn: bảng spec thầy giao)

### Phòng họp (độ khó 0.40) — Nguyễn Duy Bảo (mượn Nhóm 6), làm lại từ đầu
- Thêm phòng họp; danh sách phòng họp theo ngày...
- *Ghi chú field DB:* DB cho phòng họp.
- *Trạng thái:* PR #27 cũ của Hiếu (đã pass 27/27 test, tạm dùng `auth.User` thay CBNV) không dùng nữa — Bảo code lại từ đầu. Cần chờ PM thêm quyền `team_7` cho Bảo trước khi mở PR.

### Sinh nhật (độ khó 0.40) — Tình, đã hoàn thành (PR #30)
- Hiển thị theo ngày tháng sinh dạng calendar (tham khảo mẫu thầy gửi).
- Gửi mail chúc mừng sinh nhật tự động khi tới ngày — tự thiết kế mẫu email.
- *Ghi chú field DB:* lấy ngày sinh từ thông tin của user (CBNV).

### Hệ thống (độ khó 0.80)

**Trang Đơn vị, phòng ban** (Quang phụ trách):
- Thêm Khối/Khu vực (Cấp 1): id, tên khối/khu vực.
- Thêm Đơn vị, phòng ban (Cấp 2): chọn khối/khu vực, tên đơn vị/phòng ban, địa chỉ, điện thoại, email.
- Danh sách lấy theo số thứ tự ưu tiên; có tìm kiếm; có xuất Excel.
- **Field:** STT ưu tiên hiển thị(*) — kiểm tra trùng, tự động lấy số lớn nhất + 1; Tên đơn vị/phòng ban(*) — text; Địa chỉ — text; Điện thoại — số; Email; isPublic(*) — mặc định true (false vẫn hiện cho admin nhưng đổi màu); Ghi chú.

**Trang danh mục Chức vụ** (Quang phụ trách):
- Thêm chức vụ; danh sách lấy theo số thứ tự ưu tiên; import file mẫu (tải về rồi import lên); tìm kiếm.
- **Field:** STT ưu tiên hiển thị(*) — kiểm tra trùng, tự động max+1; Tên chức vụ(*); isPublic(*) — mặc định true; Ghi chú.

**Trang CBNV** (Khánh phụ trách):
- Có tên đăng nhập, mật khẩu. Thêm CBNV mới.
- Danh sách lấy theo thứ tự: đơn vị/phòng ban có ưu tiên → chức vụ. Cột hiển thị: STT, Họ và tên, Đơn vị, Chức danh, Nhóm quyền (**chỉ admin thấy cột này**), Email, SĐT cá nhân/bàn, Trạng thái (Làm việc/Nghỉ việc — **bôi đỏ nếu nghỉ việc**), Thao tác (sửa/xóa).
- Import file mẫu; Chi tiết CBNV dạng popup (hiển thị hết thông tin nhưng **che năm sinh**); có phân trang.
- **Quy tắc mật khẩu khi Import Excel:** Tài khoản tạo hàng loạt qua Excel sẽ nhận mật khẩu tạm thời ngẫu nhiên an toàn sinh từ hệ thống. Cán bộ nhân viên sau đó nhận tài khoản và chủ động lấy lại/thiết lập mật khẩu qua tính năng Quên mật khẩu / Cấp lại mật khẩu của hệ thống (hoặc được Quản trị viên duyệt cấp lại mật khẩu qua quyền `approve_password_reset_cbnv`).
- **Field:** Họ và tên(*); Ngày tháng năm sinh(*) — lưu đủ ngày nhưng giao diện ẩn năm sinh; Chức vụ(*) — chọn từ danh sách (FK); Chức danh — text tự do, khác Chức vụ; Nhóm quyền(*) — chọn từ danh sách; Email; SĐT; Đơn vị(*) — chọn từ danh sách (FK); Mật khẩu IT cấp — chỉ admin thấy khi cấp; isPublic(*) — mặc định true; Ghi chú.

**Trang Phân quyền** (Tân + Hiếu phụ trách):
- Danh sách nhóm quyền; thêm/xóa/sửa nhóm quyền; danh sách phân quyền sử dụng theo từng nhóm.
- Theo đề bài thầy (mục 7.7): giao diện phải có dạng **ma trận phân quyền** (hàng = module, cột = hành động Xem/Thêm/Sửa/Xóa/Duyệt/Ký...), không chỉ list checkbox phẳng.
- *Ghi chú:* tạo bảng DB (Group/Permission theo chuẩn `django.contrib.auth`), không tự chế model riêng.

## 3. Thứ tự làm để tránh chồng chéo/block nhau

| Đợt | Việc | Ai | Trạng thái |
| --- | --- | --- | --- |
| Đợt 1 (đã làm) | Đơn vị/Khối; Sinh nhật | Quang; Tình | Đã xong, PR #36 / #30 |
| Đợt 1 (đang làm) | Nhóm quyền (Phân quyền, Issue #21) | Tân + Hiếu | Đang code |
| Đợt 1 (chưa làm) | Chức vụ | Quang | Chưa có PR |
| Đợt 1 (chưa làm, mới) | Phòng họp (`PhongHop`+`DatPhongHop`) | Nguyễn Duy Bảo (mượn Nhóm 6) | Chưa có PR — chờ PM cấp quyền `team_7` trước |
| Đợt 2 (đang chặn) | CBNV (Issue #20) | Khánh | **Chưa có PR — đang chặn Phân quyền hoàn thiện (FK Employee↔Group) và việc đổi `SinhNhatLog`/`DatPhongHop` sang FK CBNV thật khi làm xong** |

**Vì sao CBNV vẫn là bottleneck:** Tình đã tự implement xong Sinh nhật bằng cách tạm dùng `auth.User` mặc định của Django thay cho CBNV thật (vì CBNV chưa tồn tại). Bảo khi code Phòng họp mới cũng sẽ gặp tình huống tương tự nếu CBNV chưa xong. Khi Khánh hoàn thành `accounts.Employee` (Issue #20) và đổi `AUTH_USER_MODEL`, các module này cần 1 đợt sửa lại FK (`nguoi_dat`, `cbnv`) để trỏ đúng vào CBNV.

## 4. Cảnh báo va chạm với NHÓM KHÁC

- ~~"Loại tài liệu biểu mẫu" và app `resources` với Nhóm 4~~ — đã giải quyết: chuyển hẳn phần này cho Nhóm 4, không còn cảnh báo conflict Git ở đây.
- Mọi module khác (Văn bản, Hồ sơ, Công việc, Trình ký...) đều FK tới Đơn vị/CBNV/Phân quyền của Nhóm 7 → nhóm 7 nên báo trước cho cả lớp field/tên bảng chính thức để tránh mỗi nhóm tự đặt tên khác nhau rồi phải sửa lại.
- ⚠️ **Theo `FRONTEND_BASELINE_GUIDE.md` (Nhóm 1/DevOps, đã merge vào `staging`):** Nhóm 1 không tự đặt role/permission riêng — hợp đồng phân quyền (contract) do Nhóm 7 cung cấp. Các nhóm khác đang chờ Tân/Hiếu chốt cấu trúc RBAC để tích hợp — **việc Phân quyền cần ưu tiên cao nhất**.
- ⚠️ Khi Khánh xong CBNV (Issue #20): Bảo (Phòng họp) và Tình (Sinh nhật) cần branch mới từ code nhóm mới nhất để đổi FK `auth.User` → `accounts.Employee`, không sửa trên branch cũ đã lỗi thời.
- ⚠️ **Bảo (mượn từ Nhóm 6) chưa có quyền `team_7`** — không thể fork/PR vào branch `7_meeting_rooms_birthdays_system` cho đến khi PM (Châu Tuấn Kiệt) hoặc Admin cấp quyền. Báo trước khi Bảo bắt đầu code để tránh code xong không push được.

## 5. Quy tắc kỹ thuật áp dụng cho MỌI module của Nhóm 7

**Validate (bắt buộc ở Backend, dù JS đã validate rồi):**
- Không tin dữ liệu từ client — JS có thể bị tắt hoặc bị bypass bằng gọi API trực tiếp (Postman...). Validate lại 100% ở Django serializer/form.
- Trong bảng mô tả field của thầy: có dấu **(*)** = bắt buộc nhập (`required=True`, `null=False, blank=False`); không có dấu (*) = không bắt buộc.
- Field chọn từ danh sách (FK/dropdown) phải kiểm tra giá trị có tồn tại trong DB, không nhận giá trị tùy ý gửi lên.
- Field có "kiểm tra trùng" (STT ưu tiên...) phải validate unique trước khi lưu.
- Đúng định dạng: email → `EmailField`; ngày giờ → lưu đủ giờ:phút:giây; số điện thoại → validate regex VN.

**Giới hạn dung lượng khi POST/nhập liệu:**
- File đính kèm giới hạn dung lượng theo module, chặn cả FE lẫn BE (`FILE_UPLOAD_MAX_MEMORY_SIZE`, `DATA_UPLOAD_MAX_MEMORY_SIZE`).
- Text field đặt `max_length` hợp lý.
- Danh sách trả về API luôn phân trang, không trả toàn bộ bảng 1 lần.

**CSRF:**
- Mọi form/API có thao tác ghi (POST/PUT/PATCH/DELETE) bắt buộc gửi kèm CSRF token, thiếu/sai token → 403 Forbidden.
- FE lấy token từ cookie Django, gửi qua header `X-CSRFToken`.

**Thông báo trạng thái (UX):**
- Mọi thao tác Thêm/Sửa/Xóa phải có 3 trạng thái: đang xử lý → thành công (thông báo rõ) → thất bại (lý do cụ thể, không chỉ "Có lỗi xảy ra").

**Quy tắc URL:** tiếng Anh, số nhiều kebab-case (`/organizations/`, `/positions/`, `/employees/`, `/permissions/`, `/meetings/`, `/meeting-bookings/`, `/birthdays/`), không dùng tiếng Việt có dấu.

**Danh sách nhiều cấp** (Khối → Đơn vị): mỗi cấp có ô tìm kiếm + phân trang riêng.

**Nguồn dữ liệu tự động:** "Người lập/Người tạo" → lấy từ tài khoản đăng nhập; "STT ưu tiên" → tự động max+1; các field khác lấy trực tiếp từ form.

## 6. Quy tắc Git — tóm tắt nhanh

**Mô hình:** `main` (tích hợp cuối) ← `staging` (tích hợp chung) ← branch nhóm (`7_meeting_rooms_birthdays_system`...) ← `feat/<task>` trên fork cá nhân.

**Quyền:** Thành viên (`team_7`) = Read, phải fork + PR vào branch nhóm. Trưởng nhóm (Tân) = Write, push thẳng branch nhóm, merge PR thành viên, mở PR nhóm → staging. Admin/owner merge staging → main.

**Quy trình 1 task:**
```bash
git worktree add -b feat/<task> ../qlvb-<task> upstream/7_meeting_rooms_birthdays_system
cd ../qlvb-<task>
git branch --show-current
# code, test/lint/build
git add <file-cụ-thể>
git commit -m "feat: mô tả thay đổi"
git push -u fork HEAD
# → mở PR: fork:feat/<task> → QuanLyVanBanTLBM/QuanLyVanBan_TLBM:7_meeting_rooms_birthdays_system
```

**Cấm/hạn chế:** không `git push --force` (chỉ `--force-with-lease` trên fork) · không `git reset --hard` tùy tiện · không code/commit trực tiếp trên `main`/`staging` · không `git add .`/`-A` bừa bãi · không commit secret/`.env`/token.

*(Bản đầy đủ 10 mục về Git, xử lý conflict, quy trình reviewer: xem tài liệu Git workflow chính thức của repo.)*
