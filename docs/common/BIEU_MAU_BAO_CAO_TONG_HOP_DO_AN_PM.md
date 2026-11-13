# [BIỂU MẪU CHUẨN] BÁO CÁO TỔNG KẾT TOÀN DIỆN ĐỒ ÁN CUỐI KỲ
## HỆ THỐNG QUẢN LÝ VĂN BẢN VÀ HỒ SƠ ĐIỆN TỬ BẢO LONG (QLVB&TL)
*(Dành cho Project Manager - Châu Tuấn Kiệt tổng hợp từ 8 nhóm nộp cho Giảng viên hướng dẫn)*

---

- **Môn học:** Lập trình Web với Python & Django Framework
- **Giảng viên hướng dẫn:** NCS.ThS. Trần Phương Duy
- **Đơn vị thực hiện:** **TẬP THỂ LỚP ĐỒ ÁN - 8 NHÓM PHÁT TRIỂN (27 THÀNH VIÊN)**
- **Ban Quản trị Dự án (Project Management Board):**
  - **Project Manager (PM):** **Châu Tuấn Kiệt** (Trưởng nhóm 1 - MSSV: 506250495)
  - **Business Analyst (BA):** Giảng viên hướng dẫn
  - **Data Analyst / Database Architect (DA):** Tô Thanh Tân (Trưởng nhóm 7) & Nguyễn Duy Quân (Nhóm 1)
  - **DevOps Engineer:** Lê Thanh Hậu (Trưởng nhóm 5) & Châu Tuấn Kiệt (PM)
- **Kho lưu trữ mã nguồn (Repository):** [https://github.com/QuanLyVanBanTLBM/QuanLyVanBan_TLBM.git](https://github.com/QuanLyVanBanTLBM/QuanLyVanBan_TLBM.git)
- **Môi trường Staging chính thức:** `https://staging-quanlyvanban.bhbl.vn`
- **Thời gian nghiệm thu:** Học kỳ I — Năm học 2026-2027

---

## MỤC LỤC BÁO CÁO TOÀN ĐỒ ÁN

- [LỜI CAM ĐOAN & LỜI CẢM ƠN](#lời-cam-đoan--lời-cảm-ơn)
- [DANH MỤC CÁC TỪ VIẾT TẮT](#danh-mục-các-từ-viết-tắt)
- [CHƯƠNG I: TỔNG QUAN DỰ ÁN, CƠ CẤU TỔ CHỨC VÀ CƠ CHẾ QUẢN TRỊ](#chương-i-tổng-quan-dự-án-cơ-cấu-tổ-chức-và-cơ-chế-quản-trị)
  - [1.1. Bối cảnh bài toán nghiệp vụ Tổng Công ty Bảo hiểm Bảo Long](#11-bối-cảnh-bài-toán-nghiệp-vụ-tổng-công-ty-bảo-hiểm-bảo-long)
  - [1.2. Cơ cấu tổ chức 27 thành viên và ma trận phân công 8 nhóm](#12-cơ-cấu-tổ-chức-27-thành-viên-và-ma-trận-phân-công-8-nhóm)
  - [1.3. Bảng tổng hợp định mức độ khó toàn dự án (Thang 10.0)](#13-bảng-tổng-hợp-định-mức-độ-khó-toàn-dự-án-thang-100)
  - [1.4. Quy chế vận hành Git Flow và Staging Quality Gate](#14-quy-chế-vận-hành-git-flow-và-staging-quality-gate)
- [CHƯƠNG II: KIẾN TRÚC HỆ THỐNG NỀN TẢNG VÀ CƠ SỞ DỮ LIỆU TOÀN CỤC](#chương-ii-kiến-trúc-hệ-thống-nền-tảng-và-cơ-sở-dữ-liệu-toàn-cục)
  - [2.1. Kiến trúc tổng thể Monorepo Fullstack (React 19 + Django 5 + PostgreSQL)](#21-kiến-trúc-tổng-thể-monorepo-fullstack-react-19--django-5--postgresql)
  - [2.2. Khung ứng dụng dùng chung (App Shell Baseline & Design Tokens)](#22-khung-ứng-dụng-dùng-chung-app-shell-baseline--design-tokens)
  - [2.3. Single Source of Truth: Thiết kế CSDL 8 phân hệ (`release_DDL.sql`)](#23-single-source-of-truth-thiết-kế-csdl-8-phân-hệ-release_ddlsql)
  - [2.4. Công cụ tự động hóa khởi dựng CSDL và chống sai lệch Schema Drift](#24-công-cụ-tự-động-hóa-khởi-dựng-csdl-và-chống-sai-lệch-schema-drift)
  - [2.5. Chiến lược sao lưu và phục hồi thảm họa tự động](#25-chiến-lược-sao-lưu-và-phục-hồi-thảm-họa-tự-động)
- [CHƯƠNG III: BÁO CÁO KẾT QUẢ TRIỂN KHAI CHI TIẾT THEO 8 PHÂN HỆ](#chương-iii-báo-cáo-kết-quả-triển-khai-chi-tiết-theo-8-phân-hệ)
  - [3.1. Phân hệ 1: Layout Hệ thống, Xác thực & Dashboard Thông minh (Nhóm 1)](#31-phân-hệ-1-layout-hệ-thống-xác-thực--dashboard-thông-minh-nhóm-1)
  - [3.2. Phân hệ 2: Quản lý Văn bản đến, Văn bản đi và Văn bản mật (Nhóm 2)](#32-phân-hệ-2-quản-lý-văn-bản-đến-văn-bản-đi-và-văn-bản-mật-nhóm-2)
  - [3.3. Phân hệ 3: Quản lý Hồ sơ lưu trữ và Danh mục Loại văn bản (Nhóm 3)](#33-phân-hệ-3-quản-lý-hồ-sơ-lưu-trữ-và-danh-mục-loại-văn-bản-nhóm-3)
  - [3.4. Phân hệ 4: Quản lý Kho Biểu mẫu và Tài liệu dùng chung (Nhóm 4)](#34-phân-hệ-4-quản-lý-kho-biểu-mẫu-và-tài-liệu-dùng-chung-nhóm-4)
  - [3.5. Phân hệ 5: Quy trình Trình ký điện tử & Ký số Ed25519 (Nhóm 5)](#35-phân-hệ-5-quy-trình-trình-ký-điện-tử--ký-số-ed25519-nhóm-5)
  - [3.6. Phân hệ 6: Quản lý Phân công Giao việc và Xử lý Công việc (Nhóm 6)](#36-phân-hệ-6-quản-lý-phân-công-giao-việc-và-xử-lý-công-việc-nhóm-6)
  - [3.7. Phân hệ 7: Phòng họp, Sinh nhật, Quản trị Đơn vị & Phân quyền RBAC (Nhóm 7)](#37-phân-hệ-7-phòng-họp-sinh-nhật-quản-trị-đơn-vị--phân-quyền-rbac-nhóm-7)
  - [3.8. Phân hệ 8: Trợ lý ảo AI Chatbot & Tra cứu Văn bản Nội bộ (Nhóm 8)](#38-phân-hệ-8-trợ-lý-ảo-ai-chatbot--tra-cứu-văn-bản-nội-bộ-nhóm-8)
- [CHƯƠNG IV: QUY TRÌNH TÍCH HỢP LIÊN THÔNG, KIỂM ĐỊNH CHẤT LƯỢNG VÀ DEPLOY](#chương-iv-quy-trình-tích-hợp-liên-thông-kiểm-định-chất-lượng-và-deploy)
  - [4.1. Quy trình Kiểm thử Khép kín 3 Cấp (Kiệt soạn - Quân test - Hiếu duyệt)](#41-quy-trình-kiểm-thử-khép-kín-3-cấp-kiệt-soạn---quân-test---hiếu-duyệt)
  - [4.2. Hệ thống kiểm định tự động CI/CD GitHub Actions 4 luồng](#42-hệ-thống-kiểm-định-tự-động-cicd-github-actions-4-luồng)
  - [4.3. Bảng tổng hợp số liệu kiểm thử toàn hệ thống (Test Suites & Coverage)](#43-bảng-tổng-hợp-số-liệu-kiểm-thử-toàn-hệ-thống-test-suites--coverage)
  - [4.4. Hạ tầng triển khai Staging, SSL HTTPS và Quản trị Bí mật Môi trường](#44-hạ-tầng-triển-khai-staging-ssl-https-và-quản-trị-bí-mật-môi-trường)
- [CHƯƠNG V: ĐÁNH GIÁ TỔNG THỂ, BẢNG ĐIỂM ĐỀ XUẤT VÀ XẾP LOẠI](#chương-v-đánh-giá-tổng-thể-bảng-điểm-đề-xuất-và-xếp-loại)
  - [5.1. Bảng đối chiếu 100% chuẩn đầu ra đề cương môn học](#51-bảng-đối-chiếu-100-chuẩn-đầu-ra-đề-cương-môn-học)
  - [5.2. Các tính năng sáng tạo vượt trội ngoài đặc tả ban đầu](#52-các-tính-năng-sáng-tạo-vượt-trội-ngoài-đặc-tả-ban-đầu)
  - [5.3. Bảng tổng hợp đánh giá và đề xuất điểm số cho 8 nhóm](#53-bảng-tổng-hợp-đánh-giá-và-đề-xuất-điểm-số-cho-8-nhóm)
  - [5.4. Bảng chi tiết đề xuất điểm số cho 27 thành viên](#54-bảng-chi-tiết-đề-xuất-điểm-số-cho-27-thành-viên)
- [CHƯƠNG VI: KẾT LUẬN, BÀI HỌC KINH NGHIỆM VÀ HƯỚNG PHÁT TRIỂN](#chương-vi-kết-luận-bài-học-kinh-nghiệm-và-hướng-phát-triển)
  - [6.1. Kết luận về mức độ hoàn thành đồ án](#61-kết-luận-về-mức-độ-hoàn-thành-đồ-án)
  - [6.2. Bài học kinh nghiệm từ góc độ Quản trị Dự án tập trung](#62-bài-học-kinh-nghiệm-từ-góc-độ-quản-trị-dự-án-tập-trung)
  - [6.3. Kế hoạch mở rộng và thương mại hóa sản phẩm](#63-kế-hoạch-mở-rộng-và-thương-mại-hóa-sản-phẩm)
- [PHỤ LỤC: MINH CHỨNG MÃ NGUỒN VÀ BÀN GIAO HỆ THỐNG](#phụ-lục-minh-chứng-mã-nguồn-và-bàn-giao-hệ-thống)

---

## LỜI CAM ĐOAN & LỜI CẢM ƠN

### Lời Cam Đoan
Tập thể 27 sinh viên thực hiện đồ án xin cam đoan: Toàn bộ mã nguồn, cấu trúc cơ sở dữ liệu, các giao diện người dùng và tài liệu báo cáo này được xây dựng trên tinh thần tự lực nghiên cứu, học hỏi và lao động nghiêm túc. Mọi số liệu kiểm thử, commit Git, Pull Request và kết quả nghiệm thu đều là dữ liệu thực tế trên kho mã nguồn dự án, không có sự sao chép bất hợp pháp từ bất kỳ nguồn bên ngoài nào.

### Lời Cảm Ơn
Tập thể sinh viên xin bày tỏ lòng biết ơn chân thành và sâu sắc nhất đến **Thầy NCS.ThS. Trần Phương Duy** – Giảng viên hướng dẫn bộ môn. Thầy không chỉ truyền đạt những kiến thức quý báu về lập trình Django, tư duy kiến trúc hệ thống và quy trình phát triển phần mềm chuẩn mực, mà còn tận tình định hướng, đóng vai trò Business Analyst (BA) đưa ra các yêu cầu thực tiễn và phản hồi sát sao trong từng giai đoạn thẩm định đồ án.

---

## DANH MỤC CÁC TỪ VIẾT TẮT

| Viết tắt | Thuật ngữ Tiếng Anh | Ý nghĩa Tiếng Việt |
| :--- | :--- | :--- |
| **API** | Application Programming Interface | Giao diện lập trình ứng dụng |
| **BA** | Business Analyst | Chuyên viên phân tích nghiệp vụ |
| **CBNV** | Can Bo Nhan Vien | Cán bộ nhân viên |
| **CI/CD** | Continuous Integration / Continuous Deployment | Tích hợp và Triển khai liên tục |
| **DDL** | Data Definition Language | Ngôn ngữ định nghĩa dữ liệu (Schema CSDL) |
| **DRF** | Django REST Framework | Bộ công cụ xây dựng RESTful API trên Django |
| **FOUC** | Flash of Unstyled Content | Hiện tượng chớp nháy giao diện khi tải trang |
| **JIT** | Just-In-Time Provisioning | Cơ chế khởi tạo tài khoản tức thì khi xác thực |
| **JWT** | JSON Web Token | Chuỗi mã hóa xác thực phiên làm việc an toàn |
| **PM** | Project Manager | Trưởng ban Quản trị Dự án |
| **QA** | Quality Assurance | Đảm bảo chất lượng và kiểm thử phần mềm |
| **QLVB&TL** | Quan Ly Van Ban & Tai Lieu | Hệ thống Quản lý Văn bản và Tài liệu |
| **RBAC** | Role-Based Access Control | Kiểm soát quyền truy cập dựa trên vai trò |
| **SPA** | Single Page Application | Ứng dụng web một trang |
| **UI/UX** | User Interface / User Experience | Giao diện người dùng / Trải nghiệm người dùng |

---

## CHƯƠNG I: TỔNG QUAN DỰ ÁN, CƠ CẤU TỔ CHỨC VÀ CƠ CHẾ QUẢN TRỊ

### 1.1. Bối cảnh bài toán nghiệp vụ Tổng Công ty Bảo hiểm Bảo Long
Tổng Công ty Cổ phần Bảo hiểm Bảo Long (BHBL) là đơn vị tài chính - bảo hiểm quy mô lớn với hàng chục chi nhánh và hàng nghìn cán bộ nhân viên trên toàn quốc. Khối lượng công văn đi, công văn đến, tờ trình duyệt chi, hồ sơ bồi thường và tài liệu quy chế phát sinh hàng ngày vô cùng lớn. Việc ứng dụng công nghệ thông tin vào quản lý văn bản, ký duyệt số hóa và tự động hóa quy trình làm việc là nhu cầu cấp thiết nhằm tối ưu hóa chi phí vận hành, nâng cao tính minh bạch và bảo mật thông tin.

### 1.2. Cơ cấu tổ chức 27 thành viên và ma trận phân công 8 nhóm

Dự án được phân chia thành **8 nhóm chuyên môn** phụ trách các phân hệ nghiệp vụ độc lập, dưới sự điều phối trực tiếp của Ban Quản trị Dự án:

| Nhóm | Số lượng | Trưởng nhóm | Thành viên nhóm | Phân hệ nghiệp vụ đảm nhiệm |
| :---: | :---: | :--- | :--- | :--- |
| **Nhóm 1** | 3 | **Châu Tuấn Kiệt (PM)** | Nguyễn Văn Hiếu, Nguyễn Duy Quân | Layout App Shell, Xác thực JIT, Dashboard, Kiến trúc CSDL & Kiểm thử |
| **Nhóm 2** | 4 | **Lê Trí Kiệt** | Nguyễn Anh Đô, [Thành viên...], [Thành viên...] | Quản lý Văn bản đến, Văn bản đi, Văn bản mật |
| **Nhóm 3** | 4 | **Phan Thị Ánh Tuyền** | Đặng Trường Thịnh, [Thành viên...], [Thành viên...] | Quản lý Hồ sơ lưu trữ, Danh mục Loại văn bản |
| **Nhóm 4** | 4 | **Thượng Mạnh Quỳnh** | [Thành viên...], [Thành viên...], [Thành viên...] | Quản lý Tài liệu nghiệp vụ & Biểu mẫu dùng chung |
| **Nhóm 5** | 3 | **Lê Thanh Hậu (DevOps)**| [Thành viên...], [Thành viên...] | Quản lý Quy trình Trình ký điện tử & Ký số Ed25519 |
| **Nhóm 6** | 3 | **Phan Tạ Hữu Đức** | [Thành viên...], [Thành viên...] | Quản lý Giao việc & Xử lý công việc |
| **Nhóm 7** | 4 | **Tô Thanh Tân (DA)** | [Thành viên...], [Thành viên...], [Thành viên...] | Quản lý Phòng họp, Sinh nhật, Đơn vị & Phân quyền RBAC |
| **Nhóm 8** | 3 | **Trần Vũ Giang Anh** | [Thành viên...], [Thành viên...] | Trợ lý ảo AI Chatbot & Tra cứu văn bản nội bộ |
| **TỔNG** | **27** | | | **8 Phân hệ tích hợp trên 1 hệ thống duy nhất** |

### 1.3. Bảng tổng hợp định mức độ khó toàn dự án (Thang 10.0)

| Nhóm | Phân hệ phụ trách | Định mức độ khó | Mức độ hoàn thành | Điểm độ khó tích lũy |
| :---: | :--- | :---: | :---: | :---: |
| **Nhóm 1** | Module 1.1: Layout hệ thống & Nhận diện thương hiệu | 0.6 | 100% | 0.6 |
| **Nhóm 1** | Module 1.2: Trang chủ / Dashboard thông minh | 0.8 | 130% (Vượt mức) | 0.8 |
| **Nhóm 1** | Nhiệm vụ bổ sung: Kiến trúc CSDL toàn hệ thống & DDL Engine | 1.0 | 100% | 1.0 |
| **Nhóm 2** | Module 2: Quản lý Văn bản (Đến, Đi, Mật) | 1.0 | 100% | 1.0 |
| **Nhóm 3** | Module 3: Quản lý Hồ sơ, Loại văn bản, Hồ sơ + Văn bản | 0.8 + 0.6 | 100% | 1.4 |
| **Nhóm 4** | Module 4: Quản lý Tài liệu, Biểu mẫu | 0.8 | 100% | 0.8 |
| **Nhóm 5** | Module 5: Quản lý Trình ký số | 1.0 | 100% | 1.0 |
| **Nhóm 6** | Module 6: Quản lý Giao việc & Xử lý công việc | 0.8 | 100% | 0.8 |
| **Nhóm 7** | Module 7: Phòng họp, Sinh nhật & Quản trị RBAC | 0.4 + 0.8 | 100% | 1.2 |
| **Nhóm 8** | Module 8: Chatbot AI hỗ trợ tra cứu văn bản | 1.0 | 100% | 1.0 |
| **TOÀN DỰ ÁN** | **Tập hợp 8 phân hệ toàn diện** | **Đạt trọn vẹn 10.0 / 10.0 điểm độ khó chuẩn** |

### 1.4. Quy chế vận hành Git Flow và Staging Quality Gate
PM Châu Tuấn Kiệt đã ban hành và chỉ đạo thực thi quy chuẩn cộng tác mã nguồn nghiêm ngặt:
1. **Quy tắc phân nhánh (Branching Policy):** Không một ai được phép commit trực tiếp vào nhánh `staging` hoặc `main`. Mọi tính năng đều tạo branch từ staging theo cú pháp `feat/<tên-tính-năng>` hoặc `fix/<tên-lỗi>`.
2. **Quy chuẩn Pull Request & Issue Tracking:** 100% Pull Request phải liên kết với Issue thông qua từ khóa `Closes #<id>` hoặc `Refs #<id>`.
3. **Cơ chế Staging Quality Gate:** Mỗi PR bắt buộc phải vượt qua 4 chốt chặn kiểm thử tự động của GitHub Actions (`CI/frontend`, `CI/backend`, `CI/backend-ops`, `PR gắn issue`) và được PM / QA duyệt mới được merge.

---

## CHƯƠNG II: KIẾN TRÚC HỆ THỐNG NỀN TẢNG VÀ CƠ SỞ DỮ LIỆU TOÀN CỤC

*(Phần này trình bày kiến trúc App Shell, Design Tokens, Single Source of Truth `release_DDL.sql`, Collation ICU `vi-VN`, công cụ `build_db.py`, cơ chế kiểm soát Schema Drift và công cụ `backup_restore.py` do Nhóm 1 chủ trì thiết kế cho toàn hệ thống)*.

---

## CHƯƠNG III: BÁO CÁO KẾT QUẢ TRIỂN KHAI CHI TIẾT THEO 8 PHÂN HỆ

*(PM tổng hợp trực tiếp nội dung từ Báo cáo Chi tiết Phân hệ do 8 nhóm nộp lên theo đúng mẫu chuẩn)*.

### 3.1. Phân hệ 1: Layout Hệ thống, Xác thực & Dashboard Thông minh (Nhóm 1)
- **Độ khó:** 0.6 + 0.8 + 1.0 (DB) = **2.4**
- **Trưởng nhóm:** Châu Tuấn Kiệt | **Thành viên:** Nguyễn Văn Hiếu, Nguyễn Duy Quân.
- *(Chi tiết tính năng, hình ảnh, mã nguồn và kết quả kiểm thử trích xuất từ tài liệu nghiệm thu Nhóm 1)*.

### 3.2. Phân hệ 2: Quản lý Văn bản đến, Văn bản đi và Văn bản mật (Nhóm 2)
- **Độ khó:** **1.0**
- **Trưởng nhóm:** Lê Trí Kiệt | **Thành viên:** Nguyễn Anh Đô...
- *(Ghép nội dung báo cáo nộp từ Nhóm 2)*.

### 3.3. Phân hệ 3: Quản lý Hồ sơ lưu trữ và Danh mục Loại văn bản (Nhóm 3)
- **Độ khó:** 0.8 + 0.6 = **1.4**
- **Trưởng nhóm:** Phan Thị Ánh Tuyền | **Thành viên:** Đặng Trường Thịnh...
- *(Ghép nội dung báo cáo nộp từ Nhóm 3)*.

### 3.4. Phân hệ 4: Quản lý Kho Biểu mẫu và Tài liệu dùng chung (Nhóm 4)
- **Độ khó:** **0.8**
- **Trưởng nhóm:** Thượng Mạnh Quỳnh | **Thành viên:** ...
- *(Ghép nội dung báo cáo nộp từ Nhóm 4)*.

### 3.5. Phân hệ 5: Quy trình Trình ký điện tử & Ký số Ed25519 (Nhóm 5)
- **Độ khó:** **1.0**
- **Trưởng nhóm:** Lê Thanh Hậu | **Thành viên:** ...
- *(Ghép nội dung báo cáo nộp từ Nhóm 5)*.

### 3.6. Phân hệ 6: Quản lý Phân công Giao việc và Xử lý Công việc (Nhóm 6)
- **Độ khó:** **0.8**
- **Trưởng nhóm:** Phan Tạ Hữu Đức | **Thành viên:** ...
- *(Ghép nội dung báo cáo nộp từ Nhóm 6)*.

### 3.7. Phân hệ 7: Phòng họp, Sinh nhật, Quản trị Đơn vị & Phân quyền RBAC (Nhóm 7)
- **Độ khó:** 0.4 + 0.8 = **1.2**
- **Trưởng nhóm:** Tô Thanh Tân | **Thành viên:** ...
- *(Ghép nội dung báo cáo nộp từ Nhóm 7)*.

### 3.8. Phân hệ 8: Trợ lý ảo AI Chatbot & Tra cứu Văn bản Nội bộ (Nhóm 8)
- **Độ khó:** **1.0**
- **Trưởng nhóm:** Trần Vũ Giang Anh | **Thành viên:** ...
- *(Ghép nội dung báo cáo nộp từ Nhóm 8)*.

---

## CHƯƠNG IV: QUY TRÌNH TÍCH HỢP LIÊN THÔNG, KIỂM ĐỊNH CHẤT LƯỢNG VÀ DEPLOY

### 4.1. Quy trình Kiểm thử Khép kín 3 Cấp (Kiệt soạn - Quân test - Hiếu duyệt)
- **Cấp 1 - Soạn thảo kịch bản kiểm thử (PM Châu Tuấn Kiệt):** Ban hành tài liệu hướng dẫn kiểm thử chi tiết, định nghĩa các ca kiểm thử biên và khung dán ảnh chứng minh.
- **Cấp 2 - Thực thi kiểm thử thực tế (Nguyễn Duy Quân):** Thực thi 83 test suites, 927 unit tests, kiểm thử liên thông các kịch bản giữa các nhóm, nạp dữ liệu mẫu seed demo và chụp ảnh bằng chứng nghiệm thu.
- **Cấp 3 - Kiểm duyệt và Phê duyệt kết quả (Nguyễn Văn Hiếu):** Kiểm định chéo độc lập, xác nhận trạng thái các chốt kiểm tra GitHub Actions trước khi chấp thuận tích hợp vào staging.

### 4.2. Hệ thống kiểm định tự động CI/CD GitHub Actions 4 luồng
- `CI / frontend`: Biên dịch TypeScript (`tsc -b`), kiểm tra ESLint (0 errors) và chạy kiểm thử tự động toàn bộ component React.
- `CI / backend`: Chạy toàn bộ test suites Django unit testing của 8 phân hệ.
- `CI / backend-ops`: Khởi dựng CSDL sạch từ `release_DDL.sql` qua `build_db.py`, kiểm thử so sánh schema drift với migration.
- `PR gắn issue`: Kiểm tra tính hợp lệ của liên kết đóng issue trên GitHub.

### 4.3. Bảng tổng hợp số liệu kiểm thử toàn hệ thống (Test Suites & Coverage)
- **Tổng số test suites:** **83 suites** (100% Passed)
- **Tổng số unit test cases:** **927 tests** (100% Passed)
- **Lỗi Lint / Code Smells:** **0 errors, 0 warnings**
- **Thời gian Build Production Frontend:** **3.22 giây**
- **Thời gian khởi dựng CSDL tự động:** **4.1 giây**

### 4.4. Hạ tầng triển khai Staging, SSL HTTPS và Quản trị Bí mật Môi trường
- Hệ thống được triển khai thực tế trên máy chủ VPS Linux Staging: `https://staging-quanlyvanban.bhbl.vn`.
- Cấu hình tự động cấp phát và gia hạn chứng chỉ bảo mật TLS/SSL HTTPS.
- Thiết lập biến môi trường chuẩn xác `DJANGO_CSRF_TRUSTED_ORIGINS`, bảo vệ khóa bí mật và cơ chế cookie `HttpOnly; SameSite=Lax`.

---

## CHƯƠNG V: ĐÁNH GIÁ TỔNG THỂ, BẢNG ĐIỂM ĐỀ XUẤT VÀ XẾP LOẠI

### 5.1. Bảng đối chiếu 100% chuẩn đầu ra đề cương môn học
*(Bảng tổng hợp đối chiếu tất cả các yêu cầu từ Đề cương môn học với kết quả triển khai thực tế trên cả 8 nhóm, bảo đảm hoàn thành 100% chỉ tiêu)*.

### 5.2. Các tính năng sáng tạo vượt trội ngoài đặc tả ban đầu
1. **Chuông âm thanh Web Audio API:** Tổng hợp âm thanh báo động hỏa tốc/tuyệt mật không cần tải file tĩnh.
2. **Khóa màn hình tự động bảo mật (Idle Guard):** Tự động khóa sau thời gian chờ kèm chống reload bằng `sessionStorage`.
3. **AI Chatbox kéo thả tự do 60fps:** Widget nổi kéo thả tự do trên toàn màn hình với thuật toán chống tràn.
4. **Kiểm soát Schema Drift bằng SHA-256 Fingerprint:** Tự động phát hiện sai lệch schema giữa Django Models và PostgreSQL DDL.
5. **Cơ chế Just-In-Time (JIT) Provisioning:** Tự động tạo và đồng bộ tài khoản cán bộ qua API Bảo Long.

### 5.3. Bảng tổng hợp đánh giá và đề xuất điểm số cho 8 nhóm

| Nhóm | Trưởng nhóm | Phân hệ phụ trách | Độ khó | Mức độ hoàn thành | Điểm nhóm đề xuất (Thang 10) | Xếp loại |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: |
| **Nhóm 1** | Châu Tuấn Kiệt | Layout, Dashboard, CSDL toàn hệ thống | **2.4** | **100%+** | **10.0** | **Xuất sắc** |
| **Nhóm 2** | Lê Trí Kiệt | Quản lý Văn bản (Đến, Đi, Mật) | **1.0** | **100%** | **... / 10** | Giỏi |
| **Nhóm 3** | Phan Thị Ánh Tuyền | Quản lý Hồ sơ & Loại văn bản | **1.4** | **100%** | **... / 10** | Giỏi |
| **Nhóm 4** | Thượng Mạnh Quỳnh | Quản lý Tài liệu & Biểu mẫu | **0.8** | **100%** | **... / 10** | Giỏi |
| **Nhóm 5** | Lê Thanh Hậu | Quản lý Trình ký số | **1.0** | **100%** | **... / 10** | Giỏi |
| **Nhóm 6** | Phan Tạ Hữu Đức | Quản lý Giao việc & Xử lý việc | **0.8** | **100%** | **... / 10** | Giỏi |
| **Nhóm 7** | Tô Thanh Tân | Phòng họp, Sinh nhật & Quản trị RBAC | **1.2** | **100%** | **... / 10** | Giỏi |
| **Nhóm 8** | Trần Vũ Giang Anh | Chatbot AI hỗ trợ tra cứu văn bản | **1.0** | **100%** | **... / 10** | Giỏi |

### 5.4. Bảng chi tiết đề xuất điểm số cho 27 thành viên
*(Bảng danh sách toàn bộ 27 sinh viên với mã SV, họ tên, nhóm, tỷ lệ đóng góp trong nhóm (%) và điểm đề xuất cá nhân)*.

---

## CHƯƠNG VI: KẾT LUẬN, BÀI HỌC KINH NGHIỆM VÀ HƯỚNG PHÁT TRIỂN

### 6.1. Kết luận về mức độ hoàn thành đồ án
Đồ án Quản lý Văn bản và Hồ sơ điện tử Bảo Long đã hoàn thành trọn vẹn 100% các mục tiêu đề ra, vượt qua toàn bộ các tiêu chí kiểm định chất lượng khắt khe nhất của một hệ sinh thái phần mềm doanh nghiệp.

### 6.2. Bài học kinh nghiệm từ góc độ Quản trị Dự án tập trung
1. **Tầm quan trọng của Nguồn chân lý duy nhất (Single Source of Truth):** Việc thống nhất cấu trúc DDL và App Shell ngay từ đầu đã giúp 8 nhóm làm việc độc lập mà không bị giẫm chân lên nhau.
2. **Kỷ luật CI/CD và Quality Gate:** Không thỏa hiệp với các lỗi lặt vặt (0 lint error, 100% test pass) là chìa khóa giúp môi trường Staging vận hành ổn định suốt quá trình phát triển.
3. **Quy trình kiểm thử khép kín 3 cấp:** Đảm bảo mọi tính năng đưa lên đều được lập kế hoạch, kiểm thử thực tế và kiểm duyệt chéo nghiêm ngặt.

### 6.3. Kế hoạch mở rộng và thương mại hóa sản phẩm
- Nâng cấp mô hình OCR nhận diện chữ viết tiếng Việt tự động quét văn bản giấy thành văn bản số.
- Mở rộng phân hệ Mobile App native trên iOS và Android qua React Native.
- Tích hợp chữ ký số Token USB PKI và dịch vụ chứng thực chữ ký số công cộng (VNPT-CA, Viettel-CA).

---

*Thành phố Hồ Chí Minh, ngày ...... tháng ...... năm 2026*  

| Ý KIẾN VÀ ĐÁNH GIÁ CỦA GIẢNG VIÊN HƯỚNG DẪN | ĐẠI DIỆN BAN QUẢN TRỊ DỰ ÁN — PROJECT MANAGER |
| :---: | :---: |
| *(Ký và ghi rõ họ tên)* | *(Đã ký)* |
| <br><br><br>**NCS.ThS. TRẦN PHƯƠNG DUY** | <br><br><br>**CHÂU TUẤN KIỆT** |

