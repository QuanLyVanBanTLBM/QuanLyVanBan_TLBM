from django.test import SimpleTestCase

from signing import crypto


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
