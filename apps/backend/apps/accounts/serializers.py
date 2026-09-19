from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from django.urls import reverse

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .models import ClientHairProfile, DeviceSession, LegalDocument, NotificationPreference, User, UserConsent


def validate_new_password(password: str, user: User | None = None) -> str:
    try:
        validate_password(password, user)
    except DjangoValidationError as exc:
        raise serializers.ValidationError(list(exc.messages)) from exc
    return password


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=128)
    first_name = serializers.CharField(required=False, allow_blank=True, max_length=150)

    def validate_email(self, value: str) -> str:
        return User.objects.normalize_email(value).lower()

    def validate_password(self, value: str) -> str:
        return validate_new_password(value)


class EmailSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value: str) -> str:
        return User.objects.normalize_email(value).lower()


class TokenSerializer(serializers.Serializer):
    token = serializers.CharField(trim_whitespace=False, max_length=256)


class LoginSerializer(EmailSerializer):
    password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=128)
    device_name = serializers.CharField(required=False, allow_blank=True, max_length=120)


class RefreshSerializer(serializers.Serializer):
    refresh_token = serializers.CharField(write_only=True, trim_whitespace=False, max_length=256)


class ResetPasswordSerializer(TokenSerializer):
    new_password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=128)


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=128)
    new_password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=128)

    def validate_new_password(self, value: str) -> str:
        return validate_new_password(value, self.context["request"].user)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("public_id", "email", "first_name", "last_name", "phone", "is_email_verified", "is_staff")
        read_only_fields = ("public_id", "email", "is_email_verified", "is_staff")


class ClientHairProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientHairProfile
        fields = ("hair_texture", "scalp_type", "concerns", "goals", "current_routine", "updated_at")
        read_only_fields = ("updated_at",)


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = (
            "timezone",
            "email_enabled",
            "push_enabled",
            "appointment_reminders",
            "message_notifications",
            "coaching_updates",
            "updated_at",
        )
        read_only_fields = ("updated_at",)

    def validate_timezone(self, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise serializers.ValidationError("Use a valid IANA timezone, for example Asia/Kolkata.") from None
        return value


class LegalDocumentSerializer(serializers.ModelSerializer):
    type_label = serializers.CharField(source="get_type_display", read_only=True)
    attachment_name = serializers.CharField(read_only=True)
    attachment_path = serializers.SerializerMethodField()

    class Meta:
        model = LegalDocument
        fields = (
            "public_id", "type", "type_label", "version", "title", "body",
            "attachment_name", "attachment_path", "published_at",
        )

    def get_attachment_path(self, obj):
        if not obj.attachment:
            return None
        return reverse("accounts:legal-file", kwargs={"public_id": obj.public_id})


class UserConsentSerializer(serializers.ModelSerializer):
    document = LegalDocumentSerializer(source="legal_document", read_only=True)
    accepted = serializers.BooleanField(source="is_accepted", read_only=True)

    class Meta:
        model = UserConsent
        fields = ("document", "accepted", "accepted_at", "withdrawn_at")


class ConsentUpdateSerializer(serializers.Serializer):
    document_public_id = serializers.UUIDField()
    accepted = serializers.BooleanField()


class AccountDeletionSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=128)
    confirmation = serializers.CharField(write_only=True, max_length=16)

    def validate_confirmation(self, value):
        if value != "DELETE":
            raise serializers.ValidationError("Type DELETE exactly to confirm.")
        return value


class DeviceSessionSerializer(serializers.ModelSerializer):
    is_current = serializers.SerializerMethodField()

    class Meta:
        model = DeviceSession
        fields = ("public_id", "device_name", "created_at", "last_used_at", "expires_at", "is_current")

    def get_is_current(self, obj: DeviceSession) -> bool:
        current = self.context.get("current_session")
        return bool(current and current.pk == obj.pk)
