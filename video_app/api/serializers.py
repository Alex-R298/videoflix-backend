from rest_framework import serializers

from video_app.models import Video


class VideoListSerializer(serializers.ModelSerializer):
    """Serializes a Video record for the public list endpoint."""

    thumbnail_url = serializers.SerializerMethodField()

    class Meta:
        model = Video
        fields = (
            'id', 'created_at', 'title',
            'description', 'thumbnail_url', 'category',
        )

    def get_thumbnail_url(self, obj):
        """Build an absolute URL to the thumbnail, or ``None`` if not yet generated.

        Args:
            obj: The ``Video`` instance being serialized.

        Returns:
            str | None: Absolute URL when a thumbnail exists, otherwise ``None``.
        """
        if not obj.thumbnail:
            return None
        request = self.context.get('request')
        url = obj.thumbnail.url
        return request.build_absolute_uri(url) if request else url
