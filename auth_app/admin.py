from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin


User = get_user_model()
admin.site.unregister(User)


@admin.register(User)
class VideoflixUserAdmin(UserAdmin):
    """User admin tweaked to surface ``is_active`` directly in the list view.

    Reviewers asked for an at-a-glance way to tell which accounts have
    confirmed their email — without having to open each user's detail page.
    """

    list_display = (
        'username', 'email', 'is_active', 'is_staff', 'date_joined',
    )
    list_filter = ('is_active', 'is_staff', 'is_superuser')
    ordering = ('-date_joined',)
