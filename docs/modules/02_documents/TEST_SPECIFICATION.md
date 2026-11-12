# Đặc Tả Kịch Bản Kiểm Thử Toàn Diện (Test Specification)
## Module 02: Quản Lý Văn Bản Đến — Nhóm 2

> **Đơn vị phụ trách**: Nhóm 2 — Module Quản Lý Văn Bản  
> **Trưởng nhóm**: Lê Trí Kiệt  
> **Thành viên**: Nguyễn Anh Đô, Nguyễn Tấn Lộc Khiêm, Trần Nhật Tân  
> **Tài liệu tham chiếu**: `docs/modules/02_documents/README.md`, `release_DDL.sql` (PR #92), Issue #82, Issue #83  
> **Mục tiêu**: Chuẩn hóa toàn bộ kịch bản kiểm thử (Case phổ thông, Edge cases, API integration, UI/UX lifecycle) làm căn cứ nghiệm thu Quality Gate cho PR sáp nhập Staging.

---

## 📋 1. Tổng Quan Phạm Vi Kiểm Thử (Testing Scope)

Hệ thống kiểm thử phân hệ Văn bản Đến được thiết kế theo mô hình kim tự tháp (Testing Pyramid), đảm bảo độ bao phủ cả 2 tầng Frontend và Backend:

1. **Frontend Testing (Vitest + React Testing Library + jsdom)**:
   - File test trang chủ: `frontend/src/pages/InboundDocumentPage.test.tsx` (10 tests)
   - File test bảng dữ liệu & phân trang: `frontend/src/components/documents/DocumentTable.test.tsx` (4 tests)
   - File test bộ lọc đa tiêu chí: `frontend/src/components/documents/FilterBar.test.tsx` (4 tests)
   - File test bộ modal nghiệp vụ: `frontend/src/components/documents/DocumentModals.test.tsx` (8 tests)
   - File test khóa thay thế & chống văn bản ma: `frontend/src/components/documents/DocumentReplacementValidation.test.tsx` (4 tests)
2. **Backend Testing (Django TestCase + PostgreSQL/SQLite test runner)**:
   - Module test: `backend/apps/documents/tests.py` (59 tests)
   - Bao phủ: Data constraints, concurrency lock số đến, phân quyền truy cập, WORM Audit Log, lọc đa tiêu chí, xuất/nhập Excel, chống văn bản ma và quan hệ thay thế 2 chiều.

---

## 🎯 2. Ma Trận Kịch Bản Kiểm Thử Frontend (Frontend Test Matrix)

### 2.1. Nhóm Kịch Bản Phổ Thông (Happy Path)

| Mã Test | Tên Kịch Bản | Điều Kiện Tiền Đề | Các Bước Thực Hiện | Kết Quả Mong Đợi (Expected Outcome) |
|---|---|---|---|---|
| **TC-FE-01** | Khởi tạo trang và nạp danh sách | Người dùng đã đăng nhập, API `/api/documents/` hoạt động bình thường | 1. Truy cập `/documents/incoming`<br>2. Chờ API trả kết quả | - Render tiêu đề "Quản Lý Văn Bản Đến"<br>- Hiển thị đủ 4 nút: "Thêm mới", "Nhập Excel", "Xuất Excel", "Làm mới"<br>- Render bảng dữ liệu với số hiệu, ngày đến, trích yếu |
| **TC-FE-02** | Thống kê số lượng văn bản còn hiệu lực | API trả về danh sách có văn bản `CON_HIEU_LUC` | 1. Tải trang<br>2. Kiểm tra card thống kê tổng hợp | - Card hiển thị chính xác số lượng văn bản còn hiệu lực (bao gồm cả hiệu lực 1 phần)<br>- Badge "Còn hiệu lực" hiển thị đúng count |
| **TC-FE-03** | Mở modal Thêm mới văn bản đến | Trang đã nạp xong | 1. Click nút "Thêm mới" | - Modal `DocumentFormModal` mở ra qua Portal<br>- Tiêu đề modal: "Thêm Mới Văn Bản Đến"<br>- Trường "Số đến" hiển thị text tự động cấp |
| **TC-FE-04** | Mở modal Nhập tệp Excel | Trang đã nạp xong | 1. Click nút "Nhập Excel" | - Modal `ImportExcelModal` mở ra<br>- Tiêu đề modal: "Nhập Văn Bản Từ File Excel"<br>- Hiển thị vùng kéo thả tệp và nút tải file mẫu |
| **TC-FE-05** | Làm mới danh sách công văn | Người dùng đang xem danh sách | 1. Click nút "Làm mới" | - Gọi lại API `/api/documents/?loai=DEN`<br>- Cập nhật lại danh sách và số liệu thống kê |
| **TC-FE-06** | Tìm kiếm và lọc theo bộ tiêu chí | Danh sách có nhiều văn bản | 1. Nhập từ khóa tìm kiếm<br>2. Chọn năm ban hành<br>3. Bấm "Tìm kiếm" | - API nhận đúng query params `q`, `nam`, `loai=DEN`<br>- Bảng cập nhật hiển thị kết quả lọc phù hợp |
| **TC-FE-07** | Xem chi tiết văn bản đến | Có ít nhất 1 dòng văn bản | 1. Click trích yếu hoặc chọn "Xem chi tiết" trong menu tác vụ ⋮ | - Mở modal `DocumentDetailModal`<br>- Hiển thị đầy đủ metadata, cơ quan ban hành, danh sách tệp đính kèm và văn bản thay thế (nếu có) |
| **TC-FE-08** | Xem danh sách người đã đọc | Văn bản có lượt đọc | 1. Click menu ⋮ -> chọn "Lịch sử xem" | - Mở modal `DocumentViewersModal`<br>- Hiển thị danh sách cán bộ, phòng ban và thời điểm đọc công văn |

---

### 2.2. Nhóm Kịch Bản Biên & Xử Lý Ngoại Lệ (Edge Cases & Resilience)

| Mã Test | Tên Kịch Bản | Tình Huống Giả Lập | Các Bước Thực Hiện | Kết Quả Mong Đợi (Expected Outcome) |
|---|---|---|---|---|
| **TC-FE-09** | CSDL rỗng / Không có dữ liệu phù hợp (Empty State) | API trả về mảng rỗng `[]` hoặc count = 0 | 1. Mở trang hoặc lọc với từ khóa không tồn tại | - Bảng hiển thị khối Empty State thân thiện: "Không tìm thấy văn bản đến nào"<br>- Gợi ý người dùng đổi năm hoặc đặt lại bộ lọc<br>- Không gây crash React render |
| **TC-FE-10** | Lỗi kết nối máy chủ / 500 Network Error | API ném ngoại lệ hoặc trả HTTP 500 | 1. Mở trang khi backend gặp sự cố | - Hiển thị banner thông báo lỗi màu đỏ rõ ràng<br>- Hiển thị nút "Thử lại" (Retry)<br>- Cho phép người dùng bấm thử lại khi mạng phục hồi |
| **TC-FE-11** | Chặn xóa nhầm với ConfirmModal hai bước | Người dùng bấm nhầm nút xóa | 1. Click ⋮ -> chọn "Xóa văn bản"<br>2. Click nút "Hủy bỏ" trong modal xác nhận | - Bật hộp thoại `ConfirmModal`: "Bạn có chắc chắn muốn xóa văn bản..."<br>- Khi bấm "Hủy bỏ": modal đóng lại an toàn, **KHÔNG** gọi API DELETE, văn bản giữ nguyên |
| **TC-FE-12** | Thực hiện xóa văn bản an toàn | Người dùng xác nhận xóa | 1. Click ⋮ -> chọn "Xóa văn bản"<br>2. Bấm xác nhận "Xóa văn bản" | - Gọi API `DELETE /api/documents/{id}/`<br>- Hiển thị `AlertModal` thông báo thành công<br>- Tự động reload lại bảng dữ liệu và cập nhật card thống kê |
| **TC-FE-13** | Lọc nhanh trạng thái Còn hiệu lực | Người dùng cần xem nhanh các văn bản đang áp dụng | 1. Click nút toggle "Còn hiệu lực" trên card thống kê | - URL/state kích hoạt param `hieu_luc=HIEU_LUC`<br>- Chỉ hiển thị văn bản `CON_HIEU_LUC` và `CON_HIEU_LUC_1_PHAN`<br>- Click lần 2 sẽ hủy lọc (trở về tất cả) |
| **TC-FE-14** | Tự động cập nhật văn bản bị thay thế | Văn bản mới ban hành thay thế cho công văn cũ | 1. Mở form Thêm mới<br>2. Tick "Văn bản này thay thế cho văn bản khác"<br>3. Chọn số hiệu văn bản cũ | - Khi lưu, văn bản cũ tự động chuyển trạng thái `HET_VA_THAY_THE`<br>- Bảng hiển thị tag badge cam/tím "Thay thế: {so_hieu}" |
| **TC-FE-15** | Phân trang danh sách lớn | Danh sách vượt quá 10 dòng/trang | 1. Chuyển sang trang 2<br>2. Đổi kích thước trang sang 25 dòng | - Bảng tính toán lại chỉ số bắt đầu/kết thúc chính xác<br>- Nút phân trang Prev/Next tự động disable ở trang biên |

---

## 🔒 3. Ma Trận Kịch Bản Kiểm Thử Backend (Backend Quality Gate)

56 test cases trong `backend/apps/documents/tests.py` bảo đảm tuân thủ nghiêm ngặt các quy tắc nghiệp vụ:

1. **Khóa Concurrency An Toàn (Số Đến / Số Đi Tự Tăng)**:
   - Sử dụng `select_for_update()` bảo đảm khi nhiều văn thư cùng vào sổ trong cùng một giây không bị trùng số thứ tự (`so_thu_tu`).
   - Khóa cứng `so_thu_tu` và `nam` sau khi đã tạo, không cho phép cập nhật thay đổi.
2. **Quy Tắc Văn Bản Hạn Chế (Issue #82 & Issue #83)**:
   - Superuser hay người có quyền `view_vanbanden` thông thường nếu không nằm trong danh sách `nguoi_nhan` nhận HTTP 404 (bảo mật tuyệt đối, không lộ sự tồn tại của văn bản).
   - Tự động ghi nhật ký truy vết WORM (`documents_access_log`) cho mọi hành động xem, tải tệp, hoặc bị từ chối truy cập.
   - Cấm gửi email toàn hệ thống đối với văn bản hạn chế.
3. **Bộ Lọc Đa Chiều & Export**:
   - Lọc theo khoảng ngày ban hành, ngày đến, năm, trạng thái hiệu lực.
   - Endpoint export Excel tự động loại bỏ văn bản hết hiệu lực theo chỉ đạo nghiệp vụ.

---

## ⚙️ 4. Quy Trình Chạy Kiểm Thử Tự Động (Quality Gate Commands)

Trước khi tiến hành tạo Pull Request hoặc sáp nhập code vào nhánh `staging`, toàn bộ các lệnh kiểm tra chất lượng dưới đây **BẮT BUỘC ĐẠT 100% PASS**:

```bash
# 1. Kiểm tra Linter Frontend (Yêu cầu: 0 errors, 0 warnings)
cd frontend
npm run lint

# 2. Kiểm tra Đơn vị & Kịch bản Frontend (Yêu cầu: 100% Passed)
npm test

# 3. Kiểm tra Biên dịch TypeScript & Đóng gói Production (Yêu cầu: Exit code 0)
npm run build

# 4. Kiểm tra Toàn vẹn i18n & Design Tokens
npm run check:i18n
npm run check:tokens

# 5. Kiểm tra Backend Unit & Integration Tests (Yêu cầu: 56/56 Passed)
cd ../backend
python manage.py test documents
```

---

## 📊 5. Kết Quả Kiểm Thử Thực Tế Hiện Tại

- **Frontend Linter**: `pnpm lint` -> 0 errors, 0 warnings (100% Clean)
- **Frontend Unit Tests**: `pnpm test` -> 29 test suites, 181 tests passed (100% Passed)
- **Frontend Production Build**: `pnpm build` (`tsc -b && vite build`) hoàn tất không có lỗi (1.52s)
- **Design Tokens & i18n**: 857 keys i18n hợp lệ, CSS tokens chuẩn hóa
- **Backend Tests**: `python manage.py test documents` -> 59/59 tests passed (100% OK, bao gồm kiểm thử thay thế 2 chiều, chống vòng lặp, và chặn văn bản mục tiêu không tồn tại trong hệ thống)
