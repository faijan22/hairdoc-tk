from django.contrib import admin

from .models import ProgressCheckIn, ProgressPhoto, ProgressPhotoAccess


class ProgressPhotoInline(admin.TabularInline):
    model = ProgressPhoto
    extra = 0
    readonly_fields = ("public_id", "stored_file", "category", "consent_document", "consent_accepted_at", "created_at")


@admin.register(ProgressCheckIn)
class ProgressCheckInAdmin(admin.ModelAdmin):
    list_display = ("client", "case", "sequence", "status", "submitted_at", "feedback_published_at")
    list_filter = ("status", "case__service")
    search_fields = ("client__email", "case__public_id", "summary")
    readonly_fields = ("public_id", "case", "client", "sequence", "status", "summary", "wins", "challenges", "routine_adherence", "questions_for_tk", "submitted_at", "expert_feedback", "reviewed_by", "feedback_published_at", "created_at", "updated_at")
    inlines = (ProgressPhotoInline,)


@admin.register(ProgressPhotoAccess)
class ProgressPhotoAccessAdmin(admin.ModelAdmin):
    list_display = ("photo", "actor", "purpose", "created_at")
    readonly_fields = ("public_id", "photo", "actor", "purpose", "request_id", "created_at", "updated_at")

    def has_add_permission(self, request):
        return False
