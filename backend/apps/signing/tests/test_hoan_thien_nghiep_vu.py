"""
Hoàn thiện nghiệp vụ Nhóm 5: ủy quyền ký khẩn cấp, thông báo khi hủy (kể cả hủy thay), tin nhắn trao đổi,
nhắc hạn/quá hạn, tên người thực hiện trong lịch sử, tìm người nhận ủy quyền.
"""

import io
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APIClient

from authorization.models import GroupInfo
from signing import enums
from signing.models import SigningAuditLog, SigningNotification, SigningRequestStep, SigningRequestStepSigner
from signing.services import thong_bao

from .helpers import cap_quyen, tao_don_vi
from .test_hanh_dong_ky_phase8 import KyBase, khoa_hoat_dong
from .test_trinh_ky_phase7 import BASE

User = get_user_model()


def vao_nhom(user, ma):
    info = GroupInfo.objects.filter(ma_nhom_quyen=ma).first()
    if info is None:
        group = Group.objects.create(name=f"Nhom {ma} (test)")
        GroupInfo.objects.filter(pk=group.pk).update(ma_nhom_quyen=ma)
    else:
        group = Group.objects.get(pk=info.pk)
    user.groups.add(group)


def thong_bao_cua(user, loai):
    return SigningNotification.objects.filter(nguoi_nhan=user, loai_thong_bao=loai, kenh=enums.KenhThongBao.IN_APP)


class UyQuyenTests(KyBase):
    def setUp(self):
        super().setUp()
        self.quan_tri = User.objects.create_user("quan_tri_uq")
        cap_quyen(self.quan_tri, "delegate_trinhky", "view_signing_audit")
        vao_nhom(self.quan_tri, "ADMIN")
        self.nhan = User.objects.create_user("pho_phong")
        cap_quyen(self.nhan, "sign_trinhky")
        self.dong_ky1 = SigningRequestStepSigner.objects.get(buoc_ky__luot_trinh__trinh_ky=self.pk, nguoi_ky=self.ky1)

    def uy_quyen(self, user, dong=None, nguoi_nhan=None, ly_do="Đi công tác", khoa="uq-1"):
        return self.client_cua(user).post(
            f"{BASE}/{self.pk}/uy-quyen/",
            {"dong_nguoi_ky": (dong or self.dong_ky1).pk, "nguoi_nhan": (nguoi_nhan or self.nhan).pk,
             "ly_do_uy_quyen": ly_do},
            format="json", HTTP_IDEMPOTENCY_KEY=khoa)

    def test_admin_delegates_open_signer_and_recipient_signs(self):
        r = self.uy_quyen(self.quan_tri)
        self.assertEqual(r.status_code, 200, r.data)
        _, dong = self.nguoi_ky(r.data, "pho_phong")
        self.assertEqual((dong["uy_quyen_tu"], dong["ten_nguoi_uy_quyen"], dong["ly_do_uy_quyen"]),
                         (self.ky1.pk, "ke_toan", "Đi công tác"))
        self.assertIsNotNone(dong["thoi_diem_mo"])  # dòng đã mở: người nhận ký được ngay
        self.assertEqual(r.data["lich_su"][-1]["hanh_dong"], "UY_QUYEN_KY")
        self.assertEqual(r.data["lich_su"][-1]["ten_nguoi_thuc_hien"], "quan_tri_uq")
        # Người nhận và người giao nhận thông báo; người giao vẫn xem được hồ sơ
        self.assertTrue(thong_bao_cua(self.nhan, "UY_QUYEN").exists())
        self.assertTrue(thong_bao_cua(self.ky1, "UY_QUYEN").exists())
        self.assertEqual(self.client_cua(self.ky1).get(f"{BASE}/{self.pk}/").status_code, 200)
        # Người cũ không còn lượt ký; người nhận ký bằng khóa của mình
        self.assertEqual(self.ky(self.ky1).status_code, 403)
        self.khoa[self.nhan.pk] = khoa_hoat_dong(self.nhan, "K-pho-phong")
        r = self.ky(self.nhan)
        self.assertEqual(r.status_code, 200, r.data)
        _, dong = self.nguoi_ky(r.data, "pho_phong")
        self.assertEqual(dong["trang_thai"], "DA_KY")

    def test_repeat_with_same_key_is_idempotent(self):
        self.assertEqual(self.uy_quyen(self.quan_tri).status_code, 200)
        self.assertEqual(self.uy_quyen(self.quan_tri).status_code, 200)
        self.assertEqual(SigningAuditLog.objects.filter(hanh_dong="UY_QUYEN_KY").count(), 1)

    def test_unit_leader_only_for_same_unit(self):
        don_vi, don_vi_khac = tao_don_vi(), tao_don_vi()
        User.objects.filter(pk=self.ky3.pk).update(don_vi=don_vi)
        truong_phong = User.objects.create_user("truong_phong_uq", don_vi=don_vi_khac)
        cap_quyen(truong_phong, "delegate_trinhky", "view_signing_audit")
        vao_nhom(truong_phong, "TP")
        dong_ky3 = SigningRequestStepSigner.objects.get(buoc_ky__luot_trinh__trinh_ky=self.pk, nguoi_ky=self.ky3)
        r = self.uy_quyen(truong_phong, dong=dong_ky3)  # khác đơn vị người ký
        self.assertEqual((r.status_code, r.data["code"]), (403, "khong_co_quyen"))
        User.objects.filter(pk=truong_phong.pk).update(don_vi=don_vi)
        r = self.uy_quyen(User.objects.get(pk=truong_phong.pk), dong=dong_ky3, khoa="uq-2")  # cấp chưa mở
        self.assertEqual(r.status_code, 200, r.data)

    def test_rejections(self):
        self.assertEqual(self.uy_quyen(self.quan_tri, ly_do="  ").status_code, 400)
        r = self.uy_quyen(self.quan_tri, nguoi_nhan=self.ky2, khoa="uq-a")  # đã có trong cấp
        self.assertEqual((r.status_code, r.data["code"]), (409, "nguoi_nhan_da_co_trong_cap"))
        r = self.uy_quyen(self.quan_tri, nguoi_nhan=self.la, khoa="uq-b")  # không có quyền ký
        self.assertEqual(r.data["code"], "nguoi_nhan_khong_hop_le")
        # Người ký có delegate_trinhky không tự ủy quyền dòng của mình
        cap_quyen(self.ky1, "delegate_trinhky")
        vao_nhom(self.ky1, "ADMIN")
        r = self.uy_quyen(User.objects.get(pk=self.ky1.pk), khoa="uq-c")
        self.assertEqual((r.status_code, r.data["code"]), (403, "khong_co_quyen"))
        # Không có delegate_trinhky
        r = self.uy_quyen(self.tao, khoa="uq-d")
        self.assertEqual(r.status_code, 403)
        # Đã ký thì không ủy quyền
        self.ky(self.ky1)
        r = self.uy_quyen(self.quan_tri, khoa="uq-e")
        self.assertEqual((r.status_code, r.data["code"]), (409, "nguoi_ky_khong_cho_ky"))

    def test_search_recipients_requires_delegate_and_sign_permission(self):
        r = self.client_cua(self.tao).get("/api/v1/signing/nguoi-dung/?muc_dich=uy_quyen")
        self.assertEqual(r.status_code, 403)
        r = self.client_cua(self.quan_tri).get("/api/v1/signing/nguoi-dung/?muc_dich=uy_quyen&q=pho")
        self.assertEqual([u["ten_dang_nhap"] for u in r.data], ["pho_phong"])
        r = self.client_cua(self.quan_tri).get("/api/v1/signing/nguoi-dung/?muc_dich=uy_quyen&q=nguoi_ngoai")
        self.assertEqual(r.data, [])


class ThongBaoHoanThienTests(KyBase):
    def test_creator_cancel_notifies_opened_and_signed_signers(self):
        self.ky(self.ky1)  # ký nháy xong, ký chính được mở
        r = self.hanh_dong(self.tao, "huy", ly_do="Đổi nội dung")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertTrue(thong_bao_cua(self.ky1, "HUY").exists())  # đã ký
        self.assertTrue(thong_bao_cua(self.ky2, "HUY").exists())  # đang chờ
        self.assertFalse(thong_bao_cua(self.ky3, "HUY").exists())  # cấp chưa mở
        self.assertFalse(thong_bao_cua(self.tao, "HUY").exists())  # người tự hủy

    def test_admin_cancel_on_behalf_notifies_creator(self):
        quan_tri = User.objects.create_user("quan_tri_huy")
        cap_quyen(quan_tri, "cancel_trinhky", "view_signing_audit")
        r = self.hanh_dong(quan_tri, "huy", ly_do="Sai quy trình")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertTrue(thong_bao_cua(self.tao, "HUY").exists())
        self.assertEqual(r.data["lich_su"][-1]["ten_nguoi_thuc_hien"], "quan_tri_huy")

    def test_change_thread_message_notifies_other_side(self):
        self.hanh_dong(self.ky1, "yeu-cau-sua", tieu_de="Sai số", ly_do="Mục 2")
        r = self.client_cua(self.tao).post(f"{BASE}/{self.pk}/trao-doi/", {"noi_dung": "Đã sửa"}, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        self.assertTrue(thong_bao_cua(self.ky1, "TIN_NHAN").exists())
        self.client_cua(self.ky1).post(f"{BASE}/{self.pk}/trao-doi/", {"noi_dung": "Đồng ý"}, format="json")
        tb = thong_bao_cua(self.tao, "TIN_NHAN").order_by("-pk").first()
        self.assertIsNotNone(tb)
        _, than, _ = thong_bao.noi_dung(tb)
        self.assertIn("Người gửi: ke_toan", than)
        self.assertIn("Nội dung: Đồng ý", than)
        r = self.client_cua(self.tao).get("/api/v1/signing/thong-bao/")
        self.assertEqual(r.data[0]["loai_thong_bao"], "TIN_NHAN")
        self.assertEqual((r.data[0]["nguoi_thao_tac"], r.data[0]["ly_do"]), ("ke_toan", "Đồng ý"))

    def test_deadline_reminders_are_idempotent(self):
        cap = SigningRequestStep.objects.get(luot_trinh__trinh_ky=self.pk, trang_thai=enums.TrangThaiCapKy.DANG_KY)
        cap.han_xu_ly = timezone.now() + timedelta(hours=3)
        cap.save(update_fields=["han_xu_ly"])
        self.assertEqual(thong_bao.nhac_han(), 1)  # người ký nháy đang mở
        self.assertEqual(thong_bao.nhac_han(), 0)
        self.assertTrue(thong_bao_cua(self.ky1, "NHAC_HAN").exists())
        cap.han_xu_ly = timezone.now() - timedelta(hours=1)
        cap.save(update_fields=["han_xu_ly"])
        call_command("nhac_han_trinh_ky", stdout=io.StringIO())
        self.assertTrue(thong_bao_cua(self.ky1, "QUA_HAN").exists())
        self.assertTrue(thong_bao_cua(self.tao, "QUA_HAN").exists())
        self.assertEqual(thong_bao.nhac_han(), 0)
        self.assertEqual(thong_bao.nhac_han(timezone.now() + timedelta(days=1)), 2)  # nhắc lặp ngày sau


class RaSoatStagingTests(KyBase):
    """Lỗi từ rà soát E2E staging: dọn trạng thái khi kết thúc, thứ tự lịch sử, 404 tiếng Việt, lý do trong thông báo."""

    def cap_dang_mo(self):
        return SigningRequestStep.objects.filter(luot_trinh__trinh_ky=self.pk, trang_thai=enums.TrangThaiCapKy.DANG_KY)

    def test_reject_and_cancel_stop_open_level(self):
        self.assertTrue(self.cap_dang_mo().exists())
        self.hanh_dong(self.ky1, "tu-choi", ly_do_tu_choi="Sai căn cứ")
        self.assertFalse(self.cap_dang_mo().exists())
        self.assertTrue(SigningRequestStep.objects.filter(luot_trinh__trinh_ky=self.pk,
                                                          trang_thai=enums.TrangThaiCapKy.TAM_DUNG).exists())
        self.pk = self.ho_so_da_gui()["id"]
        self.hanh_dong(self.tao, "huy", ly_do="Đổi phương án")
        self.assertFalse(self.cap_dang_mo().exists())
        r = self.client_cua(self.ky1).get(f"{BASE}/?hop=can_toi_ky")
        self.assertEqual(r.data["results"], [])

    def test_history_lists_submit_before_open_level(self):
        hanh_dong = [e["hanh_dong"] for e in self.client_cua(self.tao).get(f"{BASE}/{self.pk}/").data["lich_su"]]
        self.assertLess(hanh_dong.index("GUI_TRINH_KY"), hanh_dong.index("MO_CAP_KY"))

    def test_not_found_detail_is_vietnamese(self):
        r = self.client_cua(self.la).get(f"{BASE}/{self.pk}/")
        self.assertEqual((r.status_code, r.data["code"]), (404, "khong_tim_thay"))
        self.assertTrue(r.data["detail"].startswith("Không tìm thấy"))
        r = APIClient().get(f"{BASE}/")
        self.assertEqual(r.status_code, 401)
        self.assertTrue(r.data["detail"].startswith("Chưa đăng nhập"))

    def test_notification_and_email_carry_actor_and_reason(self):
        self.hanh_dong(self.ky1, "tu-choi", ly_do_tu_choi="Sai căn cứ pháp lý")
        tb = thong_bao_cua(self.tao, "TU_CHOI").get()
        _, than, _ = thong_bao.noi_dung(tb)
        self.assertIn("Người thực hiện: ke_toan", than)
        self.assertIn("Lý do: Sai căn cứ pháp lý", than)
        d = self.client_cua(self.tao).get("/api/v1/signing/thong-bao/").data[0]
        self.assertEqual((d["nguoi_thao_tac"], d["ly_do"]), ("ke_toan", "Sai căn cứ pháp lý"))

    def test_change_request_notification_reason(self):
        self.hanh_dong(self.ky1, "yeu-cau-sua", tieu_de="Sai số", ly_do="Mục 2 thiếu tổng")
        _, than, _ = thong_bao.noi_dung(thong_bao_cua(self.tao, "YEU_CAU_SUA").get())
        self.assertIn("Lý do: Sai số: Mục 2 thiếu tổng", than)

    def test_list_shows_returned_and_overdue(self):
        d = self.client_cua(self.tao).get(f"{BASE}/?hop=toi_gui").data["results"][0]
        self.assertEqual((d["trang_thai_luot"], d["qua_han"]), ("CHO_KY", False))
        SigningRequestStep.objects.filter(luot_trinh__trinh_ky=self.pk, trang_thai=enums.TrangThaiCapKy.DANG_KY) \
            .update(han_xu_ly=timezone.now() - timedelta(hours=1))
        d_tre = self.client_cua(self.tao).get(f"{BASE}/?hop=toi_gui").data["results"][0]
        self.assertTrue(d_tre["qua_han"])
        self.assertTrue(d_tre["qua_han_cap"])
        self.assertIsNotNone(d_tre["han_xu_ly_cap"])
        self.hanh_dong(self.ky1, "yeu-cau-sua", tieu_de="Sai số", ly_do="Mục 2")
        d = self.client_cua(self.tao).get(f"{BASE}/?hop=toi_gui").data["results"][0]
        self.assertEqual((d["trang_thai"], d["trang_thai_luot"]), ("CHO_KY", "YEU_CAU_SUA"))
