from rest_framework.generics import ListAPIView

from video_app.models import Video

from .serializers import VideoListSerializer


class VideoListView(ListAPIView):
    """GET /api/video/ — return all available videos."""

    serializer_class = VideoListSerializer
    queryset = Video.objects.all()
