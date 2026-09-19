import io
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image
from rest_framework.test import APITestCase

from apps.accounts.models import LegalDocument, User, UserConsent
from apps.accounts.services import create_device_session
from apps.coaching.models import CoachingPlan, CoachingPlanSection
from apps.consultations.models import ConsultationCase, ConsultationService

from ..models import ProgressCheckIn, ProgressPhoto, ProgressPhotoAccess


class ProgressApiTests(APITestCase):
    def setUp(self):
        self.private_root = tempfile.mkdtemp(prefix="hairdoc-progress-")
        self.override = override_settings(
            PRIVATE_MEDIA_ROOT=self.private_root,
            PHOTO_CONSENT_REQUIRED=True,
        )
        self.override.enable()
        self.client_user = User.objects.create_user("client@example.com", "HairDoc!2026Strong", first_name="Client", is_email_verified=True)
        self.tk = User.objects.create_user("tk@example.com", "HairDoc!2026Strong", is_staff=True, is_email_verified=True)
        self.other_staff = User.objects.create_user("other@example.com", "HairDoc!2026Strong", is_staff=True, is_email_verified=True)
        self.service = ConsultationService.objects.create(name="Care", slug="care", short_description="Care", description="Care", duration_minutes=30, price_amount="0", currency="USD", status=ConsultationService.Status.PUBLISHED, published_at=timezone.now(), expert=self.tk)
        self.case = ConsultationCase.objects.create(client=self.client_user, service=self.service, status=ConsultationCase.Status.PHOTOS_COMPLETE, timezone_snapshot="UTC", service_name="Care", duration_minutes=30, price_amount="0", currency="USD", intake_completed_at=timezone.now(), photos_completed_at=timezone.now())
        self.document = LegalDocument.objects.create(type=LegalDocument.Type.PHOTO_DATA_CONSENT, version=1, title="Photo consent", body="Test consent", status=LegalDocument.Status.PUBLISHED, published_at=timezone.now())
        UserConsent.objects.create(user=self.client_user, legal_document=self.document, accepted_at=timezone.now())

    def tearDown(self):
        self.override.disable()
        shutil.rmtree(self.private_root, ignore_errors=True)

    def authorize(self, user):
        access, _, _ = create_device_session(user, "Test")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    def image(self):
        content = io.BytesIO()
        Image.new("RGB", (800, 600), "#765847").save(content, format="PNG")
        return SimpleUploadedFile("progress.png", content.getvalue(), content_type="image/png")

    def publish_plan(self):
        plan = CoachingPlan.objects.create(case=self.case, author=self.tk, version=1, title="Plan", status=CoachingPlan.Status.DRAFT)
        CoachingPlanSection.objects.create(plan=plan, title="Routine", body="Follow routine", display_order=0)
        plan.status = CoachingPlan.Status.PUBLISHED
        plan.published_at = timezone.now()
        plan.save(update_fields=("status", "published_at", "updated_at"))

    def test_complete_client_to_tk_review_flow(self):
        self.publish_plan()
        self.authorize(self.client_user)
        case_url = reverse("progress:client-case-list-create", kwargs={"case_id": self.case.public_id})
        created = self.client.post(case_url, {}, format="json")
        self.assertEqual(created.status_code, 201)
        check_id = created.json()["public_id"]
        detail_url = reverse("progress:client-detail", kwargs={"public_id": check_id})
        updated = self.client.patch(detail_url, {"summary": "Less irritation this month.", "wins": "Consistent routine", "challenges": "Dryness", "routine_adherence": 4, "questions_for_tk": "Should I adjust wash days?"}, format="json")
        self.assertEqual(updated.status_code, 200)
        photos_url = reverse("progress:photos", kwargs={"public_id": check_id})
        uploaded = self.client.post(photos_url, {"file": self.image(), "category": "TOP"}, format="multipart")
        self.assertEqual(uploaded.status_code, 201)
        content_path = uploaded.json()["photos"][0]["content_path"]
        content = self.client.get(content_path)
        self.assertEqual(content.status_code, 200)
        content.close()
        self.assertTrue(ProgressPhotoAccess.objects.filter(purpose="CLIENT_VIEW").exists())
        submitted = self.client.post(reverse("progress:client-submit", kwargs={"public_id": check_id}), {}, format="json")
        self.assertEqual(submitted.json()["status"], "SUBMITTED")
        self.assertEqual(self.client.patch(detail_url, {"summary": "Changed"}, format="json").status_code, 400)

        self.authorize(self.tk)
        queue = self.client.get(reverse("progress:staff-list"))
        self.assertEqual(queue.status_code, 200)
        self.assertEqual(queue.json()[0]["client_name"], "Client")
        staff_url = reverse("progress:staff-detail", kwargs={"public_id": check_id})
        self.assertEqual(self.client.patch(staff_url, {"expert_feedback": "Continue the routine and reduce heat."}, format="json").status_code, 200)

        self.authorize(self.client_user)
        self.assertEqual(self.client.get(detail_url).json()["expert_feedback"], "")

        self.authorize(self.tk)
        reviewed = self.client.post(reverse("progress:staff-publish", kwargs={"public_id": check_id}), {}, format="json")
        self.assertEqual(reviewed.json()["status"], "REVIEWED")

        self.authorize(self.client_user)
        self.assertEqual(self.client.get(detail_url).json()["expert_feedback"], "Continue the routine and reduce heat.")

        self.authorize(self.other_staff)
        self.assertEqual(self.client.get(staff_url).status_code, 404)

    def test_requires_published_plan_and_photo(self):
        self.authorize(self.client_user)
        case_url = reverse("progress:client-case-list-create", kwargs={"case_id": self.case.public_id})
        self.assertEqual(self.client.post(case_url, {}, format="json").status_code, 400)
        self.publish_plan()
        created = self.client.post(case_url, {}, format="json")
        check_id = created.json()["public_id"]
        self.client.patch(reverse("progress:client-detail", kwargs={"public_id": check_id}), {"summary": "Update"}, format="json")
        self.assertEqual(self.client.post(reverse("progress:client-submit", kwargs={"public_id": check_id}), {}, format="json").status_code, 400)
        self.assertEqual(ProgressCheckIn.objects.get(public_id=check_id).status, ProgressCheckIn.Status.DRAFT)

    def test_development_photo_upload_does_not_create_fake_consent(self):
        self.publish_plan()
        UserConsent.objects.filter(user=self.client_user).delete()
        self.authorize(self.client_user)
        case_url = reverse("progress:client-case-list-create", kwargs={"case_id": self.case.public_id})
        created = self.client.post(case_url, {}, format="json")
        photos_url = reverse("progress:photos", kwargs={"public_id": created.json()["public_id"]})
        with self.settings(PHOTO_CONSENT_REQUIRED=False):
            uploaded = self.client.post(
                photos_url,
                {"file": self.image(), "category": "TOP"},
                format="multipart",
            )
            self.assertEqual(uploaded.status_code, 201)
            self.assertFalse(uploaded.json()["consent"]["required"])
            photo = ProgressPhoto.objects.get()
            self.assertIsNone(photo.consent_document)
            self.assertIsNone(photo.consent_accepted_at)
