import os

from django.conf import settings
from django.http import FileResponse, Http404


def _hls_file_path(video_id, resolution, filename):
    """Return the absolute path of an HLS file, guarded against traversal."""
    base = os.path.realpath(
        os.path.join(settings.MEDIA_ROOT, 'videos', str(video_id), resolution),
    )
    target = os.path.realpath(os.path.join(base, filename))
    if not target.startswith(base + os.sep) and target != base:
        raise Http404('Invalid path.')
    return target


def serve_hls_file(video_id, resolution, filename, content_type):
    """Return a FileResponse for an HLS file or raise Http404 if missing."""
    path = _hls_file_path(video_id, resolution, filename)
    if not os.path.isfile(path):
        raise Http404('File not found.')
    return FileResponse(open(path, 'rb'), content_type=content_type)
