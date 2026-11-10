"""Focused coverage for canonical AI metadata views and qlvb_readonly access."""

import importlib
import re
import unittest
from datetime import date

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import DatabaseError, connections, transaction
from django.test import SimpleTestCase, TransactionTestCase

from document_templates.models import DanhMucTaiLieu, TaiLieuChiTiet
from documents.models import PhamVi, VanBanDen, VanBanDi
from organizations.models import DonVi, KhoiKhuVuc


MIGRATION = importlib.import_module("documents.migrations.0010_ai_metadata_views")
VIEW_NAMES = {
    "ai_vanbanden",
    "ai_vanbanden_nguoinhan",
    "ai_vanbanden_donvinhan",
    "ai_vanbandi",
    "ai_vanbandi_noibanhanh",
    "ai_vanbandi_nguoinhan",
    "ai_vanbandi_donvinhan",
    "ai_tailieu",
}
PARENT_VIEWS = {"ai_vanbanden", "ai_vanbandi", "ai_tailieu"}
AUXILIARY_VIEWS = VIEW_NAMES - PARENT_VIEWS
CANONICAL_AUXILIARY_VIEW_COLUMNS = {
    "ai_vanbanden_nguoinhan": ("vanbanden_id", "employee_id"),
    "ai_vanbanden_donvinhan": ("vanbanden_id", "donvi_id"),
    "ai_vanbandi_noibanhanh": ("vanbandi_id", "donvi_id"),
    "ai_vanbandi_nguoinhan": ("vanbandi_id", "employee_id"),
    "ai_vanbandi_donvinhan": ("vanbandi_id", "donvi_id"),
}
CANONICAL_V2_AUXILIARY_VIEW_SQL = {
    "ai_vanbanden_nguoinhan": """
        CREATE VIEW ai_vanbanden_nguoinhan WITH (security_barrier) AS
        SELECT nn.vanbanden_id, nn.employee_id
        FROM documents_vanbanden_nguoinhan nn
        JOIN documents_vanbanden vb ON vb.id = nn.vanbanden_id
        WHERE vb.pham_vi = 'NOI_BO' AND vb.hien_thi IS TRUE
    """,
    "ai_vanbanden_donvinhan": """
        CREATE VIEW ai_vanbanden_donvinhan WITH (security_barrier) AS
        SELECT dv.vanbanden_id, dv.donvi_id
        FROM documents_vanbanden_donvinhan dv
        JOIN documents_vanbanden vb ON vb.id = dv.vanbanden_id
        WHERE vb.pham_vi = 'NOI_BO' AND vb.hien_thi IS TRUE
    """,
    "ai_vanbandi_noibanhanh": """
        CREATE VIEW ai_vanbandi_noibanhanh WITH (security_barrier) AS
        SELECT nb.vanbandi_id, nb.donvi_id
        FROM documents_vanbandi_noibanhanh nb
        JOIN documents_vanbandi vb ON vb.id = nb.vanbandi_id
        WHERE vb.pham_vi = 'NOI_BO' AND vb.hien_thi IS TRUE
    """,
    "ai_vanbandi_nguoinhan": """
        CREATE VIEW ai_vanbandi_nguoinhan WITH (security_barrier) AS
        SELECT nn.vanbandi_id, nn.employee_id
        FROM documents_vanbandi_nguoinhan nn
        JOIN documents_vanbandi vb ON vb.id = nn.vanbandi_id
        WHERE vb.pham_vi = 'NOI_BO' AND vb.hien_thi IS TRUE
    """,
    "ai_vanbandi_donvinhan": """
        CREATE VIEW ai_vanbandi_donvinhan WITH (security_barrier) AS
        SELECT dv.vanbandi_id, dv.donvi_id
        FROM documents_vanbandi_donvinhan dv
        JOIN documents_vanbandi vb ON vb.id = dv.vanbandi_id
        WHERE vb.pham_vi = 'NOI_BO' AND vb.hien_thi IS TRUE
    """,
}


class AIMetadataViewColumnOrderTests(TransactionTestCase):
    databases = {"default"}

    @classmethod
    def setUpClass(cls):
        if connections["default"].vendor != "postgresql":
            raise unittest.SkipTest("AI metadata view column order requires PostgreSQL.")
        super().setUpClass()

    def _view_columns(self, cursor, view_name):
        cursor.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = %s "
            "ORDER BY ordinal_position",
            [view_name],
        )
        return tuple(row[0] for row in cursor.fetchall())

    def _view_oid(self, cursor, view_name):
        cursor.execute(
            "SELECT c.oid FROM pg_class c "
            "JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE n.nspname = 'public' AND c.relname = %s",
            [view_name],
        )
        return cursor.fetchone()[0]

    def test_migrated_auxiliary_views_match_canonical_v2_column_order(self):
        with connections["default"].cursor() as cursor:
            for view_name, expected_columns in CANONICAL_AUXILIARY_VIEW_COLUMNS.items():
                with self.subTest(view=view_name):
                    self.assertEqual(self._view_columns(cursor, view_name), expected_columns)

    def test_existing_canonical_v2_views_are_replaced_in_place(self):
        with transaction.atomic():
            with connections["default"].cursor() as cursor:
                # Recreate the existing DDL v2 view shapes before replaying the migration.
                for view_name in CANONICAL_V2_AUXILIARY_VIEW_SQL:
                    cursor.execute(f"DROP VIEW {view_name}")
                for statement in CANONICAL_V2_AUXILIARY_VIEW_SQL.values():
                    cursor.execute(statement)
                previous_oids = {
                    view_name: self._view_oid(cursor, view_name)
                    for view_name in CANONICAL_V2_AUXILIARY_VIEW_SQL
                }

                for statement in MIGRATION.FORWARD_SQL:
                    cursor.execute(statement)

                current_oids = {
                    view_name: self._view_oid(cursor, view_name)
                    for view_name in CANONICAL_V2_AUXILIARY_VIEW_SQL
                }
                self.assertEqual(current_oids, previous_oids)
                for view_name, expected_columns in CANONICAL_AUXILIARY_VIEW_COLUMNS.items():
                    with self.subTest(view=view_name):
                        self.assertEqual(self._view_columns(cursor, view_name), expected_columns)

            # Keep this regression isolated from the migrated test database schema.
            transaction.set_rollback(True)


class AIMetadataViewsMigrationContractTests(SimpleTestCase):
    def test_migration_creates_all_eight_security_barrier_views(self):
        sql = "\n".join(MIGRATION.FORWARD_SQL)
        created = set(
            re.findall(
                r"CREATE\s+OR\s+REPLACE\s+VIEW\s+(ai_[a-z_]+)\s+WITH\s*\(security_barrier\)",
                sql,
                re.IGNORECASE,
            )
        )
        self.assertEqual(created, VIEW_NAMES)

    def test_role_grants_match_the_canonical_three_view_contract(self):
        sql = "\n".join(MIGRATION.FORWARD_SQL)
        grant = re.search(
            r"GRANT\s+SELECT\s+ON(.*?)TO\s+qlvb_readonly",
            sql,
            re.IGNORECASE | re.DOTALL,
        )
        self.assertIsNotNone(grant)
        granted = set(re.findall(r"\bai_[a-z_]+\b", grant.group(1), re.IGNORECASE))
        self.assertEqual(granted, PARENT_VIEWS)
        for view in AUXILIARY_VIEWS:
            self.assertIn(view, sql)
        self.assertIn("c.relowner = current_user::regrole", sql)
        self.assertIn("c.relkind IN ('r', 'p', 'v', 'm', 'f')", sql)
        self.assertIn("REVOKE SELECT ON TABLE %I.%I FROM qlvb_readonly", sql)
        self.assertIn(
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public\n                REVOKE SELECT ON TABLES FROM qlvb_readonly",
            sql,
        )
        self.assertIn("has_any_column_privilege", sql)
        self.assertIn("remaining_select_count", sql)
        self.assertNotRegex(sql, r"\b(?:CREATE|ALTER)\s+(?:ROLE|USER)\b")
        self.assertNotIn("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT", sql)
        self.assertNotIn("PASSWORD", sql.upper())

    def test_role_is_optional_and_views_do_not_load_mutable_ddl(self):
        sql = "\n".join(MIGRATION.FORWARD_SQL)
        self.assertIn("IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'qlvb_readonly')", sql)
        self.assertIn("RAISE NOTICE", sql)
        self.assertNotIn("release_DDL.sql", sql)
        self.assertNotIn("read_text(", sql)

    def test_canonical_document_and_employee_filters_are_present(self):
        sql = "\n".join(MIGRATION.FORWARD_SQL)
        self.assertIn("pham_vi = 'NOI_BO' AND hien_thi IS TRUE", sql)
        self.assertIn("current_setting('qlvb.employee_id', true)", sql)
        self.assertIn("e.is_active IS TRUE", sql)
        self.assertIn("e.trang_thai::text = 'LAM_VIEC'", sql)
        self.assertIn("t.hien_thi::text = 'TAT_CA'", sql)
        self.assertIn("t.hien_thi::text = 'NOI_BO_PHONG_BAN'", sql)

    def test_graph_waits_for_both_source_scalar_migrations(self):
        self.assertIn(("documents", "0009_schema_scalars"), MIGRATION.Migration.dependencies)
        self.assertIn(("document_templates", "0004_schema_scalars"), MIGRATION.Migration.dependencies)


class AIMetadataViewsPostgreSQLAccessTests(TransactionTestCase):
    databases = {"default"} | ({"readonly"} if "readonly" in settings.DATABASES else set())
    reset_sequences = True

    @classmethod
    def setUpClass(cls):
        if connections["default"].vendor != "postgresql":
            raise unittest.SkipTest("AI metadata view access contract requires PostgreSQL.")
        if "readonly" not in settings.DATABASES:
            raise unittest.SkipTest(
                "Configure DB_READONLY_USER=qlvb_readonly and its test password to exercise the database role."
            )
        if settings.DATABASES["readonly"]["USER"] != "qlvb_readonly":
            raise unittest.SkipTest("The readonly test alias must connect as qlvb_readonly.")
        super().setUpClass()

    def setUp(self):
        super().setUp()
        self.assertEqual(connections["readonly"].settings_dict["USER"], "qlvb_readonly")

        region_id = (KhoiKhuVuc.objects.order_by("-pk").values_list("pk", flat=True).first() or 0) + 1
        self.region = KhoiKhuVuc.objects.create(id=region_id, ten="C3 AI test region")
        last_unit_id = DonVi.objects.order_by("-pk").values_list("pk", flat=True).first() or 0
        last_priority = DonVi.objects.order_by("-stt_uu_tien").values_list(
            "stt_uu_tien", flat=True
        ).first() or 0
        self.unit_a = DonVi.objects.create(
            id=last_unit_id + 1,
            khoi=self.region,
            stt_uu_tien=last_priority + 1,
            ten="C3 AI unit A",
        )
        self.unit_b = DonVi.objects.create(
            id=last_unit_id + 2,
            khoi=self.region,
            stt_uu_tien=last_priority + 2,
            ten="C3 AI unit B",
        )

        user_model = get_user_model()
        last_employee_id = user_model.objects.order_by("-pk").values_list(
            "pk", flat=True
        ).first() or 0
        self.employee_a = user_model.objects.create_user(
            id=last_employee_id + 1,
            username="c3-ai-active-a",
            password="test-only",
            don_vi=self.unit_a,
        )
        self.employee_b = user_model.objects.create_user(
            id=last_employee_id + 2,
            username="c3-ai-active-b",
            password="test-only",
            don_vi=self.unit_b,
        )
        self.employee_inactive = user_model.objects.create_user(
            id=last_employee_id + 3,
            username="c3-ai-inactive",
            password="test-only",
            don_vi=self.unit_a,
            is_active=False,
        )
        self.employee_nonworking = user_model.objects.create_user(
            id=last_employee_id + 4,
            username="c3-ai-nonworking",
            password="test-only",
            don_vi=self.unit_a,
            trang_thai=user_model.Status.NGHI_VIEC,
        )
        # Isolate the status predicate: this row is active but explicitly not working.
        with connections["default"].cursor() as cursor:
            cursor.execute(
                "UPDATE accounts_employee SET is_active = TRUE WHERE id = %s",
                [self.employee_nonworking.pk],
            )

        self.visible_incoming = VanBanDen.objects.create(
            nam=2098, so_hieu="C3-DEN-VISIBLE", so_thu_tu=29001,
            trich_yeu="Visible internal incoming document",
            pham_vi=PhamVi.NOI_BO, hien_thi=True,
        )
        self.hidden_incoming = VanBanDen.objects.create(
            nam=2098, so_hieu="C3-DEN-HIDDEN", so_thu_tu=29002,
            trich_yeu="Hidden incoming document",
            pham_vi=PhamVi.NOI_BO, hien_thi=False,
        )
        self.restricted_incoming = VanBanDen.objects.create(
            nam=2098, so_hieu="C3-DEN-RESTRICTED", so_thu_tu=29003,
            trich_yeu="Restricted incoming document",
            pham_vi=PhamVi.HAN_CHE, hien_thi=True,
        )
        self.visible_outgoing = VanBanDi.objects.create(
            nam=2098, so_hieu="C3-DI-VISIBLE", so_thu_tu=29001,
            trich_yeu="Visible internal outgoing document",
            pham_vi=PhamVi.NOI_BO, hien_thi=True,
        )
        self.hidden_outgoing = VanBanDi.objects.create(
            nam=2098, so_hieu="C3-DI-HIDDEN", so_thu_tu=29002,
            trich_yeu="Hidden outgoing document",
            pham_vi=PhamVi.NOI_BO, hien_thi=False,
        )
        self.restricted_outgoing = VanBanDi.objects.create(
            nam=2098, so_hieu="C3-DI-RESTRICTED", so_thu_tu=29003,
            trich_yeu="Restricted outgoing document",
            pham_vi=PhamVi.HAN_CHE, hien_thi=True,
        )

        category = DanhMucTaiLieu.objects.create(
            stt_uu_tien=29001,
            ten_tai_lieu="C3 AI view test category",
            nguoi_lap=self.employee_a,
        )
        self.public_template = TaiLieuChiTiet.objects.create(
            dm_tai_lieu=category,
            tieu_de="C3 public metadata",
            ngay_dang=date(2026, 10, 20),
            hien_thi="TAT_CA",
        )
        self.unit_a_template = TaiLieuChiTiet.objects.create(
            dm_tai_lieu=category,
            tieu_de="C3 unit A metadata",
            ngay_dang=date(2026, 10, 20),
            hien_thi="NOI_BO_PHONG_BAN",
            don_vi_id=self.unit_a.pk,
        )
        self.unit_b_template = TaiLieuChiTiet.objects.create(
            dm_tai_lieu=category,
            tieu_de="C3 unit B metadata",
            ngay_dang=date(2026, 10, 20),
            hien_thi="NOI_BO_PHONG_BAN",
            don_vi_id=self.unit_b.pk,
        )

    def _readonly_ids(self, view_name, employee_id=None):
        with transaction.atomic(using="readonly"):
            with connections["readonly"].cursor() as cursor:
                identity = "" if employee_id is None else str(employee_id)
                cursor.execute(
                    "SELECT set_config('qlvb.employee_id', %s, TRUE)",
                    [identity],
                )
                cursor.execute(f"SELECT id FROM {view_name} ORDER BY id")
                return {row[0] for row in cursor.fetchall()}

    def _assert_read_denied(self, relation):
        with self.assertRaises(DatabaseError):
            with transaction.atomic(using="readonly"):
                with connections["readonly"].cursor() as cursor:
                    cursor.execute(f"SELECT * FROM {relation} LIMIT 1")
                    cursor.fetchall()

    def test_only_three_parent_views_are_readable(self):
        with connections["readonly"].cursor() as cursor:
            cursor.execute("SELECT current_user")
            self.assertEqual(cursor.fetchone()[0], "qlvb_readonly")
            for view in PARENT_VIEWS:
                cursor.execute(f"SELECT id FROM {view} LIMIT 0")

        for view in AUXILIARY_VIEWS:
            self._assert_read_denied(view)

        for table in (
            "accounts_employee",
            "organizations_donvi",
            "records_chitiettailieu",
            "documents_vanbanden",
            "documents_vanbandi",
            "documents_vanbanden_attachment",
            "documents_vanbandi_attachment",
            "documents_access_log",
            "documents_view_log",
            "records_chitiettailieu_attachment",
        ):
            self._assert_read_denied(table)

    def test_migration_clears_legacy_table_column_and_current_owner_default_grants(self):
        with connections["default"].cursor() as cursor:
            cursor.execute("GRANT SELECT ON ALL TABLES IN SCHEMA public TO qlvb_readonly")
            cursor.execute(
                "GRANT SELECT (id, don_vi_id, is_active, trang_thai, is_superuser) "
                "ON accounts_employee TO qlvb_readonly"
            )
            cursor.execute(
                "GRANT SELECT (id, ten) ON organizations_donvi TO qlvb_readonly"
            )
            cursor.execute(
                "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
                "GRANT SELECT ON TABLES TO qlvb_readonly"
            )
            for statement in MIGRATION.FORWARD_SQL:
                cursor.execute(statement)

            for relation in (
                "accounts_employee_groups",
                "auth_group_permissions",
                "auth_permission",
                "documents_vanbanden",
                "documents_vanbandi",
                "records_chitiettailieu",
                *AUXILIARY_VIEWS,
            ):
                cursor.execute(
                    "SELECT has_table_privilege('qlvb_readonly', %s, 'SELECT') "
                    "OR has_any_column_privilege('qlvb_readonly', %s, 'SELECT')",
                    [f"public.{relation}", f"public.{relation}"],
                )
                self.assertFalse(cursor.fetchone()[0], relation)

            for view in PARENT_VIEWS:
                cursor.execute(
                    "SELECT has_table_privilege('qlvb_readonly', %s, 'SELECT')",
                    [f"public.{view}"],
                )
                self.assertTrue(cursor.fetchone()[0], view)

            cursor.execute("CREATE TABLE public.c3_acl_future_table (id bigint)")
            cursor.execute(
                "SELECT has_table_privilege('qlvb_readonly', "
                "'public.c3_acl_future_table', 'SELECT')"
            )
            self.assertFalse(cursor.fetchone()[0])
            cursor.execute("DROP TABLE public.c3_acl_future_table")

        for relation in (
            "accounts_employee_groups",
            "auth_group_permissions",
            "auth_permission",
            "documents_vanbanden",
            "documents_vanbandi",
            "records_chitiettailieu",
            *AUXILIARY_VIEWS,
        ):
            self._assert_read_denied(relation)

    def test_document_views_exclude_hidden_and_restricted_rows(self):
        incoming = self._readonly_ids("ai_vanbanden")
        outgoing = self._readonly_ids("ai_vanbandi")
        self.assertIn(self.visible_incoming.pk, incoming)
        self.assertNotIn(self.hidden_incoming.pk, incoming)
        self.assertNotIn(self.restricted_incoming.pk, incoming)
        self.assertIn(self.visible_outgoing.pk, outgoing)
        self.assertNotIn(self.hidden_outgoing.pk, outgoing)
        self.assertNotIn(self.restricted_outgoing.pk, outgoing)

    def test_template_view_requires_matching_active_working_employee_unit(self):
        anonymous = self._readonly_ids("ai_tailieu")
        self.assertEqual(anonymous, {self.public_template.pk})

        unit_a = self._readonly_ids("ai_tailieu", self.employee_a.pk)
        self.assertEqual(unit_a, {self.public_template.pk, self.unit_a_template.pk})

        unit_b = self._readonly_ids("ai_tailieu", self.employee_b.pk)
        self.assertEqual(unit_b, {self.public_template.pk, self.unit_b_template.pk})

        inactive = self._readonly_ids("ai_tailieu", self.employee_inactive.pk)
        self.assertEqual(inactive, {self.public_template.pk})

        nonworking = self._readonly_ids("ai_tailieu", self.employee_nonworking.pk)
        self.assertEqual(nonworking, {self.public_template.pk})
