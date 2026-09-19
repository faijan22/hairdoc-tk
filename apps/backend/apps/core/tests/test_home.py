from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.accounts.services import create_device_session
from apps.consultations.models import (
    Appointment,
    ConsultationCase,
    ConsultationResponse,
    ConsultationService,
    Questionnaire,
)
from apps.content.models import ContentItem


class HomeViewTests(APITestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(
            "client@example.com", "HairDoc!2026Strong", first_name="Client", is_email_verified=True,
        )
        self.other_user = User.objects.create_user(
            "other@example.com", "HairDoc!2026Strong", is_email_verified=True,
        )
        self.tk = User.objects.create_user(
            "tk@example.com", "HairDoc!2026Strong", first_name="TK", is_email_verified=True, is_staff=True,
        )
        self.service = ConsultationService.objects.create(
            name="Private hair consultation", slug="private-hair-consultation",
            short_description="Discuss your hair concerns with TK.", description="Private guidance.",
            duration_minutes=45, price_amount="80", currency="GBP",
            status=ConsultationService.Status.PUBLISHED, published_at=timezone.now(), expert=self.tk,
        )
        ConsultationService.objects.create(
            name="Draft service", slug="draft-service", short_description="Hidden.", description="Hidden.",
            duration_minutes=30, price_amount="50", currency="GBP",
        )
        self.questionnaire = Questionnaire.objects.create(
            service=self.service, version=1, title="Hair consultation intake",
            status=Questionnaire.Status.PUBLISHED, published_at=timezone.now(),
        )
        self.case = self.make_case(self.client_user)
        self.make_case(self.other_user)
        self.content = ContentItem.objects.create(
            type=ContentItem.Type.TEDX, title="TK's published talk", slug="tk-published-talk",
            summary="A published resource.", status=ContentItem.Status.PUBLISHED, published_at=timezone.now(),
        )
        ContentItem.objects.create(
            type=ContentItem.Type.ARTICLE, title="Draft article", slug="draft-article",
            summary="Hidden.", status=ContentItem.Status.DRAFT,
        )

    def make_case(self, user):
        case = ConsultationCase.objects.create(
            client=user, service=self.service, timezone_snapshot="Europe/London",
            service_name=self.service.name, duration_minutes=self.service.duration_minutes,
            price_amount=self.service.price_amount, currency=self.service.currency,
        )
        ConsultationResponse.objects.create(case=case, questionnaire=self.questionnaire)
        return case

    def authorize(self):
        access, _, _ = create_device_session(self.client_user, "Home test")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    def test_anonymous_home_contains_public_content_but_no_services(self):
        response = self.client.get(reverse("core:home"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["services"], [])
        self.assertEqual([item["public_id"] for item in response.json()["content"]], [str(self.content.public_id)])
        self.assertIsNone(response.json()["active_consultation"])
        self.assertIsNone(response.json()["next_appointment"])

    def test_authenticated_home_is_user_scoped_and_expires_stale_hold(self):
        now = timezone.now()
        expired = Appointment.objects.create(
            case=self.case, client=self.client_user, expert=self.tk,
            starts_at=now + timedelta(hours=1), ends_at=now + timedelta(hours=2),
            status=Appointment.Status.PAYMENT_PENDING, client_timezone="Europe/London",
            expert_timezone="Europe/London", reservation_expires_at=now - timedelta(minutes=1),
        )
        self.authorize()

        response = self.client.get(reverse("core:home"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["active_consultation"]["public_id"], str(self.case.public_id))
        self.assertIsNone(response.json()["next_appointment"])
        expired.refresh_from_db()
        self.assertEqual(expired.status, Appointment.Status.EXPIRED)
