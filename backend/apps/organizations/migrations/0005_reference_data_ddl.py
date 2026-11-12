"""Dữ liệu nền Khối/Khu vực và Đơn vị (cơ cấu tổ chức).

Chép nguyên văn từ docs/common/database/release_DDL.sql (mục seed dữ liệu nền) để DB dựng bằng migration có cùng
dữ liệu với DB nạp DDL. Câu lệnh idempotent: chỉ chèn khi chưa có dòng tương ứng, không ghi đè dữ liệu sẵn có.
Reverse không xóa dữ liệu vì các dòng này có thể đã được tham chiếu hoặc chỉnh sửa.
"""
from django.db import migrations

SEED_SQL = r"""
-- 1) Chèn các Khối/Khu vực (Cấp 1) — không trùng lặp (Idempotent)
-- thu_tu_hien_thi = vị trí của khối trong danh sách liệt kê (WITH ORDINALITY), không phụ thuộc collation.
INSERT INTO
    organizations_khoi (ten, thu_tu_hien_thi)
SELECT t.khoi, t.vi_tri::INTEGER
FROM unnest(
    ARRAY[
        'HỘI ĐỒNG QUẢN TRỊ',
        'VĂN PHÒNG HỘI ĐỒNG QUẢN TRỊ',
        'BAN TỔNG GIÁM ĐỐC',
        'VĂN PHÒNG BAN ĐIỀU HÀNH TẠI TP.HCM & HÀ NỘI',
        'KHỐI KINH DOANH',
        'KHỐI NGHIỆP VỤ',
        'KHỐI HỖ TRỢ',
        'KHỐI QUẢN LÝ RỦI RO',
        'KHỐI TÀI CHÍNH',
        'KHỐI KẾ TOÁN',
        'VĂN PHÒNG 2',
        'KHU VỰC THÀNH PHỐ HỒ CHÍ MINH',
        'KHU VỰC MIỀN BẮC',
        'KHU VỰC MIỀN TRUNG TÂY NGUYÊN',
        'KHU VỰC ĐÔNG NAM BỘ',
        'GIÁM ĐỊNH VÙNG'
    ]
) WITH ORDINALITY AS t (khoi, vi_tri)
WHERE
    NOT EXISTS (
        SELECT 1
        FROM organizations_khoi
    )
ORDER BY t.vi_tri;

-- 2) Chèn Đơn vị/phòng ban (Cấp 2), gán khoi_id theo tên Khối tương ứng
INSERT INTO
    organizations_donvi (khoi_id, ten, stt_uu_tien)
-- stt_uu_tien = vị trí của đơn vị trong danh sách liệt kê (cột vi_tri), không phụ thuộc collation.
SELECT k.id, x.don_vi, x.vi_tri
FROM (
        VALUES (
                'HỘI ĐỒNG QUẢN TRỊ', 'Hội đồng quản trị', 1), (
                'HỘI ĐỒNG QUẢN TRỊ', 'Ban kiểm toán nội bộ', 2), (
                'VĂN PHÒNG HỘI ĐỒNG QUẢN TRỊ', 'Văn phòng hội đồng quản trị', 3), (
                'BAN TỔNG GIÁM ĐỐC', 'Ban tổng giám đốc', 4), (
                'BAN TỔNG GIÁM ĐỐC', 'Giám đốc vùng', 5), (
                'VĂN PHÒNG BAN ĐIỀU HÀNH TẠI TP.HCM & HÀ NỘI', 'Văn phòng ban điều hành', 6), (
                'KHỐI KINH DOANH', 'Ban khách hàng doanh nghiệp', 7), (
                'KHỐI KINH DOANH', 'Ban khách hàng qua môi giới', 8), (
                'KHỐI KINH DOANH', 'Ban Bancassurance', 9), (
                'KHỐI KINH DOANH', 'Ban khách hàng cá nhân', 10), (
                'KHỐI KINH DOANH', 'Ban chăm sóc khách hàng ĐT', 11), (
                'KHỐI KINH DOANH', 'Ban dự án phát triển sản phẩm liên kết với các công ty dịch vụ viễn thông', 12), (
                'KHỐI KINH DOANH', 'Ban dự án lớn', 13), (
                'KHỐI KINH DOANH', 'Ban dự án khách hàng qua đại lý', 14), (
                'KHỐI NGHIỆP VỤ', 'Ban bảo hiểm con người', 15), (
                'KHỐI NGHIỆP VỤ', 'Ban bảo hiểm tài sản kỹ thuật', 16), (
                'KHỐI NGHIỆP VỤ', 'Ban tái bảo hiểm', 17), (
                'KHỐI NGHIỆP VỤ', 'Ban bảo hiểm xe cơ giới', 18), (
                'KHỐI NGHIỆP VỤ', 'Ban bảo hiểm hàng hải, hàng không, dầu khí, năng lượng', 19), (
                'KHỐI HỖ TRỢ', 'Lãnh đạo khối', 20), (
                'KHỐI HỖ TRỢ', 'Ban hành chính quản trị', 21), ('KHỐI HỖ TRỢ', 'Ban nhân sự', 22), ('KHỐI HỖ TRỢ', 'Ban pháp chế', 23), (
                'KHỐI HỖ TRỢ', 'Ban công nghệ thông tin', 24), (
                'KHỐI HỖ TRỢ', 'Ban truyền thông và marketing', 25), (
                'KHỐI QUẢN LÝ RỦI RO', 'Ban quản lý rủi ro và tuân thủ', 26), (
                'KHỐI TÀI CHÍNH', 'Ban đầu tư', 27), (
                'KHỐI TÀI CHÍNH', 'Ban tài chính kế hoạch', 28), (
                'KHỐI TÀI CHÍNH', 'Ban dự án MIS', 29), (
                'KHỐI KẾ TOÁN', 'Lãnh đạo khối', 30), ('KHỐI KẾ TOÁN', 'Ban kế toán', 31), ('VĂN PHÒNG 2', 'Văn phòng 2', 32), (
                'KHU VỰC THÀNH PHỐ HỒ CHÍ MINH', 'Sở giao dịch Bảo Long', 33), (
                'KHU VỰC THÀNH PHỐ HỒ CHÍ MINH', 'Bảo Long TP.HCM', 34), (
                'KHU VỰC THÀNH PHỐ HỒ CHÍ MINH', 'Bảo Long Sài Gòn', 35), (
                'KHU VỰC THÀNH PHỐ HỒ CHÍ MINH', 'Bảo Long Gia Định', 36), (
                'KHU VỰC THÀNH PHỐ HỒ CHÍ MINH', 'Bảo Long Bến Thành', 37), (
                'KHU VỰC THÀNH PHỐ HỒ CHÍ MINH', 'Bảo Long Nam Sài Gòn', 38), (
                'KHU VỰC THÀNH PHỐ HỒ CHÍ MINH', 'Bảo Long Tân Sơn Nhất', 39), (
                'KHU VỰC THÀNH PHỐ HỒ CHÍ MINH', 'Bảo Long Đông Sài Gòn', 40), (
                'KHU VỰC THÀNH PHỐ HỒ CHÍ MINH', 'Bảo Long Đông Phương', 41), (
                'KHU VỰC THÀNH PHỐ HỒ CHÍ MINH', 'Trung tâm kinh doanh Thủ Thiêm', 42), (
                'KHU VỰC MIỀN BẮC', 'Bảo Long Hà Nội', 43), (
                'KHU VỰC MIỀN BẮC', 'Bảo Long Thủ Đô', 44), (
                'KHU VỰC MIỀN BẮC', 'Bảo Long Thăng Long', 45), (
                'KHU VỰC MIỀN BẮC', 'Bảo Long Thái Nguyên', 46), (
                'KHU VỰC MIỀN BẮC', 'Bảo Long Quảng Ninh', 47), (
                'KHU VỰC MIỀN BẮC', 'Bảo Long Hải Phòng', 48), (
                'KHU VỰC MIỀN BẮC', 'Bảo Long Phú Thọ', 49), (
                'KHU VỰC MIỀN BẮC', 'Bảo Long Bắc Ninh', 50), (
                'KHU VỰC MIỀN BẮC', 'Bảo Long Hải Dương', 51), (
                'KHU VỰC MIỀN BẮC', 'Bảo Long Nam Định', 52), (
                'KHU VỰC MIỀN BẮC', 'Bảo Long Vĩnh Phúc', 53), (
                'KHU VỰC MIỀN BẮC', 'Bảo Long Đông Hải', 54), (
                'KHU VỰC MIỀN BẮC', 'Sở giao dịch miền Bắc', 55), (
                'KHU VỰC MIỀN BẮC', 'Bảo Long Ninh Bình', 56), (
                'KHU VỰC MIỀN BẮC', 'Bảo Long Thái Bình', 57), (
                'KHU VỰC MIỀN BẮC', 'Bảo Long Đông Đô', 58), (
                'KHU VỰC MIỀN BẮC', 'Bảo Long Thanh Hóa', 59), (
                'KHU VỰC MIỀN TRUNG TÂY NGUYÊN', 'Bảo Long KV Tây Nguyên (Daklak)', 60), (
                'KHU VỰC MIỀN TRUNG TÂY NGUYÊN', 'Bảo Long Phú Yên', 61), (
                'KHU VỰC MIỀN TRUNG TÂY NGUYÊN', 'Bảo Long Đà Nẵng', 62), (
                'KHU VỰC MIỀN TRUNG TÂY NGUYÊN', 'Bảo Long Trung Bộ (Huế)', 63), (
                'KHU VỰC MIỀN TRUNG TÂY NGUYÊN', 'Bảo Long Bắc Trung Bộ (Nghệ An)', 64), (
                'KHU VỰC MIỀN TRUNG TÂY NGUYÊN', 'Bảo Long Khánh Hòa', 65), (
                'KHU VỰC MIỀN TRUNG TÂY NGUYÊN', 'Bảo Long Bình Định', 66), (
                'KHU VỰC MIỀN TRUNG TÂY NGUYÊN', 'Bảo Long Bình Thuận', 67), (
                'KHU VỰC MIỀN TRUNG TÂY NGUYÊN', 'Bảo Long Quảng Ngãi', 68), (
                'KHU VỰC MIỀN TRUNG TÂY NGUYÊN', 'Bảo Long Gia Lai', 69), (
                'KHU VỰC MIỀN TRUNG TÂY NGUYÊN', 'Bảo Long Lâm Đồng', 70), (
                'KHU VỰC MIỀN TRUNG TÂY NGUYÊN', 'Bảo Long Quảng Bình', 71), (
                'KHU VỰC MIỀN TRUNG TÂY NGUYÊN', 'Trung tâm kinh doanh Sông Hàn', 72), (
                'KHU VỰC ĐÔNG NAM BỘ', 'Bảo Long Bình Dương', 73), (
                'KHU VỰC ĐÔNG NAM BỘ', 'Bảo Long Vũng Tàu', 74), (
                'KHU VỰC ĐÔNG NAM BỘ', 'Bảo Long Đồng Nai', 75), (
                'KHU VỰC ĐÔNG NAM BỘ', 'Bảo Long Tây Ninh', 76), (
                'KHU VỰC ĐÔNG NAM BỘ', 'Bảo Long Long An', 77), (
                'KHU VỰC ĐÔNG NAM BỘ', 'Bảo Long Cần Thơ', 78), (
                'KHU VỰC ĐÔNG NAM BỘ', 'Bảo Long Cà Mau', 79), (
                'KHU VỰC ĐÔNG NAM BỘ', 'Bảo Long Kiên Giang', 80), (
                'KHU VỰC ĐÔNG NAM BỘ', 'Bảo Long Đồng Tháp', 81), (
                'GIÁM ĐỊNH VÙNG', 'Giám định vùng', 82)
    ) AS x (khoi, don_vi, vi_tri)
    JOIN organizations_khoi k ON k.ten = x.khoi
WHERE
    NOT EXISTS (
        SELECT 1
        FROM organizations_donvi
    )
ORDER BY x.vi_tri;
"""


def seed(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(SEED_SQL)


class Migration(migrations.Migration):
    dependencies = [
        ('organizations', '0004_align_release_ddl'),
    ]

    operations = [
        migrations.RunPython(seed, migrations.RunPython.noop),
    ]
