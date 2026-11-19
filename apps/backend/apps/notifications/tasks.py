from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMessage
from django.db.models import Q
from django.utils import timezone

from apps.consultations.models import Appointment

from .models import EmailDelivery, Notification, PushDelivery, PushDevice
from .providers import ExpoPushProvider, PushProviderError
from .services import notify_appointment_reminder

PERMANENT_PUSH_ERRORS = {"DeviceNotRegistered", "InvalidCredentials"}


@shared_task(bind=True, max_retries=3)
def deliver_notification(self, notification_id):
    notification = Notification.objects.select_related("recipient", "conversation").get(pk=notification_id)
    retry_needed = False
    provider = ExpoPushProvider()
    push_deliveries = notification.deliveries.select_related("device").filter(
        status=PushDelivery.Status.PENDING,
    ) if settings.PUSH_NOTIFICATIONS_ENABLED else []
    for delivery in push_deliveries:
        delivery.attempt_count += 1
        delivery.last_attempt_at = timezone.now()
        try:
            delivery.provider_ticket_id = provider.send(
                delivery.device.expo_token, notification.title, notification.body,
                {"type": notification.kind, "route": notification.route},
            )
            delivery.status = PushDelivery.Status.ACCEPTED
            delivery.last_error_code = ""
        except PushProviderError as exc:
            code = str(exc)[:80]
            delivery.last_error_code = code
            if code in PERMANENT_PUSH_ERRORS or self.request.retries >= self.max_retries:
                delivery.status = PushDelivery.Status.FAILED
                if code == "DeviceNotRegistered":
                    delivery.device.active = False
                    delivery.device.save(update_fields=("active", "updated_at"))
            else:
                retry_needed = True
        delivery.save(update_fields=(
            "status", "provider_ticket_id", "attempt_count", "last_attempt_at",
            "last_error_code", "updated_at",
        ))

    email_delivery = EmailDelivery.objects.filter(
        notification=notification, status=EmailDelivery.Status.PENDING,
    ).first()
    if email_delivery and settings.EMAIL_NOTIFICATIONS_ENABLED:
        email_delivery.attempt_count += 1
        email_delivery.last_attempt_at = timezone.now()
        try:
            EmailMessage(
                subject=notification.title,
                body=f"{notification.body}\n\nOpen the HairDoc TK app to view details.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[notification.recipient.email],
                headers={"Idempotency-Key": f"notification-{notification.public_id}"},
            ).send(fail_silently=False)
            email_delivery.status = EmailDelivery.Status.SENT
            email_delivery.sent_at = timezone.now()
            email_delivery.last_error_code = ""
        except Exception:
            email_delivery.last_error_code = "EMAIL_PROVIDER_UNAVAILABLE"
            if self.request.retries >= self.max_retries:
                email_delivery.status = EmailDelivery.Status.FAILED
            else:
                retry_needed = True
        email_delivery.save(update_fields=(
            "status", "attempt_count", "last_attempt_at", "sent_at",
            "last_error_code", "updated_at",
        ))
    if retry_needed:
        raise self.retry(countdown=min(30 * (2 ** self.request.retries), 300))


@shared_task
def create_due_appointment_reminders():
    now = timezone.now()
    appointments = Appointment.objects.select_related("client", "expert").filter(
        status=Appointment.Status.CONFIRMED,
        starts_at__gt=now,
        starts_at__lte=now + timedelta(hours=24),
    )
    created = 0
    for appointment in appointments.iterator(chunk_size=200):
        hours = 1 if appointment.starts_at - now <= timedelta(hours=1) else 24
        results = notify_appointment_reminder(appointment, hours)
        created += sum(item is not None for item in results)
    return created


@shared_task
def reconcile_push_receipts():
    if not settings.PUSH_NOTIFICATIONS_ENABLED:
        return 0
    deliveries = list(PushDelivery.objects.select_related("device").filter(
        status=PushDelivery.Status.ACCEPTED,
        receipt_checked_at__isnull=True,
        provider_ticket_id__gt="",
        last_attempt_at__lte=timezone.now() - timedelta(minutes=15),
    )[:1000])
    if not deliveries:
        return 0
    receipts = ExpoPushProvider().receipts([item.provider_ticket_id for item in deliveries])
    checked_at = timezone.now()
    updated = []
    for delivery in deliveries:
        receipt = receipts.get(delivery.provider_ticket_id)
        if not isinstance(receipt, dict):
            continue
        delivery.receipt_checked_at = checked_at
        if receipt.get("status") == "error":
            code = str(receipt.get("details", {}).get("error") or "RECEIPT_ERROR")[:80]
            delivery.status = PushDelivery.Status.FAILED
            delivery.last_error_code = code
            if code == "DeviceNotRegistered":
                delivery.device.active = False
                delivery.device.save(update_fields=("active", "updated_at"))
        updated.append(delivery)
    PushDelivery.objects.bulk_update(
        updated, ("status", "last_error_code", "receipt_checked_at", "updated_at"),
    )
    return len(updated)


@shared_task
def deactivate_stale_push_devices():
    now = timezone.now()
    return PushDevice.objects.filter(active=True).filter(
        Q(session__isnull=True)
        | Q(session__revoked_at__isnull=False)
        | Q(session__expires_at__lte=now)
    ).update(active=False, updated_at=now)
