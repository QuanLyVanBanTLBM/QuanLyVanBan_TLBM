# Quy ước quản lý dự án

Áp dụng cho cả 8 nhóm, có hiệu lực từ 06/10/2026. Mục tiêu: một nguồn sự thật cho tiến độ và schema, và chỉ merge vào nhánh chung khi đã kiểm soát được.

## 1. Ba quy ước bắt buộc

### 1.1. Nhóm sở hữu module tự merge vào `staging` khi đủ điều kiện

- Người merge: thành viên nhóm sở hữu module của PR (thường là trưởng nhóm). Không cần chờ người phụ trách DevOps.
- Điều kiện merge:
  - toàn bộ CI xanh trên commit cuối;
  - không còn xung đột với `staging`;
  - PR gắn issue (mục 1.3).
- Merge bằng nút Merge trên PR, không push thẳng vào `staging`. Mỗi thay đổi trên `staging` truy được về PR, issue và người merge.
- Merge kích hoạt deploy staging tự động; người merge theo dõi job deploy và báo lỗi qua issue nếu job thất bại.

### 1.2. Sửa CSDL: DDL, migration và changelog trong cùng một PR

- Nguồn sự thật của schema: `docs/common/database/release_DDL.sql` trên `staging`.
- Một PR đổi schema gồm đủ ba phần: sửa `release_DDL.sql`, migration mới sinh ra đúng thay đổi đó, một mục trong `docs/common/database/DDL_CHANGELOG.md`. Bước so schema của CI là cổng chặn.
- Migration đã có trên `staging` không được sửa: DB staging đã chạy migration đó. Cần đổi tiếp thì thêm migration mới.
- Chi tiết: `AGENTS.md` mục 5.

### 1.3. Mỗi vấn đề một issue, mỗi nhánh một issue, mỗi PR gắn issue của nhánh

- Mở issue trước khi code; issue có label nhóm (`nhom-1` … `nhom-8`) và milestone.
- Nhánh tạo từ `staging` mới nhất, tên `<loại>/<số-issue>-<mô-tả-ngắn>` (ví dụ `fix/164-tim-kiem-ho-so`); một nhánh chỉ phục vụ một issue.
- Mô tả PR có dòng `Closes #<số>` hoặc `Refs #<số>`. PR không gắn issue thì không merge.
- Nhánh kết thúc khi merge vào `staging`, người merge xoá nhánh; việc tiếp theo mở issue và nhánh mới. Không dùng nhánh nhóm dài hạn.
- Chi tiết: `AGENTS.md` mục 8.

## 2. Label và milestone

| Label | Ý nghĩa |
|---|---|
| `nhom-1` … `nhom-8` | Nhóm phụ trách |
| `P0` | Chặn nhóm khác hoặc chặn base staging; xử lý trước |
| `P1` | Cần cho MVP |
| `blocked` | Đang chờ việc khác; mô tả issue ghi rõ chờ issue/PR nào |
| `ddl` | Có thay đổi CSDL, áp dụng mục 1.2 |

| Milestone | Phạm vi |
|---|---|
| `Base staging` | Nền chung: DDL vào staging, `Employee`/RBAC, quy trình dựng DB, CI PostgreSQL, gỡ văn bản mật |
| `MVP` | Chức năng MVP của từng nhóm |

## 3. Bảng GitHub Project

Một bảng Project chung cho tổ chức, gom issue và PR của repo:

- Trường: `Status` (Todo / Doing / Review / Done), `Nhóm`, `Ưu tiên` (P0 / P1), `Milestone`.
- View:
  - **Theo trạng thái**: dạng board, nhóm theo `Status`;
  - **Theo nhóm**: dạng bảng, nhóm theo `Nhóm`;
  - **Đang chặn**: lọc `label:P0` hoặc `label:blocked`.
- Trưởng nhóm cập nhật `Status` khi bắt đầu, khi mở PR và khi merge.

## 4. Bảo vệ nhánh

Repo đang ở chế độ public nên dùng được bảo vệ nhánh trên gói GitHub Free. Áp dụng cho `staging` và `main`:

- bắt buộc merge qua PR;
- bắt buộc CI xanh;
- chặn force-push và xóa nhánh.

Trước khi có bảo vệ nhánh, mục 1.1 là quy ước thủ công.
