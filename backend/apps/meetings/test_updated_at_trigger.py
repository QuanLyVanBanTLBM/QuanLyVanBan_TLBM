from datetime import timedelta
from uuid import uuid4

from django.db import connection
from django.test import TestCase
from django.utils import timezone

from meetings.models import MeetingRoom


class MeetingRoomUpdatedAtTriggerTest(TestCase):
    def test_raw_update_refreshes_updated_at(self):
        room = MeetingRoom.objects.create(
            name=f"Trigger {uuid4().hex[:12]}",
            location="Test",
            capacity=1,
        )
        old = timezone.now() - timedelta(days=2)

        with connection.cursor() as cursor:
            cursor.execute("UPDATE meetings_meetingroom SET updated_at = %s WHERE id = %s", [old, room.pk])
            cursor.execute(
                "UPDATE meetings_meetingroom SET amenities = 'updated by trigger test' WHERE id = %s",
                [room.pk],
            )

        self.assertGreater(MeetingRoom.objects.get(pk=room.pk).updated_at, old)
