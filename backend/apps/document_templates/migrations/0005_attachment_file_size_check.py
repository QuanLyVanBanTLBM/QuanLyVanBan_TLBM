"""Reject negative attachment sizes without changing existing records."""

import re

import django.core.validators
from django.db import migrations, models


TABLE = "records_chitiettailieu_attachment"
CONSTRAINT = "records_chitiettailieu_attachment_file_size_check"


def _normalize_check(expression):
    expression = re.sub(r"::(?:bigint|integer|smallint|numeric|text)\b", "", expression.lower())
    return re.sub(r"[\s()\"]+", "", expression)


def ensure_nonnegative_file_size(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        raise RuntimeError("document_templates 0005 requires PostgreSQL.")

    with schema_editor.connection.cursor() as cursor:
        cursor.execute(f"SELECT count(*) FROM {TABLE} WHERE file_size < 0")
        invalid_count = cursor.fetchone()[0]
        if invalid_count:
            raise RuntimeError(
                f"{TABLE}.file_size has {invalid_count} negative rows; migration made no changes."
            )

        cursor.execute(
            "SELECT conname, pg_get_expr(conbin, conrelid), convalidated "
            "FROM pg_constraint WHERE conrelid = %s::regclass AND contype = 'c'",
            [TABLE],
        )
        checks = cursor.fetchall()
        canonical = next((row for row in checks if row[0] == CONSTRAINT), None)
        if canonical and _normalize_check(canonical[1]) != "file_size>=0":
            raise RuntimeError(
                f"{TABLE}.{CONSTRAINT} has an unexpected definition; migration made no changes."
            )

        equivalent = [row for row in checks if _normalize_check(row[1]) == "file_size>=0"]
        if len(equivalent) > 1:
            raise RuntimeError(
                f"{TABLE} has multiple file_size checks; migration made no changes."
            )

        q = schema_editor.connection.ops.quote_name
        if canonical:
            if not canonical[2]:
                cursor.execute(f"ALTER TABLE {q(TABLE)} VALIDATE CONSTRAINT {q(CONSTRAINT)}")
        elif equivalent:
            cursor.execute(
                f"ALTER TABLE {q(TABLE)} RENAME CONSTRAINT {q(equivalent[0][0])} TO {q(CONSTRAINT)}"
            )
            if not equivalent[0][2]:
                cursor.execute(f"ALTER TABLE {q(TABLE)} VALIDATE CONSTRAINT {q(CONSTRAINT)}")
        else:
            cursor.execute(
                f"ALTER TABLE {q(TABLE)} ADD CONSTRAINT {q(CONSTRAINT)} CHECK (file_size >= 0)"
            )


class Migration(migrations.Migration):
    dependencies = [
        ("document_templates", "0004_schema_scalars"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[migrations.RunPython(ensure_nonnegative_file_size, migrations.RunPython.noop)],
            state_operations=[
                migrations.AlterField(
                    model_name="chitiettailieuattachment",
                    name="file_size",
                    field=models.BigIntegerField(
                        blank=True,
                        null=True,
                        validators=[django.core.validators.MinValueValidator(0)],
                        verbose_name="Dung lượng (byte)",
                    ),
                ),
                migrations.AddConstraint(
                    model_name="chitiettailieuattachment",
                    constraint=models.CheckConstraint(
                        condition=models.Q(file_size__gte=0),
                        name=CONSTRAINT,
                    ),
                ),
            ],
        ),
    ]
