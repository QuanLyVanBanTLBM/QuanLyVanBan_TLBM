import django.db.models.deletion
from django.db import migrations, models
from django.utils import timezone


def expire_unbound_reset_codes(apps, schema_editor):
    SigningPinResetCode = apps.get_model("signing", "SigningPinResetCode")
    now = timezone.now()
    SigningPinResetCode.objects.filter(da_dung_luc__isnull=True, het_han__gt=now).update(het_han=now)


def add_khoa_foreign_key(apps, schema_editor):
    connection = schema_editor.connection
    if connection.vendor != "postgresql":
        return
    with connection.cursor() as cursor:
        cursor.execute(
            "ALTER TABLE signing_pin_reset_code ADD CONSTRAINT signing_pin_reset_code_khoa_id_fkey "
            "FOREIGN KEY (khoa_id) REFERENCES signing_key (id) ON DELETE RESTRICT"
        )


def drop_khoa_foreign_key(apps, schema_editor):
    connection = schema_editor.connection
    if connection.vendor != "postgresql":
        return
    with connection.cursor() as cursor:
        cursor.execute(
            "ALTER TABLE signing_pin_reset_code "
            "DROP CONSTRAINT IF EXISTS signing_pin_reset_code_khoa_id_fkey"
        )


class Migration(migrations.Migration):
    atomic = True

    dependencies = [
        ("signing", "0025_server_side_private_key"),
    ]

    operations = [
        # Old email codes were issued under the revoke-and-reregister contract; do not let them
        # reset the PIN of a key registered after this migration.
        migrations.RunPython(expire_unbound_reset_codes, migrations.RunPython.noop),
        migrations.AddField(
            model_name="signingpinresetcode",
            name="khoa",
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to="signing.signingkey",
            ),
        ),
        migrations.RunPython(add_khoa_foreign_key, drop_khoa_foreign_key),
    ]
