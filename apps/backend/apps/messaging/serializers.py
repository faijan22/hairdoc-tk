from rest_framework import serializers

from .models import Conversation, ConversationMember, Message
from .services import issue_attachment_access_token, reply_payload


class MessageSerializer(serializers.ModelSerializer):
    conversation_public_id = serializers.UUIDField(source="conversation.public_id", read_only=True)
    sender_public_id = serializers.UUIDField(source="sender.public_id", read_only=True)
    sender_name = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    attachment = serializers.SerializerMethodField()
    reply_to = serializers.SerializerMethodField()
    deleted_for_everyone = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = (
            "public_id", "conversation_public_id", "sender_public_id", "sender_name",
            "body", "attachment", "status", "client_message_id", "created_at",
            "reply_to", "deleted_for_everyone",
        )

    def get_sender_name(self, obj):
        return f"{obj.sender.first_name} {obj.sender.last_name}".strip() or obj.sender.email

    def get_status(self, obj):
        viewer = self.context.get("viewer")
        if not viewer or obj.sender_id != viewer.id:
            return "READ"
        other = next((member for member in obj.conversation.members.all() if member.user_id != viewer.id), None)
        read = other.last_read_message if other else None
        return "READ" if read and (read.created_at, read.id) >= (obj.created_at, obj.id) else "SENT"

    def get_attachment(self, obj):
        if obj.deleted_for_everyone_at:
            return None
        attachment = getattr(obj, "attachment", None)
        viewer = self.context.get("viewer")
        if not attachment or not viewer:
            return None
        token = issue_attachment_access_token(attachment, viewer)
        return {
            "public_id": attachment.public_id,
            "content_type": attachment.stored_file.content_type,
            "byte_size": attachment.stored_file.byte_size,
            "width": attachment.stored_file.width,
            "height": attachment.stored_file.height,
            "content_path": f"/api/v1/private-files/message-images/{attachment.public_id}/?token={token}",
        }

    def get_reply_to(self, obj):
        return reply_payload(obj.reply_to)

    def get_deleted_for_everyone(self, obj):
        return bool(obj.deleted_for_everyone_at)


class MessageCreateSerializer(serializers.Serializer):
    body = serializers.CharField(max_length=4000, trim_whitespace=True, required=False, allow_blank=True, default="")
    file = serializers.FileField(required=False)
    client_message_id = serializers.UUIDField()
    reply_to_public_id = serializers.UUIDField(required=False, source="reply_to_id")

    def validate(self, attrs):
        if not attrs.get("body") and not attrs.get("file"):
            raise serializers.ValidationError("Write a message or attach an image.")
        return attrs


class ConversationSerializer(serializers.ModelSerializer):
    consultation_public_id = serializers.UUIDField(source="consultation.public_id", read_only=True)
    service_name = serializers.CharField(source="consultation.service_name", read_only=True)
    other_member_name = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = (
            "public_id", "consultation_public_id", "service_name", "status", "other_member_name",
            "last_message", "unread_count", "created_at", "updated_at",
        )

    def _membership(self, obj):
        user = self.context["request"].user
        return next(member for member in obj.members.all() if member.user_id == user.id)

    def get_other_member_name(self, obj):
        user = self.context["request"].user
        other = next((member.user for member in obj.members.all() if member.user_id != user.id), None)
        return (f"{other.first_name} {other.last_name}".strip() or other.email) if other else "Care team"

    def get_last_message(self, obj):
        user = self.context["request"].user
        message = (
            obj.latest_messages[0] if obj.latest_messages else None
        ) if hasattr(obj, "latest_messages") else obj.messages.exclude(hidden_by__user=user).select_related("sender").first()
        return MessageSerializer(message, context={"viewer": user}).data if message else None

    def get_unread_count(self, obj):
        membership = self._membership(obj)
        messages = obj.messages.exclude(sender_id=membership.user_id).exclude(hidden_by__user=membership.user)
        if membership.last_read_message_id:
            messages = messages.filter(created_at__gt=membership.last_read_message.created_at)
        return messages.count()


class ReadSerializer(serializers.Serializer):
    message_public_id = serializers.UUIDField(required=False)


class TicketSerializer(serializers.Serializer):
    conversation_public_id = serializers.UUIDField(required=False)
