from importlib import import_module
from types import SimpleNamespace

from django.contrib.auth.models import Permission
from django.db import connection
from django.test import TestCase
from unittest import skipUnless


align = import_module("authorization.migrations.0006_align_permission_defaults_and_labels")


class PermissionAlignmentMigrationTest(TestCase):
    @skipUnless(connection.vendor == "postgresql", "requires PostgreSQL")
    def test_unexpected_default_aborts_before_permission_label_update(self):
        permission = Permission.objects.get(codename="add_phonghop")
        legacy_name = "Thêm phòng họp"
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE auth_permission SET name = %s WHERE id = %s",
                [legacy_name, permission.pk],
            )
            cursor.execute(
                "ALTER TABLE auth_permission ALTER COLUMN module_ten SET DEFAULT CURRENT_USER"
            )

        with self.assertRaisesRegex(RuntimeError, "unexpected default"):
            align.align_permission_schema_and_labels(None, SimpleNamespace(connection=connection))

        self.assertEqual(Permission.objects.get(pk=permission.pk).name, legacy_name)
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT column_default FROM information_schema.columns "
                "WHERE table_schema = current_schema() AND table_name = 'auth_permission' "
                "AND column_name = 'module_ten'"
            )
            self.assertEqual(cursor.fetchone()[0], "CURRENT_USER")

    @skipUnless(connection.vendor == "postgresql", "requires PostgreSQL")
    def test_known_legacy_default_and_exact_old_labels_are_aligned(self):
        permission = Permission.objects.get(codename="add_phonghop")
        customized_permission = Permission.objects.get(codename="import_chucvu")
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE auth_permission SET name = %s WHERE id = %s",
                ["Thêm phòng họp", permission.pk],
            )
            cursor.execute(
                "UPDATE auth_permission SET name = %s WHERE id = %s",
                ["Tên tùy chỉnh", customized_permission.pk],
            )
            cursor.execute("ALTER TABLE auth_permission ALTER COLUMN module_ten SET DEFAULT ''")

        align.align_permission_schema_and_labels(None, SimpleNamespace(connection=connection))

        self.assertEqual(
            Permission.objects.get(pk=permission.pk).name,
            "Thêm phòng họp (danh mục)",
        )
        self.assertEqual(Permission.objects.get(pk=customized_permission.pk).name, "Tên tùy chỉnh")
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT column_default FROM information_schema.columns "
                "WHERE table_schema = current_schema() AND table_name = 'auth_permission' "
                "AND column_name = 'module_ten'"
            )
            self.assertIsNone(cursor.fetchone()[0])
