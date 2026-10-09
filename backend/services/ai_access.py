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
