from django.db import migrations
from django.db.models import Count


def merge_duplicate_direct_conversations(apps, schema_editor):
    Conversation = apps.get_model("messaging", "Conversation")
    ConversationMember = apps.get_model("messaging", "ConversationMember")
    Message = apps.get_model("messaging", "Message")
    MessageHidden = apps.get_model("messaging", "MessageHidden")
    MessageAttachment = apps.get_model("messaging", "MessageAttachment")
    RealtimeTicket = apps.get_model("messaging", "RealtimeTicket")
    Notification = apps.get_model("notifications", "Notification")

    pairs = {}
    for conversation_id in Conversation.objects.values_list("id", flat=True).iterator():
        members = list(
            ConversationMember.objects.filter(conversation_id=conversation_id).values("user_id", "role")
        )
        client_ids = [member["user_id"] for member in members if member["role"] == "CLIENT"]
        expert_ids = [member["user_id"] for member in members if member["role"] == "EXPERT"]
        if len(client_ids) == 1 and len(expert_ids) == 1:
            pairs.setdefault((client_ids[0], expert_ids[0]), []).append(conversation_id)

    for conversation_ids in pairs.values():
        if len(conversation_ids) < 2:
            continue

        conversations = list(
            Conversation.objects.filter(id__in=conversation_ids)
            .annotate(message_count=Count("messages"))
            .order_by("-message_count", "created_at", "id")
        )
        canonical = conversations[0]
        canonical_members = {
            member.user_id: member
            for member in ConversationMember.objects.filter(conversation_id=canonical.id)
        }
        latest_updated_at = max(conversation.updated_at for conversation in conversations)
        should_be_active = any(conversation.status == "ACTIVE" for conversation in conversations)

        for duplicate in conversations[1:]:
            duplicate_members = list(ConversationMember.objects.filter(conversation_id=duplicate.id))
            remapped_message_ids = {}

            # A retry carrying the same client-generated message id is the only
            # possible unique-key collision. Preserve its related state on the
            # canonical message before removing the duplicate copy.
            for message in list(Message.objects.filter(conversation_id=duplicate.id)):
                existing = Message.objects.filter(
                    conversation_id=canonical.id,
                    sender_id=message.sender_id,
                    client_message_id=message.client_message_id,
                ).first()
                if not existing:
                    continue

                remapped_message_ids[message.id] = existing.id
                Message.objects.filter(reply_to_id=message.id).update(reply_to_id=existing.id)
                for hidden in MessageHidden.objects.filter(message_id=message.id):
                    MessageHidden.objects.get_or_create(message_id=existing.id, user_id=hidden.user_id)

                duplicate_notification = Notification.objects.filter(message_id=message.id).first()
                if duplicate_notification:
                    if Notification.objects.filter(message_id=existing.id).exists():
                        duplicate_notification.delete()
                    else:
                        duplicate_notification.message_id = existing.id
                        duplicate_notification.conversation_id = canonical.id
                        duplicate_notification.route = f"/messages/{canonical.public_id}"
                        duplicate_notification.save(
                            update_fields=("message_id", "conversation_id", "route", "updated_at")
                        )

                duplicate_attachment = MessageAttachment.objects.filter(message_id=message.id).first()
                if duplicate_attachment and not MessageAttachment.objects.filter(message_id=existing.id).exists():
                    duplicate_attachment.message_id = existing.id
                    duplicate_attachment.save(update_fields=("message_id", "updated_at"))
                message.delete()

            Message.objects.filter(conversation_id=duplicate.id).update(conversation_id=canonical.id)
            Notification.objects.filter(conversation_id=duplicate.id).update(
                conversation_id=canonical.id,
                route=f"/messages/{canonical.public_id}",
            )
            RealtimeTicket.objects.filter(conversation_id=duplicate.id).delete()

            for duplicate_member in duplicate_members:
                canonical_member = canonical_members.get(duplicate_member.user_id)
                if not canonical_member or not duplicate_member.last_read_message_id:
                    continue
                duplicate_read_id = remapped_message_ids.get(
                    duplicate_member.last_read_message_id,
                    duplicate_member.last_read_message_id,
                )
                current_read = (
                    Message.objects.filter(id=canonical_member.last_read_message_id).first()
                    if canonical_member.last_read_message_id
                    else None
                )
                duplicate_read = Message.objects.filter(id=duplicate_read_id).first()
                if duplicate_read and (
                    not current_read
                    or (duplicate_read.created_at, duplicate_read.id) > (current_read.created_at, current_read.id)
                ):
                    canonical_member.last_read_message_id = duplicate_read.id
                    canonical_member.save(update_fields=("last_read_message_id", "updated_at"))

            ConversationMember.objects.filter(conversation_id=duplicate.id).delete()
            duplicate.delete()

        Conversation.objects.filter(id=canonical.id).update(
            status="ACTIVE" if should_be_active else canonical.status,
            updated_at=latest_updated_at,
        )


class Migration(migrations.Migration):
    dependencies = [
        ("messaging", "0005_inbox_realtime_ticket"),
        ("notifications", "0004_pushdevice_session"),
    ]

    operations = [
        migrations.RunPython(merge_duplicate_direct_conversations, migrations.RunPython.noop),
    ]
