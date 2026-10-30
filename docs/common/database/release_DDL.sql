-- =====================================================================
-- THAY ĐỔI CÁN BỘ NHÂN VIÊN (Nhóm 7; issue #24; đánh dấu [CBNV] tại vị trí)
-- Căn cứ: issue #24; accounts 0010_employeeassignment/0011_employeeassignment_fk_cascade_ddl;
--   authorization 0009_add_export_cbnv_permission.
--   1) Thêm accounts_employee_assignment với các cột employee_id, don_vi_id, chuc_vu_id,
--      chuc_danh và ràng buộc UNIQUE (employee_id, don_vi_id, chuc_vu_id).
--   2) Thêm quyền export_cbnv cho các nhóm TP, BGD, ADMIN.
-- Quy mô sau [CBNV] (nạp sạch): 58 bảng vật lý | 20 kiểu ENUM | 78 quyền thao tác | 7 nhóm quyền chuẩn | 208 lượt phân quyền.
-- =====================================================================
-- THAY ĐỔI VĂN BẢN TRÌNH KÝ KHÔNG BẮT BUỘC GẮN VĂN BẢN ĐI (Nhóm 5; issue #274; đánh dấu [VBTK] tại vị trí)
-- Căn cứ: yêu cầu nghiệp vụ trình ký (issue #275 mục 3); migration signing 0015_van_ban_trinh_ky_khac.
--   signing_request.document_type, document_id bỏ NOT NULL; thêm so_hieu_van_ban, trich_yeu_van_ban (nhập tay).
--   CHECK chk_signing_request_van_ban: hồ sơ gắn văn bản đi (hai cột cùng có giá trị) hoặc không gắn (hai cột
--   cùng NULL) và có trích yếu. Tệp PDF trình ký vẫn tải lên riêng như trước.
-- =====================================================================
-- THAY ĐỔI NHÓM QUYỀN BỔ SUNG (Nhóm 7; issue #228; đánh dấu [NQBS] tại vị trí)
-- Căn cứ: bảng nhóm quyền mặc định theo 25 chức vụ (nhóm trưởng chốt 21/10/2026, PR #211).
--   Thêm 2 nhóm chuẩn chỉ chứa quyền cộng thêm, gán cùng nhóm CV:
--   1) TLBGD (Trợ lý Ban Giám đốc): view_all_congviec, view_read_log_vanbanden, view_read_log_vanbandi, send_trinhky.
--   2) KT (Kiểm toán): view_signing_audit, view_read_log_vanbanden, view_read_log_vanbandi.
--   Migration authorization 0008_supplementary_groups_tlbgd_kt bổ sung cho DB dựng bằng migration.
-- Quy mô sau [NQBS] (cộng sau [CVTK]): 7 nhóm quyền chuẩn; thêm 7 lượt phân quyền (198 -> 205).
-- =====================================================================
-- THAY ĐỔI QUYỀN GỬI TRÌNH KÝ CỦA CHUYÊN VIÊN (Nhóm 5; issue #226; đánh dấu [CVTK] tại vị trí)
-- Căn cứ: signing-backend-plan.md mục 8 (nhân viên đã xác thực được tạo yêu cầu; gửi cần send_trinhky + người tạo).
--   Nhóm CV có add_trinhky nhưng thiếu send_trinhky nên hồ sơ do Chuyên viên tạo dừng ở NHAP: người tạo
--   không gửi được, người có send_trinhky cũng không gửi thay vì không phải người tạo. Cấp send_trinhky cho CV;
--   migration authorization 0007_grant_cv_send_trinhky bổ sung cho DB đã seed từ trước.
-- Quy mô sau [CVTK] (nạp sạch): nhóm CV 22 quyền; 198 lượt phân quyền (thêm 1 lượt).
-- =====================================================================
-- THAY ĐỔI BỎ MỨC ĐỘ KHẨN CỦA TRÌNH KÝ (Nhóm 5; issue #238)
-- Căn cứ: spec Nhóm 5 bỏ mức độ khẩn/ưu tiên; migration signing 0014_bo_muc_do.
--   signing_request bỏ cột muc_do (VARCHAR(20) NOT NULL; THUONG | KHAN | HOA_TOC kiểm ở tầng ứng dụng).
--   Bằng chứng đã chốt (signing_manifest.noi_dung_chuan_hoa) xác minh bằng nội dung đã lưu nên manifest
--   phiên bản 1 (có ho_so.muc_do) giữ nguyên; manifest phiên bản 2 trở đi không còn trường này.
-- =====================================================================
-- THAY ĐỔI PHASE 10 LÕI TRÌNH KÝ (Nhóm 5; issue #80; đánh dấu [P10] tại vị trí)
-- Căn cứ: issue #80 mục D; signing-backend-plan.md mục 3.2 "Phẳng hóa"; migration signing 0007_tep_hoan_tat.
--   signing_attempt thêm trang_thai_tep_hoan_tat (NULL khi lượt chưa hoàn thành; DANG_XU_LY | LOI | THANH_CONG)
--   và loi_tep_hoan_tat (mã lỗi lần tạo gần nhất): tệp PDF hoàn tất sinh sau khi lượt hoàn thành, lỗi thì
--   thử lại được, không yêu cầu ký lại. Giá trị trạng thái kiểm ở tầng ứng dụng như các cột trạng thái khác.
-- =====================================================================
-- THAY ĐỔI PHASE 7 TRÌNH KÝ (Nhóm 5; issue #80; đánh dấu [P7] tại vị trí)
-- Căn cứ: signing-backend-plan.md mục 3.2, 3.3; migration signing 0006_ho_so_goc_pham_vi_chuc_vu_muc_do.
--   1) signing_request thêm ho_so_goc_id (FK tự tham chiếu, RESTRICT) và index: trình lại sau từ chối
--      tạo hồ sơ mới trỏ về hồ sơ bị từ chối; hồ sơ TU_CHOI là trạng thái kết thúc.
--   2) signing_process_step_signer thêm pham_vi_chuc_vu (NULL khi cấu hình theo tài khoản): chức vụ
--      hiểu tương đối trong đơn vị người tạo, đơn vị cố định của cấp hoặc toàn cơ quan.
--   3) signing_process thêm don_vi_ap_dung_id (FK organizations_donvi, RESTRICT) và index; CHECK phạm vi
--      PHONG_BAN bắt buộc có đơn vị, CONG_TY không gắn đơn vị (migration signing 0008_don_vi_ap_dung; dữ liệu
--      cũ PHONG_BAN chưa có đơn vị được chuyển CONG_TY, đúng hành vi trước đó). Người tạo hồ sơ chỉ chọn
--      quy trình CONG_TY hoặc PHONG_BAN của đơn vị mình.
--   4) Cấp manage_signing_process cho nhóm TP (plan mục 8): lãnh đạo đơn vị quản lý quy trình PHONG_BAN
--      của đơn vị mình; quy trình CONG_TY vẫn chỉ quản trị quản lý (kiểm ở tầng ứng dụng).
--   5) Cột của các bảng signing_* theo tên chuẩn hóa ở #96 (nguoi_tao_id, nguoi_cap_nhat_id, updated_at,
--      document_id); migration signing 0009_doi_ten_cot_theo_ddl_chuan_hoa đổi tên cột cho DB dựng bằng migration.
-- Quy mô sau [P7] và [P10] (nạp sạch): 55 bảng vật lý | 20 kiểu ENUM | 77 quyền thao tác | 5 nhóm quyền chuẩn | 197 lượt phân quyền.
-- =====================================================================
-- THAY ĐỔI PHASE 6c TRÌNH KÝ (Nhóm 5; issue #79; đánh dấu [6c] tại vị trí)
-- Căn cứ: docs/modules/05_signing_workflow/danh-gia-nghiep-vu-va-de-xuat.md mục 2 (đã chốt ở PR #78),
--   plan-trien-khai-theo-phase.md Phase 6c; migration signing 0005_bo_kieu_ky_chi_nhan_van_ban_di.
--   1) signing_process bỏ cột kieu_ky_mac_dinh; signing_request bỏ cột kieu_ky.
--      Cấp ký luôn tuần tự theo thu_tu, người trong cùng cấp ký song song.
--      Lý do bỏ cách thức TUAN_TU/SONG_SONG cho toàn hồ sơ:
--      - SONG_SONG mở mọi cấp cùng lúc, tương đương quy trình một cấp: người ký cuối có thể ký trước
--        khi cấp kiểm tra (nội dung, pháp chế) xem xong, việc chia cấp mất nghĩa.
--      - Người trình được chọn cách thức, tức tự quyết lãnh đạo có phải chờ cấp dưới; thứ tự kiểm duyệt
--        thuộc người thiết kế quy trình.
--      - Mọi quy tắc (mở cấp, hạn xử lý, thu hồi chữ ký) phải rẽ nhánh theo cách thức mà không thêm giá trị.
--      Căn cứ thực tiễn: ký điện tử định tuyến theo thứ tự (cùng thứ tự ký song song, thứ tự sau chờ
--      thứ tự trước); văn phòng điện tử đi theo cấp. Tham khảo NĐ 30/2020 Điều 12: kiểm tra nội dung,
--      thể thức trước khi trình người có thẩm quyền ký.
--   2) Bỏ ENUM signing_kieuky: không cột, hàm hay đối tượng nào dùng. Bằng chứng trên bản trước thay đổi:
--      tên chỉ xuất hiện ở dòng CREATE TYPE; information_schema.columns không có cột udt_name =
--      'signing_kieuky' (kieu_ky, kieu_ky_mac_dinh là VARCHAR); pg_depend không có đối tượng phụ thuộc.
--   3) Không đổi document_kind: trình ký chỉ nhận 'vanbandi', kiểm ở tầng ứng dụng; giữ ENUM chung
--      vì documents_view_log và task_congviec vẫn dùng 'vanbanden'.
-- Quy mô sau thay đổi (đã ghép PR #92): 55 bảng vật lý | 20 kiểu ENUM | 77 quyền thao tác | 5 nhóm quyền chuẩn | 196 lượt phân quyền.
-- =====================================================================
-- THAY ĐỔI BỎ VĂN BẢN MẬT (GVHD đã chốt bỏ văn bản mật; đánh dấu [BỎ MẬT] tại vị trí; giữ nhãn phiên bản)
-- Bối cảnh: khách hàng là doanh nghiệp bảo hiểm; "văn bản mật" được hiểu là tài liệu nội bộ
--   hạn chế (không phải bí mật nhà nước) và xử lý bằng quyền xem + nhật ký xem trên văn bản đến/đi.
--   1) Bỏ phân hệ văn bản mật: xóa 7 bảng documents_vanbanmat*, 2 hàm và 4 trigger đi kèm.
--   2) ENUM document_kind còn 'vanbanden', 'vanbandi'.
--   3) documents_vanbanden, documents_vanbandi thêm cột pham_vi ('NOI_BO' | 'HAN_CHE'), mặc định 'NOI_BO';
--      CHECK văn bản HAN_CHE không gửi mail toàn hệ thống (chuyển từ CHECK B2 của bảng mật).
--   4) Bỏ 4 quyền view/add/change/delete_vanbanmat và các lượt phân quyền tương ứng.
--   5) Trợ lý AI (role qlvb_readonly) chỉ đọc metadata qua view ai_*; view văn bản loại HAN_CHE,
--      bỏ cột/bảng đính kèm, và role không có SELECT trên bảng nghiệp vụ gốc.
-- Quy tắc xem văn bản HAN_CHE (tầng ứng dụng, queryset dùng chung của Nhóm 2):
--   chỉ người tạo, người nhận, thành viên đơn vị nhận; không ngoại lệ cho superuser hay quyền view_*;
--   mọi lượt mở ghi documents_view_log.
-- Trợ lý AI không dùng văn bản HAN_CHE trong mọi trường hợp, kể cả khi người hỏi là người nhận.
-- Quy tắc văn bản HAN_CHE (văn bản mật nội bộ công ty; không phải mật hành chính do cơ quan nhà nước ban hành):
--   người xem = người tạo + người nhận do người tạo chọn theo ID nhân viên (documents_*_nguoinhan);
--   không ngoại lệ cho superuser hay quyền view_*; tài khoản bị khóa (is_active = FALSE) mất quyền xem;
--   người không có quyền nhận 404 (như văn bản không tồn tại); mọi lượt xem/tải/bị chặn/đổi danh sách ghi documents_access_log.
--   pham_vi không đổi sau khi tạo; văn bản HAN_CHE không được xóa (MVP). Văn bản NOI_BO chỉ ghi documents_view_log.
--   Mã hóa nội dung: sau MVP.
-- Quy mô sau thay đổi: 55 bảng vật lý | 21 kiểu ENUM | 77 quyền thao tác | 5 nhóm quyền chuẩn | 196 lượt phân quyền.
-- =====================================================================
-- =====================================================================
-- CHUẨN HÓA TÊN CỘT (quy ước ở #68; các nhóm cập nhật model và migration theo tên mới)
--   1) update_at -> updated_at: signing_process, signing_request, signing_attempt, signing_change_thread.
--   2) create_by_id -> nguoi_tao_id: signing_process, signing_request, signing_attempt, signing_manifest;
--      update_by_id -> nguoi_cap_nhat_id: signing_process, signing_request, signing_attempt;
--      chỉ mục idx_signing_*_create_by -> idx_signing_*_nguoi_tao, idx_signing_*_update_by -> idx_signing_*_nguoi_cap_nhat.
--   3) created_time -> created_at, created_user_id -> nguoi_tao_id: records_chitiettailieu_attachment,
--      documents_vanbanden_attachment, documents_vanbandi_attachment, task_attachment.
--   4) nguoi_tao -> nguoi_tao_id: records_chitiettailieu, documents_vanbanden, documents_vanbandi, task_congviec.
--   5) status -> trang_thai: meetings_meetingroom, meetings_meetingbooking, birthdays_birthdaywish,
--      birthdays_birthdayemaillog (giá trị ENUM giữ nguyên).
--   6) signing_request.van_ban_id -> document_id (cùng tên với document_id ở các bảng dùng quan hệ đa hình khác).
-- Giữ nguyên: nguoi_lap_id (records_hoso, records_tailieu), các cột tiếng Anh/viết tắt của task_*,
--   meetings_meetingbooking.organizer_id (tên theo nghiệp vụ, không phải xung đột giữa các nhóm).
-- =====================================================================
-- =====================================================================
-- RELEASE_DDL_v1 — trạng thái đích của Issue #53, sinh từ RELEASE_DDL_v0
-- Thay đổi so với v0 (mọi thay đổi đều đánh dấu [v1] tại vị trí):
--   1) ENUM hieu_luc_status thêm 'CON_HIEU_LUC_1_PHAN' (Nhóm 2; dùng chung 3 bảng văn bản và records_chitiettailieu).
--   2) records_chitiettailieu thêm don_vi_id (FK organizations_donvi, NULL) và chỉ mục (Nhóm 4).
--   3) records_chitiettailieu_attachment thêm file_size, mime_type (NULL) (Nhóm 4).
--   4) documents_vanbanmat: CHECK gui_mail_toan_he_thong = FALSE (mục B2).
--   5) auth_permission thêm 8 quyền: view/add/change/delete_nhomquyen, import_chucvu,
--      add/change/delete_phonghop (Nhóm 7); nhóm ADMIN nhận qua phép CROSS JOIN sẵn có.
--   6) Thêm bảng signing_key_unlock (Nhóm 5, Phase 6a; mục B7).
--   7) Cấp quyền chỉ đọc theo bảng/cột cho role qlvb_readonly nếu role tồn tại (Nhóm 8).
-- Không đưa vào DDL: mục B3 (độ khẩn/độ mật/số đăng ký; Nhóm 2 xác nhận bỏ), B1 (quy ước tài liệu),
--   B4/B5 (queryset dùng chung ở tầng ứng dụng), B6 (chưa chốt), bảng dashboard_* và bảng Django hệ thống.
-- Quy tắc cho nhóm: không tạo lại các thay đổi 2, 3, 5 bằng migration riêng (trùng cột/quyền khi áp dụng).
-- =====================================================================
-- =====================================================================
-- RELEASE_DDL_v0 — sinh từ SQL_Fix4 (csdl_qlvbtl_schema_final.sql)
-- Thay đổi so với SQL_Fix4 (chỉ phần Trình ký đã chốt, giữ model, sửa DDL):
--   1) signing_request.document_type: bỏ DEFAULT 'vanbanden'.
--   2) Trigger prevent_delete_or_tamper_signing_signature: chặn mọi cột trừ
--      trang_thai_xac_minh và thoi_diem_xac_minh.
--   3) ON DELETE RESTRICT cho: signing_attempt.trinh_ky_id, signing_attempt.luot_truoc_id,
--      signing_request_step.luot_trinh_id, signing_request_step_signer.buoc_ky_id,
--      signing_request_step_signer.uy_quyen_tu_id, signing_key.khoa_thay_the_id.
--   4) Bỏ kiểu ENUM thừa signing_key_status (21 kiểu ENUM).
--   5) Số liệu thống nhất theo kết quả chạy thực: 73 quyền, 198 lượt phân quyền; bỏ phần lặp trong danh sách quyền các nhóm.
-- Chưa đưa vào v0 (chờ chốt): ENUM hieu_luc_status thêm giá trị mới, bảng Django
-- hệ thống, signing_key_unlock, và các cột bổ sung của từng nhóm (làm bằng migration sau base).
-- =====================================================================
-- =====================================================================
-- HỆ THỐNG QUẢN LÝ VĂN BẢN VÀ TÀI LIỆU (QLVB&TL) — PostgreSQL DDL
-- Sinh tự động & đồng bộ từ đặc tả: CSDL QLVB&TL.md
-- Quy mô: 58 bảng vật lý | 20 kiểu ENUM | 78 quyền thao tác | 7 nhóm quyền chuẩn | 208 lượt phân quyền
-- =====================================================================
-- GHI CHÚ VỀ CÁC QUYẾT ĐỊNH THIẾT KẾ & ĐỒNG BỘ KIẾN TRÚC:
--
-- 1) [CẬP NHẬT] Cơ cấu tổ chức dùng 2 BẢNG RIÊNG theo đặc tả mới nhất
-- (tab "Đvị, phòngban"): organizations*khoi (Khối/Khu vực - cấp 1) và
-- organizations_donvi (Đơn vị/phòng ban - cấp 2, FK khoi_id -> Khối).
-- Không dùng self-reference — mọi FK nghiệp vụ (don_vi_nhan,
-- accounts_employee.don_vi_id...) chỉ trỏ tới organizations_donvi,
-- tránh trường hợp trỏ nhầm vào một hàng Khối như thiết kế tự tham
-- chiếu cũ có thể gặp phải.
-- 2) Mục 14 "accounts_employee" là bản đặc tả cuối cùng, dùng làm bảng
-- người dùng chính (thay auth_user mặc định của Django, vì có sẵn
-- username/password) — mọi FK "ForeignKey (auth_user)" trong tài
-- liệu được trỏ về accounts_employee(id).
-- 3) "Văn bản liên quan" ở signing_request và task (Công việc) tham
-- chiếu đa hình tới 1-trong-3 bảng văn bản -> dùng cặp cột
-- (document_type, document_id) thay vì FK cứng (generic relation
-- kiểu Django ContentType), có CHECK ràng buộc giá trị hợp lệ.
-- 4) Cột "kyhieu" trùng lặp với "so_hieu" ở documents_vanbandi /
-- documents_vanbanmat (tài liệu gốc tự ghi chú "trùng với 7") ->
-- bỏ, chỉ giữ so_hieu.
-- 5) Thống nhất ENUM: Đúng 21 kiểu ENUM chuẩn. Hợp nhất hieu_luc_status
-- ('CON_HIEU_LUC', 'HET_HIEU_LUC', 'HET_VA_THAY_THE') dùng chung cho
-- cả 4 bảng văn bản và chi tiết tài liệu; xóa bỏ hieu_luc_status_v2.
-- 6) [Tô Thanh Tân] Hệ thống phân quyền RBAC độc lập, kế thừa quy ước và tên bảng
-- chuẩn của Django Auth (auth_group, auth_permission, auth_group_permissions),
-- mở rộng cột module_ten phục vụ trực tiếp giao diện phân nhóm quyền, không phụ
-- thuộc cứng vào bảng nội bộ django_content_type để đảm bảo tính độc lập DDL.
-- Cột content_type_id để NULL để chạy DDL trực tiếp trên PostgreSQL;
-- Seed 81 quyền chi tiết, 5 nhóm quyền chuẩn và 206 lượt mapping idempotent.
-- 7) [Tô Thanh Tân] accounts_employee bổ sung is_active (khóa tài khoản nhân viên nghỉ
-- việc theo chuẩn Django User), is_staff, is_superuser; thống nhất mô hình
-- Custom User Model hoặc Profile 1-1 không bị dư thừa dữ liệu.
-- 8) [Lê Thanh Hậu — Issue #25] Bảo toàn bằng chứng ký số điện tử:
-- - FK signing_attempt -> request, signing_signature, signing_manifest đổi sang
-- ON DELETE RESTRICT.
-- - Trigger chặn xóa cứng attempt đã kích hoạt, chữ ký số và manifest đã chốt.
-- - Kiến trúc Zero-Knowledge: Backend TUYỆT ĐỐI KHÔNG lưu encrypted_private_key.
-- 9) [Phan Tạ Hữu Đức & Chỉ đạo GVHD 25/09/2026] Chuẩn hóa phân hệ Công việc:
-- - Phân quyền duyệt/hủy duyệt theo Object-level trong task_participant (Người tạo,
-- Chủ trì CHU_TRI, Chỉ đạo CHI_DAO); bỏ kiểm tra 3 lớp cứng và không chặn duyệt bằng approve_congviec.
-- - Bổ sung bảng liên kết Many-to-Many task_congviec_donvi (gắn công việc với phòng ban).
-- - Bổ sung 2 quyền xem: view_all_congviec và view_dept_congviec.
-- 10) [Trần Vũ Giang Anh] Quyền use_aiassistant có ranh giới an ninh chặt chẽ:
-- chỉ cấp quyền UI, tầng ứng dụng / RAG bắt buộc kiểm tra quyền xem (view*\*)
-- và ACL trước khi cung cấp ngữ cảnh cho mô hình ngôn ngữ lớn (LLM).
-- 11) [Chỉ đạo GVHD Thầy Trần Phương Duy & Phan Tạ Hữu Đức Nhóm 6 29/09/2026] Chuẩn hóa Tệp đính kèm Hướng A:
-- Xóa cột đơn file_dinh_kem trong 4 bảng chính (documents_vanbanden, documents_vanbandi,
-- documents_vanbanmat, records_chitiettailieu) chuyển sang 4 bảng con 1-N chuẩn 7 trường.
-- Đồng thời bảng task_attachment của Nhóm 6 được nâng cấp lên 9 trường chuẩn (thêm name, path,
-- is_deleted, created_at, nguoi_tao_id nhưng bảo toàn nguyên vẹn 2 cột nghiệp vụ loai và y_kien_id).
-- 12) [Lê Thành Tài & Lê Thanh Hậu — Nhóm 5 29/09/2026] Đồng bộ 100% 14 bảng signing_* theo Django model:
-- Chuẩn hóa tên cột thuần Việt (so_luot, phien_ban_van_ban, vi_tri_luu_tep, ma_bam_tai_lieu...),
-- bổ sung đầy đủ trường tọa độ box ký trên PDF (trang_ky, toa_do_x, toa_do_y, chieu_rong_khung, chieu_cao_khung),
-- ảnh chữ ký, ủy quyền ký (uy_quyen_tu_id, ly_do_uy_quyen); chuẩn hóa toàn bộ khóa ngoại người dùng
-- sang accounts_employee(id) và đơn vị, chức vụ; duy trì bất biến chứng thực bằng trigger.
-- 13) [Lê Trí Kiệt — Nhóm 2 29/09/2026] Chuẩn hóa nghiệp vụ Phân hệ Văn bản (Nghị định 30/2020/NĐ-CP):
-- - Khóa chống trùng STT theo năm: CONSTRAINT uq_vanbanden_nam_stt UNIQUE (nam, so_thu_tu) và
-- uq_vanbandi_nam_stt UNIQUE (nam, so_thu_tu) chống xung đột lưu đồng thời (Race Condition).
-- - Ràng buộc toàn vẹn link_thay_the: Bắt buộc không rỗng khi hieu_luc = 'HET_VA_THAY_THE' trên cả 3 bảng văn bản.
-- - Trigger tự động dọn dẹp documents_view_log khi xóa cứng văn bản: trg_cleanup_viewlog_on_doc_delete
-- loại bỏ triệt để bản ghi mồ côi sinh ra do quan hệ đa hình Generic Relation.
-- 14) [Lê Thanh Hậu — Nhóm 5 Issue #47 30/09/2026] Chuẩn hóa chuyên sâu Phân hệ Trình ký (signing_*):
-- - [P0] Bổ sung document_type document_kind NOT NULL cho signing_request và index (document_type, document_id).
-- - [P0] Trigger bảo toàn bằng chứng số: chặn UPDATE trên signing_signature (chỉ cho phép cập nhật thẩm định),
-- chặn UPDATE/DELETE trên signing_manifest khi DA_CHOT, biến signing_audit_log thành chuẩn WORM (chặn cả UPDATE và DELETE).
-- - [P0] Chuyển 3 FK của signing_audit_log sang ON DELETE RESTRICT (tránh UPDATE ngầm làm mất dấu vết).
-- - [P1] Bổ sung 5 quyền phân hệ Trình ký: manage_signing_process, send_trinhky, delegate_trinhky, cancel_trinhky, view_signing_audit (nâng tổng lên 73 quyền).
-- - [P1] Chuyển FK luot_trinh_id ở signing_change_thread và yeu_cau_sua_id ở signing_change_message sang ON DELETE RESTRICT (bảo toàn lịch sử thảo luận).
-- - [P1] Chuyển FK nguoi_ky_id, chuc_vu_id ở signing_process_step_signer sang ON DELETE RESTRICT (tránh vi phạm CHECK một trong hai khi xóa user/chức vụ).
-- - [P1] Cho phép NULL ở các cột chưa có giá trị lúc tạo bản nháp (phien_ban_van_ban, vi_tri_luu_tep, ma_bam_tai_lieu ở request; ten_chuc_vu, khoa_chong_trung_thao_tac ở signer; vi_tri_luu ở manifest).
-- - [P1] signing_audit_log.dia_chi_ip cho phép NULL, bỏ mặc định 127.0.0.1.
-- - [P2] Bổ sung 2 index nhắc hạn: signing_request(han_chot) và signing_request_step(han_xu_ly).
-- =====================================================================
CREATE SCHEMA IF NOT EXISTS public;

SET search_path TO public;

BEGIN;

---

-- 0. HÀM DÙNG CHUNG: tự cập nhật updated_at (tương đương auto_now=True)

---

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
NEW.updated_at = now();
RETURN NEW;
END;

$$
LANGUAGE plpgsql;

-- ---------------------------------------------------------------------
-- 0.1 ENUM TYPES
-- ---------------------------------------------------------------------
-- Hiệu lực văn bản / tài liệu: thống nhất 1 ENUM duy nhất dùng chung cho cả Văn bản và Tài liệu lưu trữ
CREATE TYPE hieu_luc_status       AS ENUM ('CON_HIEU_LUC', 'CON_HIEU_LUC_1_PHAN', 'HET_HIEU_LUC', 'HET_VA_THAY_THE');
-- [REMOVED] hoso_status ENUM — đã xóa theo yêu cầu Nhóm 3 (Thịnh Trương): cột trang_thai chưa được duyệt.
CREATE TYPE chitiettailieu_hienthi AS ENUM ('TAT_CA','NOI_BO_PHONG_BAN');

CREATE TYPE signing_process_status AS ENUM ('DRAFT','HOAT_DONG','NGUNG');

CREATE TYPE signing_scope          AS ENUM ('DEPARTMENT','COMPANY');

-- [6c] Bỏ ENUM signing_kieuky: không cột nào dùng; cách thức ký toàn yêu cầu đã bỏ (cấp luôn tuần tự).

CREATE TYPE signing_request_status AS ENUM ('NHAP','CHO_KY','HOAN_THANH','TU_CHOI','HUY','QUA_HAN');

CREATE TYPE signing_attempt_status AS ENUM ('DRAFT','CHO_KY','YEU_CAU_SUA','HOAN_THANH','TU_CHOI','HUY','QUA_HAN');

CREATE TYPE signing_step_status    AS ENUM ('CHO_KY','DA_KY','TU_CHOI','BO_QUA','YEU_CAU_SUA','THU_HOI');


CREATE TYPE signing_verify_status  AS ENUM ('CHUA_XAC_MINH','HOP_LE','KHONG_HOP_LE');

CREATE TYPE signing_manifest_status AS ENUM ('DRAFT','FINAL');

CREATE TYPE signing_thread_status  AS ENUM ('OPEN','RELEASED','RESOLVED');

CREATE TYPE signing_notify_channel AS ENUM ('IN_APP','EMAIL');

CREATE TYPE signing_notify_status  AS ENUM ('CHO_GUI','DA_GUI','THAT_BAI');

CREATE TYPE task_vaitro            AS ENUM ('CHU_TRI','CHI_DAO','THAM_GIA');

CREATE TYPE task_attachment_loai   AS ENUM ('GIAO_VIEC','BANG_CHUNG');

CREATE TYPE meetingroom_status     AS ENUM ('AVAILABLE','MAINTENANCE','UNAVAILABLE');

CREATE TYPE meetingbooking_status  AS ENUM ('CONFIRMED','CANCELLED','COMPLETED');

CREATE TYPE birthdaywish_status    AS ENUM ('PENDING','APPROVED','REJECTED');

CREATE TYPE emaillog_status        AS ENUM ('PENDING','SENDING','SUCCESS','FAILED','RETRY');

CREATE TYPE employee_work_status   AS ENUM ('LAM_VIEC','NGHI_VIEC');
-- dùng chung cho generic relation "văn bản liên quan"
CREATE TYPE document_kind          AS ENUM ('vanbanden','vanbandi'); -- [BỎ MẬT] bỏ 'vanbanmat'

-- =====================================================================
-- 12. DANH MỤC CHỨC VỤ (accounts_position)
-- =====================================================================
CREATE TABLE accounts_position (
    id BIGSERIAL PRIMARY KEY,
    display_order INTEGER NOT NULL UNIQUE, -- STT ưu tiên hiển thị, tự động = MAX+1
    name VARCHAR(255) NOT NULL, -- Tên chức vụ
    is_public BOOLEAN NOT NULL DEFAULT TRUE, -- Hiển thị (isPublic)
    note TEXT
);

-- =====================================================================
-- 11. CƠ CẤU TỔ CHỨC: KHỐI/KHU VỰC (Cấp 1) + ĐƠN VỊ, PHÒNG BAN (Cấp 2)
-- =====================================================================
CREATE TABLE organizations_khoi (
    id BIGSERIAL PRIMARY KEY,
    ten VARCHAR(255) NOT NULL, -- Tên khối/khu vực
    thu_tu_hien_thi INTEGER NOT NULL DEFAULT 0 -- Thứ tự hiển thị
);

CREATE TABLE organizations_donvi (
    id BIGSERIAL PRIMARY KEY,
    khoi_id BIGINT NOT NULL REFERENCES organizations_khoi (id) ON DELETE RESTRICT,
    stt_uu_tien INTEGER NOT NULL UNIQUE, -- tự động = MAX + 1
    ten VARCHAR(255) NOT NULL, -- Tên đơn vị/phòng ban
    dia_chi VARCHAR(255),
    dien_thoai VARCHAR(20),
    email VARCHAR(254),
    is_public BOOLEAN NOT NULL DEFAULT TRUE, -- isPublic
    ghi_chu TEXT
);

CREATE INDEX idx_donvi_khoi ON organizations_donvi (khoi_id);

-- =====================================================================
-- 15. NHÓM QUYỀN & QUYỀN THAO TÁC (auth_group / auth_permission)
-- RBAC độc lập, kế thừa quy ước Django Auth và mở rộng module_ten phục vụ quản trị/phân nhóm quyền
-- =====================================================================
CREATE TABLE auth_group (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL UNIQUE,
    ma_nhom_quyen VARCHAR(50) UNIQUE -- vd: TP -> Trưởng phòng (mã nhóm mở rộng)
);

CREATE TABLE auth_permission (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL, -- vd: Xem chi tiết văn bản đến
    content_type_id BIGINT, -- Tương thích quy ước Django Auth; để NULL trong DDL vì hệ thống dùng RBAC độc lập, không phụ thuộc django_content_type
    codename VARCHAR(100) NOT NULL UNIQUE, -- vd: view_vanbanden
    module_ten VARCHAR(150) NOT NULL -- Module áp dụng phục vụ gom nhóm trực tiếp trên UI
);

CREATE TABLE auth_group_permissions (
    id BIGSERIAL PRIMARY KEY,
    group_id BIGINT NOT NULL REFERENCES auth_group (id) ON DELETE CASCADE,
    permission_id BIGINT NOT NULL REFERENCES auth_permission (id) ON DELETE CASCADE,
    CONSTRAINT uq_auth_group_permission UNIQUE (group_id, permission_id)
);

-- =====================================================================
-- 14. CÁN BỘ NHÂN VIÊN (accounts_employee) — kiêm Custom User Model Django
-- Đã bổ sung is_active, is_staff, is_superuser theo góp ý của Tô Thanh Tân
-- =====================================================================
CREATE TABLE accounts_employee (
    id BIGSERIAL PRIMARY KEY,
    ho_ten VARCHAR(150) NOT NULL, -- Họ và tên
    ngay_sinh DATE NOT NULL, -- UI ẩn năm sinh trừ Admin
    chuc_vu_id BIGINT NOT NULL REFERENCES accounts_position (id) ON DELETE RESTRICT,
    chuc_danh VARCHAR(150), -- Chức danh (tự do, khác Chức vụ)
    email VARCHAR(254) UNIQUE,
    sdt VARCHAR(20), -- SĐT cá nhân / SĐT bàn
    don_vi_id BIGINT NOT NULL REFERENCES organizations_donvi (id) ON DELETE RESTRICT,
    username VARCHAR(150) NOT NULL UNIQUE, -- auto = local-part email
    password VARCHAR(255) NOT NULL, -- lưu hash (vd pbkdf2/argon2), KHÔNG lưu plaintext
    is_active BOOLEAN NOT NULL DEFAULT TRUE, -- Cờ khóa tài khoản nhân viên nghỉ việc (chuẩn Django)
    is_staff BOOLEAN NOT NULL DEFAULT FALSE, -- Quyền đăng nhập trang quản trị
    is_superuser BOOLEAN NOT NULL DEFAULT FALSE, -- Quyền quản trị tối cao
    is_public BOOLEAN NOT NULL DEFAULT TRUE,
    trang_thai employee_work_status NOT NULL DEFAULT 'LAM_VIEC',
    ghi_chu TEXT,
    last_login TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_employee_updated_at BEFORE UPDATE ON accounts_employee
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE INDEX idx_employee_donvi ON accounts_employee (don_vi_id);

CREATE INDEX idx_employee_chucvu ON accounts_employee (chuc_vu_id);

CREATE INDEX idx_employee_is_active ON accounts_employee (is_active);

-- Nhóm quyền của CBNV (FK/M2M -> auth_group, tương đương auth_user_groups trong Django)
CREATE TABLE accounts_employee_groups (
    id BIGSERIAL PRIMARY KEY,
    employee_id BIGINT NOT NULL REFERENCES accounts_employee (id) ON DELETE CASCADE,
    group_id BIGINT NOT NULL REFERENCES auth_group (id) ON DELETE CASCADE,
    CONSTRAINT uq_employee_group UNIQUE (employee_id, group_id)
);

-- Quyền cá nhân trực tiếp của CBNV (FK/M2M -> auth_permission, tương đương auth_user_user_permissions trong Django)
CREATE TABLE accounts_employee_user_permissions (
    id BIGSERIAL PRIMARY KEY,
    employee_id BIGINT NOT NULL REFERENCES accounts_employee (id) ON DELETE CASCADE,
    permission_id BIGINT NOT NULL REFERENCES auth_permission (id) ON DELETE CASCADE,
    CONSTRAINT uq_employee_permission UNIQUE (employee_id, permission_id)
);

-- Phân công kiêm nhiệm của CBNV (Issue #24; đánh dấu [CBNV])
CREATE TABLE accounts_employee_assignment (
    id BIGSERIAL PRIMARY KEY,
    employee_id BIGINT NOT NULL REFERENCES accounts_employee (id) ON DELETE CASCADE,
    don_vi_id BIGINT NOT NULL REFERENCES organizations_donvi (id) ON DELETE RESTRICT,
    chuc_vu_id BIGINT NOT NULL REFERENCES accounts_position (id) ON DELETE RESTRICT,
    chuc_danh VARCHAR(150),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_employee_assignment UNIQUE (employee_id, don_vi_id, chuc_vu_id)
);

CREATE INDEX idx_emp_assign_emp ON accounts_employee_assignment (employee_id);

CREATE INDEX idx_emp_assign_donvi ON accounts_employee_assignment (don_vi_id);

CREATE INDEX idx_emp_assign_chucvu ON accounts_employee_assignment (chuc_vu_id);

-- Lượt nhập Excel CBNV chạy nền; active_key đảm bảo toàn hệ thống chỉ có một lượt đang chạy.
CREATE TABLE accounts_employee_import_job (
    id UUID PRIMARY KEY,
    owner_id BIGINT NOT NULL REFERENCES accounts_employee (id),
    idempotency_key VARCHAR(128),
    active_key VARCHAR(32),
    file_path VARCHAR(1024) NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'queued',
    phase VARCHAR(16) NOT NULL DEFAULT 'queued',
    processed INTEGER NOT NULL DEFAULT 0 CHECK (processed >= 0),
    total INTEGER NOT NULL DEFAULT 0 CHECK (total >= 0),
    created_count INTEGER NOT NULL DEFAULT 0 CHECK (created_count >= 0),
    errors JSONB NOT NULL DEFAULT '[]'::jsonb,
    message VARCHAR(100) NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_employee_import_owner_idem UNIQUE (owner_id, idempotency_key),
    CONSTRAINT uq_employee_import_active_key UNIQUE (active_key)
);

CREATE INDEX idx_employee_import_status ON accounts_employee_import_job (status, created_at);

-- Ghi chú: spec mới (tab "Đvị, phòngban") không có trường "Trưởng đơn vị"
-- trên organizations_donvi -> không tạo cột manager_id.

-- =====================================================================
-- 4. DANH MỤC HỒ SƠ (records_hoso)
-- Đã tinh gọn & nâng cấp theo review của Nhóm 3 (Thịnh Trương):
--   - Xóa 6 trường chưa duyệt: don_vi, trang_thai, thoi_han_bao_quan,
--     ngay_dong, ngay_nop_luu, is_default.
--   - FK nguoi_lap_id → settings.AUTH_USER_MODEL (ON DELETE RESTRICT
--     tương đương on_delete=PROTECT trong Django).
--   - stt_uu_tien: số nguyên dương, UNIQUE, tự động MAX+1 qua trigger,
--     có xử lý chống trùng đồng thời (advisory lock).
--   - is_he_thong: cờ nhận diện Hồ sơ chung / bản ghi hệ thống, có trigger
--     BEFORE DELETE chống xóa.
--   - Partial unique index: đảm bảo duy nhất 1 Hồ sơ hệ thống (Hồ sơ chung).
--   - Bổ sung chỉ mục tìm kiếm: so_ky_hieu, ten_ho_so, ngay_lap, nguoi_lap_id.
-- =====================================================================
CREATE TABLE records_hoso (
    id BIGSERIAL PRIMARY KEY,
    stt_uu_tien INTEGER NOT NULL UNIQUE CHECK (stt_uu_tien > 0),
    so_ky_hieu VARCHAR(255) NOT NULL UNIQUE CHECK (BTRIM (so_ky_hieu) <> ''),
    ten_ho_so VARCHAR(255) NOT NULL CHECK (BTRIM (ten_ho_so) <> ''),
    nguoi_lap_id BIGINT NOT NULL REFERENCES accounts_employee (id) ON DELETE RESTRICT,
    ngay_lap TIMESTAMPTZ,
    ghi_chu TEXT,
    is_he_thong BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Partial index: đảm bảo duy nhất 1 bản ghi Hồ sơ hệ thống (Hồ sơ chung)
CREATE UNIQUE INDEX uq_records_hoso_he_thong ON records_hoso (is_he_thong)
WHERE
    is_he_thong = TRUE;

-- Chỉ mục tìm kiếm cho records_hoso (Đã loại bỏ idx_hoso_so_ky_hieu thừa do trùng với UNIQUE constraint)
CREATE INDEX idx_hoso_ten ON records_hoso (ten_ho_so);

CREATE INDEX idx_hoso_ngay_lap ON records_hoso (ngay_lap);

CREATE INDEX idx_hoso_nguoi_lap ON records_hoso (nguoi_lap_id);

CREATE TRIGGER trg_hoso_updated_at BEFORE UPDATE ON records_hoso
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Trigger tự động gán stt_uu_tien = MAX + 1 khi INSERT (nếu chưa cung cấp hoặc = 0)
-- Sử dụng advisory lock để chống race condition khi nhiều request đồng thời.
CREATE OR REPLACE FUNCTION auto_stt_uu_tien_hoso()
RETURNS TRIGGER AS
$$

BEGIN
IF NEW.stt_uu_tien IS NULL OR NEW.stt_uu_tien = 0 THEN
-- Advisory lock trên OID của bảng để serialize việc tính MAX
PERFORM pg_advisory_xact_lock('records_hoso'::regclass::oid::bigint);
NEW.stt_uu_tien := COALESCE(
(SELECT MAX(stt_uu_tien) FROM records_hoso), 0
) + 1;
END IF;
RETURN NEW;
END;

$$
LANGUAGE plpgsql;

CREATE TRIGGER trg_hoso_auto_stt BEFORE INSERT ON records_hoso
  FOR EACH ROW EXECUTE FUNCTION auto_stt_uu_tien_hoso();

-- Trigger chống xóa Hồ sơ chung / bản ghi hệ thống
CREATE OR REPLACE FUNCTION prevent_delete_he_thong_hoso()
RETURNS TRIGGER AS
$$

BEGIN
IF OLD.is_he_thong = TRUE THEN
RAISE EXCEPTION 'Không thể xóa Hồ sơ chung / bản ghi hệ thống (records_hoso id=%).', OLD.id;
END IF;
RETURN OLD;
END;

$$
LANGUAGE plpgsql;

CREATE TRIGGER trg_hoso_prevent_delete BEFORE DELETE ON records_hoso
  FOR EACH ROW EXECUTE FUNCTION prevent_delete_he_thong_hoso();

-- Trigger bảo vệ tuyệt đối Hồ sơ chung: Chặn lách luật tắt cờ is_he_thong từ TRUE sang FALSE
CREATE OR REPLACE FUNCTION prevent_update_he_thong_hoso()
RETURNS TRIGGER AS
$$

BEGIN
IF OLD.is_he_thong = TRUE AND NEW.is_he_thong = FALSE THEN
RAISE EXCEPTION 'Bảo toàn Hồ sơ hệ thống: Không thể gỡ bỏ cờ is_he_thong từ TRUE sang FALSE (records_hoso id=%).', OLD.id;
END IF;
RETURN NEW;
END;

$$
LANGUAGE plpgsql;

CREATE TRIGGER trg_hoso_prevent_update_he_thong BEFORE UPDATE ON records_hoso
  FOR EACH ROW EXECUTE FUNCTION prevent_update_he_thong_hoso();

-- =====================================================================
-- 5. LOẠI VĂN BẢN (records_loaivanban)
-- Giữ đúng 7 trường đã duyệt bởi Nhóm 3 (Thịnh Trương).
-- Không thêm stt_uu_tien — STT hiển thị trên UI là forloop.counter.
-- FK ho_so_id theo chuẩn Django _id convention.
-- Ràng buộc chống trùng tên Loại văn bản trong cùng một Hồ sơ (không phân biệt hoa/thường, khoảng trắng thừa).
-- Bổ sung CHECK (BTRIM(ten_loai) <> '') chống chuỗi rỗng và khoảng trắng thừa.
-- =====================================================================
CREATE TABLE records_loaivanban (
    id BIGSERIAL PRIMARY KEY,
    ho_so_id BIGINT NOT NULL REFERENCES records_hoso (id) ON DELETE RESTRICT,
    ten_loai VARCHAR(255) NOT NULL CHECK (BTRIM (ten_loai) <> ''),
    ngay_lap TIMESTAMPTZ,
    ghi_chu TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_loaivanban_updated_at BEFORE UPDATE ON records_loaivanban
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Ràng buộc không cho trùng tên Loại văn bản trong cùng một Hồ sơ (xử lý chữ hoa/thường và khoảng trắng thừa)
CREATE UNIQUE INDEX uq_records_loaivanban_hoso_ten ON records_loaivanban (
    ho_so_id,
    LOWER(TRIM(ten_loai))
);

-- Chỉ mục tìm kiếm cho records_loaivanban
CREATE INDEX idx_loaivanban_hoso ON records_loaivanban (ho_so_id);

CREATE INDEX idx_loaivanban_ten ON records_loaivanban (ten_loai);

CREATE INDEX idx_loaivanban_ngay_lap ON records_loaivanban (ngay_lap);

-- =====================================================================
-- 6. DANH MỤC TÀI LIỆU CẤP 1 (records_tailieu)
-- =====================================================================
CREATE TABLE records_tailieu (
    id BIGSERIAL PRIMARY KEY,
    stt_uu_tien SMALLINT NOT NULL UNIQUE,
    ky_hieu VARCHAR(255),
    ten_tai_lieu VARCHAR(255) NOT NULL,
    nguoi_lap_id BIGINT NOT NULL REFERENCES accounts_employee (id) ON DELETE RESTRICT,
    ngay_lap DATE,
    ghi_chu TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_tailieu_updated_at BEFORE UPDATE ON records_tailieu
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- =====================================================================
-- 7. LOẠI TÀI LIỆU CẤP 2 (records_loaitailieu)
-- =====================================================================
CREATE TABLE records_loaitailieu (
    id BIGSERIAL PRIMARY KEY,
    dm_tai_lieu BIGINT NOT NULL REFERENCES records_tailieu (id) ON DELETE RESTRICT,
    ten_loai VARCHAR(255) NOT NULL,
    is_public BOOLEAN NOT NULL DEFAULT TRUE,
    ngay_lap TIMESTAMPTZ,
    ghi_chu TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_loaitailieu_updated_at BEFORE UPDATE ON records_loaitailieu
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- =====================================================================
-- 8. CHI TIẾT TÀI LIỆU (records_chitiettailieu)
-- =====================================================================
CREATE TABLE records_chitiettailieu (
    id BIGSERIAL PRIMARY KEY,
    dm_tai_lieu BIGINT NOT NULL REFERENCES records_tailieu (id) ON DELETE RESTRICT,
    ky_hieu VARCHAR(255),
    tieu_de VARCHAR(255) NOT NULL,
    ngay_dang DATE NOT NULL,
    noi_ban_hanh VARCHAR(255),
    hieu_luc hieu_luc_status NOT NULL,
    ngay_het_hieu_luc DATE,
    link_thay_the VARCHAR(500),
    ghi_chu TEXT,
    hien_thi chitiettailieu_hienthi NOT NULL,
    don_vi_id BIGINT REFERENCES organizations_donvi (id) ON DELETE RESTRICT, -- [v1] Đơn vị sở hữu; phục vụ lọc NOI_BO_PHONG_BAN (Nhóm 4, Nhóm 8)
    nguoi_tao_id BIGINT REFERENCES accounts_employee (id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_chitiettailieu_updated_at BEFORE UPDATE ON records_chitiettailieu
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE INDEX idx_chitiettailieu_don_vi ON records_chitiettailieu (don_vi_id);

-- Loại tài liệu cấp 2 áp dụng cho chi tiết tài liệu (M2M, lọc theo dm_tai_lieu đã chọn)
CREATE TABLE records_chitiettailieu_loaitailieu (
    chitiettailieu_id BIGINT NOT NULL REFERENCES records_chitiettailieu (id) ON DELETE CASCADE,
    loaitailieu_id BIGINT NOT NULL REFERENCES records_loaitailieu (id) ON DELETE RESTRICT,
    PRIMARY KEY (
        chitiettailieu_id,
        loaitailieu_id
    )
);

-- Tệp đính kèm Chi tiết tài liệu (1-N, Hướng A theo Thầy Duy chốt)
CREATE TABLE records_chitiettailieu_attachment (
    id BIGSERIAL PRIMARY KEY,
    document_id BIGINT NOT NULL REFERENCES records_chitiettailieu (id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL, -- Tên gốc file khi upload
    path VARCHAR(500) NOT NULL, -- Đường dẫn lưu file trên server/storage
    file_size BIGINT CHECK (file_size >= 0), -- [v1] Dung lượng (byte); NULL với bản ghi cũ (Nhóm 4)
    mime_type VARCHAR(255), -- [v1] Kiểu MIME; NULL với bản ghi cũ (Nhóm 4)
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE, -- Cờ xóa mềm
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    nguoi_tao_id BIGINT REFERENCES accounts_employee (id) ON DELETE SET NULL
);

CREATE INDEX idx_chitiettailieu_attachment_doc ON records_chitiettailieu_attachment (document_id);

CREATE INDEX idx_chitiettailieu_attachment_deleted ON records_chitiettailieu_attachment (is_deleted);

-- =====================================================================
-- 1. VĂN BẢN ĐẾN (documents_vanbanden)
-- =====================================================================
CREATE TABLE documents_vanbanden (
    id BIGSERIAL PRIMARY KEY,
    nam SMALLINT NOT NULL,
    so_hieu VARCHAR(255) NOT NULL,
    so_thu_tu INTEGER NOT NULL, -- Số đến (auto increment theo nghiệp vụ, xử lý ở tầng app)
    ngay_den TIMESTAMPTZ NOT NULL,
    trich_yeu TEXT NOT NULL,
    noi_ban_hanh VARCHAR(500),
    ngay_van_ban TIMESTAMPTZ,
    nguoi_ky VARCHAR(255),
    chuc_vu VARCHAR(255),
    hieu_luc hieu_luc_status NOT NULL,
    ngay_het_hieu_luc TIMESTAMPTZ,
    link_thay_the VARCHAR(500),
    ghi_chu TEXT,
    hien_thi BOOLEAN NOT NULL DEFAULT TRUE,
    gui_mail_toan_he_thong BOOLEAN NOT NULL DEFAULT FALSE,
    pham_vi VARCHAR(20) NOT NULL DEFAULT 'NOI_BO', -- [BỎ MẬT] NOI_BO | HAN_CHE
    nguoi_tao_id BIGINT REFERENCES accounts_employee (id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_vanbanden_nam_stt UNIQUE (nam, so_thu_tu), -- Nghị định 30/2020/NĐ-CP: chống trùng số đến trong năm
    CONSTRAINT chk_vanbanden_link_thay_the CHECK (
        hieu_luc <> 'HET_VA_THAY_THE' OR (link_thay_the IS NOT NULL AND BTRIM(link_thay_the) <> '')
    ),
    -- [BỎ MẬT] Phạm vi xem: HAN_CHE chỉ người tạo, người nhận, đơn vị nhận được xem (tầng ứng dụng)
    CONSTRAINT chk_vanbanden_pham_vi CHECK (pham_vi IN ('NOI_BO', 'HAN_CHE')),
    -- [BỎ MẬT] Văn bản hạn chế không được gửi mail toàn hệ thống (thay CHECK B2 của bảng mật cũ)
    CONSTRAINT chk_vanbanden_han_che_khong_mail_toan_he_thong CHECK (pham_vi <> 'HAN_CHE' OR gui_mail_toan_he_thong = FALSE)
);

CREATE TRIGGER trg_vanbanden_updated_at BEFORE UPDATE ON documents_vanbanden
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE INDEX idx_vanbanden_sohieu ON documents_vanbanden (so_hieu);

CREATE INDEX idx_vanbanden_nam ON documents_vanbanden (nam);

CREATE TABLE documents_vanbanden_hoso (
    vanbanden_id BIGINT NOT NULL REFERENCES documents_vanbanden (id) ON DELETE CASCADE,
    hoso_id BIGINT NOT NULL REFERENCES records_hoso (id) ON DELETE RESTRICT,
    PRIMARY KEY (vanbanden_id, hoso_id)
);

CREATE INDEX idx_vanbanden_hoso_hoso ON documents_vanbanden_hoso (hoso_id);

CREATE TABLE documents_vanbanden_danhmuc (
    vanbanden_id BIGINT NOT NULL REFERENCES documents_vanbanden (id) ON DELETE CASCADE,
    loaivanban_id BIGINT NOT NULL REFERENCES records_loaivanban (id) ON DELETE RESTRICT,
    PRIMARY KEY (vanbanden_id, loaivanban_id)
);

CREATE INDEX idx_vanbanden_danhmuc_loai ON documents_vanbanden_danhmuc (loaivanban_id);

-- Toàn vẹn tham chiếu chéo giữa Hồ sơ và Loại văn bản cho Văn bản đến:
-- 1) Khi thêm Loại văn bản, nếu văn bản đã liên kết hồ sơ thì Loại văn bản phải thuộc đúng Hồ sơ đó
CREATE OR REPLACE FUNCTION check_vanbanden_cross_reference()
RETURNS TRIGGER AS
$$

DECLARE
v_hoso_id BIGINT;
BEGIN
SELECT ho_so_id INTO v_hoso_id FROM records_loaivanban WHERE id = NEW.loaivanban_id;
IF EXISTS (SELECT 1 FROM documents_vanbanden_hoso WHERE vanbanden_id = NEW.vanbanden_id) THEN
IF NOT EXISTS (
SELECT 1 FROM documents_vanbanden_hoso
WHERE vanbanden_id = NEW.vanbanden_id AND hoso_id = v_hoso_id
) THEN
RAISE EXCEPTION 'Vi phạm toàn vẹn tham chiếu chéo: Loại văn bản (id=%) thuộc Hồ sơ (id=%), nhưng Văn bản đến (id=%) không liên kết với Hồ sơ này.',
NEW.loaivanban_id, v_hoso_id, NEW.vanbanden_id;
END IF;
END IF;
RETURN NEW;
END;

$$
LANGUAGE plpgsql;

CREATE TRIGGER trg_vanbanden_danhmuc_cross_ref
  BEFORE INSERT OR UPDATE ON documents_vanbanden_danhmuc
  FOR EACH ROW EXECUTE FUNCTION check_vanbanden_cross_reference();

-- 2) Khi xóa liên kết hồ sơ, không cho xóa nếu văn bản vẫn còn chứa loại văn bản thuộc hồ sơ đó
-- An toàn khi xóa văn bản cha (ON DELETE CASCADE): bỏ qua kiểm tra nếu văn bản cha không còn tồn tại
CREATE OR REPLACE FUNCTION check_vanbanden_hoso_delete_cross_ref()
RETURNS TRIGGER AS
$$

BEGIN
-- Nếu văn bản cha không còn tồn tại (đang trong luồng ON DELETE CASCADE của documents_vanbanden), bỏ qua không chặn
IF NOT EXISTS (SELECT 1 FROM documents_vanbanden WHERE id = OLD.vanbanden_id) THEN
RETURN OLD;
END IF;

IF EXISTS (
SELECT 1 FROM documents_vanbanden_danhmuc dm
JOIN records_loaivanban lvb ON dm.loaivanban_id = lvb.id
WHERE dm.vanbanden_id = OLD.vanbanden_id AND lvb.ho_so_id = OLD.hoso_id
) THEN
RAISE EXCEPTION 'Không thể gỡ Hồ sơ (id=%) khỏi Văn bản đến (id=%): văn bản vẫn còn chứa Loại văn bản thuộc Hồ sơ này.',
OLD.hoso_id, OLD.vanbanden_id;
END IF;
RETURN OLD;
END;

$$
LANGUAGE plpgsql;

CREATE CONSTRAINT TRIGGER trg_vanbanden_hoso_del_cross_ref
  AFTER DELETE ON documents_vanbanden_hoso
  DEFERRABLE INITIALLY IMMEDIATE
  FOR EACH ROW EXECUTE FUNCTION check_vanbanden_hoso_delete_cross_ref();

CREATE TABLE documents_vanbanden_donvinhan (
    vanbanden_id BIGINT NOT NULL REFERENCES documents_vanbanden (id) ON DELETE CASCADE,
    donvi_id BIGINT NOT NULL REFERENCES organizations_donvi (id) ON DELETE RESTRICT,
    PRIMARY KEY (vanbanden_id, donvi_id)
);

CREATE TABLE documents_vanbanden_nguoinhan (
    vanbanden_id BIGINT NOT NULL REFERENCES documents_vanbanden (id) ON DELETE CASCADE,
    employee_id BIGINT NOT NULL REFERENCES accounts_employee (id) ON DELETE RESTRICT,
    PRIMARY KEY (vanbanden_id, employee_id)
);

-- Tệp đính kèm Văn bản Đến (1-N, Hướng A theo Thầy Duy chốt)
CREATE TABLE documents_vanbanden_attachment (
    id BIGSERIAL PRIMARY KEY,
    document_id BIGINT NOT NULL REFERENCES documents_vanbanden (id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL, -- Tên gốc file (vd: To_trinh_01.pdf)
    path VARCHAR(500) NOT NULL, -- Đường dẫn lưu file trên server/storage
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE, -- Cờ xóa mềm
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    nguoi_tao_id BIGINT REFERENCES accounts_employee (id) ON DELETE SET NULL
);

CREATE INDEX idx_vanbanden_attachment_doc ON documents_vanbanden_attachment (document_id);

CREATE INDEX idx_vanbanden_attachment_deleted ON documents_vanbanden_attachment (is_deleted);

-- =====================================================================
-- 2. VĂN BẢN ĐI (documents_vanbandi)
-- Đã đổi tên cột 'so' thành 'so_thu_tu' theo góp ý của Lê Trí Kiệt (Nhóm 2)
-- Đã bỏ cột 'noi_ban_hanh' và chuyển sang bảng M2M documents_vanbandi_noibanhanh
-- =====================================================================
CREATE TABLE documents_vanbandi (
    id BIGSERIAL PRIMARY KEY,
    nam SMALLINT NOT NULL,
    so_hieu VARCHAR(255) NOT NULL, -- (bỏ cột 'kyhieu' trùng lặp — xem ghi chú đầu file)
    so_thu_tu INTEGER NOT NULL, -- Số thứ tự văn bản đi trong năm
    ngay_ban_hanh TIMESTAMPTZ NOT NULL,
    trich_yeu TEXT NOT NULL,
    ngay_van_ban TIMESTAMPTZ NOT NULL,
    nguoi_ky VARCHAR(255),
    chuc_vu VARCHAR(255),
    hieu_luc hieu_luc_status NOT NULL,
    ngay_het_hieu_luc TIMESTAMPTZ,
    link_thay_the VARCHAR(500),
    ghi_chu TEXT,
    hien_thi BOOLEAN NOT NULL DEFAULT TRUE,
    gui_mail_toan_he_thong BOOLEAN NOT NULL DEFAULT FALSE,
    pham_vi VARCHAR(20) NOT NULL DEFAULT 'NOI_BO', -- [BỎ MẬT] NOI_BO | HAN_CHE
    nguoi_tao_id BIGINT REFERENCES accounts_employee (id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_vanbandi_nam_stt UNIQUE (nam, so_thu_tu), -- Nghị định 30/2020/NĐ-CP: chống trùng số đi trong năm
    CONSTRAINT chk_vanbandi_link_thay_the CHECK (
        hieu_luc <> 'HET_VA_THAY_THE' OR (link_thay_the IS NOT NULL AND BTRIM(link_thay_the) <> '')
    ),
    -- [BỎ MẬT] Phạm vi xem: HAN_CHE chỉ người tạo, người nhận, đơn vị nhận được xem (tầng ứng dụng)
    CONSTRAINT chk_vanbandi_pham_vi CHECK (pham_vi IN ('NOI_BO', 'HAN_CHE')),
    -- [BỎ MẬT] Văn bản hạn chế không được gửi mail toàn hệ thống (thay CHECK B2 của bảng mật cũ)
    CONSTRAINT chk_vanbandi_han_che_khong_mail_toan_he_thong CHECK (pham_vi <> 'HAN_CHE' OR gui_mail_toan_he_thong = FALSE)
);

CREATE TRIGGER trg_vanbandi_updated_at BEFORE UPDATE ON documents_vanbandi
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE INDEX idx_vanbandi_sohieu ON documents_vanbandi (so_hieu);

CREATE INDEX idx_vanbandi_nam ON documents_vanbandi (nam);

CREATE TABLE documents_vanbandi_hoso (
    vanbandi_id BIGINT NOT NULL REFERENCES documents_vanbandi (id) ON DELETE CASCADE,
    hoso_id BIGINT NOT NULL REFERENCES records_hoso (id) ON DELETE RESTRICT,
    PRIMARY KEY (vanbandi_id, hoso_id)
);

CREATE INDEX idx_vanbandi_hoso_hoso ON documents_vanbandi_hoso (hoso_id);

CREATE TABLE documents_vanbandi_danhmuc (
    vanbandi_id BIGINT NOT NULL REFERENCES documents_vanbandi (id) ON DELETE CASCADE,
    loaivanban_id BIGINT NOT NULL REFERENCES records_loaivanban (id) ON DELETE RESTRICT,
    PRIMARY KEY (vanbandi_id, loaivanban_id)
);

CREATE INDEX idx_vanbandi_danhmuc_loai ON documents_vanbandi_danhmuc (loaivanban_id);

-- Toàn vẹn tham chiếu chéo giữa Hồ sơ và Loại văn bản cho Văn bản đi:
-- 1) Khi thêm Loại văn bản, nếu văn bản đã liên kết hồ sơ thì Loại văn bản phải thuộc đúng Hồ sơ đó
CREATE OR REPLACE FUNCTION check_vanbandi_cross_reference()
RETURNS TRIGGER AS
$$

DECLARE
v_hoso_id BIGINT;
BEGIN
SELECT ho_so_id INTO v_hoso_id FROM records_loaivanban WHERE id = NEW.loaivanban_id;
IF EXISTS (SELECT 1 FROM documents_vanbandi_hoso WHERE vanbandi_id = NEW.vanbandi_id) THEN
IF NOT EXISTS (
SELECT 1 FROM documents_vanbandi_hoso
WHERE vanbandi_id = NEW.vanbandi_id AND hoso_id = v_hoso_id
) THEN
RAISE EXCEPTION 'Vi phạm toàn vẹn tham chiếu chéo: Loại văn bản (id=%) thuộc Hồ sơ (id=%), nhưng Văn bản đi (id=%) không liên kết với Hồ sơ này.',
NEW.loaivanban_id, v_hoso_id, NEW.vanbandi_id;
END IF;
END IF;
RETURN NEW;
END;

$$
LANGUAGE plpgsql;

CREATE TRIGGER trg_vanbandi_danhmuc_cross_ref
  BEFORE INSERT OR UPDATE ON documents_vanbandi_danhmuc
  FOR EACH ROW EXECUTE FUNCTION check_vanbandi_cross_reference();

-- 2) Khi xóa liên kết hồ sơ, không cho xóa nếu văn bản vẫn còn chứa loại văn bản thuộc hồ sơ đó
-- An toàn khi xóa văn bản cha (ON DELETE CASCADE): bỏ qua kiểm tra nếu văn bản cha không còn tồn tại
CREATE OR REPLACE FUNCTION check_vanbandi_hoso_delete_cross_ref()
RETURNS TRIGGER AS
$$

BEGIN
-- Nếu văn bản cha không còn tồn tại (đang trong luồng ON DELETE CASCADE của documents_vanbandi), bỏ qua không chặn
IF NOT EXISTS (SELECT 1 FROM documents_vanbandi WHERE id = OLD.vanbandi_id) THEN
RETURN OLD;
END IF;

IF EXISTS (
SELECT 1 FROM documents_vanbandi_danhmuc dm
JOIN records_loaivanban lvb ON dm.loaivanban_id = lvb.id
WHERE dm.vanbandi_id = OLD.vanbandi_id AND lvb.ho_so_id = OLD.hoso_id
) THEN
RAISE EXCEPTION 'Không thể gỡ Hồ sơ (id=%) khỏi Văn bản đi (id=%): văn bản vẫn còn chứa Loại văn bản thuộc Hồ sơ này.',
OLD.hoso_id, OLD.vanbandi_id;
END IF;
RETURN OLD;
END;

$$
LANGUAGE plpgsql;

CREATE CONSTRAINT TRIGGER trg_vanbandi_hoso_del_cross_ref
  AFTER DELETE ON documents_vanbandi_hoso
  DEFERRABLE INITIALLY IMMEDIATE
  FOR EACH ROW EXECUTE FUNCTION check_vanbandi_hoso_delete_cross_ref();

-- Bảng trung gian M2M Nơi ban hành cho Văn bản đi
CREATE TABLE documents_vanbandi_noibanhanh (
    vanbandi_id BIGINT NOT NULL REFERENCES documents_vanbandi (id) ON DELETE CASCADE,
    donvi_id BIGINT NOT NULL REFERENCES organizations_donvi (id) ON DELETE RESTRICT,
    PRIMARY KEY (vanbandi_id, donvi_id)
);

CREATE INDEX idx_vanbandi_noibanhanh_donvi ON documents_vanbandi_noibanhanh (donvi_id);

CREATE TABLE documents_vanbandi_donvinhan (
    vanbandi_id BIGINT NOT NULL REFERENCES documents_vanbandi (id) ON DELETE CASCADE,
    donvi_id BIGINT NOT NULL REFERENCES organizations_donvi (id) ON DELETE RESTRICT,
    PRIMARY KEY (vanbandi_id, donvi_id)
);

CREATE TABLE documents_vanbandi_nguoinhan (
    vanbandi_id BIGINT NOT NULL REFERENCES documents_vanbandi (id) ON DELETE CASCADE,
    employee_id BIGINT NOT NULL REFERENCES accounts_employee (id) ON DELETE RESTRICT,
    PRIMARY KEY (vanbandi_id, employee_id)
);

-- Tệp đính kèm Văn bản Đi (1-N, Hướng A theo Thầy Duy chốt)
CREATE TABLE documents_vanbandi_attachment (
    id BIGSERIAL PRIMARY KEY,
    document_id BIGINT NOT NULL REFERENCES documents_vanbandi (id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    path VARCHAR(500) NOT NULL,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    nguoi_tao_id BIGINT REFERENCES accounts_employee (id) ON DELETE SET NULL
);

CREATE INDEX idx_vanbandi_attachment_doc ON documents_vanbandi_attachment (document_id);

CREATE INDEX idx_vanbandi_attachment_deleted ON documents_vanbandi_attachment (is_deleted);

-- =====================================================================
-- 3. [BỎ MẬT] VĂN BẢN MẬT: đã bỏ. Tài liệu nội bộ hạn chế dùng cột pham_vi = 'HAN_CHE'
-- trên documents_vanbanden / documents_vanbandi.
-- =====================================================================

-- =====================================================================
-- BẢNG PHỤ: LỊCH SỬ NGƯỜI XEM (documents_view_log)
-- Dùng chung cho 2 bảng văn bản (Đến/Đi) qua cặp document_type +
-- document_id (generic relation, cùng cơ chế với signing_request/task_congviec).
-- unique_together(document_type, document_id, user_id) -> mỗi user chỉ giữ
-- 1 bản ghi mới nhất trên 1 văn bản (upsert ở tầng app bằng
-- INSERT ... ON CONFLICT (document_type, document_id, user_id)
-- DO UPDATE SET viewed_at = EXCLUDED.viewed_at).
-- =====================================================================
-- Hierarchical document folders (Django documents migrations 0006 and 0007).
CREATE TABLE documents_folder (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    parent_id BIGINT,
    path VARCHAR(1000) NOT NULL,
    depth INTEGER NOT NULL CONSTRAINT documents_folder_depth_check CHECK (depth >= 0),
    "order" INTEGER NOT NULL CONSTRAINT documents_folder_order_check CHECK ("order" >= 0),
    description TEXT NOT NULL,
    is_local BOOLEAN NOT NULL,
    local_path VARCHAR(1000) NOT NULL,
    created_by_id BIGINT,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT uq_folder_parent_name UNIQUE (parent_id, name),
    CONSTRAINT fk_documents_folder_parent FOREIGN KEY (parent_id)
        REFERENCES documents_folder (id),
    CONSTRAINT fk_documents_folder_created_by FOREIGN KEY (created_by_id)
        REFERENCES accounts_employee (id)
);

CREATE INDEX idx_folder_parent ON documents_folder (parent_id);
CREATE INDEX idx_folder_path ON documents_folder (path);
CREATE INDEX idx_folder_depth ON documents_folder (depth);

CREATE TABLE documents_folder_file (
    id BIGSERIAL PRIMARY KEY,
    file_name VARCHAR(500) NOT NULL,
    file_path VARCHAR(1000) NOT NULL,
    file_size BIGINT NOT NULL CONSTRAINT documents_folder_file_file_size_check CHECK (file_size >= 0),
    file_type VARCHAR(50) NOT NULL,
    description TEXT NOT NULL,
    is_local BOOLEAN NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    folder_id BIGINT NOT NULL,
    uploaded_by_id BIGINT,
    CONSTRAINT fk_documents_folder_file_folder FOREIGN KEY (folder_id)
        REFERENCES documents_folder (id),
    CONSTRAINT fk_documents_folder_file_uploaded_by FOREIGN KEY (uploaded_by_id)
        REFERENCES accounts_employee (id)
);

CREATE INDEX idx_folder_file_folder ON documents_folder_file (folder_id);

CREATE TABLE documents_view_log (
    id BIGSERIAL PRIMARY KEY,
    document_type document_kind NOT NULL,
    document_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL REFERENCES accounts_employee (id) ON DELETE CASCADE,
    viewed_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT uq_viewlog_doc_user UNIQUE (
        document_type,
        document_id,
        user_id
    )
);

CREATE INDEX idx_viewlog_document ON documents_view_log (document_type, document_id);

-- Trigger dọn dẹp Log người xem khi xóa văn bản (Tránh bản ghi mồ côi do Generic Relation):
CREATE OR REPLACE FUNCTION trg_cleanup_viewlog_on_doc_delete()
RETURNS TRIGGER AS $$
BEGIN
    DELETE FROM documents_view_log
    WHERE document_id = OLD.id AND document_type = TG_ARGV[0]::document_kind;
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_del_viewlog_vanbanden AFTER DELETE ON documents_vanbanden
    FOR EACH ROW EXECUTE FUNCTION trg_cleanup_viewlog_on_doc_delete('vanbanden');

CREATE TRIGGER trg_del_viewlog_vanbandi AFTER DELETE ON documents_vanbandi
    FOR EACH ROW EXECUTE FUNCTION trg_cleanup_viewlog_on_doc_delete('vanbandi');

-- =====================================================================
-- BẢNG PHỤ: NHẬT KÝ TRUY CẬP VĂN BẢN HẠN CHẾ (documents_access_log)
-- Chỉ ghi cho văn bản pham_vi = 'HAN_CHE'. Chỉ thêm dòng, không ghi đè (WORM), khác documents_view_log
-- (mỗi người một dòng, dùng cho văn bản nội bộ). Không có FK tới văn bản (generic relation, cùng cơ chế
-- documents_view_log); văn bản HAN_CHE không xóa được nên không phát sinh bản ghi mồ côi.
-- hanh_dong: XEM | TAI_FILE | BI_TU_CHOI (bị chặn quyền, API trả 404) | THEM_NGUOI_XEM | BOT_NGUOI_XEM.
-- user_id: tài khoản thực hiện, lấy từ phiên đăng nhập phía máy chủ. doi_tuong_user_id: người bị thêm/bớt.
-- =====================================================================
CREATE TABLE documents_access_log (
    id BIGSERIAL PRIMARY KEY,
    document_type document_kind NOT NULL,
    document_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL REFERENCES accounts_employee (id) ON DELETE RESTRICT,
    hanh_dong VARCHAR(20) NOT NULL,
    doi_tuong_user_id BIGINT REFERENCES accounts_employee (id) ON DELETE RESTRICT,
    tep_id BIGINT,
    dia_chi_ip VARCHAR(45),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_access_log_hanh_dong CHECK (
        hanh_dong IN ('XEM', 'TAI_FILE', 'BI_TU_CHOI', 'THEM_NGUOI_XEM', 'BOT_NGUOI_XEM')
    ),
    CONSTRAINT chk_access_log_doi_tuong CHECK (
        hanh_dong NOT IN ('THEM_NGUOI_XEM', 'BOT_NGUOI_XEM') OR doi_tuong_user_id IS NOT NULL
    )
);

CREATE INDEX idx_access_log_document ON documents_access_log (document_type, document_id, created_at);
CREATE INDEX idx_access_log_user ON documents_access_log (user_id, created_at);

CREATE OR REPLACE FUNCTION prevent_modify_documents_access_log()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Nhật ký truy cập văn bản hạn chế (documents_access_log id=%) chỉ được thêm, nghiêm cấm sửa hoặc xóa.', OLD.id;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_documents_access_log_immutable
    BEFORE UPDATE OR DELETE ON documents_access_log
    FOR EACH ROW EXECUTE FUNCTION prevent_modify_documents_access_log();

-- MVP: văn bản HAN_CHE không được xóa (chưa có cơ chế xóa mềm); chặn xóa để không mất dấu vết truy cập.
CREATE OR REPLACE FUNCTION prevent_delete_van_ban_han_che()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.pham_vi = 'HAN_CHE' THEN
        RAISE EXCEPTION 'Văn bản hạn chế (id=%) không được xóa.', OLD.id;
    END IF;
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_vanbanden_no_hard_delete_han_che BEFORE DELETE ON documents_vanbanden
    FOR EACH ROW EXECUTE FUNCTION prevent_delete_van_ban_han_che();

CREATE TRIGGER trg_vanbandi_no_hard_delete_han_che BEFORE DELETE ON documents_vanbandi
    FOR EACH ROW EXECUTE FUNCTION prevent_delete_van_ban_han_che();

-- pham_vi bất biến sau khi tạo: không cho hạ HAN_CHE xuống NOI_BO (sẽ lộ văn bản cho quyền view_* và trợ lý AI)
-- và không cho nâng NOI_BO lên HAN_CHE (log xem cũ không đủ chi tiết).
CREATE OR REPLACE FUNCTION prevent_change_pham_vi()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.pham_vi IS DISTINCT FROM OLD.pham_vi THEN
        RAISE EXCEPTION 'Phạm vi văn bản (id=%) không được đổi sau khi tạo.', OLD.id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_vanbanden_pham_vi_bat_bien BEFORE UPDATE OF pham_vi ON documents_vanbanden
    FOR EACH ROW EXECUTE FUNCTION prevent_change_pham_vi();

CREATE TRIGGER trg_vanbandi_pham_vi_bat_bien BEFORE UPDATE OF pham_vi ON documents_vanbandi
    FOR EACH ROW EXECUTE FUNCTION prevent_change_pham_vi();


-- =====================================================================
-- =====================================================================
-- 9. PHÂN HỆ TRÌNH KÝ (signing_*) — ĐỒNG BỘ 100% DJANGO MODEL & CHUẨN HÓA THEO ISSUE #47 (LÊ THANH HẬU & LÊ THÀNH TÀI)
-- Quy mô: 14 bảng vật lý | Khóa ngoại accounts_employee(id), organizations_donvi(id), accounts_position(id)
-- Hỗ trợ đầy đủ: Generic Relation (document_type, document_id), box ký PDF, ủy quyền, outbox nhắc hạn, WORM audit log
-- =====================================================================

-- 9.1. Quy trình trình ký chuẩn mẫu
CREATE TABLE signing_process (
    id BIGSERIAL PRIMARY KEY,
    ma_quy_trinh VARCHAR(50) NOT NULL,
    ten_quy_trinh VARCHAR(255) NOT NULL,
    mo_ta TEXT NOT NULL DEFAULT '',
    phien_ban SMALLINT NOT NULL DEFAULT 1 CHECK (phien_ban >= 0),
    trang_thai VARCHAR(20) NOT NULL DEFAULT 'NHAP',
    pham_vi VARCHAR(20) NOT NULL,
    don_vi_ap_dung_id BIGINT REFERENCES organizations_donvi (id) ON DELETE RESTRICT, -- [P7] bắt buộc khi PHONG_BAN
    -- [6c] Bỏ kieu_ky_mac_dinh: cấp ký luôn tuần tự, song song là nhiều người trong một cấp.
    cau_hinh_nhac_han JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    nguoi_tao_id BIGINT NOT NULL REFERENCES accounts_employee (id) ON DELETE RESTRICT,
    nguoi_cap_nhat_id BIGINT REFERENCES accounts_employee (id) ON DELETE SET NULL,
    CONSTRAINT uq_signing_process_ma_phien_ban UNIQUE (ma_quy_trinh, phien_ban),
    CONSTRAINT chk_signing_process_don_vi_ap_dung CHECK ( -- [P7]
        (pham_vi = 'PHONG_BAN' AND don_vi_ap_dung_id IS NOT NULL)
        OR (pham_vi = 'CONG_TY' AND don_vi_ap_dung_id IS NULL)
    )
);

CREATE INDEX idx_signing_process_nguoi_tao ON signing_process (nguoi_tao_id);
CREATE INDEX idx_signing_process_don_vi_ap_dung ON signing_process (don_vi_ap_dung_id); -- [P7]
CREATE INDEX idx_signing_process_nguoi_cap_nhat ON signing_process (nguoi_cap_nhat_id);

-- 9.2. Cấp ký trong quy trình mẫu
CREATE TABLE signing_process_step (
    id BIGSERIAL PRIMARY KEY,
    quy_trinh_id BIGINT NOT NULL REFERENCES signing_process (id) ON DELETE CASCADE,
    cap_ky SMALLINT NOT NULL CHECK (cap_ky >= 0),
    ten_cap_ky VARCHAR(255) NOT NULL,
    thu_tu SMALLINT NOT NULL CHECK (thu_tu >= 0),
    don_vi_id BIGINT REFERENCES organizations_donvi (id) ON DELETE SET NULL,
    so_gio_xu_ly INTEGER CHECK (so_gio_xu_ly >= 0),
    dang_ap_dung BOOLEAN NOT NULL DEFAULT true,
    ghi_chu TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_signing_process_step_thu_tu UNIQUE (quy_trinh_id, thu_tu)
);

CREATE INDEX idx_signing_process_step_quytrinh ON signing_process_step (quy_trinh_id);

-- 9.3. Danh sách người ký cấu hình sẵn cho cấp ký
-- Issue #47 P1.7: đổi nguoi_ky_id và chuc_vu_id từ SET NULL sang RESTRICT để tránh vi phạm CHECK một-trong-hai khi xóa
CREATE TABLE signing_process_step_signer (
    id BIGSERIAL PRIMARY KEY,
    buoc_quy_trinh_id BIGINT NOT NULL REFERENCES signing_process_step (id) ON DELETE CASCADE,
    nguoi_ky_id BIGINT REFERENCES accounts_employee (id) ON DELETE RESTRICT,
    chuc_vu_id BIGINT REFERENCES accounts_position (id) ON DELETE RESTRICT,
    pham_vi_chuc_vu VARCHAR(20), -- [P7] DON_VI_NGUOI_TAO | DON_VI_CO_DINH | TOAN_CO_QUAN; chỉ dùng khi cấu hình theo chức vụ
    vai_tro_ky VARCHAR(20) NOT NULL DEFAULT 'KY_CHINH',
    chan_ky_chinh BOOLEAN NOT NULL DEFAULT true,
    thu_tu SMALLINT NOT NULL CHECK (thu_tu >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_signing_process_step_signer_mot_doi_tuong CHECK (
        (chuc_vu_id IS NULL AND nguoi_ky_id IS NOT NULL) OR
        (chuc_vu_id IS NOT NULL AND nguoi_ky_id IS NULL)
    )
);

CREATE INDEX idx_signing_process_step_signer_buoc ON signing_process_step_signer (buoc_quy_trinh_id);
CREATE INDEX idx_signing_process_step_signer_nguoi ON signing_process_step_signer (nguoi_ky_id);

-- Chức vụ được phép ký thay cho từng chức vụ của người ký.
CREATE TABLE signing_delegation_role (
    id BIGSERIAL PRIMARY KEY,
    chuc_vu_giao_id BIGINT NOT NULL REFERENCES accounts_position (id) ON DELETE RESTRICT,
    chuc_vu_nhan_id BIGINT NOT NULL REFERENCES accounts_position (id) ON DELETE RESTRICT,
    CONSTRAINT uq_signing_delegation_role UNIQUE (chuc_vu_giao_id, chuc_vu_nhan_id)
);
CREATE INDEX idx_signing_delegation_role_giao ON signing_delegation_role (chuc_vu_giao_id);
CREATE INDEX idx_signing_delegation_role_nhan ON signing_delegation_role (chuc_vu_nhan_id);

-- 9.4. Phiếu yêu cầu trình ký
-- Issue #47 P0.1: Bổ sung document_type document_kind NOT NULL và index (document_type, document_id)
-- Issue #47 P1.9: Cho phép NULL ở phien_ban_van_ban, vi_tri_luu_tep, ma_bam_tai_lieu khi tạo bản nháp
-- Issue #47 P2.12: Bổ sung index signing_request (han_chot)
CREATE TABLE signing_request (
    id BIGSERIAL PRIMARY KEY,
    document_type document_kind, -- [VBTK] Văn bản đi gắn với hồ sơ (Generic Relation); NULL khi văn bản trình ký nhập tay
    document_id BIGINT, -- [VBTK] NULL cùng document_type
    phien_ban_van_ban VARCHAR(50), -- Cho phép NULL ở bản nháp ban đầu
    vi_tri_luu_tep VARCHAR(500), -- Cho phép NULL ở bản nháp ban đầu
    ma_bam_tai_lieu VARCHAR(64), -- Cho phép NULL ở bản nháp ban đầu
    quy_trinh_id BIGINT NOT NULL REFERENCES signing_process (id) ON DELETE RESTRICT,
    phien_ban_quy_trinh SMALLINT NOT NULL CHECK (phien_ban_quy_trinh >= 0),
    -- [6c] Bỏ kieu_ky: cấp ký luôn tuần tự (không còn cách thức ký áp dụng cho toàn yêu cầu).
    trang_thai VARCHAR(20) NOT NULL DEFAULT 'NHAP',
    han_chot TIMESTAMPTZ,
    ngay_gui TIMESTAMPTZ,
    ngay_hoan_thanh TIMESTAMPTZ,
    ngay_tu_choi TIMESTAMPTZ,
    ly_do_tu_choi TEXT NOT NULL DEFAULT '',
    ngay_huy TIMESTAMPTZ,
    ly_do_huy TEXT NOT NULL DEFAULT '',
    ghi_chu TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    nguoi_tao_id BIGINT NOT NULL REFERENCES accounts_employee (id) ON DELETE RESTRICT,
    nguoi_cap_nhat_id BIGINT REFERENCES accounts_employee (id) ON DELETE SET NULL,
    ho_so_goc_id BIGINT REFERENCES signing_request (id) ON DELETE RESTRICT, -- [P7] trình lại sau từ chối trỏ về hồ sơ gốc
    so_hieu_van_ban VARCHAR(100) NOT NULL DEFAULT '', -- [VBTK] số hiệu văn bản trình ký nhập tay (tùy chọn)
    trich_yeu_van_ban TEXT NOT NULL DEFAULT '', -- [VBTK] trích yếu văn bản trình ký nhập tay
    CONSTRAINT chk_signing_request_ma_bam_sha256 CHECK (ma_bam_tai_lieu IS NULL OR ma_bam_tai_lieu ~ '^[0-9a-f]{64}$'),
    CONSTRAINT chk_signing_request_van_ban CHECK ((document_type IS NOT NULL AND document_id IS NOT NULL) OR (document_type IS NULL AND document_id IS NULL AND trich_yeu_van_ban <> ''))
);

CREATE INDEX idx_signing_request_document ON signing_request (document_type, document_id);
CREATE INDEX idx_signing_request_trang_thai ON signing_request (trang_thai);
CREATE INDEX idx_signing_request_nguoi_tao ON signing_request (nguoi_tao_id);
CREATE INDEX idx_signing_request_quy_trinh ON signing_request (quy_trinh_id);
CREATE INDEX idx_signing_request_nguoi_cap_nhat ON signing_request (nguoi_cap_nhat_id);
CREATE INDEX idx_signing_request_hanchot ON signing_request (han_chot); -- Issue #47 P2.12
CREATE INDEX idx_signing_request_ho_so_goc ON signing_request (ho_so_goc_id); -- [P7]
CREATE UNIQUE INDEX uq_signing_completed_doc ON signing_request (document_type, document_id) WHERE (trang_thai = 'HOAN_THANH' AND document_id IS NOT NULL);

-- 9.5. Lượt trình ký (mỗi lần nộp lại tài liệu sinh 1 lượt mới)
-- Issue #47 P1.9: Cho phép NULL ở phien_ban_van_ban; GIỮ NOT NULL cho vi_tri_luu_tep và ma_bam_tai_lieu
CREATE TABLE signing_attempt (
    id BIGSERIAL PRIMARY KEY,
    trinh_ky_id BIGINT NOT NULL REFERENCES signing_request (id) ON DELETE RESTRICT,
    so_luot SMALLINT NOT NULL CHECK (so_luot >= 0),
    phien_ban_van_ban VARCHAR(50), -- Cho phép NULL ở bản nháp ban đầu
    vi_tri_luu_tep VARCHAR(500) NOT NULL, -- Bắt buộc có tệp tài liệu cho lượt trình
    ma_bam_tai_lieu VARCHAR(64) NOT NULL, -- Bắt buộc có mã băm SHA-256
    trang_thai VARCHAR(20) NOT NULL DEFAULT 'NHAP',
    ly_do TEXT NOT NULL DEFAULT '',
    khoa_chong_trung VARCHAR(255) UNIQUE,
    thoi_diem_gui TIMESTAMPTZ,
    thoi_diem_hoan_thanh TIMESTAMPTZ,
    thoi_diem_tu_choi TIMESTAMPTZ,
    thoi_diem_huy TIMESTAMPTZ,
    vi_tri_tep_hoan_tat VARCHAR(500) NOT NULL DEFAULT '',
    ma_bam_tep_hoan_tat VARCHAR(64) NOT NULL DEFAULT '',
    trang_thai_tep_hoan_tat VARCHAR(20), -- [P10] DANG_XU_LY | LOI | THANH_CONG; NULL khi lượt chưa hoàn thành
    loi_tep_hoan_tat VARCHAR(100) NOT NULL DEFAULT '', -- [P10] mã lỗi lần tạo tệp hoàn tất gần nhất
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    nguoi_tao_id BIGINT NOT NULL REFERENCES accounts_employee (id) ON DELETE RESTRICT,
    luot_truoc_id BIGINT REFERENCES signing_attempt (id) ON DELETE RESTRICT,
    nguoi_cap_nhat_id BIGINT REFERENCES accounts_employee (id) ON DELETE SET NULL,
    CONSTRAINT uq_signing_attempt_so_luot UNIQUE (trinh_ky_id, so_luot),
    CONSTRAINT chk_signing_attempt_ma_bam_sha256 CHECK (ma_bam_tai_lieu ~ '^[0-9a-f]{64}$')
);

CREATE INDEX idx_signing_attempt_trinh_ky ON signing_attempt (trinh_ky_id);
CREATE INDEX idx_signing_attempt_nguoi_tao ON signing_attempt (nguoi_tao_id);
CREATE INDEX idx_signing_attempt_luot_truoc ON signing_attempt (luot_truoc_id);
CREATE INDEX idx_signing_attempt_nguoi_cap_nhat ON signing_attempt (nguoi_cap_nhat_id);

-- 9.6. Cấp ký thực tế trong một lượt trình
-- Issue #47 P2.12: Bổ sung index signing_request_step (han_xu_ly)
CREATE TABLE signing_request_step (
    id BIGSERIAL PRIMARY KEY,
    luot_trinh_id BIGINT NOT NULL REFERENCES signing_attempt (id) ON DELETE RESTRICT,
    buoc_quy_trinh_id BIGINT NOT NULL REFERENCES signing_process_step (id) ON DELETE RESTRICT,
    cap_ky SMALLINT NOT NULL CHECK (cap_ky >= 0),
    ten_cap_ky VARCHAR(255) NOT NULL,
    thu_tu SMALLINT NOT NULL CHECK (thu_tu >= 0),
    trang_thai VARCHAR(20) NOT NULL DEFAULT 'CHUA_MO',
    han_xu_ly TIMESTAMPTZ,
    thoi_diem_mo TIMESTAMPTZ,
    thoi_diem_hoan_thanh TIMESTAMPTZ,
    ghi_chu TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_signing_request_step_thu_tu UNIQUE (luot_trinh_id, thu_tu)
);

CREATE INDEX idx_signing_request_step_buoc_quy_trinh ON signing_request_step (buoc_quy_trinh_id);
CREATE INDEX idx_signing_request_step_luot_trinh ON signing_request_step (luot_trinh_id);
CREATE INDEX idx_signing_request_step_hanxuly ON signing_request_step (han_xu_ly); -- Issue #47 P2.12

-- 9.7. Người ký thực tế trong cấp ký (Tọa độ box ký, ảnh chữ ký, ủy quyền)
-- Issue #47 P1.9: Cho phép NULL ở ten_chuc_vu và khoa_chong_trung_thao_tac khi tạo nháp
CREATE TABLE signing_request_step_signer (
    id BIGSERIAL PRIMARY KEY,
    buoc_ky_id BIGINT NOT NULL REFERENCES signing_request_step (id) ON DELETE RESTRICT,
    nguoi_ky_id BIGINT NOT NULL REFERENCES accounts_employee (id) ON DELETE RESTRICT,
    chuc_vu_id BIGINT REFERENCES accounts_position (id) ON DELETE SET NULL,
    ten_nguoi_ky VARCHAR(255) NOT NULL,
    ten_chuc_vu VARCHAR(255), -- Cho phép NULL ở bản nháp ban đầu
    vai_tro_ky VARCHAR(20) NOT NULL,
    chan_ky_chinh BOOLEAN NOT NULL DEFAULT true,
    trang_thai VARCHAR(20) NOT NULL DEFAULT 'CHO_KY',
    thoi_diem_mo TIMESTAMPTZ,
    ngay_ky TIMESTAMPTZ,
    ngay_tu_choi TIMESTAMPTZ,
    ly_do_tu_choi TEXT NOT NULL DEFAULT '',
    chu_ky_hien_hanh_id BIGINT, -- Khóa ngoại trỏ sang signing_signature thêm sau
    uy_quyen_tu_id BIGINT REFERENCES accounts_employee (id) ON DELETE RESTRICT,
    chuc_vu_goc_uy_quyen_id BIGINT REFERENCES accounts_position (id) ON DELETE RESTRICT,
    ly_do_uy_quyen TEXT NOT NULL DEFAULT '',
    ngay_uy_quyen TIMESTAMPTZ,
    trang_ky INTEGER CHECK (trang_ky >= 0),
    toa_do_x NUMERIC(10, 4),
    toa_do_y NUMERIC(10, 4),
    chieu_rong_khung NUMERIC(10, 4),
    chieu_cao_khung NUMERIC(10, 4),
    khoa_chong_trung_thao_tac VARCHAR(255), -- Cho phép NULL ở bản nháp ban đầu
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_signing_request_step_signer_nguoi_ky UNIQUE (buoc_ky_id, nguoi_ky_id),
    CONSTRAINT chk_signing_signer_ly_do_uy_quyen CHECK (uy_quyen_tu_id IS NULL OR NOT (ly_do_uy_quyen = ''))
);

CREATE INDEX idx_signing_request_step_signer_buoc ON signing_request_step_signer (buoc_ky_id);
CREATE INDEX idx_signing_request_step_signer_nguoi ON signing_request_step_signer (nguoi_ky_id);
CREATE INDEX idx_signing_request_step_signer_uy_quyen ON signing_request_step_signer (uy_quyen_tu_id);
CREATE INDEX idx_signing_request_step_signer_chuc_vu_goc ON signing_request_step_signer (chuc_vu_goc_uy_quyen_id);

-- 9.8. Quản lý Khóa ký số (Zero-Knowledge: Backend tuyệt đối không lưu private key)
CREATE TABLE signing_key (
    id BIGSERIAL PRIMARY KEY,
    nguoi_so_huu_id BIGINT NOT NULL REFERENCES accounts_employee (id) ON DELETE RESTRICT,
    ma_khoa VARCHAR(100) NOT NULL UNIQUE,
    dau_van_tay VARCHAR(64) NOT NULL UNIQUE,
    thuat_toan VARCHAR(50) NOT NULL DEFAULT 'Ed25519',
    khoa_cong_khai TEXT NOT NULL,
    trang_thai VARCHAR(20) NOT NULL DEFAULT 'CHO_KICH_HOAT',
    thoi_diem_xac_minh_so_huu TIMESTAMPTZ,
    thoi_diem_kich_hoat TIMESTAMPTZ,
    ngay_hieu_luc TIMESTAMPTZ NOT NULL,
    ngay_het_han TIMESTAMPTZ,
    ngay_thu_hoi TIMESTAMPTZ,
    ghi_chu TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    khoa_thay_the_id BIGINT REFERENCES signing_key (id) ON DELETE RESTRICT,
    CONSTRAINT chk_signing_key_hoat_dong_da_xac_minh CHECK (
        NOT (trang_thai = 'HOAT_DONG') OR thoi_diem_xac_minh_so_huu IS NOT NULL
    )
);

CREATE UNIQUE INDEX uq_signing_key_mot_khoa_hoat_dong ON signing_key (nguoi_so_huu_id) WHERE (trang_thai = 'HOAT_DONG');
CREATE INDEX idx_signing_key_khoa_thay_the ON signing_key (khoa_thay_the_id);
CREATE INDEX idx_signing_key_nguoi_so_huu ON signing_key (nguoi_so_huu_id);

-- 9.8b. [v1] Mở khóa ký bằng PIN (Nhóm 5, Phase 6a) — bảng trạng thái, được phép UPDATE.
-- Không lưu PIN; chỉ lưu hash verifier và mảnh bí mật máy chủ đã mã hóa. Sự kiện PIN ghi vào signing_audit_log.
CREATE TABLE signing_key_unlock (
    id BIGSERIAL PRIMARY KEY,
    khoa_id BIGINT NOT NULL UNIQUE REFERENCES signing_key (id) ON DELETE CASCADE,
    ma_bam_xac_minh_pin TEXT NOT NULL,
    manh_bi_mat_ma_hoa TEXT NOT NULL,
    tham_so_kdf JSONB NOT NULL,
    so_lan_sai INTEGER NOT NULL DEFAULT 0 CHECK (so_lan_sai >= 0),
    khoa_den TIMESTAMPTZ, -- NULL: không bị khóa
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_signing_key_unlock_updated_at BEFORE UPDATE ON signing_key_unlock
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- 9.9. Chữ ký số điện tử (Bảo toàn bằng chứng pháp lý — Bất biến không thể sửa/xóa)
-- Issue #47 P0.3: Chặn DELETE và chặn UPDATE mọi cột, CHỈ CHO PHÉP cập nhật trang_thai_xac_minh và thoi_diem_xac_minh
CREATE TABLE signing_signature (
    id BIGSERIAL PRIMARY KEY,
    luot_trinh_id BIGINT NOT NULL REFERENCES signing_attempt (id) ON DELETE RESTRICT,
    buoc_ky_id BIGINT NOT NULL REFERENCES signing_request_step_signer (id) ON DELETE RESTRICT,
    khoa_ky_id BIGINT NOT NULL REFERENCES signing_key (id) ON DELETE RESTRICT,
    hash_tai_lieu VARCHAR(64) NOT NULL,
    thuat_toan VARCHAR(50) NOT NULL,
    chu_ky_so TEXT NOT NULL,
    ghi_chu_ky TEXT NOT NULL DEFAULT '',
    ky_tre_han BOOLEAN NOT NULL DEFAULT false,
    so_giay_tre INTEGER CHECK (so_giay_tre >= 0),
    ngay_ky TIMESTAMPTZ NOT NULL DEFAULT now(),
    trang_thai_xac_minh VARCHAR(20) NOT NULL DEFAULT 'HOP_LE',
    thoi_diem_xac_minh TIMESTAMPTZ,
    vi_tri_anh_chu_ky VARCHAR(500) NOT NULL DEFAULT '',
    ma_bam_anh_chu_ky VARCHAR(64) NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_signing_signature_hash_sha256 CHECK (hash_tai_lieu ~ '^[0-9a-f]{64}$')
);

CREATE INDEX idx_signing_signature_buoc_ky ON signing_signature (buoc_ky_id);
CREATE INDEX idx_signing_signature_khoa_ky ON signing_signature (khoa_ky_id);
CREATE INDEX idx_signing_signature_luot_trinh ON signing_signature (luot_trinh_id);

-- Gắn FK chu_ky_hien_hanh_id trên signing_request_step_signer trỏ tới signing_signature
ALTER TABLE signing_request_step_signer
    ADD CONSTRAINT fk_signer_chu_ky_hien_hanh
    FOREIGN KEY (chu_ky_hien_hanh_id) REFERENCES signing_signature (id) ON DELETE SET NULL;

CREATE INDEX idx_signing_request_step_signer_chuky ON signing_request_step_signer (chu_ky_hien_hanh_id);

-- Trigger bảo vệ chữ ký số: Chặn tuyệt đối xóa chữ ký và chặn sửa đổi (trừ kết quả xác minh)
CREATE OR REPLACE FUNCTION prevent_delete_or_tamper_signing_signature()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'Bảo toàn bằng chứng pháp lý: Chữ ký số điện tử (signing_signature id=%) là bất biến và không thể xóa khỏi CSDL.', OLD.id;
    ELSIF TG_OP = 'UPDATE' THEN
        IF (to_jsonb(OLD) - 'trang_thai_xac_minh' - 'thoi_diem_xac_minh')
           IS DISTINCT FROM
           (to_jsonb(NEW) - 'trang_thai_xac_minh' - 'thoi_diem_xac_minh') THEN
            RAISE EXCEPTION 'Bảo toàn bằng chứng pháp lý: Không được phép sửa đổi thông tin cốt lõi của chữ ký số (signing_signature id=%). Chỉ cho phép cập nhật kết quả xác minh.', OLD.id;
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_signing_signature_immutable
    BEFORE UPDATE OR DELETE ON signing_signature
    FOR EACH ROW EXECUTE FUNCTION prevent_delete_or_tamper_signing_signature();

-- 9.10. Bằng chứng tổng hợp (Manifest Canonical) của attempt sau khi hoàn tất ký
-- Issue #47 P0.2: Kiểm tra trang_thai = 'DA_CHOT' (hoặc CHOT/FINAL)
-- Issue #47 P0.3: Chặn UPDATE khi DA_CHOT
-- Issue #47 P1.9: Cho phép NULL ở vi_tri_luu khi tạo nháp
CREATE TABLE signing_manifest (
    id BIGSERIAL PRIMARY KEY,
    luot_trinh_id BIGINT NOT NULL REFERENCES signing_attempt (id) ON DELETE RESTRICT,
    phien_ban_bang_chung SMALLINT NOT NULL DEFAULT 1 CHECK (phien_ban_bang_chung >= 0),
    noi_dung_chuan_hoa JSONB NOT NULL,
    ma_bam_bang_chung VARCHAR(64) NOT NULL,
    vi_tri_luu VARCHAR(500), -- Cho phép NULL ở bản nháp ban đầu
    trang_thai VARCHAR(20) NOT NULL DEFAULT 'NHAP',
    thoi_diem_chot TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    nguoi_tao_id BIGINT NOT NULL REFERENCES accounts_employee (id) ON DELETE RESTRICT,
    CONSTRAINT chk_signing_manifest_ma_bam_sha256 CHECK (ma_bam_bang_chung ~ '^[0-9a-f]{64}$')
);

CREATE INDEX idx_signing_manifest_nguoi_tao ON signing_manifest (nguoi_tao_id);
CREATE INDEX idx_signing_manifest_luot_trinh ON signing_manifest (luot_trinh_id);

-- Trigger bảo vệ bằng chứng: Chặn xóa và chặn sửa manifest đã chốt (DA_CHOT / CHOT / FINAL)
CREATE OR REPLACE FUNCTION protect_final_manifest()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        IF OLD.trang_thai IN ('DA_CHOT', 'CHOT', 'FINAL') THEN
            RAISE EXCEPTION 'Bảo toàn bằng chứng pháp lý: Không thể xóa manifest số đã chốt (signing_manifest id=%, phien_ban=%).', OLD.id, OLD.phien_ban_bang_chung;
        END IF;
        RETURN OLD;
    ELSIF TG_OP = 'UPDATE' THEN
        IF OLD.trang_thai IN ('DA_CHOT', 'CHOT', 'FINAL') THEN
            RAISE EXCEPTION 'Bảo toàn bằng chứng pháp lý: Manifest số đã chốt (DA_CHOT) là bất biến và không thể sửa đổi (signing_manifest id=%).', OLD.id;
        END IF;
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_signing_manifest_protect
    BEFORE UPDATE OR DELETE ON signing_manifest
    FOR EACH ROW EXECUTE FUNCTION protect_final_manifest();

-- Trigger bảo vệ signing_attempt: Chặn xóa cứng attempt đã kích hoạt hoặc đã có chữ ký/manifest
CREATE OR REPLACE FUNCTION prevent_delete_signing_attempt()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.trang_thai <> 'NHAP' THEN
        RAISE EXCEPTION 'Bảo toàn bằng chứng pháp lý: Không thể xóa lượt trình ký (signing_attempt id=%) đã kích hoạt (trạng thái: %).', OLD.id, OLD.trang_thai;
    END IF;
    IF EXISTS (SELECT 1 FROM signing_manifest WHERE luot_trinh_id = OLD.id) THEN
        RAISE EXCEPTION 'Bảo toàn bằng chứng pháp lý: Lượt trình ký (id=%) đã có manifest số, không thể xóa.', OLD.id;
    END IF;
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_signing_attempt_prevent_delete
    BEFORE DELETE ON signing_attempt
    FOR EACH ROW EXECUTE FUNCTION prevent_delete_signing_attempt();

-- 9.11. Luồng yêu cầu chỉnh sửa trong quá trình trình ký
-- Issue #47 P1.6: Đổi ON DELETE CASCADE sang RESTRICT để bảo toàn lịch sử yêu cầu chỉnh sửa
CREATE TABLE signing_change_thread (
    id BIGSERIAL PRIMARY KEY,
    luot_trinh_id BIGINT NOT NULL REFERENCES signing_attempt (id) ON DELETE RESTRICT,
    nguoi_yeu_cau_id BIGINT NOT NULL REFERENCES accounts_employee (id) ON DELETE RESTRICT,
    tieu_de VARCHAR(255) NOT NULL,
    ly_do TEXT NOT NULL,
    trang_thai VARCHAR(20) NOT NULL DEFAULT 'DANG_MO',
    thoi_diem_giai_quyet TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_signing_change_thread_luot_trinh ON signing_change_thread (luot_trinh_id);
CREATE INDEX idx_signing_change_thread_nguoi_yeu_cau ON signing_change_thread (nguoi_yeu_cau_id);

-- 9.12. Tin nhắn trao đổi chỉnh sửa
-- Issue #47 P1.6: Đổi ON DELETE CASCADE sang RESTRICT để bảo toàn lịch sử trao đổi
CREATE TABLE signing_change_message (
    id BIGSERIAL PRIMARY KEY,
    yeu_cau_sua_id BIGINT NOT NULL REFERENCES signing_change_thread (id) ON DELETE RESTRICT,
    nguoi_viet_id BIGINT NOT NULL REFERENCES accounts_employee (id) ON DELETE RESTRICT,
    noi_dung TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_signing_change_message_nguoi_viet ON signing_change_message (nguoi_viet_id);
CREATE INDEX idx_signing_change_message_yeu_cau_sua ON signing_change_message (yeu_cau_sua_id);

-- 9.13. Nhật ký kiểm toán trình ký (Audit Trail)
-- Issue #47 P0.3: Chặn cả UPDATE và DELETE (chuẩn WORM - Write Once, Read Many)
-- Issue #47 P0.4: Đổi 3 FK sang ON DELETE RESTRICT (tránh UPDATE ngầm sang NULL làm mất dấu vết)
-- Issue #47 P1.8: dia_chi_ip cho phép NULL, bỏ giá trị mặc định '127.0.0.1'
CREATE TABLE signing_audit_log (
    id BIGSERIAL PRIMARY KEY,
    trinh_ky_id BIGINT REFERENCES signing_request (id) ON DELETE RESTRICT,
    luot_trinh_id BIGINT REFERENCES signing_attempt (id) ON DELETE RESTRICT,
    buoc_ky_id BIGINT REFERENCES signing_request_step_signer (id) ON DELETE RESTRICT,
    loai_doi_tuong VARCHAR(50) NOT NULL,
    ma_doi_tuong BIGINT NOT NULL,
    nguoi_thuc_hien_id BIGINT NOT NULL REFERENCES accounts_employee (id) ON DELETE RESTRICT,
    hanh_dong VARCHAR(50) NOT NULL,
    trang_thai_truoc VARCHAR(20) NOT NULL DEFAULT '',
    trang_thai_sau VARCHAR(20) NOT NULL DEFAULT '',
    chi_tiet TEXT NOT NULL DEFAULT '',
    du_lieu_kem_theo JSONB,
    dia_chi_ip VARCHAR(45), -- Cho phép NULL, bỏ mặc định 127.0.0.1
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_signing_audit_log_luong_ky_co_trinh_ky CHECK (
        NOT (loai_doi_tuong IN ('signing_request', 'signing_attempt', 'signing_request_step_signer', 'signing_signature')) OR trinh_ky_id IS NOT NULL
    )
);

CREATE INDEX idx_signing_audit_log_luot_trinh ON signing_audit_log (luot_trinh_id);
CREATE INDEX idx_signing_audit_log_nguoi_thuc_hien ON signing_audit_log (nguoi_thuc_hien_id);
CREATE INDEX idx_signing_audit_log_trinh_ky ON signing_audit_log (trinh_ky_id);
CREATE INDEX idx_signing_audit_log_buoc_ky ON signing_audit_log (buoc_ky_id);

-- Trigger bảo vệ nhật ký kiểm toán: WORM (Write Once, Read Many) - Chặn cả UPDATE và DELETE
CREATE OR REPLACE FUNCTION prevent_modify_signing_audit_log()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Bảo toàn bằng chứng pháp lý: Nhật ký kiểm toán (signing_audit_log id=%) tuân thủ chuẩn WORM, nghiêm cấm mọi hành vi sửa đổi hoặc xóa.', OLD.id;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_signing_audit_log_immutable
    BEFORE UPDATE OR DELETE ON signing_audit_log
    FOR EACH ROW EXECUTE FUNCTION prevent_modify_signing_audit_log();

-- 9.14. Thông báo trình ký (Outbox nhắc việc & gửi lại)
CREATE TABLE signing_notification (
    id BIGSERIAL PRIMARY KEY,
    trinh_ky_id BIGINT NOT NULL REFERENCES signing_request (id) ON DELETE CASCADE,
    buoc_ky_id BIGINT REFERENCES signing_request_step_signer (id) ON DELETE CASCADE,
    nguoi_nhan_id BIGINT NOT NULL REFERENCES accounts_employee (id) ON DELETE RESTRICT,
    kenh VARCHAR(20) NOT NULL,
    loai_thong_bao VARCHAR(50) NOT NULL,
    trang_thai VARCHAR(20) NOT NULL DEFAULT 'CHO_GUI',
    hen_gio_gui TIMESTAMPTZ,
    khoa_chong_gui_trung VARCHAR(255) NOT NULL UNIQUE,
    so_lan_gui_lai INTEGER NOT NULL DEFAULT 0 CHECK (so_lan_gui_lai >= 0),
    thoi_diem_gui TIMESTAMPTZ,
    loi_gui TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_signing_notif_outbox ON signing_notification (trang_thai, hen_gio_gui);
CREATE INDEX idx_signing_notification_nguoi_nhan ON signing_notification (nguoi_nhan_id);
CREATE INDEX idx_signing_notification_trinh_ky ON signing_notification (trinh_ky_id);
CREATE INDEX idx_signing_notification_buoc_ky ON signing_notification (buoc_ky_id);

-- =====================================================================
-- 10. QUẢN LÝ CÔNG VIỆC (task_*)
-- =====================================================================
CREATE TABLE task_congviec (
    id BIGSERIAL PRIMARY KEY,
    noi_dung TEXT NOT NULL,
    ngay_tao_cv DATE NOT NULL,
    ngay_xu_ly DATE NOT NULL, -- hạn xử lý
    yeu_cau_xu_ly TEXT NOT NULL,
    nguoi_tao_id BIGINT NOT NULL REFERENCES accounts_employee (id) ON DELETE RESTRICT,
    document_type document_kind, -- văn bản liên quan (có thể trống)
    document_id BIGINT,
    hien_thi BOOLEAN NOT NULL DEFAULT TRUE,
    opened_at TIMESTAMPTZ,
    opened_by BIGINT REFERENCES accounts_employee (id) ON DELETE SET NULL,
    approved_at TIMESTAMPTZ,
    approved_by BIGINT REFERENCES accounts_employee (id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_task_document CHECK (
        (
            document_type IS NULL
            AND document_id IS NULL
        )
        OR (
            document_type IS NOT NULL
            AND document_id IS NOT NULL
        )
    ),
    -- [Nhóm 6] Hạn xử lý không trước ngày tạo (trước đó chỉ kiểm ở tầng ứng dụng)
    CONSTRAINT chk_task_due_after_created CHECK (ngay_xu_ly >= ngay_tao_cv)
);

CREATE TRIGGER trg_congviec_updated_at BEFORE UPDATE ON task_congviec
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Chỉ mục phức hợp hỗ trợ tra cứu công việc theo quan hệ đa hình với văn bản liên quan
CREATE INDEX IF NOT EXISTS idx_task_congviec_document ON task_congviec (document_type, document_id);
-- Trạng thái (Chờ xử lý/Đang xử lý/Chờ duyệt/Hoàn thành/Chưa hoàn thành/Quá hạn)
-- là giá trị TÍNH TOÁN ở tầng ứng dụng dựa trên ngay_xu_ly/opened_at/approved_at,
-- KHÔNG lưu cột riêng — đúng theo ghi chú gốc trong tài liệu.

CREATE TABLE task_participant (
    id BIGSERIAL PRIMARY KEY,
    cong_viec BIGINT NOT NULL REFERENCES task_congviec (id) ON DELETE CASCADE,
    can_bo BIGINT NOT NULL REFERENCES accounts_employee (id) ON DELETE RESTRICT,
    vai_tro task_vaitro NOT NULL,
    CONSTRAINT uq_task_participant UNIQUE (cong_viec, can_bo),
    CONSTRAINT chk_task_participant_role CHECK (
        vai_tro IN (
            'CHU_TRI',
            'CHI_DAO',
            'THAM_GIA'
        )
    )
);

CREATE INDEX idx_participant_congviec ON task_participant (cong_viec);
-- [Nhóm 6] Mỗi công việc có tối đa một chủ trì (đủ một chủ trì kiểm ở tầng ứng dụng)
CREATE UNIQUE INDEX uq_task_participant_one_host ON task_participant (cong_viec) WHERE vai_tro = 'CHU_TRI';

-- Bảng liên kết Many-to-Many giữa Công việc và Đơn vị/Phòng ban (theo chỉ đạo của GVHD ngày 25/09/2026)
CREATE TABLE task_congviec_donvi (
    id BIGSERIAL PRIMARY KEY,
    cong_viec BIGINT NOT NULL REFERENCES task_congviec (id) ON DELETE CASCADE,
    don_vi BIGINT NOT NULL REFERENCES organizations_donvi (id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_task_congviec_donvi UNIQUE (cong_viec, don_vi)
);

CREATE INDEX idx_task_donvi_congviec ON task_congviec_donvi (cong_viec);

CREATE INDEX idx_task_donvi_donvi ON task_congviec_donvi (don_vi);

CREATE TABLE task_comment (
    id BIGSERIAL PRIMARY KEY,
    cong_viec BIGINT NOT NULL REFERENCES task_congviec (id) ON DELETE CASCADE,
    nguoi_ghi BIGINT NOT NULL REFERENCES accounts_employee (id) ON DELETE RESTRICT,
    noi_dung TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_comment_congviec ON task_comment (cong_viec);

-- File bằng chứng hoàn thành và file trong ý kiến (chuẩn hóa 9 cột theo chỉ đạo GVHD & Phan Tạ Hữu Đức Nhóm 6)
CREATE TABLE task_attachment (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,                                     -- Tên file gốc người dùng tải lên
    path VARCHAR(500) NOT NULL,                                     -- Đường dẫn lưu file trên máy chủ
    cong_viec_id BIGINT NOT NULL REFERENCES task_congviec (id) ON DELETE CASCADE,
    y_kien_id BIGINT REFERENCES task_comment (id) ON DELETE CASCADE, -- Trống nếu là file giao việc ban đầu
    loai task_attachment_loai NOT NULL,                             -- GIAO_VIEC hoặc BANG_CHUNG hoàn thành
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,                      -- Xóa mềm (soft-delete) theo chuẩn GVHD
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),                -- Thời điểm tải lên
    nguoi_tao_id BIGINT NOT NULL REFERENCES accounts_employee (id) ON DELETE RESTRICT, -- Người tải file
    -- [Nhóm 6] File bằng chứng phải gắn một ý kiến; file giao việc ban đầu thì không
    CONSTRAINT chk_task_attachment_evidence CHECK (
        (loai = 'GIAO_VIEC' AND y_kien_id IS NULL)
        OR (loai = 'BANG_CHUNG' AND y_kien_id IS NOT NULL)
    )
);

CREATE INDEX idx_task_attachment_congviec ON task_attachment (cong_viec_id);
CREATE INDEX idx_task_attachment_deleted ON task_attachment (is_deleted);

-- =====================================================================
-- 13. PHÒNG HỌP, SINH NHẬT & NHẬT KÝ EMAIL (meetings_*, birthdays_*)
-- =====================================================================
CREATE TABLE meetings_meetingroom (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    location VARCHAR(200) NOT NULL,
    capacity INTEGER NOT NULL CHECK (capacity > 0),
    amenities TEXT,
    is_public BOOLEAN NOT NULL DEFAULT TRUE, -- Hiển thị công khai cho CBNV đặt (nếu False chỉ Admin/Lễ tân thấy)
    trang_thai meetingroom_status NOT NULL DEFAULT 'AVAILABLE',
    ghi_chu TEXT, -- Ghi chú thiết bị, hướng dẫn sử dụng
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_meetingroom_updated_at BEFORE UPDATE ON meetings_meetingroom
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE meetings_meetingbooking (
    id BIGSERIAL PRIMARY KEY,
    room_id BIGINT NOT NULL REFERENCES meetings_meetingroom (id) ON DELETE RESTRICT,
    organizer_id BIGINT NOT NULL REFERENCES accounts_employee (id) ON DELETE RESTRICT,
    department_id BIGINT REFERENCES organizations_donvi (id) ON DELETE SET NULL,
    title VARCHAR(255) NOT NULL,
    date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    attendees_count INTEGER NOT NULL DEFAULT 1 CHECK (attendees_count > 0),
    purpose TEXT,
    trang_thai meetingbooking_status NOT NULL DEFAULT 'CONFIRMED',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_booking_time CHECK (end_time > start_time)
);

CREATE INDEX idx_booking_room_date ON meetings_meetingbooking (room_id, date);
-- Chống trùng lịch cùng phòng cùng khung giờ ở tầng DB (yêu cầu extension btree_gist,
-- có sẵn trong contrib của PostgreSQL — hầu hết managed DB đều cho phép CREATE EXTENSION này).
CREATE EXTENSION IF NOT EXISTS btree_gist;

ALTER TABLE meetings_meetingbooking
ADD CONSTRAINT excl_room_time EXCLUDE USING gist (
    room_id
    WITH
        =,
        tsrange (
            date + start_time,
            date + end_time
        )
    WITH
        &&
)
WHERE (trang_thai <> 'CANCELLED');

CREATE TABLE birthdays_birthdaywish (
    id BIGSERIAL PRIMARY KEY,
    employee_id BIGINT NOT NULL REFERENCES accounts_employee (id) ON DELETE CASCADE,
    sender_name VARCHAR(150) NOT NULL,
    message TEXT NOT NULL,
    card_template VARCHAR(50) NOT NULL DEFAULT 'GOLDEN',
    is_anonymous BOOLEAN NOT NULL DEFAULT FALSE,
    trang_thai birthdaywish_status NOT NULL DEFAULT 'APPROVED',
    sticker_url VARCHAR(500),
    likes_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_birthdaywish_updated_at BEFORE UPDATE ON birthdays_birthdaywish
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE INDEX idx_birthdaywish_employee ON birthdays_birthdaywish (employee_id);

CREATE TABLE birthdays_birthdayemaillog (
    id BIGSERIAL PRIMARY KEY,
    employee_id BIGINT NOT NULL REFERENCES accounts_employee (id) ON DELETE CASCADE,
    sent_date DATE NOT NULL,
    sent_at TIMESTAMPTZ NOT NULL,
    recipient_email VARCHAR(254) NOT NULL,
    subject VARCHAR(255) NOT NULL,
    card_template VARCHAR(50) NOT NULL DEFAULT 'GOLDEN',
    trang_thai emaillog_status NOT NULL DEFAULT 'PENDING',
    error_message TEXT,
    retry_count INTEGER NOT NULL DEFAULT 0,
    next_retry_at TIMESTAMPTZ, -- Hẹn thời điểm thử lại tiếp theo cho Celery worker
    smtp_response_code VARCHAR(50),
    opened_at TIMESTAMPTZ,
    clicked_count INTEGER NOT NULL DEFAULT 0,
    email_provider VARCHAR(50),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_emaillog_employee_date UNIQUE (employee_id, sent_date)
);

CREATE TRIGGER trg_emaillog_updated_at BEFORE UPDATE ON birthdays_birthdayemaillog
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

COMMIT;

-- =====================================================================
-- SEED DATA: Cơ cấu tổ chức thực tế (Khối/Khu vực cấp 1 + Đơn vị cấp 2)
-- Nguồn: Mục 11 tài liệu đặc tả — đây là dữ liệu danh mục tổ chức thật
-- của doanh nghiệp, không phải dữ liệu cá nhân/mock, phù hợp để seed.
-- =====================================================================
BEGIN;

-- 1) Chèn các Khối/Khu vực (Cấp 1) — không trùng lặp (Idempotent)
-- thu_tu_hien_thi = vị trí của khối trong danh sách liệt kê (WITH ORDINALITY), không phụ thuộc collation.
INSERT INTO
    organizations_khoi (ten, thu_tu_hien_thi)
SELECT t.khoi, t.vi_tri::INTEGER
FROM unnest(
    ARRAY[
        'HỘI ĐỒNG QUẢN TRỊ',
        'VĂN PHÒNG HỘI ĐỒNG QUẢN TRỊ',
        'BAN TỔNG GIÁM ĐỐC',
        'VĂN PHÒNG BAN ĐIỀU HÀNH TẠI TP.HCM & HÀ NỘI',
        'KHỐI KINH DOANH',
        'KHỐI NGHIỆP VỤ',
        'KHỐI HỖ TRỢ',
        'KHỐI QUẢN LÝ RỦI RO',
        'KHỐI TÀI CHÍNH',
        'KHỐI KẾ TOÁN',
        'VĂN PHÒNG 2',
        'KHU VỰC THÀNH PHỐ HỒ CHÍ MINH',
        'KHU VỰC MIỀN BẮC',
        'KHU VỰC MIỀN TRUNG TÂY NGUYÊN',
        'KHU VỰC ĐÔNG NAM BỘ',
        'GIÁM ĐỊNH VÙNG'
    ]
) WITH ORDINALITY AS t (khoi, vi_tri)
WHERE
    NOT EXISTS (
        SELECT 1
        FROM organizations_khoi
    )
ORDER BY t.vi_tri;

-- 2) Chèn Đơn vị/phòng ban (Cấp 2), gán khoi_id theo tên Khối tương ứng
INSERT INTO
    organizations_donvi (khoi_id, ten, stt_uu_tien)
-- stt_uu_tien = vị trí của đơn vị trong danh sách liệt kê (cột vi_tri), không phụ thuộc collation.
SELECT k.id, x.don_vi, x.vi_tri
FROM (
        VALUES (
                'HỘI ĐỒNG QUẢN TRỊ', 'Hội đồng quản trị', 1), (
                'HỘI ĐỒNG QUẢN TRỊ', 'Ban kiểm toán nội bộ', 2), (
                'VĂN PHÒNG HỘI ĐỒNG QUẢN TRỊ', 'Văn phòng hội đồng quản trị', 3), (
                'BAN TỔNG GIÁM ĐỐC', 'Ban tổng giám đốc', 4), (
                'BAN TỔNG GIÁM ĐỐC', 'Giám đốc vùng', 5), (
                'VĂN PHÒNG BAN ĐIỀU HÀNH TẠI TP.HCM & HÀ NỘI', 'Văn phòng ban điều hành', 6), (
                'KHỐI KINH DOANH', 'Ban khách hàng doanh nghiệp', 7), (
                'KHỐI KINH DOANH', 'Ban khách hàng qua môi giới', 8), (
                'KHỐI KINH DOANH', 'Ban Bancassurance', 9), (
                'KHỐI KINH DOANH', 'Ban khách hàng cá nhân', 10), (
                'KHỐI KINH DOANH', 'Ban chăm sóc khách hàng ĐT', 11), (
                'KHỐI KINH DOANH', 'Ban dự án phát triển sản phẩm liên kết với các công ty dịch vụ viễn thông', 12), (
                'KHỐI KINH DOANH', 'Ban dự án lớn', 13), (
                'KHỐI KINH DOANH', 'Ban dự án khách hàng qua đại lý', 14), (
                'KHỐI NGHIỆP VỤ', 'Ban bảo hiểm con người', 15), (
                'KHỐI NGHIỆP VỤ', 'Ban bảo hiểm tài sản kỹ thuật', 16), (
                'KHỐI NGHIỆP VỤ', 'Ban tái bảo hiểm', 17), (
                'KHỐI NGHIỆP VỤ', 'Ban bảo hiểm xe cơ giới', 18), (
                'KHỐI NGHIỆP VỤ', 'Ban bảo hiểm hàng hải, hàng không, dầu khí, năng lượng', 19), (
                'KHỐI HỖ TRỢ', 'Lãnh đạo khối', 20), (
                'KHỐI HỖ TRỢ', 'Ban hành chính quản trị', 21), ('KHỐI HỖ TRỢ', 'Ban nhân sự', 22), ('KHỐI HỖ TRỢ', 'Ban pháp chế', 23), (
                'KHỐI HỖ TRỢ', 'Ban công nghệ thông tin', 24), (
                'KHỐI HỖ TRỢ', 'Ban truyền thông và marketing', 25), (
                'KHỐI QUẢN LÝ RỦI RO', 'Ban quản lý rủi ro và tuân thủ', 26), (
                'KHỐI TÀI CHÍNH', 'Ban đầu tư', 27), (
                'KHỐI TÀI CHÍNH', 'Ban tài chính kế hoạch', 28), (
                'KHỐI TÀI CHÍNH', 'Ban dự án MIS', 29), (
                'KHỐI KẾ TOÁN', 'Lãnh đạo khối', 30), ('KHỐI KẾ TOÁN', 'Ban kế toán', 31), ('VĂN PHÒNG 2', 'Văn phòng 2', 32), (
                'KHU VỰC THÀNH PHỐ HỒ CHÍ MINH', 'Sở giao dịch Bảo Long', 33), (
                'KHU VỰC THÀNH PHỐ HỒ CHÍ MINH', 'Bảo Long TP.HCM', 34), (
                'KHU VỰC THÀNH PHỐ HỒ CHÍ MINH', 'Bảo Long Sài Gòn', 35), (
                'KHU VỰC THÀNH PHỐ HỒ CHÍ MINH', 'Bảo Long Gia Định', 36), (
                'KHU VỰC THÀNH PHỐ HỒ CHÍ MINH', 'Bảo Long Bến Thành', 37), (
                'KHU VỰC THÀNH PHỐ HỒ CHÍ MINH', 'Bảo Long Nam Sài Gòn', 38), (
                'KHU VỰC THÀNH PHỐ HỒ CHÍ MINH', 'Bảo Long Tân Sơn Nhất', 39), (
                'KHU VỰC THÀNH PHỐ HỒ CHÍ MINH', 'Bảo Long Đông Sài Gòn', 40), (
                'KHU VỰC THÀNH PHỐ HỒ CHÍ MINH', 'Bảo Long Đông Phương', 41), (
                'KHU VỰC THÀNH PHỐ HỒ CHÍ MINH', 'Trung tâm kinh doanh Thủ Thiêm', 42), (
                'KHU VỰC MIỀN BẮC', 'Bảo Long Hà Nội', 43), (
                'KHU VỰC MIỀN BẮC', 'Bảo Long Thủ Đô', 44), (
                'KHU VỰC MIỀN BẮC', 'Bảo Long Thăng Long', 45), (
                'KHU VỰC MIỀN BẮC', 'Bảo Long Thái Nguyên', 46), (
                'KHU VỰC MIỀN BẮC', 'Bảo Long Quảng Ninh', 47), (
                'KHU VỰC MIỀN BẮC', 'Bảo Long Hải Phòng', 48), (
                'KHU VỰC MIỀN BẮC', 'Bảo Long Phú Thọ', 49), (
                'KHU VỰC MIỀN BẮC', 'Bảo Long Bắc Ninh', 50), (
                'KHU VỰC MIỀN BẮC', 'Bảo Long Hải Dương', 51), (
                'KHU VỰC MIỀN BẮC', 'Bảo Long Nam Định', 52), (
                'KHU VỰC MIỀN BẮC', 'Bảo Long Vĩnh Phúc', 53), (
                'KHU VỰC MIỀN BẮC', 'Bảo Long Đông Hải', 54), (
                'KHU VỰC MIỀN BẮC', 'Sở giao dịch miền Bắc', 55), (
                'KHU VỰC MIỀN BẮC', 'Bảo Long Ninh Bình', 56), (
                'KHU VỰC MIỀN BẮC', 'Bảo Long Thái Bình', 57), (
                'KHU VỰC MIỀN BẮC', 'Bảo Long Đông Đô', 58), (
                'KHU VỰC MIỀN BẮC', 'Bảo Long Thanh Hóa', 59), (
                'KHU VỰC MIỀN TRUNG TÂY NGUYÊN', 'Bảo Long KV Tây Nguyên (Daklak)', 60), (
                'KHU VỰC MIỀN TRUNG TÂY NGUYÊN', 'Bảo Long Phú Yên', 61), (
                'KHU VỰC MIỀN TRUNG TÂY NGUYÊN', 'Bảo Long Đà Nẵng', 62), (
                'KHU VỰC MIỀN TRUNG TÂY NGUYÊN', 'Bảo Long Trung Bộ (Huế)', 63), (
                'KHU VỰC MIỀN TRUNG TÂY NGUYÊN', 'Bảo Long Bắc Trung Bộ (Nghệ An)', 64), (
                'KHU VỰC MIỀN TRUNG TÂY NGUYÊN', 'Bảo Long Khánh Hòa', 65), (
                'KHU VỰC MIỀN TRUNG TÂY NGUYÊN', 'Bảo Long Bình Định', 66), (
                'KHU VỰC MIỀN TRUNG TÂY NGUYÊN', 'Bảo Long Bình Thuận', 67), (
                'KHU VỰC MIỀN TRUNG TÂY NGUYÊN', 'Bảo Long Quảng Ngãi', 68), (
                'KHU VỰC MIỀN TRUNG TÂY NGUYÊN', 'Bảo Long Gia Lai', 69), (
                'KHU VỰC MIỀN TRUNG TÂY NGUYÊN', 'Bảo Long Lâm Đồng', 70), (
                'KHU VỰC MIỀN TRUNG TÂY NGUYÊN', 'Bảo Long Quảng Bình', 71), (
                'KHU VỰC MIỀN TRUNG TÂY NGUYÊN', 'Trung tâm kinh doanh Sông Hàn', 72), (
                'KHU VỰC ĐÔNG NAM BỘ', 'Bảo Long Bình Dương', 73), (
                'KHU VỰC ĐÔNG NAM BỘ', 'Bảo Long Vũng Tàu', 74), (
                'KHU VỰC ĐÔNG NAM BỘ', 'Bảo Long Đồng Nai', 75), (
                'KHU VỰC ĐÔNG NAM BỘ', 'Bảo Long Tây Ninh', 76), (
                'KHU VỰC ĐÔNG NAM BỘ', 'Bảo Long Long An', 77), (
                'KHU VỰC ĐÔNG NAM BỘ', 'Bảo Long Cần Thơ', 78), (
                'KHU VỰC ĐÔNG NAM BỘ', 'Bảo Long Cà Mau', 79), (
                'KHU VỰC ĐÔNG NAM BỘ', 'Bảo Long Kiên Giang', 80), (
                'KHU VỰC ĐÔNG NAM BỘ', 'Bảo Long Đồng Tháp', 81), (
                'GIÁM ĐỊNH VÙNG', 'Giám định vùng', 82)
    ) AS x (khoi, don_vi, vi_tri)
    JOIN organizations_khoi k ON k.ten = x.khoi
WHERE
    NOT EXISTS (
        SELECT 1
        FROM organizations_donvi
    )
ORDER BY x.vi_tri;

-- 3) Seed 25 Chức vụ chuẩn (STT 1 = cao nhất: 22 chức vụ của đặc tả, giữ "Quản trị viên",
--    "Lãnh đạo cơ quan", "Văn thư" chèn theo cấp bậc) và Tài khoản quản trị hệ thống mẫu
--    (Idempotent, không hard-code ID)
INSERT INTO
    accounts_position (
        display_order,
        name,
        is_public
    )
SELECT x.stt, x.ten, TRUE
FROM (
        VALUES
        (1, 'Quản trị viên'),
        (2, 'Chủ tịch HĐQT'),
        (3, 'Phó Chủ tịch HĐQT'),
        (4, 'Thành viên HĐQT'),
        (5, 'Tổng Giám đốc'),
        (6, 'Lãnh đạo cơ quan'),
        (7, 'Phó Tổng Giám đốc điều hành'),
        (8, 'Phó Tổng Giám đốc kinh doanh'),
        (9, 'Giám đốc Khối'),
        (10, 'Phó Giám đốc Khối'),
        (11, 'Giám đốc Vùng'),
        (12, 'Trợ lý TGĐ'),
        (13, 'Giám đốc'),
        (14, 'Phó Giám đốc'),
        (15, 'Trưởng Ban'),
        (16, 'Phó Ban'),
        (17, 'Trưởng Bộ phận'),
        (18, 'Trưởng nhóm'),
        (19, 'Trưởng phòng'),
        (20, 'Phó phòng'),
        (21, 'Chuyên viên'),
        (22, 'Văn thư'),
        (23, 'Kiểm toán viên'),
        (24, 'Nhân viên'),
        (25, 'Thành viên')
    ) AS x (stt, ten)
WHERE
    NOT EXISTS (
        SELECT 1
        FROM accounts_position p
        WHERE
            p.name = x.ten
    )
ORDER BY x.stt;

-- Đảm bảo có tài khoản quản trị hệ thống mẫu làm nguoi_lap_id nếu chưa có (truy vấn động ID)
INSERT INTO
    accounts_employee (
        username,
        email,
        password,
        ho_ten,
        ngay_sinh,
        chuc_vu_id,
        don_vi_id,
        is_staff,
        is_superuser,
        is_active
    )
SELECT 'admin', 'admin@baolong.vn', '!system_seed_placeholder', 'Quản trị hệ thống', '1990-01-01', (
        SELECT id
        FROM accounts_position
        WHERE
            name = 'Quản trị viên'
        LIMIT 1
    ), COALESCE(
        (
            SELECT id
            FROM organizations_donvi
            WHERE
                ten = 'Ban công nghệ thông tin'
            LIMIT 1
        ), (
            SELECT id
            FROM organizations_donvi
            ORDER BY id
            LIMIT 1
        )
    ), TRUE, TRUE, TRUE
WHERE
    NOT EXISTS (
        SELECT 1
        FROM accounts_employee
        WHERE
            username = 'admin'
    ) ON CONFLICT (username) DO NOTHING;

-- Chèn hoặc cập nhật Hồ sơ chung an toàn, idempotent 100% (không cố định stt_uu_tien = 1 nếu đã bị chiếm)
UPDATE records_hoso
SET
    is_he_thong = TRUE
WHERE
    so_ky_hieu = 'HSC'
    AND is_he_thong = FALSE
    AND NOT EXISTS (
        SELECT 1
        FROM records_hoso
        WHERE
            is_he_thong = TRUE
    );

INSERT INTO
    records_hoso (
        stt_uu_tien,
        so_ky_hieu,
        ten_ho_so,
        nguoi_lap_id,
        is_he_thong,
        ghi_chu
    )
SELECT
    CASE
        WHEN NOT EXISTS (
            SELECT 1
            FROM records_hoso
            WHERE
                stt_uu_tien = 1
        ) THEN 1
        ELSE (
            SELECT COALESCE(MAX(stt_uu_tien), 0) + 1
            FROM records_hoso
        )
    END,
    'HSC',
    'Hồ sơ chung',
    (
        SELECT id
        FROM accounts_employee
        WHERE
            username = 'admin'
        LIMIT 1
    ),
    TRUE,
    'Hồ sơ chung mặc định của hệ thống - không được xóa'
WHERE
    NOT EXISTS (
        SELECT 1
        FROM records_hoso
        WHERE
            is_he_thong = TRUE
            OR so_ky_hieu = 'HSC'
    ) ON CONFLICT (so_ky_hieu) DO
UPDATE
SET
    is_he_thong = TRUE;

-- ---------------------------------------------------------------------
-- 4) Seed 7 Nhóm quyền chuẩn (auth_group): 5 nhóm chính và 2 nhóm bổ sung [NQBS]
-- ---------------------------------------------------------------------
INSERT INTO
    auth_group (name, ma_nhom_quyen)
VALUES ('Văn thư', 'VT'),
    ('Chuyên viên', 'CV'),
    ('Trưởng phòng', 'TP'),
    ('Ban Giám đốc', 'BGD'),
    ('Quản trị hệ thống', 'ADMIN'),
    -- [NQBS] Nhóm bổ sung, gán cùng nhóm CV
    ('Trợ lý Ban Giám đốc', 'TLBGD'),
    ('Kiểm toán', 'KT') ON CONFLICT (name) DO
UPDATE
SET
    ma_nhom_quyen = EXCLUDED.ma_nhom_quyen;

-- ---------------------------------------------------------------------
-- 5) Seed 81 Quyền thao tác chi tiết (auth_permission)
-- ---------------------------------------------------------------------
INSERT INTO
    auth_permission (name, codename, module_ten)
VALUES
    -- Đơn vị, phòng ban (Nhóm 7)
    (
        'Xem danh sách đơn vị/phòng ban',
        'view_donvi',
        'Đơn vị, phòng ban'
    ),
    (
        'Thêm đơn vị/phòng ban',
        'add_donvi',
        'Đơn vị, phòng ban'
    ),
    (
        'Sửa đơn vị/phòng ban',
        'change_donvi',
        'Đơn vị, phòng ban'
    ),
    (
        'Xóa đơn vị/phòng ban',
        'delete_donvi',
        'Đơn vị, phòng ban'
    ),
    (
        'Xuất Excel đơn vị/phòng ban',
        'export_donvi',
        'Đơn vị, phòng ban'
    ),
    -- Chức vụ (Nhóm 7)
    (
        'Xem danh sách chức vụ',
        'view_chucvu',
        'Chức vụ'
    ),
    (
        'Thêm chức vụ',
        'add_chucvu',
        'Chức vụ'
    ),
    (
        'Sửa chức vụ',
        'change_chucvu',
        'Chức vụ'
    ),
    (
        'Xóa chức vụ',
        'delete_chucvu',
        'Chức vụ'
    ),
    -- Loại tài liệu biểu mẫu (Nhóm 7)
    (
        'Xem danh sách loại tài liệu',
        'view_loaitailieubieumau',
        'Loại tài liệu biểu mẫu'
    ),
    (
        'Thêm loại tài liệu',
        'add_loaitailieubieumau',
        'Loại tài liệu biểu mẫu'
    ),
    (
        'Sửa loại tài liệu',
        'change_loaitailieubieumau',
        'Loại tài liệu biểu mẫu'
    ),
    (
        'Xóa loại tài liệu',
        'delete_loaitailieubieumau',
        'Loại tài liệu biểu mẫu'
    ),
    -- Cán bộ nhân viên (Nhóm 7)
    (
        'Xem toàn bộ thông tin CBNV (kể cả năm sinh, Nhóm quyền, mật khẩu)',
        'view_full_cbnv',
        'CBNV'
    ),
    (
        'Xem danh sách CBNV (ẩn field nhạy cảm)',
        'view_list_cbnv',
        'CBNV'
    ),
    (
        'Thêm CBNV',
        'add_cbnv',
        'CBNV'
    ),
    (
        'Sửa CBNV (đầy đủ field)',
        'change_full_cbnv',
        'CBNV'
    ),
    (
        'Sửa thông tin cá nhân của chính mình',
        'change_self_cbnv',
        'CBNV'
    ),
    (
        'Xóa CBNV',
        'delete_cbnv',
        'CBNV'
    ),
    (
        'Duyệt yêu cầu đổi mật khẩu',
        'approve_password_reset_cbnv',
        'CBNV'
    ),
    (
        'Import file CBNV',
        'import_cbnv',
        'CBNV'
    ),
    (
        'Xuất Excel danh sách CBNV',
        'export_cbnv',
        'CBNV'
    ),
    -- Văn bản đến (Nhóm 2)
    (
        'Xem danh sách/chi tiết văn bản đến',
        'view_vanbanden',
        'Văn bản đến'
    ),
    (
        'Thêm văn bản đến',
        'add_vanbanden',
        'Văn bản đến'
    ),
    (
        'Sửa văn bản đến',
        'change_vanbanden',
        'Văn bản đến'
    ),
    (
        'Xóa văn bản đến',
        'delete_vanbanden',
        'Văn bản đến'
    ),
    (
        'Import file văn bản đến',
        'import_vanbanden',
        'Văn bản đến'
    ),
    (
        'Xuất Excel văn bản đến',
        'export_vanbanden',
        'Văn bản đến'
    ),
    (
        'Xem log user đã xem văn bản đến',
        'view_read_log_vanbanden',
        'Văn bản đến'
    ),
    (
        'Gửi mail toàn hệ thống (văn bản đến)',
        'send_mail_all_vanbanden',
        'Văn bản đến'
    ),
    -- Văn bản đi (Nhóm 2)
    (
        'Xem danh sách/chi tiết văn bản đi',
        'view_vanbandi',
        'Văn bản đi'
    ),
    (
        'Thêm văn bản đi',
        'add_vanbandi',
        'Văn bản đi'
    ),
    (
        'Sửa văn bản đi',
        'change_vanbandi',
        'Văn bản đi'
    ),
    (
        'Xóa văn bản đi',
        'delete_vanbandi',
        'Văn bản đi'
    ),
    (
        'Import file văn bản đi',
        'import_vanbandi',
        'Văn bản đi'
    ),
    (
        'Xuất Excel văn bản đi',
        'export_vanbandi',
        'Văn bản đi'
    ),
    (
        'Xem log user đã xem văn bản đi',
        'view_read_log_vanbandi',
        'Văn bản đi'
    ),
    (
        'Gửi mail toàn hệ thống (văn bản đi)',
        'send_mail_all_vanbandi',
        'Văn bản đi'
    ),
    -- Hồ sơ lưu trữ (Nhóm 3)
    (
        'Xem danh mục hồ sơ',
        'view_hoso',
        'Hồ sơ'
    ),
    (
        'Lập/Thêm hồ sơ',
        'add_hoso',
        'Hồ sơ'
    ),
    (
        'Sửa hồ sơ',
        'change_hoso',
        'Hồ sơ'
    ),
    (
        'Xóa hồ sơ',
        'delete_hoso',
        'Hồ sơ'
    ),
    (
        'Mở/Đóng danh mục hồ sơ',
        'toggle_status_hoso',
        'Hồ sơ'
    ),
    (
        'Đưa văn bản vào / loại ra khỏi hồ sơ điện tử',
        'manage_documents_hoso',
        'Hồ sơ'
    ),
    -- Tài liệu, biểu mẫu (Nhóm 4)
    (
        'Xem tài liệu, biểu mẫu',
        'view_tailieu',
        'Tài liệu, biểu mẫu'
    ),
    (
        'Thêm tài liệu, biểu mẫu',
        'add_tailieu',
        'Tài liệu, biểu mẫu'
    ),
    (
        'Sửa tài liệu, biểu mẫu',
        'change_tailieu',
        'Tài liệu, biểu mẫu'
    ),
    (
        'Xóa tài liệu, biểu mẫu',
        'delete_tailieu',
        'Tài liệu, biểu mẫu'
    ),
    -- Trình ký (Nhóm 5 — Cập nhật đầy đủ 8 quyền theo Issue #47)
    (
        'Xem văn bản trình ký',
        'view_trinhky',
        'Trình ký'
    ),
    (
        'Tạo trình ký',
        'add_trinhky',
        'Trình ký'
    ),
    (
        'Ký (đúng lượt trong sơ đồ)',
        'sign_trinhky',
        'Trình ký'
    ),
    (
        'Quản lý quy trình trình ký',
        'manage_signing_process',
        'Trình ký'
    ),
    (
        'Gửi trình ký / Nộp lại lượt trình',
        'send_trinhky',
        'Trình ký'
    ),
    (
        'Ủy quyền ký số',
        'delegate_trinhky',
        'Trình ký'
    ),
    (
        'Hủy yêu cầu trình ký',
        'cancel_trinhky',
        'Trình ký'
    ),
    (
        'Xem nhật ký kiểm toán trình ký',
        'view_signing_audit',
        'Trình ký'
    ),
    -- Quản lý Công việc (Nhóm 6)
    (
        'Xem công việc (chung)',
        'view_congviec',
        'Công việc'
    ),
    (
        'Xem tất cả công việc (toàn hệ thống)',
        'view_all_congviec',
        'Công việc'
    ),
    (
        'Xem công việc theo phòng ban',
        'view_dept_congviec',
        'Công việc'
    ),
    (
        'Thêm/Giao việc',
        'add_congviec',
        'Công việc'
    ),
    (
        'Sửa công việc',
        'change_congviec',
        'Công việc'
    ),
    (
        'Xóa công việc',
        'delete_congviec',
        'Công việc'
    ),
    (
        'Duyệt / Hủy duyệt công việc',
        'approve_congviec',
        'Công việc'
    ),
    -- Phòng họp (Nhóm 7)
    (
        'Xem lịch phòng họp',
        'view_schedule_phonghop',
        'Phòng họp (danh mục)'
    ),
    (
        'Đặt phòng họp',
        'add_datphonghop',
        'Đặt phòng họp'
    ),
    (
        'Sửa/Hủy lịch do chính mình đặt',
        'change_own_datphonghop',
        'Đặt phòng họp'
    ),
    (
        'Sửa/Hủy mọi lịch đặt phòng (QT)',
        'change_any_datphonghop',
        'Đặt phòng họp'
    ),
    -- Sinh nhật (Nhóm 7)
    (
        'Xem danh sách sinh nhật',
        'view_sinhnhat',
        'Sinh nhật'
    ),
    (
        'Gửi lời chúc (thủ công)',
        'send_wish_sinhnhat',
        'Sinh nhật'
    ),
    -- [v1] Quyền bổ sung của Nhóm 7 (Issue #53): trang Phân quyền, import Chức vụ, quản lý danh mục phòng họp
    (
        'Xem danh sách nhóm quyền',
        'view_nhomquyen',
        'Phân quyền'
    ),
    (
        'Thêm nhóm quyền',
        'add_nhomquyen',
        'Phân quyền'
    ),
    (
        'Sửa nhóm quyền',
        'change_nhomquyen',
        'Phân quyền'
    ),
    (
        'Xóa nhóm quyền',
        'delete_nhomquyen',
        'Phân quyền'
    ),
    (
        'Import chức vụ từ Excel',
        'import_chucvu',
        'Chức vụ'
    ),
    (
        'Thêm phòng họp (danh mục)',
        'add_phonghop',
        'Phòng họp (danh mục)'
    ),
    (
        'Sửa phòng họp (danh mục)',
        'change_phonghop',
        'Phòng họp (danh mục)'
    ),
    (
        'Xóa phòng họp (danh mục)',
        'delete_phonghop',
        'Phòng họp (danh mục)'
    ),
    -- Chatbox AI (Nhóm 8)
    (
        'Sử dụng chatbot (chỉ trả lời nội dung người hỏi có quyền Xem)',
        'use_aiassistant',
        'Chatbox AI'
    ) ON CONFLICT (codename) DO
UPDATE
SET
    name = EXCLUDED.name,
    module_ten = EXCLUDED.module_ten;

-- ---------------------------------------------------------------------
-- 6) Seed Mapping Quyền vào Nhóm (auth_group_permissions)
-- Truy vấn động theo codename và ma_nhom_quyen (không hard-code ID)
-- ---------------------------------------------------------------------

-- Nhóm ADMIN: Toàn bộ quyền trong hệ thống
INSERT INTO
    auth_group_permissions (group_id, permission_id)
SELECT g.id, p.id
FROM auth_group g
    CROSS JOIN auth_permission p
WHERE
    g.ma_nhom_quyen = 'ADMIN' ON CONFLICT (group_id, permission_id) DO NOTHING;

-- Nhóm BGD (Ban Giám đốc): Toàn quyền xem, ký số, duyệt việc, quản lý lịch họp, sinh nhật, AI
INSERT INTO
    auth_group_permissions (group_id, permission_id)
SELECT g.id, p.id
FROM auth_group g, auth_permission p
WHERE
    g.ma_nhom_quyen = 'BGD'
    AND p.codename IN (
        'view_donvi',
        'view_chucvu',
        'view_loaitailieubieumau',
        'view_list_cbnv',
        'change_self_cbnv',
        'export_cbnv',
        'view_vanbanden',
        'view_vanbandi',
        'view_read_log_vanbanden',
        'view_read_log_vanbandi',
        'view_hoso',
        'view_tailieu',
        'view_trinhky',
        'add_trinhky',
        'sign_trinhky',
        'send_trinhky',
        'delegate_trinhky',
        'cancel_trinhky',
        'view_signing_audit',
        'view_congviec',
        'view_all_congviec',
        'view_dept_congviec',
        'add_congviec',
        'approve_congviec',
        'view_schedule_phonghop',
        'add_datphonghop',
        'change_own_datphonghop',
        'view_sinhnhat',
        'send_wish_sinhnhat',
        'use_aiassistant'
    ) ON CONFLICT (group_id, permission_id) DO NOTHING;

-- Nhóm TP (Trưởng phòng): Quyền xem, ký duyệt phòng ban, giao việc, xem việc phòng ban, đặt phòng họp, AI
INSERT INTO
    auth_group_permissions (group_id, permission_id)
SELECT g.id, p.id
FROM auth_group g, auth_permission p
WHERE
    g.ma_nhom_quyen = 'TP'
    AND p.codename IN (
        'view_donvi',
        'view_chucvu',
        'view_loaitailieubieumau',
        'view_list_cbnv',
        'change_self_cbnv',
        'export_cbnv',
        'view_vanbanden',
        'view_vanbandi',
        'view_read_log_vanbanden',
        'view_hoso',
        'view_tailieu',
        'view_trinhky',
        'add_trinhky',
        'sign_trinhky',
        'send_trinhky',
        'delegate_trinhky',
        'cancel_trinhky',
        'manage_signing_process', -- [P7] lãnh đạo đơn vị quản lý quy trình PHONG_BAN
        'view_congviec',
        'view_dept_congviec',
        'add_congviec',
        'change_congviec',
        'approve_congviec',
        'view_schedule_phonghop',
        'add_datphonghop',
        'change_own_datphonghop',
        'view_sinhnhat',
        'send_wish_sinhnhat',
        'use_aiassistant'
    ) ON CONFLICT (group_id, permission_id) DO NOTHING;

-- Nhóm CV (Chuyên viên): Xử lý nghiệp vụ chuyên môn, xem việc phòng ban (view_dept_congviec). Quyền duyệt công việc phân quyền theo ngữ cảnh task_participant (Người tạo, Chủ trì, Chỉ đạo)
INSERT INTO
    auth_group_permissions (group_id, permission_id)
SELECT g.id, p.id
FROM auth_group g, auth_permission p
WHERE
    g.ma_nhom_quyen = 'CV'
    AND p.codename IN (
        'view_donvi',
        'view_chucvu',
        'view_loaitailieubieumau',
        'view_list_cbnv',
        'change_self_cbnv',
        'view_vanbanden',
        'view_vanbandi',
        'view_hoso',
        'view_tailieu',
        'view_trinhky',
        'add_trinhky',
        'send_trinhky', -- [CVTK] người tạo hồ sơ tự gửi trình ký
        'view_congviec',
        'view_dept_congviec',
        'add_congviec',
        'change_congviec',
        'view_schedule_phonghop',
        'add_datphonghop',
        'change_own_datphonghop',
        'view_sinhnhat',
        'send_wish_sinhnhat',
        'use_aiassistant'
    ) ON CONFLICT (group_id, permission_id) DO NOTHING;

-- Nhóm VT (Văn thư): Nghiệp vụ văn thư lưu trữ, văn bản đến/đi, quản lý hồ sơ, tài liệu biểu mẫu
INSERT INTO
    auth_group_permissions (group_id, permission_id)
SELECT g.id, p.id
FROM auth_group g, auth_permission p
WHERE
    g.ma_nhom_quyen = 'VT'
    AND p.codename IN (
        'view_donvi',
        'view_chucvu',
        'view_loaitailieubieumau',
        'view_list_cbnv',
        'change_self_cbnv',
        'view_vanbanden',
        'add_vanbanden',
        'change_vanbanden',
        'delete_vanbanden',
        'import_vanbanden',
        'export_vanbanden',
        'view_read_log_vanbanden',
        'send_mail_all_vanbanden',
        'view_vanbandi',
        'add_vanbandi',
        'change_vanbandi',
        'delete_vanbandi',
        'import_vanbandi',
        'export_vanbandi',
        'view_read_log_vanbandi',
        'send_mail_all_vanbandi',
        'view_hoso',
        'add_hoso',
        'change_hoso',
        'manage_documents_hoso',
        'toggle_status_hoso',
        'view_tailieu',
        'add_tailieu',
        'change_tailieu',
        'view_trinhky',
        'send_trinhky',
        'add_trinhky',
        'view_congviec',
        'view_dept_congviec',
        'add_congviec',
        'change_congviec',
        'view_schedule_phonghop',
        'add_datphonghop',
        'change_own_datphonghop',
        'view_sinhnhat',
        'send_wish_sinhnhat',
        'use_aiassistant'
    ) ON CONFLICT (group_id, permission_id) DO NOTHING;
-- [NQBS] Nhóm TLBGD (Trợ lý Ban Giám đốc): chỉ chứa quyền cộng thêm, người dùng giữ nhóm CV
INSERT INTO
    auth_group_permissions (group_id, permission_id)
SELECT g.id, p.id
FROM auth_group g, auth_permission p
WHERE
    g.ma_nhom_quyen = 'TLBGD'
    AND p.codename IN (
        'view_all_congviec',
        'view_read_log_vanbanden',
        'view_read_log_vanbandi',
        'send_trinhky'
    ) ON CONFLICT (group_id, permission_id) DO NOTHING;
-- [NQBS] Nhóm KT (Kiểm toán): chỉ chứa quyền cộng thêm, người dùng giữ nhóm CV
INSERT INTO
    auth_group_permissions (group_id, permission_id)
SELECT g.id, p.id
FROM auth_group g, auth_permission p
WHERE
    g.ma_nhom_quyen = 'KT'
    AND p.codename IN (
        'view_signing_audit',
        'view_read_log_vanbanden',
        'view_read_log_vanbandi'
    ) ON CONFLICT (group_id, permission_id) DO NOTHING;
COMMIT;

-- =====================================================================
-- [v1][BỎ MẬT] TÀI KHOẢN CSDL CHỈ ĐỌC CHO TRỢ LÝ AI (Nhóm 8)
-- - Role được tạo ngoài DDL (kèm mật khẩu từ biến môi trường); khối dưới chỉ cấp quyền khi role đã tồn tại.
-- - Cấp theo bảng/cột cần dùng; KHÔNG cấp bảng khóa ký/PIN/nhật ký, cột password;
--   KHÔNG dùng ALTER DEFAULT PRIVILEGES.
-- - AI chỉ được cấp SELECT trên ai_vanbanden, ai_vanbandi, ai_tailieu.
--   Các view văn bản chỉ trả về NOI_BO đang hiển thị; cột/bảng đính kèm không nằm trong view.
-- - Quyền dùng AI và quyền xem từng loại được kiểm tra ở ứng dụng theo codename.
--   View ai_tailieu tự giới hạn TAT_CA / NOI_BO_PHONG_BAN theo employee_id của phiên DB.
-- =====================================================================
CREATE VIEW ai_vanbanden WITH (security_barrier) AS
    SELECT id, so_hieu, so_thu_tu, nam, ngay_den, trich_yeu, noi_ban_hanh,
           ngay_van_ban, nguoi_ky, chuc_vu, hieu_luc, ngay_het_hieu_luc,
           ghi_chu, updated_at
    FROM documents_vanbanden
    WHERE pham_vi = 'NOI_BO' AND hien_thi IS TRUE;

CREATE VIEW ai_vanbanden_nguoinhan WITH (security_barrier) AS
    SELECT nn.* FROM documents_vanbanden_nguoinhan nn
    JOIN documents_vanbanden vb ON vb.id = nn.vanbanden_id
    WHERE vb.pham_vi = 'NOI_BO' AND vb.hien_thi IS TRUE;

CREATE VIEW ai_vanbanden_donvinhan WITH (security_barrier) AS
    SELECT dv.* FROM documents_vanbanden_donvinhan dv
    JOIN documents_vanbanden vb ON vb.id = dv.vanbanden_id
    WHERE vb.pham_vi = 'NOI_BO' AND vb.hien_thi IS TRUE;

CREATE VIEW ai_vanbandi WITH (security_barrier) AS
    SELECT vb.id, vb.so_hieu, vb.so_thu_tu, vb.nam, vb.ngay_ban_hanh,
           vb.trich_yeu,
           (
               SELECT string_agg(dv.ten, ', ' ORDER BY dv.ten)
               FROM documents_vanbandi_noibanhanh nb
               JOIN organizations_donvi dv ON dv.id = nb.donvi_id
               WHERE nb.vanbandi_id = vb.id
           ) AS noi_ban_hanh,
           vb.ngay_van_ban, vb.nguoi_ky, vb.chuc_vu, vb.hieu_luc,
           vb.ngay_het_hieu_luc, vb.ghi_chu, vb.updated_at
    FROM documents_vanbandi vb
    WHERE vb.pham_vi = 'NOI_BO' AND vb.hien_thi IS TRUE;

CREATE VIEW ai_vanbandi_noibanhanh WITH (security_barrier) AS
    SELECT nb.* FROM documents_vanbandi_noibanhanh nb
    JOIN documents_vanbandi vb ON vb.id = nb.vanbandi_id
    WHERE vb.pham_vi = 'NOI_BO' AND vb.hien_thi IS TRUE;

CREATE VIEW ai_vanbandi_nguoinhan WITH (security_barrier) AS
    SELECT nn.* FROM documents_vanbandi_nguoinhan nn
    JOIN documents_vanbandi vb ON vb.id = nn.vanbandi_id
    WHERE vb.pham_vi = 'NOI_BO' AND vb.hien_thi IS TRUE;

CREATE VIEW ai_vanbandi_donvinhan WITH (security_barrier) AS
    SELECT dv.* FROM documents_vanbandi_donvinhan dv
    JOIN documents_vanbandi vb ON vb.id = dv.vanbandi_id
    WHERE vb.pham_vi = 'NOI_BO' AND vb.hien_thi IS TRUE;

CREATE VIEW ai_tailieu WITH (security_barrier) AS
    SELECT t.id, t.ky_hieu, t.tieu_de, t.ngay_dang, t.noi_ban_hanh,
           t.hieu_luc, t.ngay_het_hieu_luc, t.ghi_chu, t.updated_at
    FROM records_chitiettailieu t
    WHERE t.hien_thi::text = 'TAT_CA'
       OR (
           t.hien_thi::text = 'NOI_BO_PHONG_BAN'
           AND t.don_vi_id = (
               SELECT e.don_vi_id
               FROM accounts_employee e
               WHERE e.id = NULLIF(current_setting('qlvb.employee_id', true), '')::bigint
                 AND e.is_active IS TRUE
                 AND e.trang_thai::text = 'LAM_VIEC'
           )
       );

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'qlvb_readonly') THEN
        -- Remove grants from the previous raw-table implementation before
        -- granting the view-only contract.
        REVOKE SELECT (id, don_vi_id, is_active, trang_thai, is_superuser) ON accounts_employee FROM qlvb_readonly;
        REVOKE SELECT (id, ten) ON organizations_donvi FROM qlvb_readonly;
        REVOKE SELECT ON accounts_employee, organizations_donvi, records_chitiettailieu FROM qlvb_readonly;
        REVOKE SELECT ON
            ai_vanbanden_nguoinhan,
            ai_vanbanden_donvinhan,
            ai_vanbandi_noibanhanh,
            ai_vanbandi_nguoinhan,
            ai_vanbandi_donvinhan
        FROM qlvb_readonly;
        GRANT SELECT ON
            ai_vanbanden,
            ai_vanbandi,
            ai_tailieu
        TO qlvb_readonly;
    ELSE
        RAISE NOTICE 'Role qlvb_readonly chưa tồn tại: bỏ qua cấp quyền chỉ đọc cho trợ lý AI';
    END IF;
END
$$;
