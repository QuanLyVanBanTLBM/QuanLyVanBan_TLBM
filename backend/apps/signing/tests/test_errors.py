from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory, force_authenticate

from signing.errors import ConflictError, SigningAPIView, SigningError

User = get_user_model()


class _RaiseView(SigningAPIView):
    exc = None

    def get(self, request):
        raise self.exc


def _call(exc):
    view = _RaiseView.as_view(exc=exc)
    request = APIRequestFactory().get("/x/")
    force_authenticate(request, user=User(username="u"))
    return view(request)


class ErrorFormatTests(SimpleTestCase):
    def test_signing_error_has_stable_code(self):
        response = _call(SigningError(code="quy_trinh_khong_co_cap", detail="Quy trình chưa có cấp ký."))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "quy_trinh_khong_co_cap")
        self.assertEqual(response.data["detail"], "Quy trình chưa có cấp ký.")
        self.assertEqual(response.data["fields"], {})

    def test_conflict_error_is_409(self):
        response = _call(ConflictError())
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "xung_dot_trang_thai")

    def test_field_errors_kept(self):
        response = _call(SigningError(code="sai_du_lieu", detail="Sai.", fields={"ma_quy_trinh": ["Bắt buộc."]}))
        self.assertEqual(response.data["fields"], {"ma_quy_trinh": ["Bắt buộc."]})

    def test_drf_validation_error_grouped_by_field(self):
        response = _call(serializers.ValidationError({"ma_quy_trinh": ["Bắt buộc."]}))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "du_lieu_khong_hop_le")
        self.assertEqual(response.data["fields"], {"ma_quy_trinh": ["Bắt buộc."]})


class OtherModulesUnaffectedTests(TestCase):
    def test_global_handler_not_replaced(self):
        from django.conf import settings

        self.assertNotIn("EXCEPTION_HANDLER", settings.REST_FRAMEWORK)
