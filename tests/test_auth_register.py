from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from rest_framework.test import APIClient


class RegisterEndpointTests(TestCase):
    """Specs for POST /api/register/ — derived from the API documentation."""

    url = '/api/register/'

    def setUp(self):
        self.client = APIClient()
        self.payload = {
            'email': 'new.user@example.com',
            'password': 'securepass123',
            'confirmed_password': 'securepass123',
        }

    def test_returns_201_with_user_and_token(self):
        response = self.client.post(self.url, self.payload, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['user']['email'], self.payload['email'])
        self.assertIn('token', response.data)

    def test_creates_inactive_user(self):
        self.client.post(self.url, self.payload, format='json')
        user = get_user_model().objects.get(email=self.payload['email'])
        self.assertFalse(user.is_active)

    def test_sends_activation_email(self):
        self.client.post(self.url, self.payload, format='json')
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.payload['email'], mail.outbox[0].to)

    def test_rejects_duplicate_email(self):
        get_user_model().objects.create_user(
            username='existing', email=self.payload['email'], password='x'
        )
        response = self.client.post(self.url, self.payload, format='json')
        self.assertEqual(response.status_code, 400)

    def test_rejects_password_mismatch(self):
        payload = {**self.payload, 'confirmed_password': 'different'}
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, 400)

    def test_rejects_missing_email(self):
        payload = {'password': 'x', 'confirmed_password': 'x'}
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, 400)
