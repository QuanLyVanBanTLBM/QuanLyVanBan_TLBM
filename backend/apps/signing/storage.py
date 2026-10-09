import os
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings
from django.utils import timezone


class StorageError(Exception):
    """Vị trí lưu không hợp lệ hoặc tệp không đọc được."""


@dataclass(frozen=True)
class StoredFileMeta:
    vi_tri_luu_tep: str
    kich_thuoc: int


class DocumentStorageAdapter(ABC):
    """Đọc tệp văn bản theo `vi_tri_luu_tep`; nghiệp vụ ký không phụ thuộc cách lưu."""

    @abstractmethod
    def read_bytes(self, vi_tri_luu_tep: str) -> bytes: ...

    @abstractmethod
    def metadata(self, vi_tri_luu_tep: str) -> StoredFileMeta: ...

    @abstractmethod
    def save_bytes(self, data: bytes, thu_muc: str, duoi_tep: str) -> StoredFileMeta:
        """Ghi tệp mới, không bao giờ ghi đè; trả vị trí lưu tương đối."""


class FilesystemStorageAdapter(DocumentStorageAdapter):
    """Đọc từ thư mục gốc cấu hình; vị trí lưu là đường dẫn tương đối so với thư mục gốc."""

    def __init__(self, root: str | os.PathLike | None = None):
        root = root or getattr(settings, "SIGNING_DOCUMENT_ROOT", None)
        if not root and settings.DEBUG:
            # Dev: thư mục media đã được .gitignore; production bắt buộc cấu hình (checks.py, signing.E003)
            root = Path(settings.BASE_DIR) / "media" / "signing"
        if not root:
            raise StorageError("Chưa cấu hình SIGNING_DOCUMENT_ROOT.")
        self.root = Path(root).resolve()

    def _resolve(self, vi_tri_luu_tep: str) -> Path:
        if not vi_tri_luu_tep or os.path.isabs(vi_tri_luu_tep):
            raise StorageError("Vị trí lưu tệp phải là đường dẫn tương đối.")
        path = (self.root / vi_tri_luu_tep).resolve()
        if not path.is_relative_to(self.root):
            raise StorageError("Vị trí lưu tệp nằm ngoài thư mục gốc.")
        if not path.is_file():
            raise StorageError("Không tìm thấy tệp tại vị trí lưu.")
        return path

    def read_bytes(self, vi_tri_luu_tep: str) -> bytes:
        return self._resolve(vi_tri_luu_tep).read_bytes()

    def metadata(self, vi_tri_luu_tep: str) -> StoredFileMeta:
        path = self._resolve(vi_tri_luu_tep)
        return StoredFileMeta(vi_tri_luu_tep, path.stat().st_size)

    def save_bytes(self, data: bytes, thu_muc: str, duoi_tep: str) -> StoredFileMeta:
        hom_nay = timezone.localdate()
        vi_tri = f"{thu_muc}/{hom_nay:%Y}/{hom_nay:%m}/{uuid.uuid4().hex}.{duoi_tep}"
        path = (self.root / vi_tri).resolve()
        if not path.is_relative_to(self.root):
            raise StorageError("Vị trí lưu tệp nằm ngoài thư mục gốc.")
        path.parent.mkdir(parents=True, exist_ok=True)
        tam = path.with_suffix(path.suffix + ".tmp")
        with open(tam, "xb") as f:  # "x": không ghi đè tệp đã có
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tam, path)
        return StoredFileMeta(vi_tri, len(data))


def get_storage() -> DocumentStorageAdapter:
    """Adapter lưu trữ mặc định của phân hệ; thay bằng adapter khác (S3, ...) mà không đổi nghiệp vụ."""
    return FilesystemStorageAdapter()
