"""Migration signing/0018: chuyển dữ liệu ký nháy/ủy quyền thay vì dừng (PostgreSQL, dựng DB tại 0017)."""

from django.contrib.auth import get_user_model
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone

from .helpers import tao_chuc_vu

TRUOC = [("signing", "0017_signingrequest_uq_signing_completed_doc")]
SAU = [("signing", "0018_bo_ky_nhay_uy_quyen")]


class Migration0018ChuyenKyNhayTests(TransactionTestCase):
    def _migrate(self, targets):
        executor = MigrationExecutor(connection)
        executor.migrate(targets)
        return executor.loader.project_state(targets).apps

    def setUp(self):
        self._migrate(TRUOC)

    def tearDown(self):
        self._migrate(MigrationExecutor(connection).loader.graph.leaf_nodes())

    def _dung_du_lieu(self, apps):
        User = get_user_model()
        QuyTrinh = apps.get_model("signing", "SigningProcess")
        Buoc = apps.get_model("signing", "SigningProcessStep")
        CauHinh = apps.get_model("signing", "SigningProcessStepSigner")
        HoSo = apps.get_model("signing", "SigningRequest")
        Luot = apps.get_model("signing", "SigningAttempt")
        CapKy = apps.get_model("signing", "SigningRequestStep")
        NguoiKy = apps.get_model("signing", "SigningRequestStepSigner")
        Vai = apps.get_model("signing", "SigningDelegationRole")

        # Tài khoản và chức vụ thuộc app khác (không đổi ở 0018) nên dùng model thật; model lịch sử nhận qua *_id.
        a, b, c = (User.objects.create_user(f"mig0018_{i}") for i in "abc")
        chuc_vu = tao_chuc_vu()
        Vai.objects.create(chuc_vu_giao_id=chuc_vu.pk, chuc_vu_nhan_id=chuc_vu.pk)

        quy_trinh = QuyTrinh.objects.create(
            ma_quy_trinh="MIG0018", ten_quy_trinh="Quy trình kiểm thử", pham_vi="CONG_TY", create_by_id=a.pk,
        )
        buoc1 = Buoc.objects.create(quy_trinh_id=quy_trinh.pk, cap_ky=1, ten_cap_ky="Duyệt nháy", thu_tu=1)
        buoc2 = Buoc.objects.create(quy_trinh_id=quy_trinh.pk, cap_ky=2, ten_cap_ky="Ký chính", thu_tu=2)
        # Cấp 1: một ký nháy theo tài khoản và một ký nháy trùng người với ký chính cùng cấp.
        cau_nhay = CauHinh.objects.create(buoc_quy_trinh_id=buoc1.pk, nguoi_ky_id=a.pk, vai_tro_ky="KY_NHAY", thu_tu=1)
        cau_nhay_trung = CauHinh.objects.create(buoc_quy_trinh_id=buoc1.pk, nguoi_ky_id=b.pk, vai_tro_ky="KY_NHAY", thu_tu=2)
        cau_chinh_b = CauHinh.objects.create(buoc_quy_trinh_id=buoc1.pk, nguoi_ky_id=b.pk, vai_tro_ky="KY_CHINH", thu_tu=3)
        cau_chuc_vu = CauHinh.objects.create(
            buoc_quy_trinh_id=buoc2.pk, chuc_vu_id=chuc_vu.pk, pham_vi_chuc_vu="TOAN_CO_QUAN", vai_tro_ky="KY_NHAY", thu_tu=1,
        )

        ho_so = HoSo.objects.create(quy_trinh_id=quy_trinh.pk, phien_ban_quy_trinh=1, trang_thai="CHO_KY",
            trich_yeu_van_ban="Hồ sơ kiểm thử migration", create_by_id=a.pk,
        )
        luot = Luot.objects.create(
            trinh_ky_id=ho_so.pk, so_luot=1, vi_tri_luu_tep="tep.pdf", ma_bam_tai_lieu="0" * 64, trang_thai="CHO_KY", create_by_id=a.pk,
        )
        cap = CapKy.objects.create(
            luot_trinh_id=luot.pk, buoc_quy_trinh_id=buoc1.pk, cap_ky=1, ten_cap_ky="Duyệt nháy", thu_tu=1,
            trang_thai="DANG_KY", thoi_diem_mo=timezone.now(),
        )
        cap_cho = CapKy.objects.create(
            luot_trinh_id=luot.pk, buoc_quy_trinh_id=buoc2.pk, cap_ky=2, ten_cap_ky="Ký chính", thu_tu=2, trang_thai="CHUA_MO",
        )
        dong_nhay_da_ky = NguoiKy.objects.create(
            buoc_ky_id=cap.pk, nguoi_ky_id=a.pk, ten_nguoi_ky="A", vai_tro_ky="KY_NHAY", trang_thai="DA_KY",
            thoi_diem_mo=cap.thoi_diem_mo, ngay_ky=timezone.now(),
        )
        # Ký chính bị ký nháy chặn: chưa được mở.
        dong_chinh_bi_chan = NguoiKy.objects.create(
            buoc_ky_id=cap.pk, nguoi_ky_id=b.pk, ten_nguoi_ky="B", vai_tro_ky="KY_CHINH", trang_thai="CHO_KY",
        )
        dong_uy_quyen = NguoiKy.objects.create(
            buoc_ky_id=cap.pk, nguoi_ky_id=c.pk, ten_nguoi_ky="C", vai_tro_ky="KY_CHINH", trang_thai="CHO_KY",
            uy_quyen_tu_id=a.pk, ly_do_uy_quyen="Công tác", ngay_uy_quyen=timezone.now(), chuc_vu_goc_uy_quyen_id=chuc_vu.pk,
        )
        dong_chua_mo_cap_sau = NguoiKy.objects.create(
            buoc_ky_id=cap_cho.pk, nguoi_ky_id=a.pk, ten_nguoi_ky="A", vai_tro_ky="KY_NHAY", trang_thai="CHO_KY",
        )
        return {
            "cau_nhay": cau_nhay.pk, "cau_nhay_trung": cau_nhay_trung.pk, "cau_chinh_b": cau_chinh_b.pk,
            "cau_chuc_vu": cau_chuc_vu.pk, "nhay_da_ky": dong_nhay_da_ky.pk, "chinh_bi_chan": dong_chinh_bi_chan.pk,
            "uy_quyen": dong_uy_quyen.pk, "cap_sau": dong_chua_mo_cap_sau.pk, "cap_thoi_diem_mo": cap.thoi_diem_mo,
        }

    def test_tu_chuyen_du_lieu_thay_vi_dung(self):
        ids = self._dung_du_lieu(self._migrate(TRUOC))

        apps = self._migrate(SAU)  # không được ném lỗi dù còn dữ liệu ký nháy/ủy quyền

        CauHinh = apps.get_model("signing", "SigningProcessStepSigner")
        NguoiKy = apps.get_model("signing", "SigningRequestStepSigner")
        self.assertFalse(CauHinh.objects.exclude(vai_tro_ky="KY_CHINH").exists())
        self.assertFalse(NguoiKy.objects.exclude(vai_tro_ky="KY_CHINH").exists())

        # Cấu hình: ký nháy thành ký chính, giữ thứ tự; dòng trùng người với ký chính cùng cấp bị bỏ.
        self.assertEqual(CauHinh.objects.get(pk=ids["cau_nhay"]).thu_tu, 1)
        self.assertEqual(CauHinh.objects.get(pk=ids["cau_chuc_vu"]).pham_vi_chuc_vu, "TOAN_CO_QUAN")
        self.assertFalse(CauHinh.objects.filter(pk=ids["cau_nhay_trung"]).exists())
        self.assertTrue(CauHinh.objects.filter(pk=ids["cau_chinh_b"]).exists())
        self.assertEqual(CauHinh.objects.count(), 3)

        # Hồ sơ: không mất người ký, giữ trạng thái đã ký; dòng ủy quyền vẫn là người ký của cấp.
        self.assertEqual(NguoiKy.objects.count(), 4)
        self.assertEqual(NguoiKy.objects.get(pk=ids["nhay_da_ky"]).trang_thai, "DA_KY")
        self.assertTrue(NguoiKy.objects.filter(pk=ids["uy_quyen"]).exists())

        # Người ký bị ký nháy chặn trong cấp đang ký được mở; cấp chưa mở vẫn chưa mở.
        cho_mo = NguoiKy.objects.get(pk=ids["chinh_bi_chan"])
        self.assertEqual(cho_mo.thoi_diem_mo, ids["cap_thoi_diem_mo"])
        self.assertIsNotNone(NguoiKy.objects.get(pk=ids["uy_quyen"]).thoi_diem_mo)
        self.assertIsNone(NguoiKy.objects.get(pk=ids["cap_sau"]).thoi_diem_mo)

        # Schema cuối: không còn bảng/cột ủy quyền và cột chan_ky_chinh.
        with connection.cursor() as cursor:
            self.assertNotIn("signing_delegation_role", connection.introspection.table_names(cursor))
            cot = {c.name for c in connection.introspection.get_table_description(cursor, "signing_request_step_signer")}
        self.assertFalse(cot & {"uy_quyen_tu_id", "ly_do_uy_quyen", "ngay_uy_quyen", "chuc_vu_goc_uy_quyen_id", "chan_ky_chinh"})

    def test_khong_co_du_lieu_cu_van_ap_dung_duoc(self):
        self._migrate(SAU)
