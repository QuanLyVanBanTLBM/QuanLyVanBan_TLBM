from django.db import migrations, models
from django.utils import timezone
from django.db.models.functions import Now


def flag_ambiguous_legacy_deliveries(apps, schema_editor):
    log = apps.get_model("birthdays", "BirthdayEmailLog")
    log.objects.filter(trang_thai__in=("RETRY", "FAILED")).exclude(
        error_message__startswith="Bỏ qua:"
    ).exclude(
        error_message="SMTP did not accept the message."
    ).exclude(
        error_message__regex=r"^SMTP(AuthenticationError|ConnectError|DataError|HeloError|SenderRefused) \(SMTP [45][0-9]{2}\)$"
    ).update(trang_thai="FAILED", delivery_uncertain=True, next_retry_at=None)


class Migration(migrations.Migration):
    dependencies = [("birthdays", "0004_install_updated_at_triggers")]

    operations = [
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
        migrations.RunPython(flag_ambiguous_legacy_deliveries, migrations.RunPython.noop),
    ]
