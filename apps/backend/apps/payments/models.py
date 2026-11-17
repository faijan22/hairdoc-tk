from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q

from apps.core.models import BaseModel


class Order(BaseModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending payment"
        PAID = "PAID", "Paid"
        CANCELLED = "CANCELLED", "Cancelled"
        EXPIRED = "EXPIRED", "Expired"
        REFUND_PENDING = "REFUND_PENDING", "Refund pending"
        PARTIALLY_REFUNDED = "PARTIALLY_REFUNDED", "Partially refunded"
        REFUNDED = "REFUNDED", "Refunded"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders")
    appointment = models.OneToOneField(
        "consultations.Appointment", on_delete=models.PROTECT, related_name="order",
    )
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.PENDING)
    subtotal_amount = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3)
    paid_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=("user", "status", "-created_at"), name="order_user_status_created")]
        constraints = [
            models.CheckConstraint(condition=Q(subtotal_amount__gte=0), name="order_nonnegative_subtotal"),
            models.CheckConstraint(condition=Q(total_amount__gte=0), name="order_nonnegative_total"),
            models.CheckConstraint(condition=Q(total_amount=F("subtotal_amount")), name="order_total_matches_subtotal"),
        ]

    def save(self, *args, **kwargs):
        self.currency = self.currency.upper()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.public_id} - {self.status}"


class OrderItem(BaseModel):
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="items")
    description = models.CharField(max_length=200)
    quantity = models.PositiveSmallIntegerField(default=1)
    unit_amount = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    service_public_id = models.UUIDField()
    consultation_public_id = models.UUIDField()
    appointment_public_id = models.UUIDField()

    class Meta:
        ordering = ("created_at",)
        constraints = [
            models.CheckConstraint(condition=Q(quantity__gte=1), name="order_item_positive_quantity"),
            models.CheckConstraint(condition=Q(unit_amount__gte=0), name="order_item_nonnegative_unit"),
            models.CheckConstraint(condition=Q(total_amount__gte=0), name="order_item_nonnegative_total"),
        ]

    def clean(self):
        if self.total_amount != self.unit_amount * self.quantity:
            raise ValidationError({"total_amount": "Line total must match unit amount multiplied by quantity."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class Payment(BaseModel):
    class Status(models.TextChoices):
        CREATED = "CREATED", "Ready for checkout"
        PROCESSING = "PROCESSING", "Processing"
        SUCCEEDED = "SUCCEEDED", "Paid"
        FAILED = "FAILED", "Failed"
        CANCELLED = "CANCELLED", "Cancelled"
        REFUND_PENDING = "REFUND_PENDING", "Refund pending"
        PARTIALLY_REFUNDED = "PARTIALLY_REFUNDED", "Partially refunded"
        REFUNDED = "REFUNDED", "Refunded"

    order = models.OneToOneField(Order, on_delete=models.PROTECT, related_name="payment")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="payments")
    provider = models.CharField(max_length=24, default="STRIPE")
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.CREATED)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3)
    provider_payment_id = models.CharField(max_length=255, blank=True)
    provider_order_id = models.CharField(max_length=255, blank=True)
    provider_checkout_session_id = models.CharField(max_length=255, blank=True)
    failure_code = models.CharField(max_length=80, blank=True)
    failure_message = models.CharField(max_length=300, blank=True)
    paid_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=("user", "status", "-created_at"), name="payment_user_status_created")]
        constraints = [models.CheckConstraint(condition=Q(amount__gte=0), name="payment_nonnegative_amount")]

    def save(self, *args, **kwargs):
        self.currency = self.currency.upper()
        return super().save(*args, **kwargs)


class PaymentAttempt(BaseModel):
    class Status(models.TextChoices):
        CREATED = "CREATED", "Created"
        OPEN = "OPEN", "Checkout open"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"
        EXPIRED = "EXPIRED", "Expired"

    payment = models.ForeignKey(Payment, on_delete=models.PROTECT, related_name="attempts")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.CREATED)
    idempotency_key = models.CharField(max_length=64, unique=True)
    provider_checkout_session_id = models.CharField(max_length=255, blank=True)
    provider_payment_id = models.CharField(max_length=255, blank=True)
    checkout_url = models.URLField(max_length=2048, blank=True)
    expires_at = models.DateTimeField(blank=True, null=True)
    safe_error = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ("-created_at",)


class Refund(BaseModel):
    class Status(models.TextChoices):
        REQUESTED = "REQUESTED", "Review required"
        PROCESSING = "PROCESSING", "Processing"
        SUCCEEDED = "SUCCEEDED", "Refunded"
        FAILED = "FAILED", "Failed"

    payment = models.ForeignKey(Payment, on_delete=models.PROTECT, related_name="refunds")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.REQUESTED)
    provider_refund_id = models.CharField(max_length=255, blank=True)
    reason = models.CharField(max_length=300)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.CheckConstraint(condition=Q(amount__gt=0), name="refund_positive_amount"),
            models.UniqueConstraint(
                fields=("provider_refund_id",), condition=~Q(provider_refund_id=""), name="unique_provider_refund_id",
            ),
        ]


class WebhookEvent(BaseModel):
    class Status(models.TextChoices):
        RECEIVED = "RECEIVED", "Received"
        PROCESSED = "PROCESSED", "Processed"
        IGNORED = "IGNORED", "Ignored"
        FAILED = "FAILED", "Failed"

    provider = models.CharField(max_length=24, default="STRIPE")
    provider_event_id = models.CharField(max_length=255)
    event_type = models.CharField(max_length=120)
    payload_hash = models.CharField(max_length=64)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.RECEIVED)
    processed_at = models.DateTimeField(blank=True, null=True)
    safe_error = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(fields=("provider", "provider_event_id"), name="unique_provider_webhook_event"),
        ]
