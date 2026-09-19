from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.consultations.models import Appointment

from .models import Order, Payment
from .serializers import (
    CheckoutSerializer,
    OrderCreateSerializer,
    OrderSerializer,
    PaymentSerializer,
    StaffPaymentSerializer,
)
from .services import PaymentError, create_checkout, create_order, parse_and_process_webhook


class PaymentUnavailable(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_code = "PAYMENT_UNAVAILABLE"


def _raise_payment(exc):
    if exc.unavailable:
        raise PaymentUnavailable(detail=exc.details) from None
    raise ValidationError(exc.details) from None


class OrderCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        appointment = get_object_or_404(
            Appointment.objects.select_related("case__service", "client"),
            public_id=serializer.validated_data["appointment_public_id"], client=request.user,
        )
        try:
            order, created = create_order(request.user, appointment)
        except PaymentError as exc:
            _raise_payment(exc)
        order = Order.objects.select_related("appointment__case", "payment").prefetch_related("items").get(pk=order.pk)
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class OrderCheckoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, public_id):
        order = get_object_or_404(
            Order.objects.select_related("user", "appointment__case"), public_id=public_id, user=request.user,
        )
        try:
            payment, attempt = create_checkout(request.user, order)
        except PaymentError as exc:
            _raise_payment(exc)
        payload = {"payment": payment, "checkout_url": attempt.checkout_url, "expires_at": attempt.expires_at}
        return Response(CheckoutSerializer(payload).data)


class PaymentListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        payments = request.user.payments.select_related(
            "order__appointment__case",
        ).prefetch_related("refunds")
        return Response(PaymentSerializer(payments, many=True).data)


class PaymentDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, public_id):
        payment = get_object_or_404(
            Payment.objects.select_related("order__appointment__case").prefetch_related("refunds"),
            public_id=public_id, user=request.user,
        )
        return Response(PaymentSerializer(payment).data)


def _staff_payments(request):
    return Payment.objects.filter(
        order__appointment__expert=request.user,
    ).select_related(
        "user", "order__appointment__case",
    ).prefetch_related("refunds")


class StaffPaymentListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        return Response(StaffPaymentSerializer(_staff_payments(request)[:100], many=True).data)


class StaffPaymentDetailView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, public_id):
        payment = get_object_or_404(_staff_payments(request), public_id=public_id)
        return Response(StaffPaymentSerializer(payment).data)


class SquareWebhookView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            event = parse_and_process_webhook(
                request.body,
                request.headers.get("X-Square-HmacSha256-Signature", ""),
            )
        except PaymentError as exc:
            raise ValidationError(exc.details) from None
        return Response({"received": True, "status": event.status})


def payment_return_success(request):
    return _return_page(
        "Payment submitted",
        "Square has returned your payment. Go back to HairDoc TK while the secure confirmation finishes.",
    )


def payment_return_cancel(request):
    return _return_page(
        "Checkout closed",
        "No confirmation was received. Return to HairDoc TK to try again while your reservation remains active.",
    )


def _return_page(title, message):
    body = f"""<!doctype html><html><head><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
    <title>{title}</title><style>body{{margin:0;background:#f7f3ec;color:#1b2821;font:16px system-ui;display:grid;min-height:100vh;place-items:center}}
    main{{max-width:420px;margin:24px;padding:28px;background:#fffdfa;border:1px solid #dce2dc;border-radius:20px}}h1{{font:700 28px Georgia,serif}}p{{line-height:1.55;color:#5f6c64}}</style></head>
    <body><main><h1>{title}</h1><p>{message}</p><p>You may close this page.</p></main></body></html>"""
    return HttpResponse(body)
