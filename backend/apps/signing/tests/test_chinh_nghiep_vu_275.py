"""
Chỉnh nghiệp vụ trình ký (#275): văn bản trình ký chọn văn bản đi hoặc nhập văn bản khác, nhãn "Văn bản trình ký"
trong thông báo/email, tên chức vụ của người ký cấu hình theo Danh mục chức vụ (CBNV).
"""
from django.contrib.auth import get_user_model
from django.core import mail

from signing import enums, selectors
from signing.models import SigningNotification, SigningRequest
from signing.services import thong_bao as thong_bao_service

from .test_chuc_nang_nhom_5 import QT
from .test_hanh_dong_ky_phase8 import KyBase
from .test_trinh_ky_phase7 import BASE, TrinhKyBase, tep_pdf

User = get_user_model()


class VanBanNhapTayTests(TrinhKyBase):
    def tao_nhap_tay(self, **kw):
        data = {"quy_trinh": self.process.pk, "tep": tep_pdf(), "so_hieu_van_ban": " 05/TTr ",
                "trich_yeu_van_ban": " Tờ trình mua sắm thiết bị ", **kw}
        return self.c.post(f"{BASE}/", data, format="multipart")

    def test_create_without_outgoing_document_uses_manual_number_and_summary(self):
        r = self.tao_nhap_tay()
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual((r.data["document_type"], r.data["van_ban_id"]), (None, None))
        self.assertEqual(r.data["van_ban"], {"so_hieu": "05/TTr", "trich_yeu": "Tờ trình mua sắm thiết bị"})
        r = self.gui(r.data["id"], khoa="gui-nhap-tay")
        self.assertEqual((r.status_code, r.data["trang_thai"]), (200, "CHO_KY"))

    def test_manual_summary_required_when_no_outgoing_document(self):
        r = self.tao_nhap_tay(trich_yeu_van_ban="  ")
        self.assertEqual((r.status_code, r.data["code"]), (400, "thieu_van_ban_trinh_ky"))
        self.assertIn("trich_yeu_van_ban", r.data["fields"])
        self.assertFalse(SigningRequest.objects.exists())

    def test_outgoing_document_wins_over_manual_fields(self):
        r = self.tao_nhap(so_hieu_van_ban="X", trich_yeu_van_ban="Bị bỏ qua")
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data["van_ban"], {"so_hieu": "10/QD", "trich_yeu": "Mua sắm"})
        self.assertEqual((r.data["so_hieu_van_ban"], r.data["trich_yeu_van_ban"]), ("", ""))
        # Gắn văn bản đi thì không sửa số hiệu/trích yếu nhập tay
        r = self.c.patch(f"{BASE}/{r.data['id']}/", {"trich_yeu_van_ban": "Khác"}, format="multipart")
        self.assertEqual((r.status_code, r.data["code"]), (400, "van_ban_da_gan"))

    def test_manual_documents_do_not_block_each_other_and_are_searchable(self):
        a = self.tao_nhap_tay().data["id"]
        b = self.tao_nhap_tay(trich_yeu_van_ban="Báo cáo quý").data["id"]  # không áp quy tắc một văn bản một hồ sơ
        r = self.c.get(f"{BASE}/", {"hop": "toi_gui", "q": "bao cao"})
        self.assertEqual([h["id"] for h in r.data["results"]], [b])
        r = self.c.get(f"{BASE}/", {"hop": "toi_gui", "q": "05/ttr"})
        self.assertEqual({h["id"] for h in r.data["results"]}, {a, b})
        tep = self.c.get("/api/v1/signing/tai-lieu/").data["results"]
        self.assertEqual({x["trinh_ky"]: x["van_ban"]["trich_yeu"] for x in tep}[a], "Tờ trình mua sắm thiết bị")

    def test_edit_manual_draft(self):
        pk = self.tao_nhap_tay().data["id"]
        r = self.c.patch(f"{BASE}/{pk}/", {"so_hieu_van_ban": "06/TTr", "trich_yeu_van_ban": "Đã sửa"},
                         format="multipart")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data["van_ban"], {"so_hieu": "06/TTr", "trich_yeu": "Đã sửa"})
        r = self.c.patch(f"{BASE}/{pk}/", {"trich_yeu_van_ban": ""}, format="multipart")
        self.assertEqual((r.status_code, r.data["code"]), (400, "thieu_van_ban_trinh_ky"))

    def test_dashboard_title_uses_manual_summary(self):
        pk = self.tao_nhap_tay().data["id"]
        phieu = selectors.tong_quan_dashboard(self.tao)["gan_day"]
        self.assertEqual(next(p for p in phieu if p["id"] == pk)["tieu_de"], "05/TTr — Tờ trình mua sắm thiết bị")


class VanBanNhapTayLuongKyTests(KyBase):
    def setUp(self):
        super().setUp()
        User.objects.filter(pk=self.ky1.pk).update(email="ky1@demo.local")
        r = self.c.post(f"{BASE}/", {"quy_trinh": self.process.pk, "tep": tep_pdf(),
                                     "trich_yeu_van_ban": "Kế hoạch đào tạo"}, format="multipart")
        self.assertEqual(r.status_code, 201, r.data)
        self.pk = r.data["id"]

    def test_email_labels_document_and_resubmit_keeps_manual_document(self):
        mail.outbox.clear()
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.gui(self.pk, khoa="gui-tay").status_code, 200)
        self.assertIn("Văn bản trình ký: Kế hoạch đào tạo.", mail.outbox[0].body)
        tb = SigningNotification.objects.get(trinh_ky_id=self.pk, nguoi_nhan=self.ky1, kenh=enums.KenhThongBao.IN_APP)
        self.assertEqual(thong_bao_service.noi_dung(tb)[2], "Kế hoạch đào tạo")

        r = self.hanh_dong(self.ky1, "tu-choi", ly_do_tu_choi="Chưa đủ")
        self.assertEqual(r.status_code, 200, r.data)
        r = self.c.post(f"{BASE}/{self.pk}/trinh-lai/", {}, format="json", HTTP_IDEMPOTENCY_KEY="trinh-lai-tay")
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual((r.data["van_ban_id"], r.data["van_ban"]["trich_yeu"]), (None, "Kế hoạch đào tạo"))


class ChucVuCauHinhTests(TrinhKyBase):
    def test_process_shows_position_name_from_staff_catalog(self):
        from .helpers import cap_quyen
        ql = User.objects.create_user("quan_ly_cv")
        cap_quyen(ql, "manage_signing_process", "view_trinhky")
        r = self.client_cua(User.objects.get(pk=ql.pk)).post(f"{QT}/", {
            "ma_quy_trinh": "CV1", "ten_quy_trinh": "Theo chức vụ", "pham_vi": "CONG_TY",
            "cap_ky": [{"cap_ky": 1, "ten_cap_ky": "C1", "thu_tu": 1, "nguoi_ky": [
                {"chuc_vu_id": self.position.pk, "pham_vi_chuc_vu": "TOAN_CO_QUAN", "thu_tu": 1}]}]}, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        nguoi_ky = r.data["cap_ky"][0]["nguoi_ky"][0]
        self.assertEqual((nguoi_ky["chuc_vu_id"], nguoi_ky["ten_chuc_vu"], nguoi_ky["ten_nguoi_ky"]),
                         (self.position.pk, "Trưởng phòng", None))


class CanBoTheoChucVuTests(TrinhKyBase):
    """#275 mục 8: chọn chức vụ (và đơn vị) thì thấy tên cán bộ đang giữ chức vụ đó."""

    URL = "/api/v1/signing/can-bo-theo-chuc-vu/"

    def setUp(self):
        super().setUp()
        from .helpers import tao_chuc_vu, tao_don_vi
        self.cv = tao_chuc_vu("Trưởng phòng thử")
        self.a, self.b = tao_don_vi("Phòng A"), tao_don_vi("Phòng B")
        tao = User.objects.create_user
        self.u_a = tao("tp_a", ho_ten="Nguyễn Văn A", chuc_vu=self.cv, don_vi=self.a)
        self.u_b = tao("tp_b", ho_ten="Trần Thị B", chuc_vu=self.cv, don_vi=self.b)
        tao("tp_khoa", ho_ten="Đã khóa", chuc_vu=self.cv, don_vi=self.a, is_active=False)
        tao("tp_nghi", ho_ten="Đã nghỉ", chuc_vu=self.cv, don_vi=self.a, trang_thai="NGHI_VIEC")
        tao("khac", ho_ten="Chức vụ khác", don_vi=self.a)
        self.xem = User.objects.create_user("xem_qt")
        from .helpers import cap_quyen
        cap_quyen(self.xem, "view_trinhky")

    def test_lists_active_staff_holding_position_optionally_in_unit(self):
        c = self.client_cua(User.objects.get(pk=self.xem.pk))
        r = c.get(self.URL, {"chuc_vu": self.cv.pk})
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data["count"], 2)
        self.assertEqual({x["id"] for x in r.data["results"]}, {self.u_a.pk, self.u_b.pk})
        dong = next(x for x in r.data["results"] if x["id"] == self.u_a.pk)
        self.assertEqual((dong["ten"], dong["don_vi_id"]), ("Nguyễn Văn A", self.a.pk))
        self.assertTrue(dong["chuc_vu"].startswith("Trưởng phòng thử"))
        r = c.get(self.URL, {"chuc_vu": self.cv.pk, "don_vi": self.b.pk})
        self.assertEqual([x["id"] for x in r.data["results"]], [self.u_b.pk])
        r = c.get(self.URL, {"chuc_vu": self.position.pk, "don_vi": self.b.pk})
        self.assertEqual((r.data["count"], r.data["results"]), (0, []))  # không có ai: giao diện cảnh báo

    def test_requires_process_permission_and_valid_params(self):
        self.assertEqual(self.client_cua(self.la).get(self.URL, {"chuc_vu": self.cv.pk}).status_code, 403)
        c = self.client_cua(User.objects.get(pk=self.xem.pk))
        for sai in ({}, {"chuc_vu": "x"}, {"chuc_vu": self.cv.pk, "don_vi": "y"}):
            r = c.get(self.URL, sai)
            self.assertEqual((r.status_code, r.data["code"]), (400, "tham_so_khong_hop_le"))
