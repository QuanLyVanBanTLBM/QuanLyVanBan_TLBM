from pathlib import Path
import re
import unittest


WORKFLOW_PATH = Path(__file__).resolve().parents[3] / ".github" / "workflows" / "birthday-email.yml"


class BirthdaySchedulerConfigurationTests(unittest.TestCase):
    def test_0700_schedule_and_staggered_recovery_are_tagged_correctly(self):
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
        schedules = re.findall(r'^\s*-\s+cron:\s+["\']([^"\']+)["\']', workflow, re.MULTILINE)

        self.assertEqual(schedules, ["0 0 * * *", "37 0 * * *"])
        self.assertIn("Asia/Ho_Chi_Minh (UTC+7)", workflow)
        self.assertIn('if [[ "$event_schedule" == "37 0 * * *" ]]; then\n              trigger_source=RECOVERY', workflow)
        self.assertIn('elif [[ "$event_schedule" == "0 0 * * *" ]]; then\n              scheduled_slot=07:00', workflow)
        self.assertIn("scheduled_slot=07:37", workflow)
        self.assertIn('TZ=Asia/Ho_Chi_Minh date --date="$created_at"', workflow)
        self.assertIn("trigger_source=SCHEDULED", workflow)
        self.assertIn('"--trigger-source=$1"', workflow)
        self.assertIn('"--scheduled-slot=$4"', workflow)
        self.assertIn('"--github-run-id=$5" "--github-run-attempt=$6"', workflow)
        self.assertIn("github.ref == 'refs/heads/staging'", workflow)

    def test_workflow_preserves_manual_recovery_timeout_lock_and_nonconcurrency(self):
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("timeout-minutes: 120", workflow)
        self.assertIn('flock --wait 3600 "$BASE/.deploy.lock"', workflow)
        self.assertNotRegex(workflow, r"(?m)^concurrency:")


if __name__ == "__main__":
    unittest.main()
