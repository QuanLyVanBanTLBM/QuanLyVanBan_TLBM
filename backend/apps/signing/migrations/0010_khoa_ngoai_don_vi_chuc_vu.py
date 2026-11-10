"""Restore the signing foreign keys declared by release_DDL.sql.

The four model-state conversions reuse the focused field mapping from PR #138. The
database operations are idempotent on an already canonical DDL schema and report
only table/column counts when existing rows prevent a constraint from being added.
"""

import django.db.models.deletion
from django.db import migrations, models


FOREIGN_KEYS = (
    ("signing_process", "don_vi_ap_dung_id", "organizations_donvi", "id", "RESTRICT", True,
     "fk_signing_process_don_vi_ap_dung"),
    ("signing_process_step", "don_vi_id", "organizations_donvi", "id", "SET NULL", True,
     "fk_signing_process_step_don_vi"),
    ("signing_process_step_signer", "chuc_vu_id", "accounts_position", "id", "RESTRICT", True,
     "fk_signing_process_step_signer_chuc_vu"),
    ("signing_request_step_signer", "chuc_vu_id", "accounts_position", "id", "SET NULL", True,
     "fk_signing_request_step_signer_chuc_vu"),
    ("signing_attempt", "nguoi_cap_nhat_id", "accounts_employee", "id", "SET NULL", True,
     "fk_signing_attempt_nguoi_cap_nhat"),
    ("signing_process", "nguoi_cap_nhat_id", "accounts_employee", "id", "SET NULL", True,
     "fk_signing_process_nguoi_cap_nhat"),
    ("signing_request", "nguoi_cap_nhat_id", "accounts_employee", "id", "SET NULL", True,
     "fk_signing_request_nguoi_cap_nhat"),
    ("signing_key_unlock", "khoa_id", "signing_key", "id", "CASCADE", False,
     "fk_signing_key_unlock_khoa"),
    ("signing_notification", "buoc_ky_id", "signing_request_step_signer", "id", "CASCADE", True,
     "fk_signing_notification_buoc_ky"),
    ("signing_notification", "trinh_ky_id", "signing_request", "id", "CASCADE", False,
     "fk_signing_notification_trinh_ky"),
    ("signing_process_step", "quy_trinh_id", "signing_process", "id", "CASCADE", False,
     "fk_signing_process_step_quy_trinh"),
    ("signing_process_step_signer", "buoc_quy_trinh_id", "signing_process_step", "id", "CASCADE", False,
     "fk_signing_process_step_signer_buoc"),
    ("signing_request_step_signer", "chu_ky_hien_hanh_id", "signing_signature", "id", "SET NULL", True,
     "fk_signer_chu_ky_hien_hanh"),
)

DELETE_ACTIONS = {
    "RESTRICT": "r",
    "SET NULL": "n",
    "CASCADE": "c",
}


def preflight_signing_fk_data(apps, schema_editor):
    connection = schema_editor.connection
    if connection.vendor != "postgresql":
        return

    quote = connection.ops.quote_name
    problems = []
    with connection.cursor() as cursor:
        tables = set(connection.introspection.table_names(cursor))
        required = {item[0] for item in FOREIGN_KEYS} | {item[2] for item in FOREIGN_KEYS}
        missing = sorted(required - tables)
        if missing:
            raise RuntimeError(
                "Signing foreign-key preflight failed; required tables are missing: " + ", ".join(missing)
            )

        for table, column, target, target_column, _, nullable, _ in FOREIGN_KEYS:
            cursor.execute(
                f"SELECT COUNT(*) FROM {quote(table)} AS source "
                f"LEFT JOIN {quote(target)} AS target "
                f"ON source.{quote(column)} = target.{quote(target_column)} "
                f"WHERE source.{quote(column)} IS NOT NULL "
                f"AND target.{quote(target_column)} IS NULL"
            )
            orphan_count = cursor.fetchone()[0]
            if orphan_count:
                problems.append(f"{table}.{column}: {orphan_count} orphan reference(s)")

            if not nullable:
                cursor.execute(f"SELECT COUNT(*) FROM {quote(table)} WHERE {quote(column)} IS NULL")
                null_count = cursor.fetchone()[0]
                if null_count:
                    problems.append(f"{table}.{column}: {null_count} NULL value(s)")

    if problems:
        raise RuntimeError(
            "Signing foreign-key preflight failed; no rows were changed: " + "; ".join(problems)
        )


def _inspect_fk_plan(connection):
    quote = connection.ops.quote_name
    plans = []
    problems = []

    with connection.cursor() as cursor:
        for table, column, target, target_column, action, _, constraint_name in FOREIGN_KEYS:
            constraints = connection.introspection.get_constraints(cursor, table)
            matching = []
            for name, info in constraints.items():
                source_columns = info.get("columns") or []
                foreign_key = info.get("foreign_key")
                if foreign_key is None or column not in source_columns:
                    continue
                if source_columns != [column] or tuple(foreign_key) != (target, target_column):
                    problems.append(f"{table}.{column}: unexpected foreign-key definition")
                    continue
                cursor.execute(
                    "SELECT confdeltype, condeferrable, condeferred, convalidated "
                    "FROM pg_catalog.pg_constraint "
                    "WHERE conrelid = to_regclass(%s) AND conname = %s AND contype = 'f'",
                    [table, name],
                )
                metadata = cursor.fetchone()
                if metadata is None:
                    problems.append(f"{table}.{column}: foreign-key catalog entry is missing")
                    continue
                matching.append((name, metadata))

            if len(matching) > 1:
                problems.append(f"{table}.{column}: {len(matching)} foreign-key constraints found")
                continue

            if constraint_name in constraints and not any(name == constraint_name for name, _ in matching):
                problems.append(f"{table}.{column}: constraint name {constraint_name} is already in use")
                continue

            current_name = matching[0][0] if matching else None
            current_metadata = matching[0][1] if matching else None
            desired_metadata = (DELETE_ACTIONS[action], False, False, True)
            already_correct = current_metadata == desired_metadata
            plans.append((table, column, target, target_column, action, constraint_name, current_name, already_correct))

    if problems:
        raise RuntimeError(
            "Signing foreign-key schema preflight failed; no schema was changed: " + "; ".join(problems)
        )
    return plans


def ensure_signing_foreign_keys(apps, schema_editor):
    connection = schema_editor.connection
    if connection.vendor != "postgresql":
        return

    plans = _inspect_fk_plan(connection)
    quote = connection.ops.quote_name
    for table, column, target, target_column, action, constraint_name, current_name, already_correct in plans:
        if already_correct:
            continue
        if current_name:
            schema_editor.execute(
                f"ALTER TABLE {quote(table)} DROP CONSTRAINT {quote(current_name)}"
            )
        schema_editor.execute(
            f"ALTER TABLE {quote(table)} ADD CONSTRAINT {quote(constraint_name)} "
            f"FOREIGN KEY ({quote(column)}) REFERENCES {quote(target)} ({quote(target_column)}) "
            f"ON DELETE {action}"
        )

    with connection.cursor() as cursor:
        constraints = connection.introspection.get_constraints(cursor, "signing_process")
    index_name = "idx_signing_process_don_vi_ap_dung"
    index_info = constraints.get(index_name)
    if index_info:
        if not (
            index_info.get("index")
            and index_info.get("columns") == ["don_vi_ap_dung_id"]
            and not index_info.get("unique")
            and not index_info.get("primary_key")
        ):
            raise RuntimeError(
                "Signing index preflight failed; signing_process." "don_vi_ap_dung_id index name is incompatible"
            )
    elif not any(
        info.get("index")
        and info.get("columns") == ["don_vi_ap_dung_id"]
        and not info.get("unique")
        and not info.get("primary_key")
        for info in constraints.values()
    ):
        schema_editor.execute(
            f"CREATE INDEX {quote(index_name)} ON {quote('signing_process')} "
            f"({quote('don_vi_ap_dung_id')})"
        )


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0007_normalize_system_account_password"),
        ("organizations", "0005_reference_data_ddl"),
        ("signing", "0009_doi_ten_cot_theo_ddl_chuan_hoa"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(preflight_signing_fk_data, migrations.RunPython.noop),
                migrations.RunPython(ensure_signing_foreign_keys, migrations.RunPython.noop),
            ],
            state_operations=[
                migrations.RemoveField(model_name="signingprocess", name="don_vi_ap_dung_id"),
                migrations.AddField(
                    model_name="signingprocess",
                    name="don_vi_ap_dung",
                    field=models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+",
                        to="organizations.donvi",
                    ),
                ),
                migrations.RemoveField(model_name="signingprocessstep", name="don_vi_id"),
                migrations.AddField(
                    model_name="signingprocessstep",
                    name="don_vi",
                    field=models.ForeignKey(
                        blank=True,
                        db_index=False,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="organizations.donvi",
                    ),
                ),
                migrations.RemoveField(model_name="signingprocessstepsigner", name="chuc_vu_id"),
                migrations.AddField(
                    model_name="signingprocessstepsigner",
                    name="chuc_vu",
                    field=models.ForeignKey(
                        blank=True,
                        db_index=False,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+",
                        to="accounts.position",
                    ),
                ),
                migrations.RemoveField(model_name="signingrequeststepsigner", name="chuc_vu_id"),
                migrations.AddField(
                    model_name="signingrequeststepsigner",
                    name="chuc_vu",
                    field=models.ForeignKey(
                        blank=True,
                        db_index=False,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="accounts.position",
                    ),
                ),
            ],
        ),
    ]
