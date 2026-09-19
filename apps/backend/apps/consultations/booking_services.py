from datetime import date, datetime, time, timedelta, timezone as datetime_timezone
from decimal import Decimal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.accounts.models import User

from .models import (
    Appointment,
    AppointmentStatusHistory,
    AvailabilityException,
    AvailabilityRule,
    ConsultationCase,
    ConsultationService,
)

SLOT_INCREMENT_MINUTES = 15
RESERVATION_MINUTES = 30
MAX_SLOT_WINDOW_DAYS = 31


class BookingError(Exception):
    def __init__(self, details):
        self.details = details
        super().__init__("The booking request could not be completed.")


def valid_zone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        raise BookingError({"timezone": ["Use a valid IANA timezone, for example Europe/London."]}) from None


def resolve_expert(service: ConsultationService):
    if service.expert_id:
        expert = User.objects.filter(pk=service.expert_id, is_active=True, is_staff=True).first()
        if expert:
            return expert
        raise BookingError({"service": ["The assigned expert is unavailable."]})
    candidates = User.objects.filter(is_active=True, is_staff=True, availability_rules__is_active=True).distinct()
    if candidates.count() == 1:
        return candidates.first()
    all_staff = User.objects.filter(is_active=True, is_staff=True)
    if all_staff.count() == 1:
        return all_staff.first()
    raise BookingError({"service": ["This service needs an assigned expert before booking can open."]})


def _local_to_utc(day: date, wall_time: time, zone: ZoneInfo):
    naive = datetime.combine(day, wall_time)
    aware = naive.replace(tzinfo=zone, fold=0)
    result = aware.astimezone(datetime_timezone.utc)
    if result.astimezone(zone).replace(tzinfo=None) != naive:
        return None
    return result


def _day_bounds(day: date, zone: ZoneInfo):
    start = _local_to_utc(day, time.min, zone)
    end = _local_to_utc(day + timedelta(days=1), time.min, zone)
    return (start, end) if start and end else None


def _merge(intervals):
    merged = []
    for start, end in sorted(intervals):
        if start >= end:
            continue
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def _subtract(intervals, blocks):
    result = intervals
    for blocked_start, blocked_end in blocks:
        next_result = []
        for start, end in result:
            if blocked_end <= start or blocked_start >= end:
                next_result.append((start, end))
                continue
            if blocked_start > start:
                next_result.append((start, blocked_start))
            if blocked_end < end:
                next_result.append((blocked_end, end))
        result = next_result
    return result


def _expert_timezone(expert):
    zone_name = (
        expert.availability_rules.filter(is_active=True).values_list("timezone", flat=True).first()
        or expert.availability_exceptions.values_list("timezone", flat=True).first()
        or "UTC"
    )
    valid_zone(zone_name)
    return zone_name


def _intervals_for_expert_day(expert, day: date):
    intervals = []
    for rule in expert.availability_rules.filter(is_active=True, weekday=day.weekday()):
        if rule.effective_from and day < rule.effective_from:
            continue
        if rule.effective_until and day > rule.effective_until:
            continue
        zone = valid_zone(rule.timezone)
        start = _local_to_utc(day, rule.local_start, zone)
        end = _local_to_utc(day, rule.local_end, zone)
        if start and end and end > start:
            intervals.append((start, end))

    extras, blocks = [], []
    for exception in expert.availability_exceptions.filter(date=day):
        zone = valid_zone(exception.timezone)
        if exception.local_start is None:
            bounds = _day_bounds(day, zone)
            if bounds:
                blocks.append(bounds)
            continue
        start = _local_to_utc(day, exception.local_start, zone)
        end = _local_to_utc(day, exception.local_end, zone)
        if not start or not end or end <= start:
            continue
        (extras if exception.kind == AvailabilityException.Kind.EXTRA else blocks).append((start, end))
    return _merge(_subtract(_merge(intervals + extras), _merge(blocks)))


def expire_pending_reservations(queryset=None):
    now = timezone.now()
    queryset = queryset if queryset is not None else Appointment.objects.all()
    expired = list(queryset.filter(status=Appointment.Status.PAYMENT_PENDING, reservation_expires_at__lte=now))
    for appointment in expired:
        appointment.status = Appointment.Status.EXPIRED
        appointment.save(update_fields=("status", "updated_at"))
        AppointmentStatusHistory.objects.create(
            appointment=appointment,
            from_status=Appointment.Status.PAYMENT_PENDING,
            to_status=Appointment.Status.EXPIRED,
            note="Payment reservation expired.",
        )
    return len(expired)


def available_slots(case, date_from: date, date_to: date, client_timezone: str, exclude_appointment=None):
    _assert_bookable_case(case)
    if date_to < date_from or (date_to - date_from).days >= MAX_SLOT_WINDOW_DAYS:
        raise BookingError({"date_to": [f"Choose a window of {MAX_SLOT_WINDOW_DAYS} days or fewer."]})
    client_zone = valid_zone(client_timezone)
    expert = resolve_expert(case.service)
    expert_zone_name = _expert_timezone(expert)
    expert_zone = valid_zone(expert_zone_name)
    expire_pending_reservations(Appointment.objects.filter(expert=expert))

    client_window_start = datetime.combine(date_from, time.min, client_zone).astimezone(datetime_timezone.utc)
    client_window_end = datetime.combine(date_to + timedelta(days=1), time.min, client_zone).astimezone(datetime_timezone.utc)
    first_expert_day = client_window_start.astimezone(expert_zone).date() - timedelta(days=1)
    last_expert_day = client_window_end.astimezone(expert_zone).date() + timedelta(days=1)
    occupied_query = Appointment.objects.filter(
        expert=expert,
        starts_at__lt=client_window_end,
        ends_at__gt=client_window_start,
    ).filter(
        Q(status=Appointment.Status.CONFIRMED)
        | Q(status=Appointment.Status.PAYMENT_PENDING, reservation_expires_at__gt=timezone.now())
    )
    if exclude_appointment:
        occupied_query = occupied_query.exclude(pk=exclude_appointment.pk)
    occupied = list(occupied_query.values_list("starts_at", "ends_at"))
    duration = timedelta(minutes=case.duration_minutes)
    increment = timedelta(minutes=SLOT_INCREMENT_MINUTES)
    earliest = timezone.now()
    slots = []
    day = first_expert_day
    seen = set()
    while day <= last_expert_day:
        for interval_start, interval_end in _intervals_for_expert_day(expert, day):
            candidate = interval_start
            while candidate + duration <= interval_end:
                end = candidate + duration
                local_start = candidate.astimezone(client_zone)
                if (
                    candidate >= earliest
                    and date_from <= local_start.date() <= date_to
                    and not any(candidate < busy_end and end > busy_start for busy_start, busy_end in occupied)
                    and candidate not in seen
                ):
                    seen.add(candidate)
                    slots.append({
                        "starts_at": candidate,
                        "ends_at": end,
                        "local_date": local_start.date(),
                        "local_start": local_start,
                        "local_end": end.astimezone(client_zone),
                    })
                candidate += increment
        day += timedelta(days=1)
    return expert, expert_zone_name, sorted(slots, key=lambda item: item["starts_at"])


def _assert_bookable_case(case):
    if case.status != ConsultationCase.Status.PHOTOS_COMPLETE:
        raise BookingError({"case": ["Submit the consultation intake and private photos before booking."]})


def _slot_for_start(case, desired_start, client_timezone, exclude_appointment=None):
    local_date = desired_start.astimezone(valid_zone(client_timezone)).date()
    expert, expert_timezone, slots = available_slots(
        case, local_date, local_date, client_timezone, exclude_appointment=exclude_appointment,
    )
    match = next((slot for slot in slots if slot["starts_at"] == desired_start), None)
    if not match:
        raise BookingError({"starts_at": ["This slot is no longer available. Refresh and choose another time."]})
    return expert, expert_timezone, match


@transaction.atomic
def create_appointment(client, case, desired_start, client_timezone):
    case = ConsultationCase.objects.select_for_update().select_related("service").get(pk=case.pk)
    _assert_bookable_case(case)
    expert = resolve_expert(case.service)
    User.objects.select_for_update().get(pk=expert.pk)
    expire_pending_reservations(Appointment.objects.filter(expert=expert))
    if case.appointments.filter(status__in=(Appointment.Status.PAYMENT_PENDING, Appointment.Status.CONFIRMED)).exists():
        raise BookingError({"case": ["This consultation already has an active appointment."]})
    expert, expert_timezone, slot = _slot_for_start(case, desired_start, client_timezone)
    now = timezone.now()
    requires_payment = case.price_amount > Decimal("0")
    appointment_status = (
        Appointment.Status.PAYMENT_PENDING if requires_payment else Appointment.Status.CONFIRMED
    )
    appointment = Appointment.objects.create(
        case=case,
        client=client,
        expert=expert,
        starts_at=slot["starts_at"],
        ends_at=slot["ends_at"],
        client_timezone=client_timezone,
        expert_timezone=expert_timezone,
        status=appointment_status,
        reservation_expires_at=(now + timedelta(minutes=RESERVATION_MINUTES)) if requires_payment else None,
    )
    AppointmentStatusHistory.objects.create(
        appointment=appointment,
        to_status=appointment_status,
        actor=client,
        note=(
            f"Slot reserved for {RESERVATION_MINUTES} minutes pending payment."
            if requires_payment
            else "Confirmed immediately because this consultation has no charge."
        ),
    )
    if not requires_payment:
        from apps.messaging.services import ensure_consultation_conversation
        from apps.notifications.services import notify_appointment_confirmed

        ensure_consultation_conversation(appointment)
        notify_appointment_confirmed(appointment)
    return appointment


@transaction.atomic
def reschedule_appointment(appointment, actor, desired_start, client_timezone):
    appointment = Appointment.objects.select_for_update().select_related("case__service", "expert").get(pk=appointment.pk)
    if appointment.status not in (Appointment.Status.PAYMENT_PENDING, Appointment.Status.CONFIRMED):
        raise BookingError({"appointment": ["This appointment cannot be rescheduled."]})
    User.objects.select_for_update().get(pk=appointment.expert_id)
    expire_pending_reservations(Appointment.objects.filter(expert=appointment.expert).exclude(pk=appointment.pk))
    expert, expert_timezone, slot = _slot_for_start(
        appointment.case, desired_start, client_timezone, exclude_appointment=appointment,
    )
    previous = f"{appointment.starts_at.isoformat()} to {appointment.ends_at.isoformat()}"
    appointment.expert = expert
    appointment.starts_at = slot["starts_at"]
    appointment.ends_at = slot["ends_at"]
    appointment.client_timezone = client_timezone
    appointment.expert_timezone = expert_timezone
    if appointment.status == Appointment.Status.PAYMENT_PENDING:
        appointment.reservation_expires_at = timezone.now() + timedelta(minutes=RESERVATION_MINUTES)
    appointment.save(update_fields=(
        "expert", "starts_at", "ends_at", "client_timezone", "expert_timezone",
        "reservation_expires_at", "updated_at",
    ))
    AppointmentStatusHistory.objects.create(
        appointment=appointment,
        from_status=appointment.status,
        to_status=appointment.status,
        actor=actor,
        note=f"Rescheduled from {previous}.",
    )
    from apps.notifications.services import notify_appointment_rescheduled

    notify_appointment_rescheduled(appointment)
    return appointment


@transaction.atomic
def cancel_appointment(appointment, actor, reason=""):
    appointment = Appointment.objects.select_for_update().get(pk=appointment.pk)
    if appointment.status not in (Appointment.Status.PAYMENT_PENDING, Appointment.Status.CONFIRMED):
        raise BookingError({"appointment": ["This appointment cannot be cancelled."]})
    previous_status = appointment.status
    appointment.status = Appointment.Status.CANCELLED
    appointment.cancelled_at = timezone.now()
    appointment.cancel_reason = reason
    appointment.reservation_expires_at = None
    appointment.save(update_fields=(
        "status", "cancelled_at", "cancel_reason", "reservation_expires_at", "updated_at",
    ))
    AppointmentStatusHistory.objects.create(
        appointment=appointment,
        from_status=previous_status,
        to_status=Appointment.Status.CANCELLED,
        actor=actor,
        note=reason,
    )
    from apps.video.services import cancel_video_for_appointment
    from apps.notifications.services import notify_appointment_cancelled

    cancel_video_for_appointment(appointment)
    notify_appointment_cancelled(appointment)
    return appointment
