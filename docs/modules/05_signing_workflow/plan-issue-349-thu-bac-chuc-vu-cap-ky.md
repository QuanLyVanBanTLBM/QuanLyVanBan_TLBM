# Ràng buộc thứ bậc chức vụ giữa các cấp ký — Kế hoạch triển khai Issue #349

> **Dành cho agent triển khai:** Bắt buộc dùng `executing-plans` và thực hiện từng tác vụ theo TDD.

**Mục tiêu:** Cấp ký có người ký theo chức vụ chỉ được dùng chức vụ có thứ bậc cao hơn hoặc bằng cấp có chức vụ liền trước, đồng thời giữ nguyên hành vi chọn cán bộ đích danh.

**Kiến trúc:** Backend là lớp cưỡng chế cuối cùng, kiểm tra payload trước mọi thao tác ghi trong `tao_quy_trinh` và `sua_quy_trinh`. Frontend tính giới hạn từ các cấp có người ký theo chức vụ gần nhất ở hai phía, lọc gợi ý chức vụ và hiển thị giải thích; lựa chọn tài khoản cụ thể không tham gia phép so sánh.

**Công nghệ:** Django/PostgreSQL 16, React 19/TypeScript, Django TestCase, Vitest/Testing Library.

**Đặc tả:** [GitHub Issue #349](https://github.com/QuanLyVanBanTLBM/QuanLyVanBan_TLBM/issues/349) và `docs/modules/05_signing_workflow/spec.md`.

## Ràng buộc toàn cục

- Chỉ sửa phạm vi Nhóm 5: `backend/apps/signing`, `frontend/src/pages/signing`, `frontend/src/lib/signing/i18n`, tài liệu của module 05.
- Chỉ đọc `accounts_position.display_order`; số nhỏ hơn là chức vụ cao hơn. Không sửa model, API hoặc dữ liệu Nhóm 7.
- Không đổi schema, không thêm migration hoặc dependency.
- Người ký theo tài khoản đích danh không bị ràng buộc.
- Quy trình đã lưu không bị hồi tố; kiểm tra áp dụng khi tạo mới hoặc lưu lại bản nháp.
- Text giao diện phải đủ `vi`/`en`; không thêm mã màu hoặc cỡ chữ hardcode.

## Trọng tâm review

- Payload có cấp chỉ chứa người ký đích danh phải được bỏ qua khi tìm cấp có chức vụ liền trước/liền sau.
- Nhiều chức vụ song song trong một cấp phải so theo `display_order` nhỏ nhất của cấp đó.
- `chuc_vu_id` không tồn tại vẫn phải trả lỗi tham chiếu hiện có, không bị đổi thành lỗi thứ bậc.
- Sửa bản nháp vi phạm phải rollback, giữ nguyên toàn bộ cấu trúc quy trình cũ.
- Frontend không được làm hẹp danh bạ “Chọn cán bộ đích danh”.

---

### Tác vụ 1: Cưỡng chế thứ bậc ở service backend

**Files:**
- Tạo: `backend/apps/signing/tests/test_thu_bac_chuc_vu_cap_ky.py`
- Sửa: `backend/apps/signing/services/process.py`

**Interfaces:**
- Consumes: `Position.display_order`, payload `cap_ky[*].nguoi_ky[*].chuc_vu_id`.
- Produces: `_kiem_tra_thu_bac_chuc_vu_cap_ky(cap_ky)`; lỗi nghiệp vụ `cap_ky_thu_bac_khong_hop_le` trước khi ghi dữ liệu.

- [ ] Viết test RED cho tạo hợp lệ khi cấp sau có thứ bậc cao hơn hoặc bằng cấp chức vụ gần nhất phía trước.
- [ ] Viết test RED cho tạo vi phạm và xác nhận không có `SigningProcess` nào được ghi.
- [ ] Viết test RED cho một cấp, cấp chỉ có tài khoản, cấp có nhiều chức vụ song song và `chuc_vu_id` không tồn tại.
- [ ] Viết test RED cho sửa bản nháp vi phạm và xác nhận cấu trúc cũ không đổi.
- [ ] Chạy `python backend/manage.py test signing.tests.test_thu_bac_chuc_vu_cap_ky` và xác nhận lỗi vì chưa có kiểm tra thứ bậc.
- [ ] Cài đặt helper tối giản: lấy thứ bậc theo một query, sắp cấp theo `thu_tu`, bỏ qua cấp không có chức vụ, so `min(display_order)` của hai cấp chức vụ liên tiếp.
- [ ] Gọi helper trước mọi ghi dữ liệu trong `tao_quy_trinh` và `sua_quy_trinh`; giữ lỗi tham chiếu hiện có cho ID không tồn tại.
- [ ] Chạy lại test mục tiêu; kỳ vọng PASS.

### Tác vụ 2: Lọc gợi ý và giải thích giới hạn trên frontend

**Files:**
- Sửa: `frontend/src/pages/signing/QuyTrinhPage.tsx`
- Sửa: `frontend/src/pages/signing/signing.test.tsx`
- Sửa: `frontend/src/lib/signing/i18n/vi.json`
- Sửa: `frontend/src/lib/signing/i18n/en.json`

**Interfaces:**
- Consumes: `ChucVu.display_order`, `CapNhap.nguoi_ky[*].chuc_vu_id`.
- Produces: `tinhGioiHanThuBac(...)` và prop `gioiHanThuBac` cho `ThemNguoiKyCap`; các key i18n cho lỗi backend và gợi ý hai phía.

- [ ] Viết test RED: cấp sau chỉ gợi ý chức vụ cao hơn/bằng cấp chức vụ gần nhất phía trước và hiển thị giải thích.
- [ ] Viết test RED: sửa cấp trước phải tôn trọng cấp chức vụ gần nhất phía sau.
- [ ] Viết test RED: danh bạ cán bộ đích danh vẫn hiển thị đầy đủ và không chịu bộ lọc thứ bậc.
- [ ] Chạy test mục tiêu trong `signing.test.tsx`; xác nhận lỗi do chưa có giới hạn.
- [ ] Cài đặt phép tính giới hạn hai phía và lọc option theo thứ bậc hiệu lực của cấp (`min` giữa chức vụ hiện có và ứng viên).
- [ ] Truyền `gioiHanThuBac` từ `FormTao` vào từng `ThemNguoiKyCap`; hiển thị gợi ý/cảnh báo ngay dưới dropdown chức vụ, cạnh trạng thái lỗi tải danh mục.
- [ ] Thêm đủ bản dịch `vi`/`en`, gồm mã lỗi `cap_ky_thu_bac_khong_hop_le`.
- [ ] Chạy lại test mục tiêu; kỳ vọng PASS.

### Tác vụ 3: Gate và bàn giao Git

**Files:** Chỉ sáu file implementation/test ở trên và kế hoạch này.

**Interfaces:**
- Consumes: kết quả hai tác vụ trước.
- Produces: commit Conventional Commits và PR vào `staging` có `Closes #349`.

- [ ] Chạy backend: `manage.py check`, `makemigrations --check --dry-run`, test mục tiêu, sau đó `manage.py test signing` trên PostgreSQL 16.
- [ ] Chạy frontend: `pnpm --dir frontend install --frozen-lockfile`, `lint`, `check:i18n`, `check:tokens`, `test`, `build`.
- [ ] Kiểm tra `git diff --check`, `git status`, và xác nhận không có file ngoài phạm vi.
- [ ] Review toàn nhánh theo Issue #349; sửa duy nhất các lỗi Critical/Important bằng RED→GREEN.
- [ ] Merge `origin/staging` mới nhất vào nhánh, chạy lại các gate bị ảnh hưởng.
- [ ] Commit bằng tiếng Việt không dấu theo Conventional Commits; push nhánh và mở PR đúng mẫu, không tự merge.
