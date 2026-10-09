import tempfile
from pathlib import Path

from django.test import SimpleTestCase, override_settings

from signing.storage import FilesystemStorageAdapter, StorageError


class FilesystemStorageTests(SimpleTestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "docs"
        (self.root / "2026").mkdir(parents=True)
        (self.root / "2026" / "a.pdf").write_bytes(b"%PDF-1.4 noi dung")
        (Path(self._tmp.name) / "secret.txt").write_bytes(b"ngoai thu muc goc")
        self.adapter = FilesystemStorageAdapter(self.root)

    def test_read_and_metadata(self):
        self.assertEqual(self.adapter.read_bytes("2026/a.pdf"), b"%PDF-1.4 noi dung")
        self.assertEqual(self.adapter.metadata("2026/a.pdf").kich_thuoc, len(b"%PDF-1.4 noi dung"))

    def test_rejects_path_traversal(self):
        with self.assertRaises(StorageError):
            self.adapter.read_bytes("../secret.txt")

    def test_rejects_absolute_and_empty(self):
        with self.assertRaises(StorageError):
            self.adapter.read_bytes(str(Path(self._tmp.name) / "secret.txt"))
        with self.assertRaises(StorageError):
            self.adapter.read_bytes("")

    def test_missing_file_and_directory(self):
        with self.assertRaises(StorageError):
            self.adapter.read_bytes("2026/khong-co.pdf")
        with self.assertRaises(StorageError):
            self.adapter.read_bytes("2026")

    @override_settings(SIGNING_DOCUMENT_ROOT="", DEBUG=False)
    def test_requires_root_configuration(self):
        with self.assertRaises(StorageError):
            FilesystemStorageAdapter()

    @override_settings(SIGNING_DOCUMENT_ROOT="", DEBUG=True)
    def test_dev_falls_back_to_media_signing(self):
        self.assertEqual(FilesystemStorageAdapter().root.parts[-2:], ("media", "signing"))

    def test_save_bytes_creates_new_relative_file_and_never_overwrites(self):
        meta1 = self.adapter.save_bytes(b"%PDF-1", "trinh_ky", "pdf")
        meta2 = self.adapter.save_bytes(b"%PDF-2", "trinh_ky", "pdf")
        self.assertNotEqual(meta1.vi_tri_luu_tep, meta2.vi_tri_luu_tep)
        self.assertTrue(meta1.vi_tri_luu_tep.startswith("trinh_ky/") and meta1.vi_tri_luu_tep.endswith(".pdf"))
        self.assertEqual((self.adapter.read_bytes(meta1.vi_tri_luu_tep), meta1.kich_thuoc), (b"%PDF-1", 6))
        self.assertEqual(self.adapter.read_bytes(meta2.vi_tri_luu_tep), b"%PDF-2")
        self.assertEqual(list(self.root.rglob("*.tmp")), [])

    def test_save_bytes_rejects_escape(self):
        with self.assertRaises(StorageError):
            self.adapter.save_bytes(b"x", "../ngoai", "pdf")
