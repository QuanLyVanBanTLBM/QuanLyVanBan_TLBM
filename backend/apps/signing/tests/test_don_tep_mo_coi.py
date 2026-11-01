"""Xóa và dọn tệp mồ côi của kho lưu trữ Trình ký (Issue #453)."""
import io
import os
import time
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from PIL import Image

from signing.models import SigningUserSignature
from signing.services import tep_hoan_tat
from signing.storage import THU_MUC_ANH_CA_NHAN, StorageError, get_storage

from .helpers import cap_quyen
from .test_hoan_tat_phase10 import HoanTatBase
from .test_trinh_ky_phase7 import TrinhKyBase

User = get_user_model()
BASE = "/api/v1/signing/anh-chu-ky-ca-nhan"


def _png(color):
    buf = io.BytesIO()
    Image.new("RGBA", (80, 30), color).save(buf, format="PNG")
    return buf.getvalue()


def _tai_len(client, color):
    tep = SimpleUploadedFile("chuky.png", _png(color), content_type="image/png")
    return client.post(f"{BASE}/", {"tep": tep}, format="multipart")


def _doc_duoc(vi_tri):
    try:
        get_storage().read_bytes(vi_tri)
    except StorageError:
        return False
    return True


class XoaTepStorageTests(TrinhKyBase):
    def test_xoa_tep_va_tep_khong_ton_tai(self):
        storage = get_storage()
        meta = storage.save_bytes(b"x", "thu_nghiem", "bin")
        self.assertTrue(storage.delete(meta.vi_tri_luu_tep))
        self.assertFalse(storage.delete(meta.vi_tri_luu_tep))
        self.assertFalse(_doc_duoc(meta.vi_tri_luu_tep))

    def test_tu_choi_vi_tri_ngoai_thu_muc_goc(self):
        storage = get_storage()
        for vi_tri in ("", "../ngoai.bin", "/etc/hostname", "."):
            with self.subTest(vi_tri=vi_tri), self.assertRaises(StorageError):
                storage.delete(vi_tri)


class AnhCaNhanXoaTepTests(TrinhKyBase):
    def setUp(self):
        super().setUp()
        self.u = User.objects.create_user("user_anh_1")
        cap_quyen(self.u, "sign_trinhky", "view_trinhky")
        self.client_u = self.client_cua(self.u)

    def _vi_tri(self):
        return SigningUserSignature.objects.get(nguoi_dung=self.u).vi_tri_tep

    def test_ghi_de_anh_xoa_tep_cu(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(_tai_len(self.client_u, (0, 0, 200, 255)).status_code, 200)
        cu = self._vi_tri()
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(_tai_len(self.client_u, (200, 0, 0, 255)).status_code, 200)
        moi = self._vi_tri()
        self.assertNotEqual(cu, moi)
        self.assertFalse(_doc_duoc(cu))
        self.assertTrue(_doc_duoc(moi))

    def test_lay_thong_tin_sau_khi_co_anh(self):
        with self.captureOnCommitCallbacks(execute=True):
            _tai_len(self.client_u, (0, 0, 200, 255))
        res = self.client_u.get(f"{BASE}/")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.data["co_anh"])

    def test_xoa_anh_xoa_tep(self):
        with self.captureOnCommitCallbacks(execute=True):
            _tai_len(self.client_u, (0, 0, 200, 255))
        vi_tri = self._vi_tri()
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.client_u.delete(f"{BASE}/").status_code, 204)
        self.assertFalse(SigningUserSignature.objects.filter(nguoi_dung=self.u).exists())
        self.assertFalse(_doc_duoc(vi_tri))

    def test_xoa_khi_chua_co_anh_van_204(self):
        self.assertEqual(self.client_u.delete(f"{BASE}/").status_code, 204)


class TepHoanTatBoKetQuaTests(HoanTatBase):
    def test_ket_thuc_bo_ket_qua_xoa_tep_vua_ghi(self):
        luot = self.ky_het()  # lượt đã THANH_CONG: kết quả đến sau bị bỏ
        meta = get_storage().save_bytes(b"%PDF-vua-ghi", tep_hoan_tat.THU_MUC, "pdf")
        with self.captureOnCommitCallbacks(execute=True):
            tep_hoan_tat._ket_thuc(luot.pk, self.ky3.pk, vi_tri=meta.vi_tri_luu_tep, ma_bam="a" * 64)
        self.assertFalse(_doc_duoc(meta.vi_tri_luu_tep))
        luot.refresh_from_db()
        self.assertNotEqual(luot.vi_tri_tep_hoan_tat, meta.vi_tri_luu_tep)
        self.assertTrue(_doc_duoc(luot.vi_tri_tep_hoan_tat))  # tệp hoàn tất đã có vẫn giữ nguyên


class DonTepMoCoiCommandTests(TrinhKyBase):
    def setUp(self):
        super().setUp()
        self.u = User.objects.create_user("user_anh_2")
        cap_quyen(self.u, "sign_trinhky", "view_trinhky")
        self.client_u = self.client_cua(self.u)

    def _cu_hoa(self, vi_tri, gio=48):
        path = os.path.join(self.thu_muc, vi_tri)
        t = time.time() - gio * 3600
        os.utime(path, (t, t))

    def _chay(self, *args):
        out = StringIO()
        call_command("don_tep_mo_coi", *args, stdout=out)
        return out.getvalue()

    def test_liet_ke_mac_dinh_va_xoa_khi_co_co(self):
        with self.captureOnCommitCallbacks(execute=True):
            _tai_len(self.client_u, (0, 0, 200, 255))
        dang_dung = SigningUserSignature.objects.get(nguoi_dung=self.u).vi_tri_tep
        mo_coi = get_storage().save_bytes(b"mo-coi", THU_MUC_ANH_CA_NHAN, "png").vi_tri_luu_tep
        moi = get_storage().save_bytes(b"moi-ghi", THU_MUC_ANH_CA_NHAN, "png").vi_tri_luu_tep
        for vi_tri in (dang_dung, mo_coi):
            self._cu_hoa(vi_tri)

        ra = self._chay()
        self.assertIn(mo_coi, ra)
        self.assertNotIn(dang_dung, ra)
        self.assertNotIn(moi, ra)
        self.assertTrue(_doc_duoc(mo_coi))  # mặc định chỉ liệt kê

        self._chay("--xoa")
        self.assertFalse(_doc_duoc(mo_coi))
        self.assertTrue(_doc_duoc(dang_dung))  # còn bản ghi tham chiếu
        self.assertTrue(_doc_duoc(moi))  # chưa đủ tuổi
