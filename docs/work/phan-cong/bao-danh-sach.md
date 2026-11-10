# Phân công — Nguyễn Duy Bảo: Bảng danh sách công việc

> Module **Công việc** · Nhóm 6
> Nhánh làm việc: **`6_tasks-bao-danh-sach`** → PR vào **`6_tasks`**. **Không PR thẳng vào `staging`.**
> Ước lượng: khoảng **10 giờ** công.

Việc của bạn là làm **bảng hiển thị danh sách công việc** — phần người dùng nhìn thấy
đầu tiên khi vào module. Nhận dữ liệu vào rồi vẽ ra, không cần đụng backend.

---

## Chuẩn bị (làm 1 lần)

Mở terminal trong thư mục dự án, chạy lần lượt:

```bash
git fetch --all
git checkout 6_tasks
git pull origin 6_tasks
git checkout -b 6_tasks-bao-danh-sach
```

Cài đặt:

```bash
cd frontend
npm install
npm run dev
```

Mở trình duyệt vào `http://localhost:5173/`, bấm menu **Công việc** ở bên trái.

---

## Việc 1 — TaskAssigneeCell.tsx (dễ nhất, làm trước)

**File:** `frontend/src/modules/work/components/TaskAssigneeCell.tsx`

Đây là ô "Người thực hiện" trong bảng. Nhận danh sách người rồi hiển thị như sau:

```
Chủ trì: Phan Quốc Dũng
Cán bộ thực hiện:
- Nguyễn Thu Hiền
- Nguyễn Bình Minh
```

Kiểu dữ liệu xem trong `frontend/src/modules/work/types/task.ts`.
Mở file đó ra xem trước khi làm.

**Cách kiểm tra:** tạo dữ liệu giả trong file, gọi component ra xem có hiện đúng không.

---

## Việc 2 — TaskPagination.tsx

**File:** `frontend/src/modules/work/components/TaskPagination.tsx`

Thanh phân trang ở cuối bảng, gồm:

- Nút **Trang trước** / **Trang sau**
- Số trang hiện tại, ví dụ "Trang 2 / 5"
- Ô chọn số dòng mỗi trang: 10, 20, 50

Khi bấm thì gọi hàm được truyền vào qua props. Component này **không tự gọi API**.

---

## Việc 3 — TaskTable.tsx (khó nhất, làm cuối)

**File:** `frontend/src/modules/work/components/TaskTable.tsx`

Bảng 9 cột, theo đúng ảnh mẫu thầy đưa:

| Cột | Nội dung |
|---|---|
| TT | Số thứ tự |
| Nội dung công việc | Tiêu đề, bấm vào thì gọi hàm `onOpenTask` |
| Người giao | Tên ở dòng trên, chức vụ trong ngoặc ở dòng dưới |
| Yêu cầu xử lý | Chữ |
| Người thực hiện | Dùng `TaskAssigneeCell` bạn vừa làm ở Việc 1 |
| Ngày giao | Định dạng `dd/mm/yyyy` |
| Hạn xử lý | Định dạng `dd/mm/yyyy` |
| Trạng thái | Dùng `TaskStatusBadge` của Phát |
| Tác vụ | Nút sửa, nút xóa, nút duyệt |

**Lưu ý quan trọng:**

- Dòng nào có `isPublic = false` thì tô nền khác và ghi nhãn "Đang ẩn"
- Ngày phải hiện `dd/mm/yyyy`, không phải `mm/dd/yyyy`
- **Không tự tính trạng thái.** API trả về sao thì hiện vậy
- Ở màn hình hẹp thì bảng cuộn ngang được

---

## Quy tắc về màu sắc

Dự án có 2 giao diện sáng và tối. **Không được viết màu cụ thể** kiểu `color: "#333"`.

Mở file `frontend/src/shared/styles/global.css` xem danh sách biến màu, rồi dùng như sau:

```tsx
style={{ color: "var(--text-main)" }}
```

Xem file `frontend/src/modules/dashboard/pages/DashboardPage.tsx` để học cách viết.

**Nhớ thử cả 2 giao diện sáng và tối**, có nút đổi ở góc trên bên phải.

---

## Tiêu chí hoàn thành

- [ ] Bảng hiện đủ 9 cột, đúng thứ tự như ảnh mẫu
- [ ] Ngày hiện đúng `dd/mm/yyyy`
- [ ] Dòng ẩn có màu nền khác và nhãn "Đang ẩn"
- [ ] Bấm vào tiêu đề thì gọi đúng hàm `onOpenTask`
- [ ] Hiển thị đúng ở cả giao diện sáng và tối
- [ ] `npm run build` chạy qua, không báo lỗi

---

## Khi làm xong

```bash
cd frontend
npm run build
```

Nếu không báo lỗi thì đẩy lên:

```bash
git add .
git commit -m "feat(work): them TaskTable, TaskAssigneeCell, TaskPagination"
git push origin 6_tasks-bao-danh-sach
```

Rồi vào GitHub tạo **Pull Request** vào nhánh `6_tasks`, nhắn Đức review.

---

## Phụ thuộc

- **Đức**: file `types/task.ts` để biết kiểu dữ liệu
- **Phát**: `TaskStatusBadge` cho cột Trạng thái

Chưa có thì cứ tạo dữ liệu giả và dùng chữ tạm để làm trước.

---

## Tuyệt đối không được

- Sửa file trong thư mục `backend/`
- Sửa file trong thư mục `frontend/src/shared/`
- Sửa file `router.tsx`
- Sửa component của Phát hoặc Vĩ
- Cài thêm thư viện mới (`npm install ...`)

**Cần sửa gì ngoài 3 file của mình thì nhắn Đức, đừng tự sửa.**

---

## Bị kẹt thì làm gì

1. Xem file `DashboardPage.tsx` của nhóm 1 để học cách viết
2. Nhắn Đức
3. Đừng ngồi kẹt quá 30 phút mà không hỏi
