# TLBM SYSTEM — FRONTEND ARCHITECTURE & BASELINE GUIDE
> **Phân hệ Giao diện Người dùng (React 19 + TypeScript 6 + Vite 8)**  
> **Nhóm phụ trách kiến trúc**: Nhóm 1 (Kiến trúc App Shell, Xác thực & Dashboard)  
> **Dự án**: Quản Lý Văn Bản và Tài Liệu (QLVB&TL) — Trường CĐ CNTT TP.HCM (ITC)  
> **Trạng thái**: Nhánh `1_layout_home` hiện là **Baseline Candidate (Bản chuẩn tạm thời)**; baseline chính thức sẽ được kích hoạt trên nhánh `staging` sau khi hoàn tất kiểm duyệt.

---

## 🛠️ 1. Công nghệ sử dụng

- **Core**: React 19 (Hooks, Context API)
- **Language**: TypeScript 6 (Strict Typing, Interface Definitions)
- **Routing**: React Router v7 (`react-router-dom`)
- **Build Tool**: Vite 8 (HMR, tối ưu bundle)
- **Styling**: Tailwind CSS + Design Tokens CSS Variables tập trung (`src/styles/global.css`)
- **Icons**: FontAwesome 6 Free Pro CDN + Custom SVGs
- **i18n**: Song ngữ Tiếng Việt (`vi.json`) / Tiếng Anh (`en.json`) theo từng module, qua hook `useTranslation()`
- **Testing**: Vitest + React Testing Library (Yêu cầu toàn bộ test suite phải pass 100%)
- **Quality Gate**: ESLint + TypeScript Typecheck + Production Build

---

## 📂 2. Cấu trúc thư mục mã nguồn chuẩn (`frontend/src/`)

Dự án áp dụng cấu trúc thư mục phẳng, tập trung, **không sử dụng cấu trúc `modules/` hay `shared/`**. Tất cả các nhóm dùng chung cấu trúc này làm bản tham chiếu:

```text
src/
├── app/                        # Tầng khởi chạy & cấu hình ứng dụng
│   ├── main.tsx                # Entry point
│   └── router.tsx              # Ghép route khai báo trong <module>/routes.ts của từng module
│
├── layouts/                    # Khung sườn bố cục ứng dụng (App Shell)
│   └── MainLayout.tsx          # Master Layout chứa Header, Sidebar, TopSubNav, Footer & <Outlet />
│
├── pages/                      # Màn hình nghiệp vụ theo từng phân hệ
│   ├── auth/                   # Màn hình Đăng nhập (LoginPage.tsx)
│   ├── dashboard/              # Bảng điều khiển tác nghiệp trung tâm (DashboardPage.tsx)
│   ├── settings/               # Cài đặt giao diện & tùy chọn (SettingsPage.tsx)
│   └── ...                     # Các nhóm tạo thư mục màn hình của nhóm mình tại đây
│
├── components/                 # Các component giao diện
│   ├── common/                 # Component dùng chung: Button, Card, Table, Badge, Logo
│   ├── layout/                 # AppHeader, AppSidebar, AppFooter, UserDropdown, LanguageSwitcher
│   ├── auth/                   # LoginForm, LoginCharacters
│   └── dashboard/              # ModernDashboardView, Empty States
│
├── lib/                        # Thư viện dùng chung, API Client & Service
│   ├── apiClient.ts            # Client gọi API tự động đính kèm JWT Token & Refresh Token
│   ├── authService.ts          # Service xác thực, đăng nhập, đăng xuất, lưu session
│   ├── constants.ts            # Hằng số hệ thống, danh mục Navigation
│   └── routes.ts               # pageIdToPath/pathToPageId, ghép từ <module>/paths.ts
│
├── types/                      # Định nghĩa kiểu dữ liệu TypeScript
│   ├── auth.ts                 # UserSession, LoginCredentials
│   ├── navigation.ts           # ActivePageId, NavItem, NavigationCategory
│   └── theme.ts                # ThemeMode (Clean Light / Sleek Dark)
│
├── i18n/                       # Quản lý từ điển đa ngôn ngữ
│   ├── <module>/vi.json        # Từ điển Tiếng Việt của module
│   ├── <module>/en.json        # Từ điển Tiếng Anh của module
│   └── translate.ts            # Hook useTranslation()
│
├── styles/                     # Quy chuẩn giao diện & CSS Variables
│   ├── global.css              # Hệ thống Design Tokens CSS Variables
│   └── login-characters.css    # Animation nhân vật đăng nhập
│
└── test/                       # Cấu hình môi trường kiểm thử
    └── setup.ts                # Vitest setup
```

---

## 🚀 3. Hướng dẫn nhóm khác thêm tính năng mới (Step-by-Step)

Mọi thành viên các nhóm 2, 3, 4, 5, 6, 7, 8 khi phát triển phân hệ của mình đều tuân theo 6 bước:

### Bước 1: Tạo trang mới trong `src/pages/`
Tạo thư mục nghiệp vụ tương ứng trong `src/pages/`, ví dụ `src/pages/documents/IncomingDocumentsPage.tsx`:
```tsx
import React from 'react';
import Card from '@components/common/Card';

export default function IncomingDocumentsPage() {
  return (
    <div className="p-6">
      <Card title="Quản lý Văn bản Đến">
        {/* Nội dung nghiệp vụ của Nhóm 2 */}
      </Card>
    </div>
  );
}
```

### Bước 2: Khai báo Route trong thư mục module
Mỗi module khai báo route trong `src/pages/<module>/routes.ts` và trang (page id ↔ đường dẫn) trong `src/pages/<module>/paths.ts` (module Công việc: `src/modules/work/`). `src/app/router.tsx` và `src/lib/routes.ts` tự ghép các file này, không sửa trực tiếp. Route mặc định nằm bên trong `<MainLayout />` để kế thừa Header, Sidebar, Footer:
```ts
// src/pages/documents/routes.ts
import type { ModuleRoute } from '@app/moduleRoutes';
import InboundDocumentPage from '../InboundDocumentPage';

export default [
  { path: '/documents/incoming', Component: InboundDocumentPage },
] satisfies ModuleRoute[];

// src/pages/documents/paths.ts
import type { ModulePage } from '@app/moduleRoutes';

export default [
  { id: 'documents_incoming', path: '/documents/incoming', matches: (pathname) => pathname.startsWith('/documents/incoming') },
] satisfies ModulePage[];
```
Page id mới vẫn cần thêm vào `ActivePageId` (`src/types/navigation.ts`) và mục menu trong `src/lib/constants.ts`.

### Bước 3: Gọi API Backend qua `apiClient`
Sử dụng `apiClient` từ `@lib/apiClient` để tự động đính kèm `Authorization: Bearer <token>`:
```tsx
import apiClient from '@lib/apiClient';

// Tự động xử lý BaseURL, JWT token và refresh token khi 401
const data = await apiClient.get<DocumentResponse>('/api/documents/incoming/');
```

### Bước 4: Khai báo Type trong `src/types/`
Tạo file type riêng hoặc thêm vào `src/types/`, ví dụ `src/types/document.ts`.

### Bước 5: Bổ sung từ điển đa ngôn ngữ trong `src/i18n/`
Thêm chuỗi vào cả `src/i18n/<module>/vi.json` và `src/i18n/<module>/en.json` của module mình (gồm cả `pages.<id>` và `navigation.<id>` của màn hình mới). `translate.ts` tự ghép mọi thư mục module; `pnpm check:i18n` báo lỗi khi lệch key giữa hai file hoặc trùng key với module khác.

### Bước 6: Viết Unit Test bằng Vitest
Tạo file test bên cạnh component, ví dụ `IncomingDocumentsPage.test.tsx` và chạy `pnpm test`.

---

## 📋 4. Checklist dành cho nhóm tiếp theo khi tạo branch từ Baseline

Khi nhận task và tạo nhánh từ `staging`, nhóm cần kiểm tra:

- [ ] Nhánh làm việc được tạo từ commit mới nhất trên `staging`.
- [ ] Màn hình mới được đặt trong `src/pages/<tên_tính_năng>/`.
- [ ] Route mới được cắm bên trong `<MainLayout />` (dùng `<Outlet />`), không tạo layout song song.
- [ ] Sử dụng các component dùng chung (`Card`, `Button`, `Table`, `Badge`) từ `@components/common/`.
- [ ] Không hardcode màu sắc (mã hex `#xxxxxx`), dùng semantic class của Tailwind hoặc biến CSS trong `global.css`.
- [ ] Gọi API qua `apiClient`, không tự ý bypass đăng nhập hoặc hardcode mock data vào production bundle.
- [ ] Tích hợp Role/Permission theo đúng contract do Nhóm 7 cung cấp.
- [ ] Đạt 100% Quality Gate trước khi mở PR:
  - `pnpm test` (PASS)
  - `pnpm lint` (0 errors, 0 warnings)
  - `pnpm build` (PASS)
  - `python backend/manage.py test` (PASS)
  - `python backend/manage.py check` (PASS)
- [ ] Mô tả PR rõ ràng, ghi rõ `Closes #<mã_issue>`.
