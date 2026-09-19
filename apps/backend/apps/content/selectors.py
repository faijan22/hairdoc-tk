from django.db.models import Q, QuerySet
from django.utils import timezone

from .models import ContentItem


def published_content() -> QuerySet[ContentItem]:
    return ContentItem.objects.filter(status=ContentItem.Status.PUBLISHED).filter(
        Q(published_at__isnull=True) | Q(published_at__lte=timezone.now())
    )

