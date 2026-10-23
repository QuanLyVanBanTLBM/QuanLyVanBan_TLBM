"""
Tích hợp với dữ liệu thật của Nhóm 2 (văn bản đi, hàm xem văn bản dùng chung) và Nhóm 7 (Đơn vị, Chức vụ),
không giả lập lớp tích hợp.
"""
from unittest import mock

from django.contrib.auth import get_user_model
from django.db.models import ProtectedError
from django.test import TestCase
from documents.models import PhamVi, VanBanDi
from rest_framework.test import APIClient

from signing.errors import SigningError
from signing.models import SigningProcessStepSigner
from signing.tich_hop import van_ban

from .helpers import cap_quyen, tao_chuc_vu, tao_don_vi

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
        self.assertEqual(van_ban.kiem_tra_van_ban_trinh_ky(self.khac, "vanbandi", self.cong_khai.pk).pk,
                         self.cong_khai.pk)  # nội bộ công khai: ai cũng xem
        self.assertEqual(self.ma_loi(self.khac, self.khong_cong_khai.pk), (404, "khong_tim_thay_van_ban"))
        cap_quyen(self.khac, "view_vanbandi")
        khac = User.objects.get(pk=self.khac.pk)
        self.assertEqual(van_ban.kiem_tra_van_ban_trinh_ky(khac, "vanbandi", self.khong_cong_khai.pk).pk,
                         self.khong_cong_khai.pk)

    def test_restricted_and_missing_documents_rejected(self):
        self.assertEqual(self.ma_loi(self.tao, self.han_che.pk), (400, "van_ban_han_che_khong_trinh_ky"))
        self.assertEqual(self.ma_loi(self.tao, 999999), (404, "khong_tim_thay_van_ban"))

    def test_search_excludes_restricted_and_filters_keyword(self):
        # Không có quyền xem văn bản đi: chỉ thấy văn bản nội bộ công khai (quy tắc Nhóm 2)
        self.assertEqual([v["so_hieu"] for v in van_ban.tim_van_ban_di(self.khac)], ["01/TTr"])
        cap_quyen(self.tao, "view_vanbandi")
        tao = User.objects.get(pk=self.tao.pk)
        self.assertEqual([v["so_hieu"] for v in van_ban.tim_van_ban_di(tao)], ["02/TTr", "01/TTr"])
        self.assertEqual([v["so_hieu"] for v in van_ban.tim_van_ban_di(tao, "01/")], ["01/TTr"])

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

    def test_user_search_by_name_position_unit_without_accents(self):
        User.objects.filter(pk=self.ky.pk).update(ho_ten="Trần Đức Trưởng", chuc_vu=self.chuc_vu, don_vi=self.don_vi, chuc_danh="Kiểm toán viên")

        def tim(q):
            return [u["ten_dang_nhap"] for u in self.c.get("/api/v1/signing/nguoi-dung/", {"q": q}).data]
        self.assertIn("nguoi_ky_qt", tim("tran duc"))  # không dấu
        self.assertIn("nguoi_ky_qt", tim("ĐỨC TRƯỞNG"))  # hoa, có dấu
        self.assertIn("nguoi_ky_qt", tim(self.chuc_vu.name.lower()))  # chức vụ
        self.assertIn("nguoi_ky_qt", tim("kiem toan"))  # chức danh tự do
        self.assertIn("nguoi_ky_qt", tim(self.don_vi.ten))  # đơn vị
        self.assertEqual(tim("khong-co-ai"), [])
        r = self.c.get("/api/v1/signing/nguoi-dung/", {"q": "tran duc"}).data[0]
        self.assertEqual((r["chuc_vu"], r["don_vi"]), (self.chuc_vu.name, self.don_vi.ten))
