"""
Dựng tệp PDF hoàn tất của lượt trình — phần lõi Phase 10 (#80; plan mục 3.2 "Phẳng hóa").

Đầu vào: bytes tệp gốc đã khóa, nội dung bằng chứng đã chốt và mã băm bằng chứng. Đầu ra là tệp mới:
- giữ nguyên nội dung mọi trang gốc, thêm một dòng nhận diện "bản duyệt nội bộ, chưa phát hành" ở chân trang;
- nối trang phê duyệt (thông tin hồ sơ, mã băm tệp gốc, các cấp, người ký, thời điểm ký, dấu vân tay khóa);
- đính kèm `bang-chung-<lượt>.json` (JSON chuẩn hóa) để xác minh ngoại tuyến.

MVP chưa dán ảnh chữ ký theo tọa độ: chưa có nguồn ảnh chữ ký cá nhân (Nhóm 7, #67 mục 2) và chưa chốt hệ tọa độ.
Tệp không nhúng chữ ký số, không thay cho văn bản ban hành.

Phông chữ phải có dấu tiếng Việt: `SIGNING_PDF_FONT` (và `SIGNING_PDF_FONT_BOLD`, tùy chọn) hoặc tự dò phông hệ
thống phổ biến (DejaVu Sans, Noto Sans, Liberation Sans, Arial). Không có thì lỗi `thieu_phong_chu`.
"""

import hashlib
import io
import os
from datetime import datetime
from functools import lru_cache
from zoneinfo import ZoneInfo

from django.conf import settings

from .services.bang_chung import ma_hoa_chuan

KY_TU_KIEM_TRA = "ăâđêôơưĂÂĐÊÔƠƯạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹ"

UNG_VIEN_PHONG_CHU = [
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ("/usr/share/fonts/dejavu/DejaVuSans.ttf", "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"),
    ("/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf", "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf"),
    ("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
     "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
    (r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\arialbd.ttf"),
    ("/System/Library/Fonts/Supplemental/Arial.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
    ("/Library/Fonts/Arial.ttf", "/Library/Fonts/Arial Bold.ttf"),
]

VAI_TRO = {"KY_NHAY": "Ký nháy", "KY_CHINH": "Ký chính"}
MUC_DO = {"THUONG": "Thường", "KHAN": "Khẩn", "HOA_TOC": "Hỏa tốc"}


class LoiTaoTep(Exception):
    def __init__(self, ma, chi_tiet=""):
        super().__init__(f"{ma}: {chi_tiet}" if chi_tiet else ma)
        self.ma = ma


def _du_tieng_viet(path):
    from reportlab.pdfbase.ttfonts import TTFont

    try:
        bang_ma = TTFont("_kiem_tra", path).face.charToGlyph
    except Exception:  # noqa: BLE001 — tệp phông hỏng/không đọc được thì bỏ qua ứng viên
        return False
    return all(ord(c) in bang_ma for c in KY_TU_KIEM_TRA)


def tim_phong_chu():
    """(đường dẫn thường, đường dẫn đậm) hoặc None. Phông cấu hình được dùng nguyên; phông tự dò phải đủ dấu."""
    cau_hinh = getattr(settings, "SIGNING_PDF_FONT", "")
    if cau_hinh:
        if not os.path.isfile(cau_hinh):
            return None
        dam = getattr(settings, "SIGNING_PDF_FONT_BOLD", "") or cau_hinh
        return cau_hinh, dam if os.path.isfile(dam) else cau_hinh
    for thuong, dam in UNG_VIEN_PHONG_CHU:
        if os.path.isfile(thuong) and _du_tieng_viet(thuong):
            return thuong, dam if os.path.isfile(dam) else thuong
    return None


@lru_cache(maxsize=8)
def _dang_ky_phong(path):
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    ten = "SigningVN-" + hashlib.sha1(path.encode("utf-8")).hexdigest()[:10]
    pdfmetrics.registerFont(TTFont(ten, path))
    return ten


def _phong_chu():
    duong_dan = tim_phong_chu()
    if duong_dan is None:
        raise LoiTaoTep("thieu_phong_chu", "Không có phông chữ tiếng Việt (đặt SIGNING_PDF_FONT).")
    return _dang_ky_phong(duong_dan[0]), _dang_ky_phong(duong_dan[1])


def _gio_vn(iso):
    if not iso:
        return ""
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return dt.astimezone(ZoneInfo(settings.TIME_ZONE)).strftime("%d/%m/%Y %H:%M:%S")


def _khoi_chu_ky(c, khung, nguoi_ky, anh, phong, phong_dam):
    """Dán ảnh chữ ký (snapshot lúc ký) vào khung; chưa có ảnh thì in khối chữ "ĐÃ KÝ DUYỆT"."""
    from reportlab.lib.colors import Color
    from reportlab.lib.utils import ImageReader

    x, y, rong, cao = khung
    ck = nguoi_ky["chu_ky"]
    co_chu = max(4.5, min(8.0, cao / 6))
    cao_dong = co_chu * 1.25
    xanh = Color(0.05, 0.25, 0.6)
    c.setFillColor(xanh)
    if anh:
        # Ảnh ở phần trên khung, hai dòng chú thích (tên, thời điểm) ở đáy khung
        chu_thich = [nguoi_ky["ten_nguoi_ky"], _gio_vn(ck["ngay_ky"])]
        cao_chu = cao_dong * len(chu_thich) + co_chu * 0.4
        c.drawImage(ImageReader(io.BytesIO(anh)), x, y + cao_chu, rong, max(cao - cao_chu, 1),
                    preserveAspectRatio=True, anchor="c", mask="auto")
        c.setFont(phong, co_chu)
        for i, dong in enumerate(chu_thich):
            c.drawCentredString(x + rong / 2, y + co_chu * 0.4 + cao_dong * (len(chu_thich) - 1 - i), dong[:60])
        return
    dong_chu = [d for d in ("ĐÃ KÝ DUYỆT", nguoi_ky["ten_nguoi_ky"], nguoi_ky.get("ten_chuc_vu") or "",
                            _gio_vn(ck["ngay_ky"])) if d]
    c.setStrokeColor(xanh)
    c.setLineWidth(0.6)
    c.rect(x, y, rong, cao)
    for i, dong in enumerate(dong_chu):  # từ trên xuống trong khung
        c.setFont(phong_dam if i == 0 else phong, co_chu)
        c.drawCentredString(x + rong / 2, y + cao - (i + 1) * cao_dong, dong[:60])


def _lop_phu(rong, cao, dong_chan, khoi_ky, phong, phong_dam):
    """Lớp phủ một trang: dòng nhận diện ở chân trang và các khối chữ ký đặt trên trang đó."""
    from reportlab.lib.colors import Color
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(rong, cao))
    for vi_tri, nguoi_ky, anh in khoi_ky:
        # Tỷ lệ % theo trang, gốc trên-trái (UI) -> điểm PDF, gốc dưới-trái
        x = float(vi_tri["toa_do_x"]) / 100 * rong
        w = float(vi_tri["chieu_rong_khung"]) / 100 * rong
        h = float(vi_tri["chieu_cao_khung"]) / 100 * cao
        y = cao - float(vi_tri["toa_do_y"]) / 100 * cao - h
        _khoi_chu_ky(c, (x, y, w, h), nguoi_ky, anh, phong, phong_dam)
    c.setFont(phong, 7)
    c.setFillColor(Color(0.55, 0.1, 0.1))
    c.drawCentredString(rong / 2, 10, dong_chan)
    c.save()
    return buf.getvalue()


def _trang_phe_duyet(noi_dung, ma_bam_bang_chung, phong, phong_dam):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    from xml.sax.saxutils import escape

    thuong = ParagraphStyle("thuong", fontName=phong, fontSize=9, leading=12)
    nho = ParagraphStyle("nho", parent=thuong, fontSize=7.5, leading=10, textColor=colors.HexColor("#444444"))
    dam = ParagraphStyle("dam", parent=thuong, fontName=phong_dam)
    tieu_de = ParagraphStyle("tieu_de", parent=dam, fontSize=14, leading=18, alignment=1)
    nhan = ParagraphStyle("nhan", parent=dam, fontSize=11, leading=15, alignment=1,
                          textColor=colors.HexColor("#8b1a1a"))

    def p(text, style=thuong):
        return Paragraph(escape(str(text or "")), style)

    ho_so, luot = noi_dung["ho_so"], noi_dung["luot_trinh"]
    van_ban = ho_so.get("van_ban") or {}
    mo_ta_vb = " — ".join(x for x in (van_ban.get("so_hieu"), van_ban.get("trich_yeu")) if x)
    quy_trinh = ho_so["quy_trinh"]
    thong_tin = [
        ("Hồ sơ trình ký", f"#{ho_so['id']} — lượt {luot['so_luot']}"),
        ("Văn bản", mo_ta_vb or f"Văn bản đi #{ho_so['van_ban_id']}"),
        ("Quy trình", f"{quy_trinh['ma']} — {quy_trinh['ten']} (phiên bản {quy_trinh['phien_ban']})"),
        ("Mức độ", MUC_DO.get(ho_so["muc_do"], ho_so["muc_do"])),
        ("Người trình", ho_so["nguoi_tao"]["ten"]),
        ("Gửi lúc", _gio_vn(luot["thoi_diem_gui"])),
        ("Hoàn tất duyệt lúc", _gio_vn(luot["thoi_diem_hoan_thanh"])),
        ("SHA-256 tệp gốc", luot["ma_bam_tai_lieu"]),
    ]
    bang_tt = Table([[p(k, dam), p(v)] for k, v in thong_tin], colWidths=[40 * mm, 130 * mm])
    bang_tt.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                 ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#cccccc"))]))

    dong = [[p(h, dam) for h in ("Cấp", "Người ký", "Vai trò", "Thời điểm ký", "Ghi chú")]]
    for cap in noi_dung["cap_ky"]:
        for n in cap["nguoi_ky"]:
            ck = n["chu_ky"] or {}
            ten = escape(n["ten_nguoi_ky"]) + (f"<br/>{escape(n['ten_chuc_vu'])}" if n.get("ten_chuc_vu") else "")
            if ck:
                ten += f"<br/><font size=6.5>Khóa {escape(ck['dau_van_tay_khoa'][:16])}…</font>"
            ghi_chu = ("Trễ hạn. " if ck.get("ky_tre_han") else "") + (ck.get("ghi_chu_ky") or "")
            dong.append([p(f"{cap['cap_ky']}. {cap['ten_cap_ky']}"), Paragraph(ten, thuong),
                         p(VAI_TRO.get(n["vai_tro_ky"], n["vai_tro_ky"])), p(_gio_vn(ck.get("ngay_ky"))), p(ghi_chu)])
    bang_ky = Table(dong, colWidths=[34 * mm, 50 * mm, 20 * mm, 32 * mm, 34 * mm], repeatRows=1)
    bang_ky.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eeeeee")),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#999999")),
    ]))

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm,
                            bottomMargin=18 * mm, title=f"Trang phê duyệt nội bộ — hồ sơ #{ho_so['id']}")
    doc.build([
        p("TRANG PHÊ DUYỆT NỘI BỘ", tieu_de), Spacer(1, 3 * mm),
        p(noi_dung["nhan_dien"], nhan),
        p("Tệp này chưa cấp số, chưa ký số pháp lý và không thay cho văn bản ban hành.", nho), Spacer(1, 5 * mm),
        bang_tt, Spacer(1, 6 * mm), p("Các cấp ký duyệt", dam), Spacer(1, 2 * mm), bang_ky, Spacer(1, 6 * mm),
        p(f"Mã băm bằng chứng (SHA-256): {ma_bam_bang_chung}", nho),
        p("Các trang trước là nguyên văn tệp gốc, chỉ thêm dòng nhận diện ở chân trang. Mỗi chữ ký Ed25519 được "
          "ký trên mã băm SHA-256 của tệp gốc; bằng chứng đầy đủ (chữ ký, khóa công khai) đính kèm trong tệp "
          f"bang-chung-{luot['id']}.json và xem được qua API /api/v1/signing/trinh-ky/{ho_so['id']}/bang-chung/.",
          nho),
    ])
    return buf.getvalue()


def dung_tep_hoan_tat(tep_goc: bytes, noi_dung: dict, ma_bam_bang_chung: str, anh_chu_ky=None) -> bytes:
    """`anh_chu_ky`: {id chữ ký: bytes PNG snapshot} đã kiểm mã băm theo bằng chứng."""
    from pypdf import PdfReader, PdfWriter, Transformation
    from pypdf.errors import PdfReadError

    anh_chu_ky = anh_chu_ky or {}
    phong, phong_dam = _phong_chu()
    try:
        reader = PdfReader(io.BytesIO(tep_goc))
        if reader.is_encrypted and not reader.decrypt(""):
            raise LoiTaoTep("tep_goc_bi_ma_hoa", "Tệp gốc có mật khẩu.")
        trang_goc = list(reader.pages)
    except (PdfReadError, ValueError, KeyError, TypeError) as exc:
        raise LoiTaoTep("tep_goc_khong_doc_duoc", str(exc)) from exc

    ho_so, luot = noi_dung["ho_so"], noi_dung["luot_trinh"]
    dong_chan = (f"{noi_dung['nhan_dien']} · Hồ sơ trình ký #{ho_so['id']}, lượt {luot['so_luot']} · "
                 f"Mã bằng chứng {ma_bam_bang_chung[:16]}")
    khoi_theo_trang = {}
    for cap in noi_dung["cap_ky"]:
        for n in cap["nguoi_ky"]:
            if n.get("vi_tri") and n["chu_ky"]:
                khoi_theo_trang.setdefault(n["vi_tri"]["trang_ky"], []).append(
                    (n["vi_tri"], n, anh_chu_ky.get(n["chu_ky"]["id"])))
    writer = PdfWriter()
    for so, trang in enumerate(trang_goc, start=1):
        trang = writer.add_page(trang)
        trang.transfer_rotation_to_content()
        hop = trang.mediabox
        lop = _lop_phu(float(hop.width), float(hop.height), dong_chan, khoi_theo_trang.get(so, []), phong, phong_dam)
        trang.merge_transformed_page(PdfReader(io.BytesIO(lop)).pages[0],
                                     Transformation().translate(float(hop.left), float(hop.bottom)))
    for trang in PdfReader(io.BytesIO(_trang_phe_duyet(noi_dung, ma_bam_bang_chung, phong, phong_dam))).pages:
        writer.add_page(trang)
    writer.add_attachment(f"bang-chung-{luot['id']}.json", ma_hoa_chuan(noi_dung))
    writer.add_metadata({"/Title": f"Bản duyệt nội bộ — hồ sơ trình ký #{ho_so['id']}",
                         "/Subject": noi_dung["nhan_dien"], "/Producer": "QLVB TLBM — Trình ký"})
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()
