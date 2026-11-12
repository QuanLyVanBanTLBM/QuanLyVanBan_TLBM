# HƯỚNG DẪN NHIỆM VỤ: HUỲNH THỊ KIM TRANG

- **Họ và tên:** Huỳnh Thị Kim Trang
- **Vai trò:** Thành viên Nhóm 4 — Phân hệ Tài Liệu & Biểu Mẫu (BM)
- **Nhiệm vụ chính:** 
  1. **Backend & Frontend CRUD Danh mục Tài liệu (Cấp 1):** Quản lý danh mục theo STT ưu tiên (mặc định *"Tài liệu, BM chung"* ở đầu tiên), Tên tài liệu, Ký hiệu, Ngày lập, Người lập, Ghi chú; tìm kiếm, phân trang, xuất Excel.
  2. **Backend & Frontend CRUD Loại tài liệu biểu mẫu (Cấp 2):** Quản lý loại tài liệu thuộc danh mục Cấp 1 (`dm_tai_lieu`), Tên loại, `is_public`, Ngày lập, Ghi chú; tìm kiếm theo tên loại, phân trang.

---

## 1. QUY TRÌNH GIT VÀ WORKTREE CỦA BẠN

### 1.1. Chuẩn bị Fork và Remote (chỉ làm lần đầu)
Mở Terminal tại thư mục `QuanLyVanBan_TLBM` trên máy của bạn:
```bash
# Đảm bảo đã thêm remote upstream
git remote add upstream https://github.com/QuanLyVanBanTLBM/QuanLyVanBan_TLBM.git
git fetch upstream --prune
```

### 1.2. Tạo Worktree riêng cho task
```bash
# Đứng tại thư mục chính của repo:
git worktree add -b feat/category-level1-level2 ../qlvb-category-level1-level2 upstream/4_documents_templates
cd ../qlvb-category-level1-level2
```

### 1.3. Đẩy code và mở Pull Request
Sau khi code và kiểm tra xong:
```bash
git status
git add .
git commit -m "feat(categories): implement CRUD for document categories level 1 and level 2"
git push -u fork HEAD
```
Vào GitHub fork cá nhân của bạn, mở Pull Request:
- **Base repository:** `QuanLyVanBanTLBM/QuanLyVanBan_TLBM`
- **Base branch:** `4_documents_templates` *(Lưu ý: Không chọn staging hoặc main)*
- Báo Trưởng nhóm Thượng Mạnh Quỳnh review.

---

## 2. CHI TIẾT FILE VÀ MÃ NGUỒN PHỤ TRÁCH

### 2.1. Backend (Django REST Framework)
- **Thư mục:** `backend/apps/document_templates/`

#### Các Model phụ trách trong `models.py`:
```python
from django.db import models
from django.contrib.auth.models import User

# 1. Danh mục Cấp 1 (Khớp bảng records_tailieu trong SQL)
class DanhMucTaiLieu(models.Model):
    stt_uu_tien = models.SmallIntegerField(unique=True, verbose_name="STT ưu tiên")
    ky_hieu = models.CharField(max_length=255, blank=True, null=True, verbose_name="Số ký hiệu")
    ten_tai_lieu = models.CharField(max_length=255, verbose_name="Tên tài liệu")
    nguoi_lap = models.ForeignKey(User, on_delete=models.RESTRICT, verbose_name="Người lập")
    ngay_lap = models.DateField(null=True, blank=True, verbose_name="Ngày lập")
    ghi_chu = models.TextField(blank=True, null=True, verbose_name="Ghi chú")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "records_tailieu"
        ordering = ["stt_uu_tien"]

# 2. Loại tài liệu Cấp 2 (Khớp bảng records_loaitailieu trong SQL)
class LoaiTaiLieu(models.Model):
    dm_tai_lieu = models.ForeignKey(
        DanhMucTaiLieu, 
        on_delete=models.PROTECT, 
        related_name="danh_sach_loai",
        verbose_name="Thuộc danh mục cấp 1"
    )
    ten_loai = models.CharField(max_length=255, verbose_name="Tên loại tài liệu")
    is_public = models.BooleanField(default=True, verbose_name="Công khai")
    ngay_lap = models.DateTimeField(null=True, blank=True, verbose_name="Ngày lập")
    ghi_chu = models.TextField(blank=True, null=True, verbose_name="Ghi chú")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "records_loaitailieu"
        ordering = ["id"]
```

#### Các API ViewSets trong `views.py`:
- `DanhMucTaiLieuViewSet`: 
  - `GET /api/resources/categories/` (danh sách có phân trang, lọc theo năm, tìm kiếm theo tên/ký hiệu)
  - `POST /api/resources/categories/` (thêm mới, tự động gán `nguoi_lap = request.user`, tự động tính STT = max + 1)
  - `PUT/PATCH /api/resources/categories/{id}/` (chỉnh sửa)
  - `DELETE /api/resources/categories/{id}/` (xóa)
  - `GET /api/resources/categories/export-excel/` (xuất file Excel danh mục)
- `LoaiTaiLieuViewSet`:
  - `GET /api/resources/types/?dm_tai_lieu={id}` (lấy danh sách loại theo Cấp 1 để phục vụ cho bộ lọc và form thêm mới của Tín & Phong)
  - `POST /api/resources/types/` (thêm loại mới)
  - `PUT/DELETE /api/resources/types/{id}/` (sửa/xóa)

### 2.2. Frontend (React + TypeScript)
- **Tạo Component Quản lý:** `frontend/src/components/resources/CategoryManagementModal.tsx`
  - Modal dạng Tab hoặc 2 bảng: Quản lý Danh mục Cấp 1 & Quản lý Loại Cấp 2.
  - Popup Thêm/Sửa Cấp 1 (các trường theo đúng spec: STT, Tên, Ký hiệu, Ngày lập, Ghi chú).
  - Popup Thêm/Sửa Cấp 2 (chọn Cấp 1 cha, nhập Tên loại, Checkbox isPublic, Ghi chú).
  - Nút Xuất Excel Danh mục Cấp 1.

---

## 3. CHECKLIST KIỂM TRA TRƯỚC KHI MỞ PULL REQUEST
- [ ] API CRUD Cấp 1 và Cấp 2 hoạt động tốt trên Swagger / Postman / Insomnia.
- [ ] Khi tạo danh mục Cấp 1, STT ưu tiên tự động tăng hoặc kiểm tra không được trùng.
- [ ] Khi xóa Danh mục Cấp 1 đang chứa Loại Cấp 2 con, hệ thống chặn an toàn (`PROTECT`).
- [ ] Modal trên giao diện React đóng/mở mượt mà, hỗ trợ cả 2 giao diện Clean Light & Sleek Dark.
- [ ] Không sửa đổi file của các bạn khác để tránh xung đột mã nguồn.
