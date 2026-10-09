from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from signing import enums
from signing.models import SigningKey, SigningProcess, SigningProcessStep

User = get_user_model()


def make_key(user, ma="k1", fp="a" * 64, **kw):
    return SigningKey.objects.create(
        nguoi_so_huu=user, ma_khoa=ma, dau_van_tay=fp, khoa_cong_khai="x",
        ngay_hieu_luc=timezone.now(), **kw,
    )


class SigningKeyConstraintTests(TestCase):
    def setUp(self):
        self.u1 = User.objects.create_user("u1")
        self.u2 = User.objects.create_user("u2")

    def test_default_state_is_pending_activation(self):
        self.assertEqual(make_key(self.u1).trang_thai, enums.TrangThaiKhoa.CHO_KICH_HOAT)

    def test_active_key_requires_ownership_proof(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_key(self.u1, trang_thai=enums.TrangThaiKhoa.HOAT_DONG)

    def test_one_active_key_per_owner(self):
        now = timezone.now()
        make_key(self.u1, "k1", "a" * 64, trang_thai=enums.TrangThaiKhoa.HOAT_DONG, thoi_diem_xac_minh_so_huu=now)
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_key(self.u1, "k2", "b" * 64, trang_thai=enums.TrangThaiKhoa.HOAT_DONG, thoi_diem_xac_minh_so_huu=now)
        make_key(self.u2, "k3", "c" * 64, trang_thai=enums.TrangThaiKhoa.HOAT_DONG, thoi_diem_xac_minh_so_huu=now)

    def test_many_non_active_keys_allowed(self):
        make_key(self.u1, "k1", "a" * 64, trang_thai=enums.TrangThaiKhoa.THU_HOI)
        make_key(self.u1, "k2", "b" * 64, trang_thai=enums.TrangThaiKhoa.THU_HOI)
        self.assertEqual(SigningKey.objects.filter(nguoi_so_huu=self.u1).count(), 2)

    def test_ma_khoa_and_fingerprint_unique(self):
        make_key(self.u1, "k1", "a" * 64)
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_key(self.u2, "k1", "b" * 64)
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_key(self.u2, "k9", "a" * 64)

    def test_no_private_key_field(self):
        names = {f.name for f in SigningKey._meta.get_fields()}
        self.assertFalse({n for n in names if "rieng" in n or "private" in n or "bi_mat" in n})


class SigningProcessConstraintTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("u1")

    def _process(self, ma="QT1", phien_ban=1):
        return SigningProcess.objects.create(
            ma_quy_trinh=ma, ten_quy_trinh="Quy trình", phien_ban=phien_ban,
            pham_vi=enums.PhamViQuyTrinh.CONG_TY,
            create_by=self.user,
        )

    def test_defaults(self):
        self.assertEqual(self._process().trang_thai, enums.TrangThaiQuyTrinh.NHAP)

    def test_unique_code_and_version(self):
        self._process("QT1", 1)
        self._process("QT1", 2)
        self._process("QT2", 1)
        with self.assertRaises(IntegrityError), transaction.atomic():
            self._process("QT1", 1)

    def test_step_unique_order_within_process(self):
        p1, p2 = self._process("A"), self._process("B")
        SigningProcessStep.objects.create(quy_trinh=p1, cap_ky=1, ten_cap_ky="Cấp 1", thu_tu=1)
        SigningProcessStep.objects.create(quy_trinh=p2, cap_ky=1, ten_cap_ky="Cấp 1", thu_tu=1)
        with self.assertRaises(IntegrityError), transaction.atomic():
            SigningProcessStep.objects.create(quy_trinh=p1, cap_ky=2, ten_cap_ky="Cấp 2", thu_tu=1)

    def test_step_defaults(self):
        s = SigningProcessStep.objects.create(quy_trinh=self._process(), cap_ky=1, ten_cap_ky="Cấp 1", thu_tu=1)
        self.assertTrue(s.dang_ap_dung)
        self.assertIsNone(s.don_vi_id)
