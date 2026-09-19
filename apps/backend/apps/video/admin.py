from django.contrib import admin

from .models import VideoParticipantEvent, VideoSession


@admin.register(VideoSession)
class VideoSessionAdmin(admin.ModelAdmin):
    list_display = ("appointment", "provider", "status", "available_from", "expires_at", "started_at", "completed_at")
    list_filter = ("provider", "status")
    search_fields = ("appointment__public_id", "appointment__client__email", "appointment__expert__email")
    readonly_fields = (
        "public_id", "appointment", "provider", "provider_room_id", "status", "available_from", "expires_at",
        "started_at", "completed_at", "completed_by", "created_at", "updated_at",
    )

    def has_add_permission(self, request):
        return False


@admin.register(VideoParticipantEvent)
class VideoParticipantEventAdmin(admin.ModelAdmin):
    list_display = ("session", "participant", "role", "event_type", "created_at")
    list_filter = ("role", "event_type")
    search_fields = ("session__appointment__public_id", "participant__email")
    readonly_fields = (
        "public_id", "session", "participant", "role", "event_type", "client_event_id", "created_at", "updated_at",
    )

    def has_add_permission(self, request):
        return False
