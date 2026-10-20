"""FK department_id của đặt phòng họp phải có ON DELETE SET NULL ở mức DB như release_DDL.sql."""
import importlib
import unittest
from datetime import date, time

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase

from meetings.models import MeetingBooking, MeetingRoom
from organizations.models import DonVi, KhoiKhuVuc

migration = importlib.import_module("meetings.migrations.0003_department_fk_set_null_ddl")


@unittest.skipUnless(connection.vendor == "postgresql", "Cấu trúc theo DDL chỉ kiểm trên PostgreSQL")
class MeetingBookingForeignKeyMatchesDdlTests(TestCase):
    def test_department_fk_sets_null_in_database(self):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT pg_get_constraintdef(c.oid) FROM pg_constraint c "
                "WHERE c.conrelid = 'meetings_meetingbooking'::regclass AND c.contype = 'f' "
                "AND pg_get_constraintdef(c.oid) LIKE 'FOREIGN KEY (department_id)%'"
            )
            definitions = [row[0] for row in cursor.fetchall()]
        self.assertEqual(len(definitions), 1)
        self.assertIn("ON DELETE SET NULL", definitions[0])

    def test_deleting_unit_with_raw_sql_keeps_booking_and_clears_department(self):
        region = KhoiKhuVuc.objects.create(ten="Khối họp")
        home = DonVi.objects.create(khoi=region, stt_uu_tien=1, ten="Đơn vị chủ trì")
        removable = DonVi.objects.create(khoi=region, stt_uu_tien=2, ten="Đơn vị sẽ xóa")
        organizer = get_user_model().objects.create_user(username="fk_dat_phong", password="x", don_vi=home)
        room = MeetingRoom.objects.create(name="Phòng FK", location="Tầng 1", capacity=5)
        booking = MeetingBooking.objects.create(
            room=room, organizer=organizer, department=removable, title="Họp FK",
            date=date(2026, 10, 20), start_time=time(9, 0), end_time=time(10, 0), attendees_count=3,
        )
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM organizations_donvi WHERE id = %s", [removable.id])
        booking.refresh_from_db()
        self.assertIsNone(booking.department_id)

    def test_migration_is_idempotent(self):
        with connection.schema_editor() as schema_editor:
            migration.set_null_department_fk(None, schema_editor)
            migration.set_null_department_fk(None, schema_editor)
