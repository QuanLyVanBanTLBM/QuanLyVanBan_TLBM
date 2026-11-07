"""Quy tắc email và số điện thoại CBNV: SĐT đúng 10 số di động VN; email nhận mọi tên miền, giới hạn tên miền chỉ khi cấu hình."""
from io import BytesIO

import openpyxl
from django.conf import settings
from django.test import override_settings
from rest_framework import status

from accounts.excel_cbnv import generate_cbnv_template
from accounts.models import Employee, vietnam_phone_regex
from accounts.test_employees import EmployeeBaseTestCase

VALID_PHONES = ["0912345678", "0387654321", "0587654321", "0712345678", "0812345678"]
INVALID_PHONES = [
    "012345678",  # 9 số
    "091234567",  # 9 số
    "09123456789",  # 11 số
    "+84912345678",  # dạng quốc tế không còn nhận
    "84912345678",
    "0112345678",  # đầu số 01/02/04/06 không phải di động
    "0212345678",
    "0412345678",
    "0612345678",
    "091 234 5678",  # có khoảng trắng
    "09123abc78",
]
NON_COMPANY_EMAILS = [
    "x@yahoo.com",
    "x@gmail.com",
    "x@baolong.vn.evil.com",  # tên miền chứa baolong.vn nhưng không đúng
    "x@mail.baolong.vn",  # tên miền con
    "x@notbaolong.vn",
    "x@baolong.com",
]


class EmployeeContactRulesTests(EmployeeBaseTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_authenticate(user=self.admin_user)
        self.counter = 0

    def payload(self, **overrides):
        self.counter += 1
        data = {
            "ho_ten": f"Người Thử {self.counter}",
            "email": f"nguoi.thu{self.counter}@baolong.vn",
            "ngay_sinh": "1990-01-01",
            "don_vi_id": self.don_vi_1.id,
            "chuc_vu_id": self.cv_chuyen_vien.id,
            "sdt": "0912345678",
        }
        data.update(overrides)
        return data

    def create(self, **overrides):
        return self.client.post(self.employee_list_url, self.payload(**overrides), format="json")

    def detail_url(self, employee):
        return f"{self.employee_list_url}{employee.id}/"

    # --- Số điện thoại ---------------------------------------------------------------------------------------

    def test_create_accepts_only_ten_digit_mobile_numbers(self):
        for phone in VALID_PHONES:
            with self.subTest(phone=phone):
                response = self.create(sdt=phone)
                self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content)
                self.assertEqual(response.json()["sdt"], phone)

    def test_create_rejects_every_non_ten_digit_phone(self):
        for phone in INVALID_PHONES:
            with self.subTest(phone=phone):
                response = self.create(sdt=phone)
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertEqual(response.json()["sdt"], ["employees.messages.invalidPhone"])

    def test_blank_phone_is_still_optional(self):
        self.assertEqual(self.create(sdt="").status_code, status.HTTP_201_CREATED)

    def test_update_rejects_nine_digit_phone_and_accepts_ten_digit(self):
        employee = self.normal_user
        bad = self.client.patch(self.detail_url(employee), {"sdt": "023243423"}, format="json")
        self.assertEqual(bad.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(bad.json()["sdt"], ["employees.messages.invalidPhone"])
        good = self.client.patch(self.detail_url(employee), {"sdt": "0987654321"}, format="json")
        self.assertEqual(good.status_code, status.HTTP_200_OK)
        employee.refresh_from_db()
        self.assertEqual(employee.sdt, "0987654321")

    def test_self_service_update_uses_the_same_phone_rule(self):
        self.client.force_authenticate(user=self.self_user)
        bad = self.client.patch(self.detail_url(self.self_user), {"sdt": "012345678"}, format="json")
        self.assertEqual(bad.status_code, status.HTTP_400_BAD_REQUEST)
        good = self.client.patch(self.detail_url(self.self_user), {"sdt": "0911223355"}, format="json")
        self.assertEqual(good.status_code, status.HTTP_200_OK)

    def test_model_validator_matches_the_api_rule(self):
        for phone in VALID_PHONES:
            vietnam_phone_regex(phone)
        for phone in INVALID_PHONES:
            with self.subTest(phone=phone), self.assertRaises(Exception):
                vietnam_phone_regex(phone)

    # --- Email ------------------------------------------------------------------------------------------------

    @override_settings(EMPLOYEE_EMAIL_ALLOWED_DOMAINS=("baolong.vn",))
    def test_create_accepts_company_domain_in_any_letter_case(self):
        response = self.create(email="Nguyen.Van.An@BaoLong.VN")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content)
        self.assertEqual(response.json()["email"], "nguyen.van.an@baolong.vn")

    @override_settings(EMPLOYEE_EMAIL_ALLOWED_DOMAINS=("baolong.vn",))
    def test_create_rejects_non_company_domains(self):
        for email in NON_COMPANY_EMAILS:
            with self.subTest(email=email):
                response = self.create(email=email)
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertEqual(response.json()["email"], ["employees.messages.emailDomainNotAllowed"])

    def test_malformed_email_still_reports_format_error(self):
        response = self.create(email="khong-phai-email")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["email"], ["employees.messages.invalidEmail"])

    @override_settings(EMPLOYEE_EMAIL_ALLOWED_DOMAINS=("baolong.vn",))
    def test_update_rejects_non_company_email_and_accepts_company_email(self):
        employee = self.normal_user
        bad = self.client.patch(self.detail_url(employee), {"email": "binh@yahoo.com"}, format="json")
        self.assertEqual(bad.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(bad.json()["email"], ["employees.messages.emailDomainNotAllowed"])
        good = self.client.patch(self.detail_url(employee), {"email": "binh@baolong.vn"}, format="json")
        self.assertEqual(good.status_code, status.HTTP_200_OK)

    @override_settings(EMPLOYEE_EMAIL_ALLOWED_DOMAINS=("baolong.vn",))
    def test_update_that_does_not_send_email_keeps_a_legacy_address(self):
        """Hồ sơ cũ có email ngoài tên miền vẫn sửa được các trường khác khi không gửi lại email."""
        Employee.objects.filter(pk=self.normal_user.pk).update(email="cu@yahoo.com", sdt="023243423")
        response = self.client.patch(self.detail_url(self.normal_user), {"ghi_chu": "Cập nhật"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.normal_user.refresh_from_db()
        self.assertEqual((self.normal_user.email, self.normal_user.sdt), ("cu@yahoo.com", "023243423"))

    def test_default_settings_do_not_restrict_the_email_domain(self):
        self.assertEqual(settings.EMPLOYEE_EMAIL_ALLOWED_DOMAINS, ())

    def test_create_and_update_accept_any_domain_by_default(self):
        for email in ("ai.do@gmail.com", "ai.do2@yahoo.com", "ai.do3@baolong.vn", "ai.do4@baohiembaolong.vn"):
            with self.subTest(email=email):
                response = self.create(email=email)
                self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content)
        updated = self.client.patch(self.detail_url(self.normal_user), {"email": "binh.moi@gmail.com"}, format="json")
        self.assertEqual(updated.status_code, status.HTTP_200_OK, updated.content)

    def test_default_import_accepts_gmail_rows(self):
        response = self.import_rows([("nguoi.moi@gmail.com", "0912345670"), ("khac@yahoo.com", "0912345671")])
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content)
        self.assertEqual(response.json()["created_count"], 2)

    def test_malformed_email_is_still_rejected_by_default(self):
        response = self.create(email="gmail.com")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @override_settings(EMPLOYEE_EMAIL_ALLOWED_DOMAINS=())
    def test_empty_allow_list_disables_the_domain_rule(self):
        self.assertEqual(self.create(email="ai.do@yahoo.com").status_code, status.HTTP_201_CREATED)

    @override_settings(EMPLOYEE_EMAIL_ALLOWED_DOMAINS=("baolong.vn", "baohiembaolong.vn"))
    def test_allow_list_can_hold_several_domains(self):
        self.assertEqual(self.create(email="ai.do@baohiembaolong.vn").status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.create(email="ai.do2@yahoo.com").status_code, status.HTTP_400_BAD_REQUEST)

    # --- Import Excel -----------------------------------------------------------------------------------------

    def import_rows(self, rows):
        self.client.force_authenticate(user=self.admin_user)
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Danh Sach CBNV"
        ws.append(["STT", "Họ và tên (*)", "Ngày sinh (*)", "Email (*)", "Số điện thoại", "Tên Đơn vị / Phòng ban (*)",
                   "Tên Chức vụ (*)", "Chức danh", "Trạng thái", "Ghi chú"])
        ws.append(["(Ghi chú)", "", "", "", "", "", "", "", "", ""])
        for number, (email, phone) in enumerate(rows, start=1):
            ws.append([number, f"Nhập Thử {number}", "1995-05-05", email, phone, self.don_vi_1.ten,
                       self.cv_chuyen_vien.name, "", "Đang làm việc", ""])
        bio = BytesIO()
        wb.save(bio)
        bio.seek(0)
        bio.name = "lien_he.xlsx"
        return self.client.post(self.import_url, {"file": bio}, format="multipart")

    def error_codes(self, response):
        return {(error["field"], error["code"]) for error in response.json()["errors"]}

    @override_settings(EMPLOYEE_EMAIL_ALLOWED_DOMAINS=("baolong.vn",))
    def test_import_reports_domain_and_phone_errors_per_row(self):
        response = self.import_rows([
            ("a@yahoo.com", "0912345678"),
            ("b@baolong.vn", "023243423"),
            ("c@baolong.vn", "+84912345678"),
        ])
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            self.error_codes(response),
            {("email", "employees.messages.emailDomainNotAllowed"), ("sdt", "employees.validation.phoneInvalid")},
        )
        self.assertEqual(Employee.objects.filter(ho_ten__startswith="Nhập Thử").count(), 0)

    def test_import_keeps_accepting_valid_company_rows(self):
        response = self.import_rows([("hop.le@baolong.vn", "0912345670"), ("khong.sdt@baolong.vn", "")])
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content)
        self.assertEqual(response.json()["created_count"], 2)

    def test_import_still_rejects_malformed_email(self):
        response = self.import_rows([("a@-baolong.vn", "0912345670")])
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.error_codes(response), {("email", "employees.import.errors.invalidEmail")})

    def test_template_examples_follow_the_rules(self):
        sheet = openpyxl.load_workbook(BytesIO(generate_cbnv_template().getvalue())).active
        cells = [str(cell.value) for row in sheet.iter_rows() for cell in row if cell.value]
        emails = [value for value in cells if "@" in value and " " not in value]
        phones = [value for value in cells if value.isdigit() and value.startswith("0")]
        self.assertTrue(emails and phones)
        for email in emails:
            self.assertTrue(email.endswith("@baolong.vn"), email)
        for phone in phones:
            vietnam_phone_regex(phone)
