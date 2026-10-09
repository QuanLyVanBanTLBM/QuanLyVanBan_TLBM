"""
Phần còn lại của #80: quy trình theo đơn vị (mục A), vị trí ký chụp vào lượt trình (mục A), snapshot ảnh chữ ký
lúc ký và khối chữ ký trên tệp hoàn tất (mục D), tìm tài khoản để cấu hình người ký.
"""

import io
import json
from unittest import mock

from django.contrib.auth import get_user_model
from pypdf import PdfReader

from signing.models import SigningProcessStepSigner, SigningRequestStepSigner, SigningSignature
from signing.services import process as process_service
from signing.storage import get_storage

from .helpers import cap_quyen
from .test_hanh_dong_ky_phase8 import KyBase, ky_so
from .test_hoan_tat_phase10 import HoanTatBase
from .test_trinh_ky_phase7 import BASE, TrinhKyBase, pdf_mau, tep_pdf

User = get_user_model()
QT = "/api/v1/signing/quy-trinh"


def anh_png():
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGBA", (80, 30), (0, 0, 200, 255)).save(buf, format="PNG")
    return buf.getvalue()


class PhamViQuyTrinhTests(TrinhKyBase):
    """Quy trình CONG_TY do quản trị; PHONG_BAN do lãnh đạo đơn vị áp dụng hoặc quản trị (#80 mục A)."""

    def setUp(self):
        super().setUp()
        self.quan_tri = User.objects.create_user("quan_tri")
        self.tp = User.objects.create_user("truong_phong")
        self.cv6 = User.objects.create_user("cv_don_vi_6")
        cap_quyen(self.quan_tri, "manage_signing_process", "view_trinhky")
        cap_quyen(self.tp, "manage_signing_process", "view_trinhky")
        cap_quyen(self.tao, "view_trinhky")
        cap_quyen(self.cv6, "view_trinhky", "add_trinhky", "view_vanbandi")
        ma_nhom = {self.quan_tri.pk: {"ADMIN"}, self.tp.pk: {"TP"}}
        don_vi = {self.tp.pk: 5, self.tao.pk: 5, self.cv6.pk: 6}
        for ten, bang in (("ma_nhom_cua", ma_nhom), ("don_vi_cua", don_vi)):
            vay = mock.patch(f"signing.tich_hop.to_chuc.{ten}", side_effect=lambda u, b=bang: b.get(u.pk, set()
                             if b is ma_nhom else None))
            vay.start()
            self.addCleanup(vay.stop)

    def tao_qt(self, user, ma, pham_vi, don_vi=None):
        body = {"ma_quy_trinh": ma, "ten_quy_trinh": ma, "pham_vi": pham_vi, "don_vi_ap_dung_id": don_vi,
                "cap_ky": [{"cap_ky": 1, "ten_cap_ky": "C", "thu_tu": 1, "nguoi_ky": [
                    {"nguoi_ky": self.ky1.pk, "thu_tu": 1}]}]}
        return self.client_cua(User.objects.get(pk=user.pk)).post(f"{QT}/", body, format="json")

    def kich_hoat(self, user, pk):
        return self.client_cua(User.objects.get(pk=user.pk)).post(f"{QT}/{pk}/kich-hoat/")

    def test_unit_is_required_for_department_scope_only(self):
        r = self.tao_qt(self.quan_tri, "PB-THIEU", "PHONG_BAN")
        self.assertEqual((r.status_code, r.data["code"]), (400, "quy_trinh_phong_ban_thieu_don_vi"))
        r = self.tao_qt(self.quan_tri, "CT-THUA", "CONG_TY", don_vi=5)
        self.assertEqual((r.status_code, r.data["code"]), (400, "quy_trinh_cong_ty_co_don_vi"))

    def test_management_by_scope_visibility_and_usage(self):
        self.assertEqual(self.tao_qt(self.tp, "CT-TP", "CONG_TY").status_code, 403)  # công ty: chỉ quản trị
        self.assertEqual(self.tao_qt(self.tp, "PB6-TP", "PHONG_BAN", 6).status_code, 403)  # đơn vị khác
        pb5 = self.tao_qt(self.tp, "PB5", "PHONG_BAN", 5)
        self.assertEqual(pb5.status_code, 201, pb5.data)
        self.assertEqual(self.kich_hoat(self.tp, pb5.data["id"]).status_code, 200)
        ct = self.tao_qt(self.quan_tri, "CT", "CONG_TY")
        self.assertEqual(self.kich_hoat(self.quan_tri, ct.data["id"]).status_code, 200)
        nhap5 = self.tao_qt(self.tp, "PB5-NHAP", "PHONG_BAN", 5).data["id"]
        self.assertEqual(self.kich_hoat(self.quan_tri, self.tao_qt(self.quan_tri, "PB6", "PHONG_BAN", 6).data["id"])
                         .status_code, 200)  # quản trị quản lý được quy trình phòng ban

        def ma_thay(user):
            data = self.client_cua(User.objects.get(pk=user.pk)).get(f"{QT}/").data
            return {q["ma_quy_trinh"] for q in data}
        self.assertTrue({"CT", "PB5"} <= ma_thay(self.tao))
        self.assertFalse({"PB6", "PB5-NHAP"} & ma_thay(self.tao))  # không thấy phòng khác, không thấy nháp
        self.assertTrue({"CT", "PB6"} <= ma_thay(self.cv6) and "PB5" not in ma_thay(self.cv6))
        self.assertIn("PB5-NHAP", ma_thay(self.tp))  # lãnh đạo thấy mọi trạng thái quy trình đơn vị mình
        self.assertIn("PB6", ma_thay(self.quan_tri))
        self.assertEqual(self.client_cua(User.objects.get(pk=self.tao.pk)).get(f"{QT}/{nhap5}/").status_code, 404)

        r = self.client_cua(User.objects.get(pk=self.cv6.pk)).post(f"{BASE}/", {
            "document_type": "vanbandi", "van_ban_id": 10, "quy_trinh": pb5.data["id"], "muc_do": "THUONG",
            "tep": tep_pdf()}, format="multipart")
        self.assertEqual((r.status_code, r.data["code"]), (403, "quy_trinh_khong_ap_dung"))
        r = self.tao_nhap(quy_trinh=pb5.data["id"])  # người tạo cùng đơn vị 5
        self.assertEqual(r.status_code, 201, r.data)

    def test_clone_keeps_unit(self):
        pb5 = self.tao_qt(self.tp, "PB5-NB", "PHONG_BAN", 5).data
        moi = process_service.nhan_ban(process_service.SigningProcess.objects.get(pk=pb5["id"]), self.tp)
        self.assertEqual((moi.pham_vi, moi.don_vi_ap_dung_id), ("PHONG_BAN", 5))

    def test_user_lookup_for_process_configuration(self):
        c = self.client_cua(User.objects.get(pk=self.quan_tri.pk))
        r = c.get("/api/v1/signing/nguoi-dung/", {"q": "ke_t"})
        self.assertEqual([u["ten_dang_nhap"] for u in r.data], ["ke_toan"])
        self.assertEqual(set(r.data[0]), {"id", "ten", "ten_dang_nhap", "chuc_vu", "don_vi_id"})
        self.assertEqual(self.c.get("/api/v1/signing/nguoi-dung/").status_code, 403)


class ViTriKyTests(TrinhKyBase):
    """Vị trí ký đặt lúc gửi, chụp vào lượt trình; tỷ lệ % theo trang, gốc trên-trái (#80 mục A)."""

    def cau_hinh(self):
        return {n.nguoi_ky_id: n.pk for n in SigningProcessStepSigner.objects.filter(
            buoc_quy_trinh__quy_trinh=self.process)}

    def test_positions_are_validated_and_snapshotted(self):
        pk = self.tao_nhap(tep=tep_pdf(pdf_mau(2))).data["id"]
        ch = self.cau_hinh()
        tot = {"trang_ky": 2, "toa_do_x": "60", "toa_do_y": "75", "chieu_rong_khung": "30", "chieu_cao_khung": "12"}
        r = self.gui(pk, khoa="v1", vi_tri_ky={str(ch[self.ky1.pk]): {**tot, "trang_ky": 3}})
        self.assertEqual((r.status_code, r.data["code"]), (400, "vi_tri_ky_khong_hop_le"))  # tệp chỉ có 2 trang
        r = self.gui(pk, khoa="v2", vi_tri_ky={"999999": tot})
        self.assertEqual(r.data["fields"]["vi_tri_ky"][0]["loai"], "khong_co_nguoi_ky")
        r = self.gui(pk, khoa="v3", vi_tri_ky={str(ch[self.ky1.pk]): {**tot, "toa_do_x": "80"}})
        self.assertEqual((r.status_code, r.data["code"]), (400, "du_lieu_khong_hop_le"))  # khung tràn khỏi trang
        r = self.gui(pk, khoa="v4", vi_tri_ky={str(ch[self.ky1.pk]): tot, str(ch[self.ky3.pk]): {**tot, "trang_ky": 1}})
        self.assertEqual(r.status_code, 200, r.data)
        dong = SigningRequestStepSigner.objects.get(buoc_ky__luot_trinh__trinh_ky_id=pk, nguoi_ky=self.ky1)
        self.assertEqual((dong.trang_ky, float(dong.toa_do_x), float(dong.chieu_cao_khung)), (2, 60.0, 12.0))
        n2 = SigningRequestStepSigner.objects.get(buoc_ky__luot_trinh__trinh_ky_id=pk, nguoi_ky=self.ky2)
        self.assertIsNone(n2.trang_ky)  # không đặt vị trí thì chỉ có tên trên trang phê duyệt
        _, nk = next((c, n) for c in r.data["luot_trinh"][0]["cap_ky"] for n in c["nguoi_ky"]
                     if n["ten_nguoi_ky"] == "ke_toan")
        self.assertEqual((nk["trang_ky"], nk["toa_do_y"]), (2, "75.0000"))


@mock.patch("signing.tich_hop.to_chuc.anh_chu_ky",
            side_effect=lambda u: anh_png() if u.username != "phap_che" else None)  # phap_che chưa có ảnh
class AnhChuKyTests(HoanTatBase):
    """Snapshot ảnh chữ ký lúc ký; tệp hoàn tất dán ảnh (hoặc khối chữ) vào đúng khung (#80 mục D)."""

    def setUp(self):
        super().setUp()
        tep = pdf_mau(2)
        self.pk = self.tao_nhap(tep=tep_pdf(tep)).data["id"]
        ch = {n.nguoi_ky_id: n.pk for n in SigningProcessStepSigner.objects.filter(
            buoc_quy_trinh__quy_trinh=self.process)}
        khung = {"toa_do_x": "55", "toa_do_y": "70", "chieu_rong_khung": "35", "chieu_cao_khung": "15"}
        self.gui(self.pk, khoa="anh", vi_tri_ky={str(ch[self.ky1.pk]): {"trang_ky": 1, **khung},
                                                 str(ch[self.ky2.pk]): {"trang_ky": 1, **khung, "toa_do_y": "50"},
                                                 str(ch[self.ky3.pk]): {"trang_ky": 2, **khung}})
        import hashlib
        self.hash = hashlib.sha256(tep).hexdigest()

    def ky_tep(self, user):
        private, key = self.khoa[user.pk]
        return self.ky(user, hash_tai_lieu=self.hash, chu_ky_so=ky_so(private, self.hash))

    def test_snapshot_overlay_and_stamped_result(self, _anh):
        self.ky_tep(self.ky1)
        self.ky_tep(self.ky2)
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.ky_tep(self.ky3).status_code, 200)
        ck1 = SigningSignature.objects.get(buoc_ky__nguoi_ky=self.ky1)
        self.assertTrue(ck1.vi_tri_anh_chu_ky.startswith("anh_chu_ky/"))
        self.assertEqual(SigningSignature.objects.get(buoc_ky__nguoi_ky=self.ky2).vi_tri_anh_chu_ky, "")  # chưa có ảnh
        r = self.c.get(f"{BASE}/{self.pk}/anh-chu-ky/{ck1.pk}/")
        self.assertEqual((r.status_code, r["Content-Type"], r.content), (200, "image/png", anh_png()))
        self.assertEqual(self.client_cua(self.la).get(f"{BASE}/{self.pk}/anh-chu-ky/{ck1.pk}/").status_code, 404)
        d = self.c.get(f"{BASE}/{self.pk}/").data
        self.assertEqual(d["luot_trinh"][0]["trang_thai_tep_hoan_tat"], "THANH_CONG")
        bc = self.c.get(f"{BASE}/{self.pk}/bang-chung/").data
        self.assertTrue(bc["xac_minh"]["hop_le"])
        nk = [n for c in bc["noi_dung_chuan_hoa"]["cap_ky"] for n in c["nguoi_ky"]]
        self.assertEqual(nk[0]["vi_tri"], {"trang_ky": 1, "toa_do_x": "55.0000", "toa_do_y": "70.0000",
                                           "chieu_rong_khung": "35.0000", "chieu_cao_khung": "15.0000"})
        self.assertEqual(nk[0]["chu_ky"]["ma_bam_anh_chu_ky"], ck1.ma_bam_anh_chu_ky)
        self.assertIsNone(nk[1]["chu_ky"]["ma_bam_anh_chu_ky"])

        pdf = PdfReader(io.BytesIO(self.c.get(f"{BASE}/{self.pk}/tep-hoan-tat/").content))
        self.assertEqual(len(pdf.pages), 3)  # 2 trang gốc + trang phê duyệt
        trang1, trang2 = pdf.pages[0].extract_text(), pdf.pages[1].extract_text()
        self.assertIn("ke_toan", trang1)  # chú thích dưới ảnh chữ ký
        self.assertIn("phap_che", trang1)  # khối chữ khi chưa có ảnh
        self.assertIn("giam_doc", trang2)
        self.assertNotIn("giam_doc", trang1)
        self.assertIn("/XObject", str(pdf.pages[0]["/Resources"]))  # ảnh đã dán
        self.assertEqual(json.loads(pdf.attachments[f"bang-chung-{d['luot_trinh'][0]['id']}.json"][0]),
                         bc["noi_dung_chuan_hoa"])

    def test_tampered_signature_image_fails_verification(self, _anh):
        self.ky_tep(self.ky1)
        ck1 = SigningSignature.objects.get(buoc_ky__nguoi_ky=self.ky1)
        with open(get_storage()._resolve(ck1.vi_tri_anh_chu_ky), "ab") as f:
            f.write(b"x")
        self.assertEqual(self.c.get(f"{BASE}/{self.pk}/anh-chu-ky/{ck1.pk}/").data["code"], "anh_chu_ky_bi_thay_doi")
        self.ky_tep(self.ky2)
        with self.captureOnCommitCallbacks(execute=True):
            self.ky_tep(self.ky3)
        d = self.c.get(f"{BASE}/{self.pk}/").data["luot_trinh"][0]
        self.assertEqual((d["trang_thai_tep_hoan_tat"], d["loi_tep_hoan_tat"]), ("LOI", "anh_chu_ky_khong_khop"))
        xm = self.c.get(f"{BASE}/{self.pk}/bang-chung/").data["xac_minh"]
        self.assertEqual((xm["chu_ky"][0]["anh_chu_ky_khop"], xm["hop_le"]), (False, False))


class GiaiQuyetViTriTests(KyBase):
    """Lượt mới sau trả sửa chép vị trí ký, cho đặt lại; tệp mới ít trang hơn thì báo lỗi rõ (#80 mục A, C)."""

    def setUp(self):
        TrinhKyBase.setUp(self)
        from .test_hanh_dong_ky_phase8 import khoa_hoat_dong
        self.khoa = {}
        for user in (self.ky1, self.ky2, self.ky3):
            cap_quyen(user, "sign_trinhky")
            self.khoa[user.pk] = khoa_hoat_dong(user, f"K-{user.username}")
        self.pk = self.tao_nhap(tep=tep_pdf(pdf_mau(2))).data["id"]
        ch = {n.nguoi_ky_id: n.pk for n in SigningProcessStepSigner.objects.filter(
            buoc_quy_trinh__quy_trinh=self.process)}
        self.gui(self.pk, khoa="gq-vt", vi_tri_ky={str(ch[self.ky1.pk]): {
            "trang_ky": 2, "toa_do_x": "10", "toa_do_y": "10", "chieu_rong_khung": "20", "chieu_cao_khung": "10"}})

    def giai_quyet(self, tep, khoa, vi_tri_ky=None):
        body = {"tep": tep_pdf(tep)}
        if vi_tri_ky is not None:
            body["vi_tri_ky"] = json.dumps(vi_tri_ky)
        return self.c.post(f"{BASE}/{self.pk}/giai-quyet/", body, format="multipart", HTTP_IDEMPOTENCY_KEY=khoa)

    def test_positions_carry_over_and_can_be_reset(self):
        self.hanh_dong(self.ky1, "yeu-cau-sua", "ycs", tieu_de="Sửa", ly_do="Sai")
        dong_cu = SigningRequestStepSigner.objects.get(buoc_ky__luot_trinh__so_luot=1, nguoi_ky=self.ky1)
        r = self.giai_quyet(pdf_mau(1), "gq-1")  # vị trí cũ ở trang 2, tệp mới chỉ 1 trang
        self.assertEqual((r.status_code, r.data["code"]), (400, "vi_tri_ky_khong_hop_le"))
        r = self.giai_quyet(pdf_mau(1), "gq-2", {str(dong_cu.pk): {
            "trang_ky": 1, "toa_do_x": "50", "toa_do_y": "80", "chieu_rong_khung": "30", "chieu_cao_khung": "10"}})
        self.assertEqual(r.status_code, 200, r.data)
        moi = SigningRequestStepSigner.objects.get(buoc_ky__luot_trinh__so_luot=2, nguoi_ky=self.ky1)
        self.assertEqual((moi.trang_ky, float(moi.toa_do_x)), (1, 50.0))


class HoTroGiaoDienTests(TrinhKyBase):
    def test_current_user_permissions_and_document_lookup(self):
        r = self.c.get("/api/v1/signing/toi/")
        self.assertEqual((r.data["id"], r.data["ten"]), (self.tao.pk, "chuyen_vien"))
        self.assertEqual({k for k, v in r.data["quyen"].items() if v}, {"add_trinhky", "send_trinhky"})
        self.assertFalse(r.data["la_quan_tri"])
        self.assertEqual(self.c.get("/api/v1/signing/van-ban-di/", {"q": "QD"}).status_code, 200)
        self.assertEqual(self.client_cua(self.la).get("/api/v1/signing/van-ban-di/").status_code, 403)
        d = self.c.get(f"{BASE}/{self.tao_nhap().data['id']}/").data
        self.assertEqual((d["ten_nguoi_tao"], d["van_ban"]),
                         ("chuyen_vien", {"so_hieu": "10/QD", "trich_yeu": "Mua sắm"}))
