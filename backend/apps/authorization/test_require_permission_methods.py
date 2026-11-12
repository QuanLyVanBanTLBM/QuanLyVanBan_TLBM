"""
require_permission({method: codename}): kiểm quyền theo method cho view phục vụ nhiều method (contract Issue #21).
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser, Permission
from django.test import RequestFactory, TestCase

from authorization.permissions import DEFAULT_DENIED_MESSAGE, require_permission

PERMS = {"GET": "view_nhomquyen", "POST": "add_nhomquyen"}


class RequirePermissionByMethodTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.factory = RequestFactory()
        self.viewer = User.objects.create_user(username="perm_method_viewer", password="Test@12345")
        self.viewer.user_permissions.add(Permission.objects.get(codename="view_nhomquyen"))
        self.root = User.objects.create_superuser(
            username="perm_method_root", password="Test@12345", email="pm@example.com"
        )
        self.permission = require_permission(PERMS)()

    def allowed(self, method, user):
        request = getattr(self.factory, method.lower())("/x/")
        request.user = user
        return self.permission.has_permission(request, view=None)

    def test_method_uses_its_own_codename(self):
        self.assertTrue(self.allowed("GET", self.viewer))
        self.assertFalse(self.allowed("POST", self.viewer))

    def test_head_and_options_follow_get(self):
        self.assertTrue(self.allowed("HEAD", self.viewer))
        self.assertTrue(self.allowed("OPTIONS", self.viewer))

    def test_method_missing_from_mapping_is_denied_even_for_superuser(self):
        self.assertFalse(self.allowed("DELETE", self.root))

    def test_superuser_allowed_for_mapped_methods(self):
        self.assertTrue(self.allowed("GET", self.root))
        self.assertTrue(self.allowed("POST", self.root))

    def test_anonymous_denied(self):
        self.assertFalse(self.allowed("GET", AnonymousUser()))

    def test_message_and_name(self):
        permission_class = require_permission(PERMS)
        self.assertEqual(permission_class.message, DEFAULT_DENIED_MESSAGE)
        self.assertEqual(permission_class.__name__, "Require_add_nhomquyen_view_nhomquyen")
        self.assertEqual(require_permission(PERMS, "positions.messages.permissionDenied").message,
                         "positions.messages.permissionDenied")
