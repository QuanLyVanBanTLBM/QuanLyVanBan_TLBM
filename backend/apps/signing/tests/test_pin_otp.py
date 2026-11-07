"""PIN ký PBKDF2 độc lập với khóa; mặc định gửi OTP SMS, email là lựa chọn thay thế."""

from datetime import timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from signing.errors import SigningError
from signing.models import SigningAuditLog, SigningPinCredential, SigningPinOtpChallenge
from signing.services import pin, pin_otp

User = get_user_model()
PIN_CU = "482739"
PIN_MOI = "593817"


@override_settings(
    SIGNING_PIN_SECRET="test-pin-otp-secret",
    SIGNING_SMS_URL="https://sms.example.test/send",
    SIGNING_SMS_AUTHORIZATION="Basic test-only",
    SIGNING_SMS_FROM="TEST",
    SIGNING_EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class PinOtpTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("pin-user", email="pin-user@example.test", sdt="0900000000")

    def gui_otp_gia_lap(self):
        gui = mock.patch.object(pin_otp, "_gui_otp")
        mock_gui = gui.start()
        self.addCleanup(gui.stop)
        return mock_gui

    def tao_pin_cho(self, user=None, pin_moi=PIN_CU):
        return pin.dat_pin(user or self.user, pin_moi)

    def test_pin_credential_uses_pbkdf2_and_is_independent_of_key_records(self):
        credential = self.tao_pin_cho()

        self.assertEqual(credential.nguoi_dung_id, self.user.pk)
        self.assertTrue(credential.ma_bam_xac_minh_pin.startswith("pbkdf2_sha256$"))
        self.assertNotIn(PIN_CU, credential.ma_bam_xac_minh_pin)
        self.assertFalse(hasattr(credential, "khoa_bi_mat_ma_hoa"))
        self.assertTrue(pin.xac_thuc(self.user, PIN_CU))

    def test_fifth_wrong_pin_locks_for_30_minutes_and_sixth_is_not_counted(self):
        self.tao_pin_cho()

        for remaining in (4, 3, 2, 1):
            with self.assertRaises(SigningError) as ctx:
                pin.xac_thuc(self.user, "999999")
            self.assertEqual(ctx.exception.fields["so_lan_con_lai"], [remaining])

        with self.assertRaises(SigningError) as ctx:
            pin.xac_thuc(self.user, "999999")
        self.assertEqual(ctx.exception.get_codes(), "pin_bi_khoa_tam_thoi")
        self.assertEqual(ctx.exception.fields["so_lan_con_lai"], [0])

        credential = SigningPinCredential.objects.get(nguoi_dung=self.user)
        self.assertEqual(credential.so_lan_sai_ngay, 5)
        self.assertEqual(credential.so_lan_sai_chu_ky, 5)
        self.assertAlmostEqual((credential.khoa_den - timezone.now()).total_seconds(), 30 * 60, delta=3)

        with self.assertRaises(SigningError) as ctx:
            pin.xac_thuc(self.user, PIN_CU)
        self.assertEqual(ctx.exception.get_codes(), "pin_bi_khoa_tam_thoi")
        credential.refresh_from_db()
        self.assertEqual(credential.so_lan_sai_ngay, 5)

    def test_each_lock_starts_a_new_five_attempt_cycle_but_daily_cap_is_fifteen(self):
        credential = self.tao_pin_cho()
        for _ in range(5):
            with self.assertRaises(SigningError):
                pin.xac_thuc(self.user, "999999")
        credential.refresh_from_db()
        credential.khoa_den = timezone.now() - timedelta(seconds=1)
        credential.save(update_fields=["khoa_den"])

        for _ in range(5):
            with self.assertRaises(SigningError):
                pin.xac_thuc(self.user, "999999")
        credential.refresh_from_db()
        credential.khoa_den = timezone.now() - timedelta(seconds=1)
        credential.save(update_fields=["khoa_den"])

        for _ in range(5):
            with self.assertRaises(SigningError):
                pin.xac_thuc(self.user, "999999")

        credential.refresh_from_db()
        self.assertEqual(credential.so_lan_sai_ngay, 15)
        self.assertEqual(credential.so_lan_sai_chu_ky, 5)
        with self.assertRaises(SigningError) as ctx:
            pin.xac_thuc(self.user, PIN_CU)
        self.assertEqual(ctx.exception.get_codes(), "pin_het_luot_trong_ngay")

    def test_active_thirty_minute_lock_survives_local_midnight(self):
        credential = self.tao_pin_cho()
        khoa_den = timezone.now() + timedelta(minutes=20)
        hom_qua = timezone.localdate() - timedelta(days=1)
        credential.so_lan_sai_ngay = 5
        credential.so_lan_sai_chu_ky = 5
        credential.ngay_dem_sai = hom_qua
        credential.khoa_den = khoa_den
        credential.save(update_fields=["so_lan_sai_ngay", "so_lan_sai_chu_ky", "ngay_dem_sai", "khoa_den"])

        with mock.patch.object(pin.timezone, "localdate", return_value=timezone.localdate()):
            with self.assertRaises(SigningError) as ctx:
                pin.xac_thuc(self.user, PIN_CU)

        self.assertEqual(ctx.exception.get_codes(), "pin_bi_khoa_tam_thoi")
        credential.refresh_from_db()
        self.assertEqual(credential.so_lan_sai_ngay, 0)
        self.assertEqual(credential.so_lan_sai_chu_ky, 5)
        self.assertEqual(credential.khoa_den, khoa_den)

    def test_sms_is_default_and_pin_is_saved_only_after_otp_verifies(self):
        send = self.gui_otp_gia_lap()
        challenge = pin_otp.yeu_cau_ma(self.user, PIN_CU, PIN_CU)

        self.assertEqual(send.call_args.args[1], "SMS")
        self.assertEqual(SigningPinCredential.objects.count(), 0)
        challenge.refresh_from_db()
        otp = send.call_args.args[2]
        self.assertNotIn(otp, challenge.ma_bam)
        self.assertNotIn(PIN_CU, challenge.pin_moi_verifier)

        pin_otp.xac_nhan_ma(self.user, challenge.pk, otp)
        credential = SigningPinCredential.objects.get(nguoi_dung=self.user)
        self.assertTrue(pin.xac_thuc(self.user, PIN_CU))
        challenge.refresh_from_db()
        self.assertIsNotNone(challenge.da_dung_luc)
        self.assertEqual(challenge.pin_moi_verifier, "")
        self.assertTrue(SigningAuditLog.objects.filter(hanh_dong="TAO_PIN").exists())

    @override_settings(DEBUG=False)
    def test_http_pin_setup_and_otp_confirmation_are_allowed_when_debug_is_disabled(self):
        client = APIClient()
        client.force_authenticate(self.user)
        send = self.gui_otp_gia_lap()

        response = client.post(
            "/api/v1/signing/pin/yeu-cau/",
            {"pin_moi": PIN_CU, "pin_xac_nhan": PIN_CU, "kenh": "SMS"},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)

        response = client.post(
            "/api/v1/signing/pin/xac-nhan/",
            {"challenge_id": response.data["challenge_id"], "ma": send.call_args.args[2]},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data["da_dat_pin"])

    def test_email_is_an_explicit_alternative_channel(self):
        from django.core import mail

        pin_otp.yeu_cau_ma(self.user, PIN_CU, PIN_CU, "EMAIL")

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.user.email])
        self.assertEqual(SigningPinOtpChallenge.objects.get().kenh, "EMAIL")

    def test_cancel_discards_pending_pin_and_code(self):
        send = self.gui_otp_gia_lap()
        challenge = pin_otp.yeu_cau_ma(self.user, PIN_CU, PIN_CU)

        pin_otp.huy_yeu_cau(self.user, challenge.pk)

        self.assertEqual(SigningPinCredential.objects.count(), 0)
        challenge.refresh_from_db()
        self.assertIsNotNone(challenge.da_huy_luc)
        self.assertEqual(challenge.pin_moi_verifier, "")
        send.assert_called_once()
        self.assertTrue(SigningAuditLog.objects.filter(hanh_dong="HUY_TAO_PIN").exists())

    def test_recovery_replaces_pin_and_resets_all_pin_counters(self):
        credential = self.tao_pin_cho()
        SigningPinCredential.objects.filter(pk=credential.pk).update(
            so_lan_sai_ngay=12,
            so_lan_sai_chu_ky=5,
            ngay_dem_sai=timezone.localdate(),
            khoa_den=timezone.now() + timedelta(minutes=20),
        )
        send = self.gui_otp_gia_lap()
        challenge = pin_otp.yeu_cau_ma(self.user, PIN_MOI, PIN_MOI)

        pin_otp.xac_nhan_ma(self.user, challenge.pk, send.call_args.args[2])

        credential.refresh_from_db()
        self.assertEqual(credential.so_lan_sai_ngay, 0)
        self.assertEqual(credential.so_lan_sai_chu_ky, 0)
        self.assertIsNone(credential.khoa_den)
        self.assertTrue(pin.xac_thuc(self.user, PIN_MOI))
        with self.assertRaises(SigningError):
            pin.xac_thuc(self.user, PIN_CU)
        self.assertTrue(SigningAuditLog.objects.filter(hanh_dong="KHOI_PHUC_PIN").exists())

    def test_missing_selected_contact_and_failed_delivery_leave_no_pending_challenge(self):
        self.user.sdt = ""
        self.user.save(update_fields=["sdt"])
        send = self.gui_otp_gia_lap()

        with self.assertRaises(SigningError) as ctx:
            pin_otp.yeu_cau_ma(self.user, PIN_CU, PIN_CU)
        self.assertEqual(ctx.exception.get_codes(), "kenh_otp_khong_kha_dung")
        self.assertFalse(send.called)
        self.assertEqual(SigningPinOtpChallenge.objects.count(), 0)

        self.user.sdt = "0900000000"
        self.user.save(update_fields=["sdt"])
        send.side_effect = SigningError(code="gui_otp_that_bai", detail="Không gửi được mã.")
        with self.assertRaises(SigningError):
            pin_otp.yeu_cau_ma(self.user, PIN_CU, PIN_CU)
        self.assertEqual(SigningPinOtpChallenge.objects.count(), 0)
        self.assertEqual(SigningPinCredential.objects.count(), 0)

    @override_settings(SIGNING_SMS_URL="http://sms.example.test/send")
    def test_sms_provider_url_must_use_https(self):
        with self.assertRaises(SigningError) as ctx:
            pin_otp._gui_sms(self.user, "123456")
        self.assertEqual(ctx.exception.get_codes(), "otp_sms_chua_cau_hinh")
