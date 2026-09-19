from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import CoachingPlan, CoachingPlanSection, Recommendation


@transaction.atomic
def create_plan(*, case, author, title, summary):
    if case.service.expert_id != author.id:
        raise ValidationError("This consultation is not assigned to you.")
    if case.coaching_plans.filter(status=CoachingPlan.Status.DRAFT).exists():
        raise ValidationError("Finish the existing draft before creating another version.")
    version = (case.coaching_plans.aggregate(value=Max("version"))["value"] or 0) + 1
    return CoachingPlan.objects.create(case=case, author=author, version=version, title=title, summary=summary)


@transaction.atomic
def update_plan(*, plan, title, summary, sections, recommendations):
    plan = CoachingPlan.objects.select_for_update().get(pk=plan.pk)
    if plan.status != CoachingPlan.Status.DRAFT:
        raise ValidationError("Published coaching plans cannot be changed.")
    plan.title = title
    plan.summary = summary
    plan.save(update_fields=("title", "summary", "updated_at"))
    plan.sections.all().delete()
    plan.recommendations.all().delete()
    CoachingPlanSection.objects.bulk_create([CoachingPlanSection(plan=plan, display_order=index, **item) for index, item in enumerate(sections)])
    Recommendation.objects.bulk_create([Recommendation(plan=plan, display_order=index, **item) for index, item in enumerate(recommendations)])
    return plan


@transaction.atomic
def publish_plan(*, plan):
    plan = CoachingPlan.objects.select_for_update().get(pk=plan.pk)
    if plan.status != CoachingPlan.Status.DRAFT:
        raise ValidationError("Only a draft can be published.")
    if not plan.sections.exclude(title="").exclude(body="").exists():
        raise ValidationError("Add at least one complete guidance section before publishing.")
    plan.status = CoachingPlan.Status.PUBLISHED
    plan.published_at = timezone.now()
    plan.save(update_fields=("status", "published_at", "updated_at"))
    from apps.notifications.services import notify_coaching_plan_published

    notify_coaching_plan_published(plan)
    return plan
