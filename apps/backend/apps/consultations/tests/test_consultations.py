from datetime import timedelta

from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import ClientHairProfile, User
from apps.accounts.services import create_device_session
from apps.consultations.models import (
    ConsultationAnswer,
    ConsultationCase,
    ConsultationService,
    QuestionOption,
    Questionnaire,
    QuestionnaireQuestion,
)


class ConsultationApiTests(APITestCase):
    def setUp(self):
        now = timezone.now()
        self.service = ConsultationService.objects.create(
            name="Hair & Scalp Consultation",
            slug="hair-scalp-consultation",
            short_description="A focused review with TK.",
            description="Share your history before a private consultation.",
            duration_minutes=45,
            price_amount="85.00",
            currency="gbp",
            status=ConsultationService.Status.PUBLISHED,
            published_at=now,
        )
        self.questionnaire = Questionnaire.objects.create(
            service=self.service,
            version=1,
            title="Your hair story",
            introduction="Answer what you can; required items are marked.",
            status=Questionnaire.Status.PUBLISHED,
            published_at=now,
        )
        self.goal = QuestionnaireQuestion.objects.create(
            questionnaire=self.questionnaire,
            key="main-goal",
            section="Your goals",
            prompt="What would you most like help with?",
            type=QuestionnaireQuestion.Type.LONG_TEXT,
            required=True,
            max_length=500,
            display_order=1,
        )
        self.shedding = QuestionnaireQuestion.objects.create(
            questionnaire=self.questionnaire,
            key="shedding",
            section="Hair history",
            prompt="Are you noticing shedding?",
            type=QuestionnaireQuestion.Type.BOOLEAN,
            display_order=2,
        )
        self.pattern = QuestionnaireQuestion.objects.create(
            questionnaire=self.questionnaire,
            key="pattern",
            section="Hair history",
            prompt="Which pattern best matches?",
            type=QuestionnaireQuestion.Type.SINGLE_CHOICE,
            required=True,
            show_if_question_key="shedding",
            show_if_value="true",
            display_order=3,
        )
        QuestionOption.objects.create(question=self.pattern, value="diffuse", label="All over")
        QuestionOption.objects.create(question=self.pattern, value="patchy", label="In patches", display_order=2)

        ConsultationService.objects.create(
            name="Draft service", slug="draft-service", short_description="Not ready.", description="Not ready.",
            duration_minutes=30, price_amount="50.00",
        )
        ConsultationService.objects.create(
            name="Future service", slug="future-service", short_description="Not yet available.",
            description="Not yet available.", duration_minutes=30, price_amount="50.00",
            status=ConsultationService.Status.PUBLISHED, published_at=now + timedelta(days=1),
        )

        self.user = User.objects.create_user("client@example.com", "HairDoc!2026Strong", is_email_verified=True)
        ClientHairProfile.objects.create(
            user=self.user, hair_texture=ClientHairProfile.Texture.CURLY, goals="More comfortable scalp",
        )
        self.authorize(self.user, "Test phone")

    def authorize(self, user, device_name):
        access, _, _ = create_device_session(user, device_name)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    def start(self):
        return self.client.post(
            reverse("consultations:case-list-start"),
            {"service_public_id": str(self.service.public_id), "timezone": "Europe/London"},
            format="json",
        )

    def test_catalogue_requires_auth_and_only_lists_current_published_services(self):
        self.client.credentials()
        response = self.client.get(reverse("consultations:service-list"))
        self.assertEqual(response.status_code, 401)
        detail = self.client.get(reverse("consultations:service-detail", kwargs={"public_id": self.service.public_id}))
        self.assertEqual(detail.status_code, 401)
        self.authorize(self.user, "Catalogue test")
        response = self.client.get(reverse("consultations:service-list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["public_id"] for item in response.json()], [str(self.service.public_id)])
        detail = self.client.get(reverse("consultations:service-detail", kwargs={"public_id": self.service.public_id}))
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["currency"], "GBP")

    def test_start_requires_auth_is_idempotent_and_locks_snapshots(self):
        self.client.credentials()
        self.assertEqual(self.start().status_code, 401)
        self.authorize(self.user, "Second phone")
        started = self.start()
        self.assertEqual(started.status_code, 201)
        repeated = self.start()
        self.assertEqual(repeated.status_code, 200)
        self.assertEqual(repeated.json()["public_id"], started.json()["public_id"])
        case = ConsultationCase.objects.get()
        self.assertEqual(case.response.questionnaire, self.questionnaire)
        self.assertEqual(case.hair_profile_snapshot["hair_texture"], "CURLY")
        self.assertEqual(case.timezone_snapshot, "Europe/London")
        self.assertEqual(str(case.price_amount), "85.00")

        Questionnaire.objects.create(
            service=self.service, version=2, title="A newer intake",
            status=Questionnaire.Status.PUBLISHED, published_at=timezone.now() + timedelta(seconds=1),
        )
        self.assertEqual(case.response.questionnaire.version, 1)

    def test_answers_are_typed_user_scoped_and_locked_after_completion(self):
        case_id = self.start().json()["public_id"]
        answers_url = reverse("consultations:answers", kwargs={"public_id": case_id})
        invalid = self.client.patch(
            answers_url, {"answers": [{"question_key": "shedding", "value": "yes"}]}, format="json",
        )
        self.assertEqual(invalid.status_code, 400)
        saved = self.client.patch(
            answers_url,
            {"answers": [
                {"question_key": "main-goal", "value": "Understand my recent changes."},
                {"question_key": "shedding", "value": True},
                {"question_key": "pattern", "value": "diffuse"},
            ]},
            format="json",
        )
        self.assertEqual(saved.status_code, 200)
        self.assertEqual(saved.json()["answers"]["pattern"], "diffuse")

        other = User.objects.create_user("other@example.com", "HairDoc!2026Strong", is_email_verified=True)
        self.authorize(other, "Other phone")
        self.assertEqual(self.client.get(answers_url).status_code, 404)

        self.authorize(self.user, "Third phone")
        submitted = self.client.post(reverse("consultations:submit", kwargs={"public_id": case_id}), {}, format="json")
        self.assertEqual(submitted.status_code, 200)
        self.assertEqual(submitted.json()["status"], ConsultationCase.Status.INTAKE_COMPLETE)
        changed = self.client.patch(
            answers_url, {"answers": [{"question_key": "main-goal", "value": "Changed"}]}, format="json",
        )
        self.assertEqual(changed.status_code, 400)

    def test_required_visible_answers_are_checked_on_completion(self):
        case_id = self.start().json()["public_id"]
        submit_url = reverse("consultations:submit", kwargs={"public_id": case_id})
        missing = self.client.post(submit_url, {}, format="json")
        self.assertEqual(missing.status_code, 400)
        details = missing.json()["error"]["details"]["answers"]
        self.assertIn("main-goal", details)
        self.assertNotIn("pattern", details)

        self.client.patch(
            reverse("consultations:answers", kwargs={"public_id": case_id}),
            {"answers": [{"question_key": "main-goal", "value": "A clear routine."}]}, format="json",
        )
        self.assertEqual(self.client.post(submit_url, {}, format="json").status_code, 200)

    def test_questionnaire_content_is_immutable_once_used(self):
        self.start()
        self.goal.prompt = "Changed prompt"
        with self.assertRaises(ValidationError):
            self.goal.save()
        self.goal.refresh_from_db()
        other = Questionnaire.objects.create(service=self.service, version=2, title="Draft replacement")
        self.goal.questionnaire = other
        with self.assertRaises(ValidationError):
            self.goal.save()
        option = self.pattern.options.first()
        option.label = "Changed option"
        with self.assertRaises(ValidationError):
            option.save()
        self.assertEqual(ConsultationAnswer.objects.count(), 0)
