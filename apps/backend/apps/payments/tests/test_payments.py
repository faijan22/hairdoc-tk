from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.accounts.services import create_device_session
from apps.consultations.models import Appointment, AppointmentStatusHistory, ConsultationCase, ConsultationService
from apps.payments.models import Order, Payment, Refund, WebhookEvent
from apps.payments.providers.base import CheckoutSession
from apps.messaging.models import Conversation


class FakeStripeProvider:
    code = "STRIPE"

    def create_checkout(self, **kwargs):
        return CheckoutSession(
            session_id="cs_test_hairdoc",
            order_id="cs_test_hairdoc",
            url="https://checkout.stripe.com/c/pay/hairdoc-test",
            expires_at=timezone.now() + timedelta(minutes=31),
        )


class PaymentApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("client@example.com", "HairDoc!2026Strong", is_email_verified=True)
        self.other = User.objects.create_user("other@example.com", "HairDoc!2026Strong", is_email_verified=True)
        self.tk = User.objects.create_user("tk@example.com", "HairDoc!2026Strong", is_staff=True, is_email_verified=True)
        self.service = ConsultationService.objects.create(
            name="Private consultation", slug="private-payment", short_description="Review with TK.",
            description="Review with TK.", duration_minutes=45, price_amount="80.00", currency="GBP",
            status=ConsultationService.Status.PUBLISHED, published_at=timezone.now(), expert=self.tk,
        )
        self.case = ConsultationCase.objects.create(
            client=self.user, service=self.service, status=ConsultationCase.Status.PHOTOS_COMPLETE,
            timezone_snapshot="Europe/London", service_name=self.service.name, duration_minutes=45,
            price_amount="80.00", currency="GBP", intake_completed_at=timezone.now(), photos_completed_at=timezone.now(),
        )
        self.appointment = Appointment.objects.create(
            case=self.case, client=self.user, expert=self.tk,
            starts_at=timezone.now() + timedelta(days=4), ends_at=timezone.now() + timedelta(days=4, minutes=45),
            status=Appointment.Status.PAYMENT_PENDING, client_timezone="Europe/London", expert_timezone="Europe/London",
            reservation_expires_at=timezone.now() + timedelta(minutes=30),
        )
        self.authorize(self.user)

    def authorize(self, user):
        access, _, _ = create_device_session(user, "Payment test")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    def create_order(self):
        return self.client.post(
            reverse("payments:order-create"),
            {"appointment_public_id": str(self.appointment.public_id), "total_amount": "0.01", "currency": "USD"},
            format="json",
        )

    def checkout(self, order):
        with patch("apps.payments.services.get_payment_provider", return_value=FakeStripeProvider()):
            return self.client.post(reverse("payments:order-checkout", kwargs={"public_id": order.public_id}))

    def stripe_event(
        self, event_id="evt_paid", *, amount=8000, payment_status="paid",
        event_type="checkout.session.completed",
    ):
        payment = Payment.objects.get(order__appointment=self.appointment)
        return {
            "id": event_id,
            "type": event_type,
            "data": {"object": {
                "id": payment.provider_checkout_session_id,
                "client_reference_id": str(payment.order.public_id),
                "metadata": {"hairdoc_order_id": str(payment.order.public_id)},
                "payment_intent": "pi_hairdoc",
                "amount_total": amount,
                "currency": "gbp",
                "payment_status": payment_status,
            }},
        }

    def post_event(self, event):
        with patch("apps.payments.services.get_payment_provider") as provider:
            provider.return_value.code = "STRIPE"
            provider.return_value.parse_webhook.return_value = event
            return self.client.post(
                reverse("payments:stripe-webhook"), data=b"{}", content_type="application/json",
                HTTP_STRIPE_SIGNATURE="test-signature",
            )

    def test_stripe_webhook_readiness_is_public_but_processing_stays_signed(self):
        readiness = self.client.get(reverse("payments:stripe-webhook"))
        self.assertEqual(readiness.status_code, 200)
        self.assertEqual(readiness.json(), {"status": "ready", "provider": "stripe"})
        unsigned = self.client.post(
            reverse("payments:stripe-webhook"), data=b"{}", content_type="application/json",
        )
        self.assertEqual(unsigned.status_code, 400)

    def test_order_is_user_scoped_server_priced_and_idempotent(self):
        response = self.create_order()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["total_amount"], "80.00")
        self.assertEqual(response.json()["currency"], "GBP")
        self.assertEqual(self.create_order().status_code, 200)
        self.assertEqual(Order.objects.count(), 1)

        self.authorize(self.other)
        hidden = self.client.post(
            reverse("payments:order-create"), {"appointment_public_id": str(self.appointment.public_id)}, format="json",
        )
        self.assertEqual(hidden.status_code, 404)

    def test_checkout_is_reused_and_missing_configuration_is_honest(self):
        order = Order.objects.get(public_id=self.create_order().json()["public_id"])
        first = self.checkout(order)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()["checkout_url"], "https://checkout.stripe.com/c/pay/hairdoc-test")
        self.assertEqual(self.checkout(order).json()["payment"]["public_id"], first.json()["payment"]["public_id"])
        self.assertEqual(Payment.objects.get(order=order).attempts.count(), 1)

        Payment.objects.get(order=order).attempts.update(status="EXPIRED")
        with self.settings(STRIPE_SECRET_KEY=""):
            missing = self.client.post(reverse("payments:order-checkout", kwargs={"public_id": order.public_id}))
        self.assertEqual(missing.status_code, 503)
        self.assertNotEqual(Payment.objects.get(order=order).status, Payment.Status.SUCCEEDED)

    def test_verified_paid_webhook_confirms_once_and_history_is_scoped(self):
        order = Order.objects.get(public_id=self.create_order().json()["public_id"])
        payment_id = self.checkout(order).json()["payment"]["public_id"]
        event = self.stripe_event()
        self.assertEqual(self.post_event(event).status_code, 200)
        self.assertEqual(self.post_event(event).status_code, 200)

        self.appointment.refresh_from_db()
        payment = Payment.objects.get(public_id=payment_id)
        self.assertEqual(self.appointment.status, Appointment.Status.CONFIRMED)
        self.assertEqual(payment.status, Payment.Status.SUCCEEDED)
        self.assertEqual(payment.provider_payment_id, "pi_hairdoc")
        self.assertEqual(AppointmentStatusHistory.objects.filter(to_status=Appointment.Status.CONFIRMED).count(), 1)
        self.assertEqual(WebhookEvent.objects.count(), 1)
        self.assertEqual(Conversation.objects.get(consultation=self.case).members.count(), 2)
        self.assertEqual(self.client.get(reverse("payments:payment-list")).json()[0]["receipt_number"][:5], "HDTK-")

        self.authorize(self.other)
        self.assertEqual(self.client.get(reverse("payments:payment-list")).json(), [])
        self.assertEqual(self.client.get(reverse("payments:payment-detail", kwargs={"public_id": payment_id})).status_code, 404)

        self.authorize(self.tk)
        staff_list = self.client.get(reverse("payments:staff-payment-list"))
        self.assertEqual(staff_list.status_code, 200)
        self.assertEqual(staff_list.json()[0]["client_email"], self.user.email)
        self.assertEqual(
            self.client.get(reverse("payments:staff-payment-detail", kwargs={"public_id": payment_id})).status_code,
            200,
        )

        unrelated_staff = User.objects.create_user(
            "unrelated-staff@example.com", "HairDoc!2026Strong", is_staff=True, is_email_verified=True,
        )
        self.authorize(unrelated_staff)
        self.assertEqual(self.client.get(reverse("payments:staff-payment-list")).json(), [])
        self.assertEqual(
            self.client.get(reverse("payments:staff-payment-detail", kwargs={"public_id": payment_id})).status_code,
            404,
        )

    def test_wrong_total_cannot_confirm_and_failed_event_is_recorded(self):
        order = Order.objects.get(public_id=self.create_order().json()["public_id"])
        self.checkout(order)
        response = self.post_event(self.stripe_event(event_id="evt_wrong", amount=1))
        self.assertEqual(response.status_code, 400)
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, Appointment.Status.PAYMENT_PENDING)
        self.assertNotEqual(Payment.objects.get(order=order).status, Payment.Status.SUCCEEDED)
        self.assertEqual(WebhookEvent.objects.get(provider_event_id="evt_wrong").status, WebhookEvent.Status.FAILED)

    def test_verified_unrelated_stripe_events_are_acknowledged_and_ignored(self):
        payment_event = {
            "id": "evt_unrelated_payment",
            "type": "checkout.session.completed",
            "data": {"object": {
                "id": "cs_test_other", "client_reference_id": "other",
                "metadata": {"hairdoc_order_id": "other"}, "payment_intent": "pi_other",
                "amount_total": 100, "currency": "gbp", "payment_status": "paid",
            }},
        }
        refund_event = {
            "id": "evt_unrelated_refund",
            "type": "refund.updated",
            "data": {"object": {
                "id": "re_other", "payment_intent": "pi_other",
                "amount": 100, "currency": "gbp", "status": "succeeded",
            }},
        }

        self.assertEqual(self.post_event(payment_event).status_code, 200)
        self.assertEqual(self.post_event(refund_event).status_code, 200)
        self.assertEqual(
            set(WebhookEvent.objects.values_list("status", flat=True)),
            {WebhookEvent.Status.IGNORED},
        )

    def test_late_payment_requests_refund_instead_of_confirming_cancelled_slot(self):
        order = Order.objects.get(public_id=self.create_order().json()["public_id"])
        self.checkout(order)
        self.appointment.status = Appointment.Status.CANCELLED
        self.appointment.cancelled_at = timezone.now()
        self.appointment.save(update_fields=("status", "cancelled_at", "updated_at"))
        self.assertEqual(self.post_event(self.stripe_event(event_id="evt_late")).status_code, 200)
        self.appointment.refresh_from_db()
        payment = Payment.objects.get(order=order)
        self.assertEqual(self.appointment.status, Appointment.Status.CANCELLED)
        self.assertEqual(payment.status, Payment.Status.REFUND_PENDING)
        self.assertEqual(Refund.objects.get(payment=payment).amount, Decimal("80.00"))

    def test_expired_checkout_releases_the_unpaid_slot(self):
        order = Order.objects.get(public_id=self.create_order().json()["public_id"])
        self.checkout(order)
        event = self.stripe_event(
            event_id="evt_expired", payment_status="unpaid", event_type="checkout.session.expired",
        )
        self.assertEqual(self.post_event(event).status_code, 200)

        self.appointment.refresh_from_db()
        order.refresh_from_db()
        payment = Payment.objects.get(order=order)
        self.assertEqual(self.appointment.status, Appointment.Status.EXPIRED)
        self.assertEqual(order.status, Order.Status.EXPIRED)
        self.assertEqual(payment.status, Payment.Status.CANCELLED)

    def test_stripe_refund_webhook_updates_client_visible_state(self):
        order = Order.objects.get(public_id=self.create_order().json()["public_id"])
        self.checkout(order)
        self.assertEqual(self.post_event(self.stripe_event(event_id="evt_for_refund")).status_code, 200)
        refund_event = {
            "id": "evt_refund",
            "type": "refund.created",
            "data": {"object": {
                "id": "re_hairdoc", "payment_intent": "pi_hairdoc",
                "amount": 8000, "currency": "gbp", "status": "succeeded",
            }},
        }
        self.assertEqual(self.post_event(refund_event).status_code, 200)
        payment = Payment.objects.get(order=order)
        order.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.REFUNDED)
        self.assertEqual(order.status, Order.Status.REFUNDED)
        self.assertEqual(Refund.objects.get(payment=payment).provider_refund_id, "re_hairdoc")
