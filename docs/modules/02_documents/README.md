# Tài Liệu Đặc Tả Kỹ Thuật & Kế Hoạch Nghiệp Vụ — Module 02: Quản Lý Văn Bản (Nhóm 2)

> **Đơn vị phụ trách**: Nhóm 2 — Module Quản Lý Văn Bản (Văn bản Đến, Văn bản Đi)  
> **Trưởng nhóm**: Lê Trí Kiệt  
> **Thành viên**: Nguyễn Anh Đô, Nguyễn Tấn Lộc Khiêm, Trần Nhật Tân  
> **Thư mục tài liệu**: `docs/modules/02_documents/`  
> **Căn cứ tham chiếu**: `docs/common/database/release_DDL.sql` (PR #92), Issue #82, Issue #83, Plan tổng #68.

---

## 🏛️ 1. Kiến Trúc Dữ Liệu Cốt Lõi (Database Architecture chuẩn DDL)

Theo quyết định thống nhất từ GVHD (PR #92, Issue #82, Issue #83), phân hệ đã **bỏ văn bản mật hành chính và bỏ độ khẩn**. CSDL được chuẩn hóa thành 2 bảng thực thể chính tương ứng với 2 luồng nghiệp vụ Đến / Đi:

1. **`VanBanDen` (`documents_vanbanden`):**
   - Quản lý toàn bộ văn bản từ ngoài gửi đến trường.
   - Định danh: `id` (BigAutoField).
   - Số thứ tự tự tăng: `so_thu_tu` ("Số đến" tự tăng theo năm `nam`, khóa cứng khi cập nhật).
   - Mốc thời gian: `ngay_den` (DateTimeField), `ngay_van_ban`, `ngay_het_hieu_luc`.
   - Thuộc tính phạm vi: `pham_vi` (`NOI_BO` | `HAN_CHE`), mặc định `NOI_BO`.
   - Check constraints: `chk_vanbanden_pham_vi`, `chk_vanbanden_han_che_khong_mail_toan_he_thong`.

2. **`VanBanDi` (`documents_vanbandi`):**
   - Quản lý toàn bộ văn bản nội bộ trường phát hành.
   - Định danh: `id` (BigAutoField).
   - Số thứ tự tự tăng: `so_thu_tu` ("Số đi" tự tăng theo năm `nam`, concurrency-safe lock, khóa cứng khi cập nhật).
   - Mốc thời gian: `ngay_ban_hanh` (DateTimeField bắt buộc), `ngay_van_ban`, `ngay_het_hieu_luc`.
   - Thuộc tính phạm vi: `pham_vi` (`NOI_BO` | `HAN_CHE`), mặc định `NOI_BO`.
   - Check constraints: `chk_vanbandi_pham_vi`, `chk_vanbandi_han_che_khong_mail_toan_he_thong`.

3. **`DocumentAccessLog` (`documents_access_log`) — Bảng nhật ký kiểm toán WORM:**
   - Ghi nhận truy vết đối với văn bản có `pham_vi = 'HAN_CHE'`.
   - Các hành động: `XEM`, `TAI_FILE`, `BI_TU_CHOI`, `THEM_NGUOI_XEM`, `BOT_NGUOI_XEM`.
   - Nguyên tắc WORM (Write-Once-Read-Many): Cấm sửa và cấm xóa dòng nhật ký.

4. **`DocumentViewLog` (`documents_view_log`):**
   - Ghi nhận và đếm lượt đọc đối với các văn bản nội bộ thông thường (`pham_vi = 'NOI_BO'`).

---

## 🔒 2. Quy Tắc Nghiệp Vụ Chuẩn Văn Bản Hạn Chế (Issue #82 & #83)

| Nội dung | Văn bản thường (`NOI_BO`) | Văn bản hạn chế (`HAN_CHE`) |
|---|---|---|
| **Người xem** | Có quyền `view_vanbanden` / `view_vanbandi` hoặc admin/staff | **CHỈ người tạo + người nhận được chọn đích danh (`nguoi_nhan`)**. Superuser và quyền `view_*` không có ngoại lệ. |
| **Không có quyền** | Trả về theo phân quyền | **404 Not Found** (như văn bản không tồn tại). Ghi log `BI_TU_CHOI`. |
| **Tài khoản bị khóa** | Theo quyền | `is_active = FALSE` mất quyền xem toàn bộ. |
| **Gửi mail toàn trường** | Được phép | **Cấm tuyệt đối**. Form ẩn lựa chọn gửi mail. |
| **Trình ký** | Có luồng ký nháy / ký chính | **Không đi qua trình ký**. |
| **Đổi phạm vi, Xóa** | Không đổi `pham_vi` | Không đổi `pham_vi`, **cấm xóa** (DDL và Model chặn). |
| **Danh sách người xem** | Không áp dụng | Chỉ người tạo được thêm/bớt người xem. Tự động ghi log `THEM_NGUOI_XEM` / `BOT_NGUOI_XEM`. |

---

## 📡 3. Hàm Dùng Chung & API Endpoints (`selectors.py` & `/api/documents/`)

### 3.1. Hàm dùng chung cho các phân hệ khác (`apps/documents/selectors.py`)
- `van_ban_xem_duoc(user, loai)`: Điểm kiểm soát duy nhất cho Nhóm 1 (Dashboard), Nhóm 3 (Hồ sơ), Nhóm 6 (Công việc) để lấy danh sách văn bản người dùng được phép xem.
- `la_nguoi_xem_duoc(user, van_ban)`: Hàm kiểm tra boolean cho Nhóm 6 trước khi giao việc từ văn bản hạn chế.

### 3.2. Danh sách API Endpoints
| Method | Endpoint | Quyền hạn | Mô tả |
| :---: | :--- | :---: | :--- |
| `GET` | `/api/documents/?loai=DEN` (hoặc `DI`) | Đăng nhập | Danh sách văn bản được phép xem theo `van_ban_xem_duoc` |
| `POST` | `/api/documents/` | `add_vanbanden`/`add_vanbandi` | Tạo mới văn bản (tự sinh STT, ghi log người xem ban đầu nếu `HAN_CHE`) |
| `GET` | `/api/documents/{id}/` | Đăng nhập | Xem chi tiết văn bản (404 nếu không được xem văn bản `HAN_CHE`, ghi log tương ứng) |
| `PUT/PATCH` | `/api/documents/{id}/` | Người tạo / Admin | Cập nhật văn bản (chặn đổi `pham_vi`, diff ghi log thêm/bớt người xem) |
| `DELETE` | `/api/documents/{id}/` | Quyền xóa | Xóa văn bản thường (chặn xóa văn bản `HAN_CHE`) |
| `GET` | `/api/documents/{id}/attachments/{tep_id}/download/` | Đăng nhập | Tải file đính kèm (ghi log `TAI_FILE` hoặc `BI_TU_CHOI`) |
| `GET` | `/api/documents/{id}/viewers/` | Đăng nhập | Xem danh sách cán bộ đã đọc văn bản nội bộ |
| `GET` | `/api/documents/template/?loai=...` | Đăng nhập | Xuất file Excel mẫu trực tiếp từ DB |
| `POST` | `/api/documents/import/` | `add_*` | Import văn bản từ file Excel |
| `GET` | `/api/documents/export/?loai=...` | Đăng nhập | Export danh sách văn bản theo bộ lọc |

---

## 🧪 4. Trạng Thái Kiểm Thử (Quality Gate)

- **Backend Django Check**: `python manage.py check` ➔ **0 issues (OK)**
- **Backend Unit Tests**: `python manage.py test documents` ➔ **54/54 tests PASS (100%)**
- **Frontend Vitest**: `npm test` ➔ **67/67 tests PASS (100%)**
- **Đồng bộ mã nguồn**: Đã đồng bộ hoàn chỉnh giữa upstream và nhánh phát triển của nhóm.
