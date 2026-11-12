"""Kiểm tra hai quy ước schema của AGENTS.md mục 5 trên PR, so với nhánh đích.

  changelog <base_ref>  nếu nội dung release_DDL.sql đổi so với nhánh đích thì DDL_CHANGELOG.md phải có
                        ít nhất một dòng bảng mới (ngày, PR, đối tượng thay đổi, lý do).
  baseline <base_ref>   schema_drift_baseline.txt chỉ được giảm: so theo đối tượng lệch với baseline của
                        nhánh đích, đối tượng lệch mới thì fail; chi tiết của đối tượng đã có được phép đổi.

<base_ref> là ref của nhánh đích đã fetch (ví dụ origin/staging). Rỗng thì bỏ qua có thông báo (push, schedule).
Chạy từ thư mục gốc repo. Không phụ thuộc thư viện ngoài.
"""
import re
import subprocess
import sys
from collections import Counter

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")  # thông báo tiếng Việt, tránh lỗi mã hoá trên console Windows

DDL_PATH ="docs/common/database/release_DDL.sql"
CHANGELOG_PATH = "docs/common/database/DDL_CHANGELOG.md"
BASELINE_PATH = "docs/common/database/schema_drift_baseline.txt"

CHANGELOG_ROW = re.compile(r"^\|\s*\d{4}-\d{2}-\d{2}\s*\|")

# Dòng baseline do compare_schema_ddl.py sinh, theo bốn nhóm định danh:
#   "KIND tên: chi tiết"  (ENUM, VIEW, FUNCTION, TRIGGER, SEED)  -> định danh "KIND tên"
#   "bảng.cột: chi tiết"                                         -> định danh "bảng.cột"
#   "bảng: thiếu bảng" / "bảng: bảng không có trong DDL"          -> cả dòng
#   "bảng: thiếu|... constraint|index ..."                       -> cả dòng (nội dung là định danh)
OBJECT_KINDS = ("ENUM", "VIEW", "FUNCTION", "TRIGGER", "SEED")
COLUMN_HEAD = re.compile(r"[A-Za-z_]\w*\.[A-Za-z_]\w*")
TABLE_HEAD = re.compile(r"[A-Za-z_]\w*")
TABLE_LEVEL_DETAIL = re.compile(
    r"thiếu bảng$|bảng không có trong DDL$"
    r"|thiếu constraint \S|constraint không có trong DDL \S"
    r"|thiếu index \S|index UNIQUE không có trong DDL \S"
)


def drift_object(line):
    """Định danh đối tượng lệch của một dòng baseline; ValueError nếu dòng không thuộc format nào đã biết."""
    head, sep, detail = line.partition(": ")
    if not sep:
        raise ValueError(f"Dòng baseline không có dạng '<đối tượng>: <chi tiết>': {line!r}")
    kind, _, name = head.partition(" ")
    if kind in OBJECT_KINDS and name:
        return head
    if COLUMN_HEAD.fullmatch(head):
        return head
    if TABLE_HEAD.fullmatch(head) and TABLE_LEVEL_DETAIL.match(detail):
        return line
    raise ValueError(f"Dòng baseline có format chưa được xử lý: {line!r}")


def baseline_lines(text):
    return [line for line in text.splitlines() if line.strip() and not line.startswith("#")]


def new_drift_objects(base_text, head_text):
    """Đối tượng lệch có ở baseline của PR mà baseline của nhánh đích chưa có."""
    known = {drift_object(line) for line in baseline_lines(base_text)}
    added = {drift_object(line) for line in baseline_lines(head_text)}
    return sorted(added - known)


def added_changelog_rows(base_text, head_text):
    """Dòng bảng (bắt đầu bằng ngày) có ở changelog của PR nhiều hơn của nhánh đích."""
    rows = lambda text: Counter(l.strip() for l in text.splitlines() if CHANGELOG_ROW.match(l))
    return sorted((rows(head_text) - rows(base_text)).elements())


def ddl_changed(base_text, head_text):
    return base_text.replace("\r\n", "\n") != head_text.replace("\r\n", "\n")


def git_show(ref, path):
    """Nội dung file ở ref; None nếu ref không có file."""
    result = subprocess.run(
        ["git", "show", f"{ref}:{path}"], capture_output=True, encoding="utf-8", errors="replace"
    )
    return result.stdout if result.returncode == 0 else None


def read_head(path):
    with open(path, encoding="utf-8", newline="") as fh:
        return fh.read()


def check_changelog(base_ref):
    base_ddl = git_show(base_ref, DDL_PATH)
    if base_ddl is None:
        print(f"Nhánh đích {base_ref} chưa có {DDL_PATH}, bỏ qua check changelog.")
        return 0
    if not ddl_changed(base_ddl, read_head(DDL_PATH)):
        print(f"{DDL_PATH} không đổi so với {base_ref}: không cần mục changelog.")
        return 0
    if added_changelog_rows(git_show(base_ref, CHANGELOG_PATH) or "", read_head(CHANGELOG_PATH)):
        print(f"{DDL_PATH} đổi và {CHANGELOG_PATH} có dòng mới: đạt.")
        return 0
    print(
        f"::error file={CHANGELOG_PATH}::{DDL_PATH} đổi so với {base_ref} nhưng {CHANGELOG_PATH} "
        "chưa có dòng mới. Thêm một dòng vào bảng: | ngày (YYYY-MM-DD) | PR | đối tượng thay đổi | lý do |."
    )
    return 1


def check_baseline(base_ref):
    base_text = git_show(base_ref, BASELINE_PATH)
    if base_text is None:
        print(f"Nhánh đích {base_ref} chưa có {BASELINE_PATH}, bỏ qua check baseline.")
        return 0
    try:
        new = new_drift_objects(base_text, read_head(BASELINE_PATH))
    except ValueError as error:
        print(f"::error file={BASELINE_PATH}::{error}")
        return 1
    if not new:
        print(f"{BASELINE_PATH} không thêm đối tượng lệch nào so với {base_ref}: đạt.")
        return 0
    print(
        f"::error file={BASELINE_PATH}::{len(new)} đối tượng lệch mới trong baseline so với {base_ref}. "
        "Baseline chỉ được giảm: sửa lệch bằng migration hoặc thay đổi release_DDL.sql theo AGENTS.md mục 5."
    )
    for item in new:
        print("  " + item)
    return 1


CHECKS = {"changelog": check_changelog, "baseline": check_baseline}


def main(argv):
    if len(argv) < 2 or argv[1] not in CHECKS:
        print(__doc__)
        return 2
    base_ref = argv[2] if len(argv) > 2 else ""
    if not base_ref:
        print("Không có nhánh đích (không phải pull_request): bỏ qua.")
        return 0
    return CHECKS[argv[1]](base_ref)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
