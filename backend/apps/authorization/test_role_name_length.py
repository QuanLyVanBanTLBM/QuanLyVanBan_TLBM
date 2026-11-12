"""B3 (QA 14/10): tên nhóm quyền quá 150 ký tự trả key i18n, không trả câu tiếng Anh của DRF."""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient


class RoleNameLengthTest(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(username="rbac_len", password="Test@12345")
        user.user_permissions.add(*Permission.objects.filter(codename__in=["add_nhomquyen", "change_nhomquyen"]))
        self.client = APIClient()
        self.client.force_authenticate(user=user)

    def test_name_over_150_characters_returns_message_key(self):
        res = self.client.post("/api/roles/", {"name": "A" * 151}, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.json()["name"], ["roles.messages.nameTooLong"])
        self.assertFalse(Group.objects.filter(name="A" * 151).exists())

    def test_rename_over_150_characters_returns_message_key(self):
        group = Group.objects.create(name="QA-Len")
        res = self.client.put(f"/api/roles/{group.pk}/", {"name": "B" * 151}, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.json()["name"], ["roles.messages.nameTooLong"])

    def test_name_of_exactly_150_characters_is_accepted(self):
        res = self.client.post("/api/roles/", {"name": "C" * 150}, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
