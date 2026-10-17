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
- **i18n (Trụ cột 1)**: 100% text trên giao diện React phải dùng `t('namespace.key')`. Mọi key mới phải có đầy đủ cả 2 nhánh `vi` và `en` trong `frontend/src/i18n/translations.js`.
- **Design Tokens (Trụ cột 3)**: Không dùng mã màu Hex (`#...`) hay font-size pixel trong CSS. Bắt buộc dùng `var(--color-...)` và `var(--font-...)` từ `src/styles/global.css`.
- **Git Flow**: Không commit/push trực tiếp vào `main`. Kiểm tra `git status` trước khi commit, không dùng `git add .` bừa bãi.
