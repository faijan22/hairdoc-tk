from datetime import timedelta
from pathlib import Path
import tempfile
from uuid import uuid4

from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import ClientHairProfile, DeviceSession, NotificationPreference, User
from apps.accounts.services import create_device_session
from apps.consultations.models import Appointment, ConsultationCase, ConsultationService
from apps.messaging.models import Conversation, Message
from apps.messaging.services import create_message, ensure_consultation_conversation
from apps.payments.models import Order, Payment
from apps.private_media.models import StoredFile
from apps.private_media.storage import get_storage_provider


class AccountDeletionTests(APITestCase):
    password = "HairDoc!2026Strong"

    def setUp(self):
        self.user = User.objects.create_user(
            "delete-me@example.com", self.password, is_email_verified=True
        )
        self.tk = User.objects.create_user(
            "tk-delete-test@example.com", self.password,
            is_email_verified=True, is_staff=True,
        )
        access, _, _ = create_device_session(self.user, "Deletion test")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    def test_deletion_requires_password_and_exact_confirmation_then_deidentifies(self):
        ClientHairProfile.objects.create(user=self.user, concerns="Private concern")
        NotificationPreference.objects.create(user=self.user, timezone="Europe/London")
        service = ConsultationService.objects.create(
            name="Deletion audit consultation", slug=f"deletion-{uuid4()}",
            short_description="Test", description="Test", duration_minutes=30,
            price_amount="50.00", currency="GBP", status=ConsultationService.Status.PUBLISHED,
            published_at=timezone.now(), expert=self.tk,
        )
        case = ConsultationCase.objects.create(
            client=self.user, service=service, status=ConsultationCase.Status.PHOTOS_COMPLETE,
            timezone_snapshot="Europe/London", hair_profile_snapshot={"concerns": "Private concern"},
            service_name=service.name, duration_minutes=30, price_amount="50.00", currency="GBP",
            intake_completed_at=timezone.now(), photos_completed_at=timezone.now(),
        )
        appointment = Appointment.objects.create(
            case=case, client=self.user, expert=self.tk,
            starts_at=timezone.now() + timedelta(days=2),
            ends_at=timezone.now() + timedelta(days=2, minutes=30),
            status=Appointment.Status.CONFIRMED,
            client_timezone="Europe/London", expert_timezone="Europe/London",
        )
        order = Order.objects.create(
            user=self.user, appointment=appointment, status=Order.Status.PAID,
            subtotal_amount="50.00", total_amount="50.00", currency="GBP", paid_at=timezone.now(),
        )
        Payment.objects.create(
            order=order, user=self.user, provider="STRIPE", status=Payment.Status.SUCCEEDED,
            amount="50.00", currency="GBP", paid_at=timezone.now(),
        )
        conversation = ensure_consultation_conversation(appointment)
        create_message(conversation, self.user, "Private message", uuid4())

        url = reverse("accounts:account-delete")
        self.assertEqual(
            self.client.post(url, {"current_password": self.password, "confirmation": "delete"}, format="json").status_code,
            400,
        )
        self.assertEqual(
            self.client.post(url, {"current_password": "wrong", "confirmation": "DELETE"}, format="json").status_code,
            400,
        )
        original_public_id = self.user.public_id
        with tempfile.TemporaryDirectory() as private_root, self.settings(PRIVATE_MEDIA_ROOT=private_root):
            storage_key = "deletion/private-photo.jpg"
            get_storage_provider().save(storage_key, b"private image bytes")
            StoredFile.objects.create(
                owner=self.user, storage_key=storage_key, original_name="private-photo.jpg",
                content_type="image/jpeg", byte_size=19, checksum_sha256="0" * 64,
                width=10, height=10,
            )
            self.assertEqual(
                self.client.post(url, {"current_password": self.password, "confirmation": "DELETE"}, format="json").status_code,
                204,
            )
            self.assertFalse(Path(private_root, storage_key).exists())

        self.user.refresh_from_db()
        case.refresh_from_db()
        self.assertFalse(self.user.is_active)
        self.assertIsNotNone(self.user.deleted_at)
        self.assertNotEqual(self.user.public_id, original_public_id)
        self.assertTrue(self.user.email.endswith("@deleted.invalid"))
        self.assertEqual(self.user.first_name, "")
        self.assertFalse(self.user.has_usable_password())
        self.assertEqual(case.hair_profile_snapshot, {})
        self.assertEqual(case.timezone_snapshot, "UTC")
        self.assertEqual(Message.objects.count(), 0)
        self.assertEqual(Conversation.objects.count(), 0)
        self.assertEqual(DeviceSession.objects.filter(user=self.user).count(), 0)
        self.assertTrue(Payment.objects.filter(order=order, user=self.user).exists())
        self.assertEqual(self.client.get(reverse("accounts:me")).status_code, 401)

    def test_staff_account_deletion_fails_closed(self):
        access, _, _ = create_device_session(self.tk, "Staff deletion test")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        response = self.client.post(
            reverse("accounts:account-delete"),
            {"current_password": self.password, "confirmation": "DELETE"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.tk.refresh_from_db()
        self.assertTrue(self.tk.is_active)
