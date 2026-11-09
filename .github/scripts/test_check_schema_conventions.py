"""Test cho check_schema_conventions: logic thuần và chạy thật trên repo git tạm (nhánh đích giả lập).

Dùng: python -m unittest discover -s .github/scripts -p "test_*.py"
"""
import os
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

import check_schema_conventions as chk

REPO_ROOT = Path(__file__).resolve().parents[2]

HEADER = "| Ngày | PR | Đối tượng thay đổi | Lý do |\n|---|---|---|---|\n"
ROW_OLD = "| 2026-10-17 | #173 | Seed khối | Thứ tự không phụ thuộc collation |\n"
ROW_NEW = "| 2026-10-18 | #200 | Bảng mới | Cần cho module mới |\n"

BASELINE_BASE = (
    "# chú thích\n"
    "documents_vanbanden.ghi_chu: migration text() null=NO default=None | DDL text() null=YES default=None\n"
    "documents_vanbanden: thiếu constraint CHECK ((a > 0))\n"
    "ENUM e1: thiếu (A,B)\n"
    "SEED t1: DDL 2 dòng, migration thiếu 1 #aaaa, thừa 0 #-\n"
)


class DriftObjectTest(unittest.TestCase):
    def test_object_identity_per_format(self):
        cases = {
            "documents_vanbanden.ghi_chu: migration x | DDL y": "documents_vanbanden.ghi_chu",
            "documents_vanbanden.ghi_chu: thiếu cột, DDL: text() null=NO default=None": "documents_vanbanden.ghi_chu",
            "t.c: cột không có trong DDL": "t.c",
            "ENUM e1: thiếu (A,B)": "ENUM e1",
            "ENUM e1: migration (A) | DDL (A,B)": "ENUM e1",
            "VIEW v: khác định nghĩa so với DDL": "VIEW v",
            "FUNCTION f(a integer, b text): thiếu": "FUNCTION f(a integer, b text)",
            "TRIGGER t.trg: trạng thái migration D | DDL O": "TRIGGER t.trg",
            "SEED t1: DDL 2 dòng, migration thiếu 1 #aaaa, thừa 0 #-": "SEED t1",
            "t: thiếu bảng": "t: thiếu bảng",
            "t: bảng không có trong DDL": "t: bảng không có trong DDL",
            "t: thiếu constraint CHECK ((a > 0))": "t: thiếu constraint CHECK ((a > 0))",
            "t: constraint không có trong DDL CHECK ((a > 0))": "t: constraint không có trong DDL CHECK ((a > 0))",
            "t: thiếu index USING btree (a)": "t: thiếu index USING btree (a)",
            "t: index UNIQUE không có trong DDL UNIQUE USING btree (a)": "t: index UNIQUE không có trong DDL UNIQUE USING btree (a)",
        }
        for line, expected in cases.items():
            self.assertEqual(chk.drift_object(line), expected, line)

    def test_unknown_format_is_rejected(self):
        for line in ("không có dấu hai chấm", "t: nội dung lạ", "KIND x: y"):
            with self.assertRaises(ValueError, msg=line):
                chk.drift_object(line)

    def test_every_line_of_current_baseline_has_a_known_format(self):
        text = (REPO_ROOT / chk.BASELINE_PATH).read_text(encoding="utf-8")
        lines = chk.baseline_lines(text)
        for line in lines:
            chk.drift_object(line)


class BaselineLogicTest(unittest.TestCase):
    def test_reduced_baseline_passes(self):
        head = BASELINE_BASE.replace("ENUM e1: thiếu (A,B)\n", "")
        self.assertEqual(chk.new_drift_objects(BASELINE_BASE, head), [])

    def test_new_object_fails_and_is_listed(self):
        head = BASELINE_BASE + "ENUM e2: thiếu (X)\nt2.c: thiếu cột, DDL: int4() null=NO default=None\n"
        self.assertEqual(chk.new_drift_objects(BASELINE_BASE, head), ["ENUM e2", "t2.c"])

    def test_new_constraint_on_existing_table_is_a_new_object(self):
        head = BASELINE_BASE + "documents_vanbanden: thiếu constraint CHECK ((b > 0))\n"
        self.assertEqual(
            chk.new_drift_objects(BASELINE_BASE, head), ["documents_vanbanden: thiếu constraint CHECK ((b > 0))"]
        )

    def test_changed_detail_of_existing_object_passes(self):
        head = BASELINE_BASE.replace("#aaaa", "#bbbb").replace("migration text()", "migration varchar(5)")
        self.assertEqual(chk.new_drift_objects(BASELINE_BASE, head), [])

    def test_empty_or_comment_only_baseline_passes_against_existing_base(self):
        for head in ("", "# không còn sai lệch\n\n"):
            with self.subTest(head=head):
                self.assertEqual(chk.new_drift_objects(BASELINE_BASE, head), [])


class ChangelogLogicTest(unittest.TestCase):
    def test_added_rows_counts_only_dated_table_rows(self):
        base = HEADER + ROW_OLD
        self.assertEqual(chk.added_changelog_rows(base, base), [])
        self.assertEqual(chk.added_changelog_rows(base, HEADER + ROW_NEW + ROW_OLD), [ROW_NEW.strip()])
        self.assertEqual(chk.added_changelog_rows(base, base + "ghi chú tự do\n"), [])

    def test_line_endings_do_not_count_as_ddl_change(self):
        self.assertFalse(chk.ddl_changed("a\nb\n", "a\r\nb\r\n"))
        self.assertTrue(chk.ddl_changed("a\nb\n", "a\nc\n"))


class GitCheckTest(unittest.TestCase):
    """Dựng repo tạm có nhánh main (đích) và nhánh PR, chạy check thật."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = Path(self._tmp.name)
        self._cwd = os.getcwd()
        os.chdir(self.repo)
        self.addCleanup(os.chdir, self._cwd)
        self.git("init", "-q", "-b", "main")
        self.write(chk.DDL_PATH, "CREATE TABLE a (id int);\n")
        self.write(chk.CHANGELOG_PATH, HEADER + ROW_OLD)
        self.write(chk.BASELINE_PATH, BASELINE_BASE)
        self.commit("base")
        self.git("checkout", "-q", "-b", "pr")

    def git(self, *args):
        subprocess.run(
            ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
            cwd=self.repo, check=True, capture_output=True,
        )

    def write(self, path, text):
        target = self.repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8", newline="")

    def commit(self, message):
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)

    def test_changelog_ddl_changed_with_row_passes(self):
        self.write(chk.DDL_PATH, "CREATE TABLE a (id int, b int);\n")
        self.write(chk.CHANGELOG_PATH, HEADER + ROW_NEW + ROW_OLD)
        self.commit("pr")
        self.assertEqual(chk.check_changelog("main"), 0)

    def test_changelog_ddl_changed_without_row_fails(self):
        self.write(chk.DDL_PATH, "CREATE TABLE a (id int, b int);\n")
        self.commit("pr")
        with redirect_stdout(StringIO()):
            self.assertEqual(chk.check_changelog("main"), 1)

    def test_changelog_ddl_changed_with_non_row_edit_fails(self):
        self.write(chk.DDL_PATH, "CREATE TABLE a (id int, b int);\n")
        self.write(chk.CHANGELOG_PATH, HEADER + ROW_OLD + "ghi chú thêm\n")
        self.commit("pr")
        with redirect_stdout(StringIO()):
            self.assertEqual(chk.check_changelog("main"), 1)

    def test_changelog_ddl_unchanged_passes(self):
        self.write("README.md", "x\n")
        self.commit("pr")
        self.assertEqual(chk.check_changelog("main"), 0)

    def test_baseline_reduced_passes(self):
        self.write(chk.BASELINE_PATH, BASELINE_BASE.replace("ENUM e1: thiếu (A,B)\n", ""))
        self.commit("pr")
        self.assertEqual(chk.check_baseline("main"), 0)

    def test_baseline_new_object_fails(self):
        self.write(chk.BASELINE_PATH, BASELINE_BASE + "ENUM e2: thiếu (X)\n")
        self.commit("pr")
        with redirect_stdout(StringIO()):
            self.assertEqual(chk.check_baseline("main"), 1)

    def test_baseline_changed_detail_passes(self):
        self.write(chk.BASELINE_PATH, BASELINE_BASE.replace("#aaaa", "#bbbb"))
        self.commit("pr")
        self.assertEqual(chk.check_baseline("main"), 0)

    def test_baseline_empty_or_comment_only_passes(self):
        for baseline in ("", "# không còn sai lệch\n\n"):
            with self.subTest(baseline=baseline):
                self.write(chk.BASELINE_PATH, baseline)
                self.commit("pr")
                self.assertEqual(chk.check_baseline("main"), 0)

    def test_no_base_ref_is_skipped(self):
        self.assertEqual(chk.main(["x", "changelog", ""]), 0)
        self.assertEqual(chk.main(["x", "baseline"]), 0)


if __name__ == "__main__":
    unittest.main()
