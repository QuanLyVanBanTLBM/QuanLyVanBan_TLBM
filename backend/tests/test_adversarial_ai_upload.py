import os
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile

from backend.services.ai_settings_service import save_ai_settings
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


class AdversarialAIUploadTests(unittest.TestCase):
    """Bộ kiểm thử phản biện (Adversarial Testing) cho cơ chế lưu trữ và phân quyền AI."""

    def test_adv_1_permission_bitmask_exactness(self):
        """Phản biện 1: Bitmask quyền truy cập phải chính xác tuyệt đối, cấm hở quyền cho others."""
        # 0o640: Owner có read (4) + write (2) = 6; Group có read (4) = 4; Others = 0
        self.assertEqual(DEFAULT_FILE_MODE, 0o640)
        self.assertEqual(DEFAULT_FILE_MODE & 0o007, 0, "Others tuyệt đối không được có bất kỳ quyền nào trên tệp")
        self.assertEqual(DEFAULT_FILE_MODE & 0o070, 0o040, "Group bắt buộc phải có đúng quyền đọc (r)")
        self.assertEqual(DEFAULT_FILE_MODE & 0o700, 0o600, "Owner bắt buộc phải có đủ quyền đọc + ghi (rw)")

        # 0o750: Owner có rwx (7); Group có r-x (5: đọc và duyệt thư mục); Others = 0
        self.assertEqual(DEFAULT_DIR_MODE, 0o750)
        self.assertEqual(DEFAULT_DIR_MODE & 0o007, 0, "Others tuyệt đối không được có quyền trong thư mục")
        self.assertEqual(DEFAULT_DIR_MODE & 0o070, 0o050, "Group bắt buộc phải có quyền đọc và duyệt thư mục (rx)")
        self.assertEqual(DEFAULT_DIR_MODE & 0o700, 0o700, "Owner bắt buộc phải có toàn quyền (rwx)")

    def test_adv_2_fault_tolerance_when_chmod_fails(self):
        """Phản biện 2: Nếu hệ thống tệp cấm chmod (NFS/CIFS/SELinux/Windows restriction), nghiệp vụ không được crash."""
        with TemporaryDirectory() as temp_dir:
            docs_dir = Path(temp_dir)
            registry_path = docs_dir / "doc_registry.json"
            upload = SimpleUploadedFile("document.txt", b"important content")

            with (
                patch("backend.services.document_service.DOCS_DIR", docs_dir),
                patch("backend.services.document_service.DOC_REGISTRY_PATH", registry_path),
                patch.object(Path, "chmod", side_effect=PermissionError("Filesystem restricts chmod")),
            ):
                # stage_upload_file không được văng lỗi
                staged_path, filename, is_reupload = stage_upload_file(upload)
                self.assertTrue(staged_path.exists())
                self.assertEqual(staged_path.read_bytes(), b"important content")

                # commit_staged_upload không được văng lỗi
                final_path = commit_staged_upload(staged_path, filename)
                self.assertTrue(final_path.exists())
                self.assertEqual(final_path.read_bytes(), b"important content")

                # save_registry không được văng lỗi
                save_registry([{"filename": filename, "category": "Test", "size": 17}])
                self.assertTrue(registry_path.exists())

    def test_adv_3_path_traversal_resilience(self):
        """Phản biện 3: Tên tệp chứa ký tự tấn công leo thang thư mục (Path Traversal) không được thoát khỏi DOCS_DIR."""
        with TemporaryDirectory() as temp_dir:
            docs_dir = Path(temp_dir) / "safe_docs"
            docs_dir.mkdir(parents=True, exist_ok=True)

            traversal_filenames = [
                "../../etc/passwd",
                "..\\..\\windows\\win.ini",
                "nested/folder/secret.pdf",
                "/root/hacked.sh",
            ]

            with patch("backend.services.document_service.DOCS_DIR", docs_dir):
                for malicious_name in traversal_filenames:
                    upload = SimpleUploadedFile(malicious_name, b"malicious content")
                    staged_path, filename, _ = stage_upload_file(upload)
                    final_path = commit_staged_upload(staged_path, filename)

                    # Tệp đích bắt buộc phải nằm bên trong docs_dir, không được văng ra ngoài
                    self.assertEqual(final_path.parent.resolve(), docs_dir.resolve())
                    self.assertNotIn("..", final_path.name)
                    self.assertNotIn("/", final_path.name)
                    self.assertNotIn("\\", final_path.name)

    def test_adv_4_concurrent_cleanup_does_not_delete_active_uploads(self):
        """Phản biện 4: Tiến trình dọn dẹp không bao giờ được xóa tệp đang upload dở hoặc mới tạo."""
        with TemporaryDirectory() as temp_dir:
            staging_dir = Path(temp_dir)

            # Tệp vừa tạo 5 giây trước (đang được tải lên hoặc vừa lập chỉ mục)
            active_upload = staging_dir / "upload-active-123.tmp"
            active_upload.write_bytes(b"in-flight upload payload")

            # Tệp mồ côi 3 giờ trước
            orphan_upload = staging_dir / "upload-orphan-456.tmp"
            orphan_upload.write_bytes(b"old dead payload")
            old_time = time.time() - (3 * 3600)
            os.utime(orphan_upload, (old_time, old_time))

            # Chạy dọn dẹp với ngưỡng mặc định 1 giờ (3600s)
            cleaned = cleanup_stale_staging_uploads(staging_dir, max_age_seconds=3600)

            self.assertEqual(cleaned, 1)
            self.assertTrue(active_upload.exists(), "Tệp đang hoạt động tuyệt đối không được bị xóa")
            self.assertFalse(orphan_upload.exists(), "Tệp mồ côi quá hạn bắt buộc phải bị dọn sạch")

    def test_adv_5_save_ai_settings_chmod_resilience(self):
        """Phản biện 5: save_ai_settings phải bọc bắt lỗi nếu chmod thất bại."""
        with TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            (temp_root / "backend").mkdir()
            settings_path = temp_root / "ai_settings.json"

            with (
                patch.dict("os.environ", {}, clear=False),
                patch("backend.services.ai_settings_service.get_settings_file_path", return_value=settings_path),
                patch.multiple(
                    "backend.services.ai_settings_service.config",
                    BASE_DIR=temp_root,
                    DATA_DIR=temp_root,
                    OPENAI_API_KEY="",
                    MODEL_PROVIDER="openai",
                    LLM_MODEL="gpt-6-luna",
                    EMBED_MODEL="text-embedding-3-large",
                    VISION_MODEL="gpt-6-luna",
                ),
                patch.object(Path, "chmod", side_effect=OSError("Read-only system")),
            ):
                result = save_ai_settings({"provider": "openai", "openai_api_key": "sk-dummy"})
                self.assertEqual(result.get("openai_api_key"), "sk-dummy")
                self.assertTrue(settings_path.exists())
                self.assertTrue((temp_root / "backend" / ".env").exists())

    def test_adv_6_save_ai_settings_skips_real_env_in_test_runtime(self):
        """Phản biện 6: Khi chạy test, save_ai_settings tuyệt đối không ghi đè .env thật của workspace."""
        repo_root = Path(__file__).resolve().parents[2]
        real_env = Path(__file__).resolve().parents[1] / ".env"
        before_stat = (real_env.stat().st_mtime_ns, real_env.stat().st_size) if real_env.exists() else None

        with TemporaryDirectory() as temp_dir:
            settings_path = Path(temp_dir) / "ai_settings.json"
            with (
                patch.dict("os.environ", {"PYTEST_CURRENT_TEST": "test_adv_6"}, clear=False),
                patch("backend.services.ai_settings_service.get_settings_file_path", return_value=settings_path),
                patch.multiple(
                    "backend.services.ai_settings_service.config",
                    BASE_DIR=repo_root,
                    OPENAI_API_KEY="",
                    MODEL_PROVIDER="openai",
                    LLM_MODEL="gpt-6-luna",
                    EMBED_MODEL="text-embedding-3-large",
                    VISION_MODEL="gpt-6-luna",
                ),
            ):
                save_ai_settings({"provider": "openai", "openai_api_key": "sk-dummy-guard"})
                self.assertTrue(settings_path.exists())

        after_stat = (real_env.stat().st_mtime_ns, real_env.stat().st_size) if real_env.exists() else None
        self.assertEqual(after_stat, before_stat)


if __name__ == "__main__":
    unittest.main()
