# KỊCH BẢN BÁO CÁO MIỆNG GIAI ĐOẠN 1: PHÂN HỆ VĂN BẢN ĐẾN (INBOUND DOCUMENTS)
## ĐỒ ÁN TỐT NGHIỆP: HỆ THỐNG QUẢN LÝ VĂN BẢN & TÀI LIỆU (TLBM SYSTEM) — MODULE 2: VĂN BẢN

> **Giảng viên hướng dẫn**: NCS.ThS. Trần Phương Duy  
> **Đơn vị**: Khoa Công Nghệ Thông Tin — Trường Cao Đẳng Công Nghệ Thông Tin TP.HCM (ITC)  
> **Người báo cáo chính**: **Lê Trí Kiệt** (Trưởng nhóm 2)  
> **Các thành viên nhóm**: Lê Trí Kiệt (25%), Nguyễn Anh Đô (25%), Nguyễn Tấn Lộc Khiêm (25%), Trần Nhật Tân (25%)  
> **Căn cứ tài liệu**: Mục II — Bảng phân công chi tiết Giai đoạn 1 (`BangPhanCong_Nhom2_ModuleVanBan.docx`) & Nghiệp vụ `itc.pdf`

---

## 🧭 CẤU TRÚC THỜI GIAN TRÌNH BÀY (KHUYẾN NGHỊ: 5 - 7 PHÚT)

| Phần | Nội dung chính | Thời lượng dự kiến |
| :---: | :--- | :---: |
| **Phần 1** | Lời chào, giới thiệu đề tài & nguyên tắc phân công 4 thành viên | ~ 45 giây |
| **Phần 2** | Báo cáo chi tiết công việc 4 thành viên theo Mục II file phân công | ~ 2.5 phút |
| **Phần 3** | Các điểm sáng kỹ thuật & tối ưu hóa nghiệp vụ nổi bật | ~ 1.5 phút |
| **Phần 4** | Lời dẫn chuyển tiếp sang Live Demo thực tế | ~ 30 giây |
| **Phần 5** | Dự trù câu hỏi vấn đáp (Q&A) của Thầy & cách trả lời | Phần mở rộng |

---

## 🎙️ TOÀN VĂN LỜI THOẠI BÁO CÁO MIỆNG (CHO TRƯỞNG NHÓM LÊ TRÍ KIỆT)

### PHẦN 1: LỜI CHÀO & TỔNG QUAN PHÂN CÔNG (45 giây)

> *"Em kính chào Thầy Duy cùng quý Thầy Cô trong Hội đồng đánh giá.*
>
> *Em tên là **Lê Trí Kiệt**, đại diện cho **Nhóm 2** phụ trách **Module 2: Quản lý Văn bản (Đến – Đi – Mật)** trong Đồ án Hệ thống Quản lý Văn bản và Tài liệu TLBM.*
>
> *Hôm nay, nhóm em xin phép được báo cáo tiến độ và nghiệm thu kết quả **Giai đoạn 1: Phân hệ Văn bản Đến (Inbound Documents)**.*
>
> *Thưa Thầy, Nhóm 2 gồm 4 thành viên. Ngay từ đầu, nhóm đã thống nhất phân chia khối lượng công việc theo **nguyên tắc kiến trúc phân tầng (Clean Architecture & Full-stack theo lớp)**. Trong Giai đoạn 1, nhóm tập trung hoàn thiện trọn vẹn toàn bộ CSDL và quy trình tiếp nhận cho **Phân hệ Văn bản Đến**, tạo nền móng vững chắc để đến Giai đoạn 2 và 3 chỉ việc tạo thêm bảng Văn bản Đi và Văn bản Mật theo đúng CSDL Thầy đã duyệt. Mỗi thành viên đảm nhận đúng **25%** khối lượng dự án. Cụ thể:*
> - *Em — **Lê Trí Kiệt**: Đảm nhiệm **Backend Core & Kiến trúc CSDL**.*
> - *Bạn **Nguyễn Anh Đô**: Đảm nhiệm **Backend Service & Logic Xử lý Dữ liệu**.*
> - *Bạn **Nguyễn Tấn Lộc Khiêm**: Đảm nhiệm **Frontend View & Trải nghiệm Hiển thị**.*
> - *Bạn **Trần Nhật Tân**: Đảm nhiệm **Frontend Input & Xử lý Nhập liệu**.*
>
> *Sau đây, em xin phép đi vào chi tiết công việc từng bạn đã hoàn thành trong Giai đoạn 1 theo đúng bảng phân công đã gửi Thầy."*

---

### PHẦN 2: BÁO CÁO CHI TIẾT CÔNG VIỆC 4 THÀNH VIÊN (2.5 phút)

#### 1. Lê Trí Kiệt (Trưởng nhóm — 25% — Backend Core & Bảo mật):
> *"Về phần em, em chịu trách nhiệm xây dựng nền móng cốt lõi cho phân hệ Backend:*
> 1. *Khởi tạo app `apps/documents`, cấu hình hệ thống lưu trữ `MEDIA_ROOT` bảo mật, tự động phân luồng lưu trữ file scan văn bản vào thư mục chuyên biệt `02_documents/den/%Y/%m/`.*
> 2. *Thiết kế CSDL quan hệ cho Phân hệ Văn bản Đến quản lý chặt chẽ: `so_thu_tu` (Số đến), `so_hieu`, `trich_yeu`, `noi_ban_hanh`, `hieu_luc`. Đặc biệt, trường **`ngay_den` được cấu hình kiểu `DateTimeField`**, tự động ghi nhận chính xác đến từng **giờ : phút : giây** theo đúng chỉ đạo của Thầy, sẵn sàng mở rộng thêm bảng cho Văn bản Đi và Mật ở các giai đoạn sau.*
> 3. *Xây dựng Model `DocumentAttachment` (quản lý file đính kèm đa định dạng) và `DocumentViewLog` (theo dõi nhật ký đọc văn bản).*
> 4. *Xây dựng hệ thống Base CRUD API RESTful đầy đủ, đăng ký trang quản trị Django Admin trực quan.*
> 5. *Thiết lập cơ chế phân quyền bảo mật linh hoạt: quyền Xóa thuộc về Admin; quyền Sửa mở rộng cho Admin, Người tạo và Cán bộ được phân quyền."*

#### 2. Nguyễn Anh Đô (Thành viên — 25% — Backend Service & Logic Dữ liệu):
> *"Tiếp theo, bạn Nguyễn Anh Đô phụ trách toàn bộ tầng nghiệp vụ chuyên sâu và xử lý dữ liệu:*
> 1. *Xây dựng thuật toán **tự sinh Số đến (`so_thu_tu`) tự tăng theo từng năm** (1, 2, 3...), xử lý an toàn đồng thời (concurrency-safe), tránh tuyệt đối tình trạng nhảy trùng số khi nhiều văn thư cùng tiếp nhận công văn.*
> 2. *Xây dựng bộ lọc tìm kiếm nâng cao đa tiêu chí `DocumentFilter`: tìm kiếm theo từ khóa trích yếu/số hiệu/nơi ban hành (`q`), lọc theo năm (`nam`), lọc khoảng ngày đến (`tu_ngay` - `den_ngay`), và lọc trạng thái hiệu lực.*
> 3. *Xây dựng API `GET /api/documents/{id}/viewers/` truy vấn danh sách cán bộ đã xem, hỗ trợ tìm kiếm theo tên và lọc theo phòng ban.*
> 4. *Phát triển dịch vụ Excel toàn diện: API tự động sinh file Excel mẫu trực tiếp từ cấu trúc Database, API Import hàng loạt văn bản từ Excel và API Export danh sách văn bản theo đúng kết quả của bộ lọc."*

#### 3. Nguyễn Tấn Lộc Khiêm (Thành viên — 25% — Frontend View & Hiển thị):
> *"Ở phía giao diện người dùng, bạn Nguyễn Tấn Lộc Khiêm phụ trách Bảng hiển thị và trải nghiệm tra cứu:*
> 1. *Xây dựng Bảng danh sách văn bản `DocumentTable` hiển thị đầy đủ các cột nghiệp vụ: Số ký hiệu, Ngày văn bản, Ngày đến (kèm giờ phút giây), Trích yếu, Nơi ban hành, Trạng thái hiệu lực và Cột thao tác.*
> 2. *Xử lý trải nghiệm trực quan: **tự động đổi màu dòng tối/mờ cho các văn bản Hết hiệu lực**, giúp văn thư phân biệt ngay lập tức.*
> 3. *Thiết kế **Menu thao tác 3 chấm `⋮`** tinh gọn, click vào mở menu hành động (Xem chi tiết, Chỉnh sửa, Xóa, Người đã đọc), tự động kiểm tra quyền để ẩn/hiện nút Sửa và Xóa theo từng vai trò.*
> 4. *Xây dựng thanh công cụ `FilterBar` đa năng với đầy đủ ô tìm kiếm từ khóa, chọn năm, khoảng ngày đến và hiệu lực.*
> 5. *Xây dựng Modal Xem chi tiết (`DocumentDetailModal`) và Modal Lịch sử người đã đọc (`DocumentViewersModal`) có tìm kiếm tên và chọn phòng ban."*

#### 4. Trần Nhật Tân (Thành viên — 25% — Frontend Input & Nhập liệu):
> *"Cuối cùng, bạn Trần Nhật Tân phụ trách toàn bộ tầng tiếp nhận và nhập liệu văn bản:*
> 1. *Xây dựng Popup Form thêm mới và chỉnh sửa `DocumentFormModal`. Form tự động hiển thị Số đến tăng dần, mặc định Ngày đến là thời điểm hiện tại. Đặc biệt, **khóa trường Số đến ở chế độ Read-Only khi sửa** đúng theo quy định trong tài liệu `itc.pdf`.*
> 2. *Tích hợp cơ chế thông minh: **tự động gợi ý chuỗi Số ký hiệu** dựa trên Năm và Nơi ban hành mà người dùng không cần phải gõ lại từ đầu.*
> 3. *Xử lý kỹ thuật **Cascading Dropdown**: khi chọn Đơn vị nhận, hệ thống tự động lọc và tải danh sách Cán bộ nhân viên tương ứng thuộc phòng ban đó.*
> 4. *Xây dựng khu vực **kéo thả Upload file đính kèm**, kiểm soát chặt chẽ dung lượng và giới hạn định dạng an toàn (PDF, DOC/DOCX, JPG/PNG).*
> 5. *Xây dựng giao diện Modal Nhập liệu Excel (kèm nút tải file mẫu chuẩn) và Nút Xuất Excel nhanh chóng."*

---

### PHẦN 3: CÁC ĐIỂM SÁNG KỸ THUẬT & TỐI ƯU HÓA NỔI BẬT (1.5 phút)

> *"Thưa Thầy, trong quá trình thực hiện Giai đoạn 1, Nhóm 2 đã đặc biệt chú trọng giải quyết các bài toán thực tế và tuân thủ chặt chẽ tài liệu yêu cầu:*
>
> 1. ***Tuân thủ tuyệt đối quy định Ngày Giờ**: Trường Ngày đến được nhóm cấu hình `DateTimeField` ở Backend và format `HH:mm:ss dd/MM/yyyy` ở Frontend, đáp ứng 100% yêu cầu khắt khe của Thầy về thời gian tiếp nhận công văn.*
> 2. ***Bảo vệ Số đến bất biến theo chuẩn `itc.pdf`**: Số đến là định danh vào sổ công văn. Nhóm đã khóa trường này ở cả 2 đầu: Frontend đặt `readOnly` và Backend Serializer đặt `read_only_fields`, ngăn ngừa hoàn toàn nguy cơ sửa đổi sai lệch hồ sơ.*
> 3. ***Đồng bộ trạng thái 2 chiều cho Văn bản thay thế**: Khi văn bản mới thay thế văn bản cũ, hệ thống tự động cập nhật văn bản cũ sang trạng thái 'Đã bị thay thế'. Nếu văn bản mới bị xóa, hệ thống sẽ tự động khôi phục văn bản cũ về trạng thái 'Còn hiệu lực', không để dữ liệu mồ côi.*
> 4. ***Chất lượng kiểm thử (Quality Gate) đạt 100%**:*
>    - *Bộ Test Backend Django: **36/36 tests PASS 100%**.*
>    - *Bộ Test Frontend Vitest: **67/67 tests PASS 100%**.*
>    - *Quy trình Build dự án hoàn toàn sạch lỗi, sẵn sàng tích hợp."*

---

### PHẦN 4: LỜI CHUYỂN TIẾP SANG LIVE DEMO (30 giây)

> *"Thưa Thầy, toàn bộ các chức năng của Giai đoạn 1 hiện đã được nhóm triển khai hoàn tất và đang chạy thực tế trên máy.*
>
> *Sau đây, em xin phép được mời Thầy cùng xem phần **Live Demo trực tiếp trên hệ thống** để kiểm chứng luồng hoạt động từ tiếp nhận, gợi ý số ký hiệu, upload file, tra cứu lọc đa tiêu chí, theo dõi người đọc đến xuất nhập Excel.*
>
> *(Chuyển sang màn hình trình duyệt `http://localhost:5173/documents/incoming`)*
>
> *Kính mời Thầy cùng theo dõi ạ!"*

---

## 🖥️ KỊCH BẢN THAO TÁC LIVE DEMO TRÊN MÀN HÌNH (DÀNH CHO BẠN TRÌNH CHIẾU)

Để buổi demo diễn ra mạch lạc, người bấm máy thao tác tuần tự theo 7 bước sau:

```
[Bước 1] Đăng nhập tài khoản Admin (admin / Admin@123)
  └── Mở trang "Văn bản đến" (/documents/incoming).
  └── Thuyết minh: Giao diện hiển thị danh sách văn bản, hỗ trợ cả 2 Theme (Sáng/Tối).
  └── Chỉ vào dòng văn bản có nền mờ: Giải thích đây là văn bản "Hết hiệu lực".

[Bước 2] Thao tác Thêm mới Văn bản Đến
  └── Nhấn nút "+ Thêm văn bản đến".
  └── Thuyết minh: 
      • "Số đến" tự động tăng (ví dụ: số 6).
      • "Ngày đến" tự lấy thời điểm hiện tại kèm giờ:phút:giây.
      • Chọn Nơi ban hành: "Bộ GD&ĐT", chọn Năm: "2026" ➔ ô Số ký hiệu tự động sinh chuỗi gợi ý.
      • Thử chọn Đơn vị nhận (Phòng Đào tạo) ➔ Ô Cán bộ nhận tự lọc đúng người của phòng ban đó.
      • Kéo thả 1 file PDF đính kèm.
  └── Bấm "Lưu" ➔ Văn bản mới xuất hiện ngay trên đầu bảng.

[Bước 3] Thao tác Tra cứu & Bộ lọc (FilterBar)
  └── Nhập từ khóa trích yếu hoặc nơi ban hành vào ô Tìm kiếm ➔ Bảng lọc tức thì.
  └── Chọn năm, chọn khoảng ngày đến ➔ Dữ liệu lọc chính xác theo ngày giờ tiếp nhận.

[Bước 4] Xem chi tiết & Lịch sử người đã đọc
  └── Bấm Menu 3 chấm ⋮ ➔ Chọn "Xem chi tiết".
      • Hiển thị đầy đủ thông tin, tải thử file đính kèm.
  └── Bấm Menu 3 chấm ⋮ ➔ Chọn "Danh sách người đã xem".
      • Modal hiển thị danh sách cán bộ đã mở văn bản.
      • Thử gõ tên tìm kiếm hoặc lọc theo phòng ban.

[Bước 5] Minh chứng Bảo vệ Số đến & Phân quyền Sửa/Xóa
  └── Bấm Menu 3 chấm ⋮ ➔ Chọn "Chỉnh sửa".
      • Chỉ rõ cho Thầy thấy: Ô "Số đến" bị khóa xám (Read-Only), không cho sửa theo đúng itc.pdf.
  └── Thử đăng xuất, đăng nhập tài khoản Cán bộ (canbo / Canbo@123).
      • Bấm menu 3 chấm ⋮ ➔ Nút "Xóa" bị ẩn đi hoàn toàn (chỉ Admin mới có quyền xóa).

[Bước 6] Xuất & Nhập Excel
  └── Bấm "Xuất Excel" ➔ Tải về file Excel chứa đúng danh sách đang lọc.
  └── Bấm "Nhập Excel" ➔ Bấm "Tải file mẫu" ➔ Mở file mẫu cho Thầy thấy backend tự sinh từ CSDL.
```

---

## ❓ BỘ CÂU HỎI VẤN ĐÁP (Q&A) DỰ KIẾN VỚI THẦY DUY & GỢI Ý TRẢ LỜI

### Câu 1: "Tại sao nhóm lại chia công việc theo chiều dọc (Full-stack layers) thay vì mỗi bạn làm trọn gói 1 loại văn bản (Bạn Đến, Bạn Đi, Bạn Mật)?"
> **Trả lời:**  
> *"Dạ thưa Thầy, theo đúng thiết kế CSDL đã được Thầy duyệt, hệ thống sẽ gồm 3 bảng riêng biệt cho Văn bản Đến, Văn bản Đi và Văn bản Mật. Tuy nhiên, về mặt kỹ thuật, cả 3 phân hệ này đều chia sẻ chung các lớp nghiệp vụ tương đồng (như Bảng danh sách, Menu thao tác 3 chấm, Modal xem chi tiết, Bộ lọc đa tiêu chí, Dịch vụ Excel và Thuật toán tự sinh số).*  
> *Nếu chia mỗi bạn ôm trọn 1 loại văn bản, mã nguồn sẽ bị phân mảnh, viết lặp code nhiều lần và các bạn làm giai đoạn sau sẽ phải chờ đợi. Vì vậy, nhóm quyết định đi theo chiều dọc: ở Giai đoạn 1, cả 4 bạn cùng tập trung làm thật kỹ và chuẩn hóa toàn bộ nền tảng cho **Văn bản Đến** (Kiệt làm Core CSDL & Base API, Đô làm Service & Excel, Khiêm làm Bảng hiển thị, Tân làm Form nhập liệu). Nhờ kiến trúc phân tầng này, khi bước sang Giai đoạn 2 (Văn bản Đi) và Giai đoạn 3 (Văn bản Mật), nhóm chỉ việc tạo thêm bảng theo đúng CSDL Thầy duyệt và kế thừa lại toàn bộ các tầng xử lý đã xây dựng, vừa hoàn thành nhanh chóng, vừa bảo đảm tính đồng bộ cao nhất cho toàn hệ thống ạ."*

---

### Câu 2: "Trường 'Ngày đến' có gì đặc biệt mà nhóm phải lưu ý?"
> **Trả lời:**  
> *"Dạ thưa Thầy, theo đúng lưu ý của Thầy trong các buổi hướng dẫn trước, thời điểm văn bản đến trường cần xác định chính xác để tính thời hạn xử lý công văn. Vì vậy, nhóm đã dùng kiểu dữ liệu `DateTimeField` thay vì `DateField`. Hệ thống lưu trữ và hiển thị đầy đủ định dạng `HH:mm:ss dd/MM/yyyy`, giúp văn thư và ban giám hiệu biết chính xác công văn đến vào giờ phút nào trong ngày ạ."*

---

### Câu 3: "Nếu hai cán bộ văn thư cùng lúc tiếp nhận 2 văn bản khác nhau, số đến có bị trùng lặp không?"
> **Trả lời:**  
> *"Dạ thưa Thầy, hoàn toàn không bị trùng lặp ạ. Ở tầng Backend Service do bạn Nguyễn Anh Đô viết, hàm tự sinh số đến được bọc trong một Database Transaction sử dụng cơ chế khóa hàng hoặc truy vấn `Max('so_thu_tu')` trong phạm vi từng năm. Ngay cả khi có nhiều yêu cầu gửi lên đồng thời, hệ thống vẫn đảm bảo cấp phát tuần tự 1, 2, 3... an toàn concurrency ạ."*

---

### Câu 4: "Người dùng có thể sửa Số đến khi cập nhật văn bản không?"
> **Trả lời:**  
> *"Dạ thưa Thầy, tuyệt đối không được phép sửa ạ. Theo quy định của công tác văn thư lưu trữ và yêu cầu trong tài liệu `itc.pdf`, Số đến là số thứ tự vào sổ công văn bất biến. Nhóm đã bảo vệ 2 lớp: ở Frontend, bạn Tân đã đặt thuộc tính `readOnly` và style khóa xám trên giao diện; ở Backend, bạn Kiệt đã cấu hình `read_only_fields = ['so_thu_tu']` trong Serializer của Django REST Framework. Do đó, người dùng cố tình can thiệp qua API cũng không thể thay đổi được Số đến ạ."*

---

### Câu 5: "Quyền xóa và sửa văn bản được phân cấp ra sao?"
> **Trả lời:**  
> *"Dạ thưa Thầy, nhóm áp dụng chính sách phân quyền bảo vệ an toàn dữ liệu:*
> - *Quyền Xóa: Chỉ duy nhất tài khoản Quản trị viên (Admin) mới có quyền xóa văn bản để tránh thất thoát hồ sơ.*
> - *Quyền Sửa: Dành cho Admin, Người trực tiếp tạo ra văn bản đó, hoặc các Cán bộ được phân quyền nghiệp vụ.*
> *Hệ thống tự động kiểm tra token JWT của người đăng nhập để ẩn/hiện các nút bấm trên giao diện và chặn mã lỗi 403 Forbidden ở Backend nếu không đủ thẩm quyền ạ."*

---

## 📌 BẢNG TỔNG KẾT FILE MINH CHỨNG (DẪN CHỨNG TRƯỚC HỘI ĐỒNG)

| Hạng mục | Đường dẫn mã nguồn kiểm chứng | Người phụ trách |
| :--- | :--- | :--- |
| **Model & Base API** | `backend/apps/documents/models.py`<br>`backend/apps/documents/views.py` | Lê Trí Kiệt |
| **Service Tự sinh số & Excel** | `backend/apps/documents/services.py`<br>`backend/apps/documents/filters.py` | Nguyễn Anh Đô |
| **Bảng danh sách & Lọc** | `frontend/src/components/documents/DocumentTable.tsx`<br>`frontend/src/components/documents/FilterBar.tsx` | Nguyễn Tấn Lộc Khiêm |
| **Form Nhập liệu & File** | `frontend/src/components/documents/DocumentFormModal.tsx`<br>`frontend/src/components/documents/DocumentDetailModal.tsx` | Trần Nhật Tân |
| **Kết quả Kiểm thử** | Backend: 36/36 tests PASS<br>Frontend: 67/67 tests PASS | Cả nhóm |
