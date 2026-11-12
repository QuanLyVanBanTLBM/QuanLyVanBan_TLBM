# 📖 HƯỚNG DẪN FRONTEND BASELINE DÀNH CHO 8 NHÓM ĐỒ ÁN (ISSUE #9)

> **Dự án:** Quản lý Văn bản và Tài liệu Bảo Long (QLVB & TLBM)  
> **Nhóm xây dựng Baseline:** Nhóm 1 (Kiến trúc App Shell, Xác thực & Dashboard)  
> **Áp dụng cho:** Toàn bộ các nhóm 1, 2, 3, 4, 5, 6, 7, 8  

---

## 🎯 1. Mục tiêu của bản Frontend Baseline

> [!IMPORTANT]
> **Trạng thái Baseline:** Mã nguồn trên nhánh `1_layout_home` hiện là **Baseline Candidate (Bản chuẩn tạm thời / ứng viên)**. Chỉ sau khi được Reviewer / DevOps kiểm duyệt và hợp nhất chính thức vào nhánh `staging`, commit trên `staging` mới trở thành **Baseline chính thức** cho toàn bộ 8 nhóm.  
> Việc đồng bộ tài liệu là bước chuẩn bị cuối cùng cho các nhóm đọc chuẩn chung; CI, cấu hình môi trường và smoke test là các bước kiểm thử độc lập tiếp theo.

Bản Frontend Baseline là **mốc tham chiếu chuẩn mực** được đưa lên nhánh `staging`. Các nhóm khác khi nhận nhiệm vụ sẽ **tạo branch trực tiếp từ `staging`** (`git checkout staging && git pull origin staging && git checkout -b feat/<ten-chuc-nang>`) để bắt đầu phát triển module của nhóm mình mà không cần phải tự cấu hình lại giao diện, layout, định tuyến hay cơ chế gọi API.

---

## 🏗️ 2. Quyết định kỹ thuật bắt buộc (Technical Decisions)

1. **Cấu trúc phẳng, không dùng `modules/` hay `shared/`:**  
   Toàn bộ mã nguồn tổ chức theo các thư mục chức năng rõ ràng:
   - `src/pages/`: Chứa các màn hình nghiệp vụ (auth, dashboard, settings, profile...).
   - `src/components/`: Chứa component chia theo nhóm (`common/`, `layout/`, `auth/`, `dashboard/`).
   - `src/lib/`: Chứa `apiClient.ts`, `authService.ts`, `constants.ts`, `routes.ts`.
   - `src/types/`: Khai báo kiểu dữ liệu TypeScript (auth, navigation, theme...).
   - `src/i18n/`: Quản lý song ngữ (`<module>/vi.json`, `<module>/en.json`, `translate.ts`).
   - `src/styles/`: Design tokens và biến CSS tập trung (`global.css`, `animations.css`...).

2. **Khung sườn App Shell dùng chung (`MainLayout` & `<Outlet />`):**  
   Mọi route nghiệp vụ mới khai báo trong `src/pages/<module>/routes.ts` và được `src/app/router.tsx` đặt bên trong `<MainLayout />`. Khi chuyển trang, Header, Sidebar và Footer sẽ luôn cố định, chỉ có khu vực nội dung bên trong `<Outlet />` thay đổi.

3. **Cơ chế gọi API & Xác thực tập trung (`apiClient`):**  
   - Tất cả request gọi Backend phải dùng `apiClient` (`import apiClient from '@lib/apiClient'`).
   - `apiClient` tự động quản lý Bearer Token (Django Authentication + SimpleJWT), tự động gọi API Refresh Token khi gặp lỗi HTTP 401, và xử lý lỗi tập trung.
   - **Zero Mock Data:** Không lưu trữ dữ liệu giả lập (mock data) trong bundle sản phẩm. Nếu backend chưa trả về dữ liệu, hiển thị giao diện rỗng (Empty State) sạch sẽ.

4. **Phân quyền & Vai trò (Role/Permission):**  
   - Nhóm 1 không tự đặt ra cơ chế role/permission riêng lẻ.
   - Hợp đồng phân quyền (Contract) sẽ do **Nhóm 7 (Quản trị hệ thống)** cung cấp. Các nhóm tích hợp theo đúng contract này.
   - Nguồn kiểm tra quyền chính xác nhất (Source of Truth) luôn nằm ở Backend.

5. **Quy chuẩn Phông chữ & Cấm chữ siêu nhỏ (Typography & Accessibility):**  
   - Toàn bộ giao diện phần mềm công vụ bắt buộc sử dụng phông chữ rõ ràng, dễ đọc, tối thiểu từ 13px–14px trở lên để bảo vệ mắt người dùng theo chuẩn WCAG.
   - Hệ thống đã chuẩn hóa cấu hình `tailwind.config.js`: class `text-xs` đã được nâng từ 10.5px lên scale **`13px - 14px` (`0.875rem`)**, loại bỏ hoàn toàn cỡ chữ siêu nhỏ.
   - Các nhóm khi thiết kế nhãn badge, ngày tháng, nội dung bảng... bắt buộc dùng utility classes (`text-xs`, `text-sm`, `text-base`), **tuyệt đối không hardcode inline style cỡ chữ nhỏ bằng px** (như `style={{ fontSize: '10px' }}`).

---

## 🚀 3. Quy trình phát triển tính năng cho nhóm tiếp theo

```mermaid
graph TD
    A[Nhánh staging mới nhất] -->|1. Tạo nhánh tính năng| B[feat/ten-chuc-nang]
    B -->|2. Thêm Page vào src/pages/| C[Code UI & Logic]
    C -->|3. Khai báo Route trong routes.ts của module| D[Cắm vào MainLayout Outlet]
    D -->|4. Gọi API qua apiClient| E[Kết nối Backend]
    E -->|5. Chạy 5 lệnh Quality Gate| F{Pass 100%?}
    F -->|No| C
    F -->|Yes| G[Mở Pull Request vào staging kèm Closes #issue]
```

### Chi tiết các bước thực hiện:

1. **Tạo nhánh:** `git checkout staging && git pull origin staging && git checkout -b feat/<ten-tinh-nang>`
2. **Tạo trang:** Đặt file trong `src/pages/<nhom_module>/<TenTrang>Page.tsx`.
3. **Khai báo Route:** Thêm `{ path: '...', Component: TenTrangPage }` vào `src/pages/<nhom_module>/routes.ts` và page id tương ứng vào `paths.ts` cùng thư mục; không sửa `src/app/router.tsx`, `src/lib/routes.ts`.
4. **Kết nối API:** Sử dụng `apiClient.get()`, `apiClient.post()`.
5. **Kiểm thử Quality Gate:** Chạy đủ 5 lệnh bắt buộc:
   ```bash
   pnpm test
   pnpm lint
   pnpm build
   pnpm test:backend
   pnpm manage check
   ```
6. **Tạo PR:** Mở Pull Request trỏ đích về `staging`, điền form đầy đủ và ghi rõ `Closes #<mã_issue>`.

---

## ✅ 4. Checklist nghiệm thu Baseline (Quality Gate Verification)

- [x] Cấu trúc Frontend chuẩn mực không dùng `modules/`.
- [x] Đăng ký Route hoạt động 100% trong `MainLayout` thông qua `<Outlet />`.
- [x] Đầy đủ các component dùng chung chuẩn mực (`Card`, `Button`, `Table`, `Badge`, `Logo`).
- [x] Xác thực thật bằng Django Authentication + SimpleJWT (`authService` & `apiClient`).
- [x] Xóa 100% dữ liệu giả lập (Zero Mock Data), xử lý Empty State tự nhiên.
- [x] Hỗ trợ song ngữ Tiếng Việt và Tiếng Anh hoàn chỉnh.
- [x] Tuân thủ Typography: Loại bỏ hoàn toàn phông chữ siêu nhỏ (<13px), kế thừa đúng thang đo chuẩn trong `tailwind.config.js`.
- [x] Đạt 100% Quality Gate: Toàn bộ Unit Tests trong test suite phải pass 100% (0 failed), 0 lỗi ESLint, build production thành công.
