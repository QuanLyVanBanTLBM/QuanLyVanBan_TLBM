import base64

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from django.test import SimpleTestCase

from signing import crypto


def _keypair():
    private = Ed25519PrivateKey.generate()
    raw = private.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    return private, base64.b64encode(raw).decode()


class Sha256Tests(SimpleTestCase):
    def test_known_vector(self):
        self.assertEqual(
            crypto.sha256_hex(b"abc"),
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
        )

    def test_is_sha256_hex(self):
        self.assertTrue(crypto.is_sha256_hex("a" * 64))
        self.assertFalse(crypto.is_sha256_hex("A" * 64))
        self.assertFalse(crypto.is_sha256_hex("a" * 63))
        self.assertFalse(crypto.is_sha256_hex(""))
        self.assertFalse(crypto.is_sha256_hex(None))


class Ed25519Tests(SimpleTestCase):
    def setUp(self):
        self.private, self.public_b64 = _keypair()
        self.message = b"noi dung can ky"
        self.signature_b64 = base64.b64encode(self.private.sign(self.message)).decode()

    def test_valid_signature(self):
        self.assertTrue(crypto.verify_signature(self.public_b64, self.message, self.signature_b64))

    def test_tampered_message(self):
        self.assertFalse(crypto.verify_signature(self.public_b64, b"noi dung khac", self.signature_b64))

    def test_wrong_key(self):
        _, other_public = _keypair()
        self.assertFalse(crypto.verify_signature(other_public, self.message, self.signature_b64))

    def test_malformed_inputs_return_false(self):
        self.assertFalse(crypto.verify_signature("khong-phai-base64!", self.message, self.signature_b64))
        self.assertFalse(crypto.verify_signature(self.public_b64, self.message, "khong-phai-base64!"))
        self.assertFalse(crypto.verify_signature(base64.b64encode(b"short").decode(), self.message, self.signature_b64))
        self.assertFalse(crypto.verify_signature(self.public_b64, self.message, base64.b64encode(b"x").decode()))

    def test_fingerprint_is_sha256_of_raw_key(self):
        raw = base64.b64decode(self.public_b64)
        self.assertEqual(crypto.key_fingerprint(self.public_b64), crypto.sha256_hex(raw))

    def test_is_valid_public_key(self):
        self.assertTrue(crypto.is_valid_public_key(self.public_b64))
        self.assertFalse(crypto.is_valid_public_key(base64.b64encode(b"short").decode()))
        self.assertFalse(crypto.is_valid_public_key("khong-phai-base64!"))
