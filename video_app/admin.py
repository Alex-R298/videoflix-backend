from django.contrib import admin

from .models import Video


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    """Admin configuration for the Video model.

    Surfaces the category and creation date in the list view and makes the
    auto-generated ``thumbnail`` read-only since it is created by the
    background worker, not by hand.
    """

    list_display = ('title', 'category', 'created_at')
    list_filter = ('category',)
    search_fields = ('title', 'description')
    readonly_fields = ('created_at', 'thumbnail')
