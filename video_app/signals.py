import os

import django_rq
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Video
from .tasks import process_video


@receiver(post_save, sender=Video)
def enqueue_video_processing(sender, instance, created, **kwargs):
    """Schedule HLS conversion and thumbnail generation on initial upload."""
    if not created:
        return
    django_rq.get_queue('default').enqueue(process_video, instance.pk)


@receiver(post_delete, sender=Video)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    """Remove the uploaded source file when a Video row is deleted."""
    if instance.video_file and os.path.isfile(instance.video_file.path):
        os.remove(instance.video_file.path)
