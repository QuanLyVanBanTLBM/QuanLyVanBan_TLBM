"""
Hoàn thiện nghiệp vụ Nhóm 5: thông báo khi hủy (kể cả hủy thay), tin nhắn trao đổi,
nhắc hạn/quá hạn, tên người thực hiện trong lịch sử.
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
from signing.models import (
    SigningNotification, SigningRequestStep, SigningRequestStepSigner,
    SigningSignature,
)
from signing.services import thong_bao

from .helpers import cap_quyen, tao_chuc_vu
from .test_hanh_dong_ky_phase8 import KyBase, khoa_hoat_dong
from .test_trinh_ky_phase7 import BASE, PDF, tep_pdf

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


class ThongBaoHoanThienTests(KyBase):
    def test_creator_cancel_notifies_opened_and_signed_signers(self):
        self.ky(self.ky1)  # người ký cấp 1 đã ký
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
        d = r.data["results"][0]
        self.assertEqual(d["loai_thong_bao"], "TIN_NHAN")
        self.assertEqual((d["nguoi_thao_tac"], d["ly_do"]), ("ke_toan", "Đồng ý"))

    def test_deadline_reminders_are_idempotent(self):
        cap = SigningRequestStep.objects.get(luot_trinh__trinh_ky=self.pk, trang_thai=enums.TrangThaiCapKy.DANG_KY)
        cap.han_xu_ly = timezone.now() + timedelta(hours=3)
        cap.save(update_fields=["han_xu_ly"])
        self.assertEqual(thong_bao.nhac_han(), 2)  # hai người ký của cấp đang mở
        self.assertEqual(thong_bao.nhac_han(), 0)
        self.assertTrue(thong_bao_cua(self.ky1, "NHAC_HAN").exists())
        cap.han_xu_ly = timezone.now() - timedelta(hours=1)
        cap.save(update_fields=["han_xu_ly"])
        call_command("nhac_han_trinh_ky", stdout=io.StringIO())
        self.assertTrue(thong_bao_cua(self.ky1, "QUA_HAN").exists())
        self.assertTrue(thong_bao_cua(self.tao, "QUA_HAN").exists())
        self.assertEqual(thong_bao.nhac_han(), 0)
        self.assertEqual(thong_bao.nhac_han(timezone.now() + timedelta(days=1)), 4)  # nhắc lặp ngày sau: mỗi dòng người ký đang mở báo người ký và người tạo


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
        d = self.client_cua(self.tao).get("/api/v1/signing/thong-bao/").data["results"][0]
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
