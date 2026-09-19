from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.consultations.models import Appointment
from apps.core.models import BaseModel


class VideoSession(BaseModel):
    class Status(models.TextChoices):
        SCHEDULED = "SCHEDULED", "Scheduled"
        PROVISIONING = "PROVISIONING", "Provisioning"
        READY = "READY", "Ready"
        ACTIVE = "ACTIVE", "Active"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"
        FAILED = "FAILED", "Failed"

    appointment = models.OneToOneField(Appointment, on_delete=models.CASCADE, related_name="video_session")
    provider = models.CharField(max_length=32)
    provider_room_id = models.CharField(max_length=128, unique=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SCHEDULED)
    available_from = models.DateTimeField()
    expires_at = models.DateTimeField()
    started_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="completed_video_sessions",
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=("status", "expires_at"), name="video_status_expiry")]

    def __str__(self):
        return f"{self.appointment.public_id}: {self.status}"


class VideoParticipantEvent(BaseModel):
    class Type(models.TextChoices):
        TOKEN_ISSUED = "TOKEN_ISSUED", "Join token issued"
        JOINED = "JOINED", "Joined"
        LEFT = "LEFT", "Left"
        RECONNECTED = "RECONNECTED", "Reconnected"
        PERMISSION_DENIED = "PERMISSION_DENIED", "Device permission denied"

    class Role(models.TextChoices):
        CLIENT = "CLIENT", "Client"
        EXPERT = "EXPERT", "Expert"

    session = models.ForeignKey(VideoSession, on_delete=models.CASCADE, related_name="participant_events")
    participant = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="video_participant_events",
    )
    role = models.CharField(max_length=12, choices=Role.choices)
    event_type = models.CharField(max_length=24, choices=Type.choices)
    client_event_id = models.CharField(max_length=64, blank=True, null=True)

    class Meta:
        ordering = ("created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("session", "participant", "client_event_id"),
                condition=Q(client_event_id__isnull=False),
                name="unique_video_client_event",
            ),
        ]
        indexes = [models.Index(fields=("session", "participant", "created_at"), name="video_participant_recent")]
