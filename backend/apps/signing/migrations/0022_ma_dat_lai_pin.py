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
            "ALTER TABLE signing_pin_reset_code ADD CONSTRAINT signing_pin_reset_code_nguoi_dung_id_fkey "
            "FOREIGN KEY (nguoi_dung_id) REFERENCES accounts_employee (id) ON DELETE CASCADE"
        )


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("signing", "0021_thong_bao_khong_gan_ho_so"),
    ]

    operations = [
        migrations.CreateModel(
            name="SigningPinResetCode",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("ma_bam", models.CharField(max_length=64)),
                ("het_han", models.DateTimeField()),
                ("so_lan_sai", models.IntegerField(db_default=0, default=0)),
                ("da_dung_luc", models.DateTimeField(blank=True, null=True)),
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
                "db_table": "signing_pin_reset_code",
                "indexes": [
                    models.Index(fields=["nguoi_dung", "created_at"], name="idx_signing_pin_reset_user")
                ],
            },
        ),
        migrations.RunPython(them_khoa_ngoai_cascade, migrations.RunPython.noop),
    ]
