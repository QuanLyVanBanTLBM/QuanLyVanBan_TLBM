# Hướng dẫn làm việc và an toàn Git của Nhóm 3

Cập nhật ngày 24/10/2026 theo [AGENTS.md](../../../AGENTS.md) và [README](../../../README.md). Bản này thay quy trình nhánh nhóm dài hạn trong tài liệu cũ. PR và bằng chứng lịch sử giữ giá trị tại commit đã ghi; không dùng làm chỉ dẫn tích hợp hiện hành.

## Phạm vi sở hữu

Nhóm 3 quản lý `backend/apps/records/`, các trang/component/service/type/i18n Records và tài liệu nhóm. Không nhận sở hữu module tài liệu Nhóm 4 hoặc Văn bản Nhóm 2.

- Mỗi PR chỉ sửa đúng module và issue được giao.
- Danh sách/chi tiết/tạo Văn bản, bảng nối và ACL thuộc Nhóm 2; dùng API/selector của chủ module.
- Không khôi phục trang/API metadata Văn bản riêng trong Records hoặc đọc bảng nối bằng SQL.
- Tài liệu nhóm mới ở `docs/module/team_3/`. Hai tài liệu hiện hữu ở `docs/modules/03_dossiers_records/` được cập nhật tại chỗ, không di chuyển tài liệu.
- Cấu hình/dependency chung chỉ thêm đúng nhu cầu đã thống nhất từ nền staging. Tooling CI/deploy thuộc vận hành chung.

## Một issue một nhánh một PR

1. Mở issue đúng nhiệm vụ, label `nhom-3`, phạm vi và tiêu chí nghiệm thu.
2. Kiểm tra repository, nhánh, `git status`; bảo toàn thay đổi đang có.
3. Fetch staging, tạo nhánh ngắn gắn một issue từ `origin/staging`.
4. Mở Draft PR sớm, base `staging`, liên kết đúng issue.
5. Đồng bộ staging ít nhất mỗi ngày làm việc và trước khi mở PR/merge; đọc từng conflict và chạy gate trên commit cuối.
6. Người phụ trách merge theo quy định dự án và theo dõi deploy. Trong bàn giao hiện tại, người phụ trách tự thao tác staging.

Chỉ chạy ví dụ khi working tree sạch, tên nhánh mới chưa tồn tại:

```powershell
git status
git fetch origin
git switch -c docs/<issue>-<mo-ta> origin/staging
```

Tiền tố: `feat/`, `fix/`, `docs/`, `chore/`, `refactor/`; không dùng `codex/`. Không dùng `3_dossiers_documents` làm nhánh trung gian cho việc mới. Nhánh đã merge kết thúc vòng đời; phát sinh vấn đề tạo issue/nhánh mới.

Nhánh đang làm việc đồng bộ bằng merge `origin/staging` sau khi kiểm tra diff. Không tự stash/reset/đổi nhánh khi chưa xác định chủ thay đổi. Không commit/push trực tiếp `main` hoặc `staging`.

## Commit và nội dung GitHub

- Conventional Commits, ví dụ `docs(records): cập nhật hợp đồng bàn giao hồ sơ`.
- Văn phong kỹ thuật trung tính, không xưng hô cá nhân, không tuyệt đối hóa kết quả.
- Không đưa account, tên dữ liệu thử, ID seed, credential hoặc raw log có dữ liệu riêng vào GitHub.
- Bình luận/review/request changes/approve phải có bản nháp được người phụ trách duyệt trước khi gửi.
- PR đủ Objective, Changes, Verification theo AGENTS.md; `Closes #<issue>` nếu hoàn tất, `Refs #<issue>` khi còn việc.
- Chỉ cập nhật phần nhóm trong issue chung, không đóng thay nhóm khác. Phân biệt source đã tích hợp, nghiệm thu local và tích hợp toàn luồng.

Trước commit:

```powershell
git status
git diff
git diff --check
git add -- <cac-file-thuoc-nhiem-vu>
git diff --cached
```

Không dùng `git add .` máy móc. Chỉ commit file đã đọc và thuộc issue của nhánh.

## Môi trường local và dữ liệu

Dùng PostgreSQL 16 trong `compose.yaml`, ICU `vi-VN`; dựng DB duy nhất qua `scripts/build_db.py`. Lệnh wrapper theo README:

```powershell
pnpm setup:frontend
pnpm db:setup
pnpm db:start
pnpm runserver
pnpm dev
```

Setup/start có thể tạo môi trường hoặc seed: kiểm tra đúng đích DB, dữ liệu và secret trước khi chạy. Ví dụ không phải yêu cầu chạy lại seed/reset trên DB đang dùng.

- Có migration mới: `pnpm db:migrate`. DDL đổi không cho phép tự xóa dữ liệu; đọc runbook và kiểm marker/schema/migration.
- `pnpm db:reset` chỉ khi chủ ý xóa DB local, bảo toàn dữ liệu và xác nhận rõ; không dùng né drift/conflict.
- Không dùng SQLite, chạy SQL/migration trên staging hoặc sửa server thủ công.
- Nghiệm thu ghi dùng DB QA, account và dữ liệu tổng hợp, cổng/volume riêng; không đưa dữ liệu/credential thật vào fixture.
- Secret chỉ đọc từ biến môi trường. Không commit `.env`, backup, cache, dependency, log hoặc storage local.

Runbook: [dựng DB](../../common/database/build_db_runbook.md), [backup/restore](../../common/database/backup_restore_runbook.md).

## Schema và migration

`docs/common/database/release_DDL.sql` là chuẩn duy nhất. PR đổi schema phải có DDL, migration mới, mục DDL_CHANGELOG và max migration cập nhật bằng công cụ dự án.

Không sửa migration đã có trên staging hoặc thêm baseline drift để qua CI. RunSQL function/trigger/view khớp nguyên văn DDL. Conflict migration/baseline phải đồng bộ staging và tái sinh theo AGENTS.md, không ghép tay. Nhiệm vụ tài liệu không đổi schema.

## Gate và bằng chứng

Frontend: frozen install, lint, i18n, tokens, test, build. Text UI dùng namespace Records đủ vi/en; màu/font dùng tokens.

Backend: check, kiểm migration/pending, migrate, schema DDL/baseline, build_db/seed/smoke, test PostgreSQL 16 theo gate dự án.

- Ghi đúng lệnh, commit, kết quả và warning. Gate chưa chạy/chưa kết luận không được ghi đạt.
- Không đổi timeout, tắt lint, loại test hoặc sửa CI chung để làm xanh PR.
- Phân biệt API giả lập với HTTP và trình duyệt/backend thật.
- PR tài liệu chỉ đổi markdown; vẫn theo dõi gate CI thực tế trên commit cuối.

## Conflict và an toàn

Đọc cả hai phía; giữ nghiệp vụ mới trên staging và thay đổi đúng module. Không nhận toàn file cũ hoặc chọn toàn bộ một phía theo thói quen.

Không tự force push, reset hard, clean, xóa nhánh/repository để né conflict; không đổi tác giả commit. Người merge xóa nhánh khi kết thúc vòng đời.

Nếu cần sửa ngoài sở hữu hoặc gặp lỗi nền ngoài nhiệm vụ, giữ bằng chứng và bàn giao chủ module. Khi đã có chỉ đạo/phạm vi được xác nhận thì thực hiện trong phạm vi đó, không hỏi lại xác nhận đã có.

## Bàn giao hiện tại

Xem [API Records](api.md) và [trạng thái/bằng chứng](../../module/team_3/STATUS_AND_HANDOFF.md). Popup #224 đang Draft; tiếp nhận Văn bản #229/#230 còn chờ. Kết quả một module không thay thế điều kiện ship toàn dự án.
