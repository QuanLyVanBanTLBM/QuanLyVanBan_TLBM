import json
import random
import re
from pathlib import Path

from django.template.loader import render_to_string

from .models import BirthdayEmailTemplate


LAYOUT_DEFAULTS = json.loads(
    (Path(__file__).parent / "templates/birthdays/layouts/defaults.json").read_text(encoding="utf-8")
)
PLACEHOLDERS = (
    "employee_name", "department", "position", "chuc_danh",
    "birthday_date", "brand_name", "organization_name",
)
PLACEHOLDER_RE = re.compile(r"\{\{\s*(\w+)\s*\}\}")

# --- PHƯƠNG ÁN LAI THÔNG MINH (SMART HYBRID TEMPLATE SYSTEM) ---

SENIOR_LEADERSHIP_ROLE = "SENIOR_LEADERSHIP"
MIDDLE_MANAGEMENT_ROLE = "MIDDLE_MANAGEMENT"
STAFF_ROLE = "STAFF"

ROLE_TITLES = {
    SENIOR_LEADERSHIP_ROLE: "Lãnh đạo cấp cao",
    MIDDLE_MANAGEMENT_ROLE: "Cán bộ quản lý cấp trung",
    STAFF_ROLE: "Cán bộ nhân viên",
}

# 1. Danh mục chức vụ chuẩn theo phân cấp
SENIOR_LEADERSHIP_POSITIONS = (
    "Chủ tịch HĐQT",
    "Phó Chủ tịch HĐQT",
    "Thành viên HĐQT",
    "Tổng Giám đốc",
    "Lãnh đạo cơ quan",
    "Phó Tổng Giám đốc điều hành",
    "Phó Tổng Giám đốc kinh doanh",
    "Giám đốc Khối",
    "Phó Giám đốc Khối",
    "Giám đốc Vùng",
    "Trợ lý TGĐ",
)

MIDDLE_MANAGEMENT_POSITIONS = (
    "Giám đốc",
    "Phó Giám đốc",
    "Giám đốc Ban",
    "Phụ trách Ban",
    "Trưởng Ban",
    "Phó Ban",
    "Trưởng Bộ phận",
    "Trưởng nhóm",
    "Trưởng phòng",
    "Phó phòng",
)

# 2. Pool mẫu layout phân bổ theo nhóm chức vụ:
# - Nhóm 1 (Lãnh đạo cấp cao): Mẫu 01 (Navy Gold), 02 (Emerald Prestige), 09 (Classic Diplomatic Scroll)
# - Nhóm 2 (Quản lý cấp trung): Mẫu 02 (Emerald Prestige), 03 (Minimalist Editorial), 07 (Midnight Starlight), 08 (Warm Terracotta)
# - Nhóm 3 (Cán bộ nhân viên): Mẫu 04 (Crimson Celebration), 05 (Modern Tech Blue), 06 (Pastel Botanical), 08 (Warm Terracotta), 10 (Festive Confetti)
TEMPLATE_POOLS = {
    SENIOR_LEADERSHIP_ROLE: ["01", "02", "09"],
    MIDDLE_MANAGEMENT_ROLE: ["02", "03", "07", "08"],
    STAFF_ROLE: ["04", "05", "06", "08", "10"],
}


def get_employee_role_category(position_name: str | None) -> str:
    """Phân nhóm nhân viên vào 1 trong 3 nhóm chức vụ theo quy định."""
    if not position_name:
        return STAFF_ROLE

    cleaned = position_name.strip()
    if cleaned in SENIOR_LEADERSHIP_POSITIONS:
        return SENIOR_LEADERSHIP_ROLE
    if cleaned in MIDDLE_MANAGEMENT_POSITIONS:
        return MIDDLE_MANAGEMENT_ROLE

    # Heuristic cho chức vụ mở rộng / tự định nghĩa
    lower = cleaned.lower()
    senior_keywords = ("chủ tịch", "tổng giám đốc", "giám đốc khối", "giám đốc vùng", "hđqt", "ban tgđ")
    if any(kw in lower for kw in senior_keywords):
        return SENIOR_LEADERSHIP_ROLE

    mgmt_keywords = ("giám đốc", "trưởng", "phó ban", "phó phòng", "phụ trách", "trưởng nhóm")
    if any(kw in lower for kw in mgmt_keywords):
        return MIDDLE_MANAGEMENT_ROLE

    return STAFF_ROLE


def get_template_pool(role_category: str) -> list[str]:
    """Trả về danh sách mã layout được cấu hình cho nhóm chức vụ."""
    return TEMPLATE_POOLS.get(role_category, TEMPLATE_POOLS[STAFF_ROLE])


def pick_hybrid_template(position_name: str | None, *, seed: int | str | None = None) -> tuple[str, dict]:
    """
    Chọn mẫu layout ngẫu nhiên trong pool an toàn của nhóm chức vụ.
    Hỗ trợ seed để kiểm thử hoặc đảm bảo tính xác định nếu cần.
    """
    category = get_employee_role_category(position_name)
    pool = get_template_pool(category)
    rng = random.Random(seed) if seed is not None else random
    layout = rng.choice(pool)
    draft = LAYOUT_DEFAULTS.get(layout)
    if not draft:
        layout = "01"
        draft = LAYOUT_DEFAULTS[layout]
    return layout, draft


def valid_placeholders(value: str) -> bool:
    remainder = PLACEHOLDER_RE.sub(
        lambda match: "" if match[1] in PLACEHOLDERS else match[0], value
    )
    return "{" not in remainder and "}" not in remainder


def render_placeholders(value: str, data: dict) -> str:
    return PLACEHOLDER_RE.sub(lambda match: data[match[1]], value)


def saved_template(template: BirthdayEmailTemplate) -> dict:
    return {
        "id": f"saved:{template.pk}",
        "name": template.name,
        "layout": template.layout,
        "subject": template.subject,
        "message": template.message,
    }


def template_catalog() -> list[dict]:
    built_in = []
    for layout, draft in LAYOUT_DEFAULTS.items():
        recommended_roles = [
            role for role, pool in TEMPLATE_POOLS.items() if layout in pool
        ]
        built_in.append({
            "id": f"layout:{layout}",
            "layout": layout,
            "name": None,
            "recommended_roles": recommended_roles,
            **draft,
        })
    return built_in + [saved_template(item) for item in BirthdayEmailTemplate.objects.all()]


def render_email_draft(draft: dict, data: dict, card_url: str) -> tuple[str, dict]:
    subject = render_placeholders(draft["subject"], data)
    greeting = render_placeholders(draft["message"], data)
    text = "\n".join(filter(None, [
        data["employee_name"],
        f"Chức vụ: {data['position']}",
        f"Đơn vị: {data['department']}",
        f"Chức danh: {data['chuc_danh']}" if data["chuc_danh"] else "",
        f"Ngày sinh: {data['birthday_date']}",
        f"\n{greeting}",
        f"\nMở thiệp chúc mừng sinh nhật: {card_url}" if card_url else "",
    ]))
    layout = draft["layout"]
    html = render_to_string(f"birthdays/layouts/{layout}.html", {
        **data, "subject": subject, "greeting": greeting, "birthday_card_url": card_url,
    })
    version = draft["template_id"]
    if version.startswith("layout:"):
        version += ":1"
    return subject, {
        "layout": layout, "template_version": version, "html": html, "text": text,
    }
