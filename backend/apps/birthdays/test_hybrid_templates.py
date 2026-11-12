import unittest
from unittest.mock import MagicMock
from datetime import date

from django.conf import settings
if not settings.configured:
    settings.configure(
        SECRET_KEY="test-key",
        INSTALLED_APPS=[
            "django.contrib.auth",
            "django.contrib.contenttypes",
            "accounts",
            "birthdays",
        ],
        TEMPLATES=[{
            "BACKEND": "django.template.backends.django.DjangoTemplates",
            "APP_DIRS": True,
        }],
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": ":memory:",
            }
        },
        DEFAULT_FROM_EMAIL="noreply@baolong.test",
        BRAND_NAME="Bảo Long Insurance",
        ORGANIZATION_NAME="Tổng Công ty Cổ phần Bảo hiểm Bảo Long",
        SIGNING_FRONTEND_URL="https://qlvb.baolong.vn",
    )
    import django
    django.setup()

from birthdays.templates_service import (
    SENIOR_LEADERSHIP_ROLE,
    MIDDLE_MANAGEMENT_ROLE,
    STAFF_ROLE,
    TEMPLATE_POOLS,
    get_employee_role_category,
    get_template_pool,
    pick_hybrid_template,
    template_catalog,
)
from birthdays.services import _default_snapshot


class SmartHybridTemplateTests(unittest.TestCase):
    def test_role_categorization(self):
        # Senior Leadership
        self.assertEqual(get_employee_role_category("Chủ tịch HĐQT"), SENIOR_LEADERSHIP_ROLE)
        self.assertEqual(get_employee_role_category("Tổng Giám đốc"), SENIOR_LEADERSHIP_ROLE)
        self.assertEqual(get_employee_role_category("Giám đốc Khối"), SENIOR_LEADERSHIP_ROLE)
        self.assertEqual(get_employee_role_category("Phó Giám đốc Khối"), SENIOR_LEADERSHIP_ROLE)
        self.assertEqual(get_employee_role_category("Giám đốc Vùng"), SENIOR_LEADERSHIP_ROLE)

        # Middle Management
        self.assertEqual(get_employee_role_category("Giám đốc Ban"), MIDDLE_MANAGEMENT_ROLE)
        self.assertEqual(get_employee_role_category("Trưởng Ban"), MIDDLE_MANAGEMENT_ROLE)
        self.assertEqual(get_employee_role_category("Phó Ban"), MIDDLE_MANAGEMENT_ROLE)
        self.assertEqual(get_employee_role_category("Trưởng phòng"), MIDDLE_MANAGEMENT_ROLE)
        self.assertEqual(get_employee_role_category("Phó phòng"), MIDDLE_MANAGEMENT_ROLE)
        self.assertEqual(get_employee_role_category("Trưởng Bộ phận"), MIDDLE_MANAGEMENT_ROLE)

        # General Staff
        self.assertEqual(get_employee_role_category("Chuyên viên"), STAFF_ROLE)
        self.assertEqual(get_employee_role_category("Văn thư"), STAFF_ROLE)
        self.assertEqual(get_employee_role_category("Kiểm toán viên"), STAFF_ROLE)
        self.assertEqual(get_employee_role_category("Nhân viên"), STAFF_ROLE)
        self.assertEqual(get_employee_role_category("Thành viên"), STAFF_ROLE)
        self.assertEqual(get_employee_role_category(None), STAFF_ROLE)
        self.assertEqual(get_employee_role_category(""), STAFF_ROLE)

    def test_template_pools_mapping(self):
        self.assertEqual(get_template_pool(SENIOR_LEADERSHIP_ROLE), ["01", "02", "09"])
        self.assertEqual(get_template_pool(MIDDLE_MANAGEMENT_ROLE), ["02", "03", "07", "08"])
        self.assertEqual(get_template_pool(STAFF_ROLE), ["04", "05", "06", "08", "10"])

    def test_pick_hybrid_template_deterministic_with_seed(self):
        # Test Senior Leadership
        for seed in range(10):
            layout, draft = pick_hybrid_template("Chủ tịch HĐQT", seed=seed)
            self.assertIn(layout, TEMPLATE_POOLS[SENIOR_LEADERSHIP_ROLE])
            self.assertIn("subject", draft)
            self.assertIn("message", draft)

        # Test Middle Management
        for seed in range(10):
            layout, draft = pick_hybrid_template("Trưởng phòng", seed=seed)
            self.assertIn(layout, TEMPLATE_POOLS[MIDDLE_MANAGEMENT_ROLE])

        # Test Staff
        for seed in range(10):
            layout, draft = pick_hybrid_template("Chuyên viên", seed=seed)
            self.assertIn(layout, TEMPLATE_POOLS[STAFF_ROLE])

    @unittest.mock.patch("birthdays.templates_service.BirthdayEmailTemplate.objects.all", return_value=[])
    def test_template_catalog_includes_recommended_roles(self, _mock_all):
        catalog = template_catalog()
        self.assertGreaterEqual(len(catalog), 10)
        by_layout = {item["layout"]: item for item in catalog if item["name"] is None}

        # Layout 01 should be recommended for Senior Leadership
        self.assertIn(SENIOR_LEADERSHIP_ROLE, by_layout["01"]["recommended_roles"])
        # Layout 04 should be recommended for Staff
        self.assertIn(STAFF_ROLE, by_layout["04"]["recommended_roles"])
        # Layout 02 should be in Senior Leadership and Middle Management
        self.assertIn(SENIOR_LEADERSHIP_ROLE, by_layout["02"]["recommended_roles"])
        self.assertIn(MIDDLE_MANAGEMENT_ROLE, by_layout["02"]["recommended_roles"])

    def test_default_snapshot_renders_hybrid_layout_and_card(self):
        employee = MagicMock()
        employee.id = 101
        employee.pk = 101
        employee.ho_ten = "Nguyễn Văn Test"
        employee.ngay_sinh = date(1995, 8, 15)
        employee.chuc_danh = "Chuyên viên Cao cấp"
        employee.chuc_vu = MagicMock(name="Position")
        employee.chuc_vu.name = "Chuyên viên"
        employee.don_vi = MagicMock(name="Department")
        employee.don_vi.ten = "Ban Công nghệ Thông tin"

        snapshot = _default_snapshot(employee, seed=42)

        self.assertIn(snapshot["layout"], TEMPLATE_POOLS[STAFF_ROLE])
        self.assertEqual(snapshot["template_version"], f"layout:{snapshot['layout']}:1")
        self.assertIn("Nguyễn Văn Test", snapshot["html"])
        self.assertIn("Ban Công nghệ Thông tin", snapshot["html"])
        self.assertIn(f"/birthday-cards/{snapshot['layout']}.html#token=", snapshot["html"])
        self.assertIn("Nguyễn Văn Test", snapshot["text"])
        self.assertIn("Nguyễn Văn Test", snapshot["subject"])


if __name__ == "__main__":
    unittest.main()
