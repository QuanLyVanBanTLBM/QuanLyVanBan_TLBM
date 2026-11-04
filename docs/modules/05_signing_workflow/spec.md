# ĐẶC TẢ PHÂN HỆ: NHÓM 5 — TRÌNH KÝ SỐ (SIGNING WORKFLOW)

> **Tài liệu căn cứ:** 
> - File đặc tả đề án: `docs/common/ITC - Django - QLVB&TL.md` & `docs/common/ITC - Django - QLVB&TL.xlsx`.
> - Cấu trúc chuẩn hệ thống: `docs/common/architecture/structure.md`.
> - Phân công: **Nhóm 5** (Trưởng nhóm: Lê Thanh Hậu, Thành viên: Lê Thành Tài).
> - Nhánh phát triển: `5_signing_workflow`.
> - Tài liệu kỹ thuật chi tiết backend: [`signing-backend-plan.md`](signing-backend-plan.md).
> - Đánh giá nghiệp vụ và quyết định điều chỉnh (06/10/2026): [`danh-gia-nghiep-vu-va-de-xuat.md`](danh-gia-nghiep-vu-va-de-xuat.md).

---

## 1. MỤC TIÊU & PHẠM VI NGHIỆP VỤ

### 1.1. Mục tiêu
Xây dựng phân hệ **Trình ký** gồm: tạo hồ sơ trình ký; luân chuyển theo quy trình nhiều cấp (các cấp tuần tự, người trong cùng cấp ký song song); hiển thị tiến trình trực quan (stepper/timeline); ký duyệt bằng chữ ký điện tử nội bộ Ed25519 kèm kiểm tra toàn vẹn (SHA-256 raw digest); xử lý phản hồi hai nhánh; xử lý quá hạn không chặn luồng. Điểm kết thúc của MVP (#80) là **hoàn tất duyệt nội bộ, chưa phát hành**: sinh PDF kết quả kèm bằng chứng tổng hợp. Ủy quyền, nhắc/leo thang và phát hành pháp lý nằm trong backlog sau MVP (#80 mục 8).

### 1.2. Phạm vi chức năng
1. **Ảnh chữ ký cá nhân (phụ thuộc Nhóm 7, để sau MVP theo #67 mục 2):**
   - Người dùng tải lên ảnh chữ ký PNG nền trong suốt, tối đa 2MB, trong hồ sơ cá nhân (field `anh_chu_ky`, sheet CBNV).
   - Phân hệ Trình ký chỉ đọc ảnh qua contract do Nhóm 7 cung cấp.
   - Lúc ký, phân hệ chụp snapshot ảnh vào bản ghi chữ ký; tệp hoàn tất dán ảnh vào khung ký, chưa có ảnh thì in khối chữ "ĐÃ KÝ DUYỆT" kèm họ tên, chức vụ, thời điểm ký (đã triển khai, #80). MVP dùng khối chữ: Nhóm 7 chốt cột `anh_chu_ky` để sau MVP (#67 mục 2); khi có cột, chỉ cần nối nguồn ảnh ở `tich_hop/to_chuc.anh_chu_ky`.
2. **Mẫu quy trình trình ký:**
   - Quy trình nhiều cấp, trạng thái `NHAP -> HOAT_DONG -> NGUNG`, phạm vi `PHONG_BAN` (gắn đơn vị áp dụng) hoặc `CONG_TY`.
   - Quy trình `CONG_TY` do quản trị cấu hình; quy trình `PHONG_BAN` do lãnh đạo đơn vị đó hoặc quản trị cấu hình.
   - Các cấp mở tuần tự; trong một cấp, mọi người ký nhận cùng lúc và đều phải ký. Muốn mọi người ký cùng lúc thì cấu hình quy trình một cấp.
   - Người ký cấu hình theo tài khoản hoặc theo chức vụ. Chức vụ hiểu tương đối: trong đơn vị người tạo, trong một đơn vị cố định, hoặc cấp cơ quan. Khi gửi, chức vụ có nhiều người thì người tạo phải chọn; không có ai thì không cho gửi.
   - Mọi người ký có cùng một vai trò (**Ký chính**, `KY_CHINH`).
   - Quy trình đã kích hoạt không sửa trực tiếp; thay đổi bằng nhân bản phiên bản mới.
   - Nháp chưa gửi chỉ được gửi theo phiên bản đang hoạt động. Khi phiên bản cũ đã ngừng và có phiên bản mới hơn cùng mã đang hoạt động, người tạo có thể xác nhận chuyển nháp sang phiên bản đó; hệ thống cập nhật phiên bản trên nháp và ghi nhật ký. Người tạo phải xem lại danh sách người ký và đặt lại vị trí ký trước khi gửi. Không có phiên bản cùng mã đang chạy thì nháp chưa thể gửi.
3. **Tạo trình ký, định vị nơi ký và Lazy Stamping:**
   - Khi gửi, khóa snapshot quy trình, người ký (tài khoản, tên, chức vụ) và mã băm SHA-256 của tài liệu vào lượt trình (`signing_attempt`).
   - **Định vị nơi ký:** người tạo kéo-thả khung ký cho từng người ký trên bản xem trước: `trang_ky`, `toa_do_x`, `toa_do_y`, `chieu_rong_khung`, `chieu_cao_khung`. Hệ tọa độ đã chốt: tỷ lệ % theo trang, gốc góc trên-trái; khung nằm trọn trong trang.
   - **Lazy Stamping và lớp phủ giao diện:**
     - Trong suốt luồng duyệt nội bộ, **tệp PDF gốc không bị sửa raw bytes**; mọi người ký ký trên cùng một mã băm.
     - Giao diện React hiển thị ảnh chữ ký như lớp phủ CSS/Canvas trên bản xem trước theo tọa độ.
     - Khi ký, backend chỉ lưu snapshot ảnh chữ ký vào bản ghi chữ ký, không sửa tệp.
     - Chỉ khi lượt trình `HOAN_THANH`, hệ thống chốt bằng chứng tổng hợp và sinh tệp hoàn tất (`vi_tri_tep_hoan_tat`) một lần: giữ nguyên nội dung trang gốc, dán khối chữ ký vào đúng khung, thêm dòng "BẢN DUYỆT NỘI BỘ, CHƯA PHÁT HÀNH" ở chân trang, nối trang phê duyệt và đính kèm bằng chứng JSON. Lỗi tạo tệp thì thử lại, không ký lại.
   - Thiết lập hạn chót (`han_chot`) và số giờ xử lý từng cấp (`so_gio_xu_ly`).
   - Nguồn tài liệu: chọn **văn bản đi** (`vanbandi`) đã đăng ký cùng một tệp PDF đang đính kèm trên chính bản ghi đó; hoặc tải PDF dự thảo chưa vào sổ. Với PDF dự thảo, hồ sơ nhận mã trình ký tự cấp (`signing_request.id`), số hiệu nhập tay nếu có chỉ là tham chiếu. Sau khi duyệt nội bộ hoàn tất và PDF kết quả tạo thành công, người tạo đăng ký tệp kết quả ở phân hệ Văn bản đi rồi liên kết hồ sơ với bản ghi vừa tạo. Trình ký không tự tạo bản ghi, cấp số văn bản hoặc chuyển tệp sang kho Văn bản đi. Văn bản đến không trình ký (bút phê/chỉ đạo thuộc Nhóm 2). Văn bản mật đã bỏ (GVHD chốt); văn bản hạn chế (`pham_vi = 'HAN_CHE'`) không ký và API từ chối khi gắn bản ghi đó (`signing-backend-plan.md` mục 3.3).
4. **Danh sách hồ sơ trình ký:**
   - Tabs: *Cần tôi ký duyệt*, *Tôi đã gửi trình*, *Hồ sơ theo quyền* (tab chỉ là bộ lọc; quyền đọc do server kiểm).
   - Bộ lọc: trạng thái. Lọc phòng ban, khoảng thời gian, tìm kiếm và phân trang thuộc backlog.
5. **Chi tiết hồ sơ và sơ đồ luồng ký:**
   - Split view: cột trái là stepper tiến độ ký; cột phải là PDF viewer có lớp phủ khung ký.
6. **Ký duyệt và xử lý phản hồi hai nhánh:**
   - **Nhánh 1 — Lỗi nhỏ, không chặn luồng:** ký duyệt kèm `ghi_chu_ky`; luồng tiếp tục; ghi chú hiển thị cho người tạo và các cấp sau.
   - **Nhánh 2 — Lỗi lớn, chặn luồng:** `yeu_cau_sua` kèm lý do; lượt trình chuyển `YEU_CAU_SUA`, các cấp đang mở `TAM_DUNG`; mở thread trao đổi hai chiều (`signing_change_thread`). Khi thống nhất, người tạo tải bản mới, thread `DA_GIAI_QUYET`, hệ thống tạo lượt trình mới để ký lại toàn bộ. Lượt cũ giữ nguyên `YEU_CAU_SUA` làm lịch sử.
   - **Từ chối = không đồng ý ban hành** (`tu_choi`), bắt buộc lý do; hồ sơ kết thúc ở `TU_CHOI`. Muốn trình lại thì tạo hồ sơ mới (`trinh_lai`) trỏ về hồ sơ gốc (`ho_so_goc`). Giao diện phân biệt rõ "Trả lại để sửa" (nhánh 2) và "Không đồng ý ban hành".
   - Thu hồi chữ ký (`thu_hoi`) chỉ khi cấp của người ký còn mở và trước khi lượt trình hoàn thành; chữ ký cũ giữ nguyên làm bằng chứng.
7. **Quá hạn** (MVP: hiển thị hạn xử lý, ký muộn có ghi nhận; nhắc, leo thang và ủy quyền theo thời gian thuộc backlog sau MVP, #80 mục 8):
   - Quá hạn không tự hủy, không tự từ chối; người ký vẫn ký muộn được và hệ thống ghi `ky_tre_han = true`, `so_giay_tre`.
   - Nhắc và leo thang: nhắc trước hạn 24 giờ, tại hạn, nhắc lặp mỗi 24 giờ khi quá hạn; quá hạn 48 giờ báo cấp trên trực tiếp của người ký và người tạo. Có báo cáo trễ hạn theo người/đơn vị.
   - **Ủy quyền theo thời gian** (căn cứ NĐ 30/2020 Điều 13: ủy quyền có thời hạn và phạm vi): người ủy quyền hoặc cấp trên khai báo trước người nhận, khoảng thời gian, phạm vi và hình thức ký (KT., TL., TUQ.); hồ sơ đến trong khoảng đó tự chuyển người nhận.
8. **Ngoài phạm vi MVP (#80 mục 8):**
   - Chữ ký Ed25519 của luồng duyệt là **chữ ký điện tử nội bộ**, không gọi là chữ ký số và không có giá trị pháp lý với bên ngoài. Tệp hoàn tất mang dòng nhận diện "bản duyệt nội bộ, chưa phát hành".
   - CA, chứng thư số, `LegalSignerAdapter`, DocMDP, cấp số qua sổ văn bản đi và phát hành pháp lý không phải điều kiện hoàn tất MVP và đã gỡ khỏi roadmap triển khai của #80.

---

## 2. MÔ HÌNH DỮ LIỆU

Chi tiết field, kiểu dữ liệu và ràng buộc tại [`signing-backend-plan.md` mục 5](signing-backend-plan.md#5-thiết-kế-dữ-liệu). Tên field dùng tiếng Việt, trừ `id`, `create_by`, `created_at`, `update_by`, `update_at`.

| Bảng | Vai trò | Trạng thái |
| :--- | :--- | :--- |
| `signing_process` | Quy trình mẫu có phiên bản, phạm vi và đơn vị áp dụng | `NHAP`, `HOAT_DONG`, `NGUNG` |
| `signing_process_step` | Cấp ký trong quy trình, số giờ xử lý | — |
| `signing_process_step_signer` | Người ký cấu hình sẵn (người ký hoặc chức vụ + phạm vi chức vụ), `vai_tro_ky` | — |
| `signing_request` | Hồ sơ trình ký, vòng đời tổng; `ho_so_goc` khi trình lại | `NHAP`, `CHO_KY`, `HOAN_THANH`, `TU_CHOI`, `HUY` (3 trạng thái cuối là kết thúc) |
| `signing_attempt` | Lượt trình bất biến, nguồn sự thật của mã băm, tệp hoàn tất | `NHAP`, `CHO_KY`, `YEU_CAU_SUA`, `HOAN_THANH`, `TU_CHOI`, `HUY` |
| `signing_request_step` | Snapshot cấp ký của lượt trình | `CHUA_MO`, `DANG_KY`, `HOAN_THANH`, `TAM_DUNG` |
| `signing_request_step_signer` | Snapshot người ký, tọa độ ký, `chu_ky_hien_hanh` | `CHO_KY`, `DA_KY`, `TU_CHOI`, `YEU_CAU_SUA` |
| `signing_key` | Khóa công khai Ed25519 (không lưu private key) | `CHO_KICH_HOAT`, `HOAT_DONG`, `DA_XOAY_VONG`, `THU_HOI`, `HET_HAN` |
| `signing_signature` | Chữ ký bất biến: `chu_ky_so`, `ghi_chu_ky`, `ky_tre_han`, snapshot ảnh chữ ký | `CHUA_XAC_MINH`, `HOP_LE`, `KHONG_HOP_LE` |
| `signing_manifest` | Bằng chứng tổng hợp chuẩn hóa, `ma_bam_bang_chung` | `NHAP`, `DA_CHOT` |
| `signing_change_thread` / `signing_change_message` | Trao đổi hai chiều khi yêu cầu sửa | `DANG_MO`, `DA_GIAI_QUYET` |
| `signing_audit_log` | Nhật ký chỉ ghi thêm, gồm cả sự kiện quy trình và khóa ký | — |
| `signing_notification` | Thông báo in-app/email, kiêm outbox | `CHO_GUI`, `DA_GUI`, `THAT_BAI` |

---

## 3. RESTFUL API

Prefix `/api/v1/signing/`. Payload dùng đúng tên field CSDL; lỗi trả `{code, detail, fields}`. Hành động chuyển trạng thái của hồ sơ/lượt trình bắt buộc header `Idempotency-Key`. Chi tiết tại `signing-backend-plan.md` mục 7.

| Phương thức | Endpoint | Chức năng | Phân quyền |
| :--- | :--- | :--- | :--- |
| `GET/POST` | `quy-trinh/` | Danh sách quy trình (theo phạm vi, đơn vị); tạo quy trình `NHAP` | `view_trinhky` / `manage_signing_process` + phạm vi |
| `GET` | `quy-trinh/{id}/` | Chi tiết quy trình, cấp, người ký | Như danh sách |
| `POST` | `quy-trinh/{id}/kich-hoat/`, `ngung/`, `nhan-ban/` | Kích hoạt (tự ngừng bản cũ cùng mã), ngừng, nhân bản | Quản trị (`CONG_TY`); lãnh đạo đơn vị hoặc quản trị (`PHONG_BAN`) |
| `GET/POST` | `trinh-ky/` | Danh sách theo hộp (`can_toi_ky`, `toi_gui`, `tat_ca`); tạo nháp kèm PDF | Đăng nhập / `add_trinhky` |
| `GET/PATCH` | `trinh-ky/{id}/` | Chi tiết, lượt trình, tiến trình, lịch sử; sửa nháp | Người liên quan / kiểm toán; người tạo |
| `GET` | `trinh-ky/{id}/tep/` | Tệp của lượt hiện hành | Người xem được hồ sơ |
| `POST` | `trinh-ky/{id}/gui/` | Khóa tệp/mã băm, snapshot người ký và vị trí ký, mở cấp đầu | `send_trinhky` (người tạo) |
| `POST` | `trinh-ky/{id}/huy/`, `trinh-lai/` | Hủy; trình lại sau từ chối (`ho_so_goc`) | Người tạo / `cancel_trinhky`; `send_trinhky` |
| `POST` | `trinh-ky/{id}/ky/`, `tu-choi/`, `thu-hoi/`, `yeu-cau-sua/` | Ký duyệt (verify Ed25519, snapshot ảnh), không đồng ý, thu hồi, trả lại để sửa | `sign_trinhky` (người ký đang được mở) |
| `GET/POST` | `trinh-ky/{id}/trao-doi/` | Trao đổi về yêu cầu sửa | Người tạo / người yêu cầu sửa; kiểm toán chỉ đọc |
| `POST` | `trinh-ky/{id}/giai-quyet/` | Tải bản sửa, tạo lượt trình mới | Người tạo (`send_trinhky`) |
| `GET` | `trinh-ky/{id}/bang-chung/`, `tep-hoan-tat/`, `anh-chu-ky/{chu_ky}/` | Bằng chứng và xác minh; tệp hoàn tất; ảnh snapshot | Người xem được hồ sơ |
| `POST` | `trinh-ky/{id}/tao-lai-tep-hoan-tat/` | Thử lại khi tạo tệp lỗi | Người tạo / kiểm toán |
| `GET/POST` | `khoa/`; `khoa/{id}/thach-thuc/`, `xac-minh/`, `kich-hoat/`, `xoay-vong/`, `thu-hoi/` | Khóa công khai Ed25519 và vòng đời khóa | Chủ khóa (`sign_trinhky`) |
| `POST` | `khoa/{id}/dat-pin/`, `mo-khoa-ky/`, `doi-pin/` | PIN bảo vệ khóa ký, xoay vòng `k_srv` | Chủ khóa (`sign_trinhky`) |
| `GET` | `toi/`, `van-ban-di/`, `nguoi-dung/` | Hỗ trợ giao diện: quyền người dùng hiện tại, chọn văn bản đi, chọn người ký | Đăng nhập / `add_trinhky` / `manage_signing_process` |

Ngoài MVP (backlog): `uy-quyen` (khẩn cấp và theo thời gian), báo cáo trễ hạn.

API ảnh chữ ký cá nhân thuộc Nhóm 7, không nằm trong phân hệ này.

---

## 4. QUY CHUẨN GIAO DIỆN (UI/UX)

Đã triển khai dưới `/approvals/*` (`frontend/src/pages/signing/`, #80 mục E):

1. **Ảnh chữ ký trong hồ sơ cá nhân:** thuộc Nhóm 7.
2. **Danh sách:** tab *Cần tôi ký duyệt*, *Tôi đã gửi trình*, *Hồ sơ theo quyền*; bảng gồm văn bản, quy trình, trạng thái, người đang chờ, người trình, hạn chót; lọc trạng thái; trạng thái tải/rỗng/lỗi.
3. **Tạo hồ sơ:** bước 1 chọn văn bản đi đã đăng ký rồi chọn PDF đính kèm trên bản ghi, hoặc tải PDF dự thảo chưa vào sổ (hồ sơ được cấp mã tự động; số hiệu nhập tay là tham chiếu), chọn quy trình được dùng, hạn chót → lưu nháp; bước 2 xem trước PDF, xem người ký theo quy trình, kéo-thả khung ký từng người, chọn người ký khi chức vụ nhiều ứng viên, xác nhận mã băm rồi gửi. Nháp mở lại được. Sau khi duyệt PDF dự thảo, người tạo đăng ký tệp kết quả trong Văn bản đi rồi liên kết hồ sơ.
4. **Chi tiết:** PDF của lượt hiện hành kèm lớp phủ chữ ký (ảnh snapshot hoặc khối "đã ký"; người đang chờ nét đứt), tiến trình theo cấp (vai trò, hạn xử lý, ký trễ), người đang chờ, lịch sử, các lượt trước. Hành động theo quyền/trạng thái: *Ký duyệt* (PIN, hiện tên tệp và mã băm, chặn ký khi tệp đang xem khác mã băm đã khóa), *Trả lại để sửa*, *Không đồng ý ban hành*, *Thu hồi chữ ký*, *Hủy*, *Trình lại*. Trao đổi và tải bản sửa khi trả sửa.
5. **Kết quả:** nhận diện "Hoàn tất duyệt nội bộ, chưa phát hành"; trạng thái tạo tệp đang xử lý/lỗi/thành công; chỉ cho tải khi tạo tệp thành công; thử lại khi lỗi; xác minh bằng chứng.
6. **Quy trình và Cấu hình khóa ký:** cấu hình quy trình theo phạm vi; tạo khóa trên thiết bị (Argon2id ở trình duyệt), đổi PIN, đổi thiết bị bằng xoay vòng khóa, thu hồi khóa.

## 5. TIÊU CHUẨN KỸ THUẬT & INVARIANTS

- **i18n:** text UI của phân hệ khai báo đủ `vi`/`en` trong từ điển riêng `frontend/src/lib/signing/i18n/` (theo ngôn ngữ của bộ chọn chung); test kiểm hai ngôn ngữ cùng tập khóa.
- **Design Tokens:** chỉ dùng class Tailwind ngữ nghĩa ánh xạ biến của `src/styles/global.css`; không hardcode mã màu. Inline style chỉ cho tọa độ khung ký (ngoại lệ tọa độ động lúc chạy).
- **Toàn vẹn dữ liệu:** không lưu private key trên backend; verify chữ ký đồng bộ trước khi đổi trạng thái người ký; mã băm của lượt trình, chữ ký và bằng chứng `DA_CHOT` là bất biến; không cascade xóa lịch sử.
- **Tọa độ chữ ký:** tỷ lệ % theo trang, gốc trên-trái, độc lập độ phân giải màn hình.
- **Lazy Stamping:** không sửa raw bytes tệp PDF trong luồng nội bộ; chỉ dán ảnh chữ ký một lần khi lượt trình `HOAN_THANH`, dùng snapshot ảnh tại thời điểm ký.
- **Bảo vệ khóa ký bằng PIN (Phase 6):** PIN 8 chữ số, Argon2id ở client; bản bọc private key chỉ ở thiết bị, server giữ mảnh bí mật `k_srv` và hash verifier, khóa theo số lần sai, có nhật ký; đổi PIN xoay vòng `k_srv` (Phase 6c). Chi tiết tại `signing-backend-plan.md` mục 3.4.
- **Thể thức:** khối chữ ký theo `hinh_thuc_ky` (KT., TL., TUQ.) đi cùng ủy quyền, thuộc backlog sau MVP.
- **Văn bản hạn chế (`pham_vi = 'HAN_CHE'`):** là văn bản gửi đi chọn người xem và lưu log xem (Nhóm 2), không ký và không đi qua trình ký; API tạo hồ sơ từ chối. Bảo mật trình ký (khóa ký, PIN, mã băm, nhật ký, bằng chứng) giữ nguyên.
- **Ranh giới pháp lý:** kết quả MVP là bản duyệt nội bộ, chưa phát hành; không thay cho văn bản ban hành.
- **Technical Gates:**
  - `python backend/manage.py check` (Pass)
  - `python backend/manage.py test signing` trên SQLite và PostgreSQL (Pass 100%)
  - `pnpm --dir frontend run build` (Pass 0 warning/error)
