"""Tắt xác thực 2FA cho tài khoản admin hệ thống để khôi phục quyền truy cập trên staging."""

from django.db import migrations


def disable_admin_2fa(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    with schema_editor.connection.cursor() as cursor:
        cols = {
            col.name
            for col in schema_editor.connection.introspection.get_table_description(
                cursor, "accounts_employee"
            )
        }
    if "is_2fa_enabled" in cols:
        schema_editor.execute(
            "UPDATE accounts_employee "
            "SET is_2fa_enabled = FALSE, "
            "    totp_secret = NULL, "
            "    twofa_backup_codes = '[]'::jsonb, "
            "    totp_last_used_step = NULL, "
            "    twofa_failed_attempts = 0, "
            "    twofa_locked_until = NULL "
            "WHERE username = %s",
            ["admin"],
        )


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0016_employee_twofa_totp"),
    ]

    operations = [
        migrations.RunPython(disable_admin_2fa, migrations.RunPython.noop),
    ]
