# Popup chuyển từ hồ sơ sang danh sách văn bản

Refs #223.

## Phạm vi

Luồng nhóm 3: Hồ sơ (cấp 1) → Loại văn bản thuộc hồ sơ (cấp 2) → popup chọn văn bản đến/đi và phạm vi → trang danh sách văn bản của nhóm 2.

“Cache cấp 1/cấp 2” được thực hiện bằng việc giữ ngữ cảnh lựa chọn trong route và popup. Không thêm hệ thống cache hoặc nguồn dữ liệu thay API.

## Hợp đồng URL

- Cấp 2: `/records/:hoSoId/document-types?ten_ho_so=<tên đã mã hóa>`.
- Văn bản đến: `/documents/incoming?ho_so=<ID hồ sơ>&ten_ho_so=<tên đã mã hóa>&loai_van_ban=<ID loại>&pham_vi=NOI_BO`.
- Văn bản đi: cùng query trên với đường dẫn `/documents/outgoing`.
- Chọn hạn chế: `pham_vi=HAN_CHE`, giữ nguyên hướng đến/đi. Không có route hoặc bảng văn bản mật riêng.
- `URLSearchParams` mã hóa tên tiếng Việt và các ký tự dành riêng. Tên chỉ cung cấp ngữ cảnh hiển thị; ID mới xác định bản ghi.

## Xác minh ngữ cảnh

- Reload trang cấp 2 gọi API hồ sơ theo ID route; tên trong query được thay bằng tên API trả về. Không dùng query/state làm nguồn tên đáng tin cậy.
- Popup gọi `GET /api/records/document-types/:id/` để xác nhận loại còn tồn tại, đúng ID và vẫn thuộc hồ sơ đã chọn; tên loại hiển thị theo phản hồi mới nhất. Nếu loại đã bị xóa, đổi hồ sơ cha hoặc phản hồi không hợp lệ thì không tạo liên kết.
- Sau khi loại được xác nhận, popup gọi lại API hồ sơ cha. ID cha phải khớp ID route khi mở trong hồ sơ và ID hồ sơ API trả về.
- Khi đóng popup trong lúc xác minh loại, không tiếp tục yêu cầu đọc hồ sơ cha hoặc điều hướng bằng phản hồi đến muộn.
- Khi chưa xác minh được, API lỗi, tên rỗng hoặc quan hệ không khớp: không tạo liên kết điều hướng. Thao tác hủy vẫn hoạt động.
- Liên kết “Xem văn bản” có `href` thật; giữ chức năng mở liên kết của trình duyệt.
- Escape đóng popup; Tab/Shift+Tab được giữ trong popup; khi đóng trả focus về nút mở, kể cả React StrictMode.

## Phân biệt danh sách và chi tiết văn bản

- `ho_so` là ID hồ sơ; `loai_van_ban` là ID loại; `detail` là ID một văn bản cụ thể.
- Popup này chọn danh sách theo loại, hướng và phạm vi. Một loại có thể có nhiều văn bản hoặc chưa có văn bản, nên không truyền ID loại hoặc hồ sơ vào `detail`.
- Sau khi chọn một văn bản tại module Văn bản, contract chi tiết là `/documents/incoming?detail=<documentId>` hoặc `/documents/outgoing?detail=<documentId>`. Staging có helper dùng chung `resolveDocumentDetailUrl` và popup chi tiết thuộc module Văn bản.
- Contract API theo phân hệ: `GET /api/documents/den/:id/` và `GET /api/documents/di/:id/`. API chung là `GET /api/documents/:id/`; khi biết hướng phải giữ hướng để tránh sự mơ hồ giữa ID ở hai bảng.
- Không đọc trực tiếp bảng nối Văn bản từ Records. Không khôi phục API metadata hoặc trang danh sách văn bản riêng đã bị gỡ.
- Thao tác tạo văn bản và giá trị mặc định của form thuộc module Văn bản, không nằm trong popup chọn danh sách của #223.

## Phụ thuộc module Văn bản (nhóm 2)

Đối chiếu nền staging tại thời điểm triển khai cho thấy cả `InboundDocumentPage.tsx` và `OutboundDocumentPage.tsx` đọc `ho_so` từ URL nhưng hàm `fetchDocuments` chưa thêm `ho_so` vào query API. Hàm `syncFiltersToUrl` dựng query mới và chưa giữ `ten_ho_so` khi đổi bộ lọc.

Nhóm sở hữu module Văn bản cần xác nhận/cập nhật hai hành vi này trong Issue/PR riêng theo quy định sở hữu module. PR nhóm 3 không sửa trang nhóm 2 hoặc backend Văn bản. Không coi kiểm thử điều hướng bằng router giả lập là xác nhận danh sách văn bản thật đã lọc đúng xuyên suốt.

Đối chiếu staging `fc87b04` ngày 23/10/2026: hai hành vi trên vẫn cần nghiệm thu qua #229/#230; #230 cần giải conflict với hai trang Văn bản mới. Không ghép thay đổi module Văn bản vào nhánh #223.

## Kiểm tra thủ công sau khi chạy project

1. Đăng nhập bằng tài khoản được phép đọc hồ sơ và văn bản. Mở danh sách Hồ sơ.
2. Chọn hồ sơ: kiểm tra tên trên giao diện và `ten_ho_so` trong URL cấp 2; tải lại trang và xác nhận giữ đúng ngữ cảnh.
3. Chọn một loại: popup hiển thị tên hồ sơ API xác nhận và tên loại.
4. Lần lượt thử đến/đi, bật/tắt hạn chế: kiểm tra `href` chứa ID hồ sơ, tên, ID loại và phạm vi đúng. Thử mở liên kết trong tab mới.
5. Thử Tab/Shift+Tab, Hủy, Escape và kiểm tra focus trở về nút mở.
6. Kiểm tra Network ở trang nhóm 2: lời gọi `/api/documents/` phải nhận đúng các bộ lọc và trả dữ liệu theo phân quyền. Bước này còn phụ thuộc phần tiếp nhận của nhóm 2 nêu trên.
7. Thử hồ sơ không còn tồn tại/không có quyền đọc: popup báo không xác minh được và không cho điều hướng bằng dữ liệu chưa xác nhận.

## Giới hạn

Không thay schema, migration, dữ liệu local, cấu hình chia sẻ hoặc CI/deploy. Không triển khai hay merge staging trong phạm vi công việc này. Kết quả gate và cảnh báo thực tế được ghi trong PR; không đánh dấu gate chưa chạy là đạt.
