"""
Ảnh chữ ký cá nhân do trình duyệt gửi kèm yêu cầu ký (#420).

Ảnh chữ ký hiện lưu phía trình duyệt nên server nhận ảnh cùng yêu cầu ký, kiểm tra nghiêm ngặt rồi chụp snapshot
như luồng cũ. Chỉ nhận PNG (kiểm theo chữ ký tệp và khối IHDR), tối đa 2 MB, kích thước trong giới hạn hợp lý.
"""

import base64
import binascii
import struct

ANH_TOI_DA = 2 * 1024 * 1024
CHU_KY_PNG = b"\x89PNG\r\n\x1a\n"
CANH_TOI_DA = 4000  # px mỗi cạnh
TIEN_TO_DATA_URL = "data:image/png;base64,"


class AnhChuKyKhongHop(ValueError):
    """Ảnh không đạt kiểm tra; thông điệp dùng làm lỗi trường."""


def giai_ma_anh(gia_tri: str) -> bytes:
    """Nhận Base64 thuần hoặc data URL `data:image/png;base64,...`; trả bytes PNG đã kiểm tra."""
    chuoi = gia_tri.strip()
    if chuoi.startswith("data:"):
        if not chuoi.startswith(TIEN_TO_DATA_URL):
            raise AnhChuKyKhongHop("Ảnh chữ ký phải là PNG.")
        chuoi = chuoi[len(TIEN_TO_DATA_URL):]
    if len(chuoi) > (ANH_TOI_DA * 4) // 3 + 8:
        raise AnhChuKyKhongHop("Ảnh chữ ký vượt quá 2 MB.")
    try:
        du_lieu = base64.b64decode(chuoi, validate=True)
    except (binascii.Error, ValueError):
        raise AnhChuKyKhongHop("Ảnh chữ ký không phải Base64 hợp lệ.")
    if len(du_lieu) > ANH_TOI_DA:
        raise AnhChuKyKhongHop("Ảnh chữ ký vượt quá 2 MB.")
    kiem_tra_png(du_lieu)
    return du_lieu


def kiem_tra_png(du_lieu: bytes) -> None:
    if not du_lieu.startswith(CHU_KY_PNG) or len(du_lieu) < 33 or du_lieu[12:16] != b"IHDR":
        raise AnhChuKyKhongHop("Ảnh chữ ký phải là PNG.")
    rong, cao = struct.unpack(">II", du_lieu[16:24])
    if not (0 < rong <= CANH_TOI_DA and 0 < cao <= CANH_TOI_DA):
        raise AnhChuKyKhongHop(f"Kích thước ảnh chữ ký phải trong khoảng 1–{CANH_TOI_DA} px mỗi cạnh.")
    if not du_lieu.rstrip(b"\x00").endswith(b"IEND\xaeB`\x82"):
        raise AnhChuKyKhongHop("Ảnh chữ ký PNG bị cắt hoặc hỏng.")
