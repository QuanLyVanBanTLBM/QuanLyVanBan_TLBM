from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [
        ("birthdays", "0005_manual_email_delivery"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql=(
                        'ALTER TABLE "birthdays_birthdayemaillog" '
                        'DROP CONSTRAINT IF EXISTS "uq_emaillog_employee_date"'
                    ),
                    reverse_sql=None,
                ),
            ],
            state_operations=[
                migrations.RemoveConstraint(
                    model_name="birthdayemaillog",
                    name="uq_emaillog_employee_date",
                ),
            ],
        ),
        migrations.AlterField(
            model_name="birthdayemaillog",
            name="delivery_source",
            field=models.CharField(
                choices=[
                    ("AUTO", "Tự động"),
                    ("MANUAL", "Thủ công"),
                    ("MANUAL_RESEND", "Quản trị viên gửi lại"),
                ],
                db_default="AUTO",
                default="AUTO",
                max_length=16,
            ),
        ),
        migrations.AddConstraint(
            model_name="birthdayemaillog",
            constraint=models.UniqueConstraint(
                condition=Q(delivery_source="AUTO"),
                fields=("employee", "sent_date"),
                name="uq_emaillog_employee_date_auto",
            ),
        ),
        migrations.AddConstraint(
            model_name="birthdayemaillog",
            constraint=models.UniqueConstraint(
                condition=Q(delivery_source="MANUAL"),
                fields=("employee", "sent_date"),
                name="uq_emaillog_employee_date_manual",
            ),
        ),
        migrations.AddConstraint(
            model_name="birthdayemaillog",
            constraint=models.UniqueConstraint(
                condition=Q(delivery_source="MANUAL_RESEND", trang_thai="SENDING"),
                fields=("employee", "sent_date"),
                name="uq_emaillog_resend_inflight",
            ),
        ),
    ]
