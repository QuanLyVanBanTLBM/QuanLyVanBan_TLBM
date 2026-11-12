"""Create the canonical AI metadata views after source-table scalar migrations."""

from django.db import migrations


FORWARD_SQL = [
    """
    CREATE OR REPLACE VIEW ai_vanbanden WITH (security_barrier) AS
        SELECT id, so_hieu, so_thu_tu, nam, ngay_den, trich_yeu, noi_ban_hanh,
               ngay_van_ban, nguoi_ky, chuc_vu, hieu_luc, ngay_het_hieu_luc,
               ghi_chu, updated_at
        FROM documents_vanbanden
        WHERE pham_vi = 'NOI_BO' AND hien_thi IS TRUE
    """,
    """
    CREATE OR REPLACE VIEW ai_vanbanden_nguoinhan WITH (security_barrier) AS
        SELECT nn.vanbanden_id, nn.employee_id
        FROM documents_vanbanden_nguoinhan nn
        JOIN documents_vanbanden vb ON vb.id = nn.vanbanden_id
        WHERE vb.pham_vi = 'NOI_BO' AND vb.hien_thi IS TRUE
    """,
    """
    CREATE OR REPLACE VIEW ai_vanbanden_donvinhan WITH (security_barrier) AS
        SELECT dv.vanbanden_id, dv.donvi_id
        FROM documents_vanbanden_donvinhan dv
        JOIN documents_vanbanden vb ON vb.id = dv.vanbanden_id
        WHERE vb.pham_vi = 'NOI_BO' AND vb.hien_thi IS TRUE
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
        WHERE vb.pham_vi = 'NOI_BO' AND vb.hien_thi IS TRUE
    """,
    """
    CREATE OR REPLACE VIEW ai_vanbandi_noibanhanh WITH (security_barrier) AS
        SELECT nb.vanbandi_id, nb.donvi_id
        FROM documents_vanbandi_noibanhanh nb
        JOIN documents_vanbandi vb ON vb.id = nb.vanbandi_id
        WHERE vb.pham_vi = 'NOI_BO' AND vb.hien_thi IS TRUE
    """,
    """
    CREATE OR REPLACE VIEW ai_vanbandi_nguoinhan WITH (security_barrier) AS
        SELECT nn.vanbandi_id, nn.employee_id
        FROM documents_vanbandi_nguoinhan nn
        JOIN documents_vanbandi vb ON vb.id = nn.vanbandi_id
        WHERE vb.pham_vi = 'NOI_BO' AND vb.hien_thi IS TRUE
    """,
    """
    CREATE OR REPLACE VIEW ai_vanbandi_donvinhan WITH (security_barrier) AS
        SELECT dv.vanbandi_id, dv.donvi_id
        FROM documents_vanbandi_donvinhan dv
        JOIN documents_vanbandi vb ON vb.id = dv.vanbandi_id
        WHERE vb.pham_vi = 'NOI_BO' AND vb.hien_thi IS TRUE
    """,
    """
    CREATE OR REPLACE VIEW ai_tailieu WITH (security_barrier) AS
        SELECT t.id, t.ky_hieu, t.tieu_de, t.ngay_dang, t.noi_ban_hanh,
               t.hieu_luc, t.ngay_het_hieu_luc, t.ghi_chu, t.updated_at
        FROM records_chitiettailieu t
        WHERE t.hien_thi::text = 'TAT_CA'
           OR (
               t.hien_thi::text = 'NOI_BO_PHONG_BAN'
               AND t.don_vi_id = (
                   SELECT e.don_vi_id
                   FROM accounts_employee e
                   WHERE e.id = NULLIF(current_setting('qlvb.employee_id', true), '')::bigint
                     AND e.is_active IS TRUE
                     AND e.trang_thai::text = 'LAM_VIEC'
               )
           )
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
              AND rel.relname NOT IN ('ai_vanbanden', 'ai_vanbandi', 'ai_tailieu')
              AND (
                  has_table_privilege('qlvb_readonly', rel.oid, 'SELECT')
                  OR has_any_column_privilege('qlvb_readonly', rel.oid, 'SELECT')
              );
            IF remaining_select_count > 0 THEN
                RAISE EXCEPTION
                    'Role qlvb_readonly retains SELECT on % public relation(s) outside the three approved AI views; resolve external grants or memberships before retrying.',
                    remaining_select_count;
            END IF;

            GRANT SELECT ON
                ai_vanbanden,
                ai_vanbandi,
                ai_tailieu
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
        ("documents", "0009_schema_scalars"),
        ("document_templates", "0004_schema_scalars"),
    ]

    operations = [
        # These canonical views may predate migration history on an adopted DDL database.
        # Keep them on rollback rather than dropping objects the migration did not create.
        migrations.RunSQL(sql=FORWARD_SQL, reverse_sql=migrations.RunSQL.noop),
    ]
