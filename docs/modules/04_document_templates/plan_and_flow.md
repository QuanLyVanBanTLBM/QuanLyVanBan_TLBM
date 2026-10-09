# 📁 MODULE 4: TÀI LIỆU VÀ BIỂU MẪU (DOCUMENT TEMPLATES)
## FLOW VÀ KẾ HOẠCH TRIỂN KHAI (PLAN & FLOW)

- **Đơn vị phụ trách:** Nhóm 4
- **Nhánh phát triển:** `4_documents_templates`
- **Tài liệu đặc tả liên quan:** [`spec.md`](./spec.md)
- **Ngày cập nhật:** 2026-10-07
- **Mục tiêu MVP:** Hoàn thành luồng quản lý danh mục 3 cấp và tài liệu dùng chung trước ngày **2026-10-12** (theo issue #68).

---

## 1. KIẾN TRÚC DỮ LIỆU 3 CẤP (DATA ARCHITECTURE)

Hệ thống quản lý tài liệu và biểu mẫu được thiết kế theo phân cấp 3 tầng chuẩn hóa:

```
Cấp 1: Danh mục / Thư mục (DanhMucTaiLieu - table `records_tailieu`)
  ├── id (PK)
  ├── ten_tai_lieu ("Hồ sơ Ban Nhân sự", "Tài liệu chung",...)
  ├── ky_hieu (Mã danh mục)
  ├── stt_uu_tien (Thứ tự hiển thị tab: 1, 2, 3...)
  └── ghi_chu

Cấp 2: Loại tài liệu (LoaiTaiLieu - table `records_loaitailieu`)
  ├── id (PK)
  ├── dm_tai_lieu (FK → records_tailieu)
  ├── ten_loai ("Hợp đồng lao động", "Quyết định", "Biểu mẫu",...)
  ├── is_public (true/false: công khai hay nội bộ)
  └── ghi_chu

Cấp 3: Chi tiết tài liệu (TaiLieuChiTiet - table `records_chitiettailieu`)
  ├── id (PK)
  ├── tieu_de (Tiêu đề tài liệu)
  ├── ky_hieu (Ký hiệu văn bản: HDLD-NS-2025)
  ├── dm_tai_lieu (FK → Cấp 1)
  ├── loai_tai_lieu (M2M qua `records_chitiettailieu_loaitailieu` → Cấp 2)
  ├── hieu_luc (CON_HIEU_LUC | CON_HIEU_LUC_1_PHAN | HET_HIEU_LUC | HET_VA_THAY_THE)
  ├── ngay_dang (Ngày ban hành / đăng)
  ├── noi_ban_hanh (Cơ quan/phòng ban ban hành)
  ├── hien_thi (TAT_CA | NOI_BO_PHONG_BAN)
  ├── don_vi_id (BigInt - ID phòng ban sở hữu, chờ FK DonVi từ Nhóm 7)
  ├── nguoi_tao (FK User)
  ├── link_thay_the (URL văn bản thay thế khi HET_VA_THAY_THE)
  └── [Attachments] (1-N qua table `records_chitiettailieu_attachment`)
        ├── id (PK)
        ├── tai_lieu_chi_tiet (FK → records_chitiettailieu)
        ├── file (File đính kèm lưu trên server)
        ├── file_name (Tên file gốc)
        ├── file_size (Dung lượng file, tối đa 20MB)
        └── uploaded_at
```

---

## 2. LUỒNG NGHIỆP VỤ & TƯƠNG TÁC NGƯỜI DÙNG (USER FLOW)

### 2.1. Luồng điều hướng trang chính (`/resources`)

```
[Truy cập /resources]
       │
       ▼
┌────────────────────────────────────────────────────────────────────────┐
│  HEADER TRANG                                                          │
│  "Kho Tài Liệu & Biểu Mẫu Dùng Chung"                                  │
│  [Quản lý Danh mục & Cấp 2] (Admin/Authorized)  [+ Thêm mới tài liệu]  │
└────────────────────────────────────────────────────────────────────────┘
       │
       ▼
┌────────────────────────────────────────────────────────────────────────┐
│  THANH PHÂN CẤP CẤP 1 & CẤP 2 (Tích hợp Nút bấm Dropdown)              │
│  - Hàng 1 (Cấp 1): ◄ [Tất cả] │ [📁 Ban Nhân sự ▾] ... ► [📁 Danh mục ▾]│
│    (Nhấn tab/mũi tên: sổ ra dropdown các loại tài liệu con tương ứng)   │
│  - Hàng 2 (Cấp 2): Loại tài liệu: [🏷️ Chọn loại ▾] [Tất cả] [HĐLĐ]... │
│    (Nhấn nút: sổ ra dropdown danh sách loại tài liệu tương ứng)        │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│  THANH BỘ LỌC TÌM KIẾM (Search + Năm + Hiệu lực)                       │
│  [🔍 Tìm theo tiêu đề, ký hiệu, nơi ban hành...]    [Năm▼]  [Hiệu lực▼] │
│  * Hiển thị active filter tags + nút [Xóa tất cả bộ lọc]               │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Kết hợp AND tất cả tiêu chí
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│  THANH KẾT QUẢ & THAO TÁC                                              │
│  "Hiển thị 1–10 trên tổng số 7 tài liệu"                 [Xuất Excel]  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│  BẢNG DỮ LIỆU CẤP 3 (ResourceTable)                                    │
│  - Cột: STT | Ký hiệu | Tiêu đề + Loại | Nơi BH | Ngày đăng | HL | File │ Thao tác
│  - Tương tác:                                                          │
│    + Click vào dòng: Drill-down điều hướng về đúng Tab Cấp 1 & Chip Cấp 2│
│    + Dòng hết hiệu lực (HET_HIEU_LUC, HET_VA_THAY_THE): Tự động làm mờ│
│    + Nút ⋯ Thao tác (Fixed Dropdown Menu):                             │
│        👁 Xem chi tiết → Mở popup ResourceDetailModal                   │
│        📂 Vào Thư mục  → Drill-down trực tiếp                          │
│        ✏ Chỉnh sửa    → Mở popup ResourceFormModal (chế độ Edit)      │
│        🗑 Xóa tài liệu → Xác nhận và xóa                               │
└────────────────────────────────────────────────────────────────────────┘
```

### 2.2. Luồng hoạt động của các Modal / Popup

#### A. Xem chi tiết tài liệu (`ResourceDetailModal`)
- **Điểm mở:** Từ menu thao tác `⋯` ➔ chọn **"Xem chi tiết"**.
- **Nội dung:** Ký hiệu, Tiêu đề, Thư mục (Cấp 1), Loại tài liệu (Cấp 2), Nơi ban hành, Ngày đăng, Trạng thái hiệu lực kèm huy hiệu màu, Link văn bản thay thế (nếu có), Phạm vi tiếp cận (Tất cả / Nội bộ), Đơn vị sở hữu, Người tạo.
- **Tệp đính kèm:** Danh sách file có kèm dung lượng và nút tải về từng file.
- **Thao tác nhanh:** Có nút chuyển sang **Chỉnh sửa** hoặc **Xóa** ngay trong modal.

#### B. Thêm mới / Cập nhật tài liệu (`ResourceFormModal`)
- **Điểm mở:** Nút **[+ Thêm mới tài liệu]** hoặc menu `⋯` ➔ **"Chỉnh sửa"**.
- **Cascading Dropdowns:** 
  - Chọn Thư mục (Cấp 1) ➔ Dropdown Loại tài liệu (Cấp 2) tự động lọc theo danh mục vừa chọn.
- **Validation quy chuẩn:**
  - Tiêu đề, Thư mục, Loại tài liệu, Trạng thái hiệu lực: Bắt buộc.
  - Khi chọn `HET_VA_THAY_THE`: Bắt buộc nhập `link_thay_the`.
  - Tải lên tệp đính kèm: Kiểm tra định dạng (.pdf, .doc, .docx, .jpg, .png, .zip, .rar) và dung lượng tối đa 20MB.

#### C. Quản lý Danh mục & Cấp 2 (`CategoryManagementModal`)
- **Điểm mở:** Nút **[Quản lý Danh mục & Cấp 2]** trên tiêu đề trang.
- **Cấu trúc 2 panel liên kết:**
  - **Panel trái (Cấp 1):** Danh sách Thư mục với STT ưu tiên, ký hiệu, tên. Hỗ trợ Thêm/Sửa/Xóa.
  - **Panel phải (Cấp 2):** Khi click chọn 1 Thư mục bên trái, panel bên phải hiển thị danh sách Loại tài liệu thuộc thư mục đó, cho phép Thêm/Sửa/Xóa và cấu hình `is_public`.

---

## 3. LOGIC LỌC PHÂN TẦNG VÀ HIỂN THỊ (FILTER & CASCADE LOGIC)

1. **Điều kiện lọc đồng thời (Compound AND Query):**
   ```ts
   filteredDocuments = documents.filter(doc => {
     const matchCategory = selectedCategory === 'all' || doc.dm_tai_lieu === selectedCategory;
     const matchType = selectedType === 'all' || doc.loai_tai_lieu.includes(selectedType);
     const matchYear = selectedYear === 'all' || doc.ngay_dang.startsWith(selectedYear);
     const matchStatus = statusFilter === 'all' || doc.hieu_luc === statusFilter;
     const matchSearch = !searchTerm || (
       doc.tieu_de.toLowerCase().includes(searchTerm.toLowerCase()) ||
       doc.ky_hieu.toLowerCase().includes(searchTerm.toLowerCase()) ||
       doc.noi_ban_hanh.toLowerCase().includes(searchTerm.toLowerCase())
     );
     return matchCategory && matchType && matchYear && matchStatus && matchSearch;
   });
   ```
2. **Cascading State:**
   - Đổi Tab Cấp 1 ➔ Chip Cấp 2 tự động đặt lại về `"all"` và trang phân trang về `1`.
   - Chọn Chip Cấp 2 ➔ Dropdown "Loại tài liệu" trong thanh tìm kiếm tự động đồng bộ giá trị.
3. **Hiển thị trực quan trạng thái hiệu lực:**
   - `CON_HIEU_LUC`: Xanh lá (Green badge)
   - `CON_HIEU_LUC_1_PHAN`: Cam/Vàng (Amber badge)
   - `HET_HIEU_LUC` & `HET_VA_THAY_THE`: Đỏ/Xám (Red/Slate badge) + Làm mờ cả dòng bảng dữ liệu (`opacity-65`, text mờ) để người dùng tập trung vào tài liệu còn hiệu lực.

---

## 4. PHÂN CÔNG NHIỆM VỤ THÀNH VIÊN (TEAM ASSIGNMENTS)

| Thành viên | Vai trò | Nhiệm vụ chính | Tài liệu hướng dẫn |
|---|---|---|---|
| **Thượng Mạnh Quỳnh** | Trưởng nhóm | • Kiến trúc luồng 3 tầng & Cascading Filter Cấp 1 ➔ Cấp 2<br>• Trang `/resources` trung tâm<br>• Quản lý nhánh `4_documents_templates`, Review/Merge PR<br>• Kiểm thử tổng thể & đồng bộ staging | [`01_huong_dan_thuong_manh_quynh.md`](./01_huong_dan_thuong_manh_quynh.md) |
| **Huỳnh Thị Kim Trang** | Thành viên | • Backend & Frontend CRUD Danh mục Cấp 1 (`records_tailieu`)<br>• Backend & Frontend CRUD Loại Cấp 2 (`records_loaitailieu`)<br>• Modal quản lý danh mục 2 panel (`CategoryManagementModal`) | [`02_huong_dan_huynh_thi_kim_trang.md`](./02_huong_dan_huynh_thi_kim_trang.md) |
| **Nguyễn Chí Tín** | Thành viên | • Backend API Chi tiết tài liệu Cấp 3 (`records_chitiettailieu`)<br>• Upload file & validator (<20MB, đuôi hợp lệ)<br>• Bộ lọc đa tiêu chí backend, endpoint `toggle-validity`<br>• Xuất file Excel theo kết quả lọc | [`03_huong_dan_nguyen_chi_tin.md`](./03_huong_dan_nguyen_chi_tin.md) |
| **Đỗ Trung Phong** | Thành viên | • Frontend Bảng dữ liệu Cấp 3 (`ResourceTable`)<br>• Popup xem chi tiết (`ResourceDetailModal`)<br>• Popup form thêm/sửa (`ResourceFormModal`)<br>• Hiệu ứng mờ dòng hết hiệu lực, menu thao tác floating | [`04_huong_dan_do_trung_phong.md`](./04_huong_dan_do_trung_phong.md) |

---

## 5. KẾ HOẠCH TRIỂN KHAI THEO PHASE (ROADMAP & PHASES)

### Phase 1: Chuẩn hóa Cơ sở dữ liệu & Model Backend (ĐÃ XONG)
- [x] Tạo 4 model Django: `DanhMucTaiLieu`, `LoaiTaiLieu`, `TaiLieuChiTiet`, `ChiTietTaiLieuAttachment`
- [x] Mapping chính xác với schema DDL `ddl_base_v0`: `records_tailieu`, `records_loaitailieu`, `records_chitiettailieu`, `records_chitiettailieu_loaitailieu`, `records_chitiettailieu_attachment`
- [x] Tạo migration `0001_initial.py` chạy sạch trên SQLite và PostgreSQL

### Phase 2: RESTful APIs & Backend Business Logic (ĐÃ XONG)
- [x] Serializers và ViewSets đầy đủ CRUD cho 4 tầng dữ liệu
- [x] Endpoint bổ trợ: Lọc theo năm, lọc theo hiệu lực, tìm kiếm từ khóa
- [x] Endpoint xuất Excel danh sách tài liệu (`/documents/export-excel/`)
- [x] Endpoint chuyển trạng thái nhanh (`/documents/{id}/toggle-validity/`)
- [x] Validator file đính kèm: chặn file vượt 20MB và sai phần mở rộng
- [x] Bộ lọc quyền nội bộ theo `don_vi_id` (`TAT_CA` vs `NOI_BO_PHONG_BAN`)
- [x] Router đăng ký API dưới tiền tố `/api/resources/` (đã gỡ alias `/api/document-templates/` theo chốt tại issue #93)

### Phase 3: Thiết kế lại Giao diện & Tối ưu Trải nghiệm Frontend (ĐÃ XONG)
- [x] Xây dựng UI phân cấp 3 tầng trực quan: Tab Cấp 1 có cuộn ◄ ►, Chip Cấp 2, Bảng Cấp 3
- [x] Bộ lọc kết hợp AND (Search + Type + Year + Validity) kèm Tag hiển thị và xóa nhanh
- [x] Cải tiến Bảng: Drill-down khi click dòng; Menu `⋯` fixed position không bị che khuất
- [x] Highlight làm mờ tài liệu hết hiệu lực; hiển thị link thay thế khi `HET_VA_THAY_THE`
- [x] 3 Modal tương tác: Chi tiết, Thêm/Sửa, Quản lý Cấp 1 & Cấp 2
- [x] Cập nhật đa ngôn ngữ Việt - Anh (i18n `vi.json`, `en.json`)
- [x] Bộ unit/integration test Frontend 45/45 passed 100%

### Phase 4: Tích hợp API thật & Phân quyền RBAC (ĐANG TIẾN HÀNH)
- [ ] Chuyển đổi `resourceService.ts` từ dữ liệu mẫu (mock) sang gọi API backend Django thật
- [ ] Hỗ trợ upload nhiều file đính kèm cùng lúc trong `ResourceFormModal`
- [ ] Tích hợp RBAC từ Nhóm 7 (phân quyền xem/thêm/sửa/xóa theo vai trò cán bộ)
- [ ] Preview nhanh file PDF/ảnh trực tiếp trong popup chi tiết
- [ ] Toast notification thống nhất sau mỗi thao tác thêm/sửa/xóa thành công
- [ ] Đóng gói và kiểm thử e2e chuẩn bị merge `staging` trước **2026-10-12**

---

## 6. DANH MỤC CONFLICT & ĐIỂM LỆCH THỰC TẾ

| Mã | Hạng mục | Nhóm liên quan | Thực tế hiện tại & Lý do lệch | Giải pháp | Mức độ |
|---|---|---|---|---|---|
| **G4-1** | `don_vi_id` Model | Nhóm 7 (RBAC) | `don_vi_id` trong `TaiLieuChiTiet` đang dùng `BigIntegerField` do `DonVi` chưa có trên nhánh `staging`. | Giữ nguyên BigInt cho MVP, phối hợp Nhóm 7 chuyển FK sau khi merge RBAC. | P1 (Chờ) |
| **G4-2** | Phân quyền API | Nhóm 7 (RBAC) | Đang dùng `IsAuthenticatedOrReadOnly` cho toàn bộ ViewSet vì thiếu permission class chuẩn của hệ thống. | Nhóm 7 cung cấp class RBAC, Nhóm 4 gắn vào ViewSet. | P1 (Chờ) |
| **G4-3** | Quyền tài liệu nội bộ | Nhóm 6 (Auth) | Query nội bộ phòng ban đang dựa vào `user.profile.department` và `user.don_vi_id`. | Nhóm 6 xác nhận schema profile; Nhóm 4 hiệu chỉnh query tương ứng. | P1 (Chờ) |
| **G4-4** | URL Basename | Nội bộ Nhóm 4 | Đang có 3 alias URL cho `TaiLieuChiTietViewSet` trong `urls.py`. | Rà soát và gộp về 1 endpoint chính `/chi-tiet-tai-lieu/`. | Không chặn |
