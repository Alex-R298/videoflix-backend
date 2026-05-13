import os
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from video_app.models import Video


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class VideoSegmentEndpointTests(TestCase):
    """Specs for GET /api/video/<movie_id>/<resolution>/<segment>/"""

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
        self._write_segment('480p', '000.ts', b'\x47fake-ts-payload')

    def _write_segment(self, resolution, name, content):
        folder = os.path.join(
            settings.MEDIA_ROOT, 'videos', str(self.video.id), resolution,
        )
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, name), 'wb') as f:
            f.write(content)

    def _login(self):
        self.client.post(
            '/api/login/',
            {'email': self.email, 'password': self.password}, format='json',
        )

    def _url(self, vid, res, seg):
        return f'/api/video/{vid}/{res}/{seg}/'

    def test_rejects_unauthenticated(self):
        response = self.client.get(self._url(self.video.id, '480p', '000.ts'))
        self.assertEqual(response.status_code, 401)

    def test_returns_200_with_ts_content_type(self):
        self._login()
        response = self.client.get(self._url(self.video.id, '480p', '000.ts'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'video/MP2T')

    def test_returns_404_for_unknown_video(self):
        self._login()
        response = self.client.get(self._url(99999, '480p', '000.ts'))
        self.assertEqual(response.status_code, 404)

    def test_returns_404_for_missing_segment_file(self):
        self._login()
        response = self.client.get(self._url(self.video.id, '480p', '999.ts'))
        self.assertEqual(response.status_code, 404)

    def test_rejects_path_traversal(self):
        self._login()
        response = self.client.get(self._url(self.video.id, '480p', '../../../etc/passwd'))
        self.assertIn(response.status_code, (400, 404))
