"""
Hoàn thiện nghiệp vụ Nhóm 5: ký với dòng đã ủy quyền từ trước, thông báo khi hủy (kể cả hủy thay), tin nhắn trao đổi,
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
    SigningDelegationRole, SigningNotification, SigningRequestStep, SigningRequestStepSigner,
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


class UyQuyenDaCapTests(KyBase):
    """Chức năng tạo ủy quyền đã bỏ; dòng người ký được ủy quyền từ trước vẫn phải ký được và được kiểm lại khi ký."""

    def setUp(self):
        super().setUp()
        self.nhan = User.objects.create_user("pho_phong")
        cap_quyen(self.nhan, "sign_trinhky")
        self.dong_ky1 = SigningRequestStepSigner.objects.get(buoc_ky__luot_trinh__trinh_ky=self.pk, nguoi_ky=self.ky1)
        self.chuc_vu_giao = tao_chuc_vu("Người ký")
        self.chuc_vu_nhan = tao_chuc_vu("Người nhận")
        User.objects.filter(pk=self.ky1.pk).update(chuc_vu=self.chuc_vu_giao)
        User.objects.filter(pk=self.nhan.pk).update(chuc_vu=self.chuc_vu_nhan)
        SigningDelegationRole.objects.create(chuc_vu_giao=self.chuc_vu_giao, chuc_vu_nhan=self.chuc_vu_nhan)
        # Dữ liệu ủy quyền đã có từ trước: chuyển dòng người ký ky1 sang người nhận
        SigningRequestStepSigner.objects.filter(pk=self.dong_ky1.pk).update(
            uy_quyen_tu=self.ky1, chuc_vu_goc_uy_quyen=self.chuc_vu_giao, nguoi_ky=self.nhan,
            ten_nguoi_ky="pho_phong", chuc_vu=self.chuc_vu_nhan, ly_do_uy_quyen="Đi công tác",
            ngay_uy_quyen=timezone.now())
        self.dong_ky1.refresh_from_db()

    def test_existing_delegation_recipient_signs(self):
        # Người giao vẫn xem được hồ sơ; người nhận ký bằng khóa của mình
        self.assertEqual(self.client_cua(self.ky1).get(f"{BASE}/{self.pk}/").status_code, 200)
        self.assertEqual(self.ky(self.ky1).status_code, 403)
        self.khoa[self.nhan.pk] = khoa_hoat_dong(self.nhan, "K-pho-phong")
        r = self.ky(self.nhan)
        self.assertEqual(r.status_code, 200, r.data)
        _, dong = self.nguoi_ky(r.data, "pho_phong")
        self.assertEqual((dong["trang_thai"], dong["uy_quyen_tu"], dong["ten_nguoi_uy_quyen"]),
                         ("DA_KY", self.ky1.pk, "ke_toan"))

    def test_delegated_signer_must_retain_an_allowed_position_at_signing_time(self):
        self.khoa[self.nhan.pk] = khoa_hoat_dong(self.nhan, "K-pho-phong-role-change")
        User.objects.filter(pk=self.nhan.pk).update(chuc_vu=tao_chuc_vu("Chuyên viên"))

        response = self.ky(User.objects.get(pk=self.nhan.pk))

        self.assertEqual((response.status_code, response.data["code"]), (403, "uy_quyen_khong_con_hop_le"))
        self.assertFalse(SigningSignature.objects.filter(luot_trinh__trinh_ky_id=self.pk).exists())
        self.dong_ky1.refresh_from_db()
        self.assertEqual(self.dong_ky1.trang_thai, enums.TrangThaiNguoiKy.CHO_KY)

    def test_delegated_signer_is_rechecked_when_role_mapping_is_removed(self):
        self.khoa[self.nhan.pk] = khoa_hoat_dong(self.nhan, "K-pho-phong-mapping-removed")
        SigningDelegationRole.objects.filter(
            chuc_vu_giao=self.chuc_vu_giao, chuc_vu_nhan=self.chuc_vu_nhan,
        ).delete()

        response = self.ky(User.objects.get(pk=self.nhan.pk))

        self.assertEqual((response.status_code, response.data["code"]), (403, "uy_quyen_khong_con_hop_le"))
        self.assertFalse(SigningSignature.objects.filter(luot_trinh__trinh_ky_id=self.pk).exists())
        self.dong_ky1.refresh_from_db()
        self.assertEqual(self.dong_ky1.trang_thai, enums.TrangThaiNguoiKy.CHO_KY)

    def test_deactivated_delegated_signer_cannot_sign(self):
        self.khoa[self.nhan.pk] = khoa_hoat_dong(self.nhan, "K-pho-phong-deactivated")
        User.objects.filter(pk=self.nhan.pk).update(is_active=False)

        response = self.ky(User.objects.get(pk=self.nhan.pk))

        self.assertEqual(response.status_code, 403, response.data)
        self.assertFalse(SigningSignature.objects.filter(luot_trinh__trinh_ky_id=self.pk).exists())
        self.dong_ky1.refresh_from_db()
        self.assertEqual(self.dong_ky1.trang_thai, enums.TrangThaiNguoiKy.CHO_KY)

    def test_return_for_changes_preserves_delegation_and_original_role(self):
        response = self.hanh_dong(self.nhan, "yeu-cau-sua", tieu_de="Sửa", ly_do="Sai nội dung")
        self.assertEqual(response.status_code, 200, response.data)
        response = self.c.post(f"{BASE}/{self.pk}/giai-quyet/", {"tep": tep_pdf(PDF + b"% updated\n")},
                               format="multipart", HTTP_IDEMPOTENCY_KEY="giai-quyet-uq")
        self.assertEqual(response.status_code, 200, response.data)
        dong_moi = SigningRequestStepSigner.objects.get(buoc_ky__luot_trinh__trinh_ky=self.pk,
                                                       buoc_ky__luot_trinh__so_luot=2, nguoi_ky=self.nhan)
        self.assertEqual((dong_moi.uy_quyen_tu_id, dong_moi.chuc_vu_goc_uy_quyen_id),
                         (self.ky1.pk, self.chuc_vu_giao.pk))

    def test_create_and_config_endpoints_removed(self):
        quan_tri = User.objects.create_user("quan_tri_uq")
        cap_quyen(quan_tri, "manage_signing_process", "view_signing_audit")
        vao_nhom(quan_tri, "ADMIN")
        c = self.client_cua(quan_tri)
        r = c.post(f"{BASE}/{self.pk}/uy-quyen/", {"dong_nguoi_ky": self.dong_ky1.pk, "nguoi_nhan": self.nhan.pk,
                                                    "ly_do_uy_quyen": "x"}, format="json", HTTP_IDEMPOTENCY_KEY="uq-x")
        self.assertEqual(r.status_code, 404)
        self.assertEqual(c.get("/api/v1/signing/cau-hinh-uy-quyen/").status_code, 404)
        self.assertEqual(c.put("/api/v1/signing/cau-hinh-uy-quyen/", {}, format="json").status_code, 404)
        # Tham số muc_dich=uy_quyen không còn đổi hành vi tìm người dùng (không lọc theo ủy quyền)
        r = c.get(f"/api/v1/signing/nguoi-dung/?muc_dich=uy_quyen&ho_so={self.pk}&dong_nguoi_ky={self.dong_ky1.pk}&q=pho")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual([u["ten_dang_nhap"] for u in r.data], ["pho_phong"])
        # Chi tiết hồ sơ không còn trường co_the_uy_quyen
        r = c.get(f"{BASE}/{self.pk}/")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertNotIn("co_the_uy_quyen", r.data["luot_trinh"][0]["cap_ky"][0]["nguoi_ky"][0])


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
        d = r.data["results"][0]
        self.assertEqual(d["loai_thong_bao"], "TIN_NHAN")
        self.assertEqual((d["nguoi_thao_tac"], d["ly_do"]), ("ke_toan", "Đồng ý"))

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
