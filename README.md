# TLBM — Hệ thống Quản lý Văn bản và Tài liệu (Phân hệ AI Chatbox - Nhóm 8)

TLBM là nền tảng quản lý văn bản, tài liệu và điều hành công việc nội bộ dành cho doanh nghiệp. Hệ thống đưa toàn bộ luồng giấy tờ, phê duyệt và trao đổi công việc của tổ chức lên môi trường số, giúp việc xử lý nhanh hơn, minh bạch hơn và dễ tra cứu hơn.

Đồ án môn Django — Trường Cao đẳng Công nghệ Thông tin TP.HCM (ITC).  
Nhánh: `8_ai_chatbox` — Module 8: Trợ lý AI Chatbox & RAG thông minh.

---

## Tổng quan Module 8 (Trợ lý AI Chatbox)

Module 8 phụ trách xây dựng Trợ lý ảo AI thông minh, hỗ trợ cán bộ nhân viên tra cứu văn bản, quy chế nội bộ, hướng dẫn nghiệp vụ và hỏi đáp ngữ cảnh tự động dựa trên kiến trúc **RAG (Retrieval-Augmented Generation)** và **CSDL Chỉ đọc (Read-only Database)**.

### Ba nguồn tri thức chính của Trợ lý AI:
1. **Dữ liệu Văn bản & Hồ sơ CSDL (PostgreSQL View `ai_*`)**:
   - Truy vấn qua tài khoản chỉ đọc (`qlvb_readonly`) trên các Security Barrier Views: `ai_vanbanden`, `ai_vanbandi`, `ai_tailieu`.
   - Lọc phân quyền tự động theo User Token/Session và phòng ban (`qlvb.employee_id`).
   - Tự động loại trừ 100% các văn bản thuộc phạm vi "HẠN CHẾ" (`pham_vi = 'HAN_CHE'`).
2. **Kho tài liệu nghiệp vụ (Local ChromaDB)**:
   - Các tài liệu hướng dẫn, quy định nội bộ được lập chỉ mục vector, lưu trữ an toàn trong ChromaDB.
3. **Thẻ đặc tả nghiệp vụ phân hệ 1–7**:
   - Kiến thức tổng quan về quy trình xử lý văn bản, ký số điện tử và phân quyền hệ thống.

---

## Tính năng nổi bật của Trợ lý AI

- 🔍 **Tra cứu văn bản ngữ cảnh**: Tìm kiếm thông tin chính xác theo Số hiệu, Trích yếu, Ngày ban hành, Đơn vị ban hành.
- 🎯 **Nguyên tắc "Zero-Hallucination"**: Chỉ trả lời dựa trên tài liệu được cấp phép; từ chối khi không có dữ liệu nguồn để bảo đảm tính chuẩn xác của văn bản hành chính.
- 🛡️ **Bảo mật & Phân quyền RBAC**: Yêu cầu quyền `use_aiassistant` để tương tác; chức năng quản trị kho tài liệu và cài đặt AI dành riêng cho Quản trị viên (`is_superuser`).
- ⚡ **Đa mô hình AI (LLM)**: Tích hợp Google Gemini (mặc định: `gemini-3.8-flash` với cơ chế tự động chuyển đổi fallback) và OpenAI GPT qua cấu hình giao diện.
- 📄 **Xử lý tệp đa định dạng**: Hỗ trợ PDF, DOCX, TXT, CSV, PPTX, Markdown, ảnh số hóa văn bản (Vision OCR).
- 💬 **Giao diện hiện đại**: Tích hợp trực tiếp vào App Shell chuẩn Staging (React + TypeScript + Vite), hỗ trợ Dark/Light theme và đa ngôn ngữ (Tiếng Việt, Tiếng Anh).

---

## Kiến trúc công nghệ

| Thành phần | Công nghệ / Thư viện |
|---|---|
| **Frontend** | React 19, TypeScript, Vite, Vanilla CSS Tokens, Axios / Fetch API Client |
| **Backend** | Python 3.12+, Django 6.1, Django REST Framework, SimpleJWT |
| **RAG & AI Engine** | LlamaIndex, ChromaDB, Gemini REST Client, OpenAI API |
| **Cơ sở dữ liệu** | PostgreSQL (với các Database View `ai_*` và role `qlvb_readonly`), SQLite (kiểm thử/dự phòng) |
| **CI / Quality Gate** | GitHub Actions, Unittest & Pytest Suite |

---

## Cài đặt và chạy local

### Yêu cầu

- Docker Desktop đã mở và Docker Engine đang chạy.
- Node.js theo phiên bản khai báo trong `package.json` ở thư mục gốc; `pnpm` đã được cài.
- Python 3.12 trở lên. Lệnh backend sẽ tự tạo `backend/.venv` (môi trường Python riêng) và tự cài thư viện; không cần tự tạo hoặc bật môi trường ảo.

### Thiết lập lần đầu sau khi clone dự án

Mở Terminal (cửa sổ nhập lệnh) tại thư mục gốc có file `package.json`, rồi chạy:

```powershell
pnpm setup:frontend
pnpm db:setup
```

`pnpm setup:frontend` cài các gói giao diện theo lockfile (file khóa phiên bản thư viện). `pnpm db:setup` khởi động PostgreSQL và pgAdmin bằng Docker Compose (công cụ chạy các dịch vụ Docker), sau đó tự tạo môi trường Python và áp dụng các migration (bản thay đổi cấu trúc DB do Django quản lý).

Nếu cần cấu hình khóa Gemini, sao chép `.env.example` thành `.env` ở thư mục gốc và điền khóa API. Không commit file `.env`.

### Chạy dự án — hai Terminal riêng

`pnpm db:setup` chỉ cần chạy một lần cho DB local mới. Dữ liệu DB được lưu trong Docker volume, nên các lần mở dự án sau không cần dựng lại DB. Mỗi ngày, mở Docker Desktop và chờ Docker Engine sẵn sàng; nếu container DB đang chạy thì không cần chạy thêm lệnh DB.

Nếu trước đó mày đã chạy `pnpm db:stop` hoặc container DB đang dừng, mở Terminal tại thư mục gốc rồi chạy:

```powershell
pnpm db:start
```

Sau đó chạy hai lệnh dưới đây trong hai Terminal riêng, đều đứng tại thư mục gốc:

Terminal 1 — Backend (máy chủ xử lý API):

```powershell
pnpm runserver
```

Lệnh này kiểm tra Docker Engine và DB trước. Nếu Docker chưa chạy hoặc DB chưa sẵn sàng, sẽ báo cách xử lý ngay. Khi DB sẵn sàng, lệnh tự tạo `backend/.venv` nếu chưa có, cài hoặc cập nhật thư viện khi `backend/requirements.txt` thay đổi, rồi chạy Django tại `http://127.0.0.1:8000`. Backend kết nối cố định tới PostgreSQL local `127.0.0.1:55432`; không lấy thông tin kết nối DB từ `.env`.

Terminal 2 — Frontend (giao diện):

```powershell
pnpm dev
```

Mở địa chỉ do Vite in trong Terminal, mặc định là `http://localhost:5173`. Khi có migration Django mới, chạy riêng `pnpm db:migrate`; backend không tự áp dụng migration khi khởi động.

### pgAdmin và kết nối DB local

pgAdmin (trang web quản trị PostgreSQL) được mở tại `http://127.0.0.1:5050`.

- Email đăng nhập: `admin@qlvb.local`
- Mật khẩu pgAdmin: `qlvb_pgadmin_local_only`
- Máy chủ DB đã được khai báo sẵn trong pgAdmin. Nếu cần nhập thủ công, dùng host `db`, cổng `5432` trong mạng Docker; tên DB và user là `qlvb_dev`, mật khẩu là `qlvb_local_only`.
- Từ ứng dụng chạy trên máy Windows, dùng host `127.0.0.1`, cổng `55432`, database `qlvb_dev`, user `qlvb_dev`, mật khẩu `qlvb_local_only`.

Các cổng DB và pgAdmin chỉ bind vào `127.0.0.1` (chỉ truy cập từ máy local).

### Lệnh DB thường dùng

Chạy tại thư mục gốc:

- `pnpm db:setup`: khởi động DB và pgAdmin, tạo môi trường Python nếu thiếu, rồi chạy migration.
- `pnpm db:start`: chỉ khởi động DB và pgAdmin; giữ nguyên dữ liệu local hiện có.
- `pnpm db:status`: xem trạng thái container DB/pgAdmin và địa chỉ truy cập.
- `pnpm db:migrate`: áp dụng migration Django mới vào DB local sau khi code có migration mới.
- `pnpm db:migrations`: xem danh sách migration và trạng thái đã áp dụng/chưa áp dụng.
- `pnpm db:reset`: xóa dữ liệu trong DB local `qlvb_dev`, tạo lại DB rỗng rồi áp dụng migration; phải gõ `RESET` để xác nhận. Lệnh này không xóa dữ liệu production.
- `pnpm db:stop`: dừng DB và pgAdmin nhưng giữ volume (kho dữ liệu bền vững của Docker).

Không cần xóa volume khi chỉ muốn làm DB trống; dùng `pnpm db:reset` để chỉ reset đúng database local của dự án.

---

## Cấu hình Biến môi trường Backend (`backend/.env`)

| Tên biến | Giá trị mặc định | Giải thích |
|---|---|---|
| `MODEL_PROVIDER` | `gemini` | Nhà cung cấp mô hình (`gemini` hoặc `openai`) |
| `GEMINI_API_KEY` | *(bỏ trống)* | API Key Gemini của Google |
| `LLM_MODEL` | `gemini-3.8-flash` | Tên mô hình ngôn ngữ chính |
| `EMBED_MODEL` | `models/gemini-embedding-001` | Mô hình nhúng vector |
| `READONLY_DB_NAME` | *(tùy chọn)* | Tên CSDL PostgreSQL cho kết nối chỉ đọc |
| `READONLY_DB_USER` | `qlvb_readonly` | Role chỉ đọc an toàn theo DDL mới |

---

## Kiểm thử Đơn vị (Unit Tests)

Module 8 đi kèm bộ test suite kiểm tra toàn diện quyền truy cập và bảo mật View chỉ đọc:

```powershell
# Chạy toàn bộ test của phân hệ AI Chatbox
$env:PYTHONPATH="."
python backend/manage.py test tests.test_sql_document_source tests.test_ai_access
```

Bộ test bao gồm:
- **`test_sql_document_source`**: Kiểm tra truy vấn qua View `ai_*`, chặn đọc file đính kèm, từ chối role có đặc quyền cao hoặc sai role chỉ đọc.
- **`test_ai_access`**: Kiểm tra quyền RBAC `use_aiassistant`, xác thực tài khoản qua JWT và kiểm soát quyền admin trên các endpoint cấu hình.

---

## Cấu trúc thư mục

```text
.
├── backend/
│   ├── api/views.py                  # API endpoints cho Chat, Documents, Settings
│   ├── config/                       # Settings & routing tập trung của Django
│   ├── services/
│   │   ├── ai_access.py              # Xác thực người dùng & kiểm tra quyền RBAC
│   │   ├── rag_service.py            # Xử lý RAG, ChromaDB & System Prompt
│   │   ├── sql_document_source.py    # Truy vấn an toàn qua Database View ai_*
│   │   └── gemini_service.py         # Kết nối Gemini REST LLM & Embeddings
│   └── tests/                        # Bộ kiểm thử đơn vị cho AI Module
├── frontend/
│   ├── src/pages/ai/                 # Giao diện Chatbox chính (AiAssistantPage.tsx)
│   ├── src/components/               # Modal cấu hình AI, thanh điều hướng
│   └── src/lib/apiClient.ts          # Client gọi API có đính kèm Bearer Token
├── data/                             # Kho lưu trữ tệp, ChromaDB và registry JSON
└── docs/                             # Tài liệu kỹ thuật, DDL và quy chuẩn dự án
```

---

## Thực hiện

- **Đồ án**: Quản lý Văn bản và Tài liệu (QLVB&TL)
- **Lớp**: CD25CT_CLC — Khoa Công nghệ Thông tin, Trường Cao đẳng Công nghệ Thông tin TP.HCM (ITC).
- **Giảng viên hướng dẫn**: NCS.ThS. Trần Phương Duy.
- **Phân hệ**: Module 8 — Trợ lý AI Chatbox (branch `8_ai_chatbox`).
