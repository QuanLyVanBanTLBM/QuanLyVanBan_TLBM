"""Shared permission checks and trusted employee identity for the AI API."""

from django.db import connection


def resolve_employee_id(request):
    """Return an employee ID from host authentication or a trusted DB mapping.

    Client-supplied request data is never consulted. If the host session does not
    supply an employee ID, a unique username lookup may resolve an active,
    working employee. A missing mapping or lookup failure returns None.
    """
    user = getattr(request, "user", None)
    explicit = getattr(request, "employee_id", None)
    if explicit in (None, ""):
        explicit = getattr(user, "employee_id", None)
    if explicit not in (None, ""):
        return explicit
    if not getattr(user, "is_authenticated", False) or not getattr(user, "is_active", False):
        return None
    if connection.vendor != "postgresql":
        return None
    try:
        username = user.get_username()
        if not username:
            return None
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id FROM accounts_employee
                WHERE username = %s AND is_active IS TRUE AND trang_thai::text = 'LAM_VIEC'
                """,
                [username],
            )
            row = cursor.fetchone()
        return row[0] if row else None
    except Exception:
        return None


def has_permission_codename(user, codename):
    """Check the standard Django RBAC codename for an active account."""
    if not getattr(user, "is_authenticated", False) or not getattr(user, "is_active", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    return user.has_perm(codename)


def is_ai_admin(user):
    """AI knowledge management stays superuser-only until DDL defines its own permission."""
    return bool(
        getattr(user, "is_authenticated", False)
        and getattr(user, "is_active", False)
        and getattr(user, "is_superuser", False)
    )