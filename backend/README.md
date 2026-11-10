# TLBM SYSTEM — BACKEND API SERVICE
> **Phân hệ Máy chủ & API Dữ liệu (Django 6.1 + Python 3.12)**  
> **Dự án**: Quản Lý Văn Bản và Tài Liệu (QLVB&TL) — Trường CĐ CNTT TP.HCM (ITC)

---

## 🛠️ 1. Công nghệ & Yêu cầu môi trường

- **Framework**: Django 6.1.x (Python Web Framework)
- **Python**: Bắt buộc Python 3.12 trở lên (Django 6.1 không hỗ trợ Python thấp hơn)
- **Database**: PostgreSQL 16 (Docker Compose cho local, schema từ `docs/common/database/release_DDL.sql`)
- **API Architecture**: RESTful API, JSON responses

---

## 📂 2. Cấu trúc thư mục Backend

```text
backend/
├── config/                     # Cấu hình dự án Django chính
│   ├── settings.py             # Cấu hình Database, Installed Apps, Middleware, CORS
│   ├── urls.py                 # Định tuyến API cấp cao nhất
│   ├── wsgi.py                 # Cổng WSGI chạy Production
│   └── asgi.py                 # Cổng ASGI hỗ trợ Async / WebSocket
│
├── apps/                       # Các ứng dụng nghiệp vụ Django
│   ├── birthdays/              # Module dữ liệu sinh nhật CBNV (Nhóm 7 / Dashboard Nhóm 1)
│   └── ...                     # Các module khác đang tích hợp (documents, records,...)
│
└── manage.py                   # Script quản trị lệnh Django CLI
```

---

## 🚀 3. Hướng dẫn chạy local

Quy trình setup, chạy hằng ngày, test và lệnh DB nằm ở mục "Cài đặt và chạy local" trong `README.md` gốc. Chạy mọi lệnh `pnpm` từ thư mục gốc; backend không chạy trực tiếp bằng `python manage.py` vì kết nối DB do `scripts/project.mjs` đặt (dùng `pnpm manage <lệnh>`).

- API Backend: `http://127.0.0.1:8000/`
- Django Admin: `http://127.0.0.1:8000/admin/`

---

## 🔗 4. Kết nối với Frontend React

- Frontend gọi đến Backend qua base URL: `http://127.0.0.1:8000/`
- Cấu hình CORS đã được thiết lập sẵn trong `config/settings.py` cho phép nguồn `http://localhost:<cổng>` và `http://127.0.0.1:<cổng>`.

---

## 🧪 5. Đặc tả API & Kịch bản Kiểm thử Tham chiếu (Test Reference & API Contracts)

> **Lưu ý trong giai đoạn phát triển**: Để giữ mã nguồn Backend tinh gọn và đúng chuẩn trạng thái ban đầu, các kịch bản kiểm thử đơn vị được lưu trữ tại tài liệu này nhằm làm tài liệu tham chiếu (Contract Specification) cho các lập trình viên Backend khi tiếp tục hoàn thiện nghiệp vụ.

### 5.1. Phân hệ Xác thực & Tài khoản (`apps.accounts`)

#### Danh sách API Endpoints:
| Endpoint | Method | Quyền hạn | Mô tả |
| :--- | :---: | :---: | :--- |
| `/api/auth/login/` | `POST` | Công khai | Đăng nhập cấp JWT Access & Refresh Token |
| `/api/auth/profile/` | `GET` | `IsAuthenticated` | Lấy thông tin hồ sơ cán bộ đăng nhập |
| `/api/auth/change-password/` | `POST` | `IsAuthenticated` | Đổi mật khẩu cá nhân (tối thiểu 8 ký tự) |
| `/api/auth/logout/` | `POST` | `IsAuthenticated` | Đăng xuất và đưa Refresh Token vào blacklist |

#### Bộ kịch bản kiểm thử mẫu (`AccountsAPITests`):
1. **`test_login_success`**: Đăng nhập đúng username/password ➔ Trả về `200 OK`, token JWT, payload `user` chuẩn hỗ trợ cả camelCase (`fullName`, `roleTitle`, `unit`) và snake_case.
2. **`test_login_invalid_credentials`**: Đăng nhập sai mật khẩu ➔ Trả về `401 Unauthorized` và thông báo lỗi tiếng Việt.
3. **`test_profile_unauthorized`**: Truy cập profile khi thiếu Header Bearer ➔ Trả về `401 Unauthorized`.
4. **`test_profile_authorized`**: Truy cập profile khi có token hợp lệ ➔ Trả về `200 OK` với thông tin cá nhân.
5. **`test_change_password_wrong_old_password`**: Nhập sai mật khẩu cũ ➔ Trả về `400 Bad Request` (*"Mật khẩu hiện tại không chính xác!"*).
6. **`test_change_password_short_new_password`**: Mật khẩu mới dưới 8 ký tự ➔ Trả về `400 Bad Request`.
7. **`test_change_password_success`**: Đổi mật khẩu hợp lệ ➔ Trả về `200 OK`.
8. **`test_logout`**: Gửi yêu cầu đăng xuất ➔ Trả về `200 OK`.

<details>
<summary><b>👉 Xem mã nguồn kiểm thử mẫu (Python TestCase)</b></summary>

```python
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from accounts.models import StaffProfile


class AccountsAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="admin",
            password="AdminPassword@123",
            email="quantri@donvi.gov.vn",
        )
        self.profile = StaffProfile.objects.create(
            user=self.user,
            full_name="Quản Trị Viên Hệ Thống",
            department="Văn phòng Trung tâm",
            position="Quản trị viên tối cao",
            role="admin",
        )

    def test_login_success(self):
        response = self.client.post(
            "/api/auth/login/",
            {"username": "admin", "password": "AdminPassword@123"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data.get("success"))
        self.assertIn("token", response.data)
        self.assertEqual(response.data["user"]["username"], "admin")

    def test_login_invalid_credentials(self):
        response = self.client.post(
            "/api/auth/login/",
            {"username": "admin", "password": "WrongPassword"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_profile_unauthorized(self):
        response = self.client.get("/api/auth/profile/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_profile_authorized(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/auth/profile/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["fullName"], "Quản Trị Viên Hệ Thống")

    def test_change_password_wrong_old_password(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/auth/change-password/",
            {"old_password": "WrongPassword@123", "new_password": "NewSecurePassword@456"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_change_password_short_new_password(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/auth/change-password/",
            {"old_password": "AdminPassword@123", "new_password": "123"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_change_password_success(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/auth/change-password/",
            {"old_password": "AdminPassword@123", "new_password": "NewSecurePassword@456"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_logout(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post("/api/auth/logout/", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
```
</details>

---

### 5.2. Phân hệ Bảng điều khiển (`apps.dashboard`)

#### Danh sách API Endpoints:
| Endpoint | Method | Quyền hạn | Mô tả |
| :--- | :---: | :---: | :--- |
| `/api/dashboard/overview/` | `GET` | `IsAuthenticated` | Cung cấp KPI, văn bản mới, phòng họp hôm nay, sinh nhật |

#### Bộ kịch bản kiểm thử mẫu (`DashboardAPITests`):
1. **`test_overview_unauthorized`**: Kiểm tra chặn `401 Unauthorized` khi chưa có JWT Token.
2. **`test_overview_authorized_contract`**: Kiểm tra cấu trúc dữ liệu theo hợp đồng API:
   - `kpis`: `incomingCount`, `outgoingCount`, `tasksCount`.
   - Danh sách mảng: `recentIncoming`, `recentOutgoing`, `tasks`, `meetingRooms`, `birthdays`.
3. **`test_overview_documents_and_meetings_empty_until_modules_wired`**: Khối văn bản và phòng họp rỗng với mọi vai trò.
4. **`test_overview_has_no_confidential_data`**: Không còn khóa văn bản mật.
5. **`test_dashboard_defines_no_models`**: App không tạo bảng riêng.
6. **`test_overview_birthdays_today_and_tomorrow`**: Sinh nhật hôm nay và ngày mai đọc từ bảng nhân viên.

Ghi chú nguồn dữ liệu: app `dashboard` không có model riêng. Khối văn bản và phòng họp trả rỗng cho tới khi nối với `documents_*` (qua `van_ban_xem_duoc` của Nhóm 2) và `meetings_*` (Nhóm 7). Mã kiểm thử: `backend/apps/dashboard/tests.py`.

---

### 5.3. Hướng dẫn thực thi kiểm thử cục bộ
Khi các nhóm Backend tiếp tục phát triển:
1. Tạo hoặc sao chép các hàm test vào `backend/apps/<tên_app>/tests.py`.
2. Chạy lệnh tại thư mục gốc:
   ```bash
   pnpm test:backend accounts
   pnpm test:backend dashboard
   ```

### 5.4. Email chúc mừng sinh nhật

Ứng dụng dùng backend email console nếu chưa cấu hình SMTP. Để gửi email thật, đặt các biến sau trong `.env` ở thư mục gốc dự án:

```dotenv
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_USE_TLS=true
EMAIL_HOST_USER=account@example.com
EMAIL_HOST_PASSWORD=<secret>
DEFAULT_FROM_EMAIL=account@example.com
```

Không commit `.env` hoặc mật khẩu SMTP. `BRAND_NAME` và `ORGANIZATION_NAME` có thể đặt để đổi thương hiệu trong tiêu đề và nội dung thư; mặc định là `Bảo Long Insurance`.

Chạy thủ công tại thư mục gốc:

```bash
pnpm manage send_birthday_emails
pnpm manage send_birthday_emails --date=YYYY-MM-DD
```

`--allow-locmem` chỉ dành cho kiểm thử. Kết quả gửi được ghi trong `birthdays_birthdayemaillog`; hiện API nhật ký chỉ cho superuser xem cho đến khi DDL bổ sung quyền riêng.

Trên môi trường deploy `/srv/qlvb`, workflow `.github/workflows/birthday-email.yml` chạy lệnh gửi hằng ngày lúc 08:00 theo giờ Việt Nam (01:00 UTC). Workflow dùng các GitHub Actions secrets `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_SSH_PRIVATE_KEY` và `DEPLOY_KNOWN_HOSTS` đã dùng cho deploy, chờ khóa deploy trước khi chạy bản release hiện tại, rồi nạp cấu hình từ `/etc/qlvb/backend.env`. Đầu ra chi tiết được ghi vào `/srv/qlvb/birthday-email.log` với quyền chỉ chủ sở hữu đọc; log Actions chỉ ghi trạng thái chung để tránh lộ dữ liệu nhân viên. Nhật ký theo từng người vẫn được lưu trong `birthdays_birthdayemaillog`.

Workflow lịch chạy trên nhánh mặc định của repository. Nếu tác vụ thất bại, kiểm tra log riêng trên máy chủ và nhật ký email trong ứng dụng; xác nhận máy chủ có SMTP qua `EMAIL_HOST` và `DEFAULT_FROM_EMAIL`.

