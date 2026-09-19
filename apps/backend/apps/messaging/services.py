import hashlib
import io
import logging
import secrets
import uuid
import warnings
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import IntegrityError, transaction
from django.core import signing
from django.db.models import Prefetch
from django.utils import timezone
from PIL import Image, ImageOps, UnidentifiedImageError

from apps.accounts.models import User
from apps.private_media.models import StoredFile
from apps.private_media.storage import get_storage_provider

from .models import Conversation, ConversationMember, Message, MessageAttachment, MessageHidden, RealtimeTicket

logger = logging.getLogger(__name__)
TICKET_SECONDS = 45
ATTACHMENT_TOKEN_SECONDS = 300
ATTACHMENT_TOKEN_SALT = "hairdoc.private-message-image.v1"
MAX_IMAGE_BYTES = 12 * 1024 * 1024
MAX_STORED_IMAGE_BYTES = 8 * 1024 * 1024


class MessagingError(Exception):
    def __init__(self, details):
        self.details = details
        super().__init__("The messaging request could not be completed.")


@transaction.atomic
def ensure_consultation_conversation(appointment):
    conversation, _ = Conversation.objects.get_or_create(consultation=appointment.case)
    ConversationMember.objects.get_or_create(
        conversation=conversation, user=appointment.client, defaults={"role": ConversationMember.Role.CLIENT},
    )
    ConversationMember.objects.get_or_create(
        conversation=conversation, user=appointment.expert, defaults={"role": ConversationMember.Role.EXPERT},
    )
    return conversation


@transaction.atomic
def _normalize_image(uploaded_file):
    if uploaded_file.size > MAX_IMAGE_BYTES:
        raise MessagingError({"file": ["Choose an image smaller than 12 MB."]})
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(uploaded_file.read())) as source:
                if source.format not in {"JPEG", "PNG", "WEBP"}:
                    raise MessagingError({"file": ["Use a JPEG, PNG, or WebP image."]})
                source.load()
                image = ImageOps.exif_transpose(source)
                if min(image.size) < 100:
                    raise MessagingError({"file": ["Choose an image at least 100 pixels on each side."]})
                image.thumbnail((2400, 2400), Image.Resampling.LANCZOS)
                if image.mode != "RGB":
                    background = Image.new("RGB", image.size, "white")
                    background.paste(image, mask=image.getchannel("A") if "A" in image.getbands() else None)
                    image = background
                output = io.BytesIO()
                image.save(output, "JPEG", quality=88, optimize=True)
                content = output.getvalue()
                width, height = image.size
    except MessagingError:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning, UnidentifiedImageError, OSError, ValueError):
        raise MessagingError({"file": ["This is not a valid supported image."]}) from None
    if len(content) > MAX_STORED_IMAGE_BYTES:
        raise MessagingError({"file": ["The processed image is too large."]})
    return content, width, height


@transaction.atomic
def create_message(conversation, sender, body, client_message_id, file=None, reply_to_id=None):
    if not ConversationMember.objects.filter(conversation=conversation, user=sender).exists():
        raise MessagingError({"conversation": ["This conversation is not available."]})
    if conversation.status != Conversation.Status.ACTIVE:
        raise MessagingError({"conversation": ["This conversation is closed."]})
    existing = Message.objects.filter(
        conversation=conversation, sender=sender, client_message_id=client_message_id,
    ).select_related("attachment__stored_file").first()
    if existing:
        if (existing.body != body or bool(file) != hasattr(existing, "attachment")
                or (existing.reply_to.public_id if existing.reply_to_id else None) != reply_to_id):
            raise MessagingError({"client_message_id": ["This message identifier was already used."]})
        return existing, False

    if reply_to_id:
        reply = Message.objects.filter(
            conversation=conversation, public_id=reply_to_id, deleted_for_everyone_at__isnull=True,
        ).exclude(hidden_by__user=sender).first()
        if not reply:
            raise MessagingError({"reply_to_public_id": ["This message is unavailable."]})

    content = width = height = None
    storage_key = None
    if file:
        content, width, height = _normalize_image(file)
        storage_key = f"messages/{conversation.public_id}/{uuid.uuid4()}.jpg"
        get_storage_provider().save(storage_key, content)
    try:
        message, created = Message.objects.get_or_create(
            conversation=conversation, sender=sender, client_message_id=client_message_id,
            defaults={"body": body, "reply_to": reply if reply_to_id else None},
        )
        if created and storage_key:
            stored = StoredFile.objects.create(
                owner=sender, storage_key=storage_key,
                original_name=Path(file.name or "message-image.jpg").name[:255],
                content_type="image/jpeg", byte_size=len(content), checksum_sha256=hashlib.sha256(content).hexdigest(),
                width=width, height=height,
            )
            MessageAttachment.objects.create(message=message, stored_file=stored)
    except IntegrityError:
        message = Message.objects.get(
            conversation=conversation, sender=sender, client_message_id=client_message_id,
        )
        created = False
    except Exception:
        if storage_key:
            get_storage_provider().delete(storage_key)
        raise
    if not created and storage_key:
        get_storage_provider().delete(storage_key)
    if not created and (message.body != body or bool(file) != hasattr(message, "attachment")
                        or message.reply_to_id != (reply.id if reply_to_id else None)):
        raise MessagingError({"client_message_id": ["This message identifier was already used."]})
    if created:
        Conversation.objects.filter(pk=conversation.pk).update(updated_at=timezone.now())
        transaction.on_commit(lambda: _message_committed(message.pk))
    return message, created


def _message_committed(message_id):
    message = Message.objects.select_related("conversation", "sender").get(pk=message_id)
    try:
        from apps.notifications.services import notify_new_message
        notify_new_message(message)
    except Exception:
        logger.exception("Message notification enqueue failed for %s.", message.public_id)
    _broadcast_message(message)


def _broadcast_message(message):
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(conversation_group(message.conversation.public_id), {
            "type": "message.created", "message": message_payload(message),
        })
        _broadcast_inbox_snapshot(message.conversation)
    except Exception:
        logger.warning("Realtime message broadcast failed for message %s.", message.public_id)


def broadcast_read(conversation, user_public_id, message_public_id):
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(conversation_group(conversation.public_id), {
            "type": "conversation.read", "user_public_id": str(user_public_id),
            "message_public_id": str(message_public_id),
        })
        _broadcast_inbox_snapshot(conversation)
    except Exception:
        logger.warning("Realtime read broadcast failed for conversation %s.", conversation.public_id)


def message_payload(message):
    has_attachment = hasattr(message, "attachment")
    return {
        "public_id": str(message.public_id), "conversation_public_id": str(message.conversation.public_id),
        "sender_public_id": str(message.sender.public_id),
        "sender_name": f"{message.sender.first_name} {message.sender.last_name}".strip() or message.sender.email,
        "body": "" if message.deleted_for_everyone_at else message.body,
        "status": "SENT", "attachment": None,
        "attachment_pending": has_attachment, "client_message_id": str(message.client_message_id),
        "deleted_for_everyone": bool(message.deleted_for_everyone_at),
        "reply_to": reply_payload(message.reply_to),
        "created_at": message.created_at.isoformat(),
    }


def reply_payload(message):
    if not message:
        return None
    return {
        "public_id": str(message.public_id),
        "sender_name": f"{message.sender.first_name} {message.sender.last_name}".strip() or message.sender.email,
        "body": "" if message.deleted_for_everyone_at else message.body[:120],
        "deleted_for_everyone": bool(message.deleted_for_everyone_at),
        "has_attachment": not message.deleted_for_everyone_at and hasattr(message, "attachment"),
    }


@transaction.atomic
def delete_message_for_everyone(conversation, actor, message):
    if message.conversation_id != conversation.id or message.sender_id != actor.id:
        raise MessagingError({"message": ["This message cannot be deleted for everyone."]})
    if message.deleted_for_everyone_at:
        return message
    attachment = getattr(message, "attachment", None)
    if attachment:
        stored = attachment.stored_file
        key = stored.storage_key
        attachment.delete()
        stored.delete()
        transaction.on_commit(lambda: get_storage_provider().delete(key))
    message.body = ""
    message.deleted_for_everyone_at = timezone.now()
    message.save(update_fields=("body", "deleted_for_everyone_at", "updated_at"))
    transaction.on_commit(lambda: _broadcast_message_deleted(message))
    return message


def _broadcast_message_deleted(message):
    try:
        async_to_sync(get_channel_layer().group_send)(conversation_group(message.conversation.public_id), {
            "type": "message.deleted", "message_public_id": str(message.public_id),
        })
        _broadcast_inbox_snapshot(message.conversation)
    except Exception:
        logger.warning("Realtime deletion broadcast failed for message %s.", message.public_id)


def hide_message_for_user(conversation, actor, message):
    if message.conversation_id != conversation.id or not ConversationMember.objects.filter(
        conversation=conversation, user=actor,
    ).exists():
        raise MessagingError({"message": ["This message is unavailable."]})
    MessageHidden.objects.get_or_create(message=message, user=actor)
    _broadcast_inbox_snapshot(conversation, only_user_id=actor.id)


def issue_attachment_access_token(attachment, viewer):
    if not ConversationMember.objects.filter(conversation=attachment.message.conversation, user=viewer).exists():
        raise MessagingError({"attachment": ["This image is not available."]})
    return signing.dumps(
        {"attachment": str(attachment.public_id), "viewer": str(viewer.public_id)},
        salt=ATTACHMENT_TOKEN_SALT, compress=True,
    )


def resolve_attachment_access(token):
    from .models import MessageAttachment
    try:
        payload = signing.loads(token, salt=ATTACHMENT_TOKEN_SALT, max_age=ATTACHMENT_TOKEN_SECONDS)
        viewer = User.objects.get(public_id=payload["viewer"], is_active=True)
        attachment = MessageAttachment.objects.select_related(
            "message__conversation", "stored_file",
        ).get(public_id=payload["attachment"])
    except (signing.BadSignature, signing.SignatureExpired, KeyError, User.DoesNotExist, MessageAttachment.DoesNotExist):
        raise MessagingError({"token": ["This private image link is invalid or expired."]}) from None
    if not ConversationMember.objects.filter(conversation=attachment.message.conversation, user=viewer).exists():
        raise MessagingError({"attachment": ["This image is not available."]})
    return attachment, viewer


def conversation_group(public_id):
    return f"conversation_{str(public_id).replace('-', '')}"


def inbox_group(public_id):
    return f"inbox_{str(public_id).replace('-', '')}"


def _broadcast_inbox_snapshot(conversation, only_user_id=None):
    """Send each member only the inbox row they are authorized to see."""
    from .serializers import ConversationSerializer

    members = ConversationMember.objects.filter(conversation=conversation).select_related("user")
    if only_user_id:
        members = members.filter(user_id=only_user_id)
    channel_layer = get_channel_layer()
    for member in members:
        snapshot = Conversation.objects.filter(pk=conversation.pk).select_related("consultation").prefetch_related(
            "members__user", "members__last_read_message",
            Prefetch(
                "messages",
                queryset=Message.objects.exclude(hidden_by__user=member.user).select_related(
                    "sender", "attachment__stored_file", "reply_to__sender", "reply_to__attachment",
                ).order_by("-created_at", "-id")[:1],
                to_attr="latest_messages",
            ),
        ).get()
        payload = ConversationSerializer(snapshot, context={"request": SimpleNamespace(user=member.user)}).data
        async_to_sync(channel_layer.group_send)(inbox_group(member.user.public_id), {
            "type": "inbox.changed", "conversation": payload,
        })


@transaction.atomic
def issue_ticket(user, conversation):
    if conversation and not ConversationMember.objects.filter(conversation=conversation, user=user).exists():
        raise MessagingError({"conversation": ["This conversation is not available."]})
    raw = secrets.token_urlsafe(32)
    ticket = RealtimeTicket.objects.create(
        user=user, conversation=conversation, token_hash=_hash(raw),
        expires_at=timezone.now() + timedelta(seconds=TICKET_SECONDS),
    )
    return ticket, raw


@transaction.atomic
def consume_ticket(raw, conversation_public_id=None):
    if not raw:
        return None
    tickets = RealtimeTicket.objects.select_for_update().select_related("user").filter(token_hash=_hash(raw))
    tickets = tickets.filter(conversation__public_id=conversation_public_id) if conversation_public_id else tickets.filter(conversation__isnull=True)
    ticket = tickets.first()
    if not ticket or ticket.used_at or ticket.expires_at <= timezone.now() or not ticket.user.is_active:
        return None
    if ticket.conversation and not ConversationMember.objects.filter(conversation=ticket.conversation, user=ticket.user).exists():
        return None
    ticket.used_at = timezone.now()
    ticket.save(update_fields=("used_at", "updated_at"))
    return ticket


def _hash(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
