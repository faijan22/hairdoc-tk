from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.core.models import BaseModel
from apps.private_media.models import StoredFile


class Conversation(BaseModel):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        CLOSED = "CLOSED", "Closed"

    consultation = models.OneToOneField(
        "consultations.ConsultationCase", on_delete=models.PROTECT, related_name="conversation",
    )
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        ordering = ("-updated_at",)
        indexes = [models.Index(fields=("status", "-updated_at"), name="conversation_status_recent")]


class ConversationMember(BaseModel):
    class Role(models.TextChoices):
        CLIENT = "CLIENT", "Client"
        EXPERT = "EXPERT", "Expert"

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="conversation_memberships")
    role = models.CharField(max_length=12, choices=Role.choices)
    last_read_message = models.ForeignKey(
        "Message", on_delete=models.SET_NULL, related_name="read_by_members", blank=True, null=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("conversation", "user"), name="unique_conversation_member"),
            models.UniqueConstraint(fields=("conversation", "role"), name="unique_conversation_role"),
        ]


class Message(BaseModel):
    conversation = models.ForeignKey(Conversation, on_delete=models.PROTECT, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="sent_messages")
    client_message_id = models.UUIDField()
    body = models.TextField(max_length=4000, blank=True)
    reply_to = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="replies")
    deleted_for_everyone_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at", "-id")
        constraints = [
            models.UniqueConstraint(
                fields=("conversation", "sender", "client_message_id"), name="unique_client_message",
            ),
        ]
        indexes = [models.Index(fields=("conversation", "-created_at", "-id"), name="message_conversation_recent")]


class MessageHidden(BaseModel):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="hidden_by")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="hidden_messages")

    class Meta:
        constraints = [models.UniqueConstraint(fields=("message", "user"), name="unique_hidden_message_user")]


class MessageAttachment(BaseModel):
    message = models.OneToOneField(Message, on_delete=models.CASCADE, related_name="attachment")
    stored_file = models.OneToOneField(StoredFile, on_delete=models.CASCADE, related_name="message_attachment")

    def __str__(self):
        return f"Image for {self.message.public_id}"


class MessageAttachmentAccess(BaseModel):
    attachment = models.ForeignKey(MessageAttachment, on_delete=models.CASCADE, related_name="access_events")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="message_image_accesses")
    request_id = models.CharField(max_length=64, blank=True)

    class Meta:
        ordering = ("-created_at",)


class RealtimeTicket(BaseModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="realtime_tickets")
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="realtime_tickets", null=True, blank=True)
    token_hash = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        indexes = [models.Index(fields=("conversation", "expires_at"), name="realtime_ticket_expiry")]
