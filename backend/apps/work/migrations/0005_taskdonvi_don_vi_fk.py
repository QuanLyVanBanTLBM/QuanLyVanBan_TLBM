import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("organizations", "0003_remove_donvi_created_at_remove_donvi_updated_at_and_more"),
        ("work", "0004_alter_task_options_and_more"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="taskdonvi",
            name="uq_task_congviec_donvi",
        ),
        migrations.RemoveIndex(
            model_name="taskdonvi",
            name="idx_task_donvi_donvi",
        ),
        migrations.RenameField(
            model_name="taskdonvi",
            old_name="don_vi_id",
            new_name="don_vi",
        ),
        migrations.AlterField(
            model_name="taskdonvi",
            name="don_vi",
            field=models.ForeignKey(
                db_column="don_vi",
                db_index=False,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="task_links",
                to="organizations.donvi",
                verbose_name="Đơn vị",
            ),
        ),
        migrations.AddIndex(
            model_name="taskdonvi",
            index=models.Index(fields=["don_vi"], name="idx_task_donvi_donvi"),
        ),
        migrations.AddConstraint(
            model_name="taskdonvi",
            constraint=models.UniqueConstraint(
                fields=("task", "don_vi"),
                name="uq_task_congviec_donvi",
                violation_error_message=(
                    "Phòng ban này đã được gắn cho công việc. Hãy bỏ bớt phòng ban trùng."
                ),
            ),
        ),
    ]
