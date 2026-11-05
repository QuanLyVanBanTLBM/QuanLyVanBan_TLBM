"""
Hồ sơ trình ký của văn bản hạn chế (`pham_vi = 'HAN_CHE'`) bị từ chối trên dữ liệu thật của module Văn bản
(issue #501; mục Nhóm 5 của #83). Không giả lập lớp tích hợp: văn bản đi, người nhận và tệp đính kèm là bản ghi thật.
"""

import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from documents.models import PhamVi, VanBanDi, VanBanDiAttachment
from rest_framework.test import APIClient

from signing import enums
from signing.models import SigningRequest
from signing.errors import SigningError
from signing.services import process as process_service
from signing.tich_hop import van_ban as tich_hop_van_ban

from .helpers import cap_quyen
from .test_trinh_ky_phase7 import BASE, PDF

User = get_user_model()
MA_LOI = "van_ban_han_che_khong_trinh_ky"


class TuChoiVanBanHanCheTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.thu_muc = tempfile.mkdtemp()
        cls._cai_dat = override_settings(SIGNING_DOCUMENT_ROOT=cls.thu_muc, DOCUMENT_STORAGE_ROOT=cls.thu_muc)
        cls._cai_dat.enable()

    @classmethod
    def tearDownClass(cls):
        cls._cai_dat.disable()
        shutil.rmtree(cls.thu_muc, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.tao = User.objects.create_user("nguoi_tao_ho_so")
        self.nguoi_nhan = User.objects.create_user("nguoi_nhan_van_ban")
        self.ky = User.objects.create_user("nguoi_ky")
        cap_quyen(self.tao, "add_trinhky", "send_trinhky", "view_vanbandi")
        cap_quyen(self.nguoi_nhan, "add_trinhky", "send_trinhky", "view_vanbandi")
        cap_quyen(self.ky, "sign_trinhky")
        quy_trinh = process_service.tao_quy_trinh(
            self.tao, ma_quy_trinh="QT-HC", ten_quy_trinh="Duyệt tờ trình", pham_vi=enums.PhamViQuyTrinh.CONG_TY,
            cap_ky=[{"cap_ky": 1, "ten_cap_ky": "Duyệt", "thu_tu": 1, "nguoi_ky": [{"nguoi_ky": self.ky, "thu_tu": 1}]}],
        )
        self.quy_trinh = process_service.kich_hoat(quy_trinh, self.tao)
        self.han_che = self.tao_van_ban("01/HC", pham_vi=PhamVi.HAN_CHE)
        self.han_che.nguoi_nhan.add(self.nguoi_nhan)
        self.noi_bo = self.tao_van_ban("02/NB", pham_vi=PhamVi.NOI_BO)

    def tao_van_ban(self, so_hieu, **kw):
        van_ban = VanBanDi.objects.create(so_hieu=so_hieu, trich_yeu=f"Trích yếu {so_hieu}", nguoi_tao=self.tao, **kw)
        tep = VanBanDiAttachment(document=van_ban, name="dinh-kem.pdf", nguoi_tao=self.tao)
        tep.file.save("dinh-kem.pdf", ContentFile(PDF), save=True)
        return van_ban

    def client_cua(self, user):
        client = APIClient()
        client.force_authenticate(User.objects.get(pk=user.pk))
        return client

    def tao_nhap_tu_van_ban(self, nguoi, van_ban):
        tep = van_ban.attachments.get()
        return self.client_cua(nguoi).post(f"{BASE}/", {
            "document_type": "vanbandi", "van_ban_id": van_ban.pk, "quy_trinh": self.quy_trinh.pk,
            "tep_dinh_kem_id": tep.pk}, format="multipart")

    def test_create_draft_from_restricted_document_rejected_for_creator_and_recipient(self):
        for nguoi in (self.tao, self.nguoi_nhan):  # người được xem theo Nhóm 2 vẫn không được trình ký
            r = self.tao_nhap_tu_van_ban(nguoi, self.han_che)
            self.assertEqual((r.status_code, r.data["code"]), (400, MA_LOI), nguoi.username)
        self.assertFalse(SigningRequest.objects.exists())

    def test_normal_document_still_accepted(self):
        r = self.tao_nhap_tu_van_ban(self.tao, self.noi_bo)
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data["van_ban_id"], self.noi_bo.pk)

    def test_send_rechecks_document_that_became_restricted(self):
        r = self.tao_nhap_tu_van_ban(self.tao, self.noi_bo)
        self.assertEqual(r.status_code, 201, r.data)
        pk = r.data["id"]
        SigningRequest.objects.filter(pk=pk).update(van_ban_id=self.han_che.pk)
        r = self.client_cua(self.tao).post(f"{BASE}/{pk}/gui/", {}, format="json", HTTP_IDEMPOTENCY_KEY="gui-hc")
        self.assertEqual((r.status_code, r.data["code"]), (400, MA_LOI))
        self.assertEqual(SigningRequest.objects.get(pk=pk).trang_thai, enums.TrangThaiYeuCau.NHAP)

    def test_link_to_restricted_document_rejected_by_shared_check(self):
        """Liên kết hồ sơ đã hoàn tất với văn bản đi dùng cùng hàm kiểm tra với tạo và gửi hồ sơ."""
        with self.assertRaises(SigningError) as ctx:
            tich_hop_van_ban.kiem_tra_van_ban_trinh_ky(self.tao, "vanbandi", self.han_che.pk)
        self.assertEqual(ctx.exception.detail.code, MA_LOI)

    def test_search_hides_restricted_document(self):
        r = self.client_cua(self.tao).get("/api/v1/signing/van-ban-di/")
        self.assertEqual(r.status_code, 200, r.data)
        so_hieu = [v["so_hieu"] for v in (r.data["results"] if isinstance(r.data, dict) and "results" in r.data else r.data)]
        self.assertIn("02/NB", so_hieu)
        self.assertNotIn("01/HC", so_hieu)
