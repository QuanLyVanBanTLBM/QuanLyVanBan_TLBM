from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from documents.models import VanBanDi
from signing import enums
from signing.services.trinh_ky import dang_cho_toi_ky
from signing.models import SigningRequest, SigningRequestStepSigner

User = get_user_model()


class SeedSigningDemoTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("nguoi_ky_demo")

    def seed(self, user="nguoi_ky_demo"):
        call_command("seed_signing_demo", user=user, stdout=StringIO())

    def test_tao_3_cho_ky_1_da_ky_1_tu_choi_cho_dung_tai_khoan(self):
        self.seed()
        signers = SigningRequestStepSigner.objects.filter(nguoi_ky=self.user)
        self.assertEqual(signers.filter(trang_thai=enums.TrangThaiNguoiKy.CHO_KY).count(), 3)
        self.assertEqual(signers.filter(trang_thai=enums.TrangThaiNguoiKy.DA_KY).count(), 1)
        self.assertEqual(signers.filter(trang_thai=enums.TrangThaiNguoiKy.TU_CHOI).count(), 1)
        self.assertEqual(SigningRequest.objects.filter(trang_thai=enums.TrangThaiYeuCau.CHO_KY).count(), 3)
        self.assertEqual(dang_cho_toi_ky(self.user).count(), 3)

    def test_van_ban_va_nguoi_trinh_co_du_lieu_hien_thi(self):
        self.seed()
        for yc in SigningRequest.objects.all():
            van_ban = VanBanDi.objects.get(pk=yc.van_ban_id)
            self.assertTrue(van_ban.trich_yeu)
            self.assertTrue(yc.create_by.ho_ten)
            self.assertIsNotNone(yc.ngay_gui)

    def test_chay_lai_khong_tao_trung(self):
        self.seed()
        self.seed()
        self.assertEqual(SigningRequest.objects.count(), 5)
        self.assertEqual(VanBanDi.objects.count(), 5)

    def test_tai_khoan_khong_ton_tai(self):
        with self.assertRaises(CommandError):
            self.seed(user="khong_co")
