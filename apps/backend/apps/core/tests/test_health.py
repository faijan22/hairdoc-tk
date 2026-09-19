from django.test import TestCase
from django.urls import reverse


class HealthViewTests(TestCase):
    def test_health_response_and_request_id(self):
        response = self.client.get(reverse("core:health"), HTTP_X_REQUEST_ID="test-request")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "status": "ok",
                "service": "hairdoc-tk-api",
                "api_version": "v1",
            },
        )
        self.assertEqual(response.headers["X-Request-ID"], "test-request")

