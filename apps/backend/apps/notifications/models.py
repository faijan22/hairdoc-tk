from django.conf import settings
from django.db import models

from apps.core.models import BaseModel


class PushDevice(BaseModel):
    class Platform(models.TextChoices):
        IOS = "IOS", "iOS"
        ANDROID = "ANDROID", "Android"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="push_devices")
    session = models.ForeignKey(
        "accounts.DeviceSession",
        on_delete=models.CASCADE,
        related_name="push_devices",
        blank=True,
        null=True,
    )
    expo_token = models.CharField(max_length=255, unique=True)
    platform = models.CharField(max_length=12, choices=Platform.choices)
    device_id = models.CharField(max_length=120)
    active = models.BooleanField(default=True)
    last_seen_at = models.DateTimeField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=("user", "device_id"), name="unique_user_push_device")]
        indexes = [models.Index(fields=("user", "active"), name="push_device_user_active")]


class Notification(BaseModel):
    class Kind(models.TextChoices):
        NEW_MESSAGE = "NEW_MESSAGE", "New message"
        CONSULTATION_SUBMITTED = "CONSULTATION_SUBMITTED", "Consultation submitted"
        APPOINTMENT_CONFIRMED = "APPOINTMENT_CONFIRMED", "Appointment confirmed"
        APPOINTMENT_RESCHEDULED = "APPOINTMENT_RESCHEDULED", "Appointment rescheduled"
        APPOINTMENT_CANCELLED = "APPOINTMENT_CANCELLED", "Appointment cancelled"
        APPOINTMENT_REMINDER_24H = "APPOINTMENT_REMINDER_24H", "Appointment reminder (24 hours)"
        APPOINTMENT_REMINDER_1H = "APPOINTMENT_REMINDER_1H", "Appointment reminder (1 hour)"
        COACHING_PLAN_PUBLISHED = "COACHING_PLAN_PUBLISHED", "Care plan published"
        PROGRESS_SUBMITTED = "PROGRESS_SUBMITTED", "Progress submitted"
        PROGRESS_FEEDBACK_PUBLISHED = "PROGRESS_FEEDBACK_PUBLISHED", "Progress feedback published"

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    kind = models.CharField(max_length=32, choices=Kind.choices)
    title = models.CharField(max_length=120)
    body = models.CharField(max_length=240)
    route = models.CharField(max_length=240, blank=True)
    dedupe_key = models.CharField(max_length=200, unique=True, blank=True, null=True)
    conversation = models.ForeignKey(
        "messaging.Conversation", on_delete=models.CASCADE, related_name="notifications", blank=True, null=True,
    )
    message = models.OneToOneField(
        "messaging.Message", on_delete=models.CASCADE, related_name="notification", blank=True, null=True,
    )
    read_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=("recipient", "read_at", "-created_at"), name="notification_user_unread")]


class EmailDelivery(BaseModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SENT = "SENT", "Sent"
        FAILED = "FAILED", "Failed"

    notification = models.OneToOneField(Notification, on_delete=models.CASCADE, related_name="email_delivery")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    attempt_count = models.PositiveSmallIntegerField(default=0)
    last_error_code = models.CharField(max_length=80, blank=True)
    last_attempt_at = models.DateTimeField(blank=True, null=True)
    sent_at = models.DateTimeField(blank=True, null=True)


class PushDelivery(BaseModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        ACCEPTED = "ACCEPTED", "Accepted by push service"
        FAILED = "FAILED", "Failed"

    notification = models.ForeignKey(Notification, on_delete=models.CASCADE, related_name="deliveries")
    device = models.ForeignKey(PushDevice, on_delete=models.CASCADE, related_name="deliveries")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    provider_ticket_id = models.CharField(max_length=120, blank=True)
    attempt_count = models.PositiveSmallIntegerField(default=0)
    last_error_code = models.CharField(max_length=80, blank=True)
    last_attempt_at = models.DateTimeField(blank=True, null=True)
    receipt_checked_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("notification", "device"), name="unique_notification_device")]
