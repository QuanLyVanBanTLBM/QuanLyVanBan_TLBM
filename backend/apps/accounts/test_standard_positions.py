"""Danh mục 25 chức vụ chuẩn: thứ tự, một danh sách ở ba nơi, migration cho DB đã có dữ liệu, seed_db."""
import importlib
import os
import re
from pathlib import Path
from unittest import mock

from django.apps import apps as django_apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import connection
from django.db.models import Max
from django.test import TestCase

from accounts.models import Position
from accounts.standard_positions import (
    ADMIN_POSITION,
    AGENCY_LEADER_POSITION,
    CLERK_POSITION,
    STANDARD_POSITIONS,
    TEACHER_POSITIONS,
)
from organizations.models import DonVi, KhoiKhuVuc

migration = importlib.import_module("accounts.migrations.0009_standard_positions")
DDL_PATH = Path(settings.BASE_DIR).parent / "docs" / "common" / "database" / "release_DDL.sql"


class SchemaEditorStub:
    connection = connection


def run_migration():
    migration.apply_standard_positions(django_apps, SchemaEditorStub())


def ordered_names():
    return list(Position.objects.order_by("display_order").values_list("display_order", "name"))


class StandardPositionListTest(TestCase):
    def test_25_positions_numbered_1_to_25_without_duplicates(self):
        self.assertEqual([order for order, _ in STANDARD_POSITIONS], list(range(1, 26)))
        names = [name for _, name in STANDARD_POSITIONS]
        self.assertEqual(len(set(n.casefold() for n in names)), 25)

    def test_teacher_order_kept_and_old_positions_inserted_by_rank(self):
        names = [name for _, name in STANDARD_POSITIONS]
        self.assertEqual([n for n in names if n in TEACHER_POSITIONS], TEACHER_POSITIONS)
        self.assertEqual(len(TEACHER_POSITIONS), 22)
        self.assertEqual(names[0], ADMIN_POSITION)
        self.assertEqual(names.index(AGENCY_LEADER_POSITION), names.index("Tổng Giám đốc") + 1)
        self.assertEqual(names.index(CLERK_POSITION), names.index("Chuyên viên") + 1)

    def test_migration_keeps_a_frozen_copy_of_the_same_list(self):
        self.assertEqual([tuple(x) for x in migration.STANDARD_POSITIONS], STANDARD_POSITIONS)

    def test_release_ddl_seeds_the_same_list(self):
        ddl = DDL_PATH.read_text(encoding="utf-8")
        block = ddl[ddl.index("-- 3) Seed 25 Chức vụ chuẩn"):]
        block = block[: block.index("ORDER BY x.stt;")]
        seeded = [(int(order), name) for order, name in re.findall(r"\((\d+), '([^']+)'\)", block)]
        self.assertEqual(seeded, STANDARD_POSITIONS)


class MigratedDatabaseTest(TestCase):
    def test_database_built_by_migrations_has_the_25_positions_of_release_ddl(self):
        self.assertEqual(ordered_names(), STANDARD_POSITIONS)
        admin = get_user_model().objects.get(username="admin")
        self.assertEqual(admin.chuc_vu.name, ADMIN_POSITION)


class StandardPositionMigrationTest(TestCase):
    def setUp(self):
        # Dùng danh mục mẫu có sẵn; không xóa chức vụ đang được nhân viên mẫu tham chiếu.
        unit = DonVi.objects.create(khoi=KhoiKhuVuc.objects.create(ten="Khối chức vụ"), stt_uu_tien=(DonVi.objects.aggregate(m=Max("stt_uu_tien"))["m"] or 0) + 1, ten="Đơn vị chức vụ")
        old = ["Trưởng phòng", "Phó phòng", "Chuyên viên", "Nhân viên", "Văn thư", "Lãnh đạo cơ quan"]
        self.old = {ADMIN_POSITION: Position.objects.get(name=ADMIN_POSITION)}
        self.old.update({name: Position.objects.get(name=name) for name in old})
        next_order = Position.get_next_display_order()
        self.custom = Position.objects.create(display_order=next_order, name="Cộng tác viên")
        self.custom_two = Position.objects.create(display_order=next_order + 1, name="Thực tập sinh")
        User = get_user_model()
        self.clerk = User.objects.create_user(username="vt_old", password="x", don_vi=unit, chuc_vu=self.old["Văn thư"])
        self.leader = User.objects.create_user(username="ld_old", password="x", don_vi=unit, chuc_vu=self.old["Lãnh đạo cơ quan"])
        self.helper = User.objects.create_user(username="ctv_old", password="x", don_vi=unit, chuc_vu=self.custom)

    def test_missing_standard_position_is_added_without_deleting_legacy_row(self):
        legacy_position = self.old["Trưởng phòng"]
        legacy_position.name = "Trưởng phòng cũ"
        legacy_position.save(update_fields=["name"])

        run_migration()
        self.assertEqual(ordered_names()[:25], STANDARD_POSITIONS)
        legacy_position.refresh_from_db()
        self.assertEqual(legacy_position.name, "Trưởng phòng cũ")
        self.assertGreater(legacy_position.display_order, 25)

    def test_nothing_is_deleted_and_staff_keep_their_position_rows(self):
        ids_before = set(Position.objects.values_list("id", flat=True))
        run_migration()
        self.assertTrue(ids_before <= set(Position.objects.values_list("id", flat=True)))
        self.assertEqual(Position.objects.count(), 25 + 2)
        for user, position in ((self.clerk, self.old["Văn thư"]), (self.leader, self.old["Lãnh đạo cơ quan"]), (self.helper, self.custom)):
            user.refresh_from_db()
            self.assertEqual(user.chuc_vu_id, position.pk)
        self.assertEqual(Position.objects.get(pk=self.old["Văn thư"].pk).display_order, 22)
        self.assertEqual(Position.objects.get(pk=self.old["Lãnh đạo cơ quan"].pk).display_order, 6)
        self.assertEqual(Position.objects.get(pk=self.old["Quản trị viên"].pk).display_order, 1)

    def test_user_added_positions_follow_after_25_in_their_old_order(self):
        run_migration()
        self.assertEqual(ordered_names()[25:], [(26, "Cộng tác viên"), (27, "Thực tập sinh")])

    def test_running_twice_gives_the_same_result(self):
        run_migration()
        first = list(Position.objects.order_by("id").values_list("id", "display_order", "name"))
        run_migration()
        self.assertEqual(list(Position.objects.order_by("id").values_list("id", "display_order", "name")), first)

    def test_names_are_matched_case_insensitively_and_normalised(self):
        Position.objects.filter(pk=self.old["Trưởng phòng"].pk).update(name="  trưởng PHÒNG ")
        run_migration()
        self.assertEqual(Position.objects.filter(name__iexact="trưởng phòng").count(), 1)
        self.assertEqual(Position.objects.get(pk=self.old["Trưởng phòng"].pk).name, "Trưởng phòng")


class SeedDbPositionsTest(TestCase):
    def test_seed_db_creates_the_25_positions_once(self):
        with mock.patch.dict(os.environ, {"ADMIN_PASSWORD": "test-admin-password"}, clear=False):
            call_command("seed_db", verbosity=0)
            call_command("seed_db", verbosity=0)
        self.assertEqual(ordered_names(), STANDARD_POSITIONS)
        admin = get_user_model().objects.get(username="admin")
        self.assertEqual(admin.chuc_vu.name, ADMIN_POSITION)
