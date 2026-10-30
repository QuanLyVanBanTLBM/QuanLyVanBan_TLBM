# Bộ lọc Phòng/Ban Trình ký — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hoàn tất bug #314 bằng cách đồng bộ PR #318 với `staging` mới nhất, giữ bộ lọc đơn vị áp dụng và đưa thay đổi lên bản deploy.

**Architecture:** Bộ lọc dùng `don_vi_ap_dung` xuyên suốt UI, API danh sách và thống kê. Khi giải xung đột, `staging` là nền cho các thay đổi mới đã merge; chỉ ghép lại phần thuộc issue #314 và test tương ứng.

**Tech Stack:** Django REST Framework, PostgreSQL 16, React, TypeScript, Vitest.

**Spec:** GitHub issue #314 và PR #318.

## Global Constraints

- Chỉ sửa module Nhóm 5.
- Không đổi schema, dependency, CI hoặc deploy.
- Tuân thủ i18n, design tokens và Git Flow Issue → nhánh → PR → `staging`.

## Review Focus

- Bộ lọc không được mở rộng phạm vi hồ sơ người dùng được phép xem.
- Danh sách và thống kê phải nhận cùng `don_vi_ap_dung`.
- ID đơn vị sai phải trả lỗi nghiệp vụ, không gây 500.
- Chế độ Hồ sơ/Tệp mới trên `staging` phải tiếp tục hoạt động.
- Các thay đổi đã merge về thông báo, PDF và thứ bậc cấp ký không được hồi quy.

---

### Task 1: Đồng bộ nhánh và giải xung đột

**Files:** Các file Nhóm 5 đang xung đột giữa PR #318 và `origin/staging`.

- [ ] Merge `origin/staging` vào nhánh `fix/314-bo-loc-phong-ban-trinh-ky`.
- [ ] Giữ nền `staging`, ghép lại API/type/UI/test của bộ lọc đơn vị.
- [ ] Kiểm tra `git diff --check` và phạm vi file.

### Task 2: Xác minh theo TDD và gate

**Files:** Test backend/frontend của module signing.

- [ ] Chạy test mục tiêu cho lọc danh sách, thống kê, quyền và ID sai.
- [ ] Chạy toàn bộ frontend test, lint, i18n, tokens và build.
- [ ] Chạy backend check/migration checks/test trên PostgreSQL khi môi trường cho phép.

### Task 3: Phát hành qua PR

- [ ] Commit phần hòa giải xung đột theo Conventional Commits.
- [ ] Push nhánh PR #318, chờ toàn bộ CI xanh.
- [ ] Merge PR #318 vào `staging`, theo dõi deploy tự động.
- [ ] Xác minh bản deploy và đối chiếu 8 dòng bug Nhóm 5.
