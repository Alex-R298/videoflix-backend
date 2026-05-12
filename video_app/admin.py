from django.contrib import admin

from .models import Video


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'created_at')
    list_filter = ('category',)
    search_fields = ('title', 'description')
    readonly_fields = ('created_at', 'thumbnail')
