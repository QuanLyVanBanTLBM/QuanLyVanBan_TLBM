import importlib
from urllib.error import URLError
from unittest.mock import patch

from django.apps import apps as global_apps
from django.contrib.auth.hashers import is_password_usable
from django.db import connection
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import Employee, Position
from accounts.standard_positions import STANDARD_POSITIONS
from organizations.models import DonVi, KhoiKhuVuc

organizations_seed = importlib.import_module("organizations.migrations.0005_reference_data_ddl")
accounts_seed = importlib.import_module("accounts.migrations.0006_reference_data_ddl")
account_password_fix = importlib.import_module("accounts.migrations.0007_normalize_system_account_password")


class SeedReferenceDataMigrationTests(TestCase):
    """Migration dữ liệu nền: đúng nội dung release_DDL.sql, idempotent, không ghi đè dữ liệu sẵn có."""

    def run_seeds(self):
        with connection.schema_editor() as editor:
            organizations_seed.seed(global_apps, editor)
            accounts_seed.seed(global_apps, editor)
            account_password_fix.normalize_system_seed_password(global_apps, editor)

    def test_seed_creates_reference_data_once(self):
        self.run_seeds()
        self.assertEqual(KhoiKhuVuc.objects.count(), 16)
        self.assertEqual(DonVi.objects.count(), 82)
        # 0006 chỉ nạp "Quản trị viên" khi chưa có; 24 chức vụ chuẩn còn lại do accounts/0009 nạp.
        self.assertEqual(Position.objects.filter(name="Quản trị viên").count(), 1)
        self.assertEqual(list(Position.objects.order_by("display_order").values_list("name", flat=True)), [name for _, name in STANDARD_POSITIONS])
        admin = Employee.objects.get(username="admin")
        self.assertEqual(admin.password, "!system_seed_placeholder")
        self.assertFalse(is_password_usable(admin.password))
        self.assertFalse(admin.check_password("bat-ky"))
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.is_active)
        self.assertEqual(admin.don_vi.ten, "Ban công nghệ thông tin")

        self.run_seeds()
        self.assertEqual(KhoiKhuVuc.objects.count(), 16)
        self.assertEqual(DonVi.objects.count(), 82)
        self.assertEqual(Employee.objects.filter(username="admin").count(), 1)

    def test_seed_keeps_existing_account_and_hierarchy(self):
        self.run_seeds()
        admin = Employee.objects.get(username="admin")
        admin.email = "admin@example.test"
        admin.ho_ten = "Tài khoản có sẵn"
        admin.set_password("mat-khau-hien-co")
        admin.is_active = False
        admin.is_staff = False
        admin.is_superuser = False
        admin.save(update_fields=["email", "ho_ten", "password", "is_active", "is_staff", "is_superuser"])

        position = Position.objects.get(name="Quản trị viên")
        position.display_order = Position.get_next_display_order()
        position.save(update_fields=["display_order"])
        donvi = DonVi.objects.get(ten="Ban công nghệ thông tin")
        donvi.is_public = False
        donvi.save(update_fields=["is_public"])

        self.run_seeds()

        self.assertEqual(KhoiKhuVuc.objects.count(), 16)
        self.assertEqual(DonVi.objects.count(), 82)
        self.assertEqual(Position.objects.count(), len(STANDARD_POSITIONS))
        admin.refresh_from_db()
        self.assertEqual(admin.ho_ten, "Tài khoản có sẵn")
        self.assertFalse(admin.is_active)
        self.assertFalse(admin.is_staff)
        self.assertFalse(admin.is_superuser)
        self.assertTrue(admin.check_password("mat-khau-hien-co"))
        self.assertEqual(Position.objects.get(pk=position.pk).display_order, position.display_order)
        self.assertFalse(DonVi.objects.get(pk=donvi.pk).is_public)

    def test_legacy_placeholder_is_fixed_without_reactivating_admin_or_overwriting_users(self):
        self.run_seeds()
        admin = Employee.objects.get(username="admin")
        admin.password = account_password_fix.LEGACY_PLACEHOLDER
        admin.is_active = False
        admin.save(update_fields=["password", "is_active"])
        user = Employee.objects.create_user(username="existing-seed-test-user", password="kept-password")
        user.is_active = False
        user.save(update_fields=["is_active"])
        user_hash = user.password

        with connection.schema_editor() as editor:
            account_password_fix.normalize_system_seed_password(global_apps, editor)

        admin.refresh_from_db()
        user.refresh_from_db()
        self.assertFalse(admin.is_active)
        self.assertEqual(admin.password, "!system_seed_placeholder")
        self.assertFalse(admin.has_usable_password())
        self.assertFalse(user.is_active)
        self.assertTrue(user.check_password("kept-password"))
        self.assertEqual(user.password, user_hash)

    def test_seeded_admin_login_rejects_wrong_password_when_provider_is_unavailable(self):
        self.run_seeds()
        client = APIClient()
        with patch("accounts.alpaca_auth.urllib.request.urlopen", side_effect=URLError("offline test")):
            response = client.post(
                reverse("accounts:login"),
                {"username": "admin", "password": "wrong-password"},
                format="json",
            )

        self.assertEqual(response.status_code, 401)
        self.assertNotIn("token", response.data)
        self.assertNotIn("access", response.data)
        self.assertNotIn("refresh", response.data)
