from .models import Video
from django.dispatch import receiver
from django.db.models.signals import post_save, post_delete
import os
from .tasks import convert_480p

@receiver(post_save, sender=Video)
def video_post_save(sender, instance, created, **kwargs):
    print(f'Video "{instance.title}" has been saved.')

    if created:
        print('New object created')
        convert_480p(instance.video_file.path)


@receiver(post_delete, sender=Video)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    """
    Deletes file from filesystem
    when corresponding `Video` object is deleted.
    """
    if instance.video_file:
        if os.path.isfile(instance.video_file.path):
            os.remove(instance.video_file.path)



