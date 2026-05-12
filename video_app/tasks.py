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
    """Return the absolute folder for HLS files of a video at a resolution."""
    return os.path.join(
        settings.MEDIA_ROOT, 'videos', str(video_id), resolution,
    )


def _build_hls_command(source, output_dir, scale):
    """Return the ffmpeg argv list that converts source to HLS at one scale."""
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
    """Convert a video to HLS at a single resolution."""
    output_dir = _hls_output_dir(video_id, resolution)
    os.makedirs(output_dir, exist_ok=True)
    cmd = _build_hls_command(source, output_dir, HLS_RESOLUTIONS[resolution])
    subprocess.run(cmd, check=True)


def extract_thumbnail(source, video_id):
    """Extract one frame near the start of the video as a JPEG thumbnail."""
    output_dir = os.path.join(settings.MEDIA_ROOT, 'thumbnails')
    os.makedirs(output_dir, exist_ok=True)
    target = os.path.join(output_dir, f'{video_id}.jpg')
    cmd = ['ffmpeg', '-y', '-ss', '00:00:01', '-i', source,
           '-vframes', '1', target]
    subprocess.run(cmd, check=True)
    return target


def process_video(video_id):
    """Run the full pipeline: HLS for all resolutions plus the thumbnail."""
    video = Video.objects.get(pk=video_id)
    source = video.video_file.path
    for resolution in HLS_RESOLUTIONS:
        convert_to_hls(source, video_id, resolution)
    thumbnail_path = extract_thumbnail(source, video_id)
    rel = os.path.relpath(thumbnail_path, settings.MEDIA_ROOT)
    video.thumbnail.name = rel.replace(os.sep, '/')
    video.save(update_fields=['thumbnail'])
