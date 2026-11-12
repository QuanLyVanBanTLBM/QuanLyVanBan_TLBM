import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("signing", "0015_van_ban_trinh_ky_khac"), ("accounts", "0001_initial")]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql=(
                        "ALTER TABLE signing_request_step_signer "
                        "ADD COLUMN IF NOT EXISTS chuc_vu_goc_uy_quyen_id BIGINT REFERENCES accounts_position (id) ON DELETE RESTRICT;"
                        "CREATE INDEX IF NOT EXISTS idx_signing_request_step_signer_chuc_vu_goc "
                        "ON signing_request_step_signer (chuc_vu_goc_uy_quyen_id);"
                        "CREATE TABLE IF NOT EXISTS signing_delegation_role ("
                        "    id BIGSERIAL PRIMARY KEY,"
                        "    chuc_vu_giao_id BIGINT NOT NULL REFERENCES accounts_position (id) ON DELETE RESTRICT,"
                        "    chuc_vu_nhan_id BIGINT NOT NULL REFERENCES accounts_position (id) ON DELETE RESTRICT,"
                        "    CONSTRAINT uq_signing_delegation_role UNIQUE (chuc_vu_giao_id, chuc_vu_nhan_id)"
                        ");"
                        "CREATE INDEX IF NOT EXISTS idx_signing_delegation_role_giao ON signing_delegation_role (chuc_vu_giao_id);"
                        "CREATE INDEX IF NOT EXISTS idx_signing_delegation_role_nhan ON signing_delegation_role (chuc_vu_nhan_id);"
                    ),
                    reverse_sql=(
                        "DROP TABLE IF EXISTS signing_delegation_role;"
                        "DROP INDEX IF EXISTS idx_signing_request_step_signer_chuc_vu_goc;"
                        "ALTER TABLE signing_request_step_signer DROP COLUMN IF EXISTS chuc_vu_goc_uy_quyen_id;"
                    ),
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name="signingrequeststepsigner",
                    name="chuc_vu_goc_uy_quyen",
                    field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="+", to="accounts.position"),
                ),
                migrations.CreateModel(
                    name="SigningDelegationRole",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("chuc_vu_giao", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="+", to="accounts.position")),
                        ("chuc_vu_nhan", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="+", to="accounts.position")),
                    ],
                    options={"db_table": "signing_delegation_role", "constraints": [models.UniqueConstraint(fields=("chuc_vu_giao", "chuc_vu_nhan"), name="uq_signing_delegation_role")]},
                ),
            ],
        ),
    ]
