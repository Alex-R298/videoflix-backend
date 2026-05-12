from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from video_app.models import Video


class VideoListEndpointTests(TestCase):
    """Specs for GET /api/video/ — derived from the API documentation."""

    url = '/api/video/'

    def setUp(self):
        self.client = APIClient()
        self.email = 'viewer@example.com'
        self.password = 'securepass123'
        get_user_model().objects.create_user(
            username=self.email, email=self.email,
            password=self.password, is_active=True,
        )
        Video.objects.create(
            title='Movie Title', description='Movie Description',
            category='Drama', video_file='videos/test.mp4',
        )

    def _login(self):
        self.client.post(
            '/api/login/',
            {'email': self.email, 'password': self.password}, format='json',
        )

    def test_rejects_unauthenticated(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 401)

    def test_returns_200_and_video_list(self):
        self._login()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'Movie Title')

    def test_response_contains_expected_fields(self):
        self._login()
        video = self.client.get(self.url).data[0]
        for field in ('id', 'created_at', 'title', 'description',
                      'thumbnail_url', 'category'):
            self.assertIn(field, video)
