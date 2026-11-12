import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / ".github" / "scripts" / "compare_schema_ddl.py"
SPEC = importlib.util.spec_from_file_location("compare_schema_ddl", SCRIPT)
COMPARATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(COMPARATOR)


class SigningCheckComparatorTests(unittest.TestCase):
    def test_exact_signer_check_term_reordering_is_equivalent(self):
        ddl = (
            "CHECK ((((chuc_vu_id IS NULL) AND (nguoi_ky_id IS NOT NULL)) OR "
            "((chuc_vu_id IS NOT NULL) AND (nguoi_ky_id IS NULL))))"
        )
        migration = (
            "CHECK ((((nguoi_ky_id IS NOT NULL) AND (chuc_vu_id IS NULL)) OR "
            "((nguoi_ky_id IS NULL) AND (chuc_vu_id IS NOT NULL))))"
        )

        self.assertEqual(COMPARATOR.norm_check(ddl), COMPARATOR.norm_check(migration))

    def test_changed_boolean_operator_is_not_normalized(self):
        ddl = (
            "CHECK ((((chuc_vu_id IS NULL) AND (nguoi_ky_id IS NOT NULL)) OR "
            "((chuc_vu_id IS NOT NULL) AND (nguoi_ky_id IS NULL))))"
        )
        negative = ddl.replace(" OR ", " AND ", 1)

        self.assertNotEqual(COMPARATOR.norm_check(ddl), COMPARATOR.norm_check(negative))
        self.assertEqual(COMPARATOR.norm_check(negative), negative)


if __name__ == "__main__":
    unittest.main()
