from django.db import migrations, models
from django.utils import timezone


def retire_old_keys_and_clear_unlocks(apps, schema_editor):
    SigningKey = apps.get_model("signing", "SigningKey")
    SigningKeyUnlock = apps.get_model("signing", "SigningKeyUnlock")
    SigningKey.objects.filter(trang_thai__in=["HOAT_DONG", "CHO_KICH_HOAT"]).update(
        trang_thai="THU_HOI", ngay_thu_hoi=timezone.now(),
    )
    # Old PIN verifiers were derived under the browser-key scheme; new enrollment writes a new verifier.
    # Unlock rows also hold the obsolete server share, not signed evidence.
    # Public keys, signature rows, and audit logs are deliberately retained.
    SigningKeyUnlock.objects.all().delete()


class Migration(migrations.Migration):
    atomic = True

    dependencies = [
        ("signing", "0024_ma_xac_thuc_mfa_ky"),
    ]

    operations = [
        # Retired browser-key material is deliberately not restored on downgrade; restore a backup instead.
        migrations.RunPython(retire_old_keys_and_clear_unlocks, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="signingkeyunlock",
            name="manh_bi_mat_ma_hoa",
        ),
        migrations.AddField(
            model_name="signingkeyunlock",
            name="khoa_bi_mat_ma_hoa",
            field=models.TextField(),
        ),
    ]
