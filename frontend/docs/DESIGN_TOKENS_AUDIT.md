# TLBM - Báo Cáo Kỹ Thuật: Rà Soát Mã Màu & Design Tokens (DevOps Audit Report)

**Dự án:** Quản Lý Văn Bản & Tài Liệu Mật (TLBM)  
**Nhánh:** `1_layout_home`  
**Nhóm phụ trách:** Nhóm 1 - Kiến Trúc Layout & Trang Chủ  
**Tình trạng:** Hoàn tất 100% chuyển đổi Tailwind CSS Semantic Tokens & Zero-Hardcode Compliance.

---

## 1. Kết Quả Rà Soát Hệ Thống Mã Nguồn Nhóm 1

Toàn bộ các khối giao diện thuộc phạm vi Nhóm 1 đã được chuẩn hóa 100% sang **Tailwind CSS v3** kết hợp hệ thống **Design Tokens** tập trung tại `src/shared/styles/global.css`:

| Khối Giao Diện | Tệp Mã Nguồn | Tình Trạng | Chuẩn Tuân Thủ |
| :--- | :--- | :---: | :--- |
| **App Shell** | `MainLayout.tsx` | ✅ Đạt | 100% Tailwind utility classes |
| **Thanh Header** | `AppHeader.tsx`, `LanguageSwitcher.tsx`, `ThemeSelector.tsx`, `UserDropdown.tsx` | ✅ Đạt | 0 inline styles, 0 raw hex colors |
| **Thanh Điều Hướng** | `AppSidebar.tsx` (Facebook Accordion & Dock), `TopSubNav.tsx`, `MobileAssistiveTouch.tsx` | ✅ Đạt | Sử dụng semantic tokens `bg-fb-*`, `bg-primary`, `bg-surface-elevated` |
| **Thông Báo 3 Luồng** | `NotificationStreams.tsx` | ✅ Đạt | 100% Tailwind classes |
| **Trợ Lý AI Nổi** | `FloatingAIBox.tsx` | ✅ Đạt | Giao diện thẻ kính mờ `backdrop-blur-xl`, không chứa tên cá nhân, 0 raw hex |
| **7 Sub-widgets Dashboard** | `DashboardStats`, `QuickSearch`, `IncomingDocuments`, `RecentOutgoing`, `RecentTasks`, `Birthdays`, `RecentResources`, `NewTasksWidget` | ✅ Đạt | Toàn bộ 29 mã arbitrary hex (`bg-[#...]`, `accent-[#...]`) đã chuyển thành `bg-primary`, `bg-warning`, `bg-success`, `bg-slate-800` |
| **Trang Cài Đặt** | `SettingsPage.tsx` | ✅ Đạt | 100% Tailwind classes (giảm từ 36 inline styles tĩnh xuống **0 inline style**) |
| **Các Trang Phân Hệ** | `DashboardPage.tsx`, `ProfilePage.tsx`, `PasswordChangePage.tsx`, `SyllabusPreview.tsx`, `AiAssistantPage.tsx` | ✅ Đạt | 0 hardcode hex colors trong TSX |

---

## 2. Các Điểm Ngoại Lệ Kỹ Thuật Được Phép (Allowlist & Justifications)

Trong toàn bộ dự án, các điểm sau đây duy trì mã màu gốc hoặc inline style với lý do kỹ thuật bắt buộc:

### 2.1. Nguồn Gốc Khai Báo Gốc: `src/shared/styles/global.css` (Dòng 15 – 120)
* **Mục đích:** Khởi tạo bảng biến CSS `:root`, `[data-theme='dark']`, và `[data-theme='light']`.
* **Ghi chú kỹ thuật:** Đây là **Single Source of Truth (Nguồn gốc duy nhất)** của Design Tokens. Toàn bộ `tailwind.config.js` ánh xạ màu sắc từ các biến `var(--...)` này (`var(--color-primary)`, `var(--bg-surface)`, v.v.). Bắt buộc phải có giá trị mã màu gốc tại file CSS này.

### 2.2. Ô Màu Xem Trước (Swatches): `src/shared/utils/constants.ts`
* **Mục đích:** Cung cấp màu gradient xem trước (`previewGradient`) cho bộ chọn theme `ThemeSelector`.
* **Ghi chú kỹ thuật:** Dùng để người dùng khi đang ở Theme Sáng vẫn nhìn thấy ô demo của Theme Tối (và ngược lại) trước khi quyết định bấm chuyển đổi theme.

### 2.3. Hiệu Ứng Pháo Hoa Canvas: `src/modules/auth/pages/LoginPage.tsx` (Dòng 122)
* **Mục đích:** Truyền mảng màu vào hàm `confetti()` khi đăng nhập thành công.
* **Ghi chú kỹ thuật:** Thư viện bên thứ ba `canvas-confetti` vẽ trực tiếp lên thẻ HTML5 `<canvas>`, do đó bắt buộc phải nhận chuỗi mã màu hex thuần (`['#ff6b35', '#6d28d9', ...]`), không thể dùng class CSS.

### 2.4. Inline Style Động (Runtime Dynamic Coordinates)
* `src/modules/auth/pages/LoginPage.tsx`: Các thuộc tính `style={{ transform: translate3d(...) }}` và `style={{ opacity: ... }}` điều khiển cử động tròng mắt của 4 nhân vật hoạt họa theo tọa độ chuột thực tế của người dùng.
* `src/shared/components/Navigation/MobileAssistiveTouch.tsx`: Thuộc tính `style={{ left: ..., top: ... }}` điều khiển vị trí kéo thả tự do của phím Home ảo theo tọa độ con trỏ (Touch/Mouse Drag).

---

## 3. Xác Thực Kiểm Thử (Automated Verification)

* **TypeScript Compilation (`pnpm tsc --noEmit`):** 0 lỗi.
* **ESLint Gate (`pnpm lint`):** **0 errors, 0 warnings** (đã xử lý triệt để toàn bộ 16 lỗi ESLint).
* **Vitest Suite (`pnpm test -- --run`):** 6 test files, 15 tests, **100% PASS**.
* **Production Build (`pnpm build`):** Biên dịch hoàn tất thành công, không chứa bất kỳ chuỗi tên hay email cá nhân nào trong bundle JS/CSS.
* **Backend Django System Check (`python backend/manage.py check`):** **0 issues**.
