"""Database contract tests for the document DDL-backed integrity rules."""

from django.db import DatabaseError, IntegrityError, connection, transaction
from django.test import TestCase
from django.utils import timezone
from importlib import import_module
from types import SimpleNamespace

from accounts.models import Employee
from documents.models import (
    DocumentAccessLog,
    DocumentViewLog,
    VanBanDen,
    VanBanDenAttachment,
    VanBanDenDanhmuc,
    VanBanDenHoSo,
    VanBanDi,
)
from organizations.models import DonVi
from records.models import HoSo, LoaiVanBan as RecordLoaiVanBan


JUNCTION_COLUMNS = {
    "documents_vanbanden_nguoinhan": ("vanbanden_id", "employee_id"),
    "documents_vanbanden_hoso": ("vanbanden_id", "hoso_id"),
    "documents_vanbanden_danhmuc": ("vanbanden_id", "loaivanban_id"),
    "documents_vanbanden_donvinhan": ("vanbanden_id", "donvi_id"),
    "documents_vanbandi_nguoinhan": ("vanbandi_id", "employee_id"),
    "documents_vanbandi_hoso": ("vanbandi_id", "hoso_id"),
    "documents_vanbandi_danhmuc": ("vanbandi_id", "loaivanban_id"),
    "documents_vanbandi_donvinhan": ("vanbandi_id", "donvi_id"),
    "documents_vanbandi_noibanhanh": ("vanbandi_id", "donvi_id"),
}


class DocumentDdlIntegrityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = Employee.objects.create_user(username="ddl_integrity_user", password="pw")
        cls.hoso = HoSo.objects.get(is_he_thong=True)
        cls.other_hoso = HoSo.objects.create(
            stt_uu_tien=0,
            so_ky_hieu="DDL-TEST-HOSO",
            ten_ho_so="Hồ sơ kiểm tra toàn vẹn",
            nguoi_lap=cls.user,
        )
        cls.category = RecordLoaiVanBan.objects.create(
            ho_so=cls.hoso,
            ten_loai="Loại văn bản kiểm tra toàn vẹn",
        )
        cls.other_category = RecordLoaiVanBan.objects.create(
            ho_so=cls.other_hoso,
            ten_loai="Loại văn bản khác hồ sơ",
        )
        cls.donvi = DonVi.objects.exclude(pk=cls.user.don_vi_id).order_by("id").first()
        cls.incoming = VanBanDen.objects.create(
            nam=2098,
            so_hieu="DDL-TEST-DEN",
            so_thu_tu=1,
            trich_yeu="Văn bản đến kiểm tra toàn vẹn",
            nguoi_tao=cls.user,
        )
        cls.outgoing = VanBanDi.objects.create(
            nam=2098,
            so_hieu="DDL-TEST-DI",
            so_thu_tu=1,
            trich_yeu="Văn bản đi kiểm tra toàn vẹn",
            nguoi_tao=cls.user,
        )

    def test_all_nine_junctions_have_the_ddl_composite_primary_key(self):
        with connection.cursor() as cursor:
            for table, expected_columns in JUNCTION_COLUMNS.items():
                cursor.execute(
                    """SELECT ARRAY(
                              SELECT att.attname
                              FROM unnest(con.conkey) WITH ORDINALITY AS key(attnum, ord)
                              JOIN pg_attribute att ON att.attrelid = con.conrelid AND att.attnum = key.attnum
                              ORDER BY key.ord
                          )
                       FROM pg_constraint con
                       WHERE con.conrelid = %s::regclass AND con.contype = 'p'""",
                    [table],
                )
                row = cursor.fetchone()
                with self.subTest(table=table):
                    self.assertIsNotNone(row, f"{table} has no physical primary key")
                    self.assertEqual(tuple(row[0]), expected_columns)

    def test_duplicate_composite_keys_are_rejected_on_all_nine_tables(self):
        values_by_table = {
            "documents_vanbanden_nguoinhan": (self.incoming.pk, self.user.pk),
            "documents_vanbanden_hoso": (self.incoming.pk, self.hoso.pk),
            "documents_vanbanden_danhmuc": (self.incoming.pk, self.category.pk),
            "documents_vanbanden_donvinhan": (self.incoming.pk, self.donvi.pk),
            "documents_vanbandi_nguoinhan": (self.outgoing.pk, self.user.pk),
            "documents_vanbandi_hoso": (self.outgoing.pk, self.hoso.pk),
            "documents_vanbandi_danhmuc": (self.outgoing.pk, self.category.pk),
            "documents_vanbandi_donvinhan": (self.outgoing.pk, self.donvi.pk),
            "documents_vanbandi_noibanhanh": (self.outgoing.pk, self.donvi.pk),
        }

        for table, columns in JUNCTION_COLUMNS.items():
            values = values_by_table[table]
            column_sql = ", ".join(columns)
            placeholders = ", ".join(["%s"] * len(values))
            insert_sql = f"INSERT INTO {table} ({column_sql}) VALUES ({placeholders})"
            with self.subTest(table=table):
                with connection.cursor() as cursor:
                    cursor.execute(insert_sql, values)
                with self.assertRaises(IntegrityError):
                    with transaction.atomic():
                        with connection.cursor() as cursor:
                            cursor.execute(insert_sql, values)

    def test_preflight_reports_and_preserves_duplicate_link_rows_before_any_ddl(self):
        migration = import_module("documents.migrations.0008_ddl_integrity")
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(
                    "ALTER TABLE documents_vanbanden_hoso DROP CONSTRAINT pk_vbd_hoso"
                )
                cursor.execute(
                    "INSERT INTO documents_vanbanden_hoso (vanbanden_id, hoso_id) VALUES (%s, %s)",
                    [self.incoming.pk, self.hoso.pk],
                )
                cursor.execute(
                    "INSERT INTO documents_vanbanden_hoso (vanbanden_id, hoso_id) VALUES (%s, %s)",
                    [self.incoming.pk, self.hoso.pk],
                )

            with self.assertRaisesRegex(RuntimeError, r"documents_vanbanden_hoso: 2"):
                migration.install_integrity(None, SimpleNamespace(connection=connection))

            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT COUNT(*) FROM documents_vanbanden_hoso WHERE vanbanden_id = %s AND hoso_id = %s",
                    [self.incoming.pk, self.hoso.pk],
                )
                self.assertEqual(cursor.fetchone()[0], 2)
                cursor.execute(
                    "SELECT COUNT(*) FROM pg_constraint "
                    "WHERE conrelid = 'documents_vanbanden_hoso'::regclass AND contype = 'p'"
                )
                self.assertEqual(cursor.fetchone()[0], 0)

            transaction.set_rollback(True)

    def test_orphan_references_and_cross_dossier_categories_are_rejected(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                VanBanDenHoSo.objects.create(vanbanden=self.incoming, hoso_id=9223372036854770000)

        VanBanDenHoSo.objects.create(vanbanden=self.incoming, hoso_id=self.hoso.pk)
        with self.assertRaises(DatabaseError):
            with transaction.atomic():
                VanBanDenDanhmuc.objects.create(
                    vanbanden=self.incoming,
                    loaivanban_id=self.other_category.pk,
                )

        VanBanDenDanhmuc.objects.create(vanbanden=self.incoming, loaivanban_id=self.category.pk)
        with self.assertRaises(DatabaseError):
            with transaction.atomic():
                VanBanDenHoSo.objects.filter(vanbanden=self.incoming, hoso_id=self.hoso.pk).delete()

    def test_restricted_scope_and_access_log_are_database_protected(self):
        restricted = VanBanDen.objects.create(
            nam=2098,
            so_hieu="DDL-TEST-HAN-CHE",
            so_thu_tu=2,
            trich_yeu="Văn bản hạn chế kiểm tra toàn vẹn",
            pham_vi="HAN_CHE",
            nguoi_tao=self.user,
        )
        log = DocumentAccessLog.objects.create(
            document_type="vanbanden",
            document_id=restricted.pk,
            user=self.user,
            hanh_dong=DocumentAccessLog.HanhDong.XEM,
        )

        with self.assertRaises(DatabaseError):
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(
                        "UPDATE documents_vanbanden SET pham_vi = 'NOI_BO' WHERE id = %s",
                        [restricted.pk],
                    )
        with self.assertRaises(DatabaseError):
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute("DELETE FROM documents_vanbanden WHERE id = %s", [restricted.pk])
        with self.assertRaises(DatabaseError):
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(
                        "UPDATE documents_access_log SET hanh_dong = 'TAI_FILE' WHERE id = %s",
                        [log.pk],
                    )
        with self.assertRaises(DatabaseError):
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute("DELETE FROM documents_access_log WHERE id = %s", [log.pk])

        allowed = VanBanDen.objects.create(
            nam=2098,
            so_hieu="DDL-TEST-NOI-BO",
            so_thu_tu=3,
            trich_yeu="Văn bản nội bộ cập nhật bình thường",
            nguoi_tao=self.user,
        )
        allowed.trich_yeu = "Nội dung cập nhật được phép"
        allowed.save(update_fields=["trich_yeu"])
        allowed.refresh_from_db()
        self.assertEqual(allowed.trich_yeu, "Nội dung cập nhật được phép")

    def test_document_delete_cascades_children_and_cleans_view_log(self):
        VanBanDenHoSo.objects.create(vanbanden=self.incoming, hoso_id=self.hoso.pk)
        VanBanDenAttachment.objects.create(document=self.incoming, name="sample.pdf", file="sample.pdf")
        DocumentViewLog.objects.create(
            document_type="vanbanden",
            document_id=self.incoming.pk,
            user=self.user,
        )

        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM documents_vanbanden WHERE id = %s", [self.incoming.pk])

        self.assertFalse(VanBanDenHoSo.objects.filter(vanbanden_id=self.incoming.pk).exists())
        self.assertFalse(VanBanDenAttachment.objects.filter(document_id=self.incoming.pk).exists())
        self.assertFalse(DocumentViewLog.objects.filter(document_type="vanbanden", document_id=self.incoming.pk).exists())


class DocumentKindMigrationTests(TestCase):
    def setUp(self):
        self.user = Employee.objects.create_user(username="document_kind_migration_user", password="pw")
        self.restricted = VanBanDen.objects.create(
            nam=2097,
            so_hieu="DDL-TEST-KIND-MIGRATION",
            so_thu_tu=1,
            trich_yeu="Văn bản hạn chế cho kiểm tra migration",
            pham_vi="HAN_CHE",
            nguoi_tao=self.user,
        )
        self.migration = import_module("documents.migrations.0008_ddl_integrity")
        self.schema = SimpleNamespace(connection=connection)

    def _make_view_log_varchar(self):
        with connection.cursor() as cursor:
            cursor.execute(
                "ALTER TABLE documents_view_log ALTER COLUMN document_type TYPE varchar "
                "USING document_type::text"
            )

    def test_legacy_alias_is_canonicalized_without_losing_view_log_fields(self):
        timestamp = timezone.now()
        with transaction.atomic():
            self._make_view_log_varchar()
            with connection.cursor() as cursor:
                cursor.execute(
                    """INSERT INTO documents_view_log (document_type, document_id, user_id, viewed_at)
                       VALUES ('vanbanmat', %s, %s, %s) RETURNING id""",
                    [self.restricted.pk, self.user.pk, timestamp],
                )
                row_id = cursor.fetchone()[0]

            preflight = self.migration._preflight_document_kind_logs(self.schema)
            self.migration._canonicalize_document_kind_logs(self.schema, preflight)

            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT id, document_type::text, document_id, user_id, viewed_at "
                    "FROM documents_view_log WHERE id = %s",
                    [row_id],
                )
                row = cursor.fetchone()
                self.assertEqual(row[:4], (row_id, "vanbanden", self.restricted.pk, self.user.pk))
                self.assertEqual(row[4], timestamp)
                cursor.execute(
                    "SELECT udt_name FROM information_schema.columns "
                    "WHERE table_schema = current_schema() AND table_name = 'documents_view_log' "
                    "AND column_name = 'document_type'"
                )
                self.assertEqual(cursor.fetchone()[0], "document_kind")

            transaction.set_rollback(True)

    def test_alias_collision_fails_before_changing_rows_or_column_type(self):
        timestamp = timezone.now()
        with transaction.atomic():
            DocumentViewLog.objects.create(
                document_type="vanbanden",
                document_id=self.restricted.pk,
                user=self.user,
                viewed_at=timestamp,
            )
            self._make_view_log_varchar()
            with connection.cursor() as cursor:
                cursor.execute(
                    """INSERT INTO documents_view_log (document_type, document_id, user_id, viewed_at)
                       VALUES ('vanbanmat', %s, %s, %s)""",
                    [self.restricted.pk, self.user.pk, timestamp],
                )

            with self.assertRaisesRegex(RuntimeError, r"documents_view_log: 1 hàng alias xung đột"):
                self.migration._preflight_document_kind_logs(self.schema)

            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT document_type::text, COUNT(*) FROM documents_view_log "
                    "WHERE document_id = %s AND user_id = %s GROUP BY document_type::text "
                    "ORDER BY document_type::text",
                    [self.restricted.pk, self.user.pk],
                )
                self.assertEqual(cursor.fetchall(), [("vanbanden", 1), ("vanbanmat", 1)])
                cursor.execute(
                    "SELECT udt_name FROM information_schema.columns "
                    "WHERE table_schema = current_schema() AND table_name = 'documents_view_log' "
                    "AND column_name = 'document_type'"
                )
                self.assertEqual(cursor.fetchone()[0], "varchar")

            transaction.set_rollback(True)

    def test_orphan_alias_fails_without_changing_audit_row(self):
        timestamp = timezone.now()
        missing_document_id = 9223372036854775807
        with transaction.atomic():
            self._make_view_log_varchar()
            with connection.cursor() as cursor:
                cursor.execute(
                    """INSERT INTO documents_view_log (document_type, document_id, user_id, viewed_at)
                       VALUES ('vanbanmat', %s, %s, %s) RETURNING id""",
                    [missing_document_id, self.user.pk, timestamp],
                )
                row_id = cursor.fetchone()[0]

            with self.assertRaisesRegex(RuntimeError, r"documents_view_log: 1 hàng alias không trỏ"):
                self.migration._preflight_document_kind_logs(self.schema)

            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT document_type::text, document_id, user_id, viewed_at "
                    "FROM documents_view_log WHERE id = %s",
                    [row_id],
                )
                self.assertEqual(cursor.fetchone(), ("vanbanmat", missing_document_id, self.user.pk, timestamp))

            transaction.set_rollback(True)

    def test_legacy_access_log_alias_is_not_rewritten_behind_worm_trigger(self):
        timestamp = timezone.now()
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(
                    "ALTER TABLE documents_access_log ALTER COLUMN document_type TYPE varchar "
                    "USING document_type::text"
                )
                cursor.execute(
                    """INSERT INTO documents_access_log
                       (document_type, document_id, user_id, hanh_dong, created_at)
                       VALUES ('vanbanmat', %s, %s, 'XEM', %s) RETURNING id""",
                    [self.restricted.pk, self.user.pk, timestamp],
                )
                row_id = cursor.fetchone()[0]

            with self.assertRaisesRegex(RuntimeError, r"documents_access_log: 1 hàng alias gặp trigger bảo vệ UPDATE"):
                self.migration._preflight_document_kind_logs(self.schema)

            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT document_type::text, document_id, user_id, hanh_dong, created_at "
                    "FROM documents_access_log WHERE id = %s",
                    [row_id],
                )
                self.assertEqual(
                    cursor.fetchone(),
                    ("vanbanmat", self.restricted.pk, self.user.pk, "XEM", timestamp),
                )

            transaction.set_rollback(True)
