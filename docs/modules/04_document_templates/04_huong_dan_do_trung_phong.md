# HƯỚNG DẪN NHIỆM VỤ: ĐỖ TRUNG PHONG

- **Họ và tên:** Đỗ Trung Phong
- **Vai trò:** Thành viên Nhóm 4 — Phân hệ Tài Liệu & Biểu Mẫu (BM)
- **Nhiệm vụ chính:** 
  1. **Xây dựng Giao diện Bảng Danh sách Tài liệu chung:**
     - Hiển thị các cột: STT, Ký hiệu tài liệu, Tiêu đề, Nơi ban hành, Ngày đăng, Trạng thái hiệu lực, Nút tải file đính kèm, Cột Thao tác (Xem chi tiết, Sửa, Xóa).
     - **Quy chuẩn đặc biệt từ đề án:** Các dòng tài liệu có trạng thái *"Hết hiệu lực"* hoặc *"Hết hiệu lực và thay thế"* **phải tự động đổi màu nền tối hơn (dim/muted color)** để dễ phân biệt trực quan.
  2. **Popup Xem chi tiết Tài liệu:** Hiển thị modal đầy đủ tất cả các trường thông tin (Người tạo, ngày hết hiệu lực, link văn bản thay thế, ghi chú, xem trước hoặc tải file đính kèm).
  3. **Popup Thêm mới & Chỉnh sửa Tài liệu:** Form đầy đủ các trường, tích hợp component chọn file tải lên, liên kết 2 dropdown Cấp 1 và Cấp 2.
  4. **Nút Xuất Excel và Phân trang (Pagination):** Liên kết nút xuất Excel với API Backend để tải file về máy.

---

## 1. QUY TRÌNH GIT VÀ WORKTREE CỦA BẠN

### 1.1. Chuẩn bị Fork và Remote (chỉ làm lần đầu)
Mở Terminal tại thư mục `QuanLyVanBan_TLBM` trên máy của bạn:
```bash
git remote add upstream https://github.com/QuanLyVanBanTLBM/QuanLyVanBan_TLBM.git
git fetch upstream --prune
```

### 1.2. Tạo Worktree riêng cho task Frontend
```bash
git worktree add -b feat/frontend-document-list ../qlvb-frontend-document-list upstream/4_documents_templates
cd ../qlvb-frontend-document-list
```

### 1.3. Đẩy code và mở Pull Request
Sau khi code xong và chạy thử trên trình duyệt:
```bash
git status
git add .
git commit -m "feat(frontend): build ResourceTable, DetailModal, FormModal with expired row highlight"
git push -u fork HEAD
```
Vào GitHub fork cá nhân của bạn, mở Pull Request:
- **Base repository:** `QuanLyVanBanTLBM/QuanLyVanBan_TLBM`
- **Base branch:** `4_documents_templates` *(Lưu ý: Không chọn staging hoặc main)*
- Báo Trưởng nhóm Thượng Mạnh Quỳnh review.

---

## 2. CHI TIẾT FILE VÀ COMPONENT PHỤ TRÁCH

### 2.1. Bảng dữ liệu: `frontend/src/components/resources/ResourceTable.tsx`
- **Yêu cầu giao diện:**
  - Responsive, dùng CSS Variables chuẩn của dự án (`var(--bg-card)`, `var(--text-primary)`, `var(--border-color)`).
  - Tô màu tối dòng hết hiệu lực:
    ```tsx
    const isExpired = item.hieu_luc === 'HET_HIEU_LUC' || item.hieu_luc === 'HET_VA_THAY_THE';
    const rowClass = isExpired 
      ? "bg-slate-100/70 dark:bg-slate-800/60 opacity-75 text-slate-500" 
      : "hover:bg-slate-50 dark:hover:bg-slate-800/40";
    ```
  - Huy hiệu (Badge) trạng thái:
    - *Còn hiệu lực*: Màu xanh lá (`badge-success`)
    - *Hết hiệu lực*: Màu xám / đỏ nhẹ (`badge-neutral` / `badge-danger`)
    - *Hết và thay thế*: Màu cam (`badge-warning`) kèm icon link dẫn tới văn bản thay thế.
  - Phân trang: Hiển thị thanh chuyển trang phía dưới bảng (Trang trước, Trang sau, Số trang).

### 2.2. Modal Chi tiết: `frontend/src/components/resources/ResourceDetailModal.tsx`
- Modal hiển thị dạng Dialog trung tâm màn hình.
- Trình bày thông tin chia 2 cột rõ ràng, có nút bấm tải file đính kèm trực tiếp (PDF, DOCX, ZIP...).

### 2.3. Modal Thêm/Sửa tài liệu: `frontend/src/components/resources/ResourceFormModal.tsx`
- Form nhập liệu có validation:
  - Bắt buộc: Danh mục Cấp 1, Loại Cấp 2, Tiêu đề, Ngày đăng, Hiệu lực, File đính kèm, Phạm vi hiển thị.
  - Tự động thay đổi danh sách Loại Cấp 2 khi người dùng thay đổi Danh mục Cấp 1.
  - Input chọn file: Kiểm tra trước ở client nếu file > 20MB thì cảnh báo ngay trước khi bấm Lưu.

### 2.4. Khai báo Types: `frontend/src/types/resource.ts`
```typescript
export type HieuLucType = 'CON_HIEU_LUC' | 'HET_HIEU_LUC' | 'HET_VA_THAY_THE';
export type HienThiType = 'TAT_CA' | 'NOI_BO_PHONG_BAN';

export interface ResourceItem {
  id: number;
  dm_tai_lieu: number;
  dm_tai_lieu_name?: string;
  loai_tai_lieu: number[];
  loai_tai_lieu_names?: string[];
  ky_hieu?: string;
  tieu_de: string;
  ngay_dang: string;
  noi_ban_hanh?: string;
  hieu_luc: HieuLucType;
  ngay_het_hieu_luc?: string;
  link_thay_the?: string;
  ghi_chu?: string;
  file_dinh_kem: string;
  hien_thi: HienThiType;
  nguoi_tao_name?: string;
}
```

---

## 3. CHECKLIST KIỂM TRA TRƯỚC KHI MỞ PULL REQUEST
- [ ] Bảng dữ liệu hiển thị tốt trên cả 2 Theme (Clean Light và Sleek Dark).
- [ ] Các dòng hết hiệu lực hiển thị đổi màu tối đúng yêu cầu đặc tả.
- [ ] Bấm nút Xem chi tiết mở đúng Modal với dữ liệu của dòng đó.
- [ ] Bấm nút Tải file tải được file đính kèm.
- [ ] Chạy `pnpm build` không có bất kỳ lỗi TypeScript nào.
