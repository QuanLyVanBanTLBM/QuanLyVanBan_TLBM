from django.db import models


class TrangThaiQuyTrinh(models.TextChoices):
    NHAP = "NHAP", "Nháp"
    HOAT_DONG = "HOAT_DONG", "Hoạt động"
    NGUNG = "NGUNG", "Ngừng"


class PhamViQuyTrinh(models.TextChoices):
    PHONG_BAN = "PHONG_BAN", "Phòng ban"
    CONG_TY = "CONG_TY", "Công ty"


class PhamViChucVu(models.TextChoices):
    """Chức vụ của người ký cấu hình được hiểu tương đối (plan mục 3.2, #80 Phase 7)."""

    DON_VI_NGUOI_TAO = "DON_VI_NGUOI_TAO", "Trong đơn vị người tạo"
    DON_VI_CO_DINH = "DON_VI_CO_DINH", "Trong đơn vị cố định của cấp"
    TOAN_CO_QUAN = "TOAN_CO_QUAN", "Toàn cơ quan"


class VaiTroKy(models.TextChoices):
    KY_CHINH = "KY_CHINH", "Ký chính"


class LoaiVanBan(models.TextChoices):
    # Bản ghi gắn ngoài Trình ký chỉ nhận văn bản đi (Phase 6c); PDF dự thảo chưa vào sổ để document_type=NULL. Văn bản đến
    # thuộc luồng chỉ đạo của Nhóm 2; văn bản mật đã bỏ khỏi hệ thống.
    VAN_BAN_DI = "vanbandi", "Văn bản"


class TrangThaiYeuCau(models.TextChoices):
    NHAP = "NHAP", "Nháp"
    CHO_KY = "CHO_KY", "Chờ ký"
    HOAN_THANH = "HOAN_THANH", "Hoàn thành"
    TU_CHOI = "TU_CHOI", "Từ chối"
    HUY = "HUY", "Hủy"


class TrangThaiLuotTrinh(models.TextChoices):
    NHAP = "NHAP", "Nháp"
    CHO_KY = "CHO_KY", "Chờ ký"
    YEU_CAU_SUA = "YEU_CAU_SUA", "Yêu cầu sửa"
    HOAN_THANH = "HOAN_THANH", "Hoàn thành"
    TU_CHOI = "TU_CHOI", "Từ chối"
    HUY = "HUY", "Hủy"


class TrangThaiCapKy(models.TextChoices):
    CHUA_MO = "CHUA_MO", "Chưa mở"
    DANG_KY = "DANG_KY", "Đang ký"
    HOAN_THANH = "HOAN_THANH", "Hoàn thành"
    TAM_DUNG = "TAM_DUNG", "Tạm dừng"


class TrangThaiNguoiKy(models.TextChoices):
    CHO_KY = "CHO_KY", "Chờ ký"
    DA_KY = "DA_KY", "Đã ký"
    TU_CHOI = "TU_CHOI", "Từ chối"
    YEU_CAU_SUA = "YEU_CAU_SUA", "Yêu cầu sửa"


class TrangThaiKhoa(models.TextChoices):
    CHO_KICH_HOAT = "CHO_KICH_HOAT", "Chờ kích hoạt"
    HOAT_DONG = "HOAT_DONG", "Hoạt động"
    DA_XOAY_VONG = "DA_XOAY_VONG", "Đã xoay vòng"
    THU_HOI = "THU_HOI", "Thu hồi"
    HET_HAN = "HET_HAN", "Hết hạn"


class TrangThaiXacMinh(models.TextChoices):
    CHUA_XAC_MINH = "CHUA_XAC_MINH", "Chưa xác minh"
    HOP_LE = "HOP_LE", "Hợp lệ"
    KHONG_HOP_LE = "KHONG_HOP_LE", "Không hợp lệ"


class TrangThaiManifest(models.TextChoices):
    NHAP = "NHAP", "Nháp"
    DA_CHOT = "DA_CHOT", "Đã chốt"


class TrangThaiTepHoanTat(models.TextChoices):
    """Trạng thái sinh tệp PDF hoàn tất của lượt trình (Phase 10 lõi, #80); NULL khi lượt chưa hoàn thành."""

    DANG_XU_LY = "DANG_XU_LY", "Đang xử lý"
    LOI = "LOI", "Lỗi"
    THANH_CONG = "THANH_CONG", "Thành công"


class TrangThaiThread(models.TextChoices):
    DANG_MO = "DANG_MO", "Đang mở"
    DA_GIAI_QUYET = "DA_GIAI_QUYET", "Đã giải quyết"


class KenhThongBao(models.TextChoices):
    IN_APP = "IN_APP", "Trong ứng dụng"
    EMAIL = "EMAIL", "Email"


class TrangThaiThongBao(models.TextChoices):
    CHO_GUI = "CHO_GUI", "Chờ gửi"
    DA_GUI = "DA_GUI", "Đã gửi"
    THAT_BAI = "THAT_BAI", "Thất bại"
