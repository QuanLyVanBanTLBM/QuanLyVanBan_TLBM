# Kế Hoạch Triển Khai Phân Hệ Quản Lý Văn Bản Đến (Frontend View & Hiển Thị)

> **Người thực hiện**: Nguyễn Tấn Lộc Khiêm  
> **Vai trò**: Frontend View & Hiển thị (25% khối lượng Module 02_Documents)  
> **Căn cứ**: Bảng phân công nhiệm vụ Nhóm 2 (`BangPhanCong_Nhom2_ModuleVanBan.docx` — Mục I, II, III) & Đề cương `ITC - Django - QLVB&TL.md` (Mục 2.1)  
> **Git Branch chuẩn**: `feat/frontend-inbound-list-detail`  
> **Phương pháp làm việc**: Triển khai theo từng giai đoạn (Step-by-step), kiểm tra kỹ lưỡng từng bước trước khi sang giai đoạn tiếp theo.

---

## 📌 BẢNG THEO DÕI TIẾN ĐỘ TỪNG GIAI ĐOẠN

| Giai đoạn | Hạng mục công việc | File tác động | Trạng thái |
| :---: | :--- | :--- | :---: |
| **GĐ 1** | Chuẩn hóa Type Contract đầy đủ cho Văn bản & Bộ lọc | `frontend/src/types/document.ts` | ✅ **Hoàn thành** |
| **GĐ 2** | Xây dựng tiện ích format Datetime chuẩn `HH:mm:ss dd/MM/yyyy` & kích thước file | `frontend/src/lib/dateUtils.ts`<br>`frontend/src/lib/dateUtils.test.ts` | ✅ **Hoàn thành** |
| **GĐ 3** | Xây dựng Thanh tìm kiếm & Bộ lọc đa tiêu chí | `frontend/src/components/documents/FilterBar.tsx`<br>`frontend/src/components/documents/FilterBar.test.tsx` | ✅ **Hoàn thành** |
| **GĐ 4** | Xây dựng Bảng danh sách văn bản (đổi màu hết hiệu lực, menu ⋮, phân trang) | `frontend/src/components/documents/DocumentTable.tsx`<br>`frontend/src/components/documents/DocumentTable.test.tsx` | ✅ **Hoàn thành** |
| **GĐ 5** | Xây dựng Modal Xem chi tiết & Modal Theo dõi người đã đọc | `frontend/src/components/documents/DocumentDetailModal.tsx`<br>`frontend/src/components/documents/DocumentViewersModal.tsx` | ✅ **Hoàn thành** |
| **GĐ 6** | Hoàn thiện Trang điều phối chính & Kết nối Route chính thức | `frontend/src/pages/InboundDocumentPage.tsx`<br>`frontend/src/app/router.tsx` | ✅ **Hoàn thành** |
| **GĐ 7** | Kiểm thử giao diện trên trình duyệt (2 theme Dark/Light) & nghiệm thu | Toàn bộ phân hệ (Build 4.76s, 63/63 tests PASS) | ✅ **Hoàn thành** |

---

## 🎯 1. BÁO CÁO HIỆN TRẠNG DỰ ÁN

### 1.1. Backend đã hoàn thiện 100%:
- **Lê Trí Kiệt (Backend Core)**: Models `Document`, `DocumentAttachment`, `DocumentViewLog` tại `apps/documents/models.py`; phân quyền văn bản mật; quản trị Admin.
- **Nguyễn Anh Đô (Backend Service)**: Logic tự sinh số đến `so_thu_tu`; bộ lọc đa tiêu chí `DocumentFilter` (`q`, `nam`, `tu_ngay`, `den_ngay`, `hieu_luc`); API viewers `GET /api/documents/{id}/viewers/`; dịch vụ Excel (template, import, export). Đạt **23/23 tests PASS (100%)**.

### 1.2. Frontend nền tảng:
- Đã có hệ thống layout `MainLayout`, bảng màu CSS token 2 theme Dark/Light trong `global.css`.
- `apiClient.ts` tự động gán Bearer Token JWT và tự động refresh token khi gặp 401.

### 1.3. Phần của Nguyễn Tấn Lộc Khiêm:
- Đã khởi tạo 6 file khung sườn rỗng, cần viết mã nguồn hoàn chỉnh theo từng giai đoạn bên dưới.
- Đường dẫn `/documents/incoming` trong `router.tsx` đang tạm trỏ về `SyllabusPreview`, cần trỏ về `InboundDocumentPage` ở giai đoạn cuối.

---

## 🏗️ 2. CHI TIẾT TỪNG GIAI ĐOẠN TRIỂN KHAI

### 🔹 GIAI ĐOẠN 1: Chuẩn hóa Type Contract
- **File**: `frontend/src/types/document.ts`
- **Mục tiêu**: Định nghĩa kiểu dữ liệu khớp 100% với Django Serializer để Frontend và Backend đồng bộ tuyệt đối:
  - `DocumentType`: `'DEN' | 'DI' | 'MAT'`.
  - `DocumentStatus`: `'CON_HIEU_LUC' | 'HET_HIEU_LUC' | 'HET_VA_THAY_THE'`.
  - `DocumentAttachment`: `id`, `file`, `file_name`, `file_size`, `uploaded_at`.
  - `DocumentItem`: Cấu trúc văn bản trả về trong danh sách bảng.
  - `DocumentDetail`: Kế thừa `DocumentItem` kèm toàn bộ thông tin chi tiết và danh sách file đính kèm.
  - `DocumentViewer`: Thông tin cán bộ đã xem (`id`, `user_id`, `username`, `full_name`, `chuc_danh`, `don_vi`, `viewed_at`).
  - `DocumentFilterParams`: Các tham số lọc (`q`, `nam`, `tu_ngay`, `den_ngay`, `hieu_luc`, `page`, `page_size`).
  - `PaginatedResponse<T>`: Cấu trúc phân trang chuẩn từ Django REST Framework (`count`, `next`, `previous`, `results`).

---

### 🔹 GIAI ĐOẠN 2: Tiện ích Định dạng Ngày Giờ & Dung Lượng File
- **File**: `frontend/src/lib/dateUtils.ts`
- **Mục tiêu**:
  - Tuân thủ quy định bắt buộc của Thầy giảng viên: *"Định dạng ngày tháng bắt buộc phải lưu và hiển thị kèm cả Giờ : Phút : Giây"*.
  - Hàm `formatDateTime(dateStr)` trả về chuẩn `HH:mm:ss dd/MM/yyyy`.
  - Hàm `formatDate(dateStr)` trả về `dd/MM/yyyy`.
  - Hàm `formatFileSize(bytes)` hiển thị `KB`, `MB` cho file đính kèm.

---

### 🔹 GIAI ĐOẠN 3: Thanh Tìm Kiếm & Bộ Lọc Đa Tiêu Chí
- **File**: `frontend/src/components/documents/FilterBar.tsx`
- **Mục tiêu**:
  - Ô tìm kiếm từ khóa `q` (tìm theo số hiệu, trích yếu, nơi gửi).
  - Dropdown chọn Năm phát hành `nam` (mặc định năm hiện tại 2026, các năm trước).
  - 2 ô Date Picker lọc khoảng ngày đến: `tu_ngay` -> `den_ngay`.
  - Dropdown trạng thái Hiệu lực `hieu_luc` (Tất cả, Còn hiệu lực, Hết hiệu lực, Hết hiệu lực & thay thế).
  - Nút "Tìm kiếm" và nút "Đặt lại" (Reset).
  - Hỗ trợ đầy đủ 2 giao diện Sleek Dark & Clean Light.

---

### 🔹 GIAI ĐOẠN 4: Bảng Dữ Liệu Văn Bản Đa Năng
- **File**: `frontend/src/components/documents/DocumentTable.tsx`
- **Mục tiêu**:
  - Hiển thị đầy đủ các cột: Số đến, Số ký hiệu, Ngày văn bản, Ngày đến (`HH:mm:ss dd/MM/yyyy`), Trích yếu (rút gọn 2 dòng kèm tooltip), Nơi ban hành, Badge hiệu lực, Menu tác vụ 3 chấm ⋮.
  - **Đổi màu tối / làm mờ dòng** đối với các văn bản Hết hiệu lực (`opacity-70`, viền cảnh báo).
  - **Menu thao tác 3 chấm ⋮**:
    - "Xem chi tiết" ➔ Mở modal chi tiết.
    - "Người đã xem" ➔ Mở modal danh sách cán bộ đã đọc.
    - "Chỉnh sửa" ➔ Tự động khóa nếu là văn bản mật.
    - "Xóa" ➔ Xác nhận xóa an toàn.
  - **Phân trang (Pagination)**: Chuyển trang (Trước, Sau, các số trang) và chọn số lượng bản ghi 10/20/50.
  - Skeleton loading khi đang tải và giao diện trống (Empty state).

---

### 🔹 GIAI ĐOẠN 5: Modal Xem Chi Tiết & Modal Người Đã Đọc
- **Files**:
  - `frontend/src/components/documents/DocumentDetailModal.tsx`
  - `frontend/src/components/documents/DocumentViewersModal.tsx`
- **Mục tiêu**:
  - `DocumentDetailModal`: Mở popup gọi `GET /api/documents/{id}/` ➔ Hiển thị lưới 2 cột thông tin chi tiết, trích yếu đầy đủ, văn bản thay thế, danh sách file scan đính kèm với nút xem và tải file scan. *(Backend tự động ghi log đọc).*
  - `DocumentViewersModal`: Gọi `GET /api/documents/{id}/viewers/` ➔ Thống kê tổng số lượt xem, hiển thị danh sách cán bộ kèm chức danh, phòng ban và thời gian xem chính xác. Tích hợp ô tìm kiếm tên cán bộ và lọc theo phòng ban ngay trong popup.

---

### 🔹 GIAI ĐOẠN 6: Trang Quản Lý Chính & Kết Nối Route
- **Files**:
  - `frontend/src/pages/InboundDocumentPage.tsx`
  - `frontend/src/app/router.tsx`
- **Mục tiêu**:
  - `InboundDocumentPage`: Quản lý toàn bộ State dữ liệu, gọi API Backend, truyền dữ liệu vào `FilterBar` và `DocumentTable`, điều khiển đóng/mở modals, xử lý xóa văn bản kèm thông báo.
  - Header trang: Thống kê số lượng (Tổng văn bản, Còn hiệu lực, Hết hiệu lực) và nút "Làm mới dữ liệu".
  - Kết nối đường dẫn chính thức `/documents/incoming` trong `router.tsx` để người dùng click vào sidebar là hiển thị ngay trang hoàn chỉnh.

---

### 🔹 GIAI ĐOẠN 7: Kiểm Thử & Nghiệm Thu Toàn Diện
- Kiểm tra TypeScript (`tsc --noEmit`) và build bundle không lỗi.
- Đăng nhập kiểm thử với tài khoản `canbo` / `Canbo@123` và `admin` / `Admin@123`.
- Kiểm tra tính năng lọc, đổi màu văn bản hết hiệu lực, xem chi tiết, tải file scan và kiểm tra danh sách người đã đọc trên cả 2 chế độ **Sleek Dark** và **Clean Light**.
