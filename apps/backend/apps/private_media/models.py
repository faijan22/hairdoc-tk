from django.conf import settings
from django.db import models

from apps.core.models import BaseModel


class StoredFile(BaseModel):
    class Status(models.TextChoices):
        READY = "READY", "Ready"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="stored_files")
    storage_key = models.CharField(max_length=500, unique=True)
    original_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)
    byte_size = models.PositiveBigIntegerField()
    checksum_sha256 = models.CharField(max_length=64)
    width = models.PositiveIntegerField()
    height = models.PositiveIntegerField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.READY)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=("owner", "status", "-created_at"), name="private_file_owner_status")]

    def __str__(self) -> str:
        return f"{self.original_name} ({self.public_id})"
