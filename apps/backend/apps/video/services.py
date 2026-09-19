import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.module_loading import import_string

from apps.consultations.models import Appointment, AppointmentStatusHistory

from .models import VideoParticipantEvent, VideoSession
from .providers.base import VideoProviderError

logger = logging.getLogger(__name__)


class VideoAccessError(Exception):
    def __init__(self, message, code="video_unavailable"):
        self.message = message
        self.code = code
        super().__init__(message)


def get_video_provider():
    return import_string(settings.VIDEO_PROVIDER_BACKEND)()


def participant_role(appointment, user):
    if appointment.client_id == user.id:
        return VideoParticipantEvent.Role.CLIENT
    if appointment.expert_id == user.id:
        return VideoParticipantEvent.Role.EXPERT
    raise VideoAccessError("This video consultation is not available.", "not_found")


def video_window(appointment):
    return (
        appointment.starts_at - timedelta(minutes=settings.VIDEO_JOIN_EARLY_MINUTES),
        appointment.ends_at + timedelta(minutes=settings.VIDEO_JOIN_LATE_MINUTES),
    )


def video_state(appointment, user):
    role = participant_role(appointment, user)
    available_from, expires_at = video_window(appointment)
    now = timezone.now()
    provider = get_video_provider()
    session = getattr(appointment, "video_session", None)
    can_join, code, message = False, "unavailable", "This appointment is not open for video."
    if appointment.status == Appointment.Status.COMPLETED or (session and session.status == VideoSession.Status.COMPLETED):
        code, message = "completed", "This consultation has been completed."
    elif appointment.status != Appointment.Status.CONFIRMED:
        code, message = "appointment_not_confirmed", "Video opens only for a confirmed appointment."
    elif not provider.is_configured:
        code, message = "provider_not_configured", "Secure video is being configured."
    elif now < available_from:
        code, message = "too_early", f"The waiting room opens {settings.VIDEO_JOIN_EARLY_MINUTES} minutes before the appointment."
    elif now > expires_at:
        code, message = "window_closed", "The join window for this appointment has closed."
    elif session and session.status == VideoSession.Status.CANCELLED:
        code, message = "cancelled", "This video session was cancelled."
    else:
        can_join, code, message = True, "ready", "Your secure waiting room is ready."
    return {
        "appointment_public_id": appointment.public_id,
        "service_name": appointment.case.service_name,
        "participant_role": role,
        "appointment_status": appointment.status,
        "session_status": session.status if session else "NOT_CREATED",
        "starts_at": appointment.starts_at,
        "ends_at": appointment.ends_at,
        "available_from": available_from,
        "expires_at": expires_at,
        "provider_configured": provider.is_configured,
        "can_join": can_join,
        "reason_code": code,
        "message": message,
    }


def _ensure_session(appointment, provider):
    available_from, expires_at = video_window(appointment)
    with transaction.atomic():
        locked = Appointment.objects.select_for_update().get(pk=appointment.pk)
        session, _ = VideoSession.objects.get_or_create(
            appointment=locked,
            defaults={
                "provider": provider.code,
                "provider_room_id": f"hdt_{secrets.token_hex(16)}",
                "available_from": available_from,
                "expires_at": expires_at,
            },
        )
    if session.status in (VideoSession.Status.READY, VideoSession.Status.ACTIVE):
        return session
    claimed = VideoSession.objects.filter(
        pk=session.pk,
        status__in=(VideoSession.Status.SCHEDULED, VideoSession.Status.FAILED),
    ).update(status=VideoSession.Status.PROVISIONING)
    if not claimed:
        raise VideoAccessError("The secure room is being prepared. Try again in a moment.", "room_preparing")
    try:
        provider.create_room(
            room_id=session.provider_room_id,
            available_from=session.available_from,
            expires_at=session.expires_at,
        )
    except VideoProviderError:
        VideoSession.objects.filter(pk=session.pk).update(status=VideoSession.Status.FAILED)
        raise
    VideoSession.objects.filter(pk=session.pk).update(status=VideoSession.Status.READY)
    session.refresh_from_db()
    return session


def join_video(appointment, user):
    state = video_state(appointment, user)
    if not state["can_join"]:
        raise VideoAccessError(state["message"], state["reason_code"])
    provider = get_video_provider()
    session = _ensure_session(appointment, provider)
    name = f"{user.first_name} {user.last_name}".strip() or ("TK" if user.is_staff else "Client")
    grant = provider.issue_join_grant(
        room_id=session.provider_room_id,
        user_id=str(user.public_id),
        user_name=name,
        is_owner=appointment.expert_id == user.id,
        available_from=session.available_from,
        expires_at=session.expires_at,
    )
    VideoParticipantEvent.objects.create(
        session=session,
        participant=user,
        role=participant_role(appointment, user),
        event_type=VideoParticipantEvent.Type.TOKEN_ISSUED,
    )
    return session, grant


@transaction.atomic
def record_event(appointment, user, event_type, client_event_id):
    role = participant_role(appointment, user)
    session = VideoSession.objects.select_for_update().filter(appointment=appointment).first()
    if not session:
        raise VideoAccessError("Open the secure room before reporting call activity.")
    if session.status in (VideoSession.Status.COMPLETED, VideoSession.Status.CANCELLED):
        raise VideoAccessError("This video session has ended.", "session_ended")
    event, _ = VideoParticipantEvent.objects.get_or_create(
        session=session,
        participant=user,
        client_event_id=client_event_id,
        defaults={"role": role, "event_type": event_type},
    )
    if event.event_type != event_type:
        raise VideoAccessError("That call event identifier has already been used.", "duplicate_event")
    if event_type in (VideoParticipantEvent.Type.JOINED, VideoParticipantEvent.Type.RECONNECTED):
        updates = {"status": VideoSession.Status.ACTIVE}
        if not session.started_at:
            updates["started_at"] = timezone.now()
        VideoSession.objects.filter(pk=session.pk).update(**updates)
    return event


@transaction.atomic
def complete_video(appointment, user):
    if appointment.expert_id != user.id:
        raise VideoAccessError("Only TK can complete this consultation.", "expert_required")
    appointment = Appointment.objects.select_for_update().get(pk=appointment.pk)
    if appointment.status == Appointment.Status.COMPLETED:
        return appointment.video_session
    if appointment.status != Appointment.Status.CONFIRMED:
        raise VideoAccessError("Only a confirmed appointment can be completed.")
    session = VideoSession.objects.select_for_update().filter(appointment=appointment).first()
    if not session:
        raise VideoAccessError("The video room has not been opened yet.")
    now = timezone.now()
    session.status = VideoSession.Status.COMPLETED
    session.completed_at = now
    session.completed_by = user
    session.save(update_fields=("status", "completed_at", "completed_by", "updated_at"))
    appointment.status = Appointment.Status.COMPLETED
    appointment.save(update_fields=("status", "updated_at"))
    AppointmentStatusHistory.objects.create(
        appointment=appointment,
        from_status=Appointment.Status.CONFIRMED,
        to_status=Appointment.Status.COMPLETED,
        actor=user,
        note="Video consultation completed by TK.",
    )
    transaction.on_commit(lambda: _close_room_safely(session.provider_room_id))
    return session


def _close_room_safely(room_id):
    try:
        provider = get_video_provider()
        if provider.is_configured:
            provider.close_room(room_id=room_id)
    except VideoProviderError:
        logger.exception("Video room close failed", extra={"room_id": room_id})


def cancel_video_for_appointment(appointment):
    session = VideoSession.objects.filter(appointment=appointment).first()
    if not session or session.status in (VideoSession.Status.COMPLETED, VideoSession.Status.CANCELLED):
        return
    VideoSession.objects.filter(pk=session.pk).update(status=VideoSession.Status.CANCELLED)
    transaction.on_commit(lambda: _close_room_safely(session.provider_room_id))
