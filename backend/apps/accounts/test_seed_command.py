import datetime
import io
import os
from unittest import mock
from django.contrib.auth import get_user_model
from django.core.management import call_command, CommandError
from django.test import TestCase

from accounts.management.commands.seed_db import SYSTEM_PASSWORD_PLACEHOLDER
from accounts.models import Employee, Position
from organizations.models import DonVi, KhoiKhuVuc

UserModel = get_user_model()


class SeedDbCommandTests(TestCase):
    def setUp(self):
        super().setUp()
        self.admin_pass = "AdminSecr3t!2026"
        self.demo_pass = "DemoSecr3t!2026"

    def test_seed_admin_with_placeholder_and_admin_password(self):
        """Edge case 1: admin có placeholder + ADMIN_PASSWORD -> đặt password, các trường khác giữ nguyên."""
        # Chạy seed lần đầu để có reference data chuẩn
        with mock.patch.dict(os.environ, {"ADMIN_PASSWORD": "initial_password_1"}, clear=False):
            call_command("seed_db")

        admin = UserModel.objects.get(username="admin")
        admin.password = SYSTEM_PASSWORD_PLACEHOLDER
        admin.ho_ten = "Admin Gốc Giữ Nguyên"
        admin.email = "admin_kept@test.vn"
        admin.sdt = "0999888777"
        admin.is_active = False
        admin.is_staff = False
        admin.is_superuser = False
        admin.save()

        out = io.StringIO()
        with mock.patch.dict(os.environ, {"ADMIN_PASSWORD": self.admin_pass}, clear=False):
            call_command("seed_db", stdout=out)

        admin.refresh_from_db()
        self.assertTrue(admin.check_password(self.admin_pass))
        self.assertNotEqual(admin.password, SYSTEM_PASSWORD_PLACEHOLDER)
        self.assertEqual(admin.ho_ten, "Admin Gốc Giữ Nguyên")
        self.assertEqual(admin.email, "admin_kept@test.vn")
        self.assertEqual(admin.sdt, "0999888777")
        self.assertFalse(admin.is_active)
        self.assertFalse(admin.is_staff)
        self.assertFalse(admin.is_superuser)

    def test_seed_admin_with_existing_custom_password(self):
        """Edge case 2: admin có password khác placeholder -> không đổi gì, kể cả khi is_active=False."""
        # Chạy seed lần đầu để có reference data chuẩn
        with mock.patch.dict(os.environ, {"ADMIN_PASSWORD": "initial_password_2"}, clear=False):
            call_command("seed_db")

        admin = UserModel.objects.get(username="admin")
        admin.set_password("OldCustomPass!123")
        admin.ho_ten = "Admin Tùy Biến"
        admin.is_active = False
        admin.is_staff = False
        admin.is_superuser = False
        admin.save()
        old_hash = admin.password

        out = io.StringIO()
        with mock.patch.dict(os.environ, {"ADMIN_PASSWORD": self.admin_pass}, clear=False):
            call_command("seed_db", stdout=out)

        admin.refresh_from_db()
        self.assertEqual(admin.password, old_hash)
        self.assertTrue(admin.check_password("OldCustomPass!123"))
        self.assertFalse(admin.is_active)
        self.assertFalse(admin.is_staff)
        self.assertFalse(admin.is_superuser)
        self.assertEqual(admin.ho_ten, "Admin Tùy Biến")

    def test_seed_without_admin_and_missing_admin_password_rolls_back(self):
        """Edge case 3: Không có admin, thiếu ADMIN_PASSWORD -> CommandError, rollback transaction."""
        # Keep the migration-seeded account and its references; exercise the missing-admin case.
        UserModel.objects.filter(username="admin").update(username="seed_reference_admin")
        self.assertFalse(UserModel.objects.filter(username="admin").exists())
        initial_counts = (
            KhoiKhuVuc.objects.count(),
            DonVi.objects.count(),
            Position.objects.count(),
            UserModel.objects.count(),
        )

        env = os.environ.copy()
        env.pop("ADMIN_PASSWORD", None)
        with mock.patch.dict(os.environ, env, clear=True):
            with self.assertRaises(CommandError) as ctx:
                call_command("seed_db")
            self.assertIn("ADMIN_PASSWORD is required", str(ctx.exception))

        current_counts = (
            KhoiKhuVuc.objects.count(),
            DonVi.objects.count(),
            Position.objects.count(),
            UserModel.objects.count(),
        )
        self.assertEqual(initial_counts, current_counts)

    def test_seed_admin_password_whitespace_only_is_treated_as_missing(self):
        """Edge case 4: ADMIN_PASSWORD chỉ có khoảng trắng được coi là thiếu."""
        # Keep the migration-seeded account and its references; exercise the missing-admin case.
        UserModel.objects.filter(username="admin").update(username="seed_reference_admin")
        self.assertFalse(UserModel.objects.filter(username="admin").exists())
        with mock.patch.dict(os.environ, {"ADMIN_PASSWORD": "   \t  "}, clear=False):
            with self.assertRaises(CommandError) as ctx:
                call_command("seed_db")
            self.assertIn("ADMIN_PASSWORD is required", str(ctx.exception))

    def test_demo_data_flag_behavior(self):
        """Edge case 5: Không có --demo-data: không tạo demo users. Có --demo-data mà thiếu DEMO_PASSWORD: lỗi."""
        out = io.StringIO()
        with mock.patch.dict(os.environ, {"ADMIN_PASSWORD": self.admin_pass}, clear=False):
            call_command("seed_db", stdout=out)

        demo_usernames = ["truongphong_cntt", "chuyenvien_cntt", "vanthu_cntt"]
        for u in demo_usernames:
            self.assertFalse(UserModel.objects.filter(username=u).exists())

        # Có --demo-data nhưng thiếu DEMO_PASSWORD (hoặc whitespace) -> CommandError
        env = os.environ.copy()
        env["ADMIN_PASSWORD"] = self.admin_pass
        env.pop("DEMO_PASSWORD", None)
        with mock.patch.dict(os.environ, env, clear=True):
            with self.assertRaises(CommandError) as ctx:
                call_command("seed_db", demo_data=True)
            self.assertIn("DEMO_PASSWORD is required", str(ctx.exception))

        with mock.patch.dict(os.environ, {"ADMIN_PASSWORD": self.admin_pass, "DEMO_PASSWORD": "   "}, clear=False):
            with self.assertRaises(CommandError) as ctx:
                call_command("seed_db", demo_data=True)
            self.assertIn("DEMO_PASSWORD is required", str(ctx.exception))

        # Có --demo-data và DEMO_PASSWORD hợp lệ -> tạo demo users
        with mock.patch.dict(os.environ, {"ADMIN_PASSWORD": self.admin_pass, "DEMO_PASSWORD": self.demo_pass}, clear=False):
            call_command("seed_db", demo_data=True, stdout=out)

        for u in demo_usernames:
            user = UserModel.objects.filter(username=u).first()
            self.assertIsNotNone(user, f"User {u} should exist")
            self.assertTrue(user.check_password(self.demo_pass))

    def test_seed_run_twice_idempotency(self):
        """Edge case 6: Chạy seed hai lần liên tiếp: lần 2 không đổi gì (password hash và các cờ)."""
        out1 = io.StringIO()
        out2 = io.StringIO()
        env_map = {"ADMIN_PASSWORD": self.admin_pass, "DEMO_PASSWORD": self.demo_pass}
        with mock.patch.dict(os.environ, env_map, clear=False):
            call_command("seed_db", demo_data=True, stdout=out1)

        admin1 = UserModel.objects.get(username="admin")
        admin1_hash = admin1.password
        admin1_flags = (admin1.is_active, admin1.is_staff, admin1.is_superuser)

        demo1 = UserModel.objects.get(username="truongphong_cntt")
        demo1_hash = demo1.password
        demo1_flags = (demo1.is_active, demo1.is_staff, demo1.is_superuser)

        with mock.patch.dict(os.environ, env_map, clear=False):
            call_command("seed_db", demo_data=True, stdout=out2)

        admin2 = UserModel.objects.get(username="admin")
        self.assertEqual(admin2.password, admin1_hash)
        self.assertEqual((admin2.is_active, admin2.is_staff, admin2.is_superuser), admin1_flags)

        demo2 = UserModel.objects.get(username="truongphong_cntt")
        self.assertEqual(demo2.password, demo1_hash)
        self.assertEqual((demo2.is_active, demo2.is_staff, demo2.is_superuser), demo1_flags)

    def test_output_stdout_does_not_leak_passwords(self):
        """Edge case 7: Output stdout của seed không chứa giá trị ADMIN_PASSWORD hay DEMO_PASSWORD."""
        out = io.StringIO()
        secret_admin = "VerySecretAdminPass999!"
        secret_demo = "VerySecretDemoPass888!"
        with mock.patch.dict(os.environ, {"ADMIN_PASSWORD": secret_admin, "DEMO_PASSWORD": secret_demo}, clear=False):
            call_command("seed_db", demo_data=True, stdout=out)

        rendered = out.getvalue()
        self.assertNotIn(secret_admin, rendered)
        self.assertNotIn(secret_demo, rendered)
        self.assertNotIn("Admin@123", rendered)
