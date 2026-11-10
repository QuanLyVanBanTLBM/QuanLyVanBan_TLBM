### 1. Mục tiêu thay đổi (Objective)
<!-- Tóm tắt mục đích của PR: giải quyết issue nào, hoàn thành task nào -->

Issue: Closes #
<!-- Bắt buộc: một issue của nhánh này (Closes # hoặc Refs #), label nhóm, milestone. Nhánh tạo từ staging, tên <loại>/<số-issue>-<mô-tả> (AGENTS.md mục 8) -->

### 2. Chi tiết thay đổi kỹ thuật (Changes)
<!-- Liệt kê các file thay đổi và lý do kỹ thuật ngắn gọn -->
- `path/to/file`: 

### 3. Kiểm thử & Bằng chứng xác thực (Verification & Technical Gates)
> CI tự động chạy các lệnh dưới đây (job `backend` và `frontend`). Chạy local trước khi push để tránh CI đỏ.

- [ ] Frontend Lint: `pnpm --dir frontend run lint` (Pass)
- [ ] Frontend Test: `pnpm --dir frontend run test` (Pass)
- [ ] Frontend Build: `pnpm --dir frontend run build` (Pass 100%, 0 error/warning)
- [ ] Backend Check: `python backend/manage.py check` (Pass)
- [ ] Backend Migrations: `python backend/manage.py makemigrations --check --dry-run` (No changes detected)
- [ ] Backend Test: `python backend/manage.py test` (Pass)
- [ ] Đồng bộ nhánh đích: đã cập nhật nhánh `staging` mới nhất vào nhánh PR (rebase hoặc merge) và job `backend` (ci.yml) chạy lại xanh sau lần cập nhật cuối
- [ ] Thay đổi CSDL: cùng PR này sửa `release_DDL.sql`, thêm migration mới và mục `DDL_CHANGELOG.md`; không sửa migration đã có trên `staging`; bỏ qua nếu không đổi CSDL
- [ ] Phạm vi migration: chỉ tạo/sửa migration của app thuộc nhóm; thay đổi bảng của nhóm khác đã có issue được nhóm đó xác nhận
- [ ] i18n Key Parity: `pnpm --dir frontend run check:i18n` (Pass)
- [ ] CSS Design Tokens: `pnpm --dir frontend run check:tokens` (Pass)
- [ ] Tuân thủ i18n (kiểm tra thủ công): 100% text UI dùng `t('namespace.key')`, không hardcode chuỗi trong component
- [ ] Tuân thủ Design Tokens (kiểm tra thủ công): 100% sử dụng biến CSS từ `frontend/src/styles/global.css`
