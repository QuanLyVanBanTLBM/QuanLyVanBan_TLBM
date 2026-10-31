"""
Quyền `view_all_trinhky`: xem toàn bộ hồ sơ trình ký (danh sách, chi tiết, tải tệp, tệp tài liệu, thống kê) nhưng không
kéo theo quyền ký, hủy, từ chối hay đọc trao đổi; hồ sơ của văn bản hạn chế mà người dùng không xem được không bị lộ.
"""

from django.contrib.auth import get_user_model
from documents.models import PhamVi, VanBanDi

from signing.models import SigningRequest

from .helpers import cap_quyen
from .test_hanh_dong_ky_phase8 import KyBase
from .test_trinh_ky_phase7 import BASE

GOC = BASE.rsplit("/", 1)[0]
User = get_user_model()


class XemTatCaHoSoTests(KyBase):
    def setUp(self):
        super().setUp()
        # Bản ghi văn bản đi thật (bộ lọc dùng truy vấn DB của module Văn bản; test gốc chỉ giả lập đọc văn bản)
        self.van_ban = VanBanDi.objects.create(id=10, so_hieu="10/QD", trich_yeu="Văn bản nội bộ", nguoi_tao=self.tao)
        SigningRequest.objects.filter(pk=self.pk).update(document_type="vanbandi", van_ban_id=10)
        self.van_thu = User.objects.create_user("van_thu_xem")
        cap_quyen(self.van_thu, "view_trinhky", "view_vanbandi", "view_all_trinhky")
        self.chuyen_vien = User.objects.create_user("chuyen_vien_khac")
        cap_quyen(self.chuyen_vien, "view_trinhky", "view_vanbandi")

    def ids(self, user, **tham_so):
        r = self.client_cua(user).get(f"{BASE}/", {"hop": "tat_ca", **tham_so})
        self.assertEqual(r.status_code, 200, r.data)
        return {x["id"] for x in r.data["results"]}

    def test_holder_sees_other_users_requests_everywhere(self):
        c = self.client_cua(self.van_thu)
        self.assertIn(self.pk, self.ids(self.van_thu))
        self.assertEqual(c.get(f"{BASE}/{self.pk}/").status_code, 200)
        luot = SigningRequest.objects.get(pk=self.pk).luot_trinh_set.get().pk
        r = c.get(f"{BASE}/{self.pk}/tep/", {"luot": luot})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.content.startswith(b"%PDF-"))
        tep = c.get(f"{GOC}/tai-lieu/")
        self.assertEqual(tep.status_code, 200, tep.data)
        self.assertIn(self.pk, {x["trinh_ky"] for x in tep.data["results"]})
        dem = c.get(f"{BASE}/thong-ke/", {"hop": "tat_ca"})
        self.assertEqual(dem.status_code, 200, dem.data)
        self.assertEqual(dem.data["tat_ca"], len(self.ids(self.van_thu)))
        self.assertEqual(c.get(f"{BASE}/", {"hop": "tat_ca", "q": "10/QD"}).data["count"], 1)

    def test_user_without_permission_sees_nothing_unrelated(self):
        self.assertNotIn(self.pk, self.ids(self.chuyen_vien))
        c = self.client_cua(self.chuyen_vien)
        self.assertEqual(c.get(f"{BASE}/{self.pk}/").status_code, 404)
        self.assertEqual(c.get(f"{BASE}/thong-ke/", {"hop": "tat_ca"}).data["tat_ca"], 0)
        self.assertEqual(c.get(f"{GOC}/tai-lieu/").data["count"], 0)

    def test_permission_does_not_grant_actions_or_discussion(self):
        self.assertEqual(self.hanh_dong(self.van_thu, "huy", ly_do="Không có quyền hủy").status_code, 403)
        for hanh_dong in ("ky", "tu-choi", "thu-hoi"):
            r = self.hanh_dong(self.van_thu, hanh_dong, ly_do="Không phải người ký")
            self.assertIn(r.status_code, (400, 403, 404, 409), (hanh_dong, r.data))
        self.assertEqual(SigningRequest.objects.get(pk=self.pk).trang_thai, "CHO_KY")

    def test_restricted_document_request_hidden_unless_document_visible(self):
        # Phạm vi văn bản không đổi được sau khi tạo (trigger): gắn hồ sơ sang văn bản đi hạn chế khác
        self.van_ban = VanBanDi.objects.create(
            id=11, so_hieu="11/QD", trich_yeu="Văn bản hạn chế", nguoi_tao=self.tao, pham_vi=PhamVi.HAN_CHE)
        SigningRequest.objects.filter(pk=self.pk).update(van_ban_id=11)
        self.assertNotIn(self.pk, self.ids(self.van_thu))
        c = self.client_cua(self.van_thu)
        self.assertEqual(c.get(f"{BASE}/{self.pk}/").status_code, 404)
        self.assertNotIn(self.pk, {x["trinh_ky"] for x in c.get(f"{GOC}/tai-lieu/").data["results"]})
        self.assertEqual(c.get(f"{BASE}/thong-ke/", {"hop": "tat_ca"}).data["tat_ca"], 0)
        # Người nhận được chỉ định xem được văn bản gốc thì xem được hồ sơ
        self.van_ban.nguoi_nhan.add(self.van_thu)
        self.assertIn(self.pk, self.ids(self.van_thu))
        self.assertEqual(c.get(f"{BASE}/{self.pk}/").status_code, 200)

    def test_draft_request_without_document_visible_to_holder(self):
        r = self.tao_nhap(van_ban_id=None)
        self.assertEqual(r.status_code, 201, r.data)
        self.assertIn(r.data["id"], self.ids(self.van_thu))

    def test_current_user_permissions_expose_new_code(self):
        r = self.client_cua(self.van_thu).get(f"{GOC}/toi/")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertTrue(r.data["quyen"]["view_all_trinhky"])
        self.assertFalse(r.data["quyen"]["view_signing_audit"])
