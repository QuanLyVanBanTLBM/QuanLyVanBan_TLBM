# Văn bản trình ký không bắt buộc gắn văn bản đi (#274): document_type, document_id bỏ NOT NULL; thêm số hiệu,
# trích yếu nhập tay; CHECK hoặc gắn văn bản, hoặc có trích yếu. SQL theo release_DDL.sql (document_type giữ kiểu
# ENUM document_kind nên không để Django sinh ALTER TYPE). Idempotent trên DB đã dựng từ DDL (build_db.py --sync).

from django.db import migrations, models

CHECK_VAN_BAN = (
    "(document_type IS NOT NULL AND document_id IS NOT NULL) "
    "OR (document_type IS NULL AND document_id IS NULL AND trich_yeu_van_ban <> '')"
)


class Migration(migrations.Migration):

    dependencies = [
        ('signing', '0014_bo_muc_do'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql=(
                        "ALTER TABLE signing_request "
                        "ALTER COLUMN document_type DROP NOT NULL, "
                        "ALTER COLUMN document_id DROP NOT NULL, "
                        "ADD COLUMN IF NOT EXISTS so_hieu_van_ban VARCHAR(100) NOT NULL DEFAULT '', "
                        "ADD COLUMN IF NOT EXISTS trich_yeu_van_ban TEXT NOT NULL DEFAULT '';"
                        "DO $$ BEGIN "
                        "IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_signing_request_van_ban' "
                        "AND conrelid = 'signing_request'::regclass) THEN "
                        f"ALTER TABLE signing_request ADD CONSTRAINT chk_signing_request_van_ban CHECK ({CHECK_VAN_BAN}); "
                        "END IF; END $$;"
                    ),
                    reverse_sql=(
                        "ALTER TABLE signing_request "
                        "DROP CONSTRAINT IF EXISTS chk_signing_request_van_ban, "
                        "DROP COLUMN IF EXISTS trich_yeu_van_ban, "
                        "DROP COLUMN IF EXISTS so_hieu_van_ban, "
                        "ALTER COLUMN document_id SET NOT NULL, "
                        "ALTER COLUMN document_type SET NOT NULL;"
                    ),
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name='signingrequest',
                    name='so_hieu_van_ban',
                    field=models.CharField(blank=True, db_default='', default='', max_length=100),
                ),
                migrations.AddField(
                    model_name='signingrequest',
                    name='trich_yeu_van_ban',
                    field=models.TextField(blank=True, db_default='', default=''),
                ),
                migrations.AlterField(
                    model_name='signingrequest',
                    name='document_type',
                    field=models.CharField(blank=True, choices=[('vanbandi', 'Văn bản')], max_length=20, null=True),
                ),
                migrations.AlterField(
                    model_name='signingrequest',
                    name='van_ban_id',
                    field=models.BigIntegerField(blank=True, db_column='document_id', null=True),
                ),
                migrations.AddConstraint(
                    model_name='signingrequest',
                    constraint=models.CheckConstraint(
                        condition=models.Q(
                            models.Q(('document_type__isnull', False), ('van_ban_id__isnull', False)),
                            models.Q(('document_type__isnull', True), ('van_ban_id__isnull', True),
                                     models.Q(('trich_yeu_van_ban', ''), _negated=True)),
                            _connector='OR'),
                        name='chk_signing_request_van_ban'),
                ),
            ],
        ),
    ]
