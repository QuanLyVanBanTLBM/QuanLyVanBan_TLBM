"""Dữ liệu nền "Hồ sơ chung" (bản ghi hệ thống của records_hoso).

Chép nguyên văn từ docs/common/database/release_DDL.sql. Người lập lấy từ tài khoản hệ thống `admin` do migration
accounts 0006 tạo; migration không tạo tài khoản và bỏ qua khi chưa có tài khoản này. Câu lệnh idempotent: không chèn khi đã có Hồ sơ hệ thống hoặc
hồ sơ `HSC`. Reverse không xóa dữ liệu vì trigger bảo vệ bản ghi hệ thống và dòng này có thể đã được tham chiếu.
"""
from django.db import migrations

SEED_SQL = r"""
-- Chèn hoặc cập nhật Hồ sơ chung an toàn, idempotent (không cố định stt_uu_tien = 1 nếu đã bị chiếm)
UPDATE records_hoso
SET
    is_he_thong = TRUE
WHERE
    so_ky_hieu = 'HSC'
    AND is_he_thong = FALSE
    AND NOT EXISTS (
        SELECT 1
        FROM records_hoso
        WHERE
            is_he_thong = TRUE
    );

INSERT INTO
    records_hoso (
        stt_uu_tien,
        so_ky_hieu,
        ten_ho_so,
        nguoi_lap_id,
        is_he_thong,
        ghi_chu
    )
SELECT
    CASE
        WHEN NOT EXISTS (
            SELECT 1
            FROM records_hoso
            WHERE
                stt_uu_tien = 1
        ) THEN 1
        ELSE (
            SELECT COALESCE(MAX(stt_uu_tien), 0) + 1
            FROM records_hoso
        )
    END,
    'HSC',
    'Hồ sơ chung',
    (
        SELECT id
        FROM accounts_employee
        WHERE
            username = 'admin'
        LIMIT 1
    ),
    TRUE,
    'Hồ sơ chung mặc định của hệ thống - không được xóa'
WHERE
    NOT EXISTS (
        SELECT 1
        FROM records_hoso
        WHERE
            is_he_thong = TRUE
            OR so_ky_hieu = 'HSC'
    ) ON CONFLICT (so_ky_hieu) DO
UPDATE
SET
    is_he_thong = TRUE;
"""


def seed(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM accounts_employee WHERE username = 'admin'")
        if cursor.fetchone() is None:
            return
    schema_editor.execute(SEED_SQL)


class Migration(migrations.Migration):
    dependencies = [
        ("records", "0002_hoso_guards"),
        ("accounts", "0006_reference_data_ddl"),
    ]

    operations = [
        migrations.RunPython(seed, migrations.RunPython.noop),
    ]
