import importlib
import unittest
from datetime import date, time

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase

from meetings.models import MeetingBooking, MeetingRoom
from organizations.models import DonVi, KhoiKhuVuc

migration = importlib.import_module("meetings.migrations.0003_department_fk_set_null_ddl")


def _next_unit_priority():
    return (DonVi.objects.order_by("-stt_uu_tien").values_list("stt_uu_tien", flat=True).first() or 0) + 1


@unittest.skipUnless(connection.vendor == "postgresql", "Cấu trúc theo DDL chỉ kiểm trên PostgreSQL")
class MeetingBookingForeignKeyMatchesDdlTests(TestCase):
    def test_department_fk_sets_null_in_database(self):
        with connection.cursor() as cursor:
            definitions = [
                row[2] for row in migration._foreign_keys(cursor) if row[1] == ["department_id"]
            ]
        self.assertEqual(len(definitions), 1)
        self.assertIn("ON DELETE SET NULL", definitions[0])

    def test_raw_sql_unit_delete_preserves_booking_and_clears_department(self):
        region = KhoiKhuVuc.objects.create(ten="C1B khối họp")
        priority = _next_unit_priority()
        home = DonVi.objects.create(khoi=region, stt_uu_tien=priority, ten="C1B đơn vị chủ trì")
        removable = DonVi.objects.create(khoi=region, stt_uu_tien=priority + 1, ten="C1B đơn vị xóa")
        organizer = get_user_model().objects.create_user(username="c1b_meeting_fk", password="unused", don_vi=home)
        room = MeetingRoom.objects.create(name="C1B phòng FK", location="Tầng 1", capacity=5)
        booking = MeetingBooking.objects.create(
            room=room,
            organizer=organizer,
            department=removable,
            title="C1B họp FK",
            date=date(2026, 10, 20),
            start_time=time(9, 0),
            end_time=time(10, 0),
            attendees_count=3,
        )

        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM organizations_donvi WHERE id = %s", [removable.pk])
        booking.refresh_from_db()
        self.assertIsNone(booking.department_id)
        self.assertTrue(MeetingBooking.objects.filter(pk=booking.pk).exists())

    def test_orphaned_department_reference_fails_closed(self):
        region = KhoiKhuVuc.objects.create(ten="C1B khối meeting orphan")
        priority = _next_unit_priority()
        home = DonVi.objects.create(khoi=region, stt_uu_tien=priority, ten="C1B đơn vị meeting chủ trì")
        removable = DonVi.objects.create(khoi=region, stt_uu_tien=priority + 1, ten="C1B đơn vị meeting")
        organizer = get_user_model().objects.create_user(
            username="c1b_meeting_orphan", password="unused", don_vi=home
        )
        room = MeetingRoom.objects.create(name="C1B phòng orphan", location="Tầng 2", capacity=5)
        booking = MeetingBooking.objects.create(
            room=room,
            organizer=organizer,
            department=removable,
            title="C1B họp orphan",
            date=date(2026, 10, 21),
            start_time=time(9, 0),
            end_time=time(10, 0),
            attendees_count=3,
        )
        with connection.cursor() as cursor:
            cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
            fk = next(row[0] for row in migration._foreign_keys(cursor) if row[1] == ["department_id"])
            cursor.execute(
                f"ALTER TABLE meetings_meetingbooking DROP CONSTRAINT {connection.ops.quote_name(fk)}"
            )
            cursor.execute(
                "UPDATE meetings_meetingbooking SET department_id = %s WHERE id = %s",
                [9223372036854770000, booking.pk],
            )

        with connection.schema_editor() as schema_editor:
            with self.assertRaisesRegex(RuntimeError, r"meetings_meetingbooking.department_id has 1 orphan"):
                migration.set_null_department_fk(None, schema_editor)

        with connection.cursor() as cursor:
            cursor.execute("SELECT department_id FROM meetings_meetingbooking WHERE id = %s", [booking.pk])
            self.assertEqual(cursor.fetchone()[0], 9223372036854770000)

    def test_migration_is_idempotent(self):
        with connection.schema_editor() as schema_editor:
            migration.set_null_department_fk(None, schema_editor)
            migration.set_null_department_fk(None, schema_editor)
