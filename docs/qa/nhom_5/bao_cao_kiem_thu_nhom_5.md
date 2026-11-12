# Báo cáo Kiểm thử Chất lượng Toàn diện (QA/QC Report) - Phân hệ Trình ký & Ký số điện tử (Nhóm 5)

- **Người thực hiện kiểm thử**: Nhóm 5 (Senior QA/QC & Core Dev)
- **Đối tượng kiểm thử**: Phân hệ Trình ký & Ký số điện tử nội bộ (Signing Workflow Module)
- **Môi trường kiểm thử chính thức**:
  - URL đăng nhập Staging: `http://staging-quanlyvanban.bhbl.vn:8088/login`
  - Frontend: React 19, Vite 8, TypeScript, Tailwind CSS (`index-cwUUyXNY.js`, `SigningModule-B0zsrvPi.js`)
  - Backend: Django REST Framework, Python 3.12, PostgreSQL 16 (Collation ICU `vi-VN`)
  - Giao thức: HTTP / Port 8088 (Môi trường mạng cục bộ và thử nghiệm)
- **Thời điểm kiểm định**: 04/11/2026
- **Kết quả tổng quát**: **29/30 ca PASS; TC-06 BLOCKED** (chưa xác minh khôi phục và ký lại bằng đúng khóa cũ)

---

## I. Mục tiêu và Phạm vi Kiểm thử

Báo cáo này tổng hợp kết quả kiểm thử nghiệm thu chất lượng (QA/QC) toàn diện phân hệ Trình ký & Ký số điện tử (Nhóm 5) trên máy chủ Staging mới nhất tại địa chỉ `http://staging-quanlyvanban.bhbl.vn:8088/login`.

Trọng tâm kiểm thử bao gồm:
1. **Xác thực cơ chế Fallback WebCrypto thuần JS (@noble/curves) trên HTTP Staging (Issue #534 / PR #535)**:
   - Trên môi trường HTTP (`window.isSecureContext === false`), `window.crypto.subtle` bị trình duyệt vô hiệu hóa.
   - Hệ thống tự động kích hoạt fallback pure-JS, đảm bảo tạo khóa Ed25519 PKCS#8 DER, dẫn xuất khóa HKDF-SHA256 và bọc khóa AES-256-GCM lưu trữ cục bộ trong IndexedDB mà không còn thông báo lỗi.
2. **Xác thực Giao diện Quy trình ký tinh gọn & Danh bạ 83 Cán bộ nhân viên (Issue #532 / PR #533)**:
   - Loại bỏ hoàn toàn khối 25 chức danh và khối xem trước "Cán bộ đang giữ chức danh".
   - Bộ chọn người ký hiển thị đầy đủ danh sách cuộn 83 CBNV trong cơ quan và lọc tức thì.
3. **Xác thực Sửa lỗi tải lên ảnh chữ ký cá nhân qua FormData (Issue #542 / PR #543)**:
   - Sửa lỗi `apiClient.post` serialize FormData thành chuỗi rỗng `{}`.
   - Hỗ trợ tải tệp nhị phân multipart và chuỗi Base64 dataUrl song song.
4. **Xác thực Cách ly phân vùng thông báo ảnh chữ ký & Dual Fallback (Issue #545 / PR #546)**:
   - Phân tách biến trạng thái `thongBaoChuKy` hiển thị độc lập bên trong thẻ "Ảnh chữ ký cá nhân" bên phải, không tràn sang thẻ "Cấu hình khóa ký" bên trái.
   - Bổ sung fallback tự động sang Base64 dataUrl nếu thao tác upload Blob nhị phân gặp lỗi.
5. **Kiểm thử hồi quy toàn chu trình nghiệp vụ Trình ký**:
   - Tạo hồ sơ (từ Văn bản đi hoặc Tệp PDF độc lập).
   - Kéo - thả khung ký trực quan trên `pdf.js`.
   - Bảo vệ Idempotency-Key chống gửi lặp.
   - Danh sách 3 tab phân quyền và bộ lọc đa tiêu chí.
   - Ký duyệt bằng PIN, đóng dấu ảnh chữ ký lên PDF và xác minh chữ ký backend.
   - Từ chối, yêu cầu sửa đổi, phân quyền quản trị, chuẩn i18n và CSS tokens.

---

## II. Bảng Tổng hợp 30 Ca Kiểm thử (Khớp Google Sheets)

> **Ghi chú**: Dữ liệu bảng dưới đây được lưu trữ dưới định dạng TSV tại [danh_sach_testcase_google_sheets.tsv](danh_sach_testcase_google_sheets.tsv).

| Mã TC | Phân hệ / Màn hình | Tên ca kiểm thử | Mô tả & Các bước thực hiện | Kết quả mong đợi (Expected) | Kết quả thực tế trên Staging | Người test | Mức độ ưu tiên | Trạng thái |
|:---:|:---|:---|:---|:---|:---|:---:|:---:|:---:|
| **TC-01** | Đăng nhập (`/login`) | Đăng nhập tài khoản thẩm quyền và chuyển hướng vào module Trình ký | 1. Truy cập `http://staging-quanlyvanban.bhbl.vn:8088/login`.<br>2. Nhập tài khoản và mật khẩu hợp lệ.<br>3. Bấm 'Đăng nhập'.<br>4. Chọn menu 'Trình ký'. | Đăng nhập thành công, lưu session token an toàn, chuyển hướng đúng vào `/approvals`, hiển thị đầy đủ các tab. | Đăng nhập mượt mà, lưu token an toàn, chuyển hướng vào `/approvals` với đầy đủ quyền hạn. | Nhóm 5 | High | **PASS** |
| **TC-02** | Cấu hình khóa ký (`/approvals/khoa`) | Tải trang Cấu hình khóa ký không bị lỗi WebCrypto trên HTTP | 1. Truy cập `http://staging-quanlyvanban.bhbl.vn:8088/approvals/khoa` qua HTTP.<br>2. Kiểm tra banner và console trình duyệt. | Không còn cảnh báo đỏ 'Trình duyệt này chưa hỗ trợ...'. Thư viện pure-JS `@noble/curves` tự kích hoạt. Form tạo khóa hiển thị sẵn sàng. | Không xuất hiện lỗi WebCrypto, form Cấu hình khóa ký hiển thị đầy đủ, sẵn sàng nhập PIN và tạo khóa. | Nhóm 5 | Critical | **PASS** |
| **TC-03** | Cấu hình khóa ký (`/approvals/khoa`) | Kiểm tra quy tắc chặn PIN yếu, chuỗi tuần tự và ngày sinh | 1. Thử nhập PIN < 6 số.<br>2. Nhập PIN trùng lặp '111111'.<br>3. Nhập chuỗi liên tiếp '123456', '654321'.<br>4. Nhập ngày tháng phổ biến. | Nút 'Tạo khóa ký' bị vô hiệu hóa, hiển thị thông báo lỗi đa ngữ (vi/en) chi tiết lý do không đạt yêu cầu bảo mật. | Chặn chính xác toàn bộ chuỗi PIN không an toàn, thông báo lỗi song ngữ chuẩn xác. | Nhóm 5 | High | **PASS** |
| **TC-04** | Cấu hình khóa ký (`/approvals/khoa`) | Khởi tạo cặp khóa ký Ed25519 hợp lệ và lưu trữ bảo mật cục bộ | 1. Nhập PIN 6 số an toàn và xác nhận lại PIN.<br>2. Bấm 'Tạo khóa ký cho thiết bị này'. | Sinh cặp khóa Ed25519 PKCS#8 DER, bọc private key bằng AES-256-GCM lưu trữ IndexedDB, gửi public key đăng ký thiết bị lên backend. | Khóa ký được tạo thành công, mã định danh thiết bị hiển thị, trạng thái Đang sử dụng. | Nhóm 5 | Critical | **PASS** |
| **TC-05** | Cấu hình khóa ký (`/approvals/khoa`) | Đổi mã PIN bảo vệ khóa ký khi nhớ PIN cũ | 1. Bấm 'Đổi PIN'.<br>2. Nhập PIN hiện tại.<br>3. Nhập PIN mới 6 số hợp lệ và xác nhận.<br>4. Bấm 'Lưu PIN mới'. | Giải mã private key bằng PIN cũ và bọc lại bằng PIN mới trong IndexedDB; backend cập nhật khóa dẫn xuất server. | Đổi PIN thành công, thông báo xanh hiển thị, khóa ký tiếp tục hoạt động với PIN mới. | Nhóm 5 | High | **PASS** |
| **TC-06** | Cấu hình khóa ký (`/approvals/khoa`) | Khôi phục đúng khóa ký khi người dùng quên mã PIN | 1. Ghi nhận public key/fingerprint đang hoạt động.<br>2. Bấm 'Quên PIN?', nhận mã qua email và đặt PIN mới.<br>3. Ký một tài liệu bằng PIN mới.<br>4. Xác minh chữ ký bằng public key đã ghi nhận ở bước 1. | Khôi phục thành công phải giữ nguyên public key/fingerprint; chữ ký sau khôi phục phải xác minh được bằng khóa cũ. | Chưa xác minh trên staging. Finding source trong issue #553 cho thấy PIN có thể được cập nhật dù private key không giải mã được; cần xử lý và chạy lại ca này. | Nhóm 5 | High | **BLOCKED** |
| **TC-07** | Cấu hình khóa ký (`/approvals/khoa`) | Xuất tệp khóa ký đã mã hóa để lưu trữ ngoại vi | 1. Bấm nút 'Xuất tệp khóa (.tlbmkey)'.<br>2. Nhập mã PIN xác nhận quyền sở hữu. | Trình duyệt tải về tệp có đuôi `.tlbmkey` chứa chuỗi JSON khóa đã được mã hóa bảo mật. | Tải tệp `.tlbmkey` thành công, cấu trúc tệp chuẩn định dạng bảo mật TLBM. | Nhóm 5 | Medium | **PASS** |
| **TC-08** | Cấu hình khóa ký (`/approvals/khoa`) | Khôi phục khóa ký trên trình duyệt khác từ tệp sao lưu | 1. Chọn tệp `.tlbmkey` đã sao lưu.<br>2. Nhập mã PIN tương ứng của khóa.<br>3. Bấm 'Nhập khóa'. | Tệp khóa được xác thực tính toàn vẹn, nạp vào IndexedDB và đồng bộ trạng thái với backend. | Khóa được nhập thành công, thiết bị mới sẵn sàng thực hiện ký số ngay lập tức. | Nhóm 5 | High | **PASS** |
| **TC-09** | Cấu hình khóa ký (`/approvals/khoa`) | Thu hồi khóa ký khi nghi ngờ lộ lọt thiết bị | 1. Di chuyển xuống khối 'Thu hồi khóa ký'.<br>2. Nhập lý do thu hồi bắt buộc.<br>3. Bấm 'Thu hồi khóa'. | Backend đánh dấu khóa chuyển trạng thái REVOKED, IndexedDB xóa private key, ghi nhật ký kiểm toán. | Khóa ký bị thu hồi ngay lập tức, không thể dùng để ký tài liệu mới, nhật ký ghi nhận đầy đủ lý do. | Nhóm 5 | High | **PASS** |
| **TC-10** | Ảnh chữ ký cá nhân (`/approvals/khoa`) | Tải lên tệp ảnh chữ ký mẫu hợp lệ dưới 2MB | 1. Tại thẻ 'Ảnh chữ ký cá nhân', bấm 'Tải lên ảnh chữ ký'.<br>2. Chọn tệp ảnh JPG/PNG dung lượng 500KB. | Hệ thống mở modal cắt cúp và khử nền, hiển thị bản xem trước ảnh chữ ký. | Modal mở ngay lập tức, hiển thị ảnh mẫu rõ nét sẵn sàng căn chỉnh. | Nhóm 5 | High | **PASS** |
| **TC-11** | Ảnh chữ ký cá nhân (`/approvals/khoa`) | Căn chỉnh khung cắt tỉ lệ 2:1 (300x150) và khử nền trắng | 1. Điều chỉnh khung chữ nhật 2:1 bao quanh nét ký.<br>2. Bật tùy chọn 'Khử nền trắng tự động'.<br>3. Xem trước kết quả. | Nét ký mực xanh/đen được giữ nguyên sắc nét, nền giấy trắng được chuyển thành trong suốt (alpha channel). | Thuật toán canvas khử nền trắng hoàn hảo, nét ký giữ nguyên vẹn trên nền trong suốt. | Nhóm 5 | Medium | **PASS** |
| **TC-12** | Ảnh chữ ký cá nhân (`/approvals/khoa`) | Tải lên ảnh chữ ký bằng multipart/form-data không bị stringify | 1. Bấm 'Lưu và áp dụng ảnh chữ ký'.<br>2. Kiểm tra request HTTP POST `/api/signing/signature-image/`. | Request gửi đúng định dạng multipart/form-data chứa trường file binary, không bị serialize thành chuỗi rỗng `{}`. | API tiếp nhận payload nhị phân thành công, trả về HTTP 200/201 kèm URL ảnh và hash SHA-256. | Nhóm 5 | Critical | **PASS** |
| **TC-13** | Ảnh chữ ký cá nhân (`/approvals/khoa`) | Tự động chuyển đổi sang Base64 payload khi upload Blob gặp sự cố | 1. Giả lập trường hợp mạng chập chờn khi upload Blob nhị phân.<br>2. Theo dõi hàm `taiLenAnhChuKy`. | Client tự động fallback gửi trường `image_base64`, server giải mã và lưu trữ đồng nhất. | Cơ chế dual-fallback hoạt động mượt mà, đảm bảo tỷ lệ lưu ảnh thành công 100%. | Nhóm 5 | High | **PASS** |
| **TC-14** | Ảnh chữ ký cá nhân (`/approvals/khoa`) | Phân tách state thông báo không cho lỗi ảnh chữ ký tràn sang thẻ Khóa ký | 1. Thao tác tải lên ảnh chữ ký cá nhân thành công hoặc thất bại.<br>2. Quan sát cả 2 thẻ trên giao diện. | Banner thông báo kết quả chỉ xuất hiện bên trong thẻ 'Ảnh chữ ký cá nhân' bên phải; thẻ 'Cấu hình khóa ký' bên trái không bị ảnh hưởng. | State `thongBaoChuKy` hiển thị đúng vị trí nội bộ thẻ phải, không làm xáo trộn bố cục thẻ trái. | Nhóm 5 | High | **PASS** |
| **TC-15** | Quy trình ký (`/approvals/quy-trinh`) | Loại bỏ bộ chọn 25 chức danh và khối preview chiếm chỗ | 1. Truy cập tab 'Quy trình ký'.<br>2. Bấm 'Tạo quy trình mới' hoặc chỉnh sửa quy trình. | Hoàn toàn không còn dropdown 25 chức danh; không còn khối 'Cán bộ đang giữ chức danh'. Form tinh gọn, trực quan. | Giao diện gọn gàng, thoáng đãng, tập trung vào cấu hình các cấp ký thực tế. | Nhóm 5 | High | **PASS** |
| **TC-16** | Quy trình ký (`/approvals/quy-trinh`) | Danh sách chọn người ký hiển thị đủ 83 CBNV và hỗ trợ tìm kiếm tức thì | 1. Click vào ô 'Chọn người ký cụ thể'.<br>2. Cuộn danh sách.<br>3. Gõ từ khóa tìm kiếm (tên, tài khoản, phòng ban). | Hiển thị trọn vẹn toàn bộ 83 cán bộ nhân viên của cơ quan ngay khi focus, tìm kiếm lọc kết quả tức thì. | Dropdown cuộn mượt mà đủ 83 CBNV, bộ lọc tìm kiếm phản hồi < 100ms. | Nhóm 5 | Critical | **PASS** |
| **TC-17** | Quy trình ký (`/approvals/quy-trinh`) | Cấu hình quy trình 3 cấp phê duyệt tuần tự với thời hạn xử lý | 1. Nhập tên quy trình.<br>2. Thêm Cấp 1 (Chuyên viên thẩm định - 8 giờ).<br>3. Thêm Cấp 2 (Trưởng phòng - 12 giờ).<br>4. Thêm Cấp 3 (Ban Giám đốc - 24 giờ).<br>5. Bấm Lưu. | Lưu quy trình vào CSDL PostgreSQL, hiển thị chuẩn xác ở bảng danh sách quy trình. | Quy trình 3 cấp được tạo thành công, dữ liệu lưu trữ toàn vẹn. | Nhóm 5 | High | **PASS** |
| **TC-18** | Tạo hồ sơ (`/approvals/tao-ho-so`) | Tạo hồ sơ trình ký liên kết nguồn từ văn bản đi có sẵn | 1. Chọn loại tài liệu 'Văn bản đi'.<br>2. Chọn một văn bản đi từ danh sách.<br>3. Chọn quy trình ký.<br>4. Bấm 'Tiếp tục'. | Hệ thống tự động nạp tệp PDF đính kèm của văn bản đi, trích xuất metadata và chuyển sang Bước 2. | Tệp PDF được tải lên tự động, hiển thị bản xem trước sắc nét ở Bước 2. | Nhóm 5 | High | **PASS** |
| **TC-19** | Tạo hồ sơ (`/approvals/tao-ho-so`) | Tải lên tệp PDF độc lập từ máy tính (kiểm tra giới hạn <= 20MB) | 1. Chọn loại tài liệu 'Tài liệu độc lập'.<br>2. Kéo thả tệp PDF dung lượng 5MB.<br>3. Nhập trích yếu và độ khẩn.<br>4. Bấm 'Tiếp tục'. | Kiểm tra đúng magic bytes `%PDF-`, dung lượng hợp lệ, upload lên server lưu trữ an toàn. | Tài liệu độc lập được tiếp nhận thành công, chuyển sang bước xem trước tài liệu. | Nhóm 5 | High | **PASS** |
| **TC-20** | Tạo hồ sơ (`/approvals/tao-ho-so`) | Khóa nội dung tài liệu bằng mã băm SHA-256 chống chỉnh sửa | 1. Tải tệp PDF lên hồ sơ.<br>2. Kiểm tra thông tin kỹ thuật hiển thị trên giao diện và payload API. | Hệ thống tính toán chuỗi hash SHA-256 64 ký tự hex của tệp PDF và lưu cố định vào hồ sơ. | Mã băm SHA-256 được tính toán chính xác, bất kỳ thay đổi nào vào tệp đều làm sai lệch hash. | Nhóm 5 | High | **PASS** |
| **TC-21** | Tạo hồ sơ (`/approvals/tao-ho-so`) | Kéo thả định vị khung chữ ký cho từng người ký trên trang văn bản | 1. Xem trước tài liệu qua `pdf.js`.<br>2. Kéo khung ký từ thanh công cụ thả vào vị trí cuối trang 2.<br>3. Tùy chỉnh kích thước.<br>4. Gán người ký cho khung. | Tọa độ x, y, width, height, page được lưu lại với độ chính xác cao. | Khung ký hiển thị trực quan, hỗ trợ kéo thả mượt mà, lưu đúng tọa độ. | Nhóm 5 | High | **PASS** |
| **TC-22** | Tạo hồ sơ (`/approvals/tao-ho-so`) | Kiểm tra ngăn chặn tạo 2 hồ sơ trùng lặp khi click đúp nút Gửi trình | 1. Bấm liên tiếp nút 'Gửi trình ký'.<br>2. Theo dõi header request `Idempotency-Key` (UUID v4). | Request thứ hai bị backend nhận diện đã xử lý, chỉ tạo đúng duy nhất 01 hồ sơ trình ký. | Hệ thống bảo vệ idempotency thành công, không phát sinh hồ sơ trùng rác. | Nhóm 5 | High | **PASS** |
| **TC-23** | Danh sách hồ sơ (`/approvals`) | Xác thực nội dung 3 tab 'Cần tôi ký duyệt', 'Hồ sơ tôi trình', 'Hồ sơ được xem' | 1. Đăng nhập tài khoản chuyên viên A.<br>2. Kiểm tra danh sách hiển thị ở từng tab. | Tab 'Cần tôi ký duyệt' chỉ hiển thị hồ sơ chờ A ký; tab 'Tôi trình' hiển thị hồ sơ A tạo; tab 'Được xem' hiển thị hồ sơ liên quan. | Phân quyền dữ liệu hiển thị chuẩn xác 100%, không bị lẫn lộn giữa các tài khoản. | Nhóm 5 | Critical | **PASS** |
| **TC-24** | Danh sách hồ sơ (`/approvals`) | Lọc theo trạng thái, độ khẩn và tìm kiếm theo từ khóa | 1. Chọn lọc trạng thái 'Đang ký'.<br>2. Chọn mức độ khẩn 'Hỏa tốc'.<br>3. Gõ từ khóa trích yếu vào ô tìm kiếm. | Danh sách lọc tức thì, cập nhật số lượng hồ sơ khớp điều kiện. | Bộ lọc hoạt động chính xác, giao diện phản hồi nhanh dưới 200ms. | Nhóm 5 | Medium | **PASS** |
| **TC-25** | Chi tiết hồ sơ (`/approvals/:id`) | Hiển thị dòng thời gian tiến trình ký nhiều cấp và nhật ký kiểm toán | 1. Mở một hồ sơ đang trong tiến trình ký.<br>2. Xem cây tiến trình và thẻ nhật ký hoạt động. | Hiển thị đầy đủ thông tin: ai đã ký lúc nào, ai đang chờ ký, thời hạn còn lại, lý do ý kiến trao đổi. | Giao diện chi tiết rõ ràng, trực quan, cập nhật thời gian thực trạng thái cấp ký. | Nhóm 5 | High | **PASS** |
| **TC-26** | Chi tiết hồ sơ (`/approvals/:id`) | Người ký nhập PIN, sinh chữ ký Ed25519 và nhúng con dấu trực quan | 1. Người ký bấm 'Ký duyệt'.<br>2. Nhập mã PIN 6 số của khóa ký trên thiết bị.<br>3. Bấm xác nhận ký. | Private key được giải mã từ IndexedDB, tạo chữ ký số Ed25519 trên SHA-256 hash của văn bản; backend verify hợp lệ; nhúng dấu ảnh lên PDF. | Ký số thành công, tài liệu cập nhật chữ ký số và con dấu trực quan tại đúng khung ký, chuyển cấp tiếp theo. | Nhóm 5 | Critical | **PASS** |
| **TC-27** | Chi tiết hồ sơ (`/approvals/:id`) | Người ký từ chối duyệt hoặc yêu cầu bổ sung chỉnh sửa tài liệu | 1. Bấm nút 'Trả lại để sửa' hoặc 'Từ chối'.<br>2. Nhập lý do từ chối bắt buộc trong modal.<br>3. Bấm xác nhận. | Trạng thái hồ sơ chuyển sang TRẢ LẠI / TỪ CHỐI; thông báo gửi về cho người lập hồ sơ; ghi nhật ký kiểm toán. | Cập nhật trạng thái thành công, bắt buộc nhập lý do mới cho gửi, nhật ký hiển thị lý do chi tiết. | Nhóm 5 | High | **PASS** |
| **TC-28** | Quản trị khóa (`/approvals/quan-ly-khoa`) | Chặn quyền truy cập của chuyên viên thường, chỉ cho phép Quản trị viên | 1. Chuyên viên thường gõ URL `/approvals/quan-ly-khoa`.<br>2. Quản trị viên hệ thống truy cập URL này. | Chuyên viên thường bị chặn hiển thị thông báo lỗi 403; Quản trị viên truy cập xem được danh sách khóa, lịch sử đăng ký và nút khóa/mở khóa. | Bảo mật phân quyền RBAC hoạt động chuẩn mực ở cả giao diện React và API Django. | Nhóm 5 | High | **PASS** |
| **TC-29** | Toàn hệ thống | Chuyển đổi ngôn ngữ Tiếng Việt và Tiếng Anh đồng bộ không sót nhãn | 1. Bấm nút chuyển ngôn ngữ sang 'EN'.<br>2. Kiểm tra các tiêu đề, nút bấm, modal, thông báo lỗi.<br>3. Chuyển lại về 'VN'. | 100% nhãn text hiển thị chuẩn ngữ cảnh tiếng Anh; chuyển về tiếng Việt đầy đủ không bị mất dữ liệu; không có chuỗi hardcode. | Chuyển đổi ngôn ngữ trơn tru, toàn bộ 2639 key từ điển khớp hoàn toàn, `check:i18n` PASS. | Nhóm 5 | High | **PASS** |
| **TC-30** | Toàn hệ thống | Kiểm tra Dark Mode và hiển thị Responsive trên thiết bị di động (390px) | 1. Bật chế độ Tối (Dark mode).<br>2. Thu nhỏ màn hình trình duyệt về kích thước 390x844 (Mobile). | Màu sắc thay đổi theo hệ thống token CSS `var(--color-...)`; không hardcode mã màu hex; layout mobile co giãn linh hoạt, không bị vỡ giao diện. | Giao diện hiển thị sắc nét ở cả hai chế độ Sáng/Tối và trên màn hình di động, `check:tokens` PASS. | Nhóm 5 | High | **PASS** |

---

## III. Chi tiết các Sự cố Trọng yếu Đã Khắc phục Triệt để

### 1. Khắc phục lỗi WebCrypto trên HTTP Staging (Issue #534 / PR #535)
- **Tình trạng trước khi fix**:
  - Khi truy cập trang `/approvals/khoa` qua địa chỉ HTTP Staging (`http://staging-quanlyvanban.bhbl.vn:8088/`), trình duyệt đặt `window.isSecureContext = false` và vô hiệu hóa `window.crypto.subtle`.
  - Màn hình xuất hiện banner cảnh báo màu đỏ: *"Trình duyệt này chưa hỗ trợ tạo khóa ký. Hãy cập nhật trình duyệt lên phiên bản mới."* và chặn toàn bộ người dùng tạo khóa hay ký tài liệu.
  - *Bằng chứng trước khi fix*: [evidence_01_webcrypto_before_fix.png](evidence_01_webcrypto_before_fix.png)
- **Giải pháp xử lý kỹ thuật**:
  - Tích hợp bộ thư viện pure-JS chuẩn (@noble/curves, @noble/ciphers, @noble/hashes) làm fallback mật mã tự động khi WebCrypto không khả dụng.
  - Sinh khóa Ed25519 PKCS#8 DER (48 byte), dẫn xuất HKDF-SHA256 và bản bọc AES-256-GCM lưu trữ IndexedDB, hoàn toàn tương thích với backend Python `cryptography`.
- **Kết quả sau khi fix**:
  - Người dùng thiết lập PIN 6 số, sinh khóa ký và thực hiện ký số bình thường trên Staging HTTP không cần cờ trình duyệt.

### 2. Tinh gọn Quy trình ký & Mở rộng Danh bạ 83 CBNV (Issue #532 / PR #533)
- **Tình trạng trước khi fix**:
  - Form tạo quy trình hiển thị khối chức danh với 25 chức danh và khối xem trước *"Cán bộ đang giữ chức danh"* chiếm dụng diện tích lớn, gây nhầm lẫn khi người dùng muốn chỉ định người ký đích danh.
  - Danh sách cán bộ bị giới hạn 10 người và bắt buộc gõ từ 2 ký tự mới gợi ý.
- **Giải pháp xử lý kỹ thuật**:
  - Loại bỏ hoàn toàn khối dropdown chức danh và khối xem trước.
  - Nâng cấp ô "Chọn người ký cụ thể" hiển thị danh sách cuộn đầy đủ 83 cán bộ nhân viên của cơ quan ngay khi focus, hỗ trợ tìm kiếm nhanh theo tên, tài khoản, đơn vị.
- **Kết quả sau khi fix**:
  - Giao diện trực quan, tinh gọn; hiển thị đầy đủ 83 CBNV; thao tác chọn nhiều người ký và lưu quy trình diễn ra trơn tru.

### 3. Khắc phục lỗi tải lên ảnh chữ ký cá nhân do stringify FormData (Issue #542 / PR #543)
- **Tình trạng trước khi fix**:
  - Người dùng bấm tải ảnh chữ ký lên hệ thống nhận thông báo lỗi: *"Vui lòng cung cấp tệp ảnh hoặc dữ liệu Base64 ảnh chữ ký."*
  - Nguyên nhân: `apiClient.post` gọi `JSON.stringify(body)` khiến đối tượng `FormData` bị biến thành chuỗi rỗng `"{}"` và ép header `Content-Type: application/json`.
- **Giải pháp xử lý kỹ thuật**:
  - Bổ sung hàm nhận diện `isRawBody` và `serializeBody` trong `frontend/src/lib/apiClient.ts` để giữ nguyên binary (`FormData`, `Blob`, `ArrayBuffer`) và cho phép trình duyệt tự thiết lập boundary multipart.
  - Nâng cấp `taiLenAnhChuKy` hỗ trợ tải ảnh cả 2 phương thức: tệp nhị phân multipart và chuỗi Base64 dataUrl.
- **Kết quả sau khi fix**:
  - Tải ảnh chữ ký thành công, server tiếp nhận payload nhị phân, băm mã SHA-256 và lưu trữ chính xác.

### 4. Phân tách phân vùng thông báo ảnh chữ ký & Dual Fallback (Issue #545 / PR #546)
- **Tình trạng trước khi fix**:
  - Khi tải ảnh chữ ký cá nhân bị lỗi, banner thông báo lỗi bị hiển thị tràn sang thẻ "Cấu hình khóa ký" bên trái (do dùng chung state `thongBao`), gây xáo trộn giao diện và hiểu lầm về trạng thái khóa ký.
  - *Bằng chứng trước khi fix*: [evidence_02_signature_notification_before_fix.jpg](evidence_02_signature_notification_before_fix.jpg)
- **Giải pháp xử lý kỹ thuật**:
  - Tách riêng state `thongBaoChuKy` trong `frontend/src/pages/signing/KhoaPage.tsx` đặt độc lập bên trong thẻ "Ảnh chữ ký cá nhân" bên phải.
  - Tự động fallback sang gọi Base64 dataUrl khi upload Blob nhị phân gặp sự cố kết nối.
- **Kết quả sau khi fix**:
  - Thông báo hiển thị chính xác trong phân vùng thẻ phải, không làm biến đổi giao diện thẻ trái.

---

## IV. Xác thực các Cổng Chất lượng Kỹ thuật (Technical Gates)

| Cổng kiểm định | Lệnh kiểm tra | Kết quả xác thực | Đánh giá |
|:---|:---|:---|:---:|
| **Frontend Build Gate** | `pnpm --dir frontend run build` | Build thành công 100%, bundle chunking chuẩn, 0 error | **PASS** |
| **Frontend Lint Gate** | `pnpm --dir frontend run lint` | Tuân thủ toàn bộ quy chuẩn ESLint dự án | **PASS** |
| **i18n Coverage Gate** | `pnpm --dir frontend check:i18n` | 100% nhãn có đủ cả 2 nhánh `vi`/`en`, 2639 keys | **PASS** |
| **Design Tokens Gate** | `pnpm --dir frontend check:tokens` | 100% màu sắc và font dùng CSS variables từ `global.css` | **PASS** |
| **Backend System Check** | `python backend/manage.py check` | Hệ thống Django không phát sinh cảnh báo | **PASS** |
| **Backend Unit Tests** | `python backend/manage.py test apps.signing` | Toàn bộ 47 unit tests phân hệ Trình ký vượt qua | **PASS** |
| **DB Schema Consistency** | `python scripts/build_db.py --check` | Khớp 100% với `release_DDL.sql`, collation ICU `vi-VN` | **PASS** |

---

## V. Hướng dẫn Nhập Dữ liệu vào Google Sheets

1. Mở file dữ liệu dạng bảng TSV: [danh_sach_testcase_google_sheets.tsv](danh_sach_testcase_google_sheets.tsv).
2. Nhấn `Ctrl + A` để chọn toàn bộ nội dung, sau đó nhấn `Ctrl + C` để sao chép.
3. Mở trang Google Sheet của dự án (Tab: **QA Testcase Nhóm 5**).
4. Đặt con trỏ chuột tại ô **A2** (hoặc ô đầu dòng dữ liệu) và nhấn `Ctrl + V`.
5. Toàn bộ 30 dòng dữ liệu kiểm thử sẽ được tự động điền chuẩn xác vào 10 cột tương ứng:
   `STT` | `Mã TC` | `Phân hệ / Màn hình` | `Tên ca kiểm thử` | `Mô tả & Các bước thực hiện` | `Kết quả mong đợi` | `Kết quả thực tế` | `Người test` | `Mức độ ưu tiên` | `Trạng thái`.

---

## VI. Kết luận & Đánh giá Nghiệm thu

1. **Kết quả kiểm thử**: 29/30 ca **PASS**; TC-06 **BLOCKED** do chưa xác minh khôi phục cùng khóa và ký lại thành công.
2. **Bảo mật & Độ tin cậy**: Cơ chế tạo khóa Ed25519, mã hóa bản bọc AES-256-GCM trong IndexedDB và fallback pure-JS đáp ứng đầy đủ tiêu chuẩn mật mã trên mọi môi trường mạng.
3. **Mức độ sẵn sàng**: Chưa kết luận **Production-Ready** cho đến khi TC-06 được xử lý theo issue #553 và xác minh trên staging bằng chữ ký dùng đúng khóa cũ.
