from uuid import uuid4

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase

from authorization.models import PermissionInfo
from signing.tests.helpers import cap_quyen


class PermissionFixtureTest(TestCase):
    def test_missing_permission_is_created_with_explicit_module(self):
        codename = f"test_signing_{uuid4().hex[:24]}"
        user = get_user_model().objects.create_user(
            username=f"user_{uuid4().hex[:12]}",
            email=f"{uuid4().hex[:12]}@example.test",
            ho_ten="Signing test user",
            password="test-password",
        )

        cap_quyen(user, codename)

        permission = Permission.objects.get(codename=codename)
        permission_info = PermissionInfo.objects.get(pk=permission.pk)
        self.assertEqual(permission_info.module_ten, "Trình ký")
        self.assertTrue(user.user_permissions.filter(pk=permission.pk).exists())
