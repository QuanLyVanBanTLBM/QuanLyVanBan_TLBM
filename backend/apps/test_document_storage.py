import tempfile
from datetime import datetime, timezone as dt_timezone
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured, SuspiciousFileOperation
from django.core.files.base import ContentFile
from django.test import SimpleTestCase, override_settings

from document_storage import (
    DocumentStorageError,
    build_dated_path,
    get_document_storage,
    has_allowed_extension,
)

# 2026-10-14 18:30 UTC = 2026-10-15 01:30 giờ Việt Nam.
NOW = datetime(2026, 10, 14, 18, 30, tzinfo=dt_timezone.utc)


class DocumentStorageTests(SimpleTestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        patcher = override_settings(DOCUMENT_STORAGE_ROOT=str(self.root), TIME_ZONE="Asia/Ho_Chi_Minh")
        patcher.enable()
        self.addCleanup(patcher.disable)

    def test_path_uses_local_date_and_uuid(self):
        path = build_dated_path("van-ban-den", "Quyết định.PDF", NOW)
        self.assertRegex(path, r"^van-ban-den/2026/10/15/[0-9a-f]{32}\.pdf$")

    def test_rejects_unknown_module_and_extension(self):
        with self.assertRaises(DocumentStorageError):
            build_dated_path("khac", "a.pdf", NOW)
        with self.assertRaises(DocumentStorageError):
            build_dated_path("van-ban-di", "a.exe", NOW)
        with self.assertRaises(DocumentStorageError):
            build_dated_path("van-ban-di", "khongduoi", NOW)

    def test_module_may_widen_allowed_extensions(self):
        self.assertFalse(has_allowed_extension("bang.xlsx"))
        self.assertTrue(has_allowed_extension("bang.xlsx", {".xlsx"}))
        path = build_dated_path("mau-van-ban", "Bảng.XLSX", NOW, allowed={".xlsx"})
        self.assertRegex(path, r"^mau-van-ban/2026/10/15/[0-9a-f]{32}\.xlsx$")

    def test_save_creates_day_folder_on_first_file_and_reuses_it(self):
        storage = get_document_storage()
        self.assertFalse((self.root / "cong-viec").exists())
        p1 = storage.save(build_dated_path("cong-viec", "a.docx", NOW), ContentFile(b"1"))
        p2 = storage.save(build_dated_path("cong-viec", "b.png", NOW), ContentFile(b"2"))
        self.assertEqual(Path(p1).parent, Path(p2).parent)
        self.assertEqual((self.root / p1).read_bytes(), b"1")
        self.assertEqual((self.root / p2).read_bytes(), b"2")

    def test_storage_follows_settings_changes(self):
        storage = get_document_storage()
        with tempfile.TemporaryDirectory() as other:
            with override_settings(DOCUMENT_STORAGE_ROOT=other):
                name = storage.save(build_dated_path("ho-so", "a.pdf", NOW), ContentFile(b"x"))
                self.assertEqual((Path(other) / name).read_bytes(), b"x")
        self.assertFalse((self.root / name).exists())

    def test_url_uses_media_url(self):
        with override_settings(MEDIA_URL="/media/"):
            self.assertEqual(get_document_storage().url("van-ban-den/2026/10/15/x.pdf"), "/media/van-ban-den/2026/10/15/x.pdf")

    def test_rejects_path_outside_root(self):
        storage = get_document_storage()
        for bad in ("../x.pdf", "/etc/x.pdf"):
            with self.assertRaises(SuspiciousFileOperation):
                storage.path(bad)

    def test_requires_root_configuration(self):
        with override_settings(DOCUMENT_STORAGE_ROOT=""):
            with self.assertRaises(ImproperlyConfigured):
                get_document_storage().save("ho-so/a.pdf", ContentFile(b"x"))
