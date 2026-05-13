import os
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from video_app.models import Video


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class VideoManifestEndpointTests(TestCase):
    """Specs for GET /api/video/<movie_id>/<resolution>/index.m3u8"""

    def setUp(self):
        self.client = APIClient()
        self.email = 'viewer@example.com'
        self.password = 'securepass123'
        get_user_model().objects.create_user(
            username=self.email, email=self.email,
            password=self.password, is_active=True,
        )
        self.video = Video.objects.create(
            title='Movie', video_file='videos/test.mp4',
        )
        self._write_manifest('480p', '#EXTM3U\n#EXT-X-VERSION:3\n')

    def _write_manifest(self, resolution, content):
        folder = os.path.join(
            settings.MEDIA_ROOT, 'videos', str(self.video.id), resolution,
        )
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, 'index.m3u8'), 'w') as f:
            f.write(content)

    def _login(self):
        self.client.post(
            '/api/login/',
            {'email': self.email, 'password': self.password}, format='json',
        )

    def _url(self, vid, res):
        return f'/api/video/{vid}/{res}/index.m3u8'

    def test_rejects_unauthenticated(self):
        response = self.client.get(self._url(self.video.id, '480p'))
        self.assertEqual(response.status_code, 401)

    def test_returns_200_with_m3u8_content_type(self):
        self._login()
        response = self.client.get(self._url(self.video.id, '480p'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/vnd.apple.mpegurl')

    def test_returns_404_for_unknown_video(self):
        self._login()
        response = self.client.get(self._url(99999, '480p'))
        self.assertEqual(response.status_code, 404)

    def test_returns_404_for_missing_manifest_file(self):
        self._login()
        response = self.client.get(self._url(self.video.id, '999p'))
        self.assertEqual(response.status_code, 404)
