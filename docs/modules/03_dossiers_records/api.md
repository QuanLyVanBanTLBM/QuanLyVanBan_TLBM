# API Hồ sơ và Loại văn bản

Cập nhật ngày 24/10/2026. Staging đối chiếu: `213758251fa407874e555d5ab575f60c629a2966`. Tài khoản dùng `accounts.Employee`, backend quyền `authorization.backends.RbacBackend`.

Tài liệu mô tả API Records và contract popup #223/#224 đã tích hợp vào source staging. Trạng thái deploy được xác minh riêng qua pipeline; phụ thuộc #229/#230 chưa được coi là đã hoàn tất.

## Endpoint và quyền

Base `/api/records/`. Yêu cầu JWT thật và quyền nghiệp vụ; không có quyền riêng `*_loaivanban`.

- `GET dossiers/`: danh sách Hồ sơ, quyền `view_hoso`.
- `POST dossiers/`: tạo Hồ sơ, quyền `add_hoso`; người lập lấy từ phiên đăng nhập.
- `GET dossiers/{id}/`: chi tiết Hồ sơ, quyền `view_hoso`.
- `PATCH dossiers/{id}/`: sửa Hồ sơ, quyền `change_hoso`.
- `DELETE dossiers/{id}/`: xóa Hồ sơ, quyền `delete_hoso`.
- `GET document-types/`: danh mục loại độc lập, quyền `view_hoso`; không POST ở endpoint này.
- `GET dossiers/{id}/document-types/`: loại thuộc hồ sơ, quyền `view_hoso`.
- `POST dossiers/{id}/document-types/`: tạo loại trong hồ sơ cha, quyền `add_hoso`.
- `GET document-types/{id}/`: chi tiết loại, quyền `view_hoso`.
- `PATCH document-types/{id}/`: sửa loại, quyền `change_hoso`.
- `DELETE document-types/{id}/`: xóa loại, quyền `delete_hoso`.

Danh sách trả `{count,next,previous,results}`; mặc định 10 bản ghi/trang, `page_size` tối đa 100. Bộ lọc: `search`, `year`, `page`, `page_size`; danh mục loại độc lập thêm `ho_so` là số nguyên dương. Hồ sơ tìm theo ký hiệu, tên, ghi chú; loại tìm theo tên, ghi chú. Frontend tìm kiếm tức thời đã tích hợp qua #185 và giữ tải lại sau CRUD.

Hồ sơ có ID, thứ tự ưu tiên, ký hiệu, tên, người lập, ngày lập, ghi chú, cờ hệ thống và thời điểm hệ thống. ID, người lập, cờ hệ thống và thời điểm hệ thống là chỉ đọc. Loại văn bản có ID, `ho_so`, `ten_ho_so`, `ten_loai`, ngày lập, ghi chú và thời điểm hệ thống; hồ sơ cha chỉ đọc, lấy từ URL khi tạo.

## Validation và lỗi

- Chưa đăng nhập 401; thiếu quyền nghiệp vụ 403; đối tượng không tồn tại 404.
- Input không hợp lệ, rỗng sau trim hoặc trùng dữ liệu: 400. Năm hợp lệ từ 1 đến 9999.
- Tạo thành công 201; xóa thành công 204.
- Xóa Hồ sơ chung/hồ sơ hệ thống hoặc đối tượng còn tham chiếu: 409.
- Mã/tên hồ sơ và tên loại được trim. Tên loại không trùng sau trim và so chữ thường trong cùng hồ sơ.
- Không hạ cờ `is_he_thong`, không xóa Hồ sơ chung. Field chỉ đọc ở API không thay thế guard model/trigger CSDL.
- API ghi lỗi không được hiển thị thành thông báo thành công.

## Route Records và bàn giao popup

Route hiện có: `/records`, `/records/document-types`, `/records/{dossierId}/document-types`. Route danh sách văn bản riêng cũ chuyển về danh mục loại; API `/api/records/dossiers/{id}/documents/` đã gỡ. Không khôi phục trang hoặc API metadata Văn bản riêng.

#223/#224 bổ sung ngữ cảnh cấp 1/cấp 2 trong popup. PR #224 đã merge vào staging ngày 24/10/2026 tại `213758251fa407874e555d5ab575f60c629a2966`, từ head `3a9fe048d512988a65f4dab4670017ffad236dec`. Contract phần Records đã tích hợp; phần tiếp nhận/lọc Văn bản và nghiệm thu toàn luồng còn theo dõi tại #229/#230:

- Cấp 2: `/records/{dossierId}/document-types?ten_ho_so={encodedName}`.
- Đến: `/documents/incoming?ho_so={dossierId}&ten_ho_so={encodedName}&loai_van_ban={typeId}&pham_vi=NOI_BO`.
- Đi: cùng query trên đường dẫn `/documents/outgoing`.
- Hạn chế: `pham_vi=HAN_CHE`, giữ hướng đến/đi; không tạo hướng/bảng mật riêng.
- Dùng `URLSearchParams` mã hóa tên. Tên chỉ là ngữ cảnh hiển thị, không dùng thay ID hoặc làm căn cứ phân quyền.
- Popup xác minh loại rồi hồ sơ cha qua API Records. Loại đã xóa/đổi cha, sai ID/tên, API lỗi hoặc phản hồi đến muộn sau đóng phải chặn điều hướng chưa xác minh.
- Liên kết có href thật; hỗ trợ Escape, Tab/Shift+Tab và trả focus về điều khiển mở.

Chi tiết Nhóm 2 dùng ID một văn bản đã chọn:

- UI: `/documents/incoming?detail={documentId}` hoặc `/documents/outgoing?detail={documentId}`.
- API theo hướng: `GET /api/documents/den/{documentId}/`, `GET /api/documents/di/{documentId}/`.
- API chung: `GET /api/documents/{documentId}/`; khi biết hướng, giữ hướng theo helper/API của module Văn bản.

ID hồ sơ, ID loại và ID văn bản khác nhau. Chọn loại chưa xác định một văn bản duy nhất; không thay ID loại/hồ sơ vào `detail`.

Phạm vi tạo mới chốt ngày 23/10: dùng chức năng Nhóm 2, không bổ sung tự điền form trong #223/#224. Popup chọn danh sách không tự gửi `action=create` hoặc tạo bản ghi. Records không truy vấn trực tiếp bảng nối Văn bản.

[Contract đầy đủ của #224 tại commit đã kiểm chứng](https://github.com/QuanLyVanBanTLBM/QuanLyVanBan_TLBM/blob/a5b45064a31ada9c7c1288fe7cdf5c8e43e80bd0/docs/module/team_3/POPUP_DOCUMENT_HANDOFF.md).

## Phụ thuộc chủ module Văn bản

Nhóm 2 sở hữu danh sách/chi tiết/tạo Văn bản, bảng nối, bộ lọc và selector phân quyền. Records không viết lại ACL hoặc dùng SQL để vượt lớp này.

#229/#230 còn cần gửi `ho_so` từ request danh sách đầu trên cả hai hướng; giữ `ten_ho_so` khi hồ sơ không đổi; lọc ID loại bằng FK chính xác, không OR với nội dung/số hiệu; kiểm quyền trước count/phân trang. Chủ module đồng bộ staging, giải conflict và bàn giao head/CI cuối.

Nghiệm thu ngày 23/10 trên #224 bằng PostgreSQL 16 riêng: 25/25 API Records, 8/8 tổ hợp URL popup đạt; toàn bộ HTTP 34/36 đạt, hai ca lọc loại Văn bản chưa đạt. URL đúng không xác nhận dữ liệu đã lọc đúng toàn luồng. Xem [trạng thái bàn giao](../../module/team_3/STATUS_AND_HANDOFF.md).

## Schema và môi trường

Nguồn schema duy nhất: [release_DDL.sql](../../common/database/release_DDL.sql). Dựng DB bằng `scripts/build_db.py`, chỉ PostgreSQL 16 ICU `vi-VN`; không dùng SQLite hoặc dựng schema tay.

Records hiện có `0001_initial`, `0002_hoso_guards`, `0003_reference_data_ddl`; không phục hồi chain migration #161 đã được thay thế. Model có index người lập, tên/ngày Hồ sơ, hồ sơ cha, tên/ngày Loại văn bản; không chỉ còn hai index như snapshot cũ.

Không tự fake migration trên DB đang có. Dùng công cụ dựng/adopt/sync theo [runbook](../../common/database/build_db_runbook.md); không reset để vượt gate. Đổi schema đi cùng DDL, migration mới, changelog/max migration theo AGENTS.md.

[Hướng dẫn làm việc Nhóm 3](GROUP3_DEVELOPMENT_GUIDE.md).
