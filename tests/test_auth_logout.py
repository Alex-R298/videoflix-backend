from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken


class LogoutEndpointTests(TestCase):
    """Specs for POST /api/logout/ — derived from the API documentation."""

    url = '/api/logout/'

    def setUp(self):
        self.client = APIClient()
        email = 'test.user@example.com'
        password = 'securepass123'
        get_user_model().objects.create_user(
            username=email, email=email, password=password, is_active=True,
        )
        self.client.post(
            '/api/login/', {'email': email, 'password': password}, format='json',
        )

    def test_returns_200_and_clears_cookies(self):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.cookies['access_token'].value, '')
        self.assertEqual(response.cookies['refresh_token'].value, '')

    def test_blacklists_refresh_token(self):
        self.client.post(self.url)
        self.assertTrue(BlacklistedToken.objects.exists())

    def test_rejects_missing_refresh_cookie(self):
        fresh_client = APIClient()
        response = fresh_client.post(self.url)
        self.assertEqual(response.status_code, 400)
