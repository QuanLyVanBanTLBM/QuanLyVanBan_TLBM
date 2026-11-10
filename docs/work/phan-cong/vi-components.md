# Phân công — Lâm Chí Vĩ: Các khối hiển thị trang chi tiết

> Module **Công việc** · Nhóm 6
> Nhánh làm việc: **`6_tasks-vi-hien-thi`** → PR vào **`6_tasks`**. **Không PR thẳng vào `staging`.**
> Ước lượng: khoảng **8 giờ** công.

Việc của bạn là **hiển thị thông tin ra màn hình**. Nhận dữ liệu vào rồi vẽ ra.
Không có logic phức tạp, không cần đụng backend.

---

## Chuẩn bị (làm 1 lần)

Mở terminal trong thư mục dự án, chạy lần lượt:

```bash
git fetch --all
git checkout 6_tasks
git pull origin 6_tasks
git checkout -b 6_tasks-vi-hien-thi
```

Cài đặt:

```bash
cd frontend
npm install
npm run dev
```

Mở trình duyệt vào `http://localhost:5173/`, bấm menu **Công việc** ở bên trái.

---

## Việc 1 — TaskInfoCard.tsx (dễ nhất, làm trước)

**File:** `frontend/src/modules/work/components/TaskInfoCard.tsx`

Khối hiển thị thông tin công việc:

- Nội dung công việc
- Yêu cầu xử lý
- Ngày giao và Hạn xử lý, định dạng `dd/mm/yyyy`
- Bên cạnh hạn xử lý ghi thêm: "còn 3 ngày" hoặc "quá hạn 2 ngày"

Kiểu dữ liệu xem trong `frontend/src/modules/work/types/task.ts`.
Mở file đó ra xem trước khi làm.

---

## Việc 2 — TaskPeopleCard.tsx

**File:** `frontend/src/modules/work/components/TaskPeopleCard.tsx`

Khối hiển thị những người liên quan, chia theo 4 nhóm:

```
Người giao:      Trần Phương Duy (Nhân viên)
Chủ trì:         Phan Quốc Dũng (Nhân viên)
Chỉ đạo:         Nguyễn Thu Hiền (Nhân viên)
Cán bộ tham gia: Nguyễn Bình Minh (Nhân viên)
                 Lê Văn A (Nhân viên)
```

**Thêm một chi tiết nhỏ:** nếu người đó chính là người đang đăng nhập thì gắn nhãn
"Bạn" bên cạnh tên.

---

## Việc 3 — TaskAttachmentList.tsx

**File:** `frontend/src/modules/work/components/TaskAttachmentList.tsx`

Danh sách file đính kèm, mỗi dòng gồm:

- Icon theo loại file (PDF khác, ảnh khác, Word khác)
- Tên file
- Dung lượng, ví dụ "2.4 MB"
- Nút tải xuống
- Nút xóa — chỉ hiện khi được truyền vào `onDelete`

Component này dùng cho **cả hai chỗ**: file đính kèm lúc giao việc, và file bằng chứng.
Nên viết sao cho linh hoạt, nhận danh sách file rồi hiển thị.

---

## Việc 4 — TaskCommentPanel.tsx

**File:** `frontend/src/modules/work/components/TaskCommentPanel.tsx`

Khu vực ý kiến, gồm 2 phần:

**Phần trên** — danh sách ý kiến đã ghi, cũ ở trên mới ở dưới. Mỗi ý kiến hiện:
- Tên người ghi
- Thời điểm, định dạng `dd/mm/yyyy HH:mm`
- Nội dung

**Phần dưới** — ô nhập ý kiến mới và nút "Gửi ý kiến".
Bên dưới ghi dòng nhỏ: *"Ý kiến đã gửi không thể sửa hoặc xóa."*

**Trường hợp đặc biệt:** nếu công việc đã bị đóng băng (trạng thái Quá hạn hoặc
Chưa hoàn thành) thì **ẩn ô nhập đi**, thay bằng dòng chữ giải thích lý do.

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

- [ ] Bốn khối hiển thị đúng dữ liệu, không lỗi
- [ ] Ngày hiện đúng `dd/mm/yyyy`, giờ hiện `dd/mm/yyyy HH:mm`
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
git commit -m "feat(work): them cac khoi hien thi trang chi tiet"
git push origin 6_tasks-vi-hien-thi
```

Rồi vào GitHub tạo **Pull Request** vào nhánh `6_tasks`, nhắn Đức review.

---

## Phụ thuộc

- **Đức**: file `types/task.ts` để biết kiểu dữ liệu
- **Phát**: `TaskStatusBadge`, `WorkAlert` nếu cần dùng

Chưa có thì cứ tạo dữ liệu giả trong file để làm trước.

---

## Tuyệt đối không được

- Sửa file trong thư mục `backend/`
- Sửa file trong thư mục `frontend/src/shared/`
- Sửa file `router.tsx`
- Sửa component của Bảo hoặc Phát
- Cài thêm thư viện mới (`npm install ...`)

**Cần sửa gì ngoài 4 file của mình thì nhắn Đức, đừng tự sửa.**

---

## Bị kẹt thì làm gì

1. Xem file `DashboardPage.tsx` của nhóm 1 để học cách viết
2. Nhắn Đức
3. Đừng ngồi kẹt quá 30 phút mà không hỏi
