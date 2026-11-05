# Plan backend Trình ký — Nhóm 5

> **Phạm vi:** mọi người ký trong một cấp có cùng một vai trò (ký chính). Ký nháy và ủy quyền ký chưa có.

> Cập nhật 06/10/2026 theo [`danh-gia-nghiep-vu-va-de-xuat.md`](danh-gia-nghiep-vu-va-de-xuat.md): cấp ký luôn tuần tự (bỏ `kieu_ky`), từ chối là kết thúc, chức vụ tương đối theo đơn vị, ủy quyền theo thời gian kèm hình thức ký, leo thang quá hạn, tách khâu văn thư.
> Cập nhật 08/10/2026 theo #80: MVP là luồng duyệt nội bộ hoàn chỉnh, kết thúc ở **hoàn tất duyệt nội bộ, chưa phát hành**. CA, chứng thư số, `LegalSignerAdapter`, DocMDP, cấp số và phát hành pháp lý đã gỡ khỏi roadmap của #80 (mục 1.4). Văn bản mật đã bỏ nên không còn phụ thuộc pháp chế về phạm vi văn bản mật.

## 1. Mục tiêu và ranh giới

### 1.1. Mục tiêu

Xây dựng backend Django REST Framework cho nghiệp vụ trình ký văn bản:

- Người tạo chọn một quy trình đang `HOAT_DONG` để trình ký.
- Các cấp ký mở tuần tự theo `thu_tu`; nhiều người trong cùng một cấp ký song song.
- Người ký được xác định cụ thể; mọi người ký được chỉ định đều phải ký thì yêu cầu mới hoàn thành.

### 1.2. Phạm vi MVP

- Quản lý quy trình trình ký có phiên bản.
- Chọn quy trình khi tạo yêu cầu trình ký.
- Cấp ký tuần tự; song song là nhiều người ký trong cùng một cấp (không còn cách thức ký áp dụng cho toàn yêu cầu).
- Người ký cấu hình theo tài khoản hoặc theo chức vụ (tương đối theo đơn vị, mục 3.2); chốt snapshot người ký tại thời điểm gửi.
- Mọi người ký trong một cấp có cùng một vai trò: ký chính (`KY_CHINH`).
- Chữ ký số nội bộ Ed25519; backend ký bằng private key được lưu trong CSDL dưới dạng ciphertext AES-256-GCM.
- Khóa nội dung văn bản bằng phiên bản và mã băm SHA-256 tại thời điểm gửi.
- Phản hồi hai nhánh:
  - Lỗi nhỏ: ký duyệt kèm ghi chú (`ghi_chu_ky`), không chặn luồng.
  - Lỗi lớn: yêu cầu chỉnh sửa, mở luồng trao đổi hai chiều, sau khi chốt thì gửi lại toàn bộ bằng một lượt trình mới.
- Từ chối là kết thúc hồ sơ; trình lại bằng hồ sơ mới trỏ về hồ sơ gốc.
- Quá hạn không đóng luồng: hiển thị hạn xử lý, vẫn cho ký muộn và ghi nhận trễ hạn.
- Nhật ký trình ký chỉ ghi thêm; bằng chứng tổng hợp chốt khi hoàn tất.
- Lưu trữ tệp qua adapter; MVP dùng thư mục filesystem được mount, cấu hình bằng biến môi trường.
- Tệp PDF hoàn tất sinh một lần khi lượt trình `HOAN_THANH`: khối chữ ký theo vị trí, dòng nhận diện "bản duyệt nội bộ, chưa phát hành", trang phê duyệt, bằng chứng đính kèm; trạng thái tạo tệp và thử lại.
- Giao diện tối thiểu (#80 mục E).

### 1.3. Ngoài phạm vi MVP

- Triển khai production, Docker/Compose, cấu hình hạ tầng.
- Ký theo quorum hoặc "một trong nhiều người ký".
- Tự động từ chối hoặc tự động hủy khi quá hạn.
- Luồng tự do (người xử lý tự chọn người kế tiếp, không theo quy trình mẫu).
- Văn bản đến (`vanbanden`): bút phê/chỉ đạo thuộc luồng xử lý văn bản đến của Nhóm 2. Văn bản mật (`vanbanmat`): đã bỏ khỏi hệ thống (GVHD chốt); tài liệu nội bộ hạn chế (`pham_vi = 'HAN_CHE'`) không đi qua trình ký (mục 3.3).
- Nhiều tệp đính kèm/phụ lục trong một lượt trình (MVP: một lượt trình ứng với một tệp).
- Vai trò xem/góp ý không ký; thu hồi hoặc ban hành bản thay thế sau khi lượt trình `HOAN_THANH`.
- Quay lui về cấp trước trong cùng một lượt trình.
- Backlog sau MVP (#80 mục 8): ủy quyền theo thời gian và khẩn cấp kèm hình thức ký (KT., TL., TUQ.); nhắc trước/tại hạn, nhắc lặp, email, leo thang cấp trên, báo cáo trễ hạn nâng cao; thông báo qua Celery.

### 1.4. Ngoài phạm vi MVP: phát hành pháp lý

Theo #80 mục 8, MVP dùng chữ ký điện tử nội bộ Ed25519 và kết thúc ở **hoàn tất duyệt nội bộ, chưa phát hành**. Không yêu cầu CA, chứng thư số, `LegalSignerAdapter`, DocMDP hoặc khâu cấp số/phát hành pháp lý; các hạng mục này đã gỡ khỏi roadmap triển khai của #80. Chữ ký Ed25519 nội bộ không có giá trị pháp lý với bên ngoài; tệp hoàn tất ghi rõ là bản duyệt nội bộ.

## 2. Bằng chứng và giả định

- `[FACT]` Nhánh triển khai của Nhóm 5 là `5_signing_workflow`.
- `[FACT]` Nhánh triển khai của Nhóm 5 là `5_signing_workflow`; đã có Django project (`backend/config`) và app `signing` (Phase 1–5 của `plan-trien-khai-theo-phase.md`).
- `[FACT]` Cấu hình hiện tại: SQLite, `AUTH_USER_MODEL` mặc định (`auth.User`); app `accounts` chỉ có `StaffProfile` (OneToOne tới tài khoản). `requirements.txt` chưa có `psycopg`, `celery`, `redis`.
- `[ĐỀ XUẤT]` Stack đích: Django REST Framework, PostgreSQL, Celery, Redis.
- `[ĐỀ XUẤT]` Mọi FK người dùng trỏ tới `AUTH_USER_MODEL`; không tạo bảng người dùng mới.
- `[FACT]` CSDL chung (`csdl_qlvbtl_schema_final.sql`) dùng 3 bảng văn bản đến/đi/mật và kiểu enum `document_kind`; do đó Trình ký tham chiếu văn bản bằng `document_type` + `van_ban_id`, không FK.
- `[CHƯA XÁC MINH]` CSDL chung trỏ FK người dùng tới `accounts_employee`, trong khi Django hiện dùng `auth.User`; chờ chốt model người dùng (Phase 6).
- `[CHƯA XÁC MINH]` Tên model đơn vị/phòng ban, chức vụ và API lưu trữ tài liệu hiện có (Nhóm 7).

## 3. Quy tắc nghiệp vụ và bất biến

### 3.1. Quy trình

- Vòng đời: `NHAP -> HOAT_DONG -> NGUNG`.
- Chỉ quy trình `HOAT_DONG` được chọn khi tạo yêu cầu.
- Tài khoản có quyền `manage_signing_process` được tạo, kích hoạt, ngừng, nhân bản quy trình (Phase 6b). Người tạo bị gỡ quyền thì không thao tác được nữa.
- Quyền quản lý theo phạm vi: quy trình `CONG_TY` do quản trị (ADMIN) quản lý; quy trình `PHONG_BAN` gắn `don_vi_ap_dung` và do lãnh đạo đơn vị đó (có `manage_signing_process`) hoặc ADMIN quản lý. Đã triển khai (#80): `don_vi_ap_dung_id` + CHECK; lãnh đạo đơn vị = nhóm `TP` thuộc đơn vị đó (mã nhóm đọc qua `authorization.GroupInfo` của Nhóm 7); chưa có mã nhóm thì người có `manage_signing_process` được coi là quản trị như Phase 6b.
- Chỉ sửa trực tiếp quy trình ở trạng thái `NHAP`. Muốn thay đổi quy trình đã kích hoạt thì nhân bản thành phiên bản mới (`phien_ban` + 1, cùng `ma_quy_trinh`); phiên bản cũ giữ nguyên để tra cứu.
- Mỗi `ma_quy_trinh` chỉ có một phiên bản `HOAT_DONG`: kích hoạt phiên bản mới thì phiên bản đang hoạt động cùng mã chuyển `NGUNG` trong cùng transaction (ghi nhật ký `NGUNG_QUY_TRINH` kèm phiên bản thay thế). Yêu cầu đã tạo từ phiên bản cũ không bị ảnh hưởng.
- Phạm vi hiển thị: `pham_vi` = `PHONG_BAN` (chỉ người thuộc `don_vi_ap_dung` thấy khi tạo hồ sơ) hoặc `CONG_TY`.
- Không có cách thức ký ở mức quy trình hay yêu cầu: cấp luôn tuần tự, song song là nhiều người trong một cấp. Muốn mọi người ký cùng lúc thì cấu hình quy trình một cấp.
- Người tạo yêu cầu không được sửa danh sách người ký đã cấu hình trong quy trình, trừ việc chọn người cụ thể khi chức vụ có nhiều người (mục 3.2).

### 3.2. Người ký, cấp ký và vị trí đặt chữ ký

**Cấp ký và vai trò**

- Một cấp có thể có nhiều người ký; mọi người ký đều bắt buộc. Không có người ký tùy chọn, không có quorum.
- Mọi người ký của một cấp được mở cùng lúc và ký song song.
- `thu_tu` của cấp quyết định thứ tự mở cấp; `cap_ky` chỉ là số hiệu hiển thị.
- Chỉ cấp có `thu_tu` nhỏ nhất chưa hoàn thành được mở; cấp sau chỉ mở khi mọi người ký của cấp trước đã ký. Người trong cùng cấp ký song song.
- Yêu cầu hoàn thành khi cấp cuối hoàn thành.
- Người tạo không mặc nhiên là người ký; chỉ là người ký nếu có trong cấu hình quy trình.

**Người ký theo chức vụ**

- Chức vụ được hiểu theo `pham_vi_chuc_vu` của người ký cấu hình:
  - `DON_VI_NGUOI_TAO`: chức vụ trong đơn vị của người tạo hồ sơ (ví dụ "Trưởng phòng của người trình").
  - `DON_VI_CO_DINH`: chức vụ trong đơn vị `don_vi_id` của cấp.
  - `TOAN_CO_QUAN`: chức vụ cấp cơ quan (Giám đốc, Chánh văn phòng).
- Khi gửi: đúng một người phù hợp thì tự gán; nhiều người thì người tạo bắt buộc chọn qua `chon_nguoi_ky` trong payload `gui`, thiếu thì trả lỗi kèm danh sách ứng viên; không có ai thì không cho gửi.
- Quy trình lưu quy tắc; yêu cầu lưu snapshot tài khoản, tên hiển thị và tên chức vụ để lịch sử không đổi khi cơ cấu tổ chức thay đổi.
- Không có field số người ký; số người ký đếm từ các dòng người ký snapshot.

**Vị trí đặt chữ ký và Lazy Stamping**

- Khi tạo hồ sơ, người tạo kéo-thả trên bản xem trước để xác định vị trí ký cho từng người ký: `trang_ky`, `toa_do_x`, `toa_do_y`, `chieu_rong_khung`, `chieu_cao_khung`.
- Tọa độ lưu dạng chuẩn hóa: **đã chốt tỷ lệ % theo khung trang, gốc góc trên-trái** (#80), khung nằm trọn trong trang. Người tạo đặt khung khi gửi (`vi_tri_ky` theo người ký cấu hình), server kiểm số trang của tệp đã khóa và chụp vào dòng người ký của lượt trình; lượt mới sau trả sửa chép vị trí, được đặt lại.
- **Bất biến tệp gốc:** trong suốt luồng duyệt nội bộ, không sửa raw bytes của tệp PDF gốc. Mọi người ký của một lượt trình đều ký trên cùng một mã băm SHA-256 của tệp gốc đã khóa lúc gửi.
- Ảnh chữ ký và tọa độ chỉ là metadata trong CSDL:
  - Ảnh chữ ký gốc nằm ở hồ sơ cá nhân (do Nhóm 7 cung cấp, mục 3.4).
  - Tọa độ nằm ở `signing_request_step_signer`.
  - Tại thời điểm ký, backend chốt snapshot ảnh chữ ký vào bản ghi chữ ký (`vi_tri_anh_chu_ky`, `ma_bam_anh_chu_ky`). Nếu người dùng đổi ảnh trong hồ sơ trước khi lượt trình hoàn thành, tệp hoàn tất vẫn dùng đúng ảnh tại lúc ký.
- Giao diện (React PDF viewer) hiển thị ảnh chữ ký như một lớp phủ CSS/Canvas đè lên bản xem trước theo tọa độ; không tạo tệp trung gian.
- **Phẳng hóa (Stamping & Flattening):** chỉ khi lượt trình chuyển `HOAN_THANH`, tác vụ nền đọc tệp gốc, lấy snapshot ảnh và tọa độ của toàn bộ chữ ký hiện hành, dán một lần và sinh tệp PDF hoàn tất. Vị trí và mã băm tệp này lưu tại `signing_attempt.vi_tri_tep_hoan_tat`, `signing_attempt.ma_bam_tep_hoan_tat`.
- Không sinh tệp theo từng người ký.
- Tệp hoàn tất của giai đoạn nội bộ chỉ chứa ảnh chữ ký, không nhúng chữ ký số, nên không verify được bằng phần mềm đọc PDF. Phải có dòng nhận diện "bản duyệt nội bộ, chưa phát hành". Đã làm ở lõi Phase 10 (#80): dòng nhận diện ở chân mọi trang, trang phê duyệt và bằng chứng JSON đính kèm; MVP chưa dán ảnh chữ ký vì chưa có nguồn ảnh (Nhóm 7 chốt cột `anh_chu_ky` để sau MVP, #67 mục 2).
- Đã triển khai (#80): snapshot ảnh lúc ký qua `tich_hop.to_chuc.anh_chu_ky` (field `anh_chu_ky` của Nhóm 7 khi có); tệp hoàn tất dán ảnh vào khung, chưa có ảnh thì in khối chữ "ĐÃ KÝ DUYỆT" kèm họ tên, chức vụ, thời điểm ký; mã băm ảnh ghi trong bằng chứng và được kiểm khi dựng tệp.

### 3.3. Yêu cầu, lượt trình và nội dung văn bản

- Một `signing_request` có thể có nhiều `signing_attempt`. Mỗi lần gửi hoặc gửi lại tạo một lượt trình mới; không ghi đè lượt cũ.
- `phien_ban_van_ban`, `vi_tri_luu_tep`, `ma_bam_tai_lieu` được khóa trên lượt trình tại thời điểm gửi. Mọi cấp ký trong một lượt trình ký chung một bản nội dung.
- **Nguồn sự thật của mã băm:** `signing_attempt.ma_bam_tai_lieu`. Ba field tương ứng trên `signing_request` là bản sao của lượt trình hiện hành (phục vụ danh sách/lọc), chỉ được cập nhật trong cùng transaction tạo lượt trình mới; không có API nào sửa trực tiếp.
- Lượt trình hiện hành là lượt có `so_luot` lớn nhất của yêu cầu; không cần thêm con trỏ.
- Nội dung thay đổi thì mọi chữ ký cũ chỉ còn là bằng chứng của lượt cũ; lượt mới ký lại từ đầu.

**Xử lý phản hồi (hai nhánh)**

- **Nhánh 1 — Lỗi nhỏ, không chặn luồng:**
  - Người ký vẫn ký duyệt và đính kèm `ghi_chu_ky`.
  - Người ký chuyển `DA_KY`, luồng tiếp tục bình thường.
  - Ghi chú lưu trên bản ghi chữ ký và hiển thị cảnh báo cho người tạo và các cấp sau.
- **Nhánh 2 — Lỗi lớn, chặn luồng:**
  - Người ký thực hiện `yeu_cau_sua` kèm lý do bắt buộc.
  - Người ký đó và lượt trình chuyển `YEU_CAU_SUA`; các cấp đang mở chuyển `TAM_DUNG`; không ai ký tiếp được trên lượt này.
  - Hệ thống mở một `signing_change_thread` (`DANG_MO`); người tạo và người yêu cầu trao đổi qua `signing_change_message`.
  - Khi đã thống nhất: người tạo tải bản văn bản mới (phiên bản mới, mã băm mới), thread chuyển `DA_GIAI_QUYET`, hệ thống tạo lượt trình mới (`luot_truoc` trỏ về lượt cũ) để toàn bộ các cấp ký lại.
  - Lượt cũ giữ nguyên trạng thái `YEU_CAU_SUA` làm lịch sử; không chuyển sang `HUY` để không mất ngữ cảnh lý do.
- **Từ chối = không đồng ý ban hành:** `tu_choi` bắt buộc lý do, ghi chú tùy chọn. Lượt trình và yêu cầu chuyển `TU_CHOI`, đây là trạng thái kết thúc của yêu cầu. Giao diện phân biệt "Trả lại để sửa" (`yeu_cau_sua`) và "Không đồng ý ban hành" (`tu_choi`).
- Muốn trình lại sau từ chối: thao tác `trinh-lai` tạo **yêu cầu mới** (sao chép văn bản, quy trình đang hoạt động, vị trí ký), `ho_so_goc` trỏ về yêu cầu bị từ chối. Không mở lại yêu cầu đã `TU_CHOI`.
- Người tạo được hủy trước khi hoàn thành; quản trị viên được hủy thay (override) nhưng bắt buộc lý do và ghi nhật ký.
- `[CHƯA CHỐT]` Xử lý khi phát hiện sai sau khi lượt trình `HOAN_THANH` (hủy, thu hồi, ban hành bản thay thế): MVP chưa hỗ trợ, xem mục 12.

**Văn bản hạn chế không đi qua trình ký**

GVHD đã chốt bỏ văn bản mật hành chính. Tài liệu nội bộ hạn chế là văn bản có `pham_vi = 'HAN_CHE'` (DDL `ddl_base_v0`, PR #81); loại này là văn bản gửi đi, người tạo chọn người xem và hệ thống lưu log xem (bảng `documents_access_log`, thuộc Nhóm 2, #82); không có bước ký và không đi qua trình ký. Trình ký chỉ xử lý văn bản thường (`pham_vi = 'NOI_BO'`) và vận hành độc lập với quy tắc xem của văn bản hạn chế (#82, #83). Giữ nguyên luồng ký chính Ed25519, PIN, mã băm, nhật ký chỉ ghi thêm và bằng chứng tổng hợp.

- Khi tạo hồ sơ hoặc phiếu trình ký (Phase 7), API từ chối văn bản gốc có `pham_vi = 'HAN_CHE'`, kể cả ở đường tạo từ quy trình mẫu. DDL không cho đổi `pham_vi` sau khi tạo nên không thể vòng qua luật này.
- Trợ lý AI không đọc bảng `signing_*` (DDL không cấp quyền cho `qlvb_readonly`).
- `[CHƯA CHỐT]` Luật từ chối chỉ thực thi được sau khi #82 có trường `pham_vi` trên model văn bản.

### 3.4. Khóa ký, chữ ký và ảnh chữ ký cá nhân

**Ảnh chữ ký cá nhân**

- Mỗi người dùng có một ảnh chữ ký PNG nền trong suốt, tối đa 2MB, lưu trong hồ sơ cá nhân.
- Hồ sơ cá nhân thuộc Nhóm 7 (sheet CBNV, field `anh_chu_ky`). Module Trình ký chỉ đọc ảnh qua contract do Nhóm 7 cung cấp, không tự định nghĩa API hồ sơ.
- `[CHƯA CHỐT]` Kích thước pixel chuẩn (ví dụ `300 x 150 px`, tỷ lệ 2:1), chốt khi làm stamping.

**Khóa ký**

- Private key chỉ được gửi cùng thao tác đăng ký/đặt PIN qua HTTPS; server lưu private key dạng ciphertext AES-256-GCM trong `signing_key_unlock`. Không trả private key/ciphertext qua API và không log hoặc đưa vào bằng chứng tổng hợp.
- Đăng ký khóa công khai Ed25519 qua proof-of-possession:
  - Client ký challenge bằng private key; server verify rồi gán `thoi_diem_xac_minh_so_huu` (`xac-minh`). Chuyển khóa từ `CHO_KICH_HOAT` sang `HOAT_DONG` là bước riêng (`kich-hoat`), chỉ cho khóa đã xác minh sở hữu.
  - `[FACT]` Triển khai hiện tại: challenge là token ký bằng `SECRET_KEY` (`django.core.signing`) chứa id khóa, dấu vân tay khóa và nonce ngẫu nhiên 16 byte; hạn dùng 10 phút; client gửi lại cả `thach_thuc` lẫn `chu_ky_so` ở `xac-minh`. Challenge dùng một lần (#507): sau khi chữ ký hợp lệ, nonce được ghi vào `signing_challenge_da_dung` (UNIQUE `nguoi_dung_id`, `nonce`) bằng `INSERT ... ON CONFLICT DO NOTHING` trong cùng giao dịch với bước xác minh, nên hai request đồng thời cùng challenge chỉ một request thành công; dùng lại trả HTTP 409, mã `thach_thuc_da_dung`. Chữ ký sai không làm mất challenge (giao dịch hoàn tác). Bản ghi hết hạn được xóa khi ghi bản ghi mới, không cần tác vụ định kỳ. `xac-minh` chỉ do chủ khóa đã xác thực thực hiện. Tài khoản không hoạt động (`is_active = false`) không đăng ký, xác minh, kích hoạt khóa hay ký.
  - `[ĐỀ XUẤT]` Khi có Redis: có thể chuyển nơi lưu nonce đã dùng sang Redis, giữ nguyên API.
- Mỗi người dùng tối đa một khóa `HOAT_DONG` tại một thời điểm, không phân biệt thuật toán.
- Xoay vòng khóa: khóa cũ chuyển `DA_XOAY_VONG`, `khoa_thay_the` trỏ khóa mới, có ghi nhật ký. Khóa cũ được giữ để xác minh chữ ký lịch sử.
- `HET_HAN`: áp dụng khi khóa có `ngay_het_han` và thời điểm hiện tại đã qua; `ngay_het_han` rỗng nghĩa là không hết hạn. Không dùng tác vụ định kỳ: dịch vụ khóa chuyển trạng thái và ghi nhật ký `HET_HAN_KHOA` khi chủ khóa đọc danh sách khóa hoặc ký (#488), nên khóa quá hạn bị từ chối ký và trạng thái vẫn được lưu.
- `THU_HOI`: thu hồi thủ công, gán `ngay_thu_hoi`, có ghi nhật ký.

**Bảo vệ khóa bằng PIN và ký phía máy chủ (#447 phân vùng 1)**

> `[QUYẾT ĐỊNH]` #447 partition 1: private key được mã hóa trong CSDL bằng khóa dẫn xuất từ pepper ổn định ngoài CSDL + salt, độc lập với PIN; PIN 6 chữ số nhập mỗi lần ký và được xác minh bằng Argon2id. Server ký. Mỗi ngày tối đa 15 lần PIN sai, sau đó trả 429 đến hết ngày. Người dùng phải đăng ký khóa mới sau rollout; public key, chữ ký, audit và bằng chứng cũ được giữ để xác minh lịch sử. Private key cũ không import.

- Mục tiêu: chặn việc ký trên thiết bị đã đăng nhập mà không có PIN đúng; ciphertext DB không giải mã được nếu không có pepper. Tradeoff: khi CSDL và pepper cùng bị lộ, private key có thể giải mã mà không cần PIN.
- Sự kiện nhật ký: `DAT_PIN`, `DOI_PIN`, `MO_KHOA_KY`, `PIN_SAI`, `PIN_HET_LUOT` (đủ 15 lần sai trong ngày).
- Tham số Argon2id: `m=64 MiB, t=3, p=1`, phiên bản 19; server chỉ chấp nhận đúng bộ tham số này để tránh KDF yếu hoặc request gây cạn tài nguyên. Dùng Argon2id (RFC 9106), không dùng PBKDF2/bcrypt.
- **Contract salt, verifier và khóa mã hóa (#447 phân vùng 1):** client sinh salt ngẫu nhiên 16 byte bằng CSPRNG (`crypto.getRandomValues`); mỗi khóa và mỗi lần đổi PIN dùng salt mới. `ma_bam_xac_minh_pin` lưu Argon2id v19 của HMAC-SHA256(pepper, domain || PIN) với `m=64 MiB, t=3, p=1`. AES key được dẫn xuất độc lập bằng HKDF-SHA256(`SIGNING_KEY_PEPPER`, salt, info riêng), rồi mã hóa private key PKCS#8 Ed25519 bằng AES-256-GCM. `signing_key_unlock` lưu verifier, ciphertext Base64(nonce || ciphertext || tag) và `tham_so_kdf`; không lưu PIN hoặc khóa dẫn xuất. Trước mỗi chữ ký server xác minh verifier, mở ciphertext trong bộ nhớ và kiểm tra private key khớp public key.
- **Pepper và tradeoff lưu trữ:** `SIGNING_KEY_PEPPER` là secret riêng, ngoài CSDL, bắt buộc và khác `SECRET_KEY`/`SIGNING_PIN_SECRET` khi `DEBUG=False`; `check --deploy` báo `signing.E005/E006`, request thiếu/sai cấu hình trả 503. Pepper phải được giữ ổn định và đưa vào backup/restore secret handling vì mất pepper làm private key hiện hành không thể giải mã. Do pepper giải mã ciphertext độc lập PIN, người có cả bản sao CSDL lẫn pepper có thể đọc private key mà không cần PIN; PIN là rào chắn xác thực ký trực tuyến, không phải lớp mã hóa private key. `SIGNING_PIN_SECRET` vẫn dùng riêng cho mã email reset/MFA.
- **Kênh truyền:** raw PIN, private key lúc đăng ký, PIN đổi/recovery và PIN lúc ký chỉ được gửi qua HTTPS. Endpoint đặt/đổi/recovery PIN và ký từ chối HTTP khi `DEBUG=False` (`https_bat_buoc`). Khi TLS kết thúc ở Nginx, chỉ bật `DJANGO_SECURE_PROXY_SSL_HEADER=true` nếu Nginx luôn ghi đè `X-Forwarded-Proto`; HTTPS cần sẵn sàng trước rollout.
- Chính sách PIN: đúng 6 chữ số; client chặn PIN phổ biến, dãy tăng/giảm, lặp một chữ số và dạng ngày. Server khóa theo bản ghi khóa sau 15 lần sai trong ngày, ghi audit; PIN đúng đặt bộ đếm về 0.
- **Reset rollout (#447):** migration thu hồi khóa `HOAT_DONG`/`CHO_KICH_HOAT` và xóa unlock rows cũ; người dùng đăng ký khóa server-side mới. Giữ public key cũ, chữ ký, audit và bằng chứng để xác minh lịch sử. Private key cũ không import; migration reset một chiều vì verifier/mảnh cũ không thể khôi phục.
- Mất PIN: chủ khóa dùng mã xác thực email để đặt PIN mới trên chính khóa đang hoạt động; giữ nguyên key id, public key, trạng thái và ciphertext. Quản trị viên có thể thu hồi khẩn cấp khóa, nhưng đó là thao tác vô hiệu hóa riêng; sau thu hồi phải đăng ký khóa mới. Chữ ký/audit/bằng chứng lịch sử vẫn được giữ.
- Đặt lại PIN tự phục vụ (#478): `POST /signing/dat-lai-pin/yeu-cau/` gửi mã 6 chữ số tới email tài khoản (băm lưu ở `signing_pin_reset_code`, hiệu lực 10 phút, hai lần gửi cách nhau tối thiểu 2 phút, lần gửi chỉ ghi nhận khi email gửi thành công); dòng mã lưu `khoa_id` của khóa đang hoạt động lúc gửi. Migration hết hạn mã cũ chưa gắn khóa. `POST /signing/dat-lai-pin/xac-nhan/` nhận `{ma, pin_moi}` qua HTTPS và chỉ cập nhật verifier nếu chính mã đó còn gắn đúng khóa đang hoạt động. Không thu hồi khóa, xóa/ghi lại ciphertext hoặc đổi public key; mã không thể chuyển sang khóa mới nếu key gốc bị thu hồi/xoay vòng. Endpoint không cần quyền ký; sai 5 lần thì hủy mã. Nhật ký thêm `DAT_LAI_PIN_QUA_EMAIL`; mã sai/đúng tiếp tục ghi `MA_DAT_LAI_PIN_SAI`/`XAC_NHAN_MA_DAT_LAI_PIN`. `[ĐỀ XUẤT]` Khi có Redis cho MFA có thể chuyển nơi lưu mã sang Redis, giữ nguyên API.
- MFA qua email khi ký (#509, phân vùng 2 của #447): **tắt mặc định**, bật bằng biến môi trường `SIGNING_MFA_EMAIL_ENABLED=true` (đọc trong `services/mfa_ky.py`, không nằm trong `settings.py`). Phương án lưu: **PostgreSQL** (bảng `signing_mfa_otp`), không dùng Redis; mức bảo mật bình thường theo đề xuất ghi tại #447: mã 6 chữ số lưu HMAC (khóa dẫn xuất từ `SIGNING_PIN_SECRET`, gắn với tài khoản), hiệu lực 10 phút, hai lần gửi cách nhau tối thiểu 2 phút (HTTP 429, `gui_ma_qua_nhanh`), sai 5 lần thì hủy mã (`mfa_vuot_gioi_han_nhap`); chưa có giới hạn 20 lần mỗi ngày và 10 lần trong 30 phút của phương án Redis. `POST /signing/mfa/yeu-cau/` gửi mã, `POST /signing/mfa/xac-minh/` nhận `{ma}`; kiểm tra và đánh dấu đã dùng trong một giao dịch khóa dòng tài khoản nên mã chỉ dùng một lần. Mã đúng gắn dòng với access token hiện tại (`jti`, hạn `exp`): xác thực có hiệu lực đến khi token hết hạn, đổi token (đăng nhập lại, làm mới) cần xác thực lại. Khi cờ bật, `hanh_dong_ky.ky` từ chối ký nếu phiên chưa xác thực (HTTP 403, `mfa_chua_xac_thuc`), nên gọi thẳng API ký không vượt qua được; từ chối và thu hồi chữ ký không yêu cầu MFA. `GET /signing/toi/` trả `mfa_ky` (`bat`, `da_xac_thuc`, `het_han`) để giao diện chỉ hiện bước nhập mã khi cần. Bản ghi cũ hơn 1 giờ và không còn gắn phiên hiệu lực được xóa khi gửi mã mới (không cần tác vụ định kỳ). Mã không ghi vào nhật ký, log hay phản hồi lỗi; nhật ký chỉ có sự kiện `YEU_CAU_MA_MFA_KY`, `MA_MFA_KY_SAI`, `XAC_MINH_MFA_KY`. **Điều kiện bật:** máy chủ phải gửi được email thật (đặt `EMAIL_HOST`, thuộc #448); mailer console/dummy/filebased hoặc thiếu `EMAIL_HOST` thì yêu cầu mã trả HTTP 503 `mfa_email_khong_kha_dung` và không gửi, để mã không lọt ra log. Tài khoản không có email: HTTP 400 `tai_khoan_chua_co_email`. `[ĐỀ XUẤT]` Khi có Redis (#448) có thể chuyển sang kho Redis và thêm giới hạn theo ngày, giữ nguyên API.
- Đăng ký khóa: trình duyệt tạo cặp Ed25519 mới, gửi private key PKCS#8 cùng PIN qua HTTPS khi đặt PIN; API không trả private key/ciphertext. Không có API mở khóa trả private key, IndexedDB wrapper hoặc file `.tlbmkey`. Khi ký, client gửi PIN + hash; backend giải mã trong bộ nhớ, ký raw SHA-256 digest rồi xác minh chữ ký bằng public key trước khi ghi nhận.
- MVP: một khóa `HOAT_DONG` trên một người dùng. Đổi thiết bị là tạo khóa mới và `xoay-vong`. Mô hình tin cậy chuyển từ zero-knowledge sang máy chủ ứng dụng có thể dùng private key khi ký; bảo vệ phụ thuộc HTTPS, secret pepper và kiểm soát máy chủ.
- Giới hạn (`[FACT]` về phạm vi bảo vệ): PIN không chống XSS/malware ghi phím lúc nhập; không nâng giá trị pháp lý của chữ ký nội bộ. Giảm XSS bằng CSP chặt, không script bên thứ ba, màn hình ký hiển thị tên tệp và mã băm để người ký xác nhận.

**Chữ ký**

- Ký trên raw bytes của SHA-256 digest, không ký chuỗi hex.
- Backend verify chữ ký đồng bộ trước khi chuyển người ký sang `DA_KY`. Chữ ký không hợp lệ bị từ chối ở API và không tạo bản ghi.
- `trang_thai_xac_minh`: bản ghi được tạo với `HOP_LE` và `thoi_diem_xac_minh`. `CHUA_XAC_MINH` và `KHONG_HOP_LE` chỉ dùng cho tác vụ xác minh lại về sau (ví dụ kiểm toán lại toàn bộ lượt trình).
- Bản ghi chữ ký là bằng chứng bất biến: không `UPDATE` nội dung, không `DELETE`.
- Mỗi người ký tối đa một chữ ký hiện hành, xác định qua `signing_request_step_signer.chu_ky_hien_hanh`.
- **Thu hồi:**
  - Chỉ khi cấp của người ký còn `DANG_KY` (chưa đóng) và lượt trình chưa hoàn thành.
  - Thu hồi ghi thành sự kiện nhật ký tham chiếu chữ ký bị thu hồi; `chu_ky_hien_hanh` về rỗng, người ký về `CHO_KY`; ký lại tạo bản ghi chữ ký mới. Chữ ký cũ giữ nguyên.
- Không cho thu hồi sau khi cấp đã đóng và luồng đã sang cấp sau; muốn sửa thì đi qua yêu cầu chỉnh sửa và lượt trình mới.

### 3.5. Hạn xử lý

**Hạn xử lý**

- Người tạo nhập hạn chót chung `han_chot`.
- Quy trình có thể cấu hình `so_gio_xu_ly` theo cấp. Nếu cấp không có: chia đều thời gian còn lại đến `han_chot` cho các cấp chưa mở theo giờ lịch.
- Lưu thời gian UTC, hiển thị theo `Asia/Ho_Chi_Minh`.
- Sau khi gửi không cho đổi hạn; quản trị viên đổi thay phải ghi nhật ký.

**Quá hạn**

- Không có trạng thái quá hạn; chạm hạn không tự hủy, không tự từ chối, không tự đổi người ký.
- Người ký vẫn ký được nếu các điều kiện khác hợp lệ. Chữ ký muộn được gắn `ky_tre_han = true` và `so_giay_tre` (so với `han_xu_ly` của cấp) phục vụ kiểm toán SLA/KPI.
- Lịch nhắc và leo thang mặc định (quy trình có thể thay bằng `cau_hinh_nhac_han`):
  - Trước `han_xu_ly` 24 giờ: nhắc người ký.
  - Tại `han_xu_ly`: nhắc người ký và người tạo.
  - Quá hạn mỗi 24 giờ: nhắc lặp người ký.
  - Quá hạn 48 giờ: leo thang cho cấp trên trực tiếp của người ký (theo cơ cấu Nhóm 7) và người tạo.
- Báo cáo trễ hạn theo người/đơn vị (số hồ sơ đang quá hạn, thời gian xử lý trung bình) đọc từ `ky_tre_han`, `so_giay_tre`, `han_xu_ly`.

**Ủy quyền ký (backlog sau MVP)**: chưa có. Trước khi bổ sung cần chốt người nhận hợp lệ theo chức danh (Nhóm 7), phạm vi, thời hạn và thể thức khối chữ ký.

## 4. Kiến trúc backend

### 4.1. Thành phần

- **App `signing`:** model, domain service, chuyển trạng thái, phân quyền, API.
- **Contract văn bản:** chỉ tham chiếu `document_type` + `van_ban_id`, `phien_ban_van_ban`, `vi_tri_luu_tep`, `ma_bam_tai_lieu`; không phụ thuộc đường dẫn tuyệt đối.
- **`DocumentStorageAdapter`:** interface đọc metadata/bytes theo vị trí lưu. MVP dùng filesystem mount cấu hình qua biến môi trường; có thể thêm API/SFTP mà không đổi nghiệp vụ ký.
- **`PdfStampingService`:** tác vụ nền phẳng hóa PDF khi lượt trình `HOAN_THANH` (mục 3.2).
- **`LegalSignerAdapter`:** ngoài MVP, đã gỡ khỏi roadmap #80 (mục 1.4).
- **PostgreSQL:** dữ liệu nghiệp vụ, ràng buộc unique/check, transaction, khóa dòng.
- **Redis:** broker Celery, khóa ngắn hạn nếu cần; challenge khóa ký đã ép dùng một lần bằng PostgreSQL (mục 3.4), không phụ thuộc Redis.
- **Celery worker:** gửi thông báo, nhắc hạn, escalation, phẳng hóa PDF, chốt bằng chứng tổng hợp. Task chỉ nhận ID, retry có backoff và jitter, idempotent.
- **Outbox:** dùng chính bảng `signing_notification`. Bản ghi `CHO_GUI` được tạo trong cùng transaction nghiệp vụ; sau commit (`transaction.on_commit`) mới đẩy task gửi; một tác vụ định kỳ quét các bản ghi `CHO_GUI` bị sót. Không tạo bảng outbox riêng trong MVP.
- Đã triển khai (`services/thong_bao.py`): sự kiện `CAN_KY` (người ký vừa được mở), `HOAN_THANH`, `TU_CHOI`, `YEU_CAU_SUA`, `HUY` tạo bản ghi kênh `IN_APP` (hiện ở tab Thông báo, API `GET /thong-bao/`) và `EMAIL` (khi người nhận có email) trong cùng transaction, `khoa_chong_gui_trung` chống trùng; email gửi sau commit, lỗi ghi `THAT_BAI` + `loi_gui`, lệnh `manage.py gui_thong_bao_trinh_ky` gửi lại (chạy định kỳ thay cho Celery trong MVP). Cấu hình: `SIGNING_EMAIL_BACKEND` (trống: dùng email chung của dự án), `SIGNING_FRONTEND_URL` (liên kết trong email).

### 4.2. Transaction và xử lý đồng thời

- Các hành động `gui`, `ky`, `tu_choi`, `yeu_cau_sua`, `thu_hoi`, `huy`, `trinh_lai` chạy trong `transaction.atomic()`.
- Khóa dòng lượt trình (và yêu cầu khi cần) bằng `select_for_update()` trước khi kiểm tra trạng thái và cập nhật người ký.
- Mọi hành động chuyển trạng thái nhận header `Idempotency-Key`; gửi lặp không tạo thêm chữ ký, lượt trình hay thông báo.
  - Gửi / gửi lại: lưu tại `signing_attempt.khoa_chong_trung`.
  - Hành động của người ký: lưu tại `signing_request_step_signer.khoa_chong_trung_thao_tac`.
- Không gửi thông báo trực tiếp trong transaction; chỉ tạo bản ghi thông báo.
- Client không quyết định trạng thái kế tiếp; server tính dựa trên trạng thái hiện tại, cách thức ký và các người ký.

## 5. Thiết kế dữ liệu

### 5.1. Quy ước chung

- Tên field dùng tiếng Việt không dấu, trừ nhóm cột kỹ thuật: `id`, `create_by`, `created_at`, `update_by`, `update_at`.
- Bảng gốc (`signing_process`, `signing_request`, `signing_attempt`) có đủ `create_by`, `created_at`, `update_by`, `update_at`.
- Bảng con và bảng bằng chứng chỉ có `created_at`; mọi thay đổi của chúng được truy vết qua `signing_audit_log`.
- FK khai báo không kèm hậu tố `_id` (Django tự sinh cột `_id`).
- Thời gian lưu UTC.
- Xóa: mọi FK trỏ tới bảng lịch sử/bằng chứng dùng `on_delete=PROTECT`. Không xóa cứng yêu cầu/lượt trình đã gửi.

### 5.2. Các bảng

#### `signing_process` — Quy trình trình ký

| Tên trường | Field | Kiểu dữ liệu | Bắt buộc | Ghi chú |
|---|---|---|---|---|
| ID | `id` | Number (auto) | | |
| Mã quy trình | `ma_quy_trinh` | Text (50) | X | |
| Tên quy trình | `ten_quy_trinh` | Text (255) | X | |
| Mô tả | `mo_ta` | Text | | |
| Phiên bản | `phien_ban` | Number (SmallInt) | X | Unique cùng `ma_quy_trinh` |
| Trạng thái | `trang_thai` | Text (20) [NHAP, HOAT_DONG, NGUNG] | X | Mặc định NHAP |
| Phạm vi áp dụng | `pham_vi` | Text (20) [PHONG_BAN, CONG_TY] | X | |
| Đơn vị áp dụng | `don_vi_ap_dung` | ForeignKey (Đơn vị) | | Bắt buộc khi `PHONG_BAN`, rỗng khi `CONG_TY`. Thêm ở Phase 7 |
| Cấu hình nhắc hạn | `cau_hinh_nhac_han` | JSON | | Mặc định: trước hạn 24h, đúng hạn, nhắc lặp 24h, leo thang 48h (mục 3.5) |
| Người tạo | `create_by` | ForeignKey (auth_user) | X | |
| Ngày tạo | `created_at` | DateTime (auto) | | |
| Người cập nhật | `update_by` | ForeignKey (auth_user) | | |
| Ngày cập nhật | `update_at` | DateTime (auto) | | |

Ràng buộc: unique `(ma_quy_trinh, phien_ban)`; CHECK `pham_vi = PHONG_BAN` thì `don_vi_ap_dung` khác rỗng. Bỏ `kieu_ky_mac_dinh` (Phase 6c).

#### `signing_process_step` — Cấp ký trong quy trình

| Tên trường | Field | Kiểu dữ liệu | Bắt buộc | Ghi chú |
|---|---|---|---|---|
| ID | `id` | Number (auto) | | |
| Quy trình | `quy_trinh` | ForeignKey (signing_process) | X | |
| Cấp ký | `cap_ky` | Number (SmallInt) | X | Số hiệu hiển thị |
| Tên cấp ký | `ten_cap_ky` | Text (255) | X | |
| Thứ tự ký | `thu_tu` | Number (SmallInt) | X | Quyết định thứ tự mở cấp |
| Đơn vị ký | `don_vi_id` | ForeignKey (Đơn vị) | | FK `organizations_donvi` của Nhóm 7 (migration `0010`) |
| Số giờ xử lý của cấp | `so_gio_xu_ly` | Number | | Rỗng: dùng quy tắc chia hạn mục 3.5 |
| Đang áp dụng | `dang_ap_dung` | Boolean | X | Mặc định True |
| Ghi chú | `ghi_chu` | Text | | |
| Ngày tạo | `created_at` | DateTime (auto) | | |

Ràng buộc: unique `(quy_trinh, thu_tu)`.

#### `signing_process_step_signer` — Người ký cấu hình sẵn

| Tên trường | Field | Kiểu dữ liệu | Bắt buộc | Ghi chú |
|---|---|---|---|---|
| ID | `id` | Number (auto) | | |
| Cấp ký trong quy trình | `buoc_quy_trinh` | ForeignKey (signing_process_step) | X | |
| Người ký | `nguoi_ky` | ForeignKey (auth_user) | | Nhập người ký HOẶC chức vụ |
| Chức vụ ký | `chuc_vu_id` | ForeignKey (Chức vụ) | | Nhập người ký HOẶC chức vụ; FK `accounts_position` của Nhóm 7 (migration `0010`) |
| Phạm vi chức vụ | `pham_vi_chuc_vu` | Text (20) [DON_VI_NGUOI_TAO, DON_VI_CO_DINH, TOAN_CO_QUAN] | | Bắt buộc khi cấu hình theo chức vụ (mục 3.2). Thêm ở Phase 7 |
| Vai trò ký | `vai_tro_ky` | Text (20) [KY_CHINH] | X | Mặc định KY_CHINH |
| Thứ tự trong cấp | `thu_tu` | Number (SmallInt) | X | |
| Ngày tạo | `created_at` | DateTime (auto) | | |

Ràng buộc: CHECK có đúng một trong `nguoi_ky`, `chuc_vu`. Mọi người ký đều bắt buộc, không có field bắt buộc/tùy chọn.

#### `signing_request` — Trình ký

| Tên trường | Field | Kiểu dữ liệu | Bắt buộc | Ghi chú |
|---|---|---|---|---|
| ID | `id` | Number (auto) | | |
| Loại văn bản | `document_type` | Text (20) [vanbandi] | X | Truyền tường minh, không có giá trị mặc định. Chỉ nhận `vanbandi`; `vanbanden` ngoài phạm vi; `vanbanmat` đã bỏ khỏi `document_kind` (mục 1.3) |
| Văn bản liên quan | `van_ban_id` | Number (BigInt) | X | Không FK (3 bảng văn bản); index `(document_type, van_ban_id)` |
| Phiên bản văn bản | `phien_ban_van_ban` | Text (50) | | Bản sao từ lượt trình hiện hành |
| Vị trí lưu tệp | `vi_tri_luu_tep` | Text (500) | | Bản sao từ lượt trình hiện hành |
| Mã băm tài liệu | `ma_bam_tai_lieu` | Text (64) - SHA-256 | | Bản sao từ lượt trình hiện hành |
| Quy trình trình ký | `quy_trinh` | ForeignKey (signing_process) | X | Không đổi sau khi gửi |
| Phiên bản quy trình | `phien_ban_quy_trinh` | Number (SmallInt) | X | Không đổi sau khi gửi |
| Hồ sơ gốc | `ho_so_goc` | ForeignKey (signing_request) | | Trỏ về yêu cầu bị từ chối khi trình lại (mục 3.3); `PROTECT` |
| Trạng thái | `trang_thai` | Text (20) [NHAP, CHO_KY, HOAN_THANH, TU_CHOI, HUY] | X | Mặc định NHAP |
| Hạn chót trình ký | `han_chot` | DateTime | | Chỉ quản trị viên đổi sau khi gửi, có nhật ký |
| Ngày gửi trình ký | `ngay_gui` | DateTime | | |
| Ngày hoàn thành | `ngay_hoan_thanh` | DateTime | | |
| Ngày từ chối | `ngay_tu_choi` | DateTime | | |
| Lý do từ chối | `ly_do_tu_choi` | Text | | |
| Ngày hủy | `ngay_huy` | DateTime | | |
| Lý do hủy | `ly_do_huy` | Text | | |
| Ghi chú | `ghi_chu` | Text | | |
| Người tạo | `create_by` | ForeignKey (auth_user) | X | |
| Ngày tạo | `created_at` | DateTime (auto) | | |
| Người cập nhật | `update_by` | ForeignKey (auth_user) | | |
| Ngày cập nhật | `update_at` | DateTime (auto) | | |

#### `signing_attempt` — Lượt trình ký

| Tên trường | Field | Kiểu dữ liệu | Bắt buộc | Ghi chú |
|---|---|---|---|---|
| ID | `id` | Number (auto) | | |
| Trình ký | `trinh_ky` | ForeignKey (signing_request) | X | |
| Số thứ tự lượt trình | `so_luot` | Number (SmallInt) | X | Unique cùng `trinh_ky` |
| Lượt trình trước | `luot_truoc` | ForeignKey (signing_attempt) | | Phải cùng `trinh_ky` |
| Phiên bản văn bản | `phien_ban_van_ban` | Text (50) | | |
| Vị trí lưu tệp | `vi_tri_luu_tep` | Text (500) | X | Khóa tại thời điểm gửi |
| Mã băm tài liệu | `ma_bam_tai_lieu` | Text (64) - SHA-256 | X | Nguồn sự thật của mã băm |
| Trạng thái | `trang_thai` | Text (20) [NHAP, CHO_KY, YEU_CAU_SUA, HOAN_THANH, TU_CHOI, HUY] | X | Mặc định NHAP |
| Lý do gửi lại | `ly_do` | Text | | |
| Khóa chống gửi trùng | `khoa_chong_trung` | Text (255) | | Unique |
| Thời điểm gửi | `thoi_diem_gui` | DateTime | | |
| Thời điểm hoàn thành | `thoi_diem_hoan_thanh` | DateTime | | |
| Thời điểm từ chối | `thoi_diem_tu_choi` | DateTime | | |
| Thời điểm hủy | `thoi_diem_huy` | DateTime | | |
| Vị trí tệp hoàn tất | `vi_tri_tep_hoan_tat` | Text (500) | | Gán khi phẳng hóa xong |
| Mã băm tệp hoàn tất | `ma_bam_tep_hoan_tat` | Text (64) - SHA-256 | | |
| Người tạo | `create_by` | ForeignKey (auth_user) | X | |
| Ngày tạo | `created_at` | DateTime (auto) | | |
| Người cập nhật | `update_by` | ForeignKey (auth_user) | | |
| Ngày cập nhật | `update_at` | DateTime (auto) | | |

Ràng buộc: unique `(trinh_ky, so_luot)`. Lượt đã gửi không xóa cứng, không ghi đè.

#### `signing_request_step` — Cấp ký của lượt trình

| Tên trường | Field | Kiểu dữ liệu | Bắt buộc | Ghi chú |
|---|---|---|---|---|
| ID | `id` | Number (auto) | | |
| Lượt trình ký | `luot_trinh` | ForeignKey (signing_attempt) | X | |
| Cấp theo quy trình | `buoc_quy_trinh` | ForeignKey (signing_process_step) | X | |
| Cấp ký | `cap_ky` | Number (SmallInt) | X | Snapshot |
| Tên cấp ký | `ten_cap_ky` | Text (255) | X | Snapshot |
| Thứ tự ký | `thu_tu` | Number (SmallInt) | X | Unique trong lượt trình |
| Trạng thái cấp | `trang_thai` | Text (20) [CHUA_MO, DANG_KY, HOAN_THANH, TAM_DUNG] | X | Mặc định CHUA_MO |
| Hạn xử lý cấp | `han_xu_ly` | DateTime | | |
| Thời điểm mở cấp | `thoi_diem_mo` | DateTime | | |
| Thời điểm hoàn tất cấp | `thoi_diem_hoan_thanh` | DateTime | | |
| Ghi chú | `ghi_chu` | Text | | |
| Ngày tạo | `created_at` | DateTime (auto) | | |

Ràng buộc: unique `(luot_trinh, thu_tu)`.

#### `signing_request_step_signer` — Người ký của lượt trình

| Tên trường | Field | Kiểu dữ liệu | Bắt buộc | Ghi chú |
|---|---|---|---|---|
| ID | `id` | Number (auto) | | |
| Cấp ký | `buoc_ky` | ForeignKey (signing_request_step) | X | |
| Người ký | `nguoi_ky` | ForeignKey (auth_user) | X | Unique trong cấp |
| Chức vụ lúc trình | `chuc_vu_id` | Number (BigInt) | | Tạm là số nguyên, đổi sang ForeignKey (Chức vụ) ở Phase 7 |
| Tên người ký | `ten_nguoi_ky` | Text (255) | X | Snapshot tại lúc gửi |
| Tên chức vụ | `ten_chuc_vu` | Text (255) | | Snapshot tại lúc gửi |
| Vai trò ký | `vai_tro_ky` | Text (20) [KY_CHINH] | X | |
| Trạng thái | `trang_thai` | Text (20) [CHO_KY, DA_KY, TU_CHOI, YEU_CAU_SUA] | X | Mặc định CHO_KY |
| Thời điểm mở lượt ký | `thoi_diem_mo` | DateTime | | Rỗng: chưa được phép ký |
| Ngày ký | `ngay_ky` | DateTime | | |
| Ngày từ chối | `ngay_tu_choi` | DateTime | | |
| Lý do từ chối | `ly_do_tu_choi` | Text | | |
| Chữ ký hiện hành | `chu_ky_hien_hanh` | ForeignKey (signing_signature) | | Phải thuộc đúng người ký này |
| Trang đặt chữ ký | `trang_ky` | Number | | |
| Tọa độ X | `toa_do_x` | Number (thập phân) | | |
| Tọa độ Y | `toa_do_y` | Number (thập phân) | | |
| Chiều rộng khung ký | `chieu_rong_khung` | Number (thập phân) | | |
| Chiều cao khung ký | `chieu_cao_khung` | Number (thập phân) | | |
| Khóa chống thao tác trùng | `khoa_chong_trung_thao_tac` | Text (255) | | |
| Ngày tạo | `created_at` | DateTime (auto) | | |

Ràng buộc: unique `(buoc_ky, nguoi_ky)`. Thu hồi là sự kiện nhật ký, không có trạng thái "đã thu hồi".

#### `signing_key` — Khóa ký

| Tên trường | Field | Kiểu dữ liệu | Bắt buộc | Ghi chú |
|---|---|---|---|---|
| ID | `id` | Number (auto) | | |
| Người sở hữu | `nguoi_so_huu` | ForeignKey (auth_user) | X | |
| Mã khóa | `ma_khoa` | Text (100) | X | Unique |
| Dấu vân tay khóa | `dau_van_tay` | Text (64) | X | Unique |
| Thuật toán | `thuat_toan` | Text (50) | X | Mặc định Ed25519 |
| Khóa công khai | `khoa_cong_khai` | Text | X | |
| Trạng thái | `trang_thai` | Text (20) [CHO_KICH_HOAT, HOAT_DONG, DA_XOAY_VONG, THU_HOI, HET_HAN] | X | Mặc định CHO_KICH_HOAT |
| Thời điểm xác minh sở hữu khóa | `thoi_diem_xac_minh_so_huu` | DateTime | | Bắt buộc có trước khi HOAT_DONG |
| Thời điểm kích hoạt | `thoi_diem_kich_hoat` | DateTime | | |
| Ngày hiệu lực | `ngay_hieu_luc` | DateTime | X | |
| Ngày hết hạn | `ngay_het_han` | DateTime | | Rỗng: không hết hạn |
| Ngày thu hồi | `ngay_thu_hoi` | DateTime | | |
| Khóa thay thế | `khoa_thay_the` | ForeignKey (signing_key) | | |
| Ghi chú | `ghi_chu` | Text | | |
| Ngày tạo | `created_at` | DateTime (auto) | | |

Ràng buộc: partial unique index một `nguoi_so_huu` tối đa một khóa `HOAT_DONG`; CHECK `trang_thai = HOAT_DONG` thì `thoi_diem_xac_minh_so_huu` không rỗng. Không có field private key.

#### `signing_signature` — Chữ ký số

| Tên trường | Field | Kiểu dữ liệu | Bắt buộc | Ghi chú |
|---|---|---|---|---|
| ID | `id` | Number (auto) | | |
| Lượt trình ký | `luot_trinh` | ForeignKey (signing_attempt) | X | |
| Người ký (lượt ký) | `buoc_ky` | ForeignKey (signing_request_step_signer) | X | Không unique |
| Khóa ký | `khoa_ky` | ForeignKey (signing_key) | X | |
| Hash tài liệu | `hash_tai_lieu` | Text (64) - SHA-256 | X | Phải bằng `luot_trinh.ma_bam_tai_lieu` |
| Thuật toán | `thuat_toan` | Text (50) | X | |
| Giá trị chữ ký | `chu_ky_so` | Text (Base64) | X | |
| Ghi chú khi ký | `ghi_chu_ky` | Text | | Góp ý nhỏ, không chặn luồng |
| Ký trễ hạn | `ky_tre_han` | Boolean | X | Mặc định False |
| Số giây trễ hạn | `so_giay_tre` | Number | | |
| Ngày ký | `ngay_ky` | DateTime | X | |
| Trạng thái xác minh | `trang_thai_xac_minh` | Text (20) [CHUA_XAC_MINH, HOP_LE, KHONG_HOP_LE] | X | Tạo mới luôn là HOP_LE |
| Thời điểm xác minh | `thoi_diem_xac_minh` | DateTime | | |
| Vị trí ảnh chữ ký | `vi_tri_anh_chu_ky` | Text (500) | | Snapshot ảnh tại lúc ký |
| Mã băm ảnh chữ ký | `ma_bam_anh_chu_ky` | Text (64) - SHA-256 | | |
| Ngày tạo | `created_at` | DateTime (auto) | | |

Ràng buộc: bản ghi bất biến, không UPDATE nội dung, không DELETE; chỉ được cập nhật `trang_thai_xac_minh` và `thoi_diem_xac_minh`. Bảo đảm ở hai tầng: model và trigger PostgreSQL (CSDL chung); cả hai phải chặn cùng tập cột. Không lưu tệp theo từng người ký.

#### `signing_manifest` — Bằng chứng tổng hợp

| Tên trường | Field | Kiểu dữ liệu | Bắt buộc | Ghi chú |
|---|---|---|---|---|
| ID | `id` | Number (auto) | | |
| Lượt trình ký | `luot_trinh` | ForeignKey (signing_attempt) | X | |
| Phiên bản bằng chứng | `phien_ban_bang_chung` | Number (SmallInt) | X | Mặc định 1 |
| Nội dung chuẩn hóa | `noi_dung_chuan_hoa` | JSON | X | Mã băm tài liệu, người ký, dấu vân tay khóa, chữ ký, thời điểm, cấp, trạng thái |
| Mã băm bằng chứng | `ma_bam_bang_chung` | Text (64) - SHA-256 | X | Tính trên bytes serialize chuẩn hóa có phiên bản |
| Vị trí lưu | `vi_tri_luu` | Text (500) | | |
| Trạng thái | `trang_thai` | Text (20) [NHAP, DA_CHOT] | X | DA_CHOT thì không sửa/xóa |
| Thời điểm chốt | `thoi_diem_chot` | DateTime | | |
| Người tạo | `create_by` | ForeignKey (auth_user) | X | |
| Ngày tạo | `created_at` | DateTime (auto) | | |

#### `signing_change_thread` — Yêu cầu chỉnh sửa

| Tên trường | Field | Kiểu dữ liệu | Bắt buộc | Ghi chú |
|---|---|---|---|---|
| ID | `id` | Number (auto) | | |
| Lượt trình ký | `luot_trinh` | ForeignKey (signing_attempt) | X | |
| Người yêu cầu | `nguoi_yeu_cau` | ForeignKey (auth_user) | X | |
| Tiêu đề | `tieu_de` | Text (255) | X | |
| Lý do | `ly_do` | Text | X | |
| Trạng thái | `trang_thai` | Text (20) [DANG_MO, DA_GIAI_QUYET] | X | Mặc định DANG_MO |
| Thời điểm giải quyết | `thoi_diem_giai_quyet` | DateTime | | |
| Ngày tạo | `created_at` | DateTime (auto) | | |
| Ngày cập nhật | `update_at` | DateTime (auto) | | |

#### `signing_change_message` — Tin nhắn trao đổi

| Tên trường | Field | Kiểu dữ liệu | Bắt buộc | Ghi chú |
|---|---|---|---|---|
| ID | `id` | Number (auto) | | |
| Yêu cầu chỉnh sửa | `yeu_cau_sua` | ForeignKey (signing_change_thread) | X | |
| Người viết | `nguoi_viet` | ForeignKey (auth_user) | X | |
| Nội dung | `noi_dung` | Text | X | |
| Ngày tạo | `created_at` | DateTime (auto) | | |

Thread và message không xóa cứng, không cascade khi xóa yêu cầu/lượt trình.

#### `signing_audit_log` — Nhật ký trình ký

| Tên trường | Field | Kiểu dữ liệu | Bắt buộc | Ghi chú |
|---|---|---|---|---|
| ID | `id` | Number (auto) | | |
| Trình ký | `trinh_ky` | ForeignKey (signing_request) | | Bắt buộc với sự kiện luồng ký |
| Lượt trình ký | `luot_trinh` | ForeignKey (signing_attempt) | | |
| Người ký (lượt ký) | `buoc_ky` | ForeignKey (signing_request_step_signer) | | |
| Loại đối tượng | `loai_doi_tuong` | Text (50) | X | Ví dụ signing_process, signing_key, signing_signature |
| Mã đối tượng | `ma_doi_tuong` | Number | X | |
| Người thực hiện | `nguoi_thuc_hien` | ForeignKey (auth_user) | X | |
| Hành động | `hanh_dong` | Text (50) | X | |
| Trạng thái trước | `trang_thai_truoc` | Text (20) | | |
| Trạng thái sau | `trang_thai_sau` | Text (20) | | |
| Nội dung chi tiết | `chi_tiet` | Text | | |
| Dữ liệu kèm theo | `du_lieu_kem_theo` | JSON | | |
| Địa chỉ IP | `dia_chi_ip` | Text (45) | | |
| Thời điểm | `created_at` | DateTime (auto) | | |

Ràng buộc: CHECK `loai_doi_tuong` thuộc luồng ký (request/attempt/signer/signature) thì `trinh_ky` không rỗng. Chỉ ghi thêm: chặn ở tầng model và bằng trigger PostgreSQL chặn UPDATE/DELETE (CSDL chung); có thể bổ sung giới hạn quyền role ứng dụng khi triển khai. Sự kiện thu hồi chữ ký: `loai_doi_tuong = signing_signature`, `ma_doi_tuong` = id chữ ký bị thu hồi.

#### `signing_notification` — Thông báo trình ký (kiêm outbox)

| Tên trường | Field | Kiểu dữ liệu | Bắt buộc | Ghi chú |
|---|---|---|---|---|
| ID | `id` | Number (auto) | | |
| Trình ký | `trinh_ky` | ForeignKey (signing_request) | X | |
| Người ký (lượt ký) | `buoc_ky` | ForeignKey (signing_request_step_signer) | | |
| Người nhận | `nguoi_nhan` | ForeignKey (auth_user) | X | |
| Kênh | `kenh` | Text (20) [IN_APP, EMAIL] | X | |
| Loại thông báo | `loai_thong_bao` | Text (50) | X | |
| Trạng thái | `trang_thai` | Text (20) [CHO_GUI, DA_GUI, THAT_BAI] | X | Mặc định CHO_GUI |
| Hẹn giờ gửi | `hen_gio_gui` | DateTime | | Dùng cho nhắc trước hạn |
| Khóa chống gửi trùng | `khoa_chong_gui_trung` | Text (255) | X | Unique |
| Số lần gửi lại | `so_lan_gui_lai` | Number | X | Mặc định 0 |
| Thời điểm gửi | `thoi_diem_gui` | DateTime | | |
| Lỗi gửi | `loi_gui` | Text | | |
| Ngày tạo | `created_at` | DateTime (auto) | | |

#### `signing_key_unlock` — Mở khóa ký bằng PIN (Phase 6a)

| Tên trường | Field | Kiểu dữ liệu | Bắt buộc | Ghi chú |
|---|---|---|---|---|
| ID | `id` | Number (auto) | | |
| Khóa ký | `khoa` | OneToOne (signing_key) | X | |
| PIN verifier | `ma_bam_xac_minh_pin` | Text | X | Argon2id verifier, không lưu PIN |
| Private key mã hóa | `khoa_bi_mat_ma_hoa` | Text | X | AES-256-GCM PKCS#8 Ed25519; khóa dẫn xuất từ pepper + salt; không log/serialize |
| Tham số KDF | `tham_so_kdf` | JSON | X | Argon2id verifier: thuật toán, `m`, `t`, `p`, phiên bản và salt |
| Số lần sai | `so_lan_sai` | Number | X | Mặc định 0 |
| Khóa đến | `khoa_den` | DateTime | | Rỗng: không bị khóa |
| Ngày tạo | `created_at` | DateTime (auto) | | |
| Ngày cập nhật | `updated_at` | DateTime (auto) | | Theo DDL base (trigger `set_updated_at`); khác `update_at` của các bảng `signing_*` khác |

Bảng trạng thái, không phải bảng bằng chứng: được cập nhật. Mọi sự kiện đặt/đổi/mở khóa/sai/khóa PIN ghi vào `signing_audit_log` (loại đối tượng `signing_key`).

#### Phụ thuộc nhóm khác

| Nhóm / Sheet | Field | Nội dung |
|---|---|---|
| Nhóm 7 — CBNV | `anh_chu_ky` | Image (PNG nền trong suốt, tối đa 2MB); ảnh chữ ký cá nhân trong hồ sơ |
| Nhóm 2 — Văn bản | `document_type`, `van_ban_id` | CSDL chung có 3 bảng đến/đi/mật; Trình ký tham chiếu bằng cặp này, không FK. Cần Nhóm 2 xác nhận khóa chính từng bảng |
| Nhóm 2 — Sổ văn bản đi | API cấp số | Cấp số, ký hiệu, ngày ban hành cho văn bản đã hoàn tất trình ký; chuyển trạng thái phát hành (mục 1.4) |
| Nhóm 7 — Cơ cấu tổ chức | Cấp trên trực tiếp | Dùng cho leo thang quá hạn (mục 3.5) |

### 5.3. Ràng buộc tổng hợp

- Không gửi nếu quy trình không có cấp hoặc có cấp không có người ký.
- Không gửi nếu người ký theo chức vụ không resolve được tài khoản đang hoạt động, hoặc resolve ra nhiều người mà người tạo chưa chọn.
- Không ký nếu:
  - lượt trình không ở `CHO_KY`;
  - người ký không ở `CHO_KY` hoặc `thoi_diem_mo` rỗng;
  - mã băm client ký khác `luot_trinh.ma_bam_tai_lieu`;
  - khóa không `HOAT_DONG`;
  - chữ ký không verify được.
- Không hoàn thành lượt trình khi còn cấp chưa `HOAN_THANH`; không đóng cấp khi còn người ký trong cấp chưa `DA_KY`.
- Yêu cầu `TU_CHOI`, `HOAN_THANH`, `HUY` là trạng thái kết thúc.
- Ký lại sau thu hồi tạo dòng chữ ký mới; không sửa/xóa chữ ký cũ; không có hai chữ ký hiện hành trên một người ký.
- Không có trạng thái quá hạn trong máy trạng thái ký.
- Không xóa lượt trình đã gửi; không cascade xóa chữ ký, bằng chứng tổng hợp, thread/message, nhật ký.
- `luot_truoc` chỉ trỏ lượt trình cùng yêu cầu.
- Chỉ kích hoạt khóa sau proof-of-possession; một người dùng tối đa một khóa `HOAT_DONG`.
- Hành động đồng thời chỉ một hành động hợp lệ được xử lý (khóa dòng + chống trùng).
- Không sửa raw bytes của tệp gốc trong luồng nội bộ; chỉ phẳng hóa khi lượt trình `HOAN_THANH`.

## 6. Máy trạng thái

### 6.1. Yêu cầu và lượt trình

```text
Yêu cầu (signing_request.trang_thai):
NHAP     -> CHO_KY     (gui: tạo lượt trình đầu tiên)
NHAP     -> HUY        (người tạo/quản trị hủy trước khi gửi)
CHO_KY   -> HOAN_THANH | TU_CHOI | HUY
TU_CHOI, HOAN_THANH, HUY: kết thúc (trình lại sau TU_CHOI = tạo yêu cầu mới, ho_so_goc trỏ về)

Lượt trình (signing_attempt.trang_thai):
NHAP        -> CHO_KY      (gui)
CHO_KY      -> YEU_CAU_SUA | TU_CHOI | HOAN_THANH | HUY
YEU_CAU_SUA -> HUY         (hủy hồ sơ khi đang chờ sửa)
YEU_CAU_SUA: giữ nguyên làm lịch sử khi thread DA_GIAI_QUYET; tạo lượt trình mới (luot_truoc trỏ về)
TU_CHOI     -> (kết thúc)
```

- Khi lượt trình `YEU_CAU_SUA`, yêu cầu vẫn `CHO_KY` nhưng không ai ký được trên lượt đó.
- Lượt cũ không quay lại `CHO_KY` và không bị ghi đè.
- Không có chuyển trạng thái quá hạn; hạn xử lý chỉ kích hoạt nhắc/escalation.

### 6.2. Hành động của người ký

| Hành động | Điều kiện | Kết quả |
|---|---|---|
| `ky` | Người ký `CHO_KY`, `thoi_diem_mo` có giá trị, khóa `HOAT_DONG`, verify Ed25519 thành công | Người ký `DA_KY`; tạo chữ ký `HOP_LE` kèm snapshot ảnh; gán `chu_ky_hien_hanh`; tính `ky_tre_han`. Kiểm tra mở `KY_CHINH`, mở cấp sau, hoàn thành lượt trình. |
| `tu_choi` | Lý do bắt buộc | Người ký và lượt trình `TU_CHOI`; yêu cầu `TU_CHOI` (kết thúc) |
| `yeu_cau_sua` | Lý do bắt buộc | Người ký và lượt trình `YEU_CAU_SUA`; cấp đang mở `TAM_DUNG`; mở thread |
| `thu_hoi` | Cấp của người ký còn `DANG_KY`, lượt trình chưa hoàn thành, người ký `DA_KY` | Ghi nhật ký; `chu_ky_hien_hanh` rỗng; người ký về `CHO_KY` |

## 7. API dự kiến

Prefix `/api/v1/`. Tên đoạn đường dẫn theo convention tiếng Việt đã dùng trong code (`quy-trinh`, `khoa`). Mục 7.1 và phần khóa của 7.4 đã triển khai ở Phase 5, dùng đúng route trong `backend/apps/signing/urls.py`; mục 7.2, 7.3 còn là contract dự kiến cho Phase 7–9, tên đoạn đường dẫn theo cùng convention khi triển khai. Tên field trong payload trùng tên field CSDL.

### 7.1. Quy trình

- `GET /signing/quy-trinh/`: danh sách theo phạm vi/quyền.
- `POST /signing/quy-trinh/`: tạo quy trình `NHAP`.
- `GET /signing/quy-trinh/{id}/`: chi tiết kèm cấp và người ký (`vai_tro_ky`).
- `PATCH /signing/quy-trinh/{id}/`: chỉ khi `NHAP`.
- `POST /signing/quy-trinh/{id}/kich-hoat/`
- `POST /signing/quy-trinh/{id}/ngung/`
- `POST /signing/quy-trinh/{id}/nhan-ban/`: tạo phiên bản mới.

### 7.2. Yêu cầu trình ký

Đã triển khai ở Phase 7 (#80), đường dẫn `/signing/trinh-ky/`:
- `GET /signing/trinh-ky/?hop=can_toi_ky|toi_gui|tat_ca&trang_thai=`: `can_toi_ky` = người ký đã được mở, đang chờ ký, trên lượt `CHO_KY`; `tat_ca` = hồ sơ người dùng được xem (người tạo, người ký của hồ sơ; `view_signing_audit` xem tất cả).
- `POST /signing/trinh-ky/` (multipart): dùng một trong hai nguồn: văn bản đi (`document_type=vanbandi`, `van_ban_id`, `tep_dinh_kem_id` là tệp PDF còn hiệu lực trên bản ghi; không gửi `tep`) hoặc PDF dự thảo (`tep` ≤ 20 MB, `trich_yeu_van_ban` bắt buộc, `so_hieu_van_ban` tùy chọn). Server kiểm và sao chép PDF vào kho Trình ký, tính SHA-256; tạo `NHAP`. Quyền `add_trinhky`.
- `POST /signing/trinh-ky/{id}/lien-ket-van-ban-di/`: người tạo liên kết PDF dự thảo đã duyệt với bản ghi Văn bản đi đã đăng ký; yêu cầu hồ sơ `HOAN_THANH` và PDF kết quả `THANH_CONG`; chỉ liên kết một lần, kiểm quyền xem đích và ghi nhật ký. Không tự tạo bản ghi hoặc cấp số văn bản.
- `GET /signing/trinh-ky/{id}/`: tổng quan, các lượt trình (cấp, người ký, hạn), người đang chờ, lịch sử. Không trả đường dẫn lưu tệp.
- `PATCH /signing/trinh-ky/{id}/`: chỉ khi `NHAP`, chỉ người tạo; thay tệp tăng `phien_ban_van_ban`.
- `GET /signing/trinh-ky/{id}/tep/`: tệp của lượt trình hiện hành (hoặc dự thảo khi còn nháp), kiểm quyền xem.
- `POST /signing/trinh-ky/{id}/gui/`: khóa tệp/mã băm, snapshot cấp, người ký và vị trí ký, mở cấp đầu. Nhận `chon_nguoi_ky` (`{id người ký cấu hình: id tài khoản}`) khi chức vụ có nhiều ứng viên; thiếu thì lỗi `can_chon_nguoi_ky` kèm ứng viên. Nhận `vi_tri_ky` (`{id người ký cấu hình: {trang_ky, toa_do_x, toa_do_y, chieu_rong_khung, chieu_cao_khung}}`, tỷ lệ % gốc trên-trái, khung trong trang); trang vượt số trang hoặc khóa không phải người ký cấu hình: `vi_tri_ky_khong_hop_le`. Quyền `send_trinhky` + người tạo.
- Tạo/trình lại kiểm quy trình áp dụng cho người tạo: `CONG_TY` hoặc `PHONG_BAN` của đơn vị mình (403 `quy_trinh_khong_ap_dung`). Tải lên kiểm PDF đọc được trang, không mật khẩu.
- `POST /signing/trinh-ky/{id}/huy/`: người tạo; hoặc `cancel_trinhky` hủy thay (bắt buộc `ly_do`).
- `POST /signing/trinh-ky/{id}/trinh-lai/`: chỉ khi `TU_CHOI`; tạo hồ sơ `NHAP` mới (văn bản, tệp lượt cuối; phiên bản đang hoạt động của cùng mã quy trình), `ho_so_goc` trỏ về hồ sơ cũ. Quyền `send_trinhky` + người tạo.
- `gui`, `huy`, `trinh-lai` bắt buộc header `Idempotency-Key`; gửi lặp cùng khóa trả kết quả lần trước.
- Phát hành pháp lý (`phat-hanh`): ngoài MVP, đã gỡ khỏi roadmap #80.

### 7.3. Hành động người ký

Đã triển khai ở Phase 8 (#80), đường dẫn theo hồ sơ (người ký được xác định từ tài khoản đăng nhập; cấp mở tuần tự nên mỗi người có tối đa một dòng đang mở). Quyền `sign_trinhky`, bắt buộc `Idempotency-Key`:
- `POST /signing/trinh-ky/{id}/ky/`: `khoa_ky`, `hash_tai_lieu` (hex 64), `chu_ky_so` (Base64 Ed25519 trên raw bytes của SHA-256), `ghi_chu_ky` (tùy chọn). Kiểm: lượt `CHO_KY`, người ký đã mở và chờ ký, mã băm khớp lượt, khóa thuộc người ký và đang hoạt động trong hiệu lực, chữ ký verify được. Ghi chữ ký `HOP_LE`, `ky_tre_han`/`so_giay_tre` theo `han_xu_ly` của cấp; mở ký chính khi ký nháy chặn ký đủ; đóng cấp khi mọi người ký trong cấp đã ký; mở cấp sau hoặc hoàn thành lượt và hồ sơ.
- `POST /signing/trinh-ky/{id}/tu-choi/`: "Không đồng ý ban hành", `ly_do_tu_choi` bắt buộc; chỉ người ký đang được mở; lượt và hồ sơ `TU_CHOI` (kết thúc).
- `POST /signing/trinh-ky/{id}/thu-hoi/`: khi cấp của người ký còn `DANG_KY`. Chữ ký cũ giữ nguyên, ký lại tạo bản ghi mới.
- Đồng thời: mọi hành động khóa dòng lượt trình trước khi xử lý; thao tác lặp cùng khóa trả kết quả lần trước.
- Ảnh chữ ký cá nhân để sau MVP (Nhóm 7 chốt ở #67 mục 2), `vi_tri_anh_chu_ky` để trống ở MVP; tệp hoàn tất in khối chữ thay ảnh.

Trả lại để sửa, đã triển khai ở lõi Phase 9 (#80):
- `POST /signing/trinh-ky/{id}/yeu-cau-sua/`: "Trả lại để sửa", `tieu_de` và `ly_do` bắt buộc; chỉ người ký đang được mở (quyền `sign_trinhky`, `Idempotency-Key`). Người ký và lượt `YEU_CAU_SUA`, cấp đang ký `TAM_DUNG`, mở thread; hồ sơ vẫn `CHO_KY` nhưng không ai ký tiếp trên lượt này.
- `GET /signing/trinh-ky/{id}/trao-doi/`: thread gần nhất của lượt hiện hành và tin nhắn; người tạo hồ sơ, người yêu cầu sửa, hoặc `view_signing_audit` (chỉ đọc).
- `POST /signing/trinh-ky/{id}/trao-doi/`: `noi_dung`; chỉ người tạo hồ sơ và người yêu cầu sửa, khi thread đang mở và hồ sơ còn `CHO_KY`.
- `POST /signing/trinh-ky/{id}/giai-quyet/` (multipart `tep`, tùy chọn `vi_tri_ky` dạng chuỗi JSON theo id dòng người ký lượt hiện hành; mặc định giữ vị trí lượt trước, tệp mới ít trang hơn thì báo lỗi): người tạo hồ sơ (quyền `send_trinhky`, `Idempotency-Key`) tải bản sửa; server băm, tăng `phien_ban_van_ban`, thread `DA_GIAI_QUYET`, tạo lượt mới (`luot_truoc`) cùng cấp và người ký của lượt cũ, mở cấp đầu; toàn bộ các cấp ký lại. Chữ ký lượt cũ giữ làm lịch sử, không dùng cho tệp mới (mã băm khác). Có người ký không còn hoạt động thì lỗi `khong_xac_dinh_duoc_nguoi_ky`, chưa lưu tệp.


### 7.4. Khóa, nhật ký, bằng chứng tổng hợp

- `GET|POST /signing/khoa/`: danh sách khóa của người dùng hiện tại; đăng ký khóa công khai.
- `GET /signing/khoa/{id}/thach-thuc/`: challenge chứng minh sở hữu (mục 3.4).
- `POST /signing/khoa/{id}/xac-minh/`: verify proof-of-possession, gán `thoi_diem_xac_minh_so_huu`.
- `POST /signing/khoa/{id}/kich-hoat/`: chuyển `HOAT_DONG` (khóa đã xác minh).
- `POST /signing/khoa/{id}/xoay-vong/`
- `POST /signing/khoa/{id}/thu-hoi/`
- #447 partition 1 server-side signing API:
  - `POST /signing/khoa/{id}/dat-pin/`: `{pin, khoa_bi_mat_pkcs8, tham_so_kdf}` → 201 `{khoa, da_dat_pin}`. Server verifies PKCS#8 against registered public key, encrypts it using pepper-derived AES key independent of PIN, and stores ciphertext, PIN verifier and KDF parameters. Raw request fields require HTTPS; response is `no-store` and contains no key material.
  - `POST /signing/khoa/{id}/doi-pin/`: `{pin_cu, pin_moi, tham_so_kdf}` → 200 `{khoa, da_dat_pin}`. Server decrypts and re-encrypts the same key with a fresh salt; no private key is returned. Wrong PIN → 400 `pin_khong_dung`; the 15th wrong attempt in a local day and subsequent attempts → 429 `pin_het_luot_trong_ngay`.
  - `POST /signing/dat-lai-pin/xac-nhan/`: `{ma, pin_moi}` → `{da_dat_lai_pin, khoa}` after valid emailed code. Requires HTTPS; code is bound to its original `khoa_id`. Updates only PIN verifier and failed-attempt state, retaining key status, key id, public key and ciphertext.
  - `POST /signing/trinh-ky/{id}/ky/`: `{khoa_ky, hash_tai_lieu, pin, ghi_chu_ky}`. The server checks ownership, active key, locked document hash and MFA, decrypts the key in memory, signs the raw 32-byte SHA-256 digest with Ed25519 and verifies that signature against the stored public key before state changes. Request requires HTTPS in production; response is `no-store`.
  - Legacy `mo-khoa-ky/` route and `k_srv`/PIN-verifier responses are removed. The HTTPS condition depends on correct Nginx TLS and `DJANGO_SECURE_PROXY_SSL_HEADER` configuration.
- Lịch sử hồ sơ trả trong `GET /signing/trinh-ky/{id}/` (`lich_su`).
- Lõi Phase 10 (#80), người xem được hồ sơ (người tạo, người ký, `view_signing_audit`):
  - `GET /signing/trinh-ky/{id}/bang-chung/`: bằng chứng đã chốt của lượt hiện hành (`noi_dung_chuan_hoa`, `ma_bam_bang_chung`, `thoi_diem_chot`) và `xac_minh` (băm lại, verify lại từng chữ ký bằng khóa công khai trong bằng chứng, đối chiếu tệp gốc và tệp hoàn tất đang lưu). Chưa hoàn tất: 409 `chua_co_bang_chung`.
  - `GET /signing/trinh-ky/{id}/tep-hoan-tat/`: tải tệp PDF hoàn tất (kiểm mã băm trước khi trả, `no-store`). Chưa sẵn sàng: 409 `tep_hoan_tat_chua_san_sang`; tệp bị đổi: 409 `tep_hoan_tat_bi_thay_doi`.
  - `POST /signing/trinh-ky/{id}/tao-lai-tep-hoan-tat/`: người tạo hồ sơ hoặc `view_signing_audit`; khi `LOI` hoặc đang xử lý quá 10 phút; đã `THANH_CONG` thì không sinh lại; đang xử lý: 409 `dang_tao_tep_hoan_tat`.
  - Chi tiết hồ sơ trả thêm theo lượt: `trang_thai_tep_hoan_tat`, `loi_tep_hoan_tat`, `ma_bam_tep_hoan_tat`, `ma_bam_bang_chung`; theo người ký: vị trí ký và `co_anh_chu_ky`.
  - `GET /signing/trinh-ky/{id}/anh-chu-ky/{chu_ky_id}/`: ảnh snapshot lúc ký (lớp phủ UI), kiểm mã băm.
- Hỗ trợ giao diện: `GET /signing/toi/` (id, tên, đơn vị, quyền Trình ký, `la_quan_tri`, `la_lanh_dao_don_vi`); `GET /signing/van-ban-di/?q=` (văn bản đi thường người dùng xem được, `add_trinhky`); `GET /signing/nguoi-dung/?q=` (tìm tài khoản để cấu hình người ký, `manage_signing_process`).

### 7.5. Quy tắc chung

- Lỗi validation trả theo field, kèm mã lỗi nghiệp vụ ổn định.
- Hành động chuyển trạng thái của yêu cầu/lượt trình (`gui`, `ky`, `tu-choi`, `yeu-cau-sua`, `giai-quyet`, `uy-quyen`, `thu-hoi`, `huy`, `trinh-lai`) bắt buộc header `Idempotency-Key`, áp dụng từ Phase 7–9. Endpoint quy trình và khóa (Phase 5) chưa áp dụng.
- Không trả dữ liệu nhạy cảm ngoài contract; không log chữ ký/khóa ở dạng không kiểm soát.
- Phân trang và lọc giới hạn theo quyền sở hữu, phân công, phạm vi ở server, không chỉ ẩn ở UI.
- Ảnh chữ ký cá nhân đọc qua contract của Nhóm 7; module này không định nghĩa API hồ sơ.

## 8. Phân quyền

- Nhân viên đã xác thực được tạo yêu cầu nếu có quyền truy cập văn bản và thấy quy trình `HOAT_DONG`.
- Danh sách yêu cầu mặc định gồm: người tạo, người được giao ký, quản trị, kiểm toán; lọc mặc định theo phòng ban người tạo.
- Permission tối thiểu, tên theo CSDL chung (`auth_permission`):
  - `view_trinhky`
  - `add_trinhky`
  - `manage_signing_process`
  - `send_trinhky`
  - `sign_trinhky`
  - `cancel_trinhky`
  - `view_signing_audit`
- Ánh xạ từ tên trong bản nháp cũ: `xem_trinh_ky` → `view_trinhky`, `tao_trinh_ky` → `add_trinhky`, `quan_ly_quy_trinh_ky` → `manage_signing_process`, `gui_trinh_ky` → `send_trinhky`, `ky_trinh_ky` → `sign_trinhky`, `uy_quyen_trinh_ky` → `delegate_trinhky`, `huy_trinh_ky` → `cancel_trinhky`, `xem_nhat_ky_trinh_ky` → `view_signing_audit`.
- `manage_signing_process` kiểm tra kèm phạm vi: quy trình `CONG_TY` cần quản trị; quy trình `PHONG_BAN` cần là lãnh đạo của `don_vi_ap_dung` hoặc quản trị (mục 3.1). Cần nhóm CSDL cấp thêm quyền này cho nhóm TP.
- Quyền kiểm tra ở API/service; frontend chỉ hỗ trợ UX.

## 9. Hạn xử lý, thông báo và Celery

### 9.1. Tác vụ định kỳ

- Quét theo lô các yêu cầu có `han_chot` và các cấp có `han_xu_ly` sắp đến hạn.
- Tạo thông báo với `khoa_chong_gui_trung`; worker retry không gửi trùng.
- Mốc mặc định theo mục 3.5 (trước 24h, tại hạn, nhắc lặp 24h, leo thang 48h); `cau_hinh_nhac_han` của quy trình được ưu tiên.
- Leo thang gửi cấp trên trực tiếp của người ký và người tạo; chỉ tạo thông báo và nhật ký; không đổi trạng thái, không chặn ký muộn, không tự đổi người ký, không tự từ chối.
- Quét bản ghi thông báo `CHO_GUI` bị sót (outbox, mục 4.1).
- Không cần tác vụ định kỳ cho `HET_HAN`: trạng thái được chuyển khi đọc hoặc dùng khóa (mục 3.4).

### 9.2. Quy tắc Celery

- Task nhận ID, đọc dữ liệu mới nhất trong service/transaction.
- Retry có exponential backoff, jitter, giới hạn số lần.
- Task idempotent; lỗi cuối lưu vào `loi_gui` để quan sát và retry thủ công.
- Không đặt logic chuyển trạng thái quan trọng chỉ trong task nền; hành động đồng bộ phải tự bảo toàn bất biến.

## 10. Kế hoạch theo pha

> Mục này là kế hoạch ban đầu và đã được thay bằng `plan-trien-khai-theo-phase.md` (Phase 1–10, đánh số khác). Khi trích dẫn tiến độ hoặc phase, dùng tài liệu `plan-trien-khai-theo-phase.md`.

### Pha 0 — Chốt contract và khung app

- Kiểm tra cấu trúc Django thực tế trên nhánh Nhóm 5.
- Chốt model văn bản (Nhóm 2), đơn vị, chức vụ, hồ sơ và ảnh chữ ký (Nhóm 7).
- Tạo app, URL versioning, base permission, timezone, định dạng lỗi.
- Chốt convention migration và database test.

### Pha 1 — Schema và quản lý quy trình

- Migration cho quy trình, cấp, người ký cấu hình (`vai_tro_ky`), nhật ký.
- Tạo/kích hoạt/ngừng/nhân bản quy trình; phạm vi `PHONG_BAN`/`CONG_TY`.
- Chặn sửa quy trình đã kích hoạt.
- Test: unique, quy trình không có cấp, cấp không có người ký, chức vụ trống, CHECK người ký XOR chức vụ, phân quyền.

### Pha 2 — Yêu cầu, lượt trình, snapshot người ký

- Tạo nháp, gửi, snapshot quy trình/văn bản/người ký/vị trí ký.
- Mở cấp tuần tự/song song, hoàn thành.
- Khóa dòng và chống trùng.
- Test đồng thời: hai người ký cùng lúc, gửi lặp, ký lặp.

### Pha 3 — Khóa ký, chữ ký, bằng chứng tổng hợp

- Challenge/proof-of-possession (ngẫu nhiên, có hạn dùng; dùng một lần bằng PostgreSQL, mục 3.4), tài khoản không hoạt động, xoay vòng, thu hồi, hết hạn.
- Verify Ed25519 trên raw digest.
- Lưu chữ ký bất biến (`ghi_chu_ky`, `ky_tre_han`, snapshot ảnh), con trỏ `chu_ky_hien_hanh`, bằng chứng chuẩn hóa.
- Test: lệch mã băm, khóa không hoạt động, chữ ký sai, khóa cũ verify lịch sử, thu hồi/ký lại song song, không xóa được chữ ký/bằng chứng.

### Pha 4 — Chỉnh sửa, từ chối, hủy, hạn xử lý

- Thread/message, tạm dừng lượt trình, giải quyết và gửi lại toàn bộ bằng lượt mới.
- Từ chối/xem xét lại/hủy/quản trị hủy thay.
- Hạn UTC, lịch nhắc, escalation; ký muộn có gắn cờ trễ hạn.
- Test: nhiều người cùng yêu cầu sửa; không có gửi lại một phần; quá hạn vẫn `CHO_KY` và ký muộn được.

### Pha 5 — Thông báo, lưu trữ, phẳng hóa PDF, adapter pháp lý

- Thông báo kiêm outbox, task Celery có chống trùng/retry, quét bản ghi sót.
- Adapter filesystem qua mount cấu hình bằng biến môi trường.
- `PdfStampingService`: phẳng hóa khi `HOAN_THANH`, lưu `vi_tri_tep_hoan_tat`, `ma_bam_tep_hoan_tat`; test tệp gốc không đổi mã băm trong suốt luồng nội bộ.
- (Ngoài MVP #80) Interface `LegalSignerAdapter` cho khâu phát hành.
- Contract test để thay adapter lưu trữ bằng API/SFTP không đổi domain service.

### Pha 6 — Hoàn thiện API và bàn giao

- OpenAPI, schema lỗi, tài liệu chống trùng (`Idempotency-Key`).
- Chạy migration, check, test, lint/type check theo repo.
- Rà soát quyền, nhật ký, log, dữ liệu nhạy cảm.
- Kiểm tra nhánh/status trước khi stage đúng file thuộc task.

## 11. Tiêu chí nghiệm thu

### Luồng ký

- Tạo được quy trình nhiều cấp, mỗi cấp nhiều người ký.
- Cấp sau không mở khi cấp hiện tại chưa hoàn thành; người trong cùng cấp ký song song và đều phải ký.
- Từ chối kết thúc yêu cầu; trình lại tạo yêu cầu mới có `ho_so_goc`.
- Chức vụ có nhiều người thì bắt người tạo chọn khi gửi.
- Quy trình đã kích hoạt không sửa được; thay đổi đi qua nhân bản phiên bản.
- Chức vụ trống chặn gửi.

### Toàn vẹn dữ liệu và chỉnh sửa

- Lượt trình giữ snapshot quy trình/phiên bản/người ký/mã băm; bản sao trên yêu cầu luôn khớp lượt hiện hành.
- Vị trí ký lưu và hiển thị đúng trên PDF dưới dạng lớp phủ.
- Tệp gốc không đổi mã băm trong luồng nội bộ; tệp hoàn tất sinh một lần khi `HOAN_THANH`, dùng snapshot ảnh tại thời điểm ký.
- `ghi_chu_ky` lưu vào chữ ký, không chặn luồng.
- `yeu_cau_sua` chặn luồng, mở thread; giải quyết xong thì tạo lượt mới ký lại từ đầu trên mã băm mới.
- Lượt trình đã gửi, chữ ký, bằng chứng `DA_CHOT` không bị xóa cứng hay cascade.
- Mỗi người ký tối đa một chữ ký hiện hành; ký lại không ghi đè chữ ký cũ.
- Không chữ ký nào được chấp nhận nếu mã băm hoặc khóa công khai không khớp.
- Hành động đồng thời và retry không tạo bản ghi/trạng thái trùng.

### Mật mã, nhật ký, pháp lý

- Private key chỉ xuất hiện trong request đặt PIN qua HTTPS; sau đó lưu trong CSDL dạng AES-256-GCM ciphertext. API không trả private key/ciphertext, không ghi vào log hoặc bằng chứng tổng hợp.
- PIN chỉ truyền qua HTTPS; pepper ở env ngoài CSDL. Sai PIN quá ngưỡng bị từ chối và ghi audit; response không chứa secret. Proxy phải cấu hình để `request.is_secure()` nhận diện HTTPS.
- Chữ ký verify được từ khóa công khai và raw SHA-256 digest.
- Xoay vòng/thu hồi khóa, thu hồi chữ ký, từ chối, yêu cầu sửa, hủy, quản trị hủy thay đều có nhật ký, kể cả sự kiện không gắn yêu cầu.
- Bằng chứng chuẩn hóa kiểm tra độc lập được theo lượt trình; `DA_CHOT` bất biến.
- Tệp hoàn tất mang nhận diện "bản duyệt nội bộ, chưa phát hành"; bằng chứng tổng hợp xác minh lại được (mã băm, chữ ký Ed25519, tệp gốc, tệp hoàn tất, ảnh chữ ký).
- Phát hành pháp lý bằng chứng thư số CA nằm ngoài MVP (#80 mục 8).

### Hạn xử lý và thông báo

- Hạn lưu UTC, hiển thị giờ Việt Nam.
- Nhắc trước hạn 24 giờ, tại hạn, nhắc lặp và leo thang cấp trên trực tiếp; retry không gửi trùng.
- Quá hạn không tự từ chối, không đổi người ký, không hủy luồng.
- Yêu cầu/lượt trình quá hạn vẫn `CHO_KY`; chữ ký muộn có `ky_tre_han = true` và `so_giay_tre`.

### Lệnh kiểm tra dự kiến

Chỉ chạy sau khi xác nhận cấu trúc backend thực tế:

```powershell
python backend/manage.py check
python backend/manage.py makemigrations --check --dry-run
pytest
```

Nếu repo có chuẩn lint/type check thì bổ sung đúng lệnh của repo trước khi báo hoàn tất.

## 12. Điểm còn mở và rủi ro

- `[CHƯA XÁC MINH]` Model đơn vị, chức vụ, API lưu trữ — phụ thuộc Nhóm 7 (Phase 7).
- `[CHƯA CHỐT]` Model người dùng của hệ thống (`accounts_employee` ở CSDL chung hay `auth.User` ở Django) và cách gán 8 quyền ở mục 8 (Phase 6).
- `[ĐÃ CHỐT]` Challenge chứng minh sở hữu khóa dùng một lần ép bằng bảng PostgreSQL `signing_challenge_da_dung` (#507), mục 3.4.
- `[PHỤ THUỘC NHÓM 7]` Field `anh_chu_ky` và contract đọc ảnh chữ ký trong hồ sơ cá nhân.
- `[CHƯA CHỐT]` Kích thước pixel chuẩn của ảnh chữ ký.
- `[CHƯA CHỐT]` Hệ tọa độ vị trí ký: tỷ lệ % hay điểm PDF.
- `[CHƯA CHỐT]` Khôi phục khóa đa thiết bị; mỗi thiết bị mới tạo khóa riêng và cần xoay vòng.
- `[RỦI RO]` Server-side signing cần HTTPS được cấu hình và xác minh ở staging trước rollout; endpoint PIN/ký fail closed khi Django không nhận biết request là HTTPS.
- `[RỦI RO]` Chống chối bỏ nội bộ chỉ đáng tin ở mức tin cậy vào CSDL (khóa công khai và chữ ký đều lưu trong CSDL). Giảm bằng chuỗi hash nhật ký hoặc dấu thời gian bên thứ ba; chưa thuộc MVP.
- `[CẦN XÁC NHẬN]` Contract cấp số văn bản đi và chuyển trạng thái phát hành với Nhóm 2 (mục 1.4), trước Phase 10.
- `[CẦN XÁC NHẬN]` Danh sách cấp trên trực tiếp (Nhóm 7), trước Phase 9.
- `[CHƯA CHỐT]` Luồng tự do (không theo quy trình mẫu): ngoài MVP.
- `[ĐÃ CHỐT]` Văn bản mật đã bỏ (GVHD). Khách hàng là doanh nghiệp bảo hiểm; tài liệu nội bộ hạn chế (`pham_vi = 'HAN_CHE'`) không ký và không đi qua trình ký (mục 3.3). Căn cứ bảo vệ dữ liệu: Luật Bảo vệ dữ liệu cá nhân 2025 (Luật số 91/2025/QH15).
- `[CHƯA CHỐT]` Thu hồi hoặc thay thế sau khi lượt trình `HOAN_THANH`; nhiều tệp đính kèm; vai trò xem/góp ý không ký.
- `[RỦI RO]` Test đồng thời (Phase 8) cần PostgreSQL; cấu hình mặc định là SQLite và `requirements.txt` chưa có `psycopg`.

## 13. Definition of Done

- Migration áp dụng được trên database test sạch.
- FK/retention chặn xóa yêu cầu/lượt trình đã có lịch sử và chặn cascade xóa chữ ký, thread/message, nhật ký, bằng chứng `DA_CHOT`.
- API/service đã kiểm tra chuyển trạng thái, quyền, quyền sở hữu, chống trùng.
- Unit/integration test bao phủ: mở cấp tuần tự, nhiều người ký song song trong cấp, từ chối, yêu cầu sửa, gửi lại toàn bộ, thu hồi/ký lại giữ lịch sử, ký muộn, ký đồng thời, phẳng hóa không đổi tệp gốc.
- Test mật mã: lệch mã băm, ranh giới private key, xoay vòng khóa, challenge dùng một lần (khi áp dụng challenge ngẫu nhiên), PIN và khóa theo số lần sai (Phase 6).
- Test outbox/Celery: retry không gửi trùng.
- Không sửa hoặc stage file ngoài phạm vi backend Trình ký.
- Review nhánh/status/diff trước khi commit và push.
