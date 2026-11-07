"""Cho phép Quản trị viên xóa văn bản hạn chế (release_DDL.sql [XVHC]).

Trigger prevent_delete_van_ban_han_che trước đây chặn mọi lệnh xóa văn bản HAN_CHE. Từ nay chỉ chặn khi phiên làm việc
không đặt app.allow_delete_han_che = 'on'; ứng dụng đặt biến này (SET LOCAL, trong cùng giao dịch) khi Quản trị viên xóa.
Lệnh DELETE chạy trực tiếp trong SQL vẫn bị chặn. Reverse trả về hàm cũ chặn mọi lệnh xóa.
"""
from django.db import migrations

NEW_BODY = """
BEGIN
    IF OLD.pham_vi = 'HAN_CHE' AND COALESCE(current_setting('app.allow_delete_han_che', true), '') <> 'on' THEN
        RAISE EXCEPTION 'Văn bản hạn chế (id=%) không được xóa.', OLD.id;
    END IF;
    RETURN OLD;
END;
"""

OLD_BODY = """
BEGIN
    IF OLD.pham_vi = 'HAN_CHE' THEN
        RAISE EXCEPTION 'Văn bản hạn chế (id=%) không được xóa.', OLD.id;
    END IF;
    RETURN OLD;
END;
"""


def _install(body):
    def run(apps, schema_editor):
        with schema_editor.connection.cursor() as cursor:
            cursor.execute(
                "CREATE OR REPLACE FUNCTION prevent_delete_van_ban_han_che() RETURNS TRIGGER "
                "LANGUAGE plpgsql VOLATILE CALLED ON NULL INPUT SECURITY INVOKER "
                f"PARALLEL UNSAFE COST 100 AS $${body}$$;",
                params=None,
            )

    return run


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0012_tep_dinh_kem_kho_dung_chung"),
    ]

    operations = [
        migrations.RunPython(_install(NEW_BODY), _install(OLD_BODY)),
    ]
