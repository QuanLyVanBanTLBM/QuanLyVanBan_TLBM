"""MFA qua email khi ký, lưu PostgreSQL, tắt mặc định (issue #509, phân vùng 2 của #447)."""

import re
from datetime import timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from signing.errors import SigningError
from signing.models import SigningAuditLog, SigningMfaOtp, SigningSignature
from signing.services import mfa_ky

from .helpers import cap_quyen
from .test_hanh_dong_ky_phase8 import HASH, KyBase, chay_song_song, ma_loi

User = get_user_model()
MFA = "/api/v1/signing/mfa"
EMAIL_KIEM_THU = override_settings(SIGNING_EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
MFA_BAT = override_settings(SIGNING_MFA_EMAIL_ENABLED=True)
BI_MAT_KIEM_THU = override_settings(SIGNING_PIN_SECRET="pin-test-secret", SIGNING_KEY_PEPPER="pepper-test")


def ma_trong_thu():
    return re.search(r"\b(\d{6})\b", mail.outbox[-1].body).group(1)


def phien_moi(jti="jti-1", gio=8):
    return mfa_ky.Phien(jti, timezone.now() + timedelta(hours=gio))


@BI_MAT_KIEM_THU
@EMAIL_KIEM_THU
@MFA_BAT
class MfaDichVuTests(TestCase):
    def setUp(self):
        self.u1 = User.objects.create_user("u1", email="u1@example.test")
        self.u2 = User.objects.create_user("u2", email="u2@example.test")
        self.phien = phien_moi()
        mail.outbox.clear()

    def loi(self, fn, *args, **kwargs):
        with self.assertRaises(SigningError) as ctx:
            fn(*args, **kwargs)
        return ctx.exception

    def ma_sai(self):
        return "000000" if ma_trong_thu() != "000000" else "111111"

    def test_flag_is_off_by_default(self):
        with override_settings(SIGNING_MFA_EMAIL_ENABLED=None), mock.patch.dict("os.environ", {}, clear=False):
            with mock.patch.dict("os.environ", {"SIGNING_MFA_EMAIL_ENABLED": ""}):
                self.assertFalse(mfa_ky.dang_bat())
            with mock.patch.dict("os.environ", {"SIGNING_MFA_EMAIL_ENABLED": "true"}):
                self.assertTrue(mfa_ky.dang_bat())
        with override_settings(SIGNING_MFA_EMAIL_ENABLED=False):
            self.assertFalse(mfa_ky.dang_bat())
            self.assertEqual(self.loi(mfa_ky.yeu_cau_ma, self.u1).get_codes(), "mfa_chua_bat")
            mfa_ky.kiem_tra_da_xac_thuc(self.u1, None)  # cờ tắt: không chặn
        self.assertEqual(len(mail.outbox), 0)

    def test_request_sends_email_and_stores_only_hash(self):
        het_han = mfa_ky.yeu_cau_ma(self.u1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["u1@example.test"])
        ma = ma_trong_thu()
        ban_ghi = SigningMfaOtp.objects.get()
        self.assertNotIn(ma, ban_ghi.ma_bam)
        self.assertEqual(len(ban_ghi.ma_bam), 64)
        self.assertEqual((ban_ghi.muc_dich, ban_ghi.so_lan_sai, ban_ghi.da_dung_luc), ("KY", 0, None))
        self.assertTrue(timedelta(minutes=9) < het_han - timezone.now() <= timedelta(minutes=10))
        self.assertIn("Mã xác thực ký", mail.outbox[0].body)
        self.assertIn("Signing verification code", mail.outbox[0].body)

    def test_correct_code_authenticates_only_this_user_and_token(self):
        mfa_ky.yeu_cau_ma(self.u1)
        self.assertIsNone(mfa_ky.het_han_xac_thuc(self.u1, self.phien))
        self.assertEqual(self.loi(mfa_ky.kiem_tra_da_xac_thuc, self.u1, self.phien).get_codes(), "mfa_chua_xac_thuc")
        het_han = mfa_ky.xac_minh_ma(self.u1, ma_trong_thu(), self.phien)
        self.assertEqual(het_han, self.phien.het_han)
        mfa_ky.kiem_tra_da_xac_thuc(self.u1, self.phien)
        self.assertEqual(self.loi(mfa_ky.kiem_tra_da_xac_thuc, self.u1, phien_moi("jti-khac")).get_codes(),
                         "mfa_chua_xac_thuc")  # access token khác
        self.assertEqual(self.loi(mfa_ky.kiem_tra_da_xac_thuc, self.u2, self.phien).get_codes(), "mfa_chua_xac_thuc")
        self.assertEqual(self.loi(mfa_ky.kiem_tra_da_xac_thuc, self.u1, None).get_codes(), "mfa_chua_xac_thuc")

    def test_authentication_lasts_until_token_expiry(self):
        mfa_ky.yeu_cau_ma(self.u1)
        mfa_ky.xac_minh_ma(self.u1, ma_trong_thu(), self.phien)
        SigningMfaOtp.objects.update(phien_het_han=timezone.now() - timedelta(seconds=1))
        self.assertEqual(self.loi(mfa_ky.kiem_tra_da_xac_thuc, self.u1, self.phien).get_codes(), "mfa_chua_xac_thuc")

    def test_code_is_single_use(self):
        mfa_ky.yeu_cau_ma(self.u1)
        ma = ma_trong_thu()
        mfa_ky.xac_minh_ma(self.u1, ma, self.phien)
        self.assertEqual(self.loi(mfa_ky.xac_minh_ma, self.u1, ma, phien_moi("jti-2")).get_codes(), "mfa_ma_da_dung")
        self.assertIsNone(mfa_ky.het_han_xac_thuc(self.u1, phien_moi("jti-2")))

    def test_wrong_code_counts_and_fifth_cancels(self):
        mfa_ky.yeu_cau_ma(self.u1)
        ma_dung = ma_trong_thu()
        for lan in range(1, 5):
            loi = self.loi(mfa_ky.xac_minh_ma, self.u1, self.ma_sai(), self.phien)
            self.assertEqual(loi.get_codes(), "mfa_ma_sai")
            self.assertEqual(loi.fields["so_lan_con_lai"], [5 - lan])
        loi = self.loi(mfa_ky.xac_minh_ma, self.u1, self.ma_sai(), self.phien)
        self.assertEqual(loi.get_codes(), "mfa_vuot_gioi_han_nhap")
        self.assertEqual(SigningMfaOtp.objects.get().so_lan_sai, 5)
        # Mã bị hủy: nhập mã đúng cũng không được, không có lần thứ 6
        self.assertEqual(self.loi(mfa_ky.xac_minh_ma, self.u1, ma_dung, self.phien).get_codes(),
                         "mfa_vuot_gioi_han_nhap")
        self.assertEqual(SigningMfaOtp.objects.get().so_lan_sai, 5)
        self.assertIsNone(mfa_ky.het_han_xac_thuc(self.u1, self.phien))

    def test_cancel_after_wrong_attempts_keeps_send_interval(self):
        mfa_ky.yeu_cau_ma(self.u1)
        for _ in range(5):
            self.loi(mfa_ky.xac_minh_ma, self.u1, self.ma_sai(), self.phien)
        self.assertEqual(self.loi(mfa_ky.yeu_cau_ma, self.u1).status_code, 429)

    def test_expired_code_rejected(self):
        mfa_ky.yeu_cau_ma(self.u1)
        SigningMfaOtp.objects.update(het_han=timezone.now() - timedelta(seconds=1))
        self.assertEqual(self.loi(mfa_ky.xac_minh_ma, self.u1, ma_trong_thu(), self.phien).get_codes(),
                         "mfa_ma_het_han")

    def test_no_code_and_bad_format(self):
        self.assertEqual(self.loi(mfa_ky.xac_minh_ma, self.u1, "123456", self.phien).get_codes(), "mfa_ma_khong_co")
        for ma in ("12345", "abcdef", "1234567", ""):
            self.assertEqual(self.loi(mfa_ky.xac_minh_ma, self.u1, ma, self.phien).get_codes(), "ma_khong_hop_le")
        self.assertEqual(self.loi(mfa_ky.xac_minh_ma, self.u1, "123456", None).get_codes(), "phien_khong_hop_le")

    def test_code_of_another_user_rejected(self):
        mfa_ky.yeu_cau_ma(self.u1)
        ma_u1 = ma_trong_thu()
        # u2 chưa có mã
        self.assertEqual(self.loi(mfa_ky.xac_minh_ma, self.u2, ma_u1, self.phien).get_codes(), "mfa_ma_khong_co")
        # u2 có mã riêng: mã của u1 không hợp lệ cho u2 (nếu trùng ngẫu nhiên thì băm vẫn ràng buộc theo người dùng)
        SigningMfaOtp.objects.create(nguoi_dung=self.u2, ma_bam=mfa_ky._bam(self.u2.pk, "654321"),
                                     het_han=timezone.now() + timedelta(minutes=5))
        if ma_u1 != "654321":
            self.assertEqual(self.loi(mfa_ky.xac_minh_ma, self.u2, ma_u1, self.phien).get_codes(), "mfa_ma_sai")
        self.assertNotEqual(mfa_ky._bam(self.u1.pk, "123456"), mfa_ky._bam(self.u2.pk, "123456"))
        self.assertIsNone(mfa_ky.het_han_xac_thuc(self.u2, self.phien))

    def test_resend_interval_and_new_code_invalidates_old(self):
        mfa_ky.yeu_cau_ma(self.u1)
        ma_cu = ma_trong_thu()
        loi = self.loi(mfa_ky.yeu_cau_ma, self.u1)
        self.assertEqual((loi.get_codes(), loi.status_code), ("gui_ma_qua_nhanh", 429))
        self.assertIn("thu_lai_sau", loi.fields)
        self.assertEqual(len(mail.outbox), 1)
        SigningMfaOtp.objects.update(created_at=timezone.now() - timedelta(minutes=3))
        mfa_ky.yeu_cau_ma(self.u1)
        self.assertEqual(len(mail.outbox), 2)
        ma_moi = ma_trong_thu()
        if ma_cu != ma_moi:
            self.assertEqual(self.loi(mfa_ky.xac_minh_ma, self.u1, ma_cu, self.phien).get_codes(), "mfa_ma_sai")
        mfa_ky.xac_minh_ma(self.u1, ma_moi, self.phien)
        mfa_ky.kiem_tra_da_xac_thuc(self.u1, self.phien)

    def test_failed_send_rolls_back_and_does_not_set_interval(self):
        with mock.patch.object(mfa_ky, "_gui_email", side_effect=OSError("smtp down")):
            loi = self.loi(mfa_ky.yeu_cau_ma, self.u1)
        self.assertEqual((loi.get_codes(), loi.status_code), ("gui_email_that_bai", 503))
        self.assertEqual(SigningMfaOtp.objects.count(), 0)
        mfa_ky.yeu_cau_ma(self.u1)  # gửi lại ngay được
        self.assertEqual(len(mail.outbox), 1)

    def test_account_without_email_rejected(self):
        u3 = User.objects.create_user("u3", email="")
        loi = self.loi(mfa_ky.yeu_cau_ma, u3)
        self.assertEqual((loi.get_codes(), loi.status_code), ("tai_khoan_chua_co_email", 400))
        self.assertEqual(SigningMfaOtp.objects.count(), 0)

    def test_unconfigured_email_refuses_and_never_sends(self):
        for backend in ("django.core.mail.backends.console.EmailBackend", "django.core.mail.backends.dummy.EmailBackend"):
            with override_settings(SIGNING_EMAIL_BACKEND=backend):
                self.assertFalse(mfa_ky.email_kha_dung())
                loi = self.loi(mfa_ky.yeu_cau_ma, self.u1)
                self.assertEqual((loi.get_codes(), loi.status_code), ("mfa_email_khong_kha_dung", 503))
        with override_settings(SIGNING_EMAIL_BACKEND="", MAILERS={"default": {
                "BACKEND": "django.core.mail.backends.console.EmailBackend"}}):
            self.assertFalse(mfa_ky.email_kha_dung())
        with override_settings(SIGNING_EMAIL_BACKEND="", MAILERS={"default": {
                "BACKEND": "django.core.mail.backends.smtp.EmailBackend", "OPTIONS": {"host": "smtp.example.test"}}}):
            self.assertTrue(mfa_ky.email_kha_dung())
        self.assertEqual(SigningMfaOtp.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_code_never_in_audit_log_or_application_log(self):
        bat_duoc = {}

        def gui_va_hong(tai_khoan, ma):
            bat_duoc["ma"] = ma
            raise OSError(f"loi gia lap {tai_khoan.pk}")

        with self.assertLogs("signing.services.mfa_ky", level="DEBUG") as nhat_ky_log:
            with mock.patch.object(mfa_ky, "_gui_email", side_effect=gui_va_hong):
                self.loi(mfa_ky.yeu_cau_ma, self.u1)
        self.assertNotIn(bat_duoc["ma"], "\n".join(nhat_ky_log.output))
        mfa_ky.yeu_cau_ma(self.u1)
        ma = ma_trong_thu()
        for lan in range(2):
            self.loi(mfa_ky.xac_minh_ma, self.u1, self.ma_sai(), self.phien)
        mfa_ky.xac_minh_ma(self.u1, ma, self.phien)
        hanh_dong = set(SigningAuditLog.objects.values_list("hanh_dong", flat=True))
        self.assertTrue({"YEU_CAU_MA_MFA_KY", "MA_MFA_KY_SAI", "XAC_MINH_MFA_KY"} <= hanh_dong)
        for dong in SigningAuditLog.objects.all():
            self.assertNotIn(ma, f"{dong.chi_tiet} {dong.du_lieu_kem_theo} {dong.hanh_dong}")

    def test_lazy_cleanup_keeps_active_sessions(self):
        mfa_ky.yeu_cau_ma(self.u1)
        mfa_ky.xac_minh_ma(self.u1, ma_trong_thu(), self.phien)
        cu = timezone.now() - timedelta(hours=3)
        SigningMfaOtp.objects.update(created_at=cu, het_han=cu)
        co_phien = SigningMfaOtp.objects.get()
        het_phien = SigningMfaOtp.objects.create(nguoi_dung=self.u2, ma_bam="x" * 64, het_han=cu)
        SigningMfaOtp.objects.filter(pk=het_phien.pk).update(created_at=cu)
        mfa_ky.yeu_cau_ma(self.u2)
        con_lai = set(SigningMfaOtp.objects.values_list("pk", flat=True))
        self.assertIn(co_phien.pk, con_lai)  # phiên còn hạn không bị xóa
        self.assertNotIn(het_phien.pk, con_lai)

    def test_phien_from_access_token(self):
        class Req:
            auth = AccessToken.for_user(self.u1)

        phien = mfa_ky.phien_tu_request(Req)
        self.assertEqual(phien.jti, str(Req.auth["jti"]))
        self.assertTrue(phien.het_han > timezone.now() + timedelta(hours=7))

        class KhongToken:
            auth = None

        self.assertIsNone(mfa_ky.phien_tu_request(KhongToken))


@BI_MAT_KIEM_THU
@EMAIL_KIEM_THU
@MFA_BAT
class MfaDongThoiTests(TransactionTestCase):
    def test_two_concurrent_requests_with_same_code_only_one_succeeds(self):
        u1 = User.objects.create_user("dt1", email="dt1@example.test")
        mfa_ky.yeu_cau_ma(u1)
        ma = ma_trong_thu()
        ket_qua = []

        def xac_minh(jti):
            def chay():
                ket_qua.append(mfa_ky.xac_minh_ma(u1, ma, phien_moi(jti)))
            return chay

        loi = chay_song_song(xac_minh("jti-a"), xac_minh("jti-b"))
        self.assertEqual(len(ket_qua), 1)
        self.assertEqual(len(loi), 1)
        self.assertEqual(ma_loi(loi[0]), "mfa_ma_da_dung")
        ban_ghi = SigningMfaOtp.objects.get()
        self.assertIsNotNone(ban_ghi.da_dung_luc)
        thanh_cong = [j for j in ("jti-a", "jti-b") if mfa_ky.het_han_xac_thuc(u1, mfa_ky.Phien(j, None)) is not None]
        self.assertEqual(thanh_cong, [ban_ghi.phien_jti])


@BI_MAT_KIEM_THU
@EMAIL_KIEM_THU
class MfaKyApiTests(KyBase):
    def setUp(self):
        super().setUp()
        for user in (self.ky1, self.ky2, self.ky3):
            User.objects.filter(pk=user.pk).update(email=f"{user.username}@example.test")
        mail.outbox.clear()

    def client_jwt(self, user, token=None):
        token = token or AccessToken.for_user(User.objects.get(pk=user.pk))
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        return client

    def ky_jwt(self, client, user, khoa="ky-1"):
        _, key = self.khoa[user.pk]
        body = {"khoa_ky": key.pk, "hash_tai_lieu": HASH, "pin": "123456"}
        return client.post(f"/api/v1/signing/trinh-ky/{self.pk}/ky/", body, format="json", secure=True,
                           HTTP_IDEMPOTENCY_KEY=khoa)

    def test_flag_off_signing_unchanged_and_toi_reports_off(self):
        client = self.client_jwt(self.ky1)
        self.assertEqual(client.get("/api/v1/signing/toi/").json()["mfa_ky"],
                         {"bat": False, "da_xac_thuc": False, "het_han": None})
        self.assertEqual(self.ky_jwt(client, self.ky1).status_code, 200)
        self.assertEqual(client.post(f"{MFA}/yeu-cau/").json()["code"], "mfa_chua_bat")

    @MFA_BAT
    def test_signing_blocked_until_code_verified_for_same_token(self):
        token = AccessToken.for_user(User.objects.get(pk=self.ky1.pk))
        client = self.client_jwt(self.ky1, token)
        toi = client.get("/api/v1/signing/toi/").json()["mfa_ky"]
        self.assertEqual((toi["bat"], toi["da_xac_thuc"], toi["het_han"]), (True, False, None))
        # Chưa xác thực: gọi thẳng API ký bị chặn, không tạo chữ ký
        tra_loi = self.ky_jwt(client, self.ky1)
        self.assertEqual((tra_loi.status_code, tra_loi.json()["code"]), (403, "mfa_chua_xac_thuc"))
        self.assertEqual(SigningSignature.objects.count(), 0)
        # Yêu cầu và xác minh mã
        tra_loi = client.post(f"{MFA}/yeu-cau/")
        self.assertEqual(tra_loi.status_code, 200)
        self.assertEqual(tra_loi.json()["gian_cach_giay"], 120)
        ma = ma_trong_thu()
        tra_loi = client.post(f"{MFA}/yeu-cau/")
        self.assertEqual((tra_loi.status_code, tra_loi.json()["code"]), (429, "gui_ma_qua_nhanh"))
        sai = client.post(f"{MFA}/xac-minh/", {"ma": "000000" if ma != "000000" else "111111"}, format="json")
        self.assertEqual((sai.status_code, sai.json()["code"]), (400, "mfa_ma_sai"))
        # Token khác (chưa xác thực) vẫn bị chặn dù mã đã gửi
        khac = self.client_jwt(self.ky1)
        self.assertEqual(self.ky_jwt(khac, self.ky1, "ky-khac").status_code, 403)
        dung = client.post(f"{MFA}/xac-minh/", {"ma": ma}, format="json")
        self.assertEqual(dung.status_code, 200)
        self.assertTrue(dung.json()["da_xac_thuc"])
        toi = client.get("/api/v1/signing/toi/").json()["mfa_ky"]
        self.assertEqual((toi["bat"], toi["da_xac_thuc"]), (True, True))
        self.assertIsNotNone(toi["het_han"])
        self.assertEqual(self.ky_jwt(client, self.ky1, "ky-ok").status_code, 200)
        self.assertEqual(SigningSignature.objects.count(), 1)
        # Người dùng khác dùng token của mình không thừa hưởng xác thực
        self.assertEqual(self.ky_jwt(self.client_jwt(self.ky2), self.ky2, "ky-2").status_code, 403)
        # Không lộ mã trong phản hồi
        self.assertNotIn(ma, sai.content.decode() + dung.content.decode())

    @MFA_BAT
    def test_force_authenticate_without_token_cannot_sign(self):
        tra_loi = self.ky(self.ky1)  # client force_authenticate: không có access token để gắn phiên
        self.assertEqual((tra_loi.status_code, tra_loi.json()["code"]), (403, "mfa_chua_xac_thuc"))

    @MFA_BAT
    def test_reject_and_revoke_not_blocked_by_mfa(self):
        client = self.client_jwt(self.ky1)
        tra_loi = client.post(f"/api/v1/signing/trinh-ky/{self.pk}/tu-choi/", {"ly_do_tu_choi": "Không đồng ý"},
                              format="json", HTTP_IDEMPOTENCY_KEY="tc-1")
        self.assertEqual(tra_loi.status_code, 200)

    @MFA_BAT
    def test_mfa_endpoints_need_sign_permission_and_unconfigured_email_returns_503(self):
        nguoi = User.objects.create_user("khong_quyen", email="kq@example.test")
        self.assertEqual(self.client_jwt(nguoi).post(f"{MFA}/yeu-cau/").status_code, 403)
        with override_settings(SIGNING_EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend"):
            tra_loi = self.client_jwt(self.ky1).post(f"{MFA}/yeu-cau/")
        self.assertEqual((tra_loi.status_code, tra_loi.json()["code"]), (503, "mfa_email_khong_kha_dung"))
        self.assertEqual(len(mail.outbox), 0)
