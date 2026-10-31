# Luồng kiểm thử và ca biên (Module 05 - Trình ký)

Căn cứ: Issue #80 (kiến trúc MVP), Issue #248 (danh mục kiểm thử, xem [`qa-test-cases-80.md`](qa-test-cases-80.md)),
Issue #261 (rà soát giao diện), Issue #265 (phân định trễ hạn cấp ký).

Tài liệu mô tả phạm vi kiểm thử theo nghiệp vụ. Số liệu và kết quả chạy lấy từ CI của từng PR, không ghi cố định ở đây.
Mã kiểm thử nằm trong bộ test của module ở backend và frontend.

---

## 1. Luồng nghiệp vụ chính

### Luồng 1: Ký duyệt hai cấp

- **Mục tiêu**: kiểm tra chu trình từ lập hồ sơ đến hoàn tất duyệt nội bộ.
- **Diễn biến**:
  1. Người tạo chọn văn bản đi (hoặc tải PDF dự thảo), chọn quy trình hai cấp, đặt vị trí ký rồi gửi trình; hệ thống
     khóa tệp và mã băm.
  2. Người ký cấp 1 nhận thông báo, mở khóa ký bằng PIN và ký.
  3. Khi mọi người ký của cấp 1 đã ký, cấp 1 hoàn thành và cấp 2 mở, hạn xử lý của cấp 2 được tính.
  4. Người ký cấp 2 ký; hồ sơ hoàn tất.
  5. Hệ thống tạo tệp hoàn tất có dấu "duyệt nội bộ, chưa phát hành", ảnh chữ ký đúng vị trí và trang phụ lục bằng chứng.
- **Kiểm thử**: nhóm test trình ký, hành động ký và hoàn tất.

### Luồng 2: Trả lại để sửa và trình lại

- **Mục tiêu**: kiểm tra trả hồ sơ khi có sai sót, trao đổi và nộp bản sửa.
- **Diễn biến**:
  1. Người ký chọn "Trả lại để sửa", nhập tiêu đề và lý do bắt buộc.
  2. Lượt trình hiện tại chuyển sang chờ sửa; mọi thao tác ký trên lượt này bị khóa.
  3. Người tạo và người yêu cầu sửa trao đổi qua lại; mỗi tin nhắn có thông báo cho các bên.
  4. Người tạo tải bản sửa lên; hệ thống tạo lượt trình mới với mã băm mới.
  5. Các cấp ký lại từ đầu trên tệp mới; chữ ký và lịch sử lượt trước được giữ làm bằng chứng.
- **Kiểm thử**: nhóm test yêu cầu sửa và giao diện trao đổi.

### Luồng 3: Từ chối ban hành và trình lại

- **Mục tiêu**: kiểm tra trạng thái kết thúc khi người ký không đồng ý ban hành.
- **Diễn biến**:
  1. Người ký chọn "Không đồng ý ban hành" và nhập lý do bắt buộc.
  2. Hồ sơ và lượt trình kết thúc ở trạng thái từ chối; người ký chưa ký không còn việc cần ký.
  3. Người tạo trình lại: hệ thống tạo hồ sơ nháp mới liên kết về hồ sơ gốc.
- **Kiểm thử**: nhóm test hành động ký và dữ liệu mẫu.

### Luồng 4: Quản lý khóa ký và mã PIN

- **Mục tiêu**: private key chỉ nằm ở thiết bị người dùng; máy chủ không giữ khóa bí mật hay mã PIN.
- **Diễn biến**:
  1. Người dùng tạo khóa với PIN 8 chữ số theo chính sách (chặn dãy số liên tiếp, ngày sinh, lặp số).
  2. Trình duyệt sinh cặp khóa Ed25519, mã hóa private key bằng khóa dẫn xuất từ PIN và xuất tệp khóa cho người dùng.
  3. Máy chủ chỉ nhận khóa công khai và chữ ký chứng minh sở hữu.
  4. Đổi PIN xoay vòng mảnh bí mật phía máy chủ và vô hiệu bản bọc khóa cũ.
  5. Nhập sai PIN nhiều lần bị khóa tạm, vượt ngưỡng cao hơn bị khóa vĩnh viễn khóa ký.
- **Kiểm thử**: nhóm test PIN và khóa ở backend, test khóa ký ở frontend.

---

## 2. Ca biên và cơ chế phòng vệ

| Mã | Tình huống | Cơ chế xử lý | Kết quả |
|---|---|---|---|
| EC-01 | Tệp PDF khác bản đã niêm phong khi gửi trình | Từ chối ký khi mã băm không khớp; giao diện khóa nút ký và hiện cảnh báo | Đạt |
| EC-02 | Hai hồ sơ cùng được gửi cho một văn bản đi | Khóa giao dịch theo văn bản; yêu cầu thứ hai bị từ chối | Đạt |
| EC-03 | Hai người cùng cấp ký đồng thời, hoặc ký đồng thời với hủy hồ sơ | Khóa dòng trong cùng giao dịch; xử lý tuần tự, không sinh chữ ký thừa | Đạt |
| EC-04 | Cấp ký chậm quá giờ của cấp nhưng hạn chót toàn trình chưa tới | Tách trễ hạn cấp ký khỏi quá hạn toàn trình; giao diện hiện nhãn riêng | Đạt |
| EC-05 | Gửi lặp do mạng chập chờn | Khóa chống trùng theo thao tác; yêu cầu thứ hai trả kết quả của lần đầu | Đạt |
| EC-06 | Trình ký văn bản đến hoặc văn bản hạn chế | Chặn ở tầng nghiệp vụ | Đạt |
| EC-07 | Sửa hoặc xóa bằng chứng đã chốt bằng SQL | Trigger CSDL chặn thao tác | Đạt |
