# 🖋️📐 QUY CHUẨN LAYOUT HỆ THỐNG & TYPOGRAPHY PHÔNG CHỮ (LAYOUT & TYPOGRAPHY GUIDELINES)

> **Dự án:** Quản lý Văn bản và Tài liệu Bảo Long (QLVB & TLBM)  
> **Nhóm phụ trách Baseline:** Nhóm 1 - Kiến Trúc App Shell & Layout (PM: Châu Tuấn Kiệt)  
> **Áp dụng cho:** Toàn bộ 8 nhóm phát triển (Nhóm 1 đến Nhóm 8)  
> **Nguồn gốc tập trung (Single Source of Truth):**  
> - File khung sườn Layout: [`frontend/src/layouts/MainLayout.tsx`](file:///d:/MonHocITC/Django/DoAnCuoiKy/frontend/src/layouts/MainLayout.tsx)  
> - File cấu hình Tailwind: [`frontend/tailwind.config.js`](file:///d:/MonHocITC/Django/DoAnCuoiKy/frontend/tailwind.config.js)  
> - File biến toàn cục & Design Tokens: [`frontend/src/styles/global.css`](file:///d:/MonHocITC/Django/DoAnCuoiKy/frontend/src/styles/global.css)  
> - Cam kết quy chuẩn: Commit `d90a274` (`feat(ui): loai bo phong chu sieu nho va quy chuan hoa typography`)

---

## 🎯 1. Nguyên Tắc Cốt Lõi (Core Principles)

1. **Chuẩn công vụ & Dễ đọc (WCAG 2.1 AA Compliance):**  
   Giao diện phần mềm hành chính công vụ đòi hỏi độ rõ ràng, sắc nét cao trên mọi kích thước màn hình để cán bộ, nhân viên xử lý văn bản trong thời gian dài không bị mỏi mắt.
2. **Nghiêm cấm phông chữ siêu nhỏ (< 11px):**  
   Tuyệt đối loại bỏ toàn bộ cỡ chữ `8px`, `9px`, `10px`. Kích thước nhỏ nhất cho phép hiển thị nhãn phụ, thẻ trạng thái là **`13px - 14px` (`0.875rem`)**.
3. **Kế thừa Semantic Tokens & Layout Grid (Zero Hardcode):**  
   Không viết inline style `style={{ fontSize: '...', color: '...' }}` hay dùng arbitrary class `text-[#...]`. Toàn bộ màu chữ, cỡ chữ và kích thước khung phải tuân thủ chuẩn Tailwind và Layout Token đã định nghĩa (`text-main`, `text-secondary`, `text-muted`, `text-xs`, `text-sm`, `max-w-[1600px]`...).
4. **Trực quan & Nhất quán đa thiết bị (Responsive Enterprise App Shell):**  
   Khung giao diện khóa cuộn trang ở cấp độ trình duyệt (`h-screen overflow-hidden`), chỉ cho phép cuộn nội dung độc lập ở khung tác nghiệp chính (`overflow-y-auto`).

---

## 📐 2. Quy Chuẩn Kích Thước Layout Hệ Thống (System Layout Dimensions)

Toàn bộ các trang nghiệp vụ đều được gắn vào thẻ `<Outlet />` bên trong [`MainLayout.tsx`](file:///d:/MonHocITC/Django/DoAnCuoiKy/frontend/src/layouts/MainLayout.tsx). 

### 2.1. Khung sườn tổng thể (App Shell Dimensions):

| Thành Phần Giao Diện | Kích Thước Chuẩn | Lớp CSS / Tailwind | Ý Nghĩa & Cơ Chế Hoạt Động |
| :--- | :---: | :--- | :--- |
| **Toàn khung (App Shell)** | **`100vw × 100vh`** | `w-screen h-screen overflow-hidden` | Khóa cuộn toàn màn hình, tạo cảm giác ứng dụng ERP chuyên nghiệp |
| **Header đỉnh (`AppHeader`)** | **`64px`** | `h-16 px-4 z-30 backdrop-blur-md` | Cố định trên cùng, chứa Logo, tìm kiếm, chuông thông báo, Theme, Profile |
| **Sidebar (Thu gọn / Icon Rail)** | **`72px`** | `lg:w-[72px] transform-gpu` | Trạng thái mặc định trên Desktop, hiển thị dải icon phân hệ cân đối |
| **Sidebar (Mở rộng / Ghim)** | **`290px`** | `w-[290px] shadow-2xl` | Hiển thị đầy đủ tên phân hệ khi rê chuột (hover) hoặc bấm nút Ghim cố định |
| **Sidebar Di động (< 1024px)** | **`0px`** ➔ **`290px`** | `-translate-x-full` ➔ `translate-x-0` | Ẩn hoàn toàn, mở dạng Drawer đè lên trên kèm Backdrop mờ `z-[1100]` |
| **Thanh điều hướng phụ (`TopSubNav`)** | **`44px`** | Nằm ngay dưới Header | Thanh tab ngang chuyển nhanh giữa các trang con cùng phân hệ |
| **Độ rộng nội dung tối đa (`Max-Width`)** | **`1600px`** | `max-w-[1600px] mx-auto` | Giới hạn độ rộng vùng đọc, tránh kéo dãn quá dài trên màn hình 2K/4K |
| **Lề đệm nội dung (`Padding`)** | **`16px` – `24px`** | `p-4 sm:p-6` | Đệm lề 16px trên điện thoại di động, 24px trên máy tính bảng và desktop |

### 2.2. Kích thước thành phần con (Component Dimensions & Spacing):

| Thành Phần | Kích Thước Chuẩn | Thuộc Tính Tailwind | Ghi Chú Kỹ Thuật |
| :--- | :---: | :--- | :--- |
| **Thẻ Card / Hộp dữ liệu** | Bo góc **16px**, Đệm **20px** | `rounded-2xl p-5 border border-border-subtle bg-surface` | Thống nhất cho tất cả các card thống kê và card chứa bảng |
| **Thanh tìm kiếm nhanh** | Cao **52px**, Phông **16px** | `py-3.5 pl-12 pr-10 rounded-xl text-base` | Đặt ở đầu Dashboard và đầu các danh mục quản lý |
| **Ô nhập liệu Form (Input/Select)** | Cao **40px – 44px**, Phông **14px** | `h-10 py-2 px-3.5 rounded-xl text-sm border` | Đảm bảo ngón tay chạm thoải mái trên mobile/tablet |
| **Nút bấm nhỏ (`Button sm`)** | Cao **32px**, Phông **13-14px** | `h-8 px-3 rounded-lg text-xs font-semibold` | Nút hành động nhanh trong dòng bảng, nút tải tệp |
| **Nút bấm chuẩn (`Button md`)** | Cao **40px**, Phông **14px** | `h-10 px-4 rounded-xl text-sm font-semibold` | Nút tác nghiệp chính: "Thêm mới", "Lưu", "Gửi duyệt" |
| **Nút bấm lớn (`Button lg`)** | Cao **48px**, Phông **16px** | `h-12 px-6 rounded-xl text-base font-semibold` | Nút CTA đăng nhập, duyệt lệnh đặc biệt |
| **Hộp thoại nhỏ (Confirm Dialog)** | Rộng tối đa **448px** | `max-w-md w-full rounded-2xl p-6` | Hộp xác nhận xóa, xác nhận chuyển tiếp |
| **Hộp thoại chuẩn (Form Modal)** | Rộng tối đa **672px – 896px** | `max-w-2xl` hoặc `max-w-4xl rounded-2xl` | Form nhập thông tin văn bản, chọn phòng họp |
| **Hộp thoại lớn (Document Preview)** | Rộng tối đa **1152px** | `max-w-6xl w-full rounded-2xl max-h-[90vh]` | Cửa sổ xem trước file văn bản PDF / DOCX đính kèm |

### 2.3. Khoảng cách ô lưới (Grid Gaps) & Bo góc (Border Radius):
* **Khoảng cách hàng/cột (`Gaps`):**
  * Thẻ thống kê KPI: `grid grid-cols-1 md:grid-cols-3 gap-5` (khoảng cách 20px).
  * Hai bảng dữ liệu song song: `grid grid-cols-1 lg:grid-cols-2 gap-5` (khoảng cách 20px).
  * Form trường dữ liệu: `grid grid-cols-1 md:grid-cols-2 gap-4` (khoảng cách 16px).
  * Dàn trang danh sách dọc: `flex flex-col gap-6` (khoảng cách 24px giữa các khối lớn).
* **Quy chuẩn bo góc (`Border Radius Scale`):**
  * `rounded-lg` (8px): Huy hiệu (`Badge`), icon thu nhỏ, nút phụ.
  * `rounded-xl` (12px): Ô nhập liệu (`Input`), thanh tìm kiếm, nút bấm (`Button`).
  * `rounded-2xl` (16px): Khung Card, container bảng, hộp thoại Modal.
  * `rounded-full` (9999px): Avatar người dùng, nút icon tròn, nút đóng X.

### 2.4. Điểm ngắt màn hình (Responsive Breakpoints):
* **Mobile (< 640px):** Menu ẩn hoàn toàn, hỗ trợ cử chỉ vuốt ngang cảm ứng từ mép trái (`swipe >= 40px` trong `600ms`) để bật menu drawer.
* **Tablet (640px – 1023px):** Menu dạng drawer thu gọn, nội dung đệm lề 24px (`sm:p-6`).
* **Desktop (≥ 1024px):** Cố định dải Icon Rail `72px`, nội dung chính thụt lề `lg:pl-[72px]`. Khi ghim mở rộng thì thụt lề `lg:pl-[290px]`.
* **Màn hình lớn (≥ 1280px – 1600px+):** Nội dung đạt trần tối đa `1600px` và tự động căn giữa (`mx-auto`).

---

## 🔤 3. Quy Chuẩn Phông Chữ (Font Family)

| Phân Loại | Định Nghĩa Kỹ Thuật | Phạm Vi Sử Dụng |
| :--- | :--- | :--- |
| **Font Chính (Primary Sans-Serif)** | **`Inter`** *(Nạp từ Google Fonts tại [`index.html`](file:///d:/MonHocITC/Django/DoAnCuoiKy/frontend/index.html#L12))*<br>`font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif` | Áp dụng cho **100% giao diện**: Tiêu đề trang, thanh điều hướng, bảng biểu, danh mục hồ sơ, nút bấm, form nhập liệu. |
| **Font Ký Hiệu / Biểu Tượng** | **`FontAwesome 6 Pro/Free`** (`fa-solid`, `fa-regular`) | Toàn bộ icon hành động, icon trạng thái, biểu tượng danh mục. |
| **Font Đơn Cách (Monospace)** | `font-mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas` | Mã số ký hiệu văn bản đặc biệt, mã hash bảo mật, UUID, số token xác thực, log hệ thống. |

> [!WARNING]
> Nghiêm cấm dùng phông chữ có chân (Serif như *Times New Roman*) hoặc các phông viết tay, uốn lượn mang tính trang trí trong giao diện phần mềm công vụ.

---

## 📏 4. Thang Đo Kích Thước Chữ (Type Scale & Line-Height)

Cấu hình chi tiết được ánh xạ trong [`frontend/tailwind.config.js`](file:///d:/MonHocITC/Django/DoAnCuoiKy/frontend/tailwind.config.js#L136-L142):

```javascript
fontSize: {
  // Loại bỏ hoàn toàn cỡ chữ siêu nhỏ (0.75rem ~ 10.5px); nâng 'xs' lên ngang tầm chữ đọc rõ (0.875rem ~ 13-14px)
  xs: ['0.875rem', { lineHeight: '1.25rem' }],
}
```

### Bảng tra cứu kích thước chữ chi tiết (Type Scale Reference):

| Class Tailwind | Kích Thước (px / rem) | Dòng Cao (Line-Height) | Vị Trí Áp Dụng Cụ Thể |
| :--- | :---: | :---: | :--- |
| **`text-xs`** | **13px – 14px** *(0.875rem)* | `1.25rem` (20px) | • Nhãn định danh phân hệ (Category tag, e.g. `HỒ SƠ LƯU TRỮ`)<br>• Tiêu đề các cột bảng (`TableHead` uppercase)<br>• Huy hiệu trạng thái (`Badge`), tag từ khóa<br>• Ngày giờ lập, breadcrumb, tooltip, ghi chú phụ |
| **`text-sm`** *(Chuẩn)* | **14px** *(0.875rem)* | `1.25rem` (20px) | • **Nội dung dữ liệu bảng** (`TableCell`: Số hiệu, Trích yếu...)<br>• Ô nhập liệu (`input`, `select`, `textarea`)<br>• Nút bấm kích cỡ tiêu chuẩn (`Button size="md"`)<br>• Dòng mô tả trang dưới tiêu đề chính (`description`) |
| **`text-base`** | **16px** *(1.000rem)* | `1.50rem` (24px) | • Tiêu đề thẻ (`CardTitle`), ô tìm kiếm nhanh<br>• Tiêu đề hộp thoại xác nhận (Confirm Dialog)<br>• Nút bấm lớn (`Button size="lg"`) |
| **`text-lg`** | **18px** *(1.125rem)* | `1.75rem` (28px) | • Tiêu đề phân đoạn lớn (Section Header)<br>• Nhóm phân loại chính trong drawer cài đặt |
| **`text-xl`** | **20px** *(1.250rem)* | `1.75rem` (28px) | • Tiêu đề cửa sổ Modal tạo mới / xem chi tiết văn bản<br>• Tiêu đề khay thông báo 3 luồng |
| **`text-2xl`** | **24px** *(1.500rem)* | `2.00rem` (32px) | • **Tiêu đề trang chính (`<h1>`)** của từng phân hệ<br>• Tiêu đề các báo cáo phân tích tổng hợp |
| **`text-3xl`** | **30px** *(1.875rem)* | `2.25rem` (36px) | • Số liệu chỉ số tổng hợp KPI trên Dashboard (KPI Card Value)<br>• Bộ đếm số lượng văn bản chờ xử lý |
| **`text-4xl`** | **36px** *(2.250rem)* | `2.50rem` (40px) | • Tiêu đề Hero trang Đăng nhập / Chào mừng hệ thống |

### 4.2. Nguyên tắc phân cấp thị giác (Visual Hierarchy):
1. **Cấp 1 - Tiêu đề trang (`<h1>`):** `24px` (`text-2xl`), `font-bold`, màu `text-main`. Mỗi trang chỉ có 1 thẻ `<h1>` duy nhất.
2. **Cấp 2 - Số liệu KPI trọng điểm:** `30px - 36px` (`text-3xl` / `text-4xl`), `font-bold`, màu `text-main` nổi bật.
3. **Cấp 3 - Tiêu đề Card / Modal (`<h3>`):** `16px - 20px` (`text-base` / `text-xl`), `font-bold` hoặc `font-semibold`.
4. **Cấp 4 - Nội dung tác nghiệp chính (Dòng bảng, Form):** `14px` (`text-sm`), `font-medium` / `font-normal`.
5. **Cấp 5 - Nhãn phụ, Tiêu đề cột bảng, Tag:** `13px - 14px` (`text-xs`), `font-bold`, `uppercase`, `tracking-wider`.

---

## ⚖️ 5. Quy Chuẩn Trọng Số Chữ (Font Weight)

* **`font-normal` (400 - Regular):** Văn bản mô tả phụ (`CardDescription`), nội dung chi tiết trích yếu văn bản, văn bản trợ giúp, placeholder.
* **`font-medium` (500 - Medium):** Nhãn trường nhập liệu (`<label>`), họ tên người lập, phân khoa phòng ban trong danh sách.
* **`font-semibold` (600 - Semibold):** **Tên hồ sơ** trong bảng, tên văn bản hiển thị nổi bật, tên tài nguyên biểu mẫu, tên tài khoản người dùng.
* **`font-bold` (700 - Bold):**
  * Tiêu đề trang chính (`<h1>`)
  * Tiêu đề card (`<h3>` / `CardTitle`)
  * Header tiêu đề cột bảng (`TableHead` kết hợp `uppercase tracking-wider`)
  * Chữ trên nút bấm CTA hành động (`Button`) và nhãn phân loại (`Badge`).

---

## 🎨 6. Quy Chuẩn Màu Sắc Chữ Theo Theme (Semantic Tokens)

Tất cả màu chữ phải tuân thủ bảng biến CSS trong [`frontend/src/styles/global.css`](file:///d:/MonHocITC/Django/DoAnCuoiKy/frontend/src/styles/global.css), hỗ trợ tự động cả 3 chế độ (Light, Dark, Modern Claymorphism 3D):

| Token Class | Biến CSS | Ý Nghĩa Ngữ Nghĩa | Light Theme | Dark Theme |
| :--- | :--- | :--- | :---: | :---: |
| **`text-main`** | `var(--text-main)` | Tiêu đề chính, tên hồ sơ, số hiệu, nội dung trọng tâm | `#0f172a` (Slate-900) | `#f8fafc` (Trắng tinh) |
| **`text-secondary`** | `var(--text-secondary)` | Dòng mô tả trang, tên người lập, phòng ban ban hành | `#475569` (Slate-600) | `#cbd5e1` (Xám bạc) |
| **`text-muted`** | `var(--text-muted)` | Header bảng, icon tìm kiếm, ngày tháng, placeholder | `#64748b` (Slate-500) | `#94a3b8` (Xám trung tính) |
| **`text-primary`** | `var(--color-primary)` | Tên phân hệ trên cùng, liên kết điều hướng, trạng thái chọn | `#3b82f6` (Blue-500) | `#3b82f6` (Blue-500) |
| **`text-success`** | `var(--color-success)` | Thông báo thành công, trạng thái hồ sơ *"Đã đóng / Hoàn tất"* | `#10b981` (Green-500) | `#10b981` (Green-500) |
| **`text-warning-text`** | `var(--color-warning-text)` | Cảnh báo, trạng thái *"Chờ duyệt / Đang lưu trữ"* | `#d97706` (Amber-600) | `#f59e0b` (Amber-500) |
| **`text-danger`** | `var(--color-danger)` | Báo lỗi API, cảnh báo xóa, trạng thái *"Hết hạn / Mật"* | `#ef4444` (Red-500) | `#ef4444` (Red-500) |

---

## 🧩 7. Mẫu Cấu Trúc Typography Chuẩn Trên Giao Diện

Trích đoạn triển khai chuẩn mực từ phân hệ **Nhóm 3 (Quản lý Hồ sơ lưu trữ - [`DossiersPage.tsx`](file:///d:/MonHocITC/Django/DoAnCuoiKy/frontend/src/pages/records/DossiersPage.tsx))**:

```tsx
{/* 1. Nhãn phân hệ (Module Category): text-xs, font-bold, uppercase, tracking-wider, text-primary */}
<div className="mb-1 flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-primary">
  <i className="fa-solid fa-folder-tree" />
  HỒ SƠ LƯU TRỮ
</div>

{/* 2. Tiêu đề trang chính: text-2xl, font-bold, text-main */}
<h1 id="dossiers-title" className="m-0 text-2xl font-bold text-main">
  Quản lý Hồ sơ Lưu trữ
</h1>

{/* 3. Dòng mô tả phụ: text-sm, text-secondary */}
<p className="m-0 mt-1 text-sm text-secondary">
  Quản lý, phân loại danh mục hồ sơ và phân loại tài liệu lưu trữ
</p>

{/* 4. Tiêu đề cột bảng: text-xs, font-bold, text-muted, uppercase, tracking-wider */}
<TableHead className="text-xs font-bold text-muted uppercase tracking-wider">
  SỐ / KÝ HIỆU
</TableHead>

{/* 5. Dòng dữ liệu hồ sơ trong bảng: */}
<TableCell>
  {/* Số hiệu hồ sơ: Badge text-xs font-bold */}
  <Badge variant="secondary">HS-2026-001</Badge>
</TableCell>
<TableCell>
  {/* Tên hồ sơ: text-sm, font-semibold, text-main */}
  <div className="font-semibold text-main">Hồ sơ thẩm định dự án</div>
  {/* Ghi chú phụ: text-xs, text-muted */}
  <div className="mt-1 truncate text-xs text-muted">Tài liệu phục vụ nghiệm thu Q3</div>
</TableCell>
```

---

## 📋 8. Bảng Kiểm Tra Kiểm Duyệt (Quality Gate Layout & Typography Checklist)

| STT | Tiêu Chí Kiểm Tra | Quy Định Kỹ Thuật | Đánh Giá |
| :---: | :--- | :--- | :---: |
| 1 | **Không có font chữ siêu nhỏ** | Tuyệt đối không dùng `text-[8px]`, `text-[9px]`, `text-[10px]` hay `style={{ fontSize: '10px' }}` | ❌ Cấm |
| 2 | **Không hardcode mã màu chữ** | Tuyệt đối không viết `style={{ color: '#333' }}` hay arbitrary class `text-[#1e293b]` | ❌ Cấm |
| 3 | **Sử dụng Semantic Token** | Luôn dùng `text-main`, `text-secondary`, `text-muted` cho văn bản | ✅ Đạt |
| 4 | **Tiêu đề trang chuẩn H1** | Luôn dùng `text-2xl font-bold text-main` cho `<h1>` đầu trang | ✅ Đạt |
| 5 | **Bảng dữ liệu chuẩn mực** | Header bảng dùng `text-xs font-bold text-muted uppercase tracking-wider`, body dùng `text-sm` | ✅ Đạt |
| 6 | **Tương thích Theme Sáng / Tối** | Chữ hiển thị rõ nét, đạt độ tương phản tối thiểu 4.5:1 trên cả nền Light và Dark | ✅ Đạt |
| 7 | **Khung Header chuẩn 64px** | Chiều cao Header luôn cố định `64px` (`h-16`), không bị co giãn khi cuộn | ✅ Đạt |
| 8 | **Sidebar Icon Rail 72px / 290px** | Thu gọn `72px`, mở rộng `290px`, có hiệu ứng chuyển động mượt mà | ✅ Đạt |
| 9 | **Nội dung Max-Width 1600px** | Toàn bộ các trang nghiệp vụ đều có trần giới hạn `max-w-[1600px] mx-auto` | ✅ Đạt |
