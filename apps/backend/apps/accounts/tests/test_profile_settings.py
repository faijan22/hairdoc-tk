from datetime import timedelta
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import LegalDocument, User, UserConsent
from apps.accounts.services import create_device_session


class ProfileSettingsApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="client@example.com",
            password="HairDoc!2026Strong",
            is_email_verified=True,
        )
        access, _, _ = create_device_session(self.user, "Test phone")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    def test_personal_hair_and_preferences_are_editable_and_user_scoped(self):
        personal = self.client.patch(
            reverse("accounts:me"),
            {"first_name": "Taylor", "last_name": "King", "phone": "+44 20 1234 5678", "email": "ignored@example.com"},
            format="json",
        )
        self.assertEqual(personal.status_code, 200)
        self.assertEqual(personal.json()["email"], self.user.email)
        self.assertEqual(personal.json()["phone"], "+44 20 1234 5678")

        hair = self.client.patch(
            reverse("accounts:hair-profile"),
            {"hair_texture": "CURLY", "scalp_type": "SENSITIVE", "goals": "Improve scalp comfort."},
            format="json",
        )
        self.assertEqual(hair.status_code, 200)
        self.assertEqual(hair.json()["hair_texture"], "CURLY")

        preferences = self.client.patch(
            reverse("accounts:notification-preferences"),
            {"timezone": "Asia/Kolkata", "coaching_updates": False},
            format="json",
        )
        self.assertEqual(preferences.status_code, 200)
        self.assertEqual(preferences.json()["timezone"], "Asia/Kolkata")
        self.assertFalse(preferences.json()["coaching_updates"])

        invalid = self.client.patch(
            reverse("accounts:notification-preferences"),
            {"timezone": "Mars/HairDoc"},
            format="json",
        )
        self.assertEqual(invalid.status_code, 400)

        other = User.objects.create_user("other@example.com", "test-password")
        self.assertFalse(hasattr(other, "hair_profile"))

    def test_authentication_is_required_for_personal_settings(self):
        self.client.credentials()
        for route in ("accounts:me", "accounts:hair-profile", "accounts:notification-preferences", "accounts:consents"):
            self.assertEqual(self.client.get(reverse(route)).status_code, 401)


class LegalAndConsentApiTests(APITestCase):
    def setUp(self):
        now = timezone.now()
        self.current = LegalDocument.objects.create(
            type=LegalDocument.Type.PHOTO_DATA_CONSENT,
            version=2,
            title="Photo & Data Consent",
            body="Published owner-approved consent copy.",
            status=LegalDocument.Status.PUBLISHED,
            published_at=now,
        )
        LegalDocument.objects.create(
            type=LegalDocument.Type.PHOTO_DATA_CONSENT,
            version=1,
            title="Previous Photo Consent",
            body="Previous copy.",
            status=LegalDocument.Status.PUBLISHED,
            published_at=now - timedelta(days=30),
        )
        LegalDocument.objects.create(
            type=LegalDocument.Type.PRIVACY,
            version=1,
            title="Draft Privacy Policy",
            body="Not public.",
            status=LegalDocument.Status.DRAFT,
        )
        self.user = User.objects.create_user("legal@example.com", "HairDoc!2026Strong", is_email_verified=True)
        access, _, _ = create_device_session(self.user, "Test phone")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    def test_public_legal_routes_only_return_current_published_document(self):
        self.client.credentials()
        documents = self.client.get(reverse("accounts:legal-list"))
        self.assertEqual(documents.status_code, 200)
        self.assertEqual(len(documents.json()), 1)
        self.assertEqual(documents.json()[0]["version"], 2)
        current = self.client.get(
            reverse("accounts:legal-current", kwargs={"document_type": LegalDocument.Type.PHOTO_DATA_CONSENT})
        )
        self.assertEqual(current.status_code, 200)
        self.assertEqual(current.json()["public_id"], str(self.current.public_id))
        self.assertEqual(
            self.client.get(reverse("accounts:legal-current", kwargs={"document_type": LegalDocument.Type.PRIVACY})).status_code,
            404,
        )

    def test_consent_accept_and_withdraw_are_idempotent_and_versioned(self):
        payload = {"document_public_id": str(self.current.public_id), "accepted": True}
        accepted = self.client.post(reverse("accounts:consents"), payload, format="json")
        self.assertEqual(accepted.status_code, 200)
        self.assertTrue(accepted.json()["accepted"])
        self.client.post(reverse("accounts:consents"), payload, format="json")
        self.assertEqual(UserConsent.objects.count(), 1)

        withdrawn = self.client.post(
            reverse("accounts:consents"),
            {**payload, "accepted": False},
            format="json",
        )
        self.assertEqual(withdrawn.status_code, 200)
        self.assertFalse(withdrawn.json()["accepted"])
        self.assertIsNotNone(withdrawn.json()["withdrawn_at"])

    def test_admin_uploaded_legal_file_is_public_only_after_publish(self):
        with tempfile.TemporaryDirectory() as media_root, self.settings(MEDIA_ROOT=media_root):
            document = LegalDocument.objects.create(
                type=LegalDocument.Type.PRIVACY,
                version=2,
                title="Privacy Policy",
                body="",
                attachment=SimpleUploadedFile(
                    "privacy.pdf", b"%PDF-1.4 local policy", content_type="application/pdf"
                ),
                status=LegalDocument.Status.PUBLISHED,
            )
            self.assertIsNotNone(document.published_at)
            self.client.credentials()
            current = self.client.get(
                reverse("accounts:legal-current", kwargs={"document_type": LegalDocument.Type.PRIVACY})
            )
            self.assertEqual(current.status_code, 200)
            self.assertEqual(current.json()["attachment_name"], "privacy.pdf")
            self.assertIn(str(document.public_id), current.json()["attachment_path"])
            file_response = self.client.get(
                reverse("accounts:legal-file", kwargs={"public_id": document.public_id})
            )
            self.assertEqual(file_response.status_code, 200)
            self.assertEqual(file_response["Content-Type"], "application/pdf")
            self.assertEqual(b"".join(file_response.streaming_content), b"%PDF-1.4 local policy")
