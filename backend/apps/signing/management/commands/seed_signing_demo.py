import hashlib
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from documents.models import VanBanDi
from signing import enums
from signing.models import (
    SigningAttempt, SigningProcess, SigningProcessStep, SigningProcessStepSigner,
    SigningRequest, SigningRequestStep, SigningRequestStepSigner,
)

User = get_user_model()

MA_QUY_TRINH = "DEMO-QT"
TIEN_TO_SO_HIEU = "DEMO-KY-"

# (trích yếu văn bản đi, trạng thái yêu cầu, số ngày kể từ lúc trình)
KICH_BAN = [
    ("Tờ trình đề xuất mua sắm thiết bị phòng máy năm 2026", enums.TrangThaiYeuCau.CHO_KY, 1),
    ("Quyết định thành lập hội đồng nghiệm thu đề tài cấp cơ sở", enums.TrangThaiYeuCau.CHO_KY, 2),
    ("Kế hoạch tổ chức hội nghị tổng kết công tác quý IV", enums.TrangThaiYeuCau.CHO_KY, 3),
    ("Báo cáo kết quả thực hiện nhiệm vụ khoa học công nghệ", enums.TrangThaiYeuCau.HOAN_THANH, 5),
    ("Công văn đề nghị gia hạn hợp đồng thuê bao đường truyền", enums.TrangThaiYeuCau.TU_CHOI, 6),
]

NGUOI_TRINH = [
    ("demo_nguoi_trinh_1", "Nguyễn Văn An"),
    ("demo_nguoi_trinh_2", "Trần Thị Bình"),
]


class Command(BaseCommand):
    help = (
        "Tạo dữ liệu mẫu trình ký cho một tài khoản người ký: 3 yêu cầu chờ ký, "
        "1 đã ký, 1 từ chối. Chạy lại không tạo trùng."
    )

    def add_arguments(self, parser):
        parser.add_argument("--user", required=True, help="username tài khoản đăng nhập đóng vai người ký")

    @transaction.atomic
    def handle(self, *args, user, **options):
        try:
            nguoi_ky = User.objects.get(username=user)
        except User.DoesNotExist:
            raise CommandError(f"Không có tài khoản '{user}'. Tạo tài khoản trước khi seed.")

        nguoi_trinh = [self._nguoi_trinh(*item) for item in NGUOI_TRINH]
        quy_trinh, buoc = self._quy_trinh(nguoi_ky, nguoi_trinh[0])

        tao_moi = 0
        for i, (tieu_de, trang_thai, so_ngay) in enumerate(KICH_BAN, start=1):
            so_hieu = f"{TIEN_TO_SO_HIEU}{nguoi_ky.pk}-{i}"
            if VanBanDi.objects.filter(so_hieu=so_hieu).exists():
                continue
            ngay_gui = timezone.now() - timedelta(days=so_ngay)
            van_ban = VanBanDi.objects.create(
                so_hieu=so_hieu, trich_yeu=tieu_de, nam=ngay_gui.year, nguoi_tao=nguoi_trinh[i % 2],
            )
            self._yeu_cau(van_ban, trang_thai, ngay_gui, quy_trinh, buoc, nguoi_ky, nguoi_trinh[i % 2])
            tao_moi += 1

        cho_ky = SigningRequestStepSigner.objects.filter(
            nguoi_ky=nguoi_ky, trang_thai=enums.TrangThaiNguoiKy.CHO_KY,
            buoc_ky__luot_trinh__trinh_ky__trang_thai=enums.TrangThaiYeuCau.CHO_KY,
        ).count()
        self.stdout.write(self.style.SUCCESS(
            f"Tài khoản '{user}': tạo mới {tao_moi} yêu cầu; tổng số yêu cầu đang chờ ký: {cho_ky}."
        ))

    def _nguoi_trinh(self, username, ho_ten):
        # create_user không truyền mật khẩu => mật khẩu không dùng được; chức vụ, đơn vị lấy mặc định của manager.
        user = User.objects.filter(username=username).first()
        return user or User.objects.create_user(username, ho_ten=ho_ten)

    def _quy_trinh(self, nguoi_ky, nguoi_tao):
        quy_trinh, _ = SigningProcess.objects.get_or_create(
            ma_quy_trinh=MA_QUY_TRINH, phien_ban=1,
            defaults=dict(
                ten_quy_trinh="Quy trình ký demo một cấp", trang_thai=enums.TrangThaiQuyTrinh.HOAT_DONG,
                pham_vi=enums.PhamViQuyTrinh.CONG_TY, create_by=nguoi_tao,
            ),
        )
        buoc, _ = SigningProcessStep.objects.get_or_create(
            quy_trinh=quy_trinh, thu_tu=1, defaults=dict(cap_ky=1, ten_cap_ky="Lãnh đạo ký duyệt"),
        )
        SigningProcessStepSigner.objects.get_or_create(
            buoc_quy_trinh=buoc, nguoi_ky=nguoi_ky, defaults=dict(thu_tu=1),
        )
        return quy_trinh, buoc

    def _yeu_cau(self, van_ban, trang_thai, ngay_gui, quy_trinh, buoc, nguoi_ky, nguoi_trinh):
        T = enums.TrangThaiYeuCau
        trang_thai_signer = {
            T.CHO_KY: enums.TrangThaiNguoiKy.CHO_KY,
            T.HOAN_THANH: enums.TrangThaiNguoiKy.DA_KY,
            T.TU_CHOI: enums.TrangThaiNguoiKy.TU_CHOI,
        }[trang_thai]
        ket_thuc = ngay_gui + timedelta(hours=4)
        ma_bam = hashlib.sha256(van_ban.so_hieu.encode()).hexdigest()

        yeu_cau = SigningRequest.objects.create(
            document_type=enums.LoaiVanBan.VAN_BAN_DI, van_ban_id=van_ban.pk,
            vi_tri_luu_tep=f"demo/{van_ban.so_hieu}.pdf", ma_bam_tai_lieu=ma_bam,
            quy_trinh=quy_trinh, phien_ban_quy_trinh=quy_trinh.phien_ban, muc_do=enums.MucDoTrinhKy.THUONG,
            trang_thai=trang_thai, ngay_gui=ngay_gui,
            han_chot=ngay_gui + timedelta(days=7), create_by=nguoi_trinh,
            ngay_hoan_thanh=ket_thuc if trang_thai == T.HOAN_THANH else None,
            ngay_tu_choi=ket_thuc if trang_thai == T.TU_CHOI else None,
            ly_do_tu_choi="Nội dung chưa phù hợp, đề nghị rà soát lại." if trang_thai == T.TU_CHOI else "",
        )
        luot = SigningAttempt.objects.create(
            trinh_ky=yeu_cau, so_luot=1, vi_tri_luu_tep=yeu_cau.vi_tri_luu_tep, ma_bam_tai_lieu=ma_bam,
            trang_thai={
                T.CHO_KY: enums.TrangThaiLuotTrinh.CHO_KY,
                T.HOAN_THANH: enums.TrangThaiLuotTrinh.HOAN_THANH,
                T.TU_CHOI: enums.TrangThaiLuotTrinh.TU_CHOI,
            }[trang_thai],
            thoi_diem_gui=ngay_gui, create_by=nguoi_trinh,
            thoi_diem_hoan_thanh=ket_thuc if trang_thai == T.HOAN_THANH else None,
            thoi_diem_tu_choi=ket_thuc if trang_thai == T.TU_CHOI else None,
        )
        buoc_ky = SigningRequestStep.objects.create(
            luot_trinh=luot, buoc_quy_trinh=buoc, cap_ky=buoc.cap_ky, ten_cap_ky=buoc.ten_cap_ky, thu_tu=1,
            trang_thai=enums.TrangThaiCapKy.DANG_KY if trang_thai == T.CHO_KY else enums.TrangThaiCapKy.HOAN_THANH,
            thoi_diem_mo=ngay_gui, han_xu_ly=ngay_gui + timedelta(days=3),
            thoi_diem_hoan_thanh=None if trang_thai == T.CHO_KY else ket_thuc,
        )
        SigningRequestStepSigner.objects.create(
            buoc_ky=buoc_ky, nguoi_ky=nguoi_ky, ten_nguoi_ky=nguoi_ky.get_full_name() or nguoi_ky.username,
            vai_tro_ky=enums.VaiTroKy.KY_CHINH, trang_thai=trang_thai_signer, thoi_diem_mo=ngay_gui,
            ngay_ky=ket_thuc if trang_thai == T.HOAN_THANH else None,
            ngay_tu_choi=ket_thuc if trang_thai == T.TU_CHOI else None,
            ly_do_tu_choi=yeu_cau.ly_do_tu_choi,
        )
