"""SHA-256 helpers for document, image, and manifest integrity checks."""

import hashlib
import re

SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def is_sha256_hex(value: str) -> bool:
    return bool(SHA256_HEX_RE.fullmatch(value or ""))