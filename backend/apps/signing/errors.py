import re

from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import APIException, NotFound
from rest_framework.views import APIView
from rest_framework.views import exception_handler as drf_exception_handler


class SigningError(APIException):
    """Lỗi nghiệp vụ với mã lỗi ổn định để client xử lý."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "loi_nghiep_vu"
    default_detail = "Yêu cầu không hợp lệ."

    def __init__(self, code=None, detail=None, status_code=None, fields=None):
        super().__init__(detail=detail, code=code)
        if status_code is not None:
            self.status_code = status_code
        self.fields = fields or {}


class ConflictError(SigningError):
    status_code = status.HTTP_409_CONFLICT
    default_code = "xung_dot_trang_thai"
    default_detail = "Trạng thái hiện tại không cho phép thao tác."


# Lỗi chuẩn của Django/DRF (404, 401, 403, 405, 429) mặc định trả chi tiết tiếng Anh: thay bằng tiếng Việt theo mã
# trạng thái; giao diện dịch theo `code`.
CHI_TIET_CHUAN = {
    status.HTTP_401_UNAUTHORIZED: "Chưa đăng nhập hoặc phiên đăng nhập đã hết hạn.",
    status.HTTP_403_FORBIDDEN: "Tài khoản không có quyền thực hiện thao tác này.",
    status.HTTP_404_NOT_FOUND: "Không tìm thấy hoặc tài khoản không được xem dữ liệu này.",
    status.HTTP_405_METHOD_NOT_ALLOWED: "Phương thức không được hỗ trợ.",
    status.HTTP_429_TOO_MANY_REQUESTS: "Thao tác quá nhiều lần, thử lại sau.",
}


# Thông báo mặc định của DRF chưa có bản dịch tiếng Việt: (mẫu tiếng Anh, thay bằng). `{1}` lấy nhóm bắt đầu của mẫu.
THONG_BAO_VALIDATION = (
    (re.compile(r"Ensure this field has no more than (\d+) characters\."), "Tối đa {1} ký tự."),
    (re.compile(r"Ensure this field has at least (\d+) characters\."), "Tối thiểu {1} ký tự."),
    (re.compile(r"Ensure this value is less than or equal to (\S+?)\."), "Tối đa {1}."),
    (re.compile(r"Ensure this value is greater than or equal to (\S+?)\."), "Tối thiểu {1}."),
    (re.compile(r"Datetime has wrong format.*"), "Ngày giờ không đúng định dạng."),
    (re.compile(r"Date has wrong format.*"), "Ngày không đúng định dạng."),
    (re.compile(r"Invalid pk .* object does not exist\."), "Không tồn tại."),
    (re.compile(r"Incorrect type\..*"), "Giá trị không hợp lệ."),
    (re.compile(r".* is not a valid choice\."), "Giá trị không hợp lệ."),
    (re.compile(r"A valid integer is required\."), "Phải là số nguyên."),
    (re.compile(r"A valid number is required\."), "Phải là số."),
    (re.compile(r"Not a valid string\."), "Phải là chuỗi ký tự."),
    (re.compile(r"Null characters are not allowed\."), "Không được chứa ký tự NUL."),
    (re.compile(r"Value must be valid JSON\."), "Phải là JSON hợp lệ."),
    (re.compile(r"Invalid data\. Expected a dictionary.*"), "Dữ liệu phải là một đối tượng."),
    (re.compile(r"Expected a list of items.*"), "Phải là một danh sách."),
    (re.compile(r"This field is required\."), "Bắt buộc."),
    (re.compile(r"This field may not be (null|blank)\."), "Không được để trống."),
    (re.compile(r"Enter a valid .*"), "Giá trị không hợp lệ."),
    (re.compile(r"No file was submitted\."), "Chưa chọn tệp."),
    (re.compile(r"The submitted file is empty\."), "Tệp rỗng."),
)


def viet_hoa_thong_bao(gia_tri):
    """Đổi các thông báo validation tiếng Anh của DRF sang tiếng Việt trong cấu trúc lỗi lồng nhau."""
    if isinstance(gia_tri, dict):
        return {khoa: viet_hoa_thong_bao(v) for khoa, v in gia_tri.items()}
    if isinstance(gia_tri, (list, tuple)):
        return [viet_hoa_thong_bao(v) for v in gia_tri]
    if isinstance(gia_tri, str):
        for mau, thay in THONG_BAO_VALIDATION:
            khop = mau.fullmatch(str(gia_tri))
            if khop:
                return thay.format(None, *khop.groups())
    return gia_tri


def exception_handler(exc, context):
    """Lỗi trả dạng {"code", "detail", "fields"}; lỗi validation DRF giữ chi tiết theo field."""
    response = drf_exception_handler(exc, context)
    if response is None:
        return None
    if isinstance(exc, SigningError):
        response.data = {
            "code": exc.get_codes(),
            "detail": str(exc.detail),
            "fields": exc.fields,
        }
    elif response.status_code == status.HTTP_400_BAD_REQUEST and isinstance(response.data, dict):
        response.data = {"code": "du_lieu_khong_hop_le", "detail": "Dữ liệu không hợp lệ.", "fields": viet_hoa_thong_bao(response.data)}
    elif isinstance(response.data, dict) and "detail" in response.data:
        response.data = {
            "code": "khong_tim_thay" if isinstance(exc, (Http404, NotFound)) else getattr(exc, "default_code", "loi"),
            "detail": CHI_TIET_CHUAN.get(response.status_code, str(response.data["detail"])),
            "fields": {},
        }
    return response


class ImmutableEvidenceError(ConflictError):
    default_code = "bang_chung_bat_bien"
    default_detail = "Bằng chứng đã ghi nhận không được sửa hoặc xóa."


class SigningAPIView(APIView):
    """Base view của module: chỉ áp dụng định dạng lỗi này cho /api/v1/signing/, không đổi module khác."""

    def get_exception_handler(self):
        return exception_handler
