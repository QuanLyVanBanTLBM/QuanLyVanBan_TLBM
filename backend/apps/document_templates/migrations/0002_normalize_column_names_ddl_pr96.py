# Generated for DDL Staging Release (PR #96 / PR #101 / PR #102)
# Chuẩn hóa tên cột: records_chitiettailieu (nguoi_tao_id), records_chitiettailieu_attachment (created_at, nguoi_tao_id)

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('document_templates', '0001_initial'),
    ]

    operations = [
        # 1. records_chitiettailieu: db_column nguoi_tao -> nguoi_tao_id
        migrations.AlterField(
            model_name='tailieuchitiet',
            name='nguoi_tao',
            field=models.ForeignKey(
                blank=True,
                db_column='nguoi_tao_id',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to=settings.AUTH_USER_MODEL,
                verbose_name='Người tạo'
            ),
        ),
        # 2. records_chitiettailieu_attachment: created_time -> created_at
        migrations.RenameField(
            model_name='chitiettailieuattachment',
            old_name='created_time',
            new_name='created_at',
        ),
        migrations.AlterField(
            model_name='chitiettailieuattachment',
            name='created_at',
            field=models.DateTimeField(
                auto_now_add=True,
                db_column='created_at',
                verbose_name='Thời điểm tải lên'
            ),
        ),
        # 3. records_chitiettailieu_attachment: created_user -> nguoi_tao (db_column nguoi_tao_id)
        migrations.RenameField(
            model_name='chitiettailieuattachment',
            old_name='created_user',
            new_name='nguoi_tao',
        ),
        migrations.AlterField(
            model_name='chitiettailieuattachment',
            name='nguoi_tao',
            field=models.ForeignKey(
                blank=True,
                db_column='nguoi_tao_id',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to=settings.AUTH_USER_MODEL,
                verbose_name='Người tải file'
            ),
        ),
    ]
