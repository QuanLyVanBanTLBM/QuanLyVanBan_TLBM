"""Thông báo thao tác quản trị trên tài khoản: khóa/bật lại quyền ký, thu hồi khóa (issue #467, phân vùng 3 của #447)."""

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import override_settings

from signing import enums
from signing.models import SigningNotification
from signing.services import keys, quyen_ky
from signing.services import thong_bao as thong_bao_service

from .helpers import cap_quyen
from .test_hanh_dong_ky_phase8 import KyBase

User = get_user_model()
LY_DO_NOI_BO = "Ly do noi bo cua quan tri vien"


@override_settings(SIGNING_EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class ThongBaoQuanTriTests(KyBase):
    def setUp(self):
        super().setUp()
        self.quan_tri = User.objects.create_user("quan_tri")
        cap_quyen(self.quan_tri, "manage_signing_process")
        self.ky1.email = "ky1@example.test"
        self.ky1.save(update_fields=["email"])
        SigningNotification.objects.all().delete()
        mail.outbox.clear()

    def thong_bao(self, loai, kenh):
        return SigningNotification.objects.filter(nguoi_nhan=self.ky1, loai_thong_bao=loai, kenh=kenh)

    def test_lock_creates_in_app_only_and_no_email(self):
        with self.captureOnCommitCallbacks(execute=True):
            khoa = quyen_ky.khoa_quyen(self.ky1.pk, self.quan_tri, ly_do=LY_DO_NOI_BO, thoi_han="8_gio")
        tb = self.thong_bao("KHOA_QUYEN_KY", enums.KenhThongBao.IN_APP).get()
        self.assertIsNone(tb.trinh_ky_id)
        self.assertEqual(tb.khoa_chong_gui_trung, f"KHOA_QUYEN_KY:{khoa.pk}:IN_APP")
        self.assertFalse(self.thong_bao("KHOA_QUYEN_KY", enums.KenhThongBao.EMAIL).exists())
        self.assertEqual(mail.outbox, [])

    def test_unlock_sends_email_without_internal_reason(self):
        quyen_ky.khoa_quyen(self.ky1.pk, self.quan_tri, ly_do="khoa", thoi_han="den_khi_bat_lai")
        with self.captureOnCommitCallbacks(execute=True):
            quyen_ky.bat_lai_quyen(self.ky1.pk, self.quan_tri, ly_do=LY_DO_NOI_BO)
        self.assertEqual(self.thong_bao("BAT_LAI_QUYEN_KY", enums.KenhThongBao.IN_APP).count(), 1)
        self.assertEqual(len(mail.outbox), 1)
        thu = mail.outbox[0]
        self.assertEqual(thu.to, ["ky1@example.test"])
        self.assertIn("Quyền ký đã được bật lại", thu.subject)
        self.assertIn("Signing permission restored", thu.subject)
        self.assertIn("Quản trị viên đã bật lại quyền ký", thu.body)
        self.assertIn("An administrator has restored the signing permission", thu.body)
        self.assertLess(thu.body.index("Xin chào"), thu.body.index("Hello"))  # tiếng Việt trước, tiếng Anh sau
        self.assertNotIn(LY_DO_NOI_BO, thu.subject + thu.body)

    def test_admin_revoke_notifies_owner_once_per_revocation(self):
        with self.captureOnCommitCallbacks(execute=True):
            danh_sach = keys.thu_hoi_khan_cap_boi_quan_tri(self.ky1.pk, self.quan_tri, LY_DO_NOI_BO)
        self.assertEqual(self.thong_bao("THU_HOI_KHOA", enums.KenhThongBao.IN_APP).count(), 1)
        self.assertEqual(len(danh_sach), 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Khóa ký bị thu hồi", mail.outbox[0].subject)
        self.assertIn("Signing key revoked", mail.outbox[0].subject)
        self.assertIn("An administrator has revoked the signing key", mail.outbox[0].body)
        self.assertNotIn(LY_DO_NOI_BO, mail.outbox[0].subject + mail.outbox[0].body)

    def test_lock_body_states_expiry_and_notification_list_handles_no_request(self):
        quyen_ky.khoa_quyen(self.ky1.pk, self.quan_tri, ly_do="khoa", thoi_han="8_gio")
        tb = self.thong_bao("KHOA_QUYEN_KY", enums.KenhThongBao.IN_APP).get()
        tieu_de, than, ten = thong_bao_service.noi_dung(tb)
        self.assertIn("Quyền ký bị tạm khóa", tieu_de)
        self.assertIn("khóa đến", than)
        self.assertIn("Signing permission is locked until", than)
        self.assertIn("Signing permission temporarily locked", tieu_de)
        self.assertEqual(thong_bao_service.thao_tac(tb), ("", ""))
        response = self.client_cua(self.ky1).get("/api/v1/signing/thong-bao/")
        self.assertEqual(response.status_code, 200, response.data)
        muc = next(m for m in response.data["results"] if m["loai_thong_bao"] == "KHOA_QUYEN_KY")
        self.assertIsNone(muc["trinh_ky"])
        self.assertIsNone(muc["ten_quy_trinh"])

    def test_every_admin_notification_type_has_an_english_title(self):
        self.assertEqual(set(thong_bao_service.TEN_LOAI_EN), set(thong_bao_service.LOAI_QUAN_TRI))
