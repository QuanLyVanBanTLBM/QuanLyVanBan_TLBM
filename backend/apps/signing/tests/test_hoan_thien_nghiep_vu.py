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
from signing.models import (
    SigningAuditLog, SigningDelegationRole, SigningNotification, SigningRequestStep, SigningRequestStepSigner,
    SigningSignature,
)
from signing.services import thong_bao

from .helpers import cap_quyen, tao_chuc_vu, tao_don_vi
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


class UyQuyenTests(KyBase):
    def setUp(self):
        super().setUp()
        self.quan_tri = User.objects.create_user("quan_tri_uq")
        cap_quyen(self.quan_tri, "delegate_trinhky", "view_signing_audit")
        vao_nhom(self.quan_tri, "ADMIN")
        self.nhan = User.objects.create_user("pho_phong")
        cap_quyen(self.nhan, "sign_trinhky")
        self.dong_ky1 = SigningRequestStepSigner.objects.get(buoc_ky__luot_trinh__trinh_ky=self.pk, nguoi_ky=self.ky1)
        self.chuc_vu_giao = tao_chuc_vu("Người ký")
        self.chuc_vu_nhan = tao_chuc_vu("Người nhận")
        User.objects.filter(pk__in=[self.ky1.pk, self.ky3.pk]).update(chuc_vu=self.chuc_vu_giao)
        User.objects.filter(pk__in=[self.nhan.pk, self.ky2.pk]).update(chuc_vu=self.chuc_vu_nhan)
        SigningRequestStepSigner.objects.filter(buoc_ky__luot_trinh__trinh_ky=self.pk, nguoi_ky__in=[self.ky1, self.ky3]).update(chuc_vu=self.chuc_vu_giao)
        SigningRequestStepSigner.objects.filter(buoc_ky__luot_trinh__trinh_ky=self.pk, nguoi_ky=self.ky2).update(chuc_vu=self.chuc_vu_nhan)
        self.dong_ky1.refresh_from_db()
        SigningDelegationRole.objects.create(chuc_vu_giao=self.chuc_vu_giao, chuc_vu_nhan=self.chuc_vu_nhan)

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

    def test_delegation_cannot_return_directly_to_original_signer(self):
        SigningDelegationRole.objects.create(chuc_vu_giao=self.chuc_vu_giao, chuc_vu_nhan=self.chuc_vu_giao)
        self.assertEqual(self.uy_quyen(self.quan_tri, khoa="uq-direct-first").status_code, 200)

        response = self.uy_quyen(self.quan_tri, nguoi_nhan=self.ky1, khoa="uq-direct-return")

        self.assertEqual((response.status_code, response.data["code"]), (409, "uy_quyen_vong_lap"))
        self.dong_ky1.refresh_from_db()
        self.assertEqual((self.dong_ky1.nguoi_ky_id, self.dong_ky1.uy_quyen_tu_id),
                         (self.nhan.pk, self.ky1.pk))

    def test_delegation_cannot_return_to_original_signer_after_multiple_hops(self):
        cv_thu_ba = tao_chuc_vu("Người nhận thứ ba")
        nguoi_thu_ba = User.objects.create_user("nguoi_nhan_thu_ba", chuc_vu=cv_thu_ba)
        cap_quyen(nguoi_thu_ba, "sign_trinhky")
        SigningDelegationRole.objects.create(chuc_vu_giao=self.chuc_vu_giao, chuc_vu_nhan=cv_thu_ba)
        SigningDelegationRole.objects.create(chuc_vu_giao=self.chuc_vu_giao, chuc_vu_nhan=self.chuc_vu_giao)
        self.assertEqual(self.uy_quyen(self.quan_tri, khoa="uq-hop-one").status_code, 200)
        self.assertEqual(self.uy_quyen(self.quan_tri, nguoi_nhan=nguoi_thu_ba, khoa="uq-hop-two").status_code, 200)

        response = self.uy_quyen(self.quan_tri, nguoi_nhan=self.ky1, khoa="uq-hop-return")

        self.assertEqual((response.status_code, response.data["code"]), (409, "uy_quyen_vong_lap"))
        self.dong_ky1.refresh_from_db()
        self.assertEqual((self.dong_ky1.nguoi_ky_id, self.dong_ky1.uy_quyen_tu_id),
                         (nguoi_thu_ba.pk, self.ky1.pk))

    def test_delegated_signer_must_retain_an_allowed_position_at_signing_time(self):
        self.assertEqual(self.uy_quyen(self.quan_tri, khoa="uq-role-change").status_code, 200)
        self.khoa[self.nhan.pk] = khoa_hoat_dong(self.nhan, "K-pho-phong-role-change")
        User.objects.filter(pk=self.nhan.pk).update(chuc_vu=tao_chuc_vu("Chuyên viên"))

        response = self.ky(User.objects.get(pk=self.nhan.pk))

        self.assertEqual((response.status_code, response.data["code"]), (403, "uy_quyen_khong_con_hop_le"))
        self.assertFalse(SigningSignature.objects.filter(luot_trinh__trinh_ky_id=self.pk).exists())
        self.dong_ky1.refresh_from_db()
        self.assertEqual(self.dong_ky1.trang_thai, enums.TrangThaiNguoiKy.CHO_KY)

    def test_delegated_signer_is_rechecked_when_role_mapping_is_removed(self):
        self.assertEqual(self.uy_quyen(self.quan_tri, khoa="uq-role-mapping-removed").status_code, 200)
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
        self.assertEqual(self.uy_quyen(self.quan_tri, khoa="uq-deactivated").status_code, 200)
        self.khoa[self.nhan.pk] = khoa_hoat_dong(self.nhan, "K-pho-phong-deactivated")
        User.objects.filter(pk=self.nhan.pk).update(is_active=False)

        response = self.ky(User.objects.get(pk=self.nhan.pk))

        self.assertEqual(response.status_code, 403, response.data)
        self.assertFalse(SigningSignature.objects.filter(luot_trinh__trinh_ky_id=self.pk).exists())
        self.dong_ky1.refresh_from_db()
        self.assertEqual(self.dong_ky1.trang_thai, enums.TrangThaiNguoiKy.CHO_KY)

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

    def test_detail_marks_only_signers_allowed_by_current_users_delegation_scope(self):
        don_vi, don_vi_khac = tao_don_vi(), tao_don_vi()
        User.objects.filter(pk__in=[self.ky1.pk, self.ky2.pk]).update(don_vi=don_vi)
        User.objects.filter(pk=self.ky3.pk).update(don_vi=don_vi_khac)
        User.objects.filter(pk=self.tao.pk).update(don_vi=don_vi)
        truong_phong = User.objects.get(pk=self.tao.pk)
        cap_quyen(truong_phong, "delegate_trinhky")
        vao_nhom(truong_phong, "TP")

        response = self.client_cua(truong_phong).get(f"{BASE}/{self.pk}/")
        self.assertEqual(response.status_code, 200, response.data)
        nguoi_ky = {
            signer["nguoi_ky"]: signer
            for luot in response.data["luot_trinh"]
            for cap in luot["cap_ky"]
            for signer in cap["nguoi_ky"]
        }
        self.assertTrue(nguoi_ky[self.ky1.pk]["co_the_uy_quyen"])
        self.assertTrue(nguoi_ky[self.ky2.pk]["co_the_uy_quyen"])
        self.assertFalse(nguoi_ky[self.ky3.pk]["co_the_uy_quyen"])

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
        params = f"muc_dich=uy_quyen&ho_so={self.pk}&dong_nguoi_ky={self.dong_ky1.pk}"
        r = self.client_cua(self.tao).get(f"/api/v1/signing/nguoi-dung/?{params}")
        self.assertEqual(r.status_code, 403)
        r = self.client_cua(self.quan_tri).get(f"/api/v1/signing/nguoi-dung/?{params}&q=pho")
        self.assertEqual([u["ten_dang_nhap"] for u in r.data], ["pho_phong"])
        r = self.client_cua(self.quan_tri).get(f"/api/v1/signing/nguoi-dung/?{params}&q=nguoi_ngoai")
        self.assertEqual(r.data, [])

    def test_recipient_role_must_be_configured_on_server(self):
        SigningDelegationRole.objects.all().delete()
        response = self.uy_quyen(self.quan_tri)
        self.assertEqual((response.status_code, response.data["code"]), (400, "nguoi_nhan_khong_du_tham_quyen"))
        self.dong_ky1.refresh_from_db()
        self.assertEqual(self.dong_ky1.nguoi_ky_id, self.ky1.pk)

    def test_missing_original_position_blocks_search_and_delegation(self):
        self.dong_ky1.chuc_vu = None
        self.dong_ky1.save(update_fields=["chuc_vu"])
        url = f"/api/v1/signing/nguoi-dung/?muc_dich=uy_quyen&ho_so={self.pk}&dong_nguoi_ky={self.dong_ky1.pk}"
        response = self.client_cua(self.quan_tri).get(url)
        self.assertEqual((response.status_code, response.data["code"]), (400, "khong_co_chuc_danh_goc"))
        response = self.uy_quyen(self.quan_tri)
        self.assertEqual((response.status_code, response.data["code"]), (400, "nguoi_nhan_khong_du_tham_quyen"))

    def test_redelegation_uses_original_signing_role(self):
        cv_khac = tao_chuc_vu("Người khác")
        nguoi_khac = User.objects.create_user("nguoi_khac_uq", chuc_vu=cv_khac)
        cap_quyen(nguoi_khac, "sign_trinhky")
        SigningDelegationRole.objects.create(chuc_vu_giao=self.chuc_vu_nhan, chuc_vu_nhan=cv_khac)
        self.assertEqual(self.uy_quyen(self.quan_tri).status_code, 200)
        response = self.uy_quyen(self.quan_tri, nguoi_nhan=nguoi_khac, khoa="uq-lan-hai")
        self.assertEqual((response.status_code, response.data["code"]), (400, "nguoi_nhan_khong_du_tham_quyen"))
        SigningDelegationRole.objects.create(chuc_vu_giao=self.chuc_vu_giao, chuc_vu_nhan=cv_khac)
        self.assertEqual(self.uy_quyen(self.quan_tri, nguoi_nhan=nguoi_khac, khoa="uq-lan-hai-hop-le").status_code, 200)
        self.dong_ky1.refresh_from_db()
        self.assertEqual(self.dong_ky1.chuc_vu_goc_uy_quyen_id, self.chuc_vu_giao.pk)

    def test_search_lists_each_eligible_person_and_excludes_same_step(self):
        nhan_hai = User.objects.create_user("nguoi_nhan_hai", chuc_vu=self.chuc_vu_nhan)
        cap_quyen(nhan_hai, "sign_trinhky")
        url = f"/api/v1/signing/nguoi-dung/?muc_dich=uy_quyen&ho_so={self.pk}&dong_nguoi_ky={self.dong_ky1.pk}"
        response = self.client_cua(self.quan_tri).get(url)
        self.assertEqual(response.status_code, 200, response.data)
        ids = {user["id"] for user in response.data}
        self.assertTrue({self.nhan.pk, nhan_hai.pk} <= ids)
        self.assertNotIn(self.ky2.pk, ids)

    def test_return_for_changes_preserves_delegation_and_original_role(self):
        self.assertEqual(self.uy_quyen(self.quan_tri).status_code, 200)
        response = self.hanh_dong(self.nhan, "yeu-cau-sua", tieu_de="Sửa", ly_do="Sai nội dung")
        self.assertEqual(response.status_code, 200, response.data)
        response = self.c.post(f"{BASE}/{self.pk}/giai-quyet/", {"tep": tep_pdf(PDF + b"% updated\n")},
                               format="multipart", HTTP_IDEMPOTENCY_KEY="giai-quyet-uq")
        self.assertEqual(response.status_code, 200, response.data)
        dong_moi = SigningRequestStepSigner.objects.get(buoc_ky__luot_trinh__trinh_ky=self.pk,
                                                       buoc_ky__luot_trinh__so_luot=2, nguoi_ky=self.nhan)
        self.assertEqual((dong_moi.uy_quyen_tu_id, dong_moi.chuc_vu_goc_uy_quyen_id),
                         (self.ky1.pk, self.chuc_vu_giao.pk))

    def test_config_requires_process_admin_and_records_changes(self):
        url = "/api/v1/signing/cau-hinh-uy-quyen/"
        body = {"chuc_vu_giao": self.chuc_vu_giao.pk, "chuc_vu_nhan": []}
        self.assertEqual(self.client_cua(self.tao).put(url, body, format="json").status_code, 403)
        cap_quyen(self.quan_tri, "manage_signing_process")
        response = self.client_cua(self.quan_tri).put(url, body, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertFalse(SigningDelegationRole.objects.filter(chuc_vu_giao=self.chuc_vu_giao).exists())
        self.assertTrue(SigningAuditLog.objects.filter(hanh_dong="CAU_HINH_UY_QUYEN").exists())


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
