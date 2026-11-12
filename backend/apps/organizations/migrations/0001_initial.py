# Generated manually for Django organizations app
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="KhoiKhuVuc",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "ten",
                    models.CharField(
                        max_length=255,
                        unique=True,
                        verbose_name="organizations.region.nameLabel",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        verbose_name="common.createdAt",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        verbose_name="common.updatedAt",
                    ),
                ),
            ],
            options={
                "verbose_name": "organizations.tabs.regions",
                "verbose_name_plural": "organizations.tabs.regions",
                "ordering": ["ten"],
            },
        ),
        migrations.CreateModel(
            name="DonVi",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "stt_uu_tien",
                    models.PositiveIntegerField(
                        help_text="organizations.unit.priorityHelp",
                        unique=True,
                        verbose_name="organizations.unit.priorityLabel",
                    ),
                ),
                (
                    "ten",
                    models.CharField(
                        max_length=255,
                        verbose_name="organizations.unit.nameLabel",
                    ),
                ),
                (
                    "dia_chi",
                    models.TextField(
                        blank=True,
                        default="",
                        verbose_name="organizations.unit.addressLabel",
                    ),
                ),
                (
                    "dien_thoai",
                    models.CharField(
                        blank=True,
                        default="",
                        max_length=20,
                        verbose_name="organizations.unit.phoneLabel",
                    ),
                ),
                (
                    "email",
                    models.EmailField(
                        blank=True,
                        default="",
                        max_length=254,
                        verbose_name="organizations.unit.emailLabel",
                    ),
                ),
                (
                    "is_public",
                    models.BooleanField(
                        default=True,
                        help_text="organizations.unit.isPublicHelp",
                        verbose_name="organizations.unit.isPublicLabel",
                    ),
                ),
                (
                    "ghi_chu",
                    models.TextField(
                        blank=True,
                        default="",
                        verbose_name="organizations.unit.notesLabel",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        verbose_name="common.createdAt",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        verbose_name="common.updatedAt",
                    ),
                ),
                (
                    "khoi",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="don_vi_list",
                        to="organizations.khoikhuvuc",
                        verbose_name="organizations.unit.regionLabel",
                    ),
                ),
            ],
            options={
                "verbose_name": "organizations.tabs.units",
                "verbose_name_plural": "organizations.tabs.units",
                "ordering": ["stt_uu_tien", "ten"],
                "permissions": [
                    ("export_donvi", "organizations.unit.exportPermission"),
                ],
            },
        ),
    ]
