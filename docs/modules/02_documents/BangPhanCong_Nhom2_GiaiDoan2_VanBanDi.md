# TRƯỜNG CAO ĐẲNG CÔNG NGHỆ THÔNG TIN TP.HCM (ITC)
## KHOA CÔNG NGHỆ THÔNG TIN
***

# BẢNG PHÂN CÔNG NHIỆM VỤ THÀNH VIÊN
## GIAI ĐOẠN 2: PHÂN HỆ VĂN BẢN ĐI (OUTGOING DOCUMENTS)
**Đồ Án Tốt Nghiệp:** Hệ Thống Quản Lý Văn Bản & Tài Liệu (TLBM System)  
**Phân hệ:** `2_DOCUMENTS` (Nhóm 2) | **Branch nhóm:** `2_documents`  
**Giảng viên hướng dẫn:** NCS.ThS. Trần Phương Duy | **Nhóm trưởng:** Lê Trí Kiệt  
**Ngày lập kế hoạch:** 03/10/2026  

---

## I. NGUYÊN TẮC PHÂN CHIA VÀ ĐẶC THÙ NGHIỆP VỤ VĂN BẢN ĐI

- **Phân chia đồng đều 25% / thành viên:** 4 thành viên phụ trách đúng 25% khối lượng đồ án. Trách nhiệm được phân bổ theo mô hình Clean Architecture (Backend Core & Model, Backend Business & Excel, Frontend Display & Filter, Frontend Forms & Upload) nhằm tối đa hóa tính chuyên sâu và không giẫm chân lên nhau.
- **Quy chế Git — Làm việc trên Fork cá nhân:** Theo đúng tài liệu `HuongDan_Git_Workflow.md`, thành viên `team_2` nhận quyền **Read** trên repository tổ chức `QuanLyVanBanTLBM/QuanLyVanBan_TLBM`. Vì vậy, **100% thành viên bắt buộc phải tự Fork repository về tài khoản cá nhân**, lập feature branch (`feat/vanban-di-...`) trên fork để code và commit. Tiến độ và công sức 25% của từng người được Giảng viên theo dõi trực tiếp qua commit history trên fork cá nhân.
- **Quy trình tích hợp qua Pull Request (PR):** Sau khi hoàn thành task trên fork cá nhân, thành viên mở Pull Request về branch nhóm `QuanLyVanBanTLBM/QuanLyVanBan_TLBM:2_documents`. Nhóm trưởng (Lê Trí Kiệt) có quyền **Write** thuộc `team_leads` sẽ thực hiện kiểm tra chất lượng (code review, test suite, lint, i18n, WCAG typography) và merge vào branch nhóm.
- **Bảo toàn tuyệt đối Giai đoạn 1 (Văn bản Đến Freeze):** Nhánh `vanban_den` đã hoàn thành 100% và đang chờ Giảng viên đánh giá. Toàn bộ mã nguồn, dữ liệu test và cấu hình của Giai đoạn 1 được đóng băng hoàn toàn, không có bất kỳ regression hay xung đột nào.
- **Nguồn gốc nội bộ trường học:** Văn bản đi bắt nguồn từ các đơn vị thuộc trường (Phòng/Khoa/Trung tâm trong bảng `organizations_donvi`). Cột "Nơi ban hành" thể hiện rõ đơn vị soạn thảo và phát hành trong trường.
- **Cơ chế cấp Số đi (`so_thu_tu`) tự động & Bất biến:** Số đi tự tăng liên tục theo từng năm (`nam`). Backend triển khai cơ chế transaction lock chống xung đột đồng thời (concurrency-safe). Khi chỉnh sửa văn bản, trường Số đi bị khóa cứng (Read-Only) để bảo toàn tính pháp lý hành chính.
- **Thời điểm ban hành (`ngay_ban_hanh`):** Bắt buộc nhập theo chuẩn `DateTimeField` (lấy đủ ngày, tháng, năm, giờ, phút, giây theo đúng yêu cầu nghiêm ngặt của Giảng viên hướng dẫn trong file PDF đặc tả).
- **Phạm vi lưu hành và công khai:** Văn bản đi mặc định hiển thị công khai nội bộ (`hien_thi = True`) cho toàn thể cán bộ, giảng viên trong trường vào tra cứu và thực hiện. Có cờ tùy chọn gửi email thông báo toàn hệ thống.

---

## II. BẢNG PHÂN CÔNG TỔNG QUAN GIAI ĐOẠN 2 (DÙNG ĐIỀN LINK/FILE THEO DÕI CỦA THẦY)

| STT | Thành viên | Vai trò | Trọng trách & Nhiệm vụ chính | Mô tả nhiệm vụ (Điền link của Thầy) | Sản phẩm đầu ra (Deliverables) | Tỉ lệ |
| :---: | :--- | :--- | :--- | :--- | :--- | :---: |
| **1** | **Lê Trí Kiệt**<br>*(Trưởng nhóm)* | **Backend Core & Bảo mật** | • Quản trị Model `VanBanDi` (`documents_vanbandi`) và các bảng trung gian (`attachment`, `donvinhan`, `nguoinhan`, `danhmuc`, `hoso`).<br>• Ràng buộc `uq_vanbandi_nam_stt` và `chk_vanbandi_link_thay_the`.<br>• Xây dựng `VanBanDiSerializer` & Base CRUD API chuẩn RESTful (`/api/documents/di/`).<br>• Thiết lập phân quyền lưu hành nội bộ trường.<br>• Quản trị Git: Review & Merge PR từ fork của các thành viên vào branch `2_documents`. | **Phụ trách Backend Core & Bảo mật (Giai đoạn 2 - Văn bản Đi):** Quản trị CSDL bảng `documents_vanbandi` và các bảng quan hệ liên kết; đảm bảo tính toàn vẹn ràng buộc số đi theo năm và hiệu lực văn bản; xây dựng Base CRUD API chuyên biệt (`/api/documents/di/`) chuẩn RESTful; cài đặt phân quyền lưu hành nội bộ trường học; chịu trách nhiệm kiểm tra, review kỹ thuật và merge các Pull Request từ fork cá nhân của thành viên vào branch nhóm `2_documents` an toàn. | • Model `VanBanDi` & `Attachment`<br>• API `/api/documents/di/`<br>• Serializer & Validation Core<br>• Quản trị Git PR & Review | **25%** |
| **2** | **Nguyễn Anh Đô** | **Backend Service & Logic Dữ liệu** | • Xây dựng dịch vụ cấp Số Đi tự động (`so_thu_tu`) chống xung đột concurrency bằng transaction lock.<br>• Khóa cứng Số đi không cho sửa khi cập nhật văn bản.<br>• Xây dựng bộ lọc nâng cao `VanBanDiFilter` (năm, ngày ban hành, nơi ban hành, hiệu lực, người ký).<br>• Dịch vụ Excel: Tạo file mẫu từ DB, Import kiểm tra dữ liệu và Export theo bộ lọc.<br>• API ghi nhận lịch sử người xem (ViewLog) và Unit Test suite. | **Phụ trách Backend Services & Logic Dữ liệu (Giai đoạn 2 - Văn bản Đi):** Phát triển thuật toán tự sinh Số đi tự tăng theo năm an toàn concurrency (transaction locking); logic khóa cứng số đi khi cập nhật; xây dựng bộ lọc đa tiêu chí `VanBanDiFilter`; phát triển dịch vụ Nhập/Xuất Excel riêng cho Văn bản Đi kèm tự sinh template từ CSDL; API ghi nhận danh sách người đã xem và hoàn thiện bộ kiểm thử tự động (Unit Tests); thực hiện trên fork cá nhân và mở PR. | • Service cấp Số đi concurrency<br>• `VanBanDiFilter` nâng cao<br>• Service Excel (Template/Import/Export)<br>• API ViewLog & Bộ Unit Tests | **25%** |
| **3** | **Nguyễn Tấn Lộc Khiêm** | **Frontend View & Hiển thị** | • Xây dựng trang Văn bản Đi (`OutgoingPage.tsx`) và tích hợp vào router `/van-ban-di`.<br>• Dựng Bảng hiển thị `DocumentTable` chuyên biệt cho Văn bản Đi (Số đi, Số hiệu, Ngày ban hành, Nơi ban hành, Trích yếu, Hiệu lực, Đính kèm, Tác vụ ⋮).<br>• Đảm bảo chuẩn Typography WCAG (>= 13px, độ tương phản cao, không lỗi token).<br>• Xây dựng thanh công cụ lọc `FilterBar`.<br>• Xây dựng Modal xem chi tiết và Modal danh sách người đã đọc. | **Phụ trách Frontend View & Hiển thị (Giai đoạn 2 - Văn bản Đi):** Xây dựng trang `OutgoingPage` tích hợp menu chính; phát triển Bảng danh sách văn bản đi với đầy đủ cột nghiệp vụ đặc thù; tích hợp menu tác vụ 3 chấm ⋮; xây dựng thanh `FilterBar` đa năng (tìm kiếm, chọn năm, khoảng ngày ban hành, phòng ban, hiệu lực); Modal xem chi tiết văn bản đi (kèm preview file) và Modal theo dõi danh sách cán bộ đã đọc; đảm bảo chuẩn WCAG Typography (>= 13px); thực hiện trên fork cá nhân và mở PR. | • `OutgoingPage.tsx`<br>• `DocumentTable` (Văn bản Đi)<br>• Outgoing `FilterBar`<br>• Modal Chi tiết & Người đã đọc | **25%** |
| **4** | **Trần Nhật Tân** | **Frontend Input & Nhập liệu** | • Xây dựng Modal Form Thêm mới / Cập nhật Văn bản Đi (`OutgoingFormModal.tsx`).<br>• Cơ chế gợi ý Số đi tự tăng, khóa cứng trường Số đi khi chỉnh sửa.<br>• Tự động gợi ý chuỗi Số ký hiệu chuẩn quy cách trường (VD: `.../QĐ-CĐCNTT`).<br>• Dropdown Phòng/Khoa ban hành và cascading Đơn vị nhận -> Cán bộ nhận.<br>• Khu vực kéo thả tải nhiều tệp đính kèm an toàn.<br>• Xây dựng Modal Import Excel và Export Excel. | **Phụ trách Frontend Input & Nhập liệu (Giai đoạn 2 - Văn bản Đi):** Xây dựng Popup Form thêm mới và chỉnh sửa văn bản đi; cơ chế tự động gợi ý số đi và khóa cứng Số đi khi sửa; gợi ý chuỗi số ký hiệu; dropdown chọn Phòng/Khoa ban hành nội bộ; cascading Đơn vị nhận ➔ Cán bộ nhận; khu vực kéo thả upload nhiều file đính kèm an toàn; xây dựng giao diện Import Excel (kèm tải file mẫu và xem trước dữ liệu) và nút Xuất Excel; thực hiện trên fork cá nhân và mở PR. | • `OutgoingFormModal.tsx`<br>• Logic khóa Số đi & Gợi ý ký hiệu<br>• File Attachment Dropzone<br>• Modal Import & Export Excel UI | **25%** |

---

## III. BẢNG CHI TIẾT HẠNG MỤC CÔNG VIỆC VÀ MÔ HÌNH FORK GIT (GIAI ĐOẠN 2)

| Thành viên & Nơi Push | Nhiệm vụ cụ thể ở Văn Bản Đi | Chi tiết các hạng mục công việc triển khai | Branch Feature trên Fork & Target PR |
| :--- | :--- | :--- | :--- |
| **Lê Trí Kiệt**<br>*(Trưởng nhóm)*<br><br>• *Quyền:* Write<br>• *Repo:* Nhóm 2 / Upstream | **Backend Core Văn bản Đi & Điều phối Git** | 1. Kiểm tra bảng vật lý `documents_vanbandi` và các bảng quan hệ liên kết (`noibanhanh`, `donvinhan`, `nguoinhan`, `danhmuc`, `hoso`, `attachment`) bảo đảm khớp 100% file SQL chuẩn của đề án.<br>2. Kiểm soát chặt chẽ ràng buộc toàn vẹn `uq_vanbandi_nam_stt` (`nam`, `so_thu_tu`) và ràng buộc hiệu lực `chk_vanbandi_link_thay_the`.<br>3. Xây dựng `VanBanDiSerializer` và `DocumentCreateUpdateSerializer`: validate các trường bắt buộc (`ngay_ban_hanh`, `trich_yeu`, `so_hieu`, `noibanhanh`).<br>4. Xây dựng ViewSet riêng biệt `VanBanDiViewSet` tại `/api/documents/di/` (kế thừa `ModelViewSet`) và giữ tính tương thích đồng bộ với facade chung `/api/documents/?loai=DI`.<br>5. Thiết lập logic phân quyền lưu hành nội bộ trường: Toàn bộ cán bộ nhân viên được tra cứu văn bản công khai (`hien_thi=True`), chỉ người tạo hoặc Văn thư/Admin mới có quyền sửa/xóa.<br>6. Quản trị nhánh Git `2_documents`, trực tiếp review kỹ thuật và merge các Pull Request từ fork của 3 thành viên. | • **Branch:** `feat/vanban-di-backend-core`<br>• **Target:** `upstream/2_documents`<br>• **Người merge:** Lê Trí Kiệt |
| **Nguyễn Anh Đô**<br><br>• *Quyền:* Read<br>• *Nơi push:* Fork cá nhân | **Backend Service Văn bản Đi** | 1. Viết dịch vụ cấp Số Đi tự động an toàn concurrency: `generate_so_thu_tu('DI', nam)` sử dụng transaction `select_for_update()` chống race condition khi nhiều văn thư cùng thao tác.<br>2. Cài đặt nghiệp vụ bất biến: Khóa cứng `so_thu_tu` và `nam`, chặn hoàn toàn việc sửa đổi số đi qua form cập nhật (PUT/PATCH).<br>3. Xây dựng bộ lọc nâng cao `VanBanDiFilter`: lọc theo Năm, khoảng ngày ban hành (`tu_ngay` - `den_ngay`), nơi ban hành nội bộ, người ký, đơn vị nhận, tình trạng hiệu lực.<br>4. Xây dựng module Excel Văn bản Đi: Tự sinh file Excel mẫu chuẩn cấu trúc Văn bản Đi từ DB; API Import Excel kiểm tra từng dòng và tự cấp số; API Export Excel theo đúng bộ lọc.<br>5. Xây dựng endpoint ghi nhận và truy vấn lịch sử người đã xem Văn bản Đi (`/api/documents/di/{id}/viewers/`).<br>6. Viết bộ Unit Tests & Integration Tests kiểm thử tự động cho toàn bộ phân hệ Văn bản Đi, bảo đảm test suite đạt 100% PASS. | • **Fork:** `<do-user>/QuanLyVanBan_TLBM`<br>• **Branch:** `feat/vanban-di-services-excel`<br>• **Target PR:** `upstream/2_documents`<br>• **Reviewer:** Lê Trí Kiệt |
| **Nguyễn Tấn Lộc Khiêm**<br><br>• *Quyền:* Read<br>• *Nơi push:* Fork cá nhân | **Frontend View Văn bản Đi** | 1. Khởi tạo trang Văn bản Đi (`OutgoingPage.tsx`), tích hợp vào thanh điều hướng Sidebar và router `/van-ban-di`.<br>2. Tích hợp hook gọi API Văn bản Đi với đầy đủ cơ chế phân trang (10, 25, 50 bản ghi/trang), sắp xếp linh hoạt theo Ngày ban hành hoặc Số đi giảm dần.<br>3. Dựng Bảng danh sách `DocumentTable` hiển thị chuẩn các cột nghiệp vụ: Số đi, Số hiệu, Ngày ban hành, Nơi ban hành (Nội bộ), Trích yếu, Tình trạng hiệu lực (Badge màu sắc phong phú), File đính kèm, Menu tác vụ (⋮).<br>4. Đảm bảo 100% Typography tuân thủ chuẩn WCAG: Tất cả font-size >= 13px (`text-xs`), loại bỏ hoàn toàn các class `text-[10px]`, độ tương phản màu chuẩn chỉ.<br>5. Xây dựng thanh `FilterBar` đa năng (tìm kiếm từ khóa, chọn năm ban hành, khoảng ngày ban hành, phòng ban, hiệu lực).<br>6. Xây dựng Modal xem chi tiết văn bản đi (kèm preview file PDF/ảnh) và Modal danh sách cán bộ đã xem. | • **Fork:** `<khiem-user>/QuanLyVanBan_TLBM`<br>• **Branch:** `feat/vanban-di-frontend-table-detail`<br>• **Target PR:** `upstream/2_documents`<br>• **Reviewer:** Lê Trí Kiệt |
| **Trần Nhật Tân**<br><br>• *Quyền:* Read<br>• *Nơi push:* Fork cá nhân | **Frontend Input Văn bản Đi** | 1. Xây dựng Modal Form thêm mới / cập nhật Văn bản Đi (`OutgoingFormModal.tsx`): hiển thị số đi tự tăng gợi ý, khóa cứng trường Số đi khi sửa.<br>2. Xây dựng cơ chế gợi ý chuỗi Số ký hiệu văn bản theo năm và đơn vị ban hành (VD: `.../QĐ-CĐCNTT`).<br>3. Xử lý dropdown Nơi ban hành nội bộ (lấy từ `organizations_donvi`) và dropdown cascading Đơn vị nhận -> Cán bộ nhận.<br>4. Thiết kế cờ Toggle: "Gửi mail thông báo toàn hệ thống" và "Hiển thị trên bảng tin nội bộ".<br>5. Xây dựng khu vực kéo thả Upload nhiều tệp đính kèm an toàn (PDF, DOCX, scan ảnh), hiển thị thanh tiến độ và hỗ trợ xóa/thêm file khi sửa.<br>6. Xây dựng Modal Import Excel (tải file mẫu, kéo thả file, bảng preview kiểm tra tính hợp lệ dữ liệu) và nút Xuất Excel danh sách. | • **Fork:** `<tan-user>/QuanLyVanBan_TLBM`<br>• **Branch:** `feat/vanban-di-frontend-form-upload`<br>• **Target PR:** `upstream/2_documents`<br>• **Reviewer:** Lê Trí Kiệt |

---

## IV. BẢNG SO SÁNH ĐẶC THÙ NGHIỆP VỤ: VĂN BẢN ĐẾN (GĐ 1) vs. VĂN BẢN ĐI (GĐ 2)

| Thuộc tính / Nghiệp vụ | Văn bản Đến (Giai đoạn 1 — Đã hoàn tất) | Văn bản Đi (Giai đoạn 2 — Triển khai) |
| :--- | :--- | :--- |
| **Hướng luân chuyển** | Từ bên ngoài (Bộ, Sở, Doanh nghiệp) gửi đến trường | Nội bộ trường soạn thảo và ban hành ra ngoài / lưu hành trong trường |
| **Trường số tự sinh** | `so_thu_tu` = "Số đến" (Tự tăng theo năm) | `so_thu_tu` = "Số đi" (Tự tăng theo năm, quản lý độc lập) |
| **Tính bất biến của số** | Khóa cứng Số đến khi cập nhật văn bản | Khóa cứng Số đi khi cập nhật văn bản |
| **Trường ngày bắt buộc (*)** | `ngay_den` (Ngày đến tiếp nhận, lấy đủ giờ phút giây) | `ngay_ban_hanh` (Ngày ban hành, lấy đủ giờ phút giây) |
| **Nơi ban hành** | Đơn vị/Cơ quan ngoài trường gửi đến | Phòng/Khoa/Bộ môn trực thuộc trường (bảng `organizations_donvi`) |
| **Cột hiển thị danh sách** | Số ký hiệu, Ngày VB, Ngày đến, Trích yếu, Nơi ban hành, Hiệu lực | Số đi, Số ký hiệu, Ngày ban hành, Nơi ban hành, Trích yếu, Người ký, Hiệu lực |
| **Phạm vi lưu hành** | Công khai cho toàn thể cán bộ nhân viên tra cứu | Lưu hành nội bộ trường, công khai toàn thể cán bộ giảng viên |
| **Bảng CSDL vật lý** | `documents_vanbanden` (kèm bảng attachment riêng) | `documents_vanbandi` (kèm bảng attachment riêng) |
| **Trạng thái hiện tại** | **100% Hoàn thành** — Đóng băng chờ Thầy chấm điểm | **Bắt đầu triển khai** trên nhánh `feat/vanban-di-*` từ fork cá nhân |

---

## V. QUY TRÌNH PHỐI HỢP GIT WORKFLOW (THEO HUONGDAN_GIT_WORKFLOW.MD)

### 📌 Vì sao phải dùng Fork cá nhân?
Tài khoản của các thành viên (Nguyễn Anh Đô, Nguyễn Tấn Lộc Khiêm, Trần Nhật Tân) thuộc team `team_2` trên GitHub organization `QuanLyVanBanTLBM`, chỉ có quyền **Read** (không có quyền push trực tiếp vào organization repo). Điều này nhằm:
1. Đảm bảo an toàn mã nguồn, tránh trường hợp ai đó push nhầm làm hỏng nhánh chung.
2. Thầy Duy theo dõi được chính xác commit history trên Fork cá nhân của từng bạn để đánh giá điểm số độc lập.

### 🚀 7 Bước thực hiện chi tiết cho từng thành viên:
1. **Bước 1 — Fork repository:** Truy cập `https://github.com/QuanLyVanBanTLBM/QuanLyVanBan_TLBM` trên trình duyệt và bấm nút **Fork** về tài khoản GitHub cá nhân của mình (`https://github.com/<your-username>/QuanLyVanBan_TLBM`).
2. **Bước 2 — Clone và thiết lập Remote:**
   ```bash
   git clone https://github.com/<your-username>/QuanLyVanBan_TLBM.git
   cd QuanLyVanBan_TLBM
   git remote rename origin fork
   git remote add upstream https://github.com/QuanLyVanBanTLBM/QuanLyVanBan_TLBM.git
   git fetch upstream --prune
   git remote -v
   ```
   *(Kiểm tra: `fork` trỏ về tài khoản cá nhân, `upstream` trỏ về organization).*
3. **Bước 3 — Tạo branch feature từ nhánh nhóm (`upstream/2_documents`):**
   ```bash
   git checkout -b feat/vanban-di-<ten-task> upstream/2_documents
   ```
4. **Bước 4 — Code task và kiểm tra chất lượng local:**
   - Thực hiện đúng phạm vi 25% công việc được giao.
   - Chạy test, lint, kiểm tra i18n trước khi commit.
   - Commit thường xuyên với commit message rõ ràng: `feat(documents): implement outgoing document numbering logic`.
5. **Bước 5 — Đồng bộ và Push lên Fork cá nhân:**
   ```bash
   git fetch upstream --prune
   git rebase upstream/2_documents
   git push -u fork feat/vanban-di-<ten-task>
   ```
6. **Bước 6 — Mở Pull Request (PR) về branch nhóm:**
   - Truy cập GitHub repository, tạo Pull Request:
     - **Base (Target):** `QuanLyVanBanTLBM/QuanLyVanBan_TLBM:2_documents`
     - **Head (Source):** `<your-username>:feat/vanban-di-<ten-task>`
   - Điền mô tả các tính năng đã làm và tag Trưởng nhóm Lê Trí Kiệt vào mục Reviewers.
7. **Bước 7 — Review và Merge:**
   - Trưởng nhóm Lê Trí Kiệt (thuộc `team_leads`, có quyền **Write**) sẽ review code, kiểm tra tính tương thích, chạy test suite tự động và bấm **Merge** vào branch `2_documents`.

---

## VI. QUY TRÌNH KIỂM SOÁT CHẤT LƯỢNG VÀ ĐỊNH NGHĨA HOÀN THÀNH (DEFINITION OF DONE)

1. **Độc lập tuyệt đối giữa 2 giai đoạn:** Mọi commit, branch và pull request của Giai đoạn 2 chỉ được thao tác trên phân hệ Văn bản Đi. Nghiêm cấm mọi hành vi sửa đổi logic, model hoặc test cases của Văn bản Đến khi chưa có ý kiến chính thức từ Giảng viên.
2. **Tiêu chuẩn quốc tế hóa (i18n):** 100% nhãn giao diện, thông báo lỗi và tiêu đề cột phải được khai báo đầy đủ qua hệ thống đa ngôn ngữ (`locales/vi.json` và `locales/en.json`). Chạy script `check-i18n.mjs` phải đạt 0 key thiếu.
3. **Chuẩn trợ năng và thiết kế (WCAG Typography):** 100% cỡ chữ hiển thị trên bảng, menu, modal phải đạt tối thiểu 13px (class `text-xs` trở lên), tuyệt đối không để lọt class `text-[10px]` hay `text-[11px]`. Chạy script `check-css-tokens.mjs` phải đạt 0 vi phạm.
4. **Kiểm thử tự động (Automated Testing):** Mỗi tính năng mới phải có Unit Test đi kèm. Kết quả lệnh `python manage.py test apps.documents` phải đạt 100% PASS (kể cả 40 test cases cũ của Stage 1 và các test cases mới của Stage 2).
5. **Minh bạch đóng góp cá nhân (Individual Contributions):** Mỗi thành viên phải thể hiện rõ 25% công sức qua các commit hợp lệ trên Fork cá nhân của mình trước khi merge vào repository nhóm.

---

*TP. Hồ Chí Minh, ngày 03 tháng 10 năm 2026*  
**TRƯỞNG NHÓM 2**  
*(Đã ký)*  

**Lê Trí Kiệt**  
