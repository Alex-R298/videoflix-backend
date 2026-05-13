from django.shortcuts import get_object_or_404
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from video_app.models import Video

from .serializers import VideoListSerializer
from .utils import serve_hls_file


class VideoListView(ListAPIView):
    """``GET /api/video/`` — list all available videos (auth required)."""

    serializer_class = VideoListSerializer
    queryset = Video.objects.all()


class HLSManifestView(APIView):
    """``GET /api/video/<movie_id>/<resolution>/index.m3u8`` — HLS playlist."""

    permission_classes = [IsAuthenticated]

    def get(self, request, movie_id, resolution):
        """Return the manifest for one resolution of a video.

        Args:
            request: DRF request.
            movie_id: PK of the requested video.
            resolution: ``480p`` / ``720p`` / ``1080p``.

        Returns:
            FileResponse: HLS manifest with ``application/vnd.apple.mpegurl``.
        """
        get_object_or_404(Video, pk=movie_id)
        return serve_hls_file(
            movie_id, resolution, 'index.m3u8', 'application/vnd.apple.mpegurl',
        )


class HLSSegmentView(APIView):
    """``GET /api/video/<movie_id>/<resolution>/<segment>/`` — single TS file."""

    permission_classes = [IsAuthenticated]

    def get(self, request, movie_id, resolution, segment):
        """Return a single HLS segment for the given video and resolution.

        Args:
            request: DRF request.
            movie_id: PK of the requested video.
            resolution: ``480p`` / ``720p`` / ``1080p``.
            segment: Segment file name (e.g. ``000.ts``).

        Returns:
            FileResponse: The binary segment with ``video/MP2T``.
        """
        get_object_or_404(Video, pk=movie_id)
        return serve_hls_file(movie_id, resolution, segment, 'video/MP2T')
