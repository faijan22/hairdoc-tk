from django.contrib import admin

from .models import CoachingPlan, CoachingPlanSection, Recommendation


class CoachingPlanSectionInline(admin.StackedInline):
    model = CoachingPlanSection
    extra = 0


class RecommendationInline(admin.StackedInline):
    model = Recommendation
    extra = 0


@admin.register(CoachingPlan)
class CoachingPlanAdmin(admin.ModelAdmin):
    list_display = ("title", "case", "version", "status", "author", "published_at")
    list_filter = ("status", "author")
    search_fields = ("title", "case__client__email", "case__public_id")
    readonly_fields = ("public_id", "created_at", "updated_at")
    inlines = (CoachingPlanSectionInline, RecommendationInline)
