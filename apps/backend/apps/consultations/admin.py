from django.contrib import admin
from django.utils.html import format_html_join

from .models import (
    ConsultationAnswer,
    ConsultationCase,
    ConsultationPhoto,
    ConsultationPhotoAccess,
    AvailabilityException,
    AvailabilityRule,
    Appointment,
    AppointmentStatusHistory,
    ConsultationResponse,
    ConsultationService,
    QuestionOption,
    Questionnaire,
    QuestionnaireQuestion,
)


@admin.register(ConsultationService)
class ConsultationServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "expert", "status", "duration_minutes", "price_amount", "currency", "display_order", "published_at")
    list_filter = ("status", "currency")
    search_fields = ("name", "short_description", "description")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(Questionnaire)
class QuestionnaireAdmin(admin.ModelAdmin):
    list_display = ("title", "service", "version", "status", "published_at", "used")
    list_filter = ("status", "service")
    readonly_fields = ("public_id", "created_at", "updated_at")

    @admin.display(boolean=True)
    def used(self, obj):
        return obj.is_used


class QuestionOptionInline(admin.TabularInline):
    model = QuestionOption
    extra = 0
    fields = ("value", "label", "display_order")


@admin.register(QuestionnaireQuestion)
class QuestionnaireQuestionAdmin(admin.ModelAdmin):
    list_display = ("prompt", "questionnaire", "section", "type", "required", "display_order")
    list_filter = ("type", "required", "questionnaire__service")
    search_fields = ("prompt", "key", "section")
    inlines = (QuestionOptionInline,)
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(ConsultationCase)
class ConsultationCaseAdmin(admin.ModelAdmin):
    list_display = ("public_id", "client", "service_name", "status", "updated_at", "intake_completed_at", "photos_completed_at")
    list_filter = ("status", "service")
    search_fields = ("client__email", "public_id", "service_name")
    readonly_fields = (
        "public_id", "client", "service", "status", "timezone_snapshot", "hair_profile_snapshot",
        "service_name", "duration_minutes", "price_amount", "currency", "questionnaire_version", "intake_answers",
        "intake_completed_at", "created_at", "updated_at",
        "photos_completed_at",
    )

    @admin.display(description="Questionnaire version")
    def questionnaire_version(self, obj):
        return obj.response.questionnaire.version if hasattr(obj, "response") else "-"

    @admin.display(description="Private intake answers")
    def intake_answers(self, obj):
        if not hasattr(obj, "response"):
            return "No intake response."
        answers = obj.response.answers.select_related("question").order_by("question__display_order")
        if not answers:
            return "No answers saved yet."
        return format_html_join("", "<p><strong>{}</strong><br>{}</p>", ((item.question.prompt, item.value) for item in answers))


@admin.register(ConsultationResponse)
class ConsultationResponseAdmin(admin.ModelAdmin):
    list_display = ("case", "questionnaire", "updated_at")
    search_fields = ("case__client__email", "case__public_id")
    readonly_fields = ("public_id", "case", "questionnaire", "created_at", "updated_at")


@admin.register(ConsultationAnswer)
class ConsultationAnswerAdmin(admin.ModelAdmin):
    list_display = ("response", "question", "updated_at")
    search_fields = ("response__case__client__email", "question__prompt")
    readonly_fields = ("public_id", "response", "question", "value", "created_at", "updated_at")


@admin.register(ConsultationPhoto)
class ConsultationPhotoAdmin(admin.ModelAdmin):
    list_display = ("public_id", "case", "category", "uploaded_by", "created_at")
    list_filter = ("category",)
    search_fields = ("public_id", "case__public_id", "case__client__email")
    readonly_fields = (
        "public_id", "case", "stored_file", "uploaded_by", "category", "consent_document",
        "consent_accepted_at", "created_at", "updated_at",
    )

    def has_add_permission(self, request):
        return False


@admin.register(ConsultationPhotoAccess)
class ConsultationPhotoAccessAdmin(admin.ModelAdmin):
    list_display = ("photo", "actor", "purpose", "created_at")
    list_filter = ("purpose",)
    search_fields = ("photo__public_id", "actor__email")
    readonly_fields = ("public_id", "photo", "actor", "purpose", "request_id", "created_at", "updated_at")

    def has_add_permission(self, request):
        return False


@admin.register(AvailabilityRule)
class AvailabilityRuleAdmin(admin.ModelAdmin):
    list_display = ("expert", "weekday", "local_start", "local_end", "timezone", "is_active")
    list_filter = ("expert", "weekday", "is_active")
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(AvailabilityException)
class AvailabilityExceptionAdmin(admin.ModelAdmin):
    list_display = ("expert", "date", "kind", "local_start", "local_end", "timezone", "note")
    list_filter = ("expert", "kind")
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("public_id", "client", "expert", "starts_at", "ends_at", "status", "reservation_expires_at")
    list_filter = ("status", "expert")
    search_fields = ("public_id", "client__email", "case__public_id", "case__service_name")
    readonly_fields = (
        "public_id", "case", "client", "expert", "starts_at", "ends_at", "status", "client_timezone",
        "expert_timezone", "reservation_expires_at", "cancelled_at", "cancel_reason", "created_at", "updated_at",
    )


@admin.register(AppointmentStatusHistory)
class AppointmentStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ("appointment", "from_status", "to_status", "actor", "created_at")
    list_filter = ("to_status",)
    readonly_fields = ("public_id", "appointment", "from_status", "to_status", "actor", "note", "created_at", "updated_at")

    def has_add_permission(self, request):
        return False
