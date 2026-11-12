# Tài Liệu Bàn Giao Nhóm 1 - App Shell, Layout & Hệ Thống Nền Tảng

- **Đơn vị phụ trách:** Nhóm 1 (Trưởng nhóm: Châu Tuấn Kiệt)
- **Thư mục module:** `docs/modules/01_layout_dashboard/`
- **Nhiệm vụ đồ án:** Xây dựng khung ứng dụng App Shell (Header, Sidebar, Footer, Navigation), Hệ thống Theme Clean Light / Sleek Dark, Router URL-based qua `<Outlet />`, Dashboard trung tâm kết nối dữ liệu thật và Giao diện Đăng nhập xác thực Django Auth + SimpleJWT.

## 1. Cấu Trúc App Shell Dùng Chung Cho 8 Nhóm

Các nhóm cắm màn hình nghiệp vụ vào `<Outlet />` bên trong `MainLayout`:

```tsx
// frontend/src/app/router.tsx
<Route element={<MainLayout />}>
  {/* Các nhóm chỉ cần thêm <Route> trỏ đến component trang của mình */}
  <Route path="/dashboard" element={<DashboardPage />} />
  <Route path="/documents/incoming" element={<DocumentsIncomingPage />} />
</Route>
```

### Các Thành Phần Tự Động Kế Thừa:
1. **`AppHeader`**: Đồng hồ hành chính trực tiếp, chuông thông báo 3 luồng (Đến/Đi/Mật), nút gạt theme 1-chạm Sáng/Tối, menu hồ sơ người dùng.
2. **`AppSidebar`**: Thanh điều hướng dạng Facebook Accordion và Mini-Dock, tự động đánh dấu active và mở menu con theo đúng URL hiện tại.
3. **`TopSubNav`**: Thanh chỉ mục phân hệ phụ ngang ở đỉnh trang.
4. **`AppFooter`**: Chân trang hành chính bản quyền ITC.

## 2. Hướng Dẫn Kế Thừa Theme & Token Màu Sắc

Tất cả các thành phần UI nên dùng CSS Variables đã định nghĩa tại `frontend/src/styles/global.css` (hoặc import qua `@styles/global.css`):
- Màu chính: `var(--color-primary)`
- Nền bề mặt: `var(--bg-surface)`
- Nền trang: `var(--bg-app)`
- Chữ chính: `var(--text-main)`
- Chữ phụ: `var(--text-secondary)`
- Viền: `var(--border-subtle)`

## 3. Quy Chuẩn Công Cụ
- Bộ quản lý gói: **`pnpm`** (Chạy `pnpm install`, `pnpm dev`, `pnpm build`).
- Khóa lockfile: `pnpm-lock.yaml`.
