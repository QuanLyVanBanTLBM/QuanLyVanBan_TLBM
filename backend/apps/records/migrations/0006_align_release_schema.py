"""Align only Group 3 tables with the release DDL without rebuilding data."""

import django.core.validators
import django.db.models.expressions
import django.db.models.functions.text
import django.db.models.lookups
import records.models
from django.conf import settings
from django.db import migrations, models



RELEASE_FUNCTIONS = (
    """CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
NEW.updated_at = now();
RETURN NEW;
END;

$$
LANGUAGE plpgsql;""",
    """CREATE OR REPLACE FUNCTION auto_stt_uu_tien_hoso()
RETURNS TRIGGER AS
$$

BEGIN
IF NEW.stt_uu_tien IS NULL OR NEW.stt_uu_tien = 0 THEN
-- Advisory lock trên OID của bảng để serialize việc tính MAX
PERFORM pg_advisory_xact_lock('records_hoso'::regclass::oid::bigint);
NEW.stt_uu_tien := COALESCE(
(SELECT MAX(stt_uu_tien) FROM records_hoso), 0
) + 1;
END IF;
RETURN NEW;
END;

$$
LANGUAGE plpgsql;""",
    """CREATE OR REPLACE FUNCTION prevent_delete_he_thong_hoso()
RETURNS TRIGGER AS
$$

BEGIN
IF OLD.is_he_thong = TRUE THEN
RAISE EXCEPTION 'Không thể xóa Hồ sơ chung / bản ghi hệ thống (records_hoso id=%).', OLD.id;
END IF;
RETURN OLD;
END;

$$
LANGUAGE plpgsql;""",
    """CREATE OR REPLACE FUNCTION prevent_update_he_thong_hoso()
RETURNS TRIGGER AS
$$

BEGIN
IF OLD.is_he_thong = TRUE AND NEW.is_he_thong = FALSE THEN
RAISE EXCEPTION 'Bảo toàn Hồ sơ hệ thống: Không thể gỡ bỏ cờ is_he_thong từ TRUE sang FALSE (records_hoso id=%).', OLD.id;
END IF;
RETURN NEW;
END;

$$
LANGUAGE plpgsql;""",
)


def align_schema(apps, schema_editor):
    connection = schema_editor.connection
    if connection.vendor == "sqlite":
        # Apply the same state operations using SQLite's schema editor, then
        # reinstall guards removed by its table rebuilds.
        from django.db.migrations.state import ProjectState
        from importlib import import_module
        state = ProjectState.from_apps(apps)
        for operation in STATE_OPERATIONS:
            after = state.clone()
            operation.state_forwards("records", after)
            operation.database_forwards("records", schema_editor, state, after)
            state = after
        import_module("records.migrations.0004_restore_sqlite_hoso_guards").restore_sqlite_guards(
            state.apps, schema_editor,
        )
        return
    if connection.vendor != "postgresql":
        raise RuntimeError("Records release alignment supports PostgreSQL and SQLite only.")
    q = schema_editor.quote_name
    with connection.cursor() as cursor:
        cursor.execute("SET LOCAL lock_timeout = '5s'")
        cursor.execute("LOCK TABLE records_hoso, records_loaivanban IN ACCESS EXCLUSIVE MODE")
        for table in ("records_hoso", "records_loaivanban"):
            # Convert Django identity to the release BIGSERIAL representation.
            # Preserve allocated sequence values, including gaps/deleted rows.
            cursor.execute("SELECT attidentity FROM pg_attribute WHERE attrelid=%s::regclass AND attname='id'", [table])
            identity = cursor.fetchone()[0]
            if identity:
                sequence = table + "_id_seq"
                cursor.execute("SELECT pg_get_serial_sequence(%s, 'id')", [table])
                if cursor.fetchone()[0] != "public." + sequence:
                    raise RuntimeError("Unexpected identity sequence for " + table)
                cursor.execute(f"SELECT last_value, is_called FROM {q(sequence)}")
                last, called = cursor.fetchone()
                cursor.execute(f"SELECT max(id) FROM {q(table)}")
                maximum = cursor.fetchone()[0]
                if maximum is not None and maximum >= last:
                    last, called = maximum, True
                cursor.execute(f"ALTER TABLE {q(table)} ALTER COLUMN id DROP IDENTITY")
                cursor.execute(f"CREATE SEQUENCE {q(sequence)} AS bigint OWNED BY {q(table)}.id")
                cursor.execute(f"ALTER TABLE {q(table)} ALTER COLUMN id SET DEFAULT nextval('{sequence}'::regclass)")
                cursor.execute("SELECT setval(%s::regclass, %s, %s)", [sequence, last, called])
            for column in ("created_at", "updated_at"):
                cursor.execute(f"ALTER TABLE {q(table)} ALTER COLUMN {q(column)} SET DEFAULT now()")
        cursor.execute("ALTER TABLE records_hoso ALTER COLUMN is_he_thong SET DEFAULT false")
        checks = {
            "records_hoso": {
                "records_hoso_stt_uu_tien_check": "stt_uu_tien > 0",
                "records_hoso_so_ky_hieu_check": "btrim(so_ky_hieu) <> ''",
                "records_hoso_ten_ho_so_check": "btrim(ten_ho_so) <> ''",
            },
            "records_loaivanban": {"records_loaivanban_ten_loai_check": "btrim(ten_loai) <> ''"},
        }
        legacy = {
            "records_hoso": {"ck_records_hoso_stt_positive", "ck_records_hoso_so_ky_hieu_not_blank", "ck_records_hoso_ten_ho_so_not_blank"},
            "records_loaivanban": {"ck_records_loaivanban_ten_loai_not_blank"},
        }
        for table, expected in checks.items():
            cursor.execute("SELECT conname FROM pg_constraint WHERE conrelid=%s::regclass AND contype='c'", [table])
            names = {row[0] for row in cursor.fetchall()}
            if names - set(expected) - legacy[table]:
                raise RuntimeError("Unexpected check constraints on " + table)
            for name in names:
                cursor.execute(f"ALTER TABLE {q(table)} DROP CONSTRAINT {q(name)}")
            for name, expression in expected.items():
                cursor.execute(f"ALTER TABLE {q(table)} ADD CONSTRAINT {q(name)} CHECK ({expression})")
        for table, column, destination in (
            ("records_hoso", "nguoi_lap_id", "accounts_employee"),
            ("records_loaivanban", "ho_so_id", "records_hoso"),
        ):
            cursor.execute("""SELECT conname, confrelid::regclass::text,
                ARRAY(SELECT attname FROM pg_attribute WHERE attrelid=conrelid AND attnum=ANY(conkey)),
                ARRAY(SELECT attname FROM pg_attribute WHERE attrelid=confrelid AND attnum=ANY(confkey)),
                confdeltype, condeferrable, condeferred
                FROM pg_constraint WHERE conrelid=%s::regclass AND contype='f'""", [table])
            fks = cursor.fetchall()
            if len(fks) != 1 or fks[0][1:4] != (destination, [column], ["id"]):
                raise RuntimeError("Unexpected foreign key layout on " + table)
            name = table + "_" + column + "_fkey"
            if fks[0][0] == name and fks[0][4:] == ("r", False, False):
                continue
            cursor.execute(f"ALTER TABLE {q(table)} DROP CONSTRAINT {q(fks[0][0])}")
            cursor.execute(f"ALTER TABLE {q(table)} ADD CONSTRAINT {q(name)} FOREIGN KEY ({q(column)}) REFERENCES {q(destination)} (id) ON DELETE RESTRICT")
        generated = schema_editor._create_index_name("records_hoso", ["so_ky_hieu"], suffix="_like")
        cursor.execute("SELECT indexdef FROM pg_indexes WHERE schemaname='public' AND indexname=%s", [generated])
        pattern_index = cursor.fetchone()
        if pattern_index:
            expected = f"CREATE INDEX {generated} ON public.records_hoso USING btree (so_ky_hieu varchar_pattern_ops)"
            if pattern_index[0] != expected:
                raise RuntimeError("Unexpected pattern index definition")
            cursor.execute(f"DROP INDEX {q(generated)}")
        cursor.execute("DROP INDEX uq_records_hoso_he_thong")
        cursor.execute("CREATE UNIQUE INDEX uq_records_hoso_he_thong ON records_hoso (is_he_thong) WHERE is_he_thong = true")
        # A shared function already used by other apps must not be overwritten.
        cursor.execute("SELECT prosrc FROM pg_proc WHERE oid=to_regprocedure('public.set_updated_at()')")
        shared = cursor.fetchone()
        if shared is None:
            cursor.execute(RELEASE_FUNCTIONS[0])
        else:
            import re
            compact = re.sub(r"\s+", "", shared[0]).lower()
            if compact != "beginnew.updated_at=now();returnnew;end;":
                raise RuntimeError("Existing shared set_updated_at requires owner review")
        for definition in RELEASE_FUNCTIONS[1:]:
            cursor.execute(definition)
        for table, trigger in (("records_hoso", "trg_hoso_updated_at"), ("records_loaivanban", "trg_loaivanban_updated_at")):
            cursor.execute(f"DROP TRIGGER {q(trigger)} ON {q(table)}")
            cursor.execute(f"CREATE TRIGGER {q(trigger)} BEFORE UPDATE ON {q(table)} FOR EACH ROW EXECUTE FUNCTION set_updated_at()")
        # RESTRICT refuses removal if any outside trigger depends on this old helper.
        cursor.execute("DROP FUNCTION IF EXISTS records_set_updated_at() RESTRICT")

STATE_OPERATIONS = [
    migrations.RemoveConstraint(
        model_name='hoso',
        name='ck_records_hoso_stt_positive',
    ),
    migrations.RemoveConstraint(
        model_name='hoso',
        name='ck_records_hoso_so_ky_hieu_not_blank',
    ),
    migrations.RemoveConstraint(
        model_name='hoso',
        name='ck_records_hoso_ten_ho_so_not_blank',
    ),
    migrations.RemoveConstraint(
        model_name='loaivanban',
        name='ck_records_loaivanban_ten_loai_not_blank',
    ),
    migrations.AlterField(
        model_name='hoso',
        name='created_at',
        field=models.DateTimeField(auto_now_add=True, db_default=records.models.DbNow()),
    ),
    migrations.AlterField(
        model_name='hoso',
        name='is_he_thong',
        field=models.BooleanField(db_default=False, default=False, editable=False),
    ),
    migrations.AlterField(
        model_name='hoso',
        name='stt_uu_tien',
        field=models.IntegerField(unique=True, validators=[django.core.validators.MinValueValidator(1)]),
    ),
    migrations.AlterField(
        model_name='hoso',
        name='updated_at',
        field=models.DateTimeField(auto_now=True, db_default=records.models.DbNow()),
    ),
    migrations.AlterField(
        model_name='loaivanban',
        name='created_at',
        field=models.DateTimeField(auto_now_add=True, db_default=records.models.DbNow()),
    ),
    migrations.AlterField(
        model_name='loaivanban',
        name='updated_at',
        field=models.DateTimeField(auto_now=True, db_default=records.models.DbNow()),
    ),
    migrations.AddConstraint(
        model_name='hoso',
        constraint=models.CheckConstraint(condition=models.Q(('stt_uu_tien__gt', 0)), name='records_hoso_stt_uu_tien_check'),
    ),
    migrations.AddConstraint(
        model_name='hoso',
        constraint=models.CheckConstraint(condition=django.db.models.expressions.NegatedExpression(django.db.models.lookups.Exact(django.db.models.functions.text.Trim('so_ky_hieu'), models.Value(''))), name='records_hoso_so_ky_hieu_check'),
    ),
    migrations.AddConstraint(
        model_name='hoso',
        constraint=models.CheckConstraint(condition=django.db.models.expressions.NegatedExpression(django.db.models.lookups.Exact(django.db.models.functions.text.Trim('ten_ho_so'), models.Value(''))), name='records_hoso_ten_ho_so_check'),
    ),
    migrations.AddConstraint(
        model_name='loaivanban',
        constraint=models.CheckConstraint(condition=django.db.models.expressions.NegatedExpression(django.db.models.lookups.Exact(django.db.models.functions.text.Trim('ten_loai'), models.Value(''))), name='records_loaivanban_ten_loai_check'),
    ),
]

class Migration(migrations.Migration):
    dependencies = [("records", "0005_canonical_fk_indexes"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [migrations.SeparateDatabaseAndState(
        database_operations=[migrations.RunPython(align_schema)],
        state_operations=STATE_OPERATIONS,
    )]
