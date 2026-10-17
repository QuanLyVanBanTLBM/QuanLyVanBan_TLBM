# TLBM SYSTEM — BACKEND API SERVICE
> **Phân hệ Máy chủ & API Dữ liệu (Django 6.1 + Python 3.12)**  
> **Dự án**: Quản Lý Văn Bản và Tài Liệu (QLVB&TL) — Trường CĐ CNTT TP.HCM (ITC)

---

## 🛠️ 1. Công nghệ & Yêu cầu môi trường

- **Framework**: Django 6.1.x (Python Web Framework)
- **Python**: Bắt buộc Python 3.12 trở lên (Django 6.1 không hỗ trợ Python thấp hơn)
- **Database**: PostgreSQL 16 trong Docker cho môi trường local; SQLite vẫn là cấu hình dự phòng của Django
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
├── db.sqlite3                  # Cơ sở dữ liệu SQLite cục bộ
└── manage.py                   # Script quản trị lệnh Django CLI
```

---

## 🚀 3. Hướng dẫn chạy local

Chạy mọi lệnh từ thư mục gốc của dự án, không cần chuyển vào `backend` và không cần tự bật môi trường ảo:

1. Lần đầu dựng DB local mới: mở Docker Desktop, rồi chạy `pnpm db:setup` tại thư mục gốc. Chỉ cần làm một lần; dữ liệu DB được giữ trong Docker volume.
2. Những lần chạy dự án sau: mở Docker Desktop và chờ Docker Engine sẵn sàng. Nếu DB đang chạy, không cần chạy lại lệnh dựng DB. Nếu đã dừng DB bằng `pnpm db:stop`, chạy `pnpm db:start` tại thư mục gốc.
3. Mở Terminal backend tại thư mục gốc và chạy `pnpm runserver`. Lệnh kiểm tra Docker và DB trước, rồi mới tự chuẩn bị môi trường Python và chạy Django. Nếu Docker hoặc DB chưa sẵn sàng, lệnh báo lỗi kèm hướng xử lý.
4. Mở Terminal frontend khác tại thư mục gốc và chạy `pnpm dev`.

Khi có migration Django mới, chạy `pnpm db:migrate` tại thư mục gốc trước hoặc sau khi khởi động backend. `pnpm db:status`, `pnpm db:migrations`, `pnpm db:reset` và `pnpm db:stop` lần lượt xem container, xem trạng thái migration, tạo lại DB local có xác nhận, và dừng dịch vụ mà vẫn giữ dữ liệu.

- API Backend: `http://127.0.0.1:8000/`
- Django Admin: `http://127.0.0.1:8000/admin/`
- pgAdmin local: `http://127.0.0.1:5050/` (đăng nhập bằng `admin@qlvb.local` / `qlvb_pgadmin_local_only`)
- Cổng PostgreSQL từ máy Windows: `127.0.0.1:55432`, database `qlvb_dev`

---

## 🔗 4. Kết nối với Frontend React

- Frontend gọi đến Backend qua base URL: `http://127.0.0.1:8000/`
- Cấu hình CORS đã được thiết lập sẵn trong `config/settings.py` cho phép nguồn `http://localhost:5173` và `http://localhost:5174`.

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
   - `kpis`: `incomingCount`, `outgoingCount`, `confidentialCount`, `tasksCount`.
   - Danh sách mảng: `recentIncoming`, `recentOutgoing`, `tasks`, `meetingRooms`, `birthdays`.
3. **`test_tomorrow_date_calculation`**: Kiểm tra tính toán ngày sinh nhật chuyển giao tháng/năm.

<details>
<summary><b>👉 Xem mã nguồn kiểm thử mẫu (Python TestCase)</b></summary>

```python
from datetime import date, timedelta, time
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from accounts.models import StaffProfile
from dashboard.models import MeetingRoom


class DashboardAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="testuser", password="testpassword123")
        self.today = timezone.localdate()
        self.tomorrow = self.today + timedelta(days=1)

        StaffProfile.objects.create(
            user=self.user,
            full_name="Cán Bộ Ngày Mai",
            department="Ban Kế hoạch",
            position="Chuyên viên",
            birthday=date(1995, self.tomorrow.month, self.tomorrow.day),
        )

        MeetingRoom.objects.create(
            room_name="Phòng họp A1 - Khu A",
            meeting_title="Họp giao ban định kỳ",
            date=self.today,
            start_time=time(8, 30),
            end_time=time(11, 30),
            organizer="Văn phòng Trung tâm",
            status="ready",
        )

    def test_overview_unauthorized(self):
        response = self.client.get("/api/dashboard/overview/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_overview_authorized_contract(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/dashboard/overview/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("kpis", response.data)
        self.assertIn("recentIncoming", response.data)
        self.assertIn("recentOutgoing", response.data)
        self.assertIn("meetingRooms", response.data)
        self.assertIn("birthdays", response.data)
```
</details>

---

### 5.3. Hướng dẫn thực thi kiểm thử cục bộ
Khi các nhóm Backend tiếp tục phát triển:
1. Tạo hoặc sao chép các hàm test vào `backend/apps/<tên_app>/tests.py`.
2. Chạy lệnh:
   ```bash
   python manage.py test accounts
   python manage.py test dashboard
   ```

### 5.4. Email chúc mừng sinh nhật

Ứng dụng dùng backend email console nếu chưa cấu hình SMTP. Để gửi email thật, đặt các biến sau trong `.env` ở thư mục gốc dự án hoặc trong `backend/.env`:

```dotenv
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_USE_TLS=true
EMAIL_HOST_USER=account@example.com
EMAIL_HOST_PASSWORD=<secret>
DEFAULT_FROM_EMAIL=account@example.com
```

Không commit `.env` hoặc mật khẩu SMTP. `BRAND_NAME` và `ORGANIZATION_NAME` có thể đặt để đổi thương hiệu trong tiêu đề và nội dung thư; mặc định là `Bảo Long Insurance`.

Chạy thủ công từ thư mục `backend`:

```bash
python manage.py send_birthday_emails
python manage.py send_birthday_emails --date=YYYY-MM-DD
```

`--allow-locmem` chỉ dành cho kiểm thử. Kết quả gửi được ghi trong `birthdays_birthdayemaillog`; hiện API nhật ký chỉ cho superuser xem cho đến khi DDL bổ sung quyền riêng.

Để chạy định kỳ trên Linux, dùng `deploy/birthday-email.cron.example`, thay đường dẫn, phút và giờ theo lịch đã được nhóm chốt; đặt timezone của scheduler thành `Asia/Ho_Chi_Minh`. Trên Windows, tạo tác vụ hằng ngày trong Task Scheduler: chương trình là Python của môi trường ảo, tham số là `manage.py send_birthday_emails`, thư mục bắt đầu là `backend`. Tài khoản chạy tác vụ phải nhận được các biến SMTP từ môi trường hoặc secret store.

