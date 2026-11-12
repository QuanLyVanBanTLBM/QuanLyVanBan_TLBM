"""Mỗi app nghiệp vụ (backend/apps/<app>) chỉ có một migration lá, ghi tên trong migrations/max_migration.txt.

Hai PR cùng thêm migration cho một app cùng sửa một dòng max_migration.txt, nên PR merge sau bị git báo conflict
thay vì chỉ lộ ra "nhiều migration lá" sau khi cả hai đã vào staging.

  python .github/scripts/check_max_migration.py          kiểm tra (CI)
  python .github/scripts/check_max_migration.py --write  ghi lại max_migration.txt sau khi thêm migration

Nạp graph migration từ mã nguồn, không kết nối DB; cần biến môi trường đủ để nạp config.settings
(ví dụ DJANGO_SECRET_KEY trong .env). Chạy từ thư mục bất kỳ.
"""
import os
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"
APPS_DIR = BACKEND_DIR / "apps"
MAX_FILE = "max_migration.txt"


def problems(leaves, recorded):
    """Lỗi cho từng app.

    leaves:   {app_label: [tên migration lá]}
    recorded: {app_label: nội dung max_migration.txt đã strip, hoặc None nếu thiếu file}
    """
    errors = []
    for app in sorted(leaves):
        names = sorted(leaves[app])
        if len(names) > 1:
            errors.append(
                f"{app}: có {len(names)} migration lá ({', '.join(names)}). Nhánh đã tạo migration song song với "
                "staging: merge staging, đánh lại số migration của nhánh nối tiếp migration mới nhất trên staging "
                "(không sửa migration đã có trên staging), rồi chạy lại --write."
            )
            continue
        current = recorded.get(app)
        if current is None:
            errors.append(f"{app}: thiếu migrations/{MAX_FILE}; chạy --write.")
        elif current != names[0]:
            errors.append(
                f"{app}: migrations/{MAX_FILE} ghi '{current}' nhưng migration lá là '{names[0]}'; chạy --write."
            )
    return errors


def load_state():
    """(leaves, recorded, migration dir) của các app trong backend/apps."""
    sys.path.insert(0, str(BACKEND_DIR))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django
    from django.apps import apps
    from django.db.migrations.loader import MigrationLoader

    django.setup()
    loader = MigrationLoader(None, ignore_no_migrations=True)
    local = {
        config.label: Path(config.path) / "migrations"
        for config in apps.get_app_configs()
        if Path(config.path).resolve().is_relative_to(APPS_DIR.resolve()) and (Path(config.path) / "migrations").is_dir()
    }
    leaves = {label: [] for label in local}
    for label, name in loader.graph.leaf_nodes():
        if label in leaves:
            leaves[label].append(name)
    recorded = {}
    for label, directory in local.items():
        max_file = directory / MAX_FILE
        recorded[label] = max_file.read_text(encoding="utf-8").strip() if max_file.exists() else None
    return leaves, recorded, local


def main(argv):
    write = "--write" in argv
    leaves, recorded, dirs = load_state()
    if write:
        multi = {app: names for app, names in leaves.items() if len(names) > 1}
        if not multi:
            for app, names in leaves.items():
                if names and recorded.get(app) != names[0]:
                    (dirs[app] / MAX_FILE).write_text(names[0] + "\n", encoding="utf-8", newline="\n")
                    print(f"{app}: ghi {names[0]}")
            recorded = {app: (names[0] if names else None) for app, names in leaves.items()}
    errors = problems({app: names for app, names in leaves.items() if names}, recorded)
    for error in errors:
        print(error, file=sys.stderr)
    if errors:
        return 1
    print(f"Migration: {len(leaves)} app, mỗi app một migration lá khớp {MAX_FILE}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
