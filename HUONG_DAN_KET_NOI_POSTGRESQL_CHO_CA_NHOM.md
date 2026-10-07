# 📖 HƯỚNG DẪN KẾT NỐI CƠ SỞ DỮ LIỆU POSTGRESQL (CHUẨN HÓA CHO CẢ NHÓM)
> **Dự án**: Quản Lý Văn Bản & Tài Liệu (QLVB&TL) — Nhóm 1  
> **Mục tiêu**: Hướng dẫn từng bước từ A đến Z để bất kỳ thành viên nào trong nhóm (hoặc các nhóm khác) khi kéo mã nguồn về đều có thể kết nối thành công với cơ sở dữ liệu PostgreSQL và khởi động hệ thống mượt mà 100%.  
> **Thời gian thực hiện**: ~ 5 phút.  

---

## 🛠️ PHẦN 1: CÔNG CỤ CẦN CÓ TRÊN MÁY (PREREQUISITES)

Trước khi bắt đầu, hãy đảm bảo máy tính của bạn đã cài đặt:
1. **PostgreSQL** (phiên bản 14, 15, 16 hoặc 17) — Dịch vụ đang chạy (Port 5432).
2. **DBeaver** hoặc **pgAdmin 4** (để quản lý trực quan CSDL).
3. **Mã nguồn dự án** và file SQL của Kiệt: `csdl_qlvbtl_schema_final.sql`.

---

## 🚀 PHẦN 2: QUY TRÌNH 4 BƯỚC THỰC HIỆN (CẦM TAY CHỈ VIỆC)

```text
[BƯỚC 1] Tạo DB 'quanlyvanban_db' & Chạy file SQL của Kiệt (54 bảng)
   │
[BƯỚC 2] Cấu hình file '.env' và kiểm tra 'backend/config/settings.py'
   │
[BƯỚC 3] Chạy lệnh đồng bộ Django vào PostgreSQL (MIGRATE)
   │
[BƯỚC 4] Bật hệ thống và đăng nhập kiểm tra trên Web
```

---

### BƯỚC 1: TẠO DATABASE VÀ NẠP FILE SQL CỦA KIỆT

1. Mở phần mềm **DBeaver** (hoặc pgAdmin 4), kết nối vào PostgreSQL bằng tài khoản của bạn (mặc định là `postgres`).
2. Mở một trình soạn thảo SQL mới (SQL Editor) và chạy lệnh tạo database:
   ```sql
   CREATE DATABASE quanlyvanban_db WITH ENCODING 'UTF8';
   ```
3. Chuyển kết nối sang database vừa tạo: **`quanlyvanban_db`**.
4. Mở file SQL của Kiệt:  
   👉 `csdl_qlvbtl_schema_final.sql` (bản mới nhất đã có đoạn vá cuối file).
5. Dán toàn bộ nội dung file SQL vào và nhấn nút **Execute Script** (Phím tắt: `Alt + X` hoặc `Ctrl + Enter` trong DBeaver).
6. **Kiểm tra kết quả**:  
   F5 lại cây thư mục `Schemas ➔ public ➔ Tables`, bạn sẽ thấy đủ các bảng vật lý nghiệp vụ.

---

### BƯỚC 2: CẤU HÌNH BIẾN MÔI TRƯỜNG `.env` & KIỂM TRA `settings.py`

#### 2.1. Tạo file `.env` cá nhân
1. Mở thư mục **`backend/`** của dự án.
2. Tạo một file tên là **`.env`** (chú ý có dấu chấm ở đầu).
3. Dán toàn bộ đoạn cấu hình dưới đây vào file `.env`:

```ini
# ==========================================
# CẤU HÌNH DJANGO
# ==========================================
DJANGO_DEBUG=True
DJANGO_SECRET_KEY=django-insecure-gi-kkzr*^tx3ut+arcxs2i8=!3%es0clr2punmi*hg)nbg0)mr
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# ==========================================
# CẤU HÌNH KẾT NỐI POSTGRESQL THỰC TẾ
# ==========================================
DB_ENGINE=django.db.backends.postgresql
DB_NAME=quanlyvanban_db
DB_USER=postgres
DB_PASSWORD=điền_mật_khẩu_postgres_của_bạn_vào_đây
DB_HOST=127.0.0.1
DB_PORT=5432
DB_CONN_MAX_AGE=600

# ==========================================
# FRONTEND API BASE URL
# ==========================================
VITE_API_BASE_URL=http://127.0.0.1:8000/api
```
*(Nếu PostgreSQL máy bạn không đặt mật khẩu, hãy để trống: `DB_PASSWORD=`)*.

---

#### 2.2. Kiểm tra file mã nguồn `backend/config/settings.py`
File `settings.py` trên nhánh `1_layout_home` đã được cấu hình chuẩn Production để tự động đọc cấu hình từ `.env`:

* **Ở đầu file (Dòng ~10-25)**: Phải có đoạn nạp `.env`:
  ```python
  import os
  from dotenv import load_dotenv

  BASE_DIR = Path(__file__).resolve().parent.parent

  load_dotenv(BASE_DIR / ".env")
  load_dotenv(BASE_DIR.parent / ".env")
  ```

* **Ở khối Database (Dòng ~90-115)**: Đã được cấu hình tự động nhận diện PostgreSQL:
  ```python
  DB_NAME = os.getenv("DB_NAME")

  if DB_NAME:
      DATABASES = {
          "default": {
              "ENGINE": os.getenv("DB_ENGINE", "django.db.backends.postgresql"),
              "NAME": DB_NAME,
              "USER": os.getenv("DB_USER", "postgres"),
              "PASSWORD": os.getenv("DB_PASSWORD", ""),
              "HOST": os.getenv("DB_HOST", "127.0.0.1"),
              "PORT": os.getenv("DB_PORT", "5432"),
              "CONN_MAX_AGE": int(os.getenv("DB_CONN_MAX_AGE", 600)),
              "CONN_HEALTH_CHECKS": True,
              "OPTIONS": {},
          }
      }
  else:
      DATABASES = {
          "default": {
              "ENGINE": "django.db.backends.sqlite3",
              "NAME": BASE_DIR / "db.sqlite3",
          }
      }
  ```
> 💡 **Lưu ý**: Nếu bạn `git pull` code mới nhất từ nhánh `1_layout_home`, file `settings.py` này đã có sẵn, bạn **không cần sửa tay**. Nếu đang ở nhánh cũ riêng của bạn thì chỉ cần cập nhật đoạn code trên vào `settings.py`.

---

### BƯỚC 3: ĐỒNG BỘ BACKEND DJANGO VÀO POSTGRESQL (QUAN TRỌNG NHẤT)

Mở cửa sổ **PowerShell** tại thư mục dự án và chạy tuần tự các lệnh sau:

```powershell
# 1. Di chuyển vào thư mục backend
cd backend

# 2. Kích hoạt môi trường ảo Python
.\.venv\Scripts\activate

# 3. Cài đặt driver PostgreSQL
pip install psycopg2-binary>=2.9.9

# 4. Kiểm tra thông tuyến kết nối Django -> PostgreSQL
python manage.py check --database default
# (Kết quả phải báo: System check identified no issues (0 silenced))

# 5. ĐỒNG BỘ MIGRATION (LỆNH BẮT BUỘC ĐỂ KHÔNG BỊ XUNG ĐỘT)
python manage.py migrate --fake auth
python manage.py migrate
```

> ⚠️ **TẠI SAO CẦN LỆNH `migrate --fake auth`?**  
> Vì file SQL của Kiệt đã tạo sẵn bảng `auth_group`, `auth_permission`. Lệnh `--fake auth` giúp Django nhận diện bảng đã có mà không cố tạo lại (tránh lỗi `relation already exists`). Sau đó lệnh `python manage.py migrate` sẽ hoàn tất toàn bộ các bảng hệ thống còn lại!

---

### BƯỚC 4: KHỞI ĐỘNG HỆ THỐNG VÀ KIỂM TRA ĐĂNG NHẬP

Mở 2 terminal độc lập để chạy Full-Stack:

#### Terminal 1 — Chạy Backend API (Port 8000):
```powershell
cd backend
.\.venv\Scripts\activate
python manage.py runserver 127.0.0.1:8000
```

#### Terminal 2 — Chạy Frontend React (Port 5173):
```powershell
cd frontend
pnpm run dev
```

#### Trải nghiệm trên trình duyệt:
1. Mở trình duyệt truy cập: **`http://localhost:5173`**.
2. Nhập tài khoản admin đã tạo sẵn trong CSDL:
   - **Tài khoản**: `admin`
   - **Mật khẩu**: `Admin@123`
3. Nhấn **Đăng nhập**: Hệ thống cấp token JWT và vào thẳng trang Dashboard tổng quan kết nối cơ sở dữ liệu thật!

---

## ❓ BẢNG BẮT LỖI NHANH (TROUBLESHOOTING)

| Hiện tượng / Thông báo lỗi | Nguyên nhân | Cách khắc phục ngay |
| :--- | :--- | :--- |
| `could not connect to server: Connection refused (10061)` | Dịch vụ PostgreSQL trên máy chưa được bật. | Nhấn phím `Windows + R`, gõ `services.msc`, tìm dịch vụ `postgresql-x64-xx` và nhấn **Start**. |
| `password authentication failed for user "postgres"` | Sai mật khẩu PostgreSQL. | Mở lại file `backend/.env`, kiểm tra và nhập đúng mật khẩu của user `postgres` trên máy bạn. |
| `relation "auth_permission" already exists` | Bảng auth đã có sẵn từ SQL của Kiệt. | Chạy lệnh `python manage.py migrate --fake auth` rồi chạy lại `python manage.py migrate`. |
| `relation "..." does not exist` | Chưa chạy file SQL của Kiệt vào database hoặc chưa chạy Bước 3. | Mở DBeaver nạp file SQL của Kiệt, sau đó chạy đủ Bước 3 (`migrate --fake auth` và `migrate`). |
| Frontend báo lỗi `Network Error` khi đăng nhập | Chưa bật server Backend. | Đảm bảo Terminal 1 đang chạy lệnh `python manage.py runserver 127.0.0.1:8000`. |

---
*Tài liệu được biên soạn phục vụ công tác triển khai đồng bộ cho Nhóm 1 và toàn bộ các nhóm trong Đồ án.*
