# Tài Liệu Dùng Chung Toàn Dự Án (Common Docs)

Thư mục này lưu trữ các quy chuẩn kiến trúc, tài liệu tích hợp và hướng dẫn chung áp dụng cho toàn bộ 8 nhóm thuộc đồ án Quản Lý Văn Bản & Tài Liệu Mật (TLBM).

> [!NOTE]
> **Trạng thái Baseline:** Nhánh `1_layout_home` hiện là **Baseline Candidate (Bản chuẩn tạm thời)**. Baseline chính thức của toàn bộ dự án sẽ được kích hoạt trên nhánh `staging` sau khi hoàn thành kiểm định Quality Gate, CI và Smoke Test.

## 📚 Danh Mục Tài Liệu Chung Cốt Lõi

1. **[Tài Liệu Hướng Dẫn Frontend Baseline (`FRONTEND_BASELINE_GUIDE.md`)](./FRONTEND_BASELINE_GUIDE.md)**:
   - Quy ước cấu trúc thư mục phẳng (`pages/`, `components/`, `lib/`, `types/`, `styles/`, `i18n/`), nghiêm cấm dùng `modules/` hay `shared/`.
   - Hướng dẫn 6 bước chi tiết cho các nhóm khi thêm màn hình mới vào `<Outlet />` bên trong `MainLayout`.
   - Hướng dẫn kết nối API qua `apiClient` và xác thực Django Authentication + SimpleJWT.
2. **[Bộ Tiêu Chuẩn Quality Gate & Điều Kiện Lên Staging (`QUALITY_GATE_STAGING.md`)](./QUALITY_GATE_STAGING.md)**:
   - Quy định bắt buộc vượt qua 5 lệnh kiểm thử Quality Gate (Toàn bộ test suite Backend + Frontend phải pass 100%, lint sạch, build thành công).
   - Quy trình đóng gói và nghiệm thu bàn giao từ nhánh `1_layout_home` (Baseline Candidate) lên nhánh `staging` (Baseline chính thức).
   - Checklist dành cho các nhóm khi tạo branch từ `staging`.
3. **[Đặc Tả Dự Án Toàn Diện (`ITC - Django - QLVB&TL.md`)](./ITC%20-%20Django%20-%20QLVB&TL.md)**:
   - Bảng phân công 8 nhóm, độ khó, cơ cấu tổ chức, danh sách lớp và báo cáo tiến độ.
4. **[Quy Chuẩn Typography & Phông Chữ Hệ Thống (`TYPOGRAPHY_GUIDELINES.md`)](./TYPOGRAPHY_GUIDELINES.md)**:
   - Quy tắc Font Family (`Inter`, `FontAwesome 6`, `Monospace`), cấm tuyệt đối phông chữ siêu nhỏ (< 11px).
   - Thang đo Type Scale, Font Weight và hệ thống Semantic Text Tokens đa chế độ giao diện (Light, Dark, Claymorphism).

4. **[Quy Ước Quản Lý Dự Án (`guidelines/quy-uoc-quan-ly-du-an.md`)](./guidelines/quy-uoc-quan-ly-du-an.md)**:
   - Người merge `staging`/`ddl_base_v0`, quy trình sửa CSDL (DDL trước, migration sau), gắn issue + label nhóm + milestone cho mọi PR.
   - Label `nhom-1`…`nhom-8`, `P0`, `P1`, `blocked`, `ddl`; milestone `Base staging`, `MVP`; bảng GitHub Project.

## 📂 Cấu Trúc Tài Liệu Theo Phân Hệ
- `docs/modules/01_layout_dashboard/`: Bàn giao App Shell, Header, Sidebar, Footer, Router URL, Theme Nhóm 1.
- `docs/modules/02_documents/`: Tài liệu Phân hệ Văn bản đến / đi / mật.
- `docs/modules/03_dossiers_records/`: Tài liệu Phân hệ Hồ sơ tài liệu.
- `docs/modules/04_document_templates/`: Tài liệu Phân hệ Tài nguyên biểu mẫu.
- `docs/modules/05_signing_workflow/`: Tài liệu Phân hệ Trình ký & Phê duyệt.
- `docs/modules/06_tasks_management/`: Tài liệu Phân hệ Công việc & Họp.
- `docs/modules/07_system_admin_meetings/`: Tài liệu Phân hệ Quản trị tổ chức & Nhân sự.
- `docs/modules/08_ai_assistant/`: Tài liệu Phân hệ Trợ lý AI.

## ⚙️ Quy Định Tích Hợp Frontend
- Quản lý gói: **Sử dụng duy nhất `pnpm`** (Nghiêm cấm dùng npm/yarn để tránh xung đột lockfile).
- Định tuyến: **Sử dụng `react-router-dom` qua `<Outlet />`**.
- Khung giao diện: Toàn bộ module cắm vào `<Outlet />` bên trong `MainLayout`, kế thừa tự động Header, Sidebar, Footer.
