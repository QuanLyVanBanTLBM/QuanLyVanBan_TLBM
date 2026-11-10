import importlib

from django.apps import apps as global_apps
from django.db import connection
from django.test import TestCase

from accounts.models import Employee
from records.models import HoSo

reference_data = importlib.import_module("records.migrations.0003_reference_data_ddl")
organizations_seed = importlib.import_module("organizations.migrations.0005_reference_data_ddl")
accounts_seed = importlib.import_module("accounts.migrations.0006_reference_data_ddl")
account_password_fix = importlib.import_module("accounts.migrations.0007_normalize_system_account_password")


class CommonHoSoMigrationTests(TestCase):
    """Migration dữ liệu nền Hồ sơ chung: lấy người lập từ tài khoản `admin`, idempotent, không tạo tài khoản."""

    def run_seed(self):
        with connection.schema_editor() as editor:
            organizations_seed.seed(global_apps, editor)
            accounts_seed.seed(global_apps, editor)
            account_password_fix.normalize_system_seed_password(global_apps, editor)
            reference_data.seed(global_apps, editor)

    def test_record_seed_does_not_create_admin_when_it_is_missing(self):
        admin = Employee.objects.filter(username="admin").first()
        if admin:
            admin.username = "renamed-system-user-for-test"
            admin.save(update_fields=["username"])
        employees_before = Employee.objects.count()
        records_before = HoSo.objects.count()

        with connection.schema_editor() as editor:
            reference_data.seed(global_apps, editor)

        self.assertEqual(Employee.objects.count(), employees_before)
        self.assertEqual(HoSo.objects.count(), records_before)
        self.assertFalse(Employee.objects.filter(username="admin").exists())

    def test_migration_setup_seeds_common_hoso_once_for_admin(self):
        self.run_seed()
        admin = Employee.objects.get(username="admin")
        self.assertEqual(HoSo.objects.filter(is_he_thong=True).count(), 1)
        self.assertEqual(HoSo.objects.get(is_he_thong=True).nguoi_lap_id, admin.pk)
        self.run_seed()
        hoso = HoSo.objects.get()
        self.assertEqual((hoso.so_ky_hieu, hoso.is_he_thong, hoso.nguoi_lap_id), ("HSC", True, admin.pk))

    def test_seed_rerun_preserves_existing_common_hoso_fields(self):
        self.run_seed()
        existing = HoSo.objects.get(so_ky_hieu="HSC")
        existing.ten_ho_so = "Hồ sơ đã được chỉnh sửa"
        existing.ghi_chu = "Giữ nguyên ghi chú do người dùng nhập"
        existing.save(update_fields=["ten_ho_so", "ghi_chu"])
        self.run_seed()
        existing.refresh_from_db()
        self.assertTrue(existing.is_he_thong)
        self.assertEqual(existing.ten_ho_so, "Hồ sơ đã được chỉnh sửa")
        self.assertEqual(existing.ghi_chu, "Giữ nguyên ghi chú do người dùng nhập")
        self.assertEqual(HoSo.objects.count(), 1)
