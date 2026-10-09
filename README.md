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
| **Backend** | Python 3.11+, Django 5 / 6, Django REST Framework, SimpleJWT |
| **RAG & AI Engine** | LlamaIndex, ChromaDB, Gemini REST Client, OpenAI API |
| **Cơ sở dữ liệu** | PostgreSQL (với các Database View `ai_*` và role `qlvb_readonly`), SQLite (Development/Test) |
| **CI / Quality Gate** | GitHub Actions, Unittest & Pytest Suite |

---

## Cài đặt & Khởi chạy

### Yêu cầu tiên quyết:
- Python 3.11+
- Node.js 20+ và `pnpm`
- Khóa API Google Gemini hoặc OpenAI (cấu hình trong file `.env`)

### 1. Khởi động Backend

```powershell
# Di chuyển vào thư mục backend và kích hoạt môi trường ảo
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1    # Trên Linux/macOS: source .venv/bin/activate

# Cài đặt thư viện phụ thuộc
pip install -r requirements.txt

# Cấu hình biến môi trường
Copy-Item .env.example .env     # Cập nhật GEMINI_API_KEY trong .env

# Chạy migrate và khởi động server
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

### 2. Khởi động Frontend

```powershell
# Mở terminal mới, di chuyển vào thư mục frontend
cd frontend

# Cài đặt gói thư viện bằng pnpm
pnpm install

# Khởi chạy máy chủ phát triển
pnpm dev
```

Truy cập ứng dụng tại: `http://localhost:5173` (hoặc cổng hiển thị trên terminal).

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
