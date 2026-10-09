"""
Tích hợp với dữ liệu thật của Nhóm 2 (văn bản đi, hàm xem văn bản dùng chung) và Nhóm 7 (Đơn vị, Chức vụ),
không giả lập lớp tích hợp.
"""
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models import ProtectedError
from django.test import TestCase
from documents.models import PhamVi, VanBanDi
from rest_framework.test import APIClient

from signing.errors import SigningError
from signing.models import SigningProcess, SigningProcessStepSigner, SigningRequest
from signing.tich_hop import van_ban

from .helpers import cap_quyen, tao_chuc_vu, tao_don_vi
from .test_trinh_ky_phase7 import PDF

User = get_user_model()
QT = "/api/v1/signing/quy-trinh"


def tao_van_ban(nguoi_tao, so_hieu, **kw):
    return VanBanDi.objects.create(so_hieu=so_hieu, trich_yeu=f"Trích yếu {so_hieu}", nguoi_tao=nguoi_tao, **kw)


class VanBanNhom2Tests(TestCase):
    def setUp(self):
        self.tao = User.objects.create_user("nguoi_tao_vb")
        self.khac = User.objects.create_user("nguoi_khac")
        self.cong_khai = tao_van_ban(self.tao, "01/TTr")
        self.khong_cong_khai = tao_van_ban(self.tao, "02/TTr", hien_thi=False)
        self.han_che = tao_van_ban(self.tao, "03/TTr", pham_vi=PhamVi.HAN_CHE)

    def ma_loi(self, nguoi, van_ban_id):
        with self.assertRaises(SigningError) as ctx:
            van_ban.kiem_tra_van_ban_trinh_ky(nguoi, "vanbandi", van_ban_id)
        return ctx.exception.status_code, ctx.exception.detail.code

    def test_visibility_follows_group_2_rules(self):
        # hien_thi=True không thay thế quyền view_vanbandi theo issue #83.
        self.assertEqual(self.ma_loi(self.khac, self.cong_khai.pk), (404, "khong_tim_thay_van_ban"))
        self.assertEqual(self.ma_loi(self.khac, self.khong_cong_khai.pk), (404, "khong_tim_thay_van_ban"))
        cap_quyen(self.khac, "view_vanbandi")
        khac = User.objects.get(pk=self.khac.pk)
        self.assertEqual(van_ban.kiem_tra_van_ban_trinh_ky(khac, "vanbandi", self.cong_khai.pk).pk,
                         self.cong_khai.pk)
        self.assertEqual(van_ban.kiem_tra_van_ban_trinh_ky(khac, "vanbandi", self.khong_cong_khai.pk).pk,
                         self.khong_cong_khai.pk)

    def test_restricted_and_missing_documents_rejected(self):
        self.assertEqual(self.ma_loi(self.tao, self.han_che.pk), (400, "van_ban_han_che_khong_trinh_ky"))
        self.assertEqual(self.ma_loi(self.tao, 999999), (404, "khong_tim_thay_van_ban"))

    def test_api_restricted_document_error_respects_visibility(self):
        viewer = User.objects.create_user("nguoi_co_quyen_xem_vb")
        admin = User.objects.create_superuser(username="quan_tri_ngoai_danh_sach", password="test")
        recipient = User.objects.create_user("nguoi_nhan_vb")
        cap_quyen(viewer, "view_vanbandi")
        self.han_che.nguoi_nhan.add(recipient)
        process = SigningProcess.objects.create(
            ma_quy_trinh="QT-QUYEN-XEM", ten_quy_trinh="Kiểm tra quyền xem văn bản",
            pham_vi="CONG_TY", trang_thai="HOAT_DONG", create_by=self.tao,
        )

        # Quyền view_* và superuser không mở quyền xem HAN_CHE ngoài danh sách (#83).
        for user, restricted_status in ((self.khac, 404), (viewer, 404), (admin, 404),
                                        (self.tao, 400), (recipient, 400)):
            cap_quyen(user, "add_trinhky")
            client = APIClient()
            client.force_authenticate(User.objects.get(pk=user.pk))
            with self.subTest(user=user.username):
                responses = {}
                for label, document_id in (("restricted", self.han_che.pk), ("missing", 999999)):
                    responses[label] = client.post("/api/v1/signing/trinh-ky/", {
                        "document_type": "vanbandi", "van_ban_id": document_id,
                        "quy_trinh": process.pk, "muc_do": "THUONG",
                        "tep": SimpleUploadedFile("du-thao.pdf", PDF, content_type="application/pdf"),
                    }, format="multipart")

                self.assertEqual(responses["missing"].status_code, 404, responses["missing"].data)
                self.assertEqual(responses["restricted"].status_code, restricted_status,
                                 responses["restricted"].data)
                if restricted_status == 404:
                    self.assertEqual(responses["restricted"].data, responses["missing"].data)
                else:
                    # Người được xem vẫn bị chặn trình ký HAN_CHE, nhưng được nhận lỗi nghiệp vụ.
                    self.assertEqual(responses["restricted"].data["code"], "van_ban_han_che_khong_trinh_ky")
        self.assertFalse(SigningRequest.objects.exists())

    def test_search_excludes_restricted_and_filters_keyword(self):
        # Người không có quyền không nhìn thấy văn bản NOI_BO dù hien_thi=True.
        self.assertEqual(van_ban.tim_van_ban_di(self.khac), [])
        cap_quyen(self.khac, "view_vanbandi")
        khac = User.objects.get(pk=self.khac.pk)
        self.assertEqual([v["so_hieu"] for v in van_ban.tim_van_ban_di(khac)], ["02/TTr", "01/TTr"])
        self.assertEqual([v["so_hieu"] for v in van_ban.tim_van_ban_di(khac, "01/")], ["01/TTr"])

    def test_description_for_evidence(self):
        self.assertEqual(van_ban.mo_ta_van_ban("vanbandi", self.cong_khai.pk),
                         {"so_hieu": "01/TTr", "trich_yeu": "Trích yếu 01/TTr"})
        self.assertEqual(van_ban.mo_ta_van_ban("vanbandi", 999999), {})


class ToChucNhom7Tests(TestCase):
    def setUp(self):
        self.quan_tri = User.objects.create_user("quan_tri_qt")
        self.ky = User.objects.create_user("nguoi_ky_qt")
        cap_quyen(self.quan_tri, "manage_signing_process", "view_trinhky")
        self.c = APIClient()
        self.c.force_authenticate(User.objects.get(pk=self.quan_tri.pk))
        self.chuc_vu = tao_chuc_vu()
        self.don_vi = tao_don_vi()

    def tao(self, ma, pham_vi="CONG_TY", don_vi_ap_dung_id=None, don_vi_id=None, chuc_vu_id=None):
        nguoi_ky = {"chuc_vu_id": chuc_vu_id, "thu_tu": 1} if chuc_vu_id else {"nguoi_ky": self.ky.pk, "thu_tu": 1}
        return self.c.post(f"{QT}/", {
            "ma_quy_trinh": ma, "ten_quy_trinh": ma, "pham_vi": pham_vi, "don_vi_ap_dung_id": don_vi_ap_dung_id,
            "cap_ky": [{"cap_ky": 1, "ten_cap_ky": "C", "thu_tu": 1, "don_vi_id": don_vi_id,
                        "nguoi_ky": [nguoi_ky]}]}, format="json")

    def test_real_unit_and_position_accepted(self):
        r = self.tao("PB", "PHONG_BAN", don_vi_ap_dung_id=self.don_vi.pk, don_vi_id=self.don_vi.pk,
                     chuc_vu_id=self.chuc_vu.pk)
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual((r.data["don_vi_ap_dung_id"], r.data["ten_don_vi_ap_dung"]), (self.don_vi.pk, self.don_vi.ten))
        self.assertEqual(r.data["cap_ky"][0]["don_vi_id"], self.don_vi.pk)
        self.assertEqual(r.data["cap_ky"][0]["nguoi_ky"][0]["chuc_vu_id"], self.chuc_vu.pk)

    def test_unknown_unit_or_position_rejected_with_field(self):
        for kw, truong, ma in ((
            {"pham_vi": "PHONG_BAN", "don_vi_ap_dung_id": 999999}, "don_vi_ap_dung_id", "don_vi_khong_ton_tai"),
            ({"don_vi_id": 999999}, "don_vi_id", "don_vi_khong_ton_tai"),
            ({"chuc_vu_id": 999999}, "chuc_vu_id", "chuc_vu_khong_ton_tai"),
        ):
            r = self.tao(f"SAI-{truong}", **kw)
            self.assertEqual((r.status_code, r.data["code"], list(r.data["fields"])), (400, ma, [truong]))

    def test_position_in_use_cannot_be_deleted(self):
        self.assertEqual(self.tao("CV", chuc_vu_id=self.chuc_vu.pk).status_code, 201)
        self.assertTrue(SigningProcessStepSigner.objects.filter(chuc_vu=self.chuc_vu).exists())
        with self.assertRaises(ProtectedError):
            self.chuc_vu.delete()

    def test_unit_choices_by_role(self):
        khac = tao_don_vi()
        ids = {d["id"] for d in self.c.get("/api/v1/signing/don-vi/").data}
        self.assertTrue({self.don_vi.pk, khac.pk} <= ids)  # quản trị: mọi đơn vị
        tp = User.objects.create_user("truong_phong_qt")
        cap_quyen(tp, "manage_signing_process")
        c = APIClient()
        c.force_authenticate(User.objects.get(pk=tp.pk))
        with mock.patch("signing.tich_hop.to_chuc.ma_nhom_cua", return_value={"TP"}),                 mock.patch("signing.tich_hop.to_chuc.don_vi_cua", return_value=self.don_vi.pk):
            self.assertEqual(c.get("/api/v1/signing/don-vi/").data, [{"id": self.don_vi.pk, "ten": self.don_vi.ten}])
        self.assertEqual(self.client_khong_quyen().get("/api/v1/signing/don-vi/").status_code, 403)

    def client_khong_quyen(self):
        c = APIClient()
        c.force_authenticate(self.ky)
        return c
