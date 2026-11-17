import hashlib
import hmac
import json
import time
from decimal import Decimal
from types import SimpleNamespace
from urllib.parse import parse_qs
from unittest.mock import Mock, patch

from django.test import SimpleTestCase, override_settings

from apps.payments.providers.base import PaymentProviderConfigurationError
from apps.payments.providers.stripe import StripePaymentProvider, _minor_units


@override_settings(
    STRIPE_ENVIRONMENT="test",
    STRIPE_SECRET_KEY="sk_test_hairdoc",
    STRIPE_WEBHOOK_SECRET="whsec_hairdoc",
    STRIPE_API_BASE_URL="https://api.stripe.com",
    STRIPE_API_VERSION="2026-02-25.clover",
    STRIPE_WEBHOOK_TOLERANCE_SECONDS=300,
)
class StripeProviderTests(SimpleTestCase):
    def test_webhook_signature_is_verified_over_raw_body(self):
        payload = json.dumps({
            "id": "evt_1", "type": "checkout.session.completed", "livemode": False,
        }).encode()
        timestamp = int(time.time())
        digest = hmac.new(
            b"whsec_hairdoc", f"{timestamp}.".encode() + payload, hashlib.sha256,
        ).hexdigest()
        signature = f"t={timestamp},v1={digest}"

        self.assertEqual(StripePaymentProvider().parse_webhook(payload, signature)["id"], "evt_1")
        with self.assertRaises(ValueError):
            StripePaymentProvider().parse_webhook(payload, f"t={timestamp},v1=invalid")

    def test_stale_webhook_signature_is_rejected(self):
        payload = b"{}"
        timestamp = int(time.time()) - 301
        digest = hmac.new(
            b"whsec_hairdoc", f"{timestamp}.".encode() + payload, hashlib.sha256,
        ).hexdigest()
        with self.assertRaises(ValueError):
            StripePaymentProvider().parse_webhook(payload, f"t={timestamp},v1={digest}")

    def test_webhook_mode_must_match_environment(self):
        payload = json.dumps({"id": "evt_live", "type": "checkout.session.completed", "livemode": True}).encode()
        timestamp = int(time.time())
        digest = hmac.new(
            b"whsec_hairdoc", f"{timestamp}.".encode() + payload, hashlib.sha256,
        ).hexdigest()
        with self.assertRaises(ValueError):
            StripePaymentProvider().parse_webhook(payload, f"t={timestamp},v1={digest}")

    def test_environment_rejects_wrong_key_mode(self):
        with self.settings(STRIPE_SECRET_KEY="sk_live_wrong_mode"):
            with self.assertRaises(PaymentProviderConfigurationError):
                StripePaymentProvider()._ensure_checkout_configured()

    @patch("apps.payments.providers.stripe.urlopen")
    def test_checkout_is_server_priced_and_idempotent(self, open_url):
        response = Mock()
        response.read.return_value = json.dumps({
            "id": "cs_test_hairdoc",
            "url": "https://checkout.stripe.com/c/pay/hairdoc",
            "expires_at": int(time.time()) + 1860,
        }).encode()
        open_url.return_value.__enter__.return_value = response
        item = SimpleNamespace(description="Private consultation", quantity=1, unit_amount=Decimal("80.00"))
        order = SimpleNamespace(
            public_id="0f4250d7-96c0-4a57-acb5-e069ec95b84a",
            currency="GBP",
            user=SimpleNamespace(email="client@example.com"),
            items=SimpleNamespace(get=Mock(return_value=item)),
        )
        session = StripePaymentProvider().create_checkout(
            order=order,
            attempt=SimpleNamespace(idempotency_key="checkout-test-key"),
            return_base_url="https://api.example.com/api/v1/payments/return",
        )

        request = open_url.call_args.args[0]
        fields = parse_qs(request.data.decode())
        self.assertEqual(session.session_id, "cs_test_hairdoc")
        self.assertEqual(request.headers["Idempotency-key"], "checkout-test-key")
        self.assertEqual(fields["line_items[0][price_data][unit_amount]"], ["8000"])
        self.assertEqual(fields["line_items[0][price_data][currency]"], ["gbp"])
        self.assertEqual(fields["client_reference_id"], [str(order.public_id)])
        self.assertEqual(fields["metadata[hairdoc_order_id]"], [str(order.public_id)])
        self.assertEqual(fields["payment_intent_data[capture_method]"], ["automatic"])
        with self.settings(STRIPE_ENVIRONMENT="production", STRIPE_SECRET_KEY="sk_test_wrong_mode"):
            with self.assertRaises(PaymentProviderConfigurationError):
                StripePaymentProvider()._ensure_checkout_configured()

    def test_minor_units_are_exact(self):
        self.assertEqual(_minor_units(Decimal("80.00"), "GBP"), 8000)
        self.assertEqual(_minor_units(Decimal("800"), "JPY"), 800)
        with self.assertRaises(PaymentProviderConfigurationError):
            _minor_units(Decimal("1.005"), "GBP")
