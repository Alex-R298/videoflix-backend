import os

from django.conf import settings
from django.http import FileResponse, Http404


def _hls_file_path(video_id, resolution, filename):
    """Resolve the absolute path of an HLS file with a path-traversal guard.

    Args:
        video_id: The Video's primary key.
        resolution: Folder name with the resolution label (e.g. ``480p``).
        filename: Final file name (e.g. ``index.m3u8`` or ``000.ts``).

    Returns:
        str: Absolute filesystem path inside ``MEDIA_ROOT/videos/<id>/<res>/``.

    Raises:
        Http404: If the resolved path escapes the base directory (e.g.
        because ``filename`` contains ``..``).
    """
    base = os.path.realpath(
        os.path.join(settings.MEDIA_ROOT, 'videos', str(video_id), resolution),
    )
    target = os.path.realpath(os.path.join(base, filename))
    if not target.startswith(base + os.sep) and target != base:
        raise Http404('Invalid path.')
    return target


def serve_hls_file(video_id, resolution, filename, content_type):
    """Return a streaming response for an HLS asset or raise 404 if missing.

    Args:
        video_id: The Video's primary key.
        resolution: Resolution folder (``480p`` / ``720p`` / ``1080p``).
        filename: ``index.m3u8`` for the manifest or ``<n>.ts`` for a segment.
        content_type: MIME type to set on the response.

    Returns:
        FileResponse: Streams the file with the given content type.

    Raises:
        Http404: When the file does not exist or the path is unsafe.
    """
    path = _hls_file_path(video_id, resolution, filename)
    if not os.path.isfile(path):
        raise Http404('File not found.')
    return FileResponse(open(path, 'rb'), content_type=content_type)
