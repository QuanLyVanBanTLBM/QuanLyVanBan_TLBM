"""
Lõi Phase 9 (#80): trả lại để sửa → trao đổi → tải bản mới → lượt mới, mọi cấp ký lại.
"""

import hashlib
import os
import shutil
import tempfile
import unittest
from unittest import mock

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TransactionTestCase, override_settings

from signing.models import (
    SigningAttempt, SigningAuditLog, SigningChangeThread, SigningRequestStep, SigningSignature,
)
from signing.services import hanh_dong_ky as hanh_dong_service
from signing.services import process as process_service
from signing.services import trinh_ky as trinh_ky_service
from signing.services import yeu_cau_sua as yeu_cau_sua_service

from .helpers import cap_quyen
from .test_hanh_dong_ky_phase8 import HASH, KyBase, chay_song_song, khoa_hoat_dong, ky_so, ma_loi
from .test_trinh_ky_phase7 import BASE, PDF, VAN_BAN, tep_pdf

User = get_user_model()
PDF_SUA = PDF + b"% ban da sua\n"
HASH_SUA = hashlib.sha256(PDF_SUA).hexdigest()


class YeuCauSuaTests(KyBase):
    def yeu_cau_sua(self, user, khoa="ycs", **body):
        body = {"tieu_de": "Sai số liệu", "ly_do": "Mục 2 sai tổng tiền", **body}
        return self.hanh_dong(user, "yeu-cau-sua", khoa, **body)

    def tin_nhan(self, user, noi_dung):
        return self.client_cua(User.objects.get(pk=user.pk)).post(
            f"{BASE}/{self.pk}/trao-doi/", {"noi_dung": noi_dung}, format="json")

    def giai_quyet(self, user=None, khoa="gq", noi_dung=PDF_SUA):
        client = self.client_cua(User.objects.get(pk=(user or self.tao).pk))
        return client.post(f"{BASE}/{self.pk}/giai-quyet/", {"tep": tep_pdf(noi_dung)}, format="multipart",
                           HTTP_IDEMPOTENCY_KEY=khoa)

    def ky_ban_sua(self, user):
        private, _ = self.khoa[user.pk]
        return self.ky(user, hash_tai_lieu=HASH_SUA, chu_ky_so=ky_so(private, HASH_SUA))

    def test_return_at_later_level_then_full_resign(self):
        self.ky(self.ky1)
        self.ky(self.ky2)  # cấp 1 xong, cấp 2 (giám đốc) mở
        r = self.yeu_cau_sua(self.ky3)
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual((r.data["trang_thai"], r.data["luot_trinh"][0]["trang_thai"]), ("CHO_KY", "YEU_CAU_SUA"))
        cap2, gd = self.nguoi_ky(r.data, "giam_doc")
        self.assertEqual((cap2["trang_thai"], gd["trang_thai"]), ("TAM_DUNG", "YEU_CAU_SUA"))
        self.assertEqual(r.data["dang_cho"], [])
        self.assertEqual(self.ky(self.ky3).data["code"], "luot_trinh_khong_cho_ky")  # không ai ký tiếp trên lượt

        self.assertEqual(self.tin_nhan(self.tao, "Đã sửa mục 2, nhờ anh xem").status_code, 201)
        self.assertEqual(self.tin_nhan(self.ky3, "Ok, gửi lại").status_code, 201)
        self.assertEqual(self.tin_nhan(self.ky1, "Tôi góp ý").status_code, 403)  # không phải hai bên trao đổi
        trao_doi = self.c.get(f"{BASE}/{self.pk}/trao-doi/").data
        self.assertEqual([t["noi_dung"] for t in trao_doi["tin_nhan"]], ["Đã sửa mục 2, nhờ anh xem", "Ok, gửi lại"])
        self.assertEqual(trao_doi["thread"]["tieu_de"], "Sai số liệu")

        r = self.giai_quyet()
        self.assertEqual(r.status_code, 200, r.data)
        moi, cu = r.data["luot_trinh"][0], r.data["luot_trinh"][1]
        self.assertEqual((moi["so_luot"], moi["luot_truoc"], moi["trang_thai"]), (2, cu["id"], "CHO_KY"))
        self.assertEqual((moi["ma_bam_tai_lieu"], r.data["phien_ban_van_ban"]), (HASH_SUA, "2"))
        self.assertEqual((cu["trang_thai"], cu["yeu_cau_sua"][0]["trang_thai"]), ("YEU_CAU_SUA", "DA_GIAI_QUYET"))
        self.assertEqual([c["trang_thai"] for c in moi["cap_ky"]], ["DANG_KY", "CHUA_MO"])
        self.assertTrue(all(n["chu_ky"] is None for c in moi["cap_ky"] for n in c["nguoi_ky"]))

        self.assertEqual(self.ky(self.ky1).data["code"], "ma_bam_khong_khop")  # chữ ký trên tệp cũ bị từ chối
        for user in (self.ky1, self.ky2, self.ky3):
            r = self.ky_ban_sua(user)
            self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data["trang_thai"], "HOAN_THANH")
        self.assertEqual(SigningSignature.objects.filter(luot_trinh__so_luot=1).count(), 2)  # bằng chứng lượt cũ
        self.assertEqual(SigningSignature.objects.filter(luot_trinh__so_luot=2, hash_tai_lieu=HASH_SUA).count(), 3)
        hanh_dong = list(SigningAuditLog.objects.filter(trinh_ky_id=self.pk).values_list("hanh_dong", flat=True))
        i = hanh_dong.index("GIAI_QUYET_YEU_CAU_SUA")
        self.assertEqual((hanh_dong[i - 1], hanh_dong[i + 1]), ("YEU_CAU_SUA", "MO_CAP_KY"))

    def test_rules(self):
        r = self.yeu_cau_sua(self.ky1, tieu_de="")
        self.assertEqual((r.status_code, r.data["code"]), (400, "du_lieu_khong_hop_le"))
        r = self.yeu_cau_sua(self.ky2)  # ký chính chưa mở
        self.assertEqual((r.status_code, r.data["code"]), (409, "chua_den_luot_ky"))
        r = self.giai_quyet()
        self.assertEqual((r.status_code, r.data["code"]), (409, "khong_co_yeu_cau_sua_dang_mo"))
        self.assertEqual(self.tin_nhan(self.tao, "x").data["code"], "khong_co_trao_doi_dang_mo")
        self.yeu_cau_sua(self.ky1)
        cap_quyen(self.ky1, "send_trinhky")
        r = self.giai_quyet(user=self.ky1)  # không phải người tạo
        self.assertEqual((r.status_code, r.data["code"]), (403, "khong_co_quyen"))
        r = self.giai_quyet(noi_dung=b"khong phai pdf")
        self.assertEqual((r.status_code, r.data["code"]), (400, "tep_khong_phai_pdf"))
        User.objects.filter(pk=self.ky3.pk).update(is_active=False)
        so_tep = sum(len(f) for _, _, f in os.walk(self.thu_muc))
        r = self.giai_quyet()
        self.assertEqual((r.status_code, r.data["code"]), (400, "khong_xac_dinh_duoc_nguoi_ky"))
        self.assertEqual(sum(len(f) for _, _, f in os.walk(self.thu_muc)), so_tep)  # chưa lưu tệp khi lỗi
        self.assertEqual(SigningChangeThread.objects.get().trang_thai, "DANG_MO")  # lỗi không làm đổi trạng thái

    def test_resolve_is_idempotent_and_cancel_closes_conversation(self):
        self.yeu_cau_sua(self.ky1)
        r = self.giai_quyet(khoa=f"gui-{self.pk}")  # khóa của lần gửi: không được coi là giải quyết lặp
        self.assertEqual((r.status_code, r.data["code"]), (409, "khoa_chong_trung_da_dung"))
        self.assertEqual(SigningAttempt.objects.filter(trinh_ky_id=self.pk).count(), 1)
        self.assertEqual(self.giai_quyet(khoa="lap").status_code, 200)
        self.assertEqual(self.giai_quyet(khoa="lap").status_code, 200)
        self.assertEqual(SigningAttempt.objects.filter(trinh_ky_id=self.pk).count(), 2)
        self.yeu_cau_sua(self.ky1, khoa="ycs-2")
        self.c.post(f"{BASE}/{self.pk}/huy/", {}, format="json", HTTP_IDEMPOTENCY_KEY="huy")
        self.assertEqual(self.tin_nhan(self.tao, "còn sửa không?").data["code"], "khong_co_trao_doi_dang_mo")
        self.assertEqual(self.giai_quyet(khoa="gq-2").data["code"], "khong_co_yeu_cau_sua_dang_mo")


@unittest.skipUnless(connection.vendor == "postgresql", "Cần PostgreSQL để kiểm tra khóa dòng đồng thời")
@override_settings(SIGNING_PIN_SECRET="bi-mat-test")
class TraSuaDongThoiTests(TransactionTestCase):
    """Hai người cùng cấp thao tác cùng lúc: không có chữ ký nào được ghi trên lượt đã dừng."""

    def setUp(self):
        thu_muc = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, thu_muc, ignore_errors=True)
        cai_dat = override_settings(SIGNING_DOCUMENT_ROOT=thu_muc)
        cai_dat.enable()
        self.addCleanup(cai_dat.disable)
        van_ban = mock.patch("signing.tich_hop.van_ban._doc_van_ban_di", side_effect=VAN_BAN.get)
        van_ban.start()
        self.addCleanup(van_ban.stop)
        self.tao = User.objects.create_user("tao")
        self.ky1 = User.objects.create_user("ky1")
        self.ky2 = User.objects.create_user("ky2")
        cap_quyen(self.tao, "add_trinhky", "send_trinhky", "view_vanbandi")
        qt = process_service.tao_quy_trinh(self.tao, ma_quy_trinh="DT", ten_quy_trinh="DT", pham_vi="CONG_TY", cap_ky=[
            {"cap_ky": 1, "ten_cap_ky": "C", "thu_tu": 1, "nguoi_ky": [
                {"nguoi_ky": self.ky1, "thu_tu": 1}, {"nguoi_ky": self.ky2, "thu_tu": 2}]}])
        qt = process_service.kich_hoat(qt, self.tao)
        ho_so = trinh_ky_service.tao_nhap(self.tao, document_type="vanbandi", van_ban_id=10, quy_trinh=qt,
                                          muc_do="THUONG", tep=tep_pdf())
        self.ho_so = trinh_ky_service.gui(ho_so, self.tao, khoa_chong_trung="g")
        self.private, self.key = khoa_hoat_dong(self.ky1, "K-DT")

    def tra_sua(self):
        yeu_cau_sua_service.yeu_cau_sua(self.ho_so, self.ky2, tieu_de="Sửa", ly_do="Sai", khoa_chong_trung="ycs")

    def kiem_luot_dung(self):
        luot = SigningAttempt.objects.get(trinh_ky=self.ho_so)
        cap = SigningRequestStep.objects.get(luot_trinh=luot)
        return luot.trang_thai, cap.trang_thai

    def test_sign_racing_return_never_signs_paused_attempt(self):
        loi = chay_song_song(
            lambda: hanh_dong_service.ky(self.ho_so, self.ky1, khoa_ky=self.key.pk, hash_tai_lieu=HASH,
                                         chu_ky_so=ky_so(self.private), khoa_chong_trung="ky"),
            self.tra_sua,
        )
        self.assertEqual(self.kiem_luot_dung(), ("YEU_CAU_SUA", "TAM_DUNG"))
        # ký trước: chữ ký giữ làm lịch sử, trả sửa vẫn được; trả sửa trước: lượt ký bị chặn
        self.assertEqual(len(loi) + SigningSignature.objects.count(), 1)
        self.assertEqual([ma_loi(e) for e in loi], ["luot_trinh_khong_cho_ky"] * len(loi))

    def test_return_racing_reject_has_single_winner(self):
        loi = chay_song_song(
            lambda: hanh_dong_service.tu_choi(self.ho_so, self.ky1, ly_do_tu_choi="Không", khoa_chong_trung="tc"),
            self.tra_sua,
        )
        self.assertEqual([ma_loi(e) for e in loi], ["luot_trinh_khong_cho_ky"])
        trang_thai = self.kiem_luot_dung()
        self.assertIn(trang_thai[0], ("YEU_CAU_SUA", "TU_CHOI"))
        self.assertEqual(SigningChangeThread.objects.count(), int(trang_thai[0] == "YEU_CAU_SUA"))
