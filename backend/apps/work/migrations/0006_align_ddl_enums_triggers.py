"""
Đồng bộ schema migration với release_DDL.sql (phần app work, nhóm 6).

Chỉ chạy trên PostgreSQL — SQLite (test mặc định) tự bỏ qua.

Thay đổi:
1. Tạo ENUM task_vaitro, đổi task_participant.vai_tro từ varchar → ENUM.
2. Tạo ENUM task_attachment_loai, đổi task_attachment.loai từ varchar → ENUM.
3. Tạo trigger trg_congviec_updated_at (dùng function chung set_updated_at).

4. Thêm CHECK constraint chk_task_participant_role (DDL có, Django không tạo).
5. Drop+recreate chk_task_attachment_evidence với ENUM-native syntax
   (migration 0004 tạo bằng text cast, cần thay bằng ENUM comparison).
"""

from django.db import migrations


def is_postgres(schema_editor):
    return schema_editor.connection.vendor == "postgresql"



def forward_enum_vaitro(apps, schema_editor):
    if not is_postgres(schema_editor):
        return
    schema_editor.execute("""\
DO $$ BEGIN
    CREATE TYPE task_vaitro AS ENUM ('CHU_TRI', 'CHI_DAO', 'THAM_GIA');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
""")
    # Partial unique index uq_task_participant_one_host has predicate
    # WHERE vai_tro = 'CHU_TRI'; Postgres can't validate it during
    # ALTER COLUMN TYPE (implicit cast not IMMUTABLE). Drop → alter → recreate.
    schema_editor.execute(
        "DROP INDEX IF EXISTS uq_task_participant_one_host;"
    )
    schema_editor.execute("""\
ALTER TABLE task_participant
    ALTER COLUMN vai_tro TYPE task_vaitro USING vai_tro::task_vaitro;
""")
    schema_editor.execute("""\
CREATE UNIQUE INDEX uq_task_participant_one_host
    ON task_participant (cong_viec) WHERE vai_tro = 'CHU_TRI';
""")


def reverse_enum_vaitro(apps, schema_editor):
    if not is_postgres(schema_editor):
        return
    schema_editor.execute(
        "DROP INDEX IF EXISTS uq_task_participant_one_host;"
    )
    schema_editor.execute("""\
ALTER TABLE task_participant
    ALTER COLUMN vai_tro TYPE varchar(20) USING vai_tro::text;
""")
    schema_editor.execute("DROP TYPE IF EXISTS task_vaitro;")
    schema_editor.execute("""\
CREATE UNIQUE INDEX uq_task_participant_one_host
    ON task_participant (cong_viec) WHERE vai_tro = 'CHU_TRI';
""")


def forward_enum_attachment_loai(apps, schema_editor):
    if not is_postgres(schema_editor):
        return
    schema_editor.execute("""\
DO $$ BEGIN
    CREATE TYPE task_attachment_loai AS ENUM ('GIAO_VIEC', 'BANG_CHUNG');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
""")
    schema_editor.execute("""\
ALTER TABLE task_attachment
    ALTER COLUMN loai TYPE task_attachment_loai USING loai::task_attachment_loai;
""")


def reverse_enum_attachment_loai(apps, schema_editor):
    if not is_postgres(schema_editor):
        return
    schema_editor.execute("""\
ALTER TABLE task_attachment
    ALTER COLUMN loai TYPE varchar(10) USING loai::text;
""")
    schema_editor.execute("DROP TYPE IF EXISTS task_attachment_loai;")


def forward_constraints(apps, schema_editor):
    if not is_postgres(schema_editor):
        return
    # chk_task_participant_role: DDL has it, Django never created it.
    schema_editor.execute("""\
ALTER TABLE task_participant
    ADD CONSTRAINT chk_task_participant_role CHECK (
        vai_tro = ANY (ARRAY[
            'CHU_TRI'::task_vaitro,
            'CHI_DAO'::task_vaitro,
            'THAM_GIA'::task_vaitro
        ])
    );
""")
    # chk_task_attachment_evidence: migration 0004 created it with text-cast
    # syntax; replace with ENUM-native version to match DDL.
    schema_editor.execute(
        "ALTER TABLE task_attachment DROP CONSTRAINT IF EXISTS chk_task_attachment_evidence;"
    )
    schema_editor.execute("""\
ALTER TABLE task_attachment
    ADD CONSTRAINT chk_task_attachment_evidence CHECK (
        (loai = 'GIAO_VIEC'::task_attachment_loai AND y_kien_id IS NULL)
        OR (loai = 'BANG_CHUNG'::task_attachment_loai AND y_kien_id IS NOT NULL)
    );
""")


def reverse_constraints(apps, schema_editor):
    if not is_postgres(schema_editor):
        return
    schema_editor.execute(
        "ALTER TABLE task_participant DROP CONSTRAINT IF EXISTS chk_task_participant_role;"
    )
    # Restore Django's text-cast version of the constraint.
    schema_editor.execute(
        "ALTER TABLE task_attachment DROP CONSTRAINT IF EXISTS chk_task_attachment_evidence;"
    )
    schema_editor.execute("""\
ALTER TABLE task_attachment
    ADD CONSTRAINT chk_task_attachment_evidence CHECK (
        (y_kien_id IS NULL AND loai::text = 'GIAO_VIEC')
        OR (y_kien_id IS NOT NULL AND loai::text = 'BANG_CHUNG')
    );
""")


def forward_trigger_updated_at(apps, schema_editor):
    if not is_postgres(schema_editor):
        return
    schema_editor.execute("""\
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
NEW.updated_at = now();
RETURN NEW;
END;

$$
LANGUAGE plpgsql;
""")
    schema_editor.execute(
        "DROP TRIGGER IF EXISTS trg_congviec_updated_at ON task_congviec;"
    )
    schema_editor.execute("""\
CREATE TRIGGER trg_congviec_updated_at
    BEFORE UPDATE ON task_congviec
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
""")


def reverse_trigger_updated_at(apps, schema_editor):
    if not is_postgres(schema_editor):
        return
    schema_editor.execute(
        "DROP TRIGGER IF EXISTS trg_congviec_updated_at ON task_congviec;"
    )


class Migration(migrations.Migration):

    dependencies = [
        ("work", "0005_taskdonvi_don_vi_fk"),
    ]

    operations = [
        migrations.RunPython(forward_enum_vaitro, reverse_enum_vaitro),
        migrations.RunPython(forward_enum_attachment_loai, reverse_enum_attachment_loai),
        migrations.RunPython(forward_constraints, reverse_constraints),
        migrations.RunPython(forward_trigger_updated_at, reverse_trigger_updated_at),
    ]
