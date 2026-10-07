"""Shared permission checks for the AI API and its SQL-backed source."""


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
