from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.test import TestCase
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.test import APIClient


class PasswordConfirmEndpointTests(TestCase):
    """Specs for POST /api/password_confirm/<uidb64>/<token>/"""

    def setUp(self):
        self.client = APIClient()
        self.old_password = 'oldpass123'
        self.new_password = 'brandnewpass456'
        self.user = get_user_model().objects.create_user(
            username='reset@example.com', email='reset@example.com',
            password=self.old_password, is_active=True,
        )
        self.uidb64 = urlsafe_base64_encode(force_bytes(self.user.pk))
        self.token = default_token_generator.make_token(self.user)

    def _url(self, uid, token):
        return f'/api/password_confirm/{uid}/{token}/'

    def _payload(self, **overrides):
        return {
            'new_password': self.new_password,
            'confirm_password': self.new_password,
            **overrides,
        }

    def test_returns_200_and_updates_password(self):
        response = self.client.post(self._url(self.uidb64, self.token),
                                    self._payload(), format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['detail'],
                         'Your Password has been successfully reset.')
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(self.new_password))

    def test_rejects_invalid_token(self):
        response = self.client.post(self._url(self.uidb64, 'bogus'),
                                    self._payload(), format='json')
        self.assertEqual(response.status_code, 400)

    def test_rejects_unknown_user(self):
        bogus_uid = urlsafe_base64_encode(force_bytes(999999))
        response = self.client.post(self._url(bogus_uid, self.token),
                                    self._payload(), format='json')
        self.assertEqual(response.status_code, 400)

    def test_rejects_password_mismatch(self):
        response = self.client.post(
            self._url(self.uidb64, self.token),
            self._payload(confirm_password='different'), format='json',
        )
        self.assertEqual(response.status_code, 400)

    def test_rejects_missing_fields(self):
        response = self.client.post(self._url(self.uidb64, self.token),
                                    {}, format='json')
        self.assertEqual(response.status_code, 400)
