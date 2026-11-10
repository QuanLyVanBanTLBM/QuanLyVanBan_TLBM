"""Install the DDL's employee updated_at trigger when it is missing."""

from django.db import migrations


TRIGGERS = (("accounts_employee", "trg_employee_updated_at"),)


def _trigger_exists_or_validate(cursor, table, name):
    cursor.execute(
        """SELECT trigger.tgtype, trigger.tgenabled, trigger.tgnargs,
                  cardinality(trigger.tgattr::smallint[]), trigger.tgconstraint,
                  function.proname, namespace.nspname, trigger.tgqual IS NULL
           FROM pg_trigger trigger
           JOIN pg_class relation ON relation.oid = trigger.tgrelid
           JOIN pg_proc function ON function.oid = trigger.tgfoid
           JOIN pg_namespace namespace ON namespace.oid = function.pronamespace
           WHERE relation.oid = %s::regclass AND trigger.tgname = %s
             AND NOT trigger.tgisinternal""",
        [table, name],
    )
    row = cursor.fetchone()
    if row is None:
        return False
    if row != (19, "O", 0, 0, 0, "set_updated_at", "public", True):
        raise RuntimeError(f"{table}.{name}: trigger khác định nghĩa; migration không thay đổi dữ liệu.")
    return True


def install_employee_updated_at(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        raise RuntimeError("accounts 0008 requires PostgreSQL.")

    q = schema_editor.connection.ops.quote_name
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("SELECT to_regprocedure('public.set_updated_at()') IS NOT NULL")
        if not cursor.fetchone()[0]:
            raise RuntimeError("public.set_updated_at() is missing; migration made no changes.")
        present = {trigger: _trigger_exists_or_validate(cursor, *trigger) for trigger in TRIGGERS}
        for table, name in TRIGGERS:
            if not present[(table, name)]:
                cursor.execute(
                    f"CREATE TRIGGER {q(name)} BEFORE UPDATE ON {q(table)} "
                    "FOR EACH ROW EXECUTE FUNCTION set_updated_at()"
                )


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0007_normalize_system_account_password"),
        ("documents", "0009_schema_scalars"),
    ]

    operations = [migrations.RunPython(install_employee_updated_at, migrations.RunPython.noop)]
