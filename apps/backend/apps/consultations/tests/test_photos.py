import io
import shutil
import tempfile
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image
from rest_framework.test import APITestCase

from apps.accounts.models import LegalDocument, User, UserConsent
from apps.accounts.services import create_device_session
from apps.consultations.models import (
    ConsultationAnswer,
    ConsultationCase,
    ConsultationPhoto,
    ConsultationPhotoAccess,
    ConsultationResponse,
    ConsultationService,
    Questionnaire,
    QuestionnaireQuestion,
    QuestionOption,
)


class ConsultationPhotoApiTests(APITestCase):
    def setUp(self):
        self.private_root = tempfile.mkdtemp(prefix="hairdoc-private-media-")
        self.settings_override = override_settings(
            PRIVATE_MEDIA_ROOT=self.private_root,
            PHOTO_CONSENT_REQUIRED=True,
        )
        self.settings_override.enable()
        now = timezone.now()
        self.user = User.objects.create_user(
            "client@example.com", "HairDoc!2026Strong", first_name="Client", is_email_verified=True,
        )
        self.staff = User.objects.create_user(
            "tk@example.com", "HairDoc!2026Strong", is_email_verified=True, is_staff=True,
        )
        self.service = ConsultationService.objects.create(
            name="Photo consultation", slug="photo-consultation", short_description="Private review.",
            description="Private review.", duration_minutes=45, price_amount="80", currency="GBP",
            status=ConsultationService.Status.PUBLISHED, published_at=now, expert=self.staff,
        )
        questionnaire = Questionnaire.objects.create(
            service=self.service, version=1, title="Intake", status=Questionnaire.Status.PUBLISHED, published_at=now,
        )
        self.goal_question = QuestionnaireQuestion.objects.create(
            questionnaire=questionnaire, key="goal", section="Goals", prompt="What is your goal?",
            type=QuestionnaireQuestion.Type.SINGLE_CHOICE,
        )
        QuestionOption.objects.create(
            question=self.goal_question, value="hair_health", label="Improve overall hair health",
        )
        self.case = ConsultationCase.objects.create(
            client=self.user, service=self.service, status=ConsultationCase.Status.INTAKE_COMPLETE,
            timezone_snapshot="Europe/London", hair_profile_snapshot={"goals": "Healthy scalp"},
            service_name=self.service.name, duration_minutes=45, price_amount="80", currency="GBP",
            intake_completed_at=now,
        )
        self.response = ConsultationResponse.objects.create(case=self.case, questionnaire=questionnaire)
        ConsultationAnswer.objects.create(
            response=self.response, question=self.goal_question, value="hair_health",
        )
        self.document = LegalDocument.objects.create(
            type=LegalDocument.Type.PHOTO_DATA_CONSENT, version=1, title="Private photo consent",
            body="Owner-approved test policy.", status=LegalDocument.Status.PUBLISHED, published_at=now,
        )
        self.authorize(self.user)

    def tearDown(self):
        self.settings_override.disable()
        shutil.rmtree(self.private_root, ignore_errors=True)

    def authorize(self, user):
        access, _, _ = create_device_session(user, "Test device")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    def accept_consent(self):
        return UserConsent.objects.create(
            user=self.user, legal_document=self.document, accepted_at=timezone.now(),
        )

    def image(self, name="photo.png", size=(900, 700)):
        content = io.BytesIO()
        Image.new("RGB", size, "#806451").save(content, format="PNG")
        return SimpleUploadedFile(name, content.getvalue(), content_type="image/png")

    @property
    def photos_url(self):
        return reverse("consultations:photos", kwargs={"public_id": self.case.public_id})

    def upload(self):
        return self.client.post(
            self.photos_url, {"file": self.image(), "category": "TOP"}, format="multipart",
        )

    def test_upload_requires_exact_current_consent_and_completed_intake(self):
        missing = self.upload()
        self.assertEqual(missing.status_code, 400)
        self.assertFalse(ConsultationPhoto.objects.exists())

        consent = self.accept_consent()
        uploaded = self.upload()
        self.assertEqual(uploaded.status_code, 201)
        self.assertEqual(uploaded.json()["photos"][0]["category"], "TOP")
        photo = ConsultationPhoto.objects.select_related("stored_file").get()
        self.assertEqual(photo.consent_document, self.document)
        self.assertEqual(photo.consent_accepted_at, consent.accepted_at)
        self.assertEqual(photo.stored_file.content_type, "image/jpeg")
        self.assertTrue((Path(self.private_root) / photo.stored_file.storage_key).exists())

        newer = LegalDocument.objects.create(
            type=LegalDocument.Type.PHOTO_DATA_CONSENT, version=2, title="Updated consent", body="Updated.",
            status=LegalDocument.Status.PUBLISHED, published_at=timezone.now(),
        )
        overview = self.client.get(self.photos_url)
        self.assertFalse(overview.json()["consent"]["accepted"])
        self.assertEqual(overview.json()["consent"]["document_public_id"], str(newer.public_id))
        self.assertEqual(self.upload().status_code, 400)

        self.case.status = ConsultationCase.Status.DRAFT
        self.case.save(update_fields=("status", "updated_at"))
        UserConsent.objects.create(user=self.user, legal_document=newer, accepted_at=timezone.now())
        self.assertEqual(self.upload().status_code, 400)

    def test_image_validation_private_read_and_delete(self):
        self.accept_consent()
        invalid = SimpleUploadedFile("fake.jpg", b"not an image", content_type="image/jpeg")
        response = self.client.post(self.photos_url, {"file": invalid, "category": "FRONT"}, format="multipart")
        self.assertEqual(response.status_code, 400)

        uploaded = self.upload().json()
        photo_data = uploaded["photos"][0]
        photo = ConsultationPhoto.objects.select_related("stored_file").get()
        stored_path = Path(self.private_root) / photo.stored_file.storage_key
        content = self.client.get(photo_data["content_path"])
        self.assertEqual(content.status_code, 200)
        self.assertEqual(content["Cache-Control"], "private, no-store, max-age=0")
        self.assertEqual(ConsultationPhotoAccess.objects.get().actor, self.user)
        content.close()

        other = User.objects.create_user("other@example.com", "HairDoc!2026Strong", is_email_verified=True)
        self.authorize(other)
        self.assertEqual(self.client.get(self.photos_url).status_code, 404)

        self.authorize(self.user)
        delete_url = reverse(
            "consultations:photo-detail", kwargs={"public_id": self.case.public_id, "photo_id": photo.public_id},
        )
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, 204)
        self.assertFalse(stored_path.exists())
        self.assertFalse(ConsultationPhoto.objects.exists())

    def test_submit_locks_set_and_staff_reviews_in_app_until_withdrawal(self):
        consent = self.accept_consent()
        photo_data = self.upload().json()["photos"][0]
        submit = self.client.post(reverse("consultations:photos-submit", kwargs={"public_id": self.case.public_id}), {})
        self.assertEqual(submit.status_code, 200)
        self.assertEqual(submit.json()["status"], ConsultationCase.Status.PHOTOS_COMPLETE)
        self.assertEqual(self.upload().status_code, 400)
        photo = ConsultationPhoto.objects.get()
        self.assertEqual(
            self.client.delete(reverse(
                "consultations:photo-detail", kwargs={"public_id": self.case.public_id, "photo_id": photo.public_id},
            )).status_code,
            400,
        )

        self.authorize(self.staff)
        queue = self.client.get(reverse("consultations:staff-case-list"))
        self.assertEqual(queue.status_code, 200)
        self.assertEqual(queue.json()[0]["photo_count"], 1)
        detail = self.client.get(reverse("consultations:staff-case-detail", kwargs={"public_id": self.case.public_id}))
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["client"]["email"], self.user.email)
        self.assertEqual(detail.json()["answers"][0]["value"], "hair_health")
        self.assertEqual(detail.json()["answers"][0]["display_value"], "Improve overall hair health")
        staff_content_path = detail.json()["photos"][0]["content_path"]
        staff_content = self.client.get(staff_content_path)
        self.assertEqual(staff_content.status_code, 200)
        staff_content.close()
        self.assertTrue(ConsultationPhotoAccess.objects.filter(purpose="STAFF_REVIEW", actor=self.staff).exists())

        other_staff = User.objects.create_user(
            "other-staff@example.com", "HairDoc!2026Strong", is_email_verified=True, is_staff=True,
        )
        self.authorize(other_staff)
        self.assertEqual(self.client.get(reverse("consultations:staff-case-list")).json(), [])
        self.assertEqual(
            self.client.get(reverse("consultations:staff-case-detail", kwargs={"public_id": self.case.public_id})).status_code,
            404,
        )

        self.authorize(self.staff)

        consent.withdrawn_at = timezone.now()
        consent.save(update_fields=("withdrawn_at",))
        self.assertEqual(self.client.get(staff_content_path).status_code, 400)
        withdrawn = self.client.get(reverse("consultations:staff-case-detail", kwargs={"public_id": self.case.public_id}))
        self.assertFalse(withdrawn.json()["photo_consent_active"])
        self.assertIsNone(withdrawn.json()["photos"][0]["content_path"])

    def test_empty_photo_set_cannot_be_submitted_and_nonstaff_cannot_review(self):
        self.accept_consent()
        submit = self.client.post(reverse("consultations:photos-submit", kwargs={"public_id": self.case.public_id}), {})
        self.assertEqual(submit.status_code, 400)
        self.assertEqual(self.client.get(reverse("consultations:staff-case-list")).status_code, 403)

    def test_development_can_use_real_upload_flow_before_consent_copy_exists(self):
        with self.settings(PHOTO_CONSENT_REQUIRED=False):
            uploaded = self.upload()
            self.assertEqual(uploaded.status_code, 201)
            self.assertFalse(uploaded.json()["consent"]["required"])
            self.assertFalse(uploaded.json()["consent"]["accepted"])
            photo = ConsultationPhoto.objects.get()
            self.assertIsNone(photo.consent_document)
            self.assertIsNone(photo.consent_accepted_at)
            submitted = self.client.post(
                reverse("consultations:photos-submit", kwargs={"public_id": self.case.public_id}),
                {},
            )
            self.assertEqual(submitted.status_code, 200)
