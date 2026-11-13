from pathlib import Path
import re
import unittest


WORKFLOW_PATH = Path(__file__).resolve().parents[3] / ".github" / "workflows" / "birthday-email.yml"


class BirthdaySchedulerConfigurationTests(unittest.TestCase):
    def test_staggered_recovery_schedule_is_tagged_for_recovery(self):
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
        schedules = re.findall(r'^\s*-\s+cron:\s+["\']([^"\']+)["\']', workflow, re.MULTILINE)

        self.assertEqual(schedules, ["7 0 * * *", "37 0 * * *"])
        self.assertIn('== "37 0 * * *"', workflow)
        self.assertIn("trigger_source=RECOVERY", workflow)
        self.assertIn('"--trigger-source=$trigger_source"', workflow)


if __name__ == "__main__":
    unittest.main()
