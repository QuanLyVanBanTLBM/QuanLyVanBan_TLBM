"""Shared permission checks and trusted employee identity for the AI API."""


def resolve_employee_id(request):
    """Return the authenticated employee's database ID.

    ``accounts.Employee`` is the configured auth model, so its primary key is
    the ``accounts_employee.id`` used by the AI document views. Request payloads
    and extra request attributes are not identity sources.
    """
    user = getattr(request, "user", None)
    if not getattr(user, "is_authenticated", False) or not getattr(user, "is_active", False):
        return None
    return getattr(user, "pk", None)


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
