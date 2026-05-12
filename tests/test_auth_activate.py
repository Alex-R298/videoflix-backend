from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.test import TestCase
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.test import APIClient


class ActivationEndpointTests(TestCase):
    """Specs for GET /api/activate/<uidb64>/<token>/"""

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            username='pending@example.com', email='pending@example.com',
            password='securepass123', is_active=False,
        )
        self.uidb64 = urlsafe_base64_encode(force_bytes(self.user.pk))
        self.token = default_token_generator.make_token(self.user)

    def _url(self, uid, token):
        return f'/api/activate/{uid}/{token}/'

    def test_activates_user_and_returns_200(self):
        response = self.client.get(self._url(self.uidb64, self.token))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['message'], 'Account successfully activated.')
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)

    def test_rejects_invalid_token(self):
        response = self.client.get(self._url(self.uidb64, 'bogus-token'))
        self.assertEqual(response.status_code, 400)

    def test_rejects_unknown_user(self):
        bogus_uid = urlsafe_base64_encode(force_bytes(999999))
        response = self.client.get(self._url(bogus_uid, self.token))
        self.assertEqual(response.status_code, 400)

    def test_rejects_malformed_uidb64(self):
        response = self.client.get(self._url('not-base64!', self.token))
        self.assertEqual(response.status_code, 400)
