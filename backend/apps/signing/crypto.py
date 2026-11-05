import base64
import binascii
import hashlib
import hmac
import os
import re

from argon2.low_level import Type as Argon2Type, hash_secret_raw
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
# `derive_subkey` is shared by email PIN-reset/MFA flows. The server-share helpers below
# are legacy Phase 6 primitives; server-side key signing uses the functions in the next section.
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


# ─────────────────────────────────────────────────────────────────────────────
# Khóa ký phía máy chủ (#447 partition 1)
# ─────────────────────────────────────────────────────────────────────────────

PRIVATE_KEY_PKCS8_BYTES = 48
_SIGNING_KEY_NONCE_BYTES = 12


def derive_signing_key_encryption_key(pepper: bytes, salt: bytes) -> bytes:
    """AES key is recoverable from the stable server pepper, independent of the user's PIN."""
    return HKDF(
        algorithm=hashes.SHA256(), length=32, salt=salt,
        info=b"tlbm-signing-private-key-encryption-v1",
    ).derive(pepper)


def derive_signing_pin_verifier(pin: str, pepper: bytes, salt: bytes, *, memory_cost: int,
                                time_cost: int, parallelism: int) -> str:
    """Argon2id verifier, domain-separated from AES key derivation; stored as 64 lowercase hex chars."""
    password = hmac.new(
        pepper, b"tlbm-signing-pin-verifier-v1\0" + pin.encode("ascii"), hashlib.sha256,
    ).digest()
    return hash_secret_raw(
        password, salt, time_cost=time_cost, memory_cost=memory_cost, parallelism=parallelism,
        hash_len=32, type=Argon2Type.ID, version=19,
    ).hex()


def encrypt_signing_private_key(private_key_pkcs8: bytes, key: bytes, aad: bytes) -> str:
    """Mã hóa PKCS#8 Ed25519 bằng AES-256-GCM; lưu Base64(nonce || ciphertext+tag)."""
    nonce = os.urandom(_SIGNING_KEY_NONCE_BYTES)
    ciphertext = AESGCM(key).encrypt(nonce, private_key_pkcs8, aad)
    return base64.b64encode(nonce + ciphertext).decode("ascii")


def decrypt_signing_private_key(token: str, key: bytes, aad: bytes) -> bytes:
    """Giải mã ciphertext gắn với đúng khóa; mọi lỗi xác thực trả ValueError chung."""
    try:
        raw = base64.b64decode(token or "", validate=True)
        if len(raw) < _SIGNING_KEY_NONCE_BYTES + 16:
            raise ValueError("ciphertext too short")
        return AESGCM(key).decrypt(raw[:_SIGNING_KEY_NONCE_BYTES], raw[_SIGNING_KEY_NONCE_BYTES:], aad)
    except (InvalidTag, ValueError, binascii.Error) as exc:
        raise ValueError("Không giải mã được khóa ký.") from exc


def load_ed25519_private_key(private_key_pkcs8: bytes):
    """Tải đúng định dạng PKCS#8 Ed25519 đã export từ WebCrypto."""
    if not isinstance(private_key_pkcs8, bytes) or len(private_key_pkcs8) != PRIVATE_KEY_PKCS8_BYTES:
        raise ValueError("PKCS#8 Ed25519 không hợp lệ.")
    try:
        private_key = serialization.load_der_private_key(private_key_pkcs8, password=None)
    except (TypeError, ValueError) as exc:
        raise ValueError("PKCS#8 Ed25519 không hợp lệ.") from exc
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    if not isinstance(private_key, Ed25519PrivateKey):
        raise ValueError("Chỉ chấp nhận private key Ed25519.")
    return private_key


def signing_private_key_matches_public(private_key_pkcs8: bytes, public_key_b64: str) -> bool:
    try:
        private_key = load_ed25519_private_key(private_key_pkcs8)
        public_key = private_key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw,
        )
        return hmac.compare_digest(public_key, base64.b64decode(public_key_b64, validate=True))
    except (ValueError, TypeError, binascii.Error):
        return False


def sign_with_private_key(private_key_pkcs8: bytes, message: bytes) -> str:
    """Ký bằng Ed25519; private-key bytes không được trả khỏi service."""
    return base64.b64encode(load_ed25519_private_key(private_key_pkcs8).sign(message)).decode("ascii")
