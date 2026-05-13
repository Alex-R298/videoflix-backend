import os
import subprocess

from django.conf import settings

from .models import Video


HLS_RESOLUTIONS = {
    '480p': '854:480',
    '720p': '1280:720',
    '1080p': '1920:1080',
}


def _hls_output_dir(video_id, resolution):
    """Build the absolute output directory for one resolution.

    Args:
        video_id: PK of the source video.
        resolution: Resolution label, e.g. ``480p``.

    Returns:
        str: ``MEDIA_ROOT/videos/<video_id>/<resolution>``.
    """
    return os.path.join(
        settings.MEDIA_ROOT, 'videos', str(video_id), resolution,
    )


def _build_hls_command(source, output_dir, scale):
    """Build the ffmpeg argument list for a single HLS conversion pass.

    Args:
        source: Absolute path of the original video file.
        output_dir: Where ``index.m3u8`` and the ``.ts`` segments go.
        scale: ffmpeg scale filter value (e.g. ``854:480``).

    Returns:
        list[str]: ffmpeg argv ready to hand to ``subprocess.run``.
    """
    return [
        'ffmpeg', '-y', '-i', source,
        '-vf', f'scale={scale}',
        '-c:v', 'libx264', '-crf', '23',
        '-c:a', 'aac',
        '-hls_time', '10', '-hls_playlist_type', 'vod',
        '-hls_segment_filename', os.path.join(output_dir, '%03d.ts'),
        os.path.join(output_dir, 'index.m3u8'),
    ]


def convert_to_hls(source, video_id, resolution):
    """Run ffmpeg to convert a source video into HLS at one resolution.

    Args:
        source: Absolute path of the original video file.
        video_id: PK of the source video.
        resolution: One of the keys in ``HLS_RESOLUTIONS``.
    """
    output_dir = _hls_output_dir(video_id, resolution)
    os.makedirs(output_dir, exist_ok=True)
    cmd = _build_hls_command(source, output_dir, HLS_RESOLUTIONS[resolution])
    subprocess.run(cmd, check=True)


def extract_thumbnail(source, video_id):
    """Extract one frame near the start of the video as a JPEG thumbnail.

    Args:
        source: Absolute path of the original video file.
        video_id: PK of the source video; used as the thumbnail filename stem.

    Returns:
        str: Absolute path of the generated thumbnail.
    """
    output_dir = os.path.join(settings.MEDIA_ROOT, 'thumbnails')
    os.makedirs(output_dir, exist_ok=True)
    target = os.path.join(output_dir, f'{video_id}.jpg')
    cmd = ['ffmpeg', '-y', '-ss', '00:00:01', '-i', source,
           '-vframes', '1', target]
    subprocess.run(cmd, check=True)
    return target


def process_video(video_id):
    """Background entry point: build all HLS resolutions plus the thumbnail.

    Args:
        video_id: PK of the uploaded video. The matching ``Video`` row's
        ``thumbnail`` field is updated once extraction succeeds.
    """
    video = Video.objects.get(pk=video_id)
    source = video.video_file.path
    for resolution in HLS_RESOLUTIONS:
        convert_to_hls(source, video_id, resolution)
    thumbnail_path = extract_thumbnail(source, video_id)
    rel = os.path.relpath(thumbnail_path, settings.MEDIA_ROOT)
    video.thumbnail.name = rel.replace(os.sep, '/')
    video.save(update_fields=['thumbnail'])
