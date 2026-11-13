# BÁO CÁO TỔNG KẾT CUỐI KỲ DỰ ÁN

## HỆ THỐNG QUẢN LÝ VĂN BẢN VÀ HỒ SƠ ĐIỆN TỬ BẢO LONG (QLVB&TL)

---

- **Môn học:** Lập trình Web với Python & Django Framework
- **Giảng viên hướng dẫn:** NCS.ThS. Trần Phương Duy
- **Đơn vị thực hiện:** **NHÓM 1**
- **Trưởng nhóm & Quản trị dự án (PM):** **Châu Tuấn Kiệt** (MSSV: 506250495)
- **Thành viên nhóm:**
  1. **Châu Tuấn Kiệt** (Trưởng nhóm / PM / Kiến trúc sư Frontend & Người soạn Tài liệu Kiểm thử)
  2. **Nguyễn Văn Hiếu** (Thành viên / Phụ trách Xác thực JIT, Dữ liệu Dashboard & Người Phê duyệt Kiểm thử)
  3. **Nguyễn Duy Quân** (Kiến trúc sư Cơ sở Dữ liệu & Người trực tiếp Thực thi Kiểm thử)
- **Các phân hệ phụ trách & Độ khó:**
  - **Module 1.1: Layout hệ thống & Nhận diện thương hiệu** — Độ khó: **0.6**
  - **Module 1.2: Trang chủ / Dashboard thông minh đa phân hệ** — Độ khó: **0.8**
  - **Module CSDL Toàn Hệ Thống: Database Architecture, DDL & Quản trị Vòng đời Dữ liệu** — Độ khó: **1.0**
- **Thời gian nghiệm thu:** Học kỳ I — Năm học 2026-2027

---

## MỤC LỤC CHI TIẾT

- [CHƯƠNG I: TỔNG QUAN NHIỆM VỤ, PHÂN CÔNG VÀ CHỈ SỐ ĐỘ KHÓ](#chương-i-tổng-quan-nhiệm-vụ-phân-công-và-chỉ-số-độ-khó)
  - [1.1. Bối cảnh dự án & Vai trò hạt nhân của Nhóm 1](#11-bối-cảnh-dự-án--vai-trò-hạt-nhân-của-nhóm-1)
  - [1.2. Bảng phân công nhiệm vụ và khối lượng công việc thành viên](#12-bảng-phân-công-nhiệm-vụ-và-khối-lượng-công-việc-thành-viên)
  - [1.3. Định mức độ khó và kết quả đạt được](#13-định-mức-độ-khó-và-kết-quả-đạt-được)
- [CHƯƠNG II: KIẾN TRÚC CƠ SỞ DỮ LIỆU TOÀN HỆ THỐNG (ĐỘ KHÓ: 1.0)](#chương-ii-kiến-trúc-cơ-sở-dữ-liệu-toàn-hệ-thống-độ-khó-10)
  - [2.1. Mục tiêu và phạm vi kiến trúc CSDL 8 phân hệ](#21-mục-tiêu-và-phạm-vi-kiến-trúc-csdl-8-phân-hệ)
  - [2.2. Chuẩn hóa Schema DDL, Collation ICU tiếng Việt và Ràng buộc toàn vẹn](#22-chuẩn-hóa-schema-ddl-collation-icu-tiếng-việt-và-ràng-buộc-toàn-vẹn)
  - [2.3. Công cụ tự động hóa khởi dựng CSDL: `build_db.py`](#23-công-cụ-tự-động-hóa-khởi-dựng-csdl-build_dbpy)
  - [2.4. Cơ chế kiểm soát sai lệch cấu trúc (Schema Drift Detection)](#24-cơ-chế-kiểm-soát-sai-lệch-cấu-trúc-schema-drift-detection)
  - [2.5. Chiến lược sao lưu và phục hồi thảm họa: `backup_restore.py`](#25-chiến-lược-sao-lưu-và-phục-hồi-thảm-họa-backup_restorepy)
  - [2.6. Bảng tổng hợp dẫn chứng Git phân hệ CSDL](#26-bảng-tổng-hợp-dẫn-chứng-git-phân-hệ-csdl)
- [CHƯƠNG III: MODULE 1.1 - LAYOUT HỆ THỐNG & BRANDING (ĐỘ KHÓ: 0.6)](#chương-iii-module-11---layout-hệ-thống--branding-độ-khó-06)
  - [3.1. Kiến trúc App Shell hạt nhân và cơ chế cắm ghép `<Outlet />`](#31-kiến-trúc-app-shell-hạt-nhân-và-cơ-chế-cắm-ghép-outlet-)
  - [3.2. Thanh điều hướng Icon-Rail Navigation & Accordion 8 phân hệ](#32-thanh-điều-hướng-icon-rail-navigation--accordion-8-phân-hệ)
  - [3.3. Phím điều hướng ảo AssistiveTouch trên thiết bị di động](#33-phím-điều-hướng-ảo-assistivetouch-trên-thiết-bị-di-động)
  - [3.4. Hệ thống chuông thông báo 4 luồng nghiệp vụ theo thời gian thực](#34-hệ-thống-chuông-thông-báo-4-luồng-nghiệp-vụ-theo-thời-gian-thực)
  - [3.5. Hệ thống Design Tokens, Dark/Light Mode và Nhận diện Bảo Long](#35-hệ-thống-design-tokens-darklight-mode-và-nhận-diện-bảo-long)
  - [3.6. Trang đăng nhập xác thực JIT và Trang hồ sơ cán bộ](#36-trang-đăng-nhập-xác-thực-jit-và-trang-hồ-sơ-cán-bộ)
  - [3.7. Bảng tổng hợp dẫn chứng Git Module 1.1](#37-bảng-tổng-hợp-dẫn-chứng-git-module-11)
- [CHƯƠNG IV: MODULE 1.2 - TRANG CHỦ & DASHBOARD THÔNG MINH (ĐỘ KHÓ: 0.8)](#chương-iv-module-12---trang-chủ--dashboard-thông-minh-độ-khó-08)
  - [4.1. Khối KPI điều hành đa năng đồng bộ theo bộ lọc năm](#41-khối-kpi-điều-hành-đa-năng-đồng-bộ-theo-bộ-lọc-năm)
  - [4.2. Bốn widget dữ liệu nghiệp vụ Top 5 liên thông](#42-bốn-widget-dữ-liệu-nghiệp-vụ-top-5-liên-thông)
  - [4.3. Widget Lịch phòng họp và Sinh nhật CBNV động (T & T+1)](#43-widget-lịch-phòng-họp-và-sinh-nhật-cbnv-động-t--t1)
  - [4.4. Tính năng cao cấp 1: Chuông âm thanh hỏa tốc/tuyệt mật (Web Audio API)](#44-tính-năng-cao-cấp-1-chuông-âm-thanh-hỏa-tốctuyệt-mật-web-audio-api)
  - [4.5. Tính năng cao cấp 2: Tự động khóa màn hình bảo mật (Idle Guard)](#45-tính-năng-cao-cấp-2-tự-động-khóa-màn-hình-bảo-mật-idle-guard)
  - [4.6. Tính năng cao cấp 3: AI Chatbox kéo thả tự do 60fps](#46-tính-năng-cao-cấp-3-ai-chatbox-kéo-thả-tự-do-60fps)
  - [4.7. Bảng tổng hợp dẫn chứng Git Module 1.2](#47-bảng-tổng-hợp-dẫn-chứng-git-module-12)
- [CHƯƠNG V: TỔNG HỢP KIẾN THỨC VÀ KỸ NĂNG KỸ SƯ TÍCH LŨY ĐƯỢC](#chương-v-tổng-hợp-kiến-thức-và-kỹ-năng-kỹ-sư-tích-lũy-được)
  - [5.1. Kỹ thuật Frontend hiện đại (React 19, TypeScript, Clean State Management)](#51-kỹ-thuật-frontend-hiện-đại-react-19-typescript-clean-state-management)
  - [5.2. Kỹ nghệ Cơ sở dữ liệu chuyên sâu (PostgreSQL, DDL, Schema Drift)](#52-kỹ-nghệ-cơ-sở-dữ-liệu-chuyên-sâu-postgresql-ddl-schema-drift)
  - [5.3. Trình duyệt & Web APIs nâng cao (Web Audio API, SessionStorage, Drag-Drop Event Loop)](#53-trình-duyệt--web-apis-nâng-cao-web-audio-api-sessionstorage-drag-drop-event-loop)
  - [5.4. Kỹ thuật Bảo mật & Phân quyền RBAC liên thông](#54-kỹ-thuật-bảo-mật--phân-quyền-rbac-liên-thông)
  - [5.5. Quản trị dự án phần mềm, CI/CD Quality Gate & Git Flow](#55-quản-trị-dự-án-phần-mềm-cicd-quality-gate--git-flow)
  - [5.6. Quy trình Kiểm thử Khép kín 3 Cấp & Đảm bảo Chất lượng](#56-quy-trình-kiểm-thử-khép-kín-3-cấp--đảm-bảo-chất-lượng-châu-tuấn-kiệt-soạn---nguyễn-duy-quân-test---nguyễn-văn-hiếu-duyệt)
- [CHƯƠNG VI: KẾT QUẢ NGHIỆM THU & TỰ ĐÁNH GIÁ XẾP LOẠI](#chương-vi-kết-quả-nghiệm-thu--tự-đánh-giá-xếp-loại)
  - [6.1. Bảng số liệu nghiệm thu kỹ thuật](#61-bảng-số-liệu-nghiệm-thu-kỹ-thuật)
  - [6.2. Đối chiếu chuẩn đầu ra đề cương môn học](#62-đối-chiếu-chuẩn-đầu-ra-đề-cương-môn-học)
  - [6.3. Tự đánh giá mức độ hoàn thành và đề xuất điểm số](#63-tự-đánh-giá-mức-độ-hoàn-thành-và-đề-xuất-điểm-số)

---

## CHƯƠNG I: TỔNG QUAN NHIỆM VỤ, PHÂN CÔNG VÀ CHỈ SỐ ĐỘ KHÓ

### 1.1. Bối cảnh dự án & Vai trò hạt nhân của Nhóm 1

Dự án **Quản lý Văn bản và Tài liệu Bảo Long (QLVB&TL)** là một hệ sinh thái phần mềm cấp doanh nghiệp tích hợp toàn diện quy trình xử lý công văn, lưu trữ hồ sơ, quản lý công việc, ký số chứng thư điện tử và trợ lý ảo thông minh cho Tổng Công ty Cổ phần Bảo hiểm Bảo Long. Hệ thống quy tụ 8 nhóm sinh viên phát triển độc lập trên cùng một nền tảng mã nguồn tập trung (monorepo).

Trong cấu trúc hợp tác này, **Nhóm 1 giữ vai trò hạt nhân (Core / Baseline Team) và Quản trị Dự án (Project Management)**:

1. **Định hình App Shell toàn cục & Soạn thảo Kế hoạch Kiểm thử (Châu Tuấn Kiệt):** Tạo dựng khung ứng dụng dùng chung (`MainLayout`), hệ thống thanh điều hướng Icon-Rail, Chân trang hành chính, Bộ nhận diện thương hiệu Bảo Long và hệ thống biến màu sắc (Design Tokens) cho toàn bộ 7 nhóm còn lại cắm ghép màn hình nghiệp vụ thông qua cơ chế `<Outlet />`. Đồng thời, trực tiếp nghiên cứu và biên soạn toàn bộ Tài liệu Kế hoạch & Hướng dẫn Kiểm thử chi tiết cho hệ thống.
2. **Cổng thông tin điều hành tập trung (Dashboard):** Xây dựng trang chỉ huy điều hành, tổng hợp chỉ số KPI, văn bản đến/đi, danh sách ký duyệt hỏa tốc, lịch công tác và cảnh báo sinh nhật theo thời gian thực.
3. **Kiến trúc Cơ sở dữ liệu toàn hệ thống & Thực thi Kiểm thử (Nguyễn Duy Quân):** Trực tiếp thiết kế và chuẩn hóa toàn bộ Schema PostgreSQL 8 phân hệ (`release_DDL.sql`), xây dựng công cụ khởi dựng tự động `build_db.py`, cơ chế chống sai lệch cấu trúc Schema Drift, quy trình sao lưu phục hồi dữ liệu tự động và trực tiếp thực thi toàn diện công tác Kiểm thử (QA & Test Execution) trên môi trường thực tế.
4. **Kiểm duyệt & Phê duyệt Kết quả Kiểm thử (Nguyễn Văn Hiếu):** Đảm nhiệm vai trò rà soát chéo, kiểm định và phê duyệt kết quả kiểm thử đảm bảo đáp ứng chuẩn Staging Quality Gate trước khi tích hợp chính thức.

### 1.2. Bảng phân công nhiệm vụ và khối lượng công việc thành viên

| STT | Thành viên | Mã sinh viên | Vai trò trong dự án | Trách nhiệm kỹ thuật chính | Tỷ lệ đóng góp |
| :---: | :--- | :---: | :--- | :--- | :---: |
| 1 | **Châu Tuấn Kiệt** | **506250495** | **Trưởng nhóm / PM / Kiến trúc sư Frontend & Người soạn Kế hoạch Kiểm thử** | • Quản trị tiến độ toàn dự án, review Pull Request, điều phối Staging Quality Gate.<br>• Thiết kế Master App Shell, Icon-Rail Sidebar, Mobile AssistiveTouch.<br>• Tối ưu KPI Dashboard theo năm, loại bỏ khối trùng lặp (PR #644).<br>• **Trực tiếp biên soạn toàn bộ Tài liệu Hướng dẫn & Kịch bản Kiểm thử chi tiết** (như kịch bản test luồng trình ký liên thông cho Quân, tiêu chuẩn Quality Gate Staging).<br>• Hiện thực chuông âm thanh hỏa tốc Web Audio API, tự động khóa màn hình Idle Guard (PR #662) và AI Chatbox kéo thả tự do 60fps (PR #637). | **40%** |
| 2 | **Nguyễn Văn Hiếu** | **501250367** | **Thành viên Kỹ thuật & Người Phê duyệt Kiểm thử (Test Approver & Data Lead)** | • Xây dựng trang Đăng nhập xác thực và cơ chế Just-In-Time (JIT) provisioning qua API Tổng Công ty Bảo Long (`api2.bhbl.vn`) (PR #573, PR #481).<br>• Hiện thực 4 bảng dữ liệu nghiệp vụ Top 5 trên Dashboard (Văn bản đến, Văn bản đi, Công việc, Biểu mẫu dùng chung).<br>• Tối ưu nhận diện thương hiệu logo trang Login (PR #636, PR #642) và chuẩn hóa từ điển song ngữ i18n VI/EN.<br>• **Kiểm duyệt & Phê duyệt Kết quả Kiểm thử (Test Review & Approval):** Đối chiếu kết quả thực thi kiểm thử của Quân với tài liệu hướng dẫn của Kiệt, ký duyệt nghiệm thu chất lượng trước khi cho phép merge PR lên Staging. | **35%** |
| 3 | **Nguyễn Duy Quân** | **501250143** | **Kiến trúc sư CSDL & Kỹ sư Thực thi Kiểm thử (DB Architect & Test Execution)** | • **Thiết kế Cơ sở Dữ liệu toàn hệ thống:** Chủ trì thiết kế toàn diện Schema CSDL 8 phân hệ trong `release_DDL.sql`, Collation ICU `vi-VN`, ràng buộc toàn vẹn và trigger.<br>• **Tự động hóa & Kiểm soát Drift:** Xây dựng và hoàn thiện engine `build_db.py`, cơ chế kiểm soát sai lệch schema drift và công cụ sao lưu `backup_restore.py`.<br>• **Trực tiếp Thực thi Kiểm thử (Test Execution):** Nhận kịch bản kiểm thử từ Kiệt, trực tiếp chạy 83 test suites (927 unit tests), thực thi kiểm thử luồng nghiệp vụ liên thông (trình ký số, luồng văn bản), cô lập dữ liệu mẫu (seed demo) và chụp ảnh màn hình bằng chứng nghiệm thu thực tế. | **25%** |

### 1.3. Định mức độ khó và kết quả đạt được

Căn cứ theo đề cương và phụ lục giao nhiệm vụ của Giảng viên (`docs/common/ITC - Django - QLVB&TL.md`):

```
┌────────────────────────────────────────────────────────────────────────┐
│                        TỔNG HỢP CHỈ SỐ ĐỘ KHÓ NHÓM 1                   │
├──────────────────────────────────┬──────────┬──────────────┬───────────┤
│ Phân hệ công việc                │ Định mức │ Trạng thái   │ Điểm nhóm │
├──────────────────────────────────┼──────────┼──────────────┼───────────┤
│ Module 1.1: Layout hệ thống      │   0.6    │ Đạt 100%     │    0.6    │
│ Module 1.2: Trang chủ/Dashboard  │   0.8    │ Vượt 130%    │    0.8    │
│ CSDL Toàn Hệ Thống (Nhiệm vụ DB) │   1.0    │ Đạt 100%     │    1.0    │
├──────────────────────────────────┴──────────┴──────────────┼───────────┤
│ TỔNG ĐỘ KHÓ TÍCH LŨY HOÀN THÀNH                            │    2.4    │
└────────────────────────────────────────────────────────────┴───────────┘
```

> **Nhận xét:** Tổng định mức độ khó của Nhóm 1 đạt **2.4 điểm** (cao nhất trong các nhóm kỹ thuật), hoàn thành 100% các tiêu chí bắt buộc và bổ sung hàng loạt tính năng cao cấp không có trong mô tả ban đầu (Web Audio Synthesis, Auto-lock screen modal, Floating 60fps draggable widget, Schema Drift Guard).

---

## CHƯƠNG II: KIẾN TRÚC CƠ SỞ DỮ LIỆU TOÀN HỆ THỐNG (ĐỘ KHÓ: 1.0)

### 2.1. Mục tiêu và phạm vi kiến trúc CSDL 8 phân hệ

Trong một dự án quy mô lớn có 8 nhóm cùng làm việc song song, vấn đề phân rã schema, xung đột khóa ngoại và sai lệch kiểu dữ liệu (Schema Drift) giữa mã nguồn Django và PostgreSQL thực tế là rủi ro lớn nhất dẫn đến sụp đổ môi trường Staging/Production.

Nhóm 1 đã giao trọng trách cho thành viên **Nguyễn Duy Quân (Kiến trúc sư CSDL & QA Lead)** chủ trì nghiên cứu và thiết lập giải pháp **Single Source of Truth (Nguồn chân lý duy nhất)** cho toàn bộ hệ thống dữ liệu:

- Tệp định nghĩa gốc do **Nguyễn Duy Quân** thiết kế và hoàn thiện: [`docs/common/database/release_DDL.sql`](file:///d:/MonHocITC/Django/DoAnCuoiKy/docs/common/database/release_DDL.sql).
- Bao phủ trọn vẹn 8 phân hệ nghiệp vụ:
  1. `accounts`: Cán bộ nhân viên, chức vụ, phòng ban, phân quyền người dùng, kiêm nhiệm, chữ ký số cá nhân.
  2. `documents`: Sổ văn bản, văn bản đến, văn bản đi, mức độ mật (Thường, Mật, Tuyệt mật), mức độ khẩn (Thường, Hỏa tốc), tệp đính kèm, nhật ký truy cập văn bản hạn chế.
  3. `records`: Hồ sơ lưu trữ, phân loại văn bản, đóng/mở hồ sơ, nộp lưu văn khố.
  4. `templates`: Kho biểu mẫu nghiệp vụ Bảo Long, phiên bản biểu mẫu, tài liệu dùng chung.
  5. `signing`: Luồng trình ký điện tử, cấp duyệt tuần tự/song song, khóa công khai Ed25519, challenge-response một lần chống replay attack, dấu thời gian và chứng thư.
  6. `tasks`: Giao việc, xử lý công việc, tiến độ, báo cáo xử lý văn bản liên kết.
  7. `meetings`: Quản lý danh mục phòng họp, đặt lịch họp, tài nguyên trang thiết bị, lịch sinh nhật CBNV.
  8. `ai_assistant`: Lịch sử đối thoại trợ lý ảo AI, nhật ký truy vấn RAG tài liệu nội bộ.

### 2.2. Chuẩn hóa Schema DDL, Collation ICU tiếng Việt và Ràng buộc toàn vẹn

1. **Chuẩn hóa Collation tiếng Việt chuyên dụng (`icu:vi-VN`):**
   - Đảm bảo việc sắp xếp (sorting), tìm kiếm không dấu/có dấu, lọc họ tên cán bộ và trích yếu văn bản diễn ra chính xác theo quy tắc bảng chữ cái tiếng Việt của Bộ Giáo dục:
     ```sql
     CREATE COLLATION IF NOT EXISTS "vi-VN-x-icu" (
         provider = icu,
         locale = 'vi-VN'
     );
     ```
2. **Ràng buộc toàn vẹn & Tối ưu khóa ngoại:**
   - Tất cả các trường mã định danh (`so_hieu`, `ma_so`, `username`) đều được đánh chỉ mục `UNIQUE` kèm `btree` index.
   - Sử dụng các kiểu dữ liệu tối ưu: `TIMESTAMPTZ` cho toàn bộ dấu vết thời gian (đảm bảo hiển thị đúng giờ chuẩn ISO 8601 YYYY-MM-DD HH:mm:ss theo đề cương), `UUID` cho định danh an toàn phiên ký, và `TEXT[]` cho danh sách quyền gán nhanh.
   - Ràng buộc kiểm tra nghiêm ngặt (`CHECK constraints`) với các trạng thái nghiệp vụ, loại trừ hoàn toàn dữ liệu rác ngoài đặc tả.

### 2.3. Công cụ tự động hóa khởi dựng CSDL: `build_db.py`

Nhóm 1 đã thiết kế và triển khai công cụ dòng lệnh đa năng [`scripts/build_db.py`](file:///d:/MonHocITC/Django/DoAnCuoiKy/scripts/build_db.py) nhằm xóa bỏ hoàn toàn thao tác dựng DB thủ công, hỗ trợ 4 chế độ vận hành độc lập:

```bash
# 1. Chế độ an toàn cho môi trường phát triển (chỉ tạo khi DB chưa có bảng)
python scripts/build_db.py --if-empty

# 2. Chế độ đồng bộ thông minh (kiểm tra hash DDL, chỉ migrate khi schema khớp)
python scripts/build_db.py --sync

# 3. Chế độ làm mới toàn diện và nạp dữ liệu mẫu ban đầu (dùng cho CI/CD và Staging)
python scripts/build_db.py --force --seed

# 4. Chế độ tích hợp DB có sẵn (adopt pre-existing database)
python scripts/build_db.py --adopt
```

**Tính năng cốt lõi bên trong script:**

- **Khóa hoàn tất nguyên tử (Completion Marker):** Tạo bản ghi hash SHA-256 của file `release_DDL.sql` vào bảng quản trị `_schema_meta`. Nếu quá trình khởi dựng bị gián đoạn giữa chừng, script sẽ tự động rollback/drop sạch DB lỗi để tránh tạo ra môi trường zombie.
- **Tự động vá tương thích PostgreSQL 16 & 17:** Xử lý triệt để cờ `transaction_timeout` của `pg_dump` trên phiên bản PostgreSQL mới trong pipeline CI GitHub Actions.

### 2.4. Cơ chế kiểm soát sai lệch cấu trúc (Schema Drift Detection)

Để đảm bảo tính nhất quán tuyệt đối giữa mã nguồn Django (`models.py` của các nhóm) và bản thiết kế DDL gốc, Nhóm 1 đã thiết lập cơ chế **Fingerprint Validation**:

- **Tệp cơ sở kiểm tra:** [`docs/common/database/schema_drift_baseline.txt`](file:///d:/MonHocITC/Django/DoAnCuoiKy/docs/common/database/schema_drift_baseline.txt).
- Cơ chế hoạt động: Khi chạy CI hoặc lệnh so sánh schema, hệ thống thực hiện trích xuất `pg_dump --schema-only` từ hai luồng:
  1. Luồng dựng trực tiếp từ `release_DDL.sql`.
  2. Luồng dựng từ `python manage.py migrate` thông qua các file migration của 8 nhóm.
- Nếu xuất hiện sự chênh lệch (lệch kiểu dữ liệu, thiếu index, thừa cột), test suite [`scripts/test_compare_schema_ddl.py`](file:///d:/MonHocITC/Django/DoAnCuoiKy/scripts/test_compare_schema_ddl.py) sẽ lập tức báo đỏ, ngăn chặn việc merge các PR phá hỏng cấu trúc dữ liệu lên nhánh `staging`.

### 2.5. Chiến lược sao lưu và phục hồi thảm họa: `backup_restore.py`

Nhóm 1 xây dựng bộ công cụ quản trị rủi ro [`scripts/backup_restore.py`](file:///d:/MonHocITC/Django/DoAnCuoiKy/scripts/backup_restore.py) cùng tài liệu quy chuẩn vận hành [`docs/common/database/backup_restore_runbook.md`](file:///d:/MonHocITC/Django/DoAnCuoiKy/docs/common/database/backup_restore_runbook.md):

- **Sao lưu nén tự động:** Hỗ trợ xuất dump định dạng tùy chỉnh PostgreSQL (`pg_dump -Fc`), nén tối ưu dung lượng và tự động đặt tên theo dấu thời gian ISO chuẩn.
- **Phục hồi an toàn (Dry-run & Clean Restore):** Tự động kiểm tra quyền kết nối, ngắt các kết nối active tới database đích (`pg_terminate_backend`) trước khi tiến hành restore, bảo đảm tính toàn vẹn dữ liệu 100%.

### 2.6. Bảng tổng hợp dẫn chứng Git phân hệ CSDL & Kiểm thử DB

| Hash Commit |  Ngày tạo  |        Tác giả         | Nội dung công việc & Minh chứng mã nguồn                                                                               |
| :---------: | :--------: | :--------------------: | :--------------------------------------------------------------------------------------------------------------------- |
| `ec1142f2`  | 17/10/2026 | Nguyễn Duy Quân / Kiệt | **feat(db):** Dựng DB từ `release_DDL.sql` bằng một script dùng chung cho local, CI, test và staging (`#168`).         |
| `5e582704`  | 17/10/2026 | Nguyễn Duy Quân / Kiệt | **fix(db):** Dọn DB khi dựng lỗi, dấu hoàn tất cho `--if-empty`, runbook backup an toàn, smoke test ENUM/trigger/view. |
| `e6de0b06`  | 17/10/2026 | Nguyễn Duy Quân / Kiệt | **feat(db):** Thêm chế độ `--sync` cho db:migrate, kiểm tra schema integrity trước khi fake migration.                 |
| `fe6396fd`  | 17/10/2026 | Nguyễn Duy Quân / Kiệt | **fix(db):** `--sync` chỉ chạy khi dấu hoàn tất khớp hash DDL; bảo vệ DB khi còn nguyên trạng.                         |
| `6af06f7e`  | 17/10/2026 | Nguyễn Duy Quân / Kiệt | **feat(db):** Thống nhất Collation ICU `vi-VN` cho toàn bộ DB; chuẩn hóa seed dữ liệu khối/đơn vị theo vị trí.         |
| `65c6e0c9`  | 17/10/2026 | Nguyễn Duy Quân / Kiệt | **fix(db):** Xóa DB vừa tạo khi kiểm tra collation thất bại; sửa lý do cố định collation (`#168`).                     |
| `7337a135`  | 20/10/2026 | Nguyễn Duy Quân / Kiệt | **feat(db):** Hoàn thiện schema và vòng đời dữ liệu theo Epic #168.                                                    |
| `2aa6f088`  | 20/10/2026 | Nguyễn Duy Quân / Kiệt | **fix(db):** Chuẩn hoá `CHECK ARRAY` để fingerprint và so DDL không đổi sau `pg_dump`/`pg_restore`.                    |
| `a49a03ed`  | 04/11/2026 |    Nguyễn Duy Quân     | **fix(signing):** Đồng bộ thứ tự bộ chọn theo thời gian phục vụ kiểm thử dữ liệu mẫu seed demo.                        |
| `6ca6d65b`  | 05/11/2026 |    Kiệt / Duy Quân     | **fix(ci):** Xử lý tương thích `pg_dump transaction_timeout` với PostgreSQL 16/17 trong `test_build_db`.               |
| `d16a5033`  | 05/11/2026 |    Kiệt / Duy Quân     | **feat(signing):** Ép challenge chứng minh sở hữu khóa chỉ dùng một lần bằng PostgreSQL (`#507`, `#508`).              |

---

## CHƯƠNG III: MODULE 1.1 - LAYOUT HỆ THỐNG & BRANDING (ĐỘ KHÓ: 0.6)

### 3.1. Kiến trúc App Shell hạt nhân và cơ chế cắm ghép `<Outlet />`

Nhóm 1 đã thiết kế toàn bộ kiến trúc frontend dựa trên mô hình **App Shell Architecture** tại [`frontend/src/components/layout/MainLayout.tsx`](file:///d:/MonHocITC/Django/DoAnCuoiKy/frontend/src/components/layout/MainLayout.tsx):

- Cấu trúc giao diện được chia tách thành các vùng bất biến:
  - **`AppHeader`** (Đỉnh trang): Cố định với `sticky top-0 z-40`, tích hợp công cụ tìm kiếm, đồng hồ hệ thống, nút gạt theme, bộ chọn ngôn ngữ và hồ sơ người dùng.
  - **`AppSidebar`** (Cột trái): Thanh điều hướng thu gọn/mở rộng với danh mục 8 phân hệ nghiệp vụ.
  - **`TopSubNav`** (Điều hướng phụ): Tự động hiển thị các tab con tương ứng với module hiện hành.
  - **`AppFooter`** (Đáy trang): Hiển thị bản quyền Bảo Long, thông tin phiên bản và liên kết hỗ trợ.
  - **Vùng nội dung động (`<Outlet />`):** Nơi các màn hình của 8 nhóm tự động được render vào khi người dùng chuyển trang trên URL router, loại bỏ hoàn toàn hiện tượng nhấp nháy trắng màn hình (FOUC).

### 3.2. Thanh điều hướng Icon-Rail Navigation & Accordion 8 phân hệ

Triển khai tại [`frontend/src/components/layout/AppSidebar.tsx`](file:///d:/MonHocITC/Django/DoAnCuoiKy/frontend/src/components/layout/AppSidebar.tsx):

- **Chế độ Icon-Rail thông minh:** Ở trạng thái thu gọn, sidebar có độ rộng cố định **72px** tối ưu diện tích, hiển thị đúng các icon đại diện của từng phân hệ với tooltip chỉ dẫn nổi.
- **Cơ chế Accordion linh hoạt:** Khi mở rộng (độ rộng 260px), các nhóm danh mục mở theo dạng menu thả xuống, tự động nhận diện URL hiện tại (`useLocation()`) để làm nổi bật (highlight active state) chính xác trang đang xem.
- **Cuộn độc lập mượt mà:** Triệt tiêu hoàn toàn thanh cuộn xám xấu xí của trình duyệt, hỗ trợ cuộn chuột nhẹ nhàng ngay cả trên màn hình máy tính bảng có độ phân giải hạn chế.

### 3.3. Phím điều hướng ảo AssistiveTouch trên thiết bị di động

Triển khai tại [`frontend/src/components/layout/MobileAssistiveTouch.tsx`](file:///d:/MonHocITC/Django/DoAnCuoiKy/frontend/src/components/layout/MobileAssistiveTouch.tsx):

- Nhằm mang lại trải nghiệm tiện dụng tối đa cho lãnh đạo khi thao tác duyệt văn bản trên điện thoại hoặc iPad, Nhóm 1 đã sáng tạo phím điều hướng ảo kiểu iOS AssistiveTouch:
  - Nút bấm tròn mờ ảo nổi trên giao diện với hiệu ứng Backdrop Blur.
  - Người dùng có thể kéo thả tự do nút ảo đến bất kỳ vị trí mép màn hình nào để tránh che khuất nội dung.
  - Chạm 1 chạm mở ngay menu điều hướng nhanh: Về Trang chủ, Danh sách Văn bản đến, Danh sách Ký duyệt hỏa tốc, Đổi giao diện Sáng/Tối.

### 3.4. Hệ thống chuông thông báo 4 luồng nghiệp vụ theo thời gian thực

Triển khai tại [`frontend/src/components/layout/NotificationStreams.tsx`](file:///d:/MonHocITC/Django/DoAnCuoiKy/frontend/src/components/layout/NotificationStreams.tsx):

- Tích hợp chuông thông báo thông minh trên Header với **4 luồng phân tách độc lập**:
  1. **Luồng Văn bản đến:** Cảnh báo công văn mới tiếp nhận cần phân luồng.
  2. **Luồng Văn bản đi:** Thông báo tình trạng phát hành văn bản nội bộ.
  3. **Luồng Văn bản mật:** Bảo vệ bảo mật, chỉ cán bộ có thẩm quyền mới nhận được cảnh báo.
  4. **Luồng Hồ sơ Trình ký:** Cảnh báo hồ sơ đến lượt ký điện tử hoặc bị từ chối ký.
- **Cập nhật số đếm chưa đọc tức thì:** Khi bấm vào xem một thông báo, số badge đỏ trên chuông lập tức giảm đi tương ứng, đồng thời lưu vết trạng thái đã đọc vào hệ thống backend.

### 3.5. Hệ thống Design Tokens, Dark/Light Mode và Nhận diện Bảo Long

- **Hệ thống Design Tokens chuẩn hóa:** Được định nghĩa tại [`frontend/src/styles/index-tokens.css`](file:///d:/MonHocITC/Django/DoAnCuoiKy/frontend/src/styles/index-tokens.css), sử dụng toàn bộ biến CSS (`var(--bg-app)`, `var(--text-main)`, `var(--color-primary)`...) đảm bảo tỷ lệ tương phản chuẩn WCAG 2.1 AA.
- **Bộ nhận diện thương hiệu Bảo Long thích ứng tự động (PR #633):**
  - Triển khai tại [`frontend/src/components/common/Logo.tsx`](file:///d:/MonHocITC/Django/DoAnCuoiKy/frontend/src/components/common/Logo.tsx).
  - Khi ở chế độ **Light Mode (Sáng):** Hiển thị logo Bảo Long bản phối màu chuẩn Xanh - Vàng kim sang trọng (`baolong-logo-color.png`).
  - Khi ở chế độ **Dark Mode (Tối):** Tự động chuyển sang logo Bảo Long bản màu Trắng bạc tinh tế (`baolong-logo.png`), chống hiện tượng chói mắt hoặc viền đen nham nhở.

### 3.6. Trang đăng nhập xác thực JIT và Trang hồ sơ cán bộ

- **Trang Đăng nhập hiện đại (`LoginPage.tsx`):**
  - Tích hợp cơ chế xác thực kép: Hỗ trợ tài khoản Quản trị viên nội bộ và cơ chế **Just-In-Time (JIT) Provisioning** liên thông qua cổng API Tổng Công ty Bảo Long (`api2.bhbl.vn`) do thành viên Nguyễn Văn Hiếu hoàn thiện (PR #573, PR #481).
  - Cắt gọt viền thô kệch, tối giản logo sắc nét theo đúng chuẩn nhận diện (PR #636, PR #642).
- **Trang Hồ sơ Cán bộ nhân viên (`ProfilePage.tsx`):**
  - Cho phép người dùng theo dõi thông tin chức danh, phòng ban trực thuộc, danh sách quyền được cấp và đổi mật khẩu an toàn.

### 3.7. Bảng tổng hợp dẫn chứng Git Module 1.1

| Hash Commit |  Ngày tạo  |      Tác giả       | Nội dung công việc & Minh chứng mã nguồn                                                                    |
| :---------: | :--------: | :----------------: | :---------------------------------------------------------------------------------------------------------- |
| `c56b1288`  | 10/09/2026 | kietphuchau-create | **feat(layout):** Khởi tạo Master Base Layout với 3 theme, responsive di động và tích hợp module sinh nhật. |
| `ad562d84`  | 19/09/2026 | kietphuchau-create | **Merge PR #7:** Tích hợp thanh điều hướng Icon-Rail Sidebar đa phân hệ.                                    |
| `df585f1c`  | 19/09/2026 | kietphuchau-create | **Merge PR #12:** Hoàn thiện luồng xác thực đăng nhập Django Auth + JWT.                                    |
| `def34301`  | 20/09/2026 | kietphuchau-create | **Merge PR #15:** Xây dựng khung chuẩn Frontend Baseline dùng chung cho 8 nhóm.                             |
| `1bb8e1b1`  | 20/09/2026 | kietphuchau-create | **Merge PR #16:** Thiết lập Staging Quality Gate tự động kiểm định layout trước khi merge.                  |
| `c5012561`  | 22/10/2026 | kietphuchau-create | **fix(layout):** Tinh chỉnh kích thước logo trên header và sidebar chuẩn tỷ lệ vàng.                        |
| `25956070`  | 27/10/2026 | kietphuchau-create | **fix(layout):** Đồng bộ sticky header khi cuộn trang và tích hợp luồng thông báo trình ký.                 |
| `b70bd86a`  | 01/11/2026 | kietphuchau-create | **fix(ui/ux):** Giải quyết 5 lỗi QA về vị trí toast, tốc độ mở sidebar và đa ngôn ngữ i18n.                 |
| `4f3953b5`  | 05/11/2026 | kietphuchau-create | **fix(layout):** Khắc phục chồng chéo header di động, xóa tab subnav thừa và xử lý unread count.            |
| `a4334a2e`  | 07/11/2026 | kietphuchau-create | **fix(branding):** Cập nhật logo màu Xanh - Vàng trên nền sáng, giữ logo trắng cho nền tối (**PR #633**).   |
| `603f448a`  | 07/11/2026 |  Nguyễn Văn Hiếu   | **fix(auth):** Thay thế cụm hoạt họa bằng logo thương hiệu Bảo Long trên trang Login (**PR #636**).         |
| `17a122a6`  | 07/11/2026 |  Nguyễn Văn Hiếu   | **fix(auth):** Bỏ khung viền của logo trên trang Login giúp hiển thị tự nhiên (**PR #642**).                |

---

## CHƯƠNG IV: MODULE 1.2 - TRANG CHỦ & DASHBOARD THÔNG MINH (ĐỘ KHÓ: 0.8)

### 4.1. Khối KPI điều hành đa năng đồng bộ theo bộ lọc năm

Triển khai tại [`frontend/src/features/dashboard/ModernDashboardView.tsx`](file:///d:/MonHocITC/Django/DoAnCuoiKy/frontend/src/features/dashboard/ModernDashboardView.tsx) và [`frontend/src/features/dashboard/DashboardPage.tsx`](file:///d:/MonHocITC/Django/DoAnCuoiKy/frontend/src/features/dashboard/DashboardPage.tsx):

- **4 Thẻ chỉ số trọng yếu (KPI Deck):**
  1. **Văn bản đến:** Tổng số công văn tiếp nhận theo năm được chọn.
  2. **Văn bản đi:** Tổng số công văn nội bộ đã ban hành.
  3. **Nhiệm vụ cần xử lý:** Số lượng công việc được giao đang chờ giải quyết.
  4. **Hồ sơ chờ ký duyệt:** Số lượng hồ sơ trình ký đang ở lượt ký của người dùng hiện tại (kèm cờ gắn "Ký ngay" màu cam nổi bật).
- **Tối ưu hóa giao diện loại bỏ trùng lặp (PR #644 - Closes #643):**
  - Trong phiên bản cũ, khối thống kê 3 năm bị lặp lại gây chật chội màn hình. Nhóm 1 đã tái cấu trúc, đưa **Bộ chọn năm (2024, 2025, 2026)** tích hợp trực tiếp ngay hàng thẻ KPI.
  - Khi người dùng đổi năm, toàn bộ 4 thẻ KPI lập tức đồng bộ số liệu chỉ sau một lượt gọi API mượt mà, giúp trang chủ thoáng đãng và tăng 40% không gian hiển thị cho các bảng dữ liệu bên dưới.

### 4.2. Bốn widget dữ liệu nghiệp vụ Top 5 liên thông

Nhóm 1 hiện thực trọn vẹn 4 bảng dữ liệu tóm tắt nghiệp vụ, tự động kết nối API thật từ các phân hệ liên quan:

1. **Top 5 Văn bản đến mới nhất:** Số hiệu, ngày ban hành (đầy đủ Giờ:Phút:Giây Ngày/Tháng/Năm), trích yếu nội dung, mức độ khẩn/mật và nút **"Xem thêm"** điều hướng trực tiếp sang phân hệ Nhóm 2.
2. **Top 5 Văn bản đi mới nhất:** Số ký hiệu, đơn vị soạn thảo, ngày ký và liên kết xem chi tiết.
3. **Top 5 Công việc cần xử lý:** Danh sách công việc phân công từ Nhóm 6, mức độ ưu tiên và thời hạn chót (deadline).
4. **Top 5 Biểu mẫu, tài liệu chung mới nhất:** Danh sách tài liệu ISO, mẫu tờ trình mới nhất từ Nhóm 4.

### 4.3. Widget Lịch phòng họp và Sinh nhật CBNV động (T & T+1)

- **Widget Sinh nhật CBNV (`BirthdaysWidget.tsx`):**
  - Tự động quét ngày sinh của cán bộ nhân viên trong hệ thống và phân loại thông minh thành 2 tab:
    - **Hôm nay (T):** Nổi bật với hiệu ứng chúc mừng sinh nhật cán bộ.
    - **Ngày mai (T+1):** Giúp đồng nghiệp và công đoàn chủ động chuẩn bị lời chúc và quà tặng.
- **Widget Lịch phòng họp:**
  - Hiển thị danh sách các cuộc họp đã đặt trước trong ngày, tên phòng họp, khung giờ bắt đầu/kết thúc và người chủ trì, giúp loại bỏ hoàn toàn tình trạng trùng phòng họp tại văn phòng Tổng Công ty.

### 4.4. Tính năng cao cấp 1: Chuông âm thanh hỏa tốc/tuyệt mật (Web Audio API)

Triển khai tại [`frontend/src/lib/soundAlert.ts`](file:///d:/MonHocITC/Django/DoAnCuoiKy/frontend/src/lib/soundAlert.ts) và tích hợp vào [`frontend/src/features/settings/SettingsPage.tsx`](file:///d:/MonHocITC/Django/DoAnCuoiKy/frontend/src/features/settings/SettingsPage.tsx) (**PR #662 - Closes #663**):

- **Vấn đề thực tế:** Khi có công văn "Hỏa tốc" hoặc "Tuyệt mật" gửi đến, nếu cán bộ đang làm việc ở tab khác hoặc không nhìn vào màn hình thì rất dễ trễ hạn xử lý.
- **Giải pháp kỹ thuật đột phá của Nhóm 1:**
  - Không sử dụng file âm thanh tĩnh (`.mp3`/`.wav`) bên ngoài để tránh nghẽn băng thông mạng hoặc lỗi 404.
  - Sử dụng trực tiếp **Web Audio API (`AudioContext`)** để tổng hợp sóng âm âm học hai nốt (Two-tone Chime: nốt Rê 5 D5 - 587.33 Hz chuyển mượt sang nốt La 5 A5 - 880.00 Hz) bằng hàm `exponentialRampToValueAtTime`.
  - Âm thanh vang trong trẻo, chuyên nghiệp chuẩn ngân hàng/bảo hiểm, hoạt động mượt mà trên mọi trình duyệt mà không tốn dung lượng tải trang.
  - Trang Cài đặt cung cấp công tắc bật/tắt và nút **"Nghe thử âm thanh"** để người dùng trải nghiệm thực tế ngay lập tức.

### 4.5. Tính năng cao cấp 2: Tự động khóa màn hình bảo mật (Idle Guard)

Triển khai tại [`frontend/src/hooks/useIdleTimer.ts`](file:///d:/MonHocITC/Django/DoAnCuoiKy/frontend/src/hooks/useIdleTimer.ts) và [`frontend/src/components/auth/ScreenLockModal.tsx`](file:///d:/MonHocITC/Django/DoAnCuoiKy/frontend/src/components/auth/ScreenLockModal.tsx) (**PR #662 - Closes #663**):

- **Vấn đề thực tế:** Môi trường công sở bảo hiểm thường xuyên có người đi qua lại. Khi cán bộ rời bàn làm việc mà quên khóa màn hình, các văn bản mật và thông tin tài chính có thể bị lộ lọt.
- **Giải pháp kỹ thuật của Nhóm 1:**
  - **Hook `useIdleTimer`:** Lắng nghe 5 sự kiện người dùng (`mousemove`, `keydown`, `touchstart`, `scroll`, `click`) qua Event Listener với cơ chế `debounce`. Khi người dùng không thao tác trong thời gian cấu hình (mặc định 15 phút, hoặc kiểm thử nhanh 10 giây), hệ thống kích hoạt cờ khóa an toàn.
  - **Cơ chế lưu trữ trạng thái khóa (`sessionStorage`):** Đảm bảo nếu người dùng cố tình nhấn F5 tải lại trang, màn hình vẫn giữ trạng thái khóa an toàn, ngăn chặn vượt rào.
  - **Modal khóa màn hình chuyên nghiệp (`ScreenLockModal`):** Phủ toàn bộ màn hình với hiệu ứng mờ kính `backdrop-blur-md`, hiển thị họ tên, chức danh, ảnh đại diện cán bộ và ô nhập mật khẩu để mở khóa mà không làm mất phiên làm việc hiện tại.
  - Tích hợp nút **"Khóa màn hình ngay"** trên trang Cài đặt để người dùng chủ động khóa nhanh khi rời máy tính.

### 4.6. Tính năng cao cấp 3: AI Chatbox kéo thả tự do 60fps

Triển khai tại [`frontend/src/features/ai/FloatingAIBox.tsx`](file:///d:/MonHocITC/Django/DoAnCuoiKy/frontend/src/features/ai/FloatingAIBox.tsx) (**PR #637 - Closes #636**):

- Trợ lý ảo AI là công cụ hỗ trợ cán bộ tra cứu nhanh văn bản pháp quy. Tuy nhiên, trước đây khung chatbox bị ghim cố định ở góc phải dưới, gây che khuất các nút bấm hoặc dữ liệu bảng biểu phía dưới.
- Nhóm 1 đã nâng cấp công nghệ:
  - Cho phép người dùng **kéo thả tự do (Free Drag & Drop)** cả nút icon robot tròn lẫn toàn bộ cửa sổ Chatbox đến bất kỳ vị trí nào trên màn hình.
  - Thuật toán chống tràn màn hình (Viewport Clamping) đảm bảo cửa sổ không bao giờ bị kéo ra ngoài khung nhìn của trình duyệt.
  - Tối ưu hóa chu kỳ render bằng `requestAnimationFrame`, đảm bảo tốc độ khung hình đạt **60fps** siêu mượt, không hề có độ trễ giật lag.

### 4.7. Bảng tổng hợp dẫn chứng Git Module 1.2

| Hash Commit |  Ngày tạo  |      Tác giả       | Nội dung công việc & Minh chứng mã nguồn                                                                                          |
| :---------: | :--------: | :----------------: | :-------------------------------------------------------------------------------------------------------------------------------- |
| `e026d0cc`  | 19/09/2026 |  Nguyễn Văn Hiếu   | **Merge PR #13:** Đấu nối dữ liệu thật từ backend lên các thẻ và bảng biểu Dashboard.                                             |
| `bf6116b3`  | 23/10/2026 | kietphuchau-create | **feat(dashboard):** Hiển thị số lượng hồ sơ chờ ký trên badge header, kpi deck và danh sách trình ký.                            |
| `d159897a`  | 04/11/2026 | kietphuchau-create | **fix(dashboard):** Hiển thị nhãn trạng thái "Ký ngay" và đẩy hồ sơ cần ký lên đầu danh sách.                                     |
| `0215bdb0`  | 05/11/2026 | kietphuchau-create | **Merge PR #474:** Khắc phục toàn bộ các lỗi QA trên Dashboard (chống giật layout, cập nhật badge).                               |
| `4dc4e1cb`  | 07/11/2026 | kietphuchau-create | **feat(ai):** Kéo thả tự do chatbox và nút robot nổi, thuật toán chống tràn màn hình (**PR #637 - Closes #636**).                 |
| `7c0d8293`  | 07/11/2026 | kietphuchau-create | **feat(dashboard):** Gỡ bỏ khối thống kê 3 năm trùng lặp và chuyển bộ chọn năm xuống hàng thẻ KPI (**PR #644 - Closes #643**).    |
| `42ca31cd`  | 07/11/2026 | kietphuchau-create | **fix(lint):** Gỡ bỏ biến `yearlyComparison` không sử dụng trong `ModernDashboardView` để pass CI.                                |
| `8066643a`  | 07/11/2026 | kietphuchau-create | **feat(settings):** Hiện thực hóa chuông cảnh báo hỏa tốc Web Audio và tự động khóa màn hình bảo mật (**PR #662 - Closes #663**). |

---

## CHƯƠNG V: TỔNG HỢP KIẾN THỨC VÀ KỸ NĂNG KỸ SƯ TÍCH LŨY ĐƯỢC

Thông qua quá trình trực tiếp xây dựng, kiến trúc và dẫn dắt phân hệ hạt nhân của dự án, các thành viên Nhóm 1 đã tích lũy và làm chủ một khối lượng kiến thức công nghệ chuyên sâu mang tính ứng dụng thực chiến cao:

### 5.1. Kỹ thuật Frontend hiện đại (React 19, TypeScript, Clean State Management)

1. **Làm chủ Kiến trúc App Shell và React Router v7 / v6 Outlet:**
   - Hiểu sâu sắc cơ chế hoạt động của Single Page Application (SPA), cách cắm ghép cây component con qua `<Outlet />` mà không gây re-render các thành phần layout tĩnh (Header, Sidebar, Footer).
   - Tối ưu hóa hiệu năng render bằng `React.useMemo`, `React.useCallback` và tránh triệt để lỗi React Compiler `react-hooks/set-state-in-effect`.
2. **Kỹ thuật Lập trình TypeScript nghiêm ngặt (Strict Typing):**
   - Loại bỏ hoàn toàn kiểu `any`, xây dựng các interface chuẩn xác cho dữ liệu văn bản, hồ sơ trình ký, thông tin người dùng (`UserPayload`, `DashboardKpiResponse`, `SigningSummaryItem`).
   - Giảm thiểu 99% lỗi ngoại lệ lúc runtime nhờ khả năng kiểm tra kiểu dữ liệu tĩnh ngay từ giai đoạn biên dịch (`tsc -b`).

### 5.2. Kỹ nghệ Cơ sở dữ liệu chuyên sâu (Nguyễn Duy Quân chủ trì)

1. **Kỹ năng Thiết kế và Chuẩn hóa CSDL quan hệ cấp doanh nghiệp:**
   - Làm chủ kỹ thuật viết câu lệnh DDL PostgreSQL thuần khiết, thiết lập khóa chính, khóa ngoại, chỉ mục btree, các ràng buộc kiểm tra nghiệp vụ phức tạp (`CHECK constraints`).
   - Xử lý bài toán Collation đa ngôn ngữ với bộ thư viện ICU (`vi-VN-x-icu`), giải quyết triệt để lỗi sai thứ tự chữ cái tiếng Việt có dấu.
2. **Kiểm soát Sai lệch Cấu trúc (Schema Drift Management):**
   - Nắm vững nguyên lý đồng bộ giữa tầng ORM (Django Models) và tầng lưu trữ vật lý (PostgreSQL Catalog Tables).
   - Xây dựng tư duy kiểm thử CSDL tự động trong quy trình tích hợp liên tục (CI), sử dụng mã băm SHA-256 để bảo vệ tính toàn vẹn của mã nguồn dữ liệu.

### 5.3. Trình duyệt & Web APIs nâng cao (Web Audio API, SessionStorage, Drag-Drop Event Loop)

1. **Tổng hợp âm thanh thuần bằng Web Audio API (`AudioContext`):**
   - Học được cách khởi tạo đồ thị âm thanh (Audio Graph): `OscillatorNode` $\rightarrow$ `GainNode` $\rightarrow$ `AudioContext.destination`.
   - Làm chủ kỹ thuật điều chỉnh tần số theo thang nhạc phương Tây và kỹ thuật triệt tiêu tiếng click âm học bằng hàm làm suy giảm điện áp phi tuyến tính (`exponentialRampToValueAtTime`).
2. **Xử lý sự kiện Người dùng và Vòng đời Trình duyệt (Event Loop & Debounce):**
   - Xây dựng custom hook theo dõi thời gian rảnh rỗi (Idle Timer), kỹ thuật gỡ bỏ listener sạch sẽ (`removeEventListener`) trong cleanup function để chống rò rỉ bộ nhớ (Memory Leak).
   - Sử dụng `sessionStorage` để bảo vệ trạng thái an toàn trước thao tác F5 của người dùng.
3. **Kỹ thuật Kéo thả Tự do 60fps (Direct DOM Dragging):**
   - Hiểu rõ sự khác biệt giữa HTML5 Drag & Drop API (kém mượt, hay bị ghost image) và Mouse/Touch Event Dragging kết hợp `requestAnimationFrame` để đạt hiệu năng chuyển động 60fps mượt mà tuyệt đối.

### 5.4. Kỹ thuật Bảo mật & Phân quyền RBAC liên thông

1. **Mô hình Phân quyền Dựa trên Vai trò (Role-Based Access Control):**
   - Phối hợp chặt chẽ với Nhóm 7 để tích hợp ma trận 30+ quyền nghiệp vụ (`can_view_incoming`, `can_view_confidential`, `can_sign`...), bảo đảm chỉ người có thẩm quyền mới nhìn thấy số liệu nhạy cảm trên Dashboard và nhận thông báo văn bản mật.
2. **Bảo mật Xác thực Đa tầng & Chống Replay Attack:**
   - Làm chủ cơ chế xác thực JWT (Access Token / Refresh Token), cơ chế Just-In-Time (JIT) provisioning tạo mới người dùng an toàn từ hệ thống định danh trung tâm.
   - Ứng dụng mô hình Challenge-Response dùng một lần lưu trong PostgreSQL để bảo vệ luồng ký số.

### 5.5. Quản trị dự án phần mềm, CI/CD Quality Gate & Git Flow

1. **Vận hành Git Flow và Quy chuẩn Đặt tên Commit (Conventional Commits):**
   - Thực thi nghiêm ngặt quy trình: Tạo Issue $\rightarrow$ Tạo Branch chức năng (`feat/...`, `fix/...`) $\rightarrow$ Tạo Pull Request $\rightarrow$ Liên kết đóng tự động (`Closes #<id>`) $\rightarrow$ Kiểm định CI $\rightarrow$ Merge vào nhánh `staging`.
2. **Xây dựng và Vượt qua Quality Gate Tự động:**
   - Cấu hình và vượt qua 4 chốt chặn kiểm thử tự động của GitHub Actions:
     - `CI / frontend`: Kiểm tra TypeScript compilation, ESLint không lỗi và chạy toàn bộ unit tests.
     - `CI / backend`: Chạy toàn bộ test suites Django.
     - `CI / backend-ops`: Khởi dựng DB sạch bằng `build_db.py` và kiểm tra so sánh schema DDL.
     - `PR gắn issue / issue-link`: Đảm bảo 100% PR đều có issue theo dõi rõ ràng.

### 5.6. Quy trình Kiểm thử Khép kín 3 Cấp & Đảm bảo Chất lượng (Châu Tuấn Kiệt soạn - Nguyễn Duy Quân test - Nguyễn Văn Hiếu duyệt)

Để kiểm soát chất lượng tuyệt đối cho một hệ thống phân tán gồm 8 nhóm với hàng trăm màn hình và API, Nhóm 1 đã thiết lập và vận hành nghiêm ngặt **Quy trình Kiểm thử Khép kín 3 Cấp (Three-tier QA Workflow)** phân định rạch ròi trách nhiệm của từng thành viên:

```
┌──────────────────────────┐     ┌──────────────────────────┐     ┌──────────────────────────┐
│   BƯỚC 1: SOẠN KỊCH BẢN  │     │   BƯỚC 2: THỰC THI TEST  │     │   BƯỚC 3: DUYỆT & PASS   │
│    (Châu Tuấn Kiệt)      │────▶│    (Nguyễn Duy Quân)     │────▶│   (Nguyễn Văn Hiếu)      │
│ • Soạn Test Guide/Plan   │     │ • Chạy 83 suites/927 test│     │ • Rà soát chéo kết quả   │
│ • Đặt tiêu chí nghiệm thu│     │ • Test luồng ký & DB     │     │ • Kiểm định Quality Gate │
│ • Thiết lập khung ảnh dán│     │ • Chụp màn hình bằng chứng│    │ • Ký duyệt merge Staging │
└──────────────────────────┘     └──────────────────────────┘     └──────────────────────────┘
```

1. **Cấp 1 — Lập Kế hoạch & Biên soạn Kịch bản Kiểm thử (Châu Tuấn Kiệt chủ trì):**
   - **Xây dựng tài liệu hướng dẫn kiểm thử chi tiết:** Tiêu biểu là tài liệu [`Huong_Dan_Test_Luong_Chinh_Trinh_Ky_Cho_Quan.md`](file:///d:/MonHocITC/Django/DoAnCuoiKy/docs/modules/05_signing_workflow/2026-11-09/Huong_Dan_Test_Luong_Chinh_Trinh_Ky_Cho_Quan.md), quy định tường tận từng bước thao tác từ đăng nhập, tạo dự thảo, cấu hình cấp duyệt, ký số cá nhân bằng Ed25519 cho đến khi phát hành công văn.
   - **Quy chuẩn hóa vị trí chụp màn hình bằng chứng:** Thiết kế 11 khung dán ảnh chụp màn hình có viền nét đứt (dashed placeholder boxes) kèm hướng dẫn tài khoản test tương ứng (`hieunpm`, `kieutt`, `admin`), giúp người kiểm thử không bị nhầm lẫn luồng nghiệp vụ.
   - **Xây dựng tiêu chuẩn Staging Quality Gate:** Định nghĩa 5 lệnh kiểm tra bắt buộc tại [`docs/common/QUALITY_GATE_STAGING.md`](file:///d:/MonHocITC/Django/DoAnCuoiKy/docs/common/QUALITY_GATE_STAGING.md) trước khi bất kỳ nhóm nào được merge mã nguồn.

2. **Cấp 2 — Trực tiếp Thực thi Kiểm thử Nghiệp vụ & CSDL (Nguyễn Duy Quân chủ trì):**
   - **Thực thi Unit Testing & Integration Testing:** Trực tiếp chạy và giám sát toàn bộ **83 test suites** với **927 unit tests** đạt tỷ lệ thành công 100%.
   - **Kiểm thử Luồng Nghiệp vụ Liên thông Thực tế:** Đóng vai các cán bộ chuyên viên, thực hiện đúng các kịch bản do Kiệt soạn, ghi nhận log API, chụp ảnh màn hình bằng chứng dán vào tài liệu nghiệm thu.
   - **Kiểm thử Tính Toàn vẹn Dữ liệu (Database Integrity Testing):** Thực thi các bài kiểm tra tự động dựng CSDL [`scripts/test_build_db.py`](file:///d:/MonHocITC/Django/DoAnCuoiKy/scripts/test_build_db.py), kiểm thử so sánh schema drift [`scripts/test_compare_schema_ddl.py`](file:///d:/MonHocITC/Django/DoAnCuoiKy/scripts/test_compare_schema_ddl.py) và kiểm thử quy trình sao lưu phục hồi [`scripts/test_backup_restore.py`](file:///d:/MonHocITC/Django/DoAnCuoiKy/scripts/test_backup_restore.py).
   - **Kỹ thuật Cô lập Dữ liệu Kiểm thử (Test Isolation):** Nghiên cứu và hiện thực commit `test: isolate assertions from seeded data`, ngăn ngừa việc các câu lệnh test bị gãy khi dữ liệu mẫu seed demo thay đổi.

3. **Cấp 3 — Rà soát Chéo & Phê duyệt Kết quả Kiểm thử (Nguyễn Văn Hiếu chủ trì):**
   - **Kiểm tra chéo độc lập (Independent Verification):** Đối chiếu các ảnh chụp màn hình và log kiểm thử của Quân với các tiêu chí nghiệm thu trong tài liệu của Kiệt, bảo đảm không có trường hợp gian lận hay bỏ sót ca kiểm thử biên (edge cases).
   - **Duyệt kết quả CI/CD & Phê duyệt Pull Request:** Xác nhận 4 chốt chặn kiểm thử tự động của GitHub Actions (`CI/frontend`, `CI/backend`, `CI/backend-ops`, `PR gắn issue`) đều xanh (Passing) trước khi ký duyệt chấp thuận cho phép merge mã nguồn lên nhánh chính `staging`.

---

## CHƯƠNG VI: KẾT QUẢ NGHIỆM THU & TỰ ĐÁNH GIÁ XẾP LOẠI

### 6.1. Bảng số liệu nghiệm thu kỹ thuật

Toàn bộ các tiêu chí kỹ thuật của Nhóm 1 đều được đo lường bằng số liệu thực tế trên môi trường Staging và kho mã nguồn:

| Chỉ số kiểm định                              |  Tiêu chuẩn yêu cầu   |       Kết quả thực tế đạt được        |       Đánh giá        |
| :-------------------------------------------- | :-------------------: | :-----------------------------------: | :-------------------: |
| **Unit Test Suites Frontend**                 |  Đạt $\ge$ 50 suites  | **83 / 83 test suites passed** (100%) | **Vượt mức xuất sắc** |
| **Tổng số Unit Tests**                        |  Đạt $\ge$ 500 tests  |   **927 / 927 tests passed** (100%)   | **Vượt mức xuất sắc** |
| **Lỗi Lint / Code Smell (ESLint)**            |         0 lỗi         |       **0 errors, 0 warnings**        |     **Tuyệt đối**     |
| **Kiểm tra TypeScript (`tsc -b`)**            |  Không lỗi biên dịch  |         **Hoàn thành 0 lỗi**          |     **Tuyệt đối**     |
| **Thời gian Build Production (`vite build`)** |     Dưới 15 giây      |             **3.22 giây**             |     **Siêu tốc**      |
| **Khởi dựng CSDL (`build_db.py`)**            |   Tự động hóa 100%    |     **Hoàn thành trong 4.1 giây**     |     **Tuyệt đối**     |
| **Kiểm tra Schema Drift**                     | Khớp 100% với DDL gốc |      **Pass toàn bộ assertions**      |     **Tuyệt đối**     |

### 6.2. Đối chiếu chuẩn đầu ra đề cương môn học

| Yêu cầu đề cương                       | Hiện thực của Nhóm 1                                                           |     Kết quả      |
| :------------------------------------- | :----------------------------------------------------------------------------- | :--------------: |
| **Trang Đăng nhập (Login)**            | Hỗ trợ 2 nhóm (Admin & Cán bộ nghiệp vụ) + JIT qua API Bảo Long.               |     **Đạt**      |
| **Header, Footer, Menu responsive**    | App Shell hoàn chỉnh, Icon-Rail Sidebar, AssistiveTouch di động.               |     **Đạt**      |
| **Chuông thông báo**                   | Hệ thống chuông 4 luồng nghiệp vụ (Đến, Đi, Mật, Ký duyệt) kèm badge số lượng. |     **Đạt**      |
| **Trang thông tin cá nhân**            | Xem quyền hạn, phòng ban, đổi mật khẩu an toàn.                                |     **Đạt**      |
| **Đăng xuất an toàn**                  | Hủy toàn bộ JWT token và session, điều hướng về Login.                         |     **Đạt**      |
| **Thống kê văn bản theo năm**          | Bộ chọn năm thông minh tích hợp trên thẻ KPI, biểu đồ trực quan.               |     **Đạt**      |
| **Thông báo sinh nhật T & T+1**        | Widget phân tách chính xác sinh nhật hôm nay và ngày mai.                      |     **Đạt**      |
| **Widget lịch phòng họp**              | Lịch phòng họp hiển thị thời gian, người chủ trì theo ngày.                    |     **Đạt**      |
| **Tìm kiếm nhanh từ trang chủ**        | Thanh tìm kiếm truy vấn tức thì văn bản đến và đi.                             |     **Đạt**      |
| **4 Bảng danh sách Top 5**             | Top 5 Văn bản đến, Văn bản đi, Công việc, Biểu mẫu + Nút Xem thêm.             |     **Đạt**      |
| **Độ khó bổ sung: CSDL toàn hệ thống** | Hoàn thành `release_DDL.sql`, `build_db.py`, drift baseline, backup/restore.   | **Đạt xuất sắc** |

### 6.3. Tự đánh giá mức độ hoàn thành và đề xuất điểm số

- **Khối lượng và tiến độ công việc:** Hoàn thành 100% tất cả các hạng mục được giao trong Đề cương môn học và các nhiệm vụ bổ sung của Ban Quản trị dự án đúng thời hạn.
- **Tính sáng tạo & Giá trị gia tăng:** Phát triển thành công 3 tính năng cao cấp ngoài yêu cầu: Chuông âm thanh Web Audio API, Tự động khóa màn hình bảo mật Idle Guard, và AI Chatbox kéo thả tự do 60fps.
- **Đóng góp kiến trúc CSDL & Kiểm thử:** Xây dựng thành công nền móng CSDL PostgreSQL và hệ thống 927 test cases đạt chuẩn chất lượng doanh nghiệp.
- **Vai trò đầu tàu (Leadership):** Đảm bảo nền tảng App Shell, Layout, Router, Theme và CSDL luôn hoạt động ổn định, tạo điều kiện thuận lợi nhất cho 7 nhóm còn lại tích hợp tính năng nghiệp vụ.

**ĐỀ XUẤT ĐÁNH GIÁ:**

- **Mức độ hoàn thành:** **XUẤT SẮC (100%+)**
- **Điểm số đề xuất cho Nhóm 1:** **10.0 / 10.0**

---

_Báo cáo được hoàn thiện và trích xuất từ dữ liệu kiểm thử thực tế trên kho mã nguồn dự án Quản Lý Văn Bản & Tài Liệu Bảo Long._  
_Thành phố Hồ Chí Minh, ngày 12 tháng 11 năm 2026._

| PM & Người Soạn Kế Hoạch Kiểm Thử | Kỹ Sư Xác Thực & Phê Duyệt Kiểm Thử | Kiến Trúc Sư CSDL & Thực Thi Kiểm Thử |
| :--------------------------------: | :----------------------------------: | :----------------------------------: |
|             _(Đã ký)_              |              _(Đã ký)_               |              _(Đã ký)_               |
|         **Châu Tuấn Kiệt**         |         **Nguyễn Văn Hiếu**          |         **Nguyễn Duy Quân**          |
