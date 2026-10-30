from django.contrib.auth import get_user_model
from django.test import TestCase

from signing import enums
from signing.errors import SigningError
from signing.models import SigningProcess, SigningProcessStep
from signing.services import process as process_service

from .helpers import tao_chuc_vu

User = get_user_model()


class ThuBacChucVuCapKyTests(TestCase):
    """
    Cấp ký sau không được chọn chức vụ thấp hơn cấp ký liền trước (chỉ áp dụng cho người ký cấu hình theo
    chức vụ). Thứ bậc lấy từ accounts_position.display_order (Nhóm 7): display_order nhỏ hơn là chức vụ
    cao hơn; `tao_chuc_vu` gán display_order tăng dần theo thứ tự gọi, nên gọi theo đúng thứ tự cao → thấp
    bên dưới để display_order phản ánh đúng chủ đích của test.
    """

    def setUp(self):
        self.u1 = User.objects.create_user("u1")
        self.u2 = User.objects.create_user("u2")
        self.giam_doc = tao_chuc_vu("Giám đốc")
        self.pho_giam_doc = tao_chuc_vu("Phó Giám đốc")
        self.truong_phong = tao_chuc_vu("Trưởng phòng")

    @staticmethod
    def _cap(thu_tu, chuc_vu_id=None, nguoi_ky_tai_khoan=None, them=()):
        nguoi_ky = list(them)
        if chuc_vu_id is not None:
            nguoi_ky.append({"chuc_vu_id": chuc_vu_id, "thu_tu": len(nguoi_ky) + 1})
        if nguoi_ky_tai_khoan is not None:
            nguoi_ky.append({"nguoi_ky": nguoi_ky_tai_khoan, "thu_tu": len(nguoi_ky) + 1})
        return {"cap_ky": thu_tu, "ten_cap_ky": f"Cấp {thu_tu}", "thu_tu": thu_tu, "nguoi_ky": nguoi_ky}

    def create(self, ma, cap_ky):
        return process_service.tao_quy_trinh(
            self.u1, ma_quy_trinh=ma, ten_quy_trinh="Quy trình", pham_vi=enums.PhamViQuyTrinh.CONG_TY, cap_ky=cap_ky,
        )

    def test_hop_le_cap_sau_cao_hon_cap_truoc(self):
        p = self.create("QT_TB_TANG_DAN", [
            self._cap(1, chuc_vu_id=self.truong_phong.pk),
            self._cap(2, chuc_vu_id=self.pho_giam_doc.pk),
            self._cap(3, chuc_vu_id=self.giam_doc.pk),
        ])
        self.assertEqual(p.cap_ky_set.count(), 3)

    def test_hop_le_cap_sau_cung_chuc_vu(self):
        p = self.create("QT_TB_BANG", [
            self._cap(1, chuc_vu_id=self.pho_giam_doc.pk),
            self._cap(2, chuc_vu_id=self.pho_giam_doc.pk),
        ])
        self.assertEqual(p.cap_ky_set.count(), 2)

    def test_vi_pham_cap_sau_thap_hon_cap_truoc_bi_chan(self):
        with self.assertRaises(SigningError) as ctx:
            self.create("QT_TB_VI_PHAM", [
                self._cap(1, chuc_vu_id=self.giam_doc.pk),
                self._cap(2, chuc_vu_id=self.truong_phong.pk),
            ])
        self.assertEqual(ctx.exception.get_codes(), "cap_ky_thu_bac_khong_hop_le")
        self.assertEqual(ctx.exception.fields, {"cap_ky": [{"thu_tu": 2, "thu_tu_truoc": 1}]})
        # Toàn bộ quy trình không được tạo khi vi phạm thứ bậc (kiểm tra trước khi ghi).
        self.assertFalse(SigningProcess.objects.filter(ma_quy_trinh="QT_TB_VI_PHAM").exists())

    def test_bien_chi_mot_cap_khong_bi_rang_buoc(self):
        p = self.create("QT_TB_MOT_CAP", [self._cap(1, chuc_vu_id=self.truong_phong.pk)])
        self.assertEqual(p.cap_ky_set.count(), 1)

    def test_bien_sua_lai_chuc_vu_cap_1_sau_khi_da_co_cap_2(self):
        """Quy trình đang hợp lệ (cấp 1 thấp, cấp 2 cao hơn); sửa lại cấp 1 lên cao hơn cấp 2 phải bị chặn và
        giữ nguyên dữ liệu cũ (không xóa cấp ký đang có trước khi kiểm tra xong)."""
        p = self.create("QT_TB_SUA_CAP_1", [
            self._cap(1, chuc_vu_id=self.truong_phong.pk),
            self._cap(2, chuc_vu_id=self.pho_giam_doc.pk),
        ])
        with self.assertRaises(SigningError) as ctx:
            process_service.sua_quy_trinh(
                p, self.u1, ten_quy_trinh=p.ten_quy_trinh, pham_vi=p.pham_vi,
                cap_ky=[
                    self._cap(1, chuc_vu_id=self.giam_doc.pk),  # cấp 1 đổi lên cao hơn cấp 2 hiện có
                    self._cap(2, chuc_vu_id=self.pho_giam_doc.pk),
                ],
            )
        self.assertEqual(ctx.exception.get_codes(), "cap_ky_thu_bac_khong_hop_le")
        self.assertEqual(SigningProcessStep.objects.filter(quy_trinh=p).count(), 2)
        self.assertEqual(
            SigningProcessStep.objects.get(quy_trinh=p, thu_tu=1).nguoi_ky_set.get().chuc_vu_id,
            self.truong_phong.pk,
        )

    def test_nguoi_ky_theo_tai_khoan_khong_bi_rang_buoc_thu_bac(self):
        """Người ký chọn đích danh theo tài khoản (không chuc_vu_id) không tham gia so sánh thứ bậc."""
        p = self.create("QT_TB_DICH_DANH", [
            self._cap(1, chuc_vu_id=self.giam_doc.pk),
            self._cap(2, nguoi_ky_tai_khoan=self.u2),
        ])
        self.assertEqual(p.cap_ky_set.count(), 2)

    def test_song_ky_so_voi_chuc_vu_cao_nhat_trong_cap(self):
        """Một cấp có nhiều người ký theo nhiều chức vụ (song ký): cấp sau phải cao hơn hoặc bằng chức vụ
        CAO NHẤT trong cấp trước, không phải chức vụ thấp nhất."""
        with self.assertRaises(SigningError) as ctx:
            self.create("QT_TB_SONG_KY", [
                self._cap(1, chuc_vu_id=self.giam_doc.pk, them=[{"chuc_vu_id": self.truong_phong.pk, "thu_tu": 9}]),
                self._cap(2, chuc_vu_id=self.pho_giam_doc.pk),
            ])
        self.assertEqual(ctx.exception.get_codes(), "cap_ky_thu_bac_khong_hop_le")
