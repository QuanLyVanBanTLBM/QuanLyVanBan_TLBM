from datetime import timedelta
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.utils import timezone


class EmployeeUpdatedAtTriggerTest(TestCase):
    def test_raw_update_refreshes_updated_at(self):
        user = get_user_model().objects.create_user(
            username=f"trigger_{uuid4().hex[:12]}",
            email=f"{uuid4().hex[:12]}@example.test",
            ho_ten="Trigger test employee",
        )
        old = timezone.now() - timedelta(days=2)

        with connection.cursor() as cursor:
            cursor.execute("UPDATE accounts_employee SET updated_at = %s WHERE id = %s", [old, user.pk])
            cursor.execute(
                "UPDATE accounts_employee SET is_public = NOT is_public WHERE id = %s",
                [user.pk],
            )

        updated_at = get_user_model().objects.values_list("updated_at", flat=True).get(pk=user.pk)
        self.assertGreater(updated_at, old)
