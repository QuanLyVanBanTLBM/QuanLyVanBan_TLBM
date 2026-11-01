"""API quản trị khóa ký và quyền ký của tài khoản khác (issue #451, phân vùng 3 của #447)."""

from django.contrib.auth import get_user_model

from signing.models import SigningAuditLog, SigningKey

from .helpers import cap_quyen
from .test_hanh_dong_ky_phase8 import KyBase

User = get_user_model()
QT = "/api/v1/signing/quan-tri/nguoi-dung/"


class QuanTriKhoaKyApiTests(KyBase):
    def setUp(self):
        super().setUp()
        self.quan_tri = User.objects.create_user("quan_tri")
        cap_quyen(self.quan_tri, "manage_signing_process")
        self.qt = self.client_cua(User.objects.get(pk=self.quan_tri.pk))

    def test_non_admin_forbidden_everywhere(self):
        c = self.client_cua(User.objects.get(pk=self.ky2.pk))
        self.assertEqual(c.get(QT).status_code, 403)
        for hanh_dong in ("khoa-quyen-ky", "bat-lai-quyen-ky", "thu-hoi-khoa"):
            r = c.post(f"{QT}{self.ky1.pk}/{hanh_dong}/", {"ly_do": "x", "thoi_han": "1_gio"}, format="json")
            self.assertEqual(r.status_code, 403, hanh_dong)

    def test_list_shows_key_pin_and_lock_state_and_filters(self):
        r = self.qt.get(QT, {"q": "ke_toan"})
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual([x["ten_dang_nhap"] for x in r.data], ["ke_toan"])
        dong = r.data[0]
        self.assertTrue(dong["co_quyen_ky"])
        self.assertEqual(dong["khoa_ky"]["trang_thai"], "HOAT_DONG")
        self.assertIsNone(dong["khoa_quyen_ky"])
        self.qt.post(f"{QT}{self.ky1.pk}/khoa-quyen-ky/", {"thoi_han": "24_gio", "ly_do": "Kiểm tra bảo mật"}, format="json")
        dong = self.qt.get(QT, {"q": "ke_toan"}).data[0]
        self.assertEqual(dong["khoa_quyen_ky"]["ly_do"], "Kiểm tra bảo mật")

    def test_lock_blocks_signing_then_unlock_restores(self):
        r = self.qt.post(f"{QT}{self.ky1.pk}/khoa-quyen-ky/", {"thoi_han": "den_khi_bat_lai", "ly_do": "Nghi ngờ"},
                         format="json")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertIsNotNone(r.data["khoa_quyen_ky"])
        self.assertEqual(self.ky(self.ky1).data["code"], "quyen_ky_bi_khoa")
        r = self.qt.post(f"{QT}{self.ky1.pk}/bat-lai-quyen-ky/", {"ly_do": "Đã xác minh"}, format="json")
        self.assertEqual((r.status_code, r.data["khoa_quyen_ky"]), (200, None))
        self.assertEqual(self.ky(self.ky1).status_code, 200)

    def test_validation_errors(self):
        r = self.qt.post(f"{QT}{self.ky1.pk}/khoa-quyen-ky/", {"thoi_han": "2_gio", "ly_do": "x"}, format="json")
        self.assertEqual(r.status_code, 400)
        r = self.qt.post(f"{QT}{self.ky1.pk}/khoa-quyen-ky/", {"thoi_han": "1_gio", "ly_do": ""}, format="json")
        self.assertEqual(r.status_code, 400)
        r = self.qt.post(f"{QT}{self.ky1.pk}/bat-lai-quyen-ky/", {"ly_do": "Đã xác minh"}, format="json")
        self.assertEqual((r.status_code, r.data["code"]), (409, "quyen_ky_khong_bi_khoa"))
        r = self.qt.post(f"{QT}999999/khoa-quyen-ky/", {"thoi_han": "1_gio", "ly_do": "x"}, format="json")
        self.assertEqual(r.status_code, 404)

    def test_emergency_revoke_key_makes_signing_fail_and_audits(self):
        r = self.qt.post(f"{QT}{self.ky1.pk}/thu-hoi-khoa/", {"ly_do": "Mất thiết bị"}, format="json")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertIsNone(r.data["khoa_ky"])
        self.assertFalse(SigningKey.objects.filter(nguoi_so_huu=self.ky1, trang_thai="HOAT_DONG").exists())
        nhat_ky = SigningAuditLog.objects.get(hanh_dong="QUAN_TRI_THU_HOI_KHOA")
        self.assertEqual((nhat_ky.nguoi_thuc_hien_id, nhat_ky.chi_tiet), (self.quan_tri.pk, "Mất thiết bị"))
        self.assertNotEqual(self.ky(self.ky1).status_code, 200)
        r = self.qt.post(f"{QT}{self.ky1.pk}/thu-hoi-khoa/", {"ly_do": "Mất thiết bị"}, format="json")
        self.assertEqual((r.status_code, r.data["code"]), (409, "khong_co_khoa_de_thu_hoi"))

    def test_revoke_requires_reason_and_not_self(self):
        r = self.qt.post(f"{QT}{self.ky1.pk}/thu-hoi-khoa/", {"ly_do": " "}, format="json")
        self.assertEqual(r.status_code, 400)
        r = self.qt.post(f"{QT}{self.quan_tri.pk}/thu-hoi-khoa/", {"ly_do": "x"}, format="json")
        self.assertEqual((r.status_code, r.data["code"]), (400, "dung_chuc_nang_thu_hoi_cua_chu_khoa"))
