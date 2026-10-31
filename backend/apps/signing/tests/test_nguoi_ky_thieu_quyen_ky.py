"""Gửi hồ sơ: mọi người ký (chọn cụ thể, suy ra từ chức vụ) phải có quyền sign_trinhky, nếu không trả 400."""

from unittest import mock

from django.contrib.auth import get_user_model

from signing.models import SigningAttempt, SigningRequest, SigningRequestStepSigner

from .helpers import cap_quyen
from .test_trinh_ky_phase7 import TrinhKyBase

User = get_user_model()

TIM_UNG_VIEN = "signing.tich_hop.to_chuc.tim_ung_vien_theo_chuc_vu"


class NguoiKyThieuQuyenKyTests(TrinhKyBase):
    def kiem_tra_khong_tao_ban_ghi(self, pk):
        self.assertEqual(SigningRequest.objects.get(pk=pk).trang_thai, "NHAP")
        self.assertFalse(SigningAttempt.objects.filter(trinh_ky_id=pk).exists())
        self.assertFalse(SigningRequestStepSigner.objects.exists())

    def test_signers_with_permission_send_succeeds(self):
        pk = self.tao_nhap().data["id"]
        r = self.gui(pk)
        self.assertEqual((r.status_code, r.data["trang_thai"]), (200, "CHO_KY"))

    def test_specific_signer_without_permission_rejected(self):
        self.process = self.tao_quy_trinh("QTK", [{"cap_ky": 1, "ten_cap_ky": "C", "thu_tu": 1, "nguoi_ky": [
            {"nguoi_ky": self.ky1, "thu_tu": 1}, {"nguoi_ky": self.la, "thu_tu": 2}]}])
        pk = self.tao_nhap().data["id"]
        r = self.gui(pk)
        self.assertEqual((r.status_code, r.data["code"]), (400, "nguoi_ky_thieu_quyen_ky"))
        loi = r.data["fields"]["nguoi_ky"]
        self.assertEqual([(v["loai"], v["nguoi_ky"]) for v in loi], [("nguoi_ky_thieu_quyen_ky", self.la.pk)])
        self.kiem_tra_khong_tao_ban_ghi(pk)

    def test_signer_from_position_without_permission_rejected(self):
        self.process = self.tao_quy_trinh("QTV", [{"cap_ky": 1, "ten_cap_ky": "Trưởng phòng", "thu_tu": 1,
                                                   "nguoi_ky": [{"chuc_vu_id": self.position.pk, "thu_tu": 1}]}])
        pk = self.tao_nhap().data["id"]
        with mock.patch(TIM_UNG_VIEN, return_value=[self.la]):
            r = self.gui(pk)
        self.assertEqual((r.status_code, r.data["code"]), (400, "nguoi_ky_thieu_quyen_ky"))
        self.assertEqual(r.data["fields"]["nguoi_ky"][0]["nguoi_ky"], self.la.pk)
        self.kiem_tra_khong_tao_ban_ghi(pk)

    def test_chosen_candidate_without_permission_rejected_and_flagged(self):
        self.process = self.tao_quy_trinh("QTC", [{"cap_ky": 1, "ten_cap_ky": "Trưởng phòng", "thu_tu": 1,
                                                   "nguoi_ky": [{"chuc_vu_id": self.position.pk, "thu_tu": 1}]}])
        pk = self.tao_nhap().data["id"]
        with mock.patch(TIM_UNG_VIEN, return_value=[self.ky1, self.la]):
            r = self.gui(pk, khoa="a")
            self.assertEqual(r.data["code"], "can_chon_nguoi_ky")
            van_de = r.data["fields"]["nguoi_ky"][0]
            self.assertEqual([(u["id"], u["co_quyen_ky"]) for u in van_de["ung_vien"]],
                             [(self.ky1.pk, True), (self.la.pk, False)])
            r = self.gui(pk, khoa="b", chon_nguoi_ky={str(van_de["cau_hinh"]): self.la.pk})
            self.assertEqual((r.status_code, r.data["code"]), (400, "nguoi_ky_thieu_quyen_ky"))
            self.kiem_tra_khong_tao_ban_ghi(pk)
            r = self.gui(pk, khoa="c", chon_nguoi_ky={str(van_de["cau_hinh"]): self.ky1.pk})
        self.assertEqual(r.status_code, 200, r.data)

    def test_signers_with_permission_endpoint_lists_only_permitted_accounts(self):
        cap_quyen(self.tao, "manage_signing_process")
        r = self.client_cua(User.objects.get(pk=self.tao.pk)).get("/api/v1/signing/nguoi-ky-co-quyen/")
        self.assertEqual(r.status_code, 200, r.data)
        ids = set(r.data["ids"])
        self.assertTrue({self.ky1.pk, self.ky2.pk, self.ky3.pk} <= ids)
        self.assertNotIn(self.la.pk, ids)

    def test_signers_with_permission_endpoint_requires_manage_permission(self):
        r = self.c.get("/api/v1/signing/nguoi-ky-co-quyen/")
        self.assertEqual((r.status_code, r.data["fields"]), (403, {"quyen": ["manage_signing_process"]}))
