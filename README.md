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
| **Cơ sở dữ liệu** | PostgreSQL 16 (với các Database View `ai_*` và role `qlvb_readonly`) |
| **CI / Quality Gate** | GitHub Actions, Django test runner |

---

## Cài đặt và chạy local

README này là tài liệu duy nhất về setup local. Dựng DB, build/deploy staging: `docs/common/database/build_db_runbook.md`.

### Yêu cầu

- Docker Desktop đang chạy.
- Node.js theo `engines` trong `package.json` và `pnpm`.
- Python 3.12 trở lên (Windows: lệnh `py`; Linux/macOS: `python3`). Lệnh `pnpm` tự tạo `backend/.venv` và cài thư viện; không cần tự tạo hoặc bật môi trường ảo.

Các lệnh `pnpm` dưới đây kiểm tra Docker, Python trước khi chạy và báo lỗi kèm cách xử lý.

### Thiết lập lần đầu

Tại thư mục gốc (có `package.json`):

```bash
pnpm bootstrap
```

`pnpm bootstrap` chạy `pnpm setup:frontend` (cài gói giao diện theo lockfile) và `pnpm db:setup` (khởi động PostgreSQL 16 + pgAdmin bằng `compose.yaml`, tạo `backend/.venv`, dựng DB `qlvb_dev` từ `docs/common/database/release_DDL.sql` kèm dữ liệu mẫu). DB đã dựng đúng bản DDL hiện tại thì được giữ nguyên.

Khóa Gemini và cấu hình email/ký: sao chép `.env.example` thành `.env` ở thư mục gốc và điền giá trị cần dùng. Kết nối DB do các lệnh `pnpm` tự đặt, không khai báo trong `.env`.

Tệp nghiệp vụ tải lên (đính kèm văn bản, công việc, biểu mẫu) lưu theo cây `<module>/YYYY/MM/DD/<uuid>.<ext>` dưới `DOCUMENT_STORAGE_ROOT`. Chạy local (`DJANGO_DEBUG=true`) để trống biến này thì dùng thư mục `storage/` ở thư mục gốc dự án (đã gitignore). Staging/production bắt buộc đặt biến là thư mục tuyệt đối đã tồn tại, ngoài thư mục release, user chạy service ghi được; chi tiết sao lưu trong `docs/common/database/backup_restore_runbook.md`.

### Chạy hằng ngày

Mở Docker Desktop, rồi chạy tại thư mục gốc:

```bash
pnpm db:start     # chỉ cần khi DB đang dừng
pnpm runserver    # Terminal 1: backend http://127.0.0.1:8000
pnpm dev          # Terminal 2: frontend http://127.0.0.1:5173 (proxy /api sang backend)
```

### Sau khi pull

- Có migration mới: `pnpm db:migrate`. Với DB cũ mang dấu `build_db:v2`, chạy `pnpm db:adopt` để xác minh schema và lịch sử migration rồi mới chạy `pnpm db:migrate`.
- `release_DDL.sql` đổi không tự xóa DB. `pnpm db:migrate` yêu cầu migration chờ nếu hash DDL thay đổi; chỉ dùng `pnpm db:reset` khi chủ ý xóa dữ liệu local và gõ `RESET`.
- Thư viện frontend đổi: `pnpm setup:frontend`.

Trước `pnpm db:setup` hoặc `pnpm db:reset`, đặt `ADMIN_PASSWORD` trong môi trường shell. Demo data không được tạo mặc định; khi cần, chạy `pnpm manage seed_db --demo-data` với `DEMO_PASSWORD` đã đặt.

### Test và lệnh Django

```bash
pnpm test:backend                 # toàn bộ test backend trên PostgreSQL local
pnpm test:backend accounts        # tham số được chuyển cho `manage.py test`
pnpm manage <lệnh>                # ví dụ: pnpm manage check, pnpm manage createsuperuser
```

Test dùng DB tạm `test_qlvb_dev` do Django dựng bằng migration; DB `qlvb_dev` không bị thay đổi. Kiểm tra frontend: `pnpm --dir frontend run lint|test|build`.

### Lệnh DB

| Lệnh | Tác dụng |
|---|---|
| `pnpm db:setup` | Khởi động DB/pgAdmin, tạo `backend/.venv`, dựng DB nếu chưa có (`scripts/build_db.py --if-empty --seed`) |
| `pnpm db:start` / `pnpm db:stop` | Bật / tắt DB và pgAdmin, giữ nguyên dữ liệu (Docker volume) |
| `pnpm db:status` | Trạng thái container và địa chỉ truy cập |
| `pnpm db:adopt` | Xác minh schema và migration history của DB v2 được hỗ trợ, rồi nâng marker lên v3 |
| `pnpm db:migrate` | Chạy thật migration Django chờ và cập nhật marker; không nạp lại DDL hoặc reset DB |
| `pnpm db:migrations` | Danh sách migration đã/chưa áp dụng |
| `pnpm db:reset` | Xóa và dựng lại DB local từ `release_DDL.sql` (cần `ADMIN_PASSWORD` và xác nhận `RESET`) |

Collation: DB do repo tạo dùng ICU `vi-VN`. DB `qlvb_dev` tạo từ volume cũ có collation khác sẽ bị `db:setup`/`db:migrate` từ chối. DDL hash đổi không tự kích hoạt reset; drift hoặc thiếu đường migration được báo để xử lý riêng.

### Kết nối DB local

| Thành phần | Giá trị |
|---|---|
| PostgreSQL (từ máy host) | `127.0.0.1:55432`, database/user `qlvb_dev`, mật khẩu `qlvb_local_only` |
| pgAdmin | `http://127.0.0.1:5050`, đăng nhập `admin@qlvb.local` / `qlvb_pgadmin_local_only` (máy chủ DB đã khai báo sẵn) |

Các cổng chỉ bind vào `127.0.0.1`. Cổng bị trùng thì đặt biến môi trường `QLVB_DB_PORT` và/hoặc `QLVB_PGADMIN_PORT` trước khi chạy lệnh `pnpm`; tên compose project (`COMPOSE_PROJECT_NAME`) quyết định volume dữ liệu.

### Deploy staging

`pnpm deploy:staging`: deploy `origin/staging` lên host staging và giữ dữ liệu bằng chế độ `sync`. Chỉ thêm `--reset-db` khi chủ ý xóa DB staging; thao tác này luôn yêu cầu gõ `RESET`, kể cả khi dùng `--yes`. Cần `QLVB_DEPLOY_HOST`; chi tiết ở `docs/common/database/build_db_runbook.md`.

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
