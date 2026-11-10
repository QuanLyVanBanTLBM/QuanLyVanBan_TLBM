# Phân công — Phan Tạ Hữu Đức (Trưởng nhóm): Nền tảng · Review · Tài liệu

> Module **Công việc** · Nhóm 6
> Nhánh làm việc: **`6_tasks-duc-nen-tang`** → PR vào **`6_tasks`**. **Không PR thẳng vào `staging`.**
> Ước lượng: **~36 giờ** công (chưa tính thời gian review).

---

## ⚠️ Cảnh báo rủi ro — đọc trước

- Đức đang gánh **cả nền tảng backend lẫn nền tảng frontend**. Bảo, Phát và phần backend của Vĩ
  **bị chặn** cho tới khi khung API có mặt trên `6_tasks`.
- Cách giảm rủi ro: **ngay sau khi PR#1 được merge**, đẩy luôn **PR#2 — khung `views.py` /
  `serializers.py` / `urls.py` / `tests.py` với các hàm rỗng** và chữ ký các hàm quyền `can_*`.
  Bảo và Phát có chỗ viết code ngay, trong lúc Đức còn hoàn thiện quy tắc quyền trong `models.py` (PR#4).
- Không gom PR#1 → PR#4 thành một PR lớn: vừa chậm review vừa chặn cả nhóm.

## 🎯 Mốc tối thiểu cho buổi báo cáo tiến độ

**Xong PR#1 là đủ để demo**: model chạy được, tạo được công việc thử qua Django admin.

Kịch bản demo:

1. `python manage.py migrate` → `python manage.py createsuperuser` → `python manage.py runserver`
2. Vào `http://127.0.0.1:8000/admin/` → **Công việc** → thêm công việc: nội dung, ngày tạo, ngày xử lý,
   yêu cầu xử lý, chọn chủ trì / chỉ đạo / cán bộ tham gia, đính kèm file.
3. Danh sách công việc trong admin hiện **cột trạng thái tính tự động** (thử một công việc có hạn trong
   quá khứ để thấy "Quá hạn").

---

## Thứ tự PR của Đức

| PR | Nội dung | Thời điểm | Mở khóa cho |
|---|---|---|---|
| **PR#1** | Nền tảng backend: settings, urls, .gitignore, models, migration, admin | Ngày 1 | Demo tiến độ |
| **PR#2** | Khung API: hàm rỗng + chia khu vực tên người; mock auth; chữ ký `can_*` | **Ngay sau PR#1** | Bảo, Phát, Vĩ (backend) |
| **PR#3** | Nền tảng frontend: `types/`, `api/client.ts`, `TasksPage`, 2 page rỗng, `router.tsx` | Ngày 2 | Bảo, Phát (frontend) |
| **PR#4** | Hoàn thiện quy tắc quyền `can_*`, API 5 công việc mới nhất, test trạng thái & hiển thị | Ngày 2–3 | Nhóm 1 (trang chủ) |
| PR#5 | `docs/api/api.md`, `docs/database/schema.md` | Cuối | — |

## Đầu việc chi tiết

### PR#1 — Nền tảng backend (~10h)

| File | Làm gì |
|---|---|
| `backend/config/settings.py` | **Chỉ thêm dòng**: `rest_framework`, `corsheaders`, `work` vào `INSTALLED_APPS`; `CorsMiddleware` ngay trên `CommonMiddleware`; `TIME_ZONE = "Asia/Ho_Chi_Minh"`; `CORS_ALLOWED_ORIGINS`; `CORS_ALLOW_HEADERS` (thêm `x-mock-user-id`); `MEDIA_ROOT`, `MEDIA_URL`. Không cấu hình `REST_FRAMEWORK` toàn cục. |
| `backend/config/urls.py` | `path("api/work/", include("work.urls"))` |
| `.gitignore` | Thêm dòng `backend/media/`. Không sắp xếp lại/xóa dòng có sẵn. |
| `apps/work/__init__.py`, `apps.py` | `WorkConfig` với `default_auto_field = BigAutoField` |
| `apps/work/models.py` | 4 model `Task`, `TaskParticipant`, `TaskComment`, `TaskAttachment` + ràng buộc, index; validator file (PDF/DOC/DOCX/JPG/JPEG/PNG, < 20MB); `TaskQuerySet.with_status()`, `visible_to(user)`; `task.roles_of(user)` |
| `apps/work/migrations/0001_initial.py` | Sinh bằng `makemigrations`. **Đức là người duy nhất được chạy `makemigrations`.** |
| `apps/work/admin.py` | Admin cho công việc: inline người liên quan (kiểm tra đúng 1 chủ trì), inline file, inline ý kiến; cột trạng thái |
| `apps/work/urls.py` | Tạm `urlpatterns = []` để `include` chạy được |

### PR#2 — Khung API (~4h) — đẩy ngay sau PR#1

| File | Làm gì |
|---|---|
| `apps/work/views.py` | `MockHeaderAuthentication` (đọc header `X-Mock-User-Id`, chỉ khi `DEBUG=True`); class phân trang; `TaskViewSet` và các action **rỗng**; chia khu vực `# ===== BẢO =====`, `# ===== PHÁT =====`, `# ===== VĨ =====` |
| `apps/work/serializers.py` | Viết xong `EmployeeBriefSerializer`, `AttachmentSerializer` (dùng chung); chia khu vực cho 3 người |
| `apps/work/urls.py` | Đăng ký **toàn bộ** route đã duyệt. Sau PR này **không ai khác sửa `urls.py`** |
| `apps/work/tests.py` | Khung khu vực cho từng người |
| `apps/work/models.py` | Chữ ký các hàm `can_edit`, `can_delete`, `can_mark_opened`, `can_submit_evidence`, `can_delete_evidence`, `can_approve`, `can_unapprove`, `can_comment` (thân hàm hoàn thiện ở PR#4) |

### PR#3 — Nền tảng frontend (~5h)

| File | Làm gì |
|---|---|
| `frontend/src/modules/work/types/task.ts`, `types/employee.ts` | Toàn bộ type theo hợp đồng API đã duyệt. Người khác cần đổi type thì báo Đức. |
| `frontend/src/modules/work/api/client.ts` | `request()`: base URL (`VITE_API_BASE_URL`, mặc định `http://127.0.0.1:8000/api`), gắn `X-Mock-User-Id` qua `getMockUserId()` của Vĩ, chuẩn hóa lỗi thành câu thông báo |
| `pages/TasksPage.tsx` | Điểm vào cho `case 'tasks'`; giữ state danh sách ↔ chi tiết, lưu `sessionStorage` (layout unmount trang khi rê chuột qua menu) |
| `pages/TaskListPage.tsx`, `pages/TaskDetailPage.tsx` | Bản rỗng, chốt props: `TaskListPage({ onOpenTask })`, `TaskDetailPage({ taskId, onBack })` |
| `frontend/src/app/router.tsx` | Thêm `case 'tasks': return <TasksPage />;` — **báo trưởng nhóm/PM trước khi sửa** |

### PR#4 — Quy tắc quyền, API trang chủ, test nền (~11h)

| File | Làm gì |
|---|---|
| `apps/work/models.py` | Hoàn thiện `can_*` đúng bảng quyền (xem mục "Quy tắc nghiệp vụ" bên dưới) |
| `apps/work/views.py` | Viết xong action `latest` (`GET /api/work/tasks/latest/?limit=5`) |
| `apps/work/tests.py` (khu vực ĐỨC) | Test **6 trạng thái** (kể cả Chờ duyệt đã quá hạn, xóa hết bằng chứng); test `visible_to` (isPublic, admin, người tạo); test ghi nhận "mở" sau hạn không đổi trạng thái |
| — | Nhắn **nhóm 1** hợp đồng API latest; phối hợp merge `6_tasks` → `staging` sớm để nhóm 1 gọi được |

### PR#5 — Tài liệu (~4h) và review (liên tục)

- `docs/api/api.md`, `docs/database/schema.md` — hỏi trưởng nhóm/PM trước khi ghi.
- Review mọi PR vào `6_tasks`; từ chối PR chứa file ngoài phần của người gửi; merge `6_tasks` → `staging`.

---

## Tiêu chí hoàn thành

- [ ] `python manage.py migrate` chạy được; tạo được công việc qua admin; cột trạng thái đúng.
- [ ] `python manage.py test work` đạt phần test của Đức.
- [ ] `GET /api/work/tasks/latest/` trả đúng `[{ id, title, dueDate, status, statusLabel }]`.
- [ ] `npm run build` qua; bấm menu **Công việc** thấy trang (rỗng) nằm trong `MainLayout`.
- [ ] Đã gửi hợp đồng API latest cho nhóm 1.

## Phụ thuộc

- Không phụ thuộc ai trong nhóm.
- Nhóm 1 chỉ gọi được API latest khi `6_tasks` đã merge lên `staging`.
- Nhóm 7: khi có model CBNV + JWT thì thay `MockHeaderAuthentication` và giá trị chức vụ tạm "Nhân viên".

## Không được làm

- Viết hộ thân hàm trong khu vực của Bảo / Phát / Vĩ (trừ khi họ nhờ và ghi rõ trong PR).
- Sửa `docs/architecture/structure.md`, code module khác, bất kỳ file nào trong `frontend/src/shared/`.
- Sắp xếp lại / format lại / xóa dòng có sẵn trong `settings.py`, `urls.py`, `.gitignore`, `router.tsx`.
- Thêm file ngoài 9 mục chuẩn của app Django (`services.py`, `permissions.py`, `filters.py`…).
- Cài `react-router-dom`, thư viện UI, thư viện date.

---

## Quy tắc nghiệp vụ đã chốt (tham chiếu nhanh)

- Trạng thái tính ở DB (annotate), không nhập tay. Ưu tiên: Hoàn thành → Chờ duyệt (còn ≥1 file bằng chứng,
  kể cả quá hạn) → Chưa hoàn thành (quá hạn, đã từng mở) → Quá hạn (quá hạn, chưa mở) → Đang xử lý → Chờ xử lý.
- Hết hạn = qua hết ngày xử lý (`due_date < hôm nay` theo giờ Việt Nam).
- "Đã mở" chỉ tính khi chủ trì / chỉ đạo / cán bộ tham gia mở, và chỉ khi chưa quá hạn. Người tạo mở không tính.
- Xem: người tạo, chủ trì, chỉ đạo, tham gia, admin. `isPublic = false` → chỉ người tạo và admin thấy.
- Admin chỉ xem, trừ khi cũng là người liên quan.
- Sửa: người tạo + chủ trì, chỉ khi Chờ xử lý / Đang xử lý. Hạn xử lý khi sửa phải ≥ hôm nay.
- Xóa (hard delete): người tạo + chủ trì, mọi trạng thái.
- Nộp bằng chứng: chủ trì + tham gia, khi chưa đóng băng và chưa hoàn thành. 1 người nộp là đủ.
- Xóa bằng chứng: chỉ người upload file đó, trước khi duyệt. Sau hạn không xóa được file bằng chứng cuối cùng.
- Duyệt / hủy duyệt: chủ trì + chỉ đạo. Hủy duyệt → về Chờ duyệt, duyệt lại được kể cả quá hạn.
- Ý kiến: người liên quan ghi được khi chưa đóng băng; không sửa, không xóa.
- Mỗi người 1 vai trò trong 1 công việc; người tạo được kiêm vai trò.
- Thông báo lỗi luôn nói rõ **vì sao** và **cách khắc phục**.

## Quy ước chung cả nhóm

- Nhánh: `6_tasks-duc-nen-tang`, `6_tasks-bao-danh-sach`, `6_tasks-phat-chi-tiet`, `6_tasks-vi-components`.
  PR vào `6_tasks`; chỉ Đức merge `6_tasks` → `staging`.
- Mỗi PR chỉ chứa file thuộc phần của mình.
- Trước khi tạo PR: `git pull origin 6_tasks`, chạy `python manage.py test work` và `npm run build`.
- Chỉ viết trong khu vực có comment tên mình ở `views.py`, `serializers.py`, `tests.py`.
- Cần đổi `models.py`, `urls.py`, migration, `types/`, `api/client.ts` → báo Đức, không tự sửa.
