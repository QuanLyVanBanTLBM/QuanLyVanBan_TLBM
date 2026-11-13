"""Read AI document metadata through the dedicated PostgreSQL role and views."""

from django.db import connection, connections, transaction

from backend.services.ai_access import has_permission_codename
from documents.selectors import co_quyen_xem_het_hieu_luc, van_ban_xem_duoc


DOCUMENT_VIEWS = {
    "vanbanden": "ai_vanbanden",
    "vanbandi": "ai_vanbandi",
}
READONLY_ROLE = "qlvb_readonly"
SQL_VIEW_COLUMNS = {
    "ai_vanbanden": {
        "id", "so_hieu", "so_thu_tu", "nam", "ngay_den", "trich_yeu",
        "noi_ban_hanh", "ngay_van_ban", "nguoi_ky", "chuc_vu", "hieu_luc",
        "ngay_het_hieu_luc", "ghi_chu", "updated_at",
    },
    "ai_vanbandi": {
        "id", "so_hieu", "so_thu_tu", "nam", "ngay_ban_hanh", "trich_yeu",
        "noi_ban_hanh", "ngay_van_ban", "nguoi_ky", "chuc_vu", "hieu_luc",
        "ngay_het_hieu_luc", "ghi_chu", "updated_at",
    },
    "ai_tailieu": {
        "id", "ky_hieu", "tieu_de", "ngay_dang", "noi_ban_hanh", "hieu_luc",
        "ngay_het_hieu_luc", "ghi_chu", "updated_at",
    },
    "ai_vanbanden_attachment": {"id", "document_id", "name", "path"},
    "ai_vanbandi_attachment": {"id", "document_id", "name", "path"},
}


class SqlDocumentAccessError(Exception):
    """The SQL document source cannot safely serve this chat request.

    ``ai_reason`` is a stable code written to the AI trace log to localize the failing branch.
    """

    def __init__(self, message, ai_reason="sql_access_error"):
        super().__init__(message)
        self.ai_reason = ai_reason


def is_postgres_source():
    return connection.vendor == "postgresql"


def verify_sql_schema():
    """Compare the deployed AI view contract with the columns used by this source."""
    if not is_postgres_source():
        return {"status": "skipped", "checked_views": 0, "missing_views": [], "missing_columns": {}}
    if "readonly" not in connections.databases:
        return {
            "status": "mismatch",
            "checked_views": len(SQL_VIEW_COLUMNS),
            "missing_views": list(SQL_VIEW_COLUMNS),
            "missing_columns": {},
        }

    try:
        with connections["readonly"].cursor() as cursor:
            _assert_readonly_connection(cursor)
            cursor.execute(
                """
                SELECT table_name, column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = ANY(%s)
                """,
                [list(SQL_VIEW_COLUMNS)],
            )
            present = {}
            for table_name, column_name in cursor.fetchall():
                present.setdefault(table_name, set()).add(column_name)
    except Exception as error:
        return {
            "status": "unavailable",
            "checked_views": len(SQL_VIEW_COLUMNS),
            "missing_views": [],
            "missing_columns": {},
            "error": str(error),
        }

    missing_views = sorted(set(SQL_VIEW_COLUMNS) - set(present))
    missing_columns = {
        view: sorted(columns - present.get(view, set()))
        for view, columns in SQL_VIEW_COLUMNS.items()
        if view in present and columns - present[view]
    }
    return {
        "status": "ok" if not missing_views and not missing_columns else "mismatch",
        "checked_views": len(SQL_VIEW_COLUMNS),
        "missing_views": missing_views,
        "missing_columns": missing_columns,
    }


def _dict_rows(cursor):
    columns = [item[0] for item in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def _assert_readonly_connection(cursor):
    cursor.execute(
        """
        SELECT current_user,
               current_setting('transaction_read_only') = 'on',
               role.rolsuper,
               EXISTS (
                   SELECT 1 FROM pg_class relation
                   JOIN pg_namespace namespace ON namespace.oid = relation.relnamespace
                   WHERE namespace.nspname = 'public'
                     AND relation.relkind IN ('r', 'p', 'f')
                     AND relation.relname <> 'ai_document_embedding'
                     AND has_table_privilege(current_user, relation.oid, 'SELECT')
               )
        FROM pg_roles role
        WHERE role.rolname = current_user
        """
    )
    row = cursor.fetchone()
    if not row or row[0] != READONLY_ROLE or row[1] is not True or row[2] is not False or row[3] is not False:
        raise SqlDocumentAccessError(
            "Kết nối AI không dùng đúng role chỉ đọc qlvb_readonly hoặc role đang có quyền đọc bảng gốc.",
            ai_reason="readonly_role_mismatch",
        )


def _employee_id_value(employee_id):
    try:
        value = int(employee_id)
    except (TypeError, ValueError):
        reason = "employee_unresolved" if employee_id is None else "employee_id_invalid"
        raise SqlDocumentAccessError(
            "Không xác định được mã nhân viên từ phiên đăng nhập QLVB.", ai_reason=reason
        )
    if value <= 0:
        raise SqlDocumentAccessError(
            "Mã nhân viên từ phiên đăng nhập QLVB không hợp lệ.", ai_reason="employee_id_invalid"
        )
    return value


def accessible_document_keys(user, employee_id=None) -> set[str]:
    """Return ``<source_type>:<source_id>`` keys admitted by ``ai_*`` views and user permissions.

    Optimized for the chat hot path: fetches only integer IDs in a single query without loading
    document text columns or attachment tables.
    """
    if not is_postgres_source():
        return set()
    if not has_permission_codename(user, "use_aiassistant"):
        raise SqlDocumentAccessError(
            "Tài khoản chưa được cấp quyền sử dụng trợ lý AI.", ai_reason="no_ai_permission"
        )

    document_ids = {
        "vanbanden": list(
            van_ban_xem_duoc(user, "DEN").values_list("pk", flat=True)
        ),
        "vanbandi": list(
            van_ban_xem_duoc(user, "DI").values_list("pk", flat=True)
        ),
    }
    can_read_tailieu = has_permission_codename(user, "view_tailieu")
    employee_id = _employee_id_value(employee_id)
    if "readonly" not in connections.databases:
        raise SqlDocumentAccessError(
            "Thiếu cấu hình kết nối CSDL chỉ đọc cho AI.", ai_reason="readonly_alias_missing"
        )

    allowed_keys: set[str] = set()
    try:
        with transaction.atomic(using="readonly"):
            readonly = connections["readonly"]
            with readonly.cursor() as cursor:
                _assert_readonly_connection(cursor)
            with readonly.cursor() as cursor:
                cursor.execute(
                    "SELECT set_config('qlvb.employee_id', %s, true)",
                    [str(employee_id or "")],
                )
                for source_type in DOCUMENT_VIEWS:
                    cursor.execute(
                        "SELECT set_config(%s, %s, true)",
                        [f"qlvb.can_view_{source_type}", "on"],
                    )
                    cursor.execute(
                        "SELECT set_config(%s, %s, true)",
                        [
                            f"qlvb.can_view_expired_{source_type}",
                            "on" if co_quyen_xem_het_hieu_luc(user, source_type) else "off",
                        ],
                    )
                union_parts = []
                union_params = []
                if document_ids["vanbanden"]:
                    union_parts.append(
                        "SELECT 'vanbanden'::text AS source_type, id AS source_id FROM ai_vanbanden WHERE id = ANY(%s)"
                    )
                    union_params.append(document_ids["vanbanden"])
                if document_ids["vanbandi"]:
                    union_parts.append(
                        "SELECT 'vanbandi'::text AS source_type, id AS source_id FROM ai_vanbandi WHERE id = ANY(%s)"
                    )
                    union_params.append(document_ids["vanbandi"])
                if can_read_tailieu:
                    union_parts.append(
                        "SELECT 'tailieu'::text AS source_type, id AS source_id FROM ai_tailieu"
                    )
                if union_parts:
                    cursor.execute(" UNION ALL ".join(union_parts), union_params)
                    for source_type, source_id in cursor.fetchall():
                        allowed_keys.add(f"{source_type}:{source_id}")
    except SqlDocumentAccessError:
        raise
    except Exception as error:
        raise SqlDocumentAccessError(
            "Không thể truy cập nguồn CSDL chỉ đọc an toàn cho AI.", ai_reason="readonly_query_failed"
        ) from error

    return allowed_keys


def accessible_documents(user, employee_id=None):
    """Return rows admitted by ``ai_*`` views and the user's document permissions."""
    if not is_postgres_source():
        return []
    if not has_permission_codename(user, "use_aiassistant"):
        raise SqlDocumentAccessError(
            "Tài khoản chưa được cấp quyền sử dụng trợ lý AI.", ai_reason="no_ai_permission"
        )

    document_ids = {
        "vanbanden": list(
            van_ban_xem_duoc(user, "DEN").values_list("pk", flat=True)
        ),
        "vanbandi": list(
            van_ban_xem_duoc(user, "DI").values_list("pk", flat=True)
        ),
    }
    can_read_tailieu = has_permission_codename(user, "view_tailieu")
    employee_id = _employee_id_value(employee_id)
    if "readonly" not in connections.databases:
        raise SqlDocumentAccessError(
            "Thiếu cấu hình kết nối CSDL chỉ đọc cho AI.", ai_reason="readonly_alias_missing"
        )

    queries = {
        "vanbanden": """
            SELECT 'vanbanden'::text AS source_type, id AS source_id,
                   so_hieu, so_thu_tu AS sort_number, nam,
                   ngay_den AS document_date, trich_yeu, noi_ban_hanh,
                   ngay_van_ban, nguoi_ky, chuc_vu, hieu_luc::text AS hieu_luc,
                   ngay_het_hieu_luc, ghi_chu, updated_at
            FROM ai_vanbanden
            WHERE id = ANY(%s)
            ORDER BY updated_at DESC
        """,
        "vanbandi": """
            SELECT 'vanbandi'::text AS source_type, id AS source_id,
                   so_hieu, so_thu_tu AS sort_number, nam,
                   ngay_ban_hanh AS document_date, trich_yeu, noi_ban_hanh,
                   ngay_van_ban, nguoi_ky, chuc_vu, hieu_luc::text AS hieu_luc,
                   ngay_het_hieu_luc, ghi_chu, updated_at
            FROM ai_vanbandi
            WHERE id = ANY(%s)
            ORDER BY updated_at DESC
        """,
    }
    if can_read_tailieu:
        queries["tailieu"] = """
            SELECT 'tailieu'::text AS source_type, id AS source_id,
                   ky_hieu AS so_hieu, NULL::integer AS sort_number,
                   NULL::smallint AS nam, ngay_dang::timestamptz AS document_date,
                   tieu_de AS trich_yeu, noi_ban_hanh,
                   NULL::timestamptz AS ngay_van_ban, NULL::text AS nguoi_ky,
                   NULL::text AS chuc_vu, hieu_luc::text AS hieu_luc,
                   ngay_het_hieu_luc::timestamptz AS ngay_het_hieu_luc,
                   ghi_chu, updated_at
            FROM ai_tailieu
            ORDER BY updated_at DESC
        """

    attachment_queries = {
        "vanbanden": "SELECT id, document_id, name, path FROM ai_vanbanden_attachment WHERE document_id = ANY(%s) ORDER BY document_id, id",
        "vanbandi": "SELECT id, document_id, name, path FROM ai_vanbandi_attachment WHERE document_id = ANY(%s) ORDER BY document_id, id",
    }

    docs = []
    try:
        with transaction.atomic(using="readonly"):
            readonly = connections["readonly"]
            with readonly.cursor() as cursor:
                _assert_readonly_connection(cursor)
            with readonly.cursor() as cursor:
                cursor.execute(
                    "SELECT set_config('qlvb.employee_id', %s, true)",
                    [str(employee_id or "")],
                )
                for source_type in DOCUMENT_VIEWS:
                    cursor.execute(
                        "SELECT set_config(%s, %s, true)",
                        # The document module's selector below supplies the exact row
                        # allowlist. Keep the SQL view permissive enough for every row
                        # that selector admits (including admin/staff policy).
                        [f"qlvb.can_view_{source_type}", "on"],
                    )
                    cursor.execute(
                        "SELECT set_config(%s, %s, true)",
                        [
                            f"qlvb.can_view_expired_{source_type}",
                            "on" if co_quyen_xem_het_hieu_luc(user, source_type) else "off",
                        ],
                    )
            for source_type in DOCUMENT_VIEWS:
                attachments_by_document = {}
                with readonly.cursor() as cursor:
                    cursor.execute(attachment_queries[source_type], [document_ids[source_type]])
                    for attachment in _dict_rows(cursor):
                        attachments_by_document.setdefault(attachment["document_id"], []).append(
                            {"id": attachment["id"], "name": attachment["name"], "path": attachment["path"]}
                        )
                with readonly.cursor() as cursor:
                    cursor.execute(queries[source_type], [document_ids[source_type]])
                    rows = _dict_rows(cursor)
                for row in rows:
                    row["display_name"] = f"{row['so_hieu']} — {row['trich_yeu']}"[:240]
                    row["attachments"] = attachments_by_document.get(row["source_id"], [])
                    docs.append(row)
            if can_read_tailieu:
                with readonly.cursor() as cursor:
                    cursor.execute(queries["tailieu"])
                    rows = _dict_rows(cursor)
                for row in rows:
                    row["display_name"] = f"{row['so_hieu'] or 'Tài liệu'} — {row['trich_yeu']}"[:240]
                    docs.append(row)
    except SqlDocumentAccessError:
        raise
    except Exception as error:
        raise SqlDocumentAccessError(
            "Không thể truy cập nguồn CSDL chỉ đọc an toàn cho AI.", ai_reason="readonly_query_failed"
        ) from error

    return docs


def get_accessible_document(user, source_type, source_id, employee_id=None):
    return next(
        (
            doc for doc in accessible_documents(user, employee_id)
            if doc["source_type"] == source_type and doc["source_id"] == int(source_id)
        ),
        None,
    )


def get_document_record_for_index(source_type: str, source_id: int):
    """Retrieve full metadata and attachments for a single SQL document to index in ChromaDB.

    Returns None if the document does not exist, is not internal (NOI_BO), or is hidden.
    """
    if not is_postgres_source():
        return None

    try:
        source_id = int(source_id)
    except (TypeError, ValueError):
        return None

    db_alias = "default"
    connection = connections[db_alias]

    queries = {
        "vanbanden": """
            SELECT 'vanbanden'::text AS source_type, id AS source_id,
                   so_hieu, so_thu_tu AS sort_number, nam,
                   ngay_den AS document_date, trich_yeu, noi_ban_hanh,
                   ngay_van_ban, nguoi_ky, chuc_vu, hieu_luc::text AS hieu_luc,
                   ngay_het_hieu_luc, ghi_chu, updated_at
            FROM documents_vanbanden
            WHERE id = %s AND pham_vi = 'NOI_BO' AND hien_thi IS TRUE
        """,
        "vanbandi": """
            SELECT 'vanbandi'::text AS source_type, id AS source_id,
                   so_hieu, so_thu_tu AS sort_number, nam,
                   ngay_ban_hanh AS document_date, trich_yeu,
                   (
                       SELECT string_agg(dv.ten, ', ' ORDER BY dv.ten)
                       FROM documents_vanbandi_noibanhanh nb
                       JOIN organizations_donvi dv ON dv.id = nb.donvi_id
                       WHERE nb.vanbandi_id = documents_vanbandi.id
                   ) AS noi_ban_hanh,
                   ngay_van_ban, nguoi_ky, chuc_vu, hieu_luc::text AS hieu_luc,
                   ngay_het_hieu_luc, ghi_chu, updated_at
            FROM documents_vanbandi
            WHERE id = %s AND pham_vi = 'NOI_BO' AND hien_thi IS TRUE
        """,
        "tailieu": """
            SELECT 'tailieu'::text AS source_type, id AS source_id,
                   ky_hieu AS so_hieu, NULL::integer AS sort_number,
                   NULL::smallint AS nam, ngay_dang::timestamptz AS document_date,
                   tieu_de AS trich_yeu, noi_ban_hanh,
                   NULL::timestamptz AS ngay_van_ban, NULL::text AS nguoi_ky,
                   NULL::text AS chuc_vu, hieu_luc::text AS hieu_luc,
                   ngay_het_hieu_luc::timestamptz AS ngay_het_hieu_luc,
                   ghi_chu, updated_at
            FROM records_chitiettailieu
            WHERE id = %s AND hien_thi IN ('TAT_CA', 'NOI_BO_PHONG_BAN')
        """,
    }

    attachment_queries = {
        "vanbanden": "SELECT id, document_id, name, path FROM documents_vanbanden_attachment WHERE document_id = %s AND is_deleted IS FALSE ORDER BY id",
        "vanbandi": "SELECT id, document_id, name, path FROM documents_vanbandi_attachment WHERE document_id = %s AND is_deleted IS FALSE ORDER BY id",
        "tailieu": "SELECT id, document_id, name, path FROM records_chitiettailieu_attachment WHERE document_id = %s AND is_deleted IS FALSE ORDER BY id",
    }

    if source_type not in queries:
        return None

    with connection.cursor() as cursor:
        cursor.execute(queries[source_type], [source_id])
        rows = _dict_rows(cursor)
        if not rows:
            return None
        row = rows[0]

        attachments = []
        if source_type in attachment_queries:
            cursor.execute(attachment_queries[source_type], [source_id])
            attachments = _dict_rows(cursor)

        if source_type == "tailieu":
            row["display_name"] = f"{row['so_hieu'] or 'Tài liệu'} — {row['trich_yeu']}"[:240]
        else:
            row["display_name"] = f"{row['so_hieu']} — {row['trich_yeu']}"[:240]
        row["attachments"] = attachments
        return row


def get_all_document_records_for_index(source_type: str | None = None):
    """Retrieve all internal documents across specified or all document types for indexing."""
    if not is_postgres_source():
        return []

    types_to_fetch = [source_type] if source_type else ["vanbanden", "vanbandi", "tailieu"]
    connection = connections["default"]

    queries = {
        "vanbanden": """
            SELECT 'vanbanden'::text AS source_type, id AS source_id,
                   so_hieu, so_thu_tu AS sort_number, nam,
                   ngay_den AS document_date, trich_yeu, noi_ban_hanh,
                   ngay_van_ban, nguoi_ky, chuc_vu, hieu_luc::text AS hieu_luc,
                   ngay_het_hieu_luc, ghi_chu, updated_at
            FROM documents_vanbanden
            WHERE pham_vi = 'NOI_BO' AND hien_thi IS TRUE
            ORDER BY updated_at DESC
        """,
        "vanbandi": """
            SELECT 'vanbandi'::text AS source_type, id AS source_id,
                   so_hieu, so_thu_tu AS sort_number, nam,
                   ngay_ban_hanh AS document_date, trich_yeu,
                   (
                       SELECT string_agg(dv.ten, ', ' ORDER BY dv.ten)
                       FROM documents_vanbandi_noibanhanh nb
                       JOIN organizations_donvi dv ON dv.id = nb.donvi_id
                       WHERE nb.vanbandi_id = documents_vanbandi.id
                   ) AS noi_ban_hanh,
                   ngay_van_ban, nguoi_ky, chuc_vu, hieu_luc::text AS hieu_luc,
                   ngay_het_hieu_luc, ghi_chu, updated_at
            FROM documents_vanbandi
            WHERE pham_vi = 'NOI_BO' AND hien_thi IS TRUE
            ORDER BY updated_at DESC
        """,
        "tailieu": """
            SELECT 'tailieu'::text AS source_type, id AS source_id,
                   ky_hieu AS so_hieu, NULL::integer AS sort_number,
                   NULL::smallint AS nam, ngay_dang::timestamptz AS document_date,
                   tieu_de AS trich_yeu, noi_ban_hanh,
                   NULL::timestamptz AS ngay_van_ban, NULL::text AS nguoi_ky,
                   NULL::text AS chuc_vu, hieu_luc::text AS hieu_luc,
                   ngay_het_hieu_luc::timestamptz AS ngay_het_hieu_luc,
                   ghi_chu, updated_at
            FROM records_chitiettailieu
            WHERE hien_thi IN ('TAT_CA', 'NOI_BO_PHONG_BAN')
            ORDER BY updated_at DESC
        """,
    }

    attachment_queries = {
        "vanbanden": "SELECT id, document_id, name, path FROM documents_vanbanden_attachment WHERE is_deleted IS FALSE ORDER BY document_id, id",
        "vanbandi": "SELECT id, document_id, name, path FROM documents_vanbandi_attachment WHERE is_deleted IS FALSE ORDER BY document_id, id",
        "tailieu": "SELECT id, document_id, name, path FROM records_chitiettailieu_attachment WHERE is_deleted IS FALSE ORDER BY document_id, id",
    }

    docs = []
    with connection.cursor() as cursor:
        for st in types_to_fetch:
            if st not in queries:
                continue

            attachments_by_doc = {}
            if st in attachment_queries:
                cursor.execute(attachment_queries[st])
                for att in _dict_rows(cursor):
                    attachments_by_doc.setdefault(att["document_id"], []).append(att)

            cursor.execute(queries[st])
            rows = _dict_rows(cursor)
            for row in rows:
                if st == "tailieu":
                    row["display_name"] = f"{row['so_hieu'] or 'Tài liệu'} — {row['trich_yeu']}"[:240]
                else:
                    row["display_name"] = f"{row['so_hieu']} — {row['trich_yeu']}"[:240]
                row["attachments"] = attachments_by_doc.get(row["source_id"], [])
                docs.append(row)

    return docs

