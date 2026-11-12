from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.models import Position
from signing import enums
from signing.errors import SigningError
from signing.models import SigningProcess
from signing.services import process as process_service


User = get_user_model()


class ThuBacChucVuCapKyTests(TestCase):
    def setUp(self):
        self.nguoi_tao = User.objects.create_user("nguoi_tao_thu_bac")
        self.nguoi_ky = User.objects.create_user("nguoi_ky_thu_bac")
        thu_tu_dau = Position.get_next_display_order()
        self.chuc_vu_cao = Position.objects.create(display_order=thu_tu_dau, name="Chức vụ cấp cao")
        self.chuc_vu_trung = Position.objects.create(display_order=thu_tu_dau + 1, name="Chức vụ cấp trung")
        self.chuc_vu_thap = Position.objects.create(display_order=thu_tu_dau + 2, name="Chức vụ cấp thấp")

    def _nguoi_ky_chuc_vu(self, chuc_vu, thu_tu=1):
        return {"chuc_vu_id": chuc_vu.pk, "thu_tu": thu_tu}

    def _cap(self, thu_tu, *nguoi_ky):
        return {
            "cap_ky": thu_tu,
            "ten_cap_ky": f"Cấp {thu_tu}",
            "thu_tu": thu_tu,
            "nguoi_ky": list(nguoi_ky),
        }

    def _tao_quy_trinh(self, ma_quy_trinh, cap_ky):
        return process_service.tao_quy_trinh(
            self.nguoi_tao,
            ma_quy_trinh=ma_quy_trinh,
            ten_quy_trinh="Quy trình kiểm tra thứ bậc",
            pham_vi=enums.PhamViQuyTrinh.CONG_TY,
            cap_ky=cap_ky,
        )

    def _cau_truc(self, process):
        return [
            (
                step.thu_tu,
                list(
                    step.nguoi_ky_set.order_by("thu_tu").values_list(
                        "nguoi_ky_id", "chuc_vu_id", "thu_tu"
                    )
                ),
            )
            for step in process.cap_ky_set.order_by("thu_tu")
        ]

    def test_tao_cho_phep_cap_sau_co_chuc_vu_cao_hon_hoac_bang_cap_lien_truoc(self):
        process = self._tao_quy_trinh(
            "QT_THU_BAC_HOP_LE",
            [
                self._cap(1, self._nguoi_ky_chuc_vu(self.chuc_vu_trung)),
                self._cap(2, {"nguoi_ky": self.nguoi_ky, "thu_tu": 1}),
                self._cap(3, self._nguoi_ky_chuc_vu(self.chuc_vu_cao)),
                self._cap(4, self._nguoi_ky_chuc_vu(self.chuc_vu_cao)),
            ],
        )

        self.assertEqual(process.cap_ky_set.count(), 4)

    def test_tao_tu_choi_cap_sau_co_chuc_vu_thap_hon_va_khong_ghi_quy_trinh(self):
        with self.assertRaises(SigningError) as ctx:
            self._tao_quy_trinh(
                "QT_THU_BAC_KHONG_HOP_LE",
                [
                    self._cap(1, self._nguoi_ky_chuc_vu(self.chuc_vu_trung)),
                    self._cap(2, {"nguoi_ky": self.nguoi_ky, "thu_tu": 1}),
                    self._cap(3, self._nguoi_ky_chuc_vu(self.chuc_vu_thap)),
                ],
            )

        self.assertEqual(ctx.exception.get_codes(), "cap_ky_thu_bac_khong_hop_le")
        self.assertFalse(SigningProcess.objects.filter(ma_quy_trinh="QT_THU_BAC_KHONG_HOP_LE").exists())

    def test_tao_dung_chuc_vu_cao_nhat_khi_mot_cap_co_nhieu_chuc_vu(self):
        process = self._tao_quy_trinh(
            "QT_NHIEU_CHUC_VU",
            [
                self._cap(1, self._nguoi_ky_chuc_vu(self.chuc_vu_trung)),
                self._cap(
                    2,
                    self._nguoi_ky_chuc_vu(self.chuc_vu_thap, thu_tu=1),
                    self._nguoi_ky_chuc_vu(self.chuc_vu_cao, thu_tu=2),
                ),
            ],
        )

        self.assertEqual(process.cap_ky_set.get(thu_tu=2).nguoi_ky_set.count(), 2)

    def test_chuc_vu_khong_ton_tai_giu_nguyen_ma_loi_tham_chieu(self):
        with self.assertRaises(SigningError) as ctx:
            self._tao_quy_trinh(
                "QT_CHUC_VU_KHONG_TON_TAI",
                [self._cap(1, {"chuc_vu_id": 987654321, "thu_tu": 1})],
            )

        self.assertEqual(ctx.exception.get_codes(), "chuc_vu_khong_ton_tai")
        self.assertFalse(SigningProcess.objects.filter(ma_quy_trinh="QT_CHUC_VU_KHONG_TON_TAI").exists())

    def test_sua_vi_pham_giu_nguyen_cau_truc_ban_nhap(self):
        process = self._tao_quy_trinh(
            "QT_SUA_THU_BAC",
            [
                self._cap(1, self._nguoi_ky_chuc_vu(self.chuc_vu_trung)),
                self._cap(2, self._nguoi_ky_chuc_vu(self.chuc_vu_cao)),
            ],
        )
        cau_truc_truoc = self._cau_truc(process)

        with self.assertRaises(SigningError) as ctx:
            process_service.sua_quy_trinh(
                process,
                self.nguoi_tao,
                ten_quy_trinh="Tên không được lưu",
                pham_vi=enums.PhamViQuyTrinh.CONG_TY,
                cap_ky=[
                    self._cap(1, self._nguoi_ky_chuc_vu(self.chuc_vu_cao)),
                    self._cap(2, self._nguoi_ky_chuc_vu(self.chuc_vu_thap)),
                ],
            )

        self.assertEqual(ctx.exception.get_codes(), "cap_ky_thu_bac_khong_hop_le")
        process.refresh_from_db()
        self.assertEqual(process.ten_quy_trinh, "Quy trình kiểm tra thứ bậc")
        self.assertEqual(self._cau_truc(process), cau_truc_truoc)
