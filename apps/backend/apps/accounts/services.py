import hashlib
import secrets
import uuid
from datetime import timedelta
from urllib.parse import quote

import jwt
from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.mail import EmailMessage
from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import DeviceSession, EmailActionToken, RefreshTokenRecord, User


class InvalidRefreshToken(Exception):
    pass


class InvalidActionToken(Exception):
    pass


class AccountDeletionError(Exception):
    pass


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _opaque_token() -> str:
    return secrets.token_urlsafe(48)


def create_access_token(session: DeviceSession) -> str:
    now = timezone.now()
    payload = {
        "iss": settings.AUTH_JWT_ISSUER,
        "aud": settings.AUTH_JWT_AUDIENCE,
        "sub": str(session.user.public_id),
        "sid": str(session.public_id),
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.AUTH_ACCESS_TOKEN_MINUTES),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    return jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=["HS256"],
        audience=settings.AUTH_JWT_AUDIENCE,
        issuer=settings.AUTH_JWT_ISSUER,
        options={"require": ["iss", "aud", "sub", "sid", "type", "iat", "exp", "jti"]},
    )


def _new_refresh_record(session: DeviceSession) -> str:
    raw_token = _opaque_token()
    RefreshTokenRecord.objects.create(
        session=session,
        token_hash=_token_hash(raw_token),
        expires_at=session.expires_at,
    )
    return raw_token


@transaction.atomic
def create_device_session(user: User, device_name: str) -> tuple[str, str, DeviceSession]:
    expires_at = timezone.now() + timedelta(days=settings.AUTH_REFRESH_TOKEN_DAYS)
    session = DeviceSession.objects.create(
        user=user,
        device_name=(device_name.strip() or "Unknown device")[:120],
        expires_at=expires_at,
    )
    refresh_token = _new_refresh_record(session)
    return create_access_token(session), refresh_token, session


def rotate_refresh_token(raw_token: str) -> tuple[str, str, DeviceSession]:
    token_hash = _token_hash(raw_token)
    now = timezone.now()
    result = None
    invalid = False

    with transaction.atomic():
        try:
            record = (
                RefreshTokenRecord.objects.select_for_update()
                .select_related("session__user")
                .get(token_hash=token_hash)
            )
        except RefreshTokenRecord.DoesNotExist:
            record = None

        if record is None:
            invalid = True
        else:
            session = record.session
            if record.used_at is not None:
                if session.revoked_at is None:
                    session.revoked_at = now
                    session.revoke_reason = "REFRESH_REUSE"
                    session.save(update_fields=("revoked_at", "revoke_reason"))
                    session.push_devices.filter(active=True).update(active=False, updated_at=now)
                invalid = True
            elif record.expires_at <= now or session.expires_at <= now or session.revoked_at is not None:
                if session.revoked_at is None:
                    session.revoked_at = now
                    session.revoke_reason = "EXPIRED"
                    session.save(update_fields=("revoked_at", "revoke_reason"))
                session.push_devices.filter(active=True).update(active=False, updated_at=now)
                invalid = True
            elif not session.user.is_active:
                session.revoked_at = now
                session.revoke_reason = "USER_INACTIVE"
                session.save(update_fields=("revoked_at", "revoke_reason"))
                session.push_devices.filter(active=True).update(active=False, updated_at=now)
                invalid = True
            else:
                record.used_at = now
                record.save(update_fields=("used_at",))
                session.last_used_at = now
                session.save(update_fields=("last_used_at",))
                next_refresh = _new_refresh_record(session)
                result = (create_access_token(session), next_refresh, session)

    if invalid or result is None:
        raise InvalidRefreshToken
    return result


def revoke_session(session: DeviceSession, reason: str) -> None:
    if session.revoked_at is None:
        now = timezone.now()
        session.revoked_at = now
        session.revoke_reason = reason[:40]
        session.save(update_fields=("revoked_at", "revoke_reason"))
        session.push_devices.filter(active=True).update(active=False, updated_at=now)


def revoke_session_by_refresh(raw_token: str, reason: str = "LOGOUT") -> None:
    record = RefreshTokenRecord.objects.select_related("session").filter(token_hash=_token_hash(raw_token)).first()
    if record:
        revoke_session(record.session, reason)


def revoke_all_user_sessions(user: User, reason: str) -> int:
    now = timezone.now()
    count = user.device_sessions.filter(revoked_at__isnull=True).update(
        revoked_at=now,
        revoke_reason=reason[:40],
    )
    user.push_devices.filter(active=True).update(active=False, updated_at=now)
    return count


@transaction.atomic
def delete_client_account(user: User) -> None:
    """Remove client-controlled data and leave only a non-login audit tombstone."""
    user = User.objects.select_for_update().get(pk=user.pk)
    if user.is_staff or user.is_superuser:
        raise AccountDeletionError(
            "TK/staff accounts must transfer assigned care records before deletion."
        )

    from apps.consultations.models import (
        AppointmentStatusHistory,
        ConsultationCase,
        ConsultationPhotoAccess,
        ConsultationResponse,
    )
    from apps.messaging.models import Conversation, ConversationMember, Message, RealtimeTicket
    from apps.private_media.models import StoredFile
    from apps.private_media.storage import get_storage_provider

    stored_files = list(StoredFile.objects.filter(owner=user))
    storage = get_storage_provider()
    for stored_file in stored_files:
        storage.delete(stored_file.storage_key)

    case_ids = list(ConsultationCase.objects.filter(client=user).values_list("id", flat=True))
    conversation_ids = list(
        Conversation.objects.filter(consultation_id__in=case_ids).values_list("id", flat=True)
    )
    Message.objects.filter(conversation_id__in=conversation_ids).delete()
    Conversation.objects.filter(id__in=conversation_ids).delete()
    Message.objects.filter(sender=user).delete()
    ConversationMember.objects.filter(user=user).delete()
    RealtimeTicket.objects.filter(user=user).delete()

    ConsultationPhotoAccess.objects.filter(actor=user).delete()
    AppointmentStatusHistory.objects.filter(actor=user).update(actor=None)
    ConsultationResponse.objects.filter(case_id__in=case_ids).delete()
    StoredFile.objects.filter(owner=user).delete()

    ConsultationCase.objects.filter(client=user, appointments__isnull=True).delete()
    ConsultationCase.objects.filter(client=user).update(
        hair_profile_snapshot={}, timezone_snapshot="UTC"
    )
    user.client_appointments.update(cancel_reason="")

    user.consents.all().delete()
    user.email_action_tokens.all().delete()
    user.device_sessions.all().delete()
    if hasattr(user, "hair_profile"):
        user.hair_profile.delete()
    if hasattr(user, "notification_preferences"):
        user.notification_preferences.delete()

    tombstone_id = uuid.uuid4()
    tombstone_email = f"deleted-{tombstone_id}@deleted.invalid"
    user.public_id = tombstone_id
    user.email = tombstone_email
    user.normalized_email = tombstone_email
    user.first_name = ""
    user.last_name = ""
    user.phone = ""
    user.last_login = None
    user.is_active = False
    user.is_email_verified = False
    user.deleted_at = timezone.now()
    user.set_unusable_password()
    user.save(update_fields=(
        "public_id", "email", "normalized_email", "first_name", "last_name", "phone",
        "last_login", "is_active", "is_email_verified", "deleted_at", "password", "updated_at",
    ))


def _action_url(path: str, token: str) -> str:
    return f"{settings.AUTH_APP_URL.rstrip('/')}/{path}?token={quote(token)}"


def issue_email_action(user: User, purpose: str) -> str:
    now = timezone.now()
    EmailActionToken.objects.filter(user=user, purpose=purpose, used_at__isnull=True).update(used_at=now)
    raw_token = _opaque_token()
    action = EmailActionToken.objects.create(
        user=user,
        purpose=purpose,
        token_hash=_token_hash(raw_token),
        expires_at=now + timedelta(minutes=settings.AUTH_ACTION_TOKEN_MINUTES),
    )

    if purpose == EmailActionToken.Purpose.VERIFY_EMAIL:
        subject = "Verify your HairDoc TK email"
        path = "auth/verify-email"
        intro = "Verify your email to finish creating your HairDoc TK account."
    else:
        subject = "Reset your HairDoc TK password"
        path = "auth/reset-password"
        intro = "Use this secure link to reset your HairDoc TK password."

    EmailMessage(
        subject=subject,
        body=f"{intro}\n\n{_action_url(path, raw_token)}\n\nThis link expires soon and can be used once.",
        to=[user.email],
        headers={"Idempotency-Key": f"email-action-{action.pk}"},
    ).send(fail_silently=False)
    return raw_token


def register_client(email: str, password: str, first_name: str = "") -> tuple[User | None, str | None]:
    normalized_email = User.objects.normalize_email(email).lower()
    user = User.objects.filter(normalized_email=normalized_email).first()
    if user is None:
        candidate = User(email=normalized_email, first_name=first_name.strip())
        validate_password(password, candidate)
        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    email=normalized_email,
                    password=password,
                    first_name=first_name.strip(),
                )
        except IntegrityError:
            user = User.objects.filter(normalized_email=normalized_email).first()

    if user and not user.is_email_verified:
        return user, issue_email_action(user, EmailActionToken.Purpose.VERIFY_EMAIL)
    return None, None


def verify_email(raw_token: str) -> User:
    now = timezone.now()
    with transaction.atomic():
        record = (
            EmailActionToken.objects.select_for_update()
            .select_related("user")
            .filter(token_hash=_token_hash(raw_token), purpose=EmailActionToken.Purpose.VERIFY_EMAIL)
            .first()
        )
        if not record or record.used_at is not None or record.expires_at <= now:
            raise InvalidActionToken
        record.used_at = now
        record.save(update_fields=("used_at",))
        if not record.user.is_email_verified:
            record.user.is_email_verified = True
            record.user.save(update_fields=("is_email_verified", "updated_at"))
        return record.user


def reset_password(raw_token: str, new_password: str) -> User:
    now = timezone.now()
    with transaction.atomic():
        record = (
            EmailActionToken.objects.select_for_update()
            .select_related("user")
            .filter(token_hash=_token_hash(raw_token), purpose=EmailActionToken.Purpose.RESET_PASSWORD)
            .first()
        )
        if not record or record.used_at is not None or record.expires_at <= now:
            raise InvalidActionToken
        validate_password(new_password, record.user)
        record.user.set_password(new_password)
        record.user.save(update_fields=("password", "updated_at"))
        record.used_at = now
        record.save(update_fields=("used_at",))
        revoke_all_user_sessions(record.user, "PASSWORD_RESET")
        return record.user
