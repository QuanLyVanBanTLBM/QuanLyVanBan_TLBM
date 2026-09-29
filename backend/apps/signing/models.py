"""
Phân hệ Trình ký số — Nhóm 5.

Mô hình dữ liệu theo đúng signing-backend-plan.md mục 5.1–5.3 (commit c1b9704):
tên field tiếng Việt không dấu, trừ id/create_by/created_at/update_by/update_at;
FK khai báo không kèm hậu tố _id; FK tới bảng lịch sử/bằng chứng dùng PROTECT.

Chưa có model của nhóm khác nên tạm lưu dạng số (cột trùng tên cột FK sau này):
- van_ban_id  -> bảng văn bản Nhóm 2 (chưa chốt một bảng hay ba bảng)
- don_vi_id, chuc_vu_id -> đơn vị / chức vụ (Nhóm 7)
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

USER = settings.AUTH_USER_MODEL
SHA256_HEX = r"^[0-9a-f]{64}$"


# ─────────────────────────────────────────────────────────────────────────────
# Danh mục giá trị (enum)
# ─────────────────────────────────────────────────────────────────────────────

class QuyTrinhTrangThai(models.TextChoices):
    NHAP = "NHAP", "Nháp"
    HOAT_DONG = "HOAT_DONG", "Hoạt động"
    NGUNG = "NGUNG", "Ngừng"


class PhamVi(models.TextChoices):
    PHONG_BAN = "PHONG_BAN", "Phòng ban"
    CONG_TY = "CONG_TY", "Công ty"


class KieuKy(models.TextChoices):
    TUAN_TU = "TUAN_TU", "Tuần tự"
    SONG_SONG = "SONG_SONG", "Song song"


class VaiTroKy(models.TextChoices):
    KY_NHAY = "KY_NHAY", "Ký nháy"
    KY_CHINH = "KY_CHINH", "Ký chính"


class TrinhKyTrangThai(models.TextChoices):
    NHAP = "NHAP", "Nháp"
    CHO_KY = "CHO_KY", "Chờ ký"
    HOAN_THANH = "HOAN_THANH", "Hoàn thành"
    TU_CHOI = "TU_CHOI", "Từ chối"
    HUY = "HUY", "Hủy"


class LuotTrinhTrangThai(models.TextChoices):
    NHAP = "NHAP", "Nháp"
    CHO_KY = "CHO_KY", "Chờ ký"
    YEU_CAU_SUA = "YEU_CAU_SUA", "Yêu cầu sửa"
    HOAN_THANH = "HOAN_THANH", "Hoàn thành"
    TU_CHOI = "TU_CHOI", "Từ chối"
    HUY = "HUY", "Hủy"


class CapKyTrangThai(models.TextChoices):
    CHUA_MO = "CHUA_MO", "Chưa mở"
    DANG_KY = "DANG_KY", "Đang ký"
    HOAN_THANH = "HOAN_THANH", "Hoàn thành"
    TAM_DUNG = "TAM_DUNG", "Tạm dừng"


class NguoiKyTrangThai(models.TextChoices):
    CHO_KY = "CHO_KY", "Chờ ký"
    DA_KY = "DA_KY", "Đã ký"
    TU_CHOI = "TU_CHOI", "Từ chối"
    YEU_CAU_SUA = "YEU_CAU_SUA", "Yêu cầu sửa"


class KhoaKyTrangThai(models.TextChoices):
    CHO_KICH_HOAT = "CHO_KICH_HOAT", "Chờ kích hoạt"
    HOAT_DONG = "HOAT_DONG", "Hoạt động"
    DA_XOAY_VONG = "DA_XOAY_VONG", "Đã xoay vòng"
    THU_HOI = "THU_HOI", "Thu hồi"
    HET_HAN = "HET_HAN", "Hết hạn"


class XacMinhTrangThai(models.TextChoices):
    CHUA_XAC_MINH = "CHUA_XAC_MINH", "Chưa xác minh"
    HOP_LE = "HOP_LE", "Hợp lệ"
    KHONG_HOP_LE = "KHONG_HOP_LE", "Không hợp lệ"


class BangChungTrangThai(models.TextChoices):
    NHAP = "NHAP", "Nháp"
    DA_CHOT = "DA_CHOT", "Đã chốt"


class YeuCauSuaTrangThai(models.TextChoices):
    DANG_MO = "DANG_MO", "Đang mở"
    DA_GIAI_QUYET = "DA_GIAI_QUYET", "Đã giải quyết"


class KenhThongBao(models.TextChoices):
    IN_APP = "IN_APP", "Trong hệ thống"
    EMAIL = "EMAIL", "Email"


class ThongBaoTrangThai(models.TextChoices):
    CHO_GUI = "CHO_GUI", "Chờ gửi"
    DA_GUI = "DA_GUI", "Đã gửi"
    THAT_BAI = "THAT_BAI", "Thất bại"


# Loại đối tượng thuộc luồng ký: nhật ký của các loại này bắt buộc có trinh_ky (plan 5.2)
LOAI_DOI_TUONG_LUONG_KY = ["signing_request", "signing_attempt", "signing_request_step_signer", "signing_signature"]


class BatBienError(Exception):
    """Thao tác sửa/xóa bản ghi bằng chứng bất biến."""


# ─────────────────────────────────────────────────────────────────────────────
# Quy trình mẫu
# ─────────────────────────────────────────────────────────────────────────────

class SigningProcess(models.Model):
    ma_quy_trinh = models.CharField("Mã quy trình", max_length=50)
    ten_quy_trinh = models.CharField("Tên quy trình", max_length=255)
    mo_ta = models.TextField("Mô tả", blank=True, default="")
    phien_ban = models.PositiveSmallIntegerField("Phiên bản", default=1, db_default=1)
    trang_thai = models.CharField("Trạng thái", max_length=20, choices=QuyTrinhTrangThai.choices,
                                  default=QuyTrinhTrangThai.NHAP, db_default=QuyTrinhTrangThai.NHAP)
    pham_vi = models.CharField("Phạm vi áp dụng", max_length=20, choices=PhamVi.choices)
    kieu_ky_mac_dinh = models.CharField("Cách thức ký mặc định", max_length=20, choices=KieuKy.choices)
    cau_hinh_nhac_han = models.JSONField("Cấu hình nhắc hạn", null=True, blank=True)  # rỗng: trước hạn 24h và đúng hạn
    create_by = models.ForeignKey(USER, on_delete=models.PROTECT, related_name="+", verbose_name="Người tạo")
    created_at = models.DateTimeField("Ngày tạo", auto_now_add=True)
    update_by = models.ForeignKey(USER, on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
                                  verbose_name="Người cập nhật")
    update_at = models.DateTimeField("Ngày cập nhật", auto_now=True)

    class Meta:
        db_table = "signing_process"
        verbose_name = "Quy trình trình ký"
        verbose_name_plural = "Quy trình trình ký"
        ordering = ["ma_quy_trinh", "-phien_ban"]
        constraints = [
            models.UniqueConstraint(fields=["ma_quy_trinh", "phien_ban"], name="uq_signing_process_ma_phien_ban"),
        ]

    def __str__(self):
        return f"{self.ma_quy_trinh} v{self.phien_ban} — {self.ten_quy_trinh}"


class SigningProcessStep(models.Model):
    quy_trinh = models.ForeignKey(SigningProcess, on_delete=models.CASCADE, related_name="cap_ky_set",
                                  verbose_name="Quy trình")
    cap_ky = models.PositiveSmallIntegerField("Cấp ký")  # số hiệu hiển thị
    ten_cap_ky = models.CharField("Tên cấp ký", max_length=255)
    thu_tu = models.PositiveSmallIntegerField("Thứ tự ký")  # quyết định thứ tự mở cấp
    don_vi_id = models.BigIntegerField("Đơn vị ký", null=True, blank=True)  # FK Nhóm 7 khi có model
    so_gio_xu_ly = models.PositiveIntegerField("Số giờ xử lý của cấp", null=True, blank=True)
    dang_ap_dung = models.BooleanField("Đang áp dụng", default=True, db_default=True)
    ghi_chu = models.TextField("Ghi chú", blank=True, default="")
    created_at = models.DateTimeField("Ngày tạo", auto_now_add=True)

    class Meta:
        db_table = "signing_process_step"
        verbose_name = "Cấp ký trong quy trình"
        verbose_name_plural = "Cấp ký trong quy trình"
        ordering = ["quy_trinh", "thu_tu"]
        constraints = [
            models.UniqueConstraint(fields=["quy_trinh", "thu_tu"], name="uq_signing_process_step_thu_tu"),
        ]

    def __str__(self):
        return f"{self.quy_trinh} — cấp {self.cap_ky}: {self.ten_cap_ky}"


class SigningProcessStepSigner(models.Model):
    buoc_quy_trinh = models.ForeignKey(SigningProcessStep, on_delete=models.CASCADE, related_name="nguoi_ky_set",
                                       verbose_name="Cấp ký trong quy trình")
    nguoi_ky = models.ForeignKey(USER, on_delete=models.PROTECT, null=True, blank=True, related_name="+",
                                 verbose_name="Người ký")
    chuc_vu_id = models.BigIntegerField("Chức vụ ký", null=True, blank=True)  # FK Nhóm 7 khi có model
    vai_tro_ky = models.CharField("Vai trò ký", max_length=20, choices=VaiTroKy.choices, default=VaiTroKy.KY_CHINH,
                                  db_default=VaiTroKy.KY_CHINH)
    chan_ky_chinh = models.BooleanField("Chặn ký chính", default=True, db_default=True)
    thu_tu = models.PositiveSmallIntegerField("Thứ tự trong cấp")
    created_at = models.DateTimeField("Ngày tạo", auto_now_add=True)

    class Meta:
        db_table = "signing_process_step_signer"
        verbose_name = "Người ký cấu hình sẵn"
        verbose_name_plural = "Người ký cấu hình sẵn"
        ordering = ["buoc_quy_trinh", "thu_tu"]
        constraints = [
            # Có đúng một trong nguoi_ky, chuc_vu
            models.CheckConstraint(
                condition=(Q(nguoi_ky__isnull=False, chuc_vu_id__isnull=True)
                           | Q(nguoi_ky__isnull=True, chuc_vu_id__isnull=False)),
                name="chk_signing_process_step_signer_mot_doi_tuong",
            ),
        ]


# ─────────────────────────────────────────────────────────────────────────────
# Trình ký, lượt trình, cấp ký, người ký
# ─────────────────────────────────────────────────────────────────────────────

class SigningRequest(models.Model):
    van_ban_id = models.BigIntegerField("Văn bản liên quan")  # FK Nhóm 2 khi chốt model văn bản
    # Ba field dưới là bản sao của lượt trình hiện hành, chỉ cập nhật khi tạo lượt trình mới
    phien_ban_van_ban = models.CharField("Phiên bản văn bản", max_length=50, blank=True, default="")
    vi_tri_luu_tep = models.CharField("Vị trí lưu tệp", max_length=500, blank=True, default="")
    ma_bam_tai_lieu = models.CharField("Mã băm tài liệu", max_length=64, blank=True, default="")
    quy_trinh = models.ForeignKey(SigningProcess, on_delete=models.PROTECT, related_name="trinh_ky_set",
                                  verbose_name="Quy trình trình ký")
    phien_ban_quy_trinh = models.PositiveSmallIntegerField("Phiên bản quy trình")
    muc_do = models.CharField("Mức độ", max_length=20)
    kieu_ky = models.CharField("Cách thức ký", max_length=20, choices=KieuKy.choices)
    trang_thai = models.CharField("Trạng thái", max_length=20, choices=TrinhKyTrangThai.choices,
                                  default=TrinhKyTrangThai.NHAP, db_default=TrinhKyTrangThai.NHAP, db_index=True)
    han_chot = models.DateTimeField("Hạn chót trình ký", null=True, blank=True)
    ngay_gui = models.DateTimeField("Ngày gửi trình ký", null=True, blank=True)
    ngay_hoan_thanh = models.DateTimeField("Ngày hoàn thành", null=True, blank=True)
    ngay_tu_choi = models.DateTimeField("Ngày từ chối", null=True, blank=True)
    ly_do_tu_choi = models.TextField("Lý do từ chối", blank=True, default="")
    ngay_huy = models.DateTimeField("Ngày hủy", null=True, blank=True)
    ly_do_huy = models.TextField("Lý do hủy", blank=True, default="")
    ghi_chu = models.TextField("Ghi chú", blank=True, default="")
    create_by = models.ForeignKey(USER, on_delete=models.PROTECT, related_name="+", verbose_name="Người tạo")
    created_at = models.DateTimeField("Ngày tạo", auto_now_add=True)
    update_by = models.ForeignKey(USER, on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
                                  verbose_name="Người cập nhật")
    update_at = models.DateTimeField("Ngày cập nhật", auto_now=True)

    class Meta:
        db_table = "signing_request"
        verbose_name = "Trình ký"
        verbose_name_plural = "Trình ký"
        ordering = ["-created_at"]


class SigningAttempt(models.Model):
    trinh_ky = models.ForeignKey(SigningRequest, on_delete=models.PROTECT, related_name="luot_trinh_set",
                                 verbose_name="Trình ký")
    so_luot = models.PositiveSmallIntegerField("Số thứ tự lượt trình")
    luot_truoc = models.ForeignKey("self", on_delete=models.PROTECT, null=True, blank=True, related_name="+",
                                   verbose_name="Lượt trình trước")
    phien_ban_van_ban = models.CharField("Phiên bản văn bản", max_length=50, blank=True, default="")
    vi_tri_luu_tep = models.CharField("Vị trí lưu tệp", max_length=500)
    ma_bam_tai_lieu = models.CharField("Mã băm tài liệu", max_length=64)  # nguồn sự thật của mã băm
    trang_thai = models.CharField("Trạng thái", max_length=20, choices=LuotTrinhTrangThai.choices,
                                  default=LuotTrinhTrangThai.NHAP, db_default=LuotTrinhTrangThai.NHAP)
    ly_do = models.TextField("Lý do gửi lại", blank=True, default="")
    khoa_chong_trung = models.CharField("Khóa chống gửi trùng", max_length=255, unique=True, null=True, blank=True)
    thoi_diem_gui = models.DateTimeField("Thời điểm gửi", null=True, blank=True)
    thoi_diem_hoan_thanh = models.DateTimeField("Thời điểm hoàn thành", null=True, blank=True)
    thoi_diem_tu_choi = models.DateTimeField("Thời điểm từ chối", null=True, blank=True)
    thoi_diem_huy = models.DateTimeField("Thời điểm hủy", null=True, blank=True)
    vi_tri_tep_hoan_tat = models.CharField("Vị trí tệp hoàn tất", max_length=500, blank=True, default="")
    ma_bam_tep_hoan_tat = models.CharField("Mã băm tệp hoàn tất", max_length=64, blank=True, default="")
    create_by = models.ForeignKey(USER, on_delete=models.PROTECT, related_name="+", verbose_name="Người tạo")
    created_at = models.DateTimeField("Ngày tạo", auto_now_add=True)
    update_by = models.ForeignKey(USER, on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
                                  verbose_name="Người cập nhật")
    update_at = models.DateTimeField("Ngày cập nhật", auto_now=True)

    class Meta:
        db_table = "signing_attempt"
        verbose_name = "Lượt trình ký"
        verbose_name_plural = "Lượt trình ký"
        ordering = ["trinh_ky", "so_luot"]
        constraints = [
            models.UniqueConstraint(fields=["trinh_ky", "so_luot"], name="uq_signing_attempt_so_luot"),
            models.CheckConstraint(condition=Q(ma_bam_tai_lieu__regex=SHA256_HEX),
                                   name="chk_signing_attempt_ma_bam_sha256"),
        ]

    def clean(self):
        if self.luot_truoc_id and self.luot_truoc.trinh_ky_id != self.trinh_ky_id:
            raise ValidationError({"luot_truoc": "Lượt trình trước phải thuộc cùng yêu cầu trình ký."})


class SigningRequestStep(models.Model):
    luot_trinh = models.ForeignKey(SigningAttempt, on_delete=models.PROTECT, related_name="cap_ky_set",
                                   verbose_name="Lượt trình ký")
    buoc_quy_trinh = models.ForeignKey(SigningProcessStep, on_delete=models.PROTECT, related_name="+",
                                       verbose_name="Cấp theo quy trình")
    cap_ky = models.PositiveSmallIntegerField("Cấp ký")
    ten_cap_ky = models.CharField("Tên cấp ký", max_length=255)
    thu_tu = models.PositiveSmallIntegerField("Thứ tự ký")
    trang_thai = models.CharField("Trạng thái cấp", max_length=20, choices=CapKyTrangThai.choices,
                                  default=CapKyTrangThai.CHUA_MO, db_default=CapKyTrangThai.CHUA_MO)
    han_xu_ly = models.DateTimeField("Hạn xử lý cấp", null=True, blank=True)
    thoi_diem_mo = models.DateTimeField("Thời điểm mở cấp", null=True, blank=True)
    thoi_diem_hoan_thanh = models.DateTimeField("Thời điểm hoàn tất cấp", null=True, blank=True)
    ghi_chu = models.TextField("Ghi chú", blank=True, default="")
    created_at = models.DateTimeField("Ngày tạo", auto_now_add=True)

    class Meta:
        db_table = "signing_request_step"
        verbose_name = "Cấp ký của lượt trình"
        verbose_name_plural = "Cấp ký của lượt trình"
        ordering = ["luot_trinh", "thu_tu"]
        constraints = [
            models.UniqueConstraint(fields=["luot_trinh", "thu_tu"], name="uq_signing_request_step_thu_tu"),
        ]


class SigningRequestStepSigner(models.Model):
    buoc_ky = models.ForeignKey(SigningRequestStep, on_delete=models.PROTECT, related_name="nguoi_ky_set",
                                verbose_name="Cấp ký")
    nguoi_ky = models.ForeignKey(USER, on_delete=models.PROTECT, related_name="+", verbose_name="Người ký")
    chuc_vu_id = models.BigIntegerField("Chức vụ lúc trình", null=True, blank=True)  # FK Nhóm 7 khi có model
    ten_nguoi_ky = models.CharField("Tên người ký", max_length=255)
    ten_chuc_vu = models.CharField("Tên chức vụ", max_length=255, blank=True, default="")
    vai_tro_ky = models.CharField("Vai trò ký", max_length=20, choices=VaiTroKy.choices)
    chan_ky_chinh = models.BooleanField("Chặn ký chính", default=True, db_default=True)
    trang_thai = models.CharField("Trạng thái", max_length=20, choices=NguoiKyTrangThai.choices,
                                  default=NguoiKyTrangThai.CHO_KY, db_default=NguoiKyTrangThai.CHO_KY)
    thoi_diem_mo = models.DateTimeField("Thời điểm mở lượt ký", null=True, blank=True)  # rỗng: chưa được ký
    ngay_ky = models.DateTimeField("Ngày ký", null=True, blank=True)
    ngay_tu_choi = models.DateTimeField("Ngày từ chối", null=True, blank=True)
    ly_do_tu_choi = models.TextField("Lý do từ chối", blank=True, default="")
    chu_ky_hien_hanh = models.ForeignKey("SigningSignature", on_delete=models.PROTECT, null=True, blank=True,
                                         related_name="+", verbose_name="Chữ ký hiện hành")
    uy_quyen_tu = models.ForeignKey(USER, on_delete=models.PROTECT, null=True, blank=True, related_name="+",
                                    verbose_name="Ủy quyền từ người")
    ly_do_uy_quyen = models.TextField("Lý do ủy quyền", blank=True, default="")
    ngay_uy_quyen = models.DateTimeField("Ngày ủy quyền", null=True, blank=True)
    trang_ky = models.PositiveIntegerField("Trang đặt chữ ký", null=True, blank=True)
    toa_do_x = models.DecimalField("Tọa độ X", max_digits=10, decimal_places=4, null=True, blank=True)
    toa_do_y = models.DecimalField("Tọa độ Y", max_digits=10, decimal_places=4, null=True, blank=True)
    chieu_rong_khung = models.DecimalField("Chiều rộng khung ký", max_digits=10, decimal_places=4, null=True,
                                           blank=True)
    chieu_cao_khung = models.DecimalField("Chiều cao khung ký", max_digits=10, decimal_places=4, null=True,
                                          blank=True)
    khoa_chong_trung_thao_tac = models.CharField("Khóa chống thao tác trùng", max_length=255, blank=True, default="")
    created_at = models.DateTimeField("Ngày tạo", auto_now_add=True)

    class Meta:
        db_table = "signing_request_step_signer"
        verbose_name = "Người ký của lượt trình"
        verbose_name_plural = "Người ký của lượt trình"
        ordering = ["buoc_ky", "id"]
        constraints = [
            models.UniqueConstraint(fields=["buoc_ky", "nguoi_ky"], name="uq_signing_request_step_signer_nguoi_ky"),
            # Lý do ủy quyền bắt buộc khi ủy quyền
            models.CheckConstraint(condition=Q(uy_quyen_tu__isnull=True) | ~Q(ly_do_uy_quyen=""),
                                   name="chk_signing_signer_ly_do_uy_quyen"),
        ]

    def clean(self):
        if self.chu_ky_hien_hanh_id and self.chu_ky_hien_hanh.buoc_ky_id != self.pk:
            raise ValidationError({"chu_ky_hien_hanh": "Chữ ký hiện hành phải thuộc đúng người ký này."})


# ─────────────────────────────────────────────────────────────────────────────
# Khóa ký, chữ ký số, bằng chứng tổng hợp
# ─────────────────────────────────────────────────────────────────────────────

class SigningKey(models.Model):
    nguoi_so_huu = models.ForeignKey(USER, on_delete=models.PROTECT, related_name="+", verbose_name="Người sở hữu")
    ma_khoa = models.CharField("Mã khóa", max_length=100, unique=True)
    dau_van_tay = models.CharField("Dấu vân tay khóa", max_length=64, unique=True)
    thuat_toan = models.CharField("Thuật toán", max_length=50, default="Ed25519", db_default="Ed25519")
    khoa_cong_khai = models.TextField("Khóa công khai")  # không có field private key
    trang_thai = models.CharField("Trạng thái", max_length=20, choices=KhoaKyTrangThai.choices,
                                  default=KhoaKyTrangThai.CHO_KICH_HOAT, db_default=KhoaKyTrangThai.CHO_KICH_HOAT)
    thoi_diem_xac_minh_so_huu = models.DateTimeField("Thời điểm xác minh sở hữu khóa", null=True, blank=True)
    thoi_diem_kich_hoat = models.DateTimeField("Thời điểm kích hoạt", null=True, blank=True)
    ngay_hieu_luc = models.DateTimeField("Ngày hiệu lực")
    ngay_het_han = models.DateTimeField("Ngày hết hạn", null=True, blank=True)  # rỗng: không hết hạn
    ngay_thu_hoi = models.DateTimeField("Ngày thu hồi", null=True, blank=True)
    khoa_thay_the = models.ForeignKey("self", on_delete=models.PROTECT, null=True, blank=True, related_name="+",
                                      verbose_name="Khóa thay thế")
    ghi_chu = models.TextField("Ghi chú", blank=True, default="")
    created_at = models.DateTimeField("Ngày tạo", auto_now_add=True)

    class Meta:
        db_table = "signing_key"
        verbose_name = "Khóa ký"
        verbose_name_plural = "Khóa ký"
        constraints = [
            models.UniqueConstraint(fields=["nguoi_so_huu"], condition=Q(trang_thai="HOAT_DONG"),
                                    name="uq_signing_key_mot_khoa_hoat_dong"),
            models.CheckConstraint(
                condition=~Q(trang_thai="HOAT_DONG") | Q(thoi_diem_xac_minh_so_huu__isnull=False),
                name="chk_signing_key_hoat_dong_da_xac_minh",
            ),
        ]


class SigningSignature(models.Model):
    """Bằng chứng bất biến: không sửa nội dung, không xóa (chỉ cập nhật kết quả xác minh lại)."""

    TRUONG_DUOC_CAP_NHAT = {"trang_thai_xac_minh", "thoi_diem_xac_minh"}

    luot_trinh = models.ForeignKey(SigningAttempt, on_delete=models.PROTECT, related_name="chu_ky_set",
                                   verbose_name="Lượt trình ký")
    buoc_ky = models.ForeignKey(SigningRequestStepSigner, on_delete=models.PROTECT, related_name="chu_ky_set",
                                verbose_name="Người ký (lượt ký)")  # không unique: ký lại sau thu hồi
    khoa_ky = models.ForeignKey(SigningKey, on_delete=models.PROTECT, related_name="chu_ky_set",
                                verbose_name="Khóa ký")
    hash_tai_lieu = models.CharField("Hash tài liệu", max_length=64)
    thuat_toan = models.CharField("Thuật toán", max_length=50)
    chu_ky_so = models.TextField("Giá trị chữ ký")  # Base64
    ghi_chu_ky = models.TextField("Ghi chú khi ký", blank=True, default="")
    ky_tre_han = models.BooleanField("Ký trễ hạn", default=False, db_default=False)
    so_giay_tre = models.PositiveIntegerField("Số giây trễ hạn", null=True, blank=True)
    ngay_ky = models.DateTimeField("Ngày ký")
    trang_thai_xac_minh = models.CharField("Trạng thái xác minh", max_length=20, choices=XacMinhTrangThai.choices,
                                           default=XacMinhTrangThai.HOP_LE, db_default=XacMinhTrangThai.HOP_LE)
    thoi_diem_xac_minh = models.DateTimeField("Thời điểm xác minh", null=True, blank=True)
    vi_tri_anh_chu_ky = models.CharField("Vị trí ảnh chữ ký", max_length=500, blank=True, default="")
    ma_bam_anh_chu_ky = models.CharField("Mã băm ảnh chữ ký", max_length=64, blank=True, default="")
    created_at = models.DateTimeField("Ngày tạo", auto_now_add=True)

    class Meta:
        db_table = "signing_signature"
        verbose_name = "Chữ ký số"
        verbose_name_plural = "Chữ ký số"
        constraints = [
            models.CheckConstraint(condition=Q(hash_tai_lieu__regex=SHA256_HEX),
                                   name="chk_signing_signature_hash_sha256"),
        ]

    def save(self, *args, **kwargs):
        if self.pk and not self._state.adding:
            fields = set(kwargs.get("update_fields") or [])
            if not fields or not fields <= self.TRUONG_DUOC_CAP_NHAT:
                raise BatBienError("Chữ ký số là bằng chứng bất biến, chỉ được cập nhật kết quả xác minh.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise BatBienError("Chữ ký số là bằng chứng bất biến, không được xóa.")


class SigningManifest(models.Model):
    luot_trinh = models.ForeignKey(SigningAttempt, on_delete=models.PROTECT, related_name="bang_chung_set",
                                   verbose_name="Lượt trình ký")
    phien_ban_bang_chung = models.PositiveSmallIntegerField("Phiên bản bằng chứng", default=1, db_default=1)
    noi_dung_chuan_hoa = models.JSONField("Nội dung chuẩn hóa")
    ma_bam_bang_chung = models.CharField("Mã băm bằng chứng", max_length=64)
    vi_tri_luu = models.CharField("Vị trí lưu", max_length=500, blank=True, default="")
    trang_thai = models.CharField("Trạng thái", max_length=20, choices=BangChungTrangThai.choices,
                                  default=BangChungTrangThai.NHAP, db_default=BangChungTrangThai.NHAP)
    thoi_diem_chot = models.DateTimeField("Thời điểm chốt", null=True, blank=True)
    create_by = models.ForeignKey(USER, on_delete=models.PROTECT, related_name="+", verbose_name="Người tạo")
    created_at = models.DateTimeField("Ngày tạo", auto_now_add=True)

    class Meta:
        db_table = "signing_manifest"
        verbose_name = "Bằng chứng tổng hợp"
        verbose_name_plural = "Bằng chứng tổng hợp"
        constraints = [
            models.CheckConstraint(condition=Q(ma_bam_bang_chung__regex=SHA256_HEX),
                                   name="chk_signing_manifest_ma_bam_sha256"),
        ]

    def _da_chot_trong_csdl(self):
        return bool(self.pk) and SigningManifest.objects.filter(
            pk=self.pk, trang_thai=BangChungTrangThai.DA_CHOT).exists()

    def save(self, *args, **kwargs):
        if self._da_chot_trong_csdl():
            raise BatBienError("Bằng chứng đã chốt, không được sửa.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self._da_chot_trong_csdl():
            raise BatBienError("Bằng chứng đã chốt, không được xóa.")
        return super().delete(*args, **kwargs)


# ─────────────────────────────────────────────────────────────────────────────
# Yêu cầu chỉnh sửa, nhật ký, thông báo
# ─────────────────────────────────────────────────────────────────────────────

class SigningChangeThread(models.Model):
    luot_trinh = models.ForeignKey(SigningAttempt, on_delete=models.PROTECT, related_name="yeu_cau_sua_set",
                                   verbose_name="Lượt trình ký")
    nguoi_yeu_cau = models.ForeignKey(USER, on_delete=models.PROTECT, related_name="+", verbose_name="Người yêu cầu")
    tieu_de = models.CharField("Tiêu đề", max_length=255)
    ly_do = models.TextField("Lý do")
    trang_thai = models.CharField("Trạng thái", max_length=20, choices=YeuCauSuaTrangThai.choices,
                                  default=YeuCauSuaTrangThai.DANG_MO, db_default=YeuCauSuaTrangThai.DANG_MO)
    thoi_diem_giai_quyet = models.DateTimeField("Thời điểm giải quyết", null=True, blank=True)
    created_at = models.DateTimeField("Ngày tạo", auto_now_add=True)
    update_at = models.DateTimeField("Ngày cập nhật", auto_now=True)

    class Meta:
        db_table = "signing_change_thread"
        verbose_name = "Yêu cầu chỉnh sửa"
        verbose_name_plural = "Yêu cầu chỉnh sửa"


class SigningChangeMessage(models.Model):
    yeu_cau_sua = models.ForeignKey(SigningChangeThread, on_delete=models.PROTECT, related_name="tin_nhan_set",
                                    verbose_name="Yêu cầu chỉnh sửa")
    nguoi_viet = models.ForeignKey(USER, on_delete=models.PROTECT, related_name="+", verbose_name="Người viết")
    noi_dung = models.TextField("Nội dung")
    created_at = models.DateTimeField("Ngày tạo", auto_now_add=True)

    class Meta:
        db_table = "signing_change_message"
        verbose_name = "Tin nhắn trao đổi"
        verbose_name_plural = "Tin nhắn trao đổi"
        ordering = ["created_at", "id"]


class SigningAuditLog(models.Model):
    """Nhật ký chỉ ghi thêm (append-only)."""

    trinh_ky = models.ForeignKey(SigningRequest, on_delete=models.PROTECT, null=True, blank=True,
                                 related_name="nhat_ky_set", verbose_name="Trình ký")
    luot_trinh = models.ForeignKey(SigningAttempt, on_delete=models.PROTECT, null=True, blank=True,
                                   related_name="+", verbose_name="Lượt trình ký")
    buoc_ky = models.ForeignKey(SigningRequestStepSigner, on_delete=models.PROTECT, null=True, blank=True,
                                related_name="+", verbose_name="Người ký (lượt ký)")
    loai_doi_tuong = models.CharField("Loại đối tượng", max_length=50)
    ma_doi_tuong = models.BigIntegerField("Mã đối tượng")
    nguoi_thuc_hien = models.ForeignKey(USER, on_delete=models.PROTECT, related_name="+",
                                        verbose_name="Người thực hiện")
    hanh_dong = models.CharField("Hành động", max_length=50)
    trang_thai_truoc = models.CharField("Trạng thái trước", max_length=20, blank=True, default="")
    trang_thai_sau = models.CharField("Trạng thái sau", max_length=20, blank=True, default="")
    chi_tiet = models.TextField("Nội dung chi tiết", blank=True, default="")
    du_lieu_kem_theo = models.JSONField("Dữ liệu kèm theo", null=True, blank=True)
    dia_chi_ip = models.CharField("Địa chỉ IP", max_length=45, blank=True, default="")
    created_at = models.DateTimeField("Thời điểm", auto_now_add=True)

    class Meta:
        db_table = "signing_audit_log"
        verbose_name = "Nhật ký trình ký"
        verbose_name_plural = "Nhật ký trình ký"
        ordering = ["created_at", "id"]
        constraints = [
            models.CheckConstraint(
                condition=~Q(loai_doi_tuong__in=LOAI_DOI_TUONG_LUONG_KY) | Q(trinh_ky__isnull=False),
                name="chk_signing_audit_log_luong_ky_co_trinh_ky",
            ),
        ]

    def save(self, *args, **kwargs):
        if self.pk and not self._state.adding:
            raise BatBienError("Nhật ký trình ký chỉ được ghi thêm, không được sửa.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise BatBienError("Nhật ký trình ký chỉ được ghi thêm, không được xóa.")


class SigningNotification(models.Model):
    """Thông báo trình ký, đồng thời là outbox (plan 4.1)."""

    trinh_ky = models.ForeignKey(SigningRequest, on_delete=models.PROTECT, related_name="thong_bao_set",
                                 verbose_name="Trình ký")
    buoc_ky = models.ForeignKey(SigningRequestStepSigner, on_delete=models.PROTECT, null=True, blank=True,
                                related_name="+", verbose_name="Người ký (lượt ký)")
    nguoi_nhan = models.ForeignKey(USER, on_delete=models.PROTECT, related_name="+", verbose_name="Người nhận")
    kenh = models.CharField("Kênh", max_length=20, choices=KenhThongBao.choices)
    loai_thong_bao = models.CharField("Loại thông báo", max_length=50)
    trang_thai = models.CharField("Trạng thái", max_length=20, choices=ThongBaoTrangThai.choices,
                                  default=ThongBaoTrangThai.CHO_GUI, db_default=ThongBaoTrangThai.CHO_GUI)
    hen_gio_gui = models.DateTimeField("Hẹn giờ gửi", null=True, blank=True)
    khoa_chong_gui_trung = models.CharField("Khóa chống gửi trùng", max_length=255, unique=True)
    so_lan_gui_lai = models.PositiveIntegerField("Số lần gửi lại", default=0, db_default=0)
    thoi_diem_gui = models.DateTimeField("Thời điểm gửi", null=True, blank=True)
    loi_gui = models.TextField("Lỗi gửi", blank=True, default="")
    created_at = models.DateTimeField("Ngày tạo", auto_now_add=True)

    class Meta:
        db_table = "signing_notification"
        verbose_name = "Thông báo trình ký"
        verbose_name_plural = "Thông báo trình ký"
        indexes = [models.Index(fields=["trang_thai", "hen_gio_gui"], name="idx_signing_notif_outbox")]
