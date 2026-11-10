from django.db import migrations, models
from django.utils import timezone
from django.db.models.functions import Now


def create_birthdayemailtemplate_if_missing(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        table_names = schema_editor.connection.introspection.table_names(cursor)
    if "birthdays_birthdayemailtemplate" not in table_names:
        from birthdays.models import BirthdayEmailTemplate
        schema_editor.create_model(BirthdayEmailTemplate)


def drop_birthdayemailtemplate_if_exists(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        table_names = schema_editor.connection.introspection.table_names(cursor)
    if "birthdays_birthdayemailtemplate" in table_names:
        from birthdays.models import BirthdayEmailTemplate
        schema_editor.delete_model(BirthdayEmailTemplate)


def add_emaillog_fields_if_missing(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        table_description = schema_editor.connection.introspection.get_table_description(
            cursor, "birthdays_birthdayemaillog"
        )
        existing_cols = {col.name for col in table_description}

    from birthdays.models import BirthdayEmailLog
    fields = [
        ("delivery_source", BirthdayEmailLog._meta.get_field("delivery_source")),
        ("delivery_snapshot", BirthdayEmailLog._meta.get_field("delivery_snapshot")),
        ("last_operator", BirthdayEmailLog._meta.get_field("last_operator")),
        ("delivery_uncertain", BirthdayEmailLog._meta.get_field("delivery_uncertain")),
    ]
    for col_name, field in fields:
        if col_name not in existing_cols:
            schema_editor.add_field(BirthdayEmailLog, field)


def remove_emaillog_fields_if_exists(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        table_description = schema_editor.connection.introspection.get_table_description(
            cursor, "birthdays_birthdayemaillog"
        )
        existing_cols = {col.name for col in table_description}

    from birthdays.models import BirthdayEmailLog
    for col_name in ["delivery_uncertain", "last_operator", "delivery_snapshot", "delivery_source"]:
        if col_name in existing_cols:
            schema_editor.remove_field(BirthdayEmailLog, BirthdayEmailLog._meta.get_field(col_name))


def flag_ambiguous_legacy_deliveries(apps, schema_editor):
    log = apps.get_model("birthdays", "BirthdayEmailLog")
    query = log.objects.filter(trang_thai__in=("RETRY", "FAILED")).exclude(
        error_message__startswith="Bỏ qua:"
    ).exclude(
        error_message="SMTP did not accept the message."
    )
    if schema_editor.connection.vendor == "postgresql":
        query = query.exclude(
            error_message__regex=r"^SMTP(AuthenticationError|ConnectError|DataError|HeloError|SenderRefused) \(SMTP [45][0-9]{2}\)$"
        )
    query.update(trang_thai="FAILED", delivery_uncertain=True, next_retry_at=None)


class Migration(migrations.Migration):
    dependencies = [("birthdays", "0004_install_updated_at_triggers")]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(
                    create_birthdayemailtemplate_if_missing,
                    drop_birthdayemailtemplate_if_exists,
                ),
                migrations.RunPython(
                    add_emaillog_fields_if_missing,
                    remove_emaillog_fields_if_exists,
                ),
            ],
            state_operations=[
                migrations.CreateModel(
                    name="BirthdayEmailTemplate",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("name", models.CharField(max_length=120)),
                        ("layout", models.CharField(max_length=2)),
                        ("subject", models.CharField(max_length=255)),
                        ("message", models.TextField()),
                        ("created_at", models.DateTimeField(default=timezone.now, db_default=Now())),
                    ],
                    options={"db_table": "birthdays_birthdayemailtemplate", "ordering": ["-id"]},
                ),
                migrations.AddField(
                    model_name="birthdayemaillog",
                    name="delivery_source",
                    field=models.CharField(choices=[("AUTO", "Tự động"), ("MANUAL", "Thủ công")], max_length=8, default="AUTO", db_default="AUTO"),
                ),
                migrations.AddField(
                    model_name="birthdayemaillog", name="delivery_snapshot", field=models.JSONField(blank=True, null=True),
                ),
                migrations.AddField(
                    model_name="birthdayemaillog", name="last_operator", field=models.CharField(blank=True, null=True, max_length=150),
                ),
                migrations.AddField(
                    model_name="birthdayemaillog", name="delivery_uncertain", field=models.BooleanField(default=False, db_default=False),
                ),
            ],
        ),
        migrations.RunPython(flag_ambiguous_legacy_deliveries, migrations.RunPython.noop),
    ]
