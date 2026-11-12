"""Dữ liệu nền Chức vụ và tài khoản hệ thống `admin` (mật khẩu unusable theo Django).

Chép nguyên văn từ docs/common/database/release_DDL.sql (mục seed dữ liệu nền) để DB dựng bằng migration có cùng
dữ liệu với DB nạp DDL. Câu lệnh idempotent: chỉ chèn khi chưa có dòng tương ứng, không ghi đè dữ liệu sẵn có.
Reverse không xóa dữ liệu vì các dòng này có thể đã được tham chiếu hoặc chỉnh sửa.
"""
from django.db import migrations

SEED_SQL = r"""
-- 3) Seed Chức vụ và Tài khoản quản trị hệ thống mẫu (Idempotent, không hard-code ID)
INSERT INTO
    accounts_position (
        display_order,
        name,
        is_public
    )
SELECT 1, 'Quản trị viên', TRUE
WHERE
    NOT EXISTS (
        SELECT 1
        FROM accounts_position
        WHERE
            name = 'Quản trị viên'
    );

-- Đảm bảo có tài khoản quản trị hệ thống mẫu làm nguoi_lap_id nếu chưa có (truy vấn động ID)
INSERT INTO
    accounts_employee (
        username,
        email,
        password,
        ho_ten,
        ngay_sinh,
        chuc_vu_id,
        don_vi_id,
        is_staff,
        is_superuser,
        is_active
    )
SELECT 'admin', 'admin@baolong.vn', '!system_seed_placeholder', 'Quản trị hệ thống', '1990-01-01', (
        SELECT id
        FROM accounts_position
        WHERE
            name = 'Quản trị viên'
        LIMIT 1
    ), COALESCE(
        (
            SELECT id
            FROM organizations_donvi
            WHERE
                ten = 'Ban công nghệ thông tin'
            LIMIT 1
        ), (
            SELECT id
            FROM organizations_donvi
            ORDER BY id
            LIMIT 1
        )
    ), TRUE, TRUE, TRUE
WHERE
    NOT EXISTS (
        SELECT 1
        FROM accounts_employee
        WHERE
            username = 'admin'
    ) ON CONFLICT (username) DO NOTHING;
"""


def seed(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(SEED_SQL)


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0005_align_release_ddl'),
        ('organizations', '0005_reference_data_ddl'),
    ]

    operations = [
        migrations.RunPython(seed, migrations.RunPython.noop),
    ]
