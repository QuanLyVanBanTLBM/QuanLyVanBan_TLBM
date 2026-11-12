# HƯỚNG DẪN NHIỆM VỤ: NGUYỄN CHÍ TÍN

- **Họ và tên:** Nguyễn Chí Tín
- **Vai trò:** Thành viên Nhóm 4 — Phân hệ Tài Liệu & Biểu Mẫu (BM)
- **Nhiệm vụ chính:** 
  1. **Xây dựng Model Backend `TaiLieuChiTiet`:** Cấu trúc theo đúng bảng `records_chitiettailieu` và quan hệ ManyToMany `records_chitiettailieu_loaitailieu`.
  2. **Xây dựng hệ thống REST APIs cho Danh sách Tài liệu chung:**
     - CRUD tài liệu chi tiết.
     - Xử lý chọn nhiều loại tài liệu (ManyToMany).
     - Quản lý trạng thái hiệu lực: `CON_HIEU_LUC`, `HET_HIEU_LUC`, `HET_VA_THAY_THE`.
     - Xử lý Upload file đính kèm: Giới hạn định dạng (`.pdf`, `.doc`, `.docx`, `.jpg`, `.jpeg`, `.png`, `.zip`, `.rar`) và dung lượng tối đa 20MB.
     - Phân quyền hiển thị: `TAT_CA` (Tất cả) hoặc `NOI_BO_PHONG_BAN` (Nội bộ phòng ban).
     - Bộ lọc đa tiêu chí: Lọc theo Cấp 1 (`dm_tai_lieu`), Cấp 2 (`loai_tai_lieu`), Năm đăng, Hiệu lực, Tìm kiếm tiêu đề/ký hiệu.
     - Xuất Excel danh sách tài liệu theo đúng bộ lọc tìm kiếm.

---

## 1. QUY TRÌNH GIT VÀ WORKTREE CỦA BẠN

### 1.1. Chuẩn bị Fork và Remote (chỉ làm lần đầu)
Mở Terminal tại thư mục `QuanLyVanBan_TLBM` trên máy của bạn:
```bash
git remote add upstream https://github.com/QuanLyVanBanTLBM/QuanLyVanBan_TLBM.git
git fetch upstream --prune
```

### 1.2. Tạo Worktree riêng cho task Backend
```bash
git worktree add -b feat/backend-document-list ../qlvb-backend-document-list upstream/4_documents_templates
cd ../qlvb-backend-document-list
```

### 1.3. Đẩy code và mở Pull Request
Sau khi code và chạy test Backend:
```bash
git status
git add .
git commit -m "feat(backend): implement Document Detail API, file upload validation, and excel export"
git push -u fork HEAD
```
Vào GitHub fork cá nhân của bạn, mở Pull Request:
- **Base repository:** `QuanLyVanBanTLBM/QuanLyVanBan_TLBM`
- **Base branch:** `4_documents_templates` *(Lưu ý: Không chọn staging hoặc main)*
- Báo Trưởng nhóm Thượng Mạnh Quỳnh review.

---

## 2. CHI TIẾT FILE VÀ MÃ NGUỒN PHỤ TRÁCH

### 2.1. Model trong `backend/apps/document_templates/models.py`
Khớp 100% với file SQL `records_chitiettailieu` và Google Sheets:

```python
import os
from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from .models import DanhMucTaiLieu, LoaiTaiLieu

# Hàm kiểm tra định dạng và dung lượng file đính kèm (< 20MB)
def validate_document_file(file):
    max_size_mb = 20
    if file.size > max_size_mb * 1024 * 1024:
        raise ValidationError(f"Dung lượng tệp đính kèm không được vượt quá {max_size_mb}MB.")
    
    valid_extensions = ['.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png', '.zip', '.rar']
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in valid_extensions:
        raise ValidationError(f"Định dạng tệp {ext} không được hỗ trợ. Chỉ chấp nhận PDF, DOC, DOCX, JPG, PNG, ZIP, RAR.")

class TaiLieuChiTiet(models.Model):
    HIEU_LUC_CHOICES = [
        ('CON_HIEU_LUC', 'Còn hiệu lực'),
        ('HET_HIEU_LUC', 'Hết hiệu lực'),
        ('HET_VA_THAY_THE', 'Hết hiệu lực và thay thế'),
    ]

    HIEN_THI_CHOICES = [
        ('TAT_CA', 'Tất cả'),
        ('NOI_BO_PHONG_BAN', 'Nội bộ phòng ban'),
    ]

    dm_tai_lieu = models.ForeignKey(
        DanhMucTaiLieu, 
        on_delete=models.RESTRICT, 
        related_name='tai_lieu_thuoc_danh_muc',
        verbose_name="Danh mục tài liệu (Cấp 1)"
    )
    loai_tai_lieu = models.ManyToManyField(
        LoaiTaiLieu, 
        blank=True, 
        related_name='tai_lieu_thuoc_loai',
        verbose_name="Loại tài liệu (Cấp 2)"
    )
    ky_hieu = models.CharField(max_length=255, blank=True, null=True, verbose_name="Ký hiệu tài liệu")
    tieu_de = models.CharField(max_length=255, verbose_name="Tiêu đề")
    ngay_dang = models.DateField(verbose_name="Ngày đăng")
    noi_ban_hanh = models.CharField(max_length=255, blank=True, null=True, verbose_name="Nơi ban hành")
    hieu_luc = models.CharField(max_length=30, choices=HIEU_LUC_CHOICES, default='CON_HIEU_LUC', verbose_name="Hiệu lực")
    ngay_het_hieu_luc = models.DateField(blank=True, null=True, verbose_name="Ngày hết hiệu lực")
    link_thay_the = models.CharField(max_length=500, blank=True, null=True, verbose_name="Link văn bản thay thế")
    ghi_chu = models.TextField(blank=True, null=True, verbose_name="Ghi chú")
    file_dinh_kem = models.FileField(upload_to='documents/templates/', validators=[validate_document_file], verbose_name="File đính kèm")
    hien_thi = models.CharField(max_length=30, choices=HIEN_THI_CHOICES, default='TAT_CA', verbose_name="Hiển thị")
    nguoi_tao = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Người tạo")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "records_chitiettailieu"
        ordering = ["-ngay_dang", "-id"]
```

### 2.2. Serializers trong `backend/apps/document_templates/serializers.py`
- `TaiLieuChiTietSerializer`: Bao gồm thông tin chi tiết, URL tải file đính kèm, danh sách id và tên của `loai_tai_lieu`.

### 2.3. ViewSet trong `backend/apps/document_templates/views.py`
- `TaiLieuChiTietViewSet`:
  - Kế thừa `viewsets.ModelViewSet`.
  - Hỗ trợ `filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]`.
  - Cho phép lọc: `dm_tai_lieu`, `loai_tai_lieu`, `hieu_luc`, `nam` (lọc theo `ngay_dang__year`).
  - Search theo `tieu_de`, `ky_hieu`, `noi_ban_hanh`.
  - Action `@action(detail=False, methods=['get'], url_path='export-excel')` để xuất file `.xlsx` danh sách tài liệu dựa trên kết quả lọc hiện tại bằng thư viện `openpyxl`.

---

## 3. CHECKLIST KIỂM TRA TRƯỚC KHI MỞ PULL REQUEST
- [ ] Test upload file định dạng hợp lệ (`.pdf`, `.docx`) và file không hợp lệ (`.exe`, `.mp4` - phải báo lỗi).
- [ ] Test upload file lớn hơn 20MB (phải báo lỗi đúng thông điệp).
- [ ] API xuất Excel chạy tải về file `.xlsx` chuẩn và mở được.
- [ ] Bộ lọc theo `dm_tai_lieu` và `loai_tai_lieu` trả về đúng kết quả dữ liệu.
- [ ] Chạy `python manage.py check` không báo lỗi cú pháp.
