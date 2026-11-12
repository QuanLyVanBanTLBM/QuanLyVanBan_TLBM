# RBAC contract (Issue #21)

Hợp đồng phân quyền dùng chung cho toàn dự án. Các nhóm kiểm quyền theo tài liệu này, không tự tạo role hay permission riêng.

Nguồn chuẩn: DDL base của đồ án, nhánh `ddl_base_v0`, file `docs/common/database/release_DDL.sql` (77 quyền, 196 dòng gán quyền; chốt ở Issue #53, bỏ văn bản mật ở PR #81 và Issue #83). Mã quyền, nhóm quyền và ánh xạ nhóm-quyền lấy từ DDL. Tám quyền mà Issue #20/#21/#22 yêu cầu nhưng SQL_Fix4 chưa có (đánh dấu "bổ sung" bên dưới) nay đã nằm trong DDL base; migration `authorization.0002` vẫn thêm chúng một cách idempotent để DB dựng từ bản DDL cũ không thiếu quyền.

## 1. Cơ chế

- Dùng `django.contrib.auth.models.Group` và `Permission` (bảng `auth_group`, `auth_permission`, `auth_group_permissions`, `accounts_employee_groups`, `accounts_employee_user_permissions`). Không có bảng Group/Permission riêng.
- Mã quyền là **codename trần** (ví dụ `export_donvi`), `content_type_id` NULL, kèm cột `module_ten`. Gọi: `user.has_perm("export_donvi")`. Dạng `organizations.export_donvi` cũng được chấp nhận (phần app label bị bỏ qua).
- Backend kiểm quyền: `authorization.backends.RbacBackend` (`AUTHENTICATION_BACKENDS`). Django không tự tạo quyền `add/change/delete/view_<model>` nữa (`create_permissions` bị tắt): quyền mới phải thêm bằng data migration (mục 6).
- Quản trị tối cao (`is_superuser`) luôn có mọi quyền. Tài khoản `is_active = False` (kể cả CBNV `NGHI_VIEC`) không có quyền nào.
- Nhóm `ADMIN` (Quản trị hệ thống) được gán đủ mọi quyền đang có trong bảng `auth_permission` (77/77 ở bản hiện tại). Quyền thêm về sau chỉ vào `ADMIN` khi migration thêm quyền cũng gán cho `ADMIN` (mục 6); nếu quên thì chỉ `is_superuser` mới qua được.
- `has_perm` chỉ trả lời "người này có chức năng đó không". Quy tắc theo dữ liệu (người nhận văn bản, văn bản phạm vi `HAN_CHE`, đơn vị sở hữu hồ sơ, phòng ban của tài liệu...) do nhóm sở hữu dữ liệu tự kiểm thêm trong queryset của mình. `is_superuser` qua mọi kiểm tra `has_perm`, nên không dùng `has_perm` làm điều kiện duy nhất cho dữ liệu cần "cần biết mới được xem".
- Backend là lớp bảo mật chính. Frontend chỉ ẩn/hiện thao tác dựa trên `GET /api/auth/me/permissions/`.
- Chưa đăng nhập: `401`. Đăng nhập nhưng thiếu quyền: `403`, body `{"detail": "<i18n key>"}`.
- `has_perm(codename, obj)` với `obj` khác `None` luôn trả `False`: `RbacBackend` chỉ trả lời quyền chức năng, không có quyền theo từng đối tượng. Đừng dùng `DjangoObjectPermissions` hay `has_perm(..., obj)`; quy tắc theo dữ liệu tự kiểm trong queryset (xem điểm về `has_perm` ở trên).
- Năm nhóm chuẩn (`VT`, `CV`, `TP`, `BGD`, `ADMIN`) không đổi tên và không xóa được (`400`, `roles.messages.groupProtected`); quyền của chúng vẫn chỉnh được, riêng `ADMIN` phải luôn giữ `view/add/change/delete_nhomquyen` (`400`, `roles.messages.adminPermissionsRequired`) để quản trị không tự khóa mình khỏi trang Phân quyền.
- `/api/roles/{id}/` kiểm quyền trước khi tra bản ghi: người thiếu quyền nhận `403` cả với id không tồn tại, nên không dò được id nhóm.

## 2. Cách dùng trong code nhóm khác

```python
from authorization.permissions import require_permission
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

@api_view(["GET"])
@permission_classes([IsAuthenticated, require_permission("view_hoso")])
def hoso_list(request):
    ...
```

View phục vụ nhiều method thì truyền dict `{method: codename}`; quyền được kiểm trước khi view chạy (trước cả khi tra bản ghi), method không có trong dict bị từ chối, `HEAD`/`OPTIONS` dùng quyền của `GET`:

```python
@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated, require_permission({
    "GET": "view_hoso", "PUT": "change_hoso", "PATCH": "change_hoso", "DELETE": "delete_hoso",
})])
def hoso_detail(request, pk):
    ...
```

Với `ViewSet`, chọn quyền theo `self.action` trong `get_permissions()` rồi trả `[IsAuthenticated(), require_permission("<codename>")()]`. Tham số thứ hai là key i18n của thông báo 403 (mặc định `roles.messages.permissionDenied`). Không dùng `is_staff` làm điều kiện cho qua: đó chỉ là quyền vào trang quản trị Django.

Hoặc kiểm trực tiếp: `request.user.has_perm("view_hoso")`. Khóa ngoại tới người dùng dùng `settings.AUTH_USER_MODEL` (`accounts.Employee`).

Trong test: `Permission.objects.get(codename="view_hoso")`, rồi `user.user_permissions.add(...)` hoặc thêm vào `Group` rồi `user.groups.add(group)`.

## 3. API

| Method | Path | Quyền | Mô tả |
|---|---|---|---|
| GET | `/api/roles/` | `view_nhomquyen` | Danh sách nhóm quyền. `?search=`, `?page=`, `?page_size=`, `?all=true` (không phân trang) |
| POST | `/api/roles/` | `add_nhomquyen` | Tạo nhóm, body `{name, permission_ids?}` |
| GET | `/api/roles/{id}/` | `view_nhomquyen` | Chi tiết và `permission_ids` |
| PUT, PATCH | `/api/roles/{id}/` | `change_nhomquyen` | Sửa tên và/hoặc tập quyền |
| DELETE | `/api/roles/{id}/` | `delete_nhomquyen` | Xóa; `400 roles.messages.groupHasUsers` nếu còn user |
| PUT | `/api/roles/{id}/permissions/` | `change_nhomquyen` | Thay toàn bộ tập quyền: `{permission_ids: [...]}` (mảng rỗng = bỏ hết) |
| GET | `/api/permissions/` | `view_nhomquyen` | Toàn bộ quyền: `id, name, codename, module_ten` |
| GET | `/api/auth/me/permissions/` | đăng nhập | `{is_superuser, permissions: [codename, ...]}` của user hiện tại |

Lỗi trả key i18n (`roles.messages.*`), không trả chuỗi cứng. Không API nào trả password hay password hash.

## 4. Danh sách codename chính thức

Tổng cộng 77 quyền. "Bổ sung" = không có trong SQL_Fix4 (8 quyền), hiện đã có trong DDL base và vẫn được `authorization.0002` thêm idempotent.


### Đơn vị, phòng ban

| Codename | Mô tả |
|---|---|
| `view_donvi` | Xem danh sách đơn vị/phòng ban |
| `add_donvi` | Thêm đơn vị/phòng ban |
| `change_donvi` | Sửa đơn vị/phòng ban |
| `delete_donvi` | Xóa đơn vị/phòng ban |
| `export_donvi` | Xuất Excel đơn vị/phòng ban |

### Chức vụ

| Codename | Mô tả |
|---|---|
| `view_chucvu` | Xem danh sách chức vụ |
| `add_chucvu` | Thêm chức vụ |
| `change_chucvu` | Sửa chức vụ |
| `delete_chucvu` | Xóa chức vụ |
| `import_chucvu` | Import file chức vụ (bổ sung) |

### Loại tài liệu biểu mẫu

| Codename | Mô tả |
|---|---|
| `view_loaitailieubieumau` | Xem danh sách loại tài liệu |
| `add_loaitailieubieumau` | Thêm loại tài liệu |
| `change_loaitailieubieumau` | Sửa loại tài liệu |
| `delete_loaitailieubieumau` | Xóa loại tài liệu |

### CBNV

| Codename | Mô tả |
|---|---|
| `view_full_cbnv` | Xem toàn bộ thông tin CBNV (kể cả năm sinh, Nhóm quyền, mật khẩu) |
| `view_list_cbnv` | Xem danh sách CBNV (ẩn field nhạy cảm) |
| `add_cbnv` | Thêm CBNV |
| `change_full_cbnv` | Sửa CBNV (đầy đủ field) |
| `change_self_cbnv` | Sửa thông tin cá nhân của chính mình |
| `delete_cbnv` | Xóa CBNV |
| `approve_password_reset_cbnv` | Duyệt yêu cầu đổi mật khẩu |
| `import_cbnv` | Import file CBNV |

### Văn bản đến

| Codename | Mô tả |
|---|---|
| `view_vanbanden` | Xem danh sách/chi tiết văn bản đến |
| `add_vanbanden` | Thêm văn bản đến |
| `change_vanbanden` | Sửa văn bản đến |
| `delete_vanbanden` | Xóa văn bản đến |
| `import_vanbanden` | Import file văn bản đến |
| `export_vanbanden` | Xuất Excel văn bản đến |
| `view_read_log_vanbanden` | Xem log user đã xem văn bản đến |
| `send_mail_all_vanbanden` | Gửi mail toàn hệ thống (văn bản đến) |

### Văn bản đi

| Codename | Mô tả |
|---|---|
| `view_vanbandi` | Xem danh sách/chi tiết văn bản đi |
| `add_vanbandi` | Thêm văn bản đi |
| `change_vanbandi` | Sửa văn bản đi |
| `delete_vanbandi` | Xóa văn bản đi |
| `import_vanbandi` | Import file văn bản đi |
| `export_vanbandi` | Xuất Excel văn bản đi |
| `view_read_log_vanbandi` | Xem log user đã xem văn bản đi |
| `send_mail_all_vanbandi` | Gửi mail toàn hệ thống (văn bản đi) |

Văn bản mật đã bỏ khỏi DDL base (PR #81). Bốn quyền `*_vanbanmat` không còn; DB đã seed từ trước được migration `authorization.0003` gỡ cả quyền lẫn dòng gán quyền.

### Hồ sơ

| Codename | Mô tả |
|---|---|
| `view_hoso` | Xem danh mục hồ sơ |
| `add_hoso` | Lập/Thêm hồ sơ |
| `change_hoso` | Sửa hồ sơ |
| `delete_hoso` | Xóa hồ sơ |

### Tài liệu, biểu mẫu

| Codename | Mô tả |
|---|---|
| `view_tailieu` | Xem tài liệu, biểu mẫu |
| `add_tailieu` | Thêm tài liệu, biểu mẫu |
| `change_tailieu` | Sửa tài liệu, biểu mẫu |
| `delete_tailieu` | Xóa tài liệu, biểu mẫu |

### Trình ký

| Codename | Mô tả |
|---|---|
| `view_trinhky` | Xem văn bản trình ký |
| `add_trinhky` | Tạo trình ký |
| `sign_trinhky` | Ký (đúng lượt trong sơ đồ) |
| `manage_signing_process` | Quản lý quy trình trình ký |
| `send_trinhky` | Gửi trình ký / Nộp lại lượt trình |
| `cancel_trinhky` | Hủy yêu cầu trình ký |
| `view_signing_audit` | Xem nhật ký kiểm toán trình ký |

### Công việc

| Codename | Mô tả |
|---|---|
| `view_congviec` | Xem công việc (chung) |
| `view_all_congviec` | Xem tất cả công việc (toàn hệ thống) |
| `view_dept_congviec` | Xem công việc theo phòng ban |
| `add_congviec` | Thêm/Giao việc |
| `change_congviec` | Sửa công việc |
| `delete_congviec` | Xóa công việc |
| `approve_congviec` | Duyệt / Hủy duyệt công việc |

### Phòng họp (danh mục)

| Codename | Mô tả |
|---|---|
| `view_schedule_phonghop` | Xem lịch phòng họp |
| `add_phonghop` | Thêm phòng họp (bổ sung) |
| `change_phonghop` | Sửa phòng họp (bổ sung) |
| `delete_phonghop` | Xóa phòng họp (bổ sung) |

### Đặt phòng họp

| Codename | Mô tả |
|---|---|
| `add_datphonghop` | Đặt phòng họp |
| `change_own_datphonghop` | Sửa/Hủy lịch do chính mình đặt |
| `change_any_datphonghop` | Sửa/Hủy mọi lịch đặt phòng (QT) |

### Sinh nhật

| Codename | Mô tả |
|---|---|
| `view_sinhnhat` | Xem danh sách sinh nhật |

### Chatbox AI

| Codename | Mô tả |
|---|---|
| `use_aiassistant` | Sử dụng chatbot (chỉ trả lời nội dung người hỏi có quyền Xem) |

### Phân quyền

| Codename | Mô tả |
|---|---|
| `view_nhomquyen` | Xem danh sách nhóm quyền (bổ sung) |
| `add_nhomquyen` | Thêm nhóm quyền (bổ sung) |
| `change_nhomquyen` | Sửa nhóm quyền (bổ sung) |
| `delete_nhomquyen` | Xóa nhóm quyền (bổ sung) |

### Đối chiếu tên trong Issue #21 với DDL

Khi Issue và DDL khác tên, **DDL là chuẩn** (đồ án chung chốt theo DDL base ở Issue #53):

| Tên trong Issue #21 | Dùng trong hệ thống |
|---|---|
| `view_cbnv` | `view_list_cbnv` |
| `view_sensitive_cbnv` | `view_full_cbnv` |
| `change_cbnv` | `change_full_cbnv` (sửa đầy đủ) hoặc `change_self_cbnv` (chính mình) |
| `view_phonghop` | `view_schedule_phonghop` |
| `view_datphonghop` | `view_schedule_phonghop` |
| `cancel_datphonghop` | `change_own_datphonghop` (lịch của mình) hoặc `change_any_datphonghop` (mọi lịch) |
| `approve_datphonghop` | chưa dùng (đặt phòng không có bước duyệt trong DDL) |

## 5. Nhóm quyền chuẩn

- `VT`: Văn thư
- `CV`: Chuyên viên
- `TP`: Trưởng phòng
- `BGD`: Ban Giám đốc
- `ADMIN`: Quản trị hệ thống

Ánh xạ nhóm-quyền mặc định lấy từ DDL base (206 dòng, gồm các quyền bổ sung gán cho `ADMIN`). Quản trị chỉnh lại qua trang Nhóm quyền (`/roles`).

## 6. Thêm quyền mới cho model của nhóm mình

Tạo data migration trong app của nhóm (dùng SQL thô vì `auth_permission.module_ten` là NOT NULL), idempotent:

```python
def add_permissions(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO auth_permission (name, codename, module_ten) "
            "SELECT %s, %s, %s WHERE NOT EXISTS (SELECT 1 FROM auth_permission WHERE codename = %s)",
            ["Tên hiển thị của quyền", "export_vidu", "Tên module", "export_vidu"],
        )
        # Gán cho nhóm ADMIN để quản trị hệ thống dùng được quyền mới
        cursor.execute(
            "INSERT INTO auth_group_permissions (group_id, permission_id) "
            "SELECT g.id, p.id FROM auth_group g, auth_permission p "
            "WHERE g.ma_nhom_quyen = 'ADMIN' AND p.codename = %s "
            "AND NOT EXISTS (SELECT 1 FROM auth_group_permissions x "
            "WHERE x.group_id = g.id AND x.permission_id = p.id)",
            ["export_vidu"],
        )
```

Mã `export_vidu` ở trên chỉ là tên minh họa, không phải quyền có thật; thay bằng codename của model nhóm mình. Migration phải khai báo `dependencies = [("authorization", "0002_rbac_standard_data")]` để nhóm `ADMIN` đã tồn tại khi chạy. Ánh xạ cho các nhóm khác (`VT`, `CV`, `TP`, `BGD`) làm tương tự theo nhu cầu nghiệp vụ.

`codename` phải duy nhất toàn hệ thống. Đặt tên theo quy ước `<hành động>_<đối tượng>` tiếng Việt không dấu viết liền, và đưa vào DDL base bằng PR vào nhánh `ddl_base_v0` (ghi `Refs #53`, merge khi workflow `DDL Check` pass), vì thay đổi DDL chỉ đi qua nhánh đó (Issue #68).

## 7. Dựng CSDL

Quy trình đã kiểm chứng trên PostgreSQL dựng từ DDL base (và trước đó trên SQL_Fix4); cũng là quy trình ở Issue #68 mục 2:

1. Tạo CSDL từ `docs/common/database/release_DDL.sql` (nhánh `ddl_base_v0`).
2. `python manage.py migrate contenttypes`
3. `python manage.py migrate auth --fake`
4. `python manage.py migrate accounts --fake` và `python manage.py migrate organizations --fake`
5. `python manage.py migrate authorization`
6. `python manage.py migrate`

App có bảng trong DDL phải `--fake` migration nền ở bước 4. Khi Sinh nhật (#46) và Phòng họp (#51) đã merge vào nhánh nhóm, thêm `python manage.py migrate birthdays --fake` và `python manage.py migrate meetings --fake` vào bước 4; thiếu bước này thì bước 6 báo `relation "birthdays_birthdayemaillog" already exists` (hoặc `meetings_meetingroom`). Chưa merge thì không chạy hai lệnh này (app chưa có migration).

