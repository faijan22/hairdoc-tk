import base64
import hashlib
import hmac
import json

from django.test import SimpleTestCase, override_settings

from apps.payments.providers.square import SquarePaymentProvider


@override_settings(
    SQUARE_ACCESS_TOKEN="sandbox-token",
    SQUARE_LOCATION_ID="sandbox-location",
    SQUARE_ENVIRONMENT="sandbox",
    SQUARE_WEBHOOK_SIGNATURE_KEY="signature-key",
    SQUARE_WEBHOOK_NOTIFICATION_URL="https://api.example.com/api/v1/integrations/square/webhook/",
)
class SquareProviderTests(SimpleTestCase):
    def test_webhook_signature_uses_raw_body_and_exact_notification_url(self):
        payload = json.dumps({"event_id": "event-1", "type": "payment.updated"}).encode()
        signature = base64.b64encode(
            hmac.new(
                b"signature-key",
                b"https://api.example.com/api/v1/integrations/square/webhook/" + payload,
                hashlib.sha256,
            ).digest(),
        ).decode()

        self.assertEqual(SquarePaymentProvider().parse_webhook(payload, signature)["event_id"], "event-1")
        with self.assertRaises(ValueError):
            SquarePaymentProvider().parse_webhook(payload, "invalid")
