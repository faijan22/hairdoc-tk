from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import ProgressCheckIn


@transaction.atomic
def create_check_in(*, case, client):
    locked_case = type(case).objects.select_for_update().get(pk=case.pk)
    if not locked_case.coaching_plans.filter(status="PUBLISHED").exists():
        raise ValidationError("A published care plan is required before starting a progress check-in.")
    draft = locked_case.progress_check_ins.filter(status=ProgressCheckIn.Status.DRAFT).first()
    if draft:
        return draft, False
    sequence = (locked_case.progress_check_ins.aggregate(value=Max("sequence"))["value"] or 0) + 1
    return ProgressCheckIn.objects.create(case=locked_case, client=client, sequence=sequence), True


@transaction.atomic
def update_check_in(*, check_in, **values):
    locked = ProgressCheckIn.objects.select_for_update().get(pk=check_in.pk)
    if locked.status != ProgressCheckIn.Status.DRAFT:
        raise ValidationError("Submitted check-ins cannot be changed.")
    for field, value in values.items():
        setattr(locked, field, value)
    locked.save(update_fields=tuple(values) + ("updated_at",))
    return locked


@transaction.atomic
def submit_check_in(*, check_in):
    locked = ProgressCheckIn.objects.select_for_update().get(pk=check_in.pk)
    if locked.status != ProgressCheckIn.Status.DRAFT:
        return locked
    if not locked.summary.strip():
        raise ValidationError("Add a progress summary before submitting.")
    if not locked.photos.exists():
        raise ValidationError("Add at least one progress photo before submitting.")
    locked.status = ProgressCheckIn.Status.SUBMITTED
    locked.submitted_at = timezone.now()
    locked.save(update_fields=("status", "submitted_at", "updated_at"))
    from apps.notifications.services import notify_progress_submitted

    notify_progress_submitted(locked)
    return locked


@transaction.atomic
def save_feedback(*, check_in, reviewer, feedback):
    locked = ProgressCheckIn.objects.select_for_update().get(pk=check_in.pk)
    if locked.status not in (ProgressCheckIn.Status.SUBMITTED, ProgressCheckIn.Status.REVIEWED):
        raise ValidationError("Only submitted check-ins can be reviewed.")
    if locked.feedback_published_at:
        raise ValidationError("Published feedback is locked.")
    locked.expert_feedback = feedback
    locked.reviewed_by = reviewer
    locked.save(update_fields=("expert_feedback", "reviewed_by", "updated_at"))
    return locked


@transaction.atomic
def publish_feedback(*, check_in, reviewer):
    locked = ProgressCheckIn.objects.select_for_update().get(pk=check_in.pk)
    if locked.status != ProgressCheckIn.Status.SUBMITTED:
        raise ValidationError("Only a submitted check-in can receive published feedback.")
    if not locked.expert_feedback.strip():
        raise ValidationError("Write feedback before publishing it.")
    locked.status = ProgressCheckIn.Status.REVIEWED
    locked.reviewed_by = reviewer
    locked.feedback_published_at = timezone.now()
    locked.save(update_fields=("status", "reviewed_by", "feedback_published_at", "updated_at"))
    from apps.notifications.services import notify_progress_feedback_published

    notify_progress_feedback_published(locked)
    return locked
