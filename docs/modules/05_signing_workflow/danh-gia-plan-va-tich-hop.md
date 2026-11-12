# Đánh giá plan Trình ký số (Nhóm 5): luồng, phân pha và tích hợp module

> **Tài liệu căn cứ:**
> - Plan chính thức: `docs/modules/05_signing_workflow/signing-backend-plan.md` trên nhánh `5_signing_workflow`, commit `c1b9704` (771 dòng). Trong tài liệu này gọi tắt là **plan.md**; "dòng N" là số dòng của bản này.
> - `docs/modules/05_signing_workflow/spec.md` cùng commit (144 dòng), gọi tắt **spec.md**.
> - Đề gốc: `docs/common/ITC - Django - QLVB&TL.xlsx`, sheet `Tổng quan`, ô E14 (yêu cầu Nhóm 5) và F14 (yêu cầu duyệt trường); bản `.md` cùng tên, gọi tắt **đề md**.
> - `docs/common/architecture/structure.md` và `docs/common/QUALITY_GATE_STAGING.md` trên `staging`.
>
> **Các nhánh đã đối chiếu:** `staging` 37a2729 · `2_documents` 18cff9e · `3_dossiers_documents` 828c653 · `4_documents_templates` 3c231f6 · `6_tasks` 9f2e189 · `7_meeting_rooms_birthdays_system` dc7b41f · `feat/issue-19-organizations` a2a3458 · `8_ai_chatbox` 9ca413c · `feat/5-signing-workflow` 5c8f998 · `feat/signing-models` 1a6fcc9.
>
> **Ngày đối chiếu:** 2026-10-04. **Trạng thái:** Đề xuất – chờ Trưởng nhóm 5 chốt.

Ký hiệu dùng trong bằng chứng:
- `file:dòng@nhánh` là vị trí trong mã nguồn của nhánh tương ứng; `models.py@1a6fcc9` là `backend/apps/signing/models.py` trên `feat/signing-models`.
- **KT** là kết quả kiểm thử bổ sung chạy trên bản export tạm ngoài repo (xem mục 2).
- Mọi thay đổi đề xuất trong tài liệu được ghi "Đề xuất (chờ Trưởng nhóm 5 chốt)". Tài liệu không viết lại plan.

## 1. Tóm tắt

- Plan c1b9704 đã xác định rõ lõi dữ liệu và máy trạng thái: yêu cầu tách khỏi lượt trình (`luot_truoc`), snapshot người ký, chữ ký bất biến có con trỏ `chu_ky_hien_hanh`, quá hạn không đổi trạng thái. Nhánh `feat/signing-models` đã hiện thực 14 bảng theo mục 5.2; KT: ghép lên staging@37a2729 và đăng ký app thì `check` sạch, `makemigrations --check` không có thay đổi, 19 test pass.
- Có hai điểm chặn mức nghiêm trọng. (1) Chưa chọn nền triển khai: nhánh `5_signing_workflow` chỉ có tài liệu, merge-base với staging là Initial commit, trong khi hai dòng code (app `approvals` và app `signing`) nằm trên hai gốc khác nhau (HT-01). (2) Lịch pha ở mục 10 chỉ xếp backend lõi: API danh sách và chi tiết, toàn bộ giao diện, seed và PR lên staging không thuộc pha nào, nên 6 gạch E14 không có mốc demo (PHA-01).
- Plan giả định PostgreSQL, Redis, Celery (dòng 58, 141, 196-198) nhưng mục 1.3 loại cấu hình hạ tầng; staging chạy SQLite, không nhánh nào có celery hay redis (HT-02). Quality Gate hiện có thể báo xanh khi không chạy test nào (HT-03).
- Đối chiếu E14: gạch "Chi tiết, sơ đồ ký" đủ ở mức tài liệu; bốn gạch thiếu một phần (tạo văn bản, danh sách lọc chờ ký, thông báo kèm mail, chữ ký số); gạch "Tìm kiếm, lọc phòng/ban" thiếu chỗ lưu dữ liệu (mục 3). Lịch pha cũng chưa có bước trình Giảng viên duyệt danh sách trường theo F14 (PHA-03).
- Cần chốt trước khi code Pha 2: luồng tệp và mã băm (LUONG-01), nơi lưu dự thảo và quan hệ với văn bản Nhóm 2 (TH2-01), dữ liệu nháp (LUONG-02), điều kiện hành động và sơ đồ trạng thái cho cấp và người ký (LUONG-03, LUONG-04), contract API theo dòng người ký và mô hình ủy quyền (LUONG-05, LUONG-06, DL-08).
- Mọi điểm nối với nhóm khác trong plan đều ở dạng chờ nhóm khác cung cấp hoặc thống nhất (dòng 60-61, 134, 504-509, 652, 754-756), không có hạn hay phương án tạm. Dữ kiện trên các nhánh khác với giả định của plan: văn bản Nhóm 2 không có mã băm hay phiên bản (TH2-01); Nhóm 7 chưa có ChucVu và CBNV, không có ảnh chữ ký, và dự định đổi `AUTH_USER_MODEL` (TH7-01, TH7-02, TH7-03).
- Phần lớn vấn đề về máy trạng thái và dữ liệu (LUONG-03 đến LUONG-14, DL-01 đến DL-08) sửa được với chi phí thấp, miễn là làm trước khi migration `0001` của app signing lên staging.
- Lộ trình đề xuất (mục 6): bước 0a và 0b, sau đó M1 đủ 6 gạch E14 chia thành hai kỳ báo cáo 2 tuần, rồi M2 và M3 cho phần mở rộng. Mọi điểm đều chờ Trưởng nhóm 5 chốt.

**Bảng 1. Số vấn đề theo mức độ và theo nhóm** (tổng 70; chi tiết ở mục 8)

| Nhóm vấn đề | Nghiêm trọng | Cao | Trung bình | Thấp | Tổng |
|---|---:|---:|---:|---:|---:|
| LUONG – Luồng nghiệp vụ, máy trạng thái | 0 | 1 | 5 | 8 | 14 |
| DL – Dữ liệu, model | 0 | 0 | 1 | 7 | 8 |
| PHA – Phân pha, nghiệm thu | 1 | 2 | 2 | 1 | 6 |
| TH2 – Tích hợp Nhóm 2 | 0 | 1 | 0 | 4 | 5 |
| TH7 – Tích hợp Nhóm 7 | 0 | 0 | 4 | 2 | 6 |
| TH1 – Tích hợp Nhóm 1 | 0 | 0 | 1 | 4 | 5 |
| HT – Hạ tầng, quy trình | 1 | 2 | 8 | 2 | 13 |
| BM – Bảo mật, đáp ứng đề bài | 0 | 3 | 8 | 2 | 13 |
| **Tổng** | **2** | **9** | **29** | **30** | **70** |

Quy ước mức độ:
- **Nghiêm trọng:** chặn mọi pha hoặc chặn demo đủ đề.
- **Cao:** chặn một gạch E14 hoặc một pha trên đường găng.
- **Trung bình:** gây lỗi nghiệp vụ hoặc tích hợp nhưng có phương án tạm.
- **Thấp:** chi tiết đặc tả, phần ngoài E14 hoặc rủi ro có điều kiện.

## 2. Phạm vi và phương pháp đánh giá

Phạm vi:
- Toàn bộ plan.md (mục 1–13) và spec.md, đối chiếu với đề gốc (E14, F14, đề md).
- Mã nguồn các nhánh nêu ở phần metadata, gồm hai dòng code của Nhóm 5: `feat/signing-models` (app `signing`) và `feat/5-signing-workflow` (app `approvals`).

Phương pháp:
- Đọc từng dòng plan và spec, đối chiếu với model, view, settings và tài liệu của từng nhánh bằng `git show`, `git grep`, `git diff`.
- Kiểm thử bổ sung (KT) trên bản export tạm ngoài repo, không commit. Môi trường: Python 3.11 với Django 5.2.17; Python 3.12 với Django 6.1.1 cho các ca phụ thuộc phiên bản; Node 22.22.0 và Node 20.20.0; pnpm 10.28.0.
  - Bản ghép staging@37a2729 với `backend/apps/signing`@1a6fcc9, có thêm `signing` vào `INSTALLED_APPS`.
  - Một service tối giản cài đúng chữ plan, dùng để mô phỏng máy trạng thái (`feat/signing-models` chưa có service). Kết quả mô phỏng cho biết hành vi nếu cài theo chữ plan, không phải lỗi của code hiện có.
  - Merge thử từng cặp nhánh trong bản clone tạm.
  - Kiểm thử trình duyệt Chromium 141 cho vòng đời khóa WebCrypto, chặn request bằng route interception, không mở cổng mạng.
- Mỗi nhận định được kiểm lại độc lập. Nhận định không đứng vững được liệt kê ở Phụ lục A.

Giới hạn chính (chi tiết ở mục 10):
- Chỉ đọc được bản fork dạng shallow clone; repo gốc có thể đã có thay đổi mới hơn.
- Chưa chạy trên Windows và chưa chạy trên PostgreSQL.
- Chưa có bằng chứng Giảng viên đã duyệt danh sách trường theo F14.

## 3. Đối chiếu đề gốc E14

Ô E14 gồm một dòng mở đầu và 6 gạch; ô F14 yêu cầu nhóm chọn các trường rồi báo Giảng viên duyệt (đọc bằng openpyxl). Đề md dòng 299-307 diễn giải chi tiết hơn: dòng 301 mở rộng gạch 2 thành bộ trạng thái Chờ ký, Đã ký, Từ chối ký, Đang xử lý.

| Gạch E14 | Plan/spec hiện có | Còn thiếu | Kết luận | Mã vấn đề |
|---|---|---|---|---|
| Dòng mở đầu: nhóm gặp Giảng viên để trao đổi; F14: chọn trường rồi báo duyệt | Pha 0 (dòng 649-654) chỉ chốt contract với Nhóm 2 và Nhóm 7 | Không có bước trình Giảng viên. Tìm từ khóa chỉ Giảng viên trên plan.md và spec.md không có kết quả; repo không có ghi nhận phê duyệt | Thiếu | PHA-03 |
| G1. Tạo văn bản trình ký: chọn quy trình, hiển thị thông tin người tạo, mức độ | Chọn quy trình `HOAT_DONG` (dòng 68, 580); cột `muc_do` (dòng 286) | Không có danh mục mức độ. Trang tạo (spec dòng 122-125) không có ô mức độ và khối người tạo. Payload POST (dòng 580) không liệt kê `muc_do`. Nơi lưu dự thảo chưa chốt | Thiếu một phần | BM-11, BM-07, TH2-01 |
| G2. Danh sách, lọc theo trạng thái chờ ký | Spec có tab và bộ lọc trạng thái (dòng 37-38, 120); plan có GET danh sách (dòng 579) | Plan 7.2 không có tham số `trang_thai`. Lọc "Chờ ký" lẫn hồ sơ có lượt đang `YEU_CAU_SUA` (dòng 549). Tab việc cần ký chưa định nghĩa. API danh sách không thuộc pha nào | Thiếu một phần | BM-07, PHA-01 |
| G3. Tìm kiếm và bộ lọc phòng/ban | Spec có ô tìm theo trích yếu hoặc mã hồ sơ, lọc phòng ban (dòng 38, 120-121) | `signing_request` không có `ma_ho_so`, `trich_yeu`, đơn vị trình. Phạm vi `PHONG_BAN` không có đơn vị áp dụng. `van_ban_id` là BigInteger (models.py:211@1a6fcc9) nên không join được trích yếu | Thiếu | BM-03 |
| G4. Chi tiết, sơ đồ ký | Spec dòng 39-40, 126-127; GET chi tiết (dòng 581) | Đủ ở mức tài liệu. Frontend và API chi tiết không thuộc pha nào; màu "đỏ = trả về" chưa ứng với trạng thái cụ thể | Đủ ở mức tài liệu | PHA-01, LUONG-13 |
| G5. Thông báo đến người cần ký, và gửi mail | Bảng `signing_notification` kiêm outbox, Celery, nhắc hạn (dòng 27, 196-198, 486-502, 629-638) | Không có quy tắc "đến lượt thì báo". Không có cột đã đọc, nội dung, API đọc. Nằm ở Pha 5. Email không gửi được trên Django 5.2. Chuông header của Nhóm 1 dùng dữ liệu mẫu | Thiếu một phần | BM-01, HT-04, PHA-01 |
| G6. Chữ ký số | Ed25519, proof-of-possession, chữ ký bất biến (mục 3.4, 5.2, 7.4) | Chưa có vòng đời khóa phía trình duyệt. Chưa ràng buộc khóa với người ký và chưa gắn ngữ cảnh vào thông điệp ký. Không xác thực lại khi ký. Server không băm lại tệp. Nếu demo bằng `approvals` thì chữ ký là HMAC | Thiếu một phần | BM-02, BM-04, BM-10, LUONG-01, BM-09 |

Plan còn có nhiều phần vượt đề: ủy quyền khẩn cấp, thread yêu cầu sửa, manifest, phẳng hóa PDF, khâu phát hành pháp lý (dòng 13-29, 40-52). Các phần này hợp lệ về nghiệp vụ, nhưng đang chiếm chỗ trong lịch pha trước các gạch bắt buộc (mục 5).

## 4. Luồng nghiệp vụ end-to-end và điểm đứt

1. **Cấu hình quy trình** (Pha 1; mục 3.1, 5.2). Người có quyền `quan_ly_quy_trinh_ky` tạo `signing_process`, các cấp `signing_process_step` và người ký cấu hình `signing_process_step_signer` (theo tài khoản hoặc chức vụ; `vai_tro_ky` là `KY_NHAY` hoặc `KY_CHINH`; cờ `chan_ky_chinh`).
   - Module liên quan: Nhóm 7 (DonVi, ChucVu, CBNV); Nhóm 1 và Nhóm 7 (phân quyền).
   - Điểm đứt: ChucVu và CBNV chưa có; quy tắc resolve chức vụ chưa định nghĩa (TH7-03). Phạm vi `PHONG_BAN` không có cột đơn vị (BM-03). Kích hoạt bản mới không ngừng bản cũ (LUONG-09). `dang_ap_dung` không có quy tắc (DL-07).
2. **Đăng ký khóa ký** (Pha 3; mục 3.4, 7.4). Trình duyệt sinh cặp khóa Ed25519, server cấp challenge, client ký challenge, khóa chuyển `CHO_KICH_HOAT` → `HOAT_DONG`.
   - Module liên quan: frontend (WebCrypto, IndexedDB); hạ tầng (Redis theo dòng 141).
   - Điểm đứt: staging không có Redis (HT-02). Chưa có endpoint tạo bản ghi khóa, endpoint đọc khóa của người dùng, trang quản lý khóa; plan không nói khóa riêng lưu ở đâu (BM-02). Đăng ký khóa chỉ cần phiên đăng nhập, trong khi JWT giả được bằng `SECRET_KEY` có trong repo (BM-08). Bản ghi khóa sửa được sau khi tạo (BM-13).
3. **Tạo yêu cầu nháp** (Pha 2; dòng 580). Người tạo chọn văn bản, quy trình, kiểu ký, mức độ, hạn chót, vị trí ký cho từng người ký.
   - Module liên quan: Nhóm 2 (văn bản); Nhóm 1 hoặc Nhóm 7 (thông tin người tạo).
   - Điểm đứt: `van_ban` là FK bắt buộc nhưng chưa chốt dự thảo lưu ở đâu, và loại văn bản nào của Nhóm 2 cũng có nhược điểm (TH2-01). Vị trí ký chưa có chỗ lưu trước khi gửi; chưa có API sửa hay xóa nháp (LUONG-02). Trang tạo thiếu mức độ và thông tin người tạo (BM-11). Không chặn nhiều yêu cầu trên cùng văn bản (LUONG-14).
4. **Gửi** (Pha 2; mục 3.3, 6.1). Tạo `signing_attempt` với `so_luot=1`, khóa `vi_tri_luu_tep` và `ma_bam_tai_lieu`; snapshot cấp và người ký; tính `han_xu_ly`; mở cấp (`TUAN_TU` mở cấp 1, `SONG_SONG` mở tất cả); tạo bản ghi `signing_notification`.
   - Module liên quan: Nhóm 7 (resolve người ký); hạ tầng (mail, Celery); Nhóm 1 (chuông header).
   - Điểm đứt: chưa quy định ai tính mã băm (LUONG-01). Chưa có quy tắc tạo thông báo khi đến lượt (BM-01). Email không gửi được trên Django 5.2 (HT-04). Outbox nằm ở Pha 5 (PHA-01). Trùng người trong một cấp gây IntegrityError (LUONG-05). Quy tắc hạn còn mơ hồ (LUONG-07).
5. **Ký** (Pha 3; mục 5.3, 6.2). Người ký mở trang chi tiết (stepper, PDF viewer, lớp phủ ảnh chữ ký), ký digest bằng khóa riêng; server kiểm hash, khóa và chữ ký rồi lưu `signing_signature`; mở `KY_CHINH`, mở cấp kế tiếp, hoàn thành lượt.
   - Module liên quan: frontend; Nhóm 7 (ảnh chữ ký theo plan dòng 133-134).
   - Điểm đứt: thông điệp ký chỉ là digest, không kiểm chủ khóa (BM-04). Không xác thực lại khi ký (BM-10). Server không băm lại tệp và không có API phục vụ tệp (LUONG-01). Ảnh chữ ký chưa có nguồn (TH7-02). API định danh theo lượt, không theo dòng người ký (LUONG-05). Test đồng thời trên SQLite in-memory không kiểm được cơ chế khóa (HT-08).
6. **Ngoại lệ** (Pha 4; mục 3.3, 3.5): `ghi_chu_ky`, `yeu_cau_sua` kèm thread và `giai_quyet`, `tu_choi` và `xem_xet_lai`, `huy`, `uy_quyen`, `thu_hoi`.
   - Module liên quan: Nhóm 7 (ủy quyền cho người "thẩm quyền tương đương").
   - Điểm đứt: điều kiện cho các hành động ngoài `ky` còn thiếu (LUONG-03). Lượt dừng không dọn trạng thái cấp và người ký (LUONG-04). Ủy quyền ghi đè dòng cũ (LUONG-06). Thu hồi phá quy tắc chặn ký nháy (LUONG-08). Thread chưa có ràng buộc (LUONG-10). Thiếu chuyển `TU_CHOI` → `HUY` (LUONG-11).
7. **Hoàn thành và phát hành** (Pha 3, Pha 5; mục 1.4). Chốt manifest, `PdfStampingService` sinh tệp hoàn tất, endpoint `phat-hanh` đi qua `LegalSignerAdapter`.
   - Module liên quan: Nhóm 2 (văn bản đi); Nhóm 3 (Hồ sơ, Loại văn bản mà văn bản đi bắt buộc có); Nhóm 8 (chatbot mô tả bước này).
   - Điểm đứt: vòng đời manifest chưa định nghĩa (DL-04). Không pha nào tạo văn bản đi. Chatbot mô tả ký bằng Token PKI/Cloud HSM và tự sinh số văn bản đi (TH2-02).
8. **Danh sách, tìm kiếm, nhật ký** (spec mục 4; plan 7.2, 7.4).
   - Module liên quan: Nhóm 7 (đơn vị); Nhóm 2 (ACL văn bản mật).
   - Điểm đứt: không pha nào nhận (PHA-01). Thiếu mã, trích yếu, đơn vị (BM-03). Thiếu trạng thái hiển thị (BM-07). Endpoint đọc theo id chỉ kiểm permission cấp model (BM-12). Chưa có quy tắc cho hồ sơ gắn văn bản MẬT (BM-05).
9. **Tích hợp kỹ thuật và nộp bài.** Phải sửa file chung (settings, urls, requirements, router, i18n), qua Quality Gate, theo đường PR `feat/*` → `5_signing_workflow` → `staging`.
   - Module liên quan: Nhóm 1 (file chung), Trưởng nhóm 5 (vai DevOps).
   - Điểm đứt: nhánh 5 không dựng trên staging (HT-01). Quality Gate cho kết quả xanh giả (HT-03). File chung conflict (HT-06). Plan không có điểm tích hợp theo pha (HT-10).

## 5. Đánh giá phân pha

### 5.1. Vấn đề chung của mục 10

- **Phần việc không thuộc pha nào** (PHA-01, PHA-04, HT-10):
  - API đã có ở mục 7: GET danh sách (dòng 579), GET chi tiết (dòng 581), nhật ký (dòng 603).
  - Toàn bộ giao diện ở spec mục 4, và trang khóa ký (spec mục 4 không có trang này).
  - Seed demo và trang admin.
  - Dựng hạ tầng (Redis, Celery) mà Pha 3–5 cần.
  - PR lên staging: `grep -niE 'staging|\bPR\b|merge'` trên plan.md không có kết quả.
- **Phụ thuộc cứng ngược chiều**, tức là một pha không nghiệm thu được nếu chưa có pha sau:
  - Pha 2 cần hành động `ky` của Pha 3 để nghiệm thu "hoàn thành" và "ký lặp" (dòng 666, 668 so với 673-674).
  - Pha 2–4 phải tạo outbox trong transaction (dòng 198, 207), nhưng outbox nằm ở Pha 5 (dòng 687).
  - Pha 3–4 cần Redis và Celery (dòng 672, 197, 638, 682), trong khi mục 1.3 (dòng 33) loại cấu hình hạ tầng.
  - Pha 4 cần API tải tệp mới cho `giai_quyet` (dòng 679), mà plan chưa có API này.
- **Phụ thuộc mềm**, xử lý tạm được: adapter đọc tệp (dòng 688), "Hạn UTC" (dòng 682), `ky_tre_han` ghi ở cả Pha 3 và Pha 4 (dòng 674, 682).
- **Phụ thuộc ra ngoài nhóm:**
  - Pha 0 (dòng 652), test của Pha 1 (dòng 661) và tiêu chí dòng 710 cần ChucVu của Nhóm 7, mà nhánh Nhóm 7 mới có KhoiKhuVuc và DonVi.
  - `2_documents` đi trước staging 70 commit và chưa merge.
- **Thiếu mốc thời gian:** plan không có ngày, người phụ trách hay mốc tích hợp, trong khi đề quy định báo cáo tiến độ 2 tuần một lần (xlsx ô A1).
- **Nghiệm thu không bám đề:** tiêu chí ở mục 11 và DoD ở mục 13 không có tiêu chí cho G1–G4 và không chia theo mốc (PHA-05). Các điểm mở ở mục 12 không có người chốt (PHA-06). Pha 0 không có bước trình Giảng viên (PHA-03).

### 5.2. Bảng đánh giá từng pha

| Pha | Kết luận | Vấn đề chính | Phụ thuộc | Đề xuất (chờ Trưởng nhóm 5 chốt) |
|---|---|---|---|---|
| Pha 0 – Chốt contract, khung app | Bị chặn | Dòng 651 không làm được: nhánh 5 không có backend. Dòng 652 đặt contract Nhóm 2/7 làm cửa vào Pha 1. Thiếu các việc DevOps: đồng bộ staging, email, cryptography, MEDIA, prefix API, tên app, trình Giảng viên | Nhóm 2, Nhóm 7, Nhóm 1, Giảng viên | Tách 0a (không chờ nhóm khác) và 0b (chạy nền, có hạn). Xem mục 6 |
| Pha 1 – Schema, quản lý quy trình | Cần sửa | Schema 14 bảng đã xong ở `feat/signing-models`. Còn thiếu: Meta.permissions; partial unique; đơn vị áp dụng cho `PHONG_BAN`; kích hoạt bản mới không ngừng bản cũ. Test "chức vụ trống" (dòng 661) viết được bằng resolver giả | Nhóm 7 (ChucVu); định nghĩa admin chung | Chỉ GET quy trình `HOAT_DONG` nằm trên đường găng; quy trình demo tạo bằng seed. Gộp permissions và partial unique vào `0001` khi chưa lên staging. MVP chỉ hỗ trợ người ký theo tài khoản (TH7-03) |
| Pha 2 – Yêu cầu, lượt trình, snapshot | Cần sửa | Pha có nhiều hạng mục nhất, không nghiệm thu riêng được (phụ thuộc Pha 3, 5). Chưa có luồng tệp (LUONG-01), chỗ lưu nháp (LUONG-02), mã/trích yếu/đơn vị (BM-03), danh sách và chi tiết. Test đồng thời trên SQLite in-memory không kiểm được cơ chế khóa (HT-08) | Pha 3, Pha 5, Nhóm 2, hạ tầng | Tách lõi `ghi_nhan_da_ky`, test bằng chữ ký tạo trực tiếp. Upload PDF, server tự băm. Tính `han_xu_ly` khi mở cấp. Viết helper tạo thông báo ngay ở pha này. Thêm danh sách, chi tiết, partial unique |
| Pha 3 – Khóa, chữ ký, manifest | Cần sửa | Gộp ba khối: 3a quản lý khóa (độc lập luồng), 3b ký và verify (đường găng), 3c manifest, thu hồi, `HET_HAN` (ngoài đề). Challenge cần Redis. Phía trình duyệt không thuộc pha nào. Thông điệp ký chưa có ngữ cảnh (BM-04) | Hạ tầng, Nhóm 7 (ảnh), frontend, Pha 2 | 3a làm song song Pha 2, challenge dùng `TimestampSigner`. 3b ngay sau lõi Pha 2. 3c dời sang M2. Cột ảnh chữ ký cho phép rỗng nên không chặn MVP |
| Pha 4 – Sửa, ủy quyền, từ chối, hủy, hạn | Cần sửa | Năm tính năng gộp một pha. `tu_choi`, `huy` cần cho bộ trạng thái của đề md dòng 301 nhưng xếp muộn. Điều kiện hành động thiếu (LUONG-03); ủy quyền ghi đè (LUONG-06); quy tắc hạn mơ hồ (LUONG-07) | Pha 5, API tải tệp, Nhóm 7 | 4a (`tu_choi`, `huy`, quản trị hủy thay, hàm dừng lượt) đưa vào M1. 4b (yêu cầu sửa, `giai_quyet`, ủy quyền, `xem_xet_lai`) dời sang M2 |
| Pha 5 – Thông báo, lưu trữ, phẳng hóa, adapter | Cần sửa | Gạch G5 bắt buộc nhưng nằm ở pha áp chót. Email không gửi được trên Django 5.2 (HT-04). Phẳng hóa bị chặn bởi hệ tọa độ, nguồn ảnh, thư viện PDF. Adapter lưu "mount" trái structure.md mục 7.1 (BM-06) | Hạ tầng, Nhóm 7, Nhóm 2, Nhóm 1 | 5a (thông báo in-app, email đồng bộ sau `on_commit`, 2 API) đưa vào M1. 5b (Celery, phẳng hóa, `LegalSignerAdapter`) dời sang M3; ẩn nút Phát hành |
| Pha 6 – Hoàn thiện, bàn giao | Cần sửa | DoD dòng 770 mơ hồ về file chung (HT-06). `pytest` không có trong repo (HT-03). Check/test chỉ ở cuối. OpenAPI cần thư viện chưa có | Trưởng nhóm 5, Nhóm 1 | Mỗi mốc chạy đủ 5 lệnh Quality Gate. Bỏ OpenAPI khỏi DoD MVP. PR lên staging theo từng mốc (HT-10) |
| Frontend (không có pha) | Thiếu | 3 trang spec mục 4, trang khóa ký, quản lý quy trình, kéo-thả khung ký, hộp thông báo đều không thuộc pha nào. Route `/approvals` đang trỏ tới `SyllabusPreview` (router.tsx:84@staging). Trong `approvals`, phần frontend chiếm khoảng 56% số dòng thêm của hai thư mục `frontend/` và `backend/` (+4691 so với +3649 theo `git diff --numstat`; khoảng 51% nếu tính mọi tệp), chỉ số gần đúng | API backend, Nhóm 1, Node ≥22 | F1 đi cùng Pha 2 (danh sách, tạo, chi tiết, stepper); F2 đi cùng 3a/3b (trang khóa, nút Ký); F3 đi cùng 5a (thông báo); F4 ở M2 (pdf.js, kéo-thả). i18n dùng `vi.json`/`en.json` |
| Demo và nộp bài (không có pha) | Thiếu | Không có seed, gán quyền, admin chỉ đọc, mẫu email, kịch bản và checklist trình duyệt, bảng "gạch E14 → tính năng", mốc PR staging (PHA-04) | Trưởng nhóm 5, Giảng viên | Lệnh `seed_signing_demo` đặt trong `management/commands`; checklist một origin `http://localhost:5173`; video dự phòng; mỗi mốc có bảng "đã đáp ứng gạch nào" |

## 6. Đề xuất lộ trình

Toàn bộ mục này là Đề xuất (chờ Trưởng nhóm 5 chốt). Nghiệp vụ của plan giữ nguyên; lộ trình chỉ sắp lại công việc thành các lát dọc theo 6 gạch E14.

### 6.1. Nguyên tắc

- Mỗi mốc kết thúc bằng một PR qua đủ 5 lệnh Quality Gate, chạy từ `backend/` và `frontend/` (HT-03).
- Cấu hình MVP chạy trên Windows, không cài thêm dịch vụ: SQLite chế độ `IMMEDIATE`, email đồng bộ sau `on_commit`, challenge không dùng Redis, nhắc hạn bằng management command (HT-02).
- Các thay đổi model gộp vào `0001_initial` khi migration này chưa lên staging (DL-03, PHA-03).
- Gắn ngày cụ thể cho từng mốc theo chu kỳ báo cáo 2 tuần khi biết hạn nộp.

### 6.2. Bước 0a – Trưởng nhóm 5, 1–3 ngày, không chờ nhóm khác

1. Chốt nền triển khai: app `signing` là đích; `approvals` giữ ở nhánh riêng làm bản demo dự phòng và nguồn tái dùng, không merge cả hai app lên staging (HT-01).
2. Đồng bộ staging vào `5_signing_workflow`: 5 file conflict lấy bản staging, chạy `git rm -r --cached AGENTS.md .agents`, giữ `docs/modules/05_signing_workflow`.
3. Đăng ký app `signing`; thêm `cryptography` vào requirements; thêm `MEDIA_ROOT` và `MEDIA_URL`.
4. Settings chung:
   - Email chạy được trên cả Django 5.2 và 6.1, hoặc ghim Django 5.2 LTS (HT-04).
   - `SECRET_KEY` và `SIMPLE_JWT['SIGNING_KEY']` đọc từ `.env` (BM-08).
   - SQLite `transaction_mode: IMMEDIATE`, `timeout: 20` (HT-02, HT-08).
5. Chuẩn hóa lệnh Quality Gate, thêm workflow CI tối thiểu, sửa PR template (HT-03).
6. Trình Giảng viên bảng "gạch E14 → tính năng → bảng/trường chính → mốc", danh sách trường rút gọn và danh sách phần mở rộng đề xuất dời sang M2/M3 (PHA-03).
7. Chốt các quyết định đặc tả trước Pha 2:
   - Luồng tệp và mã băm (LUONG-01); dữ liệu nháp (LUONG-02).
   - Điều kiện hành động và sơ đồ trạng thái (LUONG-03, LUONG-04).
   - Contract API theo dòng người ký, mô hình ủy quyền, liên kết dòng cấu hình (LUONG-05, LUONG-06, DL-08).
   - Chặn sửa mã băm của lượt và các partial unique (DL-01).
   - Tên app và prefix API (TH1-02); định dạng lỗi (TH1-05); hệ tọa độ và ảnh chữ ký (PHA-06).

### 6.3. Bước 0b – chạy nền, hạn khoảng 1 tuần, không chặn M1

- Nhóm 2: phương án A, tức là Nhóm 5 tự giữ PDF dự thảo, `van_ban` cho phép rỗng (TH2-01).
- Nhóm 7 và PM:
  - Không đổi `AUTH_USER_MODEL` (TH7-01).
  - Lịch cho ChucVu và CBNV (TH7-03).
  - "Xóa" tài khoản và đơn vị nghĩa là vô hiệu hóa (TH7-04).
  - Một hàm `is_admin` dùng chung (TH1-01).
- Lập danh mục contract với các cột: nhóm, thứ cần, trạng thái, hạn, phương án tạm (TH7-06).
- Gom truy cập dữ liệu tổ chức vào một module tích hợp; giữ các cột BigInteger tạm cho tới khi nhóm nguồn lên staging (DL-03).

### 6.4. M1 – MVP đủ 6 gạch E14, chia hai kỳ báo cáo

Quy ước tên: Pha 1-min là phần tối thiểu của Pha 1, Pha 2-core là phần lõi của Pha 2; 3a/3b/3c, 4a/4b, 5a/5b, F1–F4 theo bảng ở mục 5.2.

Lý do chia: ước lượng cho M1 nguyên khối là khoảng 10–14 ngày công của thành viên Nhóm 5, vượt 10 ngày làm việc của một kỳ (PHA-02). Đây là suy luận theo khối lượng code `approvals`, chưa được kiểm chứng.

**M1a (kỳ 1):**
- Pha 1-min: GET quy trình `HOAT_DONG`; seed quy trình với người ký theo tài khoản; permissions và partial unique.
- Pha 2-core:
  - Tạo nháp có upload PDF; server tự tính SHA-256.
  - Thêm `ma_ho_so`, `trich_yeu`, `muc_do` (4 mức), `ten_don_vi`.
  - Gửi, snapshot, mở cấp `TUAN_TU`/`SONG_SONG`, chặn ký chính theo ký nháy, hoàn thành.
  - Lõi `ghi_nhan_da_ky` và helper tạo thông báo.
- Danh sách 3 tab có trạng thái hiển thị, bộ lọc trạng thái/phòng ban/mức độ/ngày, tìm theo mã và trích yếu. Trang chi tiết có sơ đồ ký. API phục vụ tệp có kiểm quyền.
- 4a: `tu_choi`, `huy`, quản trị hủy thay, hàm dừng lượt dùng chung.
- 5a: thông báo in-app có cột đã đọc, 2 API đọc và đánh dấu, email gửi đồng bộ sau `on_commit`.
- Frontend F1 và F3, chuyển đổi các trang của `approvals` qua lớp ánh xạ trường (contract `approvals` dùng tên trường như `status`, `urgency`, `round`, khác payload của plan).
- PR lên staging.

**M1b (kỳ 2):**
- 3a, là việc bắt buộc có người nhận cụ thể: khóa WebCrypto non-extractable lưu trong IndexedDB; challenge bằng `TimestampSigner`; verify; thu hồi rồi đăng ký lại. Có thể bắt đầu từ M1a vì độc lập với luồng.
- 3b: thông điệp ký chuẩn hóa, kiểm chủ khóa, nhập lại mật khẩu, server băm lại tệp, chữ ký bất biến, `ky_tre_han`.
- F2: trang khóa ký cá nhân (bổ sung vào spec) và nút Ký.
- Lệnh nhắc hạn (management command chạy bằng Task Scheduler).
- Seed demo, admin chỉ đọc, kịch bản và checklist demo, PR lên staging.

**Phương án thay thế (M0):** dành 1–3 ngày sửa nhỏ `approvals` để làm mốc an toàn trên staging, rồi M1 thay phần ký bằng Ed25519. Ba việc sửa là: settings email; ghi rõ "Mã xác thực HMAC"; chặn xóa hồ sơ trong admin (BM-09). Đánh đổi: bảng `approvals` nằm lại trên staging và cần migration dọn khi chuyển sang `signing` (PHA-02).

### 6.5. M2 – sau MVP

- 4b: yêu cầu sửa kèm thread và `giai_quyet` (cho phép giữ nguyên tệp); ủy quyền theo cách tạo dòng mới; `xem_xet_lai` hoặc bỏ hẳn; escalation.
- 3c: thu hồi ở `SONG_SONG`, xoay vòng khóa, manifest đồng bộ, nút "Xác minh lại".
- Tọa độ ký, lớp phủ pdf.js, ảnh chữ ký.
- Người ký theo chức vụ khi Nhóm 7 có ChucVu; chuyển cột tạm sang FK sau khi `2_documents` lên staging.

### 6.6. M3 – nếu còn thời gian

- Celery và tác vụ quét bản ghi sót; `PdfStampingService` chỉ cho PDF.
- `LegalSignerAdapter` dạng interface; phát hành tạo văn bản đi qua hàm do Nhóm 2 cung cấp.
- OpenAPI; job test trên PostgreSQL.

### 6.7. Đường găng

0a (nền triển khai, đồng bộ staging, quyết định luồng tệp và dữ liệu nháp) → service Pha 2-core → danh sách, chi tiết và F1 → 3b → F2 → seed và kịch bản demo → PR lên staging.

- 3a, 4a, 5a chạy song song với Pha 2.
- Trong Pha 1, chỉ GET quy trình nằm trên đường găng.
- Nếu chọn phương án A với Nhóm 2 và MVP chỉ dùng người ký theo tài khoản, thì phụ thuộc vào nhóm khác không nằm trên đường găng.

### 6.8. Phân công theo vai trò

| Vai trò | Phần việc đề xuất |
|---|---|
| Trưởng nhóm 5 (kiêm DevOps) | Bước 0a và 0b; settings chung, CI, Quality Gate; review PR của các nhóm (Nhóm 4 về DB, Nhóm 6 về đồng bộ nhánh). Contract với Nhóm 2 và Nhóm 7; trình Giảng viên. 3a nếu được giao (ghi rõ người nhận trong lịch). Seed demo, gán quyền, mẫu email; kịch bản và checklist demo; tài liệu nộp; review mọi PR vào `5_signing_workflow` |
| Thành viên Nhóm 5 | Backend Pha 1-min, 2-core, 3b, 4a, 5a; frontend F1–F3. Tái dùng từ `approvals`: các trang danh sách, tạo, chi tiết; sơ đồ ký; gửi thông báo sau `on_commit`; băm tệp phía server; lệnh seed; 38 test làm checklist kịch bản. Mở PR `5_signing_workflow` → `staging` để Trưởng nhóm 5 review (HT-12) |

Ước lượng tham khảo, suy luận theo khối lượng `approvals` và chưa kiểm chứng: M1 cần khoảng 10–14 ngày công của thành viên Nhóm 5 và 4–5 ngày công của Trưởng nhóm 5. Phần DevOps chung của cả lớp chưa được tính (HT-09, HT-11).

### 6.9. Ánh xạ 6 gạch E14 vào M1

| Gạch E14 | Thành phần trong M1 | Mốc |
|---|---|---|
| G1. Tạo (chọn quy trình, người tạo, mức độ) | Pha 1-min + Pha 2-core (`muc_do`, snapshot người tạo) + F1 | M1a |
| G2. Danh sách lọc "chờ ký" | API danh sách + trạng thái hiển thị (BM-07) + 4a (cho "Từ chối ký") | M1a |
| G3. Tìm kiếm, lọc phòng/ban | Snapshot `ma_ho_so`, `trich_yeu`, `ten_don_vi` + bộ lọc (BM-03) | M1a |
| G4. Chi tiết, sơ đồ ký | API chi tiết + trang chi tiết + stepper | M1a |
| G5. Thông báo và mail | 5a + F3 + settings email (HT-04); nhắc hạn ở M1b | M1a, M1b |
| G6. Chữ ký số | 3a + 3b + F2 | M1b |

## 7. Tích hợp với các module

### 7.1. Nhóm 1 – Layout, Auth, Dashboard (app shell)

- **Điểm nối:**
  - Đăng nhập JWT và `StaffProfile` (thông tin người tạo, phòng ban tạm thời).
  - Router `/approvals`; menu `workflow` dùng chung với Nhóm 6; chuông thông báo trên header.
  - i18n `vi.json`/`en.json`; `apiClient`.
  - File chung `settings.py`, `urls.py`; định nghĩa admin.
- **Hiện trạng (staging@37a2729):**
  - `/approvals` trỏ tới `SyllabusPreview` (router.tsx:84).
  - Chuông header đọc mảng tĩnh `SAMPLE_STREAMS` (NotificationStreams.tsx:3, 29-30; constants.ts:333), chỉ có 4 loại thông báo (types/notification.ts:1).
  - `apiClient` chỉ lưu access token mới (apiClient.ts:112-118).
  - `ProtectedRoute` không lưu trang đích (router.tsx:38-40).
  - Settings chỉ khai báo `MAILERS` (dòng 143-147), không có MEDIA, `SECRET_KEY` viết cứng (dòng 28).
- **Vấn đề:** TH1-01 (định nghĩa admin), TH1-02 (prefix API, i18n), TH1-03 (lỗi app shell), TH1-04 (`apiClient.blob`), TH1-05 (định dạng lỗi), HT-04 (email), BM-01 (chuông), BM-08 (`SECRET_KEY`).
- **Contract cần chốt:**
  - (a) Thêm loại `signing` vào chuông header, gọi API thông báo của Nhóm 5.
  - (b) Một hàm `is_admin` dùng chung.
  - (c) `ProtectedRoute` truyền `state.from` để quay lại đúng trang.
  - (d) `apiClient` lưu refresh token mới; thêm `apiClient.getBlob()` trả `Blob` qua luồng refresh 401.
  - (e) Settings email theo phiên bản Django, MEDIA, `SECRET_KEY` đọc từ `.env` (Trưởng nhóm 5 làm với vai DevOps).
  - (f) Sửa nội dung chatbot trên staging (TH2-02).
- **Phương án tạm:** hiển thị thông báo ngay trong trang Trình ký; API chi tiết trả `quyen_xu_ly` để UI dựa vào; tải blob kèm Bearer bằng hàm riêng (kiểu `fetchProtectedBlob` của `approvals`); snapshot phòng ban từ `StaffProfile.department`.

### 7.2. Nhóm 2 – Văn bản đến, đi, mật

- **Điểm nối:** đầu vào `van_ban` và tệp gốc; ACL văn bản mật; trích yếu cho tìm kiếm; đầu ra là văn bản đi khi phát hành; `/media/`; settings DRF toàn cục.
- **Hiện trạng (2_documents@18cff9e, đi trước staging 70 commit, chưa merge):**
  - `Document` có `loai` DEN/DI/MAT.
  - Văn bản đi bắt buộc `so_hieu` và `ngay_ban_hanh`; số thứ tự cấp ngay lúc tạo.
  - Một văn bản có nhiều tệp đính kèm; không kiểm định dạng, không có mã băm hay phiên bản (models.py:208-221).
  - PUT/PATCH/DELETE chỉ chặn với MAT (views.py:138-165).
  - `static(MEDIA_URL)` bật khi DEBUG (urls.py:24-26).
  - Phân trang 10 và `SessionAuthentication` bật toàn cục (settings.py:169-185).
  - Chưa có frontend (`git diff --stat staging..2_documents` không có tệp frontend).
- **Vấn đề:** TH2-01 (nơi lưu dự thảo), TH2-02 (phát hành, chatbot), TH2-03 (cấp số, năm mặc định, settings DRF), TH2-04 (`loai` sửa được), TH2-05 (README lệch code), BM-05 (văn bản MẬT), BM-06 (`/media/`), TH7-04 (ProtectedError).
- **Contract cần chốt:**
  - (0) Phương án A: Nhóm 5 tự giữ PDF dự thảo; văn bản đi chỉ tạo khi phát hành.
  - (1) Bắt `ProtectedError`, trả 409.
  - (2) Kiểm quyền PUT/PATCH/DELETE cho mọi loại như README; khóa trường `loai` khi cập nhật.
  - (3) Làm endpoint tải tệp có kiểm quyền, rồi mới bỏ `static()`; đổi tên tệp sang uuid.
  - (4) Tách hàm `can_view_document` để dùng lại.
  - (5) Hàm tạo văn bản đi có cấp số và `UniqueConstraint(loai, nam, so_thu_tu)`.
  - (6) Không sửa `0001`; default năm dùng callable.
  - (7) Hẹn ngày merge `2_documents` lên staging.
- **Phương án tạm:** Nhóm 5 tự lưu tệp tại `MEDIA_ROOT/05_signing/documents/`, `van_ban` để rỗng; snapshot `trich_yeu`, `ma_ho_so` phía Nhóm 5; chỉ khai báo FK sau khi `2_documents` lên staging (DL-03); ẩn nút phát hành.

### 7.3. Nhóm 3 – Hồ sơ, Loại văn bản

- **Điểm nối:** gián tiếp qua Nhóm 2. Văn bản đi sinh ra lúc phát hành bắt buộc có Hồ sơ và Loại văn bản (xlsx ô F7). `records.HoSo.nguoi_lap` là FK PROTECT tới `AUTH_USER_MODEL`, nên cùng chịu rủi ro TH7-01.
- **Hiện trạng (3_dossiers_documents@828c653):** app `records` có `HoSo` (records/models.py:8) và `LoaiVanBan` (dòng 69); lệnh `ensure_common_hoso` tạo hồ sơ chung của hệ thống. Merge với `feat/5-signing-workflow` conflict ở `settings.py` (HT-06).
- **Vấn đề:** không ảnh hưởng M1. Chữ ký hàm tạo văn bản đi của Nhóm 2 sẽ đổi khi Nhóm 2 thêm `ho_so` (models.py:137-143@2_documents còn TODO).
- **Contract cần chốt:** văn bản đi sinh từ trình ký mặc định gắn vào Hồ sơ nào và Loại văn bản nào. Gợi ý: hồ sơ chung của hệ thống, loại "Tờ trình".
- **Phương án tạm:** phần phát hành để ở M3.

### 7.4. Nhóm 4 – Biểu mẫu, Tài liệu chung

- **Điểm nối:** biểu mẫu Tờ trình người dùng tải về để trình ký; DB mặc định; `requirements.txt`.
- **Hiện trạng (4_documents_templates@3c231f6):** `settings.py:103` đặt ENGINE mặc định là PostgreSQL qua `DB_ENGINE`, thêm `psycopg[binary]>=3.2.0`; `.env.example` không có biến DB; `backend/README.md:11` của chính nhánh ghi SQLite cho môi trường phát triển.
- **Vấn đề:** HT-05 (DB mặc định, driver, `DB_ENGINE`). Nếu biểu mẫu ở dạng DOCX/XLSX thì không đi được luồng chỉ nhận PDF; định dạng thực tế của biểu mẫu chưa được kiểm.
- **Contract cần chốt (Trưởng nhóm 5 chốt khi review PR):** SQLite là mặc định; PostgreSQL bật qua một biến với một driver duy nhất; biểu mẫu kèm hướng dẫn xuất PDF trước khi trình ký.
- **Phương án tạm:** đặt `DB_ENGINE=django.db.backends.sqlite3` trong `.env` (KT: `test accounts` 9 OK); validator Nhóm 5 chỉ nhận PDF và báo rõ lý do.

### 7.5. Nhóm 6 – Công việc

- **Điểm nối:** dùng chung menu `workflow` (teamTag "Nhóm 5 & 6", `defaultPage` là `tasks`, constants.ts:248-268@staging); route `/tasks` nằm sát `/approvals`; cùng cần mail và nhắc hạn; `CORS_ALLOW_HEADERS`; `requirements.txt`.
- **Hiện trạng (6_tasks@9f2e189):**
  - Merge-base 345122c, thiếu 75 commit staging.
  - Ghim `Django==5.2.4` nhưng settings chỉ khai báo `MAILERS` (settings.py:149).
  - `requirements.txt` mã hóa UTF-16LE nên git coi là tệp nhị phân.
  - Xác thực tạm qua header `X-Mock-User-Id` (work/views.py:60, 95; settings.py:143).
  - Frontend nằm trong `frontend/src/modules`, trái FRONTEND_BASELINE_GUIDE.md:21.
- **Vấn đề:** HT-07 (cơ chế mail và lịch chung), HT-06 (requirements nhị phân), HT-09 (nhánh chưa dựng trên staging), TH1-03 (CORS header).
- **Contract cần chốt:**
  - Dùng chung cấu hình email và cơ chế nhắc hạn (management command chạy bằng Task Scheduler).
  - `requirements.txt` dùng UTF-8, không dán nguyên `pip freeze`.
  - Một dòng `CORS_ALLOW_HEADERS` chung (thêm `idempotency-key`; bỏ header giả trước khi lên staging).
  - Trình ký không tạo Task.
- **Phương án tạm:** Nhóm 5 giữ route `/approvals` và điều hướng nội bộ bằng tab trong trang.

### 7.6. Nhóm 7 – Hệ thống (Đơn vị, Chức vụ, CBNV, phân quyền), Phòng họp, Sinh nhật

- **Điểm nối:** DonVi (lọc phòng ban, phạm vi `PHONG_BAN`, `step.don_vi`); ChucVu (resolve người ký); CBNV (họ tên, đơn vị, chức vụ, trạng thái, email); ảnh chữ ký theo plan; phân quyền; xóa tài khoản và đơn vị; `AUTH_USER_MODEL`.
- **Hiện trạng (7_meeting_rooms_birthdays_system@dc7b41f, feat/issue-19-organizations@a2a3458):**
  - Mới có KhoiKhuVuc và DonVi (organizations/models.py:45-106), đã merge vào nhánh nhóm ngày 2026-09-26, chưa lên staging.
  - ChucVu và CBNV chưa có code.
  - Kế hoạch đổi `AUTH_USER_MODEL` sang `accounts.Employee` (phan-cong-nhom7.md:62, 64, 71).
  - Endpoint ghi chỉ kiểm `IsAuthenticated` (views.py:36, 68, 110, 146); xóa đơn vị không bắt `ProtectedError` (views.py:168-173).
  - Đã dùng Permission chuẩn với `has_perm` (Meta.permissions `export_donvi`).
  - Đề và bảng phân công Nhóm 7 không có trường ảnh chữ ký.
- **Vấn đề:** TH7-01 (`AUTH_USER_MODEL`), TH7-02 (ảnh chữ ký), TH7-03 (resolve chức vụ), TH7-04 (xóa cứng va chạm FK PROTECT), TH7-05 (hai nguồn hồ sơ cán bộ), TH7-06 (plan chưa cập nhật dữ kiện), TH1-01 (định nghĩa admin), TH1-04 (`apiClient.ts` bị sửa).
- **Contract cần chốt:**
  - (a) Không đổi `AUTH_USER_MODEL`; CBNV là OneToOne tới `settings.AUTH_USER_MODEL`.
  - (b) Model ChucVu; CBNV gồm `user`, họ tên, đơn vị FK, chức vụ FK, chức danh, trạng thái.
  - (c) Nghỉ việc thì `is_active=False`; "xóa" nghĩa là vô hiệu hóa; trả 409 khi bản ghi đang bị tham chiếu; endpoint ghi kiểm `has_perm`.
  - (d) API chỉ đọc cho nhân sự, chức vụ, đơn vị (có lọc `is_public`, có tham số lấy toàn bộ); hàm `thong_tin_can_bo(user)`.
  - (e) Nhóm quyền lưu bằng `user.groups`; ma trận phân quyền hiển thị được quyền của app `signing`.
  - (f) Cam kết ngày cho ChucVu và CBNV; mở PR phần Đơn vị lên staging sớm.
- **Phương án tạm:** MVP chỉ dùng người ký theo tài khoản và giữ BigInteger tạm. Endpoint tra cứu người dùng tạm của Nhóm 5. Nhóm 5 tự giữ ảnh chữ ký. Seed các nhóm quyền mẫu.

### 7.7. Nhóm 8 – AI chatbox (project Django riêng)

- **Điểm nối:** chatbot mô tả luồng trình ký cho người dùng; truy vấn SQL trên bảng văn bản và cán bộ.
- **Hiện trạng:**
  - Nhánh `8_ai_chatbox`@9ca413c có merge-base là Initial commit và dùng `backend/django_project/settings.py` thay cho `config/settings.py`.
  - Nội dung tĩnh mô tả ký bằng "Token PKI/Cloud HSM qua OTP" và "tự động sinh số hiệu văn bản đi" (AiAssistantPage.tsx:87, 687@8_ai_chatbox; FloatingAIBox.tsx:80 và AiAssistantPage.tsx:54, 224@staging).
  - `sql_document_source.py:12-14` giả định các bảng `documents_vanbanden`, `documents_vanbandi`, `documents_vanbanmat`, khác bảng thật `documents_document`; dòng 34-35, 102-104 giả định `accounts_employee`.
  - Requirements ghim `Django>=5.1,<6.0`.
- **Vấn đề:** TH2-02 (mô tả trái luồng thật), HT-09 (nhánh chưa dựng trên staging), TH7-01 (phụ thuộc `accounts_employee`).
- **Contract cần chốt:** Trưởng nhóm 5 gửi đoạn mô tả luồng kèm danh sách trạng thái và trạng thái hiển thị đã chốt; Nhóm 8 sửa nội dung và tên bảng cho khớp.
- **Phương án tạm:** Nhóm 5 không sửa tệp của nhóm khác; khi demo trình ký thì không dùng gợi ý của chatbot nếu nội dung chưa được sửa.

### 7.8. Hạ tầng chung và nhánh Nhóm 5

- **Điểm nối:**
  - DB, mail, tác vụ định kỳ.
  - File chung: settings, urls, requirements, router, i18n.
  - Quality Gate, CI, `.gitignore`, workflow gán reviewer.
  - Phiên bản Python và Node.
  - Đường PR `feat/*` → `5_signing_workflow` → `staging`.
- **Hiện trạng:**
  - Staging dùng SQLite; không nhánh nào có celery hay redis.
  - Quality Gate chỉ chạy `test accounts`; PR template chạy test từ thư mục gốc, kết quả 0 test.
  - Không có workflow CI chạy test.
  - Node 20 chạy vitest lỗi, trong khi README cho phép Node 18/20.
  - Python 3.10/3.11 cài Django 5.2.17; Python ≥3.12 cài 6.1.1.
  - `5_signing_workflow` chỉ có tài liệu; `feat/signing-models` dựng trên nhánh này nên không có `manage.py`; `feat/5-signing-workflow` dựng trên staging và fast-forward được.
- **Vấn đề:** HT-01 đến HT-13.
- **Contract cần chốt (Trưởng nhóm 5, vai DevOps, cùng PM):**
  - MVP không dùng Redis/Celery.
  - Email theo phiên bản Django, hoặc ghim Django 5.2 LTS.
  - `SECRET_KEY` đọc từ `.env`; SQLite chế độ `IMMEDIATE`.
  - Workflow CI; sửa PR template và Quality Gate.
  - "Khe" đăng ký cho từng nhóm trong file chung.
  - Node ≥22.22.2 (khai báo engines).
  - Reviewer dự phòng khi tác giả PR vào staging là Trưởng nhóm 5.
- **Phương án tạm:** management command chạy bằng Task Scheduler; challenge dùng `TimestampSigner`; thành viên Nhóm 5 mở PR vào staging; demo trên một máy, truy cập `localhost`.

## 8. Danh sách vấn đề chi tiết

Mỗi mục gồm: mức độ, mô tả, bằng chứng, đề xuất và bên chốt. Trong từng nhóm, các mục được sắp theo mức độ giảm dần.

### 8.1. Luồng nghiệp vụ và máy trạng thái (LUONG)

#### LUONG-01 · Cao · Luồng tệp chưa được đặc tả: không có API nhận và phục vụ tệp, chưa quy định ai tính mã băm, không đối chiếu lại bytes khi ký
- **Mô tả:** Mục 7 không có endpoint nhận tệp: `POST /requests` chỉ "tạo NHAP từ văn bản", `giai-quyet` chỉ ghi "tải bản mới". Cũng không có endpoint trả bytes tệp gốc, tệp hoàn tất hay ảnh chữ ký cho PDF viewer. Plan chưa quy định server tự tính `ma_bam_tai_lieu`; spec dòng 124 lại nghiêng về để client tính trước. Văn bản Nhóm 2 không có trường băm hay phiên bản và có thể có nhiều tệp. Điều kiện ký ở 5.3 chỉ so hash client gửi với hash đã lưu, không đối chiếu bytes trên đĩa. Đây là đường găng của gạch "Chữ ký số" và của trang chi tiết.
- **Bằng chứng:** plan.md dòng 109, 191-192, 518, 580, 589, 595; dòng 563-604 không có endpoint tệp nào. spec.md dòng 91, 124, 127. documents/models.py:208-223@2_documents: `DocumentAttachment` có `FileField`, `file_size`, không có hash. `git show origin/staging:backend/config/settings.py | grep MEDIA`: rỗng. apiClient.ts:50-55@staging đọc phản hồi không phải JSON bằng `res.text()`. Đối chiếu cách làm đã có: approvals/services.py:229-241 (server tự tính sha256) và 507-512 (băm lại tệp khi ký, lệch thì ConflictError)@feat/5-signing-workflow.
- **Đề xuất (chờ Trưởng nhóm 5 chốt):**
  - (1) Server tự tính SHA-256 từ bytes đã lưu lúc gửi và lúc giải quyết; hash client gửi chỉ để đối chiếu.
  - (2) Chọn một: endpoint multipart cho tạo yêu cầu và `giai-quyet`; hoặc chọn đúng một tệp PDF đính kèm rồi sao bytes sang kho Nhóm 5 (gắn với TH2-01).
  - (3) Thêm GET tệp gốc, tệp hoàn tất, ảnh chữ ký, trả `FileResponse` sau khi kiểm quyền.
  - (4) Khi ký, băm lại tệp (tối đa 20MB); lệch thì trả 409; thêm test tráo tệp trên đĩa.
  - (5) Frontend tải blob kèm Bearer, không đi qua `apiClient` hiện tại.
- **Bên chốt:** Trưởng nhóm 5 (contract); Nhóm 1 (settings MEDIA, `apiClient`); Nhóm 2 (nếu dùng tệp đính kèm của văn bản).

#### LUONG-02 · Trung bình · Dữ liệu nháp chưa có chỗ lưu; trạng thái `NHAP` của lượt trình mâu thuẫn với quy tắc "lượt tạo lúc gửi"; nháp không sửa, xóa được
- **Mô tả:** Dòng 94 và API dòng 580 yêu cầu nhập vị trí ký cho từng người ký khi tạo NHAP; Pha 2 (dòng 665) snapshot vị trí lúc gửi. Năm cột tọa độ chỉ có trên `signing_request_step_signer`. Bảng này chỉ tồn tại dưới một `signing_attempt`, và attempt bắt buộc có `vi_tri_luu_tep`, `ma_bam_tai_lieu` hợp lệ. Dòng 537, 582 nói lượt đầu tạo lúc gửi, nhưng enum của lượt có `NHAP` và 6.1 ghi `NHAP -> CHO_KY (gui)`. Người ký theo chức vụ chỉ được resolve lúc gửi (dòng 88, 514), nên trước khi gửi chưa có dòng để gắn tọa độ. Mục 7.2 không có PATCH hay DELETE cho yêu cầu NHAP.
- **Bằng chứng:** plan.md dòng 88, 94-95, 99, 313, 369-373, 514, 537, 543, 580, 582, 665, 758. models.py@1a6fcc9: dòng 251-252, 276-277 (CHECK regex), 312 (`buoc_ky` NOT NULL), 332-338. KT: tạo `SigningAttempt` với `vi_tri_luu_tep` và `ma_bam_tai_lieu` rỗng thì gặp IntegrityError (`chk_signing_attempt_ma_bam_sha256`).
- **Đề xuất (chờ Trưởng nhóm 5 chốt), chọn một:**
  - (A) Tạo attempt `so_luot=1` ở `NHAP` ngay khi tạo nháp (đã có tệp), kèm dòng người ký tạm; khi gửi thì resolve lại và chuyển sang `CHO_KY`.
  - (B) Thêm JSON `vi_tri_ky` trên `signing_request`, đánh khóa theo id `signing_process_step_signer` (cần DL-08); lúc gửi chép sang snapshot; bỏ `NHAP` khỏi enum của lượt.
  - Dù chọn cách nào: thêm PATCH, DELETE cho yêu cầu NHAP chưa gửi lần nào; M1 cho phép tọa độ rỗng.
- **Bên chốt:** Trưởng nhóm 5.

#### LUONG-03 · Trung bình · Bảng 6.2 thiếu điều kiện ở mức người ký cho `tu_choi`/`yeu_cau_sua` và điều kiện trạng thái lượt cho `uy_quyen`/`thu_hoi`; lối thoát dòng 184 không thực hiện được
- **Mô tả:** 6.1 đã chặn `tu_choi`, `yeu_cau_sua` trên lượt đã kết thúc. Nhưng 6.2 không yêu cầu người thực hiện đang `CHO_KY` và đã được mở, nên người ở cấp chưa mở (`TUAN_TU`) hoặc người đã `DA_KY` vẫn từ chối được cả hồ sơ. `uy_quyen`, `thu_hoi` không đổi trạng thái lượt nên 6.1 không chặn; điều kiện "lượt chưa hoàn thành" của `thu_hoi` vẫn thỏa với `YEU_CAU_SUA`, `TU_CHOI`, `HUY`. Lối thoát dòng 184 ("gộp người ký thì đi qua yêu cầu chỉnh sửa") không thực hiện được, vì lượt mới dùng lại cùng quy trình và người tạo không được sửa người ký (dòng 73, 284). Lối thoát dòng 159 chạy được theo chữ plan, nhưng sẽ mất nếu siết điều kiện.
- **Bằng chứng:** plan.md dòng 73, 121-124, 159, 184, 284, 515-520, 544-546, 557-561. KT (mô phỏng): `TUAN_TU` 2 cấp, người ở cấp 2 có `thoi_diem_mo` rỗng bấm `tu_choi` → thành công, yêu cầu chuyển `TU_CHOI`. KT: lượt đang `YEU_CAU_SUA` vẫn `uy_quyen` được.
- **Đề xuất (chờ Trưởng nhóm 5 chốt):**
  - Thêm khối "Điều kiện chung" vào 6.2: mọi hành động chỉ áp trên lượt hiện hành đang `CHO_KY`; người gọi là `nguoi_ky` của dòng (riêng `uy_quyen` thì quản trị được làm thay); `tu_choi` cần người ký `CHO_KY` và đã có `thoi_diem_mo`; `thu_hoi` đổi điều kiện thành "lượt `CHO_KY`".
  - Chốt riêng: người đã `DA_KY` có được `yeu_cau_sua` không.
  - Sửa dòng 184 thành "cần đổi người ký thì hủy và tạo yêu cầu mới".
  - Thêm ma trận test: hành động × trạng thái lượt × trạng thái người ký.
- **Bên chốt:** Trưởng nhóm 5.

#### LUONG-04 · Trung bình · Lượt kết thúc không dọn trạng thái cấp, người ký, thread và thông báo; thiếu sơ đồ trạng thái cho cấp và người ký; dòng 156 và 159 mâu thuẫn về thu hồi ở `TUAN_TU`
- **Mô tả:** Chỉ nhánh `YEU_CAU_SUA` có quy tắc "cấp đang mở chuyển `TAM_DUNG`" (dòng 122). `TU_CHOI`, `HUY` không có quy tắc cho cấp và người ký; enum người ký không có trạng thái dừng; enum thông báo không có trạng thái hủy. Người ký của lượt đã dừng vẫn `CHO_KY` kèm `thoi_diem_mo`, nên truy vấn việc cần ký chỉ lọc trên dòng người ký sẽ hiện cả hồ sơ đã hủy hoặc đã bị từ chối. Hủy khi lượt đang `YEU_CAU_SUA` để lại lượt ở `YEU_CAU_SUA` và thread ở `DANG_MO`. `giai-quyet` không có điều kiện (dòng 595), nên nếu service không kiểm thì vẫn tạo được lượt mới trên yêu cầu đã `HUY`. Dòng 156 nói thu hồi chỉ có ở `SONG_SONG`, dòng 159 lại ngụ ý `TUAN_TU` vẫn thu hồi được.
- **Bằng chứng:** plan.md dòng 122, 156, 159, 339, 360, 448, 496, 539, 544-545, 558, 595. models.py@1a6fcc9 dòng 64-75, 97-110. KT (mô phỏng): sau `yeu_cau_sua`, người ký còn `CHO_KY` vẫn được truy vấn trả về; hủy xong thì lượt vẫn `YEU_CAU_SUA`, thread vẫn `DANG_MO`. Sau `tu_choi` hoặc `huy` khi đang `CHO_KY`, người ký khác vẫn `CHO_KY` và vẫn được trả về.
- **Đề xuất (chờ Trưởng nhóm 5 chốt):**
  - Một hàm dừng lượt dùng chung cho `YEU_CAU_SUA`, `TU_CHOI`, `HUY`:
    - cấp chưa `HOAN_THANH` chuyển `DA_DUNG` (đổi tên từ `TAM_DUNG`);
    - người ký `CHO_KY` chuyển `DA_DUNG` (thêm vào enum);
    - thông báo `CHO_GUI` chuyển `DA_HUY`;
    - thread `DANG_MO` chuyển `DA_DONG` khi hủy.
  - `giai-quyet` chỉ chạy khi yêu cầu `CHO_KY` và thread `DANG_MO`.
  - Thêm vào mục 6 sơ đồ trạng thái cho cấp và người ký. Sửa dòng 159 thành "`TUAN_TU` không có thu hồi".
  - Quy ước truy vấn việc cần ký: người ký `CHO_KY`, có `thoi_diem_mo`, lượt `CHO_KY`, cấp `DANG_KY`.
- **Bên chốt:** Trưởng nhóm 5 (chốt); thành viên Nhóm 5 (code, test).

#### LUONG-05 · Trung bình · API hành động định danh theo lượt trình, không theo dòng người ký; một người ở hai cấp gây mơ hồ ở `SONG_SONG`; trùng người trong cấp gây IntegrityError
- **Mô tả:** Mọi hành động có dạng `POST /signing/attempts/{id}/...`; payload `uy-quyen` chỉ có `nguoi_ky` mới và `ly_do_uy_quyen`. Khi quản trị ủy quyền thay (dòng 180, spec dòng 100), server không biết thay dòng nào. Ràng buộc chỉ là unique (`buoc_ky`, `nguoi_ky`), nên một tài khoản có thể ở hai cấp của cùng lượt; ở `SONG_SONG` cả hai dòng cùng mở và `/ky` không biết áp vào dòng nào. Plan không có quy tắc khi chức vụ resolve ra đúng người đã được chỉ định đích danh trong cùng cấp. Dòng 565 ghi đây là "contract dự kiến", nên sửa lúc này còn ít tốn kém.
- **Bằng chứng:** plan.md dòng 180, 377, 513-514, 565, 589-593; spec.md dòng 100; models.py@1a6fcc9 dòng 348. KT: cùng tài khoản ở 2 cấp tạo 2 dòng, cả hai có `thoi_diem_mo`. Trùng tài khoản trong một cấp → IntegrityError `UNIQUE constraint failed: signing_request_step_signer.buoc_ky_id, signing_request_step_signer.nguoi_ky_id`.
- **Đề xuất (chờ Trưởng nhóm 5 chốt):**
  - Đổi endpoint sang `/signing/signers/{signer_id}/ky|tu-choi|yeu-cau-sua|uy-quyen|thu-hoi`, hoặc bắt buộc truyền `signer_id`. Server kiểm dòng thuộc lượt hiện hành và đúng người gọi (hoặc quản trị khi `uy-quyen`).
  - Kiểm lúc kích hoạt quy trình và lúc gửi (sau khi resolve): một tài khoản không xuất hiện hai lần trong một lượt; vi phạm thì trả lỗi nghiệp vụ.
- **Bên chốt:** Trưởng nhóm 5.

#### LUONG-06 · Trung bình · Ủy quyền ghi đè `nguoi_ky` trên dòng cũ: chữ ký cũ hiển thị dưới tên người nhận, mất chuỗi ủy quyền; tài khoản quản trị có thể tự nhận ô ký rồi ký
- **Mô tả:** Dòng 182, 560 đổi `nguoi_ky` ngay trên dòng đang có. `signing_signature` không có cột người ký, nên chữ ký đã thu hồi của người cũ hiện như của người nhận. Người thật vẫn truy được qua `khoa_ky.nguoi_so_huu` và nhật ký. `ten_nguoi_ky`, `ten_chuc_vu` không được yêu cầu cập nhật. `uy_quyen_tu` chỉ một trường nên chuỗi ba bước mất dấu người đầu. Hạn của cấp giữ nguyên, nên người nhận ủy quyền vì "quá hạn nghiêm trọng" sẽ bị gắn `ky_tre_han`. Plan không cấm ủy quyền cho chính người thực hiện. "Thẩm quyền tương đương" chưa kiểm được khi chưa có model chức vụ. Không có quy tắc thông báo cho người được ủy quyền.
- **Bằng chứng:** plan.md dòng 175, 178-184, 356-357, 366-368, 407, 560; mục 9 không có loại thông báo cho ủy quyền. models.py@1a6fcc9 dòng 315 (`chuc_vu_id` BigInteger tạm), 395-418 (`SigningSignature` không có cột người ký). KT (mô phỏng): tài khoản quản trị tự nhận ủy quyền ô ký của người khác → thành công; dòng có `nguoi_ky` mới nhưng `ten_nguoi_ky` cũ; chữ ký cũ đọc qua `buoc_ky` hiện người ký mới; tài khoản quản trị ký bằng khóa của chính tài khoản đó → thành công.
- **Đề xuất (chờ Trưởng nhóm 5 chốt):**
  - Giữ dòng cũ với trạng thái mới `DA_UY_QUYEN`. Tạo dòng mới cho người nhận: snapshot tên và chức vụ; liên kết về dòng cũ; `thoi_diem_mo` bằng thời điểm ủy quyền nếu cấp đang mở.
  - Cấm ủy quyền cho chính người thực hiện, người tạo, hoặc người đã có trong lượt.
  - Tạo thông báo cho người nhận, người ký gốc, người tạo. Ghi rõ `ky_tre_han` tính theo hạn của cấp hay theo thời điểm nhận ủy quyền.
  - Stepper hiển thị nhãn "Ký thay theo ủy quyền".
- **Bên chốt:** Trưởng nhóm 5.

#### LUONG-07 · Thấp · Quy tắc hạn xử lý còn mơ hồ
- **Mô tả:** Dòng 167 ("chia đều thời gian còn lại đến `han_chot`") không nói chia lúc gửi hay lúc mở từng cấp. Nếu chia lúc gửi thì cấp sau bị gắn trễ vì cấp trước chậm. `han_chot` không bắt buộc và không được kiểm lúc gửi: rỗng thì không bao giờ có chữ ký trễ; đã qua thì mọi chữ ký bị gắn trễ ngay. Lượt mới dùng lại `han_chot` cũ (dòng 170 cấm đổi hạn sau khi gửi). Quản trị được đổi hạn (dòng 170, 289) nhưng mục 7.2 không có endpoint. `KY_CHINH` mở sau ký nháy vẫn dùng chung `han_xu_ly` của cấp. Phần này là mở rộng của nhóm; E14 và đề md dòng 304 chỉ đòi thông báo khi đến lượt.
- **Bằng chứng:** plan.md dòng 165-170, 175, 253, 289, 340, 513-514, 579-585; models.py@1a6fcc9 dòng 223 (`han_chot` null=True), 295. KT: `han_chot` rỗng → `han_xu_ly` rỗng, `ky_tre_han` False; gửi với `han_chot` đã qua 1 ngày → thành công, ký ngay → `ky_tre_han` True, `so_giay_tre` 86400.
- **Đề xuất (chờ Trưởng nhóm 5 chốt):**
  - (1) `han_xu_ly` tính lúc mở cấp: có `so_gio_xu_ly` thì cộng vào thời điểm mở; không có thì chia thời gian còn lại cho số cấp chưa xong; không vượt `han_chot`.
  - (2) Chọn: `han_chot` rỗng nghĩa là không có hạn, hoặc `han_chot` bắt buộc lớn hơn thời điểm gửi.
  - (3) `giai_quyet`, `xem_xet_lai` nhận `han_chot` mới.
  - (4) Thêm endpoint đổi hạn có ghi nhật ký, hoặc bỏ quyền đổi hạn khỏi M1.
- **Bên chốt:** Trưởng nhóm 5.

#### LUONG-08 · Thấp · Ký nháy chặn thu hồi khi ký chính đã được mở nhưng chưa ký thì ký chính vẫn ký được (chỉ ở `SONG_SONG`)
- **Mô tả:** Dòng 158 chỉ cấm ký nháy chặn thu hồi khi `KY_CHINH` cùng cấp "đã ký". Plan không yêu cầu xóa `thoi_diem_mo` của `KY_CHINH`, và 5.3 dòng 517 chỉ kiểm `thoi_diem_mo` có giá trị. Vì vậy `KY_CHINH` ký được trong khi ký nháy chặn đang `CHO_KY`, trái dòng 83 và tiêu chí dòng 705. Test Pha 3 (dòng 675) chỉ phủ ca "ký chính đã ký". Thu hồi không có trong E14.
- **Bằng chứng:** plan.md dòng 83, 156-158, 517, 557, 561, 675, 705. KT (mô phỏng): ký nháy ký → ký chính được mở → ký nháy thu hồi (thành công, `thoi_diem_mo` của ký chính còn) → ký chính ký (thành công) → kết quả: ký nháy `CHO_KY`, ký chính `DA_KY`.
- **Đề xuất (chờ Trưởng nhóm 5 chốt):** chọn một: (a) cấm thu hồi khi `KY_CHINH` cùng cấp đã có `thoi_diem_mo`; (b) cho thu hồi nhưng trong cùng transaction đặt lại `thoi_diem_mo` rỗng cho `KY_CHINH` đang `CHO_KY`. Khi ký vẫn kiểm lại quy tắc chặn; thêm test; có thể dời toàn bộ thu hồi sang M2.
- **Bên chốt:** Trưởng nhóm 5.

#### LUONG-09 · Thấp · Phiên bản quy trình: kích hoạt bản mới không ngừng bản cũ; lúc gửi không kiểm quy trình còn `HOAT_DONG`; lượt mới không rõ lấy snapshot từ đâu
- **Mô tả:** Plan không nói bản cũ chuyển `NGUNG` khi kích hoạt bản mới, nên hai phiên bản cùng mã có thể cùng `HOAT_DONG`. Dòng 68 chỉ kiểm `HOAT_DONG` lúc tạo yêu cầu; 5.3 không kiểm lại lúc gửi. Lượt mới (`giai_quyet`, `xem_xet_lai`) không nói resolve lại người ký hay chép từ lượt trước; nếu resolve lại thì người đang vắng, vốn đã được ủy quyền ở lượt trước, sẽ bị gán lại.
- **Bằng chứng:** plan.md dòng 67-70, 124, 126, 284-285, 513-514, 584, 595. KT: lưu được 2 bản ghi `HOAT_DONG` cùng `ma_quy_trinh`.
- **Đề xuất (chờ Trưởng nhóm 5 chốt):** kích hoạt bản mới thì các bản `HOAT_DONG` khác cùng mã chuyển `NGUNG` trong cùng transaction, kèm partial unique; lúc gửi kiểm quy trình còn `HOAT_DONG`; ghi rõ `NGUNG` không ảnh hưởng yêu cầu đang chạy; lượt mới chép cấu trúc từ lượt trước (cần DL-08), chỉ resolve lại người không còn hoạt động.
- **Bên chốt:** Trưởng nhóm 5.

#### LUONG-10 · Thấp · Vòng đời thread yêu cầu sửa: người ký khác không tham gia được; không có lối "thống nhất không cần sửa"; thiếu ràng buộc mỗi lượt một thread
- **Mô tả:** Spec dòng 102 chỉ cho người tạo và người yêu cầu sửa đọc, viết trong thread. `giai_quyet` bắt tải bản mới (dòng 124, 595), kể cả khi hai bên thống nhất không cần sửa. Yêu cầu sửa thứ hai trên cùng lượt đã bị 6.1 chặn ở service, nhưng ở CSDL vẫn lưu được hai thread `DANG_MO`.
- **Bằng chứng:** spec.md dòng 102-103; plan.md dòng 122-125, 448, 528, 545, 595; models.py@1a6fcc9 dòng 481-496. KT: lưu được 2 thread `DANG_MO` trên một lượt.
- **Đề xuất (chờ Trưởng nhóm 5 chốt):** partial unique theo `luot_trinh` cho thread `DANG_MO`; mọi người ký của lượt đọc, viết được; thêm `DA_DONG` dùng khi hủy (LUONG-04); cho `giai_quyet` giữ nguyên tệp (cùng mã băm) nhưng vẫn tạo lượt mới.
- **Bên chốt:** Trưởng nhóm 5.

#### LUONG-11 · Thấp · Từ chối và xem xét lại: không rõ có bắt tệp mới; lý do từ chối cũ còn trên yêu cầu; 6.1 thiếu chuyển `TU_CHOI` → `HUY`
- **Mô tả:** Dòng 126, 584 không nói `xem_xet_lai` có bắt tải tệp mới. Nếu giữ nguyên mã băm thì người đã từ chối nhiều khả năng từ chối lại, và ranh giới với `YEU_CAU_SUA` + `giai_quyet` trở nên mờ. `ngay_tu_choi`, `ly_do_tu_choi` không được yêu cầu xóa khi quay về `CHO_KY`. Dòng 127 cho người tạo hủy "trước khi hoàn thành", nhưng 6.1 chỉ có `NHAP → HUY` và `CHO_KY → HUY`.
- **Bằng chứng:** plan.md dòng 126-127, 292-293, 538-540, 584; spec.md dòng 95. KT (mô phỏng): hủy yêu cầu đang `TU_CHOI` theo đúng 6.1 → bị chặn.
- **Đề xuất (chờ Trưởng nhóm 5 chốt):** cách đơn giản là coi `TU_CHOI` là trạng thái kết thúc, bỏ `xem_xet_lai`; muốn trình lại thì tạo yêu cầu mới có liên kết `trinh_lai_tu`. Nếu giữ `xem_xet_lai`: chỉ người tạo; bắt buộc lý do và tệp mới; xóa lý do từ chối cũ (hoặc chuyển vào lịch sử); thêm `TU_CHOI → HUY`.
- **Bên chốt:** Trưởng nhóm 5.

#### LUONG-12 · Thấp · Người tạo tự chọn `SONG_SONG` cho mọi quy trình, nên cấp cuối ký được trước khi cấp dưới rà soát (câu hỏi thiết kế)
- **Mô tả:** Quy trình chỉ có `kieu_ky_mac_dinh`, người tạo được chọn `TUAN_TU` hoặc `SONG_SONG` (dòng 72, tiêu chí 706, spec dòng 123). Đây là lựa chọn có chủ ý của plan và E14 không quy định, nên đây là câu hỏi thiết kế, không phải lỗi đặc tả. Bản plan trên `feat/5-signing-workflow` (dòng 65) có cụm "theo lựa chọn được hệ thống cung cấp", cho thấy từng có ý giới hạn lựa chọn này.
- **Bằng chứng:** plan.md dòng 17, 72, 86, 706; spec.md dòng 123; signing-backend-plan.md:65@feat/5-signing-workflow; E14 không nhắc cách thức ký.
- **Đề xuất (chờ Trưởng nhóm 5 chốt):** tùy chọn thêm cờ `cho_phep_doi_kieu_ky` (mặc định False) trên quy trình, hoặc đưa câu hỏi vào lần trình Giảng viên duyệt F14.
- **Bên chốt:** Trưởng nhóm 5 (có thể hỏi Giảng viên).

#### LUONG-13 · Thấp · Mâu thuẫn nhỏ giữa plan và spec; ngữ nghĩa ký nháy và ký chính trong cấp còn hở
- **Mô tả:** Spec dòng 35 cho người tạo đặt số giờ xử lý từng cấp, plan để `so_gio_xu_ly` trong quy trình (dòng 253), và quy trình đã kích hoạt thì không sửa được. Màu "đỏ = trả về" (spec dòng 127) không ứng với trạng thái cụ thể; vai trò kiểm toán (dòng 617) không có permission ở mục 8. `thu_tu` trong cấp không được chụp sang snapshot người ký. Plan chưa nói nhiều `KY_NHAY` ký song song hay tuần tự, cấp có 0 hoặc 2 `KY_CHINH` có hợp lệ không; `chan_ky_chinh` mặc định True cả trên dòng `KY_CHINH`. Lượt `HOAN_THANH` chưa có tệp hoàn tất thì không phân biệt được "đang phẳng hóa" với "phẳng hóa lỗi".
- **Bằng chứng:** spec.md dòng 35, 123-127; plan.md dòng 70, 85, 253, 268-270, 320-321, 348-375, 617-626; models.py@1a6fcc9 dòng 187-188, 311-352, 319. KT: snapshot người ký không có trường `thu_tu`.
- **Đề xuất (chờ Trưởng nhóm 5 chốt):** đồng bộ lại spec sau khi chốt; chụp `thu_tu` sang snapshot; quy ước các `KY_NHAY` trong cấp ký song song; mỗi cấp đúng 1 `KY_CHINH`, kiểm lúc kích hoạt; CHECK `chan_ky_chinh=false` trên dòng `KY_CHINH`; thêm trạng thái hoặc cờ lỗi phẳng hóa trên lượt.
- **Bên chốt:** Trưởng nhóm 5.

#### LUONG-14 · Thấp · Không chặn nhiều yêu cầu trình ký chạy song song trên cùng một văn bản
- **Mô tả:** `signing_request.van_ban` là FK bắt buộc, nhưng plan không giới hạn số yêu cầu `NHAP`/`CHO_KY` trên cùng văn bản; 5.3 không nhắc, model không có ràng buộc. Hai luồng ký độc lập có thể cho hai kết quả trái nhau và hai tệp hoàn tất, khiến khâu phát hành và Nhóm 2 không biết kết quả nào chính thức.
- **Bằng chứng:** plan.md dòng 280, 509, 580; mục 5.3 (dòng 511-529) không có quy tắc; spec.md dòng 91; models.py@1a6fcc9 dòng 211. KT: hai yêu cầu cùng `van_ban_id` đều ở `CHO_KY`.
- **Đề xuất (chờ Trưởng nhóm 5 chốt):** thêm vào 5.3 "mỗi văn bản tối đa một yêu cầu `NHAP` hoặc `CHO_KY`; `HUY`, `TU_CHOI` giải phóng văn bản". Kiểm ở service lúc tạo và gửi, kèm `UniqueConstraint(fields=['van_ban'], condition=Q(trang_thai__in=['NHAP','CHO_KY']))`. Nếu theo phương án A (TH2-01, `van_ban` cho phép rỗng) thì ràng buộc chỉ áp khi `van_ban` có giá trị.
- **Bên chốt:** Trưởng nhóm 5 (thống nhất với Nhóm 2 cách hiển thị trạng thái trình ký trên văn bản).

### 8.2. Dữ liệu và model (DL)

#### DL-01 · Trung bình · Bất biến chỉ chặn ở `save()`/`delete()`/`clean()` của instance: mã băm của lượt sửa được dù spec coi là bất biến; `QuerySet.update/delete` vượt qua; thiếu partial unique
- **Mô tả:** Spec dòng 137 coi mã băm của lượt là bất biến, nhưng `SigningAttempt` không chặn gì: lượt `CHO_KY` vẫn đổi được `ma_bam_tai_lieu`, `vi_tri_luu_tep`. Theo dòng 110, cột này là nguồn sự thật. Chữ ký, nhật ký, manifest chỉ override `save()`/`delete()` của instance, nên `QuerySet.update()/delete()` vượt qua; riêng chữ ký hiện hành được FK PROTECT chặn xóa. Bất biến ở dòng 309, 365, 409 chỉ nằm trong `clean()`, mà `save()` không gọi `clean()`. Thiếu partial unique: mỗi yêu cầu một lượt `NHAP`/`CHO_KY`; mỗi lượt một thread `DANG_MO`; mỗi mã quy trình một bản `HOAT_DONG`; mỗi lượt một manifest `DA_CHOT`. Dòng 484 ("role ứng dụng không có quyền UPDATE/DELETE") không làm được trên SQLite. Staging chạy SQLite, nơi `select_for_update` không có tác dụng, nên ràng buộc ở CSDL là lớp chặn cần ưu tiên.
- **Bằng chứng:** spec.md dòng 137; plan.md dòng 109-110, 153, 309, 365, 409, 422, 434, 484; models.py@1a6fcc9 dòng 244-282, 354-356, 429-437, 462-474, 546-552. `git ls-tree origin/feat/signing-models backend/apps/signing`: không có `admin.py`. KT: `QuerySet.update` trên chữ ký sửa được 1 dòng; xóa chữ ký đã thu hồi thành công, xóa chữ ký hiện hành → ProtectedError; nhật ký update và delete được; lưu được 2 manifest `DA_CHOT` trên một lượt với `thoi_diem_chot` rỗng; lượt `CHO_KY` đổi được hash. KT: lưu được `chu_ky_hien_hanh` trỏ tới chữ ký của người khác, `DA_KY` không có chữ ký, `TU_CHOI` không lý do, `uy_quyen_tu` bằng `nguoi_ky`, 2 lượt `CHO_KY` trên một yêu cầu, chữ ký gắn sai lượt, `phien_ban_quy_trinh` lệch quy trình.
- **Đề xuất (chờ Trưởng nhóm 5 chốt), làm việc ít tốn kém trước:**
  - (1) `SigningAttempt.save()` cấm đổi `vi_tri_luu_tep`, `ma_bam_tai_lieu`, `so_luot`, `trinh_ky` khi trạng thái khác `NHAP`.
  - (2) Thêm `UniqueConstraint` có condition (chạy trên cả SQLite và PostgreSQL) cho bốn trường hợp trên, và CHECK "`DA_CHOT` thì `thoi_diem_chot` không rỗng".
  - (3) Manager/QuerySet riêng chặn update, delete cho 3 model bất biến.
  - (4) Service gọi `full_clean()` hoặc tự kiểm tương đương; `luot_trinh` của chữ ký suy ra từ `buoc_ky`.
  - (5) Sửa dòng 484 thành "chặn ở tầng ORM"; bỏ cột `phien_ban_quy_trinh` hoặc để service tự gán.
- **Bên chốt:** Trưởng nhóm 5 (câu chữ plan, review); thành viên Nhóm 5 (code).

#### DL-02 · Thấp · `Idempotency-Key` bắt buộc cho mọi hành động chuyển trạng thái nhưng chỉ có chỗ lưu cho gửi và thao tác của người ký; chưa định nghĩa phản hồi khi retry
- **Mô tả:** Dòng 204, 609 bắt buộc header cho mọi hành động chuyển trạng thái; dòng 205-206 chỉ có hai chỗ lưu. `khoa_chong_trung_thao_tac` của người ký không unique và chỉ một ô, nên khóa thao tác trước bị thao tác sau ghi đè. `huy`, `kich-hoat`, `ngung`, `phat-hanh`, `keys/verify`, `xoay-vong`, thu hồi khóa không có chỗ lưu. Plan không nói retry đúng khóa thì trả gì. Unique (`trinh_ky`, `so_luot`) cùng việc kiểm trạng thái đã chặn phần lớn ca trùng.
- **Bằng chứng:** plan.md dòng 202-206, 528, 609, 695, 722; models.py@1a6fcc9 dòng 256 (attempt unique=True), 275, 339 (signer không unique).
- **Đề xuất (chờ Trưởng nhóm 5 chốt):** thu hẹp dòng 204, 609: header chỉ bắt buộc cho hành động tạo bản ghi (`gui`, `xem-xet-lai`, `giai-quyet`, `ky`, `nhan-ban`, POST requests, POST messages). Các hành động còn lại dựa vào kiểm trạng thái dưới khóa; nếu trạng thái đã đúng thì trả 200 kèm trạng thái hiện tại. Muốn đầy đủ thì thêm bảng `signing_idempotency` (unique `nguoi_dung`, `khoa`).
- **Bên chốt:** Trưởng nhóm 5.

#### DL-03 · Thấp · Đổi cột tạm BigInteger sang ForeignKey bằng `makemigrations` tự động sinh Remove + Add và mất dữ liệu; FK tới văn bản buộc signing merge sau Nhóm 2
- **Mô tả:** Thay `don_vi_id` (BigInteger) bằng FK `don_vi` thì `makemigrations` sinh RemoveField rồi AddField, dữ liệu cũ thành NULL; với `van_ban_id` NOT NULL thì Django hỏi giá trị mặc định. FK tới `documents.Document` làm signing phụ thuộc app `documents`, mà staging chưa đăng ký app này. DB là SQLite cục bộ, phần mất chỉ là dữ liệu demo.
- **Bằng chứng:** models.py@1a6fcc9 dòng 8-10, 160, 184, 211, 315; settings.py:38-53@staging không có app documents. KT: đổi `don_vi_id` sang FK thì `makemigrations` in "Remove field don_vi_id" và "Add field don_vi"; sau migrate, giá trị đọc lại là NULL.
- **Đề xuất (chờ Trưởng nhóm 5 chốt):** giữ BigInteger cho tới khi nhóm nguồn lên staging. Khi đổi: nếu `0001` chưa lên staging thì tạo lại `0001` có FK; nếu đã lên thì viết migration tay bằng `SeparateDatabaseAndState`, hoặc reset DB và seed lại. Viết helper fixture tạo văn bản test.
- **Bên chốt:** Trưởng nhóm 5 (quy ước); thành viên Nhóm 5 (thực hiện).

#### DL-04 · Thấp · Vòng đời manifest chưa định nghĩa; `create_by` bắt buộc dù tác vụ nền tạo; nội dung thiếu khóa công khai
- **Mô tả:** Manifest chỉ được nhắc ở dòng 197 và Pha 3; plan không nói tạo khi nào. Bảng không có unique theo lượt nên lưu được nhiều bản `DA_CHOT`, và bản `DA_CHOT` lưu được với `thoi_diem_chot` rỗng. `create_by` NOT NULL trong khi tác vụ nền không có người dùng. `noi_dung_chuan_hoa` có vân tay khóa nhưng không có khóa công khai, nên tiêu chí dòng 729 ("kiểm tra độc lập được") còn phụ thuộc bảng khóa.
- **Bằng chứng:** plan.md dòng 102-104, 152, 197, 424-437, 604, 674, 729; models.py@1a6fcc9 dòng 440-460. KT: 2 manifest `DA_CHOT` trên một lượt, `thoi_diem_chot` rỗng.
- **Đề xuất (chờ Trưởng nhóm 5 chốt):** tạo và chốt manifest đồng bộ trong cùng transaction chuyển lượt sang `HOAN_THANH`, `create_by` là người ký cuối; unique (`luot_trinh`, `phien_ban_bang_chung`) và CHECK `thoi_diem_chot`; nội dung chứa khóa công khai; M2 thêm `POST /signing/attempts/{id}/xac-minh` và nút "Xác minh lại".
- **Bên chốt:** Trưởng nhóm 5.

#### DL-05 · Thấp · Chi tiết kỹ thuật model: CHECK REGEXP trên SQLite chỉ chạy qua kết nối Django; `Meta.ordering` theo FK sinh JOIN tới 3 bảng; header SQL ghi "sinh tự động" nhưng COMMENT ON viết tay
- **Mô tả:** CHECK dùng `__regex` thành REGEXP trên SQLite, hàm này chỉ Django đăng ký; ghi thẳng bằng sqlite3 (CLI, DB Browser, script seed) báo `unknown function: REGEXP()`. Ordering của bảng người ký theo `buoc_ky` kéo theo ordering bảng cha, mọi truy vấn JOIN tới `signing_request`; `select_for_update` trên PostgreSQL sẽ khóa cả dòng bảng cha. Tệp SQL ghi "không sửa tay" nhưng model không có `db_comment`, nên 191 dòng COMMENT ON là viết tay.
- **Bằng chứng:** models.py@1a6fcc9 dòng 19, 273, 276, 305, 346, 425, 458; signing_nhom5_postgresql.sql@1a6fcc9 dòng 3 và 191 dòng COMMENT ON từ dòng 393; `grep db_comment` trên models.py: 0 kết quả. KT: INSERT bằng sqlite3 vào `signing_attempt` → `OperationalError: unknown function: REGEXP()`; SQL của `signer.all()` có 3 JOIN, ORDER BY bắt đầu bằng `signing_request.created_at`.
- **Đề xuất (chờ Trưởng nhóm 5 chốt):** đổi CHECK sang `Length()=64`, kiểm hex ở validator (hoặc ghi rõ chỉ ghi qua ORM); ordering theo cột `*_id` hoặc bỏ ở bảng con; dùng `select_for_update(of=('self',))`; sửa header SQL hoặc chuyển chú thích thành `db_comment`.
- **Bên chốt:** thành viên Nhóm 5 (code); Trưởng nhóm 5 (review).

#### DL-06 · Thấp · Chữ ký đã thu hồi không có dấu hiệu trên chính bản ghi; quy tắc bất biến chặn việc bổ sung về sau
- **Mô tả:** Theo dòng 152, 157, 377, thu hồi chỉ là sự kiện nhật ký cộng với đưa `chu_ky_hien_hanh` về rỗng; bản ghi chữ ký cũ vẫn mang `trang_thai_xac_minh=HOP_LE`. API lịch sử, stepper và manifest (dòng 431 có "trạng thái") dễ hiển thị chữ ký đã thu hồi như còn hiệu lực, nhất là sau ủy quyền (LUONG-06). Model chỉ cho cập nhật hai field xác minh.
- **Bằng chứng:** plan.md dòng 102, 152, 154, 157, 377, 431; models.py@1a6fcc9 dòng 398, 413-415, 429-434. KT (mô phỏng): ký → thu hồi → ký lại, hai chữ ký cùng dòng đều `HOP_LE`; `save(update_fields=['ghi_chu_ky'])` trên chữ ký cũ → BatBienError.
- **Đề xuất (chờ Trưởng nhóm 5 chốt):** chọn một: thêm `thoi_diem_thu_hoi` (nullable, chỉ gán một lần) vào danh sách field được phép cập nhật; hoặc serializer luôn trả cờ `da_thu_hoi` (chữ ký khác `chu_ky_hien_hanh`) và manifest chỉ lấy chữ ký hiện hành. Thêm test.
- **Bên chốt:** Trưởng nhóm 5 (chốt); thành viên Nhóm 5 (code).

#### DL-07 · Thấp · Trường `dang_ap_dung` của cấp quy trình không có quy tắc sử dụng
- **Mô tả:** `signing_process_step.dang_ap_dung` (bắt buộc, mặc định True) chỉ xuất hiện trong bảng ở dòng 254. Không có quy tắc nào nói cấp tắt thì bị bỏ qua khi gửi, có tính vào điều kiện "quy trình không có cấp" (dòng 513) không, hay ai được bật tắt khi quy trình đã kích hoạt (dòng 70 cấm sửa).
- **Bằng chứng:** `grep dang_ap_dung` trên plan.md: chỉ dòng 254; spec.md không nhắc; models.py@1a6fcc9 dòng 162; plan.md dòng 70, 84-85, 513.
- **Đề xuất (chờ Trưởng nhóm 5 chốt):** bỏ trường (quy trình đã có phiên bản), hoặc ghi rõ: cấp tắt bị bỏ qua khi gửi; chỉ sửa được khi quy trình còn `NHAP`; phải có ít nhất một cấp đang áp dụng mới kích hoạt được.
- **Bên chốt:** Trưởng nhóm 5.

#### DL-08 · Thấp · Snapshot người ký không giữ liên kết tới dòng cấu hình `signing_process_step_signer`
- **Mô tả:** `signing_request_step` có FK `buoc_quy_trinh`, nhưng `signing_request_step_signer` không liên kết về dòng cấu hình đã sinh ra nó và không ghi nguồn chỉ định (tài khoản hay chức vụ). Hệ quả: không có khóa ổn định để gắn vị trí ký trước khi gửi (LUONG-02 phương án B); lượt mới không biết dòng nào cần resolve lại (LUONG-09); nhật ký không truy được chức vụ lúc gửi resolve ra ai.
- **Bằng chứng:** plan.md dòng 260-273, 335, 348-377; models.py@1a6fcc9 dòng 288 (cấp snapshot có `buoc_quy_trinh`), 311-352 (dòng người ký không có liên kết tương ứng). KT: lọc field của `SigningRequestStepSigner` chứa "quy_trinh" hoặc tên `thu_tu` → rỗng.
- **Đề xuất (chờ Trưởng nhóm 5 chốt):** thêm `cau_hinh_nguoi_ky` = FK(`signing_process_step_signer`, PROTECT, null=True; rỗng cho dòng sinh do ủy quyền) và `nguon_chi_dinh` [`TAI_KHOAN`, `CHUC_VU`]; làm cùng lúc với chụp `thu_tu` (LUONG-13), trước khi `0001` lên staging.
- **Bên chốt:** Trưởng nhóm 5 (chốt); thành viên Nhóm 5 (code).

### 8.3. Phân pha và nghiệm thu (PHA)

#### PHA-01 · Nghiêm trọng · Lịch pha chỉ xếp backend lõi: API danh sách, chi tiết, giao diện, trang khóa, seed và PR staging không thuộc pha nào; thông báo (G5) ở Pha 5; có phụ thuộc cứng ngược chiều
- **Mô tả:** Mục 10 không giao cho pha nào: API đã có ở mục 7 (danh sách, chi tiết, nhật ký), 3 trang ở spec mục 4, trang khóa ký, seed demo và PR lên staging. Vì vậy G2, G3, G4 và mọi thứ hiện ra khi demo đều không có lịch. Thông báo kèm mail (G5) nằm ở Pha 5 (dòng 687), trong khi sự kiện "đến lượt ký" phát sinh ngay ở Pha 2–3. "Từ chối" nằm ở Pha 4 (dòng 681). Điểm này chỉ chạm bộ trạng thái của đề md dòng 301; ô E14 chỉ đòi lọc "chờ ký". Có phụ thuộc cứng và mềm giữa các pha (mục 5.1). Plan không có ngày, người phụ trách hay mốc tích hợp.
- **Bằng chứng:** plan.md dòng 1 ("Plan backend"); mục 10 (dòng 647-698). `sed -n 647,698p | grep -iE 'danh sách|lọc|tìm kiếm|frontend|UI|giao diện|trang'` ra rỗng. API ở mục 7 không thuộc pha: dòng 579, 581, 603. Phụ thuộc cứng: dòng 666, 668 so với 673-674; 198, 202, 207 so với 687; 33, 197, 638, 672, 682; 679. `git ls-tree origin/5_signing_workflow docs/modules/05_signing_workflow`: chỉ có plan và spec. spec.md dòng 115-129: 3 trang, không có trang khóa ký. xlsx ô A1 (2 tuần một báo cáo); đề md dòng 301, 304. `git diff --numstat origin/staging origin/feat/5-signing-workflow`: frontend +4691, backend +3649 dòng.
- **Đề xuất (chờ Trưởng nhóm 5 chốt):**
  - Thêm luồng Frontend (F1–F3) và mục "Tích hợp – demo" (seed, admin, kịch bản, PR) vào mục 10.
  - Đưa vào Pha 2: API danh sách (lọc `trang_thai`, `q`, `don_vi`, `muc_do`, khoảng ngày) và chi tiết; lõi `ghi_nhan_da_ky`; helper tạo thông báo "đến lượt" kèm email gửi sau `on_commit`; tính `han_xu_ly` khi mở cấp.
  - Đưa `tu_choi`, `huy` lên trước yêu cầu sửa và ủy quyền. Ghi `ky_tre_han` chỉ ở Pha 3.
  - Thay Redis/Celery bằng phương án không cần hạ tầng ở MVP (HT-02).
  - Mỗi mốc kết thúc bằng PR lên staging qua 5 lệnh Quality Gate; gắn ngày theo chu kỳ 2 tuần.
- **Bên chốt:** Trưởng nhóm 5.

#### PHA-02 · Cao · Gom đủ 6 gạch E14 vào một mốc MVP thì vượt một kỳ 2 tuần; phần khóa ký chưa có người nhận; chưa có mốc an toàn; tài sản `approvals` chưa được dùng làm mốc
- **Mô tả:** Khi sửa PHA-01 bằng cách gom đủ 6 gạch E14 vào một mốc, mốc đó gồm Pha 1-min, Pha 2-core, 3a, 3b, 4a, 5a, F1–F3, seed và PR. Ước lượng cho riêng thành viên Nhóm 5 đã là 10–14 ngày công (suy luận theo khối lượng code `approvals`, chưa kiểm chứng), vượt 10 ngày làm việc của một kỳ. Phần 3a (quản lý khóa) là điều kiện bắt buộc của G6, nhưng chưa có người nhận cụ thể. App `approvals` hiện đáp ứng G1–G5; G6 chỉ ở dạng HMAC (BM-09). App qua đủ 5 lệnh Quality Gate và fast-forward được lên staging. Tái dùng các trang `approvals` cho `signing` là chuyển đổi chứ không phải chép: frontend dùng contract `/api/approvals/` với tên trường như `status`, `urgency` và mô hình round/step_type, còn plan dùng tên field tiếng Việt và mô hình lượt/cấp/người ký. Nếu M1 trễ, kỳ báo cáo kế tiếp Nhóm 5 không có gì trên staging (`/approvals` vẫn là `SyllabusPreview`).
- **Bằng chứng:** `git rev-list --left-right --count origin/staging...origin/feat/5-signing-workflow` → `0 2`. KT trên bản export `feat/5-signing-workflow`: `check` sạch; `makemigrations --check` No changes; `manage.py test` 52 OK (approvals 38); `pnpm test` trên Node 22.22.0 50 test pass (approvals 10); `pnpm lint` 0 lỗi; `pnpm build` OK. approvals/views.py:201-241 (lọc tab việc cần ký, trạng thái, độ khẩn, phòng ban, tìm theo mã hoặc trích yếu, ngày, quá hạn); models.py:113-120; services.py:180-210 (gửi mail trong `on_commit`); lệnh `send_signing_reminders`. types/approval.ts:1 (`/api/approvals/`, enum khác plan); plan.md dòng 565, spec.md dòng 79 (payload theo tên field CSDL); router.tsx:84@staging.
- **Đề xuất (chờ Trưởng nhóm 5 chốt), chọn một hướng:**
  - (a) Thêm mốc M0 (1–3 ngày): sửa nhỏ `approvals` (email, nhãn HMAC, chặn xóa trong admin) rồi PR lên staging làm bản an toàn; M1 thay phần ký bằng Ed25519 và chuyển dần sang lược đồ `signing`.
  - (b) Giữ `signing` là đích nhưng tách M1 thành M1a và M1b, mỗi phần một kỳ (mục 6.4). Ghi 3a là việc bắt buộc có người nhận cụ thể. `approvals` giữ ở nhánh riêng, có kịch bản demo dự phòng.
  - Cả hai hướng: mỗi mốc kết thúc bằng PR qua 5 lệnh Quality Gate.
- **Bên chốt:** Trưởng nhóm 5.

#### PHA-03 · Cao · Lịch pha không có bước trình Giảng viên duyệt danh sách trường và phạm vi trước khi làm schema
- **Mô tả:** Ô E14 mở đầu bằng yêu cầu nhóm gặp Giảng viên để trao đổi; ô F14 yêu cầu nhóm chọn trường rồi báo Giảng viên duyệt; đề md dòng 306-307 nhắc lại. Pha 0 (dòng 649-654) không có bước trình Giảng viên; plan và spec không nhắc Giảng viên lần nào. Lược đồ 14 bảng (191 dòng field ở mục 5.2) đã được code, nhưng repo không có ghi nhận phê duyệt. Phạm vi MVP ở mục 1.2 rộng hơn 6 gạch đề. Rủi ro làm lại có tiền lệ: Nhóm 6 đã phải thêm migration `0002` sau khi cập nhật nghiệp vụ theo góp ý Giảng viên.
- **Bằng chứng:** xlsx ô E14 (dòng đầu), F14; đề md dòng 299, 306-307; plan.md dòng 13-29, 649-654. Tìm từ khóa chỉ Giảng viên trên plan.md, spec.md và `docs/modules/05_signing_workflow` ở bốn nhánh `5_signing_workflow`, `feat/5-signing-workflow`, `feat/signing-models`, `staging`: không có kết quả. Commit b8f6986 trên `origin/6_tasks` (cập nhật nghiệp vụ theo góp ý Giảng viên, kèm migration `0002`).
- **Đề xuất (chờ Trưởng nhóm 5 chốt):**
  - Thêm vào Pha 0 bước "trình Giảng viên", làm trước mọi PR schema lên staging. Nội dung trình: bảng "gạch E14 → tính năng → bảng/trường chính → mốc"; danh sách trường rút gọn của các bảng người dùng nhìn thấy; danh sách phần ngoài đề đề xuất dời sang M2/M3.
  - Ghi kết quả duyệt vào `docs/modules/05_signing_workflow`. Mọi chỉnh sửa sau buổi duyệt gộp vào `0001` thay vì sinh `0002`.
- **Bên chốt:** Trưởng nhóm 5 (trình); Giảng viên (duyệt).

#### PHA-04 · Trung bình · Plan không có dữ liệu mẫu (seed) và trang admin để demo
- **Mô tả:** Plan và spec không có lệnh seed, fixture hay `admin.py`; app `signing` cũng chưa có. Muốn demo một lượt ký cần tài khoản có hồ sơ cán bộ, quy trình nhiều cấp có ký nháy chặn, khóa Ed25519 đã kích hoạt cho từng người ký và tệp PDF; dựng lại bằng tay sau mỗi lần reset DB tốn nhiều thao tác. `approvals` đã có `seed_signing_demo` (mật khẩu qua tham số, tạo tài khoản có `StaffProfile`, hồ sơ đi qua tầng service) và `admin.py` để làm khung.
- **Bằng chứng:** `grep -niE 'seed|fixture|demo|admin\.py|django admin'` trên plan.md, spec.md: rỗng. `git diff --stat origin/5_signing_workflow origin/feat/signing-models`: app chỉ có `__init__.py`, `apps.py`, `migrations/0001_initial.py`, `models.py`, `tests.py`. `seed_signing_demo.py` (241 dòng, tham số `--password`, `--reset`) và `admin.py` (98 dòng)@feat/5-signing-workflow. `git check-ignore -v` với `.gitignore`@staging: `migrations/*seed*.py` bị bỏ qua (dòng 52); `management/commands/seed_signing_demo.py` không bị bỏ qua.
- **Đề xuất (chờ Trưởng nhóm 5 chốt):** lệnh `seed_signing_demo` trong `management/commands`, chép khung từ `approvals`: 4–5 tài khoản có hồ sơ và email, 2 quy trình (`TUAN_TU`; `SONG_SONG` có ký nháy chặn), 1–2 hồ sơ ở các trạng thái khác nhau; mật khẩu lấy từ tham số hoặc `.env`. `admin.py`: quy trình sửa được; chữ ký, nhật ký, manifest chỉ đọc. Bước đăng ký khóa cho từng tài khoản demo ghi vào checklist (BM-02).
- **Bên chốt:** Trưởng nhóm 5.

#### PHA-05 · Trung bình · Tiêu chí nghiệm thu (mục 11) và DoD (mục 13) không bám 6 gạch E14, không chia theo mốc; DoD không có 5 lệnh Quality Gate và phần frontend
- **Mô tả:** Mục 11 có tiêu chí cho máy trạng thái, toàn vẹn dữ liệu, mật mã, hạn xử lý, nhưng không có tiêu chí cho G1 (mức độ, thông tin người tạo), G2 (lọc chờ ký), G3 (tìm kiếm, lọc phòng ban), G4 (sơ đồ ký); G5 chỉ có nhắc hạn. Dòng 715 là tiêu chí giao diện dù plan không có pha frontend. DoD (dòng 764-771) là một khối chung, đòi cả phẳng hóa, ủy quyền, xoay vòng khóa, outbox, nên khi xếp theo mốc MVP thì không mốc nào đạt. DoD và khối lệnh dòng 744-748 không có `pnpm test/lint/build`; spec dòng 141-144 là bộ lệnh thứ ba.
- **Bằng chứng:** `sed -n 700,771p plan.md | grep -niE 'mức độ|người tạo|danh sách|lọc|tìm kiếm|phòng|sơ đồ|stepper|đến lượt|thông báo|email|mail'`: chỉ ra dòng 706 và tiêu đề dòng 733. plan.md dòng 715, 736, 764-771; `grep -nE 'pnpm|lint|vitest|build'`: chỉ dòng 696, 750. spec.md dòng 141-144. QUALITY_GATE_STAGING.md:22-53@staging (5 lệnh bắt buộc).
- **Đề xuất (chờ Trưởng nhóm 5 chốt):** thêm vào mục 11 bảng "gạch E14 → tiêu chí kiểm được → test hoặc bước demo". Ví dụ: tab việc cần ký chỉ trả hồ sơ có dòng người ký của người dùng hiện tại đang `CHO_KY` và có `thoi_diem_mo`; mở cấp thì tạo một thông báo in-app và một email. Tách DoD theo mốc (DoD-M1 gồm luồng chính, từ chối/hủy, thông báo đến lượt, Ed25519; phẳng hóa, xoay vòng, outbox sang M2/M3). Mọi DoD có đủ 5 lệnh Quality Gate; thống nhất khối lệnh plan và spec theo QUALITY_GATE_STAGING.md.
- **Bên chốt:** Trưởng nhóm 5.

#### PHA-06 · Thấp · Các điểm còn mở (mục 12) không có người chốt, hạn hay pha nhận; hai quyết định bị dời tới lúc "làm PDF viewer" và "làm stamping" trong khi Pha 2–3 đã ghi dữ liệu phụ thuộc
- **Mô tả:** Mục 12 (dòng 752-760) có 7 điểm mở, không ghi người chốt, hạn hay pha bị chặn. Hệ tọa độ khung ký để "chốt khi làm PDF viewer" (dòng 95), mà PDF viewer không thuộc pha nào, trong khi API tạo yêu cầu đã nhận vị trí ký (dòng 580) và Pha 2 snapshot vị trí (dòng 665). Kích thước ảnh để "chốt khi làm stamping" (dòng 135, Pha 5), trong khi Pha 3 đã snapshot ảnh lúc ký (dòng 674).
- **Bằng chứng:** plan.md dòng 95, 135, 580, 665, 674, 752-760; `sed -n 647,698p plan.md | grep -iE 'viewer|giao diện'` ra rỗng; spec.md dòng 29, 125.
- **Đề xuất (chờ Trưởng nhóm 5 chốt):** thêm cột "người chốt / hạn / pha bị chặn" cho mục 12. Chốt ngay ở Pha 0: tọa độ theo tỷ lệ % trong [0,100], gốc góc trên-trái của trang, cho phép rỗng trong M1; ảnh PNG tối đa 2MB, chưa ép kích thước pixel cho tới M2/M3.
- **Bên chốt:** Trưởng nhóm 5.

### 8.4. Tích hợp Nhóm 2 (TH2)

#### TH2-01 · Cao · FK `van_ban` bắt buộc tới văn bản Nhóm 2 nhưng plan chưa nói dự thảo lưu ở đâu; không loại văn bản nào của Nhóm 2 dùng làm dự thảo mà không có nhược điểm; lệch spec dòng 124 và structure.md
- **Mô tả:** Plan dòng 280 đặt `van_ban` là FK bắt buộc tới `documents_vanban` (bảng thật là `documents_document`); dòng 580 tạo NHAP "từ văn bản". Spec dòng 124 lại cho đính kèm tài liệu ở trang tạo; structure.md dòng 208, 359 dành `05_signing/documents/` cho tệp trình ký; spec không nhắc Nhóm 2. Phía Nhóm 2, mọi loại văn bản bắt buộc `so_hieu`: DEN/DI được cấp số thứ tự ngay lúc tạo (DI còn bắt buộc `ngay_ban_hanh`); MAT không cấp số nhưng chỉ người tạo và `nguoi_nhan` xem được; `hien_thi=False` không ẩn văn bản khỏi danh sách. Dùng văn bản Nhóm 2 làm dự thảo thì hoặc chiếm số trong sổ, hoặc vướng ACL mật. Văn bản Nhóm 2 có nhiều tệp, không kiểm định dạng, không có phiên bản hay mã băm; PUT/PATCH/DELETE chỉ chặn với MAT, trái README Nhóm 2 dòng 48-49. Plan không nói ký tệp nào khi có nhiều tệp. Plan dòng 60, 754 chỉ treo câu hỏi "một bảng hay ba bảng"; code Nhóm 2 đã trả lời là một bảng, còn câu hỏi thật (dự thảo lưu ở đâu) chưa có. Quyết định này chặn migration đầu tiên và gạch G1.
- **Bằng chứng:** plan.md dòng 51, 60, 191, 280, 509, 580, 754; spec.md dòng 124 (`grep 'van_ban|Nhóm 2|văn bản đi|documents'` trên spec.md: 0 kết quả); structure.md:208, 359@staging. 2_documents@18cff9e: models.py:50-53, 71-76, 127-131, 208-221; serializers.py:157, 168-175; views.py:78-101, 118-133, 138-165; README.md:13, 48-49. KT trên bản export `2_documents`: POST DI thiếu `so_hieu` → 400; thiếu `ngay_ban_hanh` → 400; đủ trường → 201, số thứ tự 1. Tài khoản thứ hai vẫn thấy văn bản `hien_thi=False` trong danh sách. Tài khoản thứ hai PATCH văn bản DI của người khác kèm tệp `.exe` → 200; DELETE → 204. models.py:211@1a6fcc9 (`van_ban_id` BigInteger bắt buộc); approvals/models.py:28-33, 178-199@feat/5-signing-workflow (tự lưu tệp tại `05_signing/documents`).
- **Đề xuất (chờ Trưởng nhóm 5 chốt) – phương án A:**
  - Người tạo upload PDF dự thảo vào Nhóm 5; lưu theo từng lượt tại `MEDIA_ROOT/05_signing/documents/<năm>/<tháng>/<uuid>.pdf` (đúng structure.md dòng 359); server tự tính SHA-256.
  - `signing_request.van_ban` = FK(`documents.Document`, null=True), chỉ gán khi phát hành hoặc khi người tạo chủ động liên kết văn bản có sẵn; khi liên kết thì chọn đúng một tệp PDF và sao bytes sang kho Nhóm 5.
  - Sửa plan dòng 60, 280, 509, 580, 754 cho khớp spec dòng 124.
  - Nhóm 2 chưa có frontend, nên nếu giữ lựa chọn "liên kết văn bản có sẵn" thì Nhóm 5 tự làm ô chọn gọi `/api/documents/`.
  - Nhóm 2 kiểm quyền PUT/PATCH/DELETE cho mọi loại văn bản như README.
- **Bên chốt:** Trưởng nhóm 5 và Nhóm 2.

#### TH2-02 · Thấp · Khâu phát hành không nối về văn bản đi của Nhóm 2; spec hứa CA/HSM/PAdES vượt MVP; chatbot mô tả ký Token PKI/Cloud HSM và tự sinh số văn bản đi
- **Mô tả:** Không pha nào tạo hay cập nhật văn bản đi sau `HOAN_THANH`. `/phat-hanh` chỉ mở khi đã có tệp hoàn tất (do `PdfStampingService` Pha 5 sinh); `LegalSignerAdapter` chỉ là interface. Spec dòng 96, 129 vẫn có endpoint và nút "Phát hành văn bản" cho lãnh đạo/văn thư, trong khi `StaffProfile` chỉ có vai trò admin/staff. Văn bản đi theo đề bắt buộc Hồ sơ và Loại văn bản (Nhóm 3; Nhóm 2 còn TODO). Chatbot mô tả ký bằng Token PKI/Cloud HSM qua OTP và tự sinh số hiệu văn bản đi. Đề Nhóm 5 không bắt buộc liên thông sang văn bản đi; rủi ro chủ yếu là mâu thuẫn khi demo.
- **Bằng chứng:** plan.md dòng 49-52, 585, 649-698 (mục 10 chỉ dòng 652 nhắc Nhóm 2; dòng 690 là interface); spec.md dòng 96, 129; accounts/models.py:11-14@staging; FloatingAIBox.tsx:80, AiAssistantPage.tsx:54, 224@staging; AiAssistantPage.tsx:87, 687@8_ai_chatbox; documents/models.py:137-143@2_documents; xlsx ô F7.
- **Đề xuất (chờ Trưởng nhóm 5 chốt):** M1 ẩn nút và endpoint phát hành, ghi "ngoài MVP" ở spec mục 1.2.8 và dòng 96. Nếu làm sau khi `2_documents` lên staging: service phát hành gọi hàm tạo văn bản đi của Nhóm 2 với `so_hieu` do người phát hành nhập, `ngay_ban_hanh`, người ký và chức vụ từ snapshot `KY_CHINH` cấp cuối, trích yếu, tệp hoàn tất (hoặc tệp gốc), Hồ sơ chung của Nhóm 3; rồi gán ngược `van_ban`. Nhãn UI: "Chữ ký số nội bộ (Ed25519)". Gửi Nhóm 1 và Nhóm 8 đoạn mô tả đúng luồng.
- **Bên chốt:** Trưởng nhóm 5 (phạm vi); Nhóm 2 (hàm tạo văn bản đi); Nhóm 1, Nhóm 8 (nội dung chatbot).

#### TH2-03 · Thấp · Điểm nhỏ phía Nhóm 2: số thứ tự có thể trùng; năm mặc định đóng cứng 2026 làm `makemigrations --check` lỗi từ 2027; settings DRF toàn cục đổi hành vi view generic
- **Mô tả:** `generate_so_thu_tu` lấy MAX trong transaction riêng, đóng trước khi lưu văn bản; Django bỏ FOR UPDATE ở truy vấn aggregate; không có `UniqueConstraint(loai, nam, so_thu_tu)`. `Document.nam` dùng `default=timezone.now().year` nên `0001` chứa sẵn 2026; nếu nghiệm thu sau 31/12/2026 thì chạm Quality Gate. Settings Nhóm 2 bật phân trang 10 và `SessionAuthentication` cho mọi view: view generic viết sau của Nhóm 5 bị phân trang nếu không khai báo riêng; request không có Bearer nhưng mang cookie phiên quản trị cùng host bị 403 CSRF, kể cả đăng nhập. App `approvals` hiện không bị ảnh hưởng.
- **Bằng chứng:** 2_documents: services.py:46-55, views.py:118-133, models.py:44-49, 167-176, migrations/0001_initial.py:22, settings.py:169-185. Django 5.2.17 `django/db/models/sql/query.py:625`. KT: giả lập năm 2027 thì `makemigrations --check --dry-run documents` sinh `0003_alter_document_nam`, exit 1; cookie phiên không Bearer POST `/api/documents/` → 403 CSRF; POST `/api/auth/login/` kèm cookie phiên → 403, không cookie → 200. KT ghép `feat/5-signing-workflow` + `2_documents`: conflict `settings.py`, `urls.py`; giữ cả hai bên thì `test approvals documents` 65 OK.
- **Đề xuất (chờ Trưởng nhóm 5 chốt):** Nhóm 2 thêm `UniqueConstraint(loai, nam, so_thu_tu)`, cấp số trong cùng transaction lưu (hoặc bắt IntegrityError rồi thử lại), đổi default `nam` sang callable bằng migration mới. Nhóm 5 khai báo tường minh `pagination_class` và `authentication_classes` cho view generic. Trưởng nhóm 5 khi review đề nghị bỏ `SessionAuthentication` khỏi mặc định.
- **Bên chốt:** Nhóm 2 (constraint, default năm); thành viên Nhóm 5 (khai báo view); Trưởng nhóm 5 (review settings).

#### TH2-04 · Thấp · Trường `loai` sửa được sau khi tạo: chuyển sổ vẫn giữ số cũ, văn bản thường bị người khác chuyển thành MẬT, văn bản MẬT bị chuyển thành công khai
- **Mô tả:** `DocumentCreateUpdateSerializer` để `loai`, `nam` ghi được khi PUT/PATCH; `perform_update` không cấp lại số và không chặn đổi loại. Đề coi loại sổ là trang Đến/Đi/Mật và cho sửa mọi trường trừ số đến/số đi. Với Nhóm 5, mọi cách liên kết văn bản Nhóm 2 đều có thể lệch sau khi liên kết (FK `van_ban`, cờ mật snapshot theo BM-05, văn bản đi lúc phát hành theo TH2-02).
- **Bằng chứng:** serializers.py:126-157, views.py:138-152@2_documents; xlsx ô E6, E7, F6-F8. KT: tài khoản không phải người tạo đổi văn bản DI sang DEN → 200, sổ đến có hai văn bản cùng số thứ tự; đổi DI của người khác sang MAT → 200, văn bản biến mất với tài khoản khác; người tạo đổi MAT sang DEN → 200, tài khoản ngoài `nguoi_nhan` xem được.
- **Đề xuất (chờ Trưởng nhóm 5 chốt):** Nhóm 2 khóa `loai` khi cập nhật (read_only hoặc ValidationError khi khác giá trị cũ); nếu cho đổi `nam` thì cấp lại số. Nhóm 5 snapshot `loai`, `so_hieu`, `so_thu_tu` khi liên kết, kiểm lại `loai` khi gửi, ủy quyền, phát hành. Đưa ca này vào checklist review PR của Nhóm 2.
- **Bên chốt:** Nhóm 2 (serializer); Trưởng nhóm 5 (quy tắc snapshot, checklist review).

#### TH2-05 · Thấp · README module Nhóm 2 lệch code ở các điểm Nhóm 5 cần để chốt contract
- **Mô tả:** Plan Nhóm 5 dòng 60, 509, 652, 754 chờ Nhóm 2 "thống nhất" model văn bản; tài liệu Nhóm 2 công bố là `docs/modules/02_documents/README.md`, nhưng README khác code: `ho_so`, `loai_van_ban`, `don_vi_nhan` ghi là đã có (code còn TODO); `chuc_vu_nguoi_ky` (code: `chuc_vu`); `THAY_THE` (code: `HET_VA_THAY_THE`); PUT/PATCH/DELETE chỉ cho người tạo/Admin (code chỉ chặn MAT); 23/23 test (thực tế 27).
- **Bằng chứng:** README.md:13, 21-24, 32, 48-49, 87@2_documents; models.py:30-33, 98-103, 137-143, views.py:138-165@2_documents; KT `manage.py test documents`: 27 OK; plan.md dòng 60, 504-509, 652, 754.
- **Đề xuất (chờ Trưởng nhóm 5 chốt):** chốt contract theo code nhánh `2_documents` tại commit cụ thể (hiện là 18cff9e), không theo README. Bảng phụ thuộc (dòng 504-509) ghi đúng `documents_document` và field thật (`id`, `loai`, `so_hieu`, `so_thu_tu`, `trich_yeu`, `nguoi_ky`, `chuc_vu`, `nguoi_nhan`, `attachments`). Nhóm 2 cập nhật README hoặc tách phần "dự kiến".
- **Bên chốt:** Trưởng nhóm 5 và Nhóm 2.

### 8.5. Tích hợp Nhóm 7 (TH7)

#### TH7-01 · Trung bình · Kế hoạch đổi `AUTH_USER_MODEL` sang `accounts.Employee`: thêm bằng migration `0002` thì migrate DB mới hỏng; cách khả thi buộc cả lớp xóa DB và sửa test import cứng `auth.User`
- **Mô tả:** Phân công Nhóm 7 dự kiến tạo `accounts.Employee` rồi đổi `AUTH_USER_MODEL`, trong khi `accounts` đã có `0001` (StaffProfile). Thêm Employee bằng `0002` thì migrate DB mới dừng ở `accounts.0001`; DB cũ báo lazy reference ở `signing.*` và `token_blacklist`. Cách khả thi là tạo lại `accounts/0001`: DB mới migrate được, test signing vẫn qua; nhưng DB cũ báo "No migrations to apply" rồi lỗi thiếu bảng khi chạy, và test accounts/organizations lỗi vì import cứng `auth.User`. Code signing đã dùng `settings.AUTH_USER_MODEL` và `get_user_model`. Nhóm 8 đã viết SQL thô trên `accounts_employee`.
- **Bằng chứng:** phan-cong-nhom7.md:62, 64, 71@7_meeting_rooms_birthdays_system; accounts/models.py:2, 16-21, admin.py:40, views.py:83@staging; models.py:18@1a6fcc9 (12 FK PROTECT); seed_signing_demo.py:17, approvals/tests.py:13@feat/5-signing-workflow; sql_document_source.py:34-35, 102-104@8_ai_chatbox; plan.md dòng 59 so với nhãn "ForeignKey (auth_user)" ở dòng 236, 266, 297. KT (nhánh Nhóm 7 + app signing): Employee ở `0002` → `ValueError: Related model accounts.employee cannot be resolved`; tạo lại `0001` → DB mới OK, `test signing` 19 OK, `test accounts organizations` 27 lỗi "auth.User has been swapped", DB cũ `no such table: accounts_employee`.
- **Đề xuất (chờ Trưởng nhóm 5 chốt):** nêu với PM và Nhóm 7 sớm, kèm kết quả trên. Phương án ưu tiên: không đổi `AUTH_USER_MODEL`; CBNV là hồ sơ OneToOne tới `settings.AUTH_USER_MODEL`; nhóm quyền dùng `user.groups`; Nhóm 8 đổi truy vấn. Nếu PM chọn đổi: đổi một lần trước ngày cố định, Employee nằm trong `0001`, mọi nhánh xóa `db.sqlite3` rồi seed, đổi import cứng sang `get_user_model()`. Phía Nhóm 5: sửa `seed_signing_demo.py:17`, `approvals/tests.py:13`, nhãn "ForeignKey (auth_user)" thành `AUTH_USER_MODEL`, ghi rủi ro vào mục 12.
- **Bên chốt:** PM và Nhóm 7 (quyết định); Trưởng nhóm 5 (nêu vấn đề); Nhóm 8 (liên đới).

#### TH7-02 · Trung bình · Ảnh chữ ký giao cho "Nhóm 7, sheet CBNV, field `anh_chu_ky`" nhưng đề, xlsx và phân công Nhóm 7 đều không có; trang hồ sơ cá nhân theo đề thuộc Nhóm 1 và chưa có API sửa
- **Mô tả:** Plan 3.4 (dòng 133-134), bảng phụ thuộc (508), 7.5 (612), mục 12 (756) và spec dòng 19, 111, 117 giao ảnh chữ ký cho Nhóm 7 và cấm Nhóm 5 tự làm API. Đề không có trường này (xlsx F20, đề md mục 7.5), xlsx không có sheet CBNV, phân công Nhóm 7 dòng 47 không nhận việc. Trang thông tin người dùng cá nhân theo đề thuộc Nhóm 1 (xlsx E4, đề md dòng 51); staging chỉ có GET `/api/auth/profile/`. structure.md đặt ảnh ở `media/05_signing/signatures`; nhánh `approvals` đã có `UserSignature`. Lõi ký không bị chặn (`vi_tri_anh_chu_ky` CharField blank=True); phần phụ thuộc là lớp phủ ảnh, `PdfStampingService` và tiêu chí dòng 715-716.
- **Bằng chứng:** plan.md dòng 97-100, 133-134, 418-419, 508, 612, 652, 715-716, 756; spec.md dòng 19-20, 111, 117; xlsx: danh sách sheet, ô F20, E4; đề md dòng 51, 398-427; phan-cong-nhom7.md:47; accounts/urls.py:8-23, ProfilePage.tsx:15-28@staging; structure.md:208, 359; `git grep 'anh_chu_ky|UserSignature'` mọi nhánh: chỉ `feat/5-signing-workflow` và `feat/signing-models`.
- **Đề xuất (chờ Trưởng nhóm 5 chốt):** (a, khuyến nghị) Nhóm 5 tự giữ ảnh chữ ký trong app trình ký với `upload_to='05_signing/signatures/'`, tái dùng `UserSignature` và trang ảnh chữ ký của `approvals`; sửa plan 3.4, bảng phụ thuộc, 7.5, mục 12 và spec dòng 19, 111, 117; đọc ảnh qua hàm adapter. (b) Chỉ chuyển sang contract `get_anh_chu_ky(user)` khi Nhóm 1 hoặc Nhóm 7 nhận việc bằng văn bản, có ngày. Cả hai: lúc ký sao bytes ảnh thành tệp snapshot riêng, tính sha256 trên bản sao; ảnh chỉ phục vụ qua API có kiểm quyền.
- **Bên chốt:** Trưởng nhóm 5 (thêm Nhóm 1 hoặc Nhóm 7 nếu chọn b).

#### TH7-03 · Trung bình · Người ký theo chức vụ chưa resolve được: Nhóm 7 chưa có ChucVu/CBNV; quy tắc resolve chưa định nghĩa; chưa có nguồn danh sách người dùng cho ô chọn người ký
- **Mô tả:** Plan đưa người ký theo chức vụ vào MVP (dòng 18) nhưng chỉ có quy tắc "không resolve được tài khoản đang hoạt động thì không cho gửi" (dòng 88, 514). Chưa định nghĩa: phạm vi resolve (`step.don_vi` không bắt buộc); nhiều người cùng chức vụ (ChucVu theo đề là danh mục phẳng; đề có 82 đơn vị cấp 2; dòng 34 loại kiểu "một trong nhiều người"); cờ "đang hoạt động" (ba ứng viên: `is_active`, `isPublic`, trạng thái Làm việc/Nghỉ việc). `StaffProfile.position` là chuỗi tự do, nên hiện mọi người ký theo chức vụ resolve ra 0 người. `signing_process_step_signer` chỉ có CHECK XOR, không có unique. Staging không có API danh sách người dùng; API đơn vị của Nhóm 7 không có tham số lấy toàn bộ và không lọc `is_public` (`max_page_size=100` đủ cho 82 đơn vị).
- **Bằng chứng:** plan.md dòng 18, 34, 88-89, 252, 267, 273, 513-514, 661, 710; đề md dòng 384-396, 410, 426, mục 4 (dòng 467-488, 82 đơn vị cấp 2, khớp sheet "đvi, phòngban"); models.py@1a6fcc9 dòng 160, 184, 196-203, 315, 348; accounts/models.py:32-37, urls.py:8-23@staging; organizations/views.py:18-21, 44-47, 109-135@7_meeting_rooms_birthdays_system; phan-cong-nhom7.md:60, 62; sql_document_source.py:44, 104@8_ai_chatbox; approvals/urls.py:11-13@feat/5-signing-workflow.
- **Đề xuất (chờ Trưởng nhóm 5 chốt):** (1) MVP chỉ hỗ trợ người ký theo tài khoản; người ký theo chức vụ giữ trong schema nhưng gửi bị trả mã lỗi `CHUA_HO_TRO_CHUC_VU` tới khi có ChucVu; tiêu chí dòng 661, 710 test bằng resolver giả. (2) Quy tắc khi có ChucVu: tìm trong `step.don_vi` (cấp không có đơn vị: `PHONG_BAN` lấy đơn vị người tạo, `CONG_TY` cấm kích hoạt); chỉ lấy `user.is_active`; 1 người thì snapshot, 0 người chặn gửi, hơn 1 người chặn với `CHUC_VU_NHIEU_NGUOI`; kiểm lúc kích hoạt và lúc gửi. (3) Partial unique cho (`buoc_quy_trinh`, `nguoi_ky`) và (`buoc_quy_trinh`, `chuc_vu_id`). (4) Gom truy cập dữ liệu tổ chức vào một module tích hợp; tạm có endpoint tra cứu người dùng (`q`, `don_vi`, tối đa 20 kết quả) hoặc tái dùng `users/` của `approvals`; xin Nhóm 7 thêm tham số lấy toàn bộ và lọc `is_public`.
- **Bên chốt:** Trưởng nhóm 5; Nhóm 7 (ChucVu, CBNV, cờ trạng thái).

#### TH7-04 · Trung bình · Xóa cứng tài khoản hoặc đơn vị va vào FK PROTECT: API trả 500 hoặc để lại ID mồ côi; endpoint ghi của Nhóm 7 chỉ cần đăng nhập
- **Mô tả:** Đề có thao tác "Xóa tài khoản" (mục 7.5) và xóa đơn vị (mục 7.3). Endpoint đơn vị gọi `unit.delete()` không bắt `ProtectedError` (endpoint khu vực thì bắt và trả 400). Mọi endpoint ghi chỉ kiểm `IsAuthenticated`. Khi còn cột BigInteger tạm, `step.don_vi_id` thành ID mồ côi; khi đổi sang FK PROTECT thì xóa đơn vị đang được tham chiếu trả 500. App signing có 12 FK PROTECT tới tài khoản, kể cả `notification.nguoi_nhan`, nên tài khoản từng nhận thông báo không xóa được; `perform_destroy` của Nhóm 2 cũng không bắt `ProtectedError`.
- **Bằng chứng:** organizations/views.py:36, 68, 110, 146, 90-106, 168-173@7_meeting_rooms_birthdays_system; models.py@1a6fcc9 dòng 135, 182, 231, 263, 314, 328, 364, 450, 484, 502, 524, 562; documents/views.py:154-165@2_documents; đề md dòng 370, 411. KT (nhánh Nhóm 7 + signing): tài khoản không có quyền gọi DELETE `/api/organizations/units/:id/` → 204, `step.don_vi_id` mồ côi; POST units → 201; xóa tài khoản đã nhận thông báo → ProtectedError; biến thể FK PROTECT → 500 text/html.
- **Đề xuất (chờ Trưởng nhóm 5 chốt):** Nhóm 7: "xóa tài khoản" là chuyển Nghỉ việc và `is_active=False`; xóa đơn vị hoặc chức vụ đang bị tham chiếu trả 409 (hoặc 400 kèm key i18n như endpoint khu vực); endpoint ghi kiểm `has_perm`. Nhóm 2: bắt `ProtectedError`, trả 409. Nhóm 5: `signing_notification.nguoi_nhan` đổi sang CASCADE, giữ PROTECT cho chữ ký, nhật ký, lượt, người tạo; khi còn BigInteger thì hiển thị "Đơn vị đã bị xóa".
- **Bên chốt:** Trưởng nhóm 5, Nhóm 7, Nhóm 2.

#### TH7-05 · Thấp · Hai nguồn hồ sơ cán bộ (`StaffProfile` của Nhóm 1, CBNV dự kiến của Nhóm 7); plan không nói snapshot tên và chức vụ lấy từ đâu
- **Mô tả:** Nhóm 7 định làm CBNV trong app `accounts`, cạnh `StaffProfile`, nên họ tên, đơn vị, chức vụ sẽ có hai nguồn; CBNV còn có Chức danh (chữ tự do) bên cạnh Chức vụ (FK). Plan dòng 89 yêu cầu snapshot tên và chức vụ nhưng không nói nguồn. Payload đăng nhập và `authService` tự điền giá trị mặc định cho đơn vị và chức vụ; `profile_info` của `approvals` đọc thẳng `StaffProfile` nên chưa dính.
- **Bằng chứng:** accounts/views.py:31-34, authService.ts:50-62@staging; structure.md:301-305; phan-cong-nhom7.md:47, 64; plan.md dòng 89, 356-357; approvals/services.py:83-99@feat/5-signing-workflow; sql_document_source.py:32-36@8_ai_chatbox.
- **Đề xuất (chờ Trưởng nhóm 5 chốt):** CBNV là nguồn sự thật, có hàm `thong_tin_can_bo(user)` trả họ tên, đơn vị, chức vụ, chức danh; Nhóm 5 snapshot qua module tích hợp, không lấy từ payload `/api/auth/profile/`; chốt có snapshot chức danh không và ghi nguồn vào dòng 89.
- **Bên chốt:** Nhóm 7 và Nhóm 1; Trưởng nhóm 5 ghi vào plan.

#### TH7-06 · Thấp · Plan chưa cập nhật dữ kiện đã có của Nhóm 7 và Nhóm 1; bảng "Phụ thuộc nhóm khác" chỉ có 2 dòng
- **Mô tả:** Dòng 61, 754, 755 vẫn để `[CHƯA XÁC MINH]` tên model đơn vị và cách map permission, trong khi Nhóm 7 đã merge `organizations.DonVi` vào nhánh nhóm ngày 2026-09-26, trước bản plan c1b9704 (2026-09-28), và đã dùng Permission chuẩn với `Meta.permissions` + `has_perm`. Bảng phụ thuộc (dòng 504-509) chỉ có `anh_chu_ky` và `van_ban`; không có DonVi, ChucVu, CBNV/danh sách người dùng, nhóm quyền/`is_admin`, chuông thông báo, payload profile, `apiClient`. FRONTEND_BASELINE_GUIDE quy định hợp đồng phân quyền do Nhóm 7 cung cấp, nhưng plan không có bước gửi danh sách quyền cho Nhóm 7.
- **Bằng chứng:** plan.md dòng 61, 504-509, 652, 754-756; organizations/models.py:45-106, views.py:24-32, 177@7_meeting_rooms_birthdays_system; git log: 54c6b9d ngày 2026-09-25, merge 33ea223 ngày 2026-09-26, c1b9704 ngày 2026-09-28; FRONTEND_BASELINE_GUIDE.md:38-41@staging; phan-cong-nhom7.md:52, 69-70.
- **Đề xuất (chờ Trưởng nhóm 5 chốt):** đóng dòng 61, 755 bằng dữ kiện thực tế (FK tới `organizations.DonVi` khi bỏ cột tạm; quyền dùng `django.contrib.auth`); mở rộng bảng phụ thuộc thành danh mục contract (nhóm, thứ cần, trạng thái, hạn, phương án tạm); gửi danh sách 11 quyền (TH1-01) cho Nhóm 7.
- **Bên chốt:** Trưởng nhóm 5.

### 8.6. Tích hợp Nhóm 1 – app shell (TH1)

#### TH1-01 · Trung bình · Phân quyền: 3 định nghĩa "admin" khác nhau; mục 8 thiếu quyền cho quản trị, kiểm toán, phát hành; chưa khai báo `Meta.permissions`; session frontend chỉ có role admin/staff
- **Mô tả:** Nhóm 1 dùng `is_superuser` hoặc `profile.role=='admin'` (`approvals` làm theo), Nhóm 2 dùng `is_staff`, Nhóm 6 dùng `is_superuser`. Mục 8 có 8 codename nhưng các hành động quản trị hủy thay, đổi hạn, ủy quyền thay (dòng 127, 170, 180), kiểm toán (579, 617) và phát hành (spec dòng 96) không có quyền riêng. App signing chưa khai báo `Meta.permissions`, nên chỉ có quyền tự sinh, gồm cả `delete_signingsignature`, `delete_signingauditlog`. Đề mục 7.5 ghi nhóm quyền là khóa ngoại, mục 7.7 ghi bảng User_Groups; nếu nhóm quyền lưu bằng FK riêng thì `has_perm` không thấy quyền nhóm. Nhóm 7 đã dùng `has_perm`, nên câu hỏi dòng 755 trả lời được là map trực tiếp.
- **Bằng chứng:** dashboard/views.py:63@staging; documents/views.py:91, 147, 161@2_documents; work/models.py:188@6_tasks; approvals/services.py:74-80@feat/5-signing-workflow; plan.md dòng 127, 170, 180, 579, 614-627, 755; spec.md dòng 92-100; organizations/models.py:104-106, views.py:24-32, 177@7_meeting_rooms_birthdays_system; đề md dòng 421, 448; phan-cong-nhom7.md:52, 62; accounts/views.py:37-54, types/auth.ts:1-10, authService.ts:50-64@staging. KT: app signing có 56 quyền tự sinh, gồm 14 quyền `delete_*`; `grep permissions` trên models.py@1a6fcc9 rỗng.
- **Đề xuất (chờ Trưởng nhóm 5 chốt):** thêm `quan_tri_trinh_ky`, `xem_toan_bo_trinh_ky`, `phat_hanh_trinh_ky`; khai báo đủ 11 quyền trong `Meta.permissions`; `default_permissions = ('view',)` cho `SigningSignature`, `SigningAuditLog`, `SigningManifest`; API chi tiết trả `quyen_xu_ly` để UI ẩn/hiện nút. Xin PM và Nhóm 7: một hàm `is_admin` (superuser hoặc thuộc nhóm "Quản trị"); nhóm quyền lưu bằng `user.groups`; đưa 11 quyền vào ma trận phân quyền. Trong lúc chờ: seed 3 nhóm mẫu.
- **Bên chốt:** Trưởng nhóm 5; PM và Nhóm 7 (`is_admin`, RBAC).

#### TH1-02 · Thấp · Plan và spec lệch quy ước app shell: prefix `/api/v1/`, `translations.js`, menu `workflow`, tên app
- **Mô tả:** Plan dòng 565 và spec dòng 79 đặt prefix `/api/v1/`, nhưng không nhánh nào dùng (staging `api/auth`, `api/dashboard`; Nhóm 7 `api/organizations`; Nhóm 6 `api/work`; Nhóm 2 `api/`; `approvals` `api/approvals`). Spec dòng 135 đòi `frontend/src/i18n/translations.js`, trong khi staging dùng `vi.json`, `en.json`, `translate.ts`. Menu `workflow` gắn "Nhóm 5 & 6" với `defaultPage` là `tasks`; structure.md đặt tên app là `approvals`, plan dùng `signing`. Dòng 565 tự ghi cần đối chiếu convention trước khi code.
- **Bằng chứng:** config/urls.py:13, 16@staging và `config/urls.py` của các nhánh nêu trên; plan.md dòng 190, 565, 653; spec.md dòng 79, 135; `frontend/src/i18n`@staging; FRONTEND_BASELINE_GUIDE.md:27; constants.ts:248-268, vi.json:43, 311@staging; structure.md:114, 323.
- **Đề xuất (chờ Trưởng nhóm 5 chốt):** prefix `/api/signing/` (hoặc `/api/approvals/` nếu giữ tên theo structure.md); i18n trong `vi.json`/`en.json`, namespace `signing.*`; giữ page id và route `approvals`; điều hướng nội bộ bằng tab; báo Nhóm 6 trước khi đổi menu chung; sửa spec dòng 79, 135 và plan dòng 565.
- **Bên chốt:** Trưởng nhóm 5.

#### TH1-03 · Thấp · Lỗi phụ của app shell ảnh hưởng Trình ký: link trong email mất trang đích; refresh token xoay vòng không được lưu; `.env.example` sai tên và giá trị biến API; CORS thiếu header `Idempotency-Key`
- **Mô tả:** `ProtectedRoute` chuyển về `/login` không kèm trang đích, `LoginPage` luôn chuyển về `/dashboard`, nên link `/approvals/:id` trong email chỉ đúng khi phiên còn hiệu lực. `apiClient` chỉ lưu access mới, trong khi `SIMPLE_JWT` bật ROTATE + BLACKLIST: lần refresh thứ hai dùng token cũ nhận 401 và người dùng bị đăng xuất (access sống 8 giờ nên khoảng 16 giờ); bản `apiClient` do Nhóm 7 sửa vẫn giữ lỗi này. `.env.example` ghi `VITE_API_BASE_URL=http://127.0.0.1:8000/api`, trong khi `apiClient` đọc `VITE_API_URL` và endpoint đã có tiền tố `/api`. `default_headers` của CORS không có `idempotency-key`; lỗi chỉ lộ khi frontend gọi thẳng cổng 8000.
- **Bằng chứng:** router.tsx:38-40, 102, LoginPage.tsx:72, apiClient.ts:28, 112-118, settings.py:177-183, .env.example:6, authService.ts:38, vite.config.ts:29-34@staging; apiClient.ts:138-148@7_meeting_rooms_birthdays_system; settings.py:143@6_tasks. KT: refresh lần 1 → 200; lần 2 bằng token cũ → 401 "Token is blacklisted"; bằng token mới → 200. `corsheaders.defaults.default_headers` không có `idempotency-key`.
- **Đề xuất (chờ Trưởng nhóm 5 chốt):** Nhóm 1: `ProtectedRoute` truyền `state.from`, `LoginPage` quay lại đúng trang; `apiClient` lưu `refreshData.refresh` khi có. Trưởng nhóm 5 (vai DevOps): một dòng chung `CORS_ALLOW_HEADERS = (*default_headers, 'idempotency-key')`; sửa `.env.example` thành `VITE_API_URL=` (rỗng khi dùng proxy, hoặc `http://127.0.0.1:8000`, không kèm `/api`); nhật ký chỉ lấy IP từ `REMOTE_ADDR` và chỉ trả IP cho người có quyền xem nhật ký.
- **Bên chốt:** Nhóm 1 (router, `apiClient`); Trưởng nhóm 5 (CORS, `.env.example`, IP).

#### TH1-04 · Thấp · Nhóm 7 sửa tệp dùng chung `apiClient.ts`: `apiClient.blob` là hàm tải xuống gắn ngữ nghĩa Excel và không xử lý 401
- **Mô tả:** Nhánh Nhóm 7 sửa `frontend/src/lib/apiClient.ts` (tệp chung của Nhóm 1, 85 dòng thay đổi): thêm `credentials: 'include'` cho mọi request, `X-CSRFToken` cho request ghi, và gắn `apiClient.blob = downloadBlob`. `downloadBlob` trả `Promise<void>`, gọi fetch một lần không qua luồng refresh 401, mặc định thông báo lỗi theo key `organizations.messages.exportError` và tên tệp `download.xlsx`. Ghép thử chưa gãy gì, nhưng tên `apiClient.blob` đã bị chiếm với ngữ nghĩa khác nhu cầu trả `Blob` cho PDF viewer.
- **Bằng chứng:** `git diff origin/staging origin/7_meeting_rooms_birthdays_system -- frontend/src/lib/apiClient.ts`; apiClient.ts:96-110, 125-134, 208-253 (dòng 219, 221, 238)@7_meeting_rooms_birthdays_system; approvalService.ts:163-187@feat/5-signing-workflow. KT ghép nhánh Nhóm 7 + `feat/5-signing-workflow`: 3 conflict (`settings.py`, `urls.py`, `requirements.txt`); giữ cả hai bên thì backend test OK, vitest 15 tệp/52 test pass, `tsc -b` exit 0, eslint sạch.
- **Đề xuất (chờ Trưởng nhóm 5 chốt):** đề nghị Nhóm 1 và Nhóm 7 đổi tên hàm hiện có thành `apiClient.download(endpoint, filename)` với thông báo lỗi chung; thêm `apiClient.getBlob(endpoint): Promise<Blob>` qua luồng refresh 401; mọi thay đổi `apiClient.ts` qua PR có Nhóm 1 review. Trong lúc chờ, Nhóm 5 dùng hàm riêng kiểu `fetchProtectedBlob`.
- **Bên chốt:** Nhóm 1 (chủ tệp) và Nhóm 7; Trưởng nhóm 5 (nêu vấn đề).

#### TH1-05 · Thấp · Chưa có định dạng lỗi API chung toàn lớp; lỗi trả theo field như plan 7.5 yêu cầu sẽ hiện thành thông báo chung qua `apiClient`
- **Mô tả:** Plan dòng 608 yêu cầu lỗi validation trả theo field kèm mã lỗi nghiệp vụ ổn định; Pha 0 dòng 653 có việc "định dạng lỗi"; docs chung trên staging không có quy ước. Nhóm 1 trả `{success:false, error, detail}`; Nhóm 7 trả `{detail: '<key i18n>', key}` hoặc `serializer.errors`. `ApiError` của `apiClient` chỉ lấy `data.error`, `data.detail`, `data.message`, nên body chỉ có lỗi theo field hiện "API Error: 400" (bản Nhóm 7 hiện thông báo mã lỗi chung).
- **Bằng chứng:** plan.md dòng 608, 653; `git grep -i -E 'định dạng lỗi|error format|mã lỗi|error_code'` trong docs@staging: không có kết quả; accounts/views.py:73-78, 95-99, apiClient.ts:20-25@staging; organizations/views.py:61-64, 73-76, 92-95, apiClient.ts:22-24@7_meeting_rooms_birthdays_system.
- **Đề xuất (chờ Trưởng nhóm 5 chốt):** chốt cho module trình ký ở Pha 0 rồi đề xuất PM áp dụng chung: body lỗi luôn có `detail` (thông điệp hoặc key `signing.loi.*`), `ma_loi` (mã ổn định, ví dụ `KHOA_KHONG_HOAT_DONG`), `errors` (dict theo field khi là lỗi validation); một exception handler DRF cho app signing, kể cả `ProtectedError` trả 409.
- **Bên chốt:** Trưởng nhóm 5; PM nếu áp dụng toàn lớp.

### 8.7. Hạ tầng và quy trình (HT)

#### HT-01 · Nghiêm trọng · Chưa chọn nền triển khai: nhánh `5_signing_workflow` chỉ có tài liệu, không dựng trên staging; hai dòng code `approvals` và `signing` nằm trên hai gốc khác nhau
- **Mô tả:** Plan dòng 56-57 coi `5_signing_workflow` là nhánh triển khai; Pha 0 dòng 651 yêu cầu kiểm tra cấu trúc Django trên nhánh này. Nhưng nhánh chỉ có 21 tệp tài liệu/cấu hình, gốc chung với staging là Initial commit, thiếu 89 commit của staging. `feat/signing-models` (14 bảng đúng plan, 19 test) dựng trên nhánh tài liệu nên không có `manage.py`, settings. `feat/5-signing-workflow` (app `approvals`, 38 test backend, 10 test vitest) dựng trên staging nhưng mô hình khác plan (round, StepType review/sign, chữ ký HMAC). Bản cuối của plan (c1b9704) được sửa sau commit `approvals` khoảng 11,5 giờ mà không nhắc tới `approvals`. Các nhánh 2, 3, 4, 7 đã dựng trên tip staging 37a2729; nhánh Nhóm 5 thì chưa. Hệ quả: chưa có đường PR sạch lên staging; chưa xác định công việc từng pha áp vào app nào.
- **Bằng chứng:** `git merge-base origin/staging origin/5_signing_workflow` = d9d55df (Initial commit); `git rev-list --left-right --count` = 89/9; `git ls-tree -r origin/5_signing_workflow`: 21 tệp. KT merge staging + `feat/signing-models`: 5 conflict (bug_report.yml, feature_request.yml, team-pr-review.yml, README.md, structure.md); kéo lại `AGENTS.md` và `.agents/` mà staging đã xóa ở 33d68d6 và đưa vào `.gitignore` dòng 108-111. Lấy bản staging cho 5 tệp: `check` sạch nhưng `manage.py test` FAILED (model không thuộc app trong `INSTALLED_APPS`). Thêm `signing` vào `INSTALLED_APPS`: `check` sạch, `makemigrations --check` không thay đổi, 33 test OK trên Django 5.2.17 và 6.1.1. KT merge `5_signing_workflow` vào `feat/5-signing-workflow`: 7 conflict. approvals/models.py:52-55, 153, 287, services.py:145@feat/5-signing-workflow. fea610a ngày 28/09 07:50; c1b9704 ngày 28/09 19:20; `grep approvals` trên plan.md: 0 kết quả. structure.md:114, 323@staging đặt tên app `approvals`.
- **Đề xuất (chờ Trưởng nhóm 5 chốt):**
  - (1) Ghi vào plan (mục 2 và Pha 0) quyết định nền triển khai. Gợi ý: `signing` là đích vì bám 14 bảng; `approvals` giữ ở nhánh riêng làm bản demo dự phòng và nguồn tái dùng (trang frontend, seed, 38 test làm checklist), không merge cả hai app lên staging.
  - (2) Trên `5_signing_workflow` chạy `git merge origin/staging`, 5 tệp conflict lấy bản staging, `git rm -r --cached AGENTS.md .agents`, giữ `docs/modules/05_signing_workflow`.
  - (3) Rebase `feat/signing-models` lên nhánh đã đồng bộ; PR đầu tiên thêm `signing` vào `INSTALLED_APPS`.
  - (4) Sửa plan dòng 56-57, 651, 760 theo thực tế; chốt tên app trước khi `0001` lên staging và cập nhật structure.md.
- **Bên chốt:** Trưởng nhóm 5.

#### HT-02 · Cao · Plan dựa vào PostgreSQL, Redis, Celery trong khi mục 1.3 loại hạ tầng; staging chạy SQLite, không nhánh nào có celery hay redis; `select_for_update` không có tác dụng trên SQLite
- **Mô tả:** Challenge lưu Redis (dòng 141, 599, 672); thông báo, nhắc hạn, phẳng hóa chạy Celery (27, 196-198, 640-645, 687); khóa dòng và role DB dựa PostgreSQL (58, 195, 203, 484); DoD dòng 768-769 đòi test challenge và outbox/Celery. Trong khi đó mục 1.3 dòng 33 loại "cấu hình hạ tầng". Staging dùng SQLite; không nhánh nào khai báo celery hay redis; không có Dockerfile; README hướng tới Windows (`CHAY_FULL_STACK.bat`); plan dòng 744 dùng khối powershell. Trên SQLite `has_select_for_update=False`: hai luồng cùng ký thì một luồng nhận "database is locked" (thành HTTP 500) thay vì bị từ chối có kiểm soát. Tác vụ nền không có người dùng, trong khi `SigningAuditLog.nguoi_thuc_hien` và `SigningManifest.create_by` là NOT NULL. Plan đã gắn nhãn `[ĐỀ XUẤT]` cho stack (dòng 58) và yêu cầu hành động đồng bộ tự giữ bất biến (dòng 645), nên hạ cấp hạ tầng không làm đổi nghiệp vụ.
- **Bằng chứng:** plan.md dòng 27, 33, 58, 141, 195-198, 203, 484, 599, 640-645, 672, 687, 744-747, 760, 768-769; settings.py:95-100@staging (sqlite3, không OPTIONS); README.md:73, 89-93@staging. Quét requirements của 16 nhánh: không có celery/redis; `cryptography` chỉ có trong requirements UTF-16 của `6_tasks` (từ `pip freeze`). models.py@1a6fcc9 dòng 450 (`create_by` NOT NULL), 524-525 (`nguoi_thuc_hien` NOT NULL). KT (Django 5.2.17): `has_select_for_update` False. Hai luồng đọc rồi cập nhật trong `atomic`: mặc định một luồng `OperationalError: database is locked`; với `transaction_mode: IMMEDIATE`, `timeout: 20` thì luồng thứ hai bị từ chối đúng nghiệp vụ.
- **Đề xuất (chờ Trưởng nhóm 5 chốt) – "cấu hình MVP chạy trên Windows, không cài thêm dịch vụ":**
  - (1) SQLite với `OPTIONS {'transaction_mode': 'IMMEDIATE', 'timeout': 20}` (Django ≥5.1; KT: 52 test `feat/5-signing-workflow` vẫn OK khi bật); service bắt `OperationalError` "locked" và trả 409; test đồng thời theo HT-08.
  - (2) Challenge dùng `django.core.signing.TimestampSigner` (`max_age=300`) ký {user, key_id, nonce}, hoặc một bảng challenge nhỏ.
  - (3) Thông báo gửi đồng bộ sau `transaction.on_commit`; management command quét bản ghi `CHO_GUI` và nhắc hạn, chạy bằng Task Scheduler; manifest chốt đồng bộ khi `HOAN_THANH`.
  - (4) Thêm `cryptography` vào requirements qua PR do Trưởng nhóm 5 duyệt.
  - (5) `nguoi_thuc_hien` cho phép rỗng kèm cột nguồn (`NGUOI_DUNG`/`HE_THONG`), hoặc data migration tạo tài khoản hệ thống.
  - (6) Sửa dòng 484 thành "chặn ở tầng ORM"; dời Celery, Redis, PostgreSQL, role DB sang "giai đoạn sau"; đổi DoD dòng 769 thành "chạy lệnh quét hai lần không gửi trùng".
- **Bên chốt:** Trưởng nhóm 5.

#### HT-03 · Cao · Quality Gate cho kết quả "xanh giả": lệnh test chạy từ thư mục gốc tìm thấy 0 test; gate chỉ chạy `accounts`; không có CI; plan ghi `pytest`; `pnpm test` lỗi trên Node 20
- **Mô tả:** PR template dòng 11 chạy `python backend/manage.py test` từ thư mục gốc, kết quả "Ran 0 tests OK" trên staging, `feat/5-signing-workflow`, `2_documents`, `3_dossiers_documents`, `7_meeting_rooms_birthdays_system`; chạy trong `backend/` mới ra 14 test (staging) và 52 test (`feat/5-signing-workflow`). QUALITY_GATE dòng 31 chỉ chạy `test accounts`: bản staging ghép signing chưa đăng ký app vẫn qua `accounts`, `check`, `makemigrations`, nhưng cả suite FAILED. `2_documents` cả suite FAILED do import tương đối trong `tests.py`, còn `test documents` 27 OK. Repo không có workflow CI nào ngoài `team-pr-review.yml`, dù README dòng 34 giao "Quản trị CI/CD" cho Nhóm 5. Plan dòng 747 và spec dòng 143 ghi `pytest` (không có trong requirements). PR template dòng 12 và spec dòng 135 đòi `translations.js` không tồn tại. README dòng 82 cho phép Node 18/20, nhưng vitest 5.0.1 và jsdom 30.0.1 cần Node ≥22.12 / ≥22.22.2. Trưởng nhóm 5 là reviewer mọi PR vào staging, nên gate báo xanh khi không chạy test nào là rủi ro trực tiếp.
- **Bằng chứng:** pull_request_template.md:9-13, QUALITY_GATE_STAGING.md:28-53, README.md:34, 82, pnpm-lock.yaml:968-970, 1506-1508@staging; plan.md dòng 744-747; spec.md dòng 135, 142-143. `git ls-tree .github` trên 16 nhánh: chỉ có `team-pr-review.yml`. KT (Django 5.2.17): từ thư mục gốc "Ran 0 tests"; trong `backend/` staging 14 OK, `feat/5-signing-workflow` 52 OK, `3_dossiers_documents` 17 OK, `7_meeting_rooms_birthdays_system` 32 OK; `2_documents` FAILED (RuntimeError: model `Document` không khai báo `app_label` tường minh vì `tests.py` dùng import tương đối). KT Node 20.20.0: vitest exit 1 (`webidl.util.markAsUncloneable is not a function`), vite build OK. Node 22.22.0: test và lint OK.
- **Đề xuất (chờ Trưởng nhóm 5 chốt):**
  - (a) Lệnh chuẩn. Backend: `cd backend && python manage.py check && python manage.py makemigrations --check --dry-run && python manage.py test`. Frontend: `cd frontend && pnpm install --frozen-lockfile && pnpm test && pnpm lint && pnpm build`. Cập nhật plan mục 11, PR template, QUALITY_GATE; bỏ `pytest`.
  - (b) Thêm workflow CI (khoảng 30 dòng) chạy trên pull_request vào staging và các nhánh nhóm (Python 3.11, 3.12; Node 22).
  - (c) Test Nhóm 5 tiếp tục dùng absolute import (`from signing.models ...`).
  - (d) README ghi Node ≥22.22.2 hoặc 24; thêm `engines` và `.nvmrc`.
  - (e) Đổi `translations.js` thành `vi.json`/`en.json` trong PR template và spec.
- **Bên chốt:** Trưởng nhóm 5.

#### HT-04 · Trung bình · Email không gửi được trên Python 3.10/3.11: Django 5.2 bỏ qua `MAILERS` và gửi qua SMTP localhost; khai báo thêm `EMAIL_BACKEND` thì Django 6.1 báo lỗi
- **Mô tả:** Requirements cho phép `Django>=5.1,<6.2`, README yêu cầu Python ≥3.10, nên Python 3.10/3.11 cài Django 5.2.17, còn Python ≥3.12 cài 6.1.1. Settings staging chỉ khai báo `MAILERS` (dòng 143-147); trên 5.2.17, `EMAIL_BACKEND` rơi về smtp và `send_mail` báo ConnectionRefusedError. Trong `approvals`, lỗi bị bắt trong `on_commit` và chỉ in traceback ra console của runserver, giao diện không báo gì; test vẫn xanh vì test runner dùng locmem. Khai báo `EMAIL_BACKEND` cùng `MAILERS` thì Django 6.1.1 dừng với ImproperlyConfigured.
- **Bằng chứng:** README.md:84@staging; settings.py:184-206, services.py:203-210@feat/5-signing-workflow; settings.py:149@6_tasks. KT: `pip download 'Django>=5.1.0,<6.2.0' --python-version` → 3.10/3.11: 5.2.17; 3.12/3.13: 6.1.1. Staging trên 5.2.17: `EMAIL_BACKEND` = `smtp.EmailBackend`, `send_mail` → ConnectionRefusedError [Errno 111]. Python 3.12 + 6.1.1, thêm `EMAIL_BACKEND` → "Deprecated email settings are not allowed when MAILERS is defined". Cấu hình theo `django.VERSION`: `get_connection()` là console và `send_mail` trả 1 trên cả hai phiên bản.
- **Đề xuất (chờ Trưởng nhóm 5 chốt):** chọn một cùng Nhóm 1: (1) ghim Django 5.2 LTS (`Django>=5.2,<5.3`) và dùng `EMAIL_BACKEND`/`EMAIL_*` (KT: migration staging, signing, approvals vẫn chạy trên 5.2.17); (2) giữ dải phiên bản, cấu hình theo `django.VERSION >= (6, 1)`. Cả hai thêm `DEFAULT_FROM_EMAIL`; thêm test kiểm `get_connection()` không phải smtp ở chế độ console.
- **Bên chốt:** Trưởng nhóm 5 và Nhóm 1.

#### HT-05 · Trung bình · Nhóm 4 đổi DB mặc định sang PostgreSQL; hai driver psycopg khác nhau; biến `DB_ENGINE` hiểu theo hai cách
- **Mô tả:** `4_documents_templates` đặt ENGINE mặc định PostgreSQL qua `DB_ENGINE` (settings dòng 103), thêm `psycopg[binary]>=3.2.0`; `feat/5-signing-workflow` dùng `psycopg2-binary` và hiểu `DB_ENGINE` theo giá trị ngắn `sqlite|postgresql`. Nhánh 4 merge vào staging là fast-forward; máy chưa cài driver thì `check` lỗi, đã cài thì `test accounts` (lệnh 1 của Quality Gate) lỗi kết nối 127.0.0.1:5432. Hai cách hiểu `DB_ENGINE` lệch nhau. `backend/README.md:11` của chính Nhóm 4 ghi SQLite cho môi trường phát triển; `.env.example` không có biến DB.
- **Bằng chứng:** settings.py:101-110, requirements.txt, .env.example, backend/README.md:11@4_documents_templates; `git rev-list --left-right --count origin/staging...origin/4_documents_templates` = 0/18; settings.py:117-135@feat/5-signing-workflow. KT: không driver → "Error loading psycopg2 or psycopg module"; có psycopg3 → `check` sạch, `test accounts` → "connection ... port 5432 failed"; `DB_ENGINE=postgresql` → lỗi backend `postgresql` không tồn tại; `DB_ENGINE=django.db.backends.sqlite3` → `test accounts` 9 OK.
- **Đề xuất (chờ Trưởng nhóm 5 chốt):** khi review PR Nhóm 4, yêu cầu SQLite là mặc định, PostgreSQL bật qua một biến (`DB_ENGINE=sqlite|postgresql`, ánh xạ trong settings), một driver (`psycopg[binary]` 3), ghi đủ biến vào `.env.example`. Tạm thời đặt `DB_ENGINE=django.db.backends.sqlite3` trong `.env`. Nhóm 5 không đưa thay đổi DB vào PR module.
- **Bên chốt:** Trưởng nhóm 5 và Nhóm 4.

#### HT-06 · Trung bình · File chung: DoD dòng 770 "không sửa file ngoài phạm vi" còn mơ hồ; settings/urls/requirements conflict khi tích hợp; requirements Nhóm 6 mã hóa UTF-16
- **Mô tả:** Muốn app chạy phải sửa file chung (`INSTALLED_APPS`, MEDIA, `urls.py`, `requirements.txt`, `router.tsx`, `vi.json`/`en.json`), trong khi DoD dòng 770 không liệt kê ngoại lệ. `feat/5-signing-workflow` sửa settings +75/-13 dòng, nên ghép với nhánh 2, 3, 4, 7 đều conflict settings; thêm urls (2, 7) và requirements (4, 7). Các nhánh khác cũng conflict lẫn nhau ở cùng các tệp; phần lớn thuộc kiểu "giữ cả hai bên". Requirements `6_tasks` là UTF-16LE, CRLF, 62 gói từ `pip freeze` (ghim `Django==5.2.4`), git báo "Cannot merge binary files".
- **Bằng chứng:** plan.md dòng 770; `git diff --numstat origin/staging origin/feat/5-signing-workflow` (settings +75/-13, urls +4, requirements +6, router +29/-1, vi/en +322); `file backend/requirements.txt`@6_tasks; không nhánh nào có `.gitattributes`. KT merge từng cặp: 2 + feat/5 → settings, urls; 3 + feat/5 → settings; 4 + feat/5 → settings, requirements; 7 + feat/5 → settings, urls, requirements; 2+3, 2+7, 3+7 → settings; 4+7 → requirements; staging + 6_tasks → "Cannot merge binary files".
- **Đề xuất (chờ Trưởng nhóm 5 chốt):** (a) sửa DoD dòng 770 thành danh sách điểm đăng ký được phép sửa; (b) tạo sẵn trên staging các "khe" có comment cho 8 nhóm trong `INSTALLED_APPS`, `urls.py`, `requirements.txt`; (c) tách phần env/DB/email ra khỏi PR Trình ký; (d) requirements dùng UTF-8, thêm `.gitattributes` (`*.txt text eol=lf`); (e) khai báo thư viện dạng `>=`, đồng bộ staging trước khi mở PR.
- **Bên chốt:** Trưởng nhóm 5.

#### HT-07 · Trung bình · Ba chức năng cần gửi mail và chạy theo lịch (Nhóm 5 E14, Nhóm 6 E15, Nhóm 7 E17) chưa có cơ chế chung; nhánh `6_tasks` lệch staging nên conflict 6 tệp
- **Mô tả:** Đề yêu cầu gửi mail ở E14 (thông báo người cần ký), E15 và đề md dòng 335 (giao việc, nhắc hạn), E17 (mail chúc mừng sinh nhật tự động). Ngoài `feat/5-signing-workflow`, chưa nhánh nào có code gửi mail; staging không có bộ chạy tác vụ định kỳ. Settings `6_tasks` chỉ có `MAILERS` và ghim `Django==5.2.4`, nên sẽ gặp đúng lỗi HT-04. Merge `6_tasks` vào staging conflict 6 tệp, chủ yếu vì nhánh dựng trên commit cũ 345122c.
- **Bằng chứng:** xlsx ô E14, E15, E17; đề md dòng 335; `git grep 'send_mail|EmailMessage'` trên staging, 2, 3, 4, 6, 7: không có kết quả, chỉ approvals/services.py:15, 206@feat/5-signing-workflow; settings.py:149@6_tasks; router.tsx:84-85@staging. KT: staging + 6_tasks → 6 conflict; 6_tasks + feat/5 → 6 conflict, gồm `router.tsx`.
- **Đề xuất (chờ Trưởng nhóm 5 chốt):** một cơ chế dùng chung cho ba nhóm: cấu hình email theo HT-04; gửi sau `transaction.on_commit`; nhắc hạn và mail sinh nhật bằng management command chạy qua Task Scheduler (`approvals` đã có mẫu `send_signing_reminders`). Trình ký không tạo Task. Khi review PR Nhóm 6, yêu cầu đồng bộ staging trước và kiểm router không còn route `SyllabusPreview` ở `/approvals`.
- **Bên chốt:** Trưởng nhóm 5, Nhóm 6, Nhóm 7.

#### HT-08 · Trung bình · Test đồng thời của Pha 2 không kiểm được cơ chế khóa trên SQLite test DB mặc định
- **Mô tả:** Pha 2 (dòng 668) và DoD dòng 767 đòi test "hai người ký cùng lúc". Khi chạy test, Django tạo DB SQLite in-memory dạng shared cache; ở chế độ này SQLite khóa theo bảng và trả lỗi ngay, không chờ timeout. Chỉ khi DB test là tệp và bật `IMMEDIATE` thì luồng thứ hai mới bị từ chối đúng nghiệp vụ. Dùng `skipUnlessDBFeature('has_select_for_update')` thì test bị bỏ qua trên SQLite.
- **Bằng chứng:** plan.md dòng 203, 528, 668, 767; settings.py:95-100@staging (không OPTIONS, không TEST). KT (`TransactionTestCase`, hai luồng): in-memory + mặc định → một luồng "database table is locked"; in-memory + `IMMEDIATE`/timeout 20 → vẫn "database table is locked"; tệp + mặc định → "database is locked"; tệp + `IMMEDIATE` → luồng thứ hai bị từ chối đúng. Bật `IMMEDIATE` trong settings `feat/5-signing-workflow`: 52 test vẫn OK.
- **Đề xuất (chờ Trưởng nhóm 5 chốt):** test đồng thời dùng `TransactionTestCase`, chỉ chạy khi DB test là tệp (skipIf khi DB test in-memory). Settings chung có `OPTIONS {'transaction_mode': 'IMMEDIATE', 'timeout': 20}` và `TEST {'NAME': BASE_DIR / 'test_db.sqlite3'}` bật qua biến môi trường. Service bắt `OperationalError` "locked", trả 409. Ghi rõ trong Pha 2 rằng test này chứng minh tuần tự hóa của SQLite, chưa phải khóa dòng PostgreSQL.
- **Bên chốt:** Trưởng nhóm 5.

#### HT-09 · Trung bình · Nhánh `6_tasks` và `8_ai_chatbox` chưa dựng trên staging: merge vào staging lần lượt 6 và 8 conflict; `8_ai_chatbox` là project Django riêng; `6_tasks` kèm khoảng 9,8 MiB trong `frontend/skills/`
- **Mô tả:** `6_tasks` có merge-base 345122c (thiếu 75 commit); `8_ai_chatbox` có merge-base Initial commit (thiếu 89 commit, không có `.github`). `8_ai_chatbox` dùng `backend/django_project/settings.py` thay cho `config/settings.py`, frontend có cả `App.jsx`/`main.jsx` lẫn `app/App.tsx`. `6_tasks` commit 278 tệp (khoảng 9,8 MiB) dưới `frontend/skills/`. Vai trò DevOps (xlsx ô A2, README dòng 34) thuộc Trưởng nhóm 5, nên khối tích hợp này rơi vào cùng người phải làm module Trình ký.
- **Bằng chứng:** `git merge-base`: staging/6_tasks = 345122c (75/15), staging/8_ai_chatbox = d9d55df (89/5), các nhánh 2, 3, 4, 7 = 37a2729; `git ls-tree origin/8_ai_chatbox`; `git ls-tree -r -l origin/6_tasks | grep frontend/skills/`: 278 tệp; git_workflow.md:28, README.md:34@staging. KT merge: staging + 6_tasks → conflict `.gitignore`, README, settings, urls, requirements (nhị phân), router; staging + 8_ai_chatbox → conflict `.gitignore`, README, `backend/manage.py`, requirements, `index.html`, `package.json`, router, `AiAssistantPage.tsx`.
- **Đề xuất (chờ Trưởng nhóm 5 chốt):** báo PM và trưởng Nhóm 6, Nhóm 8 đồng bộ staging vào nhánh nhóm trước khi mở PR; Nhóm 8 chuyển code vào cấu trúc `config/`, `apps/`; Nhóm 6 bỏ `frontend/skills/`, đổi requirements sang UTF-8. Lập bảng theo dõi "nhánh đã đồng bộ staging" cho 8 nhóm, xử lý trước giai đoạn Trình ký cần tích hợp.
- **Bên chốt:** Trưởng nhóm 5 và PM.

#### HT-10 · Trung bình · Plan không có điểm tích hợp theo pha (staging, PR, đăng ký app, Quality Gate); mã Nhóm 5 xuất hiện theo khối lớn khó review
- **Mô tả:** Plan và spec không có từ staging, PR, merge, `INSTALLED_APPS`; Pha 6 dòng 698 và DoD dòng 771 chỉ nêu kiểm tra nhánh/status/diff trước khi commit. Không pha nào gắn với một PR hay một lần đồng bộ staging, nên lần ghép đầu tiên dễ dồn về cuối kèm mọi conflict ở HT-06. Hai commit mã hiện có đều lớn: fea610a (`approvals`) 44 tệp, +9.116 dòng; 1a6fcc9 (`signing`) 7 tệp, +1.835 dòng. Theo cấu hình reviewer, Trưởng nhóm 5 vừa duyệt PR vào nhánh nhóm vừa duyệt PR vào staging.
- **Bằng chứng:** `grep -niE 'staging|pull request|\bPR\b|merge|INSTALLED_APPS|settings'` trên plan.md và spec.md: không có kết quả; các dòng plan nhắc "nhánh" (56-57, 651, 698, 760, 771) chỉ nói về nhánh làm việc, spec chỉ nhắc nhánh ở dòng 7; `git show --shortstat fea610a`, `1a6fcc9`; team-pr-review.yml:65-67, 73-75@staging.
- **Đề xuất (chờ Trưởng nhóm 5 chốt):** thêm mục "Tích hợp": mỗi pha kết thúc bằng PR nhỏ `feat/5-*` → `5_signing_workflow` (một nhóm model/service/API kèm test); đồng bộ staging ở mỗi mốc báo cáo; mở PR `5_signing_workflow` → `staging` đầu tiên ngay sau Pha 1 (đăng ký app, `0001`) để lộ conflict sớm; mọi PR chạy đủ lệnh ở HT-03.
- **Bên chốt:** Trưởng nhóm 5.

#### HT-11 · Trung bình · Phần việc CI/CD, staging và production được giao cho Nhóm 5 nhưng plan không có hạng mục và repo chưa có sản phẩm tương ứng
- **Mô tả:** Đề (xlsx ô A2) ghi vai trò DevOps (GitLab, staging và production) do Trưởng nhóm 5 đảm nhận; README staging dòng 34 ghi trách nhiệm Nhóm 5 gồm quản trị CI/CD, staging, production. Plan mục 1.3 dòng 33 loại triển khai production và cấu hình hạ tầng khỏi MVP của module, và không tài liệu nào khác phân bổ phần việc DevOps. Repo chưa có workflow CI chạy test; nhánh `main` vẫn là Initial commit dù git_workflow.md dòng 9 coi `main` là Production; settings staging để `DEBUG=True`, `SECRET_KEY` viết cứng, `ALLOWED_HOSTS=[]`, không có `STATIC_ROOT`.
- **Bằng chứng:** xlsx ô A2; README.md:34, git_workflow.md:9-10, settings.py:28, 31, 33, 137@staging; plan.md dòng 33; `origin/main` = d9d55df.
- **Đề xuất (chờ Trưởng nhóm 5 chốt):** lập danh sách việc DevOps riêng, tách khỏi plan backend, ở mức tối thiểu cho demo: (1) workflow CI chạy lệnh Quality Gate (HT-03); (2) quy ước phát hành staging → main có tag tại mốc demo; (3) một môi trường demo chung có hướng dẫn cài từ đầu (migrate, seed, chạy backend và frontend). Hỏi PM/Giảng viên "production" trong đề là nhánh `main` hay môi trường chạy thật.
- **Bên chốt:** Trưởng nhóm 5 và PM (xác nhận phạm vi với Giảng viên).

#### HT-12 · Thấp · Gán reviewer tự động: PR vào staging do Trưởng nhóm 5 mở không có reviewer nào
- **Mô tả:** `team-pr-review.yml` trên staging gán một tài khoản duy nhất (Trưởng nhóm 5) cho mọi PR vào staging (dòng 65-67), lọc bỏ tác giả (dòng 83) rồi dừng với "No eligible reviewers found" (dòng 85-87). QUALITY_GATE_STAGING.md dòng 5 ghi hai DevOps Lead. Với PR `feat/*` → `5_signing_workflow`, bản trên nhánh mặc định gán trưởng nhóm khi thành viên mở (dòng 73-75). Chưa kiểm được branch protection trên repo gốc.
- **Bằng chứng:** team-pr-review.yml:45-48, 65-67, 73-75, 83, 85-87@staging; team-pr-review.yml:39-40@5_signing_workflow; `gh api` của fork: default_branch = staging; QUALITY_GATE_STAGING.md:5.
- **Đề xuất (chờ Trưởng nhóm 5 chốt):** thêm nhánh điều kiện trong script (khoảng 3 dòng): khi tác giả PR vào staging là Trưởng nhóm 5 thì gán DevOps Lead còn lại hoặc PM; hoặc để thành viên Nhóm 5 mở PR `5_signing_workflow` → `staging`.
- **Bên chốt:** Trưởng nhóm 5 và PM.

#### HT-13 · Thấp · `.gitignore` bỏ qua tệp Nhóm 5 có thể cần (`*.pem`, `*.key`, `seed_data.py`, `migrations/*seed*.py`), tệp chạy 1-click và script seed tài khoản demo mà README nhắc tới
- **Mô tả:** `git check-ignore` trên staging cho thấy `*.pem` (dòng 69), `*.key` (70), `seed_data.py` (50), `backend/apps/*/migrations/*seed*.py` (52), `CHAY_FULL_STACK.bat` (107) bị bỏ qua, trong khi README dòng 73, 91 và QUALITY_GATE dòng 98 vẫn hướng dẫn chạy `CHAY_FULL_STACK.bat`. Dòng 53 bỏ qua `seed_accounts.py` (đã xóa ở 007e9b2), nhưng README dòng 142-145 vẫn ghi tài khoản demo được sinh bởi script seed; staging hiện không có lệnh seed. Hệ quả đã xuất hiện: Nhóm 4 tự viết `seed_users.py` trong app `accounts`; `approvals` có seed riêng.
- **Bằng chứng:** `git check-ignore -v --no-index`@staging (dòng 50, 52, 53, 69, 70, 107); README.md:73, 91, 142-145, QUALITY_GATE_STAGING.md:98@staging; `git log --diff-filter=D` (007e9b2); `backend/apps/accounts/management/commands/seed_users.py`@4_documents_templates; `seed_signing_demo.py`@feat/5-signing-workflow.
- **Đề xuất (chờ Trưởng nhóm 5 chốt):** thành viên Nhóm 5 sinh khóa test trong `setUp` (`Ed25519PrivateKey.generate()`), không dùng tệp `.pem`; đặt lệnh seed tên `seed_signing_demo.py`. Trưởng nhóm 5 cùng Nhóm 1 đưa lại một lệnh seed tài khoản chung vào staging (gộp `seed_users` của Nhóm 4), bỏ `CHAY_FULL_STACK.bat` khỏi `.gitignore` hoặc sửa README và QUALITY_GATE.
- **Bên chốt:** thành viên Nhóm 5, Trưởng nhóm 5, Nhóm 1.

### 8.8. Bảo mật và đáp ứng đề bài (BM)

#### BM-01 · Cao · Gạch G5 (thông báo đến người cần ký và gửi mail): có hạ tầng outbox nhưng thiếu quy tắc tạo thông báo khi đến lượt, thiếu hộp thư in-app và API đọc
- **Mô tả:** E14 gạch 5 và đề md dòng 304 yêu cầu thông báo trên hệ thống và email khi đến lượt người ký. Plan chỉ mô tả hạ tầng: bảng `signing_notification` kiêm outbox, Celery, nhắc trước hạn 24 giờ và tại hạn. Không có quy tắc "gán `thoi_diem_mo` thì tạo thông báo IN_APP + EMAIL" (mở cấp, mở `KY_CHINH`, lượt mới, ủy quyền), không có quy tắc báo kết quả cho người tạo. Bảng không có nội dung, đường dẫn, trạng thái đã đọc; `loai_thong_bao` là chuỗi tự do; mục 7 không có API đọc hay đánh dấu đã đọc; tiêu chí nghiệm thu chỉ kiểm nhắc hạn. Chuông header Nhóm 1 đọc dữ liệu mẫu.
- **Bằng chứng:** xlsx ô E14 gạch 5; đề md dòng 304; plan.md dòng 27, 196-198, 207, 486-502 (495 `loai_thong_bao` Text(50); 496 chỉ `CHO_GUI`/`DA_GUI`/`THAT_BAI`), 629-638, 733-738, 769; `grep 'đến lượt'` trên plan.md, spec.md: 0 kết quả; models.py@1a6fcc9 dòng 107-110, 555-578; NotificationStreams.tsx:3, 29-30, constants.ts:333, types/notification.ts:1@staging; approvals/models.py:376-377, 400, urls.py:37-38, services.py:180-189@feat/5-signing-workflow.
- **Đề xuất (chờ Trưởng nhóm 5 chốt):** (1) thêm vào mục 9 bảng "sự kiện → người nhận → kênh" (đến lượt, được ủy quyền, yêu cầu sửa, từ chối, hoàn thành, hủy, sắp đến hạn); `loai_thong_bao` dùng TextChoices. (2) Thêm `tieu_de`, `noi_dung`, `duong_dan`, `thoi_diem_doc` và trạng thái `DA_HUY`. (3) Thêm `GET /signing/notifications/?chua_doc=1` và `POST /signing/notifications/danh-dau-da-doc/`. (4) Tiêu chí: ở `TUAN_TU`, cấp 1 ký xong thì người ở cấp 2 nhận đúng 1 IN_APP và 1 EMAIL, tạo trong cùng transaction. (5) Người ký không có email: tạo bản EMAIL `THAT_BAI` với `loi_gui='KHONG_CO_EMAIL'`. (6) Hiển thị badge trong trang Trình ký; đề nghị Nhóm 1 thêm luồng `signing` vào chuông header sau.
- **Bên chốt:** Trưởng nhóm 5 (thêm Nhóm 1 cho chuông header).

#### BM-02 · Cao · Vòng đời khóa phía trình duyệt chưa được thiết kế; có rủi ro về origin và secure context khi demo
- **Mô tả:** Plan 3.4, 7.4 chỉ mô tả challenge và verify. Plan không nói khóa riêng sinh và lưu ở đâu, khóa công khai gửi lên theo định dạng nào, `dau_van_tay` và `ma_khoa` tính thế nào, ai đặt `ngay_hieu_luc`. Mục 7.4 không có endpoint tạo bản ghi `CHO_KICH_HOAT` và không có GET khóa của người dùng; spec mục 4 không có trang quản lý khóa; mất khóa để `[CHƯA CHỐT]`. Phương án WebCrypto Ed25519 non-extractable lưu IndexedDB chạy được, nhưng kho khóa tách theo origin, profile trình duyệt mới không có khóa, và truy cập qua http bằng địa chỉ LAN thì không có `crypto.subtle`.
- **Bằng chứng:** `grep 'IndexedDB|WebCrypto|crypto.subtle|localStorage|trình duyệt|thiết bị'` trên plan.md, spec.md: chỉ ra các dòng "không lưu private key" (plan 20, 37, 139, 726, 759; spec 68, 137); plan.md dòng 137-146, 385-392, 597-604, 759; spec.md dòng 104-107, 115-129; vite.config.ts@staging (port 5173). KT Chromium 141: `localhost:5173` là secure context, sau reload vẫn còn khóa, `exportKey('pkcs8')` → InvalidAccessError; `127.0.0.1:5173` và `localhost:4173` không thấy khóa; context mới không thấy khóa; `http://<địa chỉ LAN>:5173` không có `crypto.subtle`. Python `cryptography` verify chữ ký trình duyệt trên raw digest OK, trên chuỗi hex → InvalidSignature.
- **Đề xuất (chờ Trưởng nhóm 5 chốt):** (1) WebCrypto Ed25519 non-extractable; `CryptoKeyPair` lưu IndexedDB theo khóa `user:<id>`; đăng xuất không xóa khóa. (2) Contract: `POST /signing/keys/` nhận `{khoa_cong_khai: base64 raw 32 byte}`, trả `{id, dau_van_tay = sha256(raw) hex, challenge}`; `POST /signing/keys/{id}/verify` nhận chữ ký challenge; `GET /signing/keys/me`; server tự đặt `ngay_hieu_luc`. (3) Trang khóa ký cá nhân, banner khi trình duyệt không có khóa hoặc vân tay cục bộ khác khóa `HOAT_DONG`. (4) MVP: mất khóa thì thu hồi và đăng ký lại, khóa cũ giữ để verify lịch sử. (5) Báo lỗi rõ khi không phải secure context hoặc không hỗ trợ Ed25519. (6) Đặt kho khóa sau interface để mock trong test frontend (jsdom không có IndexedDB). (7) Checklist demo: một URL cố định `http://localhost:5173`, mỗi tài khoản một profile trình duyệt, đăng ký khóa cho mọi tài khoản ngay sau seed, có video dự phòng.
- **Bên chốt:** Trưởng nhóm 5.

#### BM-03 · Cao · `signing_request` thiếu mã hồ sơ, trích yếu, đơn vị trình (snapshot); phạm vi `PHONG_BAN` không có đơn vị áp dụng: gạch G3 không có chỗ lưu ổn định
- **Mô tả:** E14 gạch 3 và đề md dòng 302 yêu cầu tìm theo từ khóa và lọc theo phòng ban. Spec dòng 120-121 cần cột mã, trích yếu và ô tìm theo trích yếu hoặc mã hồ sơ. Plan 5.2 không có `ma_ho_so`, `trich_yeu` hay đơn vị trình trên `signing_request`; `signing_process` có `pham_vi` `PHONG_BAN` nhưng không có đơn vị áp dụng. `van_ban_id` là BigInteger nên không join được trích yếu của Nhóm 2; `profile.department` ở staging là chuỗi tự do và không được snapshot. Có thể join tạm qua hồ sơ người tạo, nhưng người tạo đổi phòng thì hồ sơ cũ đổi theo.
- **Bằng chứng:** xlsx ô E14 gạch 3; đề md dòng 302; spec.md dòng 38, 120-121; plan.md dòng 225-241, 275-300, 579, 617; `grep 'trích yếu|trich_yeu|mã hồ sơ|ma_ho_so'` trên plan.md: 0 kết quả; models.py@1a6fcc9 dòng 125-151, 210-242; accounts/models.py:26-31@staging; approvals/models.py:132-133, 149, services.py:217@feat/5-signing-workflow.
- **Đề xuất (chờ Trưởng nhóm 5 chốt):** thêm vào `signing_request`: `ma_ho_so` (Text 20, unique, sinh `TK-YYYY-NNNN` trong transaction, thử lại khi trùng), `trich_yeu` (bắt buộc, snapshot), `don_vi_id` (BigInteger tạm, nullable) và `ten_don_vi` (snapshot lúc tạo). Thêm `signing_process.don_vi_ap_dung`, bắt buộc khi `PHONG_BAN`. GET danh sách nhận `q`, `trang_thai`, `don_vi`, `muc_do`, `tu_ngay`, `den_ngay`. Lọc phòng ban chỉ là bộ lọc người dùng chọn ở tab toàn bộ hồ sơ.
- **Bên chốt:** Trưởng nhóm 5 (thêm Nhóm 7 khi có model đơn vị).

#### BM-04 · Trung bình · Thông điệp ký chỉ là digest và plan không bắt khóa ký thuộc người ký
- **Mô tả:** Plan 3.4 dòng 150 quy định ký trên raw digest. Điều kiện ký ở 5.3 (dòng 515-520) và 6.2 (dòng 557) không có điều kiện `khoa_ky.nguoi_so_huu` là người đang ký; model cũng không ràng buộc. Mọi người ký trong một lượt ký trên cùng digest và Ed25519 là thuật toán tất định, nên một người ký có thể nộp cặp (khóa, chữ ký) của người khác lấy từ manifest vào ô ký của người nộp. Người chiếm được phiên JWT có thể nộp lại chữ ký cũ khi digest lặp lại. Vấn đề không chặn demo hay Quality Gate, nhưng làm yếu lập luận chống chối bỏ ở 1.4 dòng 48.
- **Bằng chứng:** plan.md dòng 126, 150, 154-157, 431, 515-520, 557, 589, 721; models.py@1a6fcc9 dòng 363-392, 395-418. KT: chữ ký Chromium verify OK trên raw digest; `Ed25519PrivateKey.sign(d) == sign(d)` → True.
- **Đề xuất (chờ Trưởng nhóm 5 chốt):** (1) thêm vào 5.3, 6.2: `khoa_ky.nguoi_so_huu_id == request.user.id == signer.nguoi_ky_id`, khóa `HOAT_DONG`, thời điểm hiện tại trong [`ngay_hieu_luc`, `ngay_het_han`). (2) Ký trên bytes UTF-8 của thông điệp chuẩn hóa do server dựng: `TLBM-SIGNING-KY-v1`, id lượt, id dòng người ký, user id, vân tay khóa, sha256 tài liệu; frontend lấy chuỗi qua GET rồi ký nguyên văn. (3) Challenge đăng ký khóa dùng tiền tố `TLBM-SIGNING-POP-v1`. (4) Thêm 2 test: chữ ký của người này nộp vào ô của người khác bị từ chối; chữ ký lượt 1 nộp lại ở lượt 2 bị từ chối.
- **Bên chốt:** Trưởng nhóm 5.

#### BM-05 · Trung bình · Plan không có quy tắc phạm vi xem cho hồ sơ gắn văn bản MẬT; người ký không có trong ACL của Nhóm 2 nhận 404
- **Mô tả:** Quy ước chung (đề md dòng 19) và module 2.3 (dòng 153-161) yêu cầu văn bản mật chỉ hiển thị cho người được phân quyền và có nhật ký người mở xem. Plan và spec chỉ nhắc "mật" ở chỗ chọn một hay ba bảng văn bản; spec gốc d6aa1e5 từng có `security_level`, bản hiện tại đã bỏ. Plan 8 dòng 617 "lọc mặc định theo phòng ban người tạo" và tab toàn bộ hồ sơ chưa xác định ai được xem, nên trích yếu hồ sơ mật có thể hiện ra cho người cùng phòng. E14 không có gạch về văn bản mật.
- **Bằng chứng:** `grep 'mật|MAT|confidential|security'` trên plan.md, spec.md: chỉ plan 60, 509, 724, 768; đề md dòng 19, 153-161; `git show d6aa1e5:docs/modules/05_signing_workflow/spec.md` dòng 21, 72; plan.md dòng 609-611, 616-617; documents/views.py:78-99, services.py:62@2_documents. KT trên `2_documents`: người tạo và người nhận 200, tài khoản người ký không có trong `nguoi_nhan` 404 và thấy 0 văn bản MAT.
- **Đề xuất (chờ Trưởng nhóm 5 chốt):** chọn một: (a) MVP không trình ký văn bản loại MAT, chặn ở `POST /signing/requests`; (b) thêm `la_van_ban_mat`, hồ sơ mật chỉ hiển thị cho người tạo, người ký trong snapshot, người ủy quyền, người có quyền xem toàn bộ; không xuất hiện ở bộ lọc phòng ban hay tab toàn bộ; email không ghi trích yếu, không đính kèm tệp. Nếu liên kết văn bản MAT: đề nghị Nhóm 2 tách `can_view_document`, dùng `log_document_view`; chặn gửi và ủy quyền khi người ký thiếu quyền. Thêm test "người cùng phòng không thấy hồ sơ mật".
- **Bên chốt:** Trưởng nhóm 5 và Nhóm 2.

#### BM-06 · Trung bình · Sau khi ghép `2_documents`, `/media/` được phục vụ không cần đăng nhập ở chế độ DEBUG; plan Nhóm 5 dự kiến lưu tệp qua "mount" ngoài `MEDIA_ROOT`, trái structure.md 7.1
- **Mô tả:** Nhánh `2_documents` thêm `static(MEDIA_URL)` khi DEBUG, và DEBUG mặc định True. Tệp lưu theo tên gốc; API trả URL đầy đủ tới `/media/`. Staging chưa có khối này. Riêng Nhóm 5, plan 1.2, 4.1 và Pha 5 dùng "filesystem mount cấu hình qua biến môi trường", trái structure.md dòng 354-355, và chưa nói cách đặt tên tệp hay đường phục vụ. Ảnh chữ ký của Nhóm 5 ít có nguy cơ lộ nếu đặt tên uuid và không trả đường dẫn, như `approvals` đang làm.
- **Bằng chứng:** urls.py:24-26, settings.py:31, 33, 142-143, documents/models.py:188-205@2_documents; chỉ `2_documents` có `static(MEDIA_URL)`; structure.md:354-355, 359@staging; plan.md dòng 28, 192, 688; approvals/models.py:23-41, serializers.py:239-247, 321-335, views.py:445-450@feat/5-signing-workflow. KT trên `2_documents` (không token): GET tệp trong `/media/02_documents/mat/...` → 200, trả nội dung tệp; `/api/documents/` → 401.
- **Đề xuất (chờ Trưởng nhóm 5 chốt):** với Nhóm 2: không dùng `static()` cho toàn bộ `MEDIA_ROOT`; làm endpoint tải tệp có kiểm quyền (và ghi `DocumentViewLog` cho MAT) trước, rồi mới bỏ `static()`; đổi tên tệp lưu sang uuid. Sửa plan dòng 28, 192, 688: adapter MVP là `default_storage` trong `MEDIA_ROOT/05_signing/`, tên uuid, chỉ phục vụ qua API có kiểm quyền (LUONG-01), không đưa `vi_tri_luu_tep` ra payload. Thêm test "GET `/media/05_signing/...` → 404".
- **Bên chốt:** Trưởng nhóm 5 (vai DevOps) và Nhóm 2.

#### BM-07 · Trung bình · Trạng thái và mức độ: lọc "Chờ ký" lẫn hồ sơ chờ sửa; tab việc cần ký chưa định nghĩa; `muc_do` bắt buộc nhưng không có danh mục
- **Mô tả:** E14 gạch 2 chỉ yêu cầu lọc chờ ký; đề md dòng 301 mở rộng thành Chờ ký, Đã ký, Từ chối ký, Đang xử lý. Khi lượt ở `YEU_CAU_SUA`, yêu cầu vẫn `CHO_KY` (dòng 549), nên lọc "Chờ ký" lẫn hồ sơ chờ người tạo sửa. Plan 7.2 không có tham số `trang_thai` (spec có) và không định nghĩa tab việc cần ký: người ký `CHO_KY` nhưng `thoi_diem_mo` rỗng (cấp sau ở `TUAN_TU`) hoặc thuộc cấp `TAM_DUNG` thì không làm gì được. `muc_do` (gạch 1) là Text(20) không có choices; frontend staging dùng bộ `normal|urgent|confidential`.
- **Bằng chứng:** xlsx ô E14 gạch 1-2; đề md dòng 300-301; plan.md dòng 111, 286, 288, 292-293, 361, 549, 579; spec.md dòng 37-38, 120; models.py@1a6fcc9 dòng 47-52, 219; approvals/models.py:44-49, 112-120@feat/5-signing-workflow; types/notification.ts:10@staging.
- **Đề xuất (chờ Trưởng nhóm 5 chốt):** trạng thái hiển thị suy ra từ dữ liệu: `NHAP` → Nháp; `CHO_KY`, lượt `CHO_KY`, chưa ai `DA_KY` → Chờ ký; có `DA_KY` → Đang xử lý; lượt `YEU_CAU_SUA` → Chờ chỉnh sửa; `HOAN_THANH` → Đã ký; `TU_CHOI` → Từ chối ký; `HUY` → Đã hủy. Thêm `trang_thai` vào GET ở 7.2. Tab việc cần ký = dòng người ký của người dùng, `CHO_KY`, có `thoi_diem_mo`, cấp không `TAM_DUNG`, lượt hiện hành `CHO_KY`. `muc_do` dùng TextChoices 4 mức theo NĐ30 (Thường, Khẩn, Thượng khẩn, Hỏa tốc), mặc định Thường, ánh xạ sang `priority` frontend. Xóa `ly_do_tu_choi` trên yêu cầu khi `xem_xet_lai`.
- **Bên chốt:** Trưởng nhóm 5.

#### BM-08 · Trung bình · `SECRET_KEY` viết cứng trong repo đồng thời là khóa ký JWT; đăng ký khóa ký chỉ cần phiên đăng nhập
- **Mô tả:** `SECRET_KEY` viết cứng ở settings.py:28 của staging và hầu hết nhánh nhóm; `feat/5-signing-workflow` dùng chuỗi này làm giá trị dự phòng. `SIMPLE_JWT` không đặt `SIGNING_KEY`, nên JWT được ký bằng chính chuỗi đó: ai đọc repo đều giả được token. Theo spec dòng 104-107, đăng ký khóa chỉ cần đăng nhập: không nhập lại mật khẩu, không throttle, không thông báo khi có khóa mới. Vì vậy chuỗi giả token → thu hồi khóa của người bị giả danh → đăng ký khóa mới → ký thay vẫn cho chữ ký `HOP_LE`. Đây là việc của vai DevOps và mâu thuẫn với lập luận chống chối bỏ ở plan 1.4.
- **Bằng chứng:** settings.py:28, 175-190@staging (không `SIGNING_KEY`, không THROTTLE); cùng chuỗi ở settings của `1_layout_home`, `2_documents`, `3_dossiers_documents`, `4_documents_templates` (dòng 34), `6_tasks` (dòng 29), `7_meeting_rooms_birthdays_system`, `feat/issue-19-organizations`; settings.py:47-50@feat/5-signing-workflow; spec.md dòng 104-107; plan.md dòng 48; apiClient.ts:83@staging. KT trên staging: token HS256 tự ký bằng chuỗi trong repo → GET `/api/auth/profile/` 200 với hồ sơ quản trị; không token → 401.
- **Đề xuất (chờ Trưởng nhóm 5 chốt):** `SECRET_KEY` và `SIMPLE_JWT['SIGNING_KEY']` đọc từ `.env`, bỏ giá trị dự phòng; coi chuỗi hiện tại là đã lộ; `.env.example` hướng dẫn sinh khóa; báo trước cả lớp vì phiên cũ mất hiệu lực. Trong plan Trình ký: đăng ký và xoay vòng khóa bắt nhập mật khẩu và có throttle; kích hoạt, thu hồi, xoay khóa đều tạo thông báo cho chủ khóa và ghi nhật ký; stepper hiện 8 ký tự đầu vân tay khóa. Ghi rõ giới hạn: khóa trên trình duyệt không chống được XSS hay máy bị chiếm.
- **Bên chốt:** Trưởng nhóm 5 (vai DevOps).

#### BM-09 · Trung bình · Nếu demo bằng `approvals`: "chữ ký" là HMAC-SHA256 dùng `SECRET_KEY`, không phải chữ ký số; đổi `SECRET_KEY` hoặc username thì verify thất bại; xóa hồ sơ qua admin xóa theo nhật ký
- **Mô tả:** `approvals` tính `signature_hash` bằng `salted_hmac` (khóa đối xứng của server) trên chuỗi có username. Đây là mã xác thực của server, không gắn với người ký. `SigningRequestAdmin` không chặn quyền xóa, và CASCADE xóa toàn bộ nhật ký của hồ sơ. Chỉ áp dụng nếu trình diễn bằng nhánh `approvals`.
- **Bằng chứng:** approvals/services.py:20, 42, 129-145 (dòng 138, 145), 803, admin.py:46, models.py:333, settings.py:47-50@feat/5-signing-workflow. KT trên dữ liệu seed: hash tính lại khớp ban đầu; `override_settings(SECRET_KEY mới)` → không khớp; đổi username người ký → không khớp; `has_delete_permission` của superuser = True; xóa hồ sơ có 9 nhật ký → còn 0.
- **Đề xuất (chờ Trưởng nhóm 5 chốt):** nếu theo plan Ed25519 thì chuyển các điểm đã làm tốt của `approvals` sang `signing` (băm lại tệp khi ký, nhập lại mật khẩu, view tệp có kiểm quyền, `visible_requests`). Nếu tạm demo bằng `approvals`: dùng `SIGNING_HMAC_KEY` từ `.env`; payload dùng user id; `has_delete_permission=False`; ghi rõ trên UI "Mã xác thực HMAC (không phải chữ ký số)".
- **Bên chốt:** Trưởng nhóm 5.

#### BM-10 · Trung bình · Thao tác ký không yêu cầu xác thực lại: khóa non-extractable trong IndexedDB dùng được ngay cho bất kỳ ai hoặc script nào trong phiên đăng nhập
- **Mô tả:** Payload ký ở plan 7.3 dòng 589 chỉ có `khoa_ky`, `hash_tai_lieu`, `chu_ky_so`, `ghi_chu_ky`; spec dòng 97 chỉ kiểm quyền `ky_trinh_ky`. Khóa non-extractable dùng được ngay sau khi tải lại trang, access token sống 8 giờ, nên người khác ngồi vào máy (ví dụ máy demo dùng chung) hoặc script cùng origin ký thay được bằng một thao tác. Spec gốc d6aa1e5 có "mã PIN/mật khẩu xác nhận", `approvals` kiểm mật khẩu trước khi ký, nhưng bản c1b9704 đã bỏ bước này.
- **Bằng chứng:** plan.md dòng 557, 589; spec.md dòng 97; `git show d6aa1e5:docs/modules/05_signing_workflow/spec.md` dòng 31; approvals/services.py:497-504@feat/5-signing-workflow; settings.py:177@staging. KT Chromium 141: sau reload vẫn có khóa và ký được ngay, không có bước xác nhận; chữ ký verify OK.
- **Đề xuất (chờ Trưởng nhóm 5 chốt):** thêm `mat_khau` vào `POST .../ky`, server `check_password` có throttle, giống `approvals` (phương án ít công hơn). Phương án thay thế là bọc khóa riêng bằng passphrase (PBKDF2 + `wrapKey` AES-KW), tốn công hơn. Ghi vào 3.4, 6.2; thêm test "sai mật khẩu → 400, không tạo chữ ký, không đổi trạng thái".
- **Bên chốt:** Trưởng nhóm 5.

#### BM-11 · Trung bình · Gạch G1: trang tạo trong spec không có ô mức độ và không hiển thị thông tin người tạo; payload POST trong plan không liệt kê `muc_do`
- **Mô tả:** E14 gạch 1 yêu cầu chọn quy trình, hiển thị thông tin người tạo, mức độ; đề md dòng 300 ghi rõ tự động hiển thị thông tin người tạo và thiết lập mức độ khẩn/ưu tiên. Spec mục 4 mục 3 (dòng 122-125) chỉ có chọn quy trình, cách thức ký, hạn chót, đính kèm, định vị chữ ký. Plan dòng 580 không nhắc `muc_do`; người tạo chỉ có `create_by`, không snapshot tên, đơn vị, chức vụ. Spec gốc d6aa1e5 từng có ô Độ khẩn trên form tạo.
- **Bằng chứng:** xlsx ô E14 gạch 1; đề md dòng 300; spec.md dòng 121, 122-125, 126-129; plan.md dòng 286, 297, 580; `grep 'thông tin người tạo'` trên plan.md, spec.md: 0 kết quả; `git show d6aa1e5:docs/modules/05_signing_workflow/spec.md` dòng 125; GET `/api/auth/profile/`@staging đã trả `fullName`, `department`, `position`.
- **Đề xuất (chờ Trưởng nhóm 5 chốt):** thêm vào spec mục 4 mục 3 khối "Người tạo" chỉ đọc (họ tên, đơn vị, chức vụ) và ô "Mức độ" (danh mục ở BM-07). Plan 7.2 liệt kê đủ payload POST: `trich_yeu`, `muc_do`, `kieu_ky`, `han_chot`, `quy_trinh`, vị trí ký. Snapshot `ten_don_vi` như BM-03. Thêm bảng truy vết 6 gạch E14 → mục plan, spec, test vào đầu spec.
- **Bên chốt:** Trưởng nhóm 5.

#### BM-12 · Thấp · Endpoint đọc theo id (manifest, nhật ký) chỉ kiểm permission cấp model; plan không có một quy tắc "ai được xem hồ sơ" dùng chung
- **Mô tả:** Spec dòng 92 giới hạn chi tiết hồ sơ cho người liên quan và quản trị, nhưng dòng 108-109 cho GET audit và GET manifest chỉ yêu cầu `xem_nhat_ky_trinh_ky` hoặc `xem_trinh_ky`. Plan 7.5 dòng 611 chỉ nói giới hạn ở phân trang và lọc. Người có `xem_trinh_ky` đổi id trên URL là đọc được người ký, thời điểm, vân tay khóa, chữ ký của mọi lượt; nhật ký còn có `chi_tiet` và `dia_chi_ip`.
- **Bằng chứng:** spec.md dòng 92, 108-109; plan.md dòng 431, 470-482, 611, 617; approvals/services.py:874-884, views.py:92@feat/5-signing-workflow (`visible_requests`).
- **Đề xuất (chờ Trưởng nhóm 5 chốt):** thêm vào mục 8 hàm `co_quyen_xem(user, trinh_ky)` (người tạo, người ký ở mọi lượt, người ủy quyền, người có quyền xem toàn bộ); dùng chung cho chi tiết, manifest, audit, tệp (LUONG-01) và thread; không có quyền thì trả 404. Thêm test người không liên quan GET manifest và audit nhận 404.
- **Bên chốt:** Trưởng nhóm 5.

#### BM-13 · Thấp · `signing_key` không được khai báo bất biến: khóa công khai, vân tay, chủ sở hữu sửa được
- **Mô tả:** Plan 3.4 (dòng 139-146) và 5.2 (dòng 379-399) chỉ ràng buộc trạng thái `HOAT_DONG`; không quy định khóa công khai, vân tay, chủ sở hữu, thuật toán là bất biến sau khi tạo. Model không có `save()` chặn sửa như `SigningSignature`. Vì chữ ký chỉ trỏ FK tới `khoa_ky` và manifest chỉ lưu vân tay, sửa bản ghi khóa (ví dụ qua trang admin dựng cho demo theo PHA-04) làm chữ ký cũ không verify được hoặc trông như của người khác.
- **Bằng chứng:** plan.md dòng 139-146, 379-399, 408, 431; models.py@1a6fcc9 dòng 363-392 (không có save/delete riêng) so với 429-437. KT: đổi `khoa_cong_khai` và `nguoi_so_huu` rồi `save()` → thành công; `SigningKey` không override `save`, `SigningSignature` có.
- **Đề xuất (chờ Trưởng nhóm 5 chốt):** ghi vào 3.4: sau khi tạo khóa chỉ được cập nhật `trang_thai`, các mốc thời gian, `khoa_thay_the`, `ghi_chu`. Thêm `save()` chặn sửa các cột còn lại; admin để readonly. Manifest lưu cả khóa công khai (DL-04). Thêm test "đổi `khoa_cong_khai` → BatBienError".
- **Bên chốt:** Trưởng nhóm 5 (chốt); thành viên Nhóm 5 (code).

## 9. Các điểm cần chốt

### 9.1. Trưởng nhóm 5

Nhóm A – chốt trước khi code Pha 2:

1. Nền triển khai: `signing` là đích, `approvals` giữ ở nhánh riêng làm bản demo dự phòng và nguồn tái dùng; tên app (`signing` hay `approvals`) và prefix API (HT-01, TH1-02).
2. Đồng bộ staging vào `5_signing_workflow` theo cách ở HT-01 (5 tệp conflict lấy bản staging, gỡ `AGENTS.md` và `.agents`).
3. Nguồn tệp trình ký: phương án A (Nhóm 5 tự giữ PDF dự thảo, `van_ban` cho phép rỗng) hay giữ FK bắt buộc; server tự tính mã băm; API tệp (TH2-01, LUONG-01).
4. Dữ liệu nháp: phương án A (lượt `NHAP` tạo sớm) hay B (JSON trên `signing_request`); tọa độ cho phép rỗng trong M1; thêm PATCH, DELETE nháp (LUONG-02, PHA-06).
5. Máy trạng thái:
   - Thêm điều kiện chung ở 6.2 và chốt người đã `DA_KY` có được `yeu_cau_sua` không (LUONG-03).
   - Thêm hàm dừng lượt và sơ đồ trạng thái cho cấp và người ký (LUONG-04).
   - Sửa dòng 159, 184.
6. Contract hành động theo `signer_id`; cấm một tài khoản xuất hiện hai lần trong lượt; ủy quyền tạo dòng mới; liên kết dòng cấu hình (LUONG-05, LUONG-06, DL-08).
7. Bất biến và ràng buộc CSDL:
   - Chặn sửa mã băm của lượt; các partial unique (DL-01).
   - Mỗi văn bản tối đa một yêu cầu đang chạy (LUONG-14).
   - `signing_key` bất biến (BM-13); dấu thu hồi trên chữ ký (DL-06); CHECK, ordering và chú thích SQL của model (DL-05).
8. Bổ sung `ma_ho_so`, `trich_yeu`, `muc_do` (4 mức theo NĐ30), `ten_don_vi`/`don_vi_id`, `signing_process.don_vi_ap_dung`; trạng thái hiển thị và tham số `trang_thai` (BM-03, BM-07, BM-11).

Nhóm B – chốt cho mốc M1:

9. Mốc M1 chia M1a/M1b hay thêm M0 bằng `approvals`; dời Celery, Redis, PostgreSQL, phẳng hóa, adapter pháp lý sang giai đoạn sau; ngày cụ thể của từng mốc (PHA-01, PHA-02, HT-02).
10. Chữ ký số (BM-02, BM-04, BM-10):
    - Thông điệp ký chuẩn hóa có ngữ cảnh và kiểm chủ khóa.
    - Challenge bằng `TimestampSigner`.
    - Khóa WebCrypto non-extractable trong IndexedDB; mất khóa thì thu hồi và đăng ký lại.
    - Nhập lại mật khẩu khi đăng ký khóa, xoay khóa và khi ký.
11. Ảnh chữ ký: Nhóm 5 tự giữ hay chờ nhóm khác nhận bằng văn bản có ngày (TH7-02).
12. Thông báo: bảng "sự kiện → người nhận → kênh", các trường mới, trạng thái `DA_HUY`, 2 API (BM-01).
13. Phân quyền: thêm 3 quyền, khai báo `Meta.permissions`, `default_permissions` chỉ có `view` cho 3 bảng bất biến; hàm `co_quyen_xem` dùng chung (TH1-01, BM-12).
14. Người ký theo chức vụ: MVP chỉ hỗ trợ theo tài khoản, trả mã lỗi rõ ràng cho chức vụ (TH7-03).
15. Văn bản MẬT: loại khỏi MVP hay thêm cờ và quy tắc phạm vi (BM-05).

Nhóm C – phần mở rộng và hạ tầng:

16. Hạn xử lý: tính lúc mở cấp; `han_chot` rỗng nghĩa là gì; endpoint đổi hạn (LUONG-07).
17. Thu hồi, `xem_xet_lai`, manifest, nút Phát hành, `Idempotency-Key`: giữ trong MVP hay dời; có bỏ `xem_xet_lai` không (LUONG-08, LUONG-11, DL-02, DL-04, TH2-02).
18. Hạ tầng chung với vai DevOps (HT-03, HT-04, HT-06, HT-08, HT-11, BM-08):
    - Email chạy được trên cả Django 5.2 và 6.1.
    - `SECRET_KEY` và khóa JWT chuyển ra `.env`; SQLite `IMMEDIATE`.
    - CI; sửa PR template, Quality Gate, README (Node ≥22.22.2).
    - Danh sách tệp chung được phép sửa.
    - Danh sách việc DevOps riêng.
19. Trình Giảng viên bảng "gạch E14 → tính năng → bảng/trường → mốc" trước mọi PR schema lên staging (PHA-03).

### 9.2. Các nhóm khác và PM

- **PM:**
  - Một hàm `is_admin` dùng chung (TH1-01).
  - Quyết định về `AUTH_USER_MODEL` cùng Nhóm 7 (TH7-01).
  - Định dạng lỗi API chung (TH1-05).
  - Reviewer dự phòng cho PR vào staging do Trưởng nhóm 5 mở (HT-12).
  - Theo dõi việc đồng bộ staging của các nhánh nhóm (HT-09).
  - Xác nhận phạm vi "production" (HT-11).
- **Nhóm 1:**
  - Thêm loại `signing` vào chuông header (BM-01).
  - `ProtectedRoute` nhớ trang đích; `apiClient` lưu refresh token mới; tách `apiClient.download` và `apiClient.getBlob` (TH1-03, TH1-04).
  - Settings email, MEDIA, `SECRET_KEY` cùng Trưởng nhóm 5 (HT-04, BM-08).
  - Lệnh seed tài khoản chung (HT-13).
  - Sửa nội dung chatbot trên staging theo mô tả của Nhóm 5 (TH2-02).
- **Nhóm 2:**
  - Đồng ý phương án A (TH2-01).
  - Bắt `ProtectedError` trả 409 (TH7-04).
  - Kiểm quyền PUT/PATCH/DELETE cho mọi loại; khóa trường `loai` (TH2-01, TH2-04).
  - Endpoint tải tệp có kiểm quyền trước khi bỏ `static()`, tên tệp uuid (BM-06).
  - Tách `can_view_document` (BM-05).
  - `UniqueConstraint(loai, nam, so_thu_tu)`; default năm callable (TH2-03).
  - Cập nhật README theo code (TH2-05).
  - Hẹn ngày merge `2_documents` lên staging; xử lý văn bản MẬT khi người ký không thuộc `nguoi_nhan`.
- **Nhóm 3:** văn bản đi sinh từ trình ký gắn vào Hồ sơ và Loại văn bản nào (mục 7.3).
- **Nhóm 4:** SQLite mặc định, một biến và một driver cho PostgreSQL (HT-05); hướng dẫn xuất Tờ trình sang PDF (mục 7.4).
- **Nhóm 6:**
  - Dùng chung cấu hình email và cơ chế nhắc hạn (HT-07).
  - Requirements UTF-8, không dán nguyên `pip freeze`; một dòng `CORS_ALLOW_HEADERS` chung (HT-06, TH1-03).
  - Đồng bộ staging, bỏ `frontend/skills/` (HT-09).
- **Nhóm 7:**
  - Không đổi `AUTH_USER_MODEL` (TH7-01).
  - Ngày cam kết cho ChucVu và CBNV; tên model và trường; API chỉ đọc cho nhân sự, chức vụ, đơn vị (TH7-03).
  - "Xóa" nghĩa là vô hiệu hóa; trả 409 khi đang bị tham chiếu; endpoint ghi kiểm `has_perm` (TH7-04).
  - Nhóm quyền lưu bằng `user.groups`; nhận 11 quyền của Nhóm 5 vào ma trận phân quyền (TH1-01, TH7-06).
  - CBNV là nguồn sự thật cho hồ sơ cán bộ (TH7-05).
  - Ai làm ảnh chữ ký (TH7-02).
  - Thay đổi `apiClient.ts` đi qua PR có Nhóm 1 review (TH1-04).
- **Nhóm 8:** sửa nội dung chatbot (bỏ Token/HSM, bỏ tự sinh số văn bản đi, dùng đúng danh sách trạng thái) và tên bảng trong `sql_document_source` (TH2-02, mục 7.7); đồng bộ cấu trúc project với staging (HT-09).

### 9.3. Giảng viên

- Duyệt danh sách trường và phạm vi theo F14, gồm bảng truy vết 6 gạch E14 và danh sách phần mở rộng (Ed25519, ký nháy/ký chính, ủy quyền, manifest, phát hành pháp lý) (PHA-03).
- Phần mở rộng có được tính vào đánh giá không, hay nhóm nên tập trung đủ 6 gạch E14 trước.
- Người tạo có được tự chọn `SONG_SONG` cho mọi quy trình không (LUONG-12).
- "Production" trong vai trò DevOps là nhánh `main` hay một môi trường chạy thật (HT-11).
- Yêu cầu về giá trị pháp lý của "chữ ký số nội bộ" Ed25519 so với chữ ký số có chứng thư CA (plan mục 1.4).

## 10. Giới hạn của đánh giá

- Chỉ đọc được bản fork dạng shallow clone; không đọc được repo gốc (GitHub API trả 403). Upstream có thể đã có PR hoặc merge mới hơn (ví dụ `2_documents` lên staging, Nhóm 7 có ChucVu/CBNV) hoặc branch protection khác.
- Chưa có bằng chứng Giảng viên đã duyệt danh sách trường theo F14; PHA-03 chỉ khẳng định "repo không có ghi nhận". Chưa biết hạn nộp, ngày báo cáo và ngày demo cụ thể; chỉ biết chu kỳ báo cáo 2 tuần.
- Chưa chạy trên Windows: Task Scheduler, `CHAY_FULL_STACK.bat`, đường dẫn `MEDIA_ROOT`. Nhận định Celery/Redis không được hỗ trợ chính thức trên Windows lấy theo tài liệu của các dự án đó, chưa thử trên máy nhóm.
- Chưa chạy trên PostgreSQL; các nhận định về khóa dòng chỉ kiểm trên SQLite.
- Chưa chạy end-to-end trên trình duyệt thật với backend; vòng đời khóa mới thử trên trang giả với Chromium 141. Chưa thử Firefox, Safari, Edge.
- Kịch bản máy trạng thái chạy trên service tối giản cài theo chữ plan, vì `feat/signing-models` chưa có service; kết quả phản ánh đặc tả, không phản ánh code sẽ viết.
- Chưa thử thư viện phẳng hóa PDF, lớp phủ pdf.js và hệ tọa độ khung ký.
- Nhận định "jsdom không có IndexedDB" là đặc điểm đã biết của jsdom, chưa chạy lại trong lần đối chiếu này.
- Tích hợp Nhóm 3 và Nhóm 4 mới kiểm sơ bộ (model, settings); chưa kiểm định dạng biểu mẫu Tờ trình hay giao diện của hai nhóm. Nhóm 8 chưa kiểm cách kết nối DB thật.
- Thay đổi của GitHub về `pull_request_target` lấy theo thông báo thay đổi, chưa kiểm trực tiếp trên repo gốc.
- Ước lượng ngày công và tỷ lệ tái dùng `approvals` là suy luận theo khối lượng code, chưa kiểm chứng.
- Chưa kiểm số hiệu và nội dung các văn bản pháp luật nhắc trong plan mục 1.4, chưa kiểm chính sách lưu IP và dữ liệu cá nhân trong nhật ký.

## Phụ lục A. Nhận định đã loại sau kiểm chứng

Các nhận định dưới đây từng được nêu trong quá trình đánh giá nhưng không đứng vững khi kiểm lại, hoặc đã được sửa thành dạng hẹp hơn. Chúng không nằm trong danh sách vấn đề ở mục 8.

**Về luồng và máy trạng thái**
- "Pha 2 phụ thuộc vòng vào Pha 3": không đúng. Đây là phụ thuộc thuận chiều; Pha 2 test được hàm đánh dấu `DA_KY` bằng stub, Pha 3 thêm phần verify (đã phản ánh ở PHA-01).
- "Plan không có quy tắc khi nhiều người cùng yêu cầu sửa": không đúng. Theo 6.1, lượt `YEU_CAU_SUA` là trạng thái kết thúc và 5.3 dòng 528 chỉ cho một hành động đồng thời.
- "Lượt đang `YEU_CAU_SUA` rồi có người bấm `tu_choi`": đã bị 6.1 chặn.
- "Lối thoát dòng 159 không thực hiện được": không đúng theo chữ plan. Người đã ký vẫn bấm được `yeu_cau_sua` vì 6.2 không đặt điều kiện; lối thoát chỉ mất nếu siết điều kiện (LUONG-03).
- "Người nhận ủy quyền vừa nhận đã trễ hạn vì `thoi_diem_mo` giữ nguyên": không đúng. Trễ hạn tính theo `han_xu_ly` của cấp (dòng 175), không theo `thoi_diem_mo` (LUONG-06).
- "Ủy quyền làm hỏng chống chối bỏ": nói quá. Chữ ký vẫn truy được người thật qua `khoa_ky.nguoi_so_huu` và nhật ký; phần bị ảnh hưởng là hiển thị và kiểm toán.
- "Người ký nghỉ việc thì không ai ủy quyền được": không đúng. Dòng 180 cho quản trị hoặc lãnh đạo phụ trách ủy quyền thay.
- "Người tạo tự yêu cầu sửa hồ sơ do chính người đó tạo là lỗi": không đúng. Khi người tạo đồng thời là người ký (dòng 87), việc này không phá bất biến nào.
- "Không rõ ai được `xem_xet_lai`": sai một phần. Spec dòng 95 đã gán quyền `gui_trinh_ky` cho hành động này.
- "Lịch sử từ chối theo từng lượt không xem lại được": không đúng. Thông tin nằm ở `ly_do_tu_choi` của dòng người ký và `signing_change_thread.ly_do`.
- "Một người ở hai cấp luôn gây mơ hồ": chỉ đúng ở `SONG_SONG` và khi quản trị ủy quyền thay; ở `TUAN_TU` server suy được dòng đang mở (LUONG-05).
- "Nhắc hạn luôn được gửi sau khi hủy": chỉ là suy luận có điều kiện; chỉ xảy ra nếu bản ghi nhắc được tạo trước với giờ hẹn.
- "Thông báo khóa ký sắp hết hạn không lưu được": không phải vấn đề, plan không yêu cầu loại thông báo này (dòng 638).
- "Idempotency cho `nhan-ban`, POST requests, POST messages là chỗ plan tự mâu thuẫn": không đúng theo chữ dòng 204; các thao tác này không phải "chuyển trạng thái".
- "Retry đúng khóa nhận 409": plan chưa định nghĩa phản hồi khi retry; 409 chỉ là một cách cài (DL-02).
- "Theo plan thì client tính mã băm": plan chưa quy định ai tính; chỉ spec dòng 124 nghiêng về client (LUONG-01).

**Về dữ liệu và bảo mật**
- "Admin xóa hàng loạt chữ ký hoặc nhật ký qua Django admin": hiện chưa xảy ra được vì app `signing` chưa có `admin.py`; đường vượt qua thật là `QuerySet.update/delete` (DL-01).
- "Tệp PDF hoàn tất không được ai ký là lỗi": không đúng; đây là thiết kế Lazy Stamping có chủ ý. "Manifest không kiểm độc lập được" là nói quá, chữ ký cộng khóa công khai đủ để verify từng chữ ký.
- "Ảnh chữ ký lãnh đạo bị lộ qua `/media/`": chưa nhánh nào lưu ảnh chữ ký với tên đoán được; `approvals` dùng uuid và không trả URL. Phần lộ thực tế là tệp của Nhóm 2 (BM-06).
- "Tệp Nhóm 2 bị ghi đè bytes tại cùng đường dẫn": không đúng ở hiện tại; Django tự thêm hậu tố khi trùng tên.
- "LocMem không có thao tác đọc-và-xóa nguyên tử": không chính xác; vấn đề thật là cache LocMem tách theo tiến trình và mất khi khởi động lại.
- "Lưu tệp Trình ký ở kho riêng ngoài `MEDIA_ROOT`": vi phạm structure.md mục 7.1; đã sửa thành `MEDIA_ROOT/05_signing`, tên uuid, phục vụ qua API có kiểm quyền.
- "Bằng chứng ghi chức vụ giả từ payload đăng nhập": chưa xảy ra; `profile_info` của `approvals` đọc thẳng `StaffProfile` (TH7-05).

**Về đề bài và phân pha**
- "API danh sách không có bộ lọc trạng thái": không đúng; spec dòng 38, 120 có, chỉ plan 7.2 thiếu (BM-07).
- "Lọc phòng ban và tìm kiếm không làm được": nói quá; làm tạm được bằng join qua hồ sơ người tạo. Chỗ thiếu thật là không có snapshot và mã hồ sơ (BM-03).
- "Cần hỏi Giảng viên mức độ là độ khẩn hay độ mật": không cần; đề md dòng 300 đã ghi "mức độ khẩn/ưu tiên".
- "Tab toàn bộ hồ sơ mâu thuẫn với thẻ Đã hoàn tất": không đúng; một bên là tab, một bên là thẻ đếm.
- "Pha 1 không tách được lược đồ": sai về kỹ thuật, Django cho phép `AddField` ở migration sau; lược đồ đã xong.
- "Pha 3 bị chặn vô thời hạn vì thiếu ảnh chữ ký": nói quá; cột ảnh cho phép rỗng nên lõi ký vẫn làm được (TH7-02).
- "Test chức vụ trống (dòng 661) không viết được": không đúng; viết được bằng resolver giả (TH7-03).
- "FK bắt buộc buộc phải tạo văn bản đi giả": plan không chỉ định loại văn bản; nói đúng hơn là loại nào cũng có nhược điểm (TH2-01).
- "Frontend chiếm hơn 50% khối lượng": đã thay bằng số đo cụ thể: trong `approvals`, phần frontend chiếm khoảng 56% số dòng thêm của hai thư mục `frontend/` và `backend/` (khoảng 51% nếu tính mọi tệp), là chỉ số gần đúng (mục 5.2, PHA-01).
- "Redis/Celery/PostgreSQL là quyết định đã chốt của plan": không đúng; dòng 58 gắn nhãn `[ĐỀ XUẤT]`, dòng 760 tự ghi `[BỊ CHẶN]`.
- "DoD dòng 770 chặn hẳn việc đăng ký app": nói quá; câu chữ mơ hồ (HT-06).
- "Phương án tạm tìm theo mã hồ sơ": không làm được khi chưa có trường `ma_ho_so`.

**Về tích hợp và hạ tầng**
- "Đề có khoảng 92 đơn vị cấp 2": sai số liệu; đề có 82 đơn vị cấp 2. `max_page_size=100` vì vậy không phải điểm chặn (TH7-03).
- "Endpoint khu vực của Nhóm 7 trả 409": không đúng; endpoint trả 400 kèm key i18n.
- "Dashboard Nhóm 1 sẽ hiện dự thảo trình ký": không đúng ở hiện tại; dashboard dùng model tạm riêng.
- "`SessionAuthentication` của Nhóm 2 làm luồng refresh token không chạy": phóng đại; request có Bearer hết hạn nhận 401 từ JWT trước. Lỗi 403 CSRF chỉ xảy ra khi request không có Bearer (TH2-03).
- "Nhóm 4 làm `check` lỗi ngay": chưa chính xác; `check` chỉ lỗi khi chưa cài driver, còn test và migrate lỗi khi không có PostgreSQL server (HT-05).
- "Tệp `team-pr-review.yml` cũ trên nhánh 5 bỏ qua PR `feat` → `5_signing_workflow`": không còn đúng theo thông báo thay đổi của GitHub về `pull_request_target`; phần đúng là PR vào staging do Trưởng nhóm 5 mở không có reviewer (HT-12).
- "Staging thay đổi liên tục": không có bằng chứng; tip staging vẫn là 37a2729 từ 2026-09-20.
- "Plan có nhắc PR hoặc staging ở Pha 6": không đúng; plan không nhắc staging, PR hay merge ở bất kỳ đâu (HT-10).
- "Requirements trên mọi nhánh không có `cryptography`": chưa đúng; requirements UTF-16 của `6_tasks` có `cryptography==49.0.0` (HT-02).
- "Hai app `approvals` và `signing` cùng ghi vào `media/05_signing`": không đúng; app `signing` chưa có `FileField` nào (HT-01).
- "Lỗi email bị nuốt, không để lại dấu vết": không đúng; traceback in ra console của runserver, chỉ giao diện không báo (HT-04).
- "Xung đột router với Nhóm 6 do hai route nằm liền nhau": nguyên nhân chính là `6_tasks` dựng trên commit cũ (HT-07).
- "Nội dung Token/HSM nằm trong `business_knowledge.py` của Nhóm 8": không đúng; tệp đó chỉ tóm tắt spec cũ. Nội dung Token/HSM nằm ở `AiAssistantPage.tsx` của nhánh `8_ai_chatbox` và trên staging (TH2-02).
- "Con số `views.py` của `approvals` khoảng 970 dòng": sai; `views.py` có 544 dòng, 970 là tổng của views và serializers.
