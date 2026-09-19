from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.accounts.services import create_device_session
from apps.consultations.models import ConsultationCase, ConsultationService

from ..models import CoachingPlan


class CoachingPlanApiTests(APITestCase):
    def setUp(self):
        self.client_user = User.objects.create_user("client@example.com", "HairDoc!2026Strong", first_name="Client", is_email_verified=True)
        self.tk = User.objects.create_user("tk@example.com", "HairDoc!2026Strong", is_staff=True, is_email_verified=True)
        self.other_staff = User.objects.create_user("other@example.com", "HairDoc!2026Strong", is_staff=True, is_email_verified=True)
        self.other_client = User.objects.create_user("other-client@example.com", "HairDoc!2026Strong", is_email_verified=True)
        self.service = ConsultationService.objects.create(name="Consultation", slug="consultation", short_description="Care", description="Care", duration_minutes=30, price_amount="0", currency="USD", status=ConsultationService.Status.PUBLISHED, published_at=timezone.now(), expert=self.tk)
        self.case = ConsultationCase.objects.create(client=self.client_user, service=self.service, status=ConsultationCase.Status.PHOTOS_COMPLETE, timezone_snapshot="UTC", service_name=self.service.name, duration_minutes=30, price_amount="0", currency="USD", intake_completed_at=timezone.now(), photos_completed_at=timezone.now())

    def authorize(self, user):
        access, _, _ = create_device_session(user, "Test device")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    def test_tk_drafts_updates_publishes_and_client_reads(self):
        self.authorize(self.tk)
        case_url = reverse("coaching:staff-case-plan-list", kwargs={"case_id": self.case.public_id})
        created = self.client.post(case_url, {"title": "Your scalp reset", "summary": "A focused first month."}, format="json")
        self.assertEqual(created.status_code, 201)
        plan_id = created.json()["public_id"]
        detail_url = reverse("coaching:staff-plan-detail", kwargs={"public_id": plan_id})
        payload = {"title": "Your scalp reset", "summary": "A focused first month.", "sections": [{"title": "First two weeks", "body": "Use the agreed routine three times weekly."}], "recommendations": [{"category": "ROUTINE", "title": "Wash routine", "guidance": "Keep water lukewarm.", "external_url": ""}]}
        self.assertEqual(self.client.patch(detail_url, payload, format="json").status_code, 200)

        self.authorize(self.client_user)
        self.assertEqual(self.client.get(reverse("coaching:client-plan-list")).json(), [])

        self.authorize(self.tk)
        published = self.client.post(reverse("coaching:staff-plan-publish", kwargs={"public_id": plan_id}), {}, format="json")
        self.assertEqual(published.status_code, 200)
        self.assertEqual(published.json()["status"], "PUBLISHED")
        self.assertEqual(self.client.patch(detail_url, payload, format="json").status_code, 400)

        self.authorize(self.client_user)
        plans = self.client.get(reverse("coaching:client-plan-list"))
        self.assertEqual(plans.status_code, 200)
        self.assertEqual(plans.json()[0]["sections"][0]["title"], "First two weeks")
        self.assertEqual(plans.json()[0]["recommendations"][0]["category_label"], "Routine")
        self.assertEqual(self.client.get(reverse("coaching:client-plan-detail", kwargs={"public_id": plan_id})).status_code, 200)

        self.authorize(self.other_client)
        self.assertEqual(self.client.get(reverse("coaching:client-plan-detail", kwargs={"public_id": plan_id})).status_code, 404)

    def test_only_assigned_expert_can_manage_case_plan(self):
        self.authorize(self.other_staff)
        url = reverse("coaching:staff-case-plan-list", kwargs={"case_id": self.case.public_id})
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.post(url, {"title": "No access"}, format="json").status_code, 404)

    def test_publish_requires_saved_guidance(self):
        self.authorize(self.tk)
        created = self.client.post(reverse("coaching:staff-case-plan-list", kwargs={"case_id": self.case.public_id}), {"title": "Draft"}, format="json")
        plan_id = created.json()["public_id"]
        response = self.client.post(reverse("coaching:staff-plan-publish", kwargs={"public_id": plan_id}), {}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(CoachingPlan.objects.get(public_id=plan_id).status, CoachingPlan.Status.DRAFT)
