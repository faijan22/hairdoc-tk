from django.contrib import admin

from .models import StoredFile


@admin.register(StoredFile)
class StoredFileAdmin(admin.ModelAdmin):
    list_display = ("public_id", "original_name", "owner", "content_type", "byte_size", "status", "created_at")
    search_fields = ("public_id", "original_name", "owner__email", "checksum_sha256")
    list_filter = ("status", "content_type")
    readonly_fields = (
        "public_id", "owner", "storage_key", "original_name", "content_type", "byte_size",
        "checksum_sha256", "width", "height", "status", "created_at", "updated_at",
    )

    def has_add_permission(self, request):
        return False
