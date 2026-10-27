# Hợp đồng API và Quy tắc Nghiệp vụ Phân hệ Phòng Họp (Issue #22 - Nhóm 7)

Tài liệu đặc tả hợp đồng API (API Contract), ma trận phân quyền RBAC và các quy tắc nghiệp vụ bất biến cho phân hệ Quản lý & Đặt phòng họp (Issue #22, Nhóm 7).

---

## 1. Cơ sở Kỹ thuật & Phạm vi Dữ liệu

- Nguồn DDL chuẩn: `docs/common/database/release_DDL.sql` (bảng `meetings_meetingroom`, `meetings_meetingbooking`).
- Kiểu ENUM PostgreSQL:
  - `meetingroom_status`: `'AVAILABLE'`, `'MAINTENANCE'`, `'UNAVAILABLE'`. Mặc định: `'AVAILABLE'`.
  - `meetingbooking_status`: `'CONFIRMED'`, `'CANCELLED'`, `'COMPLETED'`. Mặc định: `'CONFIRMED'`.
- Ràng buộc toàn vẹn cơ sở dữ liệu:
  - `meetings_meetingroom_capacity_check`: `capacity > 0`.
  - `meetings_meetingbooking_attendees_count_check`: `attendees_count > 0`.
  - `chk_booking_time`: `end_time > start_time`.
  - `excl_room_time`: Ràng buộc loại trừ PostgreSQL GiST chống trùng khung giờ giữa các bản ghi có cùng phòng (`room_id`), cùng ngày (`date`), trạng thái khác `'CANCELLED'`.
- Tên trường trong API: Tuân thủ 100% tên cột DDL (tiếng Anh kỹ thuật cho phòng họp và đặt lịch: `room`, `organizer`, `title`, `date`, `start_time`, `end_time`, `attendees_count`, `purpose`, `trang_thai`), không trả bí danh lai ghép.

---

## 2. Ma trận Phân quyền RBAC (Issue #21 Contract)

Phân hệ phòng họp áp dụng nghiêm ngặt hợp đồng RBAC dự án (`docs/modules/07_system_admin_meetings/api-contract-issue-21.md`). Quyền kiểm tra qua `user.has_perm(codename)`:

| Codename | Module | Thao tác được phép | Ghi chú |
|---|---|---|---|
| `view_schedule_phonghop` | Phòng họp | Xem danh mục phòng họp công khai và danh sách lịch đặt | Yêu cầu tối thiểu để mở giao diện Lịch/Phòng họp |
| `add_phonghop` | Phòng họp (danh mục) | Tạo phòng họp mới (`POST /api/meeting-rooms/`) | Dành cho Quản trị viên / Quản lý CSVC |
| `change_phonghop` | Phòng họp (danh mục) | Sửa phòng họp; Xem và đặt lịch các phòng họp nội bộ (`is_public = False`) | Quản lý thấy toàn bộ phòng nội bộ |
| `delete_phonghop` | Phòng họp (danh mục) | Xóa phòng họp (`DELETE /api/meeting-rooms/{id}/`) | Chặn xóa nếu phòng đã có lịch đặt liên kết |
| `add_datphonghop` | Đặt phòng họp | Tạo lịch đặt phòng họp mới (`POST /api/meeting-bookings/`) | Cấp cho CBNV được phép đặt phòng |
| `change_own_datphonghop` | Đặt phòng họp | Sửa hoặc hủy lịch đặt phòng do chính mình tạo (`organizer`) | CBNV chỉ điều chỉnh lịch của mình |
| `change_any_datphonghop` | Đặt phòng họp | Sửa hoặc hủy lịch đặt phòng của bất kỳ người dùng nào | Dành cho Lễ tân, Điều phối viên, Quản trị |

*Lưu ý bảo mật*:
- Tài khoản quản trị tối cao (`is_superuser = True`) có toàn quyền trên mọi endpoint.
- Tuyệt đối không dùng cờ `is_staff` để bypass kiểm tra quyền nghiệp vụ.

---

## 3. Đặc tả Chi tiết Endpoints API

### 3.1. Danh mục Phòng họp (`/api/meeting-rooms/`)

#### GET `/api/meeting-rooms/`
- **Mục đích**: Lấy danh sách phòng họp.
- **Quyền**: Yêu cầu `view_schedule_phonghop` (hoặc `is_superuser`).
- **Tham số truy vấn (Query Params)**:
  - `page`: Số trang (mặc định 1).
  - `page_size`: Kích thước trang (mặc định 10, tối đa 100).
  - `search`: Tìm kiếm không dấu / có dấu theo tên phòng, vị trí, danh sách thiết bị.
  - `is_public`: `true` (phòng công khai) hoặc `false` (phòng nội bộ). Nếu người dùng không có quyền `change_phonghop`, tham số `is_public=false` luôn trả về danh sách rỗng.
  - `trang_thai`: `AVAILABLE`, `MAINTENANCE`, `UNAVAILABLE`.
  - `all`: `true` để lấy toàn bộ danh sách không phân trang (dùng cho dropdown đặt lịch).
- **Phản hồi thành công**: `200 OK`.

#### POST `/api/meeting-rooms/`
- **Mục đích**: Tạo mới một phòng họp.
- **Quyền**: Yêu cầu `add_phonghop` (hoặc `is_superuser`).
- **Payload**:
  ```json
  {
    "name": "Phòng Hội thảo A",
    "location": "Tầng 3, Tòa Nhà Điều Hành",
    "capacity": 30,
    "amenities": "Máy chiếu 4K, 2 Micro không dây, Bảng viết",
    "is_public": true,
    "trang_thai": "AVAILABLE",
    "ghi_chu": "Phòng ưu tiên cho các cuộc họp chuyên môn"
  }
  ```
- **Phản hồi**: `201 Created` nếu hợp lệ; `400 Bad Request` nếu thiếu tên phòng, trùng tên, hoặc sức chứa `<= 0`.

#### GET `/api/meeting-rooms/{id}/`
- **Mục đích**: Xem chi tiết một phòng họp.
- **Quyền**: Yêu cầu `view_schedule_phonghop`.
- **Phản hồi**: `200 OK`.

#### PUT / PATCH `/api/meeting-rooms/{id}/`
- **Mục đích**: Cập nhật thông tin phòng họp.
- **Quyền**: Yêu cầu `change_phonghop`.
- **Phản hồi**: `200 OK`.

#### DELETE `/api/meeting-rooms/{id}/`
- **Mục đích**: Xóa phòng họp.
- **Quyền**: Yêu cầu `delete_phonghop`.
- **Phản hồi**: `204 No Content` khi xóa thành công; `400 Bad Request` kèm mã lỗi `meetings.messages.cannotDeleteRoomHasBookings` nếu phòng đã có lịch đặt liên kết.

---

### 3.2. Đặt Lịch Phòng họp (`/api/meeting-bookings/`)

#### GET `/api/meeting-bookings/`
- **Mục đích**: Danh sách lịch đặt phòng họp.
- **Quyền**: Yêu cầu `view_schedule_phonghop`.
- **Bảo mật phòng nội bộ**: Người dùng thông thường chỉ nhìn thấy các lịch đặt thuộc phòng công khai (`is_public = True`) hoặc lịch do chính mình là người đặt (`organizer`). Quản lý có quyền `change_phonghop` thấy toàn bộ.
- **Tham số truy vấn**:
  - `date`: Lọc theo ngày cụ thể (`YYYY-MM-DD`).
  - `start_date`, `end_date`: Lọc theo khoảng ngày.
  - `room`: ID phòng họp (truyền chuỗi không phải số trả về 400 an toàn).
  - `trang_thai`: `CONFIRMED`, `CANCELLED`, `COMPLETED`.
- **Phản hồi**: `200 OK`.

#### POST `/api/meeting-bookings/`
- **Mục đích**: Tạo lịch đặt phòng mới.
- **Quyền**: Yêu cầu `add_datphonghop`.
- **Cơ chế**:
  - Tự động gán `organizer` là người dùng đang gửi request.
  - Tự động gán `department` từ phòng ban của người dùng nếu chưa chỉ định.
  - Sử dụng Database Lock (`select_for_update`) trên bản ghi phòng họp để chống race condition.
- **Payload**:
  ```json
  {
    "room": 1,
    "title": "Họp triển khai quý 4",
    "date": "2026-10-30",
    "start_time": "14:00:00",
    "end_time": "15:30:00",
    "attendees_count": 12,
    "purpose": "Đánh giá tiến độ đồ án"
  }
  ```
- **Phản hồi thành công**: `201 Created`.
- **Phản hồi lỗi**: `400 Bad Request` (trùng giờ, quá khứ, phòng bảo trì, vượt sức chứa, sai khoảng giờ).

#### GET `/api/meeting-bookings/{id}/`
- **Mục đích**: Xem chi tiết lịch đặt phòng.
- **Quyền**: Yêu cầu `view_schedule_phonghop`.
- **Phản hồi**: `200 OK`. Trường `trang_thai` trả về trạng thái hiển thị động (`COMPLETED` nếu cuộc họp `CONFIRMED` đã qua thời gian kết thúc).

#### PUT / PATCH `/api/meeting-bookings/{id}/`
- **Mục đích**: Cập nhật thông tin hoặc dời lịch họp.
- **Quyền**: Người tạo lịch cần `change_own_datphonghop`; người khác cần `change_any_datphonghop`.
- **Quy tắc**:
  - Không cho phép cập nhật lịch đã kết thúc (`COMPLETED`) -> `400` (`meetings.messages.bookingAlreadyEnded`).
  - Không cho phép cập nhật lịch đã bị hủy (`CANCELLED`) -> `400` (`meetings.messages.bookingAlreadyCancelled`).
  - Không cho phép dời lịch về quá khứ -> `400` (`meetings.messages.bookingInPast`).
  - Cập nhật chỉ tiêu đề hoặc ghi chú không bị tính là trùng lịch với chính bản ghi đó.
- **Phản hồi**: `200 OK`.

#### DELETE `/api/meeting-bookings/{id}/`
- **Mục đích**: Xóa lịch đặt phòng.
- **Quy định bất biến**: **Không cho phép xóa vật lý (Hard Delete)** bản ghi lịch đặt phòng họp.
- **Phản hồi**: Luôn trả về `405 Method Not Allowed` kèm mã lỗi `meetings.messages.deleteBookingNotAllowed`. Bản ghi trong CSDL được bảo toàn nguyên vẹn.

#### POST `/api/meeting-bookings/{id}/cancel/`
- **Mục đích**: Hủy lịch đặt phòng giải phóng khung giờ.
- **Quyền**: Yêu cầu `change_own_datphonghop` (đối với người đặt) hoặc `change_any_datphonghop` (đối với điều phối viên/quản lý).
- **Payload**:
  ```json
  {
    "cancel_reason": "Thay đổi lịch công tác của ban lãnh đạo"
  }
  ```
- **Cơ chế**: Chuyển `trang_thai` sang `CANCELLED`, ghi nhận lý do hủy vào trường `purpose` kèm ký tự phân tách `\n---\n` (ví dụ `\n---\n<reason>` khi không có mục đích ban đầu, hoặc `<purpose>\n---\n<reason>` khi có mục đích ban đầu). Frontend phân tách chuỗi này để hiển thị chuẩn xác vào khối "Lý do hủy" và không nhầm vào "Mục đích". Khung giờ được giải phóng tức thì cho người dùng khác đặt.
- **Phản hồi**: `200 OK` (kèm dữ liệu `booking`). Không cho phép hủy lịch đã kết thúc hoặc lịch đã hủy từ trước.

---

## 4. Các Quy tắc Nghiệp vụ Bất biến (Business Invariants)

1. **Khung giờ liền kề (Adjacent Bookings) vs Trùng giờ (Overlapping)**:
   - Các cuộc họp liền kề (ví dụ: Cuộc họp A: `09:00 - 10:00`, Cuộc họp B: `10:00 - 11:00`) là **hợp lệ 100%** và nhận `201 Created`.
   - Các trường hợp trùng giờ (giao khoảng đầu, giao khoảng đuôi, bao trùm, nằm gọn bên trong, trùng khớp hoàn toàn) đều bị từ chối với `400 Bad Request` và mã lỗi `meetings.messages.roomTimeConflict`.
2. **Cập nhật không tự xung đột (Self-conflict Exclusion)**:
   - Khi chỉnh sửa tiêu đề, mục đích họp, số lượng người tham gia mà không đổi khung giờ, hệ thống exclude chính ID của booking đang sửa khỏi kiểm tra trùng -> `200 OK`.
3. **An toàn tương tranh (Concurrency & Database Constraints)**:
   - Test `MeetingBookingConcurrencyTestCase` xác nhận kết quả chính xác khi hai request gửi đồng thời: đúng 1 request thành công (`201 Created`), đúng 1 request bị từ chối (`400 Bad Request`), và CSDL tạo duy nhất 1 bản ghi.
   - Lớp chặn chính bảo đảm tính bất biến này là ràng buộc loại trừ PostgreSQL GiST `excl_room_time` ở cấp CSDL (khối `try...except IntegrityError` bắt lỗi và trả về `400 Bad Request`, không bao giờ trả về lỗi 500).
   - Tầng ứng dụng kết hợp khóa `MeetingRoom.objects.select_for_update()` trong khối `transaction.atomic()` để tuần tự hóa giao dịch và trả về thông tin chi tiết của cuộc họp xung đột (`meetings.messages.roomTimeConflict` kèm host, time, title).
4. **Phòng họp nội bộ (`is_public = False`)**:
   - Chỉ người dùng có quyền `change_phonghop` hoặc `is_superuser` mới được phép đặt hoặc sửa lịch vào phòng nội bộ.
   - CBNV bình thường cố tình đặt hoặc sửa lịch vào phòng nội bộ sẽ nhận **`400 Bad Request`** ở tầng serializer validation (`{"room": "meetings.messages.privateRoomForbidden"}`).
5. **Ràng buộc giá trị biên (Boundary Validation)**:
   - Số người tham gia (`attendees_count`):
     - `attendees_count == capacity`: Hợp lệ (`201 Created`).
     - `attendees_count > capacity`: Lỗi `400` (`meetings.messages.capacityExceeded`).
     - `attendees_count <= 0`: Lỗi `400` (`meetings.messages.attendeesMustBePositive`).
   - Khung giờ: `end_time <= start_time` -> Lỗi `400` (`meetings.messages.invalidTimeRange`).
   - Tiêu đề: Bắt buộc, chuỗi rỗng hoặc toàn khoảng trắng -> Lỗi `400` (`meetings.messages.titleRequired`).

---

## 5. Danh mục Mã lỗi i18n Chuẩn (`meetings.messages.*`)

100% phản hồi lỗi API trả về i18n key trong trường `detail` hoặc trường cụ thể của serializer:

| Mã lỗi i18n | HTTP Status | Ngữ cảnh phát sinh |
|---|---|---|
| `meetings.messages.permissionDenied` | 403 Forbidden | Người dùng không đủ quyền thực hiện thao tác |
| `meetings.messages.privateRoomForbidden` | 400 Bad Request | Đặt hoặc dời lịch vào phòng nội bộ khi không có quyền quản lý (trường `room`) |
| `meetings.messages.roomTimeConflict` | 400 Bad Request | Khung giờ bị trùng với một cuộc họp khác đã xác nhận |
| `meetings.messages.bookingInPast` | 400 Bad Request | Tạo lịch hoặc dời lịch về ngày/giờ trong quá khứ |
| `meetings.messages.bookingAlreadyEnded` | 400 Bad Request | Thao tác sửa hoặc hủy lịch họp đã kết thúc |
| `meetings.messages.bookingAlreadyCancelled` | 400 Bad Request | Thao tác sửa hoặc hủy lại lịch họp đã bị hủy |
| `meetings.messages.deleteBookingNotAllowed` | 405 Method Not Allowed | Cố tình gọi DELETE lên lịch đặt phòng |
| `meetings.messages.roomUnavailable` | 400 Bad Request | Đặt phòng đang ở trạng thái bảo trì hoặc tạm khóa |
| `meetings.messages.capacityExceeded` | 400 Bad Request | Số người tham gia vượt quá sức chứa phòng họp |
| `meetings.messages.attendeesMustBePositive` | 400 Bad Request | Số người tham gia `<= 0` |
| `meetings.messages.invalidTimeRange` | 400 Bad Request | Giờ kết thúc nhỏ hơn hoặc bằng giờ bắt đầu |
| `meetings.messages.titleRequired` | 400 Bad Request | Tiêu đề cuộc họp để trống hoặc chỉ có khoảng trắng |
| `meetings.messages.cannotDeleteRoomHasBookings` | 400 Bad Request | Xóa phòng họp đang có dữ liệu đặt phòng liên kết |

---

## 6. Hướng dẫn Chạy Kiểm thử Xác thực (Test Verification)

```bash
# 1. Backend: Chạy toàn bộ 75 unit & regression tests của phân hệ phòng họp
python backend/manage.py test apps.meetings --keepdb

# 2. Frontend: Kiểm tra lint, build và unit tests
pnpm --dir frontend run lint
npx vitest run
pnpm --dir frontend run build

# 3. Kiểm tra tuân thủ i18n & Tokens
node scripts/check-i18n.mjs
```
