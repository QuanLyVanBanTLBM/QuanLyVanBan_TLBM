import os
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile

from backend.services.document_service import (
    DEFAULT_FILE_MODE,
    DEFAULT_DIR_MODE,
    cleanup_stale_staging_uploads,
    commit_staged_upload,
    ensure_dir_permissions,
    ensure_file_permissions,
    save_registry,
    stage_upload_file,
)


class AIUploadPermissionsTests(unittest.TestCase):
    def test_ensure_permissions_helpers(self):
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            test_file = temp_path / "sample.txt"
            test_file.write_text("sample content", encoding="utf-8")

            with patch.object(Path, "chmod") as mock_chmod:
                ensure_file_permissions(test_file, DEFAULT_FILE_MODE)
                mock_chmod.assert_called_with(DEFAULT_FILE_MODE)

            with patch.object(Path, "chmod") as mock_chmod:
                ensure_dir_permissions(temp_path, DEFAULT_DIR_MODE)
                mock_chmod.assert_called_with(DEFAULT_DIR_MODE)

            # Non-existent path should not call chmod or raise error
            non_existent = temp_path / "does_not_exist.txt"
            with patch.object(Path, "chmod") as mock_chmod:
                ensure_file_permissions(non_existent)
                mock_chmod.assert_not_called()
                ensure_dir_permissions(non_existent)
                mock_chmod.assert_not_called()

    def test_stage_upload_file_sets_permissions_and_cleans_stale_files(self):
        with TemporaryDirectory() as temp_dir:
            docs_dir = Path(temp_dir)
            staging_dir = docs_dir / ".staging"
            staging_dir.mkdir(parents=True, exist_ok=True)

            # Create a stale staging file (modified 2 hours ago)
            stale_file = staging_dir / "upload-stale.tmp"
            stale_file.write_text("old junk", encoding="utf-8")
            old_time = time.time() - 7200
            os.utime(stale_file, (old_time, old_time))

            upload = SimpleUploadedFile("report.pdf", b"pdf report content")

            with patch("backend.services.document_service.DOCS_DIR", docs_dir):
                staged_path, filename, is_reupload = stage_upload_file(upload)

                self.assertTrue(staged_path.exists())
                self.assertEqual(filename, "report.pdf")
                self.assertFalse(is_reupload)

                # The stale file should have been cleaned up automatically
                self.assertFalse(stale_file.exists())

                if os.name != "nt":
                    self.assertEqual(staged_path.stat().st_mode & 0o777, DEFAULT_FILE_MODE)

                # Cleanup
                staged_path.unlink(missing_ok=True)

    def test_commit_staged_upload_sets_permissions(self):
        with TemporaryDirectory() as temp_dir:
            docs_dir = Path(temp_dir)
            staging_dir = docs_dir / ".staging"
            staging_dir.mkdir(parents=True, exist_ok=True)

            staged_file = staging_dir / "upload-123.tmp"
            staged_file.write_bytes(b"content to commit")
            if os.name != "nt":
                os.chmod(staged_file, 0o600)  # Simulate mkstemp 0600

            with patch("backend.services.document_service.DOCS_DIR", docs_dir):
                final_path = commit_staged_upload(staged_file, "final_report.pdf")

                self.assertTrue(final_path.exists())
                self.assertFalse(staged_file.exists())
                self.assertEqual(final_path.name, "final_report.pdf")
                self.assertEqual(final_path.read_bytes(), b"content to commit")

                if os.name != "nt":
                    self.assertEqual(final_path.stat().st_mode & 0o777, DEFAULT_FILE_MODE)

    def test_save_registry_sets_permissions(self):
        with TemporaryDirectory() as temp_dir:
            registry_path = Path(temp_dir) / "doc_registry.json"

            with patch("backend.services.document_service.DOC_REGISTRY_PATH", registry_path):
                save_registry([{"filename": "test.pdf", "category": "General", "size": 100}])

                self.assertTrue(registry_path.exists())
                if os.name != "nt":
                    self.assertEqual(registry_path.stat().st_mode & 0o777, DEFAULT_FILE_MODE)

    def test_cleanup_stale_staging_uploads(self):
        with TemporaryDirectory() as temp_dir:
            staging_dir = Path(temp_dir)

            fresh_file = staging_dir / "upload-fresh.tmp"
            fresh_file.write_text("fresh", encoding="utf-8")

            stale_file = staging_dir / "upload-stale.tmp"
            stale_file.write_text("stale", encoding="utf-8")
            old_time = time.time() - 5000
            os.utime(stale_file, (old_time, old_time))

            unrelated_file = staging_dir / "notes.txt"
            unrelated_file.write_text("do not touch", encoding="utf-8")
            os.utime(unrelated_file, (old_time, old_time))

            cleaned = cleanup_stale_staging_uploads(staging_dir, max_age_seconds=3600)

            self.assertEqual(cleaned, 1)
            self.assertTrue(fresh_file.exists())
            self.assertFalse(stale_file.exists())
            self.assertTrue(unrelated_file.exists())
