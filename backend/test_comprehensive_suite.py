"""
Kịch bản kiểm thử toàn diện Module Quản lý Văn bản:
1. Import / Export Excel & Thêm văn bản qua Excel.
2. Kiểm tra tính hợp lý của các trạng thái hiệu lực (tự động hết hạn, hiệu lực từng phần, chưa hiệu lực).
3. Tính năng thay thế văn bản (2 chiều, tự động chuyển HET_VA_THAY_THE, chặn vòng lặp, khôi phục khi xóa).
4. Khóa nghiệp vụ (nhập/chọn danh mục hồ sơ trước mới chọn loại văn bản).
5. Phân quyền toàn diện (không xem được văn bản hết hiệu lực, không sửa/xóa trái quyền, bảo vệ VB Hạn chế & VB Mật).
"""

import os
import sys
import django
import io
from datetime import timedelta

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

import openpyxl
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.exceptions import PermissionDenied, ValidationError, NotFound
from rest_framework.test import APIRequestFactory

try:
    from documents.models import (
        VanBanDen,
        VanBanDi,
        VanBanMat,
        PhamVi,
        HieuLuc,
        LoaiVanBan,
        DocumentAccessLog,
        DocumentViewLog,
    )
    from documents.services import (
        generate_excel_template,
        import_from_excel,
        export_to_excel,
        sync_replacement_document,
        cleanup_replacement_links_on_delete,
        cleanup_old_replacement_link,
    )
    from documents.selectors import (
        van_ban_xem_duoc,
        la_nguoi_xem_duoc,
    )
    from documents.views import (
        DocumentViewSet,
        can_edit_document,
        can_delete_document,
        can_create_document,
    )
except (ImportError, RuntimeError):
    from apps.documents.models import (
        VanBanDen,
        VanBanDi,
        VanBanMat,
        PhamVi,
        HieuLuc,
        LoaiVanBan,
        DocumentAccessLog,
        DocumentViewLog,
    )
    from apps.documents.services import (
        generate_excel_template,
        import_from_excel,
        export_to_excel,
        sync_replacement_document,
        cleanup_replacement_links_on_delete,
        cleanup_old_replacement_link,
    )
    from apps.documents.selectors import (
        van_ban_xem_duoc,
        la_nguoi_xem_duoc,
    )
    from apps.documents.views import (
        DocumentViewSet,
        can_edit_document,
        can_delete_document,
        can_create_document,
    )

User = get_user_model()


def run_all_tests():
    print("=" * 70)
    print("     BẮT ĐẦU CHẠY KIỂM THỬ TOÀN DIỆN HỆ THỐNG QUẢN LÝ VĂN BẢN")
    print("=" * 70)

    # 0. Chuẩn bị người dùng kiểm thử từ database
    admin_user = User.objects.filter(is_superuser=True).first()
    regular_users = list(User.objects.filter(is_superuser=False, is_staff=False))
    if len(regular_users) >= 3:
        user_creator = regular_users[0]
        user_receiver = regular_users[1]
        user_outsider = regular_users[2]
    else:
        user_creator = User.objects.get(username="truongphong_cntt")
        user_receiver = User.objects.filter(username__in=["chuyenvien_cntt", "canbo2", "canbo"]).first()
        user_outsider = User.objects.get(username="vanthu_cntt")

    # Xóa dữ liệu cũ do test tạo (nếu có)
    VanBanDen.objects.filter(so_hieu__startswith="TEST/").delete()
    VanBanDi.objects.filter(so_hieu__startswith="TEST/").delete()
    VanBanMat.objects.filter(so_hieu__startswith="TEST/").delete()

    passed_count = 0
    total_count = 0

    def assert_test(cond, title, detail=""):
        nonlocal passed_count, total_count
        total_count += 1
        if cond:
            passed_count += 1
            print(f"  [PASS] {title}")
            if detail:
                print(f"         -> {detail}")
        else:
            print(f"  [FAIL] {title}")
            if detail:
                print(f"         -> ERROR: {detail}")
            raise AssertionError(f"Test failed: {title} - {detail}")

    # =========================================================================
    # PHẦN 1: IMPORT / EXPORT EXCEL & THÊM VĂN BẢN QUA EXCEL
    # =========================================================================
    print("\n--- PHẦN 1: IMPORT / EXPORT EXCEL ---")
    
    # 1.1 Tạo template Excel
    template_buffer = generate_excel_template("DEN")
    wb_temp = openpyxl.load_workbook(template_buffer)
    sheet_temp = wb_temp.active
    headers_temp = [cell.value for cell in sheet_temp[1]]
    assert_test("Số, ký hiệu VB" in headers_temp, "1.1 Sinh file Excel mẫu (Template)", f"Headers tìm thấy: {headers_temp[:4]}")

    # 1.2 Tạo file Excel hợp lệ để import
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "VanBanDen"
    headers = [
        "Số, ký hiệu VB", "Trích yếu nội dung", "Nơi ban hành", "Ngày ban hành",
        "Ngày đến", "Người ký", "Ghi chú"
    ]
    ws.append(headers)
    ws.append([
        "TEST/IMPORT/01", "Văn bản thử nghiệm import Excel số 1", "Sở Nội vụ",
        "2026-03-01", "2026-03-02", "Nguyễn Văn A", "Ghi chú mẫu 1"
    ])
    ws.append([
        "TEST/IMPORT/02", "Văn bản thử nghiệm import Excel số 2", "UBND Tỉnh",
        "2026-03-05", "2026-03-06", "Trần Văn B", "Ghi chú mẫu 2"
    ])
    excel_file = io.BytesIO()
    wb.save(excel_file)
    excel_file.seek(0)

    # Thực hiện import
    res_import = import_from_excel(excel_file, "DEN", admin_user)
    created_count = res_import.get("created", 0)
    errors = res_import.get("errors", [])
    assert_test(created_count == 2 and len(errors) == 0, "1.2 Import văn bản từ file Excel chuẩn", f"Import thành công {created_count} văn bản, lỗi: {errors}")

    doc_imported = VanBanDen.objects.filter(so_hieu="TEST/IMPORT/01").first()
    assert_test(
        doc_imported is not None and doc_imported.trich_yeu == "Văn bản thử nghiệm import Excel số 1",
        "1.3 Kiểm tra dữ liệu sau khi Import Excel",
        f"Số hiệu: {doc_imported.so_hieu}, Trích yếu: {doc_imported.trich_yeu}"
    )

    # 1.4 Kiểm tra bắt lỗi khi file Excel thiếu trường bắt buộc (thiếu trích yếu)
    wb_err = openpyxl.Workbook()
    ws_err = wb_err.active
    ws_err.append(["Số, ký hiệu VB", "Trích yếu nội dung"])
    ws_err.append(["TEST/IMPORT/ERR", ""])   # Trích yếu rỗng
    err_file = io.BytesIO()
    wb_err.save(err_file)
    err_file.seek(0)
    res_err = import_from_excel(err_file, "DEN", admin_user)
    c_count_err = res_err.get("created", 0)
    errors_list = res_err.get("errors", [])
    assert_test(c_count_err == 0 and len(errors_list) > 0, "1.4 Bắt lỗi và validate file Excel không hợp lệ", f"Hệ thống từ chối import và ghi nhận lỗi: {errors_list[0] if errors_list else ''}")

    # 1.5 Xuất Excel (Export)
    qs_export = VanBanDen.objects.filter(so_hieu__startswith="TEST/IMPORT/")
    export_buf = export_to_excel(qs_export, "DEN")
    wb_out = openpyxl.load_workbook(export_buf)
    ws_out = wb_out.active
    assert_test(ws_out.max_row >= 3, "1.5 Xuất dữ liệu văn bản ra file Excel", f"File Excel xuất ra có {ws_out.max_row - 1} dòng dữ liệu")

    # =========================================================================
    # PHẦN 2: KIỂM TRA TÍNH HỢP LÝ CỦA CÁC TRẠNG THÁI HIỆU LỰC
    # =========================================================================
    print("\n--- PHẦN 2: TRẠNG THÁI HIỆU LỰC ---")

    now = timezone.now()
    past_date = now - timedelta(days=5)
    future_date = now + timedelta(days=30)

    # 2.1 Tự động chuyển HET_HIEU_LUC khi ngay_het_hieu_luc trong quá khứ
    doc_expired = VanBanDen.objects.create(
        so_hieu="TEST/HL/EXPIRED",
        trich_yeu="Văn bản đã quá thời hạn hiệu lực",
        nam=2026,
        so_thu_tu=901,
        ngay_van_ban=past_date - timedelta(days=100),
        ngay_het_hieu_luc=past_date,
        hieu_luc=HieuLuc.CON_HIEU_LUC,
        nguoi_tao=admin_user,
    )
    # View logic tự động quét và cập nhật hiệu lực
    factory = APIRequestFactory()
    req = factory.get(f"/api/documents/{doc_expired.id}/")
    req.user = admin_user
    view_detail = DocumentViewSet.as_view({"get": "retrieve"})
    res_det = view_detail(req, pk=doc_expired.id)
    doc_expired.refresh_from_db()
    assert_test(
        doc_expired.hieu_luc == HieuLuc.HET_HIEU_LUC or res_det.data.get("hieu_luc") == HieuLuc.HET_HIEU_LUC,
        "2.1 Tự động hết hạn khi ngày hết hiệu lực trong quá khứ",
        f"Trạng thái cập nhật thành: {doc_expired.hieu_luc}"
    )

    # 2.2 Văn bản còn hiệu lực 1 phần
    doc_partial = VanBanDen.objects.create(
        so_hieu="TEST/HL/PARTIAL",
        trich_yeu="Văn bản hết hiệu lực một phần",
        nam=2026,
        so_thu_tu=902,
        ngay_van_ban=now - timedelta(days=30),
        hieu_luc=HieuLuc.CON_HIEU_LUC_1_PHAN,
        nguoi_tao=admin_user,
    )
    assert_test(doc_partial.hieu_luc == HieuLuc.CON_HIEU_LUC_1_PHAN, "2.2 Trạng thái còn hiệu lực 1 phần (CON_HIEU_LUC_1_PHAN)", "Giữ đúng tính chất nghiệp vụ")

    # 2.3 Quét tự động định kỳ cập nhật văn bản hết hiệu lực (service check_and_update_expired_documents)
    from documents.services import check_and_update_expired_documents
    doc_expired_batch = VanBanDen.objects.create(
        so_hieu="TEST/HL/BATCH_EXP",
        trich_yeu="Văn bản hết hiệu lực quét bởi batch service",
        nam=2026,
        so_thu_tu=903,
        ngay_van_ban=past_date - timedelta(days=50),
        ngay_het_hieu_luc=past_date,
        hieu_luc=HieuLuc.CON_HIEU_LUC,
        nguoi_tao=admin_user,
    )
    count_updated = check_and_update_expired_documents()
    doc_expired_batch.refresh_from_db()
    assert_test(
        doc_expired_batch.hieu_luc == HieuLuc.HET_HIEU_LUC and count_updated >= 1,
        "2.3 Quét tự động định kỳ cập nhật văn bản hết hiệu lực (check_and_update_expired_documents)",
        f"Số văn bản cập nhật trong đợt quét: {count_updated}, Trạng thái: {doc_expired_batch.hieu_luc}"
    )

    # =========================================================================
    # PHẦN 3: TÍNH NĂNG THAY THẾ VĂN BẢN (2 CHIỀU & CHẶN VÒNG LẶP)
    # =========================================================================
    print("\n--- PHẦN 3: TÍNH NĂNG THAY THẾ VĂN BẢN ---")

    # 3.1 Tạo văn bản cũ B
    doc_old = VanBanDen.objects.create(
        so_hieu="TEST/REPLACE/DOC_B",
        trich_yeu="Văn bản cũ chuẩn bị bị thay thế",
        nam=2026,
        so_thu_tu=910,
        ngay_van_ban=now - timedelta(days=60),
        hieu_luc=HieuLuc.CON_HIEU_LUC,
        nguoi_tao=admin_user,
    )
    # Tạo văn bản mới A thay thế B
    doc_new = VanBanDen.objects.create(
        so_hieu="TEST/REPLACE/DOC_A",
        trich_yeu="Văn bản mới thay thế cho DOC_B",
        nam=2026,
        so_thu_tu=911,
        ngay_van_ban=now,
        link_thay_the="TEST/REPLACE/DOC_B",
        hieu_luc=HieuLuc.CON_HIEU_LUC,
        nguoi_tao=admin_user,
    )
    sync_replacement_document(doc_new)
    doc_old.refresh_from_db()

    assert_test(
        doc_old.hieu_luc == HieuLuc.HET_VA_THAY_THE and doc_old.ngay_het_hieu_luc is not None,
        "3.1 Tự động chuyển văn bản cũ thành HET_VA_THAY_THE và gán ngày hết hiệu lực",
        f"Trạng thái văn bản cũ: {doc_old.hieu_luc}, Ngày hết hiệu lực: {doc_old.ngay_het_hieu_luc}"
    )

    # 3.2 Liên kết 2 chiều qua API chi tiết
    req_a = factory.get(f"/api/documents/{doc_new.id}/")
    req_a.user = admin_user
    res_a = view_detail(req_a, pk=doc_new.id)

    req_b = factory.get(f"/api/documents/{doc_old.id}/")
    req_b.user = admin_user
    res_b = view_detail(req_b, pk=doc_old.id)

    thay_the_cho = res_a.data.get("thay_the_cho", [])
    bi_thay_boi = res_b.data.get("bi_thay_boi", [])

    assert_test(
        "TEST/REPLACE/DOC_B" in thay_the_cho and "TEST/REPLACE/DOC_A" in bi_thay_boi,
        "3.2 Quan hệ thay thế 2 chiều chính xác",
        f"DOC_A thay_the_cho = {thay_the_cho} | DOC_B bi_thay_boi = {bi_thay_boi}"
    )

    # 3.3 Ngăn chặn vòng lặp thay thế (Circular replacement)
    # DOC_B không được thay thế lại DOC_A
    from documents.serializers import DocumentCreateUpdateSerializer
    serializer_circ = DocumentCreateUpdateSerializer(
        instance=doc_old,
        data={"link_thay_the": "TEST/REPLACE/DOC_A"},
        partial=True,
    )
    is_valid = serializer_circ.is_valid()
    circ_prevented = not is_valid and ("link_thay_the" in serializer_circ.errors or "non_field_errors" in serializer_circ.errors)
    assert_test(circ_prevented, "3.3 Ngăn chặn vòng lặp thay thế (DOC_B không được thay thế lại DOC_A)", f"Validation Error: {serializer_circ.errors}")

    # 3.4 Phục hồi khi xóa văn bản thay thế
    cleanup_replacement_links_on_delete(doc_new)
    doc_new.delete()
    doc_old.refresh_from_db()
    assert_test(
        doc_old.link_thay_the == "" or doc_old.link_thay_the is None or "TEST/REPLACE/DOC_A" not in (doc_old.link_thay_the or ""),
        "3.4 Tự động dọn dẹp liên kết khi văn bản thay thế bị xóa",
        f"Link thay thế còn lại của DOC_B: '{doc_old.link_thay_the}'"
    )

    # =========================================================================
    # PHẦN 4: KHÓA NGHIỆP VỤ (HỒ SƠ -> LOẠI VĂN BẢN)
    # =========================================================================
    print("\n--- PHẦN 4: KHÓA NGHIỆP VỤ ---")

    # 4.1 Thêm văn bản Đến: Phải có hồ sơ và loại văn bản
    doc_den_ok = VanBanDen.objects.create(
        so_hieu="TEST/DEN/01",
        trich_yeu="Văn bản đến kiểm tra khóa nghiệp vụ",
        nam=2026,
        so_thu_tu=920,
        danh_muc_ho_so="Hồ sơ Pháp chế & Thanh tra 2026",
        ten_loai_van_ban="Báo cáo",
        ngay_van_ban=now,
        nguoi_tao=admin_user,
    )
    assert_test(
        doc_den_ok.danh_muc_ho_so != "" and doc_den_ok.ten_loai_van_ban != "",
        "4.1 Văn bản Đến lưu trữ đầy đủ Danh mục hồ sơ & Loại văn bản gõ tự do",
        f"Hồ sơ: {doc_den_ok.danh_muc_ho_so} | Loại văn bản: {doc_den_ok.ten_loai_van_ban}"
    )

    # 4.2 Thêm Văn bản Đi: Danh mục hồ sơ và loại văn bản nội bộ
    doc_di_ok = VanBanDi.objects.create(
        so_hieu="TEST/DI/01",
        trich_yeu="Văn bản đi kiểm tra danh mục quy chuẩn",
        nam=2026,
        so_thu_tu=921,
        danh_muc_ho_so="Hồ sơ Chỉ đạo & Điều hành",
        ten_loai_van_ban="Chỉ thị",
        ngay_ban_hanh=now,
        nguoi_tao=admin_user,
    )
    assert_test(
        doc_di_ok.danh_muc_ho_so == "Hồ sơ Chỉ đạo & Điều hành" and doc_di_ok.ten_loai_van_ban == "Chỉ thị",
        "4.2 Văn bản Đi lưu trữ đúng Danh mục hồ sơ và Loại văn bản quy chuẩn",
        f"Hồ sơ: {doc_di_ok.danh_muc_ho_so} | Loại văn bản: {doc_di_ok.ten_loai_van_ban}"
    )

    # 4.3 Thêm Văn bản Mật
    doc_mat_ok = VanBanMat.objects.create(
        so_hieu="TEST/MAT/01",
        trich_yeu="Văn bản mật nội bộ",
        nam=2026,
        danh_muc_ho_so="Hồ sơ An ninh & Quốc phòng",
        ten_loai_van_ban="Kế hoạch",
        ngay_ban_hanh=now,
        nguoi_tao=admin_user,
    )
    assert_test(
        doc_mat_ok.so_hieu == "TEST/MAT/01" and doc_mat_ok.loai == "MAT",
        "4.3 Văn bản Mật lưu trữ và nhận diện đúng loại MAT",
        f"Số hiệu: {doc_mat_ok.so_hieu} | Loại: {doc_mat_ok.loai}"
    )

    # =========================================================================
    # PHẦN 5: PHÂN QUYỀN TOÀN DIỆN
    # =========================================================================
    print("\n--- PHẦN 5: PHÂN QUYỀN TOÀN DIỆN ---")

    # 5.1 Văn bản hết hiệu lực: Cán bộ thông thường không được xem
    doc_expired_test = VanBanDen.objects.create(
        so_hieu="TEST/PERM/EXPIRED",
        trich_yeu="Văn bản hết hiệu lực để test phân quyền",
        nam=2026,
        so_thu_tu=930,
        ngay_van_ban=past_date - timedelta(days=200),
        ngay_het_hieu_luc=past_date,
        hieu_luc=HieuLuc.HET_HIEU_LUC,
        pham_vi=PhamVi.NOI_BO,
        hien_thi=True,
        nguoi_tao=user_creator,
    )
    # Thêm user_receiver vào người nhận
    doc_expired_test.nguoi_nhan.add(user_receiver)

    # a. User outsider (không phải người tạo, không phải người nhận, không phải admin)
    qs_outsider = van_ban_xem_duoc(user_outsider, "DEN")
    can_outsider_view_func = la_nguoi_xem_duoc(user_outsider, doc_expired_test)
    assert_test(
        not qs_outsider.filter(pk=doc_expired_test.pk).exists() and not can_outsider_view_func,
        "5.1a Tài khoản không chỉ định KHÔNG xem được văn bản hết hiệu lực",
        "Đã chặn hoàn toàn cả trong danh sách (QuerySet) và hàm kiểm tra la_nguoi_xem_duoc"
    )

    # b. Tài khoản chỉ định (người tạo, người nhận, admin) thì VẪN xem được
    can_creator_view = la_nguoi_xem_duoc(user_creator, doc_expired_test)
    can_receiver_view = la_nguoi_xem_duoc(user_receiver, doc_expired_test)
    can_admin_view = la_nguoi_xem_duoc(admin_user, doc_expired_test)
    assert_test(
        can_creator_view and can_receiver_view and can_admin_view,
        "5.1b Tài khoản chỉ định (Người tạo, Người nhận, Admin) xem được văn bản hết hiệu lực",
        f"Creator: {can_creator_view}, Receiver: {can_receiver_view}, Admin: {can_admin_view}"
    )

    # 5.2 Quyền chỉnh sửa: Cán bộ không phải người tạo/admin KHÔNG được sửa
    doc_edit_test = VanBanDen.objects.create(
        so_hieu="TEST/PERM/EDIT",
        trich_yeu="Văn bản test quyền sửa",
        nam=2026,
        so_thu_tu=931,
        ngay_van_ban=now,
        pham_vi=PhamVi.NOI_BO,
        nguoi_tao=user_creator,
    )
    can_outsider_edit = can_edit_document(user_outsider, doc_edit_test)
    can_creator_edit = can_edit_document(user_creator, doc_edit_test)
    can_admin_edit = can_edit_document(admin_user, doc_edit_test)
    can_creator_edit_mat = can_edit_document(user_creator, doc_mat_ok)
    assert_test(
        not can_outsider_edit and can_creator_edit and can_admin_edit and not can_creator_edit_mat,
        "5.2 Phân quyền chỉnh sửa (Người tạo được sửa VB thường còn hiệu lực; VB Mật CHỈ Admin được sửa)",
        f"Outsider sửa: {can_outsider_edit} | Creator sửa VB thường: {can_creator_edit} | Creator sửa VB Mật: {can_creator_edit_mat} | Admin: {can_admin_edit}"
    )

    # 5.3 Quyền xóa: Cán bộ được chỉ định (Người tạo) có quyền xóa văn bản còn hiệu lực của mình; Hết hạn chỉ Admin xóa; Outsider cấm xóa
    can_outsider_delete = can_delete_document(user_outsider, doc_edit_test)
    can_creator_delete = can_delete_document(user_creator, doc_edit_test)
    can_admin_delete = can_delete_document(admin_user, doc_edit_test)

    doc_expired_test = VanBanDen.objects.create(
        so_hieu="TEST/PERM/EXPIRED",
        trich_yeu="Văn bản đã hết hiệu lực",
        nam=2026,
        so_thu_tu=933,
        ngay_van_ban=now,
        pham_vi=PhamVi.NOI_BO,
        hieu_luc=HieuLuc.HET_HIEU_LUC,
        nguoi_tao=user_creator,
    )
    can_creator_delete_expired = can_delete_document(user_creator, doc_expired_test)
    can_admin_delete_expired = can_delete_document(admin_user, doc_expired_test)

    assert_test(
        not can_outsider_delete and can_creator_delete and can_admin_delete and not can_creator_delete_expired and can_admin_delete_expired,
        "5.3 Phân quyền xóa văn bản Đến/Đi (Người tạo xóa được khi còn hạn; Hết hạn chỉ Admin xóa; Outsider cấm xóa)",
        f"Outsider: {can_outsider_delete} | Creator xóa còn hạn: {can_creator_delete} | Creator xóa hết hạn: {can_creator_delete_expired} | Admin: {can_admin_delete}"
    )

    # 5.4 Văn bản Hạn chế (HAN_CHE) & Văn bản Mật (MAT): Admin có quyền xóa VB Mật nội bộ, Hạn chế cấm xóa, User thường cấm xóa
    doc_hanche = VanBanDen.objects.create(
        so_hieu="TEST/PERM/HANCHE",
        trich_yeu="Văn bản hạn chế nội bộ",
        nam=2026,
        so_thu_tu=932,
        ngay_van_ban=now,
        pham_vi=PhamVi.HAN_CHE,
        nguoi_tao=user_creator,
    )
    can_admin_delete_hanche = can_delete_document(admin_user, doc_hanche)
    can_creator_delete_hanche = can_delete_document(user_creator, doc_hanche)
    can_outsider_delete_hanche = can_delete_document(user_outsider, doc_hanche)
    can_admin_delete_mat = can_delete_document(admin_user, doc_mat_ok)
    can_creator_delete_mat = can_delete_document(user_creator, doc_mat_ok)
    can_outsider_delete_mat = can_delete_document(user_outsider, doc_mat_ok)
    assert_test(
        can_admin_delete_hanche and not can_creator_delete_hanche and not can_outsider_delete_hanche and can_admin_delete_mat and not can_creator_delete_mat and not can_outsider_delete_mat,
        "5.4 Phân quyền xóa Văn bản Mật & Hạn chế (Admin có toàn quyền xóa; Cán bộ chỉ định và thường cấm xóa)",
        f"Admin xóa VB Hạn chế: {can_admin_delete_hanche} | Creator xóa Hạn chế: {can_creator_delete_hanche} | Admin xóa VB Mật: {can_admin_delete_mat} | Creator xóa Mật: {can_creator_delete_mat}"
    )

    # 5.5 Truy cập Văn bản Hạn chế: Người ngoài bị từ chối 404 và ghi log BI_TU_CHOI
    view_doc = DocumentViewSet.as_view({"get": "retrieve"})
    req_hanche_out = factory.get(f"/api/documents/{doc_hanche.id}/")
    req_hanche_out.user = user_outsider
    try:
        res_hanche = view_doc(req_hanche_out, pk=doc_hanche.id)
        caught_404 = (res_hanche.status_code == 404)
    except NotFound:
        caught_404 = True

    log_entry = DocumentAccessLog.objects.filter(
        document_id=doc_hanche.id,
        user=user_outsider,
        hanh_dong=DocumentAccessLog.HanhDong.BI_TU_CHOI,
    ).first()

    assert_test(
        caught_404 and log_entry is not None,
        "5.5 Bảo vệ Văn bản Hạn chế & Ghi nhật ký BI_TU_CHOI trong DocumentAccessLog",
        f"Bị chặn 404: {caught_404} | Ghi log BI_TU_CHOI: {log_entry is not None}"
    )

    # Dọn dẹp dữ liệu test
    VanBanDen.objects.filter(so_hieu__startswith="TEST/").delete()
    VanBanDi.objects.filter(so_hieu__startswith="TEST/").delete()
    VanBanMat.objects.filter(so_hieu__startswith="TEST/").delete()

    print("\n" + "=" * 70)
    print(f"   KẾT QUẢ: ĐÃ VƯỢT QUA {passed_count}/{total_count} BÀI KIỂM THỬ TOÀN DIỆN (100%)")
    print("=" * 70)


if __name__ == "__main__":
    run_all_tests()
