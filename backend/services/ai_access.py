"""Shared permission checks for the AI API and its SQL-backed source."""

from django.db import connection


def resolve_employee_id(request):
    """Return the trusted ``accounts_employee.id`` for the authenticated user.

    Order of trust:
    1. ``request.employee_id`` / ``request.user.employee_id`` set by host auth.
    2. Lookup by the authenticated Django username in ``accounts_employee``
       (UNIQUE column) through the host connection, requiring an active,
       working employee. Never read a client-supplied field and never assume
       ``User.pk == accounts_employee.id``.
    Returns ``None`` when no trusted mapping exists.
    """
    explicit = getattr(request, "employee_id", None) or getattr(getattr(request, "user", None), "employee_id", None)
    if explicit:
        return explicit
    user = getattr(request, "user", None)
    if not getattr(user, "is_authenticated", False) or not getattr(user, "is_active", False):
        return None
    if connection.vendor == "postgresql":
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id FROM accounts_employee
                    WHERE username = %s AND is_active IS TRUE AND trang_thai::text = 'LAM_VIEC'
                    """,
                    [user.get_username()],
                )
                row = cursor.fetchone()
            if row:
                return row[0]
        except Exception:
            pass
    return None


def has_permission_codename(user, codename):
    """Check a Django permission by stable codename without importing domain apps."""
    if not getattr(user, "is_authenticated", False) or not getattr(user, "is_active", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    return (
        user.user_permissions.filter(codename=codename).exists()
        or user.groups.filter(permissions__codename=codename).exists()
    )


def is_ai_admin(user):
    """Use the existing Django/admin profile roles for AI knowledge management."""
    if not getattr(user, "is_authenticated", False) or not getattr(user, "is_active", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    try:
        return user.profile.role == "admin"
    except AttributeError:
        return False
