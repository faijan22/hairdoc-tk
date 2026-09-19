from django.contrib import admin

from .models import ContentItem


@admin.register(ContentItem)
class ContentItemAdmin(admin.ModelAdmin):
    list_display = ("title", "type", "status", "display_order", "published_at")
    list_filter = ("type", "status")
    search_fields = ("title", "summary", "body")
    prepopulated_fields = {"slug": ("title",)}
    ordering = ("display_order", "-published_at")
    readonly_fields = ("public_id", "created_at", "updated_at")

