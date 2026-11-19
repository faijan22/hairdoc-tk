import json
from unittest.mock import MagicMock, patch
from urllib.error import URLError

from django.core.mail import EmailMultiAlternatives
from django.test import SimpleTestCase, override_settings

from apps.core.email_backends import ElasticEmailAPIError, ElasticEmailBackend


@override_settings(
    ELASTIC_EMAIL_API_KEY="test-api-key",
    ELASTIC_EMAIL_API_BASE_URL="https://api.elasticemail.com/v4",
    DEFAULT_FROM_EMAIL="HairDoc TK <verified@hairdoctk.com>",
    EMAIL_TIMEOUT=10,
)
class ElasticEmailBackendTests(SimpleTestCase):
    @patch("apps.core.email_backends.urlopen")
    def test_sends_transactional_email_with_api_key_and_idempotency(self, urlopen):
        response = MagicMock()
        response.read.return_value = b'{"TransactionID":"transaction-1","MessageID":"message-1"}'
        urlopen.return_value.__enter__.return_value = response
        message = EmailMultiAlternatives(
            subject="Verify your email",
            body="Plain text",
            to=["person@example.com"],
            headers={"Idempotency-Key": "email-action-123"},
        )
        message.attach_alternative("<p>HTML</p>", "text/html")

        self.assertEqual(ElasticEmailBackend().send_messages([message]), 1)

        request = urlopen.call_args.args[0]
        headers = {key.lower(): value for key, value in request.header_items()}
        payload = json.loads(request.data)
        self.assertEqual(request.full_url, "https://api.elasticemail.com/v4/emails/transactional")
        self.assertEqual(headers["x-elasticemail-apikey"], "test-api-key")
        self.assertEqual(headers["idempotency-key"], "email-action-123")
        self.assertEqual(payload["Recipients"]["To"], ["person@example.com"])
        self.assertEqual(payload["Content"]["From"], "verified@hairdoctk.com")
        self.assertEqual(payload["Content"]["FromName"], "HairDoc TK")
        self.assertEqual(
            [part["ContentType"] for part in payload["Content"]["Body"]],
            ["PlainText", "HTML"],
        )
        self.assertEqual(urlopen.call_args.kwargs["timeout"], 10)

    @patch("apps.core.email_backends.urlopen", side_effect=URLError("offline"))
    def test_fail_silently_returns_zero(self, _urlopen):
        message = EmailMultiAlternatives(subject="Test", body="Body", to=["person@example.com"])
        self.assertEqual(ElasticEmailBackend(fail_silently=True).send_messages([message]), 0)

    @override_settings(ELASTIC_EMAIL_API_KEY="")
    def test_missing_api_key_fails_closed(self):
        message = EmailMultiAlternatives(subject="Test", body="Body", to=["person@example.com"])
        with self.assertRaises(ElasticEmailAPIError):
            ElasticEmailBackend().send_messages([message])
