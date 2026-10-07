# AI SQL document source

## Access contract

- AI document queries run through the Django `readonly` database alias. When PostgreSQL is enabled, `DB_READONLY_USER` is required and the alias sets `default_transaction_read_only=on`; it never falls back to `default`.
- The `qlvb_readonly` role receives `SELECT` only on `ai_vanbanden`, `ai_vanbandi`, and `ai_tailieu`. It does not receive access to source tables, recipient tables, or attachment tables.
- `ai_vanbanden` and `ai_vanbandi` expose only visible `NOI_BO` metadata columns. The DDL filters out `HAN_CHE`; it also omits attachment paths.
- `ai_tailieu` exposes metadata only. `TAT_CA` rows are visible to authorized users; `NOI_BO_PHONG_BAN` rows require a matching active employee unit. The host auth layer must set `request.employee_id`; the AI API copies it into a transaction-local database setting. The Django `User.pk` and request JSON are never treated as employee identity.
- The application checks `use_aiassistant` plus `view_vanbanden`, `view_vanbandi`, or `view_tailieu` by permission codename in `backend/services/ai_access.py`. The AI source does not import Group 2 or Group 7 implementation code.
- AI chat cannot read official document attachments. It indexes only metadata returned by the permitted views. Old Chroma vectors for an accessible SQL record are deleted and rebuilt as `metadata-v1` before retrieval.
- The separate AI knowledge base is for administrator-uploaded materials approved for AI use and classified as non-confidential. Do not upload confidential official documents or their attachments. Upload, delete, reclassification, file viewing, and AI settings endpoints require an administrator. These vectors are tagged `source_class=ai_knowledge_base` and remain a separate retrieval source.

## View contract

`SQL_VIEW_COLUMNS` in `backend/services/sql_document_source.py` records the view columns used by the application. `verify_sql_schema()` compares that contract with PostgreSQL `information_schema`; it reports `ok`, `mismatch`, `unavailable`, or `skipped` for non-PostgreSQL development.

The source reads only the parent views. Recipient and issuing-unit views remain ungranted to `qlvb_readonly` unless a future AI feature has an approved need for them.

## Integration requirements

1. Apply the DDL PR before enabling PostgreSQL-backed AI.
2. Django settings and AI routes are rooted at `backend/config/settings.py` and `backend/config/urls.py`; `backend/django_project/` retains compatibility imports.
3. Create `qlvb_readonly` outside the DDL and set `DB_READONLY_USER` / `DB_READONLY_PASSWORD` from deployment secrets.
4. The host authentication integration must set `request.employee_id` from the authenticated employee record. If `view_tailieu` is granted and that identity is missing, the request fails closed.
5. The permission seed must provide the codenames listed above. Cross-check with Group 2's `van_ban_xem_duoc` in tests when that contract is available; do not import it into the runtime path.

No runtime or production database was modified by this change.
