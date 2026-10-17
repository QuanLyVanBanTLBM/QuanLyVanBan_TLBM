"""PostgreSQL release contracts owned by Group 3 only."""
from importlib import import_module
from unittest import skipUnless

from django.apps import apps
from django.contrib.auth import get_user_model
from django.db import DatabaseError, connection, transaction
from django.test import TestCase

from records.models import HoSo, LoaiVanBan


@skipUnless(connection.vendor == "postgresql", "PostgreSQL catalog contract")
class ReleaseSchemaTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="release-contract", password="test-only",
        )

    def test_sql_insert_uses_release_defaults_and_auto_priority(self):
        with connection.cursor() as cursor:
            cursor.execute("""INSERT INTO records_hoso (so_ky_hieu, ten_ho_so, nguoi_lap_id)
                VALUES ('RELEASE-SQL', 'Release contract', %s)
                RETURNING id, stt_uu_tien, is_he_thong, created_at, updated_at""", [self.user.pk])
            pk, priority, system, created, updated = cursor.fetchone()
            self.assertGreater(pk, 0)
            self.assertGreater(priority, 0)
            self.assertFalse(system)
            self.assertIsNotNone(created)
            self.assertIsNotNone(updated)
            cursor.execute("""INSERT INTO records_loaivanban (ho_so_id, ten_loai)
                VALUES (%s, 'Release type') RETURNING id, created_at, updated_at""", [pk])
            pk, created, updated = cursor.fetchone()
            self.assertGreater(pk, 0)
            self.assertIsNotNone(created)
            self.assertIsNotNone(updated)

    def test_foreign_keys_match_release_restrict_and_are_not_deferred(self):
        for table, name in (
            ("records_hoso", "records_hoso_nguoi_lap_id_fkey"),
            ("records_loaivanban", "records_loaivanban_ho_so_id_fkey"),
        ):
            with connection.cursor() as cursor:
                cursor.execute("""SELECT conname, confdeltype, condeferrable, condeferred
                    FROM pg_constraint WHERE conrelid=%s::regclass AND contype='f'""", [table])
                self.assertEqual(cursor.fetchall(), [(name, "r", False, False)])

    def test_id_sequence_and_timestamp_defaults_match_release(self):
        for table in ("records_hoso", "records_loaivanban"):
            with connection.cursor() as cursor:
                cursor.execute("""SELECT a.attname, a.attidentity, pg_get_expr(d.adbin,d.adrelid)
                    FROM pg_attribute a JOIN pg_attrdef d ON d.adrelid=a.attrelid AND d.adnum=a.attnum
                    WHERE a.attrelid=%s::regclass AND a.attname IN ('id','created_at','updated_at')
                    ORDER BY a.attname""", [table])
                self.assertEqual(cursor.fetchall(), [
                    ("created_at", "", "now()"),
                    ("id", "", f"nextval('{table}_id_seq'::regclass)"),
                    ("updated_at", "", "now()"),
                ])

    def test_restrict_rejects_sql_delete_of_a_referenced_dossier(self):
        dossier = HoSo.objects.create(so_ky_hieu="RESTRICT", ten_ho_so="Contract", nguoi_lap=self.user)
        LoaiVanBan.objects.create(ho_so=dossier, ten_loai="Contract type")
        with self.assertRaises(DatabaseError), transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM records_hoso WHERE id=%s", [dossier.pk])
        self.assertTrue(HoSo.objects.filter(pk=dossier.pk).exists())

    def test_alignment_can_adopt_already_aligned_tables_without_changing_rows(self):
        dossier = HoSo.objects.create(so_ky_hieu="ADOPT", ten_ho_so="Contract", nguoi_lap=self.user)
        LoaiVanBan.objects.create(ho_so=dossier, ten_loai="Contract type")
        before = (list(HoSo.objects.values()), list(LoaiVanBan.objects.values()))
        migration = import_module("records.migrations.0006_align_release_schema")
        with connection.schema_editor() as editor:
            migration.align_schema(apps, editor)
        self.assertEqual((list(HoSo.objects.values()), list(LoaiVanBan.objects.values())), before)

    def test_updated_at_triggers_use_the_release_function(self):
        with connection.cursor() as cursor:
            cursor.execute("""SELECT t.tgname, p.proname FROM pg_trigger t
                JOIN pg_proc p ON p.oid=t.tgfoid
                WHERE t.tgname IN ('trg_hoso_updated_at','trg_loaivanban_updated_at')
                AND t.tgrelid IN ('records_hoso'::regclass,'records_loaivanban'::regclass)
                ORDER BY t.tgname""")
            self.assertEqual(cursor.fetchall(), [
                ("trg_hoso_updated_at", "set_updated_at"),
                ("trg_loaivanban_updated_at", "set_updated_at"),
            ])
