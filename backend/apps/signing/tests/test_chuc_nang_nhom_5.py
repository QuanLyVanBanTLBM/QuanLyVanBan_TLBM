"""
Chức năng Nhóm 5 theo bảng phân công: bộ lọc danh sách, sửa/xóa quy trình nháp, tệp theo lượt (trang tài liệu),
thông báo + email người trong luồng (bảng signing_notification, kiêm outbox).
"""
from unittest import mock

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.management import call_command
from django.test import override_settings
from documents.models import VanBanDi

from signing import enums
from signing.models import SigningNotification, SigningProcess, SigningRequest

from .helpers import cap_quyen
from .test_hanh_dong_ky_phase8 import KyBase
from .test_trinh_ky_phase7 import BASE, TrinhKyBase

User = get_user_model()
QT = "/api/v1/signing/quy-trinh"


def thong_bao(user, loai=None, kenh=enums.KenhThongBao.IN_APP):
    qs = SigningNotification.objects.filter(nguoi_nhan=user, kenh=kenh)
    return qs.filter(loai_thong_bao=loai) if loai else qs


class HongEmail:
    """Backend email luôn lỗi, giả lập máy chủ thư không kết nối được."""

    def __init__(self, *a, **kw):
        pass

    def send_messages(self, messages):
        raise ConnectionRefusedError("Không kết nối được máy chủ thư")


class ThongBaoTests(KyBase):
    def setUp(self):
        super().setUp()
        for i, user in enumerate((self.tao, self.ky1, self.ky2, self.ky3)):
            User.objects.filter(pk=user.pk).update(email=f"nguoi{i}@demo.local")

    def gui_moi(self):
        with self.captureOnCommitCallbacks(execute=True):
            pk = self.tao_nhap().data["id"]
            self.assertEqual(self.gui(pk, khoa=f"gui-moi-{pk}").status_code, 200)
            self.assertEqual(self.gui(pk, khoa=f"gui-moi-{pk}").status_code, 200)  # gửi lặp cùng khóa
        self.pk = pk
        return pk

    def test_opened_signers_get_in_app_and_email_once(self):
        mail.outbox.clear()
        pk = self.gui_moi()
        self.assertEqual(thong_bao(self.ky1, "CAN_KY").filter(trinh_ky_id=pk).count(), 1)  # gửi lặp không tạo thêm
        self.assertFalse(thong_bao(self.ky2, "CAN_KY").filter(trinh_ky_id=pk).exists())  # ký chính bị ký nháy chặn
        self.assertEqual([m.to for m in mail.outbox], [["nguoi1@demo.local"]])
        self.assertIn("Cần ký duyệt", mail.outbox[0].subject)
        self.assertIn(f"/approvals/{pk}", mail.outbox[0].body)
        email = thong_bao(self.ky1, "CAN_KY", enums.KenhThongBao.EMAIL).get(trinh_ky_id=pk)
        self.assertEqual(email.trang_thai, enums.TrangThaiThongBao.DA_GUI)

    def test_flow_events_reach_people_in_flow_but_not_actor(self):
        pk = self.gui_moi()
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.ky(self.ky1).status_code, 200)  # ký nháy xong: mở ký chính
        self.assertTrue(thong_bao(self.ky2, "CAN_KY").filter(trinh_ky_id=pk).exists())
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.ky(self.ky2).status_code, 200)  # đóng cấp 1: mở cấp 2
        self.assertTrue(thong_bao(self.ky3, "CAN_KY").filter(trinh_ky_id=pk).exists())
        with self.captureOnCommitCallbacks(execute=True):
            r = self.ky(self.ky3)
        self.assertEqual(r.data["trang_thai"], "HOAN_THANH")
        for user in (self.tao, self.ky1, self.ky2):
            self.assertTrue(thong_bao(user, "HOAN_THANH").filter(trinh_ky_id=pk).exists(), user.username)
        self.assertFalse(thong_bao(self.ky3, "HOAN_THANH").exists())  # người thực hiện không tự nhận

    def test_reject_return_and_cancel_notifications(self):
        pk = self.gui_moi()
        r = self.hanh_dong(self.ky1, "tu-choi", ly_do_tu_choi="Chưa đạt")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertTrue(thong_bao(self.tao, "TU_CHOI").filter(trinh_ky_id=pk).exists())
        pk2 = self.gui_moi()
        r = self.hanh_dong(self.ky1, "yeu-cau-sua", tieu_de="Sửa mục 2", ly_do="Sai số liệu")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertTrue(thong_bao(self.tao, "YEU_CAU_SUA").filter(trinh_ky_id=pk2).exists())
        pk3 = self.gui_moi()
        r = self.c.post(f"{BASE}/{pk3}/huy/", {"ly_do": "Không trình nữa"}, format="json", HTTP_IDEMPOTENCY_KEY="huy-3")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertTrue(thong_bao(self.ky1, "HUY").filter(trinh_ky_id=pk3).exists())  # người đang được mở ký
        self.assertFalse(thong_bao(self.ky3, "HUY").filter(trinh_ky_id=pk3).exists())  # cấp chưa mở

    def test_failed_email_is_recorded_and_resent_by_command(self):
        with override_settings(SIGNING_EMAIL_BACKEND="signing.tests.test_chuc_nang_nhom_5.HongEmail"):
            pk = self.gui_moi()
        email = thong_bao(self.ky1, "CAN_KY", enums.KenhThongBao.EMAIL).get(trinh_ky_id=pk)
        self.assertEqual((email.trang_thai, email.so_lan_gui_lai), (enums.TrangThaiThongBao.THAT_BAI, 1))
        self.assertIn("máy chủ thư", email.loi_gui)
        self.assertEqual(SigningRequest.objects.get(pk=pk).trang_thai, "CHO_KY")  # nghiệp vụ không bị ảnh hưởng
        mail.outbox.clear()
        call_command("gui_thong_bao_trinh_ky", stdout=mock.MagicMock())
        email.refresh_from_db()
        self.assertEqual(email.trang_thai, enums.TrangThaiThongBao.DA_GUI)
        self.assertEqual(len(mail.outbox), 1)

    def test_user_without_email_only_in_app_and_api_lists_own(self):
        User.objects.filter(pk=self.ky1.pk).update(email="")
        pk = self.gui_moi()
        self.assertFalse(thong_bao(self.ky1, kenh=enums.KenhThongBao.EMAIL).filter(trinh_ky_id=pk).exists())
        r = self.client_cua(User.objects.get(pk=self.ky1.pk)).get("/api/v1/signing/thong-bao/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual((r.data[0]["loai_thong_bao"], r.data[0]["trinh_ky"]), ("CAN_KY", pk))
        self.assertEqual(r.data[0]["van_ban"], "20/QD — Văn bản thử")  # văn bản 10 thuộc hồ sơ tạo ở setUp
        self.assertTrue(r.data[0]["kenh_in_app"])
        self.assertFalse(r.data[0]["email_da_gui"])
        self.assertIsNone(r.data[0]["email_trang_thai"])
        self.assertEqual(self.client_cua(User.objects.get(pk=self.ky3.pk)).get("/api/v1/signing/thong-bao/").data, [])


class BoLocTests(TrinhKyBase):
    def setUp(self):
        super().setUp()
        VanBanDi.objects.create(id=10, so_hieu="10/QD", trich_yeu="Mua sắm thiết bị", nguoi_tao=self.tao)
        VanBanDi.objects.create(id=20, so_hieu="20/QD", trich_yeu="Bảo trì phần mềm", nguoi_tao=self.tao)
        self.a = self.tao_nhap(ghi_chu="Gấp").data["id"]
        self.qt2 = self.tao_quy_trinh("QT2")
        self.b = self.tao_nhap(quy_trinh=self.qt2.pk).data["id"]

    def ids(self, **tham_so):
        r = self.c.get(f"{BASE}/", {"hop": "toi_gui", **tham_so})
        self.assertEqual(r.status_code, 200, r.data)
        return {h["id"] for h in r.data["results"]}

    def test_filters(self):
        self.assertEqual(self.ids(), {self.a, self.b})
        self.assertEqual(self.ids(trang_thai="NHAP"), {self.a, self.b})
        self.assertEqual(self.ids(quy_trinh=self.qt2.pk), {self.b})
        self.assertEqual(self.ids(q="10/qd"), {self.a})  # số hiệu văn bản (Nhóm 2), không phân biệt hoa
        self.assertEqual(self.ids(q="/QD"), {self.a, self.b})
        self.assertEqual(self.ids(q="Gấp"), {self.a})  # ghi chú
        self.assertEqual(self.ids(q=f"#{self.b}"), {self.b})  # mã hồ sơ
        self.assertEqual(self.ids(q="khong-co"), set())
        SigningRequest.objects.filter(pk=self.a).update(created_at="2026-01-05T08:00:00Z")
        self.assertEqual(self.ids(tu_ngay="2026-01-01", den_ngay="2026-01-31"), {self.a})
        self.assertNotIn(self.a, self.ids(tu_ngay="2026-02-01"))

    def test_invalid_parameters(self):
        for tham_so in ({"tu_ngay": "05/01/2026"}, {"quy_trinh": "abc"}):
            r = self.c.get(f"{BASE}/", {"hop": "toi_gui", **tham_so})
            self.assertEqual((r.status_code, r.data["code"]), (400, "tham_so_khong_hop_le"))

    def test_khoang_ngay_sai_thu_tu_tra_400(self):
        """Từ ngày > Đến ngày: 400 kèm thông báo tiếng Việt (không trả danh sách rỗng); cùng ngày vẫn hợp lệ."""
        sai = {"tu_ngay": "2026-10-10", "den_ngay": "2026-10-01"}
        for duong_dan, tham_so in ((f"{BASE}/", {"hop": "toi_gui"}), ("/api/v1/signing/tai-lieu/", {})):
            r = self.c.get(duong_dan, {**tham_so, **sai})
            self.assertEqual((r.status_code, r.data["code"]), (400, "tham_so_khong_hop_le"), duong_dan)
            self.assertEqual(r.data["detail"], "Từ ngày không được lớn hơn Đến ngày.")
            self.assertIn("tu_ngay", r.data["fields"])
            r = self.c.get(duong_dan, {**tham_so, "tu_ngay": "2026-10-10", "den_ngay": "2026-10-10"})
            self.assertEqual(r.status_code, 200, duong_dan)


class SuaXoaQuyTrinhTests(TrinhKyBase):
    def setUp(self):
        super().setUp()
        self.ql = User.objects.create_user("quan_ly_qt")
        cap_quyen(self.ql, "manage_signing_process", "view_trinhky")
        self.cql = self.client_cua(User.objects.get(pk=self.ql.pk))
        r = self.cql.post(f"{QT}/", {"ma_quy_trinh": "NHAP1", "ten_quy_trinh": "Nháp", "pham_vi": "CONG_TY",
                                     "cap_ky": [{"cap_ky": 1, "ten_cap_ky": "C1", "thu_tu": 1,
                                                 "nguoi_ky": [{"nguoi_ky": self.ky1.pk, "thu_tu": 1}]}]}, format="json")
        self.nhap = r.data["id"]

    def test_edit_draft_replaces_levels_and_keeps_code(self):
        r = self.cql.put(f"{QT}/{self.nhap}/", {
            "ma_quy_trinh": "DOI-MA", "ten_quy_trinh": "Nháp đã sửa", "pham_vi": "CONG_TY", "cap_ky": [
                {"cap_ky": 1, "ten_cap_ky": "Kiểm tra", "thu_tu": 1, "nguoi_ky": [{"nguoi_ky": self.ky2.pk, "thu_tu": 1}]},
                {"cap_ky": 2, "ten_cap_ky": "Duyệt", "thu_tu": 2, "nguoi_ky": [{"nguoi_ky": self.ky3.pk, "thu_tu": 1}]},
            ]}, format="json")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual((r.data["ma_quy_trinh"], r.data["ten_quy_trinh"]), ("NHAP1", "Nháp đã sửa"))
        self.assertEqual([c["ten_cap_ky"] for c in r.data["cap_ky"]], ["Kiểm tra", "Duyệt"])
        self.assertEqual(r.data["cap_ky"][0]["nguoi_ky"][0]["nguoi_ky"], self.ky2.pk)

    def test_active_process_cannot_be_edited_but_deletes_when_unused(self):
        r = self.cql.put(f"{QT}/{self.process.pk}/", {"ten_quy_trinh": "x", "pham_vi": "CONG_TY", "cap_ky": []},
                         format="json")
        self.assertEqual((r.status_code, r.data["code"]), (409, "quy_trinh_khong_the_sua"))
        self.assertEqual(self.cql.get(f"{QT}/{self.process.pk}/").data["so_ho_so"], 0)
        self.assertEqual(self.cql.delete(f"{QT}/{self.process.pk}/").status_code, 204)  # đang hoạt động, chưa dùng
        self.assertFalse(SigningProcess.objects.filter(pk=self.process.pk).exists())

    def test_process_with_requests_in_any_state_cannot_be_deleted(self):
        """Quy trình 1 tạo ra hồ sơ A: còn hồ sơ phụ thuộc (kể cả đã hủy) thì không xóa được, báo số hồ sơ."""
        huy = self.tao_nhap().data["id"]
        r = self.c.post(f"{BASE}/{huy}/huy/", {}, format="json", HTTP_IDEMPOTENCY_KEY="huy-qt")
        self.assertEqual(r.status_code, 200, r.data)
        self.tao_nhap()  # hồ sơ nháp thứ hai
        r = self.cql.delete(f"{QT}/{self.process.pk}/")
        self.assertEqual((r.status_code, r.data["code"]), (409, "quy_trinh_da_duoc_dung"))
        self.assertIn("2 hồ sơ", r.data["detail"])
        self.assertEqual(r.data["fields"]["so_ho_so"], [2])
        self.assertEqual(self.cql.get(f"{QT}/{self.process.pk}/").data["so_ho_so"], 2)
        self.assertTrue(SigningProcess.objects.filter(pk=self.process.pk).exists())
        # Phiên bản mới cùng mã chưa có hồ sơ nào thì xóa được; hồ sơ chỉ chặn đúng phiên bản nó dùng
        moi = self.cql.post(f"{QT}/{self.process.pk}/nhan-ban/").data["id"]
        self.assertEqual(self.cql.delete(f"{QT}/{moi}/").status_code, 204)

    def test_delete_draft_and_permissions(self):
        self.assertEqual(self.client_cua(self.la).delete(f"{QT}/{self.nhap}/").status_code, 403)
        self.assertEqual(self.cql.delete(f"{QT}/{self.nhap}/").status_code, 204)
        self.assertFalse(SigningProcess.objects.filter(pk=self.nhap).exists())
        self.assertEqual(self.cql.delete(f"{QT}/{self.nhap}/").status_code, 404)


class TaiLieuTests(TrinhKyBase):
    def test_download_file_of_each_attempt(self):
        data = self.ho_so_da_gui()
        luot = data["luot_trinh"][0]["id"]
        r = self.c.get(f"{BASE}/{data['id']}/tep/", {"luot": luot})
        self.assertEqual(r.status_code, 200)
        self.assertIn(f"trinh-ky-{data['id']}-luot-1.pdf", r["Content-Disposition"])
        self.assertTrue(r.content.startswith(b"%PDF-"))
        self.assertEqual(self.c.get(f"{BASE}/{data['id']}/tep/", {"luot": 999999}).status_code, 404)
        r = self.c.get(f"{BASE}/{data['id']}/tep/", {"luot": "abc"})
        self.assertEqual((r.status_code, r.data["code"]), (400, "tham_so_khong_hop_le"))
        khac = self.tao_nhap().data["id"]  # lượt của hồ sơ khác không tải được qua hồ sơ này
        self.assertEqual(self.c.get(f"{BASE}/{khac}/tep/", {"luot": luot}).status_code, 404)


class LocNhanhTests(KyBase):
    """Bộ lọc trạng thái và số lượng (#275 mục 5): đang chờ ký, quá hạn, đã ký xong, trả lại để sửa."""

    def test_quick_filters_and_counts(self):
        from django.utils import timezone
        from datetime import timedelta
        cho = self.pk  # hồ sơ đã gửi ở setUp, đang chờ ký
        nhap = self.tao_nhap().data["id"]
        tra = self.ho_so_da_gui()["id"]
        self.pk = tra
        self.assertEqual(self.hanh_dong(self.ky1, "yeu-cau-sua", tieu_de="Sửa", ly_do="Sai").status_code, 200)
        tre = self.ho_so_da_gui()["id"]
        SigningRequest.objects.filter(pk=tre).update(han_chot=timezone.now() - timedelta(hours=1))

        def ids(nhanh):
            r = self.c.get(f"{BASE}/", {"hop": "toi_gui", "nhanh": nhanh})
            self.assertEqual(r.status_code, 200, r.data)
            return {h["id"] for h in r.data["results"]}
        self.assertEqual(ids("cho_ky"), {cho})  # quá hạn tách riêng khỏi đang chờ ký
        self.assertEqual(ids("qua_han"), {tre})
        self.assertEqual(ids("tra_lai"), {tra})
        self.assertEqual(ids("hoan_thanh"), set())
        r = self.c.get(f"{BASE}/", {"hop": "toi_gui"})
        self.assertEqual({h["id"] for h in r.data["results"]}, {cho, nhap, tra, tre})  # nháp vẫn hiện ở "Tất cả"
        # Cấp đang ký quá hạn xử lý (hạn chót hồ sơ chưa qua) cũng là quá hạn
        from signing.models import SigningRequestStep
        SigningRequestStep.objects.filter(luot_trinh__trinh_ky_id=cho, trang_thai=enums.TrangThaiCapKy.DANG_KY).update(
            han_xu_ly=timezone.now() - timedelta(minutes=5))
        self.assertEqual(ids("cho_ky"), set())
        self.assertEqual(ids("qua_han"), {cho, tre})
        dem = self.c.get(f"{BASE}/thong-ke/", {"hop": "toi_gui"}).data
        self.assertEqual(dem, {"tat_ca": 4, "cho_ky": 0, "qua_han": 2, "hoan_thanh": 0, "tra_lai": 1})
        for sai in ("sai", "nhap", "tu_choi", "huy"):
            r = self.c.get(f"{BASE}/", {"hop": "toi_gui", "nhanh": sai})
            self.assertEqual((r.status_code, r.data["code"]), (400, "tham_so_khong_hop_le"))

    def test_completed_filter(self):
        for cap in (self.ky1, self.ky2, self.ky3):
            self.assertEqual(self.ky(cap).status_code, 200)
        r = self.c.get(f"{BASE}/", {"hop": "toi_gui", "nhanh": "hoan_thanh"})
        self.assertEqual([h["id"] for h in r.data["results"]], [self.pk])

    def test_document_page_lists_files_of_visible_requests(self):
        da_gui = self.ho_so_da_gui()["id"]
        nhap = self.tao_nhap().data["id"]
        r = self.c.get("/api/v1/signing/tai-lieu/")
        self.assertEqual(r.status_code, 200)
        theo_ho_so = {(x["trinh_ky"], x["loai"]) for x in r.data["results"]}
        self.assertIn((da_gui, "LUOT"), theo_ho_so)
        self.assertIn((nhap, "DU_THAO"), theo_ho_so)
        luot = next(x for x in r.data["results"] if x["trinh_ky"] == da_gui)
        self.assertEqual((luot["so_luot"], luot["ten_tep"]), (1, f"trinh-ky-{da_gui}-luot-1.pdf"))
        loai = {x["loai"] for x in self.c.get("/api/v1/signing/tai-lieu/", {"loai": "DU_THAO"}).data["results"]}
        self.assertEqual(loai, {"DU_THAO"})
        self.assertEqual(self.c.get("/api/v1/signing/tai-lieu/", {"q": f"#{nhap}"}).data["results"][0]["trinh_ky"], nhap)
        khac = self.client_cua(self.la).get("/api/v1/signing/tai-lieu/").data
        self.assertEqual((khac["count"], khac["results"]), (0, []))  # không liên quan: không thấy

    def test_document_page_is_paginated_like_request_list(self):
        for _ in range(11):
            self.tao_nhap()
        tong = self.c.get("/api/v1/signing/tai-lieu/").data["count"]
        self.assertGreaterEqual(tong, 12)
        trang_1 = self.c.get("/api/v1/signing/tai-lieu/").data
        self.assertEqual(len(trang_1["results"]), 10)  # mặc định 10 tệp mỗi trang
        self.assertIsNotNone(trang_1["next"])
        trang_2 = self.c.get("/api/v1/signing/tai-lieu/", {"page": 2}).data
        self.assertEqual(len(trang_2["results"]), tong - 10)
        cap_1 = {(x["trinh_ky"], x["loai"], x["luot"]) for x in trang_1["results"]}
        cap_2 = {(x["trinh_ky"], x["loai"], x["luot"]) for x in trang_2["results"]}
        self.assertFalse(cap_1 & cap_2)
        self.assertEqual(len(self.c.get("/api/v1/signing/tai-lieu/", {"page_size": 5}).data["results"]), 5)
        r = self.c.get("/api/v1/signing/tai-lieu/", {"loai": "SAI"})
        self.assertEqual((r.status_code, r.data["code"]), (400, "tham_so_khong_hop_le"))

