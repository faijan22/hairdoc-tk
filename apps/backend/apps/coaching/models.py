from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import BaseModel


class CoachingPlan(BaseModel):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PUBLISHED = "PUBLISHED", "Published"

    case = models.ForeignKey("consultations.ConsultationCase", on_delete=models.CASCADE, related_name="coaching_plans")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="authored_coaching_plans")
    version = models.PositiveIntegerField()
    title = models.CharField(max_length=180)
    summary = models.CharField(max_length=500, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    published_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ("-version",)
        constraints = [
            models.UniqueConstraint(fields=("case", "version"), name="unique_case_coaching_plan_version"),
            models.UniqueConstraint(fields=("case",), condition=models.Q(status="DRAFT"), name="unique_case_coaching_plan_draft"),
        ]
        indexes = [models.Index(fields=("case", "status", "-version"), name="coaching_case_status_version")]

    def save(self, *args, **kwargs):
        if self.pk:
            previous = CoachingPlan.objects.get(pk=self.pk)
            if previous.status == self.Status.PUBLISHED:
                locked = ("case_id", "author_id", "version", "title", "summary", "status", "published_at")
                if any(getattr(previous, field) != getattr(self, field) for field in locked):
                    raise ValidationError("Published coaching plans are immutable; create a new version instead.")
        return super().save(*args, **kwargs)


class CoachingPlanSection(BaseModel):
    plan = models.ForeignKey(CoachingPlan, on_delete=models.CASCADE, related_name="sections")
    title = models.CharField(max_length=160)
    body = models.TextField(max_length=4000)
    display_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ("display_order", "id")
        constraints = [models.UniqueConstraint(fields=("plan", "display_order"), name="unique_plan_section_order")]

    def save(self, *args, **kwargs):
        if self.plan.status != CoachingPlan.Status.DRAFT:
            raise ValidationError("Published coaching plan sections cannot be changed.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.plan.status != CoachingPlan.Status.DRAFT:
            raise ValidationError("Published coaching plan sections cannot be changed.")
        return super().delete(*args, **kwargs)


class Recommendation(BaseModel):
    class Category(models.TextChoices):
        ROUTINE = "ROUTINE", "Routine"
        PRODUCT = "PRODUCT", "Product"
        LIFESTYLE = "LIFESTYLE", "Lifestyle"
        FOLLOW_UP = "FOLLOW_UP", "Follow-up"
        RESOURCE = "RESOURCE", "Resource"

    plan = models.ForeignKey(CoachingPlan, on_delete=models.CASCADE, related_name="recommendations")
    category = models.CharField(max_length=16, choices=Category.choices)
    title = models.CharField(max_length=160)
    guidance = models.TextField(max_length=2000)
    external_url = models.URLField(max_length=500, blank=True)
    display_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ("display_order", "id")
        constraints = [models.UniqueConstraint(fields=("plan", "display_order"), name="unique_plan_recommendation_order")]

    def save(self, *args, **kwargs):
        if self.plan.status != CoachingPlan.Status.DRAFT:
            raise ValidationError("Published coaching plan recommendations cannot be changed.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.plan.status != CoachingPlan.Status.DRAFT:
            raise ValidationError("Published coaching plan recommendations cannot be changed.")
        return super().delete(*args, **kwargs)
