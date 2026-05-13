from django.shortcuts import get_object_or_404
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from video_app.models import Video

from .serializers import VideoListSerializer
from .utils import serve_hls_file


class VideoListView(ListAPIView):
    """GET /api/video/ — return all available videos."""

    serializer_class = VideoListSerializer
    queryset = Video.objects.all()


class HLSManifestView(APIView):
    """GET /api/video/<movie_id>/<resolution>/index.m3u8 — HLS master playlist."""

    permission_classes = [IsAuthenticated]

    def get(self, request, movie_id, resolution):
        get_object_or_404(Video, pk=movie_id)
        return serve_hls_file(
            movie_id, resolution, 'index.m3u8', 'application/vnd.apple.mpegurl',
        )


class HLSSegmentView(APIView):
    """GET /api/video/<movie_id>/<resolution>/<segment>/ — single .ts segment."""

    permission_classes = [IsAuthenticated]

    def get(self, request, movie_id, resolution, segment):
        get_object_or_404(Video, pk=movie_id)
        return serve_hls_file(movie_id, resolution, segment, 'video/MP2T')
