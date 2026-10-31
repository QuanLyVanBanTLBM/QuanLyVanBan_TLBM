from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient


class AIUploadReplacementTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(
            username="ai_upload_admin",
            password="test-password",
        )
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def test_duplicate_filename_requires_explicit_replacement(self):
        with TemporaryDirectory() as temporary_directory:
            docs_dir = Path(temporary_directory)
            original = docs_dir / "policy.txt"
            original.write_bytes(b"original document")
            upload = SimpleUploadedFile("policy.txt", b"replacement document content")

            with patch("backend.api.views.config.DOCS_DIR", docs_dir):
                response = self.client.post(
                    "/api/ai/upload/async",
                    {"file": upload},
                    format="multipart",
                )

            self.assertEqual(response.status_code, 409)
            self.assertEqual(response.json()["code"], "duplicate_filename")
            self.assertEqual(original.read_bytes(), b"original document")

    def test_index_failure_discards_staging_file_and_preserves_original(self):
        with TemporaryDirectory() as temporary_directory:
            docs_dir = Path(temporary_directory)
            staging_dir = docs_dir / ".staging"
            staging_dir.mkdir()
            original = docs_dir / "policy.txt"
            original.write_bytes(b"original document")
            staged = staging_dir / "replacement.txt"
            staged.write_bytes(b"replacement content that will fail to index")
            fake_rag = SimpleNamespace(index_document=MagicMock(side_effect=RuntimeError("embedding failed")))

            with (
                patch("backend.api.views.config.DOCS_DIR", docs_dir),
                patch("backend.services.document_service.DOCS_DIR", docs_dir),
                patch.dict("sys.modules", {"backend.services.rag_service": fake_rag}),
            ):
                from backend.api.views import _run_index_job

                _run_index_job("upload-job", staged, original.name)

            self.assertEqual(original.read_bytes(), b"original document")
            self.assertFalse(staged.exists())
