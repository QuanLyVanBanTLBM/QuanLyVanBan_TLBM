# TÀI LIỆU ĐẶC TẢ MA TRẬN PHÂN QUYỀN HỆ THỐNG QUẢN LÝ VĂN BẢN
**(TÀI LIỆU PHỤC VỤ BÁO CÁO VÀ THAM VẤN Ý KIẾN GIẢNG VIÊN HƯỚNG DẪN)**

---

* **Hệ thống:** Phân hệ Quản Lý Văn Bản (Văn bản Đến, Văn bản Đi, Văn bản Mật)
* **Đối tượng sử dụng:** Quản trị viên (Admin), Cán bộ chuyên trách, Cán bộ nhân viên
* **Ngày cập nhật:** Tháng 10/2026

---

## MỤC LỤC
1. [I. ĐỊNH NGHĨA CÁC NHÓM NGƯỜI DÙNG (ACTORS & ROLES)](#i-định-nghĩa-các-nhóm-người-dùng)
2. [II. PHÂN LOẠI CÁC NHÓM VĂN BẢN TRONG HỆ THỐNG](#ii-phân-loại-các-nhóm-văn-bản)
3. [III. MA TRẬN PHÂN QUYỀN CHI TIẾT TỪNG PHÂN HỆ](#iii-ma-trận-phân-quyền-chi-tiết)
   - [1. Văn bản Đến & Đi thông thường (Phạm vi: Nội bộ)](#1-văn-bản-đến--đi-thông-thường-phạm-vi-nội-bộ)
   - [2. Văn bản Đến & Đi HẠN CHẾ (Phạm vi: Hạn chế)](#2-văn-bản-đến--đi-hạn-chế-phạm-vi-hạn-chế)
   - [3. Văn bản MẬT (Loại: Mật - Nội bộ công ty)](#3-văn-bản-mật-loại-mật---nội-bộ-công-ty)
4. [IV. BẢNG SO SÁNH QUYỀN ĐẶC BIỆT (XÓA & SỬA)](#iv-bảng-so-sánh-quyền-đặc-biệt)
5. [V. CƠ CHẾ BẢO MẬT VÀ KIỂM TOÁN (AUDIT TRAIL)](#v-cơ-chế-bảo-mật-và-kiểm-toán)
6. [VI. DANH SÁCH CÂU HỎI ĐỀ XUẤT THAM VẤN THẦY HƯỚNG DẪN](#vi-danh-sách-câu-hỏi-đề-xuất-tham-vấn-thầy)

---

## I. ĐỊNH NGHĨA CÁC NHÓM NGƯỜI DÙNG

1. **Quản trị viên (Admin)**:
   - Người nắm quyền quản trị tối cao của hệ thống (`role = 'admin'` hoặc `is_superuser = True`).
   - Có toàn quyền kiểm soát, cấu hình, xử lý mọi văn bản trong tổ chức.

2. **Cán bộ được chỉ định (Assigned Officer)**:
   - Bao gồm: **Người tạo văn bản** (`nguoi_tao`) hoặc **Người nhận được phân công xử lý đích danh / Đơn vị nhận** (`nguoi_nhan`, `donvinhan`).
   - Trực tiếp chịu trách nhiệm thực thi và quản lý vòng đời của văn bản đó.

3. **Cán bộ không được chỉ định (General Officer)**:
   - Các cán bộ, nhân viên khác trong cơ quan/công ty.
   - Không tạo, không được giao nhiệm vụ hay nằm trong luồng xử lý của văn bản cụ thể.

---

## II. PHÂN LOẠI CÁC NHÓM VĂN BẢN

1. **Văn bản Đến & Văn bản Đi thông thường (`pham_vi = 'NOI_BO'`)**: Lưu hành công khai trong toàn bộ nội bộ cơ quan/công ty.
2. **Văn bản Đến & Văn bản Đi HẠN CHẾ (`pham_vi = 'HAN_CHE'`)**: Có nội dung nhạy cảm, chỉ lưu hành trong phạm vi nhóm người hoặc đơn vị được chỉ định.
3. **Văn bản MẬT (`loai = 'MAT'`)**: Văn bản bí mật nội bộ của công ty (kế hoạch chiến lược, tài chính đặc biệt, nhân sự cấp cao,...).

---

## III. MA TRẬN PHÂN QUYỀN CHI TIẾT TỪNG PHÂN HỆ

### 1. Văn bản Đến & Đi thông thường (Phạm vi: Nội bộ - `NOI_BO`)

#### A. Khi văn bản CÒN HIỆU LỰC (`CON_HIEU_LUC`, `CON_HIEU_LUC_1_PHAN`, `HET_VA_THAY_THE`)

| STT | Tác vụ | Cán bộ không chỉ định | Cán bộ chỉ định *(Người tạo)* | Quản trị viên *(Admin)* | Ghi chú kỹ thuật |
| :---: | :--- | :---: | :---: | :---: | :--- |
| 1 | **Xem danh sách & Tìm kiếm** | ✅ Cho phép | ✅ Cho phép | ✅ Cho phép | Hiển thị trên bảng danh sách chung |
| 2 | **Xem chi tiết văn bản** | ✅ Cho phép | ✅ Cho phép | ✅ Cho phép | Xem đầy đủ trích yếu, số hiệu, thông tin |
| 3 | **Lịch sử xem (Audit Log)** | ✅ Cho phép | ✅ Cho phép | ✅ Cho phép | Xem nhật ký những ai đã mở xem |
| 4 | **Xem & Tải tệp đính kèm** | ✅ Cho phép | ✅ Cho phép | ✅ Cho phép | Mở và tải file Word, PDF, Excel |
| 5 | **Thêm mới văn bản** | ✅ Cho phép | ✅ Cho phép | ✅ Cho phép | Khởi tạo văn bản vào hệ thống |
| 6 | **Chỉnh sửa văn bản** | ❌ **Khóa** | ✅ **Cho phép** | ✅ **Cho phép** | Chỉ người tạo hoặc Admin mới sửa được |
| 7 | **Xóa văn bản** | ❌ **Khóa** | ✅ **Cho phép** | ✅ **Cho phép** | Người tạo xóa được văn bản của mình |
| 8 | **Import / Export Excel** | ✅ Cho phép | ✅ Cho phép | ✅ Cho phép | Xuất báo cáo, nhập dữ liệu từ file Excel |

#### B. Khi văn bản HẾT HIỆU LỰC (`HET_HIEU_LUC`)

| STT | Tác vụ | Cán bộ không chỉ định | Cán bộ chỉ định *(Người tạo)* | Quản trị viên *(Admin)* | Ghi chú kỹ thuật |
| :---: | :--- | :---: | :---: | :---: | :--- |
| 1 | **Xem danh sách & Tìm kiếm** | ❌ **Ẩn 100%** | ✅ Cho phép | ✅ Cho phép | QuerySet lọc bỏ khỏi tài khoản thường |
| 2 | **Xem chi tiết văn bản** | ❌ **Chặn (404/403)** | ✅ Cho phép | ✅ Cho phép | Cán bộ chỉ định xem để tra cứu quá khứ |
| 3 | **Lịch sử xem** | ❌ **Chặn** | ✅ Cho phép | ✅ Cho phép | Khóa truy cập |
| 4 | **Xem & Tải tệp đính kèm** | ❌ **Chặn** | ✅ Cho phép | ✅ Cho phép | Khóa truy cập |
| 5 | **Chỉnh sửa văn bản** | ❌ **Khóa** | ❌ **Khóa** | 👑 **Duy nhất Admin** | Bảo toàn tính toàn vẹn hồ sơ cũ |
| 6 | **Xóa văn bản** | ❌ **Khóa** | ❌ **Khóa** | 👑 **Duy nhất Admin** | Thu hồi quyền xóa của người tạo |

---

### 2. Văn bản Đến & Đi HẠN CHẾ (Phạm vi: Hạn chế - `HAN_CHE`)

| STT | Tác vụ | Cán bộ không chỉ định *(0 quyền)* | Cán bộ được chỉ định xem *(Chỉ xem)* | Quản trị viên *(Admin)* | Ghi chú kỹ thuật |
| :---: | :--- | :---: | :---: | :---: | :--- |
| 1 | **Xem danh sách văn bản** | ❌ **Ẩn 100%** | ✅ Cho phép | ✅ **Cho phép** | Không hiển thị bất kỳ dòng nào |
| 2 | **Xem chi tiết văn bản** | ❌ **Chặn 404** | ✅ Cho phép | ✅ **Cho phép** | Trả về `404 Not Found` chống dò quét |
| 3 | **Lịch sử xem (Audit Log)** | ❌ **Chặn** | ✅ Cho phép | ✅ **Cho phép** | Tự động ghi nhật ký mỗi lần mở xem |
| 4 | **Xem & Tải tệp đính kèm** | ❌ **Chặn** | ✅ Cho phép | ✅ **Cho phép** | Ghi log IP và tài khoản khi tải file |
| 5 | **Chỉnh sửa nội dung văn bản** | ❌ **Khóa** | ❌ **Khóa (Chỉ có quyền xem)** | 👑 **Duy nhất Admin** | Người được chỉ định xem chỉ có quyền xem |
| 6 | **Chuyển đổi Phạm vi lưu hành** *(Nội bộ ⇄ Hạn chế)* | ❌ **Khóa** | ❌ **Khóa** | 👑 **Chỉ riêng Admin** | Admin được quyền đổi phạm vi sau khi thêm |
| 7 | **Xóa văn bản hạn chế** | ❌ **Khóa** | ❌ **Khóa (Cấm xóa)** | 👑 **Toàn quyền xóa** | Admin có đầy đủ mọi quyền |
| 8 | **Ghi nhận truy cập vi phạm** | ⚠️ Ghi log `BI_TU_CHOI` | — | — | Ghi lại IP, tài khoản cố tình truy cập |

---

### 3. Văn bản MẬT (Loại: Mật - `MAT` - Nội bộ công ty)

| STT | Tác vụ | Cán bộ không chỉ định | Cán bộ chỉ định *(Được phân công)* | Quản trị viên *(Admin)* | Ghi chú kỹ thuật |
| :---: | :--- | :---: | :---: | :---: | :--- |
| 1 | **Xem danh sách (Còn hạn & 1 phần)** | ❌ **Ẩn 100%** | ✅ Cho phép | ✅ Cho phép | Read-Only đối với cán bộ chỉ định |
| 2 | **Xem danh sách (Hết hạn)** | ❌ **Ẩn 100%** | ❌ **Khóa** | 👑 **Duy nhất Admin** | Admin quản lý kho lưu trữ mật |
| 3 | **Xem chi tiết văn bản mật** | ❌ **Chặn 404** | ✅ Cho phép *(Khi còn hạn)* | ✅ Cho phép | Bảo mật thông tin chiến lược |
| 4 | **Lịch sử xem** | ❌ **Chặn** | ✅ Cho phép *(Khi còn hạn)* | ✅ Cho phép | Giám sát chặt chẽ luồng đọc tài liệu |
| 5 | **Thêm mới văn bản mật** | ❌ **Khóa** | ❌ **Khóa** | 👑 **Duy nhất Admin** | Chỉ Admin mới được phát hành VB Mật |
| 6 | **Chỉnh sửa văn bản mật** | ❌ **Khóa** | ❌ **Khóa (Read-Only)** | 👑 **Duy nhất Admin** | Cán bộ chỉ định tuyệt đối không được sửa |
| 7 | **Xóa văn bản mật** | ❌ **Khóa** | ❌ **Khóa** | 👑 **Duy nhất Admin** | Admin công ty có quyền hủy/xóa |

---

## IV. BẢNG SO SÁNH QUYỀN ĐẶC BIỆT (XÓA & SỬA)

### 1. So sánh quyền XÓA (Delete Permission)
| Nhóm văn bản | Cán bộ thường | Cán bộ chỉ định (Người tạo) | Quản trị viên (Admin) | Lý do thiết kế nghiệp vụ |
| :--- | :---: | :---: | :---: | :--- |
| **VB Đến/Đi Thường** | ❌ Không | ✅ **Xóa được khi còn hạn** *(Hết hạn bị khóa)* | 👑 **Toàn quyền xóa** | Người tạo có quyền thu hồi văn bản thường do mình tạo |
| **VB Đến/Đi HẠN CHẾ** | ❌ Không (0 quyền) | ❌ **Cấm xóa** | 👑 **Toàn quyền xóa** | Tránh người tạo tự ý xóa chứng từ nhạy cảm; Admin quản trị tối cao |
| **Văn bản MẬT** | ❌ Không (0 quyền) | ❌ **Cấm xóa** *(Chỉ xem)* | 👑 **Toàn quyền xóa** | Chỉ Admin có thẩm quyền tiêu hủy/xóa văn bản mật |

### 2. So sánh quyền SỬA (Edit Permission)
| Nhóm văn bản | Cán bộ thường | Cán bộ chỉ định (Người tạo) | Quản trị viên (Admin) | Lý do thiết kế nghiệp vụ |
| :--- | :---: | :---: | :---: | :--- |
| **VB Thường còn hạn** | ❌ Không | ✅ **Được sửa** | 👑 **Được sửa** | Cho phép hoàn thiện nội dung |
| **VB Thường hết hạn** | ❌ Không | ❌ **Khóa** | 👑 **Duy nhất Admin** | Hồ sơ hết hạn chỉ Admin được chỉnh sửa điều chỉnh |
| **VB Hạn chế còn hạn** | ❌ Không (0 quyền) | ✅ **Người tạo sửa** *(Người nhận chỉ xem)* | 👑 **Được sửa** | Bảo đảm đúng thẩm quyền phát hành |
| **VB Mật** | ❌ Không (0 quyền) | ❌ **Khóa (Read-Only)** | 👑 **Duy nhất Admin** | Cán bộ được phân công chỉ nắm thông tin, không được sửa |

---

## V. CƠ CHẾ BẢO MẬT VÀ KIỂM TOÁN (AUDIT TRAIL)

1. **Bảo mật đa tầng**:
   - **Tầng Database/QuerySet:** Lọc ngay từ câu lệnh truy vấn SQL/ORM, không bao giờ gửi metadata của văn bản cấm ra frontend.
   - **Tầng API Controller:** Hàm `can_edit_document` và `can_delete_document` chặn ở cấp độ HTTP request (trả về 403 Forbidden).
   - **Tầng Giao diện (UI):** Tự động ẩn menu 3 chấm, ẩn nút Sửa, nút Xóa, ẩn tab bộ lọc tương ứng.
2. **Nhật ký kiểm toán (`DocumentAccessLog` & `DocumentViewLog`)**:
   - Mọi lượt xem văn bản đều ghi lại: Người xem, thời gian, IP.
   - Khi có hành vi cố tình đoán link/ID vào văn bản Hạn chế hoặc Mật: hệ thống tự động ghi nhận bản ghi với trạng thái `BI_TU_CHOI` để phục vụ thanh tra.

---

## VI. DANH SÁCH CÂU HỎI ĐỀ XUẤT THAM VẤN THẦY HƯỚNG DẪN (VÀO THỨ 5)

Dưới đây là 3 câu hỏi trọng tâm đã được chuẩn bị sẵn phương án để bạn trao đổi với Thầy:

1. **Câu hỏi 1 (Về Văn bản Hạn chế):**
   * *Nội dung hỏi Thầy:* "Thưa Thầy, đối với Văn bản Đến/Đi Hạn chế, hiện tại hệ thống phân quyền: Cán bộ không được chỉ định thì hoàn toàn không có quyền gì (ẩn 100%); Cán bộ được chỉ định thì chỉ người tạo mới được sửa khi còn hạn và cấm xóa; còn Admin thì có đầy đủ 4 quyền (Xem, Lịch sử, Sửa, Xóa). Thiết kế như vậy đã tối ưu theo chuẩn đồ án chưa ạ?"
   * *Phương án trả lời dự kiến:* Rất chuẩn theo mô hình bảo mật tổ chức (Admin là người quản trị tối cao, cán bộ hạn chế không tự ý tiêu hủy tài liệu).

2. **Câu hỏi 2 (Về Văn bản Mật):**
   * *Nội dung hỏi Thầy:* "Đối với Văn bản Mật nội bộ của công ty: Cán bộ được chỉ định chỉ được Xem (Read-Only) khi văn bản còn hiệu lực hoặc còn hiệu lực 1 phần; khi hết hiệu lực thì khóa lại và chỉ duy nhất Admin mới được xem và quản lý lưu trữ. Thầy thấy quy trình này có cần bổ sung thêm vai trò nào không ạ?"

3. **Câu hỏi 3 (Về Quyền Xóa của Người tạo trên Văn bản Thường):**
   * *Nội dung hỏi Thầy:* "Văn bản thường do cán bộ tạo ra: Khi còn hạn thì cán bộ tạo được sửa và xóa; nhưng khi đã hết hạn thì khóa quyền xóa/sửa của cán bộ đó và chỉ duy nhất Admin mới được xóa/sửa. Thiết kế vòng đời như vậy đã chặt chẽ chưa ạ?"
