from django.contrib import admin

from .models import Order, OrderItem, Payment, PaymentAttempt, Refund, WebhookEvent


class ReadOnlyPaymentAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False
    readonly_fields = ("description", "quantity", "unit_amount", "total_amount", "service_public_id", "consultation_public_id", "appointment_public_id")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(ReadOnlyPaymentAdmin):
    list_display = ("public_id", "user", "appointment", "status", "total_amount", "currency", "paid_at", "created_at")
    list_filter = ("status", "currency")
    search_fields = ("public_id", "user__email", "appointment__public_id")
    readonly_fields = ("public_id", "user", "appointment", "status", "subtotal_amount", "total_amount", "currency", "paid_at", "created_at", "updated_at")
    inlines = (OrderItemInline,)


@admin.register(Payment)
class PaymentAdmin(ReadOnlyPaymentAdmin):
    list_display = ("public_id", "user", "provider", "status", "amount", "currency", "paid_at", "created_at")
    list_filter = ("provider", "status", "currency")
    search_fields = ("public_id", "user__email", "provider_payment_id", "provider_checkout_session_id")
    readonly_fields = tuple(field.name for field in Payment._meta.fields)


@admin.register(PaymentAttempt)
class PaymentAttemptAdmin(ReadOnlyPaymentAdmin):
    list_display = ("public_id", "payment", "status", "expires_at", "created_at")
    list_filter = ("status",)
    search_fields = ("provider_checkout_session_id", "provider_payment_id", "payment__public_id")
    readonly_fields = tuple(field.name for field in PaymentAttempt._meta.fields)


@admin.register(Refund)
class RefundAdmin(ReadOnlyPaymentAdmin):
    list_display = ("public_id", "payment", "status", "amount", "currency", "created_at")
    list_filter = ("status", "currency")
    search_fields = ("payment__public_id", "provider_refund_id")
    readonly_fields = tuple(field.name for field in Refund._meta.fields)


@admin.register(WebhookEvent)
class WebhookEventAdmin(ReadOnlyPaymentAdmin):
    list_display = ("provider_event_id", "event_type", "status", "processed_at", "created_at")
    list_filter = ("provider", "status", "event_type")
    search_fields = ("provider_event_id",)
    readonly_fields = tuple(field.name for field in WebhookEvent._meta.fields)
