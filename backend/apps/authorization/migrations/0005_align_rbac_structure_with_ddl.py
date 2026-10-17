from django.db import migrations

# Đưa cấu trúc bảng phân quyền do Django migration tạo ra về đúng release_DDL.sql (mục 14, 15).
# DB dựng từ DDL đã khớp nên mọi bước dưới đây tự bỏ qua (idempotent); chỉ DB do Django tạo (dev, CI, test) bị đổi.
# Chỉ chạy trên PostgreSQL: SQLite (job backend của CI) không có khái niệm BIGINT/constraint tương ứng.

# Cột khóa mà Django tạo INTEGER (auth.Group/Permission dùng AutoField) còn DDL khai BIGINT.
BIGINT_COLUMNS = [
    ("auth_group", "id"),
    ("auth_permission", "id"),
    ("auth_permission", "content_type_id"),
    ("auth_group_permissions", "group_id"),
    ("auth_group_permissions", "permission_id"),
    ("accounts_employee_groups", "group_id"),
    ("accounts_employee_user_permissions", "permission_id"),
]

# DDL khai ON DELETE CASCADE ở mức DB; Django chỉ tạo FK không có ON DELETE (xóa dây chuyền ở tầng ứng dụng).
CASCADE_FOREIGN_KEYS = [
    ("auth_group_permissions", "group_id", "auth_group"),
    ("auth_group_permissions", "permission_id", "auth_permission"),
    ("accounts_employee_groups", "employee_id", "accounts_employee"),
    ("accounts_employee_groups", "group_id", "auth_group"),
    ("accounts_employee_user_permissions", "employee_id", "accounts_employee"),
    ("accounts_employee_user_permissions", "permission_id", "auth_permission"),
]

# Tên quyền theo DDL (release_DDL.sql, phần seed auth_permission); seed cũ của Django đặt tên khác.
DDL_PERMISSION_NAMES = {
    "import_chucvu": "Import chức vụ từ Excel",
    "add_phonghop": "Thêm phòng họp (danh mục)",
    "change_phonghop": "Sửa phòng họp (danh mục)",
    "delete_phonghop": "Xóa phòng họp (danh mục)",
}


def _constraints(cursor, table, kind):
    """Trả về [(tên, [cột...], định nghĩa)] của các constraint loại kind ('u' hoặc 'f') trên bảng."""
    cursor.execute(
        "SELECT c.conname, "
        "(SELECT array_agg(a.attname::text ORDER BY a.attname) FROM pg_attribute a "
        " WHERE a.attrelid = c.conrelid AND a.attnum = ANY (c.conkey)), "
        "pg_get_constraintdef(c.oid) "
        "FROM pg_constraint c WHERE c.conrelid = %s::regclass AND c.contype = %s",
        [table, kind],
    )
    return cursor.fetchall()


def _column_info(cursor, table, column):
    cursor.execute(
        "SELECT data_type, column_default FROM information_schema.columns "
        "WHERE table_schema = current_schema() AND table_name = %s AND column_name = %s",
        [table, column],
    )
    return cursor.fetchone()


def _use_unique_constraint(cursor, table, column, constraint_name, index_name):
    """DDL khai UNIQUE là constraint; Django/0001 chỉ tạo UNIQUE INDEX rời. Chuyển index sẵn có thành constraint."""
    if any(columns == [column] for _, columns, _ in _constraints(cursor, table, "u")):
        return
    cursor.execute("SELECT 1 FROM pg_indexes WHERE schemaname = current_schema() AND indexname = %s", [index_name])
    if cursor.fetchone():
        cursor.execute(f'ALTER TABLE {table} ADD CONSTRAINT {constraint_name} UNIQUE USING INDEX {index_name}')
    else:
        cursor.execute(f"ALTER TABLE {table} ADD CONSTRAINT {constraint_name} UNIQUE ({column})")


def align_structure(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return

    with schema_editor.connection.cursor() as cursor:
        # 1. Quyền không phụ thuộc django_content_type (DDL không có FK này và không có unique (content_type_id, codename)).
        for name, columns, definition in _constraints(cursor, "auth_permission", "f"):
            if columns == ["content_type_id"]:
                cursor.execute(f'ALTER TABLE auth_permission DROP CONSTRAINT "{name}"')
        for name, columns, definition in _constraints(cursor, "auth_permission", "u"):
            if columns == ["codename", "content_type_id"]:
                cursor.execute(f'ALTER TABLE auth_permission DROP CONSTRAINT "{name}"')

        # 2. Kiểu khóa BIGINT như DDL.
        for table, column in BIGINT_COLUMNS:
            info = _column_info(cursor, table, column)
            if info and info[0] == "integer":
                cursor.execute(f'ALTER TABLE {table} ALTER COLUMN "{column}" TYPE bigint')

        # 3. UNIQUE là constraint (codename, ma_nhom_quyen).
        # Cố ý KHÔNG bỏ DEFAULT '' của auth_permission.module_ten dù DDL không có: test của Nhóm 5
        # (signing/tests/helpers.py cap_quyen) tạo Permission qua ORM không có cột này, cần DEFAULT mới chèn được.
        _use_unique_constraint(cursor, "auth_permission", "codename", "auth_permission_codename_key", "uq_auth_permission_codename")
        _use_unique_constraint(cursor, "auth_group", "ma_nhom_quyen", "auth_group_ma_nhom_quyen_key", "uq_auth_group_ma_nhom_quyen")

        # 4. FK của bảng nối có ON DELETE CASCADE ở mức DB.
        for table, column, referenced in CASCADE_FOREIGN_KEYS:
            for name, columns, definition in _constraints(cursor, table, "f"):
                if columns == [column] and "ON DELETE CASCADE" not in definition:
                    cursor.execute(f'ALTER TABLE {table} DROP CONSTRAINT "{name}"')
                    cursor.execute(
                        f'ALTER TABLE {table} ADD CONSTRAINT "{name}" FOREIGN KEY ({column}) '
                        f"REFERENCES {referenced} (id) ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED"
                    )


def align_permission_names(apps, schema_editor):
    """Đổi tên hiển thị 4 quyền cho khớp DDL (mọi loại DB; so theo codename nên chạy lại không đổi gì)."""
    with schema_editor.connection.cursor() as cursor:
        for codename, name in DDL_PERMISSION_NAMES.items():
            cursor.execute(
                "UPDATE auth_permission SET name = %s WHERE codename = %s AND name <> %s",
                [name, codename, name],
            )


class Migration(migrations.Migration):

    dependencies = [
        ("authorization", "0004_grant_tp_manage_signing_process"),
        ("accounts", "0005_align_release_ddl"),
    ]

    operations = [
        migrations.RunPython(align_structure, migrations.RunPython.noop),
        migrations.RunPython(align_permission_names, migrations.RunPython.noop),
    ]
