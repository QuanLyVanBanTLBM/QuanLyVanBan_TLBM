"""Align the migration-built permission default and labels with the release DDL."""

from django.db import migrations


LEGACY_EMPTY_DEFAULTS = {"''::character varying", "''::character varying(150)"}
PERMISSION_LABELS = (
    ("add_phonghop", "Thêm phòng họp", "Thêm phòng họp (danh mục)"),
    ("change_phonghop", "Sửa phòng họp", "Sửa phòng họp (danh mục)"),
    ("delete_phonghop", "Xóa phòng họp", "Xóa phòng họp (danh mục)"),
    ("import_chucvu", "Import file chức vụ", "Import chức vụ từ Excel"),
)


def align_permission_schema_and_labels(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        raise RuntimeError("authorization 0006 requires PostgreSQL.")

    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            "SELECT column_default FROM information_schema.columns "
            "WHERE table_schema = current_schema() AND table_name = 'auth_permission' "
            "AND column_name = 'module_ten'"
        )
        row = cursor.fetchone()
        if row is None:
            raise RuntimeError("auth_permission.module_ten is missing; migration made no changes.")

        default = row[0]
        if default is not None and default not in LEGACY_EMPTY_DEFAULTS:
            raise RuntimeError(
                "auth_permission.module_ten has an unexpected default; migration made no changes."
            )

        # Complete all preflight checks before changing either schema or labels.
        if default is not None:
            cursor.execute("ALTER TABLE auth_permission ALTER COLUMN module_ten DROP DEFAULT")

        for codename, old_name, canonical_name in PERMISSION_LABELS:
            cursor.execute(
                "UPDATE auth_permission SET name = %s WHERE codename = %s AND name = %s",
                [canonical_name, codename, old_name],
            )


class Migration(migrations.Migration):
    dependencies = [
        ("authorization", "0005_align_rbac_structure_with_ddl"),
    ]

    operations = [
        migrations.RunPython(align_permission_schema_and_labels, migrations.RunPython.noop),
    ]
