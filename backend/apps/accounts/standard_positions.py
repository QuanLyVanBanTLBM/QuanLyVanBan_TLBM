"""
Danh mục chức vụ chuẩn (STT = thứ tự ưu tiên, 1 là cao nhất).

Một nguồn cho seed_db; phần seed chức vụ của release_DDL.sql và migration 0009_standard_positions
chép lại cùng danh sách, cùng thứ tự (test_standard_positions kiểm ba nơi trùng nhau).

- 22 chức vụ do giảng viên cung cấp (bảng tính đặc tả "ITC - Django - QLVB&TL", tab Chức vụ).
- Giữ 3 chức vụ cũ đang được dữ liệu và tài khoản mẫu của các phân hệ khác dùng, chèn theo cấp bậc:
  "Quản trị viên" (chức vụ của tài khoản quản trị hệ thống, STT 1 như release_DDL.sql),
  "Lãnh đạo cơ quan" (ngay sau Tổng Giám đốc), "Văn thư" (ngay sau Chuyên viên; danh bạ thật xếp
  văn thư cùng cấp chuyên viên).
"""

TEACHER_POSITIONS = [
    "Chủ tịch HĐQT",
    "Phó Chủ tịch HĐQT",
    "Thành viên HĐQT",
    "Tổng Giám đốc",
    "Phó Tổng Giám đốc điều hành",
    "Phó Tổng Giám đốc kinh doanh",
    "Giám đốc Khối",
    "Phó Giám đốc Khối",
    "Giám đốc Vùng",
    "Trợ lý TGĐ",
    "Giám đốc",
    "Phó Giám đốc",
    "Giám đốc Ban",
    "Phụ trách Ban",
    "Trưởng Ban",
    "Phó Ban",
    "Trưởng Bộ phận",
    "Trưởng nhóm",
    "Trưởng phòng",
    "Phó phòng",
    "Chuyên viên",
    "Kiểm toán viên",
    "Nhân viên",
    "Thành viên",
]

ADMIN_POSITION = "Quản trị viên"
AGENCY_LEADER_POSITION = "Lãnh đạo cơ quan"
CLERK_POSITION = "Văn thư"

# (STT, tên) theo thứ tự hiển thị.
STANDARD_POSITIONS = list(
    enumerate(
        [
            ADMIN_POSITION,
            *TEACHER_POSITIONS[:4],  # Chủ tịch HĐQT ... Tổng Giám đốc
            AGENCY_LEADER_POSITION,
            *TEACHER_POSITIONS[4:21],  # Phó Tổng Giám đốc điều hành ... Chuyên viên
            CLERK_POSITION,
            *TEACHER_POSITIONS[21:],  # Kiểm toán viên, Nhân viên, Thành viên
        ],
        start=1,
    )
)
