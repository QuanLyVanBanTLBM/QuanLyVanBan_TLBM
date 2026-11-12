# HƯỚNG DẪN NHIỆM VỤ: THƯỢNG MẠNH QUỲNH (NHÓM TRƯỞNG NHÓM 4)

- **Họ và tên:** Thượng Mạnh Quỳnh
- **Vai trò:** Trưởng Nhóm 4 — Phân hệ Tài Liệu & Biểu Mẫu (BM)
- **Nhiệm vụ chính:** 
  1. Điều hướng 3 tầng: Danh mục tài liệu (Cấp 1) ➔ Loại tài liệu (Cấp 2) ➔ Chi tiết tài liệu.
  2. Xây dựng Bộ lọc 2 cấp phân tầng (Cascading Filter: Cấp 1 ➔ Cấp 2) trên trang chính `/resources`.
  3. Quản lý nhóm, review và merge Pull Request (PR) của các thành viên (Trang, Tín, Phong).
  4. Đồng bộ nhánh nhóm với `staging` của tổ chức, kiểm thử end-to-end trước khi demo/nộp bài.

---

## 1. QUY TRÌNH GIT VÀ WORKTREE CỦA NHÓM TRƯỞNG

### 1.1. Cập nhật worktree hiện tại (`qlvb-category-detail-link`)
Bạn đã tạo sẵn thư mục `qlvb-category-detail-link` tại máy local. Để kéo toàn bộ source code mới nhất (`backend/`, `frontend/`, `docs/`...) từ nhánh `4_documents_templates`:

```bash
cd d:\Django_DACK\qlvb-category-detail-link
git pull upstream 4_documents_templates
```

### 1.2. Quy trình làm việc và đẩy code
Khi bạn viết code cho phần điều hướng và bộ lọc:
```bash
# Kiểm tra trạng thái
git status

# Thêm và commit code
git add .
git commit -m "feat(navigation): integrate 3-tier cascading filter and resources main page"

# Đẩy lên nhánh của bạn trên fork
git push -u fork HEAD
```

### 1.3. Quy trình Review và Merge Pull Request của thành viên
Khi các thành viên (Trang, Tín, Phong) mở PR vào nhánh `4_documents_templates`:
1. Truy cập: `https://github.com/QuanLyVanBanTLBM/QuanLyVanBan_TLBM/pulls`
2. Mở PR của từng bạn, kiểm tra tab **Files changed** (đảm bảo không sửa nhầm file ngoài phạm vi, không commit file thừa).
3. Bấm **Approve** và **Merge pull request** (chọn *Create a merge commit*).
4. Đồng bộ máy local của bạn sau khi merge:
   ```bash
   cd d:\Django_DACK\QuanLyVanBan_TLBM
   git checkout 4_documents_templates
   git pull upstream 4_documents_templates
   git push fork 4_documents_templates
   ```

---

## 2. CHI TIẾT FILE VÀ CODE PHỤ TRÁCH

### 2.1. Frontend: Trang chủ Phân hệ Tài liệu & Biểu mẫu
- **File:** `frontend/src/pages/resources/ResourceManagementPage.tsx`
- **Mục tiêu:** 
  - Đóng vai trò trang gốc tại URL `/resources`.
  - Quản lý state tập trung: `selectedLevel1Id`, `selectedLevel2Id`, `searchTerm`, `selectedYear`, `statusFilter`.
  - Nhúng Component Bộ Lọc (`ResourceFilterBar`) của bạn.
  - Nhúng Component Bảng dữ liệu (`ResourceTable`) của bạn Phong.
  - Nhúng Modal quản lý Cấp 1 & Cấp 2 (`CategoryModal`) của bạn Trang.

### 2.2. Frontend: Component Bộ Lọc 2 Cấp phân tầng (Cascading Filter)
- **File:** `frontend/src/components/resources/ResourceFilterBar.tsx`
- **Logic hoạt động:**
  - **Dropdown Cấp 1:** Mặc định chọn *"Tài liệu chung"*. Khi người dùng chọn sang danh mục khác (ví dụ: *Khối Hỗ Trợ*, *Khu vực TP.HCM*...).
  - **Dropdown Cấp 2:** Tự động lọc các loại tài liệu con thuộc Cấp 1 tương ứng (theo `dm_tai_lieu_id`).
  - Ô tìm kiếm từ khóa (Tiêu đề, Ký hiệu), Dropdown Năm ban hành, Dropdown Hiệu lực (*Còn hiệu lực*, *Hết hiệu lực*).

### 2.3. Cấu hình Router tổng thể
- **File:** `frontend/src/app/router.tsx`
- **Thay thế:** Chuyển dòng:
  ```tsx
  <Route path="/resources" element={<SyllabusPreview activePage="resources" />} />
  ```
  Thành:
  ```tsx
  <Route path="/resources" element={<ResourceManagementPage />} />
  ```

---

## 3. CHECKLIST NGHIỆM THU CỦA NHÓM TRƯỞNG
- [ ] Worktree local đã cập nhật code mới nhất từ `upstream/4_documents_templates`.
- [ ] Dropdown Cấp 2 tự động thay đổi theo danh mục Cấp 1 đã chọn.
- [ ] Trang `/resources` hiển thị liền mạch, không còn hiện component demo SyllabusPreview.
- [ ] Đã review code và merge PR của 3 thành viên theo đúng quy trình.
- [ ] Chạy lệnh `pnpm build` và `pnpm test` tại thư mục `frontend/` vượt qua 100% không có lỗi.
