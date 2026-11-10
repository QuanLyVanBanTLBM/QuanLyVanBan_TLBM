"""Chuyển placeholder cũ của tài khoản hệ thống sang định dạng unusable của Django."""

from django.db import migrations


UNUSABLE_PASSWORD = "!system_seed_placeholder"
LEGACY_PLACEHOLDER = "pbkdf2_sha256$system_seed_placeholder"


def normalize_system_seed_password(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(
        "UPDATE accounts_employee SET password = %s "
        "WHERE username = %s AND password = %s",
        [UNUSABLE_PASSWORD, "admin", LEGACY_PLACEHOLDER],
    )


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0006_reference_data_ddl"),
    ]

    operations = [
        migrations.RunPython(normalize_system_seed_password, migrations.RunPython.noop),
    ]
