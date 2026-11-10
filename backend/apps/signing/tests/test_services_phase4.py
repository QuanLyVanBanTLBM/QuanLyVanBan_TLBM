from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.models import Position
from signing import enums
from signing.errors import ConflictError, SigningError
from signing.models import SigningAuditLog, SigningProcess, SigningProcessStepSigner
from signing.services import process as process_service

from .helpers import tao_chuc_vu

User = get_user_model()


class ProcessServiceTests(TestCase):
    def setUp(self):
        self.u1 = User.objects.create_user("u1")
        self.u2 = User.objects.create_user("u2")
        self.position = Position.objects.create(
            display_order=Position.get_next_display_order(), name="Trưởng phòng"
        )

    def create(self, ma="QT1", cap_ky=None):
        cap_ky = cap_ky if cap_ky is not None else [
            {"cap_ky": 1, "ten_cap_ky": "Cấp 1", "thu_tu": 1,
             "nguoi_ky": [{"nguoi_ky": self.u2, "thu_tu": 1}]},
            {"cap_ky": 2, "ten_cap_ky": "Cấp 2", "thu_tu": 2,
             "nguoi_ky": [{"chuc_vu_id": self.position.pk, "thu_tu": 1}]},
        ]
        return process_service.tao_quy_trinh(
            self.u1, ma_quy_trinh=ma, ten_quy_trinh="Quy trình", pham_vi=enums.PhamViQuyTrinh.CONG_TY, cap_ky=cap_ky,
        )

    def actions(self, process):
        return list(SigningAuditLog.objects.filter(loai_doi_tuong="signing_process", ma_doi_tuong=process.pk)
                    .order_by("id").values_list("hanh_dong", flat=True))

    def test_create_draft_with_steps_and_default_reminder(self):
        p = self.create()
        self.assertEqual(p.trang_thai, enums.TrangThaiQuyTrinh.NHAP)
        self.assertEqual(p.phien_ban, 1)
        self.assertEqual(p.cap_ky_set.count(), 2)
        self.assertEqual(p.cau_hinh_nhac_han, {"truoc_han_gio": [24], "dung_han": True})
        self.assertIn("TAO_QUY_TRINH", self.actions(p))

    def test_missing_reference_ids_are_rejected_by_service_before_writes(self):
        with self.assertRaises(SigningError) as ctx:
            process_service.tao_quy_trinh(
                self.u1,
                ma_quy_trinh="QT_MISSING_UNIT",
                ten_quy_trinh="Quy trình",
                pham_vi=enums.PhamViQuyTrinh.PHONG_BAN,
                don_vi_ap_dung_id=987654321,
                cap_ky=[],
            )
        self.assertEqual(ctx.exception.get_codes(), "don_vi_khong_ton_tai")
        self.assertIn("don_vi_ap_dung_id", ctx.exception.fields)
        self.assertFalse(SigningProcess.objects.filter(ma_quy_trinh="QT_MISSING_UNIT").exists())

        process = self.create("QT_STEP_UNIT", cap_ky=[])
        audit_count = SigningAuditLog.objects.count()
        with self.assertRaises(SigningError) as ctx:
            process_service.them_cap_ky(
                process, self.u1, cap_ky=1, ten_cap_ky="Cấp 1", thu_tu=1, don_vi_id=987654321
            )
        self.assertEqual(ctx.exception.get_codes(), "don_vi_khong_ton_tai")
        self.assertIn("don_vi_id", ctx.exception.fields)
        self.assertEqual(process.cap_ky_set.count(), 0)
        self.assertEqual(SigningAuditLog.objects.count(), audit_count)

        process = self.create("QT_SIGNER_POSITION", cap_ky=[
            {"cap_ky": 1, "ten_cap_ky": "Cấp 1", "thu_tu": 1},
        ])
        step = process.cap_ky_set.get()
        audit_count = SigningAuditLog.objects.count()
        with self.assertRaises(SigningError) as ctx:
            process_service.them_nguoi_ky(step, self.u1, thu_tu=1, chuc_vu_id=987654321)
        self.assertEqual(ctx.exception.get_codes(), "chuc_vu_khong_ton_tai")
        self.assertIn("chuc_vu_id", ctx.exception.fields)
        self.assertEqual(SigningProcessStepSigner.objects.filter(buoc_quy_trinh=step).count(), 0)
        self.assertEqual(SigningAuditLog.objects.count(), audit_count)

    def test_duplicate_code_rejected(self):
        self.create("QT1")
        with self.assertRaises(ConflictError) as ctx:
            self.create("QT1")
        self.assertEqual(ctx.exception.get_codes(), "quy_trinh_trung_ma")

    def test_signer_needs_exactly_one_of_person_or_position(self):
        with self.assertRaises(SigningError) as ctx:
            self.create("QT2", cap_ky=[{"cap_ky": 1, "ten_cap_ky": "C", "thu_tu": 1,
                                        "nguoi_ky": [{"thu_tu": 1}]}])
        self.assertEqual(ctx.exception.get_codes(), "nguoi_ky_hoac_chuc_vu")
        self.assertFalse(SigningProcess.objects.filter(ma_quy_trinh="QT2").exists())

    def test_duplicate_step_order_rejected(self):
        p = self.create()
        with self.assertRaises(ConflictError) as ctx:
            process_service.them_cap_ky(p, self.u1, cap_ky=3, ten_cap_ky="Trùng", thu_tu=1)
        self.assertEqual(ctx.exception.get_codes(), "cap_ky_trung_thu_tu")

    def test_cannot_activate_process_without_steps(self):
        p = self.create("QT3", cap_ky=[])
        with self.assertRaises(SigningError) as ctx:
            process_service.kich_hoat(p, self.u1)
        self.assertEqual(ctx.exception.get_codes(), "quy_trinh_khong_co_cap")

    def test_cannot_activate_step_without_signer(self):
        p = self.create("QT4", cap_ky=[{"cap_ky": 1, "ten_cap_ky": "C", "thu_tu": 1}])
        with self.assertRaises(SigningError) as ctx:
            process_service.kich_hoat(p, self.u1)
        self.assertEqual(ctx.exception.get_codes(), "cap_ky_khong_co_nguoi_ky")
        self.assertEqual(ctx.exception.fields, {"cap_ky_thieu_nguoi_ky": [1]})

    def test_activate_then_lock_editing(self):
        p = process_service.kich_hoat(self.create(), self.u1)
        self.assertEqual(p.trang_thai, enums.TrangThaiQuyTrinh.HOAT_DONG)
        with self.assertRaises(ConflictError) as ctx:
            process_service.them_cap_ky(p, self.u1, cap_ky=9, ten_cap_ky="Mới", thu_tu=9)
        self.assertEqual(ctx.exception.get_codes(), "quy_trinh_khong_the_sua")
        step = p.cap_ky_set.first()
        with self.assertRaises(ConflictError):
            process_service.them_nguoi_ky(step, self.u1, thu_tu=9, nguoi_ky=self.u1)
        with self.assertRaises(ConflictError):
            process_service.kich_hoat(p, self.u1)

    def test_deactivate_only_from_active(self):
        p = self.create()
        with self.assertRaises(ConflictError):
            process_service.ngung(p, self.u1)
        process_service.kich_hoat(p, self.u1)
        p = process_service.ngung(p, self.u1)
        self.assertEqual(p.trang_thai, enums.TrangThaiQuyTrinh.NGUNG)
        self.assertEqual(self.actions(p)[-2:], ["KICH_HOAT_QUY_TRINH", "NGUNG_QUY_TRINH"])

    def test_activating_new_version_stops_previous_active_version(self):
        v1 = process_service.kich_hoat(self.create(), self.u1)
        v2 = process_service.nhan_ban(v1, self.u1)
        v3 = process_service.nhan_ban(v1, self.u1)
        process_service.kich_hoat(v2, self.u1)
        trang_thai = dict(SigningProcess.objects.filter(ma_quy_trinh="QT1").values_list("phien_ban", "trang_thai"))
        self.assertEqual(trang_thai, {1: "NGUNG", 2: "HOAT_DONG", 3: "NHAP"})
        log = SigningAuditLog.objects.filter(ma_doi_tuong=v1.pk, hanh_dong="NGUNG_QUY_TRINH").get()
        self.assertEqual(log.du_lieu_kem_theo, {"thay_the_boi": v2.pk, "phien_ban_moi": 2})
        process_service.kich_hoat(v3, self.u1)
        self.assertEqual(SigningProcess.objects.filter(ma_quy_trinh="QT1", trang_thai="HOAT_DONG").get().pk, v3.pk)
        # mã khác không bị ảnh hưởng
        khac = process_service.kich_hoat(self.create("QT2"), self.u1)
        self.assertEqual(SigningProcess.objects.get(pk=khac.pk).trang_thai, "HOAT_DONG")
        self.assertEqual(SigningProcess.objects.get(pk=v3.pk).trang_thai, "HOAT_DONG")

    def test_clone_increments_version_and_copies_structure(self):
        p = process_service.kich_hoat(self.create(), self.u1)
        moi = process_service.nhan_ban(p, self.u2)
        self.assertEqual((moi.ma_quy_trinh, moi.phien_ban), (p.ma_quy_trinh, 2))
        self.assertEqual(moi.trang_thai, enums.TrangThaiQuyTrinh.NHAP)
        self.assertEqual(moi.create_by, self.u2)
        self.assertEqual(moi.cap_ky_set.count(), 2)
        self.assertEqual(sum(s.nguoi_ky_set.count() for s in moi.cap_ky_set.all()), 2)
        # bản gốc không đổi, bản mới sửa được
        self.assertEqual(SigningProcess.objects.get(pk=p.pk).trang_thai, enums.TrangThaiQuyTrinh.HOAT_DONG)
        process_service.them_cap_ky(moi, self.u2, cap_ky=3, ten_cap_ky="Cấp 3", thu_tu=3)
        # nhân bản lần nữa lấy phiên bản kế tiếp
        self.assertEqual(process_service.nhan_ban(p, self.u2).phien_ban, 3)
