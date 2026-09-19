import logging
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.conf import settings
from django.db import transaction

from apps.accounts.models import NotificationPreference
from apps.messaging.models import ConversationMember

from .models import EmailDelivery, Notification, PushDelivery

logger = logging.getLogger(__name__)


def _preferences(user):
    return NotificationPreference.objects.get_or_create(user=user)[0]


@transaction.atomic
def create_notification(
    *, recipient, kind, title, body, route, dedupe_key,
    preference_field=None, email=False, conversation=None, message=None,
):
    preferences = _preferences(recipient)
    if preference_field and not getattr(preferences, preference_field):
        return None
    notification, created = Notification.objects.get_or_create(
        dedupe_key=dedupe_key,
        defaults={
            "recipient": recipient,
            "kind": kind,
            "title": title,
            "body": body,
            "route": route,
            "conversation": conversation,
            "message": message,
        },
    )
    if not created:
        return notification
    transaction.on_commit(lambda: _broadcast_notification(notification.pk))
    push_deliveries = []
    if preferences.push_enabled:
        push_deliveries = [
            PushDelivery(notification=notification, device=device)
            for device in recipient.push_devices.filter(active=True)
        ]
        PushDelivery.objects.bulk_create(push_deliveries, ignore_conflicts=True)
    email_delivery = None
    if email and preferences.email_enabled:
        email_delivery, _ = EmailDelivery.objects.get_or_create(notification=notification)
    if (
        (push_deliveries and settings.PUSH_NOTIFICATIONS_ENABLED)
        or (email_delivery and settings.EMAIL_NOTIFICATIONS_ENABLED)
    ):
        transaction.on_commit(lambda: _enqueue_notification(notification.pk))
    return notification


def _broadcast_notification(notification_id):
    try:
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer
        from apps.messaging.services import inbox_group
        from .serializers import NotificationSerializer

        notification = Notification.objects.select_related("recipient", "conversation").get(pk=notification_id)
        async_to_sync(get_channel_layer().group_send)(inbox_group(notification.recipient.public_id), {
            "type": "notification.created", "notification": NotificationSerializer(notification).data,
        })
    except Exception:
        logger.exception("Realtime notification broadcast failed.")


def broadcast_notifications_read(user, notification_ids, read_at):
    try:
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer
        from apps.messaging.services import inbox_group

        async_to_sync(get_channel_layer().group_send)(inbox_group(user.public_id), {
            "type": "notifications.read",
            "notification_ids": [str(item) for item in notification_ids],
            "read_at": read_at.isoformat(),
            "unread_count": user.notifications.filter(read_at__isnull=True).count(),
        })
    except Exception:
        logger.exception("Realtime notification read broadcast failed.")


def _enqueue_notification(notification_id):
    try:
        from .tasks import deliver_notification

        deliver_notification.delay(notification_id)
    except Exception:
        logger.exception("Could not enqueue notification %s.", notification_id)


def notify_new_message(message):
    member = ConversationMember.objects.select_related("user").filter(
        conversation=message.conversation,
    ).exclude(user=message.sender).get()
    sender_name = "TK" if message.sender.is_staff else (
        f"{message.sender.first_name} {message.sender.last_name}".strip() or "a client"
    )
    return create_notification(
        recipient=member.user,
        kind=Notification.Kind.NEW_MESSAGE,
        title="New private message",
        body=f"You have a new message from {sender_name}.",
        route=f"/messages/{message.conversation.public_id}",
        dedupe_key=f"message:{message.public_id}",
        preference_field="message_notifications",
        conversation=message.conversation,
        message=message,
    )


def notify_consultation_submitted(case):
    expert = case.service.expert
    if not expert:
        return None
    return create_notification(
        recipient=expert,
        kind=Notification.Kind.CONSULTATION_SUBMITTED,
        title="Consultation ready for review",
        body="A client submitted their intake and private photos.",
        route=f"/staff/consultations/{case.public_id}",
        dedupe_key=f"consultation:{case.public_id}:submitted",
        preference_field="coaching_updates",
        email=True,
    )


def _appointment_route(appointment, recipient):
    if recipient.pk == appointment.expert_id:
        return "/staff/appointments"
    return f"/appointments/{appointment.public_id}"


def _appointment_time(appointment, recipient):
    preferences = _preferences(recipient)
    try:
        zone = ZoneInfo(preferences.timezone)
    except (ZoneInfoNotFoundError, ValueError):
        zone = ZoneInfo("UTC")
    return appointment.starts_at.astimezone(zone).strftime("%a, %d %b at %H:%M %Z")


def _notify_appointment(appointment, *, kind, title, action, dedupe_suffix, preference_field=None):
    notifications = []
    for recipient in (appointment.client, appointment.expert):
        notifications.append(create_notification(
            recipient=recipient,
            kind=kind,
            title=title,
            body=f"Your consultation appointment {action} {_appointment_time(appointment, recipient)}.",
            route=_appointment_route(appointment, recipient),
            dedupe_key=f"appointment:{appointment.public_id}:{dedupe_suffix}:user:{recipient.pk}",
            preference_field=preference_field,
            email=True,
        ))
    return notifications


def notify_appointment_confirmed(appointment):
    return _notify_appointment(
        appointment, kind=Notification.Kind.APPOINTMENT_CONFIRMED,
        title="Appointment confirmed", action="is confirmed for", dedupe_suffix="confirmed",
    )


def notify_appointment_rescheduled(appointment):
    return _notify_appointment(
        appointment, kind=Notification.Kind.APPOINTMENT_RESCHEDULED,
        title="Appointment rescheduled", action="has moved to",
        dedupe_suffix=f"rescheduled:{appointment.updated_at.isoformat()}",
    )


def notify_appointment_cancelled(appointment):
    return _notify_appointment(
        appointment, kind=Notification.Kind.APPOINTMENT_CANCELLED,
        title="Appointment cancelled", action="scheduled for", dedupe_suffix="cancelled",
    )


def notify_appointment_reminder(appointment, hours):
    kind = (
        Notification.Kind.APPOINTMENT_REMINDER_1H
        if hours == 1
        else Notification.Kind.APPOINTMENT_REMINDER_24H
    )
    return _notify_appointment(
        appointment, kind=kind, title="Appointment reminder",
        action="is scheduled for", dedupe_suffix=f"reminder:{hours}h",
        preference_field="appointment_reminders",
    )


def notify_coaching_plan_published(plan):
    return create_notification(
        recipient=plan.case.client,
        kind=Notification.Kind.COACHING_PLAN_PUBLISHED,
        title="Your care plan is ready",
        body="TK published new guidance for you.",
        route=f"/plans/{plan.public_id}",
        dedupe_key=f"coaching-plan:{plan.public_id}:published",
        preference_field="coaching_updates",
        email=True,
    )


def notify_progress_submitted(check_in):
    expert = check_in.case.service.expert
    if not expert:
        return None
    return create_notification(
        recipient=expert,
        kind=Notification.Kind.PROGRESS_SUBMITTED,
        title="Progress check-in ready",
        body="A client submitted a progress update and private photos.",
        route=f"/staff/progress/{check_in.public_id}",
        dedupe_key=f"progress:{check_in.public_id}:submitted",
        preference_field="coaching_updates",
        email=True,
    )


def notify_progress_feedback_published(check_in):
    return create_notification(
        recipient=check_in.client,
        kind=Notification.Kind.PROGRESS_FEEDBACK_PUBLISHED,
        title="TK reviewed your progress",
        body="New feedback is ready in your progress check-in.",
        route=f"/progress/{check_in.public_id}",
        dedupe_key=f"progress:{check_in.public_id}:feedback",
        preference_field="coaching_updates",
        email=True,
    )
