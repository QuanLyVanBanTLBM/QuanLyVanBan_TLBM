"""Thay người ký của hồ sơ đang chờ người ký bị khóa quyền ký (issue #499, phân vùng 3 của #447)."""

from django.contrib.auth import get_user_model

from signing.models import SigningAuditLog, SigningNotification, SigningRequestStepSigner
from signing.services import quyen_ky

from .helpers import cap_quyen, dat_anh_chu_ky, tao_chuc_vu
from .test_hanh_dong_ky_phase8 import KyBase, khoa_hoat_dong
from .test_trinh_ky_phase7 import BASE

User = get_user_model()
DUONG_DAN = "thay-nguoi-ky"


class ThayNguoiKyTests(KyBase):
    def setUp(self):
        super().setUp()
        self.quan_tri = User.objects.create_user("quan_tri")
        cap_quyen(self.quan_tri, "manage_signing_process")
        self.moi = User.objects.create_user("ky_moi")
        cap_quyen(self.moi, "sign_trinhky")

    def dong(self, user):
        return SigningRequestStepSigner.objects.get(buoc_ky__luot_trinh__trinh_ky_id=self.pk, nguoi_ky=user)

    def khoa_quyen(self, user):
        return quyen_ky.khoa_quyen(user.pk, self.quan_tri, ly_do="Kiểm tra bảo mật", thoi_han="den_khi_bat_lai")

    def thay(self, nguoi_thuc_hien, cu, moi, ly_do="Người ký cũ bị khóa quyền ký", **ghi_de):
        body = {"nguoi_ky_id": self.dong(cu).pk, "nguoi_ky_moi_id": moi.pk, "ly_do": ly_do}
        body.update(ghi_de)
        return self.client_cua(User.objects.get(pk=nguoi_thuc_hien.pk)).post(
            f"{BASE}/{self.pk}/{DUONG_DAN}/", body, format="json")

    def test_creator_replaces_locked_pending_signer(self):
        self.khoa_quyen(self.ky1)
        r = self.thay(self.tao, self.ky1, self.moi)
        self.assertEqual(r.status_code, 200, r.data)
        dong = SigningRequestStepSigner.objects.get(pk=self.dong(self.moi).pk)
        self.assertEqual((dong.nguoi_ky_id, dong.ten_nguoi_ky, dong.trang_thai), (self.moi.pk, "ky_moi", "CHO_KY"))
        self.assertIsNotNone(dong.thoi_diem_mo)
        self.assertFalse(SigningRequestStepSigner.objects.filter(nguoi_ky=self.ky1).exists())

    def test_new_signer_can_sign_and_old_signer_is_removed(self):
        self.khoa_quyen(self.ky1)
        self.assertEqual(self.thay(self.tao, self.ky1, self.moi).status_code, 200)
        self.khoa[self.moi.pk] = khoa_hoat_dong(self.moi, "K-ky-moi")
        dat_anh_chu_ky(self.moi)
        self.assertEqual(self.ky(self.moi).status_code, 200)

    def test_admin_can_replace(self):
        self.khoa_quyen(self.ky2)
        r = self.thay(self.quan_tri, self.ky2, self.moi)
        self.assertEqual(r.status_code, 200, r.data)

    def test_existing_signature_is_kept(self):
        self.assertEqual(self.ky(self.ky2).status_code, 200)
        chu_ky_truoc = self.dong(self.ky2).chu_ky_hien_hanh_id
        self.khoa_quyen(self.ky1)
        self.assertEqual(self.thay(self.tao, self.ky1, self.moi).status_code, 200)
        dong = self.dong(self.ky2)
        self.assertEqual((dong.trang_thai, dong.chu_ky_hien_hanh_id), ("DA_KY", chu_ky_truoc))

    def test_audit_log_and_notification(self):
        self.khoa_quyen(self.ky1)
        self.thay(self.tao, self.ky1, self.moi, ly_do="  Người ký cũ nghỉ phép dài ngày  ")
        nhat_ky = SigningAuditLog.objects.get(trinh_ky_id=self.pk, hanh_dong="THAY_NGUOI_KY")
        self.assertEqual((nhat_ky.nguoi_thuc_hien_id, nhat_ky.chi_tiet), (self.tao.pk, "Người ký cũ nghỉ phép dài ngày"))
        self.assertEqual(nhat_ky.du_lieu_kem_theo["nguoi_ky_cu_id"], self.ky1.pk)
        self.assertEqual(nhat_ky.du_lieu_kem_theo["nguoi_ky_moi_id"], self.moi.pk)
        self.assertTrue(SigningNotification.objects.filter(
            nguoi_nhan=self.moi, loai_thong_bao="CAN_KY", kenh="IN_APP").exists())

    def test_reason_is_required(self):
        self.khoa_quyen(self.ky1)
        for ly_do in ("", "   "):
            r = self.thay(self.tao, self.ky1, self.moi, ly_do=ly_do)
            self.assertEqual(r.status_code, 400, r.data)
        self.assertFalse(SigningAuditLog.objects.filter(hanh_dong="THAY_NGUOI_KY").exists())

    def test_other_user_forbidden(self):
        self.khoa_quyen(self.ky1)
        r = self.thay(self.ky2, self.ky1, self.moi)
        self.assertEqual((r.status_code, r.data["code"]), (403, "khong_co_quyen"))
        self.assertEqual(self.thay(self.la, self.ky1, self.moi).status_code, 404)

    def test_signer_not_locked_rejected(self):
        r = self.thay(self.tao, self.ky1, self.moi)
        self.assertEqual((r.status_code, r.data["code"]), (409, "nguoi_ky_khong_bi_khoa_quyen_ky"))

    def test_only_signer_of_open_level_can_be_replaced(self):
        self.khoa_quyen(self.ky3)
        r = self.thay(self.tao, self.ky3, self.moi)
        self.assertEqual((r.status_code, r.data["code"]), (409, "nguoi_ky_khong_the_thay"))

    def test_signed_signer_cannot_be_replaced(self):
        self.assertEqual(self.ky(self.ky1).status_code, 200)
        self.khoa_quyen(self.ky1)
        r = self.thay(self.tao, self.ky1, self.moi)
        self.assertEqual((r.status_code, r.data["code"]), (409, "nguoi_ky_khong_the_thay"))

    def test_replacement_must_have_sign_permission_active_and_unlocked(self):
        self.khoa_quyen(self.ky1)
        khong_quyen = User.objects.create_user("khong_quyen")
        r = self.thay(self.tao, self.ky1, khong_quyen)
        self.assertEqual((r.status_code, r.data["code"]), (400, "nguoi_ky_thieu_quyen_ky"))
        bi_khoa = User.objects.create_user("bi_khoa")
        cap_quyen(bi_khoa, "sign_trinhky")
        self.khoa_quyen(bi_khoa)
        r = self.thay(self.tao, self.ky1, bi_khoa)
        self.assertEqual((r.status_code, r.data["code"]), (400, "nguoi_ky_bi_khoa_quyen_ky"))
        nghi = User.objects.create_user("nghi_viec")
        cap_quyen(nghi, "sign_trinhky")
        User.objects.filter(pk=nghi.pk).update(is_active=False)
        r = self.thay(self.tao, self.ky1, nghi)
        self.assertEqual((r.status_code, r.data["code"]), (400, "nguoi_ky_moi_khong_hoat_dong"))

    def test_replacement_already_in_level_rejected(self):
        self.khoa_quyen(self.ky1)
        r = self.thay(self.tao, self.ky1, self.ky2)
        self.assertEqual((r.status_code, r.data["code"]), (400, "nguoi_ky_trung_trong_cap"))

    def test_unknown_signer_or_account(self):
        self.khoa_quyen(self.ky1)
        r = self.thay(self.tao, self.ky1, self.moi, nguoi_ky_moi_id=999999)
        self.assertEqual((r.status_code, r.data["code"]), (404, "khong_tim_thay_tai_khoan"))
        r = self.thay(self.tao, self.ky1, self.moi, nguoi_ky_id=999999)
        self.assertEqual((r.status_code, r.data["code"]), (404, "khong_tim_thay_nguoi_ky"))

    def test_position_order_between_levels_enforced(self):
        cao, thap = tao_chuc_vu("Cao"), tao_chuc_vu("Thấp")  # display_order của `cao` nhỏ hơn: cấp cao hơn
        SigningRequestStepSigner.objects.filter(nguoi_ky=self.ky3).update(chuc_vu=cao)
        SigningRequestStepSigner.objects.filter(nguoi_ky__in=[self.ky1, self.ky2]).update(chuc_vu=thap)
        self.khoa_quyen(self.ky1)
        sai = User.objects.create_user("chuc_vu_cao_hon_cap_sau")  # cấp trước cao hơn cấp sau: không hợp lệ
        cap_quyen(sai, "sign_trinhky")
        self.assertLess(self.position.display_order, cao.display_order)  # cao hơn cả chức vụ của cấp sau
        User.objects.filter(pk=sai.pk).update(chuc_vu=self.position)
        r = self.thay(self.tao, self.ky1, sai)
        self.assertEqual((r.status_code, r.data["code"]), (400, "cap_ky_thu_bac_khong_hop_le"))
        dung = User.objects.create_user("chuc_vu_hop_le")
        cap_quyen(dung, "sign_trinhky")
        User.objects.filter(pk=dung.pk).update(chuc_vu=thap)
        r = self.thay(self.tao, self.ky1, dung)
        self.assertEqual(r.status_code, 200, r.data)

    def test_detail_flags_replaceable_signer_only_for_creator_or_admin(self):
        self.khoa_quyen(self.ky1)

        def co_the_thay(user):
            r = self.client_cua(User.objects.get(pk=user.pk)).get(f"{BASE}/{self.pk}/")
            self.assertEqual(r.status_code, 200, r.data)
            return {n["nguoi_ky"]: n["co_the_thay"] for cap in r.data["luot_trinh"][0]["cap_ky"]
                    for n in cap["nguoi_ky"]}

        self.assertEqual(co_the_thay(self.tao), {self.ky1.pk: True, self.ky2.pk: False, self.ky3.pk: False})
        self.assertEqual(co_the_thay(self.quan_tri), {self.ky1.pk: True, self.ky2.pk: False, self.ky3.pk: False})
        self.assertEqual(set(co_the_thay(self.ky2).values()), {False})

    def ung_vien(self, nguoi, cu, **tham_so):
        tham_so = {"nguoi_ky_id": self.dong(cu).pk, **tham_so}
        return self.client_cua(User.objects.get(pk=nguoi.pk)).get(f"{BASE}/{self.pk}/{DUONG_DAN}/", tham_so)

    def test_candidates_filtered_by_permission_lock_level_and_keyword(self):
        self.khoa_quyen(self.ky1)
        khong_quyen = User.objects.create_user("khong_quyen")
        bi_khoa = User.objects.create_user("bi_khoa")
        cap_quyen(bi_khoa, "sign_trinhky")
        self.khoa_quyen(bi_khoa)
        r = self.ung_vien(self.tao, self.ky1)
        self.assertEqual(r.status_code, 200, r.data)
        ids = {u["id"] for u in r.data}
        self.assertIn(self.moi.pk, ids)
        self.assertIn(self.ky3.pk, ids)  # cấp khác, còn quyền ký
        self.assertFalse({self.ky1.pk, self.ky2.pk, khong_quyen.pk, bi_khoa.pk} & ids)
        r = self.ung_vien(self.quan_tri, self.ky1, q="KY_MOI")
        self.assertEqual([u["id"] for u in r.data], [self.moi.pk])

    def test_candidates_forbidden_for_other_user_and_empty_when_not_locked(self):
        self.assertEqual(self.ung_vien(self.la, self.ky1).status_code, 404)  # không xem được hồ sơ
        self.assertEqual(self.ung_vien(self.ky2, self.ky1).status_code, 403)  # xem được nhưng không phải người tạo
        self.assertEqual(self.ung_vien(self.tao, self.ky3).data, [])  # cấp chưa mở
        self.assertEqual(self.ung_vien(self.tao, self.ky2).data, [])  # chưa bị khóa
