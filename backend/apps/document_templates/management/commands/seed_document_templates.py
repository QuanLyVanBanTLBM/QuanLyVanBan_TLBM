from datetime import date
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from document_templates.models import DanhMucTaiLieu, LoaiTaiLieu, TaiLieuChiTiet, ChiTietTaiLieuAttachment


class Command(BaseCommand):
    help = "Khởi tạo dữ liệu mẫu cho Phân hệ Tài liệu & Biểu mẫu (BM) - Nhóm 4"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Xóa sạch toàn bộ dữ liệu tài liệu, loại tài liệu và danh mục trong database",
        )

    def handle(self, *args, **options):
        if options.get("clear"):
            self.stdout.write(self.style.WARNING("Dang xoa sach toan bo du lieu Tai lieu & Bieu mau..."))
            ChiTietTaiLieuAttachment.objects.all().delete()
            TaiLieuChiTiet.objects.all().delete()
            LoaiTaiLieu.objects.all().delete()
            DanhMucTaiLieu.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("-> Da xoa sach toan bo du lieu mau trong co so du lieu!"))
            return

        self.stdout.write(self.style.NOTICE("Dang khoi tao du lieu mau Tai lieu & Bieu mau..."))
        User = get_user_model()

        admin_user, _ = User.objects.get_or_create(
            username="admin",
            defaults={
                "email": "admin@example.com",
                "first_name": "Quan Tri",
                "last_name": "Vien",
                "is_staff": True,
                "is_superuser": True,
            }
        )

        categories_data = [
            {
                "id": 1,
                "stt_uu_tien": 1,
                "ten_tai_lieu": "Tài liệu, Biểu mẫu chung",
                "ky_hieu": "TLBM-CHUNG",
                "ngay_lap": date(2026, 1, 2),
                "ghi_chu": "Toàn bộ quy chế, văn bản biểu mẫu áp dụng chung toàn Tổng công ty",
            },
            {
                "id": 2,
                "stt_uu_tien": 2,
                "ten_tai_lieu": "Hồ sơ Ban Nhân sự",
                "ky_hieu": "HS-BNS",
                "ngay_lap": date(2026, 1, 5),
                "ghi_chu": "Hồ sơ quản trị nhân sự, quy trình tuyển dụng và chế độ chính sách",
            },
            {
                "id": 3,
                "stt_uu_tien": 3,
                "ten_tai_lieu": "Hồ sơ Bảo Long Bến Thành",
                "ky_hieu": "HS-BLBT",
                "ngay_lap": date(2026, 1, 10),
                "ghi_chu": "Hồ sơ tài liệu nghiệp vụ chi nhánh Bảo Long Bến Thành",
            },
            {
                "id": 4,
                "stt_uu_tien": 4,
                "ten_tai_lieu": "Các đơn vị phòng ban cấp 2",
                "ky_hieu": "DV-PB2",
                "ngay_lap": date(2026, 1, 12),
                "ghi_chu": "Tài liệu hành chính lưu hành nội bộ phòng ban đơn vị thành viên cấp 2",
            },
        ]

        cat_objs = {}
        for cdata in categories_data:
            cat, created = DanhMucTaiLieu.objects.update_or_create(
                id=cdata["id"],
                defaults={
                    "stt_uu_tien": cdata["stt_uu_tien"],
                    "ten_tai_lieu": cdata["ten_tai_lieu"],
                    "ky_hieu": cdata["ky_hieu"],
                    "nguoi_lap": admin_user,
                    "ngay_lap": cdata["ngay_lap"],
                    "ghi_chu": cdata["ghi_chu"],
                }
            )
            cat_objs[cat.id] = cat
        self.stdout.write(f"-> Da tao {len(cat_objs)} Danh muc Cap 1")

        types_data = [
            {"id": 1, "dm_id": 1, "ten_loai": "Tài liệu bảo hiểm", "is_public": True, "ghi_chu": "Tài liệu quy tắc và biểu phí"},
            {"id": 2, "dm_id": 1, "ten_loai": "Biểu mẫu bảo hiểm", "is_public": True, "ghi_chu": "Mẫu đơn yêu cầu bảo hiểm"},
            {"id": 3, "dm_id": 1, "ten_loai": "Tờ trình", "is_public": True, "ghi_chu": "Mẫu tờ trình phê duyệt công việc"},
            {"id": 4, "dm_id": 1, "ten_loai": "Quy định", "is_public": True, "ghi_chu": "Quy định nội bộ và an toàn thông tin"},
            {"id": 5, "dm_id": 1, "ten_loai": "Quy chế quản trị", "is_public": True, "ghi_chu": "Quy chế tài chính"},
            {"id": 6, "dm_id": 1, "ten_loai": "Dự thảo nội bộ (Chưa công bố)", "is_public": False, "ghi_chu": "Đang thử nghiệm"},
            {"id": 7, "dm_id": 2, "ten_loai": "Hồ sơ tuyển dụng & HĐLĐ", "is_public": True, "ghi_chu": "Mẫu đánh giá ứng viên"},
            {"id": 8, "dm_id": 2, "ten_loai": "Quyết định bổ nhiệm & Khen thưởng", "is_public": True, "ghi_chu": "Mẫu quyết định nhân sự"},
            {"id": 9, "dm_id": 3, "ten_loai": "Báo cáo doanh số chi nhánh", "is_public": True, "ghi_chu": "Báo cáo định kỳ Bến Thành"},
            {"id": 10, "dm_id": 3, "ten_loai": "Hồ sơ giám định & Bồi thường", "is_public": True, "ghi_chu": "Hồ sơ giải quyết bồi thường"},
            {"id": 11, "dm_id": 4, "ten_loai": "Biên bản họp phòng ban", "is_public": True, "ghi_chu": "Mẫu biên bản tổng kết"},
        ]

        type_objs = {}
        for tdata in types_data:
            loai, created = LoaiTaiLieu.objects.update_or_create(
                id=tdata["id"],
                defaults={
                    "dm_tai_lieu": cat_objs[tdata["dm_id"]],
                    "ten_loai": tdata["ten_loai"],
                    "is_public": tdata["is_public"],
                    "ghi_chu": tdata["ghi_chu"],
                }
            )
            type_objs[loai.id] = loai
        self.stdout.write(f"-> Da tao {len(type_objs)} Loai tai lieu Cap 2")

        documents_data = [
            {
                "id": 1,
                "dm_id": 1,
                "types": [1, 4],
                "ky_hieu": "01/QĐ-BL-2026",
                "tieu_de": "Quy định bảo hiểm xe cơ giới và quy tắc thẩm định rủi ro 2026",
                "ngay_dang": date(2026, 1, 15),
                "noi_ban_hanh": "Ban Giám Đốc",
                "hieu_luc": "CON_HIEU_LUC",
                "ghi_chu": "Áp dụng cho toàn thể cán bộ nhân viên và đại lý trong toàn hệ thống.",
                "hien_thi": "TAT_CA",
                "file_name": "quy_dinh_bao_hiem_xe_2026.pdf",
            },
            {
                "id": 2,
                "dm_id": 1,
                "types": [2],
                "ky_hieu": "02/BM-BT-2026",
                "tieu_de": "Biểu mẫu yêu cầu bồi thường thiệt hại xe cơ giới cá nhân",
                "ngay_dang": date(2026, 1, 20),
                "noi_ban_hanh": "Khối Giám Định Bồi Thường",
                "hieu_luc": "CON_HIEU_LUC",
                "ghi_chu": "Mẫu dùng cho chủ xe khai báo hồ sơ bồi thường trực tuyến hoặc trực tiếp.",
                "hien_thi": "TAT_CA",
                "file_name": "bieu_mau_yeu_cau_boi_thuong_2026.docx",
            },
            {
                "id": 3,
                "dm_id": 1,
                "types": [3],
                "ky_hieu": "03/TTr-VP-2026",
                "tieu_de": "Tờ trình phê duyệt kinh phí trang bị thiết bị văn phòng Q1/2026",
                "ngay_dang": date(2026, 2, 5),
                "noi_ban_hanh": "Văn Phòng Tổng Công Ty",
                "hieu_luc": "CON_HIEU_LUC",
                "ghi_chu": "Đã được Ban Giám Đốc phê duyệt hạn mức 250 triệu đồng.",
                "hien_thi": "TAT_CA",
                "file_name": "to_trinh_kinh_phi_q1_2026.pdf",
            },
            {
                "id": 4,
                "dm_id": 1,
                "types": [4],
                "ky_hieu": "15/QĐ-CD-2020",
                "tieu_de": "Quy định quản lý con dấu và phân cấp thẩm quyền ký văn bản cũ (2020)",
                "ngay_dang": date(2020, 3, 10),
                "noi_ban_hanh": "Ban Kiểm Soát Nội Bộ",
                "hieu_luc": "HET_VA_THAY_THE",
                "ngay_het_hieu_luc": date(2025, 12, 31),
                "link_thay_the": "https://example.com/files/quy_dinh_con_dau_moi_2026.pdf",
                "ghi_chu": "Đã được thay thế bởi Quyết định số 01/2026/QĐ-HĐQT từ 01/01/2026.",
                "hien_thi": "TAT_CA",
                "file_name": "quy_dinh_con_dau_2020_het_hieu_luc.pdf",
            },
            {
                "id": 5,
                "dm_id": 2,
                "types": [7],
                "ky_hieu": "04/HĐLĐ-NS-2026",
                "tieu_de": "Mẫu hợp đồng lao động không xác định thời hạn chuẩn Bộ Luật Lao Động 2026",
                "ngay_dang": date(2026, 1, 8),
                "noi_ban_hanh": "Ban Nhân Sự",
                "hieu_luc": "CON_HIEU_LUC",
                "ghi_chu": "Cập nhật mức đóng BHXH, BHYT và phụ cấp trách nhiệm mới nhất.",
                "hien_thi": "TAT_CA",
                "file_name": "mau_hop_dong_lao_dong_2026.docx",
            },
            {
                "id": 6,
                "dm_id": 2,
                "types": [8],
                "ky_hieu": "05/QĐ-BN-2026",
                "tieu_de": "Quyết định bổ nhiệm Phó Giám đốc Phụ trách Kinh doanh Chi nhánh Bến Thành",
                "ngay_dang": date(2026, 2, 12),
                "noi_ban_hanh": "Tổng Giám Đốc",
                "hieu_luc": "CON_HIEU_LUC",
                "ghi_chu": "Có hiệu lực thi hành kể từ ngày ký. Thời hạn bổ nhiệm 03 năm.",
                "hien_thi": "NOI_BO_PHONG_BAN",
                "file_name": "quyet_dinh_bo_nhiem_pgd_benthanh.pdf",
            },
            {
                "id": 7,
                "dm_id": 3,
                "types": [9],
                "ky_hieu": "06/BC-BLBT-2026",
                "tieu_de": "Báo cáo tổng kết kinh doanh quý IV/2025 và kế hoạch phát triển 2026 - Chi nhánh Bến Thành",
                "ngay_dang": date(2026, 1, 18),
                "noi_ban_hanh": "Chi Nhánh Bảo Long Bến Thành",
                "hieu_luc": "CON_HIEU_LUC",
                "ghi_chu": "Doanh thu năm 2025 đạt 112% kế hoạch được giao.",
                "hien_thi": "NOI_BO_PHONG_BAN",
                "file_name": "bao_cao_kinh_doanh_q4_2025_blbt.pdf",
            },
            {
                "id": 8,
                "dm_id": 3,
                "types": [10],
                "ky_hieu": "08/QT-KN-2024",
                "tieu_de": "Quy trình tiếp nhận và giải quyết khiếu nại bảo hiểm con người phiên bản cũ (2024)",
                "ngay_dang": date(2024, 5, 15),
                "noi_ban_hanh": "Phòng Pháp Chế & Tuân Thủ",
                "hieu_luc": "HET_HIEU_LUC",
                "ngay_het_hieu_luc": date(2025, 6, 30),
                "ghi_chu": "Hết hiệu lực từ 30/06/2025 theo chỉ thị số 09 của Ban Điều Hành.",
                "hien_thi": "TAT_CA",
                "file_name": "quy_trinh_khieu_nai_2024_het_han.pdf",
            },
        ]

        for ddata in documents_data:
            doc, created = TaiLieuChiTiet.objects.update_or_create(
                id=ddata["id"],
                defaults={
                    "dm_tai_lieu": cat_objs[ddata["dm_id"]],
                    "ky_hieu": ddata["ky_hieu"],
                    "tieu_de": ddata["tieu_de"],
                    "ngay_dang": ddata["ngay_dang"],
                    "noi_ban_hanh": ddata["noi_ban_hanh"],
                    "hieu_luc": ddata["hieu_luc"],
                    "ngay_het_hieu_luc": ddata.get("ngay_het_hieu_luc"),
                    "link_thay_the": ddata.get("link_thay_the", ""),
                    "ghi_chu": ddata.get("ghi_chu", ""),
                    "hien_thi": ddata.get("hien_thi", "TAT_CA"),
                    "nguoi_tao": admin_user,
                }
            )
            doc.loai_tai_lieu.set([type_objs[tid] for tid in ddata["types"]])

            # Đính kèm tệp theo chuẩn bảng con 1-N Hướng A
            ChiTietTaiLieuAttachment.objects.update_or_create(
                document=doc,
                name=ddata["file_name"],
                defaults={
                    "path": f"document_templates/{ddata['file_name']}",
                    "file_size": 1024,
                    "mime_type": "application/pdf",
                    "nguoi_tao": admin_user,
                }
            )

        self.stdout.write(self.style.SUCCESS(f"-> Da khoi tao thanh cong {len(documents_data)} tai lieu mau!"))
