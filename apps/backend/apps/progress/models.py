from django.conf import settings
from django.db import models

from apps.core.models import BaseModel
from apps.private_media.models import StoredFile


class ProgressCheckIn(BaseModel):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        SUBMITTED = "SUBMITTED", "Submitted"
        REVIEWED = "REVIEWED", "Reviewed"

    case = models.ForeignKey("consultations.ConsultationCase", on_delete=models.CASCADE, related_name="progress_check_ins")
    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="progress_check_ins")
    sequence = models.PositiveIntegerField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    summary = models.TextField(max_length=2000, blank=True)
    wins = models.TextField(max_length=2000, blank=True)
    challenges = models.TextField(max_length=2000, blank=True)
    routine_adherence = models.PositiveSmallIntegerField(blank=True, null=True)
    questions_for_tk = models.TextField(max_length=2000, blank=True)
    submitted_at = models.DateTimeField(blank=True, null=True)
    expert_feedback = models.TextField(max_length=4000, blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="reviewed_progress_check_ins", blank=True, null=True)
    feedback_published_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ("-sequence",)
        constraints = [
            models.UniqueConstraint(fields=("case", "sequence"), name="unique_case_progress_sequence"),
            models.UniqueConstraint(fields=("case",), condition=models.Q(status="DRAFT"), name="unique_case_progress_draft"),
            models.CheckConstraint(condition=models.Q(routine_adherence__isnull=True) | models.Q(routine_adherence__gte=1, routine_adherence__lte=5), name="progress_adherence_1_to_5"),
        ]
        indexes = [
            models.Index(fields=("client", "status", "-created_at"), name="progress_client_status_created"),
            models.Index(fields=("case", "status", "-sequence"), name="progress_case_status_sequence"),
        ]


class ProgressPhoto(BaseModel):
    class Category(models.TextChoices):
        FRONT = "FRONT", "Front hairline"
        TOP = "TOP", "Top / parting"
        LEFT = "LEFT", "Left side"
        RIGHT = "RIGHT", "Right side"
        BACK = "BACK", "Back"
        CLOSE_UP = "CLOSE_UP", "Concern close-up"
        OTHER = "OTHER", "Other"

    check_in = models.ForeignKey(ProgressCheckIn, on_delete=models.CASCADE, related_name="photos")
    stored_file = models.OneToOneField(StoredFile, on_delete=models.CASCADE, related_name="progress_photo")
    category = models.CharField(max_length=16, choices=Category.choices, default=Category.OTHER)
    consent_document = models.ForeignKey("accounts.LegalDocument", on_delete=models.PROTECT, related_name="progress_photos", blank=True, null=True)
    consent_accepted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ("created_at",)
        indexes = [models.Index(fields=("check_in", "created_at"), name="progress_photo_checkin_created")]


class ProgressPhotoAccess(BaseModel):
    class Purpose(models.TextChoices):
        CLIENT_VIEW = "CLIENT_VIEW", "Client view"
        STAFF_REVIEW = "STAFF_REVIEW", "Staff review"

    photo = models.ForeignKey(ProgressPhoto, on_delete=models.CASCADE, related_name="access_events")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="progress_photo_access_events")
    purpose = models.CharField(max_length=20, choices=Purpose.choices)
    request_id = models.CharField(max_length=64, blank=True)

    class Meta:
        ordering = ("-created_at",)
