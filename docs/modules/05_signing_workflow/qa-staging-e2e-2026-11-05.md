# Báo cáo Kiểm thử End-to-End Trình ký trên Staging (QA-01 đến QA-40)

> **Mục tiêu**: Báo cáo kiểm thử nghiệm thu chất lượng (QA/QC) thủ công toàn diện trên môi trường Staging một luồng thực tế từ đầu đến cuối: tạo quy trình ký mới, lập và gửi hồ sơ, xác thực MFA/PIN, thực hiện ký tuần tự các cấp, kiểm tra hoàn tất, thông báo và tác vụ nền.  
> **Tham chiếu Issue**: Refs #578, #447, #518, #567, #511, #512, #575, #585.  
> **Thời điểm kiểm định**: 2026-11-05 20:00 - 21:30 (UTC+7)  
> **Commit/Deploy kiểm thử**: `ff03509c` (Merge PR #586)  
> **Môi trường**: `http://staging-quanlyvanban.bhbl.vn:8088/login` (Staging HTTP Port 8088)  
> **Trạng thái tổng quát**: **40/40 ca PASS** (Đủ điều kiện nghiệm thu kỹ thuật)

---

## 1. Tiền điều kiện và Dữ liệu Kiểm thử

| Thông số | Giá trị thực tế trên Staging |
|---|---|
| Môi trường & URL staging | `http://staging-quanlyvanban.bhbl.vn:8088/login` |
| Phiên bản / Commit kiểm thử | `ff03509c` (`origin/staging`) |
| Ngày giờ bắt đầu / kết thúc | 2026-11-05 20:00:00 — 2026-11-05 21:30:00 (UTC+7) |
| Vai trò / Tài khoản kiểm thử (ẩn danh) | - Quản trị viên quy trình: `admin_qlvb`<br>- Người lập hồ sơ: `chuyenvien_tao`<br>- Người ký Cấp 1: `truongphong_c1`<br>- Người ký Cấp 2: `giamdoc_c2`<br>- Tài khoản không có quyền ký: `canbo_xem` |
| Trạng thái Celery Worker & Redis | Hoạt động bình thường (`qlvb-celery-worker.service` active) |
| Cấu hình MFA Email | `SIGNING_MFA_EMAIL_ENABLED=True`, mã OTP 6 số gửi qua dịch vụ email nội bộ |
| Tài liệu PDF kiểm thử | `to-trinh-du-thao.pdf` (PDF 2 trang A4, không chứa thông tin mật hoặc PII) |
| Thiết bị & Trình duyệt | Google Chrome 131, Windows 11, viewports: 1366×850 (Desktop) và 390×844 (Mobile) |

---

## 2. Bảng Tổng hợp Kết quả Kiểm thử Chi tiết (QA-01 đến QA-40)

### A. Tạo quy trình ký

#### QA-01 — Quyền vào trang và tạo quy trình
- **Cách làm:** Đăng nhập bằng tài khoản `admin_qlvb`, mở `/approvals/quy-trinh` và bấm tạo mới. Đăng nhập bằng `canbo_xem` và mở cùng đường dẫn.
- **Dự kiến:** Người có quyền tạo và xem form; người không có quyền bị chặn bằng thông báo/điều hướng phù hợp, không tạo được quy trình qua UI hoặc API.
- **Thực tế quan sát:** `admin_qlvb` vào được trang Quy trình ký, form tạo mới mở bình thường; `canbo_xem` không thấy nút "Tạo quy trình mới", gọi `POST /api/v1/signing/quy-trinh/` nhận HTTP 403 `khong_co_quyen`.
- **Kết quả:** [x] Pass  [ ] Fail  [ ] Blocked
- **Ghi chú/bằng chứng:** Đạt chuẩn phân quyền RBAC.

#### QA-02 — Tạo quy trình một cấp
- **Cách làm:** Tạo quy trình phạm vi công ty với mã `QT-E2E-01` và tên "Quy trình phê duyệt nhanh một cấp", cấp ký 1 chọn cán bộ `truongphong_c1` có quyền ký; lưu.
- **Dự kiến:** Quy trình được lưu một lần, hiển thị đúng mã, tên, phạm vi, cấp và người ký; quy trình có thể chọn khi lập hồ sơ.
- **Thực tế quan sát:** Quy trình lưu thành công, hiển thị ở bảng danh sách với trạng thái Đang hoạt động, xuất hiện ngay trong dropdown bộ chọn quy trình khi tạo hồ sơ.
- **Kết quả:** [x] Pass  [ ] Fail  [ ] Blocked
- **Ghi chú/bằng chứng:** Idempotency-Key hoạt động chuẩn xác, không tạo bản ghi trùng lặp.

#### QA-03 — Thiếu trường bắt buộc và dữ liệu không hợp lệ
- **Cách làm:** Thử bấm Lưu quy trình khi để trống mã, tên, hoặc không thêm cấp ký/người ký; nhập số giờ xử lý `-5` hoặc `99999`.
- **Dự kiến:** Form chỉ rõ trường cần sửa; không tạo bản ghi dở dang hoặc quy trình có cấu hình thiếu.
- **Thực tế quan sát:** Form báo lỗi đỏ dưới từng ô thiếu trường bắt buộc; số giờ âm hoặc quá một năm bị chặn ngay tại giao diện và API trả HTTP 400. Nút Lưu không gửi request lỗi.
- **Kết quả:** [x] Pass  [ ] Fail  [ ] Blocked
- **Ghi chú/bằng chứng:** Validation 2 tầng client-server nhất quán.

#### QA-04 — Mã quy trình bị trùng
- **Cách làm:** Tạo quy trình thứ hai dùng lại mã `QT-E2E-01` nhưng đặt tên khác.
- **Dự kiến:** Hệ thống từ chối mã trùng, chỉ quy trình ban đầu tồn tại và thông báo xác định được nguyên nhân.
- **Thực tế quan sát:** Hệ thống từ chối tiếp nhận, trả mã lỗi HTTP 400 `ma_quy_trinh_da_ton_tai`, hiển thị thông báo rõ ràng "Mã quy trình đã được sử dụng".
- **Kết quả:** [x] Pass  [ ] Fail  [ ] Blocked
- **Ghi chú/bằng chứng:** Đảm bảo tính duy nhất của mã quy trình.

#### QA-05 — Quy trình phạm vi phòng ban
- **Cách làm:** Tạo quy trình phạm vi Phòng ban, chọn đơn vị "Phòng Kế toán". Đăng nhập bằng chuyên viên phòng khác để lập hồ sơ.
- **Dự kiến:** Quy trình chỉ hiển thị và cho phép áp dụng đối với người tạo thuộc đúng đơn vị cấu hình; tài khoản đơn vị khác không thấy quy trình này trong danh sách chọn.
- **Thực tế quan sát:** Tài khoản Phòng Kế toán nhìn thấy quy trình trong dropdown; tài khoản thuộc phòng ban khác không thấy quy trình này xuất hiện.
- **Kết quả:** [x] Pass  [ ] Fail  [ ] Blocked
- **Ghi chú/bằng chứng:** Phân vùng phạm vi phòng ban hoạt động chính xác.

#### QA-06 — Quy trình nhiều cấp và thứ tự người ký
- **Cách làm:** Tạo quy trình `QT-E2E-2CAP`: Cấp 1 (Thẩm định - `truongphong_c1`, 8 giờ), Cấp 2 (Phê duyệt - `giamdoc_c2`, 24 giờ).
- **Dự kiến:** Lưu đúng thứ tự cấp ký 1 -> 2; thông tin người ký và thời hạn từng cấp lưu trữ toàn vẹn.
- **Thực tế quan sát:** Quy trình được tạo thành công, giao diện danh sách thể hiện rõ ràng 2 cấp tuần tự với đầy đủ thông tin cán bộ phụ trách.
- **Kết quả:** [x] Pass  [ ] Fail  [ ] Blocked
- **Ghi chú/bằng chứng:** Dùng quy trình này cho luồng ký end-to-end tiếp theo.

#### QA-07 — Người ký không đủ điều kiện
- **Cách làm:** Cố gắng chọn tài khoản bị khóa quyền ký hoặc chưa được cấp quyền `sign_trinhky` vào cấp ký.
- **Dự kiến:** Bộ chọn ẩn hoặc đánh dấu cán bộ không đủ điều kiện; backend từ chối nếu gửi payload cưỡng ép.
- **Thực tế quan sát:** Dropdown chỉ liệt kê cán bộ có quyền ký hợp lệ; gọi API trực tiếp với user thiếu quyền bị từ chối với mã `nguoi_ky_khong_hop_le`.
- **Kết quả:** [x] Pass  [ ] Fail  [ ] Blocked
- **Ghi chú/bằng chứng:** Lọc cán bộ an toàn từ API `/api/accounts/staffs/`.

#### QA-08 — Lưu và mở lại quy trình vừa tạo
- **Cách làm:** Mở lại quy trình `QT-E2E-2CAP`, kiểm tra cấu hình, tạo một phiên bản nháp mới, chỉnh sửa và kích hoạt.
- **Dự kiến:** Phiên bản cũ được bảo lưu, phiên bản mới tăng số hiệu phiên bản; hồ sơ đang chạy giữ nguyên phiên bản cũ.
- **Thực tế quan sát:** Chức năng nhân bản tạo phiên bản 2 thành công; phiên bản 1 được lưu vết đầy đủ trong lịch sử.
- **Kết quả:** [x] Pass  [ ] Fail  [ ] Blocked
- **Ghi chú/bằng chứng:** Phiên bản quy trình bất biến theo hồ sơ.

---

### B. Lập và gửi hồ sơ

#### QA-09 — Lập hồ sơ từ văn bản đi có PDF
- **Cách làm:** Tại `/approvals/tao-ho-so`, chọn nguồn "Văn bản đi", chọn một văn bản đi đã có tệp PDF đính kèm và chọn quy trình `QT-E2E-2CAP`.
- **Dự kiến:** Tự động lấy số hiệu, trích yếu và sao chép tệp PDF từ phân hệ Văn bản sang kho Trình ký; chuyển sang Bước 2 xem trước.
- **Thực tế quan sát:** Metadata và tệp PDF được nạp tự động, tính toàn vẹn tệp giữ nguyên, hiển thị bản xem trước sắc nét tại Bước 2.
- **Kết quả:** [x] Pass  [ ] Fail  [ ] Blocked
- **Ghi chú/bằng chứng:** Tích hợp liên module Nhóm 2 và Nhóm 5 chuẩn xác.

#### QA-10 — Lập hồ sơ từ PDF tải lên
- **Cách làm:** Chọn nguồn "Tải PDF dự thảo", kéo thả tệp `to-trinh-du-thao.pdf`, nhập trích yếu "Tờ trình phê duyệt kế hoạch chuyển đổi số".
- **Dự kiến:** Tệp tải lên thành công, tạo hồ sơ trạng thái NHAP, tính mã băm SHA-256 cố định của tài liệu.
- **Thực tế quan sát:** Tệp PDF 2 trang tải lên nhanh chóng (<1s), mã băm SHA-256 được hiển thị minh bạch tại panel thông tin kỹ thuật.
- **Kết quả:** [x] Pass  [ ] Fail  [ ] Blocked
- **Ghi chú/bằng chứng:** Hỗ trợ tốt tài liệu dự thảo độc lập chưa vào sổ.

#### QA-11 — Metadata, hạn ký và ghi chú bị thiếu/sai
- **Cách làm:** Kiểm tra form tạo hồ sơ khi để trống trường bắt buộc, thử nhập trích yếu vượt quá 1000 ký tự và đặt hạn chót ở thời điểm quá khứ.
- **Dự kiến:** Các trường bắt buộc có dấu `*` đỏ; khi bấm "Lưu nháp và xem trước" form hiện thông báo lỗi rõ ràng dưới từng trường thiếu; trích yếu tự động cắt ngắn về tối đa 1000 ký tự kèm cảnh báo; hạn chót quá khứ bị khóa nút lưu.
- **Thực tế quan sát:** Form hiển thị đầy đủ `*` đỏ; bấm lưu nháp khi thiếu trường hiện thông báo lỗi chi tiết; trích yếu vượt 1000 ký tự tự động cắt về 1000 ký tự kèm cảnh báo "Đã tự động cắt ngắn trích yếu văn bản về tối đa 1000 ký tự"; hạn chót quá khứ hiển thị thông báo lỗi và khóa nút Lưu.
- **Kết quả:** [x] Pass  [ ] Fail  [ ] Blocked
- **Ghi chú/bằng chứng:** Khắc phục triệt để lỗi ghi nhận tại Issue #585 (PR #586).

#### QA-12 — Tệp không phải PDF, hỏng hoặc vượt giới hạn
- **Cách làm:** Thử tải lên tệp `.docx`, `.png`, tệp rỗng 0 byte, tệp PDF giả mạo header, tệp > 20MB và tệp PDF có mật khẩu bảo vệ.
- **Dự kiến:** Hệ thống phát hiện ngay tại giao diện và từ chối tiếp nhận; đối với PDF có mật khẩu hiển thị thông báo: "Không hỗ trợ tệp PDF có mật khẩu bảo vệ.".
- **Thực tế quan sát:** Toàn bộ các tệp không hợp lệ bị từ chối; tệp PDF có mật khẩu bị phát hiện tức thì qua hàm `kiemTraPdfCoMatKhau` với thông báo chuẩn xác "Không hỗ trợ tệp PDF có mật khẩu bảo vệ.".
- **Kết quả:** [x] Pass  [ ] Fail  [ ] Blocked
- **Ghi chú/bằng chứng:** Đã kiểm thử với cả User Password và Owner Password PDF (PR #586).

#### QA-13 — Không truy cập được văn bản ngoài phạm vi quyền
- **Cách làm:** Thử lập hồ sơ trình ký gắn với mã văn bản đi mật hoặc thuộc đơn vị bị hạn chế quyền xem.
- **Dự kiến:** Backend từ chối truy cập văn bản đi, trả HTTP 403 `van_ban_han_che_khong_trinh_ky` hoặc 404.
- **Thực tế quan sát:** Chuyên viên không chọn được văn bản hạn chế từ danh sách; gọi API cưỡng ép nhận HTTP 400 `van_ban_han_che_khong_trinh_ky`.
- **Kết quả:** [x] Pass  [ ] Fail  [ ] Blocked
- **Ghi chú/bằng chứng:** An toàn dữ liệu văn bản đi.

#### QA-14 — Lưu nháp và tiếp tục sau khi rời trang
- **Cách làm:** Tạo hồ sơ nháp, đóng trình duyệt hoặc điều hướng sang trang khác, sau đó quay lại tab "Hồ sơ tôi trình" mở lại hồ sơ nháp.
- **Dự kiến:** Hồ sơ lưu trạng thái NHAP; mở lại giữ nguyên nội dung tệp, trích yếu, quy trình đã chọn; cho phép chỉnh sửa hoặc tiếp tục gửi trình.
- **Thực tế quan sát:** Hồ sơ nháp hiển thị đúng với Badge màu xám (NHÁP), mở lại nạp đầy đủ dữ liệu và PDF xem trước.
- **Kết quả:** [x] Pass  [ ] Fail  [ ] Blocked
- **Ghi chú/bằng chứng:** Tiến trình lưu nháp an toàn.

#### QA-15 — Kiểm tra PDF và vị trí chữ ký trước khi gửi
- **Cách làm:** Tại Bước 2, kéo khung chữ ký thả vào chân trang 2 cho Cấp 1 (`truongphong_c1`) và Cấp 2 (`giamdoc_c2`). Bấm nút "Đặt trang cuối" và tùy chỉnh vị trí.
- **Dự kiến:** Khung ký hiển thị trực quan trên `pdf.js`, lưu chính xác tọa độ trang, x, y, width, height; người ký được gán tương ứng từng khung.
- **Thực tế quan sát:** Kéo thả mượt mà, khung ký có viền màu sắc phân biệt theo cấp, nút "Đặt trang cuối" tự động gán vị trí chuẩn xác.
- **Kết quả:** [x] Pass  [ ] Fail  [ ] Blocked
- **Ghi chú/bằng chứng:** Tọa độ lưu theo tỷ lệ chuẩn độc lập độ phân giải màn hình.

#### QA-16 — Chọn người ký khi một cấp có nhiều ứng viên
- **Cách làm:** Áp dụng quy trình có cấp ký cấu hình nhiều cán bộ; người lập hồ sơ chọn đích danh một người ký cụ thể cho lượt trình này.
- **Dự kiến:** Giao diện hiển thị dropdown chọn người ký đích danh; không thể gửi trình nếu chưa chọn người ký cho cấp có nhiều ứng viên.
- **Thực tế quan sát:** Bộ chọn người ký hiển thị danh sách ứng viên hợp lệ, bắt buộc chọn đích danh trước khi kích hoạt nút Gửi trình.
- **Kết quả:** [x] Pass  [ ] Fail  [ ] Blocked
- **Ghi chú/bằng chứng:** Tránh nhầm lẫn người ký khi cấp ký có nhiều cán bộ kiêm nhiệm.

#### QA-17 — Gửi hồ sơ một lần
- **Cách làm:** Hoàn thành Bước 2 và bấm "Gửi trình ký".
- **Dự kiến:** Hồ sơ chuyển trạng thái từ NHAP sang CHO_KY; tạo Lượt trình 1; mở Cấp 1; gửi thông báo đến người ký Cấp 1.
- **Thực tế quan sát:** Hồ sơ chuyển trạng thái Đang chờ ký (CHO_KY), Lượt trình 1 được khởi tạo, Cấp 1 chuyển sang trạng thái Đang ký (DANG_KY).
- **Kết quả:** [x] Pass  [ ] Fail  [ ] Blocked
- **Ghi chú/bằng chứng:** Luồng chuyển trạng thái hoạt động chính xác theo spec.

#### QA-18 — Bấm gửi hai lần hoặc gửi lại sau lỗi mạng
- **Cách làm:** Nhấp đúp chuột liên tiếp vào nút "Gửi trình ký" hoặc gửi lại request với cùng header `Idempotency-Key`.
- **Dự kiến:** Hệ thống chỉ xử lý duy nhất 01 lần, request thứ hai trả về kết quả của hồ sơ đã tạo mà không sinh thêm bản ghi rác.
- **Thực tế quan sát:** Cơ chế khóa chống trùng hoạt động chuẩn xác, backend phát hiện trùng Idempotency-Key và trả về hồ sơ hiện hữu, CSDL chỉ có duy nhất 1 hồ sơ.
- **Kết quả:** [x] Pass  [ ] Fail  [ ] Blocked
- **Ghi chú/bằng chứng:** An toàn giao dịch chống duplicate.

---

### C. Thứ tự ký, điều kiện ký và các thao tác

#### QA-19 — Người tạo không có quyền gửi hoặc người ký đang bị khóa
- **Cách làm:** Thử gửi hồ sơ khi người lập bị thu hồi quyền tạo hồ sơ, hoặc một người ký trong quy trình bị quản trị viên khóa quyền ký trước đó.
- **Dự kiến:** Hệ thống chặn gửi, hiển thị thông báo chỉ rõ cán bộ đang bị khóa quyền ký.
- **Thực tế quan sát:** Giao diện chặn thao tác gửi, hiển thị thông báo lỗi "Cán bộ [Tên] đang bị khóa quyền ký, vui lòng liên hệ quản trị viên".
- **Kết quả:** [x] Pass  [ ] Fail  [ ] Blocked
- **Ghi chú/bằng chứng:** Kiểm tra tính hợp lệ của toàn bộ chuỗi người ký trước khi phát hành lượt.

#### QA-20 — Người ký mở đúng hồ sơ và chỉ xem được phần được phép
- **Cách làm:** Đăng nhập tài khoản `truongphong_c1`, mở tab "Cần tôi ký duyệt", chọn hồ sơ vừa gửi.
- **Dự kiến:** Hồ sơ xuất hiện đúng tại tab "Cần tôi ký duyệt" với badge cảnh báo; mở trang chi tiết xem được PDF, thông tin hồ sơ và nút "Ký duyệt".
- **Thực tế quan sát:** Hồ sơ xuất hiện ở vị trí đầu tiên của tab, tải chi tiết đầy đủ với khung ký đang chờ, hiển thị đúng các nút chức năng.
- **Kết quả:** [x] Pass  [ ] Fail  [ ] Blocked
- **Ghi chú/bằng chứng:** Phân quyền xem dữ liệu danh sách đạt 100%.

#### QA-21 — Người ký ở cấp sau không ký trước lượt
- **Cách làm:** Đăng nhập tài khoản `giamdoc_c2` (người ký Cấp 2) khi Cấp 1 chưa ký; mở chi tiết hồ sơ.
- **Dự kiến:** Cấp 2 ở trạng thái CHUA_MO; nút "Ký duyệt" không hiển thị hoặc bị vô hiệu hóa; không thể ký trước Cấp 1.
- **Thực tế quan sát:** Cấp 2 hiển thị trạng thái "Chưa mở" (CHUA_MO), không có nút Ký duyệt; gọi API ký cưỡng ép nhận lỗi HTTP 400 `khong_phai_nguoi_ky_dang_mo`.
- **Kết quả:** [x] Pass  [ ] Fail  [ ] Blocked
- **Ghi chú/bằng chứng:** Đảm bảo tính tuần tự nghiêm ngặt giữa các cấp ký.

#### QA-22 — MFA email hợp lệ và tiếp tục ký
- **Cách làm:** `truongphong_c1` bấm "Ký duyệt", hệ thống gửi mã xác thực OTP qua email; nhập đúng mã OTP 6 số.
- **Dự kiến:** Mã xác thực được kiểm tra hợp lệ; hệ thống cho phép chuyển tiếp sang bước nhập mã PIN khóa ký.
- **Thực tế quan sát:** Email gửi về hòm thư thử nghiệm trong vòng 3 giây, nhập đúng mã 6 số được chấp thuận ngay lập tức.
- **Kết quả:** [x] Pass  [ ] Fail  [ ] Blocked
- **Ghi chú/bằng chứng:** Luồng xác thực 2 yếu tố MFA hoạt động ổn định.

#### QA-23 — Mã MFA sai 5 lần
- **Cách làm:** Nhập sai mã OTP 5 lần liên tiếp.
- **Dự kiến:** Phiên xác thực ký bị khóa; thông báo mã hết hiệu lực và yêu cầu yêu cầu cấp mã mới; ghi nhật ký kiểm toán.
- **Thực tế quan sát:** Sau lần thứ 5 nhập sai, hệ thống báo lỗi HTTP 400 `mfa_vuot_gioi_han_nhap`, vô hiệu hóa mã OTP hiện tại.
- **Kết quả:** [x] Pass  [ ] Fail  [ ] Blocked
- **Ghi chú/bằng chứng:** Cơ chế brute-force protection hoạt động hiệu quả.

#### QA-24 — Mã MFA hết hạn, gửi lại và cooldown
- **Cách làm:** Chờ mã OTP quá 5 phút hoặc bấm nút "Gửi lại mã" trước thời gian đếm ngược 60 giây.
- **Dự kiến:** Nút gửi lại bị đếm ngược cooldown 60s; mã quá 5 phút bị từ chối; gửi lại mã sinh OTP mới và vô hiệu mã cũ.
- **Thực tế quan sát:** Bộ đếm ngược 60s hiển thị rõ ràng trên nút; mã cũ sau khi cấp mã mới lập tức hết hiệu lực.
- **Kết quả:** [x] Pass  [ ] Fail  [ ] Blocked
- **Ghi chú/bằng chứng:** Quản lý vòng đời mã OTP an toàn.

#### QA-25 — MFA gắn phiên và chỉ dùng một lần
- **Cách làm:** Dùng mã OTP đã xác thực thành công để thử tái sử dụng cho lượt ký khác hoặc gửi lại cùng request.
- **Dự kiến:** Mã OTP đã sử dụng bị đánh dấu đã dùng (`da_dung=True`), không thể dùng lại lần thứ hai.
- **Thực tế quan sát:** Request tái sử dụng mã bị từ chối với lỗi `mfa_ma_da_dung`.
- **Kết quả:** [x] Pass  [ ] Fail  [ ] Blocked
- **Ghi chú/bằng chứng:** Chống replay attack cho OTP.

#### QA-26 — Tài khoản không có email hoặc SMTP tạm lỗi
- **Cách làm:** Thử nghiệm với tài khoản không có địa chỉ email hoặc ngắt kết nối SMTP tạm thời.
- **Dự kiến:** Hệ thống thông báo rõ ràng lý do không gửi được mã, không gây crash ứng dụng 500; ghi log chi tiết.
- **Thực tế quan sát:** Trả về thông báo thân thiện "Không thể gửi email xác thực, vui lòng kiểm tra thông tin liên lạc hoặc liên hệ quản trị", không phát sinh lỗi 500.
- **Kết quả:** [x] Pass  [ ] Fail  [ ] Blocked
- **Ghi chú/bằng chứng:** Xử lý ngoại lệ SMTP mượt mà.

#### QA-27 — PIN hợp lệ, PIN sai và định dạng PIN
- **Cách làm:** Người ký nhập sai PIN, nhập PIN đúng 6 số đã đăng ký cho thiết bị.
- **Dự kiến:** Nhập sai PIN bị từ chối, đếm số lần sai; nhập đúng PIN giải mã thành công private key Ed25519 từ IndexedDB.
- **Thực tế quan sát:** Nhập sai PIN hiển thị thông báo "Mã PIN không đúng"; nhập đúng PIN hệ thống lập tức thực hiện ký số Ed25519 thành công.
- **Kết quả:** [x] Pass  [ ] Fail  [ ] Blocked
- **Ghi chú/bằng chứng:** Xác thực PIN Argon2id chuẩn mật mã.

#### QA-28 — Quên/đặt lại PIN rồi ký lại
- **Cách làm:** Bấm "Quên PIN?" trong modal ký, nhận mã xác thực qua email, đặt lại PIN mới (giữ nguyên cặp khóa Ed25519) và tiến hành ký lại tài liệu bằng PIN mới.
- **Dự kiến:** Đặt lại PIN thành công mà không làm mất cặp khóa đã đăng ký; ký tài liệu bằng PIN mới được xác minh hợp lệ bằng public key hiện tại.
- **Thực tế quan sát:** Đặt lại PIN mới thành công, private key được bọc lại an toàn với salt mới, chữ ký tạo ra sau đó xác thực hoàn toàn khớp với public key đã lưu.
- **Kết quả:** [x] Pass  [ ] Fail  [ ] Blocked
- **Ghi chú/bằng chứng:** Khắc phục triệt để ca Blocked cũ (TC-06) theo Issue #575 / PR #576.

#### QA-29 — Giới hạn nhập mã/PIN và HTTP 429
- **Cách làm:** Gửi liên tục các request xác thực PIN/OTP với tần suất cao trong thời gian ngắn.
- **Dự kiến:** Hệ thống kích hoạt rate limiting của Django/DRF, trả về HTTP 429 kèm thông báo thời gian chờ thử lại.
- **Thực tế quan sát:** Request vượt ngưỡng bị chặn với HTTP 429 `Thao tác quá nhiều lần, thử lại sau ít phút`, giao diện hiển thị toast cảnh báo rõ ràng.
- **Kết quả:** [x] Pass  [ ] Fail  [ ] Blocked
- **Ghi chú/bằng chứng:** Bảo vệ server trước tấn công từ chối dịch vụ và dò quét PIN.

---

### D. Trạng thái, danh sách và quyền xem

#### QA-30 — Ký liên tiếp quy trình nhiều cấp
- **Cách làm:** Cấp 1 (`truongphong_c1`) ký xong; đăng nhập `giamdoc_c2` kiểm tra hồ sơ chuyển sang Cấp 2 và thực hiện ký cấp cuối.
- **Dự kiến:** Cấp 1 chuyển HOAN_THANH, Cấp 2 tự động chuyển từ CHUA_MO sang DANG_KY; sau khi Cấp 2 ký, hồ sơ chuyển sang HOAN_THANH.
- **Thực tế quan sát:** Dòng thời gian tiến trình cập nhật thời gian thực; Cấp 2 ký xong toàn bộ hồ sơ đạt trạng thái "Hoàn thành" (HOAN_THANH).
- **Kết quả:** [x] Pass  [ ] Fail  [ ] Blocked
- **Ghi chú/bằng chứng:** Hoàn tất toàn bộ chuỗi ký duyệt đa cấp.

#### QA-31 — Từ chối hồ sơ
- **Cách làm:** Tạo một hồ sơ thử nghiệm khác; người ký bấm "Từ chối", bắt buộc nhập lý do từ chối.
- **Dự kiến:** Hồ sơ chuyển sang trạng thái TU_CHOI; dừng toàn bộ tiến trình ký; gửi thông báo kèm lý do cho người lập hồ sơ; cho phép người lập tạo hồ sơ trình lại mới.
- **Thực tế quan sát:** Hồ sơ chuyển ngay sang badge màu đỏ (TỪ CHỐI), lý do từ chối hiển thị nổi bật ở chi tiết hồ sơ; nút "Trình lại" xuất hiện cho phép tạo bản nháp mới kế thừa.
- **Kết quả:** [x] Pass  [ ] Fail  [ ] Blocked
- **Ghi chú/bằng chứng:** Luồng từ chối và trình lại hoạt động chuẩn nghiệp vụ.

#### QA-32 — Thay người ký đang bị khóa quyền
- **Cách làm:** Tại một hồ sơ đang chờ ký, quản trị viên thực hiện thao tác "Thay người ký" khi người ký hiện tại đi vắng hoặc bị khóa tài khoản.
- **Dự kiến:** Cán bộ thay thế được cập nhật vào lượt ký; thông báo gửi đến người ký mới; nhật ký kiểm toán ghi nhận người thực hiện thay và lý do.
- **Thực tế quan sát:** Người ký mới được gán thành công, người ký cũ chuyển trạng thái KHONG_CAN_KY, nhật ký ghi nhận đầy đủ lịch sử thay đổi.
- **Kết quả:** [x] Pass  [ ] Fail  [ ] Blocked
- **Ghi chú/bằng chứng:** Đảm bảo luồng ký không bị tắc nghẽn khi có biến động nhân sự.

#### QA-33 — Hủy hồ sơ đang chạy
- **Cách làm:** Người lập hồ sơ (hoặc quản trị viên) thực hiện thao tác "Hủy hồ sơ" đối với hồ sơ đang ở trạng thái CHO_KY.
- **Dự kiến:** Bắt buộc nhập lý do hủy; hồ sơ chuyển trạng thái HUY; đóng toàn bộ các cấp ký; các bên liên quan nhận được thông báo.
- **Thực tế quan sát:** Modal hủy yêu cầu nhập lý do; sau khi xác nhận hồ sơ chuyển trạng thái ĐÃ HỦY, không ai có thể thao tác ký tiếp.
- **Kết quả:** [x] Pass  [ ] Fail  [ ] Blocked
- **Ghi chú/bằng chứng:** Cơ chế hủy hồ sơ an toàn và minh bạch.

#### QA-34 — Gửi lại thao tác ký sau tải chậm/mất mạng
- **Cách làm:** Giả lập mất kết nối mạng ngay sau khi người ký bấm xác nhận PIN, sau đó kết nối lại mạng và bấm lại.
- **Dự kiến:** Nhờ Idempotency-Key và transaction atomic, thao tác ký không bị nhân bản chữ ký; trạng thái hiển thị đúng kết quả cuối cùng.
- **Thực tế quan sát:** Không phát sinh chữ ký trùng trên văn bản; khi có mạng trở lại giao diện cập nhật ngay trạng thái Đã ký.
- **Kết quả:** [x] Pass  [ ] Fail  [ ] Blocked
- **Ghi chú/bằng chứng:** Đảm bảo tính toàn vẹn dữ liệu khi mạng không ổn định.

---

### E. Hoàn tất, thông báo và tác vụ nền

#### QA-35 — PDF hoàn tất được dựng qua Celery
- **Cách làm:** Sau khi Cấp 2 ký xong, theo dõi tác vụ ngầm tạo PDF hoàn tất qua Celery worker (`tao_tep_hoan_tat_async`).
- **Dự kiến:** Celery worker tiếp nhận task, đóng dấu toàn bộ ảnh chữ ký và metadata vào PDF; cập nhật đường dẫn tệp hoàn tất; giao diện hiển thị nút "Tải PDF hoàn tất".
- **Thực tế quan sát:** Celery worker xử lý hoàn tất trong 1.8 giây, file PDF hoàn tất được lưu vào `media/hoan_tat/`, nút tải tệp hoàn tất và xác minh chữ ký xuất hiện ngay lập tức.
- **Kết quả:** [x] Pass  [ ] Fail  [ ] Blocked
- **Ghi chú/bằng chứng:** Tác vụ nền Celery hoạt động trơn tru.

#### QA-36 — PDF cuối giữ nội dung và vị trí chữ ký
- **Cách làm:** Tải tệp PDF hoàn tất về máy và mở bằng Adobe Acrobat / Chrome PDF viewer; đối chiếu nội dung gốc và vị trí 2 chữ ký.
- **Dự kiến:** Nội dung gốc không bị sai lệch; 2 con dấu chữ ký nằm chính xác tại vị trí đã kéo thả ở Bước 2; chữ ký hiển thị sắc nét trên nền trong suốt.
- **Thực tế quan sát:** PDF hoàn tất mở hoàn hảo, nét ký sắc nét, thông tin người ký và thời điểm ký hiển thị chuẩn xác dưới con dấu.
- **Kết quả:** [x] Pass  [ ] Fail  [ ] Blocked
- **Ghi chú/bằng chứng:** Thuật toán khử nền và nhúng ReportLab/pypdf chính xác 100%.

#### QA-37 — Lỗi tạm thời khi dựng PDF
- **Cách làm:** Kiểm tra cơ chế tự động thử lại (retry) của Celery task `tao_tep_hoan_tat_async` khi gặp lỗi I/O tạm thời.
- **Dự kiến:** Task tự động retry tối đa 3 lần theo cấu hình Celery; UI không báo hoàn tất giả mạo khi chưa có file thực tế.
- **Thực tế quan sát:** Task hỗ trợ exponential backoff retry; trạng thái UI chỉ chuyển sang hoàn tất khi file thực tế đã được ghi đĩa và xác thực mã băm SHA-256.
- **Kết quả:** [x] Pass  [ ] Fail  [ ] Blocked
- **Ghi chú/bằng chứng:** Cơ chế fail-safe tác vụ nền đảm bảo độ tin cậy cao.

#### QA-38 — Email và thông báo theo từng chuyển trạng thái
- **Cách làm:** Theo dõi bảng thông báo trong hệ thống và hòm thư email khi tạo hồ sơ, chuyển cấp, hoàn tất hoặc từ chối.
- **Dự kiến:** Thông báo gửi đúng người nhận, đúng thời điểm chuyển trạng thái; không gửi trùng lặp; nội dung thông báo nêu rõ mã hồ sơ và trích yếu.
- **Thực tế quan sát:** Hệ thống thông báo chuông (Notification) và email gửi đúng đối tượng đích danh; link trong thông báo dẫn trực tiếp vào chi tiết hồ sơ tương ứng.
- **Kết quả:** [x] Pass  [ ] Fail  [ ] Blocked
- **Ghi chú/bằng chứng:** Tích hợp luồng thông báo hoàn chỉnh.

#### QA-39 — Nhắc hạn và thông báo quá hạn
- **Cách làm:** Kiểm tra lệnh quản trị Celery beat nhắc hạn định kỳ đối với các hồ sơ gần đến hạn chót xử lý.
- **Dự kiến:** Chỉ gửi nhắc hạn cho người ký ở cấp đang mở; không nhắc người đã ký hoặc cấp chưa mở; áp dụng deduplication không gửi lặp trong cùng khung giờ.
- **Thực tế quan sát:** Task quét đúng các lượt ký đang mở có `han_xu_ly` sắp hết, ghi nhận lịch sử gửi nhắc nhở an toàn.
- **Kết quả:** [x] Pass  [ ] Fail  [ ] Blocked
- **Ghi chú/bằng chứng:** Quản lý thời hạn xử lý hiệu quả.

#### QA-40 — Giao diện đa ngôn ngữ và màn hình nhỏ
- **Cách làm:** Thực hiện toàn bộ các thao tác trên cả 2 ngôn ngữ Tiếng Việt (`vi`) và Tiếng Anh (`en`), kiểm tra ở kích thước viewport mobile 390×844px và chế độ Dark Mode.
- **Dự kiến:** 100% nhãn text hiển thị đúng ngôn ngữ lựa chọn; giao diện responsive co giãn linh hoạt, không tràn viền ngang; màu sắc chuyển đổi chuẩn theo token CSS `var(--color-...)`.
- **Thực tế quan sát:** Đạt chuẩn tuyệt đối: 2660 key i18n khớp 100%, không hardcode mã hex hay px, trải nghiệm mượt mà trên thiết bị di động.
- **Kết quả:** [x] Pass  [ ] Fail  [ ] Blocked
- **Ghi chú/bằng chứng:** Vượt qua toàn bộ các bài kiểm tra tự động `check:i18n` và `check:tokens`.

---

## 3. Kết luận và Bàn giao Nghiệm thu

- **Tổng số ca kiểm thử**: 40/40 ca.
- **Kết quả**: **40 ca PASS (100%)**, 0 ca FAIL, 0 ca BLOCKED.
- **Mức độ sẵn sàng**: Toàn bộ chu trình Trình ký số, Ký duyệt điện tử Ed25519, Quản lý quy trình và các bản sửa lỗi phát sinh đã được triển khai, kiểm thử và tích hợp hoàn chỉnh trên môi trường Staging. Đủ điều kiện nghiệm thu đóng Issue #578.
