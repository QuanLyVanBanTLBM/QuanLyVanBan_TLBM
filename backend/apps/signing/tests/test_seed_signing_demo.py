"""Lệnh `seed_signing_demo`: đủ trạng thái hồ sơ, lịch sử, thông báo, dữ liệu Dashboard; chạy lại không nhân bản."""

import io
import os
import shutil
import tempfile
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from signing import enums
from signing.models import (
    SigningAttempt, SigningAuditLog, SigningKey, SigningNotification, SigningProcess, SigningRequest,
    SigningRequestStepSigner,
)
from signing.services import trinh_ky

from .helpers import tao_don_vi

User = get_user_model()
MAT_KHAU = "mat-khau-thu-nghiem-1"


def chay(test, *args, **env):
    """Chạy lệnh; tác vụ sau commit (gửi email, tạo tệp hoàn tất) được thực thi như khi chạy thật."""
    out = io.StringIO()
    with mock.patch.dict(os.environ, env, clear=False), test.captureOnCommitCallbacks(execute=True):
        call_command("seed_signing_demo", *args, stdout=out)
    return out.getvalue()


class DuLieuMauTests(TestCase):
    def setUp(self):
        self.thu_muc = tempfile.mkdtemp()
        self._cai_dat = override_settings(SIGNING_DOCUMENT_ROOT=self.thu_muc, DOCUMENT_STORAGE_ROOT=self.thu_muc)
        self._cai_dat.enable()
        tao_don_vi()

    def tearDown(self):
        self._cai_dat.disable()
        shutil.rmtree(self.thu_muc, ignore_errors=True)

    def ho_so(self, ma):
        return SigningRequest.objects.get(ghi_chu__startswith=f"Dữ liệu mẫu {ma}:", ho_so_goc__isnull=True)

    def test_requires_demo_password_to_create_accounts(self):
        with mock.patch.dict(os.environ, {"DEMO_PASSWORD": ""}):
            with self.assertRaisesMessage(CommandError, "DEMO_PASSWORD"):
                call_command("seed_signing_demo", stdout=io.StringIO())
        self.assertFalse(SigningRequest.objects.exists())

    def test_creates_all_states_and_is_idempotent(self):
        chay(self, DEMO_PASSWORD=MAT_KHAU)
        for username in ("admin", "vanthu", "chuyenvien", "truongphong", "giamdoc"):  # admin còn sentinel: khởi tạo
            self.assertTrue(User.objects.get(username=username).check_password(MAT_KHAU), username)
        self.assertEqual(SigningProcess.objects.filter(ma_quy_trinh__startswith="QT-TK-").count(), 4)
        self.assertEqual(SigningProcess.objects.filter(ma_quy_trinh="QT-TK-NHAP").get().trang_thai, "NHAP")

        tt = enums.TrangThaiYeuCau
        mong_doi = {"M01": tt.NHAP, "M02": tt.CHO_KY, "M03": tt.CHO_KY, "M04": tt.HOAN_THANH, "M05": tt.TU_CHOI,
                    "M06": tt.CHO_KY, "M07": tt.CHO_KY, "M08": tt.HUY, "M09": tt.CHO_KY, "M10": tt.CHO_KY}
        for ma, trang_thai in mong_doi.items():
            self.assertEqual(self.ho_so(ma).trang_thai, trang_thai, ma)
        # Trả sửa, sửa xong trình lượt 2, trình lại sau từ chối
        self.assertEqual(trinh_ky.luot_hien_hanh(self.ho_so("M06")).trang_thai, "YEU_CAU_SUA")
        self.assertEqual(trinh_ky.luot_hien_hanh(self.ho_so("M07")).so_luot, 2)
        self.assertEqual(SigningRequest.objects.filter(ho_so_goc=self.ho_so("M05"), trang_thai="NHAP").count(), 1)
        # Hoàn tất có tệp hoàn tất
        self.assertEqual(trinh_ky.luot_hien_hanh(self.ho_so("M04")).trang_thai_tep_hoan_tat, "THANH_CONG")
        # Người dùng thấy hồ sơ ở hộp "cần tôi ký"
        giamdoc, truongphong = User.objects.get(username="giamdoc"), User.objects.get(username="truongphong")
        self.assertIn(self.ho_so("M03"), trinh_ky.dang_cho_toi_ky(giamdoc))
        self.assertIn(self.ho_so("M10"), trinh_ky.dang_cho_toi_ky(truongphong))
        self.assertIn(self.ho_so("M02"), trinh_ky.dang_cho_toi_ky(truongphong))
        # Lịch sử và thông báo tương ứng
        loai = set(SigningNotification.objects.values_list("loai_thong_bao", flat=True))
        self.assertTrue({"CAN_KY", "HOAN_THANH", "TU_CHOI", "YEU_CAU_SUA", "HUY", "TIN_NHAN",
                         "QUA_HAN"} <= loai, loai)
        # Khóa tạm đã thu hồi: không ai còn khóa hoạt động do lệnh tạo
        self.assertFalse(SigningKey.objects.filter(trang_thai=enums.TrangThaiKhoa.HOAT_DONG).exists())

        dem = (SigningRequest.objects.count(), SigningAttempt.objects.count(), SigningNotification.objects.count(),
               SigningKey.objects.count(), User.objects.count())
        out = chay(self, DEMO_PASSWORD="")  # chạy lại: tài khoản đã có nên không cần mật khẩu, không tạo thêm gì
        self.assertIn("0 hồ sơ mẫu mới", out)
        self.assertEqual(dem, (SigningRequest.objects.count(), SigningAttempt.objects.count(),
                               SigningNotification.objects.count(), SigningKey.objects.count(), User.objects.count()))
        self.assertTrue(User.objects.get(username="vanthu").check_password(MAT_KHAU))

    def test_existing_admin_password_is_kept(self):
        admin = User.objects.filter(username="admin").first() or User.objects.create_user("admin", is_superuser=True)
        admin.set_password("mat-khau-quan-tri")
        admin.save()
        chay(self, DEMO_PASSWORD=MAT_KHAU)
        chay(self, "--dat-lai-mat-khau", DEMO_PASSWORD="mat-khau-moi-2")
        self.assertTrue(User.objects.get(username="admin").check_password("mat-khau-quan-tri"))
        self.assertTrue(User.objects.get(username="giamdoc").check_password("mat-khau-moi-2"))

    def test_dashboard_data_for_signers_with_distinct_dates(self):
        chay(self, DEMO_PASSWORD=MAT_KHAU)
        for username, toi_thieu in (("truongphong", 2), ("giamdoc", 2)):
            c = APIClient()
            c.force_authenticate(User.objects.get(username=username))
            d = c.get("/api/v1/signing/dashboard/").data
            self.assertGreaterEqual(d["so_cho_ky"], toi_thieu, username)
            self.assertLessEqual(d["so_cho_ky"], 3, username)
            self.assertEqual(len(d["gan_day"]), 5, username)
            self.assertEqual(len({p["ngay_trinh"][:10] for p in d["gan_day"]}), 5, username)
            self.assertTrue({"CHO_KY", "HOAN_THANH", "TU_CHOI"} <= {p["trang_thai"] for p in d["gan_day"]},
                            (username, d))

    def test_reset_cancels_old_sample_and_recreates(self):
        chay(self, DEMO_PASSWORD=MAT_KHAU)
        cu = set(SigningRequest.objects.filter(ghi_chu__startswith="Dữ liệu mẫu M").values_list("pk", flat=True))
        out = chay(self, "--reset", DEMO_PASSWORD=MAT_KHAU)
        self.assertIn("10 hồ sơ mẫu mới", out)
        self.assertTrue(SigningRequest.objects.filter(pk__in=cu).exclude(trang_thai__in=["NHAP", "CHO_KY"]).count()
                        == len(cu))
        self.assertTrue(all(g.startswith("Dữ liệu mẫu cũ") for g in
                            SigningRequest.objects.filter(pk__in=cu).values_list("ghi_chu", flat=True)))
        self.assertEqual(SigningRequest.objects.filter(ghi_chu__startswith="Dữ liệu mẫu M", ho_so_goc__isnull=True)
                         .count(), 10)

    def test_reset_keeps_recent_dashboard_items_from_new_sample(self):
        """Sau --reset, 5 phiếu gần nhất của giám đốc chỉ lấy từ bộ mới và có nhãn trạng thái thống nhất."""
        chay(self, DEMO_PASSWORD=MAT_KHAU)
        chay(self, "--reset", DEMO_PASSWORD=MAT_KHAU)
        c = APIClient()
        c.force_authenticate(User.objects.get(username="giamdoc"))
        gan_day = c.get("/api/v1/signing/dashboard/").data["gan_day"]
        self.assertEqual(len(gan_day), 5)
        self.assertEqual(len({p["tieu_de"] for p in gan_day}), 5, gan_day)
        self.assertTrue(
            {"Đang chờ ký", "Hoàn tất duyệt nội bộ", "Đã từ chối"}
            <= {p["nhan_trang_thai"] for p in gan_day},
            gan_day,
        )
        cu = SigningRequest.objects.filter(ghi_chu__startswith="Dữ liệu mẫu cũ").values_list("pk", flat=True)
        self.assertFalse({p["id"] for p in gan_day} & set(cu))
