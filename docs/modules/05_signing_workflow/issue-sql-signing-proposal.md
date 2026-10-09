**Tiêu đề:** `[Nhóm 5] Đề xuất bổ sung và điều chỉnh DDL phân hệ Trình ký (signing_*) trong csdl_qlvbtl_schema_final.sql`

Nhóm 5 đề xuất bổ sung và điều chỉnh DDL phân hệ Trình ký (mục 9, dòng 925–1322 của `csdl_qlvbtl_schema_final.sql`), căn cứ trên các vấn đề phát hiện khi rà soát dưới đây. Mỗi vấn đề kèm phương án đề xuất.

Rà soát là đối chiếu tĩnh, chưa chạy DDL trên PostgreSQL. Cấu trúc 14 bảng và các cột hiện đủ dùng, các vấn đề nằm ở ràng buộc, trigger, khóa ngoại và seed quyền.

## P0 — Bảo toàn bằng chứng ký và xác định văn bản

1. **Bổ sung `document_type` cho `signing_request`** (dòng 1012). Hiện chỉ có `van_ban_id`, không xác định được văn bản thuộc bảng đến, đi hay mật. Đề xuất thêm `document_type document_kind NOT NULL` (như `task_congviec` và `documents_view_log`) và index `(document_type, van_ban_id)`.
2. **Điều chỉnh trigger `prevent_delete_final_manifest`** (dòng 1219). Điều kiện đang kiểm `IN ('CHOT','FINAL')`, nhóm 5 dùng trạng thái `NHAP` / `DA_CHOT`. Đề xuất kiểm `trang_thai = 'DA_CHOT'`, nếu không thì manifest đã chốt vẫn xóa được.
3. **Bổ sung trigger chặn UPDATE** cho các bảng bằng chứng: `signing_signature` (chỉ cho phép đổi `trang_thai_xac_minh`, `thoi_diem_xac_minh`), `signing_manifest` khi `DA_CHOT`, `signing_audit_log` (chặn cả UPDATE và DELETE). Hiện chỉ có trigger chặn DELETE.
4. **Đổi 3 FK của `signing_audit_log` sang `ON DELETE RESTRICT`** (dòng 1279–1281, đang `SET NULL`). `SET NULL` là một UPDATE ngầm lên bảng nhật ký, xung đột với điểm 3.

## P1 — Đồng bộ với nghiệp vụ nhóm 5

5. **Bổ sung 5 quyền còn thiếu cho phân hệ Trình ký** (dòng 2121–2134 mới có `view_trinhky`, `add_trinhky`, `sign_trinhky`): quản lý quy trình ký, gửi trình ký, ủy quyền ký, hủy trình ký, xem nhật ký trình ký. Đề nghị Ban chuyên môn thống nhất quy ước tên quyền và ánh xạ 5 nhóm quyền chuẩn. Đồng thời cập nhật lại số lượng quyền (tiêu đề file ghi 68, ghi chú seed ghi 66).
6. **`signing_change_thread` và `signing_change_message`: đổi `ON DELETE CASCADE` sang `RESTRICT`** (dòng 1251, 1267). Nội dung yêu cầu chỉnh sửa và trao đổi là dữ liệu lịch sử, không xóa dây chuyền.
7. **`signing_process_step_signer`: đổi `nguoi_ky_id`, `chuc_vu_id` từ `SET NULL` sang `RESTRICT`** (dòng 994–995). Khi xóa người dùng hoặc chức vụ, cả hai cột cùng NULL và vi phạm CHECK "một trong hai", nên thao tác xóa báo lỗi khó hiểu.
8. **`signing_audit_log.dia_chi_ip`: cho phép NULL, bỏ mặc định `'127.0.0.1'`** (dòng 1290). Mặc định hiện tại ghi sai địa chỉ khi hệ thống không lấy được IP.
9. **Cho phép NULL ở các cột chưa có giá trị tại thời điểm tạo bản nháp:**
   - `signing_request.phien_ban_van_ban`, `vi_tri_luu_tep`, `ma_bam_tai_lieu` (dòng 1013–1015);
   - `signing_attempt.phien_ban_van_ban` (dòng 1046);
   - `signing_request_step_signer.ten_chuc_vu` (dòng 1099), `khoa_chong_trung_thao_tac` (dòng 1116);
   - `signing_manifest.vi_tri_luu` (dòng 1204).

   Giữ `NOT NULL` cho `signing_attempt.vi_tri_luu_tep` và `ma_bam_tai_lieu`.

## P2 — Nhóm 5 xử lý ở model/service, không yêu cầu đổi DDL

10. Các ràng buộc chéo bảng (`luot_truoc` cùng `trinh_ky`; `chu_ky_hien_hanh` thuộc đúng người ký; `hash_tai_lieu` bằng `ma_bam_tai_lieu` của lượt trình): kiểm tra ở tầng service kèm test. Nếu Ban chuyên môn muốn ép ở DB, nhóm 5 sẽ bổ sung trigger.
11. Các cột trạng thái, phạm vi, mức độ, kiểu ký dạng `VARCHAR(20)`: nhóm 5 khai báo `choices` ở model. Có thể bổ sung CHECK ở DDL nếu thống nhất áp dụng chung cho toàn bộ hệ thống.
12. Bổ sung index `signing_request (han_chot)` và `signing_request_step (han_xu_ly)` phục vụ tác vụ nhắc hạn.

## Đề nghị

- Ban chuyên môn xem xét các điểm P0 và P1, xác nhận phương án cho điểm 5 (quy ước tên quyền).
- Nhóm 5 sẵn sàng gửi PR sửa mục 9 của file SQL và phần seed quyền sau khi được thống nhất.
- Nghiệm thu: DDL chạy sạch trên PostgreSQL trống; test xác nhận manifest `DA_CHOT`, chữ ký và nhật ký không sửa/xóa được; lưu bản nháp chưa có tệp thành công.
