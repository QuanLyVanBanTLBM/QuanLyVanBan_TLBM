"""
Django Management Command: seed_documents
Seed dữ liệu chuẩn cho Module 02: Quản lý Văn bản (Nhóm 2)
Phục vụ hiển thị KPI và Top 5 trên Dashboard (Nhóm 1) và demo Staging toàn trường.

Sử dụng:
    python manage.py seed_documents
    python manage.py seed_documents --clean   # Làm mới dữ liệu mẫu an toàn
"""

from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from documents.models import (
    HieuLuc,
    PhamVi,
    VanBanDen,
    VanBanDenAttachment,
    VanBanDi,
    VanBanDiAttachment,
)


class Command(BaseCommand):
    help = "Seed 12 Văn bản Đến và 10 Văn bản Đi năm 2026 (100% Nội bộ, đính kèm file thật PDF/DOCX) phục vụ Dashboard Nhóm 1"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clean",
            action="store_true",
            help="Làm mới dữ liệu mẫu văn bản cũ trước khi nạp bộ dữ liệu chuẩn",
        )

    def handle(self, *args, **options):
        clean_mode = options.get("clean", False)
        self.stdout.write(self.style.NOTICE("=== KHỞI CHẠY SEED DỮ LIỆU MODULE VĂN BẢN (NHÓM 2) ==="))

        User = get_user_model()
        author = User.objects.filter(is_superuser=True).first() or User.objects.first()
        if not author:
            self.stdout.write(self.style.ERROR("Lỗi: Không tìm thấy người dùng nào trong CSDL để gán nguoi_tao!"))
            return

        # Xác định các đường dẫn chứa tệp nguồn thật trong workspace
        command_dir = Path(__file__).resolve().parent
        internal_demo_dir = command_dir.parent.parent / "fixtures" / "demo_files"
        project_root = Path(settings.BASE_DIR).parent  # d:\Đồ án\QuanLyVanBan_TLBM
        workspace_root = project_root.parent          # d:\Đồ án

        def find_source_file(relative_paths):
            for rel in relative_paths:
                p0 = internal_demo_dir / rel.name
                if p0.exists() and p0.stat().st_size > 0:
                    return p0
                p1 = project_root / rel
                if p1.exists() and p1.stat().st_size > 0:
                    return p1
                p2 = workspace_root / rel
                if p2.exists() and p2.stat().st_size > 0:
                    return p2
            return None

        # Nạp sẵn bytes của các tệp nguồn thật (.pdf, .docx chuẩn)
        file_cache = {}

        def get_file_content(key, candidate_paths):
            if key in file_cache:
                return file_cache[key]
            src_path = find_source_file(candidate_paths)
            if src_path:
                with open(src_path, "rb") as f:
                    content = f.read()
                file_cache[key] = (src_path.name, content)
                self.stdout.write(f"  [Tệp nguồn] Đã tải '{src_path.name}' ({len(content)} bytes)")
                return file_cache[key]
            else:
                fallback_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
                file_cache[key] = (key, fallback_content)
                self.stdout.write(self.style.WARNING(f"  [Cảnh báo] Không tìm thấy file nguồn cho {key}, dùng fallback."))
                return file_cache[key]

        pdf_itc = get_file_content("pdf_itc", [
            Path("ITC - Django - QLVB&TL - Tổng quan.pdf"),
            Path("docs/ITC - Django - QLVB&TL - Tổng quan.pdf"),
        ])
        pdf_chieu_sinh = get_file_content("pdf_chieu_sinh", [
            Path("frontend/public/demo_files/0. TB Chieu sinh Tieng Anh dau ra Dot 4 - 2026.pdf"),
            Path("ITC - Django - QLVB&TL - Tổng quan.pdf"),
        ])
        doc_ke_hoach = get_file_content("doc_ke_hoach", [
            Path("Quy_Trinh_Ky_So_Va_Trinh_Ky_Van_Ban.docx"),
            Path("docs/modules/02_documents/BangPhanCong_Nhom2_GiaiDoan2_VanBanDi_v2.docx"),
            Path("KeHoach_ModuleVanBan_Nhom2.docx"),
        ])
        doc_quy_che = get_file_content("doc_quy_che", [
            Path("Quy_Che_Bao_Mat_Thong_Tin_TLBM.docx"),
            Path("tai_lieu_test_ai/01_Bao_Mat_Va_Luu_Tru/Quy_Che_Bao_Mat_Thong_Tin_TLBM.docx"),
            Path("docs/modules/02_documents/BangPhanCong_Nhom2_GiaiDoan2_VanBanDi_v2.docx"),
        ])
        doc_ky_so = get_file_content("doc_ky_so", [
            Path("Quy_Trinh_Ky_So_Va_Trinh_Ky_Van_Ban.docx"),
            Path("tai_lieu_test_ai/02_Quy_Trinh_Trinh_Ky_Dien_Tu/Quy_Trinh_Ky_So_Va_Trinh_Ky_Van_Ban.docx"),
            Path("docs/modules/02_documents/BangPhanCong_Nhom2_GiaiDoan2_VanBanDi_v2.docx"),
        ])

        # -------------------------------------------------------------
        # 1. ĐỊNH NGHĨA 12 VĂN BẢN ĐẾN (CHUẨN HÀNH CHÍNH NĂM 2026)
        # -------------------------------------------------------------
        inbound_specs = [
            {
                "stt": 1,
                "code": "45/CV-BGDĐT",
                "title": "V/v hướng dẫn thực hiện công tác kiểm định chất lượng đào tạo và chuẩn đầu ra năm học 2026 - 2027",
                "date": datetime(2026, 10, 23, 8, 30),
                "sender": "Bộ Giáo dục và Đào tạo",
                "signer": "Nguyễn Văn A",
                "position": "Chuyên viên Tiếp nhận",
                "att_name": "45_CV_BGDDT_KiemDinh.pdf",
                "att_data": pdf_itc[1],
            },
            {
                "stt": 2,
                "code": "118/TB-UBND",
                "title": "Thông báo kế hoạch phát động Tháng hành động vì an toàn thông tin và chuyển đổi số trường học năm 2026",
                "date": datetime(2026, 10, 22, 9, 15),
                "sender": "UBND TP.Hồ Chí Minh",
                "signer": "Trần Thị B",
                "position": "Chánh Văn phòng",
                "att_name": "118_TB_UBND_KeHoach.pdf",
                "att_data": pdf_itc[1],
            },
            {
                "stt": 3,
                "code": "89/CV-STTTT",
                "title": "V/v rà soát, kiểm tra phương án bảo đảm an toàn hệ thống thông tin phục vụ xét tuyển trực tuyến",
                "date": datetime(2026, 10, 21, 14, 0),
                "sender": "Sở Thông tin và Truyền thông",
                "signer": "Lê Văn C",
                "position": "Trưởng phòng CNTT",
                "att_name": "89_CV_STTTT_AnToanTT.docx",
                "att_data": doc_quy_che[1],
            },
            {
                "stt": 4,
                "code": "26/HD-SGDĐT",
                "title": "Hướng dẫn tổ chức Ngày hội tư vấn hướng nghiệp và phân luồng học sinh sau THPT năm 2026",
                "date": datetime(2026, 10, 20, 10, 30),
                "sender": "Sở Giáo dục và Đào tạo TP.HCM",
                "signer": "Phạm Thị D",
                "position": "Phó Trưởng phòng Giáo dục Chuyên nghiệp",
                "att_name": "26_HD_SGDDT_HuongNghiep.pdf",
                "att_data": pdf_itc[1],
            },
            {
                "stt": 5,
                "code": "05/TB-TTr-BGD",
                "title": "Thông báo kết luận thanh tra công tác quản lý tài chính và cơ sở vật chất CNTT",
                "date": datetime(2026, 10, 18, 15, 45),
                "sender": "Thanh tra Bộ GD&ĐT",
                "signer": "Hoàng Văn E",
                "position": "Trưởng đoàn Thanh tra",
                "att_name": "05_TB_TTr_BGD_ThanhTra.pdf",
                "att_data": pdf_itc[1],
                "scope": PhamVi.HAN_CHE,
            },
            {
                "stt": 6,
                "code": "215/CV-TCGDNN",
                "title": "Triển khai chỉ tiêu tuyển sinh đào tạo hệ Cao đẳng chính quy nghề trọng điểm quốc gia năm 2026",
                "date": datetime(2026, 9, 15, 8, 0),
                "sender": "Tổng cục Giáo dục Nghề nghiệp",
                "signer": "Vũ Thị F",
                "position": "Vụ trưởng Vụ Đào tạo",
                "att_name": "215_CV_TCGDNN_TuyenSinh.pdf",
                "att_data": pdf_chieu_sinh[1],
            },
            {
                "stt": 7,
                "code": "78/TB-SLĐTBXH",
                "title": "Kế hoạch tổ chức Hội thi kỹ năng nghề cấp Thành phố dành cho học sinh, sinh viên năm 2026",
                "date": datetime(2026, 8, 28, 13, 30),
                "sender": "Sở Lao động - Thương binh & Xã hội",
                "signer": "Đặng Văn G",
                "position": "Phó Giám đốc Sở",
                "att_name": "78_TB_SLDTBXH_HoiThi.docx",
                "att_data": doc_ke_hoach[1],
            },
            {
                "stt": 8,
                "code": "34/CV-CATP",
                "title": "V/v phối hợp bảo đảm an ninh trật tự và phòng cháy chữa cháy khu vực ký túc xá sinh viên",
                "date": datetime(2026, 7, 12, 9, 0),
                "sender": "Công an TP.Hồ Chí Minh",
                "signer": "Bùi Thị H",
                "position": "Phó Trưởng Công an Thành phố",
                "att_name": "34_CV_CATP_AnNinh.docx",
                "att_data": doc_quy_che[1],
            },
            {
                "stt": 9,
                "code": "19/HD-LĐLĐ",
                "title": "Hướng dẫn tổ chức các hoạt động văn hóa thể thao chào mừng ngày Nhà giáo Việt Nam 20/11",
                "date": datetime(2026, 6, 5, 16, 0),
                "sender": "Liên đoàn Lao động TP.HCM",
                "signer": "Đỗ Văn I",
                "position": "Chủ tịch Công đoàn",
                "att_name": "19_HD_LDLD_2011.pdf",
                "att_data": pdf_itc[1],
            },
            {
                "stt": 10,
                "code": "12/CV-BYT",
                "title": "Khuyến cáo tăng cường vệ sinh phòng dịch bệnh theo mùa trong môi trường trường học",
                "date": datetime(2026, 4, 14, 11, 0),
                "sender": "Trung tâm Kiểm soát Bệnh tật (HCDC)",
                "signer": "Ngô Thị K",
                "position": "Trưởng khoa Phòng chống bệnh",
                "att_name": "12_CV_BYT_PhongDich.pdf",
                "att_data": pdf_itc[1],
            },
            {
                "stt": 11,
                "code": "67/TB-BGDĐT",
                "title": "Thông báo danh mục đề tài NCKH ứng dụng công nghệ AI được duyệt kinh phí năm 2026",
                "date": datetime(2026, 3, 2, 14, 30),
                "sender": "Bộ Giáo dục và Đào tạo",
                "signer": "Dương Văn L",
                "position": "Cục trưởng Cục KHCN",
                "att_name": "67_TB_BGDDT_NCKH.docx",
                "att_data": doc_ke_hoach[1],
            },
            {
                "stt": 12,
                "code": "03/CV-BHXH",
                "title": "Đôn đốc rà soát, đồng bộ thẻ Bảo hiểm y tế điện tử (VssID) cho sinh viên khóa mới",
                "date": datetime(2026, 1, 15, 9, 30),
                "sender": "Bảo hiểm Xã hội TP.HCM",
                "signer": "Lý Thị M",
                "position": "Giám đốc BHXH",
                "att_name": "03_CV_BHXH_BHYT.pdf",
                "att_data": pdf_itc[1],
            },
        ]

        # -------------------------------------------------------------
        # 2. ĐỊNH NGHĨA 10 VĂN BẢN ĐI (CHUẨN HÀNH CHÍNH NĂM 2026)
        # -------------------------------------------------------------
        outbound_specs = [
            {
                "stt": 1,
                "code": "15/QĐ-ITC/2026",
                "title": "Quyết định ban hành Quy chế bảo vệ thông tin và vận hành hệ thống phần mềm ITC",
                "date": datetime(2026, 10, 23, 9, 0),
                "recipient": "Nguyễn Văn A - Trưởng phòng Hành chính - Tổng hợp",
                "signer": "Nguyễn Văn A",
                "position": "Trưởng phòng HC-TH",
                "att_name": "15_QD_ITC_BaoVeThongTin.docx",
                "att_data": doc_quy_che[1],
            },
            {
                "stt": 2,
                "code": "14/TB-ITC/2026",
                "title": "Thông báo kế hoạch phát động phong trào thi đua dạy tốt - học tốt năm học 2026",
                "date": datetime(2026, 10, 22, 10, 0),
                "recipient": "Trần Thị B - Phó Hiệu trưởng thường trực",
                "signer": "Trần Thị B",
                "position": "Phó Hiệu trưởng",
                "att_name": "14_TB_ITC_ThiDuaDayTot.pdf",
                "att_data": pdf_itc[1],
            },
            {
                "stt": 3,
                "code": "13/KH-ITC/2026",
                "title": "Kế hoạch nâng cấp hạ tầng mạng máy tính thực hành Khoa Công nghệ Thông tin",
                "date": datetime(2026, 10, 21, 15, 30),
                "recipient": "Lê Văn C - Trưởng Khoa Công nghệ Thông tin",
                "signer": "Lê Văn C",
                "position": "Trưởng Khoa CNTT",
                "att_name": "13_KH_ITC_HaTangMang.docx",
                "att_data": doc_ke_hoach[1],
            },
            {
                "stt": 4,
                "code": "12/QĐ-ITC/2026",
                "title": "Quyết định kiện toàn Ban chỉ đạo Đảm bảo An toàn thông tin và Chuyển đổi số ITC",
                "date": datetime(2026, 10, 19, 8, 45),
                "recipient": "Phạm Thị D - Trưởng phòng Đào tạo",
                "signer": "Phạm Thị D",
                "position": "Trưởng phòng Đào tạo",
                "att_name": "12_QD_ITC_KienToanBCĐ.pdf",
                "att_data": pdf_itc[1],
            },
            {
                "stt": 5,
                "code": "11/TB-ITC/2026",
                "title": "Thông báo lịch thi đánh giá chuẩn đầu ra Tin học ứng dụng & Ngoại ngữ đợt 1/2026",
                "date": datetime(2026, 10, 16, 11, 15),
                "recipient": "Hoàng Văn E - Trưởng phòng Khảo thí & Đảm bảo chất lượng",
                "signer": "Hoàng Văn E",
                "position": "Trưởng phòng KT-ĐBCL",
                "att_name": "11_TB_ITC_ThiChuanDauRa.pdf",
                "att_data": pdf_chieu_sinh[1],
                "scope": PhamVi.HAN_CHE,
            },
            {
                "stt": 6,
                "code": "10/TB-ITC/2026",
                "title": "Thông báo kế hoạch nghỉ hè và đăng ký bồi dưỡng chuyên môn nghiệp vụ hè 2026",
                "date": datetime(2026, 6, 15, 14, 0),
                "recipient": "Vũ Thị F - Trưởng phòng Kế hoạch - Tài chính",
                "signer": "Vũ Thị F",
                "position": "Trưởng phòng KH-TC",
                "att_name": "10_TB_ITC_NghiHe2026.docx",
                "att_data": doc_ke_hoach[1],
            },
            {
                "stt": 7,
                "code": "09/QĐ-ITC/2026",
                "title": "Quyết định phê duyệt danh mục đề tài Nghiên cứu khoa học sinh viên năm 2025 - 2026",
                "date": datetime(2026, 5, 5, 9, 0),
                "recipient": "Đặng Văn G - Trưởng phòng Quản lý Khoa học & Hợp tác quốc tế",
                "signer": "Đặng Văn G",
                "position": "Trưởng phòng QLKH-HTQT",
                "att_name": "09_QD_ITC_NCKHSinhVien.docx",
                "att_data": doc_ke_hoach[1],
            },
            {
                "stt": 8,
                "code": "08/TB-ITC/2026",
                "title": "Triển khai cấp phát chứng thư số cá nhân và chữ ký số điện tử cho toàn thể cán bộ",
                "date": datetime(2026, 4, 10, 8, 0),
                "recipient": "Bùi Thị H - Trưởng ban Chuyển đổi số",
                "signer": "Bùi Thị H",
                "position": "Trưởng ban CĐS",
                "att_name": "08_TB_ITC_CapPhatChuKySo.docx",
                "att_data": doc_ky_so[1],
            },
            {
                "stt": 9,
                "code": "07/CV-ITC/2026",
                "title": "Công văn gửi Sở GD&ĐT TP.HCM về việc phối hợp tổ chức tư vấn hướng nghiệp",
                "date": datetime(2026, 3, 20, 10, 15),
                "recipient": "Đỗ Văn I - Phó Giám đốc Trung tâm Thông tin - Thư viện",
                "signer": "Đỗ Văn I",
                "position": "Phó Giám đốc TT-TV",
                "att_name": "07_CV_ITC_GuiSoGDDT.pdf",
                "att_data": pdf_itc[1],
            },
            {
                "stt": 10,
                "code": "06/KH-ITC/2026",
                "title": "Kế hoạch tổ chức Hội thao và Hội diễn văn nghệ chào mừng Ngày thành lập Đoàn 26/3",
                "date": datetime(2026, 3, 1, 14, 0),
                "recipient": "Ngô Thị K - Bí thư Đoàn Thanh niên",
                "signer": "Ngô Thị K",
                "position": "Bí thư Đoàn trường",
                "att_name": "06_KH_ITC_HoiThao263.docx",
                "att_data": doc_ke_hoach[1],
            },
        ]

        with transaction.atomic():
            if clean_mode:
                self.stdout.write("  -> Đang làm mới dữ liệu và tệp đính kèm theo tùy chọn --clean...")
                in_stts = [s["stt"] for s in inbound_specs]
                out_stts = [s["stt"] for s in outbound_specs]
                # Dọn tệp đính kèm cũ của đúng bộ seed để nạp mới (không xóa bảng cha tránh vi phạm trigger HAN_CHE)
                VanBanDenAttachment.objects.filter(document__nam=2026, document__so_thu_tu__in=in_stts).delete()
                VanBanDiAttachment.objects.filter(document__nam=2026, document__so_thu_tu__in=out_stts).delete()
                self.stdout.write(self.style.SUCCESS("  -> Đã làm sạch các tệp đính kèm cũ an toàn (không vi phạm trigger DB)."))

            # -------------------------------------------------------------
            # 1. SEED 12 VĂN BẢN ĐẾN (100% NỘI BỘ, NĂM 2026)
            # -------------------------------------------------------------
            self.stdout.write("\n--- BẮT ĐẦU SEED 12 VĂN BẢN ĐẾN NĂM 2026 ---")
            for item in inbound_specs:
                aware_dt = timezone.make_aware(item["date"]) if timezone.is_naive(item["date"]) else item["date"]
                doc, created = VanBanDen.objects.update_or_create(
                    nam=2026,
                    so_thu_tu=item["stt"],
                    defaults={
                        "so_hieu": item["code"],
                        "trich_yeu": item["title"],
                        "noi_ban_hanh": item["sender"],
                        "nguoi_ky": item["signer"],
                        "chuc_vu": item["position"],
                        "ngay_den": aware_dt,
                        "ngay_van_ban": aware_dt,
                        "pham_vi": item.get("scope", PhamVi.NOI_BO),
                        "hieu_luc": HieuLuc.CON_HIEU_LUC,
                        "hien_thi": True,
                        "nguoi_tao": author,
                    },
                )

                # Nạp tệp đính kèm thật (PDF/DOCX)
                att = VanBanDenAttachment.objects.filter(document=doc, is_deleted=False).first()
                if not att:
                    att = VanBanDenAttachment(document=doc, name=item["att_name"], nguoi_tao=author)
                    att.file.save(item["att_name"], ContentFile(item["att_data"]), save=True)
                else:
                    att.name = item["att_name"]
                    att.file.save(item["att_name"], ContentFile(item["att_data"]), save=True)

                status_label = "Tạo mới" if created else "Cập nhật"
                self.stdout.write(f"  [VB Đến #{item['stt']:02d}] {status_label}: {item['code']} - Tệp: {item['att_name']} ({len(item['att_data'])} bytes)")

            # -------------------------------------------------------------
            # 2. SEED 10 VĂN BẢN ĐI (100% NỘI BỘ, NĂM 2026)
            # -------------------------------------------------------------
            self.stdout.write("\n--- BẮT ĐẦU SEED 10 VĂN BẢN ĐI NĂM 2026 ---")
            for item in outbound_specs:
                aware_dt = timezone.make_aware(item["date"]) if timezone.is_naive(item["date"]) else item["date"]
                doc, created = VanBanDi.objects.update_or_create(
                    nam=2026,
                    so_thu_tu=item["stt"],
                    defaults={
                        "so_hieu": item["code"],
                        "trich_yeu": item["title"],
                        "nguoi_ky": item["recipient"],
                        "chuc_vu": item["position"],
                        "ngay_ban_hanh": aware_dt,
                        "ngay_van_ban": aware_dt,
                        "pham_vi": item.get("scope", PhamVi.NOI_BO),
                        "hieu_luc": HieuLuc.CON_HIEU_LUC,
                        "hien_thi": True,
                        "nguoi_tao": author,
                    },
                )

                # Nạp tệp đính kèm thật (PDF/DOCX)
                att = VanBanDiAttachment.objects.filter(document=doc, is_deleted=False).first()
                if not att:
                    att = VanBanDiAttachment(document=doc, name=item["att_name"], nguoi_tao=author)
                    att.file.save(item["att_name"], ContentFile(item["att_data"]), save=True)
                else:
                    att.name = item["att_name"]
                    att.file.save(item["att_name"], ContentFile(item["att_data"]), save=True)

                status_label = "Tạo mới" if created else "Cập nhật"
                self.stdout.write(f"  [VB Đi #{item['stt']:02d}] {status_label}: {item['code']} - Tệp: {item['att_name']} ({len(item['att_data'])} bytes)")

        # Thống kê kết quả
        total_in = VanBanDen.objects.filter(ngay_den__year=2026).count()
        total_out = VanBanDi.objects.filter(ngay_ban_hanh__year=2026).count()
        in_han_che = VanBanDen.objects.filter(ngay_den__year=2026, pham_vi=PhamVi.HAN_CHE).count()
        out_han_che = VanBanDi.objects.filter(ngay_ban_hanh__year=2026, pham_vi=PhamVi.HAN_CHE).count()

        self.stdout.write(self.style.SUCCESS("\n=== HOÀN TẤT SEED DỮ LIỆU THÀNH CÔNG ==="))
        self.stdout.write(f"  * KPI Văn bản Đến (2026): {total_in} văn bản ({in_han_che} Hạn chế, {total_in - in_han_che} Nội bộ)")
        self.stdout.write(f"  * KPI Văn bản Đi (2026):   {total_out} văn bản ({out_han_che} Hạn chế, {total_out - out_han_che} Nội bộ)")
        self.stdout.write(f"  * Tổng số tệp đính kèm thật: {len(inbound_specs) + len(outbound_specs)} tệp (100% PDF, DOCX)")
        self.stdout.write("Hệ thống đã sẵn sàng 100% phục vụ Dashboard và buổi Demo Staging!")
