from django.contrib import admin

from .models import Conversation, ConversationMember, Message, MessageAttachment, MessageAttachmentAccess, RealtimeTicket


class ReadOnlyMessagingAdmin(admin.ModelAdmin):
    def has_add_permission(self, request): return False
    def has_delete_permission(self, request, obj=None): return False


@admin.register(Conversation)
class ConversationAdmin(ReadOnlyMessagingAdmin):
    list_display = ("public_id", "consultation", "status", "updated_at")
    search_fields = ("public_id", "consultation__public_id", "consultation__client__email")
    readonly_fields = tuple(field.name for field in Conversation._meta.fields)


@admin.register(ConversationMember)
class ConversationMemberAdmin(ReadOnlyMessagingAdmin):
    list_display = ("conversation", "user", "role", "last_read_message")
    readonly_fields = tuple(field.name for field in ConversationMember._meta.fields)


@admin.register(Message)
class MessageAdmin(ReadOnlyMessagingAdmin):
    list_display = ("public_id", "conversation", "sender", "created_at")
    search_fields = ("public_id", "conversation__public_id", "sender__email")
    readonly_fields = tuple(field.name for field in Message._meta.fields)


@admin.register(MessageAttachment)
class MessageAttachmentAdmin(ReadOnlyMessagingAdmin):
    list_display = ("public_id", "message", "stored_file", "created_at")
    readonly_fields = tuple(field.name for field in MessageAttachment._meta.fields)


@admin.register(MessageAttachmentAccess)
class MessageAttachmentAccessAdmin(ReadOnlyMessagingAdmin):
    list_display = ("attachment", "actor", "created_at")
    readonly_fields = tuple(field.name for field in MessageAttachmentAccess._meta.fields)


@admin.register(RealtimeTicket)
class RealtimeTicketAdmin(ReadOnlyMessagingAdmin):
    list_display = ("public_id", "user", "conversation", "expires_at", "used_at")
    readonly_fields = tuple(field.name for field in RealtimeTicket._meta.fields)
