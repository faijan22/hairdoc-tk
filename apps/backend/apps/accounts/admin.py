from django.contrib import admin

from .models import ClientHairProfile, DeviceSession, EmailActionToken, LegalDocument, NotificationPreference, RefreshTokenRecord, User, UserConsent


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("email", "is_email_verified", "is_staff", "is_active", "deleted_at", "created_at")
    list_filter = ("is_email_verified", "is_staff", "is_active", "deleted_at")
    search_fields = ("email", "first_name", "last_name")
    ordering = ("-created_at",)
    readonly_fields = ("public_id", "normalized_email", "password", "last_login", "deleted_at", "created_at", "updated_at")


@admin.register(DeviceSession)
class DeviceSessionAdmin(admin.ModelAdmin):
    list_display = ("public_id", "user", "device_name", "last_used_at", "expires_at", "revoked_at")
    list_filter = ("revoked_at",)
    search_fields = ("user__email", "device_name", "public_id")
    readonly_fields = ("public_id", "family_id", "created_at", "last_used_at")


@admin.register(RefreshTokenRecord)
class RefreshTokenRecordAdmin(admin.ModelAdmin):
    list_display = ("session", "created_at", "expires_at", "used_at")
    readonly_fields = ("token_hash", "created_at", "expires_at", "used_at")


@admin.register(EmailActionToken)
class EmailActionTokenAdmin(admin.ModelAdmin):
    list_display = ("user", "purpose", "created_at", "expires_at", "used_at")
    list_filter = ("purpose",)
    readonly_fields = ("token_hash", "created_at", "expires_at", "used_at")


@admin.register(ClientHairProfile)
class ClientHairProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "hair_texture", "scalp_type", "updated_at")
    list_filter = ("hair_texture", "scalp_type")
    search_fields = ("user__email", "concerns", "goals")


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ("user", "timezone", "email_enabled", "push_enabled", "updated_at")
    search_fields = ("user__email", "timezone")


@admin.register(LegalDocument)
class LegalDocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "type", "version", "status", "published_at")
    list_filter = ("type", "status")
    search_fields = ("title", "body")
    readonly_fields = ("public_id", "created_at", "updated_at")
    fieldsets = (
        ("Document", {"fields": ("type", "version", "title", "body", "attachment")}),
        ("Publication", {"fields": ("status", "published_at")}),
        ("System", {"fields": ("public_id", "created_at", "updated_at"), "classes": ("collapse",)}),
    )


@admin.register(UserConsent)
class UserConsentAdmin(admin.ModelAdmin):
    list_display = ("user", "legal_document", "accepted_at", "withdrawn_at")
    list_filter = ("legal_document__type", "withdrawn_at")
    search_fields = ("user__email", "legal_document__title")
    readonly_fields = ("user", "legal_document", "accepted_at", "withdrawn_at")
