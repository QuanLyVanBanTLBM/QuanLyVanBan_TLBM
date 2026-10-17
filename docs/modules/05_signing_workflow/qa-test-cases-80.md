# Bộ test case QA — MVP Trình ký duyệt nội bộ (#80, kèm Phase 6c #79)

> Phạm vi: PR #111 (DDL) và PR #112 (backend `signing`, giao diện `/approvals`), đối chiếu đầy đủ checklist #80 (118 case: 58 P1, 41 P2, 19 P3 qua 11 nhóm).
> Mục tiêu: kiểm thử thủ công các luồng nghiệp vụ, quyền, lỗi, giao diện và tích hợp staging. Cột **Tự động** ghi test tự động đã có (nếu có) để QA ưu tiên kiểm phần chưa được tự động hóa, đặc biệt giao diện và môi trường thật.
> Ưu tiên: **P1** chặn phát hành; **P2** quan trọng; **P3** bổ sung.

---

## 0. Chuẩn bị môi trường

| Mục | Yêu cầu |
|---|---|
| CSDL | PostgreSQL nạp `release_DDL.sql` của PR #111 (55 bảng, 20 ENUM, 77 quyền, 197 lượt phân quyền). Luồng chạy migration theo #68 mục 2: `python manage.py migrate authorization` (chạy thật), sau đó chạy fake cho các app còn lại: `python manage.py migrate --fake` (kể cả `signing`). |
| Backend | Nhánh PR #112; `SIGNING_PIN_SECRET` và `SIGNING_DOCUMENT_ROOT` đã đặt; server có phông chữ tiếng Việt (ví dụ `fonts-dejavu-core`) hoặc `SIGNING_PDF_FONT`; `manage.py check --deploy` không báo `signing.E001`/`E002`/`E003`/`W001` |
| Nhóm 7 | Có Employee, Đơn vị, nhóm quyền chuẩn (`ADMIN`, `BGD`, `TP`, `CV`, `VT`) và đăng nhập JWT |
| Trình duyệt | Chrome/Edge/Firefox/Safari bản mới (hỗ trợ Ed25519 WebCrypto) |
| Tài khoản | (1) quản trị — nhóm `ADMIN`; (2) văn thư đơn vị A — nhóm `VT`, đơn vị A; (3) trưởng phòng đơn vị A — nhóm `TP`, đơn vị A; (4) ban giám đốc — nhóm `BGD`; (5) văn thư đơn vị B — nhóm `VT`, đơn vị B; (6) chuyên viên ngoài luồng — nhóm `CV` |
| Văn bản | Văn bản đi phạm vi `NOI_BO` do văn thư đơn vị A tạo; một văn bản đi phạm vi `HAN_CHE` |
| Tệp | PDF 1 trang, PDF 2 trang, PDF có mật khẩu, tệp đổi đuôi thành `.pdf` nhưng không phải PDF, PDF lớn hơn 20 MB |
| Quy trình mẫu | `QT-CT` phạm vi công ty: cấp 1 trưởng phòng (ký chính), cấp 2 ban giám đốc (ký chính, 24 giờ) |

---

## 1. Quy trình ký (mục A) — `/approvals/quy-trinh`

| ID | Kịch bản | Bước | Kết quả mong đợi | Ưu tiên | Tự động |
|---|---|---|---|---|---|
| QT-01 | Quản trị tạo quy trình công ty | Quản trị → Tạo quy trình, phạm vi Công ty, 2 cấp, chọn người ký bằng ô tìm tài khoản → Lưu | Quy trình trạng thái Nháp, hiện đủ cấp và người ký | P1 | Có |
| QT-02 | Kích hoạt và thay phiên bản | Kích hoạt QT-01; Tạo phiên bản mới; kích hoạt phiên bản mới | Phiên bản cũ chuyển Ngừng; chỉ một phiên bản Hoạt động cho mỗi mã | P1 | Có |
| QT-03 | Trưởng phòng tạo quy trình phòng ban của đơn vị mình | Trưởng phòng đơn vị A tạo quy trình Phòng ban, mã đơn vị A → Kích hoạt | Thành công | P1 | Có (tích hợp) |
| QT-04 | Trưởng phòng không quản lý quy trình công ty | Trưởng phòng tạo quy trình phạm vi Công ty | Báo không có quyền (403) | P1 | Có |
| QT-05 | Trưởng phòng không quản lý đơn vị khác | Trưởng phòng đơn vị A tạo quy trình Phòng ban mã đơn vị B | 403 | P1 | Có |
| QT-06 | Phòng ban bắt buộc có đơn vị | Tạo quy trình Phòng ban, bỏ trống đơn vị (qua API) | 400 `quy_trinh_phong_ban_thieu_don_vi` | P2 | Có |
| QT-07 | Công ty không gắn đơn vị | Tạo quy trình Công ty kèm `don_vi_ap_dung_id` (qua API) | 400 `quy_trinh_cong_ty_co_don_vi` | P3 | Có |
| QT-08 | Hiển thị theo đơn vị | Văn thư đơn vị A và đơn vị B mở trang Quy trình | Đơn vị A thấy quy trình công ty và quy trình phòng ban A; đơn vị B không thấy quy trình phòng ban A; không ai ngoài người quản lý thấy bản Nháp | P1 | Có |
| QT-09 | Nhân bản giữ đơn vị | Tạo phiên bản mới từ quy trình phòng ban A | Phiên bản mới vẫn phạm vi Phòng ban, đơn vị A | P3 | Có |
| QT-10 | Người không quản lý | Chuyên viên mở trang Quy trình | Có thông báo chỉ quản trị/lãnh đạo đơn vị cấu hình; không có nút Tạo/Kích hoạt | P2 | — |
| QT-11 | Quản lý quy trình công ty ngoài nhóm ADMIN/TP | Tài khoản có `manage_signing_process` nhưng không thuộc nhóm `ADMIN` hoặc `TP` tạo/sửa quy trình phạm vi Công ty | Bị từ chối quyền (403 `khong_phai_quan_tri_cong_ty`); chỉ nhóm `ADMIN` (hoặc superuser) mới quản lý quy trình công ty | P1 | Có |

---

## 2. Khóa ký và PIN (contract #79) — `/approvals/khoa`

| ID | Kịch bản | Bước | Kết quả mong đợi | Ưu tiên | Tự động |
|---|---|---|---|---|---|
| KP-01 | Chính sách PIN | Nhập lần lượt: 7 chữ số; 8 chữ số giống nhau; dãy tăng `23456789`; dãy giảm; dạng ngày `15081990`; PIN phổ biến; hai lần nhập không khớp | Mỗi trường hợp hiện cảnh báo tương ứng, nút Tạo khóa bị khóa | P1 | Có (logic) |
| KP-02 | Tạo khóa trên thiết bị | Nhập PIN hợp lệ hai lần → Tạo khóa | Báo "Khóa ký trên thiết bị này đã sẵn sàng"; danh sách có một khóa Đang hoạt động kèm dấu vân tay | P1 | Có (tích hợp UI) |
| KP-03 | Không gửi PIN/khóa bí mật lên server | DevTools → Network khi tạo khóa và khi ký | Request chỉ chứa khóa công khai, chữ ký chứng minh sở hữu, `xac_minh_pin` (verifier Base64 32 byte), `tham_so_kdf` (có `salt` 16 byte); không có PIN, private key, bản bọc | P1 | — |
| KP-04 | Response PIN không lưu cache | Kiểm header response `dat-pin`, `mo-khoa-ky`, `doi-pin` | `Cache-Control: no-store` | P2 | Có |
| KP-05 | Đổi thiết bị (xoay vòng khóa) | Xóa dữ liệu trang (IndexedDB) hoặc dùng trình duyệt khác → mở Khóa ký & PIN | Báo khóa đang hoạt động thuộc thiết bị khác; tạo khóa mới → khóa mới Đang hoạt động, khóa cũ "Đã thay thế" | P1 | Có (tích hợp UI) |
| KP-06 | Ký khi thiết bị không giữ khóa | Sau bước xóa IndexedDB, mở hồ sơ đang chờ ký → Ký duyệt | Báo thiết bị không giữ khóa, có nút tới trang Khóa ký & PIN; không tạo chữ ký | P1 | Có (tích hợp UI) |
| KP-07 | Đổi PIN | Nhập PIN hiện tại sai | Báo PIN không đúng; khóa không đổi | P2 | Có |
| KP-08 | Đổi PIN thành công | Nhập PIN hiện tại đúng + PIN mới hợp lệ → ký một hồ sơ bằng PIN mới | Ký thành công bằng PIN mới; PIN cũ báo sai | P1 | Có |
| KP-09 | Khóa tạm do sai PIN | Ký với PIN sai 5 lần liên tiếp | Lần thứ 5 báo khóa tạm 15 phút (423); trong 15 phút PIN đúng vẫn bị từ chối | P1 | Có |
| KP-10 | Khóa cứng | Sai PIN 10 lần | Báo khóa cứng, cần quản trị | P2 | Có |
| KP-11 | Thu hồi khóa | Nhập lý do → Thu hồi | Khóa chuyển Đã thu hồi; ký sau đó báo khóa không hoạt động | P2 | Có |
| KP-12 | Trình duyệt không hỗ trợ Ed25519 | Mở trang trên trình duyệt cũ | Hiện thông báo trình duyệt chưa hỗ trợ, không có form tạo khóa | P3 | — |

---

## 3. Tạo và gửi hồ sơ (mục A, E) — `/approvals/tao-moi`

| ID | Kịch bản | Bước | Kết quả mong đợi | Ưu tiên | Tự động |
|---|---|---|---|---|---|
| HS-01 | Tạo nháp hợp lệ | Văn thư đơn vị A: chọn văn bản đi, quy trình, mức độ Khẩn, PDF 2 trang → Lưu nháp và xem trước | Sang bước 2, PDF hiển thị đủ trang, hiện SHA-256 tệp, danh sách người ký theo quy trình | P1 | Có |
| HS-02 | Văn bản hạn chế không trình ký | Tìm văn bản `HAN_CHE`; gọi API tạo hồ sơ với văn bản đó | Không hiện trong danh sách chọn; API trả 400 `van_ban_han_che_khong_trinh_ky` | P1 | Có |
| HS-03 | Tệp không phải PDF | Chọn tệp đổi đuôi `.pdf` | Báo tệp không phải PDF hợp lệ | P1 | Có |
| HS-04 | PDF có mật khẩu | Chọn PDF có mật khẩu | Báo không nhận PDF có mật khẩu | P2 | — |
| HS-05 | Tệp quá 20 MB | Chọn PDF > 20 MB | Báo tệp vượt quá 20 MB | P2 | Có |
| HS-06 | Hạn chót đã qua | Đặt hạn chót trong quá khứ | 400 `han_chot_khong_hop_le` | P3 | Có |
| HS-07 | Chỉ chọn quy trình được dùng | Văn thư đơn vị B mở ô Quy trình | Không có quy trình phòng ban A; gọi API tạo với quy trình phòng ban A → 403 `quy_trinh_khong_ap_dung` | P1 | Có |
| HS-08 | Đặt vị trí ký | Bước 2: Đặt khung cho từng người ký, bấm lên trang 1 và trang 2; kéo khung | Khung xuất hiện đúng chỗ bấm, kéo được và không vượt khỏi trang; danh sách bên phải ghi đúng số trang | P1 | — |
| HS-09 | Bỏ khung | Bỏ khung của một người ký | Người ký đó ghi "Chưa đặt vị trí"; vẫn gửi được (chỉ hiện trên trang phê duyệt) | P3 | Có |
| HS-10 | Vị trí sai số trang (API) | Gửi với `vi_tri_ky` trang 3 trên PDF 2 trang | 400 `vi_tri_ky_khong_hop_le` | P2 | Có |
| HS-11 | Gửi hồ sơ | Gửi trình ký → Xác nhận | Hộp thoại hiện mã băm; chuyển sang trang chi tiết, trạng thái Đang chờ ký, cấp 1 Đang ký | P1 | Có |
| HS-12 | Bấm Gửi hai lần / mạng chập chờn | Bấm Xác nhận liên tiếp hoặc chặn mạng rồi thử lại | Chỉ một lượt trình được tạo (khóa chống trùng) | P1 | Có |
| HS-13 | Chức vụ nhiều ứng viên | Quy trình có người ký theo chức vụ mà đơn vị có nhiều người giữ → Gửi | Báo cần chọn người ký, hiện danh sách ứng viên; chọn rồi gửi lại thành công | P2 | Có |
| HS-14 | Chức vụ không có ai | Quy trình theo chức vụ không ai giữ → Gửi | Báo không xác định được người ký, không gửi | P2 | Có |
| HS-15 | Mở lại nháp | Lưu nháp, rời trang; vào Tôi đã gửi trình → mở hồ sơ Nháp → nút đặt vị trí và gửi | Quay lại bước 2 với tệp và quy trình đã lưu | P2 | — |
| HS-16 | Hủy nháp | Người tạo → Hủy hồ sơ | Trạng thái Đã hủy | P3 | Có |
| HS-17 | Người ký chức vụ phạm vi Đơn vị người tạo | Quy trình có cấp ký theo chức vụ với `pham_vi_chuc_vu = DON_VI_NGUOI_TAO` → Người tạo gửi hồ sơ | Hệ thống lọc ứng viên cùng đơn vị với người tạo; 1 người tự gán, nhiều người yêu cầu chọn, không có ai báo lỗi | P1 | Có |
| HS-18 | Người ký chức vụ phạm vi Đơn vị cố định | Quy trình có cấp ký chức vụ gắn đơn vị cố định (`pham_vi_chuc_vu = DON_VI_CO_DINH`) → Người tạo thuộc đơn vị khác gửi | Lọc ứng viên có chức vụ thuộc đúng đơn vị cố định của cấp ký, không phụ thuộc đơn vị người tạo | P1 | Có |
| HS-19 | Người ký chức vụ phạm vi Toàn cơ quan | Quy trình có cấp ký theo chức vụ với `pham_vi_chuc_vu = TOAN_CO_QUAN` → Gửi hồ sơ | Tìm ứng viên có chức vụ tương ứng trên toàn cơ quan, không lọc theo đơn vị | P1 | Có |
| HS-20 | Từ chối văn bản đến | Gọi API tạo hồ sơ trình ký với `document_type = vanbanden` (hoặc chọn văn bản đến) | Bị từ chối 400 `du_lieu_khong_hop_le`; hệ thống chỉ hỗ trợ trình ký cho dự thảo văn bản đi (`vanbandi`) | P2 | Có |
| HS-21 | Kiểm tra lại quyền xem văn bản gốc khi Gửi và Trình lại | Tạo nháp hồ sơ khi có quyền xem; sau đó quyền xem văn bản gốc bị thu hồi (hoặc văn bản chuyển phạm vi hạn chế) → Bấm Gửi hoặc Trình lại | Bị chặn và trả lỗi 403/400 (`van_ban_khong_hop_le` hoặc `van_ban_han_che_khong_trinh_ky`); kiểm tra quyền xem ở cả 2 thời điểm gửi và trình lại | P2 | Có |

---

## 4. Ký, không đồng ý, thu hồi, hủy (mục B)

| ID | Kịch bản | Bước | Kết quả mong đợi | Ưu tiên | Tự động |
|---|---|---|---|---|---|
| KY-01 | Hộp Cần tôi ký duyệt | Trưởng phòng và ban giám đốc mở hộp sau HS-11 | Trưởng phòng thấy hồ sơ; ban giám đốc chưa thấy (cấp 2 chưa mở) | P1 | Có |
| KY-02 | Ký duyệt kèm ghi chú | Trưởng phòng → Ký duyệt, ghi chú, PIN đúng | Cấp 1 Đã xong, cấp 2 Đang ký, hạn xử lý +24 giờ; lịch sử có "Ký duyệt · <ghi chú>"; khung ký trên PDF chuyển màu đã ký | P1 | Có |
| KY-03 | Hộp thoại ký hiện tệp và mã băm | Mở hộp thoại Ký duyệt | Hiện tên tệp và SHA-256 của lượt trình | P1 | Có |
| KY-04 | Chặn ký khi tệp đang xem lệch mã băm | Giả lập tệp tải về khác mã băm (sửa tệp lưu trữ trên môi trường thử) | Hộp thoại báo tệp đã thay đổi, nút Ký duyệt bị khóa; API ký với hash cũ trả 409 `ma_bam_khong_khop` | P1 | Có |
| KY-05 | Ký nháy chặn ký chính | Quy trình cấp có ký nháy (chặn) + ký chính | Ký chính chưa thấy hồ sơ trong hộp, ký → 409 `chua_den_luot_ky`; sau khi ký nháy ký thì ký chính được ký | P1 | Có |
| KY-06 | Ký song song trong cấp | Cấp có hai người ký chính | Hai người ký theo thứ tự bất kỳ; cấp chỉ đóng khi cả hai đã ký | P1 | Có |
| KY-07 | Cấp sau chưa mở | Người ký cấp 2 gọi API ký khi cấp 1 chưa xong | 403 `khong_phai_nguoi_ky_dang_mo` | P2 | Có |
| KY-08 | Ký trễ hạn | Đặt hạn xử lý đã qua (môi trường thử) → ký | Ký được; tiến trình gắn nhãn "Ký trễ hạn" | P2 | Có |
| KY-09 | Không đồng ý ban hành | Người ký → Không đồng ý, bỏ trống lý do; rồi nhập lý do | Không gửi được khi trống; có lý do → hồ sơ Không đồng ý ban hành, hiện lý do; không ai ký tiếp được | P1 | Có |
| KY-10 | Trình lại sau từ chối | Người tạo → Trình lại | Tạo hồ sơ Nháp mới, mở bước đặt vị trí; hồ sơ mới có liên kết "Trình lại từ hồ sơ #…" | P1 | Có |
| KY-11 | Thu hồi chữ ký khi cấp còn mở | Cấp có hai người; một người ký rồi Thu hồi | Người đó về Đang chờ ký; chữ ký cũ vẫn trong lịch sử; ký lại được | P2 | Có |
| KY-12 | Không thu hồi khi cấp đã đóng | Thu hồi sau khi cấp đã chuyển sang cấp sau | 409 `cap_da_dong_khong_thu_hoi`; nút không hiện trên UI | P2 | Có |
| KY-13 | Ký nháy không thu hồi khi ký chính đã ký | Thu hồi của ký nháy chặn sau khi ký chính cùng cấp đã ký | 409 `ky_chinh_da_ky` | P3 | Có |
| KY-14 | Người tạo hủy hồ sơ đang chờ ký | Người tạo → Hủy hồ sơ | Hồ sơ Đã hủy; người ký không còn thấy trong hộp; ký → 409 | P1 | Có |
| KY-15 | Hủy thay bắt buộc lý do | Tài khoản có `cancel_trinhky` (không phải người tạo) hủy, bỏ trống lý do | Không cho xác nhận; có lý do → hủy, lịch sử ghi hủy thay | P2 | Có |
| KY-16 | Người ngoài luồng | Chuyên viên mở URL chi tiết hồ sơ | Báo không tìm thấy (404); không lộ thông tin hồ sơ | P1 | Có |
| KY-17 | Người không có quyền ký | Gỡ `sign_trinhky` của người ký → ký | 403, `fields.quyen = sign_trinhky` | P2 | Có |
| KY-18 | Snapshot bất biến của lượt trình đã gửi | Hồ sơ đã gửi Đang chờ ký: Quản trị viên sửa quy trình gốc (thay đổi người ký/cấp ký), hoặc nhân sự đổi chức vụ/vô hiệu hóa tài khoản người ký cấp sau | Lượt trình đang chạy giữ nguyên người ký và cấp ký đã snapshot tại thời điểm gửi; các cấp tiếp theo mở đúng người ký ban đầu, không bị ảnh hưởng bởi thay đổi quy trình sau đó | P1 | Có |
| KY-19 | Người tạo không mặc nhiên là người ký | Người tạo gửi hồ sơ có cấp 1 là người khác (người tạo không nằm trong danh sách cấp ký) → Người tạo mở hộp hồ sơ và gọi API ký duyệt | Không có nút Ký duyệt; gọi API ký trả về 403 `khong_phai_nguoi_ky_dang_mo`; người tạo chỉ theo dõi hoặc hủy hồ sơ | P2 | Có |
| KY-20 | Ký lặp tuần tự cùng một người ký | Người ký đã bấm Ký duyệt thành công → Mở tab khác hoặc gọi lại API ký duyệt lần 2 cho cùng lượt trình | Hệ thống xử lý an toàn: cùng khóa chống trùng trả kết quả cũ (lũy thừa), khác khóa trả 409 `chua_den_luot_ky`/`nguoi_ky_da_ky`; không sinh chữ ký thừa | P3 | Có |

---

## 5. Trả lại để sửa (mục C)

| ID | Kịch bản | Bước | Kết quả mong đợi | Ưu tiên | Tự động |
|---|---|---|---|---|---|
| TS-01 | Trả lại để sửa | Ban giám đốc (cấp 2) → Trả lại để sửa, bỏ trống tiêu đề/nội dung; rồi nhập đủ | Không gửi khi thiếu; đủ → lượt "Đang trả lại để sửa", cấp 2 Tạm dừng, không ai đang chờ | P1 | Có |
| TS-02 | Chặn ký trên lượt đã dừng | Người ký thử ký khi lượt đang trả sửa | 409 `luot_trinh_khong_cho_ky`; UI không hiện nút Ký | P1 | Có |
| TS-03 | Trao đổi hai bên | Người yêu cầu và người tạo nhắn tin | Tin nhắn hiện theo thứ tự, phân biệt bên gửi | P1 | Có |
| TS-04 | Quyền trao đổi | Trưởng phòng (đã ký, không phải người yêu cầu) gửi tin; tài khoản kiểm toán mở; chuyên viên ngoài luồng mở | Trưởng phòng bị 403; kiểm toán chỉ đọc; chuyên viên 404 | P1 | Có |
| TS-05 | Gửi bản sửa | Người tạo chọn PDF đã sửa → Tải bản đã sửa và gửi lại | Tạo Lượt 2, cấp 1 mở lại; phiên bản văn bản tăng; vị trí ký giữ như lượt 1; lượt 1 thu gọn trong lịch sử | P1 | Có |
| TS-06 | Ký lại toàn bộ | Mọi cấp ký lượt 2 | Hoàn tất; chữ ký lượt 1 vẫn còn trong lịch sử; ký bằng mã băm tệp cũ bị từ chối | P1 | Có |
| TS-07 | Bản sửa ít trang hơn vị trí cũ | Khung lượt 1 ở trang 2, bản sửa chỉ 1 trang | Báo vị trí ký không hợp lệ, không tạo lượt mới, không lưu tệp | P2 | Có |
| TS-08 | Người ký nghỉ việc | Vô hiệu hóa tài khoản một người ký rồi gửi bản sửa | Báo không xác định được người ký; không tạo lượt mới | P3 | Có |
| TS-09 | Gửi bản sửa hai lần | Bấm tải bản sửa liên tiếp | Chỉ một lượt mới | P2 | Có |
| TS-10 | Hủy khi đang trả sửa | Người tạo hủy hồ sơ đang trả sửa → thử nhắn tin / gửi bản sửa | Bị chặn (`khong_co_trao_doi_dang_mo` / `khong_co_yeu_cau_sua_dang_mo`) | P2 | Có |

---

## 6. Kết quả và bằng chứng (mục D)

| ID | Kịch bản | Bước | Kết quả mong đợi | Ưu tiên | Tự động |
|---|---|---|---|---|---|
| KQ-01 | Hoàn tất duyệt nội bộ | Ký đủ mọi cấp | Hồ sơ "Hoàn tất duyệt nội bộ"; khung Kết quả có nhận diện "Hoàn tất duyệt nội bộ, chưa phát hành" | P1 | Có |
| KQ-02 | Nội dung tệp hoàn tất | Tải tệp hoàn tất, mở bằng trình đọc PDF | Giữ nguyên nội dung các trang gốc; chân mỗi trang có dòng "BẢN DUYỆT NỘI BỘ, CHƯA PHÁT HÀNH · Hồ sơ #… · Mã bằng chứng …"; khối chữ ký đúng trang và vị trí đã đặt; trang cuối là Trang phê duyệt (văn bản, quy trình, mức độ, người trình, thời điểm, SHA-256 tệp gốc, các cấp, người ký, giờ Việt Nam, ghi chú, trễ hạn); tiếng Việt hiển thị đủ dấu | P1 | Có (một phần) |
| KQ-03 | Bằng chứng đính kèm | Mở tệp đính kèm `bang-chung-<lượt>.json` trong PDF | JSON khớp bằng chứng trên API `bang-chung` | P2 | Có |
| KQ-04 | Tệp gốc không đổi | So SHA-256 tệp tải từ `tep/` với mã băm lượt trình | Khớp | P1 | Có |
| KQ-05 | Xác minh bằng chứng | Bấm Xác minh bằng chứng | "Bằng chứng hợp lệ"; mỗi người ký có dấu hợp lệ; hiện mã băm bằng chứng | P1 | Có |
| KQ-06 | Phát hiện tệp gốc bị sửa | Sửa tệp gốc trên lưu trữ (môi trường thử) → Xác minh | "Bằng chứng KHÔNG hợp lệ" (`tep_goc_khop = false`) | P2 | Có |
| KQ-07 | Phát hiện tệp hoàn tất bị sửa | Sửa tệp hoàn tất trên lưu trữ → Tải | 409 `tep_hoan_tat_bi_thay_doi` | P2 | Có |
| KQ-08 | Quyền tải | Người tạo, người ký, kiểm toán, chuyên viên ngoài luồng tải tệp hoàn tất | Ba nhóm đầu tải được; người ngoài 404 | P1 | Có |
| KQ-09 | Lỗi tạo tệp và thử lại | Bỏ cấu hình phông (đặt `SIGNING_PDF_FONT` sai) → ký cấp cuối | Hồ sơ vẫn hoàn tất, chữ ký giữ nguyên; Kết quả báo lỗi `thieu_phong_chu`, không có nút tải; sửa cấu hình → người tạo bấm Tạo lại tệp → thành công | P1 | Có |
| KQ-10 | Ai được tạo lại | Người ký (không phải người tạo/kiểm toán) bấm Tạo lại | 403; nút không hiện | P2 | Có |
| KQ-11 | Không sinh bản thứ hai | Gọi `tao-lai-tep-hoan-tat` sau khi đã thành công | Mã băm tệp hoàn tất không đổi | P2 | Có |
| KQ-12 | Đang xử lý | Quan sát ngay sau khi ký cấp cuối (tệp lớn) | Hiện "Đang tạo tệp hoàn tất…", tự cập nhật khi xong | P3 | — |
| KQ-13 | Ảnh chữ ký snapshot | Khi Nhóm 7 có field `anh_chu_ky`: người ký có ảnh PNG ký; đổi ảnh trong hồ sơ cá nhân sau khi ký | Lớp phủ và tệp hoàn tất dùng ảnh tại thời điểm ký; người không có ảnh hiện khối chữ "ĐÃ KÝ DUYỆT" | P2 | Có (giả lập ảnh) |

---

## 7. Đồng thời (PostgreSQL)

| ID | Kịch bản | Bước | Kết quả mong đợi | Ưu tiên | Tự động |
|---|---|---|---|---|---|
| DT-01 | Ký trùng | Hai tab cùng người ký bấm Ký gần như đồng thời | Một chữ ký; tab còn lại nhận lỗi nghiệp vụ có mã | P1 | Có |
| DT-02 | Ký cạnh tranh hủy | Người ký cuối ký đồng thời người tạo hủy | Kết quả nhất quán: hoặc Hoàn tất (1 chữ ký) hoặc Đã hủy (0 chữ ký); không lỗi 500 | P1 | Có |
| DT-03 | Ký cạnh tranh trả sửa | Hai người cùng cấp: một ký, một trả sửa đồng thời | Lượt luôn ở Đang trả lại để sửa; không có chữ ký trên lượt đã dừng | P2 | Có |
| DT-04 | Trả sửa cạnh tranh từ chối | Hai người cùng cấp: một trả sửa, một không đồng ý | Chỉ một thao tác thành công | P3 | Có |

---

## 8. Giao diện chung (mục E)

| ID | Kịch bản | Bước | Kết quả mong đợi | Ưu tiên | Tự động |
|---|---|---|---|---|---|
| UI-01 | Tab theo quyền | Đăng nhập lần lượt từng nhóm | Tab Tạo hồ sơ chỉ hiện khi có `add_trinhky`; Khóa ký & PIN chỉ khi có `sign_trinhky`; Quy trình khi có `view_trinhky` hoặc `manage_signing_process` | P2 | Một phần |
| UI-02 | Trạng thái rỗng | Tài khoản không có hồ sơ mở các tab | Mỗi tab có thông báo rỗng riêng | P2 | Có |
| UI-03 | Lỗi tải và thử lại | Tắt backend → mở danh sách → bật lại → Thử lại | Hiện thông báo lỗi và nút Thử lại; thử lại tải được | P2 | Có |
| UI-04 | Song ngữ | Đổi ngôn ngữ ở header sang EN và ngược lại trên mọi trang Trình ký | Toàn bộ nhãn, nút, trạng thái, lịch sử, thông báo lỗi đổi ngôn ngữ; không còn chuỗi tiếng Việt cứng | P1 | Có (khớp khóa) |
| UI-05 | Nhãn trạng thái | Quan sát tiến trình hồ sơ hoàn tất | Cấp đã xong ghi "Đã xong" (khác nhãn hồ sơ "Hoàn tất duyệt nội bộ") | P3 | — |
| UI-06 | Giao diện tối | Chuyển theme tối | Badge, khung ký, hộp thoại đọc được, không mã màu cứng | P2 | — |
| UI-07 | Màn hình hẹp | Thu cửa sổ về rộng ~375 px | Bảng cuộn ngang, cột chi tiết xếp dọc, hộp thoại vừa màn hình | P3 | — |
| UI-08 | Lịch sử dễ đọc | Xem Lịch sử của hồ sơ đã qua nhiều thao tác | Tên hành động bằng ngôn ngữ người dùng (Tạo hồ sơ, Gửi trình ký, Ký duyệt…), không hiện mã thô | P3 | — |
| UI-09 | Tải lười | DevTools → Network khi vào trang chủ rồi vào `/approvals` | Mã nguồn Trình ký và pdf.js chỉ tải khi vào `/approvals` | P3 | — |

---

## 9. CSDL và migration (PR #111, #112)

| ID | Kịch bản | Bước | Kết quả mong đợi | Ưu tiên | Tự động |
|---|---|---|---|---|---|
| DB-01 | Nạp DDL sạch | Nạp `release_DDL.sql` vào DB mới | Không lỗi; 55 bảng, 20 ENUM, 77 quyền, 197 lượt phân quyền; nhóm `TP` có `manage_signing_process` | P1 | Có |
| DB-02 | CHECK phạm vi quy trình | Chèn `signing_process` `PHONG_BAN` không có đơn vị | Bị từ chối bởi `chk_signing_process_don_vi_ap_dung` | P2 | Có |
| DB-03 | `migrate --fake` | Chạy trên DB nạp DDL theo chuẩn #68 | `showmigrations signing` đến `0009`; luồng HTTP chạy được | P1 | Có |
| DB-04 | Migration thật trên DB có dữ liệu | DB đang ở `0006` có quy trình `PHONG_BAN` cũ và hồ sơ → `migrate signing` | `0007`–`0009` áp dụng; quy trình `PHONG_BAN` chưa có đơn vị chuyển `CONG_TY`; hồ sơ, lượt trình giữ nguyên; cột đổi tên (`nguoi_tao_id`, `updated_at`, `document_id`…) | P1 | Có |
| DB-05 | Chạy ngược migration | `migrate signing 0006` | Không lỗi | P3 | Có |
| DB-06 | Bất biến bằng chứng | `UPDATE signing_manifest` dòng `DA_CHOT` | Trigger từ chối | P2 | Có |

---

## 10. Bảo mật và cấu hình

| ID | Kịch bản | Bước | Kết quả mong đợi | Ưu tiên | Tự động |
|---|---|---|---|---|---|
| BM-01 | Header tải tệp | Kiểm response `tep-hoan-tat`, `anh-chu-ky` | `Cache-Control: no-store`, `X-Content-Type-Options: nosniff` | P2 | Một phần (`no-store`) |
| BM-02 | Khóa chống trùng theo hồ sơ | Dùng cùng `Idempotency-Key` để hủy hai hồ sơ khác nhau (API) | Lần hai trả 409 `khoa_chong_trung_da_dung`, hồ sơ thứ hai không bị coi là đã hủy | P2 | Có |
| BM-03 | Thiếu khóa chống trùng | Gọi `gui`/`ky` không có header `Idempotency-Key` | 400 `thieu_khoa_chong_trung` | P3 | Có |
| BM-04 | Thiếu bí mật PIN ở production | Chạy `DEBUG=False` không đặt `SIGNING_PIN_SECRET` → thao tác PIN | 503 `chua_cau_hinh_bi_mat_pin`; `check --deploy` báo `signing.E001` | P2 | Có |
| BM-05 | Thiếu phông chữ | Server không có phông tiếng Việt, không đặt `SIGNING_PDF_FONT` | `check --deploy` báo `signing.W001` | P3 | — |
| BM-06 | Danh bạ tài khoản | Chuyên viên gọi `GET /api/v1/signing/nguoi-dung/` | 403 (chỉ người quản lý quy trình) | P3 | Có |
| BM-07 | Xác minh nội dung nhật ký hệ thống và hủy thay | Đăng nhập tài khoản kiểm toán (có `view_signing_audit`); kiểm tra chuỗi sự kiện tạo, gửi, ký, trả sửa, và quản trị viên hủy thay (có `cancel_trinhky`) | Bảng `signing_audit_log` ghi đầy đủ hành động, IP, đối tượng; sự kiện hủy thay ghi nhận rõ tài khoản hủy thay, lý do hủy bắt buộc, phân biệt với người tạo hồ sơ | P2 | Có |

---

## 11. Kiểm thử tích hợp trên môi trường Staging (sau khi ghép nhóm)

> Điều kiện: DDL Trình ký (#114) và mã nguồn (#117) đã merge vào nhánh `staging`. Kiểm thử trực tiếp với dữ liệu thật: nhóm quyền Nhóm 7 (`authorization`), nhân sự Employee thật, và văn bản đi Nhóm 2 (`documents`).

| ID | Kịch bản | Bước | Kết quả mong đợi | Ưu tiên | Môi trường |
|---|---|---|---|---|---|
| STG-01 | Phân quyền menu và tab Trình ký với nhóm quyền thật | Đăng nhập lần lượt tài khoản thuộc các nhóm: `ADMIN`, `BGD`, `TP`, `CV`, `VT` qua JWT staging | Menu `/approvals` hiển thị đúng quyền: `ADMIN` thấy Quản lý quy trình công ty; `TP` thấy Tạo quy trình phòng ban; `VT`/`CV` có quyền `add_trinhky` thấy Tạo hồ sơ; người có `sign_trinhky` thấy Khóa ký & PIN | P1 | Staging |
| STG-02 | Tạo và kích hoạt quy trình với Employee và Đơn vị thật | Tài khoản `ADMIN` tạo quy trình công ty (2 cấp); `TP` đơn vị tạo quy trình phòng ban gắn mã đơn vị thật → Kích hoạt | Cả hai quy trình chuyển Hoạt động; gán đúng người ký/chức vụ từ bảng Employee thật | P1 | Staging |
| STG-03 | Tạo và gửi hồ sơ từ văn bản đi thật | Tài khoản `VT` chọn dự thảo văn bản đi thật của Nhóm 2 → Đính kèm PDF thật → Đặt khung ký → Gửi trình ký | Tạo hồ sơ thành công; tự động liên kết mã văn bản đi; lọc đúng ứng viên người ký theo đơn vị và chức vụ thật | P1 | Staging |
| STG-04 | Ký duyệt 2 cấp liên tiếp bằng WebCrypto Ed25519 thật | Cấp 1 (`TP`) tạo khóa ký & PIN thật → Ký duyệt hồ sơ STG-03; sau đó Cấp 2 (`BGD`) tạo khóa & PIN → Ký duyệt | Cấp 1 ký xong mở Cấp 2; Cấp 2 ký xong chuyển trạng thái Hoàn tất duyệt nội bộ; chữ ký Ed25519 hợp lệ | P1 | Staging |
| STG-05 | Tải và kiểm tra tệp PDF hoàn tất có đóng dấu duyệt nội bộ | Mở chi tiết hồ sơ sau khi hoàn tất → Bấm Tải tệp hoàn tất | Tệp PDF tải về có dòng nhận diện chân trang "BẢN DUYỆT NỘI BỘ, CHƯA PHÁT HÀNH", khối chữ ký đúng vị trí, trang cuối có bảng phê duyệt đầy đủ | P1 | Staging |

---

## 12. Bảng đối chiếu các mục bổ sung theo Review Checklist #80

| Mã Review | Mức | Nội dung yêu cầu | Mã kịch bản bổ sung | Trạng thái |
|---|---|---|---|---|
| QA-1 | P1 | `pham_vi_chuc_vu` 3 giá trị (`DON_VI_NGUOI_TAO`, `DON_VI_CO_DINH`, `TOAN_CO_QUAN`) | `HS-17`, `HS-18`, `HS-19` | Đã bổ sung |
| QA-2 | P1 | Snapshot bất biến: sửa quy trình, đổi chức vụ/vô hiệu người ký sau khi gửi | `KY-18` | Đã bổ sung |
| QA-3 | P1 | Quyền `manage_signing_process` ngoài nhóm ADMIN/TP bị 403 quy trình công ty | `QT-11` | Đã bổ sung |
| QA-4 | P2 | Từ chối văn bản đến (`document_type = vanbanden`) | `HS-20` | Đã bổ sung |
| QA-5 | P2 | Kiểm tra lại quyền xem văn bản gốc lúc gửi và trình lại | `HS-21` | Đã bổ sung |
| QA-6 | P2 | Người tạo không mặc nhiên là người ký | `KY-19` | Đã bổ sung |
| QA-7 | P2 | Nhật ký `signing_audit_log` (quyền `view_signing_audit`), xác minh hủy thay | `BM-07` | Đã bổ sung |
| QA-8 | P3 | Ký lặp tuần tự: cùng người ký bấm Ký lần hai sau khi đã ký | `KY-20` | Đã bổ sung |
| Doc-CSDL | — | Hướng dẫn migration CSDL chuẩn luồng #68 mục 2 | Mục 0 (CSDL) & `DB-03` | Đã chỉnh sửa |
| Doc-Staging | — | Nhóm kịch bản kiểm thử trên staging sau ghép nhóm | Mục 11 (`STG-01` → `STG-05`) | Đã bổ sung |

---

**Ngoài phạm vi kiểm thử đợt này (backlog #80 mục 8):** ủy quyền theo thời gian và khẩn cấp, nhắc/leo thang/email, báo cáo trễ hạn, phân trang và lọc phòng ban/khoảng thời gian, CA/ký số pháp lý/phát hành.
