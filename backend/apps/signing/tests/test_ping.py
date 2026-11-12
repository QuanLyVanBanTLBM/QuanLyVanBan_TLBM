from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()


class SigningPingTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_ping_requires_authentication(self):
        response = self.client.get("/api/v1/signing/ping/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_ping_ok_when_authenticated(self):
        user = User.objects.create_user(username="signer")
        self.client.force_authenticate(user=user)
        response = self.client.get("/api/v1/signing/ping/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {"module": "signing", "status": "ok"})
