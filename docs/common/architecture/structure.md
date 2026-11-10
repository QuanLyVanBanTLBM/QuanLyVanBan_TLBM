# QLVB&TL — Cấu trúc dự án

Tài liệu này mô tả cấu trúc thư mục dự án, cách phân chia Backend Django và Frontend React, cùng tên các module nghiệp vụ. Khi tạo hoặc di chuyển mã nguồn, các nhóm sử dụng tài liệu này làm căn cứ tham chiếu.

## 1. Tầng ngoài cùng

| Tầng | Cấu trúc |
|---|---|
| Backend | `backend/` |
| Frontend | `frontend/` |
| File lưu trữ tải lên | `media/` |
| Tài liệu kỹ thuật | `docs/` |
| Environment mẫu | `.env.example` |
| Git ignore | `.gitignore` |
| Tổng quan project | `README.md` |

```text
qlvbtl/
├── backend/
├── frontend/
├── media/
├── docs/
├── .env.example
├── .gitignore
└── README.md
```

---

## 2. Cấu trúc chi tiết

```text
qlvbtl/
│
├── backend/
│   ├── manage.py
│   ├── requirements.txt
│   │
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py
│   │   ├── urls.py
│   │   ├── asgi.py
│   │   └── wsgi.py
│   │
│   └── apps/
│       │
│       ├── accounts/
│       │   ├── migrations/
│       │   ├── __init__.py
│       │   ├── admin.py
│       │   ├── apps.py
│       │   ├── models.py
│       │   ├── serializers.py
│       │   ├── urls.py
│       │   ├── views.py
│       │   └── tests.py
│       │
│       ├── organizations/
│       │   ├── migrations/
│       │   ├── __init__.py
│       │   ├── admin.py
│       │   ├── apps.py
│       │   ├── models.py
│       │   ├── serializers.py
│       │   ├── urls.py
│       │   ├── views.py
│       │   └── tests.py
│       │
│       ├── authorization/
│       │   ├── migrations/
│       │   ├── __init__.py
│       │   ├── admin.py
│       │   ├── apps.py
│       │   ├── models.py
│       │   ├── serializers.py
│       │   ├── urls.py
│       │   ├── views.py
│       │   └── tests.py
│       │
│       ├── documents/
│       │   ├── migrations/
│       │   ├── __init__.py
│       │   ├── admin.py
│       │   ├── apps.py
│       │   ├── models.py
│       │   ├── serializers.py
│       │   ├── urls.py
│       │   ├── views.py
│       │   └── tests.py
│       │
│       ├── records/
│       │   ├── migrations/
│       │   ├── __init__.py
│       │   ├── admin.py
│       │   ├── apps.py
│       │   ├── models.py
│       │   ├── serializers.py
│       │   ├── urls.py
│       │   ├── views.py
│       │   └── tests.py
│       │
│       ├── resources/
│       │   ├── migrations/
│       │   ├── __init__.py
│       │   ├── admin.py
│       │   ├── apps.py
│       │   ├── models.py
│       │   ├── serializers.py
│       │   ├── urls.py
│       │   ├── views.py
│       │   └── tests.py
│       │
│       ├── approvals/
│       │   ├── migrations/
│       │   ├── __init__.py
│       │   ├── admin.py
│       │   ├── apps.py
│       │   ├── models.py
│       │   ├── serializers.py
│       │   ├── urls.py
│       │   ├── views.py
│       │   └── tests.py
│       │
│       ├── work/
│       │   ├── migrations/
│       │   ├── __init__.py
│       │   ├── admin.py
│       │   ├── apps.py
│       │   ├── models.py
│       │   ├── serializers.py
│       │   ├── urls.py
│       │   ├── views.py
│       │   └── tests.py
│       │
│       ├── meetings/
│       │   ├── migrations/
│       │   ├── __init__.py
│       │   ├── admin.py
│       │   ├── apps.py
│       │   ├── models.py
│       │   ├── serializers.py
│       │   ├── urls.py
│       │   ├── views.py
│       │   └── tests.py
│       │
│       ├── birthdays/
│       │   ├── migrations/
│       │   ├── __init__.py
│       │   ├── admin.py
│       │   ├── apps.py
│       │   ├── models.py
│       │   ├── serializers.py
│       │   ├── urls.py
│       │   ├── views.py
│       │   └── tests.py
│       │
│       └── ai_assistant/
│           ├── migrations/
│           ├── __init__.py
│           ├── admin.py
│           ├── apps.py
│           ├── models.py
│           ├── serializers.py
│           ├── urls.py
│           ├── views.py
│           └── tests.py
│
├── frontend/
│   ├── package.json
│   ├── pnpm-lock.yaml
│   ├── tsconfig.app.json
│   ├── vite.config.ts
│   │
│   └── src/
│       ├── app/
│       │   ├── App.tsx
│       │   ├── router.tsx
│       │   └── main.tsx
│       │
│       ├── pages/                          # Màn hình hoàn chỉnh chia theo luồng
│       │   ├── auth/
│       │   ├── dashboard/
│       │   ├── profile/
│       │   ├── settings/
│       │   └── ai/
│       │
│       ├── components/                     # Component theo phạm vi và chức năng
│       │   ├── auth/
│       │   ├── dashboard/
│       │   ├── layout/
│       │   ├── common/
│       │   └── ai/
│       │
│       ├── layouts/                        # Base Layout tổng thể (MainLayout.tsx)
│       ├── lib/                            # Hằng số (constants.ts) & Routes (routes.ts)
│       ├── hooks/                          # Custom React Hooks
│       ├── styles/                         # CSS Design Tokens, Theme & Animations
│       ├── i18n/                           # Đa ngôn ngữ (translate.ts, <module>/vi.json, <module>/en.json)
│       └── types/                          # Kiểu dữ liệu TypeScript (navigation, auth...)
│
├── media/                                  # Thư mục lưu trữ tệp tin tải lên (MEDIA_ROOT)
│   ├── 02_documents/                       # Tệp văn bản đến, đi, mật
│   │   ├── incoming/
│   │   ├── outgoing/
│   │   └── confidential/
│   ├── 04_templates/                       # Biểu mẫu mẫu (.docx, .xlsx)
│   ├── 05_signing/                         # Tờ trình ký (.pdf, .docx), ảnh chữ ký (.png)
│   │   ├── attachments/
│   │   └── signatures/
│   ├── 06_tasks/                           # Tệp đính kèm xử lý công việc
│   └── 07_meetings/                        # Biên bản, tài liệu phòng họp
│
├── storage/                                # Tệp nghiệp vụ khi chạy local (DOCUMENT_STORAGE_ROOT, đã gitignore), xem mục 7.1
│
├── docs/                                   # Tài liệu kỹ thuật dự án
│   ├── common/                             # Tài liệu dùng chung toàn hệ thống
│   │   ├── ITC - Django - QLVB&TL.md       # Đề bài & đặc tả tổng quan môn học
│   │   ├── ITC - Django - QLVB&TL.xlsx     # Ma trận phân công chi tiết 8 nhóm
│   │   ├── architecture/
│   │   │   ├── structure.md                # Cấu trúc mã nguồn Backend & Frontend
│   │   │   └── media_storage.md            # Quy chuẩn lưu trữ file upload (media/)
│   │   ├── database/
│   │   │   └── global_erd.md               # Sơ đồ liên kết thực thể (ERD) toàn hệ thống
│   │   └── guidelines/
│   │       ├── git_workflow.md             # Quy trình tạo nhánh, commit, PR
│   │       └── coding_standards.md         # Chuẩn KISS, Fat Models, i18n, Tokens
│   │
│   └── modules/                            # Tài liệu đặc tả phân chia theo 8 nhóm
│       ├── 01_layout_dashboard/            # Nhóm 1: Master layout, Sidebar, Dashboard
│       │   ├── spec.md
│       │   └── theme_tokens.md
│       ├── 02_documents/                   # Nhóm 2: Văn bản đến, Văn bản đi, Văn bản mật
│       │   ├── spec.md
│       │   ├── schema.md
│       │   └── api.md
│       ├── 03_dossiers_records/            # Nhóm 3: Quản lý Hồ sơ lưu trữ
│       │   ├── spec.md
│       │   ├── schema.md
│       │   └── api.md
│       ├── 04_document_templates/          # Nhóm 4: Tài liệu & Biểu mẫu
│       │   ├── spec.md
│       │   ├── schema.md
│       │   └── api.md
│       ├── 05_signing_workflow/            # Nhóm 5: Quản lý Trình ký số (Hậu)
│       │   ├── spec.md
│       │   ├── schema.md
│       │   └── api.md
│       ├── 06_tasks_management/            # Nhóm 6: Giao việc & Xử lý công việc
│       │   ├── spec.md
│       │   ├── schema.md
│       │   └── api.md
│       ├── 07_system_admin_meetings/       # Nhóm 7: Quản trị hệ thống, Phòng họp, Sinh nhật
│       │   ├── spec.md
│       │   ├── schema.md
│       │   └── api.md
│       └── 08_ai_assistant/                # Nhóm 8: Chatbot AI tra cứu văn bản
│           ├── spec.md
│           ├── architecture.md
│           └── api.md
│
├── .env.example
├── .gitignore
└── README.md
```

---

## 3. Cấu trúc module Django

```text
apps/<module>/
├── migrations/
├── __init__.py
├── admin.py
├── apps.py
├── models.py
├── serializers.py
├── urls.py
├── views.py
└── tests.py
```

---

## 4. Cấu trúc module Frontend

```text
modules/<module>/
├── api/
├── components/
├── pages/
└── types/
```

---

## 5. Domain Map

```text
QLVB&TL
│
├── Tài khoản / CBNV
│   └── accounts
│
├── Cơ cấu tổ chức
│   └── organizations
│
├── Phân quyền
│   └── authorization
│
├── Văn bản
│   ├── Văn bản đến
│   ├── Văn bản đi
│   ├── Văn bản mật
│   └── documents
│
├── Hồ sơ
│   └── records
│
├── Tài liệu / Biểu mẫu
│   └── resources
│
├── Trình ký
│   └── approvals
│
├── Công việc
│   └── work
│
├── Phòng họp
│   └── meetings
│
├── Sinh nhật
│   └── birthdays
│
└── Chatbox AI
    └── ai_assistant
```

---

## 6. Cập nhật cấu trúc dự án

- Mã nguồn Backend đặt trong `backend/`; mã nguồn Frontend đặt trong `frontend/`.
- Mỗi module nghiệp vụ đặt trong đúng domain tương ứng ở Backend và Frontend.
- Các component giao diện phân theo chức năng đặt trong `frontend/src/components/`, các trang màn hình đặt trong `frontend/src/pages/`, khung sườn App Shell đặt trong `frontend/src/layouts/`.
- Tiện ích dùng chung đặt tại `frontend/src/lib/` (constants, routes), `frontend/src/i18n/` (đa ngôn ngữ) và `frontend/src/styles/` (design tokens).
- Khi cần thay đổi cấu trúc dự án, cập nhật tài liệu này cùng thay đổi liên quan.
- Không tạo thư mục rỗng chỉ để mô phỏng cây thư mục. Thư mục được thêm khi có mã nguồn, file cấu hình hoặc file đánh dấu cần thiết.

---

## 7. Quy chuẩn Lưu trữ Tệp tin (Media Storage) & Tài liệu (Docs)

### 7.1. Quy chuẩn Lưu trữ Tệp tin nghiệp vụ (`DOCUMENT_STORAGE_ROOT`)
- Tệp nghiệp vụ (đính kèm văn bản đến/đi, công việc, tài liệu và biểu mẫu) lưu dưới thư mục gốc `DOCUMENT_STORAGE_ROOT` (biến môi trường; dev mặc định `storage/` cạnh `backend/`, đã gitignore; staging `/srv/qlvb/shared/storage`).
- `FileField` dùng `storage=document_storage.get_document_storage` (callable, không đóng cứng đường dẫn vào migration) và `upload_to` sinh đường dẫn bằng `build_dated_path(module, filename)` trong `backend/apps/document_storage.py`: `<module>/YYYY/MM/DD/<uuid>.<ext>` theo ngày upload, với `module` thuộc `van-ban-den`, `van-ban-di`, `cong-viec`, `ho-so`, `mau-van-ban`. Tên gốc lưu ở cột tên của bảng; tên trên đĩa là UUID.
- Không dùng `default_storage` hay `MEDIA_ROOT` cho tệp nghiệp vụ mới. Tệp trình ký (`SIGNING_DOCUMENT_ROOT`) và dữ liệu AI (`AI_DATA_DIR`) giữ cấu hình riêng.
- Định dạng tệp do người dùng gửi phải được kiểm tra (trả 400) trước khi lưu; `build_dated_path` chỉ từ chối như lớp bảo vệ cuối.

### 7.2. Quy chuẩn Tài liệu Dự án (`docs/`)
- Toàn bộ tài liệu, đặc tả, biểu mẫu khảo sát, sơ đồ ERD đưa về thư mục chung `docs/`.
- Tài liệu toàn cục, hướng dẫn cài đặt, quy trình Git để ở `docs/common/`.
- Mỗi nhóm trong 8 nhóm chỉ quản lý và cập nhật tài liệu đặc tả của mình trong thư mục `docs/modules/<module_name>/`, tuyệt đối không ghi đè vào thư mục của nhóm khác để tránh xung đột mã nguồn trên Git.

