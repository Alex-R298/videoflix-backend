from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient


class LoginEndpointTests(TestCase):
    """Specs for POST /api/login/ — derived from the API documentation."""

    url = '/api/login/'

    def setUp(self):
        self.client = APIClient()
        self.email = 'test.user@example.com'
        self.password = 'securepass123'
        self.user = get_user_model().objects.create_user(
            username=self.email, email=self.email,
            password=self.password, is_active=True,
        )

    def _post(self, **overrides):
        payload = {'email': self.email, 'password': self.password, **overrides}
        return self.client.post(self.url, payload, format='json')

    def test_returns_200_with_user_and_detail(self):
        response = self._post()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['user']['id'], self.user.id)
        self.assertEqual(response.data['detail'], 'Login successful')

    def test_sets_http_only_jwt_cookies(self):
        response = self._post()
        self.assertIn('access_token', response.cookies)
        self.assertIn('refresh_token', response.cookies)
        self.assertTrue(response.cookies['access_token']['httponly'])
        self.assertTrue(response.cookies['refresh_token']['httponly'])

    def test_rejects_wrong_password(self):
        response = self._post(password='wrong')
        self.assertEqual(response.status_code, 400)

    def test_rejects_inactive_user(self):
        self.user.is_active = False
        self.user.save()
        response = self._post()
        self.assertEqual(response.status_code, 400)

    def test_rejects_unknown_email(self):
        response = self._post(email='nobody@example.com')
        self.assertEqual(response.status_code, 400)

    def test_rejects_missing_fields(self):
        response = self.client.post(self.url, {}, format='json')
        self.assertEqual(response.status_code, 400)
