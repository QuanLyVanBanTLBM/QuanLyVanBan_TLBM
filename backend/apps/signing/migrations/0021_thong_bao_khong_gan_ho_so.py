import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """`signing_notification.trinh_ky_id` cho phép rỗng (thông báo thao tác quản trị không gắn hồ sơ trình ký).

    Chỉ gỡ NOT NULL bằng SQL: `AlterField` của Django thả rồi tạo lại khóa ngoại không có ON DELETE CASCADE
    mà `release_DDL.sql` quy định, nên phần cơ sở dữ liệu tách khỏi phần trạng thái model.
    """

    dependencies = [
        ("signing", "0020_khoa_quyen_ky"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name="signingnotification",
                    name="trinh_ky",
                    field=models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to="signing.signingrequest",
                    ),
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql="ALTER TABLE signing_notification ALTER COLUMN trinh_ky_id DROP NOT NULL",
                    reverse_sql="ALTER TABLE signing_notification ALTER COLUMN trinh_ky_id SET NOT NULL",
                ),
            ],
        ),
    ]
