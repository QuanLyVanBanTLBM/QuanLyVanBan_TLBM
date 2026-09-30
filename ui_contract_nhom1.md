# Tài liệu bàn giao giao diện (UI Contract) - Cấp 1 & Cấp 2
**Người soạn:** Nguyễn Thị Yến Nhi (Nhóm 3)
**Bàn giao cho:** Nhóm 1 (Frontend)

*Lưu ý: Các tính năng danh sách Cấp 3 và Xuất Excel chưa thuộc bản giao 2 tuần này, được đánh dấu là Backlog.*

## 1. Màn hình Danh sách Hồ sơ (Cấp 1)
*   **Endpoint API:** `GET /api/records/dossiers/`
*   **Quyền yêu cầu:** `view_hoso`
*   **Mapping Cột & Field:**
    *   `id`: Ẩn (dùng làm key).
    *   `code` (Số ký hiệu): Hiển thị dạng Text.
    *   `name` (Tên hồ sơ): Hiển thị dạng Text.
    *   `created_by` (Người lập): Hiển thị Tên người dùng.
    *   `created_at` (Ngày lập): Hiển thị DateTime (giờ, phút, giây). Yêu cầu i18n định dạng theo locale.
    *   `is_system` (Hồ sơ chung): Hiển thị dạng Tag/Badge (Ví dụ: "Hồ sơ hệ thống").
*   **Các trạng thái:**
    *   **Loading:** Hiển thị Skeleton loading table.
    *   **Empty:** Hiển thị ảnh minh họa "Không có hồ sơ nào" và nút "Tạo mới".
    *   **Lỗi 403 (Forbidden):** "Bạn không có quyền xem hồ sơ".
*   **Hành động:** Nút Tạo, Nút Sửa, Nút Xóa (Ẩn nút Xóa nếu `is_system=true`).

## 2. Màn hình Danh sách Loại văn bản (Cấp 2)
*   **Luồng hoạt động:** Có nút quay lại Hồ sơ Cấp 1. Danh sách giới hạn trong 1 `dossier_id`.
*   **Endpoint API:** `GET /api/records/dossiers/{id}/document-types/`
*   **Mapping Cột & Field:**
    *   `name` (Tên loại văn bản): Text.
    *   `created_at` (Ngày lập): DateTime (giờ, phút, giây).
    *   `note` (Ghi chú): Text dài.
*   **Bộ lọc (Filters):**
    *   `search`: Input text (tìm theo tên loại).
    *   `year`: Select box chọn năm.
*   **Các trạng thái:**
    *   **Invalid Year:** Validation báo lỗi đỏ "Năm không hợp lệ" nếu nhập chữ.
    *   **Server Error (500):** Thông báo Toast báo lỗi hệ thống.