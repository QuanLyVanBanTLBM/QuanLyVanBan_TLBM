"""Tests cho tính năng xác thực hai yếu tố (2FA TOTP & Backup Codes — Issue #674)."""
from datetime import timedelta
from unittest.mock import patch
import urllib.error

from django.contrib.auth import get_user_model
from django.core import signing
from django.urls import reverse
from django.utils import timezone
import pyotp
from rest_framework import status
from rest_framework.test import APITestCase

from accounts import twofa

User = get_user_model()


class TwoFactorAuthTests(APITestCase):
    PASSWORD = "StrongPassword@2026"

    def setUp(self):
        provider = patch(
            "accounts.alpaca_auth.urllib.request.urlopen",
            side_effect=urllib.error.URLError("offline test"),
        )
        self.provider = provider.start()
        self.addCleanup(provider.stop)

        self.user = User.objects.create_user(
            username="twofa_user",
            password=self.PASSWORD,
            email="twofa_user@baolong.vn",
            ho_ten="Cán bộ Kiểm thử 2FA",
        )
        self.external_user = User.objects.create_user(
            username="alpaca_twofa",
            email="alpaca_twofa@baolong.vn",
            ho_ten="Cán bộ Bảo Long 2FA",
        )
        self.external_user.set_unusable_password()
        self.external_user.save(update_fields=["password"])

    def _enable_2fa_for(self, target_user, base_time):
        self.client.force_authenticate(user=target_user)
        with patch("accounts.twofa.timezone.now", return_value=base_time):
            setup_resp = self.client.post(reverse("accounts:twofa_setup"), {}, format="json")
            self.assertEqual(setup_resp.status_code, status.HTTP_200_OK)
            payload = setup_resp.json()
            self.assertTrue(payload["qr_code"].startswith("data:image/png;base64,"))
            self.assertIn("otpauth://totp/", payload["otpauth_uri"])

            secret = payload["secret_key"]
            code = pyotp.TOTP(secret).at(int(base_time.timestamp()))
            confirm_resp = self.client.post(
                reverse("accounts:twofa_confirm"),
                {"setup_token": payload["setup_token"], "code": code},
                format="json",
            )
            self.assertEqual(confirm_resp.status_code, status.HTTP_200_OK)
            confirm_data = confirm_resp.json()
            self.assertTrue(confirm_data["enabled"])
            self.assertEqual(len(confirm_data["backup_codes"]), twofa.BACKUP_CODE_COUNT)

        self.client.force_authenticate(user=None)
        return secret, confirm_data["backup_codes"]

    def test_login_without_2fa_issues_tokens_normally(self):
        resp = self.client.post(
            reverse("accounts:login"),
            {"username": self.user.username, "password": self.PASSWORD},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()
        self.assertFalse(data.get("require_2fa", False))
        self.assertIn("access", data)
        self.assertIn("refresh", data)
        self.assertFalse(data["user"]["is_2fa_enabled"])
        self.assertTrue(data["user"]["has_usable_credential"])

    def test_setup_rejects_invalid_otp_then_enables_with_encrypted_secret(self):
        t0 = timezone.now()
        self.client.force_authenticate(user=self.user)

        setup_resp = self.client.post(reverse("accounts:twofa_setup"), {}, format="json")
        self.assertEqual(setup_resp.status_code, status.HTTP_200_OK)
        payload = setup_resp.json()

        bad_confirm = self.client.post(
            reverse("accounts:twofa_confirm"),
            {"setup_token": payload["setup_token"], "code": "000000"},
            format="json",
        )
        self.assertEqual(bad_confirm.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(bad_confirm.json()["code"], "otp_invalid")

        self.user.refresh_from_db()
        self.assertFalse(self.user.is_2fa_enabled)
        self.assertFalse(self.user.totp_secret)

        with patch("accounts.twofa.timezone.now", return_value=t0):
            valid_code = pyotp.TOTP(payload["secret_key"]).at(int(t0.timestamp()))
            ok_confirm = self.client.post(
                reverse("accounts:twofa_confirm"),
                {"setup_token": payload["setup_token"], "code": valid_code},
                format="json",
            )
        self.assertEqual(ok_confirm.status_code, status.HTTP_200_OK)

        self.user.refresh_from_db()
        self.assertTrue(self.user.is_2fa_enabled)
        self.assertNotEqual(self.user.totp_secret, payload["secret_key"])
        self.assertEqual(twofa.decrypt_secret(self.user.totp_secret), payload["secret_key"])

        status_resp = self.client.get(reverse("accounts:twofa_status"))
        self.assertEqual(status_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(
            status_resp.json(),
            {
                "enabled": True,
                "backup_codes_remaining": twofa.BACKUP_CODE_COUNT,
                "has_usable_credential": True,
            },
        )

    def test_local_login_with_2fa_and_replay_protection(self):
        t0 = timezone.now()
        secret, _backup_codes = self._enable_2fa_for(self.user, t0)

        login_resp = self.client.post(
            reverse("accounts:login"),
            {"username": self.user.username, "password": self.PASSWORD},
            format="json",
        )
        self.assertEqual(login_resp.status_code, status.HTTP_200_OK)
        login_data = login_resp.json()
        self.assertTrue(login_data["require_2fa"])
        self.assertNotIn("access", login_data)
        self.assertNotIn("refresh", login_data)
        temp_token = login_data["temp_token"]

        # temp_token không thể dùng như Bearer JWT cho API bảo vệ
        profile_attempt = self.client.get(
            reverse("accounts:profile"),
            HTTP_AUTHORIZATION=f"Bearer {temp_token}",
        )
        self.assertEqual(profile_attempt.status_code, status.HTTP_401_UNAUTHORIZED)

        # Sang bước 30s tiếp theo xác thực TOTP thành công
        t1 = t0 + timedelta(seconds=60)
        otp = pyotp.TOTP(secret).at(int(t1.timestamp()))
        with patch("accounts.twofa.timezone.now", return_value=t1):
            verify_resp = self.client.post(
                reverse("accounts:verify_2fa"),
                {"temp_token": temp_token, "code": otp},
                format="json",
            )
        self.assertEqual(verify_resp.status_code, status.HTTP_200_OK)
        verify_data = verify_resp.json()
        self.assertIn("access", verify_data)
        self.assertIn("refresh", verify_data)
        self.assertEqual(verify_data["verified_via"], "totp")
        self.assertTrue(verify_data["user"]["is_2fa_enabled"])

        # Dùng lại đúng mã OTP trong cùng chu kỳ phải bị chặn (anti-replay)
        with patch("accounts.twofa.timezone.now", return_value=t1):
            replay_resp = self.client.post(
                reverse("accounts:verify_2fa"),
                {"temp_token": temp_token, "code": otp},
                format="json",
            )
        self.assertEqual(replay_resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(replay_resp.json()["code"], "otp_reused")

    def test_alpaca_login_with_2fa_and_otp_disable(self):
        t0 = timezone.now()
        secret, _backup_codes = self._enable_2fa_for(self.external_user, t0)

        with patch("accounts.views.check_alpaca_auth", return_value={"success": True}):
            login_resp = self.client.post(
                reverse("accounts:login"),
                {"username": self.external_user.username, "password": "ExternalApiPassword"},
                format="json",
            )
        self.assertEqual(login_resp.status_code, status.HTTP_200_OK)
        login_data = login_resp.json()
        self.assertTrue(login_data["require_2fa"])
        self.assertEqual(login_data["auth_provider"], "alpaca_api")

        t1 = t0 + timedelta(seconds=60)
        otp1 = pyotp.TOTP(secret).at(int(t1.timestamp()))
        with patch("accounts.twofa.timezone.now", return_value=t1):
            verify_resp = self.client.post(
                reverse("accounts:verify_2fa"),
                {"temp_token": login_data["temp_token"], "code": otp1},
                format="json",
            )
        self.assertEqual(verify_resp.status_code, status.HTTP_200_OK)
        self.assertFalse(verify_resp.json()["user"]["has_usable_credential"])

        # Tài khoản ngoài không có mật khẩu cục bộ -> gửi password bị từ chối với mã rõ ràng
        self.external_user.refresh_from_db()
        self.client.force_authenticate(user=self.external_user)
        pw_disable = self.client.post(
            reverse("accounts:twofa_disable"),
            {"password": "anything"},
            format="json",
        )
        self.assertEqual(pw_disable.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(pw_disable.json()["code"], "otp_required_for_external_auth")

        # Tắt bằng mã OTP hiện tại ở chu kỳ kế tiếp thành công
        t2 = t1 + timedelta(seconds=60)
        otp2 = pyotp.TOTP(secret).at(int(t2.timestamp()))
        with patch("accounts.twofa.timezone.now", return_value=t2):
            otp_disable = self.client.post(
                reverse("accounts:twofa_disable"),
                {"code": otp2},
                format="json",
            )
        self.assertEqual(otp_disable.status_code, status.HTTP_200_OK)
        self.assertFalse(otp_disable.json()["enabled"])

    def test_bruteforce_lockout_and_unlock(self):
        t0 = timezone.now()
        secret, _backup_codes = self._enable_2fa_for(self.user, t0)

        login_resp = self.client.post(
            reverse("accounts:login"),
            {"username": self.user.username, "password": self.PASSWORD},
            format="json",
        )
        temp_token = login_resp.json()["temp_token"]

        t_attempt = t0 + timedelta(seconds=60)
        with patch("accounts.twofa.timezone.now", return_value=t_attempt):
            for idx in range(twofa.MAX_FAILED_ATTEMPTS - 1):
                bad = self.client.post(
                    reverse("accounts:verify_2fa"),
                    {"temp_token": temp_token, "code": "999999"},
                    format="json",
                )
                self.assertEqual(bad.status_code, status.HTTP_401_UNAUTHORIZED, msg=f"attempt {idx}")
                self.assertEqual(bad.json()["code"], "otp_invalid")

            fifth = self.client.post(
                reverse("accounts:verify_2fa"),
                {"temp_token": temp_token, "code": "999999"},
                format="json",
            )
            self.assertEqual(fifth.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
            self.assertEqual(fifth.json()["code"], "twofa_locked")

            # Ngay cả mã đúng trong thời gian khóa vẫn bị từ chối
            valid_while_locked = pyotp.TOTP(secret).at(int(t_attempt.timestamp()))
            blocked = self.client.post(
                reverse("accounts:verify_2fa"),
                {"temp_token": temp_token, "code": valid_while_locked},
                format="json",
            )
            self.assertEqual(blocked.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

        # Sau khi hết thời gian khóa (6 phút), tạo temp_token mới & đăng nhập lại bình thường
        t_unlocked = t_attempt + timedelta(minutes=twofa.LOCKOUT_MINUTES + 1)
        fresh_token = signing.dumps(
            {"uid": self.user.id, "provider": "local", "jti": "fresh"},
            salt=twofa.LOGIN_SALT,
        )
        valid_after_unlock = pyotp.TOTP(secret).at(int(t_unlocked.timestamp()))
        with patch("accounts.twofa.timezone.now", return_value=t_unlocked):
            with patch("accounts.twofa.signing.loads", return_value={"uid": self.user.id, "provider": "local", "jti": "fresh"}):
                ok = self.client.post(
                    reverse("accounts:verify_2fa"),
                    {"temp_token": fresh_token, "code": valid_after_unlock},
                    format="json",
                )
        self.assertEqual(ok.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.twofa_failed_attempts, 0)
        self.assertIsNone(self.user.twofa_locked_until)

    def test_backup_code_single_use_and_regenerate_invalidates_old(self):
        t0 = timezone.now()
        _secret, backup_codes = self._enable_2fa_for(self.user, t0)

        login_resp = self.client.post(
            reverse("accounts:login"),
            {"username": self.user.username, "password": self.PASSWORD},
            format="json",
        )
        temp_token = login_resp.json()["temp_token"]

        # Nhập backup code không dấu gạch vẫn hợp lệ (normalize)
        first_code = backup_codes[0].replace("-", "").lower()
        ok_resp = self.client.post(
            reverse("accounts:verify_2fa"),
            {"temp_token": temp_token, "code": first_code},
            format="json",
        )
        self.assertEqual(ok_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(ok_resp.json()["verified_via"], "backup_code")

        # Dùng lại backup code đó phải fail
        reused_resp = self.client.post(
            reverse("accounts:verify_2fa"),
            {"temp_token": temp_token, "code": backup_codes[0]},
            format="json",
        )
        self.assertEqual(reused_resp.status_code, status.HTTP_401_UNAUTHORIZED)

        # Tạo lại bộ mã dự phòng bằng mật khẩu hiện tại
        self.user.refresh_from_db()
        self.client.force_authenticate(user=self.user)
        regen_resp = self.client.post(
            reverse("accounts:twofa_regenerate_backup_codes"),
            {"password": self.PASSWORD},
            format="json",
        )
        self.assertEqual(regen_resp.status_code, status.HTTP_200_OK)
        new_codes = regen_resp.json()["backup_codes"]
        self.assertEqual(len(new_codes), twofa.BACKUP_CODE_COUNT)
        self.assertNotEqual(new_codes, backup_codes)
        self.client.force_authenticate(user=None)

        # Mã cũ còn lại không dùng được nữa, mã mới dùng được
        old_attempt = self.client.post(
            reverse("accounts:verify_2fa"),
            {"temp_token": temp_token, "code": backup_codes[1]},
            format="json",
        )
        self.assertEqual(old_attempt.status_code, status.HTTP_401_UNAUTHORIZED)

        new_attempt = self.client.post(
            reverse("accounts:verify_2fa"),
            {"temp_token": temp_token, "code": new_codes[0]},
            format="json",
        )
        self.assertEqual(new_attempt.status_code, status.HTTP_200_OK)

    def test_tampered_and_expired_temp_token_rejected(self):
        bad_token = self.client.post(
            reverse("accounts:verify_2fa"),
            {"temp_token": "tampered.token", "code": "123456"},
            format="json",
        )
        self.assertEqual(bad_token.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(bad_token.json()["code"], "temp_token_invalid")

        with patch("accounts.twofa.signing.loads", side_effect=signing.SignatureExpired("expired")):
            expired_token = self.client.post(
                reverse("accounts:verify_2fa"),
                {"temp_token": "expired.token", "code": "123456"},
                format="json",
            )
        self.assertEqual(expired_token.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(expired_token.json()["code"], "temp_token_expired")

    def test_login_by_email_case_insensitive(self):
        resp = self.client.post(
            reverse("accounts:login"),
            {"username": "TWOFA_USER@BAOLONG.VN", "password": self.PASSWORD},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.json()["user"]["username"], self.user.username)

    def test_2fa_email_and_sms_otp_and_trusted_device_cookie(self):
        self.user.sdt = "0912345678"
        self.user.save(update_fields=["sdt"])
        t0 = timezone.now()
        self._enable_2fa_for(self.user, t0)

        with self.settings(DEBUG=True):
            login_resp = self.client.post(
                reverse("accounts:login"),
                {"username": self.user.email, "password": self.PASSWORD},
                format="json",
            )
        self.assertEqual(login_resp.status_code, status.HTTP_200_OK)
        login_data = login_resp.json()
        self.assertTrue(login_data["require_2fa"])
        self.assertTrue(login_data["available_channels"]["email"])
        self.assertTrue(login_data["available_channels"]["sms"])
        temp_token = login_data["temp_token"]

        captured = {}

        def fake_send_email(_user, code, _purpose):
            captured["email_code"] = code

        with patch("accounts.otp_service._send_email_otp", side_effect=fake_send_email):
            send_resp = self.client.post(
                reverse("accounts:twofa_send_otp"),
                {"temp_token": temp_token, "channel": "email"},
                format="json",
            )
        self.assertEqual(send_resp.status_code, status.HTTP_200_OK)
        otp_token = send_resp.json()["otp_token"]

        # Chặn gửi lại liên tiếp trong 60s
        cooldown_resp = self.client.post(
            reverse("accounts:twofa_send_otp"),
            {"temp_token": temp_token, "channel": "email", "previous_otp_token": otp_token},
            format="json",
        )
        self.assertEqual(cooldown_resp.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertEqual(cooldown_resp.json()["code"], "otp_cooldown")

        # Xác thực thành công và tin cậy thiết bị 30 ngày
        verify_resp = self.client.post(
            reverse("accounts:verify_2fa"),
            {
                "temp_token": temp_token,
                "otp_token": otp_token,
                "code": captured["email_code"],
                "trust_device": True,
            },
            format="json",
        )
        self.assertEqual(verify_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(verify_resp.json()["verified_via"], "email")
        self.assertIn(twofa.TRUSTED_DEVICE_COOKIE_NAME, verify_resp.cookies)

        # Replay lại otp_token đã dùng phải bị chặn vì last_login đã cập nhật
        replay_resp = self.client.post(
            reverse("accounts:verify_2fa"),
            {
                "temp_token": temp_token,
                "otp_token": otp_token,
                "code": captured["email_code"],
            },
            format="json",
        )
        self.assertEqual(replay_resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(replay_resp.json()["code"], "otp_token_expired")

        # Lần đăng nhập kế tiếp có cookie tin cậy -> bỏ qua bước 2FA
        bypass_resp = self.client.post(
            reverse("accounts:login"),
            {"username": self.user.username, "password": self.PASSWORD},
            format="json",
        )
        self.assertEqual(bypass_resp.status_code, status.HTTP_200_OK)
        self.assertFalse(bypass_resp.json().get("require_2fa", False))
        self.assertEqual(bypass_resp.json().get("verified_via"), "trusted_device")

        # Gửi SMS OTP hoạt động khi có cấu hình SMS
        self.client.cookies.clear()
        with patch("accounts.otp_service._send_sms_otp") as sms_mock:
            login_again = self.client.post(
                reverse("accounts:login"),
                {"username": self.user.username, "password": self.PASSWORD},
                format="json",
            )
            with self.settings(DEBUG=True):
                sms_send = self.client.post(
                    reverse("accounts:twofa_send_otp"),
                    {"temp_token": login_again.json()["temp_token"], "channel": "sms"},
                    format="json",
                )
            self.assertEqual(sms_send.status_code, status.HTTP_200_OK)
            sms_mock.assert_called_once()

    def test_forgot_password_self_reset_and_restrictions(self):
        from django.contrib.auth.models import Group
        from authorization.models import GroupInfo

        self.user.sdt = "0987654321"
        self.user.save(update_fields=["sdt"])

        # 1. Chặn tài khoản Alpaca (!has_usable_password)
        alpaca_lookup = self.client.post(
            reverse("accounts:forgot_password_lookup"),
            {"identifier": self.external_user.username},
            format="json",
        )
        self.assertEqual(alpaca_lookup.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(alpaca_lookup.json()["code"], "external_auth_restricted")

        # 2. Chặn superuser và thành viên nhóm ADMIN
        superuser = User.objects.create_superuser(
            username="super_2fa",
            email="super_2fa@baolong.vn",
            password=self.PASSWORD,
            ho_ten="Super User",
        )
        super_lookup = self.client.post(
            reverse("accounts:forgot_password_lookup"),
            {"identifier": superuser.email},
            format="json",
        )
        self.assertEqual(super_lookup.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(super_lookup.json()["code"], "self_reset_restricted")

        admin_group_info = GroupInfo.objects.filter(ma_nhom_quyen="ADMIN").first()
        self.assertIsNotNone(admin_group_info)
        admin_member = User.objects.create_user(
            username="admin_grp_2fa",
            email="admin_grp_2fa@baolong.vn",
            password=self.PASSWORD,
            ho_ten="Admin Group",
        )
        admin_member.groups.add(Group.objects.get(pk=admin_group_info.pk))
        grp_lookup = self.client.post(
            reverse("accounts:forgot_password_lookup"),
            {"identifier": admin_member.username},
            format="json",
        )
        self.assertEqual(grp_lookup.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(grp_lookup.json()["code"], "self_reset_restricted")

        # 3. Nhân viên thường tự đặt lại mật khẩu qua Email OTP thành công
        with self.settings(DEBUG=True):
            lookup_ok = self.client.post(
                reverse("accounts:forgot_password_lookup"),
                {"identifier": self.user.email},
                format="json",
            )
        self.assertEqual(lookup_ok.status_code, status.HTTP_200_OK)
        self.assertTrue(lookup_ok.json()["channels"]["email"])
        self.assertTrue(lookup_ok.json()["channels"]["sms"])

        captured = {}

        def fake_reset_email(_user, code, _purpose):
            captured["reset_code"] = code

        with patch("accounts.otp_service._send_email_otp", side_effect=fake_reset_email):
            send_reset = self.client.post(
                reverse("accounts:forgot_password_send_otp"),
                {"identifier": self.user.username, "channel": "email"},
                format="json",
            )
        self.assertEqual(send_reset.status_code, status.HTTP_200_OK)
        reset_token = send_reset.json()["reset_token"]

        new_password = "NewStrongPassword@2026"
        confirm_resp = self.client.post(
            reverse("accounts:forgot_password_confirm"),
            {
                "reset_token": reset_token,
                "code": captured["reset_code"],
                "new_password": new_password,
                "confirm_password": new_password,
            },
            format="json",
        )
        self.assertEqual(confirm_resp.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(new_password))

        # Token reset cũ tự vô hiệu sau khi đổi mật khẩu
        reuse_resp = self.client.post(
            reverse("accounts:forgot_password_confirm"),
            {
                "reset_token": reset_token,
                "code": captured["reset_code"],
                "new_password": "AnotherPassword@2026",
                "confirm_password": "AnotherPassword@2026",
            },
            format="json",
        )
        self.assertEqual(reuse_resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_admin_reset_2fa_for_employee_and_protects_superuser(self):
        from django.contrib.auth.models import Group
        from authorization.models import GroupInfo

        t0 = timezone.now()
        self._enable_2fa_for(self.user, t0)

        superuser = User.objects.create_superuser(
            username="super_reset_target",
            email="super_reset_target@baolong.vn",
            password=self.PASSWORD,
            ho_ten="Super Reset Target",
        )
        self._enable_2fa_for(superuser, t0)

        admin_group_info = GroupInfo.objects.filter(ma_nhom_quyen="ADMIN").first()
        self.assertIsNotNone(admin_group_info)
        admin_member = User.objects.create_user(
            username="admin_resetter",
            email="admin_resetter@baolong.vn",
            password=self.PASSWORD,
            ho_ten="Admin Resetter",
        )
        admin_member.groups.add(Group.objects.get(pk=admin_group_info.pk))
        self.client.force_authenticate(user=admin_member)

        # Kiểm tra serializer trả is_2fa_enabled cho Admin
        detail_resp = self.client.get(f"/api/accounts/employees/{self.user.id}/")
        self.assertEqual(detail_resp.status_code, status.HTTP_200_OK)
        self.assertTrue(detail_resp.json()["is_2fa_enabled"])

        # Tắt 2FA cho nhân viên thường thành công
        ok_reset = self.client.post(f"/api/accounts/employees/{self.user.id}/reset-2fa/", {}, format="json")
        self.assertEqual(ok_reset.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_2fa_enabled)
        self.assertEqual(self.user.totp_secret, "")

        # Không được tắt 2FA của superuser
        denied_reset = self.client.post(f"/api/accounts/employees/{superuser.id}/reset-2fa/", {}, format="json")
        self.assertEqual(denied_reset.status_code, status.HTTP_403_FORBIDDEN)
        superuser.refresh_from_db()
        self.assertTrue(superuser.is_2fa_enabled)


