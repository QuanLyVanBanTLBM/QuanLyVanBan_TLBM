# Hợp đồng API & Hướng dẫn bàn giao phân hệ Cán bộ Nhân viên (Issue #24)

Tài liệu đặc tả kỹ thuật, hợp đồng API và hướng dẫn kiểm thử phân hệ Quản lý Cán bộ Nhân viên (CBNV) theo yêu cầu Issue #24 thuộc Nhóm 7 (Hệ thống & Họp & Sinh nhật).

Nguồn chuẩn:
- DDL base của đồ án: `docs/common/database/release_DDL.sql`
- Phân quyền RBAC base: `docs/modules/07_system_admin_meetings/api-contract-issue-21.md`
- Đặc tả kiêm nhiệm, danh mục chức vụ và 82 đơn vị phòng ban: `SQL_Fix4`
- Tác giả phụ trách: Lê Duy Khánh (`leduykhanhdevs`)

---

## 1. Danh sách quyền liên quan (RBAC)

Phân hệ sử dụng các quyền chuẩn theo `auth_permission` (không dùng role tự chế, không kiểm tra theo object):

| Mã quyền (codename) | Tên hiển thị | Nhóm mặc định | Mô tả |
|---|---|---|---|
| `view_list_cbnv` | Xem danh sách CBNV | VT, CV, TP, BGD, ADMIN | Xem danh sách CBNV cơ bản (ngày sinh bị che `19xx`/`20xx`, ẩn CBNV nội bộ) |
| `view_full_cbnv` | Xem thông tin chi tiết CBNV | ADMIN | Xem đầy đủ ngày sinh (không che), xem CBNV nội bộ (`is_public = False`), xem chi tiết nhóm quyền |
| `change_full_cbnv` | Quản lý CBNV (tạo, sửa đầy đủ) | ADMIN | Thêm mới, chỉnh sửa mọi thông tin phòng ban, chức vụ, kiêm nhiệm, trạng thái làm việc |
| `change_self_cbnv` | Sửa thông tin cá nhân | VT, CV, TP, BGD, ADMIN | Cán bộ tự cập nhật số điện thoại, email, ngày sinh của chính mình |
| `delete_cbnv` | Xóa cán bộ nhân viên | ADMIN | Xóa tài khoản CBNV khỏi hệ thống (bắt buộc nhập mật khẩu xác nhận) |
| `export_cbnv` | Xuất Excel danh sách CBNV | TP, BGD, ADMIN | Xuất danh bạ điện tử phân cấp công ty ra tệp Excel `.xlsx` |
| `import_cbnv` | Import file cán bộ nhân viên | ADMIN | Nhập danh sách CBNV hàng loạt từ tệp Excel `.xlsx` |

> [!NOTE]
> - Nhân viên thường (`VT`, `CV`) **không có quyền** `export_cbnv` và `import_cbnv`.
> - Quyền `export_cbnv` được tạo và cấp phát tự động, lũy đẳng qua migration `backend/apps/authorization/migrations/0007_add_export_cbnv_permission.py`.

---

## 2. Danh sách Endpoints API

Tất cả các endpoint đều yêu cầu xác thực (`IsAuthenticated`) qua header `Authorization: Bearer <access_token>`.

### 2.1. Danh sách CBNV

- **URL**: `GET /api/accounts/employees/`
- **Quyền yêu cầu**: `view_list_cbnv` (hoặc `view_full_cbnv`, hoặc `is_superuser`)
- **Query Parameters**:
  - `search` (string): Tìm kiếm không phân biệt hoa thường theo Họ tên, Email, Username, Số điện thoại.
  - `don_vi_id` (int): Lọc theo đơn vị/phòng ban chính.
  - `khoi_id` (int): Lọc theo Khối / Khu vực.
  - `chuc_vu_id` (int): Lọc theo Chức vụ chính.
  - `trang_thai` (string): `LAM_VIEC` hoặc `NGHI_VIEC`.
  - `is_public` (boolean): `true` hoặc `false`.
  - `ordering` (string): Trường sắp xếp (cho phép `ho_ten`, `-ho_ten`, `email`, `-email`, `don_vi__stt_uu_tien`, `chuc_vu__display_order`). Trường `ngay_sinh` chỉ cho phép khi có quyền `view_full_cbnv`.
  - `all` (boolean): Nếu `true`, trả về toàn bộ mảng không phân trang; nếu `false` (mặc định), trả về phân trang 10 dòng/trang.
- **Thứ tự sắp xếp mặc định**:
  ```python
  queryset.order_by("don_vi__stt_uu_tien", "chuc_vu__display_order", "ho_ten", "id")
  ```
- **Quy tắc che dữ liệu (Data Masking)**:
  - Người dùng **chỉ có** `view_list_cbnv`:
    - `ngay_sinh` hiển thị dạng `DD/MM/----`.
    - `is_birthday_masked: true`.
    - `nhom_quyen`: Ẩn (trả về rỗng).
    - `has_sensitive_permission: false`.
    - `is_public = False`: Bị loại bỏ khỏi danh sách (trừ trường hợp tự xem chính mình).
  - Người dùng **có** `view_full_cbnv` hoặc `is_superuser`:
    - `ngay_sinh` trả về đầy đủ định dạng `DD/MM/YYYY`.
    - `ngay_sinh_iso` trả về định dạng chuẩn ISO `YYYY-MM-DD`.
    - `is_birthday_masked: false`.
    - `nhom_quyen`: Trả về danh sách nhóm quyền đầy đủ.

### 2.2. Chi tiết CBNV

- **URL**: `GET /api/accounts/employees/{id}/`
- **Quyền yêu cầu**: `view_list_cbnv` hoặc người dùng tự xem chính mình (`request.user.id == id`).
- **Phản hồi**:
  ```json
  {
    "id": 10,
    "username": "an.nguyen",
    "email": "an.nguyen@baolong.vn",
    "ho_ten": "Nguyễn Văn An",
    "ngay_sinh": "15/05/1990",
    "ngay_sinh_iso": "1990-05-15",
    "is_birthday_masked": false,
    "don_vi_id": 3,
    "don_vi_ten": "Ban Khách hàng Doanh nghiệp",
    "khoi_ten": "Khối Kinh doanh",
    "chuc_vu_id": 6,
    "chuc_vu_ten": "Trưởng phòng",
    "chuc_danh": "Trưởng phòng Kinh doanh",
    "sdt": "0912345678",
    "trang_thai": "LAM_VIEC",
    "trang_thai_display": "Đang làm việc",
    "is_active": true,
    "is_public": true,
    "ghi_chu": "",
    "nhom_quyen": [
      { "id": 3, "name": "Trưởng phòng" }
    ],
    "assignments": [
      {
        "id": 1,
        "don_vi_id": 5,
        "don_vi_ten": "Ban Khách hàng Cá nhân",
        "khoi_ten": "Khối Kinh doanh",
        "chuc_vu_id": 7,
        "chuc_vu_ten": "Phó phòng",
        "chuc_danh": "Phó phòng phụ trách Kênh số",
        "created_at": "2026-10-18T10:00:00Z"
      }
    ]
  }
  ```

### 2.3. Thêm mới CBNV

- **URL**: `POST /api/accounts/employees/`
- **Quyền yêu cầu**: `change_full_cbnv` (hoặc `is_superuser`)
- **Body**:
  ```json
  {
    "ho_ten": "Trần Thị Bích",
    "ngay_sinh": "1994-11-20",
    "email": "bich.tran@baolong.vn",
    "sdt": "0987654321",
    "don_vi_id": 4,
    "chuc_vu_id": 8,
    "chuc_danh": "Chuyên viên Pháp lý",
    "username": "bich.tran",
    "password": "Password@123",
    "nhom_quyen_ids": [2],
    "trang_thai": "LAM_VIEC",
    "is_public": true,
    "ghi_chu": "Nhân sự mới",
    "assignments": [
      {
        "don_vi_id": 7,
        "chuc_vu_id": 8,
        "chuc_danh": "Hỗ trợ pháp chế kiêm nhiệm"
      }
    ]
  }
  ```
- **Xử lý đặc biệt**:
  - `username`: Nếu bỏ trống, hệ thống tự động sinh username từ phần tên trước `@` của email (`local_part` + số thứ tự nếu trùng).
  - `password`: Nếu bỏ trống, hệ thống tự động sinh ngẫu nhiên mật khẩu mạnh 10 ký tự. Mật khẩu được băm an toàn lưu vào DB, đồng thời chỉ được trả về **duy nhất 1 lần** trong trường `temporary_password` của response để giao diện hiển thị sao chép cho quản trị viên. Không lưu mật khẩu thô vào DB hay in ra log.
  - `nhom_quyen_ids`: Nếu bỏ trống hoặc truyền rỗng `[]`, hệ thống tự động gán nhóm quyền mặc định theo chức vụ (`chuc_vu_id`) dựa trên mã `ma_nhom_quyen` qua `authorization.GroupInfo` (ví dụ: Quản trị viên -> `ADMIN`, Tổng Giám đốc/Lãnh đạo cơ quan -> `BGD`, Trưởng phòng -> `TP`, Chuyên viên -> `CV`, Văn thư -> `VT`, Trợ lý TGĐ -> `CV` + `TLBGD`, Kiểm toán viên -> `CV` + `KT`). Nhóm chưa tồn tại trong DB thì bỏ qua, không gây lỗi. Nếu chọn nhóm thủ công thì tôn trọng lựa chọn thủ công, không tự gán.
- **Mã phản hồi**: `201 Created`

### 2.4. Cập nhật CBNV

- **URL**: `PATCH /api/accounts/employees/{id}/` hoặc `PUT /api/accounts/employees/{id}/`
- **Quyền yêu cầu & Ràng buộc**:
  - Người dùng có `change_full_cbnv` hoặc `is_superuser`: Có quyền sửa toàn bộ thông tin.
  - Người dùng **không có** `change_full_cbnv`: Chỉ được sửa chính mình (`id == request.user.id`) và chỉ được truyền 3 trường thông tin cá nhân: `sdt`, `email`, `ngay_sinh`. Bất kỳ trường nào khác gửi lên sẽ nhận lỗi `403 roles.messages.permissionDenied`.
  - **Bảo vệ vô hiệu hóa tài khoản**:
    - Không được tự khóa/chuyển trạng thái nghỉ việc chính mình -> `400 employees.messages.cannotDeactivateSelf`.
    - Không được khóa tài khoản `is_superuser` nếu người gọi không phải superuser -> `403 employees.messages.cannotDeactivateSuperuser`.
- **Mã phản hồi**: `200 OK`

### 2.5. Xóa CBNV & Cơ chế bảo vệ Văn thư duy nhất

- **URL**: `DELETE /api/accounts/employees/{id}/`
- **Quyền yêu cầu**: `delete_cbnv` (hoặc `is_superuser`)
- **Request Body (JSON)**:
  ```json
  {
    "password": "..."
  }
  ```
  - `password` (string, bắt buộc): Mật khẩu đăng nhập của chính người thực hiện thao tác xóa để chống bấm nhầm/chiếm quyền phiên làm việc (truyền trong body JSON, không truyền qua query string URL để tránh ghi log).
- **Quy tắc kiểm tra nghiệp vụ**:
  1. Thiếu hoặc sai mật khẩu xác thực: Trả về `400 employees.messages.invalidPassword`.
  2. Tự xóa tài khoản của chính mình: Trả về `400 employees.messages.cannotDeleteSelf`.
  3. Xóa Superuser khi người xóa không phải Superuser: Trả về `403 employees.messages.cannotDeleteSuperuser`.
  4. Xóa Superuser đang hoạt động cuối cùng: Trả về `400 employees.messages.cannotDeleteLastSuperuser`.
  5. Xóa CBNV có dữ liệu liên kết được bảo vệ (văn bản, công việc...): Trả về `400 employees.messages.cannotDeleteProtected`.

### 2.6. Xuất danh bạ Excel phân cấp

- **URL**: `GET /api/accounts/employees/export/`
- **Quyền yêu cầu**: `export_cbnv` (Nhóm `TP`, `BGD`, `ADMIN`). Nhân viên thường bị chặn `403`.
- **Định dạng tệp**: File Excel chuẩn `.xlsx` (MIME: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`).
- **Cấu trúc phân cấp và hiển thị**:
  1. Header bảng danh bạ điện tử với 6 cột: STT, Họ và tên, Chức vụ, Chức danh, Số điện thoại, Email.
  2. Phân nhóm theo 16 Khối / Khu vực theo đúng thứ tự hiển thị: Dòng tiêu đề Khối in hoa, in đậm, nền xanh dương thương hiệu (`#1E3A8A`), chữ trắng.
  3. Phân nhóm theo Đơn vị / Phòng ban theo `stt_uu_tien`: Dòng tiêu đề Đơn vị in đậm, nền xám nhạt (`#F1F5F9`), hiển thị thông tin kèm theo (Địa chỉ, Điện thoại, Email phòng).
  4. Danh sách cán bộ trực thuộc đơn vị được sắp xếp theo thứ tự ưu tiên chức vụ (`Position.display_order` tăng dần). STT tự động đếm lại từ 1 ở đầu mỗi đơn vị.
  5. Cán bộ kiêm nhiệm: Xuất hiện dưới từng đơn vị kiêm nhiệm, chức vụ kiêm nhiệm được ghi rõ kèm nhãn `(Kiêm nhiệm)`.
  6. Lọc dữ liệu: Chỉ xuất CBNV `trang_thai = 'LAM_VIEC'` và `is_active = True`. Đơn vị nội bộ (`is_public = False`) và CBNV thuộc đơn vị nội bộ chỉ được hiển thị nếu người xuất có quyền `change_donvi` hoặc `is_superuser`. Loại trừ tài khoản superuser / quản trị hệ thống (`username = 'admin'` hoặc `email = 'admin@baolong.vn'`) khỏi danh bạ xuất bản.
  7. **An toàn CSV/Formula Injection**: Mọi giá trị bắt đầu bằng `=`, `+`, `-`, `@` được ép kiểu chuỗi an toàn (`data_type = 's'`) bằng `openpyxl`, triệt tiêu rủi ro thực thi lệnh macro/DDE nguy hiểm.

### 2.7. Nhập CBNV từ Excel

- **URL**: `POST /api/accounts/employees/import/`
- **Quyền yêu cầu**: `import_cbnv` (Nhóm `ADMIN`).
- **Dữ liệu gửi**: `multipart/form-data` chứa `file` (.xlsx).
- **Quy tắc xử lý**:
  - Hỗ trợ định dạng `.xlsx` tiêu chuẩn (OpenPyXL). Từ chối tệp không có đuôi `.xlsx` (bao gồm tệp `.xls` nhị phân cũ).
  - Giao dịch nguyên tử (ACID `transaction.atomic()`): Nếu bất kỳ dòng nào không hợp lệ (sai ngày sinh, sai định dạng điện thoại, trùng email...), toàn bộ thao tác import sẽ được rollback an toàn và trả về lỗi chi tiết theo từng dòng (ví dụ `Dòng 4: Email đã tồn tại`).

### 2.8. Tải tệp Excel mẫu

- **URL**: `GET /api/accounts/employees/template/`
- **Quyền yêu cầu**: `import_cbnv` (hoặc `view_list_cbnv`).
- **Mục đích**: Tải tệp `.xlsx` có đầy đủ tiêu đề cột bắt buộc, dòng hướng dẫn định dạng và 2 dòng dữ liệu mẫu chuẩn.

---

## 3. Cấu trúc Kiêm nhiệm Đa đơn vị (`EmployeeAssignment`)

Cán bộ nhân viên có thể đồng thời đảm nhiệm công tác tại nhiều phòng ban / chức vụ khác nhau. Phân hệ ánh xạ đúng bảng `accounts_employee_assignment` trong DDL:

```sql
CREATE TABLE accounts_employee_assignment (
    id SERIAL PRIMARY KEY,
    employee_id INTEGER NOT NULL REFERENCES accounts_employee(id) ON DELETE CASCADE,
    don_vi_id INTEGER NOT NULL REFERENCES organizations_donvi(id) ON DELETE RESTRICT,
    chuc_vu_id INTEGER NOT NULL REFERENCES accounts_position(id) ON DELETE RESTRICT,
    chuc_danh VARCHAR(150),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    CONSTRAINT uq_employee_assignment UNIQUE (employee_id, don_vi_id, chuc_vu_id)
);
```

- **Ràng buộc nghiệp vụ kiêm nhiệm**:
  - Không được kiêm nhiệm tại chính Đơn vị chính (`don_vi_id == primary_unit_id`).
  - Không được tạo 2 dòng kiêm nhiệm trùng cùng một Đơn vị trong danh sách.
  - Đơn vị và Chức vụ đang có cán bộ kiêm nhiệm được bảo vệ bởi `on_delete=models.PROTECT`, không thể xóa tùy tiện.

---

## 4. Danh mục Chức vụ (Tham chiếu `accounts_position`)

Phân hệ CBNV (Issue #24) tham chiếu trực tiếp danh mục chức vụ từ bảng `accounts_position` (do nhóm trưởng phụ trách và quản lý theo phân hệ Chức vụ). Thứ tự ưu tiên hiển thị và sắp xếp nhân sự trên toàn bộ hệ thống được áp dụng theo trường `chuc_vu__display_order` (từ nhỏ đến lớn) của bảng `accounts_position`.

---

## 5. Hướng dẫn Chạy Kiểm thử (Test Suite)

### 5.1. Backend Tests (Django Test Runner)
Chạy toàn bộ 62 test cases kiểm tra nghiệp vụ CBNV, phân quyền RBAC, Excel và Migration:
```powershell
python backend/manage.py test apps.accounts.test_employees
```

### 5.2. Frontend Tests (Vitest)
Chạy toàn bộ kiểm thử giao diện phân hệ CBNV và cơ chế xoay vòng Refresh Token:
```powershell
cd frontend
npm test -- EmployeesPage.test.tsx authService.test.ts --run
```

### 5.3. Kiểm tra i18n & Build Production
Đảm bảo 100% bản dịch đa ngôn ngữ khớp key và không có lỗi TypeScript:
```powershell
cd frontend
npm run check:i18n
npm run build
```
