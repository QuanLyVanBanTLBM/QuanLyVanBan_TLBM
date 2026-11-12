"""Hàm và trigger của records_hoso / records_loaivanban, chép nguyên văn từ release_DDL.sql.

Chỉ áp dụng trên PostgreSQL. Bộ so schema (compare_schema_ddl.py) so nguyên văn pg_get_functiondef và
pg_get_triggerdef nên không được định dạng lại các câu lệnh dưới đây. set_updated_at() dùng chung với các
bảng khác trong DDL, do đó CREATE OR REPLACE và reverse không xóa hàm này.
"""
from django.db import migrations

FORWARD_SQL = [
    r"""CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
NEW.updated_at = now();
RETURN NEW;
END;

$$
LANGUAGE plpgsql;""",
    r"""CREATE TRIGGER trg_hoso_updated_at BEFORE UPDATE ON records_hoso
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();""",
    r"""CREATE TRIGGER trg_loaivanban_updated_at BEFORE UPDATE ON records_loaivanban
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();""",
    r"""CREATE OR REPLACE FUNCTION auto_stt_uu_tien_hoso()
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
    r"""CREATE TRIGGER trg_hoso_auto_stt BEFORE INSERT ON records_hoso
  FOR EACH ROW EXECUTE FUNCTION auto_stt_uu_tien_hoso();""",
    r"""CREATE OR REPLACE FUNCTION prevent_delete_he_thong_hoso()
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
    r"""CREATE TRIGGER trg_hoso_prevent_delete BEFORE DELETE ON records_hoso
  FOR EACH ROW EXECUTE FUNCTION prevent_delete_he_thong_hoso();""",
    r"""CREATE OR REPLACE FUNCTION prevent_update_he_thong_hoso()
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
    r"""CREATE TRIGGER trg_hoso_prevent_update_he_thong BEFORE UPDATE ON records_hoso
  FOR EACH ROW EXECUTE FUNCTION prevent_update_he_thong_hoso();""",
]

REVERSE_SQL = [
    "DROP TRIGGER IF EXISTS trg_hoso_prevent_update_he_thong ON records_hoso",
    "DROP TRIGGER IF EXISTS trg_hoso_prevent_delete ON records_hoso",
    "DROP TRIGGER IF EXISTS trg_hoso_auto_stt ON records_hoso",
    "DROP TRIGGER IF EXISTS trg_loaivanban_updated_at ON records_loaivanban",
    "DROP TRIGGER IF EXISTS trg_hoso_updated_at ON records_hoso",
    "DROP FUNCTION IF EXISTS prevent_update_he_thong_hoso()",
    "DROP FUNCTION IF EXISTS prevent_delete_he_thong_hoso()",
    "DROP FUNCTION IF EXISTS auto_stt_uu_tien_hoso()",
]


def run(statements):
    def apply(apps, schema_editor):
        if schema_editor.connection.vendor != "postgresql":
            return
        for statement in statements:
            # params=None: thân hàm chứa ký tự % (RAISE EXCEPTION ... %) không được nội suy tham số.
            schema_editor.execute(statement, params=None)

    return apply


class Migration(migrations.Migration):
    dependencies = [("records", "0001_initial")]
    operations = [migrations.RunPython(run(FORWARD_SQL), run(REVERSE_SQL))]
