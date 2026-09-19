from django.utils import timezone

from .models import ConsultationService, Questionnaire


def published_services():
    return ConsultationService.objects.filter(
        status=ConsultationService.Status.PUBLISHED,
        published_at__isnull=False,
        published_at__lte=timezone.now(),
    )


def current_questionnaire(service: ConsultationService):
    return (
        Questionnaire.objects.filter(
            service=service,
            status=Questionnaire.Status.PUBLISHED,
            published_at__isnull=False,
            published_at__lte=timezone.now(),
        )
        .order_by("-version", "-published_at")
        .first()
    )
