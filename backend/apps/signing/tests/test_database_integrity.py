import importlib
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.db import DatabaseError, IntegrityError, connection, transaction
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from accounts.models import Position
from organizations.models import DonVi, KhoiKhuVuc
from signing import enums
from signing.models import (
    SigningAttempt,
    SigningAuditLog,
    SigningKey,
    SigningKeyUnlock,
    SigningManifest,
    SigningNotification,
    SigningProcess,
    SigningProcessStep,
    SigningProcessStepSigner,
    SigningRequest,
    SigningRequestStep,
    SigningRequestStepSigner,
    SigningSignature,
)

User = get_user_model()
HASH = "a" * 64

EXPECTED_FOREIGN_KEYS = {
    ("signing_process", "don_vi_ap_dung_id"): ("organizations_donvi", "id", "r"),
    ("signing_process_step", "don_vi_id"): ("organizations_donvi", "id", "n"),
    ("signing_process_step_signer", "chuc_vu_id"): ("accounts_position", "id", "r"),
    ("signing_request_step_signer", "chuc_vu_id"): ("accounts_position", "id", "n"),
    ("signing_attempt", "nguoi_cap_nhat_id"): ("accounts_employee", "id", "n"),
    ("signing_process", "nguoi_cap_nhat_id"): ("accounts_employee", "id", "n"),
    ("signing_request", "nguoi_cap_nhat_id"): ("accounts_employee", "id", "n"),
    ("signing_key_unlock", "khoa_id"): ("signing_key", "id", "c"),
    ("signing_notification", "buoc_ky_id"): ("signing_request_step_signer", "id", "c"),
    ("signing_notification", "trinh_ky_id"): ("signing_request", "id", "c"),
    ("signing_process_step", "quy_trinh_id"): ("signing_process", "id", "c"),
    ("signing_process_step_signer", "buoc_quy_trinh_id"): ("signing_process_step", "id", "c"),
    ("signing_request_step_signer", "chu_ky_hien_hanh_id"): ("signing_signature", "id", "n"),
}


class SigningDatabaseIntegrityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("integrity-owner")
        self.process = SigningProcess.objects.create(
            ma_quy_trinh="INTEGRITY",
            ten_quy_trinh="Integrity flow",
            pham_vi=enums.PhamViQuyTrinh.CONG_TY,
            create_by=self.user,
        )
        self.process_step = SigningProcessStep.objects.create(
            quy_trinh=self.process, cap_ky=1, ten_cap_ky="Cấp 1", thu_tu=1
        )
        self.request = SigningRequest.objects.create(
            document_type=enums.LoaiVanBan.VAN_BAN_DI,
            van_ban_id=1,
            quy_trinh=self.process,
            phien_ban_quy_trinh=1,
            create_by=self.user,
        )
        self.attempt = SigningAttempt.objects.create(
            trinh_ky=self.request,
            so_luot=1,
            vi_tri_luu_tep="source.pdf",
            ma_bam_tai_lieu=HASH,
            create_by=self.user,
        )
        self.request_step = SigningRequestStep.objects.create(
            luot_trinh=self.attempt,
            buoc_quy_trinh=self.process_step,
            cap_ky=1,
            ten_cap_ky="Cấp 1",
            thu_tu=1,
        )
        self.signer = SigningRequestStepSigner.objects.create(
            buoc_ky=self.request_step,
            nguoi_ky=self.user,
            ten_nguoi_ky="Integrity owner",
            vai_tro_ky=enums.VaiTroKy.KY_CHINH,
        )
        self.key = SigningKey.objects.create(
            nguoi_so_huu=self.user,
            ma_khoa="integrity-key",
            dau_van_tay=HASH,
            khoa_cong_khai="public-key",
            ngay_hieu_luc=timezone.now(),
        )

    def _new_unit(self):
        region = KhoiKhuVuc.objects.create(ten="Integrity test region")
        latest_priority = DonVi.objects.order_by("-stt_uu_tien").values_list("stt_uu_tien", flat=True).first() or 0
        return DonVi.objects.create(
            khoi=region,
            stt_uu_tien=latest_priority + 1,
            ten="Integrity test unit",
        )

    def test_request_van_ban_check_requires_linked_document_or_manual_summary(self):
        chung = {"quy_trinh": self.process, "phien_ban_quy_trinh": 1, "create_by": self.user}
        nhap_tay = SigningRequest.objects.create(so_hieu_van_ban="12/TTr", trich_yeu_van_ban="Tờ trình", **chung)
        self.assertIsNone(nhap_tay.van_ban_id)
        for sai in (
            {},  # không gắn văn bản và không có trích yếu
            {"document_type": enums.LoaiVanBan.VAN_BAN_DI},  # thiếu document_id
            {"van_ban_id": 1, "trich_yeu_van_ban": "Tờ trình"},  # thiếu document_type
        ):
            with self.subTest(sai=sai), self.assertRaises(IntegrityError), transaction.atomic():
                SigningRequest.objects.create(**sai, **chung)

    def test_all_signing_foreign_keys_match_ddl_targets_and_delete_actions(self):
        self.assertEqual(connection.vendor, "postgresql")
        with connection.cursor() as cursor:
            for (table, column), (target, target_column, delete_action) in EXPECTED_FOREIGN_KEYS.items():
                constraints = connection.introspection.get_constraints(cursor, table)
                actual = [
                    (name, info)
                    for name, info in constraints.items()
                    if info.get("foreign_key") is not None and column in (info.get("columns") or [])
                ]
                self.assertEqual(len(actual), 1, f"{table}.{column}")
                constraint_name, info = actual[0]
                self.assertEqual(info["columns"], [column], f"{table}.{column}")
                self.assertEqual(tuple(info["foreign_key"]), (target, target_column), f"{table}.{column}")
                cursor.execute(
                    "SELECT confdeltype, condeferrable, condeferred, convalidated "
                    "FROM pg_catalog.pg_constraint "
                    "WHERE conrelid = to_regclass(%s) AND conname = %s AND contype = 'f'",
                    [table, constraint_name],
                )
                self.assertEqual(cursor.fetchone(), (delete_action, False, False, True), f"{table}.{column}")

    def test_raw_sql_rejects_orphans_and_accepts_valid_foreign_keys(self):
        position = Position.objects.create(
            display_order=Position.get_next_display_order(), name="Integrity test position"
        )
        process_signer = SigningProcessStepSigner.objects.create(
            buoc_quy_trinh=self.process_step,
            chuc_vu=position,
            thu_tu=1,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(
                        "UPDATE signing_request_step_signer SET chuc_vu_id = -987654321 WHERE id = %s",
                        [self.signer.pk],
                    )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(
                        "UPDATE signing_process_step_signer SET chuc_vu_id = -987654321 WHERE id = %s",
                        [process_signer.pk],
                    )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(
                        "UPDATE signing_request_step_signer SET chu_ky_hien_hanh_id = -987654321 WHERE id = %s",
                        [self.signer.pk],
                    )

        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE signing_request_step_signer SET chuc_vu_id = %s WHERE id = %s",
                [position.pk, self.signer.pk],
            )
            cursor.execute(
                "UPDATE signing_process_step_signer SET nguoi_ky_id = NULL WHERE id = %s",
                [process_signer.pk],
            )
        process_signer.refresh_from_db()
        self.assertEqual(process_signer.chuc_vu_id, position.pk)
        self.assertIsNone(process_signer.nguoi_ky_id)

    def test_raw_sql_fk_delete_actions_preserve_expected_relations(self):
        position = Position.objects.create(
            display_order=Position.get_next_display_order(), name="Integrity delete position"
        )
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE signing_request_step_signer SET chuc_vu_id = %s WHERE id = %s",
                [position.pk, self.signer.pk],
            )
            cursor.execute("DELETE FROM accounts_position WHERE id = %s", [position.pk])
        self.signer.refresh_from_db()
        self.assertIsNone(self.signer.chuc_vu_id)

        unit = self._new_unit()
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE signing_process_step SET don_vi_id = %s WHERE id = %s",
                [unit.pk, self.process_step.pk],
            )
            cursor.execute("DELETE FROM organizations_donvi WHERE id = %s", [unit.pk])
        self.process_step.refresh_from_db()
        self.assertIsNone(self.process_step.don_vi_id)

        SigningKeyUnlock.objects.create(
            khoa=self.key,
            ma_bam_xac_minh_pin="verifier",
            manh_bi_mat_ma_hoa="encrypted-fragment",
            tham_so_kdf={"algorithm": "test"},
        )
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM signing_key WHERE id = %s", [self.key.pk])
            cursor.execute("SELECT COUNT(*) FROM signing_key_unlock WHERE khoa_id = %s", [self.key.pk])
            self.assertEqual(cursor.fetchone()[0], 0)

        process = SigningProcess.objects.create(
            ma_quy_trinh="DELETE-CASCADE",
            ten_quy_trinh="Delete cascade",
            pham_vi=enums.PhamViQuyTrinh.CONG_TY,
            create_by=self.user,
        )
        step = SigningProcessStep.objects.create(
            quy_trinh=process, cap_ky=1, ten_cap_ky="Cấp 1", thu_tu=1
        )
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM signing_process WHERE id = %s", [process.pk])
            cursor.execute("SELECT COUNT(*) FROM signing_process_step WHERE id = %s", [step.pk])
            self.assertEqual(cursor.fetchone()[0], 0)

        request = SigningRequest.objects.create(
            document_type=enums.LoaiVanBan.VAN_BAN_DI,
            van_ban_id=2,
            quy_trinh=self.process,
            phien_ban_quy_trinh=1,
            create_by=self.user,
        )
        SigningNotification.objects.create(
            trinh_ky=request,
            nguoi_nhan=self.user,
            kenh=enums.KenhThongBao.IN_APP,
            loai_thong_bao="INTEGRITY_TEST",
            khoa_chong_gui_trung="integrity-notification",
        )
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM signing_request WHERE id = %s", [request.pk])
            cursor.execute("SELECT COUNT(*) FROM signing_notification WHERE trinh_ky_id = %s", [request.pk])
            self.assertEqual(cursor.fetchone()[0], 0)

        updater = User.objects.create_user("integrity-updater")
        self.process.update_by = updater
        self.process.save(update_fields=["update_by"])
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM accounts_employee WHERE id = %s", [updater.pk])
            cursor.execute("SELECT nguoi_cap_nhat_id FROM signing_process WHERE id = %s", [self.process.pk])
            self.assertIsNone(cursor.fetchone()[0])

    def test_raw_sql_evidence_guards_reject_mutation_and_allow_the_declared_exceptions(self):
        signature = SigningSignature.objects.create(
            luot_trinh=self.attempt,
            buoc_ky=self.signer,
            khoa_ky=self.key,
            hash_tai_lieu=HASH,
            thuat_toan="Ed25519",
            chu_ky_so="signature",
        )
        with self.assertRaises(DatabaseError):
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(
                        "UPDATE signing_signature SET chu_ky_so = 'changed' WHERE id = %s",
                        [signature.pk],
                    )
        with self.assertRaises(DatabaseError):
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute("DELETE FROM signing_signature WHERE id = %s", [signature.pk])
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE signing_signature SET trang_thai_xac_minh = 'KHONG_HOP_LE', "
                "thoi_diem_xac_minh = NOW() WHERE id = %s",
                [signature.pk],
            )
            cursor.execute(
                "SELECT trang_thai_xac_minh FROM signing_signature WHERE id = %s", [signature.pk]
            )
            self.assertEqual(cursor.fetchone()[0], "KHONG_HOP_LE")

        draft = SigningManifest.objects.create(
            luot_trinh=self.attempt,
            noi_dung_chuan_hoa={"version": 1},
            ma_bam_bang_chung="b" * 64,
            create_by=self.user,
        )
        with connection.cursor() as cursor:
            cursor.execute("UPDATE signing_manifest SET vi_tri_luu = 'draft.json' WHERE id = %s", [draft.pk])
            cursor.execute("DELETE FROM signing_manifest WHERE id = %s", [draft.pk])

        final_manifest = SigningManifest.objects.create(
            luot_trinh=self.attempt,
            noi_dung_chuan_hoa={"version": 1},
            ma_bam_bang_chung="c" * 64,
            trang_thai=enums.TrangThaiManifest.DA_CHOT,
            thoi_diem_chot=timezone.now(),
            create_by=self.user,
        )
        with self.assertRaises(DatabaseError):
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(
                        "UPDATE signing_manifest SET vi_tri_luu = 'changed.json' WHERE id = %s",
                        [final_manifest.pk],
                    )
        with self.assertRaises(DatabaseError):
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute("DELETE FROM signing_manifest WHERE id = %s", [final_manifest.pk])

        draft_attempt = SigningAttempt.objects.create(
            trinh_ky=self.request,
            so_luot=2,
            vi_tri_luu_tep="draft.pdf",
            ma_bam_tai_lieu="d" * 64,
            create_by=self.user,
        )
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM signing_attempt WHERE id = %s", [draft_attempt.pk])
        sent_attempt = SigningAttempt.objects.create(
            trinh_ky=self.request,
            so_luot=3,
            vi_tri_luu_tep="sent.pdf",
            ma_bam_tai_lieu="e" * 64,
            trang_thai=enums.TrangThaiLuotTrinh.CHO_KY,
            create_by=self.user,
        )
        with self.assertRaises(DatabaseError):
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute("DELETE FROM signing_attempt WHERE id = %s", [sent_attempt.pk])

        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO signing_audit_log "
                "(loai_doi_tuong, ma_doi_tuong, nguoi_thuc_hien_id, hanh_dong, "
                "trang_thai_truoc, trang_thai_sau, chi_tiet, created_at) "
                "VALUES ('signing_key', 1, %s, 'RAW_INSERT', '', '', '', NOW()) RETURNING id",
                [self.user.pk],
            )
            audit_log_id = cursor.fetchone()[0]
        with self.assertRaises(DatabaseError):
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(
                        "UPDATE signing_audit_log SET chi_tiet = 'changed' WHERE id = %s",
                        [audit_log_id],
                    )
        with self.assertRaises(DatabaseError):
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute("DELETE FROM signing_audit_log WHERE id = %s", [audit_log_id])


class SigningMigrationPreflightTests(TransactionTestCase):
    def setUp(self):
        self.user = User.objects.create_user("preflight-owner")
        self.process = SigningProcess.objects.create(
            ma_quy_trinh="PREFLIGHT",
            ten_quy_trinh="Preflight flow",
            pham_vi=enums.PhamViQuyTrinh.CONG_TY,
            create_by=self.user,
        )

    def test_preflight_fails_with_table_count_and_rolls_back_orphan_probe(self):
        migration = importlib.import_module("signing.migrations.0010_khoa_ngoai_don_vi_chuc_vu")
        with connection.cursor() as cursor:
            constraints = connection.introspection.get_constraints(cursor, "signing_process")
        fk_names = [
            name
            for name, info in constraints.items()
            if info.get("foreign_key") == ("organizations_donvi", "id")
            and info.get("columns") == ["don_vi_ap_dung_id"]
        ]
        self.assertEqual(len(fk_names), 1)
        quote = connection.ops.quote_name

        with self.assertRaises(RuntimeError) as raised:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(
                        f"ALTER TABLE {quote('signing_process')} DROP CONSTRAINT {quote(fk_names[0])}"
                    )
                    cursor.execute(
                        "UPDATE signing_process SET pham_vi = 'PHONG_BAN', don_vi_ap_dung_id = -987654321 "
                        "WHERE id = %s",
                        [self.process.pk],
                    )
                migration.preflight_signing_fk_data(None, SimpleNamespace(connection=connection))

        message = str(raised.exception)
        self.assertIn("signing_process.don_vi_ap_dung_id: 1 orphan reference(s)", message)
        self.assertNotIn("-987654321", message)
        self.process.refresh_from_db()
        self.assertIsNone(self.process.don_vi_ap_dung_id)
