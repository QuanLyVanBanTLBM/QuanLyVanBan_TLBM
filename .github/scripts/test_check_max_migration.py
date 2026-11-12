"""Test logic thuần của check_max_migration (không nạp Django).

Dùng: python -m unittest discover -s .github/scripts -p "test_*.py"
"""
import unittest

import check_max_migration as chk


class ProblemsTest(unittest.TestCase):
    def test_single_leaf_matching_file_passes(self):
        self.assertEqual(chk.problems({"signing": ["0012_a"]}, {"signing": "0012_a"}), [])

    def test_two_leaves_fail_with_both_names(self):
        errors = chk.problems({"signing": ["0013_b", "0013_a"]}, {"signing": "0012_x"})
        self.assertEqual(len(errors), 1)
        self.assertIn("signing: có 2 migration lá (0013_a, 0013_b)", errors[0])

    def test_missing_file_fails(self):
        errors = chk.problems({"work": ["0007_a"]}, {"work": None})
        self.assertEqual(errors, ["work: thiếu migrations/max_migration.txt; chạy --write."])

    def test_stale_file_fails(self):
        errors = chk.problems({"work": ["0008_b"]}, {"work": "0007_a"})
        self.assertEqual(len(errors), 1)
        self.assertIn("ghi '0007_a' nhưng migration lá là '0008_b'", errors[0])

    def test_reports_every_app(self):
        errors = chk.problems({"a": ["1"], "b": ["2"]}, {"a": None, "b": "1"})
        self.assertEqual([e.split(":")[0] for e in errors], ["a", "b"])


if __name__ == "__main__":
    unittest.main()
