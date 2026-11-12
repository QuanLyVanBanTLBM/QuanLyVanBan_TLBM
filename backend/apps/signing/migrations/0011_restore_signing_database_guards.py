"""Install the signing evidence guards from the canonical release DDL.

The SQL is intentionally fixed in this migration. It must not read the mutable
release_DDL.sql file at runtime.
"""

from django.db import migrations


FUNCTIONS = (
    """CREATE OR REPLACE FUNCTION prevent_delete_or_tamper_signing_signature()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'Bảo toàn bằng chứng pháp lý: Chữ ký số điện tử (signing_signature id=%) là bất biến và không thể xóa khỏi CSDL.', OLD.id;
    ELSIF TG_OP = 'UPDATE' THEN
        IF (to_jsonb(OLD) - 'trang_thai_xac_minh' - 'thoi_diem_xac_minh')
           IS DISTINCT FROM
           (to_jsonb(NEW) - 'trang_thai_xac_minh' - 'thoi_diem_xac_minh') THEN
            RAISE EXCEPTION 'Bảo toàn bằng chứng pháp lý: Không được phép sửa đổi thông tin cốt lõi của chữ ký số (signing_signature id=%). Chỉ cho phép cập nhật kết quả xác minh.', OLD.id;
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;""",
    """CREATE OR REPLACE FUNCTION protect_final_manifest()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        IF OLD.trang_thai IN ('DA_CHOT', 'CHOT', 'FINAL') THEN
            RAISE EXCEPTION 'Bảo toàn bằng chứng pháp lý: Không thể xóa manifest số đã chốt (signing_manifest id=%, phien_ban=%).', OLD.id, OLD.phien_ban_bang_chung;
        END IF;
        RETURN OLD;
    ELSIF TG_OP = 'UPDATE' THEN
        IF OLD.trang_thai IN ('DA_CHOT', 'CHOT', 'FINAL') THEN
            RAISE EXCEPTION 'Bảo toàn bằng chứng pháp lý: Manifest số đã chốt (DA_CHOT) là bất biến và không thể sửa đổi (signing_manifest id=%).', OLD.id;
        END IF;
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql;""",
    """CREATE OR REPLACE FUNCTION prevent_delete_signing_attempt()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.trang_thai <> 'NHAP' THEN
        RAISE EXCEPTION 'Bảo toàn bằng chứng pháp lý: Không thể xóa lượt trình ký (signing_attempt id=%) đã kích hoạt (trạng thái: %).', OLD.id, OLD.trang_thai;
    END IF;
    IF EXISTS (SELECT 1 FROM signing_manifest WHERE luot_trinh_id = OLD.id) THEN
        RAISE EXCEPTION 'Bảo toàn bằng chứng pháp lý: Lượt trình ký (id=%) đã có manifest số, không thể xóa.', OLD.id;
    END IF;
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;""",
    """CREATE OR REPLACE FUNCTION prevent_modify_signing_audit_log()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Bảo toàn bằng chứng pháp lý: Nhật ký kiểm toán (signing_audit_log id=%) tuân thủ chuẩn WORM, nghiêm cấm mọi hành vi sửa đổi hoặc xóa.', OLD.id;
END;
$$ LANGUAGE plpgsql;""",
)


TRIGGERS = (
    (
        "signing_signature",
        "trg_signing_signature_immutable",
        "prevent_delete_or_tamper_signing_signature",
        27,
        "CREATE TRIGGER trg_signing_signature_immutable BEFORE UPDATE OR DELETE ON signing_signature "
        "FOR EACH ROW EXECUTE FUNCTION prevent_delete_or_tamper_signing_signature()",
    ),
    (
        "signing_manifest",
        "trg_signing_manifest_protect",
        "protect_final_manifest",
        27,
        "CREATE TRIGGER trg_signing_manifest_protect BEFORE UPDATE OR DELETE ON signing_manifest "
        "FOR EACH ROW EXECUTE FUNCTION protect_final_manifest()",
    ),
    (
        "signing_attempt",
        "trg_signing_attempt_prevent_delete",
        "prevent_delete_signing_attempt",
        11,
        "CREATE TRIGGER trg_signing_attempt_prevent_delete BEFORE DELETE ON signing_attempt "
        "FOR EACH ROW EXECUTE FUNCTION prevent_delete_signing_attempt()",
    ),
    (
        "signing_audit_log",
        "trg_signing_audit_log_immutable",
        "prevent_modify_signing_audit_log",
        27,
        "CREATE TRIGGER trg_signing_audit_log_immutable BEFORE UPDATE OR DELETE ON signing_audit_log "
        "FOR EACH ROW EXECUTE FUNCTION prevent_modify_signing_audit_log()",
    ),
)


def install_signing_guards(apps, schema_editor):
    connection = schema_editor.connection
    if connection.vendor != "postgresql":
        return

    with connection.cursor() as cursor:
        for statement in FUNCTIONS:
            cursor.execute(statement, params=None)

        for table, trigger_name, function_name, trigger_type, create_sql in TRIGGERS:
            cursor.execute(
                "SELECT trigger.tgtype, trigger.tgenabled, routine.proname, "
                "routine.pronamespace = current_schema()::regnamespace "
                "FROM pg_catalog.pg_trigger AS trigger "
                "JOIN pg_catalog.pg_proc AS routine ON routine.oid = trigger.tgfoid "
                "WHERE trigger.tgrelid = to_regclass(%s) AND trigger.tgname = %s "
                "AND NOT trigger.tgisinternal",
                [table, trigger_name],
            )
            current = cursor.fetchone()
            if current is None:
                schema_editor.execute(create_sql)
                continue

            current_type, enabled, current_function, current_schema = current
            if current_type != trigger_type or current_function != function_name or not current_schema:
                quote = connection.ops.quote_name
                schema_editor.execute(
                    f"DROP TRIGGER {quote(trigger_name)} ON {quote(table)}"
                )
                schema_editor.execute(create_sql)
            elif enabled != "O":
                quote = connection.ops.quote_name
                schema_editor.execute(
                    f"ALTER TABLE {quote(table)} ENABLE TRIGGER {quote(trigger_name)}"
                )


class Migration(migrations.Migration):
    dependencies = [
        ("signing", "0010_khoa_ngoai_don_vi_chuc_vu"),
    ]

    operations = [
        migrations.RunPython(install_signing_guards, migrations.RunPython.noop),
    ]
