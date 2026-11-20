"""Align AI resource views with validity/assignment scoping and add pg_trgm search index."""

from django.db import migrations


FORWARD_SQL = [
    """
CREATE OR REPLACE VIEW ai_tailieu WITH (security_barrier) AS
    SELECT t.id, t.ky_hieu, t.tieu_de, t.ngay_dang, t.noi_ban_hanh,
           t.hieu_luc, t.ngay_het_hieu_luc, t.ghi_chu, t.updated_at
    FROM records_chitiettailieu t
    WHERE (
        t.hien_thi::text = 'TAT_CA'
        OR EXISTS (
            SELECT 1
            FROM accounts_employee e
            WHERE e.id = NULLIF(current_setting('qlvb.employee_id', true), '')::bigint
              AND e.is_active IS TRUE
              AND e.trang_thai::text = 'LAM_VIEC'
              AND (
                  t.nguoi_tao_id = e.id
                  OR (
                      t.hien_thi::text = 'NOI_BO_PHONG_BAN'
                      AND (
                          t.don_vi_id = e.don_vi_id
                          OR EXISTS (
                              SELECT 1
                              FROM accounts_employee_assignment a
                              WHERE a.employee_id = e.id
                                AND a.don_vi_id = t.don_vi_id
                          )
                      )
                  )
              )
        )
    ) AND (
        t.hieu_luc::text IN ('CON_HIEU_LUC', 'CON_HIEU_LUC_1_PHAN')
        OR current_setting('qlvb.can_view_expired_tailieu', true) = 'on'
    );
    """,
    """
CREATE OR REPLACE VIEW ai_tailieu_attachment WITH (security_barrier) AS
    SELECT a.id, a.document_id, a.name, a.path
    FROM records_chitiettailieu_attachment a
    JOIN ai_tailieu t ON t.id = a.document_id
    WHERE a.is_deleted IS FALSE;
    """,
    """
CREATE EXTENSION IF NOT EXISTS pg_trgm;
    """,
    """
CREATE INDEX IF NOT EXISTS ai_document_embedding_search_trgm_idx ON ai_document_embedding
    USING gin ((
        translate(
            lower(
                coalesce(content_text, '') || ' ' ||
                coalesce(metadata ->> 'parent_context', '') || ' ' ||
                coalesce(metadata ->> 'contextual_prefix', '') || ' ' ||
                coalesce(metadata ->> 'doc_code', '') || ' ' ||
                coalesce(metadata ->> 'file_name', '') || ' ' ||
                coalesce(metadata ->> 'attachment_name', '')
            ),
            'áàảãạăắằẳẵặâấầẩẫậđéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵ',
            'aaaaaaaaaaaaaaaaadeeeeeeeeeeeiiiiiooooooooooooooooouuuuuuuuuuuyyyyy'
        )
    ) gin_trgm_ops);
    """,
    """
    DO $$
    DECLARE
        target_relation record;
        remaining_select_count integer;
    BEGIN
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'qlvb_readonly') THEN
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

            ALTER DEFAULT PRIVILEGES IN SCHEMA public
                REVOKE SELECT ON TABLES FROM qlvb_readonly;

            SELECT COUNT(*) INTO remaining_select_count
            FROM pg_class rel
            JOIN pg_namespace n ON n.oid = rel.relnamespace
            WHERE n.nspname = 'public'
              AND rel.relkind IN ('r', 'p', 'v', 'm', 'f')
              AND rel.relname NOT IN (
                  'ai_vanbanden',
                  'ai_vanbandi',
                  'ai_tailieu',
                  'ai_vanbanden_attachment',
                  'ai_vanbandi_attachment',
                  'ai_tailieu_attachment',
                  'ai_document_embedding'
              )
              AND (
                  has_table_privilege('qlvb_readonly', rel.oid, 'SELECT')
                  OR has_any_column_privilege('qlvb_readonly', rel.oid, 'SELECT')
              );
            IF remaining_select_count > 0 THEN
                RAISE EXCEPTION
                    'Role qlvb_readonly retains SELECT on % public relation(s) outside the approved AI relations; resolve external grants or memberships before retrying.',
                    remaining_select_count;
            END IF;

            GRANT SELECT ON
                ai_vanbanden,
                ai_vanbandi,
                ai_tailieu,
                ai_vanbanden_attachment,
                ai_vanbandi_attachment,
                ai_tailieu_attachment,
                ai_document_embedding
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
        ("documents", "0015_ai_document_embedding_pgvector"),
        ("accounts", "0010_employeeassignment"),
    ]

    operations = [
        migrations.RunSQL(sql=FORWARD_SQL, reverse_sql=migrations.RunSQL.noop),
    ]
