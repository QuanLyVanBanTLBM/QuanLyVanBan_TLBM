# Project Rules & Safety Invariants (QuanLyVanBan_TLBM)

## 1. QUY CHUẨN VĂN PHONG TRÊN GIT (COMMITS, ISSUES, PRS, REVIEWS)

- **Văn phong Thực dụng & Trung tính (Technical Report Style)**:
  - Tuyệt đối không dùng từ ngữ xưng hô cá nhân (không "tôi", "em", "thầy", "bạn", không "t - m").
  - Thể hiện thái độ thực dụng, định hướng kỹ thuật và giải pháp; hạn chế tối đa yếu tố cảm xúc (không biểu cảm, không hoa mỹ, không khen ngợi hình thức).
  - Loại bỏ các đại từ và cách diễn đạt mang tính trải nghiệm cá nhân (ví dụ: "mình thấy", "tôi nhận thấy", "cảm giác").
  - Không dùng các từ ngữ cường điệu, phóng đại hoặc mang tính tuyệt đối hóa (ví dụ: "hoàn hảo", "thảm họa", "chắc chắn 100%", "cốt tử").
  - Quy chuẩn hóa dữ liệu: không dùng tên dữ liệu thử nghiệm, tài khoản cá nhân, mock/seed ID cụ thể; dùng danh từ chung (`tài khoản người dùng`, `văn bản đến`, `bản ghi sự kiện`, `/api/:endpoint`).
- **Quy trình Duyệt Review / Request Changes**:
  - Mọi nội dung phản hồi, nhận xét (PR Comments), yêu cầu điều chỉnh (Request Changes) hoặc phê duyệt (Approve) bắt buộc phải soạn thảo bản nháp nội bộ trước để người phụ trách kiểm duyệt.
  - Tuyệt đối không tự ý submit review trực tiếp lên GitHub khi chưa có sự xác nhận của người phụ trách.
- **Commit Message**: Tuân thủ chuẩn Conventional Commits (`feat(scope): ...`, `fix(scope): ...`, `docs: ...`, `refactor: ...`), viết bằng tiếng Việt hành chính chuẩn mực hoặc tiếng Anh kỹ thuật.

---

## 2. QUY ƯỚC CẤU TRÚC ISSUE (BUG REPORT)

Mọi Issue báo cáo lỗi bắt buộc tuân theo đúng cấu trúc tiêu chuẩn:

```markdown
### 1. Tóm tắt Issue (Summary)
[Mô tả ngắn gọn, súc tích bản chất của sự cố trong 1 - 2 câu]

### 2. Các bước tái hiện (Steps to Reproduce)
1. Bước 1: ...
2. Bước 2: ...
3. Bước 3: ...

### 3. Trạng thái tái hiện & Bằng chứng (Reproduction & Evidence)
- [ ] Đã tái hiện thành công (BẮT BUỘC đính kèm bằng chứng bên dưới nếu tick chọn)
- [ ] Chưa tái hiện được / Lỗi không liên tục (Flaky)

> **Bằng chứng (Evidence):** *(Bắt buộc khi tick đã tái hiện: Log console, Error trace, Mã trạng thái HTTP, Response payload, hoặc Ảnh chụp/Video)*

### 4. Hậu quả về Kỹ thuật (Technical Impact)
[Ảnh hưởng đến database, rò rỉ bộ nhớ, race condition, crash server, tính toàn vẹn dữ liệu...]

### 5. Hậu quả đến Người dùng (User Impact)
[Người dùng bị chặn thao tác nào, dữ liệu hiển thị sai ra sao, trải nghiệm bị gián đoạn thế nào...]

### 6. Mô tả chi tiết Bug
- **Biểu hiện trên UI**: [Giao diện bị treo, vỡ layout, không phản hồi click, toast lỗi không hiện...]
- **Nguyên nhân trong Code**: [Phân tích logic bị sai, hàm nào, file nào, unhandled exception nào trong codebase]

### 7. Hướng khắc phục đề xuất (Proposed Fix)
[Giải pháp xử lý kỹ thuật tối giản theo KISS/YAGNI, không gây side-effect]
```

---

## 3. QUY ƯỚC CẤU TRÚC PULL REQUEST (PR)

Mọi Pull Request bắt buộc trình bày đầy đủ các phần:

```markdown
### 1. Mục tiêu thay đổi (Objective)
[Tóm tắt mục đích của PR: giải quyết issue nào, hoàn thành task nào]

### 2. Chi tiết thay đổi kỹ thuật (Changes)
- `path/to/file`: Mô tả ngắn gọn thay đổi và lý do kỹ thuật.

### 3. Kiểm thử & Bằng chứng xác thực (Verification & Technical Gates)
- [x] Frontend Build: `pnpm --dir frontend run build` (Pass, 0 warning/error)
- [x] Backend Check: `python backend/manage.py check` (Pass)
- [x] Tuân thủ i18n & CSS Tokens: Đã kiểm tra đầy đủ cả 2 nhánh `vi`/`en` và không hardcode mã màu/px.
```

---

## 4. Các Invariant Kỹ thuật Bắt buộc
- **i18n (Trụ cột 1)**: 100% text trên giao diện React phải dùng `t('namespace.key')`. Mỗi module giữ từ điển riêng tại `frontend/src/i18n/<module>/vi.json` và `en.json`; mọi key mới phải có đầy đủ cả 2 nhánh trong file của module mình, không khai báo key đã có ở module khác (kiểm bằng `pnpm --dir frontend check:i18n`). Không dùng dạng `lang === 'en' ? ... : ...` trong component.
- **Design Tokens (Trụ cột 3)**: Không dùng mã màu Hex (`#...`) hay font-size pixel trong CSS. Bắt buộc dùng `var(--color-...)` và `var(--font-...)` từ `src/styles/global.css` (kiểm bằng `pnpm --dir frontend check:tokens`).
- **Git Flow**: Không commit/push trực tiếp vào `main` và `staging`. Mọi thay đổi đi theo vòng đời Issue → Nhánh → PR (mục 8). Kiểm tra `git status` trước khi commit, không dùng `git add .` bừa bãi.

---

## 5. CƠ SỞ DỮ LIỆU: MỘT NGUỒN SCHEMA, MỘT CÁCH DỰNG DB

- **Nguồn schema duy nhất**: `docs/common/database/release_DDL.sql`. Model và migration Django phải sinh ra đúng schema này (bảng, cột, kiểu, NULL, DEFAULT, constraint, index, ENUM, function, trigger, view, dữ liệu seed). Khi code và DDL khác nhau, DDL là chuẩn.
- **Cách dựng DB duy nhất**: `scripts/build_db.py` (nạp DDL rồi đồng bộ trạng thái migration; collation ICU `vi-VN`). Local, CI và staging đều dùng script này. Không dựng DB bằng tay, không chạy `migrate` bằng tay lên DB staging (deploy tự nâng cấp DB bằng migration). Chi tiết: `docs/common/database/build_db_runbook.md`.
- **Chỉ PostgreSQL 16**: không dùng SQLite cho phát triển hay kiểm thử. Test backend chạy trên PostgreSQL.
- **Đổi schema** (thêm/sửa/xoá bảng, cột, constraint, ENUM, function, trigger, view, seed) phải nằm trong **cùng một PR** gồm:
  1. sửa `release_DDL.sql`;
  2. migration Django mới sinh ra đúng thay đổi đó (không sửa migration đã có trên `staging`);
  3. một mục mới trong `docs/common/database/DDL_CHANGELOG.md`: ngày, PR, đối tượng thay đổi, lý do.
  PR đổi schema qua được bước so schema của CI thì nhóm sở hữu module tự merge và chịu trách nhiệm.
- **Baseline lệch** `docs/common/database/schema_drift_baseline.txt` ghi các lệch cũ giữa migration và DDL, **chỉ được giảm**:
  - Không thêm dòng mới để PR qua được CI. Lệch mới phải sửa bằng migration hoặc bằng thay đổi DDL theo quy trình trên.
  - Sửa xong lệch nào thì xoá đúng dòng đó (CI báo lỗi khi baseline còn dòng đã hết lệch).
  - Khi conflict ở file này: merge `staging` vào nhánh, chạy lại `.github/scripts/compare_schema_ddl.py --write-baseline` trên DB dựng như CI, giữ kết quả mới, không ghép dòng bằng tay.
- **Mỗi app một nhánh migration**: mỗi app có `migrations/max_migration.txt` ghi tên migration mới nhất. Thêm migration xong chạy `python .github/scripts/check_max_migration.py --write` và commit file này cùng migration. Hai PR cùng thêm migration cho một app sẽ conflict ở file này; PR sau merge `staging`, đánh lại số migration của mình nối tiếp migration trên `staging` (không sửa migration đã có trên `staging`), rồi chạy lại `--write`.
- **Function/trigger/view tạo bằng migration** (`RunSQL`) phải chép nguyên văn từ `release_DDL.sql`; bước so schema so nguyên văn, khác một khoảng trắng cũng bị coi là lệch.
- **Sau khi pull code có đổi schema**: `pnpm db:migrate` (đồng bộ migration mới); nếu `release_DDL.sql` đổi thì `pnpm db:reset` (dựng lại DB local từ DDL).

---

## 6. PHẠM VI SỞ HỮU MODULE (TRÁNH CONFLICT CHÉO)

- **Mỗi PR chỉ sửa code của module mình.** Cần hành vi khác từ module khác thì gọi API/selector của module đó; muốn đổi logic của module khác thì mở PR riêng cho module đó.
- **Logic dùng chung thuộc về module sở hữu dữ liệu**. Ví dụ: quy tắc ai được xem văn bản (`backend/apps/documents/selectors.py`, `van_ban_xem_duoc`) thuộc module Văn bản; dashboard và module khác chỉ gọi selector này, không viết lại quy tắc và không truy vấn SQL thô vượt qua lớp phân quyền.
- **Mỗi module một namespace API** dưới `/api/<module>/...` (ví dụ AI: `/api/ai/...`). Không khai báo route trùng tiền tố với module khác.
- **Không dùng dữ liệu mock thay backend thật** trên route chính thức; không thêm route trùng đường dẫn với trang đã có.
- **Cấu hình và dependency dùng chung** (`backend/config/settings.py`, `backend/requirements.txt`, `frontend/package.json`, `pnpm-lock.yaml`, `.env.example`):
  - Lấy bản `staging` làm nền, chỉ thêm đúng phần module cần, ghi lý do trong PR.
  - Không nới cận phiên bản, không thêm driver/thư viện trùng chức năng, không đặt giá trị nới lỏng bảo mật (ví dụ `ALLOWED_HOSTS = ["*"]`).
  - Bí mật (khoá API, mật khẩu) chỉ đọc từ biến môi trường, không có giá trị mặc định trong mã nguồn.
  - `pnpm-lock.yaml` sinh lại bằng `pnpm install`, không sửa tay.
- **Tooling CI và deploy** (`.github/workflows/`, `.github/scripts/`, `scripts/build_db.py`, `deploy/`) thuộc phần vận hành chung; PR tính năng không viết lại các file này.
- **Trước khi mở PR và trước khi merge**: merge `staging` mới nhất vào nhánh, giải conflict theo các quy tắc trên, chạy lại gate (mục 7).

---

## 7. GATE TRƯỚC KHI MERGE VÀ MÔI TRƯỜNG

- **Gate bắt buộc** (CI chạy tự động; khi CI không chạy được thì chạy local tương đương và ghi kết quả vào PR):
  - Backend: `manage.py check`, `makemigrations --check --dry-run`, `migrate`, `migrate --check`, so schema với DDL (`.github/scripts/compare_schema_ddl.py` + baseline), `scripts/build_db.py --seed` + smoke ENUM/trigger/function/view, `manage.py test` trên PostgreSQL.
  - Frontend: `pnpm install --frozen-lockfile`, `lint`, `check:i18n`, `check:tokens`, `test`, `build`.
  - Không tắt rule lint, không bỏ qua hay loại trừ test để qua gate.
- **Merge**: PR vào `staging` gắn issue và qua toàn bộ CI thì nhóm sở hữu module tự merge bằng nút Merge trên PR và chịu trách nhiệm về thay đổi. Người merge theo dõi job deploy staging sau merge.
- **Môi trường local**: dùng các lệnh `pnpm` trong `package.json` (`db:setup`, `db:start`, `db:migrate`, `db:reset`, `runserver`, `dev`); hướng dẫn đầy đủ trong `README.md`. PostgreSQL local chạy bằng `compose.yaml` (collation ICU `vi-VN`).
- **Staging**: merge vào `staging` thì CI tự deploy bằng `deploy/deploy.sh` ở chế độ giữ dữ liệu (`DB_MODE=sync`): sao lưu, chạy thử migration trên bản sao, rồi nâng cấp DB bằng migration. Dựng lại DB (`rebuild`) chỉ khi chọn có chủ đích. Không deploy, không sửa DB hay cấu hình server staging bằng tay; thay đổi cấu hình server đi qua PR vào `deploy/`.

---

## 8. VÒNG ĐỜI CÔNG VIỆC: ISSUE → NHÁNH → PR → STAGING

- **Mỗi vấn đề một issue.** Lỗi, tính năng, việc kỹ thuật đều mở issue trước khi code (mẫu tại `.github/ISSUE_TEMPLATE/`), có label nhóm. Việc lớn tách thành nhiều issue con, mỗi issue làm xong được trong vài ngày.
- **Mỗi nhánh gắn đúng một issue.**
  - Tạo từ `staging` mới nhất: `git fetch origin && git switch -c feat/<số-issue>-<mô-tả-ngắn> origin/staging`.
  - Tiền tố: `feat/`, `fix/`, `docs/`, `chore/`, `refactor/`; không dùng tiền tố `codex`. Ví dụ: `fix/164-tim-kiem-ho-so`.
  - Một nhánh không gom nhiều issue; phát sinh vấn đề khác trong lúc làm thì mở issue mới và nhánh mới.
- **Mỗi PR gắn issue của nhánh.** PR vào `staging`, mô tả có dòng `Closes #<số>` (hoặc `Refs #<số>` khi issue chưa xong hẳn). PR không gắn issue thì không merge.
- **Vòng đời nhánh kết thúc khi merge vào `staging`.**
  - Merge xong người merge xoá nhánh (nút Delete branch trên PR); issue tự đóng qua `Closes #`.
  - Không tiếp tục commit lên nhánh đã merge. Sửa tiếp hoặc lỗi phát sinh sau merge: issue mới, nhánh mới từ `staging`.
  - Không dùng nhánh nhóm dài hạn làm nhánh trung gian; PR đi thẳng vào `staging`.
- **Giữ nhánh ngắn để tránh conflict.**
  - Trong lúc làm, merge `staging` vào nhánh ít nhất mỗi ngày làm việc và trước khi merge.
  - Mở draft PR sớm để nhóm khác thấy file đang bị sửa.
  - Hai issue cùng sửa một file dùng chung thì làm tuần tự, issue sau chờ PR trước merge.
- **PR không còn phù hợp** (đã có thay đổi khác thay thế, nhánh nguồn mất) thì đóng kèm lý do và số PR/commit thay thế; phần còn thiếu mở issue mới.
