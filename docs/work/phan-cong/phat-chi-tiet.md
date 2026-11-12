# Phân công — Đỗ Ngọc Phát: Component dùng chung của module

> Module **Công việc** · Nhóm 6
> Nhánh làm việc: **`6_tasks-phat-components`** → PR vào **`6_tasks`**. **Không PR thẳng vào `staging`.**
> Ước lượng: khoảng **10 giờ** công.
> Bạn làm **sớm nhất** vì Bảo và Vĩ đều cần dùng component của bạn.

---

## Chuẩn bị (làm 1 lần)

Mở terminal trong thư mục dự án, chạy lần lượt:

```bash
git fetch --all
git checkout 6_tasks
git pull origin 6_tasks
git checkout -b 6_tasks-phat-components
```

Cài đặt:

```bash
cd frontend
npm install
npm run dev
```

Mở trình duyệt vào `http://localhost:5173/`, bấm menu **Công việc** ở bên trái.

---

## Việc 1 — TaskStatusBadge.tsx (dễ nhất, làm trước)

**File:** `frontend/src/modules/work/components/TaskStatusBadge.tsx`

Cái nhãn màu nhỏ hiển thị trạng thái công việc. Có 6 trạng thái, mỗi cái một màu:

| Trạng thái | Màu gợi ý |
|---|---|
| Chờ xử lý | Xám |
| Đang xử lý | Xanh dương |
| Chờ duyệt | Vàng / cam |
| Hoàn thành | Xanh lá |
| Chưa hoàn thành | Cam đậm |
| Quá hạn | Đỏ |

Nhận vào trạng thái, trả ra một cái nhãn bo tròn có nền màu nhạt và chữ màu đậm.

**Làm xong cái này đẩy lên ngay**, Bảo và Vĩ đang cần để làm phần của họ.

---

## Việc 2 — WorkAlert.tsx

**File:** `frontend/src/modules/work/components/WorkAlert.tsx`

Khung thông báo hiện ra khi có lỗi hoặc thành công. Có 4 loại:

- **success** — xanh lá, khi lưu thành công
- **warning** — vàng, khi cảnh báo
- **danger** — đỏ, khi có lỗi
- **info** — xanh dương, khi thông tin thường

Gồm icon bên trái, nội dung ở giữa, nút X đóng bên phải (tùy chọn).

---

## Việc 3 — WorkModal.tsx

**File:** `frontend/src/modules/work/components/WorkModal.tsx`

Khung cửa sổ bật lên giữa màn hình, nền phía sau mờ đi. Gồm:

- Tiêu đề ở trên, nút X để đóng
- Phần nội dung ở giữa (nhận vào qua `children`)
- Bấm phím **Esc** thì đóng
- Khi modal mở thì **khóa cuộn của trang nền**

**Một lưu ý quan trọng:** đặt `z-index` cao hơn thanh menu bên trái. Nếu không, khi rê
chuột qua menu thì trang bị đổi và form đang nhập sẽ mất hết.

---

## Việc 4 — ConfirmDialog.tsx

**File:** `frontend/src/modules/work/components/ConfirmDialog.tsx`

Hộp thoại hỏi "Bạn có chắc không?" trước khi xóa hoặc hủy duyệt.

Dùng lại `WorkModal` bạn vừa làm ở Việc 3, thêm vào:

- Dòng tiêu đề, ví dụ "Xóa công việc"
- Dòng nội dung, ví dụ "Bạn có chắc muốn xóa công việc này? Thao tác này không hoàn tác được."
- Hai nút: **Hủy** và **Xác nhận**
- Nút Xác nhận có 2 kiểu: thường (xanh) và nguy hiểm (đỏ, dùng khi xóa)
- Khi đang xử lý thì nút hiện chữ "Đang xử lý..." và không bấm được nữa

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

- [ ] Badge hiện đúng 6 trạng thái, mỗi trạng thái một màu
- [ ] Modal đóng được bằng phím Esc và nút X
- [ ] Modal không bị mất khi rê chuột qua menu bên trái
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
git commit -m "feat(work): them TaskStatusBadge, WorkAlert, WorkModal, ConfirmDialog"
git push origin 6_tasks-phat-components
```

Rồi vào GitHub tạo **Pull Request** vào nhánh `6_tasks`, nhắn Đức review.

> Làm xong `TaskStatusBadge` và `WorkAlert` thì **đẩy lên luôn**, đừng chờ xong hết 4 cái.
> Bảo và Vĩ đang chờ dùng.

---

## Phụ thuộc

Không phụ thuộc ai, bắt đầu được ngay.

---

## Tuyệt đối không được

- Sửa file trong thư mục `backend/`
- Sửa file trong thư mục `frontend/src/shared/`
- Sửa file `router.tsx`
- Sửa component của Bảo hoặc Vĩ
- Cài thêm thư viện mới (`npm install ...`)

**Cần sửa gì ngoài 4 file của mình thì nhắn Đức, đừng tự sửa.**

---

## Bị kẹt thì làm gì

1. Xem file `DashboardPage.tsx` của nhóm 1 để học cách viết
2. Nhắn Đức
3. Đừng ngồi kẹt quá 30 phút mà không hỏi
