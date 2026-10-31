"""
Dữ liệu mẫu phân hệ Trình ký (Nhóm 5): `manage.py seed_signing_demo [--reset]` — chạy lại không nhân bản dữ liệu.
Tự đủ trên DB vừa `migrate` (đơn vị, chức vụ, nhóm quyền chuẩn có sẵn từ migration; thiếu đơn vị thì tạo).

Tạo qua chính các service nghiệp vụ (tạo nháp, gửi, ký Ed25519, từ chối, trả sửa, trao đổi, gửi bản sửa, hủy,
trình lại) nên lịch sử, bằng chứng, tệp hoàn tất và thông báo nhất quán như thao tác thật:

- 5 tài khoản: admin (quản trị), vanthu (văn thư, tạo và trình), chuyenvien (soạn nháp), truongphong (trưởng
  phòng, ký cấp 1), giamdoc (giám đốc, ký cấp 2); gán đơn vị, chức vụ, nhóm quyền chuẩn (VT, CV, TP, BGD, ADMIN).
  Mật khẩu đọc từ biến môi trường DEMO_PASSWORD (không ghi trong mã nguồn). Tài khoản đã có thì giữ mật khẩu,
  trừ khi dùng `--dat-lai-mat-khau`. Tài khoản `admin` chỉ được đặt mật khẩu khi còn mật khẩu không dùng được
  (sentinel của DDL); admin đã khởi tạo bằng `seed_db`/ADMIN_PASSWORD thì giữ nguyên.
- 4 quy trình mẫu (3 đang hoạt động: hai cấp tuần tự, một cấp và hai người ký song song; 1 nháp).
- Hồ sơ ở đủ trạng thái: nháp, đang ký (cấp 1, cấp 2), quá hạn, hoàn thành (có bằng chứng và tệp hoàn tất),
  bị từ chối (kèm hồ sơ trình lại), trả lại để sửa (có trao đổi), đã sửa và trình lại lượt 2, đã hủy, ký song song.
- Thông báo trong ứng dụng sinh từ các thao tác trên và lệnh nhắc hạn. Ngày trình giãn theo nhiều ngày để
  Dashboard (Nhóm 1, `signing.selectors.tong_quan_dashboard`) có phiếu gần đây với ngày khác nhau.
- `--reset`: làm mới bộ hồ sơ mẫu. Bằng chứng (lượt trình, chữ ký, nhật ký, bằng chứng tổng hợp) bất biến theo
  trigger của DDL nên không xóa: hồ sơ mẫu cũ còn mở được hủy, ghi chú đổi sang "Dữ liệu mẫu cũ", ngày tạo/ngày trình
  lùi 30 ngày (không chen vào 5 phiếu gần nhất của Dashboard), rồi tạo bộ mới. Nếu văn bản mẫu đã có hồ sơ hoàn tất,
  tạo bản ghi văn bản đi mới cho bộ mẫu kế tiếp.
- `--email-domain <miền>`: gán email <username>@<miền> cho tài khoản mẫu chưa có email; không có email thì chỉ có
  thông báo trong ứng dụng, không có email.

Ký mẫu dùng khóa Ed25519 tạm sinh trong bộ nhớ (khóa bí mật không lưu); xong thì thu hồi khóa tạm, người dùng tự tạo
khóa ký của mình ở trang Cấu hình khóa ký (file khóa + PIN). Hồ sơ nhận diện qua ghi chú "Dữ liệu mẫu <mã>:".
"""

import base64
import os
from datetime import timedelta

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from accounts.models import Employee, Position
from authorization.models import GroupInfo
from documents.models import PhamVi, VanBanDi, VanBanDiAttachment
from organizations.models import DonVi, KhoiKhuVuc
from signing import enums
from signing.models import (
    SigningAttempt, SigningKey, SigningProcess, SigningRequest, SigningRequestStep,
)
from signing.pdf_hoan_tat import tim_phong_chu
from signing.services import hanh_dong_ky, keys, process, thong_bao, trinh_ky, yeu_cau_sua

TIEN_TO = "Dữ liệu mẫu"
TIEN_TO_CU = "Dữ liệu mẫu cũ"
DON_VI_CHINH = "Ban công nghệ thông tin"
DON_VI_LANH_DAO = "Ban tổng giám đốc"

# username: (họ tên, chức vụ, mã nhóm quyền, đơn vị)
TAI_KHOAN = {
    "admin": ("Quản trị hệ thống", "Quản trị viên", "ADMIN", DON_VI_CHINH),
    "vanthu": ("Văn thư Ban CNTT", "Văn thư", "VT", DON_VI_CHINH),
    "chuyenvien": ("Chuyên viên Ban CNTT", "Chuyên viên", "CV", DON_VI_CHINH),
    "truongphong": ("Trưởng phòng Ban CNTT", "Trưởng phòng", "TP", DON_VI_CHINH),
    "giamdoc": ("Giám đốc", "Giám đốc", "BGD", DON_VI_LANH_DAO),
}

# mã: (tên, mô tả, cấp ký [(tên cấp, số giờ, [(username, vai trò)])], kích hoạt)
QUY_TRINH = {
    "QT-TK-HAI-CAP": ("Duyệt tờ trình hai cấp", "Trưởng phòng duyệt, sau đó Giám đốc duyệt.", [
        ("Trưởng phòng duyệt", 24, ["truongphong"]),
        ("Giám đốc duyệt", 48, ["giamdoc"]),
    ], True),
    "QT-TK-MOT-CAP": ("Duyệt một cấp", "Giám đốc phê duyệt.", [
        ("Phê duyệt", 48, ["giamdoc"]),
    ], True),
    "QT-TK-SONG-SONG": ("Lấy ý kiến song song", "Trưởng phòng và Quản trị ký song song, sau đó Giám đốc duyệt.", [
        ("Lấy ý kiến các bộ phận", 24, ["truongphong", "admin"]),
        ("Giám đốc duyệt", 48, ["giamdoc"]),
    ], True),
    "QT-TK-NHAP": ("Quy trình đang soạn", "Quy trình nháp để thử sửa, kích hoạt, nhân bản.", [
        ("Trưởng phòng duyệt", None, ["truongphong"]),
    ], False),
}

# Số giờ lùi ngày trình của từng hồ sơ (ngày trình khác nhau trên danh sách và Dashboard)
LUI_GIO = {"M01": 1, "M10": 3, "M04": 27, "M02": 51, "M05": 75, "M03": 99, "M08": 123, "M06": 147, "M07": 171,
           "M09": 195}

# --reset: bộ hồ sơ mẫu cũ lùi ngày tạo/ngày trình chừng này (không chen vào phiếu gần đây của bộ mới)
LUI_NGAY_BO_CU = timedelta(days=30)

# mã: (số hiệu, trích yếu)
VAN_BAN = {
    "M01": ("101/TTr-CNTT", "Tờ trình nâng cấp hệ thống sao lưu dữ liệu nghiệp vụ bảo hiểm"),
    "M02": ("102/TTr-CNTT", "Tờ trình mua sắm thiết bị mạng cho văn phòng khu vực"),
    "M03": ("103/KH-CNTT", "Kế hoạch triển khai hệ thống quản lý văn bản điện tử năm 2027"),
    "M04": ("104/BC-CNTT", "Báo cáo tổng kết công tác an toàn thông tin quý III"),
    "M05": ("105/ĐX-CNTT", "Đề xuất thuê dịch vụ trung tâm dữ liệu dự phòng"),
    "M06": ("106/TTr-CNTT", "Tờ trình phê duyệt dự toán bảo trì phần mềm nghiệp vụ"),
    "M07": ("107/QĐ-CNTT", "Dự thảo quyết định ban hành quy chế sử dụng chữ ký số nội bộ"),
    "M08": ("108/TB-CNTT", "Thông báo lịch bảo trì hệ thống thư điện tử"),
    "M09": ("109/TTr-CNTT", "Tờ trình gia hạn bản quyền phần mềm diệt mã độc"),
    "M10": ("110/BC-CNTT", "Báo cáo đánh giá rủi ro hệ thống thanh toán phí bảo hiểm"),
}


def tao_pdf(tieu_de, dong_phu):
    """PDF A4 hai trang có tiêu đề văn bản (phông tiếng Việt như tệp hoàn tất; thiếu phông thì dùng Helvetica)."""
    import io

    from reportlab.lib.pagesizes import A4
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas

    phong = "Helvetica"
    duong_dan = tim_phong_chu()
    if duong_dan:
        pdfmetrics.registerFont(TTFont("DuLieuMauVN", duong_dan[0]))
        phong = "DuLieuMauVN"
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    rong, cao = A4
    for trang in (1, 2):
        c.setFont(phong, 11)
        c.drawCentredString(rong / 2, cao - 60, "CÔNG TY BẢO HIỂM — BAN CÔNG NGHỆ THÔNG TIN")
        c.setFont(phong, 15)
        c.drawCentredString(rong / 2, cao - 110, tieu_de)
        c.setFont(phong, 11)
        c.drawString(70, cao - 160, dong_phu)
        c.drawString(70, cao - 180, f"Trang {trang}/2 — nội dung dự thảo dùng cho dữ liệu mẫu phân hệ Trình ký.")
        c.showPage()
    c.save()
    return buf.getvalue()


class KhoaTam:
    """Khóa Ed25519 tạm của một người ký (khóa bí mật chỉ trong bộ nhớ)."""

    def __init__(self, nguoi):
        self.nguoi = nguoi
        self.rieng = Ed25519PrivateKey.generate()
        cong_khai = self.rieng.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        bay_gio = timezone.now()
        self.khoa = keys.dang_ky(nguoi, ma_khoa=f"DLM-{nguoi.username}-{bay_gio:%Y%m%d%H%M%S%f}",
                                 khoa_cong_khai=base64.b64encode(cong_khai).decode(),
                                 ngay_hieu_luc=bay_gio - timedelta(minutes=1), ghi_chu=f"{TIEN_TO}: khóa tạm")
        keys.xac_minh_so_huu(self.khoa, nguoi, self.ky(keys.thach_thuc_so_huu(self.khoa).encode()))
        cu = SigningKey.objects.filter(nguoi_so_huu=nguoi, trang_thai=enums.TrangThaiKhoa.HOAT_DONG).first()
        self.khoa = keys.xoay_vong(cu, self.khoa, nguoi) if cu else keys.kich_hoat(self.khoa, nguoi)

    def ky(self, du_lieu):
        return base64.b64encode(self.rieng.sign(du_lieu)).decode()


class Command(BaseCommand):
    help = "Tạo dữ liệu mẫu phân hệ Trình ký (tài khoản, quy trình, hồ sơ đủ trạng thái); chạy lại không nhân bản."

    def add_arguments(self, parser):
        parser.add_argument("--dat-lai-mat-khau", action="store_true",
                            help="Đặt lại mật khẩu DEMO_PASSWORD cho tài khoản mẫu đã có (trừ admin).")
        parser.add_argument("--reset", action="store_true",
                            help="Hủy bộ hồ sơ mẫu hiện có (giữ làm lịch sử) rồi tạo bộ mới.")
        parser.add_argument("--email-domain", default="",
                            help="Gán email <username>@<domain> cho tài khoản mẫu chưa có email (để thử gửi mail).")

    def handle(self, *args, **options):
        self.mat_khau = (os.environ.get("DEMO_PASSWORD") or "").strip()
        self.khoa_tam = {}
        self.dem = 0
        self.lan_chay = f"{timezone.now():%Y%m%d%H%M%S%f}"
        nguoi = self._tai_khoan(options["dat_lai_mat_khau"], options["email_domain"].strip().lstrip("@"))
        if options["reset"]:
            self._reset(nguoi)
        quy_trinh = self._quy_trinh(nguoi)
        try:
            self._ho_so(nguoi, quy_trinh)
        finally:
            for k in self.khoa_tam.values():
                keys.thu_hoi(k.khoa, k.nguoi, f"{TIEN_TO}: thu hồi khóa tạm sau khi ký mẫu")
        so_nhac = thong_bao.nhac_han()
        self.stdout.write(self.style.SUCCESS(
            f"Xong: {self.dem} hồ sơ mẫu mới, {so_nhac} thông báo nhắc hạn mới. "
            f"Tổng hồ sơ mẫu: {self._mau().count()}."))

    def _mau(self):
        return SigningRequest.objects.filter(ghi_chu__startswith=f"{TIEN_TO} M")

    def _reset(self, nguoi):
        """
        Hủy hồ sơ mẫu còn mở (bằng chứng giữ nguyên), đổi ghi chú để bộ mới được tạo lại, và lùi ngày tạo/ngày trình
        của bộ cũ `LUI_NGAY_BO_CU` để bộ cũ không chen vào "phiếu gần nhất" của Dashboard và đầu danh sách.
        """
        so = 0
        for h in self._mau().order_by("pk"):
            if h.trang_thai in (enums.TrangThaiYeuCau.NHAP, enums.TrangThaiYeuCau.CHO_KY):
                trinh_ky.huy(h, h.create_by, ly_do=f"{TIEN_TO}: làm mới bộ dữ liệu mẫu",
                             khoa_chong_trung=self._khoa(h.pk, f"reset-{timezone.now().timestamp()}"))
            SigningRequest.objects.filter(pk=h.pk).update(
                ghi_chu=TIEN_TO_CU + h.ghi_chu[len(TIEN_TO):],
                created_at=F("created_at") - LUI_NGAY_BO_CU, ngay_gui=F("ngay_gui") - LUI_NGAY_BO_CU)
            so += 1
        self.stdout.write(f" [OK] --reset: {so} hồ sơ mẫu cũ đã hủy/đánh dấu cũ")

    # ── Tài khoản ───────────────────────────────────────────────────────────

    def _tai_khoan(self, dat_lai, mien):
        User = get_user_model()
        thieu = [u for u in TAI_KHOAN if not User.objects.filter(username=u).exists()]
        if thieu and not self.mat_khau:
            raise CommandError(f"Cần biến môi trường DEMO_PASSWORD để tạo tài khoản: {', '.join(thieu)}.")
        if dat_lai and not self.mat_khau:
            raise CommandError("--dat-lai-mat-khau cần biến môi trường DEMO_PASSWORD.")
        ket_qua = {}
        with transaction.atomic():
            for username, (ho_ten, ten_chuc_vu, ma_nhom, ten_don_vi) in TAI_KHOAN.items():
                don_vi = DonVi.objects.filter(ten=ten_don_vi).order_by("pk").first() or self._tao_don_vi(ten_don_vi)
                u = User.objects.filter(username=username).first()
                moi = u is None
                if moi:
                    u = User.objects.create_user(username, password=self.mat_khau, ho_ten=ho_ten, don_vi=don_vi,
                                                 chuc_vu=Position.objects.filter(name=ten_chuc_vu).first())
                elif username == "admin":
                    if not u.has_usable_password() and self.mat_khau:  # còn sentinel của DDL: khởi tạo cho demo
                        u.set_password(self.mat_khau)
                elif dat_lai:
                    u.set_password(self.mat_khau)
                if moi or username != "admin":  # admin đã có: giữ nguyên hồ sơ do seed_db quản lý
                    u.ho_ten = u.ho_ten or ho_ten
                    u.don_vi = u.don_vi or don_vi
                    u.chuc_vu = u.chuc_vu or Position.objects.filter(name=ten_chuc_vu).first()
                    u.trang_thai = Employee.Status.LAM_VIEC
                    u.is_active = True
                    if username == "admin":
                        u.is_staff = u.is_superuser = True
                if mien and not u.email and not User.objects.filter(email=f"{username}@{mien}").exists():
                    u.email = f"{username}@{mien}"
                u.save()
                info = GroupInfo.objects.filter(ma_nhom_quyen=ma_nhom).first()
                if info is not None:
                    u.groups.add(Group.objects.get(pk=info.pk))
                ket_qua[username] = User.objects.get(pk=u.pk)
                self.stdout.write(f" [OK] Tài khoản {username} ({'tạo mới' if moi else 'đã có'})")
        return ket_qua

    def _tao_don_vi(self, ten):
        """Đơn vị chưa có (DB không có dữ liệu nền của Nhóm 7): tạo tối thiểu để gán tài khoản mẫu."""
        khoi = KhoiKhuVuc.objects.order_by("pk").first() or KhoiKhuVuc.objects.create(ten="KHỐI HỖ TRỢ")
        stt = (DonVi.objects.order_by("-stt_uu_tien").values_list("stt_uu_tien", flat=True).first() or 0) + 1
        return DonVi.objects.create(khoi=khoi, ten=ten, stt_uu_tien=stt)

    # ── Quy trình ───────────────────────────────────────────────────────────

    def _quy_trinh(self, nguoi):
        ket_qua = {}
        for ma, (ten, mo_ta, cap_ky, kich_hoat) in QUY_TRINH.items():
            qt = (SigningProcess.objects.filter(ma_quy_trinh=ma, trang_thai=enums.TrangThaiQuyTrinh.HOAT_DONG).first()
                  or SigningProcess.objects.filter(ma_quy_trinh=ma).order_by("-phien_ban").first())
            if qt is None:
                qt = process.tao_quy_trinh(nguoi["admin"], ma_quy_trinh=ma, ten_quy_trinh=ten, mo_ta=mo_ta,
                                           pham_vi=enums.PhamViQuyTrinh.CONG_TY, cap_ky=[
                    {"cap_ky": i, "ten_cap_ky": ten_cap, "thu_tu": i, "so_gio_xu_ly": so_gio, "nguoi_ky": [
                        {"nguoi_ky": nguoi[u], "thu_tu": j}
                        for j, u in enumerate(ds, start=1)]}
                    for i, (ten_cap, so_gio, ds) in enumerate(cap_ky, start=1)])
                if kich_hoat:
                    qt = process.kich_hoat(qt, nguoi["admin"])
                self.stdout.write(f" [OK] Quy trình {ma} (tạo mới)")
            ket_qua[ma] = qt
        return ket_qua

    # ── Hồ sơ ───────────────────────────────────────────────────────────────

    def _van_ban(self, ma, nguoi_tao):
        so_hieu, trich_yeu = VAN_BAN[ma]
        vb = VanBanDi.objects.filter(so_hieu=so_hieu, trich_yeu=trich_yeu).first()
        da_hoan_tat = vb is not None and SigningRequest.objects.filter(
            document_type=enums.LoaiVanBan.VAN_BAN_DI,
            van_ban_id=vb.pk,
            trang_thai=enums.TrangThaiYeuCau.HOAN_THANH,
        ).exists()
        if da_hoan_tat:
            so_luong_hoan_tat = SigningRequest.objects.filter(
                document_type=enums.LoaiVanBan.VAN_BAN_DI,
                van_ban_id__in=VanBanDi.objects.filter(so_hieu__startswith=so_hieu).values("pk"),
                trang_thai=enums.TrangThaiYeuCau.HOAN_THANH,
            ).count()
            phien_ban = so_luong_hoan_tat + 1
            so_hieu = f"{so_hieu}-M{phien_ban}"
            trich_yeu = f"{trich_yeu} (Bộ mẫu {phien_ban})"
            vb = VanBanDi.objects.filter(so_hieu=so_hieu, trich_yeu=trich_yeu).first()
        if vb is None:
            vb = VanBanDi.objects.create(so_hieu=so_hieu, trich_yeu=trich_yeu, pham_vi=PhamVi.NOI_BO,
                                         nguoi_tao=nguoi_tao, nguoi_ky="", chuc_vu="")
        return vb

    def _tep(self, ma, ban=1):
        so_hieu, trich_yeu = VAN_BAN[ma]
        noi_dung = tao_pdf(trich_yeu, f"Số hiệu: {so_hieu} — bản {ban}")
        return SimpleUploadedFile(f"{ma}-ban-{ban}.pdf", noi_dung, content_type="application/pdf")

    def _tep_dinh_kem(self, van_ban, ma, nguoi_tao):
        tep = van_ban.attachments.filter(is_deleted=False, name__iendswith=".pdf").first()
        if tep is None:
            tai_len = self._tep(ma)
            tep = VanBanDiAttachment.objects.create(
                document=van_ban, file=tai_len, name=tai_len.name, nguoi_tao=nguoi_tao,
            )
        return tep

    def _khoa(self, ma, buoc):
        # Gắn lần chạy: --reset tạo lại hồ sơ cùng mã mà không trùng Idempotency-Key của lần trước
        return f"{TIEN_TO}:{self.lan_chay}:{ma}:{buoc}"

    def _lui_ngay(self, ho_so, gio):
        """Lùi ngày tạo/ngày trình của hồ sơ mẫu để danh sách và Dashboard có ngày trình khác nhau."""
        if not gio:
            return
        lui = timedelta(hours=gio)
        h = SigningRequest.objects.get(pk=ho_so.pk)
        SigningRequest.objects.filter(pk=h.pk).update(
            created_at=h.created_at - lui, ngay_gui=h.ngay_gui - lui if h.ngay_gui else None)
        for luot in SigningAttempt.objects.filter(trinh_ky=h):
            SigningAttempt.objects.filter(pk=luot.pk).update(
                created_at=luot.created_at - lui, thoi_diem_gui=luot.thoi_diem_gui - lui if luot.thoi_diem_gui else None)

    def _co_roi(self, ma):
        return SigningRequest.objects.filter(ghi_chu__startswith=f"{TIEN_TO} {ma}:", ho_so_goc__isnull=True).exists()

    def _ky(self, ho_so, nguoi, ghi_chu=""):
        k = self.khoa_tam[nguoi.pk]
        ma_bam = trinh_ky.luot_hien_hanh(SigningRequest.objects.get(pk=ho_so.pk)).ma_bam_tai_lieu
        return hanh_dong_ky.ky(ho_so, nguoi, khoa_ky=k.khoa.pk, hash_tai_lieu=ma_bam,
                               chu_ky_so=k.ky(bytes.fromhex(ma_bam)), ghi_chu_ky=ghi_chu,
                               khoa_chong_trung=self._khoa(ho_so.pk, f"ky-{nguoi.pk}-{timezone.now().timestamp()}"))

    def _tao(self, ma, mo_ta, nguoi_tao, quy_trinh, gui=True, han_gio=72):
        """Hồ sơ của mã `ma`: đã có thì trả None (không làm lại các bước); chưa có thì tạo nháp và gửi."""
        ghi_chu = f"{TIEN_TO} {ma}: {mo_ta}"
        if self._co_roi(ma):
            return None
        van_ban = self._van_ban(ma, nguoi_tao)
        tep = self._tep_dinh_kem(van_ban, ma, nguoi_tao)
        ho_so = trinh_ky.tao_nhap(nguoi_tao, document_type=enums.LoaiVanBan.VAN_BAN_DI,
                                  van_ban_id=van_ban.pk, tep_dinh_kem_id=tep.pk, quy_trinh=quy_trinh,
                                  han_chot=timezone.now() + timedelta(hours=han_gio),
                                  ghi_chu=ghi_chu)
        if gui:
            ho_so = trinh_ky.gui(ho_so, nguoi_tao, khoa_chong_trung=self._khoa(ma, "gui"))
        self._lui_ngay(ho_so, LUI_GIO.get(ma, 0))
        self.dem += 1
        self.stdout.write(f" [OK] Hồ sơ {ma}: {mo_ta}")
        return ho_so

    def _ho_so(self, n, qt):
        hai_cap, mot_cap, song_song = qt["QT-TK-HAI-CAP"], qt["QT-TK-MOT-CAP"], qt["QT-TK-SONG-SONG"]

        # Khóa tạm cho người ký, tạo trước (ngoài transaction từng hồ sơ) và chỉ khi còn hồ sơ cần ký chưa tạo
        if any(not self._co_roi(m) for m in ("M03", "M04", "M05", "M07", "M10")):
            for u in ("truongphong", "giamdoc", "admin"):
                self.khoa_tam[n[u].pk] = KhoaTam(n[u])

        with transaction.atomic():
            self._tao("M01", "nháp do chuyên viên soạn, chưa gửi", n["chuyenvien"], mot_cap, gui=False)

        with transaction.atomic():
            self._tao("M02", "đang chờ Trưởng phòng ký (cấp 1)", n["vanthu"], hai_cap)

        with transaction.atomic():
            h = self._tao("M03", "Trưởng phòng đã ký, chờ Giám đốc (cấp 2)", n["vanthu"], hai_cap)
            if h:
                self._ky(h, n["truongphong"], "Đã kiểm tra số liệu, đề nghị Giám đốc phê duyệt")

        with transaction.atomic():
            h = self._tao("M04", "hoàn tất duyệt nội bộ", n["vanthu"], hai_cap)
            if h:
                self._ky(h, n["truongphong"], "Thể thức đúng quy định")
                self._ky(h, n["giamdoc"])

        with transaction.atomic():
            h = self._tao("M05", "Giám đốc không đồng ý ban hành; đã tạo hồ sơ trình lại", n["vanthu"], hai_cap)
            if h:
                self._ky(h, n["truongphong"])
                hanh_dong_ky.tu_choi(h, n["giamdoc"], ly_do_tu_choi="Chưa đủ căn cứ pháp lý về chi phí thuê ngoài",
                                     khoa_chong_trung=self._khoa("M05", "tu-choi"))
                trinh_ky.trinh_lai(h, n["vanthu"], khoa_chong_trung=self._khoa("M05", "trinh-lai"),
                                   han_chot=timezone.now() + timedelta(days=5))

        with transaction.atomic():
            h = self._tao("M06", "Trưởng phòng trả lại để sửa, đang trao đổi", n["vanthu"], hai_cap)
            if h:
                yeu_cau_sua.yeu_cau_sua(h, n["truongphong"], tieu_de="Bổ sung bảng dự toán chi tiết",
                                        ly_do="Mục 3 thiếu bảng chi phí theo từng hạng mục.",
                                        khoa_chong_trung=self._khoa("M06", "yeu-cau-sua"))
                yeu_cau_sua.gui_tin_nhan(h, n["vanthu"], noi_dung="Đã nhận, sẽ bổ sung bảng chi phí trong hôm nay.")
                yeu_cau_sua.gui_tin_nhan(h, n["truongphong"], noi_dung="Ghi rõ đơn giá và nguồn báo giá.")

        with transaction.atomic():
            h = self._tao("M07", "đã sửa theo yêu cầu, trình lại lượt 2", n["vanthu"], hai_cap)
            if h:
                yeu_cau_sua.yeu_cau_sua(h, n["truongphong"], tieu_de="Sửa căn cứ ban hành",
                                        ly_do="Căn cứ pháp lý dẫn chiếu văn bản đã hết hiệu lực.",
                                        khoa_chong_trung=self._khoa("M07", "yeu-cau-sua"))
                yeu_cau_sua.gui_tin_nhan(h, n["vanthu"], noi_dung="Đã cập nhật căn cứ theo văn bản mới.")
                yeu_cau_sua.giai_quyet(h, n["vanthu"], tep=self._tep("M07", ban=2),
                                       khoa_chong_trung=self._khoa("M07", "giai-quyet"))
                self._ky(h, n["truongphong"], "Đã sửa đúng yêu cầu")

        with transaction.atomic():
            h = self._tao("M08", "người tạo hủy khi đang ký", n["vanthu"], hai_cap)
            if h:
                trinh_ky.huy(h, n["vanthu"], ly_do="Lịch bảo trì thay đổi, không cần ban hành",
                             khoa_chong_trung=self._khoa("M08", "huy"))

        with transaction.atomic():
            h = self._tao("M09", "quá hạn xử lý ở cấp Trưởng phòng", n["vanthu"], hai_cap)
            if h:
                # Lùi mốc thời gian để mô phỏng hồ sơ quá hạn (hạn chót và hạn xử lý của cấp đang ký)
                qua_han = timezone.now() - timedelta(hours=6)
                SigningRequest.objects.filter(pk=h.pk).update(han_chot=qua_han + timedelta(hours=2))
                SigningRequestStep.objects.filter(luot_trinh__trinh_ky=h, trang_thai=enums.TrangThaiCapKy.DANG_KY) \
                    .update(han_xu_ly=qua_han)

        with transaction.atomic():
            h = self._tao("M10", "hai người ký song song, một người đã ký, một người chờ ký", n["vanthu"], song_song)
            if h:
                self._ky(h, n["admin"], "Đồng ý về mặt kỹ thuật")
