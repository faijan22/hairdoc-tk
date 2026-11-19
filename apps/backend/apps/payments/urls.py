from django.urls import path

from .views import (
    OrderCheckoutView,
    OrderCreateView,
    PaymentDetailView,
    PaymentListView,
    PaymentRefreshView,
    StaffPaymentDetailView,
    StaffPaymentListView,
    StripeWebhookView,
    payment_return_cancel,
    payment_return_success,
)

app_name = "payments"

urlpatterns = [
    path("orders/", OrderCreateView.as_view(), name="order-create"),
    path("orders/<uuid:public_id>/checkout/", OrderCheckoutView.as_view(), name="order-checkout"),
    path("payments/", PaymentListView.as_view(), name="payment-list"),
    path("payments/<uuid:public_id>/", PaymentDetailView.as_view(), name="payment-detail"),
    path("payments/<uuid:public_id>/refresh/", PaymentRefreshView.as_view(), name="payment-refresh"),
    path("staff/payments/", StaffPaymentListView.as_view(), name="staff-payment-list"),
    path("staff/payments/<uuid:public_id>/", StaffPaymentDetailView.as_view(), name="staff-payment-detail"),
    path("payments/return/success/", payment_return_success, name="return-success"),
    path("payments/return/cancel/", payment_return_cancel, name="return-cancel"),
    path("integrations/stripe/webhook/", StripeWebhookView.as_view(), name="stripe-webhook"),
]
