# Module 06 — API Công việc

- Tiền tố: `/api/work/` (khai báo trong `backend/config/urls.py`)
- Mã nguồn: `backend/apps/work/views.py`, `serializers.py`, `urls.py`
- Tên bảng/cột trong CSDL theo bản PM chốt (xem `schema.md`); tên trường JSON của API giữ camelCase tiếng Anh
- Dữ liệu: JSON, tên trường dạng **camelCase**. Riêng các API có tải file dùng `multipart/form-data`.
- Ngày thuần (`createdDate`, `dueDate`): `YYYY-MM-DD`. Mốc thời gian: ISO 8601 theo giờ Việt Nam, ví dụ `2026-09-19T11:17:27.839821+07:00`. Giao diện hiển thị `dd/mm/yyyy` và `dd/mm/yyyy HH:mm:ss`.

## 1. Xác thực

Module nhận **JWT của nhóm 7** trước; nếu request không có JWT thì mới dùng **người dùng giả lập**
(chỉ hoạt động khi `DEBUG=True`) để nhóm còn thử được các vai trò khi phát triển:

| Header | Ý nghĩa |
|---|---|
| `X-Mock-User-Id: <id>` | Gọi API dưới tên người dùng có id này |
| (không gửi) | Dùng tài khoản quản trị (superuser) có id nhỏ nhất |

- Id sai hoặc tài khoản không tồn tại: `401` kèm hướng dẫn chọn lại người dùng.
- `DEBUG=False`: header bị bỏ qua, mọi request trả `401`.
- Khi hệ thống đăng nhập chạy đủ: gỡ lớp `MockHeaderAuthentication` trong `views.py` và hàm `authHeaders()` trong `frontend/src/modules/work/api/client.ts`.

## 2. Định dạng lỗi

Mọi thông báo lỗi đều nói rõ **vì sao** và **cách khắc phục**.

| Mã | Khi nào | Dạng body |
|---|---|---|
| `400` | Dữ liệu sai, hoặc trạng thái công việc không cho phép thao tác | Lỗi theo trường: `{"dueDate": ["Ngày xử lý đang trước ngày tạo. Hãy chọn ngày xử lý bằng hoặc sau ngày tạo."]}` · Lỗi trạng thái: `{"detail": "..."}` |
| `401` | Chưa xác định được người dùng | `{"detail": "..."}` |
| `403` | Sai vai trò | `{"detail": "Chỉ người tạo, người chủ trì hoặc người chỉ đạo mới được duyệt công việc. Hãy báo một trong những người này vào duyệt."}` |
| `404` | Không có công việc, **hoặc không có quyền xem** (không để lộ công việc đang ẩn) | `{"detail": "..."}` |

## 2b. Quyền xem — 3 lớp

Danh sách và chi tiết chỉ trả về công việc người gọi được xem, theo **một trong ba** điều kiện:

1. **Người liên quan**: người tạo, hoặc có tên trong `task_participant`.
2. Có quyền **`view_all_congviec`**: xem toàn bộ công việc (kể cả công việc đang ẩn).
3. Có quyền **`view_dept_congviec`**: xem công việc gắn với đơn vị của chính mình
   (lấy từ `accounts_employee.don_vi_id`, không cần chọn phòng ban khi cấp quyền).

Không đủ điều kiện thì API trả `404` (không để lộ công việc đang ẩn).
`view_congviec` ("Xem công việc (chung)") KHÔNG phải một trong ba lớp xem — cấp riêng quyền này
không làm thấy thêm việc nào.
Mã quyền hiện kiểm tra bằng permission có sẵn của Django — `TODO: noi he thong phan quyen nhom 7`
(hàm `user_has_task_permission` trong `models.py`).

### Quyền thao tác (Sửa/Xóa/Duyệt)

Ngoài vai trò per-task (người tạo / chủ trì / chỉ đạo), người được cấp các quyền RBAC sau đây
thao tác được trên **mọi công việc mà họ xem được** (kiểm tra qua `user_has_task_permission`
trong `models.py`):

- `change_congviec` → Sửa công việc
- `delete_congviec` → Xóa công việc
- `approve_congviec` → Duyệt / Hủy duyệt công việc

Các quyền trạng thái (Chờ duyệt / Hoàn thành / đóng băng) vẫn áp dụng như cũ.

## 3. Danh sách API

| Phương thức | Đường dẫn | Chức năng |
|---|---|---|
| GET | `tasks/` | Danh sách công việc (lọc, phân trang) |
| POST | `tasks/` | Thêm công việc (gửi mail cho người liên quan) |
| GET | `tasks/{id}/` | Chi tiết công việc (chỉ đọc, không ghi nhận "đã mở") |
| PATCH | `tasks/{id}/` | Sửa công việc |
| DELETE | `tasks/{id}/` | Xóa hẳn công việc cùng file và ý kiến |
| POST | `tasks/{id}/open/` | Vào trang chi tiết: ghi nhận "đã mở" nếu đủ điều kiện, trả về chi tiết |
| GET | `tasks/{id}/comments/` | Danh sách ý kiến kèm file |
| POST | `tasks/{id}/comments/` | Ghi ý kiến, có thể kèm file kết quả |
| DELETE | `tasks/{id}/evidences/{fileId}/` | Xóa một file kết quả của chính mình |
| POST | `tasks/{id}/approve/` | Duyệt hoàn thành |
| POST | `tasks/{id}/unapprove/` | Hủy duyệt |
| GET | `tasks/latest/?limit=5` | Công việc mới nhất cho trang chủ (nhóm 1) |
| GET | `attachments/{id}/download/` | Tải file (có kiểm tra quyền xem) |
| GET | `employees/?search=` | Danh sách cán bộ cho ô chọn người |
| GET | `me/` | Người dùng hiện tại |

---

## 4. Công việc

### 4.1. `GET /api/work/tasks/` — Danh sách

Tham số (đều không bắt buộc):

| Tham số | Ví dụ | Mô tả |
|---|---|---|
| `search` | `báo cáo` | Tìm trong nội dung công việc |
| `status` | `CHO_DUYET` | Một trong `CHO_XU_LY`, `DANG_XU_LY`, `CHO_DUYET`, `HOAN_THANH`, `CHUA_HOAN_THANH`, `QUA_HAN` |
| `createdFrom`, `createdTo` | `2026-09-01` | Khoảng ngày tạo (tính cả hai đầu) |
| `page` | `1` | Trang, bắt đầu từ 1 |
| `pageSize` | `10` | Số dòng mỗi trang, tối đa 100 (giao diện dùng 10/20/50) |

Chỉ trả về công việc người gọi được xem. Mặc định xếp theo bậc ưu tiên (việc đang chờ chính người gọi hành động lên đầu), cùng bậc thì hạn xử lý gần trước. Bậc 1 gồm việc **Chờ duyệt** mà người gọi là chỉ đạo, chủ trì hoặc người tạo; bậc 2 gồm việc **Chờ xử lý / Đang xử lý** mà người gọi là chủ trì hoặc tham gia.

```json
{
  "count": 4,
  "page": 1,
  "pageSize": 10,
  "totalPages": 1,
  "results": [
    {
      "id": 19,
      "title": "Chuẩn bị báo cáo quý 3",
      "requirement": "Tổng hợp số liệu",
      "createdDate": "2026-09-19",
      "dueDate": "2026-09-24",
      "status": "CHO_DUYET",
      "statusLabel": "Chờ duyệt",
      "isPublic": true,
      "creator": { "id": 2, "fullName": "Trần Phương Duy", "position": "Nhân viên" },
      "host": { "id": 3, "fullName": "Phan Quốc Dũng", "position": "Nhân viên" },
      "directors": [{ "id": 1, "fullName": "Nguyễn Thu Hiền", "position": "Nhân viên" }],
      "participants": [{ "id": 4, "fullName": "Nguyễn Bình Minh", "position": "Nhân viên" }],
      "myRoles": ["THAM_GIA"],
      "permissions": { "canEdit": false, "canDelete": false, "canApprove": false, "canUnapprove": false }
    }
  ]
}
```

- `myRoles`: vai trò của người gọi — `NGUOI_TAO`, `CHU_TRI`, `CHI_DAO`, `THAM_GIA` (có thể nhiều, ví dụ người tạo kiêm chủ trì).
- `permissions`: backend tính sẵn, giao diện chỉ dựa vào đây để hiện / ẩn nút.
- `position` tạm cố định là `"Nhân viên"` cho tới khi nhóm 7 có dữ liệu chức vụ.

### 4.2. `POST /api/work/tasks/` — Thêm công việc

`multipart/form-data` (không gửi file thì dùng JSON cũng được).

| Trường | Bắt buộc | Mô tả |
|---|---|---|
| `title` | ✔ | Nội dung công việc |
| `createdDate` | | Mặc định hôm nay. Không được ở quá khứ |
| `dueDate` | ✔ | Phải ≥ `createdDate` |
| `requirement` | ✔ | Yêu cầu xử lý |
| `hostId` | ✔ | Id người chủ trì |
| `directorIds` | ✔ | Id người chỉ đạo, ít nhất 1 (gửi lặp lại trường cho nhiều người) |
| `participantIds` | ✔ | Id cán bộ tham gia, ít nhất 1 |
| `isPublic` | | `true` / `false`, mặc định `true` |
| `donViIds` | | Id các phòng/ban gắn với công việc, gửi lặp lại trường cho nhiều phòng |
| `documentType` | | Văn bản liên quan: `vanbanden`, `vanbandi`, `vanbanmat` |
| `documentId` | | Id văn bản của nhóm 2. Phải gửi kèm `documentType`, thiếu một trong hai sẽ bị từ chối |
| `attachments` | | Nhiều file giao việc, không bắt buộc |

- Mỗi cán bộ chỉ giữ một vai trò; người tạo được kiêm vai trò.
- Người tạo là người đang gọi API.
- Trả về `201` với dữ liệu dạng chi tiết (mục 4.3).
- **Gửi mail** sau khi lưu thành công, xem mục 7.

### 4.3. `GET /api/work/tasks/{id}/` — Chi tiết

Gồm toàn bộ trường của danh sách, cộng thêm:

```json
{
  "permissions": {
    "canEdit": false, "canDelete": false, "canApprove": false, "canUnapprove": false,
    "canSubmitEvidence": true, "canComment": true
  },
  "firstOpenedAt": "2026-09-19T11:17:27.645596+07:00",
  "firstOpenedBy": { "id": 4, "fullName": "Nguyễn Bình Minh", "position": "Nhân viên" },
  "firstEvidenceAt": "2026-09-19T11:17:27.840724+07:00",
  "approvedAt": null,
  "approvedBy": null,
  "attachments": [
    {
      "id": 5, "kind": "GIAO_VIEC", "fileName": "Kế hoạch.pdf", "size": 8,
      "uploadedBy": { "id": 2, "fullName": "Trần Phương Duy", "position": "Nhân viên" },
      "uploadedAt": "2026-09-19T11:17:27.649702+07:00", "commentId": null,
      "downloadUrl": "/api/work/attachments/5/download/",
      "canDelete": false, "deleteBlockedReason": null
    }
  ],
  "evidences": [
    {
      "id": 6, "kind": "BANG_CHUNG", "fileName": "Kết quả.pdf", "size": 11,
      "uploadedBy": { "id": 4, "fullName": "Nguyễn Bình Minh", "position": "Nhân viên" },
      "uploadedAt": "2026-09-19T11:17:27.840724+07:00", "commentId": 5,
      "downloadUrl": "/api/work/attachments/6/download/",
      "canDelete": true, "deleteBlockedReason": null
    }
  ],
  "commentCount": 1,
  "donViIds": [3, 5],
  "documentType": null,
  "documentId": null
}
```

- `attachments`: file giao việc. `evidences`: toàn bộ file kết quả (mỗi file thuộc một ý kiến qua `commentId`).
- `canSubmitEvidence`: được kèm file kết quả khi ghi ý kiến.
- `downloadUrl`: **đường dẫn tương đối** (`/api/work/attachments/{id}/download/`), không kèm domain/cổng, vì proxy có thể chuyển `Host` mất cổng. Frontend dựng URL đầy đủ từ `API_BASE_URL`/origin trang (`resolveDownloadUrl` trong `api/taskActions.ts`, vẫn chấp nhận URL tuyệt đối cũ).
- `deleteBlockedReason`: chỉ có với **người đã tải file**, khi họ chưa xóa được file đó (đã duyệt, hoặc là file kết quả cuối cùng sau hạn), để giao diện hiện lý do và cách xử lý.

### 4.4. `PATCH /api/work/tasks/{id}/` — Sửa

- Người tạo và chủ trì, HOẶC có quyền `change_congviec`; chỉ khi Chờ xử lý hoặc Đang xử lý.
- Gửi trường nào sửa trường đó (cùng tên trường như khi thêm). Riêng người liên quan: muốn đổi thì gửi **đủ cả** `hostId`, `directorIds`, `participantIds`.
- `createdDate` được giữ ngày cũ (không bắt buộc ≥ hôm nay); `dueDate` khi sửa phải ≥ hôm nay.
- `attachments`: thêm file giao việc mới. `removeAttachmentIds`: id file giao việc muốn bỏ.
- `donViIds`: gửi lên là thay toàn bộ danh sách phòng/ban; gửi danh sách rỗng là bỏ hết.
- Trả về `200` với dữ liệu chi tiết. **Không gửi mail.**

### 4.5. `DELETE /api/work/tasks/{id}/` — Xóa

Người tạo và chủ trì, HOẶC có quyền `delete_congviec`, ở mọi trạng thái. Xóa hẳn công việc, người liên quan, ý kiến và file (kể cả file trên đĩa). Trả về `204`.

### 4.6. `POST /api/work/tasks/{id}/open/` — Ghi nhận mở

Giao diện gọi ngay khi vào trang chi tiết. Nếu người gọi là chủ trì / chỉ đạo / tham gia, công việc chưa ai mở và chưa quá hạn, thì ghi `firstOpenedAt` (Chờ xử lý → Đang xử lý). Người tạo mở không tính. Luôn trả về `200` với dữ liệu chi tiết.

## 5. Ý kiến và file kết quả

**Nộp kết quả = ghi ý kiến kèm file.** Không có API nộp bằng chứng riêng.

### 5.1. `GET /api/work/tasks/{id}/comments/`

Mọi người xem được công việc đều đọc được. Sắp xếp cũ → mới.

```json
[
  {
    "id": 5,
    "content": "Gửi kết quả",
    "author": { "id": 4, "fullName": "Nguyễn Bình Minh", "position": "Nhân viên" },
    "createdAt": "2026-09-19T11:17:27.839821+07:00",
    "attachments": [
      {
        "id": 6, "kind": "BANG_CHUNG", "fileName": "Kết quả.pdf", "size": 11,
        "uploadedBy": { "id": 4, "fullName": "Nguyễn Bình Minh", "position": "Nhân viên" },
        "uploadedAt": "2026-09-19T11:17:27.840724+07:00", "commentId": 5,
        "downloadUrl": "/api/work/attachments/6/download/",
        "canDelete": true, "deleteBlockedReason": null
      }
    ]
  }
]
```

### 5.2. `POST /api/work/tasks/{id}/comments/`

`multipart/form-data`:

| Trường | Bắt buộc | Mô tả |
|---|---|---|
| `content` | * | Nội dung, tối đa 5000 ký tự |
| `files` | * | File kết quả, nhiều file, không bắt buộc |

\* Phải có ít nhất một trong hai.

- Người ghi: mọi người liên quan, khi công việc không bị khóa.
- Kèm file: chỉ chủ trì và cán bộ tham gia, khi chưa Hoàn thành. Người tạo / chỉ đạo kèm file nhận `403`.
- Ý kiến có file đầu tiên chuyển công việc sang **Chờ duyệt**.
- Trả về `201` với ý kiến vừa ghi (dạng như 5.1). Ý kiến không sửa, không xóa được.

### 5.3. `DELETE /api/work/tasks/{id}/evidences/{fileId}/`

**Xóa mềm**: bản ghi và file vật lý vẫn giữ, chỉ bật cờ `is_deleted`. File đã xóa không hiện
trong danh sách, không tải xuống được và không tính vào trạng thái công việc.

- Chỉ người đã tải file, khi công việc chưa duyệt.
- Sau hạn **không xóa được file kết quả cuối cùng**: `400` — "Công việc đã quá hạn, không thể xóa file bằng chứng cuối cùng. Hãy nộp file mới trước rồi xóa file cũ sau."
- Ý kiến chứa file vẫn được giữ. Xóa hết file kết quả thì công việc quay về Đang xử lý.
- Trả về `200` với dữ liệu chi tiết.

## 6. Duyệt

| API | Ai | Điều kiện | Kết quả |
|---|---|---|---|
| `POST tasks/{id}/approve/` | Người tạo, chủ trì, chỉ đạo, hoặc có quyền `approve_congviec` | Chờ duyệt (kể cả đã quá hạn) | Hoàn thành |
| `POST tasks/{id}/unapprove/` | Người tạo, chủ trì, chỉ đạo, hoặc có quyền `approve_congviec` | Hoàn thành | Chờ duyệt, duyệt lại được |

Cả hai trả về `200` với dữ liệu chi tiết. Hai người bấm cùng lúc thì người sau nhận `400` kèm lời nhắc tải lại trang.

## 7. Gửi mail khi thêm công việc

- **Khi nào:** chỉ khi thêm mới thành công (`POST tasks/`). Sửa không gửi.
- **Gửi cho:** chủ trì, chỉ đạo, cán bộ tham gia; **trừ người tạo** (kể cả khi người tạo kiêm vai trò). Mỗi người một thư, nêu vai trò của họ, nội dung, yêu cầu, ngày tạo, hạn xử lý, người chủ trì.
- **Không gửi:** công việc đang ẩn (`isPublic = false`), vì người nhận chưa mở được; người chưa khai báo email.
- **Cấu hình:** dùng `MAILERS["default"]` trong `settings.py`, hiện là `console.EmailBackend` (thư in ra cửa sổ chạy `runserver`). Module tự đọc backend từ `MAILERS` vì dự án đang dùng Django 5.2, bản này chưa hiểu setting `MAILERS`.
- Gửi lỗi (ví dụ máy chủ mail không phản hồi) chỉ ghi log, **không** làm hỏng việc thêm công việc.

## 8. API dùng chung

### 8.1. `GET /api/work/tasks/latest/?limit=5` — cho trang chủ (nhóm 1)

`limit` từ 1 đến 20, mặc định 5. Chỉ gồm công việc người gọi được xem, mới nhất trước.

```json
[{ "id": 19, "title": "Chuẩn bị báo cáo quý 3", "createdDate": "2026-09-19", "dueDate": "2026-09-24", "status": "CHO_DUYET", "statusLabel": "Chờ duyệt" }]
```

### 8.2. `GET /api/work/attachments/{id}/download/`

Trả nội dung file, tên tải về là tên gốc. Người không xem được công việc chứa file nhận `404`. Trình duyệt phải tải bằng `fetch` có header xác thực (thẻ `<a href>` thường không gửi được header), xem `downloadAttachment()` trong `api/taskActions.ts`.

### 8.3. `GET /api/work/employees/?search=`

Danh sách cán bộ đang hoạt động, tìm theo họ tên, tên đăng nhập, **tên đơn vị (phòng ban)** hoặc **tên chức vụ**:
`[{ "id": 3, "fullName": "Phan Quốc Dũng", "position": "Nhân viên", "username": "chutri" }]`

### 8.4. `GET /api/work/me/`

`{ "id": 4, "fullName": "Nguyễn Bình Minh", "position": "Nhân viên", "username": "thamgia", "isAdmin": false }`
