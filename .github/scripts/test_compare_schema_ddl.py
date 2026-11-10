"""Test cho compare_schema_ddl.drift: mỗi ca dựng hai DB tạm trên PostgreSQL rồi kiểm tra lệch.

Dùng: python -m unittest discover -s .github/scripts -p "test_*.py"
Kết nối lấy từ POSTGRES_HOST/PORT/USER/PASSWORD (cần quyền CREATEDB).
"""
import unittest
import uuid

import psycopg
from psycopg import sql

import compare_schema_ddl as cmp

BASE = """
CREATE TABLE seed_t (id serial PRIMARY KEY, name text NOT NULL);
INSERT INTO seed_t (name) VALUES ('a'), ('b');
CREATE TABLE trig_t (id serial PRIMARY KEY, name text);
CREATE FUNCTION trg_fn() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RETURN NEW; END $$;
CREATE TRIGGER trg_t BEFORE INSERT ON trig_t FOR EACH ROW EXECUTE FUNCTION trg_fn();
CREATE FUNCTION lit_fn() RETURNS text LANGUAGE sql AS $$ SELECT 'x y'::text $$;
CREATE VIEW lit_v AS SELECT 'x y'::text AS v;
"""

RBAC_BASE = """
CREATE TABLE django_content_type (id serial PRIMARY KEY, app_label text NOT NULL, model text NOT NULL);
INSERT INTO django_content_type (id, app_label, model) VALUES
    ({content_type_id}, '{app_label}', '{content_type_model}');
CREATE TABLE auth_group (id serial PRIMARY KEY, name text NOT NULL, ma_nhom_quyen text UNIQUE);
INSERT INTO auth_group (id, name, ma_nhom_quyen) VALUES
    ({group_id}, 'Văn thư', 'VAN_THU'),
    ({custom_group_id}, 'Nhóm tùy chỉnh', NULL);
CREATE TABLE auth_permission (
    id serial PRIMARY KEY, name text NOT NULL, codename text NOT NULL UNIQUE,
    module_ten text NOT NULL, content_type_id integer
);
INSERT INTO auth_permission (id, name, codename, module_ten, content_type_id) VALUES
    ({permission_id}, 'Xem văn bản đến', 'view_vanbanden', 'Văn bản đến', {content_type_id}),
    ({other_permission_id}, 'Sửa văn bản đến', 'change_vanbanden', 'Văn bản đến', {content_type_id});
CREATE TABLE auth_group_permissions (
    group_id integer NOT NULL, permission_id integer NOT NULL, PRIMARY KEY (group_id, permission_id)
);
INSERT INTO auth_group_permissions (group_id, permission_id) VALUES
    ({group_id}, {grant_permission_id}),
    ({custom_group_id}, {custom_grant_permission_id});
"""


def maintenance():
    return cmp.connect("postgres")


class RestoredCheckFormTest(unittest.TestCase):
    def norm(self, definition):
        return cmp.norm_check(cmp.norm(definition))

    def test_pg_restore_array_forms_equal_direct_forms(self):
        direct = "CHECK (((pham_vi)::text = ANY ((ARRAY['A'::character varying, 'B'::character varying])::text[])))"
        restored = "CHECK (((pham_vi)::text = ANY (ARRAY[('A'::character varying)::text, ('B'::character varying)::text])))"
        self.assertEqual(self.norm(direct), self.norm(restored))
        direct_not = "CHECK ((((x)::text <> ALL ((ARRAY['A'::character varying])::text[])) OR (u IS NOT NULL)))"
        restored_not = "CHECK (((NOT ((x)::text = ANY (ARRAY[('A'::character varying)::text]))) OR (u IS NOT NULL)))"
        self.assertEqual(self.norm(direct_not), self.norm(restored_not))

    def test_different_values_or_operators_stay_different(self):
        restored = "CHECK (((pham_vi)::text = ANY (ARRAY[('A'::character varying)::text, ('B'::character varying)::text])))"
        self.assertNotEqual(self.norm(restored), self.norm(restored.replace("'B'", "'C'")))
        self.assertNotEqual(self.norm(restored), self.norm(restored.replace("= ANY", "<> ALL")))


class DriftTest(unittest.TestCase):
    def setUp(self):
        self.dbs = []

    def tearDown(self):
        with maintenance() as conn:
            conn.autocommit = True
            for db in self.dbs:
                conn.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(db)))

    def make_db(self, script, icu_locale="vi-VN"):
        name = "cmp_test_" + uuid.uuid4().hex[:10]
        with maintenance() as conn:
            conn.autocommit = True
            conn.execute(
                sql.SQL(
                    "CREATE DATABASE {} TEMPLATE template0 ENCODING 'UTF8' "
                    "LOCALE_PROVIDER icu ICU_LOCALE {} LOCALE 'C.UTF-8'"
                ).format(sql.Identifier(name), sql.Literal(icu_locale))
            )
        self.dbs.append(name)
        with cmp.connect(name) as conn:
            conn.execute(script)
        return name

    def drift(self, migration_script, ddl_script=BASE):
        return cmp.drift(self.make_db(migration_script), self.make_db(ddl_script))

    def test_different_collation_fails_before_comparing(self):
        with self.assertRaises(SystemExit) as raised:
            cmp.drift(self.make_db(BASE, icu_locale="en-US"), self.make_db(BASE))
        self.assertIn("khác collation", str(raised.exception))

    def test_identical_dbs_have_no_drift(self):
        self.assertEqual(self.drift(BASE), [])

    def test_disabled_trigger_is_reported(self):
        found = self.drift(BASE + "ALTER TABLE trig_t DISABLE TRIGGER trg_t;")
        self.assertEqual(found, ["TRIGGER trig_t.trg_t: trạng thái migration D | DDL O"])

    def test_function_differing_only_in_literal_whitespace(self):
        found = self.drift(BASE.replace("SELECT 'x y'::text $$", "SELECT 'x  y'::text $$"))
        self.assertEqual(found, ["FUNCTION lit_fn(): khác định nghĩa so với DDL"])

    def test_view_differing_only_in_literal_whitespace(self):
        found = self.drift(BASE.replace("SELECT 'x y'::text AS v", "SELECT 'x  y'::text AS v"))
        self.assertEqual(found, ["VIEW lit_v: khác định nghĩa so với DDL"])

    def test_seed_value_change_keeps_counts_but_changes_fingerprint(self):
        changed_b = self.drift(BASE.replace("('a'), ('b')", "('a'), ('c')"))
        changed_d = self.drift(BASE.replace("('a'), ('b')", "('a'), ('d')"))
        self.assertEqual(len(changed_b), 1)
        self.assertEqual(len(changed_d), 1)
        self.assertTrue(changed_b[0].startswith("SEED seed_t: DDL 2 dòng, migration thiếu 1 #"))
        self.assertIn(", thừa 1 #", changed_b[0])
        self.assertNotEqual(changed_b[0], changed_d[0])

    def test_rbac_seed_uses_semantics_instead_of_generated_ids(self):
        ddl = RBAC_BASE.format(
            content_type_id=4, group_id=8, custom_group_id=9, permission_id=12,
            other_permission_id=13, grant_permission_id=12, custom_grant_permission_id=13,
            app_label="documents", content_type_model="vanbanden",
        )
        migration = RBAC_BASE.format(
            content_type_id=41, group_id=82, custom_group_id=83, permission_id=123,
            other_permission_id=124, grant_permission_id=123, custom_grant_permission_id=124,
            app_label="documents", content_type_model="vanbanden",
        )
        self.assertEqual(self.drift(BASE + ddl, BASE + migration), [])

    def test_rbac_comparator_reports_changed_semantic_grant_set(self):
        ddl = RBAC_BASE.format(
            content_type_id=4, group_id=8, custom_group_id=9, permission_id=12,
            other_permission_id=13, grant_permission_id=12, custom_grant_permission_id=13,
            app_label="documents", content_type_model="vanbanden",
        )
        migration = RBAC_BASE.format(
            content_type_id=41, group_id=82, custom_group_id=83, permission_id=123,
            other_permission_id=124, grant_permission_id=123, custom_grant_permission_id=123,
            app_label="documents", content_type_model="vanbanden",
        )
        found = self.drift(BASE + ddl, BASE + migration)
        self.assertEqual(len(found), 1)
        self.assertTrue(found[0].startswith("SEED auth_group_permissions:"))

    def test_rbac_comparator_detects_content_type_natural_key_change(self):
        ddl = RBAC_BASE.format(
            content_type_id=4, group_id=8, custom_group_id=9, permission_id=12,
            other_permission_id=13, grant_permission_id=12, custom_grant_permission_id=13,
            app_label="documents", content_type_model="vanbanden",
        )
        migration = RBAC_BASE.format(
            content_type_id=41, group_id=82, custom_group_id=83, permission_id=123,
            other_permission_id=124, grant_permission_id=123, custom_grant_permission_id=124,
            app_label="records", content_type_model="tailieu",
        )
        found = self.drift(BASE + ddl, BASE + migration)
        self.assertEqual(len(found), 1)
        self.assertTrue(found[0].startswith("SEED auth_permission:"))

    def test_trim_check_equivalent_to_btrim_is_not_reported(self):
        ddl = BASE + "ALTER TABLE trig_t ADD CONSTRAINT c CHECK (name IS NULL OR btrim(name) <> '');"
        migration = BASE + "ALTER TABLE trig_t ADD CONSTRAINT c CHECK (name IS NULL OR NOT (TRIM(BOTH FROM name) = ''));"
        self.assertEqual(self.drift(migration, ddl), [])

    def test_trim_check_with_different_logic_is_still_reported(self):
        ddl = BASE + "ALTER TABLE trig_t ADD CONSTRAINT c CHECK (name IS NULL OR btrim(name) <> '');"
        migration = BASE + "ALTER TABLE trig_t ADD CONSTRAINT c CHECK (name IS NULL OR NOT (TRIM(BOTH FROM name) = 'x'));"
        found = self.drift(migration, ddl)
        self.assertEqual(len(found), 2)
        self.assertTrue(found[0].startswith("trig_t: thiếu constraint CHECK"))
        self.assertTrue(found[1].startswith("trig_t: constraint không có trong DDL CHECK"))

    def test_table_with_data_only_in_migration_db(self):
        found = self.drift(BASE + "INSERT INTO trig_t (name) VALUES ('x');")
        self.assertEqual(len(found), 1)
        self.assertTrue(found[0].startswith("SEED trig_t: DDL 0 dòng, migration thiếu 0 #-, thừa 1 #"))


if __name__ == "__main__":
    unittest.main()
