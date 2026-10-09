import base64
import binascii
import hashlib
import hmac
import os
import re

from cryptography.exceptions import InvalidSignature, InvalidTag
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")
ALGORITHM = "Ed25519"


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def is_sha256_hex(value: str) -> bool:
    return bool(SHA256_HEX_RE.match(value or ""))


def _load_public_key(public_key_b64: str) -> Ed25519PublicKey:
    """Khóa công khai Ed25519 dạng 32 byte thô, mã hóa Base64."""
    raw = base64.b64decode(public_key_b64, validate=True)
    return Ed25519PublicKey.from_public_bytes(raw)


def key_fingerprint(public_key_b64: str) -> str:
    """Dấu vân tay khóa = SHA-256 (hex) của 32 byte khóa công khai thô."""
    raw = base64.b64decode(public_key_b64, validate=True)
    return sha256_hex(raw)


def is_valid_public_key(public_key_b64: str) -> bool:
    try:
        _load_public_key(public_key_b64)
    except (ValueError, binascii.Error):
        return False
    return True


def verify_signature(public_key_b64: str, message: bytes, signature_b64: str) -> bool:
    """True khi chữ ký Base64 hợp lệ với message; mọi đầu vào sai định dạng trả False."""
    try:
        key = _load_public_key(public_key_b64)
        signature = base64.b64decode(signature_b64, validate=True)
        key.verify(signature, message)
    except (InvalidSignature, ValueError, binascii.Error):
        return False
    return True


# ─────────────────────────────────────────────────────────────────────────────
# Phase 6 — bảo vệ khóa ký bằng PIN (signing-backend-plan.md mục 3.4)
# Server không nhận PIN: client gửi verifier = HKDF(Argon2id(PIN), "verify") (32 byte).
# Server lưu HMAC(verifier) và k_srv mã hóa AES-256-GCM; khóa của hai thao tác này
# dẫn xuất từ bí mật máy chủ nên lộ CSDL không đủ để thử PIN hay lấy k_srv.
# ─────────────────────────────────────────────────────────────────────────────

PIN_VERIFIER_BYTES = 32
SERVER_SHARE_BYTES = 32
_NONCE_BYTES = 12
_SUBKEY_SALT = b"tlbm-signing-pin-v1"


def derive_subkey(secret: bytes, label: str) -> bytes:
    """Khóa con 32 byte cho từng mục đích (nhãn khác nhau -> khóa độc lập)."""
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=_SUBKEY_SALT, info=label.encode()).derive(secret)


def decode_b64_exact(value: str, length: int):
    """Giải mã Base64 chặt chẽ; trả None nếu sai định dạng hoặc sai độ dài."""
    try:
        raw = base64.b64decode(value or "", validate=True)
    except (ValueError, binascii.Error):
        return None
    return raw if len(raw) == length else None


def hash_pin_verifier(verifier: bytes, mac_key: bytes) -> str:
    return hmac.new(mac_key, verifier, hashlib.sha256).hexdigest()


def verify_pin_verifier(verifier: bytes, mac_key: bytes, stored_hex: str) -> bool:
    return hmac.compare_digest(hash_pin_verifier(verifier, mac_key), stored_hex or "")


def new_server_share() -> bytes:
    return os.urandom(SERVER_SHARE_BYTES)


def encrypt_server_share(share: bytes, enc_key: bytes, aad: bytes) -> str:
    """Base64(nonce || ciphertext+tag); aad gắn bản mã với đúng khóa ký."""
    nonce = os.urandom(_NONCE_BYTES)
    return base64.b64encode(nonce + AESGCM(enc_key).encrypt(nonce, share, aad)).decode()


def decrypt_server_share(token: str, enc_key: bytes, aad: bytes) -> bytes:
    """Ném ValueError nếu bản mã bị sửa, sai khóa máy chủ hoặc sai khóa ký."""
    try:
        raw = base64.b64decode(token, validate=True)
        return AESGCM(enc_key).decrypt(raw[:_NONCE_BYTES], raw[_NONCE_BYTES:], aad)
    except (InvalidTag, ValueError, binascii.Error) as exc:
        raise ValueError("Không giải mã được mảnh bí mật máy chủ.") from exc
