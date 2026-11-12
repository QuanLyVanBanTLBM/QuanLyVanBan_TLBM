# MODULE 4: QUẢN LÝ TÀI LIỆU VÀ BIỂU MẪU (BM)

**Đơn vị phụ trách:** Nhóm 4  
**Độ khó nghiệp vụ:** 0.8  
**Kho lưu trữ nhánh tích hợp:** `4_documents_templates`  
**Kế hoạch & Luồng chi tiết:** [Plan & Flow (plan_and_flow.md)](./plan_and_flow.md)

---

## 👥 PHÂN CÔNG NHIỆM VỤ THÀNH VIÊN

Tài liệu hướng dẫn chi tiết từng bước cho từng thành viên:

1. [01. Hướng dẫn Thượng Mạnh Quỳnh (Nhóm Trưởng)](./01_huong_dan_thuong_manh_quynh.md) — Điều hướng 3 tầng, Bộ lọc phân tầng (Cấp 1 ➔ Cấp 2), Review/Merge PR, Quản lý nhóm.
2. [02. Hướng dẫn Huỳnh Thị Kim Trang](./02_huong_dan_huynh_thi_kim_trang.md) — Backend & Frontend CRUD Danh mục Cấp 1 (`records_tailieu`) và Loại Cấp 2 (`records_loaitailieu`).
3. [03. Hướng dẫn Nguyễn Chí Tín](./03_huong_dan_nguyen_chi_tin.md) — Backend APIs Danh sách tài liệu chung (`records_chitiettailieu`), Upload file, Xuất Excel, Bộ lọc.
4. [04. Hướng dẫn Đỗ Trung Phong](./04_huong_dan_do_trung_phong.md) — Frontend Danh sách tài liệu chung (`ResourceTable`, `ResourceDetailModal`, `ResourceFormModal`, Highlight dòng hết hiệu lực).

---

## 🗄️ CẤU TRÚC BẢNG CƠ SỞ DỮ LIỆU LIÊN QUAN

- `records_tailieu`: Danh mục Cấp 1 (STT ưu tiên, Ký hiệu, Tên, Người lập, Ngày lập, Ghi chú)
- `records_loaitailieu`: Loại Cấp 2 (FK `dm_tai_lieu`, Tên loại, `is_public`, Ngày lập, Ghi chú)
- `records_chitiettailieu`: Chi tiết tài liệu (FK Cấp 1, M2M Cấp 2, Tiêu đề, File đính kèm, Hiệu lực, Nơi ban hành, Hiển thị)
- `records_chitiettailieu_loaitailieu`: Bảng trung gian M2M giữa Chi tiết tài liệu và Loại tài liệu.
