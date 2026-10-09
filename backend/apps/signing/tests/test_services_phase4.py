import base64

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from signing import enums
from signing.errors import ConflictError, SigningError
from signing.models import SigningAuditLog, SigningKey, SigningProcess
from signing.services import keys as key_service
from signing.services import process as process_service

User = get_user_model()


def new_keypair():
    private = Ed25519PrivateKey.generate()
    raw = private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return private, base64.b64encode(raw).decode()


def sign_challenge(private, key):
    return base64.b64encode(private.sign(key_service.thach_thuc_so_huu(key).encode())).decode()


class ProcessServiceTests(TestCase):
    def setUp(self):
        self.u1 = User.objects.create_user("u1")
        self.u2 = User.objects.create_user("u2")

    def create(self, ma="QT1", cap_ky=None):
        cap_ky = cap_ky if cap_ky is not None else [
            {"cap_ky": 1, "ten_cap_ky": "Cấp 1", "thu_tu": 1,
             "nguoi_ky": [{"nguoi_ky": self.u2, "thu_tu": 1}]},
            {"cap_ky": 2, "ten_cap_ky": "Cấp 2", "thu_tu": 2,
             "nguoi_ky": [{"chuc_vu_id": 7, "thu_tu": 1, "vai_tro_ky": enums.VaiTroKy.KY_NHAY}]},
        ]
        return process_service.tao_quy_trinh(
            self.u1, ma_quy_trinh=ma, ten_quy_trinh="Quy trình", pham_vi=enums.PhamViQuyTrinh.CONG_TY, cap_ky=cap_ky,
        )

    def actions(self, process):
        return list(SigningAuditLog.objects.filter(loai_doi_tuong="signing_process", ma_doi_tuong=process.pk)
                    .order_by("id").values_list("hanh_dong", flat=True))

    def test_create_draft_with_steps_and_default_reminder(self):
        p = self.create()
        self.assertEqual(p.trang_thai, enums.TrangThaiQuyTrinh.NHAP)
        self.assertEqual(p.phien_ban, 1)
        self.assertEqual(p.cap_ky_set.count(), 2)
        self.assertEqual(p.cau_hinh_nhac_han, {"truoc_han_gio": [24], "dung_han": True})
        self.assertIn("TAO_QUY_TRINH", self.actions(p))

    def test_duplicate_code_rejected(self):
        self.create("QT1")
        with self.assertRaises(ConflictError) as ctx:
            self.create("QT1")
        self.assertEqual(ctx.exception.get_codes(), "quy_trinh_trung_ma")

    def test_signer_needs_exactly_one_of_person_or_position(self):
        with self.assertRaises(SigningError) as ctx:
            self.create("QT2", cap_ky=[{"cap_ky": 1, "ten_cap_ky": "C", "thu_tu": 1,
                                        "nguoi_ky": [{"thu_tu": 1}]}])
        self.assertEqual(ctx.exception.get_codes(), "nguoi_ky_hoac_chuc_vu")
        self.assertFalse(SigningProcess.objects.filter(ma_quy_trinh="QT2").exists())

    def test_duplicate_step_order_rejected(self):
        p = self.create()
        with self.assertRaises(ConflictError) as ctx:
            process_service.them_cap_ky(p, self.u1, cap_ky=3, ten_cap_ky="Trùng", thu_tu=1)
        self.assertEqual(ctx.exception.get_codes(), "cap_ky_trung_thu_tu")

    def test_cannot_activate_process_without_steps(self):
        p = self.create("QT3", cap_ky=[])
        with self.assertRaises(SigningError) as ctx:
            process_service.kich_hoat(p, self.u1)
        self.assertEqual(ctx.exception.get_codes(), "quy_trinh_khong_co_cap")

    def test_cannot_activate_step_without_signer(self):
        p = self.create("QT4", cap_ky=[{"cap_ky": 1, "ten_cap_ky": "C", "thu_tu": 1}])
        with self.assertRaises(SigningError) as ctx:
            process_service.kich_hoat(p, self.u1)
        self.assertEqual(ctx.exception.get_codes(), "cap_ky_khong_co_nguoi_ky")
        self.assertEqual(ctx.exception.fields, {"cap_ky_thieu_nguoi_ky": [1]})

    def test_activate_then_lock_editing(self):
        p = process_service.kich_hoat(self.create(), self.u1)
        self.assertEqual(p.trang_thai, enums.TrangThaiQuyTrinh.HOAT_DONG)
        with self.assertRaises(ConflictError) as ctx:
            process_service.them_cap_ky(p, self.u1, cap_ky=9, ten_cap_ky="Mới", thu_tu=9)
        self.assertEqual(ctx.exception.get_codes(), "quy_trinh_khong_the_sua")
        step = p.cap_ky_set.first()
        with self.assertRaises(ConflictError):
            process_service.them_nguoi_ky(step, self.u1, thu_tu=9, nguoi_ky=self.u1)
        with self.assertRaises(ConflictError):
            process_service.kich_hoat(p, self.u1)

    def test_deactivate_only_from_active(self):
        p = self.create()
        with self.assertRaises(ConflictError):
            process_service.ngung(p, self.u1)
        process_service.kich_hoat(p, self.u1)
        p = process_service.ngung(p, self.u1)
        self.assertEqual(p.trang_thai, enums.TrangThaiQuyTrinh.NGUNG)
        self.assertEqual(self.actions(p)[-2:], ["KICH_HOAT_QUY_TRINH", "NGUNG_QUY_TRINH"])

    def test_activating_new_version_stops_previous_active_version(self):
        v1 = process_service.kich_hoat(self.create(), self.u1)
        v2 = process_service.nhan_ban(v1, self.u1)
        v3 = process_service.nhan_ban(v1, self.u1)
        process_service.kich_hoat(v2, self.u1)
        trang_thai = dict(SigningProcess.objects.filter(ma_quy_trinh="QT1").values_list("phien_ban", "trang_thai"))
        self.assertEqual(trang_thai, {1: "NGUNG", 2: "HOAT_DONG", 3: "NHAP"})
        log = SigningAuditLog.objects.filter(ma_doi_tuong=v1.pk, hanh_dong="NGUNG_QUY_TRINH").get()
        self.assertEqual(log.du_lieu_kem_theo, {"thay_the_boi": v2.pk, "phien_ban_moi": 2})
        process_service.kich_hoat(v3, self.u1)
        self.assertEqual(SigningProcess.objects.filter(ma_quy_trinh="QT1", trang_thai="HOAT_DONG").get().pk, v3.pk)
        # mã khác không bị ảnh hưởng
        khac = process_service.kich_hoat(self.create("QT2"), self.u1)
        self.assertEqual(SigningProcess.objects.get(pk=khac.pk).trang_thai, "HOAT_DONG")
        self.assertEqual(SigningProcess.objects.get(pk=v3.pk).trang_thai, "HOAT_DONG")

    def test_clone_increments_version_and_copies_structure(self):
        p = process_service.kich_hoat(self.create(), self.u1)
        moi = process_service.nhan_ban(p, self.u2)
        self.assertEqual((moi.ma_quy_trinh, moi.phien_ban), (p.ma_quy_trinh, 2))
        self.assertEqual(moi.trang_thai, enums.TrangThaiQuyTrinh.NHAP)
        self.assertEqual(moi.create_by, self.u2)
        self.assertEqual(moi.cap_ky_set.count(), 2)
        self.assertEqual(sum(s.nguoi_ky_set.count() for s in moi.cap_ky_set.all()), 2)
        # bản gốc không đổi, bản mới sửa được
        self.assertEqual(SigningProcess.objects.get(pk=p.pk).trang_thai, enums.TrangThaiQuyTrinh.HOAT_DONG)
        process_service.them_cap_ky(moi, self.u2, cap_ky=3, ten_cap_ky="Cấp 3", thu_tu=3)
        # nhân bản lần nữa lấy phiên bản kế tiếp
        self.assertEqual(process_service.nhan_ban(p, self.u2).phien_ban, 3)


class KeyServiceTests(TestCase):
    def setUp(self):
        self.u1 = User.objects.create_user("u1")
        self.u2 = User.objects.create_user("u2")

    def register(self, user=None, ma="k1"):
        private, public = new_keypair()
        key = key_service.dang_ky(user or self.u1, ma_khoa=ma, khoa_cong_khai=public,
                                  ngay_hieu_luc=timezone.now(), dia_chi_ip="10.0.0.1")
        return private, key

    def verify(self, private, key, user=None):
        return key_service.xac_minh_so_huu(key, user or self.u1, sign_challenge(private, key))

    def test_register_computes_fingerprint_and_logs(self):
        _, key = self.register()
        self.assertEqual(key.trang_thai, enums.TrangThaiKhoa.CHO_KICH_HOAT)
        self.assertEqual(len(key.dau_van_tay), 64)
        entry = SigningAuditLog.objects.get(loai_doi_tuong="signing_key", ma_doi_tuong=key.pk)
        self.assertEqual((entry.hanh_dong, entry.dia_chi_ip), ("DANG_KY_KHOA", "10.0.0.1"))

    def test_register_rejects_invalid_or_duplicate_key(self):
        with self.assertRaises(SigningError) as ctx:
            key_service.dang_ky(self.u1, ma_khoa="x", khoa_cong_khai="not-a-key", ngay_hieu_luc=timezone.now())
        self.assertEqual(ctx.exception.get_codes(), "khoa_cong_khai_khong_hop_le")
        private, key = self.register(ma="k1")
        with self.assertRaises(ConflictError):
            key_service.dang_ky(self.u2, ma_khoa="k1", khoa_cong_khai=key.khoa_cong_khai, ngay_hieu_luc=timezone.now())

    def test_activation_requires_ownership_proof(self):
        private, key = self.register()
        with self.assertRaises(SigningError) as ctx:
            key_service.kich_hoat(key, self.u1)
        self.assertEqual(ctx.exception.get_codes(), "khoa_chua_xac_minh_so_huu")

    def test_wrong_proof_rejected(self):
        _, key = self.register()
        other_private, _ = new_keypair()
        with self.assertRaises(SigningError) as ctx:
            key_service.xac_minh_so_huu(key, self.u1, sign_challenge(other_private, key))
        self.assertEqual(ctx.exception.get_codes(), "chung_minh_so_huu_that_bai")
        key.refresh_from_db()
        self.assertIsNone(key.thoi_diem_xac_minh_so_huu)

    def test_only_owner_can_operate(self):
        private, key = self.register()
        for call in (
            lambda: key_service.xac_minh_so_huu(key, self.u2, sign_challenge(private, key)),
            lambda: key_service.kich_hoat(key, self.u2),
            lambda: key_service.thu_hoi(key, self.u2, "ly do"),
        ):
            with self.assertRaises(SigningError) as ctx:
                call()
            self.assertEqual(ctx.exception.status_code, 403)

    def test_verify_and_activate(self):
        private, key = self.register()
        self.verify(private, key)
        key = key_service.kich_hoat(key, self.u1)
        self.assertEqual(key.trang_thai, enums.TrangThaiKhoa.HOAT_DONG)
        self.assertIsNotNone(key.thoi_diem_kich_hoat)

    def test_second_activation_blocked_until_rotation(self):
        p1, k1 = self.register(ma="k1")
        self.verify(p1, k1)
        key_service.kich_hoat(k1, self.u1)
        p2, k2 = self.register(ma="k2")
        self.verify(p2, k2)
        with self.assertRaises(ConflictError) as ctx:
            key_service.kich_hoat(k2, self.u1)
        self.assertEqual(ctx.exception.get_codes(), "da_co_khoa_hoat_dong")

    def test_rotation_swaps_active_key_atomically(self):
        p1, k1 = self.register(ma="k1")
        self.verify(p1, k1)
        key_service.kich_hoat(k1, self.u1)
        p2, k2 = self.register(ma="k2")
        self.verify(p2, k2)
        moi = key_service.xoay_vong(k1, k2, self.u1)
        k1.refresh_from_db()
        self.assertEqual(moi.trang_thai, enums.TrangThaiKhoa.HOAT_DONG)
        self.assertEqual(k1.trang_thai, enums.TrangThaiKhoa.DA_XOAY_VONG)
        self.assertEqual(k1.khoa_thay_the_id, k2.pk)
        self.assertEqual(SigningKey.objects.filter(nguoi_so_huu=self.u1, trang_thai=enums.TrangThaiKhoa.HOAT_DONG).count(), 1)

    def test_rotation_rolls_back_when_new_key_unverified(self):
        p1, k1 = self.register(ma="k1")
        self.verify(p1, k1)
        key_service.kich_hoat(k1, self.u1)
        _, k2 = self.register(ma="k2")
        with self.assertRaises(SigningError):
            key_service.xoay_vong(k1, k2, self.u1)
        k1.refresh_from_db()
        self.assertEqual(k1.trang_thai, enums.TrangThaiKhoa.HOAT_DONG)
        self.assertIsNone(k1.khoa_thay_the_id)

    def test_revoke_requires_reason_and_is_final(self):
        private, key = self.register()
        with self.assertRaises(SigningError) as ctx:
            key_service.thu_hoi(key, self.u1, "  ")
        self.assertEqual(ctx.exception.get_codes(), "thieu_ly_do_thu_hoi")
        key = key_service.thu_hoi(key, self.u1, "Mất thiết bị")
        self.assertEqual(key.trang_thai, enums.TrangThaiKhoa.THU_HOI)
        self.assertIsNotNone(key.ngay_thu_hoi)
        with self.assertRaises(ConflictError):
            key_service.thu_hoi(key, self.u1, "Lần hai")
        entry = SigningAuditLog.objects.filter(hanh_dong="THU_HOI_KHOA").get()
        self.assertEqual((entry.trang_thai_sau, entry.chi_tiet), (enums.TrangThaiKhoa.THU_HOI, "Mất thiết bị"))

    def test_revoked_key_cannot_be_activated(self):
        private, key = self.register()
        self.verify(private, key)
        key_service.thu_hoi(key, self.u1, "Thu hồi")
        with self.assertRaises(ConflictError):
            key_service.kich_hoat(key, self.u1)

    def test_revoke_active_key_frees_slot_for_new_key(self):
        p1, k1 = self.register(ma="k1")
        self.verify(p1, k1)
        key_service.kich_hoat(k1, self.u1)
        key_service.thu_hoi(k1, self.u1, "Lộ khóa")
        p2, k2 = self.register(ma="k2")
        self.verify(p2, k2)
        self.assertEqual(key_service.kich_hoat(k2, self.u1).trang_thai, enums.TrangThaiKhoa.HOAT_DONG)
