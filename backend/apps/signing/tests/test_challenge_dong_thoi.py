import base64
import threading

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TransactionTestCase
from django.utils import timezone

from signing.errors import SigningError
from signing.models import SigningChallengeDaDung
from signing.services import keys as key_service

User = get_user_model()


class ChallengeDongThoiTests(TransactionTestCase):
    """Hai request đồng thời cùng challenge: chỉ một request xác minh thành công (UNIQUE nguoi_dung + nonce)."""

    def test_concurrent_requests_only_one_succeeds(self):
        user = User.objects.create_user("dong-thoi")
        private = Ed25519PrivateKey.generate()
        public = base64.b64encode(
            private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        ).decode()
        key = key_service.dang_ky(user, ma_khoa="k-dt", khoa_cong_khai=public, ngay_hieu_luc=timezone.now())
        challenge = key_service.thach_thuc_so_huu(key)
        chu_ky = base64.b64encode(private.sign(challenge.encode())).decode()

        so_luong = 6
        rao = threading.Barrier(so_luong)
        ket_qua = []

        def chay():
            try:
                rao.wait()
                key_service.xac_minh_so_huu(key, user, challenge, chu_ky)
                ket_qua.append("ok")
            except SigningError as loi:
                ket_qua.append(loi.get_codes())
            finally:
                connection.close()

        luong = [threading.Thread(target=chay) for _ in range(so_luong)]
        for t in luong:
            t.start()
        for t in luong:
            t.join()

        self.assertEqual(ket_qua.count("ok"), 1, ket_qua)
        self.assertEqual(ket_qua.count("thach_thuc_da_dung"), so_luong - 1, ket_qua)
        self.assertEqual(SigningChallengeDaDung.objects.filter(nguoi_dung=user).count(), 1)

    def test_challenge_of_other_user_rejected(self):
        chu, khac = User.objects.create_user("chu"), User.objects.create_user("khac")
        private = Ed25519PrivateKey.generate()
        public = base64.b64encode(
            private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        ).decode()
        key = key_service.dang_ky(chu, ma_khoa="k-kh", khoa_cong_khai=public, ngay_hieu_luc=timezone.now())
        challenge = key_service.thach_thuc_so_huu(key)
        chu_ky = base64.b64encode(private.sign(challenge.encode())).decode()
        with self.assertRaises(SigningError) as ctx:
            key_service.xac_minh_so_huu(key, khac, challenge, chu_ky)
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertFalse(SigningChallengeDaDung.objects.exists())
