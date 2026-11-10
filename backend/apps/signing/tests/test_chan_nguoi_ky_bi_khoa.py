"""Áp dụng khóa quyền ký vào gửi trình ký, danh sách người ký, email và /toi/ (issue #454, phân vùng 3 của #447)."""

from unittest import mock

from django.contrib.auth import get_user_model

from signing.models import SigningAttempt, SigningNotification, SigningRequest, SigningRequestStepSigner
from signing.services import quyen_ky

from .helpers import cap_quyen
from .test_hanh_dong_ky_phase8 import KyBase
from .test_trinh_ky_phase7 import TrinhKyBase

User = get_user_model()
TIM_UNG_VIEN = "signing.tich_hop.to_chuc.tim_ung_vien_theo_chuc_vu"


class QuanTriMixin:
    def tao_quan_tri(self):
        quan_tri = User.objects.create_user("quan_tri")
        cap_quyen(quan_tri, "manage_signing_process")
        return quan_tri

    def khoa_quyen_ky(self, nguoi, thoi_han="den_khi_bat_lai"):
        return quyen_ky.khoa_quyen(nguoi.pk, self.tao_quan_tri_dung_chung, ly_do="Kiểm tra bảo mật", thoi_han=thoi_han)


class GuiTrinhKyNguoiKyBiKhoaTests(QuanTriMixin, TrinhKyBase):
    def setUp(self):
        super().setUp()
        self.tao_quan_tri_dung_chung = self.tao_quan_tri()

    def kiem_tra_khong_tao_ban_ghi(self, pk):
        self.assertEqual(SigningRequest.objects.get(pk=pk).trang_thai, "NHAP")
        self.assertFalse(SigningAttempt.objects.filter(trinh_ky_id=pk).exists())
        self.assertFalse(SigningRequestStepSigner.objects.exists())

    def test_specific_signer_locked_rejected(self):
        self.khoa_quyen_ky(self.ky1)
        pk = self.tao_nhap().data["id"]
        r = self.gui(pk)
        self.assertEqual((r.status_code, r.data["code"]), (400, "nguoi_ky_bi_khoa_quyen_ky"))
        self.assertEqual([(v["loai"], v["nguoi_ky"]) for v in r.data["fields"]["nguoi_ky"]],
                         [("nguoi_ky_bi_khoa_quyen_ky", self.ky1.pk)])
        self.kiem_tra_khong_tao_ban_ghi(pk)

    def test_send_succeeds_after_unlock(self):
        self.khoa_quyen_ky(self.ky1)
        quyen_ky.bat_lai_quyen(self.ky1.pk, self.tao_quan_tri_dung_chung, ly_do="Đã xác minh")
        r = self.gui(self.tao_nhap().data["id"])
        self.assertEqual(r.status_code, 200, r.data)

    def test_candidate_flagged_and_locked_choice_rejected(self):
        self.process = self.tao_quy_trinh("QTK", [{"cap_ky": 1, "ten_cap_ky": "Trưởng phòng", "thu_tu": 1,
                                                   "nguoi_ky": [{"chuc_vu_id": self.position.pk, "thu_tu": 1}]}])
        self.khoa_quyen_ky(self.ky2)
        pk = self.tao_nhap().data["id"]
        with mock.patch(TIM_UNG_VIEN, return_value=[self.ky1, self.ky2]):
            r = self.gui(pk, khoa="a")
            self.assertEqual(r.data["code"], "can_chon_nguoi_ky")
            van_de = r.data["fields"]["nguoi_ky"][0]
            self.assertEqual([(u["id"], u["bi_khoa_quyen_ky"]) for u in van_de["ung_vien"]],
                             [(self.ky1.pk, False), (self.ky2.pk, True)])
            r = self.gui(pk, khoa="b", chon_nguoi_ky={str(van_de["cau_hinh"]): self.ky2.pk})
            self.assertEqual((r.status_code, r.data["code"]), (400, "nguoi_ky_bi_khoa_quyen_ky"))
            r = self.gui(pk, khoa="c", chon_nguoi_ky={str(van_de["cau_hinh"]): self.ky1.pk})
        self.assertEqual(r.status_code, 200, r.data)

    def test_signers_with_permission_endpoint_excludes_locked(self):
        cap_quyen(self.tao, "manage_signing_process")
        self.khoa_quyen_ky(self.ky2)
        r = self.client_cua(User.objects.get(pk=self.tao.pk)).get("/api/v1/signing/nguoi-ky-co-quyen/")
        self.assertEqual(r.status_code, 200, r.data)
        ids = set(r.data["ids"])
        self.assertTrue({self.ky1.pk, self.ky3.pk} <= ids)
        self.assertNotIn(self.ky2.pk, ids)

    def test_me_endpoint_reports_lock_state(self):
        r = self.client_cua(User.objects.get(pk=self.ky1.pk)).get("/api/v1/signing/toi/")
        self.assertIsNone(r.data["khoa_quyen_ky"])
        self.khoa_quyen_ky(self.ky1, thoi_han="8_gio")
        r = self.client_cua(User.objects.get(pk=self.ky1.pk)).get("/api/v1/signing/toi/")
        self.assertIsNotNone(r.data["khoa_quyen_ky"]["khoa_den"])
        self.assertNotIn("ly_do", r.data["khoa_quyen_ky"])


class ThongBaoEmailNguoiBiKhoaTests(QuanTriMixin, KyBase):
    def setUp(self):
        super().setUp()
        self.tao_quan_tri_dung_chung = self.tao_quan_tri()
        User.objects.filter(pk=self.ky3.pk).update(email="nguoi.ky.cap.hai@example.test")

    def thong_bao_cua(self, nguoi):
        return list(SigningNotification.objects.filter(nguoi_nhan=nguoi, buoc_ky__isnull=False)
                    .values_list("kenh", flat=True))

    def ky_het_cap_dau(self):
        self.assertEqual(self.ky(self.ky1).status_code, 200)
        self.assertEqual(self.ky(self.ky2).status_code, 200)

    def test_email_sent_when_not_locked(self):
        self.ky_het_cap_dau()
        self.assertIn("EMAIL", self.thong_bao_cua(self.ky3))

    def test_email_skipped_but_in_app_kept_when_locked(self):
        self.khoa_quyen_ky(self.ky3)
        self.ky_het_cap_dau()
        kenh = self.thong_bao_cua(self.ky3)
        self.assertIn("IN_APP", kenh)
        self.assertNotIn("EMAIL", kenh)
