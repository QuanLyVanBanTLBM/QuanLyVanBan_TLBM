from datetime import date
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import SimpleTestCase, TestCase

from accounts.models import Employee
from document_templates.models import (
    ChiTietTaiLieuAttachment,
    DanhMucTaiLieu,
    TaiLieuChiTiet,
)


class AttachmentFileSizeValidationTest(SimpleTestCase):
    def test_negative_size_fails_model_validation(self):
        field = ChiTietTaiLieuAttachment._meta.get_field("file_size")
        with self.assertRaises(ValidationError):
            field.run_validators(-1)

    def test_database_check_uses_release_name(self):
        constraints = {constraint.name for constraint in ChiTietTaiLieuAttachment._meta.constraints}
        self.assertIn("records_chitiettailieu_attachment_file_size_check", constraints)


class AttachmentFileSizePreflightTest(SimpleTestCase):
    def test_negative_existing_rows_refuse_before_ddl(self):
        from importlib import import_module

        migration = import_module("document_templates.migrations.0005_attachment_file_size_check")
        cursor = _CountCursor(3)
        schema_editor = _SchemaEditor(cursor)

        with self.assertRaisesRegex(RuntimeError, "3 negative rows"):
            migration.ensure_nonnegative_file_size(None, schema_editor)

        self.assertEqual(len(cursor.statements), 1)
        self.assertTrue(cursor.statements[0][0].startswith("SELECT count(*)"))


class AttachmentFileSizeDatabaseConstraintTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = Employee.objects.create_user(username=f"file_size_{uuid4().hex[:12]}", password="pw")
        cls.category = DanhMucTaiLieu.objects.create(
            stt_uu_tien=0,
            ten_tai_lieu=f"Danh mục {uuid4().hex[:12]}",
            nguoi_lap=cls.user,
        )
        cls.document = TaiLieuChiTiet.objects.create(
            dm_tai_lieu=cls.category,
            tieu_de=f"Tài liệu {uuid4().hex[:12]}",
            ngay_dang=date(2026, 10, 20),
            nguoi_tao=cls.user,
        )

    def test_negative_attachment_size_is_rejected_by_database(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ChiTietTaiLieuAttachment.objects.create(
                    document=self.document,
                    name="negative-size.pdf",
                    path="negative-size.pdf",
                    file_size=-1,
                )


class _CountCursor:
    def __init__(self, count):
        self.count = count
        self.statements = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, statement, params=None):
        self.statements.append((statement, params))

    def fetchone(self):
        return (self.count,)


class _Connection:
    vendor = "postgresql"

    def __init__(self, cursor):
        self._cursor = cursor
        self.ops = self

    def cursor(self):
        return self._cursor

    @staticmethod
    def quote_name(name):
        return f'"{name}"'


class _SchemaEditor:
    def __init__(self, cursor):
        self.connection = _Connection(cursor)
