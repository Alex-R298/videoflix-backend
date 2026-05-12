from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken


class TokenRefreshEndpointTests(TestCase):
    """Specs for POST /api/token/refresh/ — derived from the API documentation."""

    url = '/api/token/refresh/'

    def setUp(self):
        self.client = APIClient()
        user = get_user_model().objects.create_user(
            username='test@example.com', email='test@example.com',
            password='securepass123', is_active=True,
        )
        self.refresh_token = str(RefreshToken.for_user(user))

    def _post_with_refresh(self):
        self.client.cookies['refresh_token'] = self.refresh_token
        return self.client.post(self.url)

    def test_returns_200_with_new_access_token(self):
        response = self._post_with_refresh()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['detail'], 'Token refreshed')
        self.assertIn('access', response.data)

    def test_sets_new_access_cookie(self):
        response = self._post_with_refresh()
        self.assertIn('access_token', response.cookies)
        self.assertTrue(response.cookies['access_token']['httponly'])

    def test_rejects_missing_refresh_cookie(self):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 400)

    def test_rejects_invalid_refresh_token(self):
        self.client.cookies['refresh_token'] = 'not-a-valid-token'
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 401)
