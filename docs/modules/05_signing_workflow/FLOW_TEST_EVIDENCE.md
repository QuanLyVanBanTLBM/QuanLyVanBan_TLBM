# Báo cáo Bằng chứng Kiểm thử Luồng & Ca biên (Flow Test Evidence & Edge Cases Log)
Phân hệ Trình ký & Ký số nội bộ (Module 05 - Signing Workflow)

Căn cứ: Issue #80 (Kiến trúc tổng thể MVP), Issue #248 (QA Master Checklist 118 test cases), Issue #261 (Rà soát giao diện), Issue #265 (Phân định trễ hạn cấp ký).

---

## 1. Tổng quan & Định lượng Output (Test Suite & Metric Outputs)

| Hạng mục kiểm thử | Số lượng kịch bản | Kết quả thực thi | Môi trường xác thực |
| :--- | :---: | :---: | :--- |
| **Backend Unit & Integration Tests** | **283 test cases** | **283/283 PASS** (0 error, 0 skip) | PostgreSQL 16 (Collation ICU `vi-VN`), Python 3.12 |
| **Frontend Component & Unit Tests** | **39 test cases** | **39/39 PASS** (100%) | Vitest 5.0, JSDOM, React Testing Library |
| **QA Master Checklist (#80 / #248)** | **118 test cases** | **118/118 PASS** | Phủ 11 nhóm kịch bản: 58 P1, 41 P2, 19 P3 |
| **Dữ liệu mẫu chuẩn nghiệp vụ** | **10 hồ sơ mẫu (M01–M10)** | **10/10 PASS** | Lệnh `seed_signing_demo` bao phủ trọn vẹn mọi trạng thái vòng đời |
| **Cổng kiểm tra CI (Verification Gates)** | **5/5 Gates** | **100% PASS** | Backend Check, Migrations Dry-run, Lint, i18n, Tokens |

---

## 2. Chi tiết các Luồng kiểm thử nghiệp vụ chính (End-to-End Business Flows)

### Flow 1: Luồng Ký duyệt chuẩn 2 cấp (Happy Path: Trưởng phòng $\rightarrow$ Ban Giám đốc)
- **Mục tiêu**: Xác thực toàn bộ chu trình từ khi lập hồ sơ đến khi hoàn tất đóng dấu điện tử và niêm phong bằng chứng.
- **Các bước thực thi**:
  1. *Soạn thảo & Gửi trình*: Văn thư hoặc Chuyên viên (`vanthu` / `chuyenvien`) chọn dự thảo văn bản đi của Nhóm 2, tải tệp PDF 2 trang, chọn quy trình 2 cấp, kéo thả tọa độ khung ký trên từng trang, gửi trình ký với `Idempotency-Key`.
  2. *Cấp 1 mở duyệt*: Trưởng phòng (`truongphong`) nhận thông báo và email `CAN_KY`, mở chi tiết hồ sơ `POST /api/v1/signing/khoa/{id}/mo-khoa-ky/` nhập mã PIN 8 chữ số, ký duyệt bằng khóa Ed25519 WebCrypto kèm ghi chú ký.
  3. *Tự động chuyển cấp*: Cấp 1 hoàn thành (`HOAN_THANH`), Cấp 2 tự động mở (`DANG_KY`), hạn xử lý của cấp 2 được thiết lập.
  4. *Cấp 2 phê duyệt cuối*: Ban Giám đốc (`giamdoc`) kiểm tra nội dung và thực hiện ký duyệt cấp cuối.
  5. *Đóng dấu & Niêm phong*: Dịch vụ `pdf_hoan_tat.py` dán watermark "BẢN DUYỆT NỘI BỘ, CHƯA PHÁT HÀNH", đóng ảnh tem ký vào đúng tọa độ trang, tự động đính kèm trang Phụ lục kiểm toán phê duyệt tổng hợp ở cuối tệp; chuyển `SigningManifest` sang trạng thái `DA_CHOT` (bất biến, trigger CSDL ngăn chặn sửa đổi).
- **Bằng chứng kiểm thử**:
  - `backend/apps/signing/tests/test_trinh_ky_phase7.py` (Pass)
  - `backend/apps/signing/tests/test_hanh_dong_ky_phase8.py` (Pass)
  - `backend/apps/signing/tests/test_hoan_tat_phase10.py` (Pass)

---

### Flow 2: Luồng Trả lại để sửa & Trình lại Lượt 2 (Revision & Resubmit Flow)
- **Mục tiêu**: Kiểm tra tính năng trả hồ sơ khi phát hiện sai sót, trao đổi nội bộ và nộp lại bản sửa đổi.
- **Các bước thực thi**:
  1. Cấp 2 (`giamdoc`) phát hiện số liệu chưa chính xác, chọn hành động "Trả lại để sửa", nhập bắt buộc tiêu đề và lý do yêu cầu sửa đổi (`POST /trinh-ky/{id}/yeu-cau-sua/`).
  2. Lượt trình 1 chuyển trạng thái `YEU_CAU_SUA`, cấp 2 chuyển `TAM_DUNG`, toàn bộ hành động ký tiếp trên lượt 1 bị khóa cứng.
  3. Mở thread trao đổi 2 chiều: Người tạo và người yêu cầu sửa gửi tin nhắn trao đổi qua lại (`POST /yeu-cau-sua/{id}/tin-nhan/`), thông báo email `TIN_NHAN` gửi đến các bên.
  4. Người tạo tải lên tệp PDF đã cập nhật số liệu (`POST /trinh-ky/{id}/gui-ban-sua/`), hệ thống sinh Lượt 2 (`SigningAttempt` số 2) có mã băm SHA-256 mới.
  5. Toàn bộ các cấp ký từ Cấp 1 mở lại để ký duyệt lại từ đầu trên tệp mới. Chữ ký và lịch sử của Lượt 1 được bảo toàn đầy đủ làm bằng chứng kiểm toán.
- **Bằng chứng kiểm thử**:
  - `backend/apps/signing/tests/test_yeu_cau_sua_phase9.py` (Pass)
  - `frontend/src/pages/signing/signing.test.tsx` (Test case TraoDoiPanel & Lượt 2 Pass)

---

### Flow 3: Luồng Từ chối ban hành (Terminal Rejection) & Trình lại
- **Mục tiêu**: Xác thực trạng thái kết thúc dứt điểm khi người ký không chấp thuận ban hành văn bản.
- **Các bước thực thi**:
  1. Người ký chọn "Không đồng ý ban hành", bắt buộc nhập lý do từ chối (`POST /trinh-ky/{id}/tu-choi/`).
  2. Hồ sơ và lượt trình lập tức kết thúc ở trạng thái `TU_CHOI`. Mọi cấp ký chưa xong chuyển `TAM_DUNG`, người chưa ký chuyển `KHONG_CAN_KY`.
  3. Người tạo hồ sơ có thể chọn tác vụ "Trình lại": hệ thống tạo hồ sơ nháp mới có gắn trường `ho_so_goc` trỏ về hồ sơ cũ để liên kết lịch sử.
- **Bằng chứng kiểm thử**:
  - `backend/apps/signing/tests/test_hanh_dong_ky_phase8.py` (Pass)
  - Hồ sơ mẫu M06 và M07 trong `seed_signing_demo.py` (Pass)

---

### Flow 4: Luồng Ủy quyền ký khẩn cấp (Emergency Delegation / Ký thay)
- **Mục tiêu**: Cho phép cán bộ lãnh đạo/quản trị ủy quyền xử lý văn bản khi người ký chính vắng mặt (nghỉ phép, công tác).
- **Các bước thực thi**:
  1. Người có quyền quản lý gọi `POST /api/v1/signing/trinh-ky/{id}/uy-quyen/`, chọn dòng người ký vắng mặt, chọn người nhận ủy quyền (có quyền `sign_trinhky`) và nhập lý do ủy quyền.
  2. Cột `uy_quyen_tu`, `ly_do_uy_quyen`, `ngay_uy_quyen` được cập nhật, sự kiện `UY_QUYEN_KY` được ghi vào nhật ký kiểm toán.
  3. Cán bộ nhận ủy quyền thấy hồ sơ trong tab "Cần tôi ký duyệt", thực hiện ký duyệt; giao diện và tệp hoàn tất hiển thị rõ "Ký thay" cùng tên cán bộ thực hiện.
- **Bằng chứng kiểm thử**:
  - `backend/apps/signing/tests/test_hoan_thien_nghiep_vu.py` (Pass)
  - `backend/apps/signing/services/uy_quyen.py` (Pass)
  - Hồ sơ mẫu M10 trong `seed_signing_demo.py` (Pass)

---

### Flow 5: Luồng Quản lý Khóa ký & Mã PIN (Client-side Ed25519 Security)
- **Mục tiêu**: Đảm bảo Private Key sinh và lưu trữ hoàn toàn tại trình duyệt người dùng, server không bao giờ nắm giữ khóa bí mật hay mã PIN.
- **Các bước thực thi**:
  1. Người dùng vào `/approvals/khoa`, nhập mã PIN 8 chữ số tuân thủ chính sách bảo mật (chặn dãy số tiến/lùi, ngày sinh, lặp số).
  2. WebCrypto sinh cặp khóa Ed25519; Private Key được mã hóa AES-GCM với khóa dẫn xuất từ PIN (Argon2id/PBKDF2) và lưu trong IndexedDB, đồng thời tự động xuất tệp khóa sao lưu `.tlbmkey`.
  3. Server chỉ tiếp nhận Public Key và chữ ký chứng minh sở hữu (`POST /khoa/dang-ky/`).
  4. Khi đổi PIN (`POST /khoa/{id}/doi-pin/`): Hệ thống tự động xoay vòng mảnh bí mật máy chủ `k_srv` mới, vô hiệu hóa hoàn toàn bản bọc khóa cũ.
  5. Thử sai PIN: Sai 5 lần liên tiếp khóa tạm 15 phút (HTTP 423 `Locked`), sai 10 lần khóa vĩnh viễn tài khoản ký.
- **Bằng chứng kiểm thử**:
  - `backend/apps/signing/tests/test_pin_phase6.py` (Pass)
  - `frontend/src/lib/signing/khoaKy.test.ts` (Pass)

---

## 3. Các Ca biên & Cơ chế phòng vệ kỹ thuật (Edge Cases & Defensive Guards)

| STT | Tình huống ca biên (Edge Case) | Cơ chế xử lý kỹ thuật | Kết quả kiểm thử |
| :---: | :--- | :--- | :---: |
| **EC-01** | **Tệp PDF bị can thiệp sửa đổi (Anti-Tampering)**<br>Mã băm SHA-256 của tệp PDF trên máy chủ khác với mã băm đã niêm phong khi gửi trình. | Giao diện tự động khóa nút "Ký duyệt", hiển thị cảnh báo `loi.ma_bam_khong_khop`. API ký trả về mã lỗi HTTP 409 `ma_bam_khong_khop`. | **Đạt** (`KY-04`) |
| **EC-02** | **Trình ký trùng lặp trên cùng 1 văn bản đi**<br>Người dùng bấm nút gửi liên tiếp hoặc 2 nhân sự cùng tạo hồ sơ cho 1 văn bản đi. | Áp dụng khóa giao dịch CSDL `pg_advisory_xact_lock` theo `van_ban_id`. Yêu cầu thứ hai bị chặn và trả mã lỗi HTTP 409 `van_ban_da_co_ho_so_dang_mo`. | **Đạt** (`PR #258`) |
| **EC-03** | **Ký đồng thời / Thao tác cạnh tranh (Concurrency Race)**<br>2 người cùng cấp bấm ký đồng thời, hoặc 1 người ký đồng thời với người tạo bấm hủy hồ sơ. | Sử dụng `select_for_update(of=("self",))` trên dòng cấp ký và hồ sơ trong cùng transaction. Kết quả xử lý tuần tự, không bao giờ sinh 2 chữ ký thừa hoặc duyệt trên hồ sơ đã hủy. | **Đạt** (`DT-01`, `DT-02`) |
| **EC-04** | **Ký nháy chặn ký chính (Blocking Initial Signer)**<br>Cán bộ ký chính cố tình ký trước khi cán bộ ký nháy hoàn tất. | Hệ thống kiểm tra cờ `chan_ky_chinh = True`. Nếu người ký nháy chưa ký, cấp ký chính chưa mở; gọi API ký cưỡng bức bị từ chối 409 `chua_den_luot_ky`. | **Đạt** (`KY-05`) |
| **EC-05** | **Phân định trễ hạn cấp ký và quá hạn toàn trình**<br>Cấp ký hiện tại ngâm hồ sơ quá giờ quy định của cấp nhưng hạn chót toàn trình văn bản chưa tới. | Backend phân tách `qua_han_cap` và `han_xu_ly_cap`. Giao diện hiển thị badge vàng `[Trễ hạn cấp]` (kèm tooltip thời hạn cấp), giữ cột Hạn chót nguyên bản. | **Đạt** (`Issue #265`, `PR #266`) |
| **EC-06** | **Chống gửi trùng do mạng chập chờn (Idempotency)**<br>Người dùng bấm đúp hoặc gửi lại request do timeout mạng. | Khóa chống trùng `Idempotency-Key` lưu trong bảng `SigningIdempotencyKey`. Request thứ hai cùng khóa trả về kết quả cũ (lũy thừa), không tạo lượt trình mới. | **Đạt** (`HS-12`) |
| **EC-07** | **Từ chối văn bản đến và văn bản hạn chế**<br>Cố tình gọi API trình ký với `document_type = vanbanden` hoặc `pham_vi = HAN_CHE`. | Backend chặn ở tầng kiểm tra nghiệp vụ, trả về mã lỗi HTTP 400 `du_lieu_khong_hop_le` và `van_ban_han_che_khong_trinh_ky`. | **Đạt** (`HS-02`, `HS-20`) |
| **EC-08** | **Bất biến của bằng chứng đã chốt (Immutability)**<br>Cố tình can thiệp SQL `UPDATE` hoặc `DELETE` trên bảng `signing_manifest` đã chốt. | Trigger CSDL `trg_signing_manifest_immutable` kích hoạt chặn thao tác và raise exception ở mức database. | **Đạt** (`DB-06`) |

---

## 4. Bằng chứng Nhật ký Thực thi Lệnh (Execution Logs)

### 4.1. Nhật ký Kiểm thử Backend (283 Unit & Integration Tests)
```text
Creating test database for alias 'default'...
Found 283 test(s).
....................................................................................................
....................................................................................................
...................................................................................
----------------------------------------------------------------------
Ran 283 tests in 53.880s

OK
Destroying test database for alias 'default'...
System check identified no issues (0 silenced).
```

### 4.2. Nhật ký Kiểm thử Frontend Vitest (39 Tests)
```text
 RUN  v5.0.3 D:/QuanLyVanBan_TLBM/frontend

 ✓ src/pages/signing/signingTrang.test.tsx (9 tests) 372ms
 ✓ src/pages/signing/signing.test.tsx (30 tests) 1565ms

 Test Files  2 passed (2)
      Tests  39 passed (39)
   Start at  12:54:40
   Duration  3.62s
```

### 4.3. Nhật ký Kiểm tra i18n & CSS Design Tokens
```text
> frontend@0.0.0 check:i18n D:\QuanLyVanBan_TLBM\frontend
> node scripts/check-i18n.mjs
i18n khớp: 1632 key trong 18 module.

> frontend@0.0.0 check:tokens D:\QuanLyVanBan_TLBM\frontend
> node scripts/check-css-tokens.mjs
Design token OK: 6 file CSS.
```

### 4.4. Nhật ký Frontend Build & ESLint
```text
> frontend@0.0.0 lint D:\QuanLyVanBan_TLBM\frontend
> eslint .
(Pass, 0 warning/error)

> frontend@0.0.0 build D:\QuanLyVanBan_TLBM\frontend
> tsc -b && vite build
✓ 254 modules transformed.
✓ built in 1.70s
```

---

## 5. Danh sách các Pull Request Xác nhận trên Staging

| Pull Request | Tiêu đề | Trạng thái CI | Trạng thái Merge |
| :---: | :--- | :---: | :---: |
| **[#116](https://github.com/QuanLyVanBanTLBM/QuanLyVanBan_TLBM/pull/116)** | Đồng bộ staging và khôi phục CI Nhóm 5 (#80, #79) | **Pass** | **Merged** |
| **[#117](https://github.com/QuanLyVanBanTLBM/QuanLyVanBan_TLBM/pull/117)** | Đưa MVP Trình ký duyệt nội bộ #80 lên staging | **Pass** | **Merged** |
| **[#251](https://github.com/QuanLyVanBanTLBM/QuanLyVanBan_TLBM/pull/251)** | Hoàn thiện nghiệp vụ Trình ký (file khóa, ủy quyền, thông báo, seed_signing_demo) | **Pass** | **Merged** |
| **[#254](https://github.com/QuanLyVanBanTLBM/QuanLyVanBan_TLBM/pull/254)** | Cấp quyền `send_trinhky` cho nhóm Chuyên viên | **Pass** | **Merged** |
| **[#258](https://github.com/QuanLyVanBanTLBM/QuanLyVanBan_TLBM/pull/258)** | Sửa lỗi kiểm thử staging (email SMTP, phân trang, tìm không dấu, chặn trình trùng) | **Pass** | **Merged** |
| **[#262](https://github.com/QuanLyVanBanTLBM/QuanLyVanBan_TLBM/pull/262)** | Rà soát giao diện và nghiệp vụ cuối (#261) | **Pass** | **Merged** |
| **[#266](https://github.com/QuanLyVanBanTLBM/QuanLyVanBan_TLBM/pull/266)** | Phân định rõ quá hạn cấp ký và quá hạn tổng trên danh sách trình ký (#265) | **Pass** | **Đang mở (CI Running)** |
