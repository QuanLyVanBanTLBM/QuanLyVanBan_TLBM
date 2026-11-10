import datetime
import os
from django.contrib.auth.hashers import make_password
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from organizations.models import KhoiKhuVuc, DonVi
from accounts.models import Employee, Position
from accounts.standard_positions import ADMIN_POSITION, STANDARD_POSITIONS

KHOI_DATA = [
    ("HỘI ĐỒNG QUẢN TRỊ", 1),
    ("VĂN PHÒNG HỘI ĐỒNG QUẢN TRỊ", 2),
    ("BAN TỔNG GIÁM ĐỐC", 3),
    ("VĂN PHÒNG BAN ĐIỀU HÀNH TẠI TP.HCM & HÀ NỘI", 4),
    ("KHỐI KINH DOANH", 5),
    ("KHỐI NGHIỆP VỤ", 6),
    ("KHỐI HỖ TRỢ", 7),
    ("KHỐI QUẢN LÝ RỦI RO", 8),
    ("KHỐI TÀI CHÍNH", 9),
    ("KHỐI KẾ TOÁN", 10),
    ("VĂN PHÒNG 2", 11),
    ("KHU VỰC THÀNH PHỐ HỒ CHÍ MINH", 12),
    ("KHU VỰC MIỀN BẮC", 13),
    ("KHU VỰC MIỀN TRUNG TÂY NGUYÊN", 14),
    ("KHU VỰC ĐÔNG NAM BỘ", 15),
    ("GIÁM ĐỊNH VÙNG", 16),
]

DONVI_DATA = [
    ("HỘI ĐỒNG QUẢN TRỊ", "Hội đồng quản trị"),
    ("HỘI ĐỒNG QUẢN TRỊ", "Ban kiểm toán nội bộ"),
    ("VĂN PHÒNG HỘI ĐỒNG QUẢN TRỊ", "Văn phòng hội đồng quản trị"),
    ("BAN TỔNG GIÁM ĐỐC", "Ban tổng giám đốc"),
    ("BAN TỔNG GIÁM ĐỐC", "Giám đốc vùng"),
    ("VĂN PHÒNG BAN ĐIỀU HÀNH TẠI TP.HCM & HÀ NỘI", "Văn phòng ban điều hành"),
    ("KHỐI KINH DOANH", "Ban khách hàng doanh nghiệp"),
    ("KHỐI KINH DOANH", "Ban khách hàng qua môi giới"),
    ("KHỐI KINH DOANH", "Ban Bancassurance"),
    ("KHỐI KINH DOANH", "Ban khách hàng cá nhân"),
    ("KHỐI KINH DOANH", "Ban chăm sóc khách hàng ĐT"),
    ("KHỐI KINH DOANH", "Ban dự án phát triển sản phẩm liên kết với các công ty dịch vụ viễn thông"),
    ("KHỐI KINH DOANH", "Ban dự án lớn"),
    ("KHỐI KINH DOANH", "Ban dự án khách hàng qua đại lý"),
    ("KHỐI NGHIỆP VỤ", "Ban bảo hiểm con người"),
    ("KHỐI NGHIỆP VỤ", "Ban bảo hiểm tài sản kỹ thuật"),
    ("KHỐI NGHIỆP VỤ", "Ban tái bảo hiểm"),
    ("KHỐI NGHIỆP VỤ", "Ban bảo hiểm xe cơ giới"),
    ("KHỐI NGHIỆP VỤ", "Ban bảo hiểm hàng hải, hàng không, dầu khí, năng lượng"),
    ("KHỐI HỖ TRỢ", "Lãnh đạo khối"),
    ("KHỐI HỖ TRỢ", "Ban hành chính quản trị"),
    ("KHỐI HỖ TRỢ", "Ban nhân sự"),
    ("KHỐI HỖ TRỢ", "Ban pháp chế"),
    ("KHỐI HỖ TRỢ", "Ban công nghệ thông tin"),
    ("KHỐI HỖ TRỢ", "Ban truyền thông và marketing"),
    ("KHỐI QUẢN LÝ RỦI RO", "Ban quản lý rủi ro và tuân thủ"),
    ("KHỐI TÀI CHÍNH", "Ban đầu tư"),
    ("KHỐI TÀI CHÍNH", "Ban tài chính kế hoạch"),
    ("KHỐI TÀI CHÍNH", "Ban dự án MIS"),
    ("KHỐI KẾ TOÁN", "Lãnh đạo khối"),
    ("KHỐI KẾ TOÁN", "Ban kế toán"),
    ("VĂN PHÒNG 2", "Văn phòng 2"),
    ("KHU VỰC THÀNH PHỐ HỒ CHÍ MINH", "Sở giao dịch Bảo Long"),
    ("KHU VỰC THÀNH PHỐ HỒ CHÍ MINH", "Bảo Long TP.HCM"),
    ("KHU VỰC THÀNH PHỐ HỒ CHÍ MINH", "Bảo Long Sài Gòn"),
    ("KHU VỰC THÀNH PHỐ HỒ CHÍ MINH", "Bảo Long Gia Định"),
    ("KHU VỰC THÀNH PHỐ HỒ CHÍ MINH", "Bảo Long Bến Thành"),
    ("KHU VỰC THÀNH PHỐ HỒ CHÍ MINH", "Bảo Long Nam Sài Gòn"),
    ("KHU VỰC THÀNH PHỐ HỒ CHÍ MINH", "Bảo Long Tân Sơn Nhất"),
    ("KHU VỰC THÀNH PHỐ HỒ CHÍ MINH", "Bảo Long Đông Sài Gòn"),
    ("KHU VỰC THÀNH PHỐ HỒ CHÍ MINH", "Bảo Long Đông Phương"),
    ("KHU VỰC THÀNH PHỐ HỒ CHÍ MINH", "Trung tâm kinh doanh Thủ Thiêm"),
    ("KHU VỰC MIỀN BẮC", "Bảo Long Hà Nội"),
    ("KHU VỰC MIỀN BẮC", "Bảo Long Thủ Đô"),
    ("KHU VỰC MIỀN BẮC", "Bảo Long Thăng Long"),
    ("KHU VỰC MIỀN BẮC", "Bảo Long Thái Nguyên"),
    ("KHU VỰC MIỀN BẮC", "Bảo Long Quảng Ninh"),
    ("KHU VỰC MIỀN BẮC", "Bảo Long Hải Phòng"),
    ("KHU VỰC MIỀN BẮC", "Bảo Long Phú Thọ"),
    ("KHU VỰC MIỀN BẮC", "Bảo Long Bắc Ninh"),
    ("KHU VỰC MIỀN BẮC", "Bảo Long Hải Dương"),
    ("KHU VỰC MIỀN BẮC", "Bảo Long Nam Định"),
    ("KHU VỰC MIỀN BẮC", "Bảo Long Vĩnh Phúc"),
    ("KHU VỰC MIỀN BẮC", "Bảo Long Đông Hải"),
    ("KHU VỰC MIỀN BẮC", "Sở giao dịch miền Bắc"),
    ("KHU VỰC MIỀN BẮC", "Bảo Long Ninh Bình"),
    ("KHU VỰC MIỀN BẮC", "Bảo Long Thái Bình"),
    ("KHU VỰC MIỀN BẮC", "Bảo Long Đông Đô"),
    ("KHU VỰC MIỀN BẮC", "Bảo Long Thanh Hóa"),
    ("KHU VỰC MIỀN TRUNG TÂY NGUYÊN", "Bảo Long KV Tây Nguyên (Daklak)"),
    ("KHU VỰC MIỀN TRUNG TÂY NGUYÊN", "Bảo Long Phú Yên"),
    ("KHU VỰC MIỀN TRUNG TÂY NGUYÊN", "Bảo Long Đà Nẵng"),
    ("KHU VỰC MIỀN TRUNG TÂY NGUYÊN", "Bảo Long Trung Bộ (Huế)"),
    ("KHU VỰC MIỀN TRUNG TÂY NGUYÊN", "Bảo Long Bắc Trung Bộ (Nghệ An)"),
    ("KHU VỰC MIỀN TRUNG TÂY NGUYÊN", "Bảo Long Khánh Hòa"),
    ("KHU VỰC MIỀN TRUNG TÂY NGUYÊN", "Bảo Long Bình Định"),
    ("KHU VỰC MIỀN TRUNG TÂY NGUYÊN", "Bảo Long Bình Thuận"),
    ("KHU VỰC MIỀN TRUNG TÂY NGUYÊN", "Bảo Long Quảng Ngãi"),
    ("KHU VỰC MIỀN TRUNG TÂY NGUYÊN", "Bảo Long Gia Lai"),
    ("KHU VỰC MIỀN TRUNG TÂY NGUYÊN", "Bảo Long Lâm Đồng"),
    ("KHU VỰC MIỀN TRUNG TÂY NGUYÊN", "Bảo Long Quảng Bình"),
    ("KHU VỰC MIỀN TRUNG TÂY NGUYÊN", "Trung tâm kinh doanh Sông Hàn"),
    ("KHU VỰC ĐÔNG NAM BỘ", "Bảo Long Bình Dương"),
    ("KHU VỰC ĐÔNG NAM BỘ", "Bảo Long Vũng Tàu"),
    ("KHU VỰC ĐÔNG NAM BỘ", "Bảo Long Đồng Nai"),
    ("KHU VỰC ĐÔNG NAM BỘ", "Bảo Long Tây Ninh"),
    ("KHU VỰC ĐÔNG NAM BỘ", "Bảo Long Long An"),
    ("KHU VỰC ĐÔNG NAM BỘ", "Bảo Long Cần Thơ"),
    ("KHU VỰC ĐÔNG NAM BỘ", "Bảo Long Cà Mau"),
    ("KHU VỰC ĐÔNG NAM BỘ", "Bảo Long Kiên Giang"),
    ("KHU VỰC ĐÔNG NAM BỘ", "Bảo Long Đồng Tháp"),
    ("GIÁM ĐỊNH VÙNG", "Giám định vùng"),
]

# Danh mục chức vụ chuẩn: 22 chức vụ của giảng viên và 3 chức vụ cũ đang được dùng (xem standard_positions).
POSITION_DATA = STANDARD_POSITIONS


SYSTEM_PASSWORD_PLACEHOLDER = "!system_seed_placeholder"


class Command(BaseCommand):
    help = "Seed reference data and bootstrap the system administrator without changing existing accounts"

    def add_arguments(self, parser):
        parser.add_argument(
            "--demo-data", action="store_true", help="create demo accounts with DEMO_PASSWORD"
        )

    def handle(self, *args, **options):
        UserModel = get_user_model()
        admin = UserModel.objects.filter(username="admin").first()
        admin_password = os.environ.get("ADMIN_PASSWORD")
        if admin_password is not None and not admin_password.strip():
            admin_password = None
        if (admin is None or admin.password == SYSTEM_PASSWORD_PLACEHOLDER) and not admin_password:
            raise CommandError("ADMIN_PASSWORD is required to create or initialize the system administrator.")
        demo_password = os.environ.get("DEMO_PASSWORD")
        if demo_password is not None and not demo_password.strip():
            demo_password = None
        if options["demo_data"] and not demo_password:
            raise CommandError("DEMO_PASSWORD is required when --demo-data is selected.")

        self.stdout.write(self.style.NOTICE("==> Seeding reference data..."))
        with transaction.atomic():
            khoi_map = {}
            for ten, thu_tu in KHOI_DATA:
                khoi, _ = KhoiKhuVuc.objects.get_or_create(
                    ten=ten,
                    defaults={"thu_tu_hien_thi": thu_tu},
                )
                khoi_map[ten] = khoi
            self.stdout.write(self.style.SUCCESS(f" [OK] Reference units: {len(khoi_map)}."))

            for idx, (khoi_ten, donvi_ten) in enumerate(DONVI_DATA, start=1):
                khoi = khoi_map.get(khoi_ten)
                if khoi:
                    DonVi.objects.get_or_create(
                        khoi=khoi,
                        ten=donvi_ten,
                        defaults={"stt_uu_tien": idx, "is_public": True},
                    )

            pos_map = {}
            for order, name in POSITION_DATA:
                pos, _ = Position.objects.get_or_create(
                    name=name,
                    defaults={"display_order": order, "is_public": True},
                )
                pos_map[name] = pos
            self.stdout.write(self.style.SUCCESS(f" [OK] Reference positions: {len(pos_map)}."))

            admin_donvi = DonVi.objects.filter(ten="Ban công nghệ thông tin").first() or DonVi.objects.first()
            admin_chucvu = pos_map.get(ADMIN_POSITION)
            admin_defaults = {
                "email": "admin@baolong.vn",
                "password": make_password(admin_password) if admin_password else SYSTEM_PASSWORD_PLACEHOLDER,
                "ho_ten": "Quản trị hệ thống",
                "ngay_sinh": datetime.date(1990, 1, 1),
                "chuc_vu": admin_chucvu,
                "don_vi": admin_donvi,
                "sdt": "0901234567",
                "is_staff": True,
                "is_superuser": True,
                "is_active": True,
            }
            admin, created = UserModel.objects.get_or_create(username="admin", defaults=admin_defaults)
            initialized = False
            if not created and admin.password == SYSTEM_PASSWORD_PLACEHOLDER:
                # This exact unusable sentinel is not a user credential. Initialize it once;
                # subsequent seed runs preserve every existing account field.
                admin.set_password(admin_password)
                admin.save(update_fields=["password"])
                initialized = True
            self.stdout.write(
                self.style.SUCCESS(
                    " [OK] System administrator "
                    + ("created." if created else "initialized from the DDL sentinel." if initialized else "preserved.")
                )
            )

            if options["demo_data"]:
                demo_users = [
                    ("truongphong_cntt", "Trưởng Phòng CNTT", "Trưởng phòng", "0901111222"),
                    ("chuyenvien_cntt", "Chuyên Viên CNTT", "Chuyên viên", "0902222333"),
                    ("vanthu_cntt", "Văn Thư Lưu Trữ", "Văn thư", "0903333444"),
                ]
                created_count = 0
                for username, full_name, position_name, phone in demo_users:
                    _, was_created = UserModel.objects.get_or_create(
                        username=username,
                        defaults={
                            "email": f"{username}@baolong.vn",
                            "password": make_password(demo_password),
                            "ho_ten": full_name,
                            "ngay_sinh": datetime.date(1990, 1, 1),
                            "chuc_vu": pos_map.get(position_name),
                            "don_vi": admin_donvi,
                            "sdt": phone,
                            "trang_thai": Employee.Status.LAM_VIEC,
                            "is_public": True,
                            "is_active": True,
                            "is_staff": False,
                            "is_superuser": False,
                        },
                    )
                    created_count += int(was_created)
                self.stdout.write(self.style.SUCCESS(f" [OK] Demo accounts created: {created_count}."))

        self.stdout.write(self.style.SUCCESS("==> Database seeding completed."))
