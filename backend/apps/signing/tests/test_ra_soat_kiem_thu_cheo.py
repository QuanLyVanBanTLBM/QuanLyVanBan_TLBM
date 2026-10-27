"""
Lỗi người kiểm thử chéo có thể bắt qua API (rà soát trước kiểm thử chéo): tham số lọc sai gây lỗi 500, từ khóa chứa
ký tự NUL, nội dung JSON không phải đối tượng, giá trị số/độ dài vượt giới hạn, thông báo lỗi validation bằng tiếng
Anh, người ký trùng trong cấp, mã quy trình sai định dạng, tiêu đề email chứa xuống dòng.
"""
from django.core import mail
from django.test import override_settings

from signing import enums
from signing.models import SigningNotification
from signing.permissions import QUAN_LY_QUY_TRINH

from .helpers import cap_quyen
from .test_hanh_dong_ky_phase8 import KyBase
from .test_trinh_ky_phase7 import BASE, TrinhKyBase

API = "/api/v1/signing"
QT = f"{API}/quy-trinh"


class LocTimKiemKhongLoiMayChuTests(TrinhKyBase):
    """Tham số lọc và từ khóa tùy ý chỉ được trả 200 hoặc 400, không bao giờ 500."""

    def setUp(self):
        super().setUp()
        self.assertEqual(self.tao_nhap().status_code, 201)

    def test_calendar_invalid_date_returns_400_not_500(self):
        for duong_dan in (f"{BASE}/", f"{API}/tai-lieu/"):
            for ten in ("tu_ngay", "den_ngay"):
                for gia_tri in ("2026-13-45", "2026-02-30", "0000-00-00"):
                    r = self.c.get(duong_dan, {ten: gia_tri})
                    self.assertEqual(r.status_code, 400, (duong_dan, ten, gia_tri))
                    self.assertEqual(r.data["code"], "tham_so_khong_hop_le")
                    self.assertIn(ten, r.data["fields"])

    def test_nul_character_in_search_is_ignored(self):
        for duong_dan in (f"{BASE}/", f"{API}/tai-lieu/", f"{API}/van-ban-di/", f"{API}/nguoi-dung/"):
            r = self.c.get(duong_dan, {"q": "a\x00b"})
            self.assertIn(r.status_code, (200, 403), duong_dan)

    def test_search_term_only_nul_returns_everything(self):
        r = self.c.get(f"{BASE}/", {"hop": "toi_gui", "q": "\x00"})
        self.assertEqual((r.status_code, r.data["count"]), (200, 1))


class ThongKeTheoBoLocTests(TrinhKyBase):
    """Số trên thẻ lọc nhanh khớp với danh sách đang xem: cùng từ khóa, quy trình, khoảng ngày."""

    THONG_KE = f"{BASE}/thong-ke/"

    def setUp(self):
        super().setUp()
        for trich_yeu in ("Mua sắm thiết bị mạng", "Đào tạo an toàn thông tin"):
            r = self.tao_nhap(van_ban_id="", document_type="", trich_yeu_van_ban=trich_yeu)
            self.assertEqual(r.status_code, 201, r.data)

    def dem(self, **loc):
        r = self.c.get(self.THONG_KE, {"hop": "toi_gui", **loc})
        self.assertEqual(r.status_code, 200, r.data)
        return r.data["tat_ca"]

    def test_counts_follow_search_term_and_dates(self):
        self.assertEqual(self.dem(), 2)
        self.assertEqual(self.dem(q="mua sam"), 1)
        self.assertEqual(self.dem(q="khong co"), 0)
        self.assertEqual(self.dem(tu_ngay="2999-01-01"), 0)
        self.assertEqual(self.dem(den_ngay="2000-01-01"), 0)
        self.assertEqual(self.dem(tu_ngay="2000-01-01", den_ngay="2999-01-01"), 2)
        self.assertEqual(self.dem(quy_trinh=self.process.pk), 2)
        self.assertEqual(self.dem(quy_trinh=self.process.pk + 1000), 0)

    def test_quick_filter_param_is_not_applied_to_its_own_counts(self):
        self.assertEqual(self.dem(nhanh="hoan_thanh", trang_thai="HUY"), 2)

    def test_invalid_filter_returns_400(self):
        for loc in ({"tu_ngay": "2026-13-45"}, {"tu_ngay": "2026-10-30", "den_ngay": "2026-10-01"}, {"quy_trinh": "abc"}):
            r = self.c.get(self.THONG_KE, {"hop": "toi_gui", **loc})
            self.assertEqual((r.status_code, r.data["code"]), (400, "tham_so_khong_hop_le"), loc)
        self.assertEqual(self.dem(q="a\x00b"), 0)


class QuyTrinhDauVaoTests(TrinhKyBase):
    def setUp(self):
        super().setUp()
        cap_quyen(self.tao, QUAN_LY_QUY_TRINH)

    def body(self, **ghi_de):
        data = {"ma_quy_trinh": "QT-NHAP-1", "ten_quy_trinh": "Quy trình thử", "pham_vi": "CONG_TY", "cap_ky": [
            {"cap_ky": 1, "ten_cap_ky": "Cấp 1", "thu_tu": 1, "nguoi_ky": [{"nguoi_ky": self.ky1.pk, "thu_tu": 1}]}]}
        data.update(ghi_de)
        return data

    def test_put_with_non_object_body_returns_400(self):
        r = self.c.post(f"{QT}/", self.body(), format="json")
        self.assertEqual(r.status_code, 201, r.data)
        for noi_dung in ([], "abc", 5):
            r2 = self.c.put(f"{QT}/{r.data['id']}/", noi_dung, format="json")
            self.assertEqual(r2.status_code, 400, noi_dung)
            self.assertEqual(r2.data["code"], "du_lieu_khong_hop_le")

    def test_processing_hours_must_be_in_range(self):
        cap = {"cap_ky": 1, "ten_cap_ky": "Cấp 1", "thu_tu": 1, "nguoi_ky": [{"nguoi_ky": self.ky1.pk, "thu_tu": 1}]}
        for gio in (2 ** 31, 10 ** 20, 8761):
            r = self.c.post(f"{QT}/", self.body(cap_ky=[{**cap, "so_gio_xu_ly": gio}]), format="json")
            self.assertEqual(r.status_code, 400, gio)
            self.assertIn("so_gio_xu_ly", r.json()["fields"]["cap_ky"]["0"])
        r = self.c.post(f"{QT}/", self.body(cap_ky=[{**cap, "so_gio_xu_ly": 8760}]), format="json")
        self.assertEqual(r.status_code, 201, r.data)

    def test_process_code_format(self):
        for ma in ("QT #1", "QT<b>", "qt/1", "Mã có dấu"):
            r = self.c.post(f"{QT}/", self.body(ma_quy_trinh=ma), format="json")
            self.assertEqual(r.status_code, 400, ma)
            self.assertIn("ma_quy_trinh", r.data["fields"])
        r = self.c.post(f"{QT}/", self.body(ma_quy_trinh="QT_PB.2026-01"), format="json")
        self.assertEqual(r.status_code, 201, r.data)

    def test_process_code_is_unique_ignoring_case(self):
        self.assertEqual(self.c.post(f"{QT}/", self.body(ma_quy_trinh="QT-HOA"), format="json").status_code, 201)
        r = self.c.post(f"{QT}/", self.body(ma_quy_trinh="qt-hoa"), format="json")
        self.assertEqual((r.status_code, r.data["code"]), (409, "quy_trinh_trung_ma"))

    def test_same_signer_twice_in_level_is_rejected(self):
        cap = {"cap_ky": 1, "ten_cap_ky": "Cấp 1", "thu_tu": 1, "nguoi_ky": [
            {"nguoi_ky": self.ky1.pk, "thu_tu": 1}, {"nguoi_ky": self.ky1.pk, "thu_tu": 2}]}
        r = self.c.post(f"{QT}/", self.body(cap_ky=[cap]), format="json")
        self.assertEqual((r.status_code, r.data["code"]), (400, "nguoi_ky_trung_trong_cap"))
        chuc_vu = self.position.pk
        cap["nguoi_ky"] = [{"chuc_vu_id": chuc_vu, "pham_vi_chuc_vu": "TOAN_CO_QUAN", "thu_tu": 1},
                           {"chuc_vu_id": chuc_vu, "pham_vi_chuc_vu": "TOAN_CO_QUAN", "thu_tu": 2}]
        r = self.c.post(f"{QT}/", self.body(cap_ky=[cap]), format="json")
        self.assertEqual((r.status_code, r.data["code"]), (400, "nguoi_ky_trung_trong_cap"))

    def test_text_lengths_are_limited(self):
        r = self.c.post(f"{QT}/", self.body(mo_ta="m" * 2001), format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("mo_ta", r.data["fields"])


class DoDaiNoiDungTests(KyBase):
    def test_create_draft_text_limits(self):
        r = self.tao_nhap(van_ban_id="", document_type="", trich_yeu_van_ban="x" * 1001)
        self.assertEqual(r.status_code, 400)
        self.assertIn("trich_yeu_van_ban", r.data["fields"])
        r = self.tao_nhap(ghi_chu="g" * 2001)
        self.assertEqual(r.status_code, 400)
        self.assertIn("ghi_chu", r.data["fields"])

    def test_action_reasons_are_limited(self):
        dai = "l" * 2001
        r = self.hanh_dong(self.ky1, "tu-choi", ly_do_tu_choi=dai)
        self.assertEqual(r.status_code, 400)
        self.assertIn("ly_do_tu_choi", r.data["fields"])
        r = self.hanh_dong(self.ky1, "yeu-cau-sua", tieu_de="Sửa", ly_do=dai)
        self.assertEqual(r.status_code, 400)
        self.assertIn("ly_do", r.data["fields"])
        r = self.c.post(f"{BASE}/{self.pk}/huy/", {"ly_do": dai}, format="json", HTTP_IDEMPOTENCY_KEY="huy-dai")
        self.assertEqual(r.status_code, 400)
        self.assertIn("ly_do", r.data["fields"])

    def test_message_is_limited(self):
        self.assertEqual(self.hanh_dong(self.ky1, "yeu-cau-sua", tieu_de="Sửa", ly_do="Sai số liệu").status_code, 200)
        r = self.c.post(f"{BASE}/{self.pk}/trao-doi/", {"noi_dung": "n" * 2001}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("noi_dung", r.data["fields"])
        r = self.c.post(f"{BASE}/{self.pk}/trao-doi/", {"noi_dung": "n" * 2000}, format="json")
        self.assertEqual(r.status_code, 201, r.data)


class TenNguoiVietTinNhanTests(KyBase):
    def test_messages_carry_writer_name(self):
        self.assertEqual(self.hanh_dong(self.ky1, "yeu-cau-sua", tieu_de="Sửa", ly_do="Sai số liệu").status_code, 200)
        self.assertEqual(self.c.post(f"{BASE}/{self.pk}/trao-doi/", {"noi_dung": "Đã nhận"}, format="json")
                         .data["ten_nguoi_viet"], "chuyen_vien")
        r = self.client_cua(self.ky1).post(f"{BASE}/{self.pk}/trao-doi/", {"noi_dung": "Cần số liệu"}, format="json")
        self.assertEqual((r.status_code, r.data["ten_nguoi_viet"]), (201, "ke_toan"))
        r = self.c.get(f"{BASE}/{self.pk}/trao-doi/")
        self.assertEqual([(m["nguoi_viet"], m["ten_nguoi_viet"]) for m in r.data["tin_nhan"]],
                         [(self.tao.pk, "chuyen_vien"), (self.ky1.pk, "ke_toan")])


class ThongBaoLoiTiengVietTests(TrinhKyBase):
    """`fields` của lỗi validation cũng phải bằng tiếng Việt (giao diện và người kiểm thử đọc cả hai)."""

    def test_validation_messages_are_vietnamese(self):
        r = self.tao_nhap(han_chot="khong-phai-ngay")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.data["fields"]["han_chot"], ["Ngày giờ không đúng định dạng."])
        r = self.tao_nhap(quy_trinh=999999)
        self.assertEqual(r.data["fields"]["quy_trinh"], ["Không tồn tại."])
        r = self.tao_nhap(quy_trinh="abc")
        self.assertEqual(r.data["fields"]["quy_trinh"], ["Giá trị không hợp lệ."])
        r = self.tao_nhap(van_ban_id="abc")
        self.assertEqual(r.data["fields"]["van_ban_id"], ["Phải là số nguyên."])
        r = self.tao_nhap(document_type="xxx")
        self.assertEqual(r.data["fields"]["document_type"], ["Giá trị không hợp lệ."])

    def test_max_length_message_names_the_limit(self):
        r = self.tao_nhap(document_type="", van_ban_id="", so_hieu_van_ban="s" * 101, trich_yeu_van_ban="x")
        self.assertEqual(r.data["fields"]["so_hieu_van_ban"], ["Tối đa 100 ký tự."])

    def test_non_object_body_message(self):
        r = self.c.post(f"{BASE}/{self.tao_nhap().data['id']}/huy/", [], format="json", HTTP_IDEMPOTENCY_KEY="h")
        self.assertEqual(r.data["fields"]["non_field_errors"], ["Dữ liệu phải là một đối tượng."])


class TieuDeEmailTests(KyBase):
    """Văn bản có xuống dòng trong trích yếu không được làm hỏng email (BadHeaderError)."""

    def test_subject_with_newline_still_sends(self):
        from django.contrib.auth import get_user_model
        get_user_model().objects.filter(pk=self.ky1.pk).update(email="ky1@demo.local")
        mail.outbox.clear()
        with override_settings(SIGNING_EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"), \
                self.captureOnCommitCallbacks(execute=True):
            r = self.tao_nhap(van_ban_id="", document_type="", so_hieu_van_ban="12/TTr",
                              trich_yeu_van_ban="Dòng một\r\nDòng hai\nDòng ba")
            self.assertEqual(r.status_code, 201, r.data)
            self.assertEqual(self.gui(r.data["id"], khoa="gui-xuong-dong").status_code, 200)
        email = SigningNotification.objects.get(trinh_ky_id=r.data["id"], nguoi_nhan=self.ky1,
                                                kenh=enums.KenhThongBao.EMAIL)
        self.assertEqual((email.trang_thai, email.loi_gui), (enums.TrangThaiThongBao.DA_GUI, ""))
        self.assertEqual(len(mail.outbox), 1)
        self.assertNotIn("\n", mail.outbox[0].subject)
        self.assertIn("Dòng một Dòng hai Dòng ba", mail.outbox[0].subject)
        self.assertIn("Dòng một Dòng hai Dòng ba", mail.outbox[0].body)

