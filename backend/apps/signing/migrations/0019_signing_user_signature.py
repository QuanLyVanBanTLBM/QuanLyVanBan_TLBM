import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def install_updated_at_trigger(apps, schema_editor):
    connection = schema_editor.connection
    if connection.vendor != "postgresql":
        return
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT 1 FROM pg_trigger WHERE tgname = 'trg_signing_user_signature_updated_at'"
        )
        if cursor.fetchone() is None:
            cursor.execute(
                "CREATE TRIGGER trg_signing_user_signature_updated_at "
                "BEFORE UPDATE ON signing_user_signature "
                "FOR EACH ROW EXECUTE FUNCTION set_updated_at()"
            )


def remove_updated_at_trigger(apps, schema_editor):
    connection = schema_editor.connection
    if connection.vendor != "postgresql":
        return
    with connection.cursor() as cursor:
        cursor.execute(
            "DROP TRIGGER IF EXISTS trg_signing_user_signature_updated_at ON signing_user_signature"
        )


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("signing", "0018_bo_ky_nhay_uy_quyen"),
    ]

    operations = [
        migrations.CreateModel(
            name="SigningUserSignature",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("vi_tri_tep", models.CharField(max_length=500)),
                ("ma_bam", models.CharField(max_length=64)),
                ("dung_luong_bytes", models.IntegerField()),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        db_default=models.Func(function="now", output_field=models.DateTimeField()),
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        db_default=models.Func(function="now", output_field=models.DateTimeField()),
                    ),
                ),
                (
                    "nguoi_dung",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="anh_chu_ky_ca_nhan",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "signing_user_signature",
            },
        ),
        migrations.RunPython(install_updated_at_trigger, remove_updated_at_trigger),
    ]
