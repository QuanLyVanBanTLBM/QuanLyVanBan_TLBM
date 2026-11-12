# AI SQL document source

## Access contract

- AI document queries run through the Django `readonly` database alias. When PostgreSQL is enabled, `DB_READONLY_USER` is required and the alias sets `default_transaction_read_only=on`; it never falls back to `default`.
- The `qlvb_readonly` role receives `SELECT` only on the three source views and two employee-scoped attachment views. It does not receive access to source tables, recipient tables, or attachment tables.
- The application asks `documents.selectors.van_ban_xem_duoc` for the logged-in user's allowed document IDs, then applies those IDs to every read from the read-only views. The authenticated employee ID and expired-document permissions are transaction-local settings; the SQL views provide an additional creator, recipient, department, and expiration filter. Attachment queries are restricted to the same selector-approved IDs and expose only non-deleted files.
- `ai_tailieu` exposes metadata only. `TAT_CA` rows are visible to authorized users; `NOI_BO_PHONG_BAN` rows require a matching active employee unit. The host auth layer must set `request.employee_id`; the AI API copies it into a transaction-local database setting. The Django `User.pk` and request JSON are never treated as employee identity.
- The application checks `use_aiassistant` plus `view_tailieu` by permission codename in `backend/services/ai_access.py`; document permissions use the owning Documents selector. It calls the document module's expired-document permission selector and does not trust request-supplied employee IDs.
- AI chat indexes metadata and supported text from current PDF, DOC, DOCX, JPG, JPEG, and PNG attachments returned by the employee-scoped views. DOC extraction supports unencrypted Word 97–2003 text; images and embedded objects in DOC files are not extracted. PostgreSQL vector results are filtered by the current request's authorized document keys; removed or changed files cause stale vectors to be replaced before retrieval. On POSIX file storage, an in-process bounded hash cache reuses hashes only while file identity, size, modification time, and change time remain unchanged.
- The separate AI knowledge base is for administrator-uploaded materials approved for AI use and classified as non-confidential. Do not upload confidential official documents or their attachments. Upload, delete, reclassification, file viewing, and AI settings endpoints require an administrator. These vectors are tagged `source_class=ai_knowledge_base` and remain a separate retrieval source.

## View contract

`SQL_VIEW_COLUMNS` in `backend/services/sql_document_source.py` records the view columns used by the application. `verify_sql_schema()` compares that contract with PostgreSQL `information_schema`; it reports `ok`, `mismatch`, `unavailable`, or `skipped` for non-PostgreSQL development.

The source reads the three content views and two filtered attachment views. Recipient, issuing-unit, and issuing-authority views remain ungranted to `qlvb_readonly` unless a future AI feature has an approved need for them.

## Integration requirements

1. Apply the DDL PR before enabling PostgreSQL-backed AI.
2. Django settings and AI routes are rooted at `backend/config/settings.py` and `backend/config/urls.py`; the former `backend/django_project/` package has been removed.
3. Create `qlvb_readonly` outside the DDL and set `DB_READONLY_USER` / `DB_READONLY_PASSWORD` from deployment secrets.
4. The host authentication integration should set `request.employee_id` from the authenticated employee record. The AI API resolves a trusted active employee mapping when absent and never uses the Django `User.pk` or request JSON as employee identity. `view_tailieu` remains denied without a trusted employee mapping.
5. The permission seed must provide the codenames listed above. `documents.selectors.van_ban_xem_duoc` is the runtime authority for document IDs; AI must not duplicate that policy.

No runtime or production database was modified by this change.
