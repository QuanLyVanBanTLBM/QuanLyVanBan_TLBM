"""Read AI document metadata through the dedicated PostgreSQL role and views."""

from django.db import connection, connections, transaction

from backend.services.ai_access import has_permission_codename


DOCUMENT_VIEWS = {
    "vanbanden": ("ai_vanbanden", "view_vanbanden"),
    "vanbandi": ("ai_vanbandi", "view_vanbandi"),
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
}


class SqlDocumentAccessError(Exception):
    """The SQL document source cannot safely serve this chat request."""


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
                     AND has_table_privilege(current_user, relation.oid, 'SELECT')
               )
        FROM pg_roles role
        WHERE role.rolname = current_user
        """
    )
    row = cursor.fetchone()
    if not row or row[0] != READONLY_ROLE or row[1] is not True or row[2] is not False or row[3] is not False:
        raise SqlDocumentAccessError(
            "Kết nối AI không dùng đúng role chỉ đọc qlvb_readonly hoặc role đang có quyền đọc bảng gốc."
        )


def _employee_id_value(employee_id):
    try:
        value = int(employee_id)
    except (TypeError, ValueError):
        raise SqlDocumentAccessError("Không xác định được mã nhân viên từ phiên đăng nhập QLVB.")
    if value <= 0:
        raise SqlDocumentAccessError("Mã nhân viên từ phiên đăng nhập QLVB không hợp lệ.")
    return value


def accessible_documents(user, employee_id=None):
    """Return rows admitted by ``ai_*`` views and the user's document permissions."""
    if not is_postgres_source():
        return []
    if not has_permission_codename(user, "use_aiassistant"):
        raise SqlDocumentAccessError("Tài khoản chưa được cấp quyền sử dụng trợ lý AI.")

    permitted_views = [
        (source_type, view_name)
        for source_type, (view_name, permission) in DOCUMENT_VIEWS.items()
        if has_permission_codename(user, permission)
    ]
    can_read_tailieu = has_permission_codename(user, "view_tailieu")
    if can_read_tailieu:
        employee_id = _employee_id_value(employee_id)
    if not permitted_views and not can_read_tailieu:
        return []
    if "readonly" not in connections.databases:
        raise SqlDocumentAccessError("Thiếu cấu hình kết nối CSDL chỉ đọc cho AI.")

    queries = {
        "vanbanden": """
            SELECT 'vanbanden'::text AS source_type, id AS source_id,
                   so_hieu, so_thu_tu AS sort_number, nam,
                   ngay_den AS document_date, trich_yeu, noi_ban_hanh,
                   ngay_van_ban, nguoi_ky, chuc_vu, hieu_luc::text AS hieu_luc,
                   ngay_het_hieu_luc, ghi_chu, updated_at
            FROM ai_vanbanden
            ORDER BY updated_at DESC
        """,
        "vanbandi": """
            SELECT 'vanbandi'::text AS source_type, id AS source_id,
                   so_hieu, so_thu_tu AS sort_number, nam,
                   ngay_ban_hanh AS document_date, trich_yeu, noi_ban_hanh,
                   ngay_van_ban, nguoi_ky, chuc_vu, hieu_luc::text AS hieu_luc,
                   ngay_het_hieu_luc, ghi_chu, updated_at
            FROM ai_vanbandi
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

    docs = []
    try:
        with transaction.atomic(using="readonly"):
            readonly = connections["readonly"]
            with readonly.cursor() as cursor:
                _assert_readonly_connection(cursor)
            if can_read_tailieu:
                with readonly.cursor() as cursor:
                    cursor.execute(
                        "SELECT set_config('qlvb.employee_id', %s, true)",
                        [str(employee_id)],
                    )
            for source_type, _view_name in permitted_views:
                with readonly.cursor() as cursor:
                    cursor.execute(queries[source_type])
                    rows = _dict_rows(cursor)
                for row in rows:
                    row["display_name"] = f"{row['so_hieu']} — {row['trich_yeu']}"[:240]
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
        raise SqlDocumentAccessError("Không thể truy cập nguồn CSDL chỉ đọc an toàn cho AI.") from error

    return docs


def get_accessible_document(user, source_type, source_id, employee_id=None):
    return next(
        (
            doc for doc in accessible_documents(user, employee_id)
            if doc["source_type"] == source_type and doc["source_id"] == int(source_id)
        ),
        None,
    )
