from django.db import models

from apps.core.models import BaseModel


class ContentItem(BaseModel):
    class Type(models.TextChoices):
        TEDX = "TEDX", "TEDx"
        BOOK = "BOOK", "Book"
        PRODUCT = "PRODUCT", "Product"
        RESOURCE = "RESOURCE", "Resource"
        ARTICLE = "ARTICLE", "Article"
        PROMOTION = "PROMOTION", "Promotion"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PUBLISHED = "PUBLISHED", "Published"

    type = models.CharField(max_length=16, choices=Type.choices)
    title = models.CharField(max_length=180)
    slug = models.SlugField(max_length=200, unique=True)
    summary = models.CharField(max_length=320)
    body = models.TextField(blank=True)
    external_url = models.URLField(blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    display_order = models.PositiveSmallIntegerField(default=0)
    published_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ("display_order", "-published_at", "title")
        indexes = [models.Index(fields=("type", "status", "display_order"), name="content_type_status_order")]

    def __str__(self) -> str:
        return self.title

