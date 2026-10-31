"""
Phase 8 (#80): ký, không đồng ý ban hành, thu hồi chữ ký; mở cấp tuần tự, ký song song trong cấp;
chống thao tác lặp và thao tác đồng thời.
"""

import base64
import hashlib
import shutil
import tempfile
import threading
import unittest
from datetime import timedelta
from unittest import mock

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TransactionTestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from signing import enums
from signing.models import (
    SigningAttempt, SigningAuditLog, SigningKey, SigningRequest, SigningRequestStep, SigningSignature,
)
from signing.services import hanh_dong_ky as hanh_dong_service
from signing.services import keys as key_service
from signing.services import process as process_service
from signing.services import trinh_ky as trinh_ky_service

from .helpers import cap_quyen
from .test_trinh_ky_phase7 import BASE, PDF, TrinhKyBase, VAN_BAN, tep_pdf

User = get_user_model()
HASH = hashlib.sha256(PDF).hexdigest()


def khoa_hoat_dong(user, ma):
    private = Ed25519PrivateKey.generate()
    raw = private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    key = key_service.dang_ky(user, ma_khoa=ma, khoa_cong_khai=base64.b64encode(raw).decode(),
                              ngay_hieu_luc=timezone.now() - timedelta(minutes=1))
    challenge = key_service.thach_thuc_so_huu(key).encode()
    key_service.xac_minh_so_huu(key, user, base64.b64encode(private.sign(challenge)).decode())
    key_service.kich_hoat(key, user)
    key.refresh_from_db()
    return private, key


def ky_so(private, hash_hex=HASH):
    return base64.b64encode(private.sign(bytes.fromhex(hash_hex))).decode()


def ma_loi(exc):
    """Mã lỗi nghiệp vụ của ngoại lệ API; lỗi khác (vd. deadlock) trả repr để test báo rõ."""
    return exc.get_codes() if hasattr(exc, "get_codes") else repr(exc)


def chay_song_song(*viec):
    """Chạy các thao tác trên luồng riêng (mỗi luồng một kết nối DB); trả về lỗi của luồng thua."""
    loi = []

    def bao(fn):
        try:
            fn()
        except Exception as exc:  # noqa: BLE001 — ghi nhận lỗi nghiệp vụ của luồng thua
            loi.append(exc)
        finally:
            connection.close()

    luong = [threading.Thread(target=bao, args=(fn,)) for fn in viec]
    for t in luong:
        t.start()
    for t in luong:
        t.join()
    return loi


class KyBase(TrinhKyBase):
    def setUp(self):
        super().setUp()
        self.khoa = {}
        for user in (self.ky1, self.ky2, self.ky3):
            cap_quyen(user, "sign_trinhky")
            self.khoa[user.pk] = khoa_hoat_dong(user, f"K-{user.username}")
        self.pk = self.ho_so_da_gui()["id"]

    def hanh_dong(self, user, action, khoa_thao_tac=None, **body):
        client = self.client_cua(User.objects.get(pk=user.pk))
        khoa = khoa_thao_tac or f"{action}-{user.pk}-{SigningSignature.objects.count()}"
        return client.post(f"{BASE}/{self.pk}/{action}/", body, format="json", HTTP_IDEMPOTENCY_KEY=khoa)

    def ky(self, user, khoa_thao_tac=None, **ghi_de):
        private, key = self.khoa[user.pk]
        body = {"khoa_ky": key.pk, "hash_tai_lieu": HASH, "chu_ky_so": ky_so(private)}
        body.update(ghi_de)
        return self.hanh_dong(user, "ky", khoa_thao_tac, **body)

    def nguoi_ky(self, data, ten):
        for cap in data["luot_trinh"][0]["cap_ky"]:
            for n in cap["nguoi_ky"]:
                if n["ten_nguoi_ky"] == ten:
                    return cap, n
        raise AssertionError(ten)


class LuongKyTests(KyBase):
    def test_full_flow_sequential_levels_and_blocking_initial(self):
        r = self.ky(self.ky1, ghi_chu_ky="Số liệu khớp")
        self.assertEqual(r.status_code, 200, r.data)
        cap1, kt = self.nguoi_ky(r.data, "ke_toan")
        _, pc = self.nguoi_ky(r.data, "phap_che")
        self.assertEqual((kt["trang_thai"], kt["chu_ky"]["ghi_chu_ky"]), ("DA_KY", "Số liệu khớp"))
        self.assertIsNotNone(pc["thoi_diem_mo"])  # người ký cùng cấp đã mở từ khi cấp mở
        self.assertEqual(cap1["trang_thai"], "DANG_KY")
        r = self.ky(self.ky2)
        cap1, _ = self.nguoi_ky(r.data, "phap_che")
        cap2, gd = self.nguoi_ky(r.data, "giam_doc")
        self.assertEqual((cap1["trang_thai"], cap2["trang_thai"]), ("HOAN_THANH", "DANG_KY"))
        self.assertIsNotNone(gd["thoi_diem_mo"])
        self.assertEqual(r.data["trang_thai"], "CHO_KY")
        r = self.ky(self.ky3)
        self.assertEqual((r.data["trang_thai"], r.data["luot_trinh"][0]["trang_thai"]), ("HOAN_THANH", "HOAN_THANH"))
        self.assertIsNotNone(r.data["ngay_hoan_thanh"])
        self.assertEqual(r.data["dang_cho"], [])
        chu_ky = SigningSignature.objects.filter(luot_trinh__trinh_ky_id=self.pk)
        self.assertEqual(chu_ky.count(), 3)
        self.assertTrue(all(c.trang_thai_xac_minh == "HOP_LE" and c.hash_tai_lieu == HASH for c in chu_ky))
        hanh_dong = list(SigningAuditLog.objects.filter(trinh_ky_id=self.pk).order_by("id").values_list("hanh_dong", flat=True))
        self.assertEqual(hanh_dong.count("KY"), 3)
        self.assertEqual(hanh_dong[-2:], ["HOAN_THANH_TRINH_KY", "CHOT_BANG_CHUNG"])  # tệp PDF sinh sau commit

    def test_parallel_signers_in_same_level_close_only_when_all_signed(self):
        self.process = self.tao_quy_trinh("SS", [
            {"cap_ky": 1, "ten_cap_ky": "Các phòng", "thu_tu": 1, "nguoi_ky": [
                {"nguoi_ky": self.ky1, "thu_tu": 1}, {"nguoi_ky": self.ky2, "thu_tu": 2}]},
            {"cap_ky": 2, "ten_cap_ky": "Giám đốc", "thu_tu": 2, "nguoi_ky": [{"nguoi_ky": self.ky3, "thu_tu": 1}]},
        ])
        self.pk = self.ho_so_da_gui()["id"]
        r = self.ky(self.ky2)  # người thứ hai ký trước: song song trong cấp
        cap1, _ = self.nguoi_ky(r.data, "ke_toan")
        self.assertEqual(cap1["trang_thai"], "DANG_KY")
        self.assertEqual(self.ky(self.ky3).data["code"], "khong_phai_nguoi_ky_dang_mo")  # cấp sau chưa mở
        r = self.ky(self.ky1)
        cap2, _ = self.nguoi_ky(r.data, "giam_doc")
        self.assertEqual(cap2["trang_thai"], "DANG_KY")

    def test_cannot_sign_before_turn(self):
        r = self.ky(self.ky3)  # cấp 2 chưa mở
        self.assertEqual((r.status_code, r.data["code"]), (403, "khong_phai_nguoi_ky_dang_mo"))
        r = self.hanh_dong(self.la, "ky", khoa_ky=1, hash_tai_lieu=HASH, chu_ky_so="x")
        self.assertEqual(r.status_code, 404)  # người ngoài không thấy hồ sơ

    def test_signature_checks(self):
        private, key = self.khoa[self.ky1.pk]
        r = self.ky(self.ky1, hash_tai_lieu="0" * 64)
        self.assertEqual((r.status_code, r.data["code"]), (409, "ma_bam_khong_khop"))
        r = self.ky(self.ky1, chu_ky_so=ky_so(Ed25519PrivateKey.generate()))
        self.assertEqual((r.status_code, r.data["code"]), (400, "chu_ky_khong_hop_le"))
        r = self.ky(self.ky1, khoa_ky=self.khoa[self.ky2.pk][1].pk)
        self.assertEqual((r.status_code, r.data["code"]), (400, "khoa_ky_khong_hop_le"))
        SigningKey.objects.filter(pk=key.pk).update(ngay_het_han=timezone.now() - timedelta(seconds=1))
        r = self.ky(self.ky1)
        self.assertEqual((r.status_code, r.data["code"]), (400, "khoa_ky_khong_hoat_dong"))  # khóa hết hạn
        SigningKey.objects.filter(pk=key.pk).update(ngay_het_han=None)
        key_service.thu_hoi(key, self.ky1, "Mất thiết bị")
        r = self.ky(self.ky1)
        self.assertEqual((r.status_code, r.data["code"]), (400, "khoa_ky_khong_hoat_dong"))
        self.assertFalse(SigningSignature.objects.exists())

    def test_sign_permission_required(self):
        User.objects.get(pk=self.ky1.pk).user_permissions.clear()
        r = self.ky(self.ky1)
        self.assertEqual((r.status_code, r.data["fields"]), (403, {"quyen": ["sign_trinhky"]}))

    def test_repeated_sign_with_same_key_is_idempotent(self):
        self.assertEqual(self.ky(self.ky1, khoa_thao_tac="k-ky").status_code, 200)
        self.assertEqual(self.ky(self.ky1, khoa_thao_tac="k-ky").status_code, 200)
        self.assertEqual(SigningSignature.objects.count(), 1)
        r = self.ky(self.ky1, khoa_thao_tac="k-khac")
        self.assertEqual((r.status_code, r.data["code"]), (409, "chua_den_luot_ky"))  # đã ký rồi

    def test_late_signature_is_recorded_not_blocked(self):
        SigningRequestStep.objects.filter(luot_trinh__trinh_ky_id=self.pk, thu_tu=1).update(
            han_xu_ly=timezone.now() - timedelta(hours=2))
        r = self.ky(self.ky1)
        _, kt = self.nguoi_ky(r.data, "ke_toan")
        self.assertTrue(kt["chu_ky"]["ky_tre_han"])
        self.assertGreaterEqual(kt["chu_ky"]["so_giay_tre"], 7200)

    def test_cancelled_request_cannot_be_signed(self):
        self.c.post(f"{BASE}/{self.pk}/huy/", {}, format="json", HTTP_IDEMPOTENCY_KEY="huy")
        r = self.ky(self.ky1)
        self.assertEqual((r.status_code, r.data["code"]), (409, "luot_trinh_khong_cho_ky"))


class TuChoiTests(KyBase):
    def test_reject_is_terminal_then_resubmit(self):
        r = self.hanh_dong(self.ky1, "tu-choi", ly_do_tu_choi="")
        self.assertEqual(r.status_code, 400)
        r = self.hanh_dong(self.ky3, "tu-choi", ly_do_tu_choi="Không đồng ý")  # cấp 2 chưa mở
        self.assertEqual((r.status_code, r.data["code"]), (403, "khong_phai_nguoi_ky_dang_mo"))
        r = self.hanh_dong(self.ky1, "tu-choi", "k-tc", ly_do_tu_choi="Sai căn cứ pháp lý")
        self.assertEqual((r.status_code, r.data["trang_thai"]), (200, "TU_CHOI"))
        self.assertEqual((r.data["ly_do_tu_choi"], r.data["luot_trinh"][0]["trang_thai"]),
                         ("Sai căn cứ pháp lý", "TU_CHOI"))
        self.assertEqual(self.hanh_dong(self.ky1, "tu-choi", "k-tc", ly_do_tu_choi="x").status_code, 200)  # lặp
        self.assertEqual(self.ky(self.ky1).data["code"], "luot_trinh_khong_cho_ky")
        moi = self.c.post(f"{BASE}/{self.pk}/trinh-lai/", {}, format="json", HTTP_IDEMPOTENCY_KEY="tl")
        self.assertEqual((moi.status_code, moi.data["ho_so_goc"]), (201, self.pk))


class ThuHoiTests(KyBase):
    def test_revoke_rules(self):
        r = self.hanh_dong(self.ky1, "thu-hoi")
        self.assertEqual((r.status_code, r.data["code"]), (409, "chua_ky_khong_thu_hoi"))
        self.ky(self.ky1)
        self.ky(self.ky2)  # cấp 1 đóng
        r = self.hanh_dong(self.ky1, "thu-hoi")
        self.assertEqual((r.status_code, r.data["code"]), (409, "cap_da_dong_khong_thu_hoi"))

    def test_revoke_while_level_open_keeps_old_signature(self):
        self.ky(self.ky1)
        cu = SigningSignature.objects.get()
        r = self.hanh_dong(self.ky1, "thu-hoi", "k-th")
        self.assertEqual(r.status_code, 200, r.data)
        _, dong = self.nguoi_ky(r.data, "ke_toan")
        self.assertEqual((dong["trang_thai"], dong["chu_ky"]), ("CHO_KY", None))
        self.assertTrue(SigningSignature.objects.filter(pk=cu.pk).exists())  # chữ ký cũ giữ làm bằng chứng
        log = SigningAuditLog.objects.get(hanh_dong="THU_HOI_CHU_KY")
        self.assertEqual(log.du_lieu_kem_theo["chu_ky_thu_hoi"], cu.pk)


@unittest.skipUnless(connection.vendor == "postgresql", "Cần PostgreSQL để kiểm tra khóa dòng đồng thời")
@override_settings(SIGNING_PIN_SECRET="bi-mat-test")
class DongThoiTests(TransactionTestCase):
    def setUp(self):
        self.thu_muc = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.thu_muc, ignore_errors=True)
        cai_dat = override_settings(SIGNING_DOCUMENT_ROOT=self.thu_muc)
        cai_dat.enable()
        self.addCleanup(cai_dat.disable)
        van_ban = mock.patch("signing.tich_hop.van_ban._doc_van_ban_di", side_effect=VAN_BAN.get)
        van_ban.start()
        self.addCleanup(van_ban.stop)
        self.tao = User.objects.create_user("tao")
        self.ky1 = User.objects.create_user("ky1")
        cap_quyen(self.tao, "add_trinhky", "send_trinhky", "view_vanbandi")
        cap_quyen(self.ky1, "sign_trinhky")
        from signing.services import process as process_service
        qt = process_service.tao_quy_trinh(self.tao, ma_quy_trinh="DT", ten_quy_trinh="DT", pham_vi="CONG_TY", cap_ky=[
            {"cap_ky": 1, "ten_cap_ky": "C", "thu_tu": 1, "nguoi_ky": [{"nguoi_ky": self.ky1, "thu_tu": 1}]}])
        qt = process_service.kich_hoat(qt, self.tao)
        self.ho_so = trinh_ky_service.tao_nhap(self.tao, quy_trinh=qt, tep=tep_pdf(),
                                               trich_yeu_van_ban="Tài liệu kiểm tra")
        self.ho_so = trinh_ky_service.gui(self.ho_so, self.tao, khoa_chong_trung="g")
        self.private, self.key = khoa_hoat_dong(self.ky1, "K-DT")

    def test_double_sign_with_different_keys_creates_one_signature(self):
        def ky(khoa):
            return lambda: hanh_dong_service.ky(self.ho_so, self.ky1, khoa_ky=self.key.pk, hash_tai_lieu=HASH,
                                                chu_ky_so=ky_so(self.private), khoa_chong_trung=khoa)
        loi = chay_song_song(ky("a"), ky("b"))
        self.assertEqual(SigningSignature.objects.count(), 1)
        self.assertEqual(len(loi), 1)
        self.assertIn(ma_loi(loi[0]), ("luot_trinh_khong_cho_ky", "chua_den_luot_ky"))  # lỗi nghiệp vụ, không deadlock
        self.assertEqual(SigningRequest.objects.get(pk=self.ho_so.pk).trang_thai, "HOAN_THANH")

    def test_sign_racing_cancel_has_single_consistent_outcome(self):
        loi = chay_song_song(
            lambda: hanh_dong_service.ky(self.ho_so, self.ky1, khoa_ky=self.key.pk, hash_tai_lieu=HASH,
                                         chu_ky_so=ky_so(self.private), khoa_chong_trung="ky"),
            lambda: trinh_ky_service.huy(self.ho_so, self.tao, khoa_chong_trung="huy"),
        )
        ho_so = SigningRequest.objects.get(pk=self.ho_so.pk)
        luot = SigningAttempt.objects.get(trinh_ky=ho_so)
        if ho_so.trang_thai == "HOAN_THANH":
            self.assertEqual((luot.trang_thai, SigningSignature.objects.count()), ("HOAN_THANH", 1))
        else:
            self.assertEqual((ho_so.trang_thai, luot.trang_thai, SigningSignature.objects.count()), ("HUY", "HUY", 0))
        self.assertEqual(len(loi), 1)
        # Bên thua nhận lỗi nghiệp vụ có mã (không phải deadlock do khóa ngược thứ tự)
        self.assertIn(ma_loi(loi[0]), ("luot_trinh_khong_cho_ky", "ho_so_da_ket_thuc"))
