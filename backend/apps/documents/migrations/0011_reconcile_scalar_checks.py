"""Align document scalar checks with the release DDL without rewriting rows."""

import re

import django.core.validators
import django.db.models.expressions
import django.db.models.functions.text
import django.db.models.lookups
from django.conf import settings
from django.db import migrations, models


LINK_CHECKS = (
    ("documents_vanbanden", "chk_vanbanden_link_thay_the"),
    ("documents_vanbandi", "chk_vanbandi_link_thay_the"),
)
EXPECTED_LINK_CHECK = (
    "((hieu_luc <> 'HET_VA_THAY_THE'::hieu_luc_status) OR "
    "((link_thay_the IS NOT NULL) AND "
    "(btrim((link_thay_the)::text) <> ''::text)))"
)


def _normalize_link_check(expression):
    # pg_get_expr has already canonicalized PostgreSQL's parsed expression.
    # Keep boolean grouping and string literals intact: deleting parentheses
    # would make (A OR B) AND C indistinguishable from A OR (B AND C).
    return re.sub(r"\s+", " ", expression.strip())


def _link_constraints(cursor, table):
    cursor.execute(
        "SELECT conname, pg_get_expr(conbin, conrelid), convalidated "
        "FROM pg_constraint WHERE conrelid = %s::regclass AND contype = 'c'",
        [table],
    )
    return cursor.fetchall()


def _validate_link_constraint_state(cursor, table, constraint):
    checks = _link_constraints(cursor, table)
    canonical = next((row for row in checks if row[0] == constraint), None)
    if canonical and _normalize_link_check(canonical[1]) != EXPECTED_LINK_CHECK:
        raise RuntimeError(
            f"{table}.{constraint} has an unexpected definition; migration made no changes."
        )

    equivalent = [row for row in checks if _normalize_link_check(row[1]) == EXPECTED_LINK_CHECK]
    if len(equivalent) > 1:
        raise RuntimeError(f"{table} has multiple replacement-link checks; migration made no changes.")


def preflight_document_constraints(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        raise RuntimeError("documents 0011 requires PostgreSQL.")

    invalid_counts = []
    with schema_editor.connection.cursor() as cursor:
        for table, _constraint in LINK_CHECKS:
            cursor.execute(
                f"SELECT count(*) FROM {table} "
                "WHERE hieu_luc::text = %s "
                "AND (link_thay_the IS NULL OR btrim(link_thay_the) = '')",
                ["HET_VA_THAY_THE"],
            )
            invalid_count = cursor.fetchone()[0]
            if invalid_count:
                invalid_counts.append((table, invalid_count))

        if invalid_counts:
            counts = ", ".join(f"{table}: {count}" for table, count in invalid_counts)
            raise RuntimeError(
                f"Replacement-link preflight found invalid row counts ({counts}); "
                "migration made no changes."
            )

        for table, constraint in LINK_CHECKS:
            _validate_link_constraint_state(cursor, table, constraint)


def ensure_document_link_checks(apps, schema_editor):
    q = schema_editor.connection.ops.quote_name
    with schema_editor.connection.cursor() as cursor:
        for table, constraint in LINK_CHECKS:
            checks = _link_constraints(cursor, table)
            canonical = next((row for row in checks if row[0] == constraint), None)
            equivalent = [row for row in checks if _normalize_link_check(row[1]) == EXPECTED_LINK_CHECK]

            if canonical:
                if _normalize_link_check(canonical[1]) != EXPECTED_LINK_CHECK:
                    raise RuntimeError(
                        f"{table}.{constraint} has an unexpected definition; migration made no changes."
                    )
                if not canonical[2]:
                    cursor.execute(f"ALTER TABLE {q(table)} VALIDATE CONSTRAINT {q(constraint)}")
            elif equivalent:
                if len(equivalent) != 1:
                    raise RuntimeError(
                        f"{table} has multiple replacement-link checks; migration made no changes."
                    )
                cursor.execute(
                    f"ALTER TABLE {q(table)} RENAME CONSTRAINT {q(equivalent[0][0])} TO {q(constraint)}"
                )
                if not equivalent[0][2]:
                    cursor.execute(f"ALTER TABLE {q(table)} VALIDATE CONSTRAINT {q(constraint)}")
            else:
                cursor.execute(
                    f"ALTER TABLE {q(table)} ADD CONSTRAINT {q(constraint)} "
                    "CHECK ((hieu_luc <> 'HET_VA_THAY_THE') OR "
                    "(link_thay_the IS NOT NULL AND btrim(link_thay_the) <> ''))"
                )


class Migration(migrations.Migration):
    atomic = True

    dependencies = [
        ("documents", "0010_ai_metadata_views"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(preflight_document_constraints, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="documentviewlog",
            name="document_id",
            field=models.BigIntegerField(
                validators=[django.core.validators.MinValueValidator(0)],
                verbose_name="ID văn bản",
            ),
        ),
        migrations.AlterField(
            model_name="vanbanden",
            name="nam",
            field=models.SmallIntegerField(
                db_index=True,
                default=2026,
                help_text="Mặc định năm hiện tại, cho phép sửa.",
                validators=[django.core.validators.MinValueValidator(0)],
                verbose_name="Năm",
            ),
        ),
        migrations.AlterField(
            model_name="vanbanden",
            name="so_thu_tu",
            field=models.IntegerField(
                default=1,
                help_text="Tự động tăng theo năm (Số đến).",
                validators=[django.core.validators.MinValueValidator(0)],
                verbose_name="Số đến",
            ),
        ),
        migrations.AlterField(
            model_name="vanbandi",
            name="nam",
            field=models.SmallIntegerField(
                db_index=True,
                default=2026,
                help_text="Mặc định năm hiện tại, cho phép sửa.",
                validators=[django.core.validators.MinValueValidator(0)],
                verbose_name="Năm",
            ),
        ),
        migrations.AlterField(
            model_name="vanbandi",
            name="so_thu_tu",
            field=models.IntegerField(
                default=1,
                help_text="Tự động tăng theo năm (Số đi).",
                validators=[django.core.validators.MinValueValidator(0)],
                verbose_name="Số đi",
            ),
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(ensure_document_link_checks, migrations.RunPython.noop),
            ],
            state_operations=[
                migrations.AddConstraint(
                    model_name="vanbanden",
                    constraint=models.CheckConstraint(
                        condition=models.Q(
                            models.Q(("hieu_luc", "HET_VA_THAY_THE"), _negated=True),
                            models.Q(
                                ("link_thay_the__isnull", False),
                                django.db.models.expressions.NegatedExpression(
                                    django.db.models.lookups.Exact(
                                        django.db.models.functions.text.Trim(models.F("link_thay_the")),
                                        models.Value(""),
                                    )
                                ),
                            ),
                            _connector="OR",
                        ),
                        name="chk_vanbanden_link_thay_the",
                    ),
                ),
                migrations.AddConstraint(
                    model_name="vanbandi",
                    constraint=models.CheckConstraint(
                        condition=models.Q(
                            models.Q(("hieu_luc", "HET_VA_THAY_THE"), _negated=True),
                            models.Q(
                                ("link_thay_the__isnull", False),
                                django.db.models.expressions.NegatedExpression(
                                    django.db.models.lookups.Exact(
                                        django.db.models.functions.text.Trim(models.F("link_thay_the")),
                                        models.Value(""),
                                    )
                                ),
                            ),
                            _connector="OR",
                        ),
                        name="chk_vanbandi_link_thay_the",
                    ),
                ),
            ],
        ),
    ]
