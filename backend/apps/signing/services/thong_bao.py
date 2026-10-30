"""
Thông báo người trong luồng trình ký (bảng `signing_notification`, kiêm outbox; plan mục 4.1, 9).

- Mỗi sự kiện tạo một bản ghi cho từng kênh: `IN_APP` (hiện ngay trong ứng dụng) và `EMAIL` (khi người nhận
  có email). Tạo trong cùng transaction nghiệp vụ; `khoa_chong_gui_trung` duy nhất nên thao tác lặp không
  tạo thêm thông báo.
- Email gửi sau commit (`transaction.on_commit`), lỗi thì ghi `THAT_BAI` + `loi_gui`; lệnh
  `gui_thong_bao_trinh_ky` gửi lại các bản ghi `CHO_GUI`/`THAT_BAI`. Sau này chuyển sang task Celery chỉ nhận id.
- Sự kiện: người ký được mở (`CAN_KY`); hồ sơ hoàn tất (`HOAN_THANH`), không đồng ý (`TU_CHOI`), trả lại để
  sửa (`YEU_CAU_SUA`), bị hủy (`HUY`: người ký đã được mở trên lượt hiện hành và người tạo khi quản trị hủy
  thay); ủy quyền ký (`UY_QUYEN`); tin nhắn trao đổi khi trả sửa (`TIN_NHAN`); nhắc hạn (`NHAC_HAN`, `QUA_HAN`,
  lệnh `nhac_han_trinh_ky`). Người thực hiện thao tác không tự nhận thông báo của mình.
"""

import logging
from datetime import timedelta

from django.conf import settings
from django.core import mail
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.module_loading import import_string

from .. import enums
from ..models import (
    SigningAuditLog,
    SigningChangeMessage,
    SigningChangeThread,
    SigningNotification,
    SigningRequestStepSigner,
)
from ..tich_hop.to_chuc import ten_hien_thi
from ..tich_hop.van_ban import mo_ta_ho_so

logger = logging.getLogger(__name__)

TEN_LOAI = {
    "CAN_KY": "Cần ký duyệt",
    "HOAN_THANH": "Đã hoàn tất duyệt nội bộ",
    "TU_CHOI": "Không đồng ý ban hành",
    "YEU_CAU_SUA": "Trả lại để sửa",
    "HUY": "Hồ sơ đã hủy",
    "UY_QUYEN": "Ủy quyền ký",
    "TIN_NHAN": "Tin nhắn trao đổi",
    "NHAC_HAN": "Sắp đến hạn ký",
    "QUA_HAN": "Quá hạn ký",
}
SO_LAN_GUI_TOI_DA = 5


def _tao(yeu_cau, nguoi_nhan, loai, khoa, buoc_ky=None):
    bay_gio = timezone.now()
    for kenh in (enums.KenhThongBao.IN_APP, enums.KenhThongBao.EMAIL):
        if kenh == enums.KenhThongBao.EMAIL and not getattr(nguoi_nhan, "email", ""):
            continue
        trong_ung_dung = kenh == enums.KenhThongBao.IN_APP
        try:
            with transaction.atomic():
                tb = SigningNotification.objects.create(
                    trinh_ky=yeu_cau, buoc_ky=buoc_ky, nguoi_nhan=nguoi_nhan, kenh=kenh, loai_thong_bao=loai,
                    khoa_chong_gui_trung=f"{khoa}:{kenh}"[:255],
                    trang_thai=enums.TrangThaiThongBao.DA_GUI if trong_ung_dung else enums.TrangThaiThongBao.CHO_GUI,
                    thoi_diem_gui=bay_gio if trong_ung_dung else None,
                )
        except IntegrityError:  # đã tạo ở lần thao tác trước (cùng khóa chống gửi trùng)
            continue
        if not trong_ung_dung:
            transaction.on_commit(lambda pk=tb.pk: gui_email(pk), robust=True)


def can_ky(dong):
    """Người ký vừa được mở trong cấp đang ký."""
    yeu_cau = dong.buoc_ky.luot_trinh.trinh_ky
    _tao(yeu_cau, dong.nguoi_ky, "CAN_KY", f"CAN_KY:{dong.pk}:{dong.thoi_diem_mo.timestamp():.6f}", buoc_ky=dong)


def _nguoi_ky_cua_luot(luot, **loc):
    return [n.nguoi_ky for n in SigningRequestStepSigner.objects.filter(buoc_ky__luot_trinh=luot, **loc)
            .select_related("nguoi_ky").order_by("pk")]


def su_kien(yeu_cau, luot, loai, nguoi_thuc_hien):
    """Thông báo kết quả cho người trong luồng: người tạo và người ký liên quan của lượt trình."""
    if loai == "HUY":
        # Người tạo (khi quản trị hủy thay) và mọi người ký đã được mở trên lượt hiện hành (đang chờ hoặc đã ký)
        nguoi_nhan = [yeu_cau.create_by, *(_nguoi_ky_cua_luot(luot, thoi_diem_mo__isnull=False) if luot else [])]
    elif loai == "YEU_CAU_SUA":
        nguoi_nhan = [yeu_cau.create_by]
    else:  # HOAN_THANH, TU_CHOI: người tạo và những người đã ký
        nguoi_nhan = [yeu_cau.create_by, *_nguoi_ky_cua_luot(luot, trang_thai=enums.TrangThaiNguoiKy.DA_KY)]
    da_gui = set()
    for nguoi in nguoi_nhan:
        if nguoi.pk == nguoi_thuc_hien.pk or nguoi.pk in da_gui:
            continue
        da_gui.add(nguoi.pk)
        _tao(yeu_cau, nguoi, loai, f"{loai}:{yeu_cau.pk}:{luot.pk if luot else 0}:{nguoi.pk}")


def tin_nhan(tin, nguoi_nhan):
    """Tin nhắn mới trong trao đổi trả sửa: báo bên còn lại (người tạo hoặc người yêu cầu sửa)."""
    if nguoi_nhan.pk != tin.nguoi_viet_id:
        _tao(tin.yeu_cau_sua.luot_trinh.trinh_ky, nguoi_nhan, "TIN_NHAN", f"TIN_NHAN:{tin.pk}:{nguoi_nhan.pk}")


NHAC_TRUOC_HAN = timedelta(hours=24)


def nhac_han(bay_gio=None):
    """
    Nhắc người ký đang được mở trên lượt `CHO_KY` (plan mục 3.5, MVP chưa leo thang): `NHAC_HAN` một lần khi còn
    dưới 24 giờ tới `han_xu_ly` của cấp; `QUA_HAN` mỗi ngày quá hạn cho người ký và người tạo. Khóa chống gửi
    trùng theo dòng người ký, lần mở và ngày quá hạn nên chạy lặp không gửi trùng. Trả số thông báo tạo mới.
    """
    bay_gio = bay_gio or timezone.now()
    truoc = SigningNotification.objects.count()
    dong_mo = (SigningRequestStepSigner.objects.filter(
        trang_thai=enums.TrangThaiNguoiKy.CHO_KY, thoi_diem_mo__isnull=False,
        buoc_ky__trang_thai=enums.TrangThaiCapKy.DANG_KY, buoc_ky__han_xu_ly__isnull=False,
        buoc_ky__han_xu_ly__lte=bay_gio + NHAC_TRUOC_HAN,
        buoc_ky__luot_trinh__trang_thai=enums.TrangThaiLuotTrinh.CHO_KY,
    ).select_related("buoc_ky__luot_trinh__trinh_ky__create_by", "nguoi_ky").order_by("pk"))
    for dong in dong_mo:
        han = dong.buoc_ky.han_xu_ly
        yeu_cau = dong.buoc_ky.luot_trinh.trinh_ky
        moc = f"{dong.pk}:{dong.thoi_diem_mo.timestamp():.6f}"
        with transaction.atomic():
            if han > bay_gio:
                _tao(yeu_cau, dong.nguoi_ky, "NHAC_HAN", f"NHAC_HAN:{moc}", buoc_ky=dong)
                continue
            ngay = (bay_gio - han).days
            for nguoi in {dong.nguoi_ky.pk: dong.nguoi_ky, yeu_cau.create_by.pk: yeu_cau.create_by}.values():
                _tao(yeu_cau, nguoi, "QUA_HAN", f"QUA_HAN:{moc}:{ngay}:{nguoi.pk}", buoc_ky=dong)
    return SigningNotification.objects.count() - truoc


# Loại thông báo -> hành động nhật ký sinh ra nó (để lấy người thao tác và lý do)
HANH_DONG_CUA_LOAI = {"TU_CHOI": "TU_CHOI", "HUY": "HUY_TRINH_KY", "YEU_CAU_SUA": "YEU_CAU_SUA",
                      "UY_QUYEN": "UY_QUYEN_KY"}


def thao_tac(tb):
    """(tên người thao tác, lý do) của sự kiện sinh ra thông báo; ("", "") với loại không có thao tác người dùng."""
    if tb.loai_thong_bao == "TIN_NHAN":
        tin = None
        if tb.khoa_chong_gui_trung and tb.khoa_chong_gui_trung.startswith("TIN_NHAN:"):
            parts = tb.khoa_chong_gui_trung.split(":")
            if len(parts) >= 2 and parts[1].isdigit():
                tin = SigningChangeMessage.objects.filter(pk=int(parts[1])).select_related("nguoi_viet").first()
        if not tin:
            tin = (SigningChangeMessage.objects.filter(yeu_cau_sua__luot_trinh__trinh_ky=tb.trinh_ky,
                                                        created_at__lte=tb.created_at)
                   .select_related("nguoi_viet").order_by("-created_at", "-pk").first())
        return (ten_hien_thi(tin.nguoi_viet) if tin else ""), (tin.noi_dung if tin else "")

    hanh_dong = HANH_DONG_CUA_LOAI.get(tb.loai_thong_bao)
    if not hanh_dong:
        return "", ""
    log = (SigningAuditLog.objects.filter(trinh_ky_id=tb.trinh_ky_id, hanh_dong=hanh_dong,
                                          created_at__lte=tb.created_at)
           .select_related("nguoi_thuc_hien").order_by("-created_at", "-pk").first())
    yeu_cau = tb.trinh_ky
    if tb.loai_thong_bao == "TU_CHOI":
        ly_do = yeu_cau.ly_do_tu_choi
    elif tb.loai_thong_bao == "HUY":
        ly_do = yeu_cau.ly_do_huy
    elif tb.loai_thong_bao == "YEU_CAU_SUA":
        thread = (SigningChangeThread.objects.filter(luot_trinh__trinh_ky=yeu_cau, created_at__lte=tb.created_at)
                  .order_by("-created_at", "-pk").first())
        ly_do = f"{thread.tieu_de}: {thread.ly_do}" if thread else ""
    else:
        ly_do = log.chi_tiet if log else ""
    return (ten_hien_thi(log.nguoi_thuc_hien) if log else ""), (ly_do or "")


LOAI_CO_HAN = ("CAN_KY", "NHAC_HAN", "QUA_HAN")
SMTP_BACKEND = "django.core.mail.backends.smtp.EmailBackend"


def han_xu_ly(tb):
    """Hạn xử lý của cấp ký gắn với thông báo cần ký/nhắc hạn/quá hạn; None với loại khác hoặc cấp không đặt hạn."""
    if tb.loai_thong_bao not in LOAI_CO_HAN or tb.buoc_ky_id is None:
        return None
    return tb.buoc_ky.buoc_ky.han_xu_ly


def dinh_dang_ngay(thoi_diem):
    """Ngày giờ kiểu Việt Nam theo múi giờ hệ thống: 25/10/2026 14:30."""
    return f"{timezone.localtime(thoi_diem):%d/%m/%Y %H:%M}"


def noi_dung(tb):
    van_ban = mo_ta_ho_so(tb.trinh_ky)
    # Một dòng: xuống dòng trong trích yếu làm email bị từ chối (BadHeaderError) ở tiêu đề
    ten_van_ban = " ".join(" — ".join(x for x in (van_ban.get("so_hieu"), van_ban.get("trich_yeu")) if x).split()) \
        or f"#{tb.trinh_ky_id}"
    duong_dan = f"{settings.SIGNING_FRONTEND_URL.rstrip('/')}/approvals/{tb.trinh_ky_id}"
    tieu_de = f"[Trình ký] {TEN_LOAI.get(tb.loai_thong_bao, tb.loai_thong_bao)}: {ten_van_ban}"
    nguoi_thao_tac, ly_do = thao_tac(tb)
    han = han_xu_ly(tb)
    nhan_nguoi = "Người gửi" if tb.loai_thong_bao == "TIN_NHAN" else "Người thực hiện"
    nhan_ly_do = "Nội dung" if tb.loai_thong_bao == "TIN_NHAN" else "Lý do"
    chi_tiet = (f"{nhan_nguoi}: {nguoi_thao_tac}.\n" if nguoi_thao_tac else "") + \
        (f"{nhan_ly_do}: {ly_do}\n" if ly_do else "") + \
        (f"Hạn xử lý: {dinh_dang_ngay(han)}.\n" if han else "")
    than = (f"Xin chào {ten_hien_thi(tb.nguoi_nhan)},\n\n"
            f"{TEN_LOAI.get(tb.loai_thong_bao, tb.loai_thong_bao)} — hồ sơ trình ký #{tb.trinh_ky_id}.\n"
            f"Văn bản trình ký: {ten_van_ban}.\n"
            f"{chi_tiet}"
            f"Quy trình: {tb.trinh_ky.quy_trinh.ten_quy_trinh}. Người trình: {ten_hien_thi(tb.trinh_ky.create_by)}.\n\n"
            f"Xem hồ sơ: {duong_dan}\n\n"
            "Thư gửi tự động từ phân hệ Trình ký, vui lòng không trả lời.")
    return tieu_de, than, ten_van_ban


def ket_noi_email():
    """
    Kết nối gửi thông báo, chạy trên Django 5.2 (EMAIL_BACKEND) và 6.1 (MAILERS).
    - `SIGNING_EMAIL_BACKEND` trống hoặc là SMTP: mailer mặc định của dự án (SMTP lấy cấu hình EMAIL_* trong settings).
      Django 6.1 không cho tạo SMTP backend trực tiếp khi đã khai báo MAILERS (đọc EMAIL_HOST bị chặn).
    - Giá trị khác (console, locmem, backend kiểm thử): khởi tạo trực tiếp backend đó, không cần cấu hình máy chủ.
    """
    duong_dan = settings.SIGNING_EMAIL_BACKEND
    if duong_dan and duong_dan != SMTP_BACKEND:
        return import_string(duong_dan)(fail_silently=False)
    mailers = getattr(mail, "mailers", None)  # Django 6.1+
    if mailers is not None and hasattr(settings, "MAILERS"):
        return mailers.default
    return mail.get_connection(fail_silently=False)


def gui_email(tb_id):
    """Gửi một thông báo email; trả True khi gửi được. Gọi lại an toàn (chỉ gửi bản ghi chưa gửi)."""
    with transaction.atomic():
        tb = (SigningNotification.objects.select_for_update(skip_locked=True, of=("self",))
              .select_related("trinh_ky__quy_trinh", "trinh_ky__create_by", "nguoi_nhan", "buoc_ky__buoc_ky")
              .filter(pk=tb_id, kenh=enums.KenhThongBao.EMAIL)
              .exclude(trang_thai=enums.TrangThaiThongBao.DA_GUI).first())
        if tb is None:
            return False
        tieu_de, than, _ = noi_dung(tb)
        try:
            thu = mail.EmailMessage(tieu_de, than, None, [tb.nguoi_nhan.email])  # người gửi: DEFAULT_FROM_EMAIL
            ket_noi_email().send_messages([thu])
        except Exception as exc:  # SMTP/cấu hình: ghi lỗi để gửi lại, không làm hỏng nghiệp vụ
            logger.warning("Gửi email thông báo %s thất bại: %s", tb.pk, exc)
            tb.trang_thai, tb.loi_gui = enums.TrangThaiThongBao.THAT_BAI, str(exc)[:1000]
            tb.so_lan_gui_lai += 1
            tb.save(update_fields=["trang_thai", "loi_gui", "so_lan_gui_lai"])
            return False
        tb.trang_thai, tb.thoi_diem_gui, tb.loi_gui = enums.TrangThaiThongBao.DA_GUI, timezone.now(), ""
        tb.save(update_fields=["trang_thai", "thoi_diem_gui", "loi_gui"])
        return True


def gui_lai_email_ton():
    """Quét outbox: gửi lại email `CHO_GUI`/`THAT_BAI` chưa quá số lần thử. Trả (đã gửi, còn lỗi)."""
    ids = list(SigningNotification.objects.filter(
        kenh=enums.KenhThongBao.EMAIL, so_lan_gui_lai__lt=SO_LAN_GUI_TOI_DA,
        trang_thai__in=[enums.TrangThaiThongBao.CHO_GUI, enums.TrangThaiThongBao.THAT_BAI],
    ).order_by("pk").values_list("pk", flat=True))
    ok = sum(1 for pk in ids if gui_email(pk))
    return ok, len(ids) - ok


def cua_toi(nguoi, gioi_han=50):
    return (SigningNotification.objects.filter(nguoi_nhan=nguoi, kenh=enums.KenhThongBao.IN_APP)
            .select_related("trinh_ky__quy_trinh", "trinh_ky__create_by", "nguoi_nhan", "buoc_ky__buoc_ky")
            .order_by("-created_at", "-pk")
            [:gioi_han])
