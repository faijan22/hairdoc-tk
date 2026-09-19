from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.db.models.signals import pre_delete
from django.dispatch import receiver

from apps.core.models import BaseModel
from apps.private_media.models import StoredFile


class ConsultationService(BaseModel):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PUBLISHED = "PUBLISHED", "Published"

    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True)
    short_description = models.CharField(max_length=320)
    description = models.TextField()
    duration_minutes = models.PositiveSmallIntegerField()
    price_amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="GBP")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    display_order = models.PositiveSmallIntegerField(default=0)
    published_at = models.DateTimeField(blank=True, null=True)
    expert = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="consultation_services",
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ("display_order", "name")
        indexes = [models.Index(fields=("status", "display_order", "published_at"), name="consult_service_public")]

    def clean(self):
        self.currency = self.currency.upper()
        if self.price_amount < 0:
            raise ValidationError({"price_amount": "Price cannot be negative."})
        if self.duration_minutes < 1:
            raise ValidationError({"duration_minutes": "Duration must be at least one minute."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class Questionnaire(BaseModel):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PUBLISHED = "PUBLISHED", "Published"

    service = models.ForeignKey(ConsultationService, on_delete=models.CASCADE, related_name="questionnaires")
    version = models.PositiveIntegerField()
    title = models.CharField(max_length=180)
    introduction = models.CharField(max_length=500, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    published_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ("service", "-version")
        constraints = [models.UniqueConstraint(fields=("service", "version"), name="unique_service_questionnaire_version")]
        indexes = [models.Index(fields=("service", "status", "-version"), name="questionnaire_current")]

    @property
    def is_used(self) -> bool:
        return bool(self.pk and self.consultation_responses.exists())

    def save(self, *args, **kwargs):
        if self.pk and self.consultation_responses.exists():
            previous = Questionnaire.objects.get(pk=self.pk)
            locked = ("service_id", "version", "title", "introduction", "status", "published_at")
            if any(getattr(previous, field) != getattr(self, field) for field in locked):
                raise ValidationError("A questionnaire used by an intake is immutable; publish a new version instead.")
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.service.name} v{self.version}"


class QuestionnaireQuestion(BaseModel):
    class Type(models.TextChoices):
        SHORT_TEXT = "SHORT_TEXT", "Short text"
        LONG_TEXT = "LONG_TEXT", "Long text"
        SINGLE_CHOICE = "SINGLE_CHOICE", "Single choice"
        MULTI_CHOICE = "MULTI_CHOICE", "Multiple choice"
        BOOLEAN = "BOOLEAN", "Yes / No"
        DATE = "DATE", "Date"

    questionnaire = models.ForeignKey(Questionnaire, on_delete=models.CASCADE, related_name="questions")
    key = models.SlugField(max_length=80)
    section = models.CharField(max_length=80)
    prompt = models.CharField(max_length=300)
    help_text = models.CharField(max_length=500, blank=True)
    type = models.CharField(max_length=24, choices=Type.choices)
    required = models.BooleanField(default=False)
    display_order = models.PositiveSmallIntegerField(default=0)
    placeholder = models.CharField(max_length=160, blank=True)
    max_length = models.PositiveSmallIntegerField(blank=True, null=True)
    show_if_question_key = models.SlugField(max_length=80, blank=True)
    show_if_value = models.CharField(max_length=120, blank=True)

    class Meta:
        ordering = ("display_order", "id")
        constraints = [models.UniqueConstraint(fields=("questionnaire", "key"), name="unique_questionnaire_question_key")]

    def clean(self):
        if self.show_if_question_key and self.show_if_question_key == self.key:
            raise ValidationError({"show_if_question_key": "A question cannot depend on itself."})
        if not self.questionnaire_id:
            return
        previous = QuestionnaireQuestion.objects.select_related("questionnaire").filter(pk=self.pk).first()
        locked = (
            "questionnaire_id", "key", "section", "prompt", "help_text", "type", "required", "display_order",
            "placeholder", "max_length", "show_if_question_key", "show_if_value",
        )
        changed = not previous or any(getattr(previous, field) != getattr(self, field) for field in locked)
        if changed and (self.questionnaire.is_used or (previous and previous.questionnaire.is_used)):
            raise ValidationError("Questions in a used questionnaire are immutable; publish a new version instead.")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.questionnaire}: {self.prompt}"


class QuestionOption(BaseModel):
    question = models.ForeignKey(QuestionnaireQuestion, on_delete=models.CASCADE, related_name="options")
    value = models.SlugField(max_length=80)
    label = models.CharField(max_length=160)
    display_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ("display_order", "id")
        constraints = [models.UniqueConstraint(fields=("question", "value"), name="unique_question_option_value")]

    def clean(self):
        if not self.question_id:
            return
        previous = QuestionOption.objects.select_related("question__questionnaire").filter(pk=self.pk).first()
        changed = not previous or any(
            getattr(previous, field) != getattr(self, field)
            for field in ("question_id", "value", "label", "display_order")
        )
        previous_used = bool(previous and previous.question.questionnaire.is_used)
        if changed and (self.question.questionnaire.is_used or previous_used):
            raise ValidationError("Options in a used questionnaire are immutable; publish a new version instead.")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.label


class ConsultationCase(BaseModel):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        INTAKE_COMPLETE = "INTAKE_COMPLETE", "Intake complete"
        PHOTOS_COMPLETE = "PHOTOS_COMPLETE", "Photos complete"
        CANCELLED = "CANCELLED", "Cancelled"

    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="consultation_cases")
    service = models.ForeignKey(ConsultationService, on_delete=models.PROTECT, related_name="consultation_cases")
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.DRAFT)
    timezone_snapshot = models.CharField(max_length=64)
    hair_profile_snapshot = models.JSONField(default=dict, blank=True)
    service_name = models.CharField(max_length=160)
    duration_minutes = models.PositiveSmallIntegerField()
    price_amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3)
    intake_completed_at = models.DateTimeField(blank=True, null=True)
    photos_completed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ("-updated_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("client", "service"),
                condition=models.Q(status="DRAFT"),
                name="unique_client_service_draft",
            )
        ]
        indexes = [models.Index(fields=("client", "status", "-created_at"), name="case_client_status_created")]

    def __str__(self) -> str:
        return f"{self.client.email} - {self.service_name}"


class ConsultationResponse(BaseModel):
    case = models.OneToOneField(ConsultationCase, on_delete=models.CASCADE, related_name="response")
    questionnaire = models.ForeignKey(Questionnaire, on_delete=models.PROTECT, related_name="consultation_responses")

    def __str__(self) -> str:
        return f"Response: {self.case}"


class ConsultationAnswer(BaseModel):
    response = models.ForeignKey(ConsultationResponse, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(QuestionnaireQuestion, on_delete=models.PROTECT, related_name="consultation_answers")
    value = models.JSONField()

    class Meta:
        ordering = ("question__display_order", "id")
        constraints = [models.UniqueConstraint(fields=("response", "question"), name="unique_response_question_answer")]

    def __str__(self) -> str:
        return f"{self.response.case.public_id}: {self.question.key}"


class ConsultationPhoto(BaseModel):
    class Category(models.TextChoices):
        FRONT = "FRONT", "Front hairline"
        TOP = "TOP", "Top / parting"
        LEFT = "LEFT", "Left side"
        RIGHT = "RIGHT", "Right side"
        BACK = "BACK", "Back"
        CLOSE_UP = "CLOSE_UP", "Concern close-up"
        OTHER = "OTHER", "Other"

    case = models.ForeignKey(ConsultationCase, on_delete=models.CASCADE, related_name="photos")
    stored_file = models.OneToOneField(StoredFile, on_delete=models.CASCADE, related_name="consultation_photo")
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="consultation_photos")
    category = models.CharField(max_length=16, choices=Category.choices, default=Category.OTHER)
    consent_document = models.ForeignKey(
        "accounts.LegalDocument", on_delete=models.PROTECT, related_name="consultation_photos", blank=True, null=True,
    )
    consent_accepted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ("created_at",)
        indexes = [models.Index(fields=("case", "created_at"), name="consult_photo_case_created")]

    def __str__(self) -> str:
        return f"{self.case.public_id}: {self.get_category_display()}"


class ConsultationPhotoAccess(BaseModel):
    class Purpose(models.TextChoices):
        CLIENT_VIEW = "CLIENT_VIEW", "Client view"
        STAFF_REVIEW = "STAFF_REVIEW", "Staff review"

    photo = models.ForeignKey(ConsultationPhoto, on_delete=models.CASCADE, related_name="access_events")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="photo_access_events")
    purpose = models.CharField(max_length=20, choices=Purpose.choices)
    request_id = models.CharField(max_length=64, blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=("photo", "-created_at"), name="photo_access_recent")]


class AvailabilityRule(BaseModel):
    expert = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="availability_rules")
    weekday = models.PositiveSmallIntegerField()
    local_start = models.TimeField()
    local_end = models.TimeField()
    timezone = models.CharField(max_length=64)
    effective_from = models.DateField(blank=True, null=True)
    effective_until = models.DateField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("weekday", "local_start")
        constraints = [
            models.CheckConstraint(condition=Q(weekday__gte=0, weekday__lte=6), name="availability_valid_weekday"),
            models.CheckConstraint(condition=Q(local_end__gt=F("local_start")), name="availability_positive_interval"),
            models.UniqueConstraint(
                fields=("expert", "weekday", "local_start", "local_end"), name="unique_expert_weekly_interval",
            ),
        ]
        indexes = [models.Index(fields=("expert", "is_active", "weekday"), name="availability_expert_day")]

    def clean(self):
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

        if self.local_start >= self.local_end:
            raise ValidationError({"local_end": "End time must be after start time."})
        if self.effective_from and self.effective_until and self.effective_until < self.effective_from:
            raise ValidationError({"effective_until": "End date cannot be before start date."})
        try:
            ZoneInfo(self.timezone)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValidationError({"timezone": "Use a valid IANA timezone."}) from None

    def __str__(self) -> str:
        return f"{self.expert.email}: {self.get_weekday_display() if hasattr(self, 'get_weekday_display') else self.weekday}"


class AvailabilityException(BaseModel):
    class Kind(models.TextChoices):
        BLOCKED = "BLOCKED", "Blocked time"
        EXTRA = "EXTRA", "Extra availability"

    expert = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="availability_exceptions")
    date = models.DateField()
    kind = models.CharField(max_length=12, choices=Kind.choices)
    local_start = models.TimeField(blank=True, null=True)
    local_end = models.TimeField(blank=True, null=True)
    timezone = models.CharField(max_length=64)
    note = models.CharField(max_length=160, blank=True)

    class Meta:
        ordering = ("date", "local_start", "created_at")
        indexes = [models.Index(fields=("expert", "date", "kind"), name="availability_exception_day")]

    def clean(self):
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

        if (self.local_start is None) != (self.local_end is None):
            raise ValidationError("Provide both start and end, or neither for a full-day block.")
        if self.local_start and self.local_start >= self.local_end:
            raise ValidationError({"local_end": "End time must be after start time."})
        if self.kind == self.Kind.EXTRA and not self.local_start:
            raise ValidationError({"local_start": "Extra availability needs start and end times."})
        try:
            ZoneInfo(self.timezone)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValidationError({"timezone": "Use a valid IANA timezone."}) from None

    def __str__(self) -> str:
        return f"{self.expert.email}: {self.date} {self.kind}"


class Appointment(BaseModel):
    class Status(models.TextChoices):
        PAYMENT_PENDING = "PAYMENT_PENDING", "Payment pending"
        CONFIRMED = "CONFIRMED", "Confirmed"
        CANCELLED = "CANCELLED", "Cancelled"
        EXPIRED = "EXPIRED", "Expired"
        COMPLETED = "COMPLETED", "Completed"
        NO_SHOW = "NO_SHOW", "No show"

    case = models.ForeignKey(ConsultationCase, on_delete=models.PROTECT, related_name="appointments")
    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="client_appointments")
    expert = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="expert_appointments")
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.PAYMENT_PENDING)
    client_timezone = models.CharField(max_length=64)
    expert_timezone = models.CharField(max_length=64)
    reservation_expires_at = models.DateTimeField(blank=True, null=True)
    cancelled_at = models.DateTimeField(blank=True, null=True)
    cancel_reason = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ("starts_at",)
        constraints = [
            models.CheckConstraint(condition=Q(ends_at__gt=F("starts_at")), name="appointment_positive_interval"),
            models.UniqueConstraint(
                fields=("case",),
                condition=Q(status__in=("PAYMENT_PENDING", "CONFIRMED")),
                name="one_active_appointment_per_case",
            ),
        ]
        indexes = [
            models.Index(fields=("expert", "starts_at", "status"), name="appointment_expert_start"),
            models.Index(fields=("client", "starts_at", "status"), name="appointment_client_start"),
        ]

    def __str__(self) -> str:
        return f"{self.case.service_name}: {self.starts_at.isoformat()}"


class AppointmentStatusHistory(BaseModel):
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name="status_history")
    from_status = models.CharField(max_length=24, blank=True)
    to_status = models.CharField(max_length=24, choices=Appointment.Status.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="appointment_status_changes", blank=True, null=True,
    )
    note = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ("created_at",)

    def __str__(self) -> str:
        return f"{self.appointment.public_id}: {self.from_status or 'NEW'} → {self.to_status}"


def _questionnaire_for_locked_object(instance):
    if isinstance(instance, QuestionnaireQuestion):
        return instance.questionnaire
    if isinstance(instance, QuestionOption):
        return instance.question.questionnaire
    return None


@receiver(pre_delete, sender=QuestionnaireQuestion)
@receiver(pre_delete, sender=QuestionOption)
def prevent_used_questionnaire_content_delete(sender, instance, **kwargs):
    questionnaire = _questionnaire_for_locked_object(instance)
    if questionnaire and questionnaire.is_used:
        raise ValidationError("Content in a used questionnaire cannot be deleted; publish a new version instead.")
