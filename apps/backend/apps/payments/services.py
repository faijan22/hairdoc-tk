import hashlib
import uuid
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.module_loading import import_string

from apps.consultations.booking_services import expire_pending_reservations
from apps.consultations.models import Appointment, AppointmentStatusHistory

from .models import Order, OrderItem, Payment, PaymentAttempt, Refund, WebhookEvent
from .providers.base import PaymentProviderConfigurationError


class PaymentError(Exception):
    def __init__(self, details, *, unavailable=False):
        self.details = details
        self.unavailable = unavailable
        super().__init__("The payment request could not be completed.")


def get_payment_provider():
    return import_string(settings.PAYMENT_PROVIDER_BACKEND)()


@transaction.atomic
def create_order(user, appointment):
    appointment = Appointment.objects.select_for_update().select_related("case__service", "client").get(pk=appointment.pk)
    expire_pending_reservations(Appointment.objects.filter(pk=appointment.pk))
    appointment.refresh_from_db()
    if appointment.client_id != user.id:
        raise PaymentError({"appointment": ["This appointment is not available."]})
    existing = Order.objects.filter(appointment=appointment).first()
    if existing:
        return existing, False
    if appointment.status != Appointment.Status.PAYMENT_PENDING:
        raise PaymentError({"appointment": ["Only a current payment-pending reservation can be checked out."]})
    case = appointment.case
    order = Order.objects.create(
        user=user, appointment=appointment, status=Order.Status.PENDING,
        subtotal_amount=case.price_amount, total_amount=case.price_amount, currency=case.currency,
    )
    OrderItem.objects.create(
        order=order, description=case.service_name, quantity=1,
        unit_amount=case.price_amount, total_amount=case.price_amount,
        service_public_id=case.service.public_id, consultation_public_id=case.public_id,
        appointment_public_id=appointment.public_id,
    )
    return order, True


@transaction.atomic
def create_checkout(user, order):
    order = Order.objects.select_for_update().select_related("user", "appointment__case").get(pk=order.pk)
    if order.user_id != user.id:
        raise PaymentError({"order": ["This order is not available."]})
    if order.status == Order.Status.PAID:
        raise PaymentError({"order": ["This order has already been paid."]})
    expire_pending_reservations(Appointment.objects.filter(pk=order.appointment_id))
    order.appointment.refresh_from_db()
    if order.appointment.status != Appointment.Status.PAYMENT_PENDING:
        if order.status == Order.Status.PENDING:
            order.status = Order.Status.EXPIRED
            order.save(update_fields=("status", "updated_at"))
        raise PaymentError({"appointment": ["This payment reservation has expired."]})

    provider = get_payment_provider()
    payment, _ = Payment.objects.get_or_create(
        order=order,
        defaults={
            "user": user, "provider": provider.code, "status": Payment.Status.CREATED,
            "amount": order.total_amount, "currency": order.currency,
        },
    )
    settled = {
        Payment.Status.SUCCEEDED, Payment.Status.REFUND_PENDING,
        Payment.Status.PARTIALLY_REFUNDED, Payment.Status.REFUNDED,
    }
    if payment.provider != provider.code and payment.status not in settled:
        payment.provider = provider.code
        payment.provider_payment_id = ""
        payment.provider_order_id = ""
        payment.provider_checkout_session_id = ""
        payment.save(update_fields=(
            "provider", "provider_payment_id", "provider_order_id",
            "provider_checkout_session_id", "updated_at",
        ))
    reusable = payment.attempts.filter(
        status=PaymentAttempt.Status.OPEN,
        expires_at__gt=timezone.now() + timedelta(seconds=30),
    ).first()
    if reusable:
        return payment, reusable

    attempt = PaymentAttempt.objects.create(
        payment=payment, idempotency_key=f"checkout-{uuid.uuid4().hex}",
    )
    try:
        session = provider.create_checkout(
            order=order, attempt=attempt, return_base_url=settings.PAYMENT_RETURN_BASE_URL,
        )
    except PaymentProviderConfigurationError as exc:
        attempt.status = PaymentAttempt.Status.FAILED
        attempt.safe_error = str(exc)
        attempt.save(update_fields=("status", "safe_error", "updated_at"))
        payment.status = Payment.Status.FAILED
        payment.failure_code = "PAYMENT_NOT_CONFIGURED"
        payment.failure_message = str(exc)
        payment.save(update_fields=("status", "failure_code", "failure_message", "updated_at"))
        raise PaymentError({"checkout": [str(exc)]}, unavailable=True) from None
    except Exception:
        attempt.status = PaymentAttempt.Status.FAILED
        attempt.safe_error = "The payment provider could not create the checkout session."
        attempt.save(update_fields=("status", "safe_error", "updated_at"))
        payment.status = Payment.Status.FAILED
        payment.failure_code = "PROVIDER_ERROR"
        payment.failure_message = "Secure checkout could not be started. Please try again."
        payment.save(update_fields=("status", "failure_code", "failure_message", "updated_at"))
        raise PaymentError({"checkout": [payment.failure_message]}, unavailable=True) from None

    attempt.status = PaymentAttempt.Status.OPEN
    attempt.provider_checkout_session_id = session.session_id
    attempt.checkout_url = session.url
    attempt.expires_at = session.expires_at
    attempt.save(update_fields=(
        "status", "provider_checkout_session_id", "checkout_url", "expires_at", "updated_at",
    ))
    payment.status = Payment.Status.PROCESSING
    payment.provider_checkout_session_id = session.session_id
    payment.provider_order_id = session.order_id
    payment.failure_code = ""
    payment.failure_message = ""
    payment.save(update_fields=(
        "status", "provider_checkout_session_id", "provider_order_id",
        "failure_code", "failure_message", "updated_at",
    ))
    order.appointment.reservation_expires_at = session.expires_at
    order.appointment.save(update_fields=("reservation_expires_at", "updated_at"))
    return payment, attempt


def parse_and_process_webhook(payload: bytes, signature: str):
    provider = get_payment_provider()
    try:
        event = provider.parse_webhook(payload, signature)
    except Exception as exc:
        raise PaymentError({"signature": ["The payment webhook signature is invalid."]}) from exc
    event_id = str(event.get("id") or event.get("event_id") or "")
    event_type = str(event.get("type") or "")
    if not event_id or not event_type:
        raise PaymentError({"event": ["Payment webhook identity is missing."]})
    digest = hashlib.sha256(payload).hexdigest()
    with transaction.atomic():
        record, created = WebhookEvent.objects.select_for_update().get_or_create(
            provider=provider.code, provider_event_id=event_id,
            defaults={"event_type": event_type, "payload_hash": digest},
        )
        if not created and record.payload_hash != digest:
            raise PaymentError({"event": ["A webhook event ID was reused with different content."]})
        if record.status in (WebhookEvent.Status.PROCESSED, WebhookEvent.Status.IGNORED):
            return record
    try:
        with transaction.atomic():
            record = WebhookEvent.objects.select_for_update().get(pk=record.pk)
            if record.status in (WebhookEvent.Status.PROCESSED, WebhookEvent.Status.IGNORED):
                return record
            provider_object = (event.get("data") or {}).get("object") or {}
            handled = _process_provider_event(provider.code, event_type, provider_object)
            record.status = WebhookEvent.Status.PROCESSED if handled else WebhookEvent.Status.IGNORED
            record.processed_at = timezone.now()
            record.safe_error = ""
            record.save(update_fields=("status", "processed_at", "safe_error", "updated_at"))
            return record
    except PaymentError as exc:
        WebhookEvent.objects.filter(pk=record.pk).update(
            status=WebhookEvent.Status.FAILED,
            safe_error=str(exc.details)[:300],
            updated_at=timezone.now(),
        )
        raise


def refresh_payment_status(user, payment):
    if payment.user_id != user.id:
        raise PaymentError({"payment": ["This payment is not available."]})
    if payment.provider != "STRIPE" or not payment.provider_checkout_session_id:
        return payment
    if payment.status not in {Payment.Status.CREATED, Payment.Status.PROCESSING}:
        return payment
    provider = get_payment_provider()
    if provider.code != payment.provider:
        raise PaymentError({"payment": ["The configured payment provider does not match this payment."]})
    try:
        stripe_session = provider.retrieve_checkout(payment.provider_checkout_session_id)
    except PaymentProviderConfigurationError as exc:
        raise PaymentError({"payment": [str(exc)]}, unavailable=True) from None
    except Exception:
        raise PaymentError(
            {"payment": ["Stripe could not be reached. Please try again shortly."]},
            unavailable=True,
        ) from None

    session_status = str(stripe_session.get("status") or "")
    payment_status = str(stripe_session.get("payment_status") or "")
    event_type = None
    if payment_status == "paid":
        event_type = "checkout.session.completed"
    elif session_status == "expired":
        event_type = "checkout.session.expired"
    elif session_status == "complete" and payment_status == "unpaid":
        event_type = "checkout.session.completed"
    if event_type:
        with transaction.atomic():
            _process_stripe_checkout(event_type, stripe_session)
    return Payment.objects.select_related("order__appointment__case").prefetch_related("refunds").get(
        pk=payment.pk,
    )


def _process_provider_event(provider_code, event_type, provider_object):
    if provider_code == "STRIPE" and event_type in {
        "checkout.session.completed",
        "checkout.session.async_payment_succeeded",
        "checkout.session.async_payment_failed",
        "checkout.session.expired",
    }:
        return _process_stripe_checkout(event_type, provider_object)
    if provider_code == "STRIPE" and event_type in {"refund.created", "refund.updated", "refund.failed"}:
        return _process_stripe_refund(provider_object)
    return False


def _process_stripe_checkout(event_type, stripe_session):
    session_id = str(stripe_session.get("id") or "")
    if not session_id:
        return False
    try:
        payment = Payment.objects.select_for_update().select_related("order__appointment").get(
            provider="STRIPE", provider_checkout_session_id=session_id,
        )
    except Payment.DoesNotExist:
        return False

    order_reference = str(stripe_session.get("client_reference_id") or "")
    metadata_reference = str((stripe_session.get("metadata") or {}).get("hairdoc_order_id") or "")
    if order_reference != str(payment.order.public_id) or (
        metadata_reference and metadata_reference != str(payment.order.public_id)
    ):
        raise PaymentError({"event": ["The Stripe checkout does not match this order."]})

    payment_intent = stripe_session.get("payment_intent")
    if isinstance(payment_intent, dict):
        payment_intent = payment_intent.get("id")
    provider_payment_id = str(payment_intent or "")
    if payment.provider_payment_id and provider_payment_id and provider_payment_id != payment.provider_payment_id:
        raise PaymentError({"event": ["The Stripe payment does not match this order."]})
    settled = {
        Payment.Status.SUCCEEDED, Payment.Status.REFUND_PENDING,
        Payment.Status.PARTIALLY_REFUNDED, Payment.Status.REFUNDED,
    }
    attempt = payment.attempts.filter(status=PaymentAttempt.Status.OPEN).first()
    payment_status = str(stripe_session.get("payment_status") or "")
    if event_type in {"checkout.session.completed", "checkout.session.async_payment_succeeded"} and payment_status == "paid":
        _validate_stripe_money(payment.order, stripe_session)
        if not provider_payment_id:
            raise PaymentError({"event": ["Stripe payment intent is missing."]})
        if payment.status in settled:
            return True
        now = timezone.now()
        payment.status = Payment.Status.SUCCEEDED
        payment.provider_payment_id = provider_payment_id
        payment.paid_at = payment.paid_at or now
        payment.failure_code = ""
        payment.failure_message = ""
        payment.save(update_fields=(
            "status", "provider_payment_id", "paid_at", "failure_code", "failure_message", "updated_at",
        ))
        payment.order.status = Order.Status.PAID
        payment.order.paid_at = payment.order.paid_at or now
        payment.order.save(update_fields=("status", "paid_at", "updated_at"))
        if attempt:
            attempt.status = PaymentAttempt.Status.COMPLETED
            attempt.provider_payment_id = provider_payment_id
            attempt.save(update_fields=("status", "provider_payment_id", "updated_at"))
        _confirm_or_flag_late_payment(payment)
        return True

    if payment.status in settled:
        return True
    if event_type == "checkout.session.completed" and payment_status == "unpaid":
        payment.status = Payment.Status.PROCESSING
        payment.save(update_fields=("status", "updated_at"))
        return True
    if event_type == "checkout.session.async_payment_failed":
        if attempt:
            attempt.status = PaymentAttempt.Status.FAILED
            attempt.safe_error = "Stripe reported that the payment did not complete."
            attempt.save(update_fields=("status", "safe_error", "updated_at"))
        payment.status = Payment.Status.FAILED
        payment.failure_code = "PAYMENT_FAILED"
        payment.failure_message = "Payment did not complete. You can try again while the reservation is active."
        payment.save(update_fields=("status", "failure_code", "failure_message", "updated_at"))
        return True
    if event_type == "checkout.session.expired":
        if attempt:
            attempt.status = PaymentAttempt.Status.EXPIRED
            attempt.safe_error = "Stripe checkout expired before payment completed."
            attempt.save(update_fields=("status", "safe_error", "updated_at"))
        payment.status = Payment.Status.CANCELLED
        payment.failure_code = "CHECKOUT_EXPIRED"
        payment.failure_message = "Checkout expired. Reserve another appointment time to try again."
        payment.save(update_fields=("status", "failure_code", "failure_message", "updated_at"))
        payment.order.status = Order.Status.EXPIRED
        payment.order.save(update_fields=("status", "updated_at"))
        _expire_appointment(payment.order.appointment, "Stripe checkout expired before payment completed.")
        return True
    return False


def _confirm_or_flag_late_payment(payment):
    appointment = payment.order.appointment
    if appointment.status == Appointment.Status.PAYMENT_PENDING:
        previous = appointment.status
        appointment.status = Appointment.Status.CONFIRMED
        appointment.reservation_expires_at = None
        appointment.save(update_fields=("status", "reservation_expires_at", "updated_at"))
        AppointmentStatusHistory.objects.create(
            appointment=appointment, from_status=previous, to_status=Appointment.Status.CONFIRMED,
            note="Confirmed by verified Stripe payment webhook.",
        )
        from apps.messaging.services import ensure_consultation_conversation
        from apps.notifications.services import notify_appointment_confirmed
        ensure_consultation_conversation(appointment)
        notify_appointment_confirmed(appointment)
        return
    if appointment.status != Appointment.Status.CONFIRMED:
        if not payment.refunds.exists():
            Refund.objects.create(
                payment=payment, amount=payment.amount, currency=payment.currency,
                reason="Payment completed after the appointment was no longer reservable; manual refund required.",
            )
        successful = sum(
            (item.amount for item in payment.refunds.filter(status=Refund.Status.SUCCEEDED)), Decimal("0"),
        )
        payment.status = Payment.Status.REFUNDED if successful >= payment.amount else Payment.Status.REFUND_PENDING
        payment.order.status = Order.Status.REFUNDED if successful >= payment.amount else Order.Status.REFUND_PENDING
        payment.save(update_fields=("status", "updated_at"))
        payment.order.save(update_fields=("status", "updated_at"))


def _process_stripe_refund(stripe_refund):
    payment_intent = stripe_refund.get("payment_intent")
    if isinstance(payment_intent, dict):
        payment_intent = payment_intent.get("id")
    provider_payment_id = str(payment_intent or "")
    if not provider_payment_id:
        return False
    try:
        payment = Payment.objects.select_for_update().select_related("order").get(
            provider="STRIPE", provider_payment_id=provider_payment_id,
        )
    except Payment.DoesNotExist:
        return False
    currency = str(stripe_refund.get("currency") or "").upper()
    amount_minor = stripe_refund.get("amount")
    if currency != payment.currency or not isinstance(amount_minor, int) or amount_minor <= 0:
        raise PaymentError({"event": ["Stripe refund amount or currency is invalid."]})
    amount = Decimal(amount_minor) / (1 if currency in _ZERO_DECIMAL_CURRENCIES else 100)
    if amount > payment.amount:
        raise PaymentError({"event": ["Stripe refund exceeds the original payment."]})
    provider_refund_id = str(stripe_refund.get("id") or "")
    if not provider_refund_id:
        raise PaymentError({"event": ["Stripe refund ID is missing."]})
    mapped_status = {
        "pending": Refund.Status.PROCESSING,
        "requires_action": Refund.Status.PROCESSING,
        "succeeded": Refund.Status.SUCCEEDED,
        "failed": Refund.Status.FAILED,
        "canceled": Refund.Status.FAILED,
    }.get(str(stripe_refund.get("status") or ""), Refund.Status.PROCESSING)
    refund = payment.refunds.filter(provider_refund_id=provider_refund_id).first()
    if not refund:
        refund = payment.refunds.filter(
            provider_refund_id="", status=Refund.Status.REQUESTED, amount=amount,
        ).first()
    if not refund:
        refund = Refund(payment=payment, amount=amount, currency=currency, reason="Refund recorded by Stripe.")
    refund.provider_refund_id = provider_refund_id
    refund.status = mapped_status
    refund.amount = amount
    refund.currency = currency
    refund.save()
    _refresh_refund_states(payment)
    return True


def _refresh_refund_states(payment):
    successful = sum(
        (item.amount for item in payment.refunds.filter(status=Refund.Status.SUCCEEDED)), Decimal("0"),
    )
    has_pending = payment.refunds.filter(
        status__in=(Refund.Status.REQUESTED, Refund.Status.PROCESSING),
    ).exists()
    if successful >= payment.amount:
        payment.status, payment.order.status = Payment.Status.REFUNDED, Order.Status.REFUNDED
    elif has_pending:
        payment.status, payment.order.status = Payment.Status.REFUND_PENDING, Order.Status.REFUND_PENDING
    elif successful > 0:
        payment.status, payment.order.status = Payment.Status.PARTIALLY_REFUNDED, Order.Status.PARTIALLY_REFUNDED
    else:
        payment.status, payment.order.status = Payment.Status.SUCCEEDED, Order.Status.PAID
    payment.save(update_fields=("status", "updated_at"))
    payment.order.save(update_fields=("status", "updated_at"))


def _validate_stripe_money(order, stripe_session):
    if (
        stripe_session.get("amount_total") != _minor_units(order.total_amount, order.currency)
        or str(stripe_session.get("currency") or "").upper() != order.currency
    ):
        raise PaymentError({"event": ["Stripe payment amount or currency does not match the order."]})


_ZERO_DECIMAL_CURRENCIES = {
    "BIF", "CLP", "DJF", "GNF", "JPY", "KMF", "KRW", "MGA", "PYG", "RWF", "UGX", "VND", "VUV", "XAF", "XOF", "XPF",
}


def _minor_units(amount: Decimal, currency: str):
    return int(amount * (1 if currency.upper() in _ZERO_DECIMAL_CURRENCIES else 100))


def _expire_appointment(appointment, note):
    if appointment.status != Appointment.Status.PAYMENT_PENDING:
        return
    previous = appointment.status
    appointment.status = Appointment.Status.EXPIRED
    appointment.reservation_expires_at = None
    appointment.save(update_fields=("status", "reservation_expires_at", "updated_at"))
    AppointmentStatusHistory.objects.create(
        appointment=appointment, from_status=previous, to_status=Appointment.Status.EXPIRED, note=note,
    )
