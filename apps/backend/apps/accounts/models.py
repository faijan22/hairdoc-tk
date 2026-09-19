import uuid
from pathlib import Path

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models, transaction
from django.utils import timezone

from .managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    email = models.EmailField(unique=True)
    normalized_email = models.EmailField(unique=True, editable=False)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=32, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_email_verified = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        ordering = ("-created_at",)

    def save(self, *args, **kwargs):
        normalized = self.__class__.objects.normalize_email(self.email).lower()
        self.email = normalized
        self.normalized_email = normalized
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.email


class ClientHairProfile(models.Model):
    class Texture(models.TextChoices):
        STRAIGHT = "STRAIGHT", "Straight"
        WAVY = "WAVY", "Wavy"
        CURLY = "CURLY", "Curly"
        COILY = "COILY", "Coily"
        UNSURE = "UNSURE", "Not sure"
        PREFER_NOT_TO_SAY = "PREFER_NOT_TO_SAY", "Prefer not to say"

    class ScalpType(models.TextChoices):
        BALANCED = "BALANCED", "Balanced"
        DRY = "DRY", "Dry"
        OILY = "OILY", "Oily"
        SENSITIVE = "SENSITIVE", "Sensitive"
        UNSURE = "UNSURE", "Not sure"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="hair_profile")
    hair_texture = models.CharField(max_length=24, choices=Texture.choices, blank=True)
    scalp_type = models.CharField(max_length=16, choices=ScalpType.choices, blank=True)
    concerns = models.CharField(max_length=500, blank=True)
    goals = models.CharField(max_length=500, blank=True)
    current_routine = models.CharField(max_length=1000, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Hair profile: {self.user.email}"


class NotificationPreference(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="notification_preferences")
    timezone = models.CharField(max_length=64, default="UTC")
    email_enabled = models.BooleanField(default=True)
    push_enabled = models.BooleanField(default=True)
    appointment_reminders = models.BooleanField(default=True)
    message_notifications = models.BooleanField(default=True)
    coaching_updates = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Preferences: {self.user.email}"


class LegalDocument(models.Model):
    class Type(models.TextChoices):
        TERMS = "TERMS", "Terms of Use"
        PRIVACY = "PRIVACY", "Privacy Policy"
        CONSULTATION_DISCLAIMER = "CONSULTATION_DISCLAIMER", "Consultation Disclaimer"
        PHOTO_DATA_CONSENT = "PHOTO_DATA_CONSENT", "Photo & Data Consent"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PUBLISHED = "PUBLISHED", "Published"

    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    type = models.CharField(max_length=32, choices=Type.choices)
    version = models.PositiveIntegerField()
    title = models.CharField(max_length=180)
    body = models.TextField(blank=True)
    attachment = models.FileField(
        upload_to="legal/%Y/%m/",
        blank=True,
        max_length=500,
        validators=[FileExtensionValidator(("pdf", "txt", "md", "docx"))],
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    published_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("type", "-version")
        constraints = [models.UniqueConstraint(fields=("type", "version"), name="unique_legal_type_version")]
        indexes = [models.Index(fields=("type", "status", "-published_at"), name="legal_current_lookup")]

    def clean(self):
        if not self.body.strip() and not self.attachment:
            raise ValidationError("Add legal copy or upload a PDF, TXT, MD, or DOCX file.")
        if self.attachment and self.attachment.size > 10 * 1024 * 1024:
            raise ValidationError({"attachment": "The legal file must be 10 MB or smaller."})

    def save(self, *args, **kwargs):
        previous_name = ""
        previous_storage = None
        if self.pk:
            previous = LegalDocument.objects.filter(pk=self.pk).only("attachment").first()
            if previous and previous.attachment:
                previous_name = previous.attachment.name
                previous_storage = previous.attachment.storage
        if self.status == self.Status.PUBLISHED and not self.published_at:
            self.published_at = timezone.now()
        self.full_clean()
        result = super().save(*args, **kwargs)
        if previous_name and previous_name != self.attachment.name:
            transaction.on_commit(lambda: previous_storage.delete(previous_name))
        return result

    def delete(self, *args, **kwargs):
        name = self.attachment.name if self.attachment else ""
        storage = self.attachment.storage if self.attachment else None
        result = super().delete(*args, **kwargs)
        if name:
            transaction.on_commit(lambda: storage.delete(name))
        return result

    @property
    def attachment_name(self):
        return Path(self.attachment.name).name if self.attachment else ""

    def __str__(self) -> str:
        return f"{self.get_type_display()} v{self.version}"


class UserConsent(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="consents")
    legal_document = models.ForeignKey(LegalDocument, on_delete=models.PROTECT, related_name="user_consents")
    accepted_at = models.DateTimeField()
    withdrawn_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ("-accepted_at",)
        constraints = [models.UniqueConstraint(fields=("user", "legal_document"), name="unique_user_legal_consent")]

    @property
    def is_accepted(self) -> bool:
        return self.withdrawn_at is None


class DeviceSession(models.Model):
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    family_id = models.UUIDField(default=uuid.uuid4, editable=False, db_index=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="device_sessions")
    device_name = models.CharField(max_length=120, default="Unknown device")
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoke_reason = models.CharField(max_length=40, blank=True)

    class Meta:
        ordering = ("-last_used_at",)
        indexes = [models.Index(fields=("user", "revoked_at", "-last_used_at"))]

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None and self.expires_at > timezone.now()


class RefreshTokenRecord(models.Model):
    session = models.ForeignKey(DeviceSession, on_delete=models.CASCADE, related_name="refresh_tokens")
    token_hash = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)


class EmailActionToken(models.Model):
    class Purpose(models.TextChoices):
        VERIFY_EMAIL = "VERIFY_EMAIL", "Verify email"
        RESET_PASSWORD = "RESET_PASSWORD", "Reset password"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="email_action_tokens")
    purpose = models.CharField(max_length=24, choices=Purpose.choices)
    token_hash = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=("user", "purpose", "used_at"))]
