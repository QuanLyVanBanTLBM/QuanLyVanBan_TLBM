"""Bổ sung Giám đốc Ban và Phụ trách Ban vào danh mục chức vụ chuẩn."""
from django.db import migrations


# Bản chép cố định của danh mục chuẩn sau khi thêm hai chức vụ quản lý ban.
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
    (15, "Giám đốc Ban"),
    (16, "Phụ trách Ban"),
    (17, "Trưởng Ban"),
    (18, "Phó Ban"),
    (19, "Trưởng Bộ phận"),
    (20, "Trưởng nhóm"),
    (21, "Trưởng phòng"),
    (22, "Phó phòng"),
    (23, "Chuyên viên"),
    (24, "Văn thư"),
    (25, "Kiểm toán viên"),
    (26, "Nhân viên"),
    (27, "Thành viên"),
]


def update_standard_positions(apps, schema_editor):
    Position = apps.get_model("accounts", "Position")
    positions = Position.objects.using(schema_editor.connection.alias)
    existing = list(positions.order_by("display_order", "id"))

    by_name = {}
    for position in existing:
        by_name.setdefault(position.name.strip().casefold(), position)

    # display_order là UNIQUE; dùng STT âm tạm thời để tránh va chạm khi dịch thứ tự.
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
        ("accounts", "0014_employee_sdt_10_chu_so"),
    ]

    operations = [
        migrations.RunPython(update_standard_positions, migrations.RunPython.noop),
    ]
