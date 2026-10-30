"""
Lỗi tìm được khi kiểm thử 8 chức năng Nhóm 5 trên staging: cấu hình email (DEFAULT_FROM_EMAIL, SIGNING_EMAIL_BACKEND
SMTP trên Django 6.1), một văn bản một hồ sơ đang mở, phân trang danh sách, tìm không dấu, hạn xử lý trong thông báo.
"""

from datetime import timedelta

from django.core import mail
from django.core.mail.backends.smtp import EmailBackend as SmtpBackend
from django.test import override_settings
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from documents.models import VanBanDi

from signing import checks, enums
from signing.models import SigningNotification, SigningRequest, SigningRequestStep
from signing.services import thong_bao
from signing.tim_kiem import bo_dau

from .test_hanh_dong_ky_phase8 import KyBase
from .test_trinh_ky_phase7 import BASE, TrinhKyBase

SMTP = "django.core.mail.backends.smtp.EmailBackend"
CONSOLE = "django.core.mail.backends.console.EmailBackend"
LOCMEM = "django.core.mail.backends.locmem.EmailBackend"
MAILERS_SMTP = {"default": {"BACKEND": SMTP, "OPTIONS": {"host": "smtp.example.invalid", "port": 587}}}
MAILERS_CONSOLE = {"default": {"BACKEND": CONSOLE}}


def ma_check(**cai_dat):
    with override_settings(**cai_dat):
        return [c.id for c in checks.kiem_tra_cau_hinh_email(None)]


class CauHinhEmailTests(KyBase):
    def test_check_warns_smtp_without_from_address(self):
        self.assertEqual(ma_check(MAILERS=MAILERS_SMTP, DEFAULT_FROM_EMAIL="", SIGNING_EMAIL_BACKEND=""),
                         ["signing.W003"])
        self.assertEqual(ma_check(MAILERS=MAILERS_SMTP, DEFAULT_FROM_EMAIL="Hệ thống QLVB <qlvb@example.vn>",
                                  SIGNING_EMAIL_BACKEND=""), [])
        # Không gửi SMTP (console, locmem) thì địa chỉ trống không gây lỗi
        self.assertEqual(ma_check(MAILERS=MAILERS_CONSOLE, DEFAULT_FROM_EMAIL="", SIGNING_EMAIL_BACKEND=""), [])
        self.assertEqual(ma_check(MAILERS=MAILERS_SMTP, DEFAULT_FROM_EMAIL="", SIGNING_EMAIL_BACKEND=CONSOLE), [])

    def test_check_signing_backend_value(self):
        self.assertEqual(ma_check(MAILERS=MAILERS_CONSOLE, DEFAULT_FROM_EMAIL="a@b.vn", SIGNING_EMAIL_BACKEND=SMTP),
                         ["signing.W002"])
        self.assertEqual(ma_check(MAILERS=MAILERS_SMTP, DEFAULT_FROM_EMAIL="a@b.vn", SIGNING_EMAIL_BACKEND=SMTP), [])
        self.assertEqual(ma_check(SIGNING_EMAIL_BACKEND="khong.ton.tai.Backend"), ["signing.E004"])

    def test_smtp_signing_backend_uses_project_mailer(self):
        # Django 6.1: tạo SMTP backend trực tiếp khi đã có MAILERS bị chặn (đọc EMAIL_HOST); dùng mailer mặc định
        with override_settings(SIGNING_EMAIL_BACKEND=SMTP, MAILERS=MAILERS_SMTP):
            ket_noi = thong_bao.ket_noi_email()
        self.assertIsInstance(ket_noi, SmtpBackend)
        self.assertEqual(ket_noi.host, "smtp.example.invalid")

    def test_smtp_signing_backend_sends_through_default_mailer(self):
        User = type(self.ky1)
        User.objects.filter(pk=self.ky1.pk).update(email="ky1@demo.local")
        mail.outbox.clear()
        with override_settings(SIGNING_EMAIL_BACKEND=SMTP, MAILERS={"default": {"BACKEND": LOCMEM}},
                               DEFAULT_FROM_EMAIL="Hệ thống QLVB <qlvb@demo.local>"), \
                self.captureOnCommitCallbacks(execute=True):
            pk = self.tao_nhap().data["id"]
            self.assertEqual(self.gui(pk, khoa=f"gui-{pk}").status_code, 200)
        email = SigningNotification.objects.get(trinh_ky_id=pk, nguoi_nhan=self.ky1, kenh=enums.KenhThongBao.EMAIL)
        self.assertEqual((email.trang_thai, email.loi_gui), (enums.TrangThaiThongBao.DA_GUI, ""))
        self.assertEqual([(m.from_email, m.to) for m in mail.outbox],
                         [("Hệ thống QLVB <qlvb@demo.local>", ["ky1@demo.local"])])


class HanXuLyThongBaoTests(KyBase):
    def test_need_to_sign_email_and_api_show_deadline(self):
        User = type(self.ky3)
        User.objects.filter(pk=self.ky3.pk).update(email="gd@demo.local")
        self.assertEqual(self.ky(self.ky1).status_code, 200)
        mail.outbox.clear()
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.ky(self.ky2).status_code, 200)  # mở cấp 2 (24 giờ xử lý)
        han = SigningRequestStep.objects.get(luot_trinh__trinh_ky_id=self.pk, thu_tu=2).han_xu_ly
        chuoi = f"Hạn xử lý: {timezone.localtime(han):%d/%m/%Y %H:%M}."
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(chuoi, mail.outbox[0].body)
        r = self.client_cua(User.objects.get(pk=self.ky3.pk)).get("/api/v1/signing/thong-bao/")
        tb = next(x for x in r.data["results"] if x["loai_thong_bao"] == "CAN_KY")
        self.assertEqual(parse_datetime(tb["han_xu_ly"]), han)  # cùng thời điểm, chuỗi giờ +07:00

    def test_reminder_and_overdue_show_deadline(self):
        cap = SigningRequestStep.objects.get(luot_trinh__trinh_ky_id=self.pk, thu_tu=1)
        SigningRequestStep.objects.filter(pk=cap.pk).update(han_xu_ly=timezone.now() + timedelta(hours=2))
        thong_bao.nhac_han()
        tb = SigningNotification.objects.get(trinh_ky_id=self.pk, loai_thong_bao="NHAC_HAN",
                                             kenh=enums.KenhThongBao.IN_APP)
        han = SigningRequestStep.objects.get(pk=cap.pk).han_xu_ly
        self.assertIn(f"Hạn xử lý: {timezone.localtime(han):%d/%m/%Y %H:%M}.", thong_bao.noi_dung(tb)[1])
        # Thông báo không gắn hạn (hoàn tất, hủy...) không ghi dòng hạn
        self.assertIsNone(thong_bao.han_xu_ly(SigningNotification(loai_thong_bao="HUY", buoc_ky=tb.buoc_ky)))


class MotHoSoDangMoTests(KyBase):
    """setUp của KyBase đã gửi một hồ sơ cho văn bản 10 (đang chờ ký)."""

    def test_cannot_create_or_send_while_request_open(self):
        r = self.tao_nhap(van_ban_id=10)
        self.assertEqual((r.status_code, r.data["code"]), (409, "van_ban_da_co_ho_so_dang_mo"))
        self.assertIn(f"#{self.pk}", r.data["detail"])
        self.assertEqual(SigningRequest.objects.filter(van_ban_id=10).count(), 1)
        # Nháp tạo trước khi có quy tắc (dữ liệu cũ): không gửi được khi văn bản đang có hồ sơ chờ ký
        cu = SigningRequest.objects.get(pk=self.pk)
        nhap = SigningRequest.objects.create(
            document_type=cu.document_type, van_ban_id=10, quy_trinh=cu.quy_trinh,
            phien_ban_quy_trinh=cu.phien_ban_quy_trinh, phien_ban_van_ban="1", vi_tri_luu_tep=cu.vi_tri_luu_tep,
            ma_bam_tai_lieu=cu.ma_bam_tai_lieu, create_by=self.tao)
        r = self.gui(nhap.pk, khoa="gui-nhap-cu")
        self.assertEqual((r.status_code, r.data["code"]), (409, "van_ban_da_co_ho_so_dang_mo"))
        self.assertEqual(SigningRequest.objects.get(pk=nhap.pk).trang_thai, "NHAP")

    def test_draft_also_blocks_new_request(self):
        nhap = self.tao_nhap(van_ban_id=20).data["id"]
        r = self.tao_nhap(van_ban_id=20)
        self.assertEqual((r.status_code, r.data["code"]), (409, "van_ban_da_co_ho_so_dang_mo"))
        self.assertEqual(self.gui(nhap, khoa="gui-nhap-20").status_code, 200)  # chính nháp đó vẫn gửi được

    def test_cancelled_allows_retry_but_completed_blocks_reuse(self):
        r = self.c.post(f"{BASE}/{self.pk}/huy/", {"ly_do": "Đổi phương án"}, format="json",
                        HTTP_IDEMPOTENCY_KEY="huy-10")
        self.assertEqual(r.status_code, 200, r.data)
        moi = self.tao_nhap(van_ban_id=10)
        self.assertEqual(moi.status_code, 201, moi.data)  # hồ sơ cũ đã hủy
        self.pk = moi.data["id"]
        self.assertEqual(self.gui(self.pk, khoa="gui-10-lan-2").status_code, 200)
        for user in (self.ky1, self.ky2, self.ky3):
            self.assertEqual(self.ky(user).status_code, 200)
        self.assertEqual(SigningRequest.objects.get(pk=self.pk).trang_thai, "HOAN_THANH")
        r = self.tao_nhap(van_ban_id=10)
        self.assertEqual((r.status_code, r.data["code"]), (409, "van_ban_da_co_ho_so_hoan_tat"))

    def test_legacy_draft_cannot_be_sent_after_another_request_completes(self):
        cu = SigningRequest.objects.get(pk=self.pk)
        nhap_cu = SigningRequest.objects.create(
            document_type=cu.document_type, van_ban_id=cu.van_ban_id, quy_trinh=cu.quy_trinh,
            phien_ban_quy_trinh=cu.phien_ban_quy_trinh, phien_ban_van_ban="1", vi_tri_luu_tep=cu.vi_tri_luu_tep,
            ma_bam_tai_lieu=cu.ma_bam_tai_lieu, create_by=self.tao,
        )
        for user in (self.ky1, self.ky2, self.ky3):
            self.assertEqual(self.ky(user).status_code, 200)

        r = self.gui(nhap_cu.pk, khoa="gui-nhap-sau-hoan-tat")
        self.assertEqual((r.status_code, r.data["code"]), (409, "van_ban_da_co_ho_so_hoan_tat"))
        self.assertEqual(SigningRequest.objects.get(pk=nhap_cu.pk).trang_thai, "NHAP")

    def test_resubmit_after_rejection_is_blocked_only_by_another_open_request(self):
        self.assertEqual(self.hanh_dong(self.ky1, "tu-choi", ly_do_tu_choi="Chưa đạt").status_code, 200)
        khac = self.tao_nhap(van_ban_id=10)  # hồ sơ bị từ chối đã kết thúc: tạo được hồ sơ mới
        self.assertEqual(khac.status_code, 201, khac.data)
        r = self.hanh_dong(self.tao, "trinh-lai", khoa_thao_tac="trinh-lai-1")
        self.assertEqual((r.status_code, r.data["code"]), (409, "van_ban_da_co_ho_so_dang_mo"))
        r = self.c.post(f"{BASE}/{khac.data['id']}/huy/", {}, format="json", HTTP_IDEMPOTENCY_KEY="huy-khac")
        self.assertEqual(r.status_code, 200, r.data)
        r = self.hanh_dong(self.tao, "trinh-lai", khoa_thao_tac="trinh-lai-2")
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(SigningRequest.objects.filter(ho_so_goc_id=self.pk, trang_thai="NHAP").count(), 1)


class PhanTrangVaTimKiemTests(TrinhKyBase):
    def setUp(self):
        super().setUp()
        VanBanDi.objects.create(id=10, so_hieu="10/QĐ", trich_yeu="Mua sắm thiết bị", nguoi_tao=self.tao)
        self.ids = [self.tao_nhap(ghi_chu="Hồ sơ gấp" if i == 0 else "").data["id"] for i in range(12)]

    def danh_sach(self, **tham_so):
        r = self.c.get(f"{BASE}/", {"hop": "toi_gui", **tham_so})
        self.assertEqual(r.status_code, 200, r.data)
        return r.data

    def test_list_is_paginated_like_other_modules(self):
        trang_1 = self.danh_sach()
        self.assertEqual((trang_1["count"], len(trang_1["results"])), (12, 10))
        self.assertIsNone(trang_1["previous"])
        self.assertIn("page=2", trang_1["next"])
        trang_2 = self.danh_sach(page=2)
        self.assertEqual(len(trang_2["results"]), 2)
        self.assertIsNone(trang_2["next"])
        tat_ca = [h["id"] for h in trang_1["results"] + trang_2["results"]]
        self.assertEqual(tat_ca, sorted(self.ids, reverse=True))  # mới nhất trước, không trùng, không sót
        self.assertEqual(len(self.danh_sach(page_size=5)["results"]), 5)
        self.assertEqual(len(self.danh_sach(page_size=500)["results"]), 12)  # tối đa 100 mỗi trang
        self.assertEqual(self.c.get(f"{BASE}/", {"hop": "toi_gui", "page": 9}).status_code, 404)

    def ids_tim(self, q):
        return {h["id"] for h in self.danh_sach(q=q, page_size=100)["results"]}

    def test_search_ignores_vietnamese_diacritics_and_case(self):
        dau = self.ids[0]  # văn bản 10 thuộc hồ sơ đầu tiên
        self.assertEqual(self.ids_tim("mua sam"), {dau})  # trích yếu văn bản
        self.assertEqual(self.ids_tim("10/qd"), {dau})  # số hiệu có chữ Đ
        self.assertEqual(self.ids_tim("MUA SẮM"), {dau})
        self.assertEqual(self.ids_tim("ho so gap"), {dau})  # ghi chú
        self.assertEqual(self.ids_tim("duyet to trinh"), set(self.ids))  # tên quy trình "Duyệt tờ trình"
        self.assertEqual(self.ids_tim("khong co"), set())

    def test_document_lookup_ignores_diacritics(self):
        r = self.c.get("/api/v1/signing/van-ban-di/", {"q": "thiet bi"})
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual([v["id"] for v in r.data], [10])

    def test_bo_dau(self):
        self.assertEqual(bo_dau("Đề Xuất ỨNG DỤNG Ỷ Ỹ"), "de xuat ung dung y y")


class RaSoatGiaoDienTests(TrinhKyBase):
    """Bổ sung sau rà soát giao diện: hạn cấp hiện hành, thông điệp lỗi, email tin nhắn trao đổi."""

    def test_validation_error_has_detail_and_pagination_404_has_stable_code(self):
        r = self.c.post(f"{BASE}/", {"document_type": "vanbandi"}, format="multipart")
        self.assertEqual((r.status_code, r.data["code"]), (400, "du_lieu_khong_hop_le"))
        self.assertTrue(r.data["detail"])
        r = self.c.get(f"{BASE}/", {"hop": "tat_ca", "page": 999})
        self.assertEqual((r.status_code, r.data["code"]), (404, "khong_tim_thay"))

    def test_notifications_use_local_timezone(self):
        self.ho_so_da_gui()
        r = self.client_cua(self.ky1).get("/api/v1/signing/thong-bao/")
        self.assertTrue(r.data["results"])
        self.assertTrue(all(x["created_at"].endswith("+07:00") for x in r.data["results"]))
