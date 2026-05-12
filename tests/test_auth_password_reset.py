from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from rest_framework.test import APIClient


class PasswordResetEndpointTests(TestCase):
    """Specs for POST /api/password_reset/ — derived from the API documentation."""

    url = '/api/password_reset/'

    def setUp(self):
        self.client = APIClient()
        self.user_email = 'known@example.com'
        get_user_model().objects.create_user(
            username=self.user_email, email=self.user_email,
            password='securepass123', is_active=True,
        )

    def test_returns_200_for_known_email(self):
        response = self.client.post(self.url, {'email': self.user_email}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data['detail'],
            'An email has been sent to reset your password.',
        )

    def test_sends_email_for_known_address(self):
        self.client.post(self.url, {'email': self.user_email}, format='json')
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.user_email, mail.outbox[0].to)

    def test_returns_200_for_unknown_email(self):
        response = self.client.post(self.url, {'email': 'nobody@example.com'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)

    def test_rejects_missing_email(self):
        response = self.client.post(self.url, {}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_rejects_invalid_email_format(self):
        response = self.client.post(self.url, {'email': 'not-an-email'}, format='json')
        self.assertEqual(response.status_code, 400)
