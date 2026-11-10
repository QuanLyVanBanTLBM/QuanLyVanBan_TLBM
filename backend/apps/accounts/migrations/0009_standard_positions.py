"""Danh mục chức vụ chuẩn (25 chức vụ) cho DB đã có dữ liệu.

- Chức vụ trong danh mục (so tên không phân biệt hoa thường, bỏ khoảng trắng đầu cuối) nhận đúng STT;
  chức vụ còn thiếu được thêm. Không xóa chức vụ nào, không đổi chức vụ của CBNV.
- Chức vụ do người dùng tự thêm (ngoài danh mục) giữ thứ tự cũ, xếp sau STT 25.
- DB dựng bằng migration có cùng 25 chức vụ với seed `accounts_position` của release_DDL.sql
  (0006_reference_data_ddl đã nạp "Quản trị viên"; migration này thêm 24 chức vụ còn lại).
- Chạy lại nhiều lần cho cùng kết quả.
"""
from django.db import migrations

# Bản chép cố định của accounts.standard_positions.STANDARD_POSITIONS tại thời điểm tạo migration
# (migration không đọc code có thể đổi về sau; test kiểm hai danh sách trùng nhau).
STANDARD_POSITIONS = [
    (1, "Quản trị viên"),
    (2, "Chủ tịch HĐQT"),
    (3, "Phó Chủ tịch HĐQT"),
    (4, "Thành viên HĐQT"),
    (5, "Tổng Giám đốc"),
    (6, "Lãnh đạo cơ quan"),
    (7, "Phó Tổng Giám đốc điều hành"),
    (8, "Phó Tổng Giám đốc kinh doanh"),
    (9, "Giám đốc Khối"),
    (10, "Phó Giám đốc Khối"),
    (11, "Giám đốc Vùng"),
    (12, "Trợ lý TGĐ"),
    (13, "Giám đốc"),
    (14, "Phó Giám đốc"),
    (15, "Trưởng Ban"),
    (16, "Phó Ban"),
    (17, "Trưởng Bộ phận"),
    (18, "Trưởng nhóm"),
    (19, "Trưởng phòng"),
    (20, "Phó phòng"),
    (21, "Chuyên viên"),
    (22, "Văn thư"),
    (23, "Kiểm toán viên"),
    (24, "Nhân viên"),
    (25, "Thành viên"),
]


def apply_standard_positions(apps, schema_editor):
    Position = apps.get_model("accounts", "Position")
    positions = Position.objects.using(schema_editor.connection.alias)
    existing = list(positions.order_by("display_order", "id"))

    by_name = {}
    for position in existing:
        by_name.setdefault(position.name.strip().casefold(), position)

    # display_order là UNIQUE: dời STT hiện có sang số âm (theo id) trước khi đánh lại.
    for position in existing:
        positions.filter(pk=position.pk).update(display_order=-position.pk)

    standard_ids = set()
    for order, name in STANDARD_POSITIONS:
        position = by_name.get(name.casefold())
        if position is None:
            position = positions.create(display_order=order, name=name, is_public=True, note=None)
        else:
            positions.filter(pk=position.pk).update(display_order=order, name=name)
        standard_ids.add(position.pk)

    next_order = len(STANDARD_POSITIONS) + 1
    for position in existing:
        if position.pk not in standard_ids:
            positions.filter(pk=position.pk).update(display_order=next_order)
            next_order += 1


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0008_install_employee_updated_at_trigger"),
    ]

    operations = [
        migrations.RunPython(apply_standard_positions, migrations.RunPython.noop),
    ]
