from django.core import checks
from django.test import SimpleTestCase, override_settings

from signing.checks import kiem_tra_bi_mat_pin
from signing.errors import SigningError
from signing.services import pin as pin_service


class SigningPinSecretCheckTests(SimpleTestCase):
    """Issue #79: production bắt buộc bí mật PIN riêng."""

    def ids(self):
        return [e.id for e in kiem_tra_bi_mat_pin(None)]

    @override_settings(DEBUG=False, SIGNING_PIN_SECRET="")
    def test_missing_secret_is_error(self):
        errors = kiem_tra_bi_mat_pin(None)
        self.assertEqual([e.id for e in errors], ["signing.E001"])
        self.assertEqual(errors[0].level, checks.ERROR)

    @override_settings(DEBUG=False, SECRET_KEY="khoa-django", SIGNING_PIN_SECRET="khoa-django")
    def test_secret_equal_to_secret_key_is_error(self):
        self.assertEqual(self.ids(), ["signing.E002"])

    @override_settings(DEBUG=False, SIGNING_PIN_SECRET="bi-mat-pin-rieng")
    def test_dedicated_secret_passes(self):
        self.assertEqual(self.ids(), [])

    @override_settings(DEBUG=False, SIGNING_PIN_SECRET="")
    def test_registered_as_deploy_check_only(self):
        # check --deploy báo lỗi; check thường (chạy cả trong manage.py test) không chặn
        self.assertIn("signing.E001", [e.id for e in checks.run_checks(include_deployment_checks=True)])
        self.assertNotIn("signing.E001", [e.id for e in checks.run_checks()])


class SigningDocumentRootCheckTests(SimpleTestCase):
    @override_settings(SIGNING_DOCUMENT_ROOT="")
    def test_missing_document_root_is_deploy_error(self):
        self.assertIn("signing.E003", [e.id for e in checks.run_checks(include_deployment_checks=True)])
        self.assertNotIn("signing.E003", [e.id for e in checks.run_checks()])

    @override_settings(SIGNING_DOCUMENT_ROOT="/srv/signing")
    def test_configured_document_root_passes(self):
        self.assertNotIn("signing.E003", [e.id for e in checks.run_checks(include_deployment_checks=True)])


class PinSecretRuntimeTests(SimpleTestCase):
    @override_settings(DEBUG=False, SIGNING_PIN_SECRET="")
    def test_production_without_secret_refuses_pin_operations(self):
        with self.assertLogs("signing.services.pin", level="ERROR"), self.assertRaises(SigningError) as ctx:
            pin_service._bi_mat_may_chu()
        self.assertEqual((ctx.exception.status_code, ctx.exception.get_codes()), (503, "chua_cau_hinh_bi_mat_pin"))

    @override_settings(DEBUG=True, SIGNING_PIN_SECRET="", SECRET_KEY="khoa-dev")
    def test_dev_falls_back_to_secret_key(self):
        self.assertEqual(pin_service._bi_mat_may_chu(), b"khoa-dev")

    @override_settings(DEBUG=False, SIGNING_PIN_SECRET="bi-mat-pin-rieng")
    def test_dedicated_secret_used(self):
        self.assertEqual(pin_service._bi_mat_may_chu(), b"bi-mat-pin-rieng")
