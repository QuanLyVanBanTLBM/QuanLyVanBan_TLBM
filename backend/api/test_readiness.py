from pathlib import Path
from unittest.mock import patch

from django.conf import settings as django_settings
from django.db import OperationalError
from django.test import Client, SimpleTestCase, override_settings

from config.settings import release_id_from_source


class ReadinessTests(SimpleTestCase):
    def setUp(self):
        self._settings = override_settings(ALLOWED_HOSTS=["testserver"])
        self._settings.enable()
        self.client = Client()

    def tearDown(self):
        self._settings.disable()
        super().tearDown()

    @patch("api.views.connection")
    def test_readiness_queries_database_and_returns_loaded_release(self, cursor):
        with patch.object(django_settings, "RELEASE_ID", "loaded-release"):
            response = self.client.get("/api/health/ready/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ready", "release": "loaded-release"})
        cursor.cursor.return_value.__enter__.return_value.execute.assert_called_once_with("SELECT 1")

    @patch("api.views.connection")
    def test_database_failure_is_unready_without_error_details(self, cursor):
        cursor.cursor.side_effect = OperationalError("db-password-must-not-leak")
        response = self.client.get("/api/health/ready/")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"status": "not_ready"})
        self.assertNotIn(b"db-password-must-not-leak", response.content)

    @patch("api.views.connection")
    def test_process_keeps_reporting_release_captured_before_current_moves(self, cursor):
        source = Path("/srv/qlvb/current/backend/config/settings.py")
        with patch("config.settings.Path.resolve") as resolve:
            resolve.side_effect = [
                Path("/srv/qlvb/releases/old-release/backend/config/settings.py"),
                Path("/srv/qlvb/releases/new-release/backend/config/settings.py"),
            ]
            captured_release = release_id_from_source(source)
            resolved_after_switch = release_id_from_source(source)

        self.assertEqual(captured_release, "old-release")
        self.assertEqual(resolved_after_switch, "new-release")
        with patch.object(django_settings, "RELEASE_ID", captured_release):
            response = self.client.get("/api/health/ready/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["release"], captured_release)

    @patch("api.views.connection")
    def test_post_is_not_a_readiness_probe(self, cursor):
        response = self.client.post("/api/health/ready/")

        self.assertEqual(response.status_code, 405)
        cursor.cursor.assert_not_called()
