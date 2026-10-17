"""
Hỗ trợ xuất tệp mẫu và nhập dữ liệu Cán bộ Nhân viên (CBNV) bằng Excel (.xlsx, .xls).
Tác giả: Lê Duy Khánh (leduykhanhdevs).
"""
import re
import secrets
from io import BytesIO
from datetime import datetime, date
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
import xlrd
from django.db import transaction
from django.contrib.auth import get_user_model

from organizations.models import DonVi, KhoiKhuVuc
from .models import Employee, EmployeeAssignment, Position, vietnam_phone_regex


def generate_cbnv_template() -> BytesIO:
    """
    Sinh tệp Excel mẫu để nhập danh sách CBNV.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Danh Sach CBNV"

    # Header styling
    header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    header_font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
    hint_font = Font(name="Arial", size=9, italic=True, color="475569")
    align_center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    thin_border = Border(
        left=Side(style="thin", color="CBD5E1"),
        right=Side(style="thin", color="CBD5E1"),
        top=Side(style="thin", color="CBD5E1"),
        bottom=Side(style="thin", color="CBD5E1"),
    )

    headers = [
        "Họ và tên (*)",
        "Ngày sinh (*)",
        "Email (*)",
        "Số điện thoại",
        "Tên Đơn vị / Phòng ban (*)",
        "Tên Chức vụ (*)",
        "Chức danh tự do",
        "Trạng thái (Đang làm việc / Nghỉ việc)",
        "Ghi chú",
    ]

    ws.append(headers)
    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = align_center
        cell.border = thin_border

    # Sample rows
    sample_rows = [
        [
            "Nguyễn Văn An",
            "1990-05-15",
            "an.nguyen@baolong.vn",
            "0912345678",
            "Bảo Long Sài Gòn",
            "Trưởng phòng",
            "Trưởng phòng Kinh doanh",
            "Đang làm việc",
            "Nhân sự tuyển dụng đợt 1",
        ],
        [
            "Trần Thị Bích",
            "1994-11-20",
            "bich.tran@baolong.vn",
            "0987654321",
            "Ban Pháp chế",
            "Chuyên viên",
            "Chuyên viên Pháp lý",
            "Đang làm việc",
            "Nhân sự chính thức",
        ],
    ]

    # Hints row
    hints = [
        "(Ví dụ: Nguyễn Văn A)",
        "(Định dạng YYYY-MM-DD)",
        "(Ví dụ: an.nguyen@baolong.vn)",
        "(Ví dụ: 0912345678)",
        "(Tên đơn vị đã có trong hệ thống)",
        "(Tên chức vụ)",
        "(Chức danh nội bộ)",
        "(Đang làm việc / Nghỉ việc)",
        "(Ghi chú tự do)",
    ]
    ws.append(hints)
    for col_idx in range(1, len(hints) + 1):
        cell = ws.cell(row=2, column=col_idx)
        cell.font = hint_font
        cell.alignment = align_center
        cell.border = thin_border

    for row_data in sample_rows:
        ws.append(row_data)

    # Set column widths
    col_widths = {
        "A": 26,  # Họ và tên
        "B": 16,  # Ngày sinh
        "C": 28,  # Email
        "D": 18,  # SĐT
        "E": 30,  # Đơn vị
        "F": 22,  # Chức vụ
        "G": 24,  # Chức danh
        "H": 25,  # Trạng thái
        "I": 30,  # Ghi chú
    }
    for col_letter, w in col_widths.items():
        ws.column_dimensions[col_letter].width = w

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output


def _parse_date(val) -> date | None:
    if isinstance(val, (datetime, date)):
        return val.date() if isinstance(val, datetime) else val
    if not val:
        return None
    val_str = str(val).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(val_str, fmt).date()
        except ValueError:
            continue
    return None



def _read_rows_xlrd(content: bytes) -> list[tuple]:
    """
    Đọc dữ liệu từ file định dạng Excel cũ (.xls - BIFF8) bằng thư viện xlrd.
    Chuyển đổi kiểu dữ liệu tương thích hoàn toàn với định dạng trả về của openpyxl iter_rows.
    """
    book = xlrd.open_workbook(file_contents=content)
    sheet = book.sheet_by_index(0)
    rows = []
    for r in range(sheet.nrows):
        row_vals = []
        for c in range(sheet.ncols):
            cell = sheet.cell(r, c)
            if cell.ctype == xlrd.XL_CELL_DATE:
                try:
                    dt = xlrd.xldate_as_datetime(cell.value, book.datemode)
                    row_vals.append(dt.date())
                except Exception:
                    row_vals.append(cell.value)
            elif cell.ctype == xlrd.XL_CELL_NUMBER:
                if isinstance(cell.value, float) and cell.value.is_integer():
                    row_vals.append(int(cell.value))
                else:
                    row_vals.append(cell.value)
            elif cell.ctype == xlrd.XL_CELL_BOOLEAN:
                row_vals.append(bool(cell.value))
            elif cell.ctype in (xlrd.XL_CELL_EMPTY, xlrd.XL_CELL_BLANK, xlrd.XL_CELL_ERROR):
                row_vals.append(None)
            else:
                row_vals.append(cell.value)
        rows.append(tuple(row_vals))
    return rows


def _read_rows_from_excel(file_obj) -> list[tuple]:
    """
    Đọc dữ liệu từ file Excel hỗ trợ cả hai định dạng:
      - .xlsx (OpenXML qua openpyxl)
      - .xls (BIFF8 qua xlrd)
    Tự động phát hiện qua phần mở rộng hoặc magic bytes nhị phân.
    """
    content = file_obj.read()
    file_obj.seek(0)

    filename = getattr(file_obj, "name", "").lower()
    is_xls = filename.endswith(".xls") or content.startswith(b"\xd0\xcf\x11\xe0")

    if is_xls:
        return _read_rows_xlrd(content)

    # Mặc định thử đọc qua openpyxl (.xlsx)
    try:
        wb = openpyxl.load_workbook(file_obj, data_only=True)
        ws = wb.active
        return list(ws.iter_rows(values_only=True))
    except Exception as e:
        # Dự phòng trường hợp file .xls bị đổi tên thành .xlsx hoặc lỗi nén
        try:
            return _read_rows_xlrd(content)
        except Exception:
            raise e


def import_cbnv_from_excel(file_obj) -> dict:
    """
    Đọc và kiểm tra tính hợp lệ từng dòng của tệp Excel nhập danh sách CBNV (.xlsx hoặc .xls).
    Trả về dict gồm:
      - success: bool
      - message: str
      - created_count: int
      - errors: list[dict(row=int, message=str)]
    """
    try:
        rows = _read_rows_from_excel(file_obj)
    except Exception as e:
        return {
            "success": False,
            "message": "employees.import.errors.invalidFile",
            "errors": [{
                "row": 0,
                "field": "file",
                "code": "employees.import.errors.invalidFile",
                "value": "",
                "message": f"Không thể đọc tệp Excel. Lỗi: {str(e)}",
            }],
        }
    if len(rows) <= 1:
        return {
            "success": False,
            "message": "employees.import.errors.emptyFile",
            "errors": [{
                "row": 0,
                "field": "file",
                "code": "employees.import.errors.emptyFile",
                "value": "",
                "message": "Tệp Excel trống hoặc không có dữ liệu ngoài dòng tiêu đề.",
            }],
        }

    # Tự động phát hiện có cột STT ở đầu hay không
    first_row = [str(c).strip().lower() if c is not None else "" for c in rows[0]]
    offset = 1 if (len(first_row) > 0 and ("stt" in first_row[0] or "số tt" in first_row[0] or "số thứ tự" in first_row[0])) else 0

    errors = []
    valid_records = []
    seen_emails_in_file = set()

    def add_error(row: int, field: str, code: str, value="", message=""):
        errors.append({
            "row": row,
            "field": field,
            "code": code,
            "value": "" if value is None else str(value),
            "message": message,
        })

    for idx, row in enumerate(rows[1:], start=2):
        if not any(row):
            continue  # Bỏ qua dòng trống hoàn toàn

        # Bỏ qua dòng hướng dẫn / gợi ý nếu ô bắt đầu bằng dấu ngoặc đơn '('
        first_cell = str(row[0]).strip() if len(row) > 0 and row[0] is not None else ""
        second_cell = str(row[1]).strip() if len(row) > 1 and row[1] is not None else ""
        if first_cell.startswith("(") or second_cell.startswith("("):
            continue

        def _get_val(col_idx):
            target = col_idx + offset
            if target < len(row) and row[target] is not None:
                return row[target]
            return None

        ho_ten = str(_get_val(0)).strip() if _get_val(0) is not None else ""
        raw_birthday = _get_val(1)
        raw_email = str(_get_val(2)).strip().lower() if _get_val(2) is not None else ""
        sdt = str(_get_val(3)).strip() if _get_val(3) is not None else ""
        don_vi_name = str(_get_val(4)).strip() if _get_val(4) is not None else ""
        chuc_vu_name = str(_get_val(5)).strip() if _get_val(5) is not None else ""
        chuc_danh = str(_get_val(6)).strip() if _get_val(6) is not None else ""
        raw_trang_thai = str(_get_val(7)).strip() if _get_val(7) is not None else "Đang làm việc"
        ghi_chu = str(_get_val(8)).strip() if _get_val(8) is not None else ""

        # 1. Validate Họ và tên
        if not ho_ten:
            add_error(idx, "ho_ten", "employees.validation.nameRequired", "", "Họ và tên không được để trống.")

        # 2. Validate Ngày sinh
        birthday = _parse_date(raw_birthday)
        if not birthday:
            add_error(
                idx,
                "ngay_sinh",
                "employees.import.errors.invalidBirthday",
                str(raw_birthday or ""),
                f"Ngày sinh '{raw_birthday}' không đúng định dạng (hỗ trợ YYYY-MM-DD hoặc DD/MM/YYYY).",
            )
        else:
            today = date.today()
            if birthday > today:
                add_error(
                    idx,
                    "ngay_sinh",
                    "employees.messages.birthdayInFuture",
                    str(raw_birthday or ""),
                    "Ngày sinh không thể ở trong tương lai.",
                )
            else:
                age = today.year - birthday.year - ((today.month, today.day) < (birthday.month, birthday.day))
                if age < 18 or age > 100:
                    add_error(
                        idx,
                        "ngay_sinh",
                        "employees.messages.birthdayOutOfRange",
                        str(raw_birthday or ""),
                        "Độ tuổi của cán bộ nhân viên phải từ 18 đến 100 tuổi.",
                    )

        # 3. Validate Email
        if not raw_email:
            add_error(idx, "email", "employees.validation.emailRequired", "", "Email không được để trống.")
        elif not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", raw_email):
            add_error(
                idx,
                "email",
                "employees.import.errors.invalidEmail",
                raw_email,
                f"Email '{raw_email}' không đúng định dạng.",
            )
        elif raw_email in seen_emails_in_file:
            add_error(
                idx,
                "email",
                "employees.import.errors.duplicateEmailInFile",
                raw_email,
                f"Email '{raw_email}' bị trùng lặp trong chính tệp Excel tải lên.",
            )
        elif get_user_model().objects.filter(email__iexact=raw_email).exists():
            add_error(
                idx,
                "email",
                "employees.messages.emailExists",
                raw_email,
                f"Email '{raw_email}' đã tồn tại trên hệ thống.",
            )
        else:
            seen_emails_in_file.add(raw_email)

        # 4. Validate Số điện thoại
        if sdt:
            sdt_clean = sdt.replace(" ", "").replace(".", "")
            if not re.match(r"^(0|\+84)[1-9][0-9]{7,9}$", sdt_clean):
                add_error(
                    idx,
                    "sdt",
                    "employees.validation.phoneInvalid",
                    sdt,
                    f"Số điện thoại '{sdt}' không hợp lệ theo chuẩn Việt Nam.",
                )
        else:
            sdt_clean = ""

        # 5. Validate Đơn vị / Phòng ban
        don_vi_instance = None
        if not don_vi_name:
            add_error(idx, "don_vi", "employees.import.errors.unitRequired", "", "Tên Đơn vị / Phòng ban không được để trống.")
        else:
            matching_units = DonVi.objects.filter(ten__iexact=don_vi_name)
            unit_count = matching_units.count()
            if unit_count == 0:
                add_error(
                    idx,
                    "don_vi",
                    "employees.messages.unitNotFound",
                    don_vi_name,
                    f"Không tìm thấy Đơn vị có tên '{don_vi_name}' trong hệ thống.",
                )
            elif unit_count > 1:
                add_error(
                    idx,
                    "don_vi",
                    "employees.messages.unitAmbiguous",
                    don_vi_name,
                    f"Tên Đơn vị '{don_vi_name}' trùng lặp giữa nhiều Khối/Khu vực. Vui lòng ghi rõ hoặc chọn đơn vị chính xác.",
                )
            else:
                don_vi_instance = matching_units.first()

        # 6. Validate Chức vụ
        chuc_vu_instance = None
        if not chuc_vu_name:
            add_error(idx, "chuc_vu", "employees.import.errors.positionRequired", "", "Tên Chức vụ không được để trống.")
        else:
            chuc_vu_instance = Position.objects.filter(name__iexact=chuc_vu_name).first()
            if not chuc_vu_instance:
                add_error(
                    idx,
                    "chuc_vu",
                    "employees.messages.positionNotFound",
                    chuc_vu_name,
                    f"Không tìm thấy Chức vụ có tên '{chuc_vu_name}' trong hệ thống.",
                )

        # 7. Validate Trạng thái
        trang_thai = Employee.Status.LAM_VIEC
        if "nghỉ" in raw_trang_thai.lower() or "nghi" in raw_trang_thai.lower():
            trang_thai = Employee.Status.NGHI_VIEC

        valid_records.append({
            "ho_ten": ho_ten,
            "ngay_sinh": birthday,
            "email": raw_email,
            "sdt": sdt_clean,
            "don_vi": don_vi_instance,
            "chuc_vu": chuc_vu_instance,
            "chuc_danh": chuc_danh,
            "trang_thai": trang_thai,
            "ghi_chu": ghi_chu,
        })

    if errors:
        return {
            "success": False,
            "errors": errors,
            "message": "employees.messages.importHasErrors",
        }

    # Nếu toàn bộ dữ liệu hợp lệ, tiến hành lưu nguyên tử (atomic) vào CSDL
    created_count = 0
    UserModel = get_user_model()
    with transaction.atomic():
        for item in valid_records:
            email = item["email"]
            local_part = email.split("@")[0]
            candidate = local_part
            idx = 1
            while UserModel.objects.filter(username__iexact=candidate).exists():
                candidate = f"{local_part}{idx}"
                idx += 1

            UserModel.objects.create_user(
                username=candidate,
                password=f"ITC@{secrets.token_hex(4)}",
                email=email,
                ho_ten=item["ho_ten"],
                ngay_sinh=item["ngay_sinh"],
                don_vi=item["don_vi"],
                chuc_vu=item["chuc_vu"],
                chuc_danh=item["chuc_danh"],
                sdt=item["sdt"],
                trang_thai=item["trang_thai"],
                is_active=(item["trang_thai"] != Employee.Status.NGHI_VIEC),
                ghi_chu=item["ghi_chu"],
            )
            created_count += 1

    return {
        "success": True,
        "message": "employees.messages.importSuccess",
        "created_count": created_count,
        "errors": [],
    }


def _write_cell(cell, value=None, font=None, fill=None, alignment=None, border=None):
    from openpyxl.cell.cell import MergedCell

    if not isinstance(cell, MergedCell) and value is not None:
        cell.value = value
        if isinstance(value, str):
            cell.data_type = "s"
    if font:
        cell.font = font
    if fill:
        cell.fill = fill
    if alignment:
        cell.alignment = alignment
    if border:
        cell.border = border


def export_cbnv_to_excel(queryset, user) -> BytesIO:
    """
    Xuất danh bạ Cán bộ Nhân viên theo phân cấp Khối -> Đơn vị -> Nhân sự (Issue #24).
    Tuân thủ quy chuẩn của thầy & phản hồi trưởng nhóm:
    - Khối sắp xếp theo thứ tự hiển thị 1 đến 16 (thu_tu_hien_thi).
    - Đơn vị sắp xếp theo STT ưu tiên (stt_uu_tien).
    - Nhân sự trong đơn vị sắp xếp theo thứ tự cấp bậc chức vụ (Position.display_order), sau đó theo họ tên.
    - STT đếm lại từ 1 ở mỗi đơn vị.
    - Nhân sự kiêm nhiệm (EmployeeAssignment) xuất hiện dưới từng đơn vị họ đảm nhiệm.
    - 6 cột: STT, Họ và tên, Chức vụ, Chức danh, Điện thoại, Email.
    - Lọc CBNV đang làm việc (trang_thai = 'LAM_VIEC', is_active = True).
    - CBNV Nội bộ (is_public = False) chỉ xuất hiện với người có quyền view_full_cbnv hoặc superuser.
    - Chống Formula Injection: ép kiểu chuỗi an toàn cell.data_type = 's'.
    """
    can_view_full = bool(
        user
        and (
            user.is_superuser
            or user.has_perm("authorization.view_full_cbnv")
            or user.has_perm("accounts.view_full_cbnv")
            or user.has_perm("view_full_cbnv")
        )
    )

    # Lọc chỉ CBNV đang làm việc
    active_employees = queryset.filter(
        trang_thai=Employee.Status.LAM_VIEC,
        is_active=True,
    )
    if not can_view_full:
        active_employees = active_employees.filter(is_public=True)

    active_employees = (
        active_employees.select_related("don_vi__khoi", "chuc_vu")
        .prefetch_related("assignments__don_vi__khoi", "assignments__chuc_vu")
        .all()
    )

    # Gom danh sách nhân sự theo don_vi_id
    unit_persons = {}
    active_emp_ids = set()

    for emp in active_employees:
        active_emp_ids.add(emp.id)
        if emp.don_vi_id:
            disp_order = emp.chuc_vu.display_order if emp.chuc_vu else 999999
            unit_persons.setdefault(emp.don_vi_id, []).append({
                "ho_ten": emp.ho_ten,
                "chuc_vu": emp.chuc_vu.name if emp.chuc_vu else "",
                "chuc_danh": emp.chuc_danh or "",
                "sdt": emp.sdt or "",
                "email": emp.email or "",
                "display_order": disp_order,
            })

    # Phân công kiêm nhiệm của các nhân sự đang làm việc
    if active_emp_ids:
        assignments = (
            EmployeeAssignment.objects.filter(employee_id__in=active_emp_ids)
            .select_related("employee", "don_vi__khoi", "chuc_vu")
            .all()
        )
        for assign in assignments:
            if assign.don_vi_id:
                disp_order = assign.chuc_vu.display_order if assign.chuc_vu else 999999
                unit_persons.setdefault(assign.don_vi_id, []).append({
                    "ho_ten": assign.employee.ho_ten,
                    "chuc_vu": assign.chuc_vu.name if assign.chuc_vu else "",
                    "chuc_danh": assign.chuc_danh or "",
                    "sdt": assign.employee.sdt or "",
                    "email": assign.employee.email or "",
                    "display_order": disp_order,
                })

    all_don_vi_ids = list(unit_persons.keys())
    don_vis = (
        DonVi.objects.filter(id__in=all_don_vi_ids)
        .select_related("khoi")
        .order_by("stt_uu_tien", "id")
    )

    khoi_units_map = {}
    don_vis_without_khoi = []
    khoi_map = {}

    for dv in don_vis:
        if dv.khoi:
            khoi_map[dv.khoi.id] = dv.khoi
            khoi_units_map.setdefault(dv.khoi.id, []).append(dv)
        else:
            don_vis_without_khoi.append(dv)

    sorted_khois = sorted(khoi_map.values(), key=lambda k: (k.thu_tu_hien_thi, k.id))

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Danh Ba CBNV"

    title_font = Font(name="Arial", size=13, bold=True, color="1E3A8A")
    sub_font_bold = Font(name="Arial", size=9, bold=True, color="1E293B")
    sub_font_italic = Font(name="Arial", size=9, italic=True, color="475569")
    header_font = Font(name="Arial", size=10, bold=True, color="000000")
    header_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")

    khoi_font = Font(name="Arial", size=11, bold=True, color="1E3A8A")
    khoi_fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")

    unit_font = Font(name="Arial", size=10, bold=True, color="000000")
    unit_fill = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")

    body_font = Font(name="Arial", size=10, color="000000")
    zebra_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    white_fill = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")

    align_center = Alignment(horizontal="center", vertical="center")
    align_left = Alignment(horizontal="left", vertical="center")
    thin_border = Border(
        left=Side(style="thin", color="CBD5E1"),
        right=Side(style="thin", color="CBD5E1"),
        top=Side(style="thin", color="CBD5E1"),
        bottom=Side(style="thin", color="CBD5E1"),
    )

    # 1. Header Banner
    ws.merge_cells("A1:F1")
    _write_cell(ws["A1"], "DANH BẠ ĐIỆN THOẠI TỔNG CÔNG TY CỔ PHẦN BẢO HIỂM BẢO LONG", font=title_font, alignment=align_center)
    ws.row_dimensions[1].height = 28

    ws.merge_cells("A2:F2")
    _write_cell(ws["A2"], "HỘI SỞ: 185 Điện Biên Phủ, Phường Đakao, Quận 1, Tp Hồ Chí Minh | ĐT: (84.8) 3823 9219 | Fax: (84.8) 3822 8967", font=sub_font_bold, alignment=align_center)
    ws.row_dimensions[2].height = 20

    ws.merge_cells("A3:F3")
    _write_cell(ws["A3"], "Website: http://baohiembaolong.vn | Email: info@baohiembaolong.vn | Hotline: (84.8) 3823 9219", font=sub_font_italic, alignment=align_center)
    ws.row_dimensions[3].height = 18

    ws.row_dimensions[4].height = 10

    # 2. Table Column Headers
    headers = ["STT", "Họ và tên", "Chức vụ", "Chức danh", "Điện thoại", "Email"]
    ws.row_dimensions[5].height = 26
    for col_idx, h in enumerate(headers, 1):
        cell = ws.cell(row=5, column=col_idx)
        _write_cell(cell, h, font=header_font, fill=header_fill, alignment=align_center, border=thin_border)

    current_row = 6

    def render_unit(dv):
        nonlocal current_row
        parts = [dv.ten.upper()]
        if dv.dia_chi:
            parts.append(f"ĐỊA CHỈ: {dv.dia_chi}")
        if dv.dien_thoai:
            parts.append(f"ĐT: {dv.dien_thoai}")
        if dv.email:
            parts.append(f"EMAIL: {dv.email}")
        unit_text = "   ".join(parts)

        ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=6)
        for c in range(1, 7):
            _write_cell(ws.cell(row=current_row, column=c), unit_text if c == 1 else None, font=unit_font, fill=unit_fill, alignment=align_left, border=thin_border)
        ws.row_dimensions[current_row].height = 22
        current_row += 1

        persons = unit_persons.get(dv.id, [])
        persons.sort(key=lambda p: (p["display_order"], p["ho_ten"]))

        for p_idx, person in enumerate(persons, 1):
            row_fill = zebra_fill if p_idx % 2 == 0 else white_fill
            row_vals = [
                p_idx,
                person["ho_ten"],
                person["chuc_vu"],
                person["chuc_danh"],
                person["sdt"],
                person["email"],
            ]
            ws.row_dimensions[current_row].height = 20
            for col_idx, val in enumerate(row_vals, 1):
                cell = ws.cell(row=current_row, column=col_idx)
                align = align_center if col_idx in (1, 5) else align_left
                _write_cell(cell, val, font=body_font, fill=row_fill, alignment=align, border=thin_border)
            current_row += 1

    for khoi in sorted_khois:
        units_in_khoi = khoi_units_map.get(khoi.id, [])
        if not units_in_khoi:
            continue
        ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=6)
        for c in range(1, 7):
            _write_cell(ws.cell(row=current_row, column=c), khoi.ten.upper() if c == 1 else None, font=khoi_font, fill=khoi_fill, alignment=align_left, border=thin_border)
        ws.row_dimensions[current_row].height = 24
        current_row += 1

        for dv in units_in_khoi:
            render_unit(dv)

    if don_vis_without_khoi:
        ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=6)
        for c in range(1, 7):
            _write_cell(ws.cell(row=current_row, column=c), "ĐƠN VỊ KHÁC" if c == 1 else None, font=khoi_font, fill=khoi_fill, alignment=align_left, border=thin_border)
        ws.row_dimensions[current_row].height = 24
        current_row += 1
        for dv in don_vis_without_khoi:
            render_unit(dv)

    col_min_widths = {1: 8, 2: 24, 3: 20, 4: 24, 5: 16, 6: 28}
    for col_idx, min_w in col_min_widths.items():
        col_letter = openpyxl.utils.get_column_letter(col_idx)
        max_len = min_w
        for r in range(5, current_row):
            if ws.row_dimensions[r].height == 20:
                c_val = str(ws.cell(row=r, column=col_idx).value or "")
                if len(c_val) > max_len:
                    max_len = len(c_val)
        ws.column_dimensions[col_letter].width = max(max_len + 3, min_w)

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer
