import os
import django
from django.utils import timezone
from datetime import datetime, timezone as dt_timezone

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from documents.models import (
    VanBanDen,
    VanBanDenAttachment,
    DocumentViewLog,
    HieuLuc,
    PhamVi,
)
from documents.services import sync_replacement_document

User = get_user_model()

def run_seed():
    print("=== BẮT ĐẦU TẠO DỮ LIỆU KIỂM THỬ TOÀN DIỆN CHO VĂN BẢN ĐẾN ===")

    def get_or_create_custom_user(username, email, password, full_name):
        u = User.objects.filter(username=username).first()
        if not u:
            parts = full_name.split()
            first = " ".join(parts[1:]) if len(parts) > 1 else full_name
            last = parts[0] if len(parts) > 1 else ""
            u = User(username=username, email=email)
            u.set_password(password)
            if hasattr(u, "ho_ten"):
                u.ho_ten = full_name
            if hasattr(u, "first_name"):
                u.first_name = first
            if hasattr(u, "last_name"):
                u.last_name = last
            u.save()
        return u

    admin_user = User.objects.filter(username="admin").first()
    if not admin_user:
        admin_user = User.objects.create_superuser("admin", "admin@example.com", "admin123")

    canbo_user = get_or_create_custom_user("canbo", "canbo@example.com", "canbo123", "Nguyễn Văn Cán Bộ")
    tp_user = get_or_create_custom_user("truongphong_cntt", "tp@example.com", "pass123", "Trần Trưởng Phòng")
    vanthu_user = get_or_create_custom_user("vanthu_cntt", "vanthu@example.com", "pass123", "Lê Thị Văn Thư")

    now = timezone.now()

    # Dọn dẹp các văn bản test nếu đã tồn tại để tạo mới tinh
    test_so_hieus = [
        "101/QĐ-UBND",
        "102/QĐ-UBND",
        "55/HD-STTTT",
        "12/TB-VP",
        "88/KH-CNTT",
        "42/BC-STC",
    ]
    VanBanDen.objects.filter(so_hieu__in=test_so_hieus).delete()

    # ── 1. VB 1: Cũ (Sẽ bị thay thế) ─────────────────────────────────
    vb1 = VanBanDen.objects.create(
        so_hieu="101/QĐ-UBND",
        nam=2025,
        trich_yeu="Quy chế tiếp nhận và xử lý văn bản năm 2025 (Bị thay thế bởi QĐ 102/QĐ-UBND)",
        ngay_den=datetime(2025, 3, 10, 8, 30, tzinfo=dt_timezone.utc),
        ngay_van_ban=datetime(2025, 3, 9, 0, 0, tzinfo=dt_timezone.utc),
        noi_ban_hanh="Ủy ban Nhân dân Thành phố",
        nguoi_ky="Trần Văn Nam",
        chuc_vu="Chủ tịch UBND",
        danh_muc_ho_so="Hồ sơ Quản lý Hành chính & Nhân sự",
        ten_loai_van_ban="Quyết định",
        hieu_luc=HieuLuc.CON_HIEU_LUC,
        pham_vi=PhamVi.NOI_BO,
        nguoi_tao=admin_user,
    )
    print(f"[OK] Đã tạo VB 1: {vb1.so_hieu} (Ban đầu Còn hiệu lực)")

    # ── 2. VB 2: Mới (Thay thế cho VB 1) ────────────────────────────
    vb2 = VanBanDen.objects.create(
        so_hieu="102/QĐ-UBND",
        nam=2026,
        trich_yeu="Quyết định ban hành Quy chế văn thư lưu trữ điện tử mới 2026 (Thay thế cho QĐ 101/QĐ-UBND)",
        ngay_den=datetime(2026, 1, 15, 9, 0, tzinfo=dt_timezone.utc),
        ngay_van_ban=datetime(2026, 1, 14, 0, 0, tzinfo=dt_timezone.utc),
        noi_ban_hanh="Ủy ban Nhân dân Thành phố",
        nguoi_ky="Trần Văn Nam",
        chuc_vu="Chủ tịch UBND",
        danh_muc_ho_so="Hồ sơ Quản lý Hành chính & Nhân sự",
        ten_loai_van_ban="Quyết định",
        hieu_luc=HieuLuc.CON_HIEU_LUC,
        link_thay_the="101/QĐ-UBND",
        pham_vi=PhamVi.NOI_BO,
        nguoi_tao=admin_user,
    )
    # Kích hoạt nghiệp vụ đồng bộ thay thế 2 chiều
    sync_replacement_document(vb2)
    vb1.refresh_from_db()
    print(f"[OK] Đã tạo VB 2: {vb2.so_hieu} (Còn hiệu lực, thay thế cho: {vb2.link_thay_the})")
    print(f"     => VB 1 {vb1.so_hieu} tự động chuyển thành: {vb1.hieu_luc} (Link: {vb1.link_thay_the})")

    # ── 3. VB 3: Còn hiệu lực 1 phần ─────────────────────────────────
    vb3 = VanBanDen.objects.create(
        so_hieu="55/HD-STTTT",
        nam=2026,
        trich_yeu="Hướng dẫn kết nối trục liên thông văn bản quốc gia và chia sẻ dữ liệu số giai đoạn 2026",
        ngay_den=datetime(2026, 2, 20, 14, 15, tzinfo=dt_timezone.utc),
        ngay_van_ban=datetime(2026, 2, 19, 0, 0, tzinfo=dt_timezone.utc),
        noi_ban_hanh="Sở Thông tin và Truyền thông",
        nguoi_ky="Nguyễn Hoàng Minh",
        chuc_vu="Phó Giám đốc Sở",
        danh_muc_ho_so="Hồ sơ Chuyển đổi số & CNTT 2026",
        ten_loai_van_ban="Hướng dẫn",
        hieu_luc=HieuLuc.CON_HIEU_LUC_1_PHAN,
        pham_vi=PhamVi.NOI_BO,
        nguoi_tao=canbo_user,
    )
    print(f"[OK] Đã tạo VB 3: {vb3.so_hieu} (Còn hiệu lực 1 phần)")

    # ── 4. VB 4: Hết hiệu lực ───────────────────────────────────────
    vb4 = VanBanDen.objects.create(
        so_hieu="12/TB-VP",
        nam=2024,
        trich_yeu="Thông báo lịch phân công trực Tết Nguyên đán Giáp Thìn năm 2024",
        ngay_den=datetime(2024, 1, 25, 10, 0, tzinfo=dt_timezone.utc),
        ngay_van_ban=datetime(2024, 1, 24, 0, 0, tzinfo=dt_timezone.utc),
        ngay_het_hieu_luc=datetime(2024, 2, 15, 23, 59, tzinfo=dt_timezone.utc),
        noi_ban_hanh="Văn phòng UBND Thành phố",
        nguoi_ky="Lê Thu Hà",
        chuc_vu="Chánh Văn phòng",
        danh_muc_ho_so="Hồ sơ Quản lý Hành chính & Nhân sự",
        ten_loai_van_ban="Thông báo",
        hieu_luc=HieuLuc.HET_HIEU_LUC,
        pham_vi=PhamVi.NOI_BO,
        nguoi_tao=canbo_user,
    )
    print(f"[OK] Đã tạo VB 4: {vb4.so_hieu} (Hết hiệu lực từ 15/02/2024)")

    # ── 5. VB 5: Chuẩn có file đính kèm PDF + Audit view log ─────────
    vb5 = VanBanDen.objects.create(
        so_hieu="88/KH-CNTT",
        nam=2026,
        trich_yeu="Kế hoạch nâng cấp hạ tầng CNTT, an toàn thông tin mạng và chuyển đổi số năm 2026",
        ngay_den=datetime(2026, 3, 5, 8, 45, tzinfo=dt_timezone.utc),
        ngay_van_ban=datetime(2026, 3, 4, 0, 0, tzinfo=dt_timezone.utc),
        noi_ban_hanh="Trung tâm Công nghệ Thông tin",
        nguoi_ky="Đặng Quốc Bảo",
        chuc_vu="Giám đốc Trung tâm",
        danh_muc_ho_so="Hồ sơ Chuyển đổi số & CNTT 2026",
        ten_loai_van_ban="Kế hoạch",
        hieu_luc=HieuLuc.CON_HIEU_LUC,
        pham_vi=PhamVi.NOI_BO,
        nguoi_tao=tp_user,
    )

    # Tạo tệp đính kèm PDF thật
    pdf_content = (
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n"
        b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>endobj\n"
        b"xref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000052 00000 n\n0000000102 00000 n\n"
        b"trailer<</Size 4/Root 1 0 R>>\nstartxref\n185\n%%EOF"
    )
    att = VanBanDenAttachment(
        document=vb5,
        name="Ke_hoach_CNTT_2026.pdf",
        nguoi_tao=tp_user,
    )
    att.file.save("Ke_hoach_CNTT_2026.pdf", ContentFile(pdf_content), save=True)
    print(f"[OK] Đã tạo VB 5: {vb5.so_hieu} kèm file đính kèm: {att.name}")

    # Ghi log lịch sử người đã xem thực tế vào CSDL
    DocumentViewLog.objects.filter(document_type="vanbanden", document_id=vb5.id).delete()
    users_to_log = list(User.objects.all()[:4])
    logged_count = 0
    for u in users_to_log:
        try:
            DocumentViewLog.objects.create(
                document_type="vanbanden",
                document_id=vb5.id,
                user=u,
            )
            logged_count += 1
        except Exception as e:
            print(f"Bỏ qua user {u.username}: {e}")
    print(f"[OK] Đã gắn {logged_count} lượt xem vào DocumentViewLog cho VB 5")

    # ── 6. VB 6: Báo cáo tài chính ──────────────────────────────────
    vb6 = VanBanDen.objects.create(
        so_hieu="42/BC-STC",
        nam=2026,
        trich_yeu="Báo cáo quyết toán dự toán kinh phí mua sắm trang thiết bị CNTT năm 2025",
        ngay_den=datetime(2026, 3, 12, 15, 30, tzinfo=dt_timezone.utc),
        ngay_van_ban=datetime(2026, 3, 11, 0, 0, tzinfo=dt_timezone.utc),
        noi_ban_hanh="Sở Tài chính",
        nguoi_ky="Phạm Hồng Sơn",
        chuc_vu="Phó Giám đốc Sở",
        danh_muc_ho_so="Hồ sơ Tài chính & Dự toán ngân sách",
        ten_loai_van_ban="Báo cáo",
        hieu_luc=HieuLuc.CON_HIEU_LUC,
        pham_vi=PhamVi.NOI_BO,
        nguoi_tao=admin_user,
    )
    print(f"[OK] Đã tạo VB 6: {vb6.so_hieu} (Thuộc HS Tài chính & Loại Báo cáo)")

    print("\n=== HOÀN TẤT SEED DỮ LIỆU THÀNH CÔNG 100% ===")

if __name__ == "__main__":
    run_seed()
