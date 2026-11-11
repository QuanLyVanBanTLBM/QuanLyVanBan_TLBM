"""Scope AI document and attachment reads to selector-approved records."""

from django.db import migrations


FORWARD_SQL = [
    """
CREATE OR REPLACE VIEW ai_vanbanden WITH (security_barrier) AS
    SELECT vb.id, vb.so_hieu, vb.so_thu_tu, vb.nam, vb.ngay_den, vb.trich_yeu, vb.noi_ban_hanh,
           vb.ngay_van_ban, vb.nguoi_ky, vb.chuc_vu, vb.hieu_luc, vb.ngay_het_hieu_luc,
           vb.ghi_chu, vb.updated_at
    FROM documents_vanbanden vb
    WHERE (
        (vb.pham_vi = 'NOI_BO'
         AND (current_setting('qlvb.can_view_vanbanden', true) = 'on'
              OR vb.nguoi_tao_id = NULLIF(current_setting('qlvb.employee_id', true), '')::bigint))
        OR (vb.pham_vi = 'HAN_CHE' AND (
            vb.nguoi_tao_id = NULLIF(current_setting('qlvb.employee_id', true), '')::bigint
            OR EXISTS (
                SELECT 1 FROM documents_vanbanden_nguoinhan nn
                WHERE nn.vanbanden_id = vb.id
                  AND nn.employee_id = NULLIF(current_setting('qlvb.employee_id', true), '')::bigint
            )
            OR (NOT EXISTS (
                SELECT 1 FROM documents_vanbanden_nguoinhan nn
                WHERE nn.vanbanden_id = vb.id
            ) AND EXISTS (
                SELECT 1 FROM documents_vanbanden_donvinhan dv
                JOIN accounts_employee e ON e.don_vi_id = dv.donvi_id
                WHERE dv.vanbanden_id = vb.id
                  AND e.id = NULLIF(current_setting('qlvb.employee_id', true), '')::bigint
            ))
        ) OR (vb.hieu_luc::text NOT IN ('CON_HIEU_LUC', 'CON_HIEU_LUC_1_PHAN')
              AND current_setting('qlvb.can_view_expired_vanbanden', true) = 'on'))
    ) AND (
        vb.hieu_luc::text IN ('CON_HIEU_LUC', 'CON_HIEU_LUC_1_PHAN')
        OR current_setting('qlvb.can_view_expired_vanbanden', true) = 'on'
    );
    """,
    """
CREATE OR REPLACE VIEW ai_vanbandi WITH (security_barrier) AS
    SELECT vb.id, vb.so_hieu, vb.so_thu_tu, vb.nam, vb.ngay_ban_hanh,
           vb.trich_yeu,
           (
               SELECT string_agg(dv.ten, ', ' ORDER BY dv.ten)
               FROM documents_vanbandi_noibanhanh nb
               JOIN organizations_donvi dv ON dv.id = nb.donvi_id
               WHERE nb.vanbandi_id = vb.id
           ) AS noi_ban_hanh,
           vb.ngay_van_ban, vb.nguoi_ky, vb.chuc_vu, vb.hieu_luc,
           vb.ngay_het_hieu_luc, vb.ghi_chu, vb.updated_at
    FROM documents_vanbandi vb
    WHERE (
        (vb.pham_vi = 'NOI_BO'
         AND (current_setting('qlvb.can_view_vanbandi', true) = 'on'
              OR vb.nguoi_tao_id = NULLIF(current_setting('qlvb.employee_id', true), '')::bigint))
        OR (vb.pham_vi = 'HAN_CHE' AND (
            vb.nguoi_tao_id = NULLIF(current_setting('qlvb.employee_id', true), '')::bigint
            OR EXISTS (
                SELECT 1 FROM documents_vanbandi_nguoinhan nn
                WHERE nn.vanbandi_id = vb.id
                  AND nn.employee_id = NULLIF(current_setting('qlvb.employee_id', true), '')::bigint
            )
            OR (NOT EXISTS (
                SELECT 1 FROM documents_vanbandi_nguoinhan nn
                WHERE nn.vanbandi_id = vb.id
            ) AND EXISTS (
                SELECT 1 FROM documents_vanbandi_donvinhan dv
                JOIN accounts_employee e ON e.don_vi_id = dv.donvi_id
                WHERE dv.vanbandi_id = vb.id
                  AND e.id = NULLIF(current_setting('qlvb.employee_id', true), '')::bigint
            ))
        ) OR (vb.hieu_luc::text NOT IN ('CON_HIEU_LUC', 'CON_HIEU_LUC_1_PHAN')
              AND current_setting('qlvb.can_view_expired_vanbandi', true) = 'on'))
    ) AND (
        vb.hieu_luc::text IN ('CON_HIEU_LUC', 'CON_HIEU_LUC_1_PHAN')
        OR current_setting('qlvb.can_view_expired_vanbandi', true) = 'on'
    );
    """,
    """
CREATE OR REPLACE VIEW ai_vanbanden_attachment WITH (security_barrier) AS
    SELECT a.id, a.document_id, a.name, a.path
    FROM documents_vanbanden_attachment a
    JOIN ai_vanbanden vb ON vb.id = a.document_id
    WHERE a.is_deleted IS FALSE;
    """,
    """
CREATE OR REPLACE VIEW ai_vanbandi_attachment WITH (security_barrier) AS
    SELECT a.id, a.document_id, a.name, a.path
    FROM documents_vanbandi_attachment a
    JOIN ai_vanbandi vb ON vb.id = a.document_id
    WHERE a.is_deleted IS FALSE;
    """,
    """
    DO $$
    DECLARE
        target_relation record;
        remaining_select_count integer;
    BEGIN
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'qlvb_readonly') THEN
            -- Collapse prior direct and default SELECT grants back to the view-only contract.
            FOR target_relation IN
                SELECT n.nspname, c.relname
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = 'public'
                  AND c.relkind IN ('r', 'p', 'v', 'm', 'f')
                  AND c.relowner = current_user::regrole
            LOOP
                EXECUTE format(
                    'REVOKE SELECT ON TABLE %I.%I FROM qlvb_readonly',
                    target_relation.nspname,
                    target_relation.relname
                );
            END LOOP;
            REVOKE SELECT ON
                ai_vanbanden_nguoinhan,
                ai_vanbanden_donvinhan,
                ai_vanbandi_noibanhanh,
                ai_vanbandi_nguoinhan,
                ai_vanbandi_donvinhan
                FROM qlvb_readonly;

            -- Only change defaults created by the current migration owner.
            ALTER DEFAULT PRIVILEGES IN SCHEMA public
                REVOKE SELECT ON TABLES FROM qlvb_readonly;

            -- Grants inherited from PUBLIC or another role/owner need an external ACL fix.
            SELECT COUNT(*) INTO remaining_select_count
            FROM pg_class rel
            JOIN pg_namespace n ON n.oid = rel.relnamespace
            WHERE n.nspname = 'public'
              AND rel.relkind IN ('r', 'p', 'v', 'm', 'f')
              AND rel.relname NOT IN ('ai_vanbanden', 'ai_vanbandi', 'ai_tailieu', 'ai_vanbanden_attachment', 'ai_vanbandi_attachment')
              AND (
                  has_table_privilege('qlvb_readonly', rel.oid, 'SELECT')
                  OR has_any_column_privilege('qlvb_readonly', rel.oid, 'SELECT')
              );
            IF remaining_select_count > 0 THEN
                RAISE EXCEPTION
                    'Role qlvb_readonly retains SELECT on % public relation(s) outside the five approved AI views; resolve external grants or memberships before retrying.',
                    remaining_select_count;
            END IF;

            GRANT SELECT ON
                ai_vanbanden,
                ai_vanbandi,
                ai_tailieu,
                ai_vanbanden_attachment,
                ai_vanbandi_attachment
                TO qlvb_readonly;
        ELSE
            RAISE NOTICE 'Role qlvb_readonly chưa tồn tại: bỏ qua cấp quyền chỉ đọc cho trợ lý AI';
        END IF;
    END
    $$
    """,
]


class Migration(migrations.Migration):
    atomic = True

    dependencies = [
        ("documents", "0013_cho_admin_xoa_van_ban_han_che"),
    ]

    operations = [
        migrations.RunSQL(sql=FORWARD_SQL, reverse_sql=migrations.RunSQL.noop),
    ]
