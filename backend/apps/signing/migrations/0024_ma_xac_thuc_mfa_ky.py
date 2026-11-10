import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def them_khoa_ngoai_cascade(apps, schema_editor):
    connection = schema_editor.connection
    if connection.vendor != "postgresql":
        return
    with connection.cursor() as cursor:
        # release_DDL.sql khai báo FK nguoi_dung_id với ON DELETE CASCADE; Django chỉ tạo FK không có hành động xóa
        # nên field dùng db_constraint=False và FK tạo ở đây.
        cursor.execute(
            "ALTER TABLE signing_mfa_otp ADD CONSTRAINT signing_mfa_otp_nguoi_dung_id_fkey "
            "FOREIGN KEY (nguoi_dung_id) REFERENCES accounts_employee (id) ON DELETE CASCADE"
        )


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("signing", "0023_challenge_da_dung"),
    ]

    operations = [
        migrations.CreateModel(
            name="SigningMfaOtp",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("muc_dich", models.CharField(db_default="KY", default="KY", max_length=20)),
                ("ma_bam", models.CharField(max_length=64)),
                ("het_han", models.DateTimeField()),
                ("so_lan_sai", models.IntegerField(db_default=0, default=0)),
                ("da_dung_luc", models.DateTimeField(blank=True, null=True)),
                ("phien_jti", models.CharField(blank=True, max_length=64, null=True)),
                ("phien_het_han", models.DateTimeField(blank=True, null=True)),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        db_default=models.Func(function="now", output_field=models.DateTimeField()),
                    ),
                ),
                (
                    "nguoi_dung",
                    models.ForeignKey(
                        db_constraint=False,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "signing_mfa_otp",
                "indexes": [
                    models.Index(fields=["nguoi_dung", "muc_dich", "created_at"], name="idx_signing_mfa_otp_user"),
                    models.Index(fields=["nguoi_dung", "phien_jti"], name="idx_signing_mfa_otp_phien"),
                ],
            },
        ),
        migrations.RunPython(them_khoa_ngoai_cascade, migrations.RunPython.noop),
    ]
