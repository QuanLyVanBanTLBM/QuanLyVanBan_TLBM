"""GET /api/v1/signing/dashboard/ (Nhóm 1): đếm hồ sơ chờ ký đúng người, phiếu gần đây chỉ của người đó."""

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from signing.selectors import tong_quan_dashboard

from .helpers import cap_quyen
from .test_hanh_dong_ky_phase8 import KyBase

User = get_user_model()
URL = "/api/v1/signing/dashboard/"


class DashboardTests(KyBase):
    def data(self, user):
        return self.client_cua(User.objects.get(pk=user.pk)).get(URL).data

    def test_requires_login(self):
        self.assertEqual(APIClient().get(URL).status_code, 401)

    def test_counts_only_dossiers_waiting_for_the_user(self):
        d = self.data(self.ky1)  # cấp 1 đang mở
        self.assertEqual(d["so_cho_ky"], 1)
        self.assertEqual(d["gan_day"][0]["id"], self.pk)
        self.assertTrue(d["gan_day"][0]["can_toi_ky"])
        self.assertEqual((d["gan_day"][0]["trang_thai"], d["gan_day"][0]["nhan_trang_thai"]), ("CHO_KY", "Đang chờ ký"))
        self.assertEqual(d["gan_day"][0]["nguoi_trinh"], "chuyen_vien")
        self.assertEqual(self.data(self.ky3)["so_cho_ky"], 0)  # cấp 2 chưa mở: có liên quan nhưng chưa chờ ký
        self.assertFalse(self.data(self.ky3)["gan_day"][0]["can_toi_ky"])
        self.ky(self.ky1)
        self.assertEqual(self.data(self.ky1)["so_cho_ky"], 0)

    def test_does_not_leak_other_users_dossiers(self):
        cap_quyen(self.la, "view_signing_audit")  # kiểm toán xem được mọi hồ sơ nhưng Dashboard chỉ việc của mình
        self.assertEqual(self.data(self.la), {"so_cho_ky": 0, "gan_day": []})

    def test_limit_and_labels(self):
        for _ in range(6):
            self.ho_so_da_gui()
        d = tong_quan_dashboard(self.tao)
        self.assertEqual(len(d["gan_day"]), 5)
        self.assertTrue(all(p["tieu_de"] for p in d["gan_day"]))
        self.hanh_dong(self.ky1, "tu-choi", ly_do_tu_choi="Sai số liệu")
        nhan = {p["id"]: p["nhan_trang_thai"] for p in tong_quan_dashboard(self.tao, 20)["gan_day"]}
        self.assertEqual(nhan[self.pk], "Đã từ chối")

    def test_returned_request_exposes_current_attempt_state(self):
        response = self.hanh_dong(
            self.ky1, "yeu-cau-sua", tieu_de="Bổ sung chứng từ", ly_do="Thiếu phụ lục."
        )
        self.assertEqual(response.status_code, 200, response.data)

        item = next(row for row in tong_quan_dashboard(self.tao)["gan_day"] if row["id"] == self.pk)
        self.assertEqual(item["trang_thai"], "CHO_KY")
        self.assertEqual(item["trang_thai_luot"], "YEU_CAU_SUA")
        self.assertEqual(item["nhan_trang_thai"], "Chờ người trình sửa")
