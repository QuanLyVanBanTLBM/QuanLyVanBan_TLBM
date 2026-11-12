# DỰ ÁN QUẢN LÝ VĂN BẢN VÀ TÀI LIỆU
**Môn học:** ITC - Lập trình Django  
**Báo cáo tiến độ:** 2 tuần / lần  
**Kho mã nguồn (Repository):** [https://github.com/tranphuongduy20/QuanLyVanBan_TLBM.git](https://github.com/tranphuongduy20/QuanLyVanBan_TLBM.git)

---

## 1. BAN QUẢN TRỊ DỰ ÁN & QUY ĐỊNH CHUNG

### 1.1. Phân công Ban Quản trị Dự án
- **Project Manager (PM):** Châu Tuấn Kiệt
- **Business Analyst (BA):** Thầy giảng viên
- **Data Analyst / Database Architect (DA):** Tô Thanh Tân
- **DevOps (GitLab, Staging & Production):** Lê Thanh Hậu

### 1.2. Quy ước & Nguyên tắc nghiệp vụ chung
- **Văn bản đến:** Là văn bản từ bên ngoài gửi đến đơn vị/tổ chức.
- **Văn bản đi:** Là văn bản nội bộ ban hành gửi đi.
- **Văn bản mật:** Chỉ gửi cho đơn vị, phòng ban hoặc đích danh cán bộ nhân viên (CBNV) được phân quyền xem.
- **Định dạng thời gian (Datetime):** Định dạng ngày tháng bắt buộc phải lưu và hiển thị kèm cả **Giờ : Phút : Giây** (YYYY-MM-DD HH:mm:ss).

---

## 2. BẢNG TỔNG HỢP PHÂN CÔNG MODULE VÀ ĐỘ KHÓ

| Nhóm | Trưởng nhóm / Thành viên | Module phụ trách | Độ khó |
| :--- | :--- | :--- | :---: |
| **Nhóm 1** | Châu Tuấn Kiệt (Trưởng nhóm, PM) | Layout hệ thống, Trang chủ (Dashboard) | 0.6 / 0.8 |
| **Nhóm 2** | Lê Trí Kiệt (Trưởng nhóm), Nguyễn Anh Đô | Quản lý Văn bản (Đến, Đi, Mật) | 1.0 |
| **Nhóm 3** | Phan Thị Ánh Tuyền (Trưởng nhóm), Đặng Trường Thịnh | Quản lý Hồ sơ, Loại văn bản, Hồ sơ + Văn bản | 0.8 / 0.6 |
| **Nhóm 4** | Thượng Mạnh Quỳnh (Trưởng nhóm) | Quản lý Tài liệu, Biểu mẫu | 0.8 |
| **Nhóm 5** | Lê Thanh Hậu (Trưởng nhóm, DevOps) | Quản lý Trình ký số | 1.0 |
| **Nhóm 6** | Phan Tạ Hữu Đức (Trưởng nhóm) | Quản lý Giao việc & Xử lý công việc | 0.8 |
| **Nhóm 7** | Tô Thanh Tân (Trưởng nhóm, DA) | Phòng họp, Sinh nhật, Quản trị hệ thống (Đơn vị, Chức vụ, CBNV, Loại TL, Phân quyền) | 0.4 / 0.8 |
| **Nhóm 8** | Trần Vũ Giang Anh (Trưởng nhóm) | Chatbot AI hỗ trợ tra cứu tài liệu, quy trình, văn bản | 1.0 |

---

## 3. YÊU CẦU CHI TIẾT THEO TỪNG NHÓM

### NHÓM 1: LAYOUT HỆ THỐNG & TRANG CHỦ (DASHBOARD)
- **Thành viên:**
  1. Châu Tuấn Kiệt (Trưởng nhóm - PM)
  2. *(Các thành viên phân công)*

#### Module 1.1: Layout hệ thống (Độ khó: 0.6)
* **Chức năng chính:**
  - Trang đăng nhập: Xử lý cho 2 trường hợp (người dùng thông thường và quản trị viên).
  - Header, Footer, Menu điều hướng responsive.
  - Hệ thống chuông / thanh thông báo: Thông báo văn bản đến, văn bản đi, văn bản mật mới.
  - Trang hiển thị và chỉnh sửa thông tin người dùng cá nhân.
  - Chức năng Đăng xuất an toàn.

#### Module 1.2: Trang chủ / Dashboard (Độ khó: 0.8)
* **Chức năng chính:**
  - Thống kê tổng số lượng văn bản đi và văn bản đến theo từng năm (biểu đồ / dashboard widgets).
  - Thông báo sinh nhật CBNV theo ngày hiện tại T và ngày kế tiếp T + 1.
  - Widget lịch phòng họp / cuộc họp sắp diễn ra.
  - Thanh tìm kiếm nhanh văn bản đến và văn bản đi trực tiếp từ trang chủ.
  - Danh sách văn bản đến mới nhất (lấy top 5): Số, ký hiệu, trích yếu nội dung, ngày văn bản + nút **Xem thêm** (dẫn link qua trang danh sách văn bản đến).
  - Danh sách văn bản đi mới nhất (lấy top 5): Số, ký hiệu, trích yếu nội dung, ngày văn bản + nút **Xem thêm** (dẫn link qua trang danh sách văn bản đi).
  - Danh sách công việc cần xử lý (lấy top 5) + nút **Xem thêm** (dẫn link qua trang công việc).
  - Danh sách biểu mẫu, tài liệu chung mới nhất + nút **Xem thêm** (dẫn link qua trang tài liệu chung).
* **Giao diện tham khảo:** [Ảnh Dashboard tham khảo](https://prnt.sc/1pXqbfiWdebq) *(Tùy chọn cải tiến layout đẹp hơn)*.

---

### NHÓM 2: QUẢN LÝ VĂN BẢN (ĐẾN, ĐI, MẬT)
- **Thành viên:**
  1. Lê Trí Kiệt (Trưởng nhóm)
  2. Nguyễn Anh Đô
  3. *(Các thành viên phân công)*
- **Độ khó chung:** 1.0

#### Module 2.1: Quản lý Văn bản đến
* **Giao diện tham khảo:** [Trang danh sách](https://prnt.sc/ic8jkIvAvj4y) | [Chi tiết văn bản (Popup)](https://prnt.sc/88WHkPzSeLls) | [Thêm mới văn bản (Popup)](https://prnt.sc/hd80uOIcbHv-) | [Mẫu Import](https://prnt.sc/bgCrcgZu5QMQ)
* **Chức năng chính:**
  - Danh sách văn bản đến lọc mặc định theo ngày văn bản. Hiển thị các cột:
    + Số, ký hiệu văn bản
    + Ngày văn bản
    + Trích yếu nội dung
    + Nơi ban hành
    + Hiệu lực (Còn hiệu lực / Hết hiệu lực / Hết hiệu lực & thay thế - dòng hết hiệu lực bôi màu tối)
    + Thao tác (Popup nhiều thao tác: Chi tiết, Sửa, Xóa, Xem lịch sử xem)
  - Xem chi tiết văn bản đến (hiển thị popup toàn bộ các trường).
  - Bộ lọc và Tìm kiếm: Theo trích yếu nội dung, Số/Ký hiệu VB; lọc theo năm; lọc khoảng thời gian từ ngày... đến ngày... (theo ngày đến); lọc theo trạng thái Hiệu lực.
  - Thêm văn bản mới (Form Popup).
  - Import danh sách văn bản từ file Excel (tạo file mẫu cho người dùng tải về).
  - Xuất file Excel theo bộ lọc tìm kiếm (gặp thầy nhận mẫu template).
  - Sửa văn bản (cho phép chỉnh sửa tất cả các trường **trừ Số đến**).
  - Xóa văn bản.
  - Xem danh sách người dùng đã đọc văn bản: Hiển thị Tên - Chức danh - Đơn vị/Phòng ban - Thời gian xem. Hỗ trợ tìm kiếm theo tên và phòng ban.
  - Phân trang dữ liệu.
* **Cấu trúc trường thông tin (Database Fields):**
  - ID: Khóa chính tự tăng.
  - Hồ sơ (*): Danh sách chọn từ bảng Hồ sơ (Mặc định chọn *Hồ sơ chung*, hỗ trợ chọn nhiều hồ sơ).
  - Loại văn bản (*): Chọn từ bảng Loại văn bản (chọn được nhiều loại).
  - Năm (*): Mặc định lấy năm hiện tại, cho phép chỉnh sửa.
  - Số, ký hiệu văn bản (*): Chuỗi ký tự (Text).
  - Số đến (*): Số tự động tăng (Auto increment).
  - Ngày đến (*): Định dạng ngày giờ.
  - Trích yếu nội dung (*): Text mô tả tóm tắt nội dung.
  - Nơi ban hành: Text.
  - Ngày văn bản: Định dạng ngày giờ.
  - Đơn vị nhận: Danh sách chọn từ bảng Đơn vị (chọn được nhiều đơn vị).
  - Người nhận: Tự động lọc danh sách nhân viên thuộc các đơn vị nhận đã chọn (chọn được nhiều người).
  - Người ký: Text.
  - Chức vụ người ký: Text.
  - Hết hiệu lực (*): Còn hiệu lực / Hết hiệu lực / Hết hiệu lực và thay thế.
  - Ngày hết hiệu lực: Định dạng ngày giờ.
  - Link văn bản thay thế: Text / URL.
  - Ghi chú: Text.
  - File đính kèm (*): Chỉ chấp nhận định dạng .pdf, .doc, .docx, .jpg, .jpeg, .png.
  - Trạng thái hiển thị: Checkbox mặc định chọn (Hiển thị công khai; nếu tắt chỉ Admin thấy và bôi màu khác).
  - Gửi mail toàn hệ thống: Checkbox mặc định không chọn (Gửi thông báo mail khi tích).

#### Module 2.2: Quản lý Văn bản đi
* **Giao diện tham khảo:** [Trang danh sách](https://prnt.sc/ic8jkIvAvj4y) | [Chi tiết văn bản (Popup)](https://prnt.sc/88WHkPzSeLls) | [Thêm mới văn bản (Popup)](https://prnt.sc/hd80uOIcbHv-) | [Mẫu Import](https://prnt.sc/bgCrcgZu5QMQ)
* **Chức năng chính:**
  - Danh sách văn bản đi lọc theo ngày văn bản: Số, ký hiệu VB; Ngày văn bản; Trích yếu nội dung; Người ký; Ngày ban hành; Hiệu lực; Thao tác.
  - Chi tiết văn bản đi (Popup đầy đủ thông tin).
  - Tìm kiếm và bộ lọc đa điều kiện: Trích yếu, Số ký hiệu, Lọc theo năm, lọc khoảng ngày đến, lọc Hiệu lực.
  - Thêm mới văn bản đi (Popup).
  - Import file Excel (theo file mẫu chuẩn).
  - Xuất Excel theo bộ lọc.
  - Sửa văn bản (cho phép chỉnh sửa tất cả các trường **trừ Số đi**).
  - Xóa văn bản.
  - Theo dõi người dùng đã xem văn bản (Tên, Chức danh, Phòng ban, Thời gian xem, có tìm kiếm).
  - Phân trang dữ liệu.
* **Cấu trúc trường thông tin (Database Fields):**
  - ID: Khóa chính.
  - Hồ sơ (*): Chọn từ bảng Hồ sơ (Mặc định Hồ sơ chung, chọn nhiều).
  - Loại văn bản (*): Chọn từ bảng Loại văn bản (chọn nhiều).
  - Năm (*): Mặc định năm hiện tại, cho sửa.
  - Số, ký hiệu văn bản (*): Text.
  - Số (*): Số đi cộng tự động tăng.
  - Trích yếu nội dung (*): Text.
  - Ngày ban hành (*): Ngày giờ.
  - Nơi ban hành: Text.
  - Ngày văn bản: Ngày giờ.
  - Đơn vị nhận: Chọn danh sách đơn vị nhận (chọn nhiều).
  - Người nhận: Chọn danh sách nhân sự thuộc các đơn vị đã chọn (chọn nhiều).
  - Người ký: Text.
  - Chức vụ: Text.
  - Hết hiệu lực (*): Còn hiệu lực / Hết hiệu lực / Hết hiệu lực và thay thế.
  - Ngày hết hiệu lực: Ngày giờ.
  - Link văn bản thay thế: Text / URL.
  - Ghi chú: Text.
  - File đính kèm (*): File PDF, DOC, JPG, JPEG, PNG.
  - Trạng thái hiển thị: Mặc định true.
  - Gửi mail toàn hệ thống: Mặc định false.

#### Module 2.3: Quản lý Văn bản mật
* **Giao diện tham khảo:** [Trang danh sách](https://prnt.sc/ic8jkIvAvj4y) | [Chi tiết văn bản (Popup)](https://prnt.sc/88WHkPzSeLls) | [Thêm mới (Popup)](https://prnt.sc/hd80uOIcbHv-)
* **Chức năng chính:**
  - Bảo mật danh sách: Chỉ người dùng thuộc đơn vị nhận hoặc đích danh người nhận mới có quyền xem nội dung và tải file.
  - Danh sách văn bản mật lọc theo ngày văn bản: Số/ký hiệu, Ngày VB, Trích yếu, Người ký, Ngày ban hành, Hiệu lực, Thao tác.
  - Chi tiết văn bản mật (Popup).
  - Bộ lọc, tìm kiếm, thêm mới, import excel, xuất file excel theo bộ lọc.
  - Sửa văn bản (chỉnh sửa các trường), Xóa văn bản.
  - Theo dõi danh sách cán bộ đã mở xem văn bản mật (Audit log).
  - Phân trang.
* **Cấu trúc trường thông tin (Database Fields):**
  - ID: Khóa chính.
  - Hồ sơ (*): Chọn từ bảng Hồ sơ (Mặc định Hồ sơ chung, chọn nhiều).
  - Loại văn bản (*): Chọn từ bảng Loại văn bản (chọn nhiều).
  - Năm (*): Mặc định năm hiện tại, cho sửa.
  - Số, ký hiệu văn bản (*): Text.
  - Trích yếu nội dung (*): Text.
  - Ngày ban hành: Ngày giờ.
  - Nơi ban hành: Text.
  - Ngày văn bản: Ngày giờ.
  - Đơn vị nhận: Chọn đơn vị (Toàn bộ thành viên trong đơn vị này sẽ được xem).
  - Người nhận: Chọn cụ thể cán bộ nhân viên đích danh được phép xem.
  - Người ký: Text.
  - Chức vụ: Text.
  - Hết hiệu lực (*): Còn hiệu lực / Hết hiệu lực / Hết hiệu lực và thay thế.
  - Ngày hết hiệu lực: Ngày giờ.
  - Link văn bản thay thế: Text.
  - Ghi chú: Text.
  - File đính kèm (*): File PDF, DOC, JPG, JPEG, PNG.
  - Trạng thái hiển thị: Checkbox mặc định tick.
  - Gửi mail toàn hệ thống: Checkbox mặc định không tick.

---

### NHÓM 3: QUẢN LÝ HỒ SƠ & VĂN BẢN THEO HỒ SƠ
- **Thành viên:**
  1. Phan Thị Ánh Tuyền (Trưởng nhóm)
  2. Đặng Trường Thịnh
  3. *(Các thành viên phân công)*

#### Module 3.1: Trang Danh mục hồ sơ - Cấp 1 (Độ khó: 0.8)
* **Giao diện tham khảo:** [Danh sách hồ sơ](https://prnt.sc/Tq0VZhXXxYYL) | [Thêm mới hồ sơ (Popup)](https://prnt.sc/FLvyZBRPqck-)
* **Chức năng chính:**
  - Danh sách hồ sơ sắp xếp theo số thứ tự (STT) ưu tiên hiển thị (Mặc định *Hồ sơ chung* luôn ở đầu tiên).
  - Các cột hiển thị: STT ưu tiên, Số Ký hiệu hồ sơ, Tên Hồ sơ, Ngày lập, Thao tác (Popup Sửa, Xóa).
  - Bộ lọc và tìm kiếm theo Tên hồ sơ hoặc Số ký hiệu hồ sơ, lọc theo năm lập.
  - Thêm hồ sơ mới (Form Popup).
  - Xuất Excel (Toàn bộ hoặc theo bộ lọc).
  - Sửa thông tin hồ sơ (Chỉnh sửa được tất cả các trường).
  - Xóa hồ sơ.
  - Phân trang.
* **Cấu trúc trường thông tin (Database Fields):**
  - ID: Khóa chính.
  - STT ưu tiên hiển thị (*): Số nguyên, kiểm tra tính duy nhất (Lấy tự động: max(STT) + 1).
  - Số Ký hiệu hồ sơ (*): Text.
  - Tên Hồ sơ (*): Text.
  - Người lập hồ sơ (*): Tự động lấy tên tài khoản người dùng đang đăng nhập.
  - Ngày lập: Ngày giờ.
  - Ghi chú: Text.

#### Module 3.2: Trang Loại văn bản - Cấp 2 (Độ khó: 0.8)
* **Giao diện tham khảo:** [Danh sách loại văn bản Cấp 2](https://prnt.sc/1q4meSpQ3WW_) | [Thêm mới (Popup)](https://prnt.sc/FLvyZBRPqck-)
* **Chức năng chính:**
  - Khi người dùng click vào một Hồ sơ ở Cấp 1, hệ thống chuyển sang trang danh sách Loại văn bản thuộc hồ sơ đó (đóng vai trò như các tag phân loại).
  - Danh sách loại văn bản: STT, Tên loại văn bản, Ngày lập, Thao tác (Popup Sửa, Xóa).
  - Có nút **Quay lại** trang Cấp 1.
  - Tìm kiếm theo Tên loại văn bản, lọc theo năm.
  - Thêm loại văn bản mới (Popup).
  - Sửa, Xóa loại văn bản.
  - Phân trang.
* **Cấu trúc trường thông tin (Database Fields):**
  - ID: Khóa chính.
  - Tên loại văn bản (*): Text.
  - Ngày lập: Ngày giờ.
  - Ghi chú: Text.

#### Module 3.3: Trang Danh sách Văn bản theo Hồ sơ (Độ khó: 0.6)
* **Giao diện tham khảo:** [Danh sách văn bản theo hồ sơ](https://prnt.sc/HfgxOQY2vjMA)
* **Chức năng chính:**
  - Hiển thị danh sách các văn bản thuộc một loại hồ sơ đã chọn.
  - Các cột: STT, Số ký hiệu, Trích yếu nội dung, Ngày văn bản, Loại văn bản (Văn bản đến, Văn bản đi, Văn bản mật).
  - Bộ lọc và Tìm kiếm theo Trích yếu hoặc Số ký hiệu văn bản; lọc theo năm; lọc loại văn bản (Đến/Đi/Mật).
  - Xuất Excel danh sách theo bộ lọc.
  - Nút **Quay lại** trang trước.
  - Click vào dòng văn bản xem được chi tiết văn bản tương tự Module Văn bản.
  - Phân trang.

---

### NHÓM 4: QUẢN LÝ TÀI LIỆU VÀ BIỂU MẪU (BM)
- **Thành viên:**
  1. Thượng Mạnh Quỳnh (Trưởng nhóm)
  2. *(Các thành viên phân công)*
- **Độ khó chung:** 0.8

#### Module 4.1: Danh mục Tài liệu - Cấp 1
* **Giao diện tham khảo:** [Danh mục tài liệu](https://prnt.sc/Tq0VZhXXxYYL) | [Thêm danh mục (Popup)](https://prnt.sc/FLvyZBRPqck-)
* **Chức năng chính:**
  - Danh sách tài liệu sắp xếp theo STT ưu tiên (Mặc định *Tài liệu, BM chung* hiển thị đầu tiên).
  - Các cột: STT ưu tiên, Tên tài liệu, Ngày lập, Thao tác (Popup Sửa, Xóa).
  - Tìm kiếm theo Tên tài liệu hoặc Số ký hiệu; lọc theo năm.
  - Thêm danh mục tài liệu mới (Popup).
  - Xuất Excel (Tất cả hoặc theo bộ lọc).
  - Sửa danh mục tài liệu (sửa tất cả các trường), Xóa danh mục tài liệu.
  - Phân trang.
* **Cấu trúc trường thông tin (Database Fields):**
  - ID: Khóa chính.
  - STT ưu tiên hiển thị (*): Số nguyên, kiểm tra trùng lặp (Tự động lấy max + 1).
  - Số Ký hiệu tài liệu: Text.
  - Tên tài liệu (*): Text.
  - Người lập tài liệu (*): Tự động lấy tài khoản người tạo.
  - Ngày lập: Ngày giờ.
  - Ghi chú: Text.

#### Module 4.2: Danh sách Tài liệu chung
* **Giao diện tham khảo:** [Chi tiết tài liệu (Popup)](https://prnt.sc/88WHkPzSeLls) | [Thêm tài liệu (Popup)](https://prnt.sc/hd80uOIcbHv-)
* **Chức năng chính:**
  - Danh sách tài liệu: STT, Tiêu đề, Nơi ban hành, Hiệu lực, Thao tác (Sửa, Xóa).
  - Chi tiết tài liệu dạng Popup (hiển thị đầy đủ tất cả các trường).
  - Tìm kiếm tiêu đề tài liệu; lọc theo năm ban hành; lọc theo Loại tài liệu (Dropdown option).
  - Thêm tài liệu mới (Popup đầy đủ các trường nhập).
  - Xuất Excel theo bộ lọc tìm kiếm.
  - Sửa tài liệu (sửa tất cả các trường), Xóa tài liệu.
  - Phân trang.
* **Cấu trúc trường thông tin (Database Fields):**
  - ID: Khóa chính.
  - Loại tài liệu (*): Lấy danh sách từ bảng Loại tài liệu (chọn được nhiều loại).
  - Ký hiệu tài liệu: Text.
  - Tiêu đề (*): Text.
  - Ngày đăng (*): Định dạng ngày giờ.
  - Nơi ban hành: Text.
  - Hết hiệu lực (*): Còn hiệu lực / Hết hiệu lực (dòng tài liệu đổi màu tối trên danh sách) / Hết hiệu lực và thay thế.
  - Ngày hết hiệu lực: Ngày giờ.
  - Link tài liệu thay thế: Text.
  - Ghi chú: Text.
  - File đính kèm (*): Chỉ chấp nhận định dạng .pdf, .doc, .docx, .jpg, .jpeg, .png, .zip, .rar và kích thước < 20MB.
  - Hiển thị: Lựa chọn *Tất cả* hoặc *Nội bộ phòng ban*.

---

### NHÓM 5: QUẢN LÝ TRÌNH KÝ SỐ
- **Thành viên:**
  1. Lê Thanh Hậu (Trưởng nhóm - DevOps)
  2. *(Các thành viên phân công)*
- **Độ khó:** 1.0

* **Chức năng chính (Nhóm gặp thầy để trao đổi và chốt chi tiết):**
  - **Tạo văn bản trình ký:** Cho phép chọn quy trình phê duyệt ký, tự động hiển thị thông tin người tạo văn bản, thiết lập mức độ khẩn/ưu tiên.
  - **Danh sách văn bản trình ký:** Xem danh sách, lọc văn bản theo trạng thái (Chờ ký, Đã ký, Từ chối ký, Đang xử lý).
  - **Tìm kiếm và bộ lọc:** Tìm kiếm theo từ khóa, lọc theo phòng ban trình ký.
  - **Chi tiết văn bản trình ký:** Hiển thị trực quan **sơ đồ luồng ký (quy trình ký qua từng cấp)**.
  - **Thông báo & Tự động gửi Email:** Gửi thông báo trên hệ thống và email nhắc việc đến người cần ký duyệt khi đến lượt.
  - **Chữ ký số:** Tích hợp ký số điện tử trên văn bản.
* **Cấu trúc trường thông tin (Database Fields):**
  - Nhóm tự đề xuất danh sách các trường thông tin chi tiết và báo thầy phụ trách phê duyệt.

---

### NHÓM 6: QUẢN LÝ GIAO VIỆC VÀ XỬ LÝ CÔNG VIỆC
- **Thành viên:**
  1. Phan Tạ Hữu Đức (Trưởng nhóm)
  2. *(Các thành viên phân công)*
- **Độ khó:** 0.8

* **Giao diện tham khảo:** [Trang danh sách công việc](https://prnt.sc/NiLyNALUO0SR) | [Chi tiết xử lý CV](https://prnt.sc/4A1Ob6rBbbIY) | [Gửi ý kiến phản hồi](https://prnt.sc/T5M1V12Zqnky) | [Thêm công việc mới (Popup)](https://prnt.sc/XgmH5-A9sVIm)
* **Chức năng chính:**
  - **Danh sách công việc:** Mặc định lọc theo ngày giao (ngày tạo). Hiển thị các trường:
    + STT
    + Tiêu đề công việc
    + Người giao việc
    + Yêu cầu xử lý
    + Người thực hiện (Chủ trì / Tham gia)
    + Ngày giao việc
    + Hạn xử lý
    + Trạng thái công việc: Tính toán tự động; đánh dấu Hoàn thành khi Người giao hoặc Người chủ trì bấm xác nhận hoàn thành.
    + Thao tác: Menu Popup gồm Sửa, Xóa; nút **Xử lý CV** (chuyển sang trang chi tiết công việc).
  - **Chi tiết xử lý công việc:** Theo dõi tiến độ, lịch sử thực hiện, các file báo cáo; chức năng gửi ý kiến trao đổi / phản hồi giữa các cán bộ.
  - **Bộ lọc & Tìm kiếm:** Tìm kiếm theo tiêu đề công việc, lọc theo ngày tháng, lọc theo trạng thái tiến độ (Chưa thực hiện, Đang thực hiện, Quá hạn, Hoàn thành).
  - **Thêm công việc mới:** Form Popup nhập đầy đủ các trường thông tin.
  - **Xuất file Excel:** Xuất danh sách theo bộ lọc tìm kiếm (gặp thầy nhận file mẫu).
  - **Sửa công việc:** Cho phép chỉnh sửa tất cả các trường.
  - **Xóa công việc.**
  - **Gửi Email tự động:** Gửi thông báo giao việc, nhắc hạn qua mail cho các CBNV có liên quan.
  - **Phân trang dữ liệu.**
* **Cấu trúc trường thông tin (Database Fields):**
  - ID: Khóa chính.
  - Tiêu đề (*): Text.
  - Ngày tạo (*): Tự động lấy ngày giờ hiện tại của hệ thống.
  - Ngày xử lý / Hạn xử lý (*): Định dạng ngày giờ.
  - Yêu cầu xử lý (*): Text mô tả chi tiết nội dung cần làm.
  - Người tạo (*): Tự động lấy thông tin người dùng đang tạo.
  - Chủ trì giải quyết công việc (*): Chọn từ danh sách CBNV (Chỉ được chọn duy nhất 1 người).
  - Chỉ đạo - Theo dõi tiến độ (*): Chọn từ danh sách CBNV (Được chọn nhiều người).
  - Cán bộ tham gia giải quyết công việc (*): Chọn từ danh sách CBNV (Được chọn nhiều người).
  - File đính kèm (*): Định dạng file chấp nhận: .pdf, .doc, .docx, .jpg, .jpeg, .png.
  - Trạng thái hiển thị: Checkbox mặc định chọn (Nếu bỏ tick, chỉ Quản trị hệ thống thấy và đổi màu hiển thị).

---

### NHÓM 7: PHÒNG HỌP, SINH NHẬT & QUẢN TRỊ HỆ THỐNG
- **Thành viên:**
  1. Tô Thanh Tân (Trưởng nhóm - DA)
  2. *(Các thành viên phân công)*

#### Module 7.1: Quản lý Phòng họp (Độ khó: 0.4)
* **Chức năng chính:**
  - Thêm mới phòng họp / Đăng ký đặt phòng họp.
  - Danh sách đặt phòng họp, xem theo ngày, tuần, tháng, kiểm tra trùng lịch phòng.

#### Module 7.2: Quản lý Sinh nhật (Độ khó: 0.4)
* **Giao diện tham khảo:** [Lịch và Email sinh nhật](https://prnt.sc/mvqGxyMMh4Lw)
* **Chức năng chính:**
  - Hiển thị thông tin ngày sinh nhật CBNV trực quan trên giao diện Calendar / Dashboard.
  - Tự động gửi Email chúc mừng sinh nhật cho CBNV khi đến đúng ngày sinh nhật (Hệ thống tự thiết kế mẫu email thiệp chúc mừng đẹp mắt).

#### Module 7.3: Quản trị Hệ thống - Đơn vị, Phòng ban (Độ khó: 0.8)
* **Chức năng chính:**
  - Quản lý Khối / Khu vực (Cấp 1): Thêm, sửa, xóa Khối/Khu vực (gồm ID, Tên Khối/Khu vực).
  - Quản lý Đơn vị, Phòng ban (Cấp 2): Chọn Khối/Khu vực, nhập Tên đơn vị, Địa chỉ, Số điện thoại, Email.
  - Danh sách đơn vị, phòng ban được sắp xếp theo số thứ tự (STT) ưu tiên.
  - Tìm kiếm và xuất danh sách ra file Excel.
* **Cấu trúc trường thông tin (Database Fields):**
  - ID: Khóa chính.
  - STT ưu tiên hiển thị (*): Số nguyên duy nhất (Tự động lấy max + 1).
  - Tên đơn vị, phòng/ban (*): Text.
  - Địa chỉ: Text.
  - Điện thoại: Chuỗi số.
  - Email: Định dạng Email.
  - isPublic (*): Boolean mặc định True (Nếu False vẫn hiển thị cho Admin nhưng đổi màu cảnh báo).
  - Ghi chú: Text.

#### Module 7.4: Quản trị Hệ thống - Danh mục Chức vụ
* **Giao diện tham khảo:** [Mẫu Import](https://prnt.sc/bgCrcgZu5QMQ)
* **Chức năng chính:**
  - Thêm chức vụ mới.
  - Danh sách chức vụ sắp xếp theo STT ưu tiên.
  - Import file Excel chức vụ (cung cấp template mẫu cho người dùng tải về và tải lên).
  - Tìm kiếm chức vụ.
* **Cấu trúc trường thông tin (Database Fields):**
  - ID: Khóa chính.
  - STT ưu tiên hiển thị (*): Kiểm tra trùng lặp (Tự động lấy max + 1).
  - Tên chức vụ (*): Text.
  - isPublic (*): Boolean mặc định True.
  - Ghi chú: Text.

#### Module 7.5: Quản trị Hệ thống - Quản lý Cán bộ Nhân viên (CBNV)
* **Giao diện tham khảo:** [Danh sách CBNV](https://prnt.sc/zZmIyhKgJAR1) | [Thêm mới CBNV](https://prnt.sc/1rCA5V5dkJ5T) | [Mẫu Import](https://prnt.sc/bgCrcgZu5QMQ)
* **Chức năng chính:**
  - Thêm mới CBNV (tạo tài khoản, mật khẩu ban đầu).
  - Danh sách CBNV hiển thị theo thứ tự: Tên đơn vị có STT ưu tiên, Chức vụ.
    + STT
    + Họ và tên
    + Đơn vị
    + Chức danh
    + Nhóm quyền (Cột này chỉ hiển thị đối với tài khoản Admin)
    + Email
    + SĐT cá nhân / SĐT bàn
    + Trạng thái: Đang làm việc / Đã nghỉ việc (Nếu nghỉ việc thì bôi đỏ nổi bật)
    + Thao tác: Sửa thông tin, Xóa tài khoản
  - Import danh sách CBNV từ file Excel (kèm file mẫu download).
  - Chi tiết CBNV: Dạng Popup hiển thị đầy đủ thông tin nhưng **che/ẩn năm sinh** để bảo mật thông tin cá nhân.
  - Phân trang dữ liệu.
* **Cấu trúc trường thông tin (Database Fields):**
  - ID: Khóa chính.
  - Họ và tên (*): Text.
  - Ngày tháng năm sinh (*): Định dạng ngày tháng, giao diện ẩn năm sinh.
  - Chức vụ (*): Khóa ngoại chọn từ danh sách Bảng Chức vụ.
  - Chức danh: Text.
  - Nhóm quyền (*): Khóa ngoại chọn từ bảng Nhóm quyền.
  - Email: Text email hợp lệ.
  - SĐT: Text.
  - Đơn vị (*): Khóa ngoại chọn từ bảng Đơn vị, phòng ban.
  - Mật khẩu do IT cấp: Hash mật khẩu (Chỉ hiển thị với Admin khi cấp/đổi).
  - isPublic (*): Boolean mặc định True cho trạng thái tài khoản.
  - Ghi chú: Text.

#### Module 7.6: Quản trị Hệ thống - Loại tài liệu, biểu mẫu
* **Giao diện tham khảo:** [Danh sách loại tài liệu BM](https://prnt.sc/wV_gimvOFr5m)
* **Chức năng chính:**
  - Danh sách loại tài liệu: STT, Tên loại, Ghi chú, Thao tác (Sửa, Xóa).
  - Tìm kiếm theo Tên loại.
  - Thêm mới loại tài liệu/biểu mẫu.
  - Phân trang.
* **Cấu trúc trường thông tin (Database Fields):**
  - ID: Khóa chính.
  - Tên loại (*): Text.
  - isPublic (*): Boolean mặc định True.
  - Ghi chú: Text.

#### Module 7.7: Quản trị Hệ thống - Phân quyền người dùng
* **Giao diện tham khảo:** [Danh sách nhóm quyền](https://prnt.sc/sLph-P65oMvA) | [Thêm/Sửa/Xóa nhóm quyền](https://prnt.sc/Xw09ZR9aeg4-) | [Ma trận phân quyền theo nhóm](https://prnt.sc/X_Y930LcU1K1)
* **Chức năng chính:**
  - Quản lý danh sách nhóm quyền / vai trò người dùng (Roles / Groups).
  - Thêm, sửa, xóa nhóm quyền.
  - Thiết lập ma trận phân quyền chi tiết (Xem, Thêm, Sửa, Xóa, Duyệt, Ký, ...) cho từng module ứng dụng.
* **Database:** Thiết kế các bảng Database tương ứng (Group, Permission, Group_Permissions, User_Groups).

---

### NHÓM 8: CHATBOT AI HỖ TRỢ TRA CỨU
- **Thành viên:**
  1. Trần Vũ Giang Anh (Trưởng nhóm)
  2. *(Các thành viên phân công)*
- **Độ khó:** 1.0

* **Chức năng chính:**
  - Tích hợp Chatbox AI thông minh để hỗ trợ người dùng tra cứu nhanh:
    + Tra cứu tài liệu, biểu mẫu, quy trình nội bộ.
    + Hỏi đáp nội dung văn bản đến, văn bản đi, tìm kiếm trích yếu và số hiệu văn bản liên quan.
  - Giao diện Box Chat tiện lợi, hiển thị cố định ở góc màn hình hoặc trang riêng.
  - Hỗ trợ dẫn đường link tài liệu/web trực tiếp ngay trong câu trả lời tương tự ChatGPT.

---

## 4. DANH MỤC ĐƠN VỊ, PHÒNG BAN

| Cấp 1 (Khối / Khu vực) | Cấp 2 (Ban / Phòng / Chi nhánh) |
| :--- | :--- |
| **HỘI ĐỒNG QUẢN TRỊ** | • HỘI ĐỒNG QUẢN TRỊ<br>• BAN KIỂM TOÁN NỘI BỘ |
| **VĂN PHÒNG HỘI ĐỒNG QUẢN TRỊ** | • VĂN PHÒNG HỘI ĐỒNG QUẢN TRỊ |
| **BAN TỔNG GIÁM ĐỐC** | • BAN TỔNG GIÁM ĐỐC<br>• GIÁM ĐỐC VÙNG |
| **VĂN PHÒNG BAN ĐIỀU HÀNH TẠI TP.HCM & HÀ NỘI** | • VĂN PHÒNG BAN ĐIỀU HÀNH |
| **KHỐI KINH DOANH** | • BAN KHÁCH HÀNG DOANH NGHIỆP<br>• BAN KHÁCH HÀNG QUA MÔI GIỚI<br>• BAN BANCASSURANCE<br>• BAN KHÁCH HÀNG CÁ NHÂN<br>• BAN CHĂM SÓC KHÁCH HÀNG ĐT<br>• BAN DỰ ÁN PHÁT TRIỂN SẢN PHẨM LIÊN KẾT VỚI CÁC CÔNG TY DỊCH VỤ VIỄN THÔNG<br>• BAN DỰ ÁN LỚN<br>• BAN DỰ ÁN KHÁCH HÀNG QUA ĐẠI LÝ |
| **KHỐI NGHIỆP VỤ** | • BAN BẢO HIỂM CON NGƯỜI<br>• BAN BẢO HIỂM TÀI SẢN KỸ THUẬT<br>• BAN TÁI BẢO HIỂM<br>• BAN BẢO HIỂM XE CƠ GIỚI<br>• BAN BẢO HIỂM HÀNG HẢI, HÀNG KHÔNG, DẦU KHÍ, NĂNG LƯỢNG |
| **KHỐI HỖ TRỢ** | • LÃNH ĐẠO KHỐI<br>• BAN HÀNH CHÍNH QUẢN TRỊ<br>• BAN NHÂN SỰ<br>• BAN PHÁP CHẾ<br>• BAN CÔNG NGHỆ THÔNG TIN<br>• BAN TRUYỀN THÔNG VÀ MARKETING |
| **KHỐI QUẢN LÝ RỦI RO** | • BAN QUẢN LÝ RỦI RO VÀ TUÂN THỦ |
| **KHỐI TÀI CHÍNH** | • BAN ĐẦU TƯ<br>• BAN TÀI CHÍNH KẾ HOẠCH<br>• BAN DỰ ÁN MIS |
| **KHỐI KẾ TOÁN** | • LÃNH ĐẠO KHỐI<br>• BAN KẾ TOÁN |
| **VĂN PHÒNG 2** | • VĂN PHÒNG 2 |
| **KHU VỰC THÀNH PHỐ HỒ CHÍ MINH** | • SỞ GIAO DỊCH BẢO LONG<br>• BẢO LONG TP HỒ CHÍ MINH<br>• BẢO LONG SÀI GÒN<br>• BẢO LONG GIA ĐỊNH<br>• BẢO LONG BẾN THÀNH<br>• BẢO LONG NAM SÀI GÒN<br>• BẢO LONG TÂN SƠN NHẤT<br>• BẢO LONG ĐÔNG SÀI GÒN<br>• BẢO LONG ĐÔNG PHƯƠNG<br>• TRUNG TÂM KINH DOANH THỦ THIÊM |
| **KHU VỰC MIỀN BẮC** | • BẢO LONG HÀ NỘI<br>• BẢO LONG THỦ ĐÔ<br>• BẢO LONG THĂNG LONG<br>• BẢO LONG THÁI NGUYÊN<br>• BẢO LONG QUẢNG NINH<br>• BẢO LONG HẢI PHÒNG<br>• BẢO LONG PHÚ THỌ<br>• BẢO LONG BẮC NINH<br>• BẢO LONG HẢI DƯƠNG<br>• BẢO LONG NAM ĐỊNH<br>• BẢO LONG VĨNH PHÚC<br>• BẢO LONG ĐÔNG HẢI<br>• SỞ GIAO DỊCH MIỀN BẮC<br>• BẢO LONG NINH BÌNH<br>• BẢO LONG THÁI BÌNH<br>• BẢO LONG ĐÔNG ĐÔ<br>• BẢO LONG THANH HÓA |
| **KHU VỰC MIỀN TRUNG TÂY NGUYÊN** | • BẢO LONG KV TÂY NGUYÊN (DAKLAK)<br>• BẢO LONG PHÚ YÊN<br>• BẢO LONG ĐÀ NẴNG<br>• BẢO LONG TRUNG BỘ (HUẾ)<br>• BẢO LONG BẮC TRUNG BỘ (NGHỆ AN)<br>• BẢO LONG KHÁNH HÒA<br>• BẢO LONG BÌNH ĐỊNH<br>• BẢO LONG BÌNH THUẬN<br>• BẢO LONG QUẢNG NGÃI<br>• BẢO LONG GIA LAI<br>• BẢO LONG LÂM ĐỒNG<br>• BẢO LONG QUẢNG BÌNH<br>• TRUNG TÂM KINH DOANH SÔNG HÀN |
| **KHU VỰC ĐÔNG NAM BỘ** | • BẢO LONG BÌNH DƯƠNG<br>• BẢO LONG VŨNG TÀU<br>• BẢO LONG ĐỒNG NAI<br>• BẢO LONG TÂY NINH<br>• BẢO LONG LONG AN<br>• BẢO LONG CẦN THƠ<br>• BẢO LONG CÀ MAU<br>• BẢO LONG KIÊN GIANG<br>• BẢO LONG ĐỒNG THÁP |
| **GIÁM ĐỊNH VÙNG** | • GIÁM ĐỊNH VÙNG |

---

## 5. DANH MỤC HỒ SƠ VÀ TÀI LIỆU BIỂU MẪU MẪU

### 5.1. Danh mục Hồ sơ
| Cấp 1 | Cấp 2 |
| :--- | :--- |
| **Hồ sơ chung** | • Quyết định<br>• Nghị định<br>• Tờ trình<br>• Quy định<br>• ... |
| **Hồ sơ Ban Nhân sự** | *(Các loại hồ sơ của Ban Nhân sự)* |
| **Hồ sơ Bảo Long Bến Thành** | *(Các loại hồ sơ của Bảo Long Bến Thành)* |
| **Các đơn vị, phòng ban cấp 2** | *(Theo từng đơn vị/phòng ban tương ứng)* |

### 5.2. Danh mục Tài liệu, Biểu mẫu
| Cấp 1 | Cấp 2 |
| :--- | :--- |
| **Tài liệu chung** | • Tài liệu bảo hiểm<br>• Biểu mẫu bảo hiểm<br>• Tờ trình<br>• Quy định<br>• ... |
| **Hồ sơ Ban Nhân sự** | *(Biểu mẫu tài liệu Ban Nhân sự)* |
| **Hồ sơ Bảo Long Bến Thành** | *(Biểu mẫu tài liệu Bảo Long Bến Thành)* |
| **Các đơn vị, phòng ban cấp 2** | *(Theo từng đơn vị/phòng ban tương ứng)* |

---

## 6. DANH SÁCH LỚP VÀ PHÂN CHIA NHÓM

### 6.1. Thống kê sĩ số các nhóm
| Nhóm | Số lượng thành viên |
| :--- | :---: |
| Nhóm 1 | 2 |
| Nhóm 2 | 4 |
| Nhóm 3 | 4 |
| Nhóm 4 | 4 |
| Nhóm 5 | 3 |
| Nhóm 6 | 3 |
| Nhóm 7 | 4 |
| Nhóm 8 | 3 |
| **Tổng cộng** | **27** |

### 6.2. Danh sách sinh viên
| STT | Mã SV | Họ và tên | Vai trò / Ghi chú |
| :---: | :---: | :--- | :--- |
| 1 | 501250117 | Trần Vũ Giang Anh | Trưởng nhóm 8 |
| 2 | 501250390 | Nguyễn Duy Bảo | |
| 3 | 501250347 | Nguyễn Anh Đô | Thành viên Nhóm 2 |
| 4 | 501250397 | Phan Tạ Hữu Đức | Trưởng nhóm 6 |
| 5 | 501250433 | Lê Thanh Hậu | DevOps, Trưởng nhóm 5 |
| 6 | 501250065 | Nguyễn Phan Minh Hiếu | |
| 7 | 501250367 | Nguyễn Văn Hiếu | |
| 8 | 501250161 | Lê Duy Khánh | |
| 9 | 501250176 | Nguyễn Tấn Lộc Khiêm | |
| 10 | 506250495 | Châu Tuấn Kiệt | Project Manager (PM), Trưởng nhóm 1 |
| 11 | 501250154 | Lê Trí Kiệt | Trưởng nhóm 2 |
| 12 | 501250354 | Huỳnh Vương Thanh Nhã | |
| 13 | 501250145 | Nguyễn Thị Yến Nhi | |
| 14 | 501250394 | Đỗ Ngọc Phát | |
| 15 | 501250126 | Đỗ Trung Phong | |
| 16 | 501250285 | Huỳnh Mạnh Quân | |
| 17 | 501250143 | Nguyễn Duy Quân | |
| 18 | 501250341 | Đỗ Mạnh Quang | |
| 19 | 501250118 | Thượng Mạnh Quỳnh | Trưởng nhóm 4 |
| 20 | 501250471 | Lê Thành Tài | |
| 21 | 501250309 | Tô Thanh Tân | Data Analyst (DA), Trưởng nhóm 7 |
| 22 | 501250392 | Trần Nhật Tân | |
| 23 | 501250475 | Đặng Trường Thịnh | Thành viên Nhóm 3 |
| 24 | 501250352 | Nguyễn Chí Tín | |
| 25 | 501250299 | Trần Đình Tình | |
| 26 | 501250114 | Huỳnh Thị Kim Trang | |
| 27 | 501250110 | Phan Thị Ánh Tuyền | Trưởng nhóm 3 |
| 28 | 501250468 | Lâm Chí Vĩ | |
