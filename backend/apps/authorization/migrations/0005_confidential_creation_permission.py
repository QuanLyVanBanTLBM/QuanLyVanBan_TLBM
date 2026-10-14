from django.db import migrations


def create_permission(apps, schema_editor):
    # Explicitly assignable creation permission; never grants decryption/reading.
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("INSERT INTO auth_permission (name, codename, module_ten) "
                       "SELECT %s, %s, %s WHERE NOT EXISTS "
                       "(SELECT 1 FROM auth_permission WHERE codename = %s)",
                       ["Tạo văn bản mật mã hóa đầu cuối", "create_confidential_document",
                        "Văn bản mật E2EE", "create_confidential_document"])


class Migration(migrations.Migration):
    dependencies = [("authorization", "0004_grant_tp_manage_signing_process")]
    operations = [migrations.RunPython(create_permission, migrations.RunPython.noop)]
