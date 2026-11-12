"""Thêm 2 nhóm chuẩn bổ sung TLBGD, KT và quyền của chúng (issue #228), khớp release_DDL.sql [NQBS]."""

from django.db import migrations

# Bản chép cố định của authorization.rbac_seed.SUPPLEMENTARY_* tại thời điểm tạo migration.
GROUPS = [("Trợ lý Ban Giám đốc", "TLBGD"), ("Kiểm toán", "KT")]
GROUP_PERMISSIONS = {
    "TLBGD": ["view_all_congviec", "view_read_log_vanbanden", "view_read_log_vanbandi", "send_trinhky"],
    "KT": ["view_signing_audit", "view_read_log_vanbanden", "view_read_log_vanbandi"],
}


def add_supplementary_groups(apps, schema_editor):
    """Idempotent: DB dựng từ DDL đã có sẵn nên chỉ bổ sung phần thiếu; tra nhóm theo mã, quyền theo codename."""
    with schema_editor.connection.cursor() as cursor:
        for code, codenames in GROUP_PERMISSIONS.items():
            cursor.execute(
                "SELECT count(*) FROM auth_permission WHERE codename = ANY(%s)", [codenames]
            )
            if cursor.fetchone()[0] != len(codenames):
                raise RuntimeError(f"Thiếu quyền của nhóm {code}; migration không thay đổi dữ liệu.")
        for name, code in GROUPS:
            # Như release_DDL.sql (ON CONFLICT (name) DO UPDATE): nhóm tự tạo trùng tên chưa có mã thì nhận mã chuẩn.
            cursor.execute(
                "UPDATE auth_group SET ma_nhom_quyen = %s WHERE name = %s AND ma_nhom_quyen IS NULL "
                "AND NOT EXISTS (SELECT 1 FROM auth_group WHERE ma_nhom_quyen = %s)",
                [code, name, code],
            )
            cursor.execute(
                "INSERT INTO auth_group (name, ma_nhom_quyen) "
                "SELECT %s, %s WHERE NOT EXISTS (SELECT 1 FROM auth_group WHERE ma_nhom_quyen = %s)",
                [name, code, code],
            )
            cursor.execute(
                "INSERT INTO auth_group_permissions (group_id, permission_id) "
                "SELECT g.id, p.id FROM auth_group g, auth_permission p "
                "WHERE g.ma_nhom_quyen = %s AND p.codename = ANY(%s) "
                "ON CONFLICT (group_id, permission_id) DO NOTHING",
                [code, GROUP_PERMISSIONS[code]],
            )


class Migration(migrations.Migration):
    dependencies = [
        ("authorization", "0007_grant_cv_send_trinhky"),
    ]

    operations = [
        migrations.RunPython(add_supplementary_groups, migrations.RunPython.noop),
    ]
